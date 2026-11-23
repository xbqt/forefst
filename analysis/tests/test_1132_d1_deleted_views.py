"""Wave D step D1 (1.14.0): the deleted views after B8, WC-1 and the maintainer's decision 49.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` decision 49 (points 1-5) and decision 48 (an output says what is
read, derived or recovered, and never prints an inference as a fact); `fixes/WAVED_PLAN.md` D1; `fixes/D1_NOTES.md`.
The RED nodes of the items (B8, N129, N145, N146; C5, C7 for `deleted`) are in `test_1132_red_b2_deleted.py` and
`test_1132_red_b2_wording.py`; these nodes cover what those do not.

What each group asserts
-----------------------
status   a remnant is DELETED only when the identity it records (a directory row's own OID, a split row's home +
         ordinal, an embedded row's FileRef from the journal) is live nowhere; RENAMED / SAME FILE, OTHER CREATION
         TIME when that identity is live; DELETED, OR RENAMED when the row records none the tool can check -- an
         embedded row found in ANOTHER directory's page (N467) whose page owner + ordinal happen to name a live file
         with another creation time is not called renamed; a row whose two timestamps are implausible gives no
         identity from its own fields.
words    "Found in a page of <folder> (... where it was found, not necessarily where it was deleted from)" in place of
         "Deleted from"; the STILL PRESENT note in the same words; "copy of the current entry (same dates)" /
         "earlier version (dates differ)"; "two plausible timestamps"; "directory entry"; "empty" for 0 B (N270/N471).
copies   one entry per (name, creation time, kind) says how many copies it stands for and whether they differ; the
         recovery log lists every copy; the shown copy is the longest (win11refs2g).
rows     C45: an index node's separator rows are set aside and counted, its free space's leaf rows are read; N273:
         --no-system drops the system churn from --csv and the recovery log too; N274: the roll-up names the sections
         it adds up and the partial STILL PRESENT rows it counts are listed.
diff     N146: the checkpoint differential reports a rename by its ObjectRef.
images   the measured rename on win11refs8gtestmove_aftermove is read from the change journal; on the public sample no
         status contradicts the sample's own workload log (the answer key, `provenance/fsactivity/*_log.csv`).

Volumes: the synthetic builder of `test_1132_red_b2_deleted.py` (imported); corpus images READ-ONLY, skipped when
absent.
"""
import csv
import glob
import os
import re
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_b2_deleted as D                     # noqa: E402  (DirVol, rows, the runners, the readers)

_T, _S, CS = D._T, D._S, D.CS
_row, _name_key, _file_value, _dir_value, _resident_value = D._row, D._name_key, D._file_value, D._dir_value, \
    D._resident_value
_syn, _syn_csv, _report, _mentions, _section, _ctx = D._syn, D._syn_csv, D._report, D._mentions, D._section, D._ctx
_fx, _keep = D._fx, D._keep
SLACK, CHKP = D.SLACK, D.CHKP


def _vol(tmp_path, dirs, orphans=()):
    v = D.DirVol()
    v.objects = v.tree(dirs)
    for oid, rows in orphans:
        v.orphan(oid, rows)
    return v.write(str(tmp_path / "target.raw"))


def _entry(out, name):
    ms = _mentions(_report(out), name)
    _fx(ms, "%s is not listed at all" % name + _ctx(0, out))
    return ms


# acceptance 1.14.0 (K22): every path in `files`' FullPath form -- no leading '/'
# ═══ status ══════════════════════════════════════════════════════════════════════════════════════════════════

def test_d1_directory_row_whose_oid_is_live_under_another_name_is_renamed(tmp_path):
    """A slack directory row 'olddir' carrying OID 0x762, which is live as /newdir: RENAMED, now /newdir, ObjectRef
    0x762:0x0 read from the row -- in the text and in the CSV's Status/LiveFile/ObjectRef."""
    path = _vol(tmp_path, {0x600: {"name": "", "slack": [_row(_name_key("olddir"), _dir_value(0x762, _T + 9 * _S))]},
                           0x762: {"parent": 0x600, "name": "newdir"}})
    rc, out, err, rows = _syn_csv(path, "deleted", "-v")
    blk = " ".join(m[0] + "\n" + m[2] for m in _entry(out, "olddir"))
    assert rc == 0 and "RENAMED" in blk and "Now: newdir" in blk and "0x762:0x0" in blk, blk
    r = [x for x in rows if x["FileName"] == "olddir"]
    assert r and r[0]["Status"] == "renamed" and r[0]["LiveFile"] == "newdir" and r[0]["ObjectRef"] == "0x762:0x0" \
        and r[0]["IdentitySource"] == "row", r


