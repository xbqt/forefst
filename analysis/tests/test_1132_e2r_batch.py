"""E2 (1.14.0): the defects the wave golden's accounting and the form scan found after the answers (fixes/E2cd_NOTES.md
section 8). RED on fixes/prefix_E2r (forefst 8d94e904, refsanalysis 20ba3dc6).

  T1  timestomp's RecordPlacement is the walker's own (the name row's layout): every row's ObjectRef, RecordPlacement and
      DataResidency are `files`' for that path. E2b's N314 row read `record_embedded`, which timestomp's walker never
      sets, so every file was `split` (all 623,326 embedded rows of the corpus's 849,950 `timestomp --all` rows).
  T2  `export deleted --carve`: the index sentence says what the index holds since E-1 (every entry the report lists,
      each with its Status; it said "every entry that is not a live file's"); the manifest key is named by its output
      name (ContentConfidence); a refused carve (every run unwritten) has no content grade and zero-filled nothing (on
      win11refs2g the 5 `medium` records were all refused files, with no content file).
  T3  `ReFS X.Y` (K29) in summary's upgraded-volume line and in integrity's boot-sector version note.
  T4  `details`' Is moved is a word (K19): `no`, never `False`.
  T5  refsanalysis: sizes (R2 `N bytes (x KiB)`, R3 `64 MiB`), words (K19), counts (K28) in boot / chkp / supb /
      containers / bootedit; the schema table's name column fits its longest name.
"""
import csv
import io
import json
import os
import re
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

