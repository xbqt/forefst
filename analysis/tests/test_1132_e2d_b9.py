"""E2d (1.14.0): B9, the N110 residue (PLAN_1.13.2 B9; DF08-DF10, DF04) -- one test each, synthetic where the corpus has
no witness.

  B9a  a split file's Encrypted / Compressed / Integrity flags are its OWN record's (the backing's +0x48), as its
       attribute word is (K006) -- not the name row's cached +0x40. Corpus: the copies differ only in the EA and Archive
       bits (47 of 577 split names on the public sample), so the volume is synthetic: name row 0x20, backing 0x20 + the
       bit.
  B9b  `_home_backings`: a file id two type-0x40 records of one home carry resolves to no record, said as a finding;
       1.13.1 kept the first. Measured before the change (`fixes/E2cd_NOTES.md` section 2): 0 such ids on 9 volumes,
       216,096 split rows -- synthetic.
  B9c  `details`: a path typed in another letter case, or with '//', on a case-insensitive directory, is the row
       resolve_path resolves (it said "path not found"); on the case-sensitive fixture (win11bidule
       tests/testdir/HI.txt and hi.txt, E94) each spelling is its own file, never the sibling.
  B9d  the timestomp storage cell's hex OID: the cell is gone (N314: RecordPlacement + DataResidency) --
       test_1132_e2b_machine::test_n314_timestomp_storage_is_split_into_both_axes.
"""
import csv
import io
import json
import os
import struct
import sys

import pytest

from _repo import REPO                                   # noqa: F401  layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
import test_1132_red_b2_deleted as D                     # noqa: E402  (DirVol, rows, the runners)
import test_1132_d2_carve_extract as X                   # noqa: E402  (_t40_key, _inline_backing)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

_T = D._T
_CONTENT = b"B9 (a): the backing's own attribute word" + b"." * 60       # 100 bytes, the name row's size


def _split_volume(tmp_path, backing_attrs):
    """/d (0x761) holds keep.txt (0x761:0x5, embedded-style name row) and split.txt: a split name row 0x761:0x9 whose
    cached attributes are 0x20, and its type-0x40 backing in the same directory with `backing_attrs` at +0x48."""
    name = bytearray(D._file_value(9, 0x761, _T))
    struct.pack_into("<Q", name, 0x38, len(_CONTENT))
    bk = bytearray(X._inline_backing(len(_CONTENT), _CONTENT, _T))
    struct.pack_into("<I", bk, 0x48, backing_attrs)
    return X._vol(tmp_path, {0x600: {"name": ""},
                             0x761: {"parent": 0x600, "name": "d",
                                     "files": [D._row(D._name_key("keep.txt"), D._file_value(5, 0x761, _T)),
                                               D._row(D._name_key("split.txt"), bytes(name)),
                                               D._row(X._t40_key(9, 0x761), bytes(bk))]}})


@pytest.mark.parametrize("bit,col", [(0x4000, "IsEncrypted"), (0x0800, "IsCompressed"), (0x8000, "HasIntegrity")])
def test_b9a_a_split_files_flags_are_its_own_records(tmp_path, bit, col):
    path = _split_volume(tmp_path, 0x20 | bit)
    rc, out, err, rows = D._syn_csv(path, "files")
    r = [x for x in rows if x["FileName"] == "split.txt"]
    assert r, "split.txt not listed" + D._ctx(rc, out, err)
    assert r[0]["RecordPlacement"] == "split", r[0]
    assert r[0][col].lower() == "true", (col, r[0][col], r[0]["FileAttributes"])      # the RED holds in any form


def test_b9a_control_the_flag_is_off_when_the_backing_has_none(tmp_path):
    path = _split_volume(tmp_path, 0x20)
    rc, out, err, rows = D._syn_csv(path, "files")
    r = [x for x in rows if x["FileName"] == "split.txt"]
    assert r and all(r[0][c].lower() == "false" for c in ("IsEncrypted", "IsCompressed", "HasIntegrity")), r


def _ref(d):
    """The details record's reference -- ObjectRef (1.14.0), or the 1.13.1 key, so the REDs fail on the defect."""
    return d.get("ObjectRef") or d.get("object_ref") or d.get("file_ref")


def _backing_rows(*fids):
    return [(X._t40_key(fid, 0x761 + i), b"\0" * 0x68) for i, fid in enumerate(fids)]


def test_b9b_a_colliding_file_id_resolves_to_no_record_and_is_said(monkeypatch):
    monkeypatch.setattr(F, "walk_bplus", lambda *a, **k: iter(_backing_rows(9, 9, 4)))
    monkeypatch.setattr(F, "_SKIP_FINDING", [])
    monkeypatch.setattr(F, "_SKIP_NOTES", {})
    m = F._home_backings(None, 0, 4096, None, {0x761: [1]}, 0x761, {})
    assert 9 not in m and 4 in m, sorted(m)
    assert "_home_backings" in F._SKIP_FINDING, F._SKIP_FINDING


def test_b9b_control_a_single_record_is_resolved(monkeypatch):
    monkeypatch.setattr(F, "walk_bplus", lambda *a, **k: iter(_backing_rows(9, 4)))
    monkeypatch.setattr(F, "_SKIP_FINDING", [])
    m = F._home_backings(None, 0, 4096, None, {0x761: [1]}, 0x761, {})
    assert sorted(m) == [4, 9] and not F._SKIP_FINDING


@pytest.mark.parametrize("typed", ["/d/KEEP.TXT", "/D//keep.txt", "/d/./Keep.txt"])
def test_b9c_details_takes_the_row_resolve_path_resolves(tmp_path, typed):
    path = _split_volume(tmp_path, 0x20)
    rc, out, err = D._syn(path, "details", typed, "--json")
    assert rc == 0, (typed, rc, err[-1500:])
    d = json.loads(out)
    d = d[0] if isinstance(d, list) else d
    assert _ref(d) == "0x761:0x5", d


def test_b9c_case_sensitive_directory_each_spelling_is_its_own_file(tmp_path):
    img = _corpus_image("win11bidule.raw")
    if img is None:
        pytest.skip("win11bidule.raw not in this tree")
    p = D._run(img, "files", "--csv")
    rows = {r["FullPath"]: r for r in csv.DictReader(io.StringIO(p[1]))}
    want = {n: rows[n]["ObjectRef"] for n in ("tests/testdir/HI.txt", "tests/testdir/hi.txt")}
    assert want["tests/testdir/HI.txt"] != want["tests/testdir/hi.txt"], want
    for n, ref in want.items():
        rc, out, err = D._run(img, "details", "/" + n, "--json")
        assert rc == 0, err[-1500:]
        d = json.loads(out)
        d = d[0] if isinstance(d, list) else d
        assert _ref(d) == ref, (n, _ref(d), ref)
