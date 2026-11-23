"""1.13.2 (ships 1.14.0) step C3, area dataruns: N262, N200 (a)(b), N304.

Plan: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (C3 rows), settlements Q33, Q34, Q35; direct mode (PLAN
decision 46): about five nodes per item.

N262 `dataruns` lists an extent-form stream of 0 bytes as "EXTENT ... 0 runs (empty stream)" and counts it as decoded
     (the public sample has 213: 103 split records whose backing was found, 110 embedded records); a split record whose
     backing was not found stays "not decoded".
N200 (a) `dataruns` (and refsanalysis `files -v`) render every attribute bit, as `files` does: the short table hid
     Encrypted, IntegrityStream, SparseFile and others. (b) `summary`'s counts beside "Files" count files only
     (directories carry the integrity bit on 15 corpus volumes, a reparse point on 15); "Integrity files".
N304 `dataruns --json`: a hole run's `vlcn`, `plcn` and `disk_offset` are null.
"""
import json
import os
import re
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21 / K10 readers)
from conftest import jint                                 # noqa: E402  (K9 reader)

from test_1132_red_a_coverage import _need, _run, _fx    # noqa: E402

SAMPLE = "step5/win11refstestmftecmd.raw"                # the public sample
INTEG = "win10refs8gsetintegristystreams1.raw"
ATTR2 = "step4continuing/win11refs4gattributestest2.raw"


def _runj(tool, img, args):
    rc, out, _ = _run(tool, img, list(args))
    i = out.find("{") if out.lstrip().startswith("{") else min(x for x in (out.find("["), out.find("{")) if x >= 0)
    try:
        return rc, jdoc(json.JSONDecoder().raw_decode(out[i:])[0])           # K21: internal names
    except ValueError:
        raise AssertionError("not JSON: rc %d\n%s" % (rc, out[:2000]))


def _records(d):
    return d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list))


# ═══ N262 -- empty extent-form streams ═══════════════════════════════════════════════════════════════════════

def test_n262_the_public_samples_empty_streams_are_listed_and_counted_as_decoded():
    rc, out, _ = _run("forefst", _need(SAMPLE), ["dataruns"])
    empties = re.findall(r"^            record=\w+, size=0, attrs=[^,]*, 0 runs \(empty stream\)$", out, re.M)
    ext = int(re.search(r"Data in extents:\s+(\d+)", out).group(1))
    dec = int(re.search(r"With decoded extents:\s+(\d+)", out).group(1))
    assert rc == 0 and len(empties) == 213 and dec == ext == 1233, (rc, len(empties), dec, ext)


@pytest.mark.parametrize("info,empty", [
    pytest.param({"extents": [], "file_size": 0, "extent_source": "local"}, True, id="split-local"),
    pytest.param({"extents": [], "file_size": 0, "extent_source": "remote"}, True, id="split-remote"),
    pytest.param({"extents": [], "file_size": 0}, True, id="embedded"),
    pytest.param({"extents": [], "file_size": 0, "extent_source": "unresolved"}, False, id="backing-not-found"),
    pytest.param({"extents": [], "file_size": 5, "extent_source": "local"}, False, id="bytes-but-no-runs"),
    pytest.param({"extents": [{"clusters": 1}], "file_size": 0, "extent_source": "local"}, False, id="has-runs"),
])
def test_n262_an_empty_stream_is_one_of_0_bytes_whose_record_is_in_hand(info, empty):
    assert F._empty_extent_stream(info) is empty


def test_n262_control_the_empty_streams_are_the_samples_0_byte_extent_files():
    """The 213 lines name 213 distinct paths, each a file `files` reports with size 0."""
    img = _need(SAMPLE)
    rc, out, _ = _run("forefst", img, ["dataruns"])
    lines = out.splitlines()
    paths = [lines[i - 1].split("EXTENT", 1)[1].strip() for i, l in enumerate(lines) if "0 runs (empty stream)" in l]
    rc2, d = _runj("forefst", img, ["files", "--json", "-"])
    size = {}
    for r in _records(d):
        p = (r.get("full_path") or "").lstrip("/\\").replace("\\", "/")
        size[p] = r.get("file_size")
    missing = [p for p in paths if p.lstrip("/") not in size]
    assert len(set(paths)) == 213 and not missing, (len(set(paths)), missing[:3])
    assert all(size[p.lstrip("/")] in (0, "0") for p in paths), [(p, size[p.lstrip("/")]) for p in paths[:5]]


# ═══ N200 (a) -- every attribute bit ═════════════════════════════════════════════════════════════════════════

def test_n200a_dataruns_attrs_are_the_attributes_files_reports():
    img = _need(SAMPLE)
    rc, out, _ = _run("forefst", img, ["dataruns"])
    pairs = re.findall(r"^  EXTENT    (.+)\n            record=\w+, size=\d+, attrs=([^,]*),", out, re.M)
    rc2, d = _runj("forefst", img, ["files", "--json", "-"])
    fa = {}
    for r in _records(d):
        p = (r.get("FullPath") or "").lstrip("/\\").replace("\\", "/")        # acceptance 1.14.0 (K21)
        fa[p] = r.get("FileAttributes") or ""
    both = [(p, a) for p, a in pairs if p.lstrip("/") in fa]
    _fx(len(both) > 500, "only %d dataruns paths found in files --json" % len(both))

    # the same NAMES (1.14.0, K14 / E-3): dataruns writes `0x20 (Archive|...)` and `0x0 (none set)`, files the names
    # and `0x0` for a word with no bit set
    def _names(text):
        m = re.search(r"\(([^)]*)\)", text)
        return set((m.group(1) if m else text).split("|")) - {"", "0x0", "none set"}
    bad = [(p, a, fa[p.lstrip("/")]) for p, a in both if _names(a) != _names(str(fa[p.lstrip("/")]))]
    assert not bad, bad[:5]
    assert any("IntegrityStream" in a for _p, a in both), "no IntegrityStream on the public sample's extent files"