def test_d1_directory_row_whose_oid_is_live_nowhere_is_deleted(tmp_path):
    """Control: a directory row whose OID (0x750, below the highest live OID) no live directory has is DELETED, with
    its identity line -- OIDs are never re-used (E66)."""
    path = _vol(tmp_path, {0x600: {"name": "", "slack": [_row(_name_key("gonedir"), _dir_value(0x750, _T + 9 * _S))]},
                           0x762: {"parent": 0x600, "name": "keep"}})
    rc, out, err, rows = _syn_csv(path, "deleted", "-v")
    ms = _entry(out, "gonedir")
    assert all(m[0].startswith("DELETED --") for m in ms), ms
    assert "Identity: ObjectRef 0x750:0x0, read from the row, live nowhere" in ms[0][2], ms[0][2]
    assert [x["Status"] for x in rows if x["FileName"] == "gonedir"] == ["deleted"], rows


def test_d1_split_row_of_a_live_file_with_another_creation_time(tmp_path):
    """A slack copy of a live file's split row (same FileRef 0x761:0x5, same name) with another creation time: SAME FILE,
    OTHER CREATION TIME, the live file's creation time printed -- not DELETED (a timestomped file's earlier row)."""
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("a.txt"), _file_value(5, 0x761, _T))],
                                   "slack": [_row(_name_key("a.txt"), _file_value(5, 0x761, _T + 400 * _S))]}})
    rc, out, err, rows = _syn_csv(path, "deleted", "-v")
    ms = _entry(out, "a.txt")
    assert ms[0][0].startswith("SAME FILE, OTHER CREATION TIME") and not any(m[0].startswith("DELETED") for m in ms), ms
    assert "Now: d/a.txt" in ms[0][2] and "The live file's creation time:" in ms[0][2], ms[0][2]
    assert [x["Status"] for x in rows if x["FileName"] == "a.txt"] == ["same file, other creation time"], rows


def test_d1_embedded_row_in_another_directorys_page_is_not_a_false_rename(tmp_path):
    """N467's shape: B's page holds, in its free space, an embedded row (zzz.txt, ordinal 6) written by another
    directory. B's own live file other.txt has ordinal 6 too, with another creation time. The page owner + ordinal
    candidate (0x762:0x6) is NOT taken: it names B's file only if the creation times agree, so the row is DELETED, OR
    RENAMED -- never 'renamed: now /B/other.txt'."""
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x762: {"parent": 0x600, "name": "B",
                                   "files": [_row(_name_key("other.txt"),
                                                  _resident_value(_T + 50 * _S, 6, 0x762, "other12.txtx"))],
                                   "slack": [_row(_name_key("zzz.txt"),
                                                  _resident_value(_T + 7 * _S, 6, 0x762, "zzzzz12.txtx"))]}})
    rc, out, err, rows = _syn_csv(path, "deleted", "-v")
    ms = _entry(out, "zzz.txt")
    assert all(m[0].startswith("DELETED, OR RENAMED") for m in ms), ms
    assert not any("other.txt" in m[2] for m in ms), ms
    assert [x["Status"] for x in rows if x["FileName"] == "zzz.txt"] == ["deleted, or renamed"], rows


def test_d1_control_embedded_row_with_the_same_creation_time_is_renamed(tmp_path):
    """Control for the node above: the same embedded row with B's file's own creation time is that file's earlier name
    (a same-directory rename keeps the record embedded): RENAMED, now /B/other.txt, from the page owner + ordinal."""
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x762: {"parent": 0x600, "name": "B",
                                   "files": [_row(_name_key("other.txt"),
                                                  _resident_value(_T + 50 * _S, 6, 0x762, "other12.txtx"))],
                                   "slack": [_row(_name_key("zzz.txt"),
                                                  _resident_value(_T + 50 * _S, 6, 0x762, "zzzzz12.txtx"))]}})
    rc, out, err, rows = _syn_csv(path, "deleted", "-v")
    ms = _entry(out, "zzz.txt")
    assert ms[0][0].startswith("RENAMED") and "Now: B/other.txt" in ms[0][2], ms
    assert "page owner + ordinal, same creation time" in ms[0][2], ms[0][2]
    r = [x for x in rows if x["FileName"] == "zzz.txt"]
    assert r and r[0]["Status"] == "renamed" and r[0]["IdentitySource"] == "page", r


