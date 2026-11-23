"""`$J` is a ring, and a record's USN IS its byte offset in that ring.

`usn % alloc == offset` holds on every genuine record: measured 217,892/217,892 on `winsider`,
9,371/9,378 on `win11refstestmftecmd`, 33,379/33,381 on `win11refs8gtestmove_aftermove` — the
few failures are zero-filled slack that happens to parse as a record. The invariant is reported,
never used to drop records: a torn or overwritten record is evidence.

Buffer order is only time order until the ring wraps. `winsider` IS wrapped (one descending step
in 217,892 records — the first wrapped journal observed on this corpus), so the listing is sorted
by USN to restore chronology.
"""
import struct

import forefst as F


def _rec(usn, name="a", reclen=None):
    """A minimal USN_RECORD_V3: 128-bit file ids push Usn to +0x28."""
    nm = name.encode("utf-16-le")
    body = 0x4C + len(nm)
    rl = reclen if reclen is not None else (body + 7) & ~7
    r = bytearray(rl)
    struct.pack_into("<I", r, 0x00, rl)
    struct.pack_into("<H", r, 0x04, 3)          # major version 3
    struct.pack_into("<Q", r, 0x28, usn)
    struct.pack_into("<H", r, 0x48, len(nm))    # name length
    struct.pack_into("<H", r, 0x4A, 0x4C)       # name offset
    r[0x4C:0x4C + len(nm)] = nm
    return bytes(r)


def _journal(records, alloc):
    """Lay records at the offsets their USNs imply, so the invariant holds by construction."""
    buf = bytearray(alloc)
    for usn, name in records:
        r = _rec(usn, name)
        buf[usn:usn + len(r)] = r
    return bytes(buf)


def test_usn_is_the_record_offset():
    alloc = 0x10000
    data = _journal([(0x100, "a"), (0x200, "b"), (0x300, "c")], alloc)
    recs = F.parse_usn_records(data, alloc=alloc)
    assert [r.usn for r in recs] == [0x100, 0x200, 0x300]
    assert all(r.usn % alloc == r.offset for r in recs)


def test_a_record_whose_usn_is_not_its_offset_is_kept_not_dropped():
    """Violations are reported. Dropping them would discard a torn or overwritten record."""
    alloc = 0x10000
    buf = bytearray(alloc)
    r = _rec(0x999)                      # USN disagrees with where it is placed
    buf[0x100:0x100 + len(r)] = r
    recs = F.parse_usn_records(bytes(buf), alloc=alloc)
    assert len(recs) == 1
    assert recs[0].usn == 0x999 and recs[0].offset == 0x100


def test_zero_filled_slack_is_not_reported_as_torn():
    """An unwrapped journal is mostly zeros; that is normal and must not raise a caveat."""
    F._SKIP_NOTES.clear()
    data = _journal([(0x100, "a")], 0x8000)
    F.parse_usn_records(data, alloc=0x8000)
    assert not any(k[0] == "USN journal" for k in F._SKIP_NOTES), F._SKIP_NOTES


def test_non_zero_unparseable_bytes_are_reported():
    """Beyond the last record they are unwritten ring space: a note about the data (expected), not a skip."""
    F._SKIP_NOTES.clear(); F._SKIP_EXPECTED.clear()
    buf = bytearray(_journal([(0x100, "a")], 0x8000))
    buf[0x2000:0x2040] = b"\xde\xad\xbe\xef" * 16      # non-zero, parses as no record
    F.parse_usn_records(bytes(buf), alloc=0x8000)
    assert any(k[0] == "USN journal" for k in F._SKIP_EXPECTED)
    assert not any(k[0] == "USN journal" for k in F._SKIP_NOTES)
    F._SKIP_EXPECTED.clear()


def test_non_zero_unparseable_bytes_inside_the_written_span_are_a_skip():
    F._SKIP_NOTES.clear(); F._SKIP_EXPECTED.clear()
    buf = bytearray(_journal([(0x100, "a"), (0x4000, "b")], 0x8000))
    buf[0x2000:0x2040] = b"\xde\xad\xbe\xef" * 16      # between two records: torn or overwritten
    F.parse_usn_records(bytes(buf), alloc=0x8000)
    assert any(k[0] == "USN journal" for k in F._SKIP_NOTES)
    assert not F._SKIP_EXPECTED
    F._SKIP_NOTES.clear()


def _fresh_registers(monkeypatch):
    """N420 (LB55): empty run registers for one node, restored by monkeypatch, so a report made here neither reaches
    the process's at-exit print nor hides behind an earlier node's."""
    for name in ("_FINDINGS", "_SKIP_NOTES", "_SKIP_EXPECTED", "_SKIP_FINDING"):
        monkeypatch.setattr(F, name, type(getattr(F, name))())


def test_alloc_omitted_means_no_invariant_check(monkeypatch, capsys):
    """Existing call sites pass no allocation and must behave exactly as before: no USN-offset check, so no report of a
    record whose USN is not its offset.

    N420 (LB55): this node looked for the report among `_SKIP_NOTES`' KEYS, which are (stage, exception name) and never
    hold a message -- and since N403 the report is a finding, not a skip -- so it could not fail. It now looks where the
    report is made (the findings and stderr), on fresh registers, and a planted control shows the reader sees it: the
    same buffer parsed WITH the allocation reports the record."""
    buf = bytearray(0x8000)
    r = _rec(0x999)
    buf[0x100:0x100 + len(r)] = r

    def reported():
        err = capsys.readouterr().err
        return [t for t in F._findings() if "journal offset" in t] + \
            [ln for ln in err.splitlines() if "journal offset" in ln]

    _fresh_registers(monkeypatch)
    recs = F.parse_usn_records(bytes(buf), alloc=0x8000)
    assert len(recs) == 1 and reported(), "the planted control: with the allocation, the record whose USN (0x999) is " \
        "not its offset (0x100) is reported -- so the reader below can see a report"
    _fresh_registers(monkeypatch)
    recs = F.parse_usn_records(bytes(buf))
    assert len(recs) == 1
    got = reported()
    assert not got, "no allocation was passed, so no USN-offset check is made: %r" % got[:2]
