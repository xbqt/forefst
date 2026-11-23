"""Wave D step D3b (1.14.0, PLAN_1.13.2.md decision 51): the two follow-up changes of step D3, each measured before it
was coded (`analysis/reports/v1.13.2/fixes/D3_DEEP_ANALYSIS.md`, `fixes/D3b_NOTES.md`; evidence `fixes/D3_evidence/`).

What each group asserts
-----------------------
C3-1   a page with another volume's signature is an earlier volume's when its address tuple, read in the page's OWN
       units (4 LCNs = 4 KiB clusters, 1 = 64 KiB), names where it lies -- directly or through this volume's container
       table; on a volume of 64 KiB clusters the scan also looks at each 4 KiB step inside a cluster for such pages
       (an earlier volume of 4 KiB clusters left 16 KiB pages there), never inside a page already met;
       `deleted --earlier-volumes` reads each page at its own size from where it begins.
N468   (decision 51) IsMoved is read from the change journal where it says how a name came where it is -- by the most
       recent record that puts that name there ("moved (change journal)", "a hard link made here (change journal)";
       a directory by its creation record) -- and only when the journal's history has no break (records whole inside
       its span, not re-created, none missing after its last record); elsewhere the metadata's value. The reading is
       held: nothing it meets changes the exit code. The journal parser steps over a run of zeros at once, with the
       same records and statements.

Volumes: synthetic images built here (the page builder of `test_1132_red_c3_scan.py`); corpus images READ-ONLY,
skipped when absent.
"""
import csv
import os
import re
import shutil
import struct
import tempfile

import pytest

from _repo import REPO                                   # noqa: F401  layout-independent; see _repo.py

import forefst as F                                      # noqa: E402
import test_1132_red_c3_scan as SC                       # noqa: E402  (the page builder)
import test_1132_d3_rest as R3                           # noqa: E402  (the runners)

K64 = 0x10000
SIG = 0x99                                               # an earlier volume's signature (SC.VSIG is this volume's)


def _image(tmp_path, blobs, cs, clusters=16):
    """An image of `clusters` clusters of `cs` bytes, each blob written at its byte offset."""
    path = str(tmp_path / "d3b.raw")
    with open(path, "wb") as fh:
        fh.truncate(clusters * cs)
        for at, data in blobs.items():
            fh.seek(at)
            fh.write(data)
    return path