def test_d1_row_with_both_timestamps_implausible_gives_no_identity(tmp_path):
    """A split row whose two times are outside 2009-2050 carries 0x761:0x4, live as /d/keep.txt: its fields may be
    overwritten, so the row decides nothing -- DELETED, OR RENAMED (never RENAMED or DELETED from those fields)."""
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("keep.txt"), _file_value(4, 0x761, _T))],
                                   "slack": [_row(_name_key("old2005.txt"),
                                                  _file_value(4, 0x761, D._ft(2005, 6, 1), D._ft(2005, 6, 2)))]}})
    rc, out, err, rows = _syn_csv(path, "deleted", "-v")
    ms = _entry(out, "old2005.txt")
    assert all(m[0].startswith("DELETED, OR RENAMED") for m in ms), ms
    r = [x for x in rows if x["FileName"] == "old2005.txt"]
    assert r and r[0]["Status"] == "deleted, or renamed" and r[0]["ObjectRef"] == "" \
        and r[0]["PlausibleTimes"] == "neither", r


# ═══ words ═══════════════════════════════════════════════════════════════════════════════════════════════════

def _b8_like(tmp_path):
    return _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "testmove1",
                                   "files": [_row(_name_key("live.txt"), _file_value(2, 0x761, _T))],
                                   "slack": [_row(_name_key("gone.txt"), _file_value(9, 0x761, _T + 3 * _S)),
                                             _row(_name_key("live.txt"), _file_value(2, 0x761, _T)),
                                             _row(_name_key("live2.txt"), _file_value(3, 0x762, _T + 2 * _S))]},
                           0x762: {"parent": 0x600, "name": "other",
                                   "files": [_row(_name_key("live2.txt"), _file_value(3, 0x762, _T + 2 * _S))]}})


def test_d1_location_says_found_in_a_page_not_deleted_from(tmp_path):
    """Decision 49 point 2: the location is where the row was FOUND, worded so; the text and the recovery log never
    say 'Deleted from' / 'deleted from'."""
    path = _b8_like(tmp_path)
    logp = str(tmp_path / "log.txt")
    rc, out, err = _syn(path, "deleted", "-v", "--log", logp)
    blk = _entry(out, "gone.txt")[0][2]
    assert ("Found in a page of: testmove1  (table 0x761; where it was found, not necessarily where it was deleted "
            "from)") in blk, blk
    log = open(logp, encoding="utf-8").read()
    assert "found in a page of testmove1" in log                          # K22 (1.14.0)
    assert not re.search(r"[Dd]eleted from:|\| deleted from |remnant in ", out + log), out + log


def test_d1_still_present_note_and_dates_words(tmp_path):
    """Decision 49 points 2-3: a STILL PRESENT row in a page of another directory says so in P2's words; a copy whose
    four times equal the live row's is 'copy of the current entry (same dates)'."""
    path = _b8_like(tmp_path)
    rc, out, err = _syn(path, "deleted", "-v")
    sp = _section(out, SLACK).split("STILL PRESENT", 1)[1]
    l2 = next(l for l in sp.splitlines() if l.strip().startswith("live2.txt"))
    l1 = next(l for l in sp.splitlines() if l.strip().startswith("live.txt"))
    assert "[found in a page of a directory the live file is not in]" in l2, l2
    assert "copy of the current entry (same dates)" in l1 and "found in a page of" not in l1, l1
    assert "former location" not in out and "CoW remnants" not in out, out


