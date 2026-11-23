"""E-6 (1.14.0): `files --cow-before OLD` is the comparison of two images of one volume -- one row per object that
differs, by ObjectRef (created / removed / changed, with the fields), the same volume checked, created / removed only
over complete walks, CSV = JSON. Expectations come from the GROUND TRUTH of each pair, never from the tool's output:

  E-6.1  win11refs8gtestmove_beforemove -> _aftermove against the session transcript (`moves.txt` beside the
        workspace: the commands after the disk was taken offline at its line 61823): the 1,111 files of
        `rm haha_9*` removed; the copies (testmove1/copied.txt, testmove2/copied.txt, testmove2/haha_100_copied.txt),
        hoho.txt, the 92 haha3_* files and the log directory with its three files created; the moves and same-directory
        renames changed in FullPath only by their path, each one object (its ObjectRef is the change journal's file
        reference of the move); hl.txt changed by its second name (HardLinkCount 1 -> 2); haha2_10021 (moved out and
        back) not changed in FullPath.
  E-6.2  the before image is the state at that offline: hahacp.txt and hahalast.txt present, haha_7000.txt absent,
        move.txt still in testmove1 (else E-6.1's reading of the transcript does not apply).
  E-6.3  LAB-G (`plan_v11_2026-09-18/lab/LAB-G_object_lsn.ps1`): labG_0 -> labG_1 changes LABG/dirA/f2.bin and no
        other f*.bin; labG_1 -> labG_2 changes LABG/dirB/f4.bin and no other; LABG/dirC never; no LABG object created
        or removed in either step (the self-test's _selftest directory is created and removed within the step).
  E-6.4  two volumes are refused (exit 1, both GUIDs named) before either image is walked, and a bodyfile before any
        image is read.
  E-6.5  CSV = JSON: the same rows, the same values.
  E-6.6  LAB-F (`LAB-F_unclean_detach.ps1`): every difference outside the system objects is a churn name.
  E-6.7  the testatomic chain: its captures share one checkpoint (virtual clock 46: open_questions.md, "the testatomic
        chain captures share a single checkpoint"), so the committed metadata of two steps is one state -- no row,
        and a statement says so (the steps' changes are in the log).
"""
import csv
import io
import json
import os
import re
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

TOOL = os.path.join(REPO, "forefst.py")
BEFORE, AFTER = "step6/win11refs8gtestmove_beforemove.raw", "step6/win11refs8gtestmove_aftermove.raw"
_RUNS = {}


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % rel)
    return p