_fx = AB._fx
FOREFST = os.path.join(REPO, "forefst.py")
RA = os.path.join(REPO, "refsanalysis.py")
MINI34 = "step1/win10refsmini.raw"
MINI314 = "step1/win11refsmini.raw"
UPGRADED = "step3/win10to11refs4g.raw"
CARVE = "step2/win11refs2g.raw"
COMPRESSED = "step3/win11refs8gcompresslz4default.raw"


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _run(tool, image, *args, timeout=3600):
    r = UW.run([sys.executable, "-B", tool, image] + list(args), capture_output=True, text=True,
               timeout=timeout, cwd=os.path.dirname(image))
    _fx("Traceback (most recent call last)" not in r.stderr, "the tool crashed:\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


def _lines(text, rx):
    return [ln for ln in text.splitlines() if re.search(rx, ln)]


# ═══ T1 -- timestomp's two axes are `files`' ══════════════════════════════════════════════════════════════════════

def _files_axes(img):
    rc, out, err = _run(FOREFST, img, "files", "--csv")
    _fx(rc == 0, "files --csv exits %d:\n%s" % (rc, err[-2000:]))
    return {r["FullPath"]: (r["ObjectRef"], r["RecordPlacement"], r["DataResidency"])
            for r in csv.DictReader(io.StringIO(out)) if r["IsDirectory"] == "false"}


@pytest.mark.parametrize("rel", [MINI34, MINI314])
def test_t1_timestomp_axes_are_the_files_axes(rel):
    img = _img(rel)
    files = _files_axes(img)
    _fx(any(v[1] == "embedded" for v in files.values()), "premise: no embedded file on %s" % rel)
    rc, out, err = _run(FOREFST, img, "timestomp", "--all", "--csv", "-")
    rows = list(csv.DictReader(io.StringIO(out)))
    _fx(rows, "no timestomp rows:\n" + err[-2000:])
    bad = [(r["FullPath"], (r["ObjectRef"], r["RecordPlacement"], r["DataResidency"]), files.get(r["FullPath"]))
           for r in rows if (r["ObjectRef"], r["RecordPlacement"], r["DataResidency"]) != files.get(r["FullPath"])]
    assert not bad, "%d of %d rows differ from files: %r" % (len(bad), len(rows), bad[:5])


def test_t1_timestomp_json_rows_carry_the_same_axes():
    img = _img(MINI34)
    files = _files_axes(img)
    rc, out, err = _run(FOREFST, img, "timestomp", "--all", "--json", "-")
    rows = json.loads(out)["Rows"]
    _fx(rows, "no timestomp rows")
    bad = [r["FullPath"] for r in rows
           if (r["ObjectRef"], r["RecordPlacement"], r["DataResidency"]) != files.get(r["FullPath"])]
    assert not bad, bad[:5]


# ═══ T2 -- export deleted --carve ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def carve(tmp_path_factory):
    d = str(tmp_path_factory.mktemp("e2r_carve") / "out")
    rc, out, err = _run(FOREFST, _img(CARVE), "export", "deleted", "--carve", d)
    _fx(os.path.isfile(os.path.join(d, "recovery_manifest.json")), "no manifest (rc %d):\n%s" % (rc, err[-2000:]))
    with open(os.path.join(d, "deleted_files.csv"), encoding="utf-8") as fh:
        index = list(csv.DictReader(fh))
    with open(os.path.join(d, "recovery_manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    return out, index, man["Records"]


def test_t2_the_index_sentence_says_what_the_index_holds(carve):
    out, index, _recs = carve
    m = re.search(r"(\d+) entr(?:y|ies) indexed → .*\(\+ \.json; (.*)\)$", out, re.M)
    assert m, out[-3000:]
    assert m.group(2) == "every entry the report lists, its Status column says what it is", m.group(2)
    assert int(m.group(1)) == len(index), (m.group(1), len(index))
    _fx(any(r["Status"] == "still present" for r in index), "premise: no live file's entry in the index")
    assert all(r["Status"] for r in index), [r for r in index if not r["Status"]][:3]


def test_t2_the_unwritten_line_names_the_manifest_key_by_its_output_name(carve):
    out, _index, recs = carve
    ln = _lines(out, r"Runs zero-filled because")
    _fx(ln, "premise: no unwritten-run line")
    assert "ContentConfidence medium" in ln[0] and "content_confidence" not in ln[0], ln[0]
    assert all("ContentConfidence" in r for r in recs)


def test_t2_a_refused_carve_has_no_content_grade_and_zero_filled_nothing(carve):
    _out, _index, recs = carve
    ref = [r for r in recs if r["RefusedAllUnwritten"]]
    _fx(any(r["UnwrittenNonzeroOnDiskBytes"] for r in ref), "premise: no refused file over non-zero on-disk data")
    bad = [(r["FileName"], r["ContentConfidence"], r["ConfidenceReason"], r["UnwrittenZeroFilledBytes"]) for r in ref
           if r["ContentConfidence"] is not None or r["ConfidenceReason"] is not None or r["UnwrittenZeroFilledBytes"]]
    assert not bad, bad[:5]
    assert all(r["UnwrittenRuns"] and not r["ContentFile"] for r in ref)        # the runs stay; no content
    assert all(r["ContentFile"] for r in recs if r["ContentConfidence"] is not None)


# ═══ T3 / T4 -- forefst text words ═════════════════════════════════════════════════════════════════════════════════

def test_t3_upgraded_volume_line_names_the_version_as_refs():
    rc, out, err = _run(FOREFST, _img(UPGRADED), "fastsummary")
    ln = _lines(out, r"Volume state:.*APPEARS UPGRADED")
    _fx(ln, "premise: no upgraded-volume line:\n" + out[-2000:])
    assert ln[0].endswith("now running ReFS 3.14)") and not re.search(r"\bv\d+\.\d+", ln[0]), ln[0]


def test_t3_integrity_version_note_names_both_versions_as_refs():
    rc, out, err = _run(FOREFST, _img(UPGRADED), "integrity")
    ln = _lines(out, r"version mismatch")
    _fx(ln, "premise: no version note:\n" + out[-2000:])
    assert "version mismatch: primary ReFS 3.14, backup ReFS 3.4 —" in ln[0], ln[0]


def test_t4_details_is_moved_is_a_word():
    rc, out, err = _run(FOREFST, _img(MINI34), "details", "/System Volume Information/WPSettings.dat")
    ln = _lines(out, r"^  Is moved:")
    _fx(ln, "no Is moved line:\n" + out[-2000:])
    assert ln[0] == "  Is moved:           no", ln[0]


# ═══ T5 -- refsanalysis forms ═══════════════════════════════════════════════════════════════════════════════════

_T5 = {
    "boot -vv": [r"^Image size:   2147483648 bytes \(2 GiB\)$", r"^  container_size = 64 MiB$",
                 r"^  partition size = \d+ bytes \(\d+(\.\d)? [KMGT]iB\)$"],
    "chkp -vv": [r"^  Bytes per container\s+64 MiB$", r"^  Clusters per container\s+16384$",
                 r"^  Image size\s+2147483648 bytes \(2 GiB\)$", r"^  Indirect root list\s+(yes|no)$",
                 r"^  Root reference size\s+\d+ bytes$"],
    "supb -vv": [r"^self_block_matches\s+(yes|no)\s*$"],
    "containers": [r"^  Container size:\s+64 MiB$"],
    "bootedit repair --dry-run": [r"^  Bytes per container\s+0x40\s+(?:[0-9a-f]{2} ){8}\s+64 MiB$"],
}


@pytest.mark.parametrize("cmd", sorted(_T5))
def test_t5_refsanalysis_sizes_words_and_counts(cmd):
    rc, out, err = _run(RA, _img(MINI314), *cmd.split())
    missing = [rx for rx in _T5[cmd] if not _lines(out, rx)]
    assert not missing, (missing, out[-4000:])
    assert not _lines(out, r"\b(True|False)\s*$"), _lines(out, r"\b(True|False)\s*$")


def test_t5_chunk_size_is_a_size():
    rc, out, err = _run(RA, _img(COMPRESSED), "containers")
    ln = _lines(out, r"Chunk size:")
    _fx(ln, "premise: no chunk-size line:\n" + out[-2000:])
    assert re.fullmatch(r"\s*Chunk size:\s+\d+ (KiB|MiB|bytes)", ln[0]), ln[0]


def test_t5_schema_name_column_fits_its_longest_name():
    rc, out, err = _run(RA, _img(MINI314), "schema")
    L = out.splitlines()
    heads = [i for i, ln in enumerate(L) if ln.lstrip().startswith("TypeID")]
    _fx(len(heads) == 2, "premise: two schema tables:\n" + out[-2000:])
    # RC3b item 13 (E167): the names are the tables by era; the longest, 42 characters, is past the 40-character minimum
    _fx(any("Directory own-row table, older set (17134)" in ln for ln in L),
        "premise: no name longer than 40 characters")
    for h in heads:
        rows = []
        for ln in L[h + 2:]:
            if not ln.startswith("  0x"):
                break
            rows.append(ln)
        _fx(rows, "no rows under the header")
        assert len(L[h + 1]) == len(L[h]), (L[h], L[h + 1])                       # the rule line spans the table
        assert all(len(r) == len(L[h]) for r in rows), [r for r in rows if len(r) != len(L[h])]