def test_d1_still_present_earlier_version_and_its_copies(tmp_path):
    """Decision 49 points 3-4: a slack row of a live identity whose modification time differs is an 'earlier version
    (dates differ)'; with a second copy that carries the current dates, the line counts both kinds of copy."""
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("b.txt"), _file_value(2, 0x761, _T, _T + 60 * _S)),
                                             _row(_name_key("c.txt"), _file_value(3, 0x761, _T, _T + 60 * _S))],
                                   "slack": [_row(_name_key("b.txt"), _file_value(2, 0x761, _T, _T + 9 * _S)),
                                             _row(_name_key("c.txt"), _file_value(3, 0x761, _T, _T + 9 * _S)),
                                             _row(_name_key("c.txt"), _file_value(3, 0x761, _T, _T + 60 * _S))]}})
    rc, out, err = _syn(path, "deleted", "-v")
    sp = _section(out, SLACK).split("STILL PRESENT", 1)[1]
    lb = next(l for l in sp.splitlines() if l.strip().startswith("b.txt"))
    lc = next(l for l in sp.splitlines() if l.strip().startswith("c.txt"))
    # Q-B (the labs-and-driver batch, 1.14.0): the times that differ are named (the planted row's Modified, and
    # Changed / Accessed, which `_file_value` writes equal to it)
    assert "earlier version (dates differ: Modified, Changed, Accessed)" in lb, lb
    assert "[2 copies, dates differ: 1 with the current dates, 1 earlier version(s)]" in lc, lc


def test_d1_grade_words_say_plausible_not_valid(tmp_path):
    """Decision 49 point 5 (P6): the grade is 'two plausible timestamps' and the NOTE says what it tests; 'valid
    timestamps', 'high confidence' and 'decode a full $SI' are gone."""
    rc, out, err = _syn(_b8_like(tmp_path), "deleted", "-v")
    assert "with two plausible timestamps" in out and "between 2009-11 and 2050-12" in out, out
    assert not re.search(r"valid timestamps|high confidence|full \$SI", out), out


def test_d1_directory_row_is_a_directory_entry(tmp_path):
    """N471: a directory row's header says 'directory' and its verdict 'directory entry (a directory holds no file
    data)' -- no data-residency word."""
    path = _vol(tmp_path, {0x600: {"name": "", "slack": [_row(_name_key("gonedir"), _dir_value(0x750, _T + 9 * _S))]},
                           0x762: {"parent": 0x600, "name": "keep"}})
    rc, out, err = _syn(path, "deleted", "-v")
    blk = _entry(out, "gonedir")[0][2]
    assert "(directory, slack of a live page @ cluster" in blk, blk
    assert "Recoverable: directory entry (a directory holds no file data)" in blk, blk
    assert "resident" not in blk, blk


@pytest.mark.parametrize("label", ["empty", "empty_symlink"])
def test_d1_empty_verdict_is_not_inline_content(label):
    """N270: a 0-byte inline row is 'empty', Reliability NONE -- not 'content inline', not EXACT, not counted as a file
    that decodes (unit level: the verdict and its reliability)."""
    e = {"name": "x", "vd": b"\0" * 0x100, "resident": True, "file_attrs": 0x400 if label == "empty_symlink" else 0x20}
    real = F.get_resident_data_content
    F.get_resident_data_content = lambda vd, salvage=False: b""
    try:
        enum, text, dec = F._deleted_recoverability(e)
    finally:
        F.get_resident_data_content = real
    assert enum == label and dec is None and F._RELIABILITY[enum] == "NONE", (enum, text)
    assert text.startswith("empty: the row declares 0 B inline") and "FULL FILE" not in text, text
    assert ("symbolic link" in text) == (label == "empty_symlink"), text


# ═══ copies ══════════════════════════════════════════════════════════════════════════════════════════════════

def test_d1_copies_are_counted_and_every_copy_is_in_the_log(tmp_path):
    """Decision 49 point 4: one entry for a row found twice (in a live page's slack, and listed on an old page of the
    same directory), 'Copies: 2 copies found (identical)'; CSV Copies 2 / CopiesDiffer 'no'; the recovery log lists
    both copies with their cluster, the shown one marked."""
    gone = _row(_name_key("twice.txt"), _file_value(9, 0x761, _T + 3 * _S))
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("live.txt"), _file_value(2, 0x761, _T))], "slack": [gone]}},
                orphans=[(0x761, [gone])])
    logp = str(tmp_path / "log.txt")
    rc, out, err, rows = _syn_csv(path, "deleted", "-v", "--full", "--log", logp)
    blk = _entry(out, "twice.txt")[0][2]
    assert "Copies: 2 copies found (identical); shown: the longest copy (the most bytes)" in blk, blk
    r = [x for x in rows if x["FileName"] == "twice.txt"]
    assert r and r[0]["Copies"] == "2" and r[0]["CopiesDiffer"] == "no", r
    log = open(logp, encoding="utf-8").read()
    copies = [l for l in log.split("twice.txt", 1)[1].splitlines()[1:5] if "@cluster 0x" in l]
    assert len(copies) == 2 and sum(l.strip().startswith("* ") for l in copies) == 1, log
    assert {"slack of a live page", "listed on an old page"} <= {t for l in copies for t in
                                                                 ("slack of a live page", "listed on an old page")
                                                                 if t in l}, copies


