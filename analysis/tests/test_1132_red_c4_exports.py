"""1.13.2 (ships 1.14.0) step C4, area exports: B11, N164, N266, N319 ($I/$R half).

Plan: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (C4 rows), settlements Q38, Q39; decision 22's O2; direct mode
(PLAN decision 46): about five nodes per item. B11's metadata and bulk-exporter nodes are in
`test_1132_red_b_items.py` (tightened to O2's `<dir>_2`); this file adds the `export deleted` forced collision (critic
M2), the directory rule for every exporter and the index's content.

B11  No export writes over an earlier one: `export metadata` takes a new or empty directory, a bulk export a directory
     that holds none of the record files (holes.json, an index, a manifest, a recovery log); otherwise `<dir>_2`,
     `_3`, ..., said on stderr. A content file whose name is taken is renamed `.dupN` and the rename is recorded:
     `export_index.csv` (ObjectRef, FullPath, ContentFile, SHA256, RenameReason) for resident-all, recyclebin and
     snapshots; SHA256 and RenameReason in `export deleted`'s deleted_files.csv/.json and recovery_manifest.json.
N164 `export deleted` writes its index when no entry reaches the content writer (only `--orphans` rows; every entry
     left out by `--no-system`).
N266 `export snapshots DIR --json` exits 1 with a usage message and writes nothing; `snapshots --json` applies
     `--file` and `--snapshot`.
N319 ($I/$R half) the recycle-bin export's index carries the $R file's ObjectRef and path.
"""
import csv
import json
import os
import re
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21: internal names)

from test_1132_red_b_items import (_run, _scratch, _image_or_skip, _file_sha, _sha, _ctx, _snapshot_dir,  # noqa: E402
                                   _synthetic_vol, _seal_failures, FOREFST, AB)

BASE = AB.BASE_IMAGE                                     # step1/win11refsmini.raw (battery base A)
ORPH = "step2/win11refs2g_sha256checksums.raw"           # one orphan directory object (OID 0x723), measured
SNAP = "win11refs2tsnapshots.raw"
RB = "win11bidule.raw"
_RB_WIN_SHA = "2bbc2c538dfe8746f432b75f5691f04714c412da20766672277d68af300776ed"   # Windows' hash of the recycled jpg


