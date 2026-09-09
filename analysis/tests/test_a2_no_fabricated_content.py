"""A2: a decode failure on a content path must DEFER, never fill the gap with zeros.

`_recover_inline_extent_content` promises "the bytes ... or None to DEFER (never wrong output)". Three
paths broke that promise by continuing past a failure, leaving the affected file-VCNs zero in a buffer
that was then returned as the file's content:

  * the shared-block map failing to decode its rows      -> `return {}`  (read as "shares no blocks")
  * one snapshot sub-stream failing to parse             -> `continue`   (that stream's blocks lost)
  * a shared block failing to translate, or reading short -> `continue`  (that VCN left zero)

That is E83's defect — snapshot CoW blocks read as holes — arriving through an exception path instead of
a missing feature. None of the three fires on any corpus image, so injection is the only proof they now
behave: each test forces the failure and asserts the caller declines to answer.
"""
import pytest

import forefst as F


class _Boom(ValueError):
    """A decode failure of a type the production code is written to catch."""


def test_incomplete_evidence_is_not_a_generic_exception():
    """It must be catchable precisely, or callers will swallow unrelated bugs with it."""
    assert issubclass(F.IncompleteEvidence, Exception)
    assert F.IncompleteEvidence is not Exception


def test_row_decode_failure_raises_instead_of_reporting_no_shared_blocks(monkeypatch):
    """`return {}` was indistinguishable from a file that genuinely shares nothing."""
    def boom(vd, ctx):
        raise _Boom("rows unreadable")
    monkeypatch.setattr(F, "parse_resident_btree_rows", boom)
    with pytest.raises(F.IncompleteEvidence):
        F._snapshot_shared_blocks(b"\x00" * 64, (None, 0, 4096, None), 1 << 20)


def test_a_snapshot_substream_that_will_not_parse_raises(monkeypatch):
    """One unparseable stream truncates the map; the map is all-or-nothing."""
    k = bytearray(0x18)
    k[0x0C] = 0x80                      # the row kind the scan accepts
    k[0x10:0x18] = (0x1234).to_bytes(8, "little")     # sub-stream id in range
    v = bytearray(0x50)
    v[4:8] = F.SNAP_DATA_DESC.to_bytes(4, "little")
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx: [(bytes(k), bytes(v))])

    def boom(v_, ncl, tr):
        raise _Boom("stream unparseable")
    monkeypatch.setattr(F, "parse_snapshot_data_entry", boom)
    with pytest.raises(F.IncompleteEvidence):
        F._snapshot_shared_blocks(b"\x00" * 64, (None, 0, 4096, None), 1 << 20)


def test_the_substream_scan_still_returns_a_map_when_nothing_fails(monkeypatch):
    """The raise must be reached only by failure -- otherwise it would defer on healthy files."""
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx: [])
    assert F._snapshot_shared_blocks(b"\x00" * 64, (None, 0, 4096, None), 1 << 20) == {}


def _holder(cs=4096):
    """A minimal 0x10028 $DATA holder that passes every check before the snapshot lookup.

    Built rather than borrowed from an image so the test runs in a clone with no corpus. One cluster
    allocated, one cluster of stream: the coverage gate accepts it and the shared lookup is reached.
    """
    k = bytearray(0x18)
    k[12] = 0x80
    k[13] = 0x00
    k[0x10:0x18] = (0x1000).to_bytes(8, "little")      # the CURRENT stream
    v = bytearray(0x50)
    v[0:4] = (0x20).to_bytes(4, "little")              # ihdr
    v[4:8] = F.SNAP_DATA_DESC.to_bytes(4, "little")
    v[0x34:0x38] = (1).to_bytes(4, "little")           # ecount at ihdr+0x14
    v[0x38:0x40] = (cs).to_bytes(8, "little")          # stream_size = one cluster
    v[0x48:0x50] = (cs).to_bytes(8, "little")          # allocated  = one cluster
    return bytes(k), bytes(v)


@pytest.fixture
def recoverable(monkeypatch):
    """`_recover_inline_extent_content` wired to reach its snapshot lookup on a synthetic volume."""
    import io
    cs = 4096
    k, v = _holder(cs)
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx: [(k, v)])
    monkeypatch.setattr(F, "_decode_inline_extents", lambda *a, **kw: [(0, 5, 1)])
    monkeypatch.setattr(F, "_volume_ncl", lambda *a, **kw: 1 << 20)
    return io.BytesIO(b"\x00" * (16 * cs)), cs, v


def test_control_the_holder_reassembles_when_nothing_fails(recoverable, monkeypatch):
    """Positive control: without an injected failure this value DOES produce content.

    Without it, the deferral test below would pass even if the function had declined for some unrelated
    reason, which is how a test comes to prove nothing.
    """
    fh, cs, v = recoverable
    monkeypatch.setattr(F, "_snapshot_shared_blocks", lambda *a, **kw: {})
    assert F._recover_inline_extent_content(fh, 0, cs, None, b"") == b"\x00" * cs