def test_d1_image_win11refs2g_the_shown_copy_is_the_longest(tmp_path):
    """The wave golden's case (GOLDEN_C section 3, told to wave D): xbpt_backup_report_125235.md has a 1,336-byte copy
    on an old page beside 616-byte ones; the entry shows the longest and the log marks it."""
    img = D._image_or_skip("win11refs2g.raw")
    logp = str(tmp_path / "log.txt")
    rc, out, err = D._run(img, "deleted", "--full", "--search", "xbpt_backup_report_125235", "--log", logp,
                          cwd=str(tmp_path))
    log = open(logp, encoding="utf-8").read()
    shown = [l for l in log.splitlines() if l.strip().startswith("* ")]
    others = [l for l in log.splitlines() if re.match(r"\s{12}\S.* \| \d+ B \|", l)]
    assert rc == 0 and len(shown) == 1 and "| 1336 B |" in shown[0], shown
    assert others and all(int(re.search(r"\| (\d+) B \|", l).group(1)) <= 1336 for l in others), others


# ═══ rows the scan sets aside or must read ════════════════════════════════════════════════════════════════════

def _inner_page(lcn, oid, listed, slack):
    p = bytearray(D._page(lcn, oid, listed, slack))
    struct.pack_into("<I", p, 0x60 + 12, 0x100)                # index header word 3: an index (inner) node
    return bytes(p)


def test_d1_index_node_separator_rows_are_set_aside_and_counted(tmp_path):
    """C45: an old index node's listed rows and a slack row of the same value length (48 bytes: a child-page reference)
    are separator rows -- not listed, counted on the scan's line. A whole leaf row in the same index node's free space
    (the leaf the node was before a split) is read."""
    ref = struct.pack("<4Q", 0x40, 0x41, 0x42, 0x43) + b"\0" * 16
    sep = [_row(_name_key("xbpt_t"), ref), _row(_name_key("xbpt_u"), ref)]
    leaf = _row(_name_key("leafrow.txt"), _file_value(9, 0x761, _T + 3 * _S))
    v = D.DirVol()
    v.objects = v.tree({0x600: {"name": ""}, 0x761: {"parent": 0x600, "name": "d",
                                                     "files": [_row(_name_key("k.txt"), _file_value(2, 0x761, _T))]}})
    lcn = v.alloc()
    v.orphans[lcn] = _inner_page(lcn, 0x761, sep[:1], [sep[1], leaf])
    path = v.write(str(tmp_path / "target.raw"))
    rc, out, err = _syn(path, "deleted", "--full")
    sec = _section(out, SLACK)
    assert "xbpt_t" not in sec and "xbpt_u" not in sec, sec
    assert re.search(r"set aside by structure: 2 index-node separator row\(s\)", sec), sec
    assert _mentions(sec, "leafrow.txt"), sec


def test_d1_no_system_drops_the_churn_from_csv_and_log(tmp_path):
    """N273: `--no-system` leaves the FVE2 row out of --csv and the recovery log as well (control: without it, both
    carry it)."""
    fve = "FVE2.{01234567-89ab-cdef-0123-456789abcdef}"
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("k.txt"), _file_value(2, 0x761, _T))],
                                   "slack": [_row(_name_key(fve), _file_value(7, 0x761, _T + 5 * _S)),
                                             _row(_name_key("user.txt"), _file_value(8, 0x761, _T + 6 * _S))]}})
    for flag, want in ((["--no-system"], False), ([], True)):
        logp = str(tmp_path / ("log%d.txt" % len(flag)))
        rc, out, err, rows = _syn_csv(path, "deleted", "--log", logp, *flag)
        names = {r["FileName"] for r in rows}
        log = open(logp, encoding="utf-8").read()
        assert "user.txt" in names and (fve in names) == want and (fve in log) == want, (flag, names)