def _run(new, old, *fmt):
    key = (new, old) + fmt
    if key not in _RUNS:
        p = subprocess.run([sys.executable, "-B", TOOL, _img(new), "files", "--cow-before", _img(old)] + list(fmt),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3600)
        _RUNS[key] = (p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"))
    return _RUNS[key]


def _rows(new, old):
    rc, out, err = _run(new, old, "--json")
    assert rc == 0, err[-3000:]
    doc = json.loads(out)
    rows = doc if isinstance(doc, list) else doc.get("rows") or doc.get("Rows")
    assert isinstance(rows, list), type(doc)
    return rows, err


def _paths(r, side):
    v = r.get(side + "FullPath") or r.get("FullPath")
    return v if isinstance(v, list) else ([v] if v else [])


# ── E-6.1 / E-6.2: the testmove session ─────────────────────────────────────────────────────────────────────────────
HAHA9 = {"testdeletion2/haha_%d.txt" % n for n in range(1, 10002) if str(n).startswith("9")}
CREATED = ({"testmove1/copied.txt", "testmove2/copied.txt", "testmove2/haha_100_copied.txt", "testdeletion2/hoho.txt",
            "log", "log/usnjournalafter.txt", "log/usnjournalbefore.txt", "log/moves.txt"}
           | {"testdeletion2/haha3_%d.txt" % n for n in range(90010, 90102)})
MOVED = {"testmove1/move.txt": "testmove2/move.txt",
         "testmove1/movesamedir.txt": "testmove1/movedsamedir.txt",
         "testdeletion2/haha2_10011.txt": "testmove2/haha2_10011.txt",
         "testdeletion2/haha2_10050.txt": "testdeletion2/haha2_10050_movedsamedir.txt",
         "testdeletion2/haha2_10070.txt": "testmove2/haha2_10070.txt"}


def test_e6_2_the_before_image_is_the_state_at_the_offline():
    p = subprocess.run([sys.executable, "-B", TOOL, _img(BEFORE), "files", "--csv"], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=3600)
    assert p.returncode == 0, p.stderr.decode()[-2000:]
    names = {r["FullPath"] for r in csv.DictReader(io.StringIO(p.stdout.decode("utf-8")))}
    assert {"testdeletion2/hahacp.txt", "testdeletion2/hahalast.txt", "testmove1/move.txt",
            "testmove1/movesamedir.txt", "testdeletion2/haha2_10021.txt"} <= names
    assert "testdeletion2/haha_7000.txt" not in names and "testmove2/move.txt" not in names
    assert HAHA9 <= names


def test_e6_1_removed_are_the_rm_haha9_files():
    rows, err = _rows(AFTER, BEFORE)
    assert "NOT stated" not in err, err[-2000:]
    removed = {p for r in rows if r["Change"] == "removed" for p in _paths(r, "Before")}
    user = {p for p in removed if not p.startswith(("$", "System Volume Information"))}
    assert user == HAHA9, (sorted(user - HAHA9)[:10], sorted(HAHA9 - user)[:10])


def test_e6_1_created_are_the_copies_and_new_files():
    rows, _err = _rows(AFTER, BEFORE)
    created = {p for r in rows if r["Change"] == "created" for p in _paths(r, "After")}
    user = {p for p in created if not p.startswith(("$", "System Volume Information"))}
    assert user == CREATED, (sorted(user - CREATED)[:10], sorted(CREATED - user)[:10])


def test_e6_1_moves_are_one_object_each_with_its_journal_reference():
    rows, _err = _rows(AFTER, BEFORE)
    by_before = {}
    for r in rows:
        if r["Change"] == "changed" and "FullPath" in r["ChangedFields"]:
            for p in _paths(r, "Before"):
                by_before[p] = r
    for old, new in MOVED.items():
        r = by_before.get(old)
        assert r is not None, "%s: no changed row" % old
        assert _paths(r, "After") == [new], (old, r)
    # the journal's file reference of each move is the row's ObjectRef
    p = subprocess.run([sys.executable, "-B", TOOL, _img(AFTER), "usn", "--csv"], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=3600)
    assert p.returncode in (0, 2), p.stderr.decode()[-2000:]
    k_name, k_ref, k_reason = F.out_key("file_name"), F.out_key("object_ref"), F.out_key("reason")
    refs = {}
    for u in csv.DictReader(io.StringIO(p.stdout.decode("utf-8"))):
        if "RENAME_NEW_NAME" in u[k_reason]:
            refs.setdefault(u[k_name], set()).add(u[k_ref])
    for old, new in MOVED.items():
        nm = new.rsplit("/", 1)[-1]
        assert by_before[old]["ObjectRef"] in refs.get(nm, set()), (nm, by_before[old]["ObjectRef"], refs.get(nm))


def test_e6_1_the_hard_link_and_the_round_trip():
    rows, _err = _rows(AFTER, BEFORE)
    hl = [r for r in rows if "testmove1/hl.txt" in _paths(r, "Before") + _paths(r, "After")]
    assert len(hl) == 1 and hl[0]["Change"] == "changed", hl
    r = hl[0]
    assert sorted(r["AfterFullPath"]) == ["testmove1/hl.txt", "testmove2/hardlinktohl.txt"], r
    assert str(r["BeforeHardLinkCount"]) == "1" and str(r["AfterHardLinkCount"]) == "2", r
    rt = [r for r in rows if "testdeletion2/haha2_10021.txt" in _paths(r, "After") + _paths(r, "Before")]
    assert all("FullPath" not in r["ChangedFields"] for r in rt), rt


# ── E-6.3: LAB-G ───────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("new,old,touched", [("step7/labG_1.raw", "step7/labG_0.raw", "LABG/dirA/f2.bin"),
                                             ("step7/labG_2.raw", "step7/labG_1.raw", "LABG/dirB/f4.bin")])
def test_e6_3_labg_one_file_changes(new, old, touched):
    rows, err = _rows(new, old)
    bins = {p for r in rows for p in _paths(r, "Before") + _paths(r, "After") if re.match(r"LABG/dir[ABC]/f\d\.bin$", p)}
    assert bins == {touched}, sorted(bins)
    r = [r for r in rows if touched in _paths(r, "After")][0]
    assert r["Change"] == "changed" and "Modified" in r["ChangedFields"], r
    if "NOT stated" not in err:
        lab = [r for r in rows if r["Change"] in ("created", "removed")
               and any(p.startswith("LABG") for p in _paths(r, "Before") + _paths(r, "After"))]
        assert not lab, lab[:5]


# ── E-6.4 / E-6.5 ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_e6_4_two_volumes_are_refused():
    rc, out, err = _run(AFTER, "step5/testatomic/win11refslasttests_baseline.raw", "--json")
    assert rc == 1 and not out.strip(), (rc, out[:500])
    assert re.search(r"not of one volume: volume GUID [0-9a-f-]{36} here, [0-9a-f-]{36} in ", err), err[-1000:]
    assert "Walking" not in err and "dirs," not in err, err[-1000:]                # refused before the walk