def test_content_recovery_defers_when_the_shared_map_is_incomplete(recoverable, monkeypatch):
    """The caller must turn IncompleteEvidence into None rather than emit a partly-zero file."""
    fh, cs, v = recoverable

    def boom(*a, **kw):
        raise F.IncompleteEvidence("injected")
    monkeypatch.setattr(F, "_snapshot_shared_blocks", boom)
    assert F._recover_inline_extent_content(fh, 0, cs, None, b"") is None


class _TrFailsOn:
    """Translates every VLCN except one, so a failure can be aimed at the shared block alone."""

    def __init__(self, bad):
        self.bad = bad

    def tr(self, vlcn):
        if vlcn == self.bad:
            raise ValueError("untranslatable")
        return vlcn


def test_a_shared_block_that_will_not_translate_defers(monkeypatch):
    """The VCN would otherwise never reach `exts` and would come back as zeros.

    The stream is TWO clusters with ONE allocated, so VCN 1 is not covered by the file's own extents and
    the shared lookup is genuinely consulted for it. An earlier version of this test used a one-cluster
    stream, where VCN 0 is already covered: the shared loop never ran, the main extent loop raised
    instead, and the test passed without touching the path it names.
    """
    import io
    cs = 4096
    k = bytearray(0x18)
    k[12] = 0x80
    k[0x10:0x18] = (0x1000).to_bytes(8, "little")
    v = bytearray(0x50)
    v[0:4] = (0x20).to_bytes(4, "little")
    v[4:8] = F.SNAP_DATA_DESC.to_bytes(4, "little")
    v[0x34:0x38] = (1).to_bytes(4, "little")
    v[0x38:0x40] = (2 * cs).to_bytes(8, "little")     # stream = 2 clusters
    v[0x48:0x50] = (cs).to_bytes(8, "little")         # allocated = 1 cluster -> VCN 1 is not owned
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx: [(bytes(k), bytes(v))])
    monkeypatch.setattr(F, "_decode_inline_extents", lambda *a, **kw: [(0, 5, 1)])
    monkeypatch.setattr(F, "_volume_ncl", lambda *a, **kw: 1 << 20)
    fh = io.BytesIO(b"\x00" * (16 * cs))

    # control: VCN 1 shared and translatable -> content comes back, 2 clusters long
    monkeypatch.setattr(F, "_snapshot_shared_blocks", lambda *a, **kw: {1: 7})
    assert F._recover_inline_extent_content(fh, 0, cs, _TrFailsOn(None), b"") == b"\x00" * (2 * cs)

    # the same file, with only the SHARED block untranslatable -> defer, not a zero-filled cluster
    assert F._recover_inline_extent_content(fh, 0, cs, _TrFailsOn(7), b"") is None


def test_an_unreadable_page_is_not_silently_dropped_from_integrity(monkeypatch):
    """`integrity` must not pronounce a clean verdict over pages it could not read.

    `_read_full_page` returned b"" on any read failure, and the caller's only test was
    `pg[:4] != b"MSB+"` -- so an unreadable page took the same exit as a page that simply is not a
    B+ page: not checked, not counted, not mentioned. It now returns None, which the caller counts
    separately and the report names.
    """
    import io

    class _Tr:
        shift = 0

        def tr(self, vlcn):
            raise OSError("cluster not present in this image")

    fh = io.BytesIO(b"\x00" * (16 * 4096))
    assert F._read_full_page(fh, 0, 4096, [1], _Tr()) is None, \
        "a read failure must be distinguishable from an empty or non-B+ page"


def test_a_readable_page_still_comes_back(monkeypatch):
    """Control: the None above must mean failure, not that the function stopped working."""
    import io
    buf = bytearray(b"\x00" * (16 * 4096))
    buf[4096:4100] = b"MSB+"
    fh = io.BytesIO(bytes(buf))
    pg = F._read_full_page(fh, 0, 4096, [1], None)
    assert pg is not None and pg[:4] == b"MSB+"


def test_undeterminable_hole_coverage_is_not_reported_as_no_holes(monkeypatch):
    """`_extent_hole_ranges` returns None for "cannot tell" and [] for "no holes".

    `cmd_extract` tested `if _hranges:`, which collapses the two -- so a file whose hole coverage could
    not be read was written with no note and exit 0, and `--refuse-holes` did not refuse. The helper's
    own contract is checked here; the caller's branch is covered by the source assertion below, because
    driving a real extract needs a corpus image.
    """
    import io
    # exts present but the reader is not a named file => undeterminable, NOT "no holes"
    fake = io.BytesIO(b"\x00" * 4096)
    exts = [{"plcn": 1, "clusters": 1}]
    assert F._extent_hole_ranges(fake, 0, 4096, exts, 4096) is None
    assert F._extent_hole_bytes(fake, 0, 4096, exts) is None
    # no extents at all is a genuine "nothing to report", and must NOT be None
    assert F._extent_hole_ranges(fake, 0, 4096, [], 4096) == []
    assert F._extent_hole_bytes(fake, 0, 4096, []) == 0