def test_d1_rollup_names_its_sections_and_lists_partial_still_present_rows(tmp_path):
    """N274 (group 2, PLAN 10.2 E: the roll-up is the table now): each status's table total is its section's count, and
    a partial STILL PRESENT row (a live file whose two times are 2005's) is listed where it is counted."""
    old = (D._ft(2005, 6, 1), D._ft(2005, 6, 2))
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("q2005.docx"), _file_value(2, 0x761, *old))],
                                   "slack": [_row(_name_key("q2005.docx"), _file_value(2, 0x761, *old)),
                                             _row(_name_key("gone.txt"), _file_value(9, 0x761, _T + 3 * _S)),
                                             _row(_name_key("x.txt"), _file_value(0, 0, _T + 4 * _S))]}})
    rc, out, err = _syn(path, "deleted")
    heads = {m.group(1): int(m.group(2)) for m in
             re.finditer(r"^  ── (DELETED, OR RENAMED|DELETED|RENAMED|SAME FILE, OTHER CREATION TIME|STILL PRESENT): "
                         r"(\d+) \(", out, re.M)}
    tab = {m.group(1): int(m.group(2).split()[-1]) for m in re.finditer(r"^    (DELETED, OR RENAMED|DELETED|RENAMED|SAME FILE, OTHER CREATION TIME|STILL PRESENT)[^\d\n]*?((?:\s+\d+\*?){6})\s*$", out, re.M)}
    assert len(tab) == 5 and all(tab[k] == heads.get(k, 0) for k in tab) and sum(heads.values()) == 3, \
        (tab, heads, out[-3000:])
    sp = _section(out, SLACK).split("── STILL PRESENT", 1)[1]
    assert heads.get("STILL PRESENT") == 1 and re.search(r"^      \S.*\sq2005\.docx\s+d$", sp, re.M), sp


# ═══ the checkpoint differential ═════════════════════════════════════════════════════════════════════════════

def test_d1_checkpoint_differential_reports_a_rename_by_objectref(tmp_path):
    """N146: between the two checkpoints A/old.txt (0x761:0x2) became A/new.txt: one 'renamed, moved ...' line with
    both paths and the ObjectRef, not a removal plus an addition."""
    v = D.DirVol()
    dirs = {0x600: {"name": ""}, 0x761: {"parent": 0x600, "name": "A",
                                         "files": [_row(_name_key("old.txt"), _file_value(2, 0x761, _T))]}}
    v.old_objects = v.tree(dirs)
    v.objects = dict(v.old_objects)
    lcn = v.alloc()
    v.objects[0x761] = (lcn, D._page(lcn, 0x761, [_row(_name_key("new.txt"), _file_value(2, 0x761, _T))]))
    path = v.write(str(tmp_path / "target.raw"))
    rc, out, err = _syn(path, "deleted")
    sec = _section(out, CHKP)
    assert "~ A/old.txt -> A/new.txt  (ObjectRef 0x761:0x2)" in sec, sec
    assert "- /A/old.txt" not in sec and "+ /A/new.txt" not in sec, sec


# ═══ images ══════════════════════════════════════════════════════════════════════════════════════════════════

def test_d1_image_aftermove_rename_is_read_from_the_change_journal():
    """win11refs8gtestmove_aftermove: movesamedir.txt is an embedded row; its LastUsn's journal record names it with
    the FileRef 0x761:0x4, live as /testmove1/movedsamedir.txt."""
    rc, out, err, rows = D._image_deleted("win11refs8gtestmove_aftermove.raw")
    ms = _mentions(_report(out), "movesamedir.txt")
    assert any(m[0].startswith("RENAMED") and "Now: testmove1/movedsamedir.txt  (ObjectRef 0x761:0x4, read from the "
               "change journal)" in m[2] for m in ms), ms
    assert [r["Status"] for r in rows if r["FileName"] == "movesamedir.txt"] == ["renamed"], rows


_LOGS = os.path.join(REPO, "analysis", "samples", "disks", "win11refstestmftecmd", "provenance", "fsactivity")