def test_e6_4_a_bodyfile_is_refused_first():
    import time
    t0 = time.time()
    p = subprocess.run([sys.executable, "-B", TOOL, _img(AFTER), "files", "--cow-before", _img(BEFORE), "--body"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
    err = p.stderr.decode("utf-8", "replace")
    assert p.returncode == 1 and "not a bodyfile" in err and not p.stdout, (p.returncode, err[-500:])
    assert "Walking" not in err and "dirs," not in err and time.time() - t0 < 30, err[-500:]   # before any walk


def test_e6_5_csv_equals_json():
    rows, _err = _rows(AFTER, BEFORE)
    rc, out, _e = _run(AFTER, BEFORE)
    assert rc == 0
    crow = list(csv.DictReader(io.StringIO(out)))
    assert len(crow) == len(rows)
    assert list(crow[0]) == F.COW_COLUMNS

    def cell(v):
        return "" if v is None else str(F._csv_cell(v))          # the CSV writes each typed JSON value as its text
    for c, j in zip(crow, rows):
        assert {k: c[k] for k in F.COW_COLUMNS} == {k: cell(j.get(k)) for k in F.COW_COLUMNS}


# ── E-6.6: LAB-F (`plan_v11_2026-09-18/lab/LAB-F_unclean_detach.ps1`) ───────────────────────────────────────────────
# The churn: LABF/d<i % 64>/f<j>_<i>.bin created (600 bytes), f0/7/14/... removed, f11/22/33 renamed r<j>_<i>.bin; the
# lab's log LABF/log/labf_actions.csv. Between the image taken after the power cut and the one after Windows recovered
# the volume, every difference outside the system objects is one of those names (or LABF, its log, the root).
LABF_NAME = re.compile(r"^(?:\.|LABF|LABF/log|LABF/log/labf_actions\.csv|LABF/d\d{1,2}|LABF/d\d{1,2}/[fr]\d{1,2}_\d+\.bin)$")


def test_e6_6_labf_every_difference_is_the_churn():
    rows, err = _rows("step7/labFafterreboot.raw", "step7/labFbeforereboot.raw")
    user = sorted({p for r in rows for p in _paths(r, "Before") + _paths(r, "After")
                   if not p.startswith(("$", "System Volume Information"))})
    assert user, "no difference outside the system objects: %s" % err[-1500:]
    bad = [p for p in user if not LABF_NAME.match(p)]
    assert not bad, bad[:10]


# ── E-6.7: the testatomic chain ─────────────────────────────────────────────────────────────────────────────────────
CHAIN = "step5/testatomic/win11refslasttests_baseline"


@pytest.mark.parametrize("old,new", [(CHAIN, CHAIN + "_mkdirtest"),
                                     (CHAIN + "_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal",
                                      CHAIN + "_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit")])
def test_e6_7_one_checkpoint_one_state_and_said(old, new):
    rows, err = _rows(new + ".raw", old + ".raw")
    assert rows == [], rows[:3]
    assert re.search(r"Both images are read from a checkpoint with virtual clock 46: the metadata they commit is one "
                     r"state", err), err[-1500:]


# ── E-6.8 / N500: a directory the walk lists and does not enter ─────────────────────────────────────────────────────
def _dirvol(tmp_path, name, ghost=False):
    import test_1132_red_b2_deleted as D
    import test_1132_d2_carve_extract as X
    dirs = {0x600: {"name": ""},
            0x761: {"parent": 0x600, "name": "d", "files": [D._row(D._name_key("a.txt"), D._file_value(5, 0x761, D._T))]},
            0x762: {"parent": 0x761, "name": "e", "files": [D._row(D._name_key("b.txt"), D._file_value(6, 0x762, D._T))]}}
    if ghost:      # a directory row whose OID (0x799) has no Object Table entry
        dirs[0x600]["files"] = [D._row(D._name_key("ghost"), D._dir_value(0x799))]
    v = D.DirVol()
    v.objects = v.tree(dirs)
    os.makedirs(str(tmp_path / name), exist_ok=True)
    return v.write(str(tmp_path / name / "target.raw")), D


def test_e6_8_a_directory_with_no_object_table_entry_is_said_and_makes_the_walk_incomplete(tmp_path):
    p, D = _dirvol(tmp_path, "now", ghost=True)
    q, _D = _dirvol(tmp_path, "old", ghost=True)
    rc, out, err = D._syn(p, "files", "--csv")
    assert rc == 2 and "1 directory it lists" in err and "no Object Table entry" in err and "0x799" in err, \
        (rc, err[-1500:])
    rc, out, err = D._syn(p, "files", "--cow-before", q, "--cow-partition-start", "0", "--json")
    assert "Created / removed objects are NOT stated" in err, err[-1500:]


def test_e6_8_a_depth_cut_is_a_note(tmp_path):
    p, D = _dirvol(tmp_path, "now")
    rc, out, err = D._syn(p, "files", "--csv", "--depth", "1")
    assert rc == 0 and "1 directory past the depth limit (1) listed and not entered" in err, (rc, err[-1500:])
    rc, out, err = D._syn(p, "files", "--csv")
    assert rc == 0 and "past the depth limit" not in err and "listed and not entered" not in err, err[-1500:]