def test_n200a_refsanalysis_files_v_names_the_integrity_stream_bit():
    rc, out, _ = _run("refsanalysis", _need(INTEG), ["files", "-v"])
    rows = [l for l in out.splitlines() if l.startswith("  FILE ")]
    assert rows and any("IntegrityStream" in l for l in rows), rows[:3]


def test_n200a_control_the_full_table_names_encrypted():
    assert "Encrypted" in F._attrs_to_str(0x4020) and "Archive" in F._attrs_to_str(0x4020)


# ═══ N200 (b) -- the counts beside "Files" ═══════════════════════════════════════════════════════════════════

def test_n200b_summary_counts_integrity_files_not_directories():
    img = _need(INTEG)
    rc, out, _ = _run("forefst", img, ["summary"])
    files = int(re.search(r"Files:\s+(\d+)", out).group(1))
    m = re.search(r"Integrity files:\s+(\d+)", out)
    rc2, d = _runj("forefst", img, ["files", "--json", "-"])
    want = sum(1 for r in _records(d) if r.get("has_integrity") and not r.get("is_directory"))
    assert m and int(m.group(1)) == want <= files, (m and m.group(0), want, files)
    assert "Integrity objects" not in out


def test_n200b_refsanalysis_summary_says_the_same_count():
    img = _need(INTEG)
    _rc, a, _ = _run("forefst", img, ["summary"])
    _rc, b, _ = _run("refsanalysis", img, ["summary++"])
    ma, mb = re.search(r"Integrity files:\s+(\d+)", a), re.search(r"Integrity files:\s+(\d+)", b)
    assert ma and mb and ma.group(1) == mb.group(1), (ma and ma.group(0), mb and mb.group(0))


def test_n200b_the_four_counts_leave_directories_out(monkeypatch):
    rows = [{"is_dir": True, "is_encrypted": 1, "has_integrity": 1, "is_compressed": 1, "has_reparse": 1},
            {"is_dir": False, "is_encrypted": 1, "has_integrity": 1, "is_compressed": 0, "has_reparse": 1},
            {"is_dir": False}]
    monkeypatch.setattr(F, "walk_directory_tree", lambda *a, **k: [dict(r) for r in rows])
    counts, _res = F.fs_content_summary(None, 0, 4096, None, {}, plus=True)
    got = {k: counts[k] for k in ("encrypted_files", "integrity_files", "compressed_files", "reparse_files")}
    assert got == {"encrypted_files": 1, "integrity_files": 1, "compressed_files": 0, "reparse_files": 1}, got


def test_n200b_reparse_count_of_summary_json_is_of_files():
    img = _need(ATTR2)
    rc, d = _runj("refsanalysis", img, ["summary++", "--json"])          # the key refsanalysis summary++ carries
    rc2, fl = _runj("forefst", img, ["files", "--json", "-"])
    # wave E step E1a (N149, acceptance change): the files, each once -- a hard-linked file is one file under several
    # names, and `summary` counts files once since then (this node counted the names: 941 against 664 files)
    # acceptance 1.14.0 (K21: the files record's names; O7)
    _hit = [r for r in _records(fl) if "ReparsePoint" in str(r.get("FileAttributes") or "")
            and not r.get("IsDirectory")]
    want = len({r["ObjectRef"] for r in _hit if r.get("ObjectRef")}) + sum(1 for r in _hit if not r.get("ObjectRef"))
    got = d.get("ReparseFiles") if "ReparseFiles" in d else next(
        (v["ReparseFiles"] for v in d.values() if isinstance(v, dict) and "ReparseFiles" in v), None)
    assert got == want, (got, want)


# ═══ N304 -- a hole run has no cluster ════════════════════════════════════════════════════════════════════

def test_n304_a_hole_run_carries_no_cluster_and_no_offset():
    rc, d = _runj("forefst", _need(SAMPLE), ["dataruns", "--json", "-"])
    holes = [r for x in _records(d) for r in x.get("Runs", []) if r.get("IsHole")]          # K21 (1.14.0)
    _fx(holes, "the public sample has no hole run")
    assert all(r["VLCN"] is None and r["PLCN"] is None and r["DiskOffset"] is None for r in holes), holes[:3]


def test_n304_control_a_real_run_keeps_its_numbers():
    img = _need(SAMPLE)
    ps = F.find_refs_partition(img)[0]
    rc, d = _runj("forefst", img, ["dataruns", "--json", "-"])
    runs = [r for x in _records(d) for r in x.get("Runs", []) if not r.get("IsHole")]     # K21, K9 (1.14.0): hex
    assert runs and all(jint(r["PLCN"]) is not None and jint(r["DiskOffset"]) == ps + jint(r["PLCN"]) * 4096
                        for r in runs[:200])


def test_n304_control_the_csv_extents_column_keeps_its_hole_form(tmp_path):
    out = str(tmp_path / "d.csv")
    rc, _o, _ = _run("forefst", _need(SAMPLE), ["dataruns", "--csv", out])
    with open(out, encoding="utf-8") as fh:
        txt = fh.read()
    assert re.search(r"fvcn=0x[0-9a-f]+,HOLE,clu=\d+", txt), txt[:500]                 # K9 (1.14.0): a VCN in hex