def _earlier(at, names, units=4096, sig=SIG):
    """An earlier volume's page that begins at byte `at` and names it directly in its own units: a 16 KiB page of 4 KiB
    clusters (4 LCNs) or a 64 KiB page of one 64 KiB cluster (1 LCN). `names` = [(offset in the page, name)]."""
    size = 0x4000 if units == 4096 else K64
    p = bytearray(SC._page(names, list(range(len(names))), sig=sig, size=size))
    if units == 4096:
        struct.pack_into("<4Q", p, 0x20, *[at // 4096 + i for i in range(4)])
    else:
        struct.pack_into("<4Q", p, 0x20, at // K64, 0, 0, 0)
    return bytes(p)


class _Table:
    """A container table that maps VLCN `v` to cluster `c` (and nothing else)."""
    shift = 0

    def __init__(self, v, c):
        self.map = {v: c}
        self._v, self._c = v, c

    def tr(self, v):
        return self._c if v == self._v else v


# ═══ C3-1 -- the address in the page's own units ════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("tup,want", [
    ((0x10, 0x11, 0x12, 0x13), (4096, 4)), ((0x10, 0, 0, 0), (K64, 1)), ((0x10, 0x11, 0, 0), None),
    ((0x10, 0x12, 0x13, 0x14), None), ((0, 0, 0, 0), None), ((0xFFFFFFFFFFFFFFFF, 0, 0, 0), None),
    ((0x10, 0, 0x12, 0), None)], ids=["16k-of-4k", "64k", "two", "gap", "zero", "unset", "hole-then-lcn"])
def test_c31_d3b_a_pages_own_units_come_from_its_tuple(tup, want):
    head = bytearray(0x40)
    struct.pack_into("<4Q", head, 0x20, *tup)
    assert F._page_own_units(bytes(head)) == want


def test_c31_d3b_an_earlier_4k_page_inside_a_64k_cluster_is_at_its_own_address():
    """win11refs15t64k's case: a 16 KiB page of an earlier volume of 4 KiB clusters, 16 KiB into a 64 KiB cluster --
    its tuple x 4096 is its byte offset directly, or (through this volume's table) maps to the cluster it lies in,
    with the same offset inside it. Read in this volume's units it lay nowhere (the D3 test counted none of 634)."""
    direct = _earlier(0xa0 * K64 + 0x4000, [(0x200, "a.txt")])[:0x40]
    assert F._page_at_own_address(direct, 0xa0, K64, None, 0x4000) is True
    assert F._page_at_own_address(direct, 0xa0, K64, None, 0x8000) is False             # another place in it
    mapped = bytearray(direct)
    struct.pack_into("<4Q", mapped, 0x20, *[0x10a04 + i for i in range(4)])               # VLCN 0x10a0 (64 KiB units)
    assert F._page_at_own_address(bytes(mapped), 0xa0, K64, _Table(0x10a0, 0xa0), 0x4000) is True
    assert F._page_at_own_address(bytes(mapped), 0xa0, K64, _Table(0x10a0, 0xa1), 0x4000) is False
    assert F._page_at_own_address(bytes(mapped), 0xa0, K64, None, 0x4000) is False


def test_c31_d3b_an_earlier_64k_page_on_a_4k_volume_is_at_its_own_address():
    head = _earlier(0x30 * K64, [(0x200, "a.txt")], units=K64)[:0x40]
    assert F._page_at_own_address(head, 0x300, 4096, None) is True                      # 0x30 x 64 KiB = cluster 0x300
    assert F._page_at_own_address(head, 0x30, 4096, None) is False


def test_c31_d3b_control_the_d3_cases_still_hold():
    """The D3 readings are kept: a 4-LCN tuple naming its cluster on a 4 KiB volume; text starting with "MSB+"."""
    assert F._page_at_own_address(R3._tuple_page(16, SIG)[:0x40], 16, 4096, None) is True
    assert F._page_at_own_address(R3._tuple_page(16, SIG, at_home=False)[:0x40], 16, 4096, None) is False
    text = b'MSB+"\nPAGE_TYPE_MLOG = "MLog"\nPAGE_TYPE_DATA = "' + b"x" * 0x20
    assert F._page_at_own_address(text[:0x40], 16, 4096, None) is False


def _64k_volume(tmp_path):
    own = bytearray(SC._page([(0x200, "mine.txt")], [0], size=K64))
    struct.pack_into("<4Q", own, 0x20, 2, 0, 0, 0)
    fake = bytearray(0x40)                                 # "MSB+" + another signature INSIDE this volume's page
    fake[0:4] = b"MSB+"
    struct.pack_into("<I", fake, 0x0C, 0x77)
    own[0x4000:0x4040] = fake
    first = bytearray(_earlier(6 * K64, [(0x200, "a.txt")]))
    first[0x1000:0x1040] = fake                            # inside the earlier page: not a page of its own
    return _image(tmp_path, {2 * K64: bytes(own), 4 * K64 + 0x8000: _earlier(4 * K64 + 0x8000, [(0x200, "c.txt")]),
                             6 * K64: bytes(first), 6 * K64 + 0x4000: _earlier(6 * K64 + 0x4000, [(0x200, "b.txt")])},
                  K64)


def test_c31_d3b_the_scan_looks_inside_a_64k_cluster_for_another_volumes_pages(tmp_path):
    path = _64k_volume(tmp_path)
    foreign = []
    with open(path, "rb") as f:
        got = [c for c, _b in F._iter_msb_clusters(f, 0, K64, 16, vsig=SC.VSIG, foreign=foreign)]
    assert got == [2], got                                  # only this volume's page is yielded
    assert foreign == [(4, SIG, 0x8000), (6, SIG, 0), (6, SIG, 0x4000)], foreign


def test_c31_d3b_control_a_4k_volume_is_looked_at_cluster_by_cluster(tmp_path):
    foreign = []
    path = _image(tmp_path, {16 * 4096: R3._tuple_page(16, SIG)}, 4096, clusters=64)
    with open(path, "rb") as f:
        list(F._iter_msb_clusters(f, 0, 4096, 64, vsig=SC.VSIG, foreign=foreign))
    assert foreign == [(16, SIG, 0)], foreign


def _listing(path, cs, monkeypatch, capsys, clusters=16):
    monkeypatch.setattr(F, "_orphan_scan_bound", lambda f, ps, c, m: (clusters, clusters, False, None))
    monkeypatch.setattr(F, "volume_format_magic", lambda f, ps, c: SC.VSIG)
    with open(path, "rb") as f:
        rc = F._earlier_volumes_view(f, 0, cs, None, None, None, None, None)
    return rc, capsys.readouterr().out


def test_c31_d3b_the_listing_reads_each_earlier_page_at_its_own_size(tmp_path, monkeypatch, capsys):
    """Each 16 KiB page is read alone: read at this volume's 64 KiB, the page at cluster 6 would also hold b.txt's page
    (b.txt twice). Offsets count from the cluster's start (b.txt: 0x4000 + 0x200)."""
    rc, out = _listing(_64k_volume(tmp_path), K64, monkeypatch, capsys)
    assert rc == 0 and "1 earlier ReFS volume wrote pages here: the area was formatted again at least 1 time." in out
    assert "Earlier volume 0x00000099: 3 page(s) at their own address, 3 entries" in out, out
    rows = re.findall(r"^    (\S+)  created .*@ cluster (0x[0-9a-f]+) off (0x[0-9a-f]+)(.*)$", out, re.M)
    assert [(n, c, o) for n, c, o, _r in rows] == [("a.txt", "0x6", "0x200"), ("b.txt", "0x6", "0x4200"),
                                                   ("c.txt", "0x4", "0x8200")], rows
    assert not any("other cop" in r[3] for r in rows), rows
    assert "mine.txt" not in out, out


def test_c31_d3b_an_earlier_64k_page_on_a_4k_volume_is_read_whole(tmp_path, monkeypatch, capsys):
    """A 64 KiB page of an earlier volume of 64 KiB clusters on a volume of 4 KiB clusters: its rows past 16 KiB are
    read (read at this volume's 16 KiB page size, late.txt was not)."""
    pg = _earlier(0x10 * K64, [(0x200, "early.txt"), (0x8200, "late.txt")], units=K64)
    rc, out = _listing(_image(tmp_path, {0x10 * K64: pg}, 4096, clusters=0x200), 4096, monkeypatch, capsys,
                       clusters=0x200)
    assert rc == 0 and "Earlier volume 0x00000099: 1 page(s) at their own address, 2 entries" in out, out
    assert re.search(r"^    late\.txt  created .*@ cluster 0x100 off 0x8200", out, re.M), out


def test_c31_d3b_a_page_inside_a_cluster_is_said_where_it_begins(tmp_path, monkeypatch, capsys):
    path = _image(tmp_path, {4 * K64 + 0x8000: _earlier(4 * K64 + 0x8000, [(0x200, "c.txt")])}, K64)
    foreign = []
    with open(path, "rb") as f:
        list(F._iter_msb_clusters(f, 0, K64, 16, vsig=SC.VSIG, foreign=foreign))
        F._scan_foreign_said(foreign, SC.VSIG, print, f, 0, K64, None)
    out = capsys.readouterr().out
    assert "(the first at cluster 0x4 + 0x8000 bytes)" in out and "at least 1 time (1 metadata page(s)" in out, out


# ═══ N468 / decision 51 -- IsMoved read from the change journal ═════════════════════════════════════════════════

class _Rec:
    def __init__(self, usn, ref, parent, name, reason):
        self.usn, (self.file_oid, self.file_idx), self.parent_oid, self.filename, self.reason = \
            usn, ref, parent, name, reason


OLD, NEW, LINK, CREATE, CLOSE = 0x1000, 0x2000, 0x10000, 0x100, 0x80000000
H, P, Q = 0x700, 0x710, 0x720                            # the creation directory, two others
REF = (H, 5)


def _journal(monkeypatch, recs, gaps=(), recreated=False, missing=(), note=None):
    """`_journal_moves`' readers fed with `recs` (in USN order as given) and the journal's state."""
    def _locate(f, ps, cs, tr, om):
        if note:
            F._skip_note("locate_change_journal", "the FS-metadata directory", IOError(note))
        return b"vd", {}
    lst = F.UsnRecordList(_Rec(i, *r) for i, r in enumerate(recs))
    lst.span_gaps = list(gaps)
    monkeypatch.setattr(F, "locate_change_journal", _locate)
    monkeypatch.setattr(F, "parse_usn_journal_streams", lambda vd, cs, tr: {"j_extents": [1], "j_stream_size": 0})
    monkeypatch.setattr(F, "read_usn_j_stream", lambda *a, **k: b"\0" * 64)
    monkeypatch.setattr(F, "_usn_j_holes", lambda *a: ([], "hole"))
    monkeypatch.setattr(F, "parse_usn_records", lambda *a, **k: lst)
    monkeypatch.setattr(F, "parse_usn_journal_metadata", lambda *a: {"journal_id": 7})
    monkeypatch.setattr(F, "_usn_journal_state", lambda *a, **k: {"recreated": recreated, "restart": recreated,
                                                                   "missing": list(missing)})


def _file(name, parent=P, links=1):
    return {"name": name, "is_dir": False, "home_oid": H, "parent_oid": parent, "file_id": REF[1],
            "hard_link_count": links}


def _moves(monkeypatch, recs, rows, **kw):
    _journal(monkeypatch, recs, **kw)
    said, state = F._journal_moves(None, 0, 4096, None, {}, rows)
    return [F._is_moved(r) for r in rows], said, state


def test_n468_d3b_a_move_record_says_moved(monkeypatch):
    got, said, state = _moves(monkeypatch, [(REF, H, "a.txt", OLD), (REF, P, "a.txt", NEW)], [_file("a.txt")])
    assert got == ["moved (change journal)"] and state == "read", (got, said)
    assert "read from the change journal (2 records)" in said and "moved 1" in said, said


def test_n468_d3b_a_rename_in_place_keeps_what_brought_the_name(monkeypatch):
    recs = [(REF, H, "a.txt", OLD), (REF, P, "a.txt", NEW), (REF, P, "a.txt", OLD), (REF, P, "b.txt", NEW),
            (REF, P, "b.txt", NEW | CLOSE)]               # the close record repeats the new name: no change
    assert _moves(monkeypatch, recs, [_file("b.txt")])[0] == ["moved (change journal)"]


def test_n468_d3b_a_link_record_says_a_hard_link_made_here(monkeypatch):
    got, _s, _st = _moves(monkeypatch, [(REF, P, "l.txt", LINK | CLOSE)], [_file("l.txt", links=2),
                                                                             _file("a.txt", parent=H, links=2)])
    assert got == ["a hard link made here (change journal)", False], got


def test_n468_d3b_the_most_recent_record_of_the_name_decides(monkeypatch):
    """A link made and removed (the driver writes HARD_LINK_CHANGE for both: RefsSetLinkInfo, RefsCommonCleanup),
    then a move that puts the same name there: moved. And the other way round: linked."""
    moved = [(REF, P, "x.txt", LINK | CLOSE), (REF, P, "x.txt", LINK | CLOSE), (REF, H, "x.txt", OLD),
             (REF, P, "x.txt", NEW)]
    assert _moves(monkeypatch, moved, [_file("x.txt")])[0] == ["moved (change journal)"]
    linked = [(REF, H, "x.txt", OLD), (REF, P, "x.txt", NEW), (REF, P, "x.txt", OLD), (REF, H, "x.txt", NEW),
              (REF, P, "x.txt", LINK | CLOSE)]
    assert _moves(monkeypatch, linked, [_file("x.txt", links=2)])[0] == ["a hard link made here (change journal)"]


def test_n468_d3b_a_record_of_another_name_decides_nothing(monkeypatch):
    """A link made in the directory under ANOTHER name says nothing of this name (D3's parent-only reading said
    "linked" here)."""
    got, _s, _st = _moves(monkeypatch, [(REF, P, "other.txt", LINK | CLOSE)], [_file("a.txt")])
    assert got == ["moved, or hard-linked and the original name removed"], got


def test_n468_d3b_without_a_record_the_metadata_value_stays(monkeypatch):
    got, _s, state = _moves(monkeypatch, [((H, 9), P, "zz.txt", CREATE)], [_file("a.txt"), _file("b.txt", links=2)])
    assert got == ["moved, or hard-linked and the original name removed", "undetermined"] and state == "read", got


@pytest.mark.parametrize("recs,parent,want", [
    ([((0x750, 0), 0x600, "d", CREATE)], 0x600, "in its creation directory (change journal)"),
    ([((0x750, 0), 0x600, "d", CREATE), ((0x750, 0), 0x600, "d", OLD), ((0x750, 0), 0x610, "d", NEW)], 0x610,
     "moved (change journal)"),
    ([((0x750, 0), 0x600, "d", CREATE | OLD)], 0x600, "undetermined"),       # a creation bit carried by a rename record
    ([], 0x600, "undetermined")], ids=["in", "moved", "create-bit-in-a-rename", "no-record"])
def test_n468_d3b_a_directory_is_decided_by_its_creation_record(monkeypatch, recs, parent, want):
    row = {"name": "d", "is_dir": True, "oid": 0x750, "parent_oid": parent}
    assert _moves(monkeypatch, recs, [row])[0] == [want]


@pytest.mark.parametrize("kw,words", [
    ({"gaps": ["4,096 zero byte(s) inside the written span where records were"]}, "not whole inside its written span"),
    ({"recreated": True}, "was re-created (its numbering restarted)"),
    ({"missing": [{"seq": 0}]}, "files point past the change journal's last record")],
    ids=["span-gap", "recreated", "missing-tail"])
def test_n468_d3b_a_journal_with_a_break_in_its_history_is_not_used(monkeypatch, kw, words):
    """The most recent record of a name is the one that put it there only when no record is missing in between."""
    got, said, state = _moves(monkeypatch, [(REF, H, "a.txt", OLD), (REF, P, "a.txt", NEW)], [_file("a.txt")], **kw)
    assert got == ["moved, or hard-linked and the original name removed"] and state == "unusable", got
    assert said.startswith("IsMoved: the metadata's values; ") and words in said, said


def test_n468_d3b_the_journal_reading_is_held_its_notes_are_not_the_runs(monkeypatch, capsys):
    """A note met while the journal is read for IsMoved does not become the run's (no exit 2, nothing printed): the
    sentence says the journal was not used and what its reading met (RW-6, wave D's close: it was "could not be read
    in full", which a held note does not show), and the metadata values stay."""
    before = (dict(F._SKIP_NOTES), list(F._SKIP_FINDING), list(F._FINDINGS))
    got, said, state = _moves(monkeypatch, [(REF, H, "a.txt", OLD), (REF, P, "a.txt", NEW)], [_file("a.txt")],
                              note="part of it could not be read")
    assert (dict(F._SKIP_NOTES), list(F._SKIP_FINDING), list(F._FINDINGS)) == before
    assert capsys.readouterr().err == "" and state == "unusable", said
    assert "the change journal was not used, because reading it met: locate_change_journal: the FS-metadata " \
        "directory: part of it" in said, said
    assert got == ["moved, or hard-linked and the original name removed"]


def _usn_v3(off, name, reason=0x100, ref=(0x700, 5), parent=0x600):
    """A USN_RECORD_V3 at `off` (its USN is its offset), 8-aligned."""
    nm = name.encode("utf-16-le")
    n = (0x4C + len(nm) + 7) & ~7
    r = bytearray(n)
    struct.pack_into("<IHH", r, 0, n, 3, 0)
    struct.pack_into("<QQQQ", r, 0x08, ref[1], ref[0], 0, parent)
    struct.pack_into("<QQIIII", r, 0x28, off, 0x01DB000000000000, reason, 0, 0, 0x20)
    struct.pack_into("<HH", r, 0x48, len(nm), 0x4C)
    r[0x4C:0x4C + len(nm)] = nm
    return bytes(r)


def _journal_bytes(gap):
    j = bytearray(0x40000)
    a = _usn_v3(0, "first.txt")
    j[0:len(a)] = a
    at = 0x100 + gap
    b = _usn_v3(at, "second.txt")
    j[at:at + len(b)] = b
    return bytes(j)


@pytest.mark.parametrize("gap,want", [(0x30000, True), (0x40, False)], ids=["zeroed-region", "padding"])
def test_n468_d3b_the_quiet_parse_returns_what_is_missing_inside_the_span(gap, want, capsys):
    """`parse_usn_records(report=False)` records and prints nothing, and returns in `span_gaps` the zeroed region the
    reporting parse states as a finding (a run of zeros inside the written span longer than one whole record); a gap
    of padding is no gap. The records are the same either way."""
    j = _journal_bytes(gap)
    f0, s0, v0 = list(F._FINDINGS), list(F._SKIP_FINDING), len(F._VIEW_FINDINGS)
    q = F.parse_usn_records(j, alloc=len(j), report=False)
    assert capsys.readouterr().err == "" and list(F._FINDINGS) == f0 and list(F._SKIP_FINDING) == s0
    assert [r.filename for r in q] == ["first.txt", "second.txt"], q
    assert bool(q.span_gaps) is want and (not want or "zero byte(s) inside the written span" in q.span_gaps[0]), \
        q.span_gaps
    loud = F.parse_usn_records(j, alloc=len(j))
    said = capsys.readouterr().err
    assert [r.filename for r in loud] == ["first.txt", "second.txt"] and ("zero byte(s)" in said) is want, said
    del F._FINDINGS[len(f0):]                              # this test's own finding is not the session's
    del F._VIEW_FINDINGS[v0:]


def test_n468_d3b_the_zero_run_step_ends_where_the_word_loop_ended():
    """D3b's speed-up of the parser: a run of zero words is stepped over at once; the records found, the zero runs
    and the scan's end are the word loop's (39 corpus journals, 990,528 records: fixes/D3_evidence/usn_parse_equiv)."""
    for tail in (0, 8, 0x48, 0x50, 0x58, 0x1000):
        j = _journal_bytes(0x40)[:0x200 + tail] + b"\0" * tail
        got = F.parse_usn_records(j, alloc=len(j), report=False)
        assert [r.filename for r in got] == ["first.txt", "second.txt"], (tail, got)



# ═══ N468 / decision 51 -- on the corpus ════════════════════════════════════════════════════════════════════════

MOVE = "win11refs8gtestmove_aftermove.raw"                # its transcript moves.txt is the answer key


def _files(name):
    img = R3._img(name)
    d = tempfile.mkdtemp(prefix="d3b_files_", dir=R3.BI.SCRATCH if os.path.isdir(R3.BI.SCRATCH) else None)
    try:
        c = os.path.join(d, "f.csv")
        rc, _o, err = R3._tool(img, "files", "--csv", c)
        with open(c, newline="", encoding="utf-8") as fh:
            return rc, list(csv.DictReader(fh)), err
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_n468_d3b_image_sample_values_and_the_line_that_says_how(tmp_path):
    """The public sample (its journal whole, 9,371 records): what the journal decides, measured against the workload
    logs 539 of 539 right (fixes/D3_evidence/n468_journal2.txt); the line says how IsMoved was read."""
    rc, rows, err = _files(R3.SAMPLE)
    got = {}
    for r in rows:
        got[r["IsMoved"]] = got.get(r["IsMoved"], 0) + 1
    # acceptance 1.14.0: IsMoved's not-moved value `false` (K19's spelling)
    assert rc == 0 and got == {"false": 1090, "undetermined": 40, "in its creation directory (change journal)": 147,
                               "moved (change journal)": 149, "a hard link made here (change journal)": 269,
                               "moved, or hard-linked and the original name removed": 49}, got
    # acceptance 1.14.0 (K28, R7): a count is decimal with no separators
    assert "IsMoved: read from the change journal (9371 records) where it says how a name came where it is -- a " \
           "directory in its creation directory 147, a directory outside its creation directory 52, a hard link " \
           "made here 269, moved 97; the metadata's values elsewhere" in err, err[-2000:]


@pytest.mark.parametrize("path,want", [
    ("testmove2/move.txt", "moved (change journal)"), ("testmove2/haha2_10011.txt", "moved (change journal)"),
    ("testmove2/haha_100_copied.txt", "moved (change journal)"),
    ("testmove2/hardlinktohl.txt", "a hard link made here (change journal)"), ("testmove1/hl.txt", "false"),
    ("testdeletion2/haha2_10021.txt", "false"),                       # moved out and back: in its creation directory
    ("testmove1/movedsamedir.txt", "false"), ("testmove2/copied.txt", "false"),
    ("testmove1", "in its creation directory (change journal)"), ("testdeletion2", "in its creation directory "
                                                                                   "(change journal)"),
    ("testdeletion", "undetermined")])
def test_n468_d3b_image_the_move_volume_against_its_transcript(path, want):
    """win11refs8gtestmove_aftermove, the operations of moves.txt: four moves into testmove2, a hard link made there,
    a move out and back, renames in place, copies; testdeletion predates the session (its `mkdir` failed: "already
    exists") and the journal holds no creation record of it."""
    rows = getattr(test_n468_d3b_image_the_move_volume_against_its_transcript, "_rows", None)
    if rows is None:
        rc, rows, err = _files(MOVE)
        assert rc == 0, err[-2000:]
        test_n468_d3b_image_the_move_volume_against_its_transcript._rows = rows
    row = next((r for r in rows if r["FullPath"].lstrip("/") == path), None)
    assert row is not None and row["IsMoved"] == want, row


def test_n468_d3b_image_details_says_the_journals_value():
    rc, out, err = R3._tool(R3._img(MOVE), "details", "/testmove2/move.txt")
    assert rc == 0, err[-2000:]
    assert "  Is moved:           moved (change journal)" in out, out
    assert re.search(r"Home directory: +0x761 +created here; this name is under parent 0x762: moved \(change "
                     r"journal\)", out), out


def test_n468_d3b_image_a_recreated_journal_is_not_used_and_said():
    """labJjournal's journal was re-created (files carry an earlier journal's id): every row keeps the metadata's
    value, the line says why on stderr, and the exit code is the listing's own."""
    rc, rows, err = _files("labJjournal.raw")
    assert rc == 0 and not any("(change journal)" in r["IsMoved"] for r in rows), err[-2000:]
    assert "IsMoved: the metadata's values; the change journal was re-created (files carry an earlier journal's " \
           "id), so the changes made between its instances are not recorded" in err, err[-2000:]


def test_n468_d3b_image_a_volume_without_a_journal_keeps_the_metadata_values():
    rc, rows, err = _files(R3.BASE)
    assert rc == 0 and not any("(change journal)" in r["IsMoved"] for r in rows), err[-2000:]
    assert "IsMoved: the metadata's values; no change journal was found" in err, err[-2000:]


# ═══ C3-1 -- on the corpus ══════════════════════════════════════════════════════════════════════════════════════
# The two 15 TB copies are scanned up to just past their last earlier-volume page (D3_evidence/c3_census3_summary.txt:
# clusters 66,528 and 1,375,748): the whole volume is 15 TB of holes, read as zeros.

def test_c31_d3b_image_15t64k_holds_an_earlier_4k_volumes_pages():
    """win11refs15t64k (64 KiB clusters): 634 pages of an earlier volume of 4 KiB clusters at their own address, 450
    of them 16, 32 or 48 KiB into a 64 KiB cluster -- the D3 reading counted none. Rows of that volume's directories
    (a workload of 2026-05-16) are listed."""
    rc, out, err = R3._tool(R3._img("win11refs15t64k.raw"), "deleted", "--earlier-volumes", "--max-scan", "66600")
    assert rc == 0, err[-2000:]
    assert "1 earlier ReFS volume wrote pages here: the area was formatted again at least 1 time." in out, out[:3000]
    assert "Earlier volume 0x0e212eb2: 634 page(s) at their own address, 549 entries" in out, out[:3000]
    # acceptance 1.14.0: K5 (the time), R4 (a volume signature is a fixed-width word, 0x%08x)
    assert re.search(r"^    elvis_dir_beta_984608/  created 2026-05-16T14:11:28\.\d{7}Z .*@ cluster 0xa0 off 0xc630 ", out,
                     re.M), out[:3000]


def test_c31_d3b_image_15t64k_the_orphan_scan_says_where_the_first_page_begins():
    rc, out, err = R3._tool(R3._img("win11refs15t64k.raw"), "deleted", "--full", "--max-scan", "66600")
    said = [l for l in (out + err).splitlines() if "Orphan-page scan:" in l and "signature" in l]
    assert rc == 0 and len(said) == 1, said
    assert said[0].startswith("  Orphan-page scan: 1 earlier ReFS volume wrote pages here: the area was formatted again "
                              "at least 1 time (634 metadata page(s)"), said
    assert "(the first at cluster 0xa0 + 0x4000 bytes)" in said[0], said


def test_c31_d3b_image_15t_counts_the_tables_that_name_their_physical_address():
    """win11refs15t: 2,115 pages of an earlier volume -- its Container Table, copy and Small Allocator (1,984, named
    by physical address) and allocator pages; no directory page, so no entry. The D3 reading counted 131."""
    rc, out, err = R3._tool(R3._img("win11refs15t.raw"), "deleted", "--earlier-volumes", "--max-scan", "1376000")
    assert rc == 0, err[-2000:]
    assert "Earlier volume 0xf3c54602: 2115 page(s) at their own address, 0 entries" in out, out[:3000]


def test_c31_d3b_image_control_the_dedup_index_is_still_no_earlier_volume():
    rc, out, err = R3._tool(R3._img("win11refs8gdedup.raw"), "deleted", "--earlier-volumes")
    assert rc == 0, err[-2000:]
    assert "792 cluster(s) begin with the page signature and carry a signature that is not this volume's " \
           "(0x409da352 on 24, 0xb32a0746 on 768;" in out, out[:3000]
    assert "No page of an earlier ReFS volume was found at its own address" in out, out[:3000]


def test_n468_d3b_a_walk_bounded_by_depth_reads_the_pointers_itself(monkeypatch):
    """`files --depth N` walks part of the tree: the files' journal pointers (the witness of a lost journal tail) are
    then not taken from its rows but read by `_usn_journal_state` itself (pointers=False)."""
    seen = []
    _journal(monkeypatch, [(REF, H, "a.txt", OLD), (REF, P, "a.txt", NEW)])
    monkeypatch.setattr(F, "_usn_journal_state", lambda *a, **k: seen.append(k["pointers"]) or
                        {"recreated": False, "restart": False, "missing": []})
    F._journal_moves(None, 0, 4096, None, {}, [_file("a.txt")], all_rows=False)
    F._journal_moves(None, 0, 4096, None, {}, [_file("a.txt")])
    assert seen[0] is False and isinstance(seen[1], list), seen


def test_n468_d3b_an_unexpected_failure_of_the_reading_is_said_not_raised(monkeypatch):
    _journal(monkeypatch, [])
    monkeypatch.setattr(F, "parse_usn_records", lambda *a, **k: (_ for _ in ()).throw(TypeError("a test fault")))
    rows = [_file("a.txt")]
    said, state = F._journal_moves(None, 0, 4096, None, {}, rows)
    assert state == "unusable" and "could not be read (TypeError: a test fault)" in said, said
    assert F._is_moved(rows[0]) == "moved, or hard-linked and the original name removed"