def test_extract_branches_on_none_before_truthiness():
    """The `is None` branch must come BEFORE `if _hranges:`, or the two collapse again."""
    import inspect
    src = inspect.getsource(F.cmd_extract)
    i_none = src.index("if _hranges is None:")
    i_truthy = src.index("if _hranges:")
    assert i_none < i_truthy, "the undeterminable case must be handled before the truthiness test"
    assert "--refuse-holes: hole coverage is undeterminable" in src, \
        "the strict flag must refuse when coverage cannot be confirmed"


def test_export_resident_all_summary_uses_the_current_vocabulary():
    """Pins the one line the golden deliberately does not cover.

    `export resident-all` writes 47,843 files / 220 MB in 50 s on the largest corpus image, so a golden
    row for it was measured and rejected as disproportionate: the only part worth guarding is its stderr
    summary. That line printed `CoW-shared` while the tool's residency value is `snapshot-shared`, and no
    gate would have caught it, so it is pinned here instead.
    """
    import inspect
    src = inspect.getsource(F.cmd_export_resident)
    assert "CoW-shared" not in src, \
        "export prints a residency word the tool does not emit; use snapshot-shared"
    assert "snapshot-shared" in src, "the summary should name the residency form it wrote"


def test_a_deferral_is_recorded_and_named(monkeypatch):
    """A declined stream must be visible: named, counted, and not a silent absence.

    Deferring is the correct behaviour -- it is how the reassembler avoids emitting bytes the volume does
    not support. But a deferral that shows up only as a missing file is the silent-default class in
    another form: the caller exits 0, no file appears, and nothing says which file or why.
    """
    import io
    del F._DEFERRALS[:]
    cs = 4096
    k = bytearray(0x18); k[12] = 0x80
    k[0x10:0x18] = (0x1000).to_bytes(8, "little")
    v = bytearray(0x50)
    v[0:4] = (0x20).to_bytes(4, "little")
    v[4:8] = F.SNAP_DATA_DESC.to_bytes(4, "little")
    v[0x34:0x38] = (1).to_bytes(4, "little")
    v[0x38:0x40] = (cs).to_bytes(8, "little")
    v[0x48:0x50] = (cs).to_bytes(8, "little")
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx: [(bytes(k), bytes(v))])
    monkeypatch.setattr(F, "_decode_inline_extents", lambda *a, **kw: [(0, 5, 1)])
    monkeypatch.setattr(F, "_volume_ncl", lambda *a, **kw: 1 << 20)

    def boom(*a, **kw):
        raise F.IncompleteEvidence("injected")
    monkeypatch.setattr(F, "_snapshot_shared_blocks", boom)

    fh = io.BytesIO(b"\x00" * (16 * cs))
    assert F._recover_inline_extent_content(fh, 0, cs, None, b"", _defer_ctx="'secret.txt'") is None
    assert len(F._DEFERRALS) == 1, "the deferral was not recorded"
    where, why = F._DEFERRALS[0]
    assert "secret.txt" in where, "the record does not name the file"
    assert "snapshot shared-block map" in why, "the record does not give the cause"
    del F._DEFERRALS[:]


def test_extract_exits_2_when_a_requested_file_is_deferred():
    """Exit 0 with no file written is indistinguishable from success."""
    import inspect
    src = inspect.getsource(F.cmd_extract)
    assert "len(_DEFERRALS) > _before" in src, "extract does not notice a deferral during its own call"
    i_ret = src.index("len(_DEFERRALS) > _before")
    assert "return 2" in src[i_ret:i_ret + 700], "a deferred request must not exit 0"


def test_both_hole_sidecars_carry_a_machine_readable_status():
    """An examiner keeping sidecars must not have to infer 'checked and clean' from a missing file.

    Two evidential positions exist and they are different: holes were found, or hole coverage could not
    be determined at all. Both now write a sidecar and both carry `status`.
    """
    import inspect
    src = inspect.getsource(F.cmd_extract)
    assert '"status": "holes_present"' in src
    assert '"status": "undeterminable"' in src
    i_und = src.index('"status": "undeterminable"')
    assert '"ranges": []' in src[i_und - 400:i_und + 400], \
        "the undeterminable sidecar must not imply an empty hole list means no holes"