def _log_namespace():
    """The sample's workload log replayed as a namespace: {basename: [entity]}, an entity = its creation time
    (FILETIME), the stamps the log set, its paths at the end, deleted or not, ever hard-linked."""
    import datetime
    rows = []
    for p in sorted(glob.glob(os.path.join(_LOGS, "*_log.csv"))):
        rows += [r for r in csv.DictReader(open(p, encoding="utf-8-sig")) if r["Result"] == "OK"]
    if not rows:
        pytest.skip("the sample's workload logs are not in this tree")
    rows.sort(key=lambda r: r["TimestampUTC"])

    def ft(t):
        d, frac = t.rstrip("Z").split(".")
        dt = datetime.datetime.strptime(d, "%Y-%m-%dT%H:%M:%S")
        return int((dt - datetime.datetime(1601, 1, 1)).total_seconds()) * 10 ** 7 + int(frac.ljust(7, "0")[:7])
    norm = lambda p: p.replace("\\", "/").lower()                                       # noqa: E731
    bn = lambda p: p.replace("\\", "/").rstrip("/").split("/")[-1]                      # noqa: E731
    by, ents = {}, []

    def new(path, t):
        e = {"created": ft(t), "names": {bn(path)}, "paths": {norm(path)}, "deleted": False, "stamps": []}
        ents.append(e)
        by[norm(path)] = e
    for r in rows:
        a, s, d, t = r["Action"], r["SourcePath"], r["DestPath"], r["TimestampUTC"]
        if a in ("CREATE_FILE", "CREATE_MARKED_FILE", "CREATE_DIR"):
            new(s, t)
        elif a in ("COPY_FILE", "CREATE_SYMLINK_FILE"):
            new(d, t)
        elif a == "CREATE_HARDLINK" and norm(s) in by:
            e = by[norm(s)]
            e["paths"].add(norm(d)); e["names"].add(bn(d)); by[norm(d)] = e
        elif a.startswith(("RENAME_", "MOVE_")) and norm(s) in by:
            e = by.pop(norm(s))
            e["paths"].discard(norm(s)); e["paths"].add(norm(d)); e["names"].add(bn(d)); by[norm(d)] = e
            if a.endswith("_DIR"):
                for k in [k for k in by if k.startswith(norm(s) + "/")]:
                    c = by.pop(k); c["paths"].discard(k); nk = norm(d) + k[len(norm(s)):]; c["paths"].add(nk)
                    by[nk] = c
        elif a.startswith("DELETE_") and norm(s) in by:
            e = by.pop(norm(s))
            e["paths"].discard(norm(s))
            e["deleted"] = not e["paths"]
        elif a == "SET_TIMESTAMPS" and norm(s) in by:
            by[norm(s)]["stamps"].append(ft(r["Details"].split(";")[-1]))
    out = {}
    for e in ents:
        for n in e["names"]:
            out.setdefault(n, []).append(e)
    return out


def test_d1_image_mftecmd_statuses_never_contradict_the_workload_log():
    """The answer key: on the public sample every DELETED entry whose file the log identifies (its name, and its
    creation time within 2 s of the log's creation or equal to a stamp the log set) is a file the log deleted, and
    every RENAMED / SAME FILE entry is a file the log leaves live. Measured at D1: 0 contradictions over 367 entries
    (66 deleted, 70 deleted or renamed, 204 renamed, 27 same file, other creation time)."""
    ns = _log_namespace()
    img = D._image_or_skip("win11refstestmftecmd.raw")
    rc, out, err, rows = D._image_deleted("win11refstestmftecmd.raw", "--full")
    _fx(rc == 0 and rows, "deleted --full gave no rows" + _ctx(rc, out, err))
    bad, decided = [], 0
    for r in rows:
        ct = r["Created"]
        if not ct or r["Status"] not in ("deleted", "renamed", "same file, other creation time"):
            continue
        import datetime
        dt = datetime.datetime.strptime(ct[:19], "%Y-%m-%dT%H:%M:%S")       # K5 (acceptance 1.14.0): ft_iso's form
        ft = int((dt - datetime.datetime(1601, 1, 1)).total_seconds()) * 10 ** 7
        fit = [e for e in ns.get(r["FileName"], []) if abs(e["created"] - ft) < 3 * 10 ** 7
               or any(abs(s - ft) < 10 ** 7 for s in e["stamps"])]
        if len(fit) != 1:
            continue
        decided += 1
        if (r["Status"] == "deleted") != fit[0]["deleted"]:
            bad.append((r["FileName"], r["Status"], sorted(fit[0]["paths"])[:2]))
    _fx(decided >= 150, "the log identifies only %d entries: not the sample this test was measured on" % decided)
    assert not bad, "%d status(es) contradict the workload log, e.g. %r" % (len(bad), bad[:6])