def _csv_rows(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _objrefs_of_files(img, s):
    """{FullPath: ObjectRef} from `files --csv` (the form the index must carry)."""
    out = os.path.join(s, "files.csv")
    rc, o, e = _run(FOREFST, img, "files", "--csv", out, cwd=s)
    return {r["FullPath"]: r["ObjectRef"] for r in _csv_rows(out)}


# ═══ B11 -- the directory rule (unit) ═════════════════════════════════════════════════════════════════════════

def test_b11_export_dir_takes_a_new_or_empty_directory_for_a_bundle(tmp_path, capsys):
    new, empty, full = str(tmp_path / "new"), tmp_path / "empty", tmp_path / "full"
    empty.mkdir(); full.mkdir(); (full / "notes.txt").write_text("examiner")
    assert F._export_dir(new, bundle=True) == new and F._export_dir(str(empty), bundle=True) == str(empty)
    assert F._export_dir(str(full), bundle=True) == str(full) + "_2"
    (tmp_path / "full_2").mkdir(); (tmp_path / "full_2" / "manifest.json").write_text("{}")
    assert F._export_dir(str(full), bundle=True) == str(full) + "_3"
    err = capsys.readouterr().err
    assert "is not empty: writing to %s_2" % full in err and "nothing is overwritten" in err, err


def test_b11_export_dir_takes_a_bulk_directory_unless_it_holds_an_export(tmp_path, capsys):
    d = tmp_path / "out"
    d.mkdir(); (d / "notes.txt").write_text("examiner")
    assert F._export_dir(str(d)) == str(d)                              # the examiner's files are no export
    for rec in ("holes.json", "deleted_files.csv", "export_index.csv", "recovery_log.txt"):
        (d / rec).write_text("x")
        assert F._export_dir(str(d)) == str(d) + "_2", rec
        (d / rec).unlink()
    (d / "holes.json").write_text("{}")
    assert F._export_dir(str(d) + "/") == str(d) + "_2"                  # a trailing separator names the same folder
    assert "holds an earlier export" in capsys.readouterr().err


def test_b11_index_place_says_why_a_name_is_taken(tmp_path):
    d = tmp_path / "x"
    (d / "a").mkdir(parents=True)
    (d / "a" / "f.txt").write_bytes(b"examiner")
    ix = F._ExportIndex(str(d))
    p1, why1 = ix.place(str(d / "a" / "f.txt"))
    assert p1.endswith("f.txt.dup1") and why1 == "a/f.txt already exists in the output directory"
    open(p1, "wb").write(b"one")
    ix.written(p1, b"one", why1, "0x702:0x2", "a/f.txt")
    p2, why2 = ix.place(str(d / "b.txt"))
    assert p2.endswith("b.txt") and why2 == ""
    open(p2, "wb").write(b"two")
    ix.written(p2, b"two", why2)
    p3, why3 = ix.place(str(d / "b.txt"))
    assert p3.endswith("b.txt.dup1") and why3 == "another file of this export is named b.txt"
    ix.write()
    rows = _csv_rows(str(d / "export_index.csv"))
    assert [r["ContentFile"] for r in rows] == ["a/f.txt.dup1", "b.txt"]
    assert rows[0]["SHA256"] == _sha(b"one") and rows[0]["ObjectRef"] == "0x702:0x2" and rows[0]["FullPath"] == "a/f.txt"


# ═══ B11 -- export metadata (synthetic volume: fast) ═══════════════════════════════════════════════════════════

def test_b11_metadata_into_a_folder_with_other_files_goes_to_dir_2(tmp_path):
    v = _synthetic_vol(tmp_path, "s1")
    d = str(tmp_path / "bundle")
    os.makedirs(d)
    open(os.path.join(d, "vbr_primary.bin"), "wb").write(b"examiner's file of a bundle name")
    before = _snapshot_dir(d)
    rc, out, err = _run(FOREFST, v.path, "export", "metadata", d, cli=v.geo.cli, cwd=str(tmp_path))
    assert _snapshot_dir(d) == before, _ctx(rc, out, err)
    seal = os.path.join(d + "_2", "sha256sums.txt")
    assert os.path.isfile(seal) and not _seal_failures(seal), _ctx(rc, out, err)
    assert d + "_2" in err, err


def test_b11_metadata_manifest_names_the_files_written(tmp_path):
    v = _synthetic_vol(tmp_path, "s1")
    d = str(tmp_path / "bundle")
    rc, out, err = _run(FOREFST, v.path, "export", "metadata", d, cli=v.geo.cli, cwd=str(tmp_path))
    m = jdoc(json.load(open(os.path.join(d, "manifest.json"))), F._BUNDLE_KEYS)
    names = [a["file"] for a in m["artifacts"]]
    assert names and all(os.path.isfile(os.path.join(d, n)) and _file_sha(os.path.join(d, n)) == a["sha256"]
                         for n, a in zip(names, m["artifacts"])), names
    assert sorted(os.listdir(d)) == sorted(set(names) | {"manifest.json", "sha256sums.txt", "holes.json"}), \
        sorted(os.listdir(d))


# ═══ B11 -- export deleted (critic M2's forced collision; base A) ═══════════════════════════════════════════════

def test_b11_export_deleted_records_a_forced_rename_in_its_index():
    img = _image_or_skip(BASE)
    with _scratch("c4del") as s:
        d = os.path.join(s, "out")
        os.makedirs(os.path.join(d, "content"))
        planted = os.path.join(d, "content", "haha.txt")
        open(planted, "wb").write(b"examiner's file")
        rc, out, err = _run(FOREFST, img, "export", "deleted", d, cwd=s)
        assert open(planted, "rb").read() == b"examiner's file", "export deleted overwrote the examiner's file"
        rows = [r for r in _csv_rows(os.path.join(d, "deleted_files.csv")) if r["FileName"] == "haha.txt"]
        assert len(rows) == 1 and rows[0]["ContentFile"] == "content/haha.txt.dup1", rows + [_ctx(rc, out, err)]
        r = rows[0]
        assert r["SHA256"] == _file_sha(os.path.join(d, r["ContentFile"])), r
        assert r["RenameReason"] == "content/haha.txt already exists in the output directory", r
        recs = [x for x in jdoc(json.load(open(os.path.join(d, "recovery_manifest.json"))), F._DELETED_MANIFEST_KEYS)["records"]
                if x["content_file"] == "content/haha.txt.dup1"]
        assert len(recs) == 1 and recs[0]["SHA256"] == r["SHA256"] and recs[0]["RenameReason"] == r["RenameReason"]
        j = [x for x in json.load(open(os.path.join(d, "deleted_files.json"))) if x["FileName"] == "haha.txt"]
        assert j and j[0]["SHA256"] == r["SHA256"] and j[0]["RenameReason"] == r["RenameReason"]


def test_b11_export_deleted_hashes_every_content_file():
    img = _image_or_skip(BASE)
    with _scratch("c4del") as s:
        d = os.path.join(s, "out")
        rc, out, err = _run(FOREFST, img, "export", "deleted", d, cwd=s)
        recs = [x for x in jdoc(json.load(open(os.path.join(d, "recovery_manifest.json"))), F._DELETED_MANIFEST_KEYS)["records"] if x["content_file"]]
        # measured: 6 content files on base A until wave D step D3; decision 50 holds back the inline bytes of the 5
        # STILL PRESENT copies (each "copy of the current entry (same dates)"), so the one deleted file is left
        assert len(recs) == 1 and recs[0]["name"] == "haha.txt", _ctx(rc, out, err)
        assert all(x["SHA256"] == _file_sha(os.path.join(d, x["content_file"])) and x["RenameReason"] is None
                   for x in recs), recs


def test_b11_a_second_export_deleted_goes_to_dir_2_and_leaves_the_first_as_written():
    img = _image_or_skip(BASE)
    with _scratch("c4del") as s:
        d = os.path.join(s, "out")
        rc1, o1, e1 = _run(FOREFST, img, "export", "deleted", d, cwd=s)
        first = _snapshot_dir(d)
        rc2, o2, e2 = _run(FOREFST, img, "export", "deleted", d, "--full", cwd=s)
        assert _snapshot_dir(d) == first, "the second run changed the first export" + _ctx(rc2, o2, e2)
        assert os.path.isfile(os.path.join(d + "_2", "deleted_files.csv")), _ctx(rc2, o2, e2)
        assert "holds an earlier export: writing to %s_2" % d in e2, e2


def test_b11_a_bulk_export_into_another_exports_folder_goes_to_dir_2():
    img = _image_or_skip(BASE)
    with _scratch("c4mix") as s:
        d = os.path.join(s, "out")
        _run(FOREFST, img, "export", "deleted", d, cwd=s)
        first = _snapshot_dir(d)
        rc, out, err = _run(FOREFST, img, "export", "resident-all", d, cwd=s)
        assert _snapshot_dir(d) == first, "resident-all rewrote the earlier export's holes.json" + _ctx(rc, out, err)
        assert os.path.isfile(os.path.join(d + "_2", "export_index.csv")) and \
            os.path.isfile(os.path.join(d + "_2", "holes.json")), _ctx(rc, out, err)


# ═══ B11 -- the bulk index's content ════════════════════════════════════════════════════════════════════════════

def test_b11_resident_all_index_rows_are_files_objectrefs_and_the_written_bytes():
    img = _image_or_skip(BASE)
    with _scratch("c4res") as s:
        d = os.path.join(s, "out")
        rc, out, err = _run(FOREFST, img, "export", "resident-all", d, cwd=s)
        rows = _csv_rows(os.path.join(d, "export_index.csv"))
        written = sorted(k for k in _snapshot_dir(d) if k not in ("export_index.csv", "holes.json"))
        assert sorted(r["ContentFile"] for r in rows) == written and len(rows) == 8, (rows, written)
        refs = _objrefs_of_files(img, s)
        bad = [r for r in rows if refs.get(r["FullPath"]) != r["ObjectRef"] or not r["ObjectRef"]
               or _file_sha(os.path.join(d, r["ContentFile"])) != r["SHA256"] or r["RenameReason"]]
        assert not bad, bad


def test_b11_index_lists_exactly_the_files_written_for_a_subtree():
    img = _image_or_skip(BASE)
    with _scratch("c4res") as s:
        d = os.path.join(s, "out")
        rc, out, err = _run(FOREFST, img, "export", "resident-all", d, "--depth", "0", "--oid", "0x701", cwd=s)
        rows = _csv_rows(os.path.join(d, "export_index.csv"))
        on_disk = sorted(k for k in _snapshot_dir(d) if k not in ("export_index.csv", "holes.json"))
        assert sorted(r["ContentFile"] for r in rows) == on_disk, (rows, on_disk, _ctx(rc, out, err))


# ═══ N319 -- the recycle bin's index ════════════════════════════════════════════════════════════════════════════

def test_n319_recyclebin_index_names_the_r_file_its_objectref_and_hash():
    img = _image_or_skip(RB)
    with _scratch("c4rb") as s:                              # the export writes about 52 MB; removed at the end
        d = os.path.join(s, "out")
        rc, out, err = _run(FOREFST, img, "export", "recyclebin", d, cwd=s)
        rows = [r for r in _csv_rows(os.path.join(d, "export_index.csv")) if r["SHA256"] == _RB_WIN_SHA]
        assert len(rows) == 1, _ctx(rc, out, err)
        r = rows[0]
        assert re.match(r"\$RECYCLE\.BIN/S-1-5-[0-9-]+/\$R\w+\.jpg$", r["FullPath"]), r
        refs = _objrefs_of_files(img, s)
        assert r["ObjectRef"] and refs.get(r["FullPath"]) == r["ObjectRef"], (r, refs.get(r["FullPath"]))
        assert _file_sha(os.path.join(d, r["ContentFile"])) == _RB_WIN_SHA


# ═══ N164 -- the index without content ══════════════════════════════════════════════════════════════════════════

def test_n164_only_orphans_rows_are_indexed():
    img = _image_or_skip(ORPH)
    with _scratch("c4n164") as s:
        d = os.path.join(s, "out")
        rc, out, err = _run(FOREFST, img, "export", "deleted", d, "--no-slack", "--orphans", cwd=s)
        rows = _csv_rows(os.path.join(d, "deleted_files.csv")) if os.path.isfile(
            os.path.join(d, "deleted_files.csv")) else None
        assert rows is not None and [r["RecoverySource"] for r in rows] == ["orphan"], _ctx(rc, out, err)
        # acceptance 1.14.0 (N318): an orphan directory's own OID is its ObjectRef; RecoveredFrom (the directory an
        # entry was found in) is not known for an orphan
        assert rows[0]["ObjectRef"] == "0x723:0x0" and rows[0]["RecoveredFrom"] == "", rows[0]


def test_n164_every_entry_left_out_by_no_system_still_writes_the_index():
    img = _image_or_skip(BASE)
    with _scratch("c4n164") as s:
        d = os.path.join(s, "out")
        rc, out, err = _run(FOREFST, img, "export", "deleted", d, "--no-system", "--search", "FVE2", cwd=s)
        p = os.path.join(d, "deleted_files.csv")
        assert os.path.isfile(p) and _csv_rows(p) == [], _ctx(rc, out, err)
        assert os.path.isfile(os.path.join(d, "recovery_manifest.json"))
        assert re.search(r"\(\d+ OS/BitLocker \(FVE2\) system entr(y|ies) left out by --no-system", out), out


def test_n164_control_no_system_keeps_the_user_entries():
    img = _image_or_skip(BASE)
    with _scratch("c4n164") as s:
        d = os.path.join(s, "out")
        rc, out, err = _run(FOREFST, img, "export", "deleted", d, "--no-system", cwd=s)
        rows = _csv_rows(os.path.join(d, "deleted_files.csv"))
        assert rows and all(r["Category"] == "user" for r in rows) and "haha.txt" in {r["FileName"] for r in rows}


# ═══ N266 -- snapshots: --json is a listing ═══════════════════════════════════════════════════════════════════

def test_n266_export_snapshots_with_json_is_refused_and_writes_nothing():
    img = _image_or_skip(SNAP)
    with _scratch("c4snap") as s:
        d = os.path.join(s, "out")
        rc, out, err = _run(FOREFST, img, "export", "snapshots", d, "--json", cwd=s)
        assert rc == 1 and "--json lists the snapshots" in err and not os.path.exists(d), _ctx(rc, out, err)


def _snap_json(img, *args):
    rc, out, err = _run(FOREFST, img, "snapshots", "--json", *args)
    return rc, jdoc(json.loads(out[out.find("{"):]))      # K21: internal names


def test_n266_snapshots_json_applies_file():
    img = _image_or_skip(SNAP)
    rc, d = _snap_json(img, "--file", "lasttest")
    assert rc == 0 and [x["path"] for x in d["files"]] == ["testsnapshots/lasttest.txt"], d["files"]


def test_n266_snapshots_json_applies_snapshot():
    img = _image_or_skip(SNAP)
    rc, d = _snap_json(img, "--file", "lasttest", "--snapshot", "2")
    assert [s["name"] for s in d["files"][0]["snapshots"]] == ["sameaslastversion"], d["files"]
    rc, d = _snap_json(img, "--snapshot", "firstversion")
    assert [(x["path"], [s["name"] for s in x["snapshots"]]) for x in d["files"]] == [
        ("testsnapshots/test.txt", ["firstversion"])], d["files"]


def test_n266_control_snapshots_json_without_filters_lists_every_version():
    img = _image_or_skip(SNAP)
    rc, d = _snap_json(img)
    assert d["files_with_snapshots"] == len(d["files"]) == 5 and d["total_snapshots"] == 10 == sum(
        len(x["snapshots"]) for x in d["files"])


def test_n266_export_snapshots_index_names_each_version():
    img = _image_or_skip(SNAP)
    with _scratch("c4snap") as s:
        d = os.path.join(s, "out")
        rc, out, err = _run(FOREFST, img, "export", "snapshots", d, cwd=s)
        rows = _csv_rows(os.path.join(d, "export_index.csv"))
        on_disk = sorted(k for k in _snapshot_dir(d) if k not in ("export_index.csv", "holes.json"))
        assert sorted(r["ContentFile"] for r in rows) == on_disk and rows, (rows, on_disk, _ctx(rc, out, err))
        assert all(r["SHA256"] == _file_sha(os.path.join(d, r["ContentFile"])) and r["ObjectRef"] for r in rows)
        arg = [r for r in rows if r["FullPath"] == "testsnapshots/arg.txt [version test2]"]
        assert len(arg) == 1 and arg[0]["ObjectRef"] == "0x73c:0x2", rows
