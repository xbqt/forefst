"""The labs-and-driver batch (1.14.0): the maintainer's answers of 2026-11-07 (LD/MAINTAINER_QUESTIONS_LD.md).

  Q-A  `$SI+0x24` bit 0x08 is named `DataInRecord`: the default data stream is held in the record (Q5: set by
       `RefsCreateNewFile` -> `RefsInitializeFcbStdInfo`, cleared by `RefsConvertToNonResident`, read twice; set on
       586,574 of 586,574 inline files of the corpus, on none of 263,526 others). The hex column keeps every bit.
  Q-B  an entry whose file is live and whose extent map survives (RENAMED, SAME FILE OTHER CREATION TIME, STILL
       PRESENT: not carved, WC-3) says where the map's clusters are now, from every live file's extents read once per
       run: the live file's at the same offsets, another live file's (named), in no live file's extents, or a mix
       (counted); and, for RENAMED / SAME FILE entries as for STILL PRESENT ones, whether the row is a copy of the
       current entry or an earlier version, naming the times that differ.

Written RED (xfail strict) on the dev tool before the fix (24 nodes RED, 2 controls green); the fix removed the marks.

Images: win10refs5g64k (the C4 review's 11 remnants: 8 whose map is the live file's, 3 earlier versions whose
clusters lie in other live files -- LD/C4_REVIEW.md item 2, read from the raw rows); the public sample for Q-A. The
case "in no live file's extents" has no corpus instance: planted (a synthetic volume, and the index filled by hand).
"""
import csv
import io
import os
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions)
import test_1132_red_b2_carve as C                       # noqa: E402  (remnants, translator)
import test_1132_red_b2_deleted as D                     # noqa: E402  (DirVol, rows, the runners)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

_fx = AB._fx
FOREFST = os.path.join(REPO, "forefst.py")
RA = os.path.join(REPO, "refsanalysis.py")
SAMPLE = "step5/win11refstestmftecmd.raw"
IMG64K = "step2/win10refs5g64k.raw"
SYMLINK = ("/test/elvis_dir_record_449015/elvis_dir_papa_104235/elvis_dir_sync_718743/elvis_dir_gamma_109016/"
           "elvis_dir_zulu_984398/elvis_dir_cache_558805/xbpt_symlink_gamma_582874.lnk")   # 0x28, a symlink


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _run(tool, image, *args, timeout=3600):
    r = subprocess.run([sys.executable, "-B", tool, image] + list(args), capture_output=True, text=True,
                       timeout=timeout, cwd=os.path.dirname(image))
    _fx("Traceback (most recent call last)" not in r.stderr, "the tool crashed:\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


# ═══ Q-A: bit 0x08 = DataInRecord ═════════════════════════════════════════════════════════════════════════════

def test_qa_bit_0x08_is_named_data_in_record():
    assert F._INTERNAL_FLAG_LABELS.get(0x08) == "DataInRecord", F._INTERNAL_FLAG_LABELS
    assert F.flag_cells(0x8, F._INTERNAL_FLAG_LABELS) == ("DataInRecord", "0x8")
    assert F.flag_cells(0x28, F._INTERNAL_FLAG_LABELS) == ("DataInRecord|RedirectionTrust", "0x28")
    assert F.internal_flags_str(0x8) == "0x8 (DataInRecord)"
    assert F.internal_flags_str(0x28) == "0x28 (DataInRecord|RedirectionTrust)"


def test_qa_control_a_bit_with_no_name_stays_hex():
    """Q-B = B1 (2026-10-30) is kept: a bit with no name is printed as its hex (0x04 has no driver reading)."""
    assert 0x04 not in F._INTERNAL_FLAG_LABELS and 0x10 not in F._INTERNAL_FLAG_LABELS
    assert F.flag_cells(0x4, F._INTERNAL_FLAG_LABELS) == ("0x4", "0x4")
    assert F.internal_flags_str(0x4) == "0x4"
    assert F.internal_flags_str(0) == "0x0 (none set)" and F.internal_flags_str(None) == ""


@pytest.fixture(scope="module")
def sample_files():
    rc, out, err = _run(FOREFST, _img(SAMPLE), "files", "--csv")
    _fx(rc == 0, "files --csv on the sample exits %d:\n%s" % (rc, err[-2000:]))
    return list(csv.DictReader(io.StringIO(out)))


def test_qa_sample_every_row_with_bit_0x08_names_it_and_holds_its_data_inline(sample_files):
    """The name follows the bit, and the bit follows the data on the sample (the Q5 census: no exception corpus-wide):
    every file row whose word has bit 0x08 is `DataInRecord` and inline; every inline file row with a word read has
    the bit."""
    rows = [r for r in sample_files if r["InternalFlagsHex"]]
    _fx(rows, "no row with an internal-flags word on the sample")
    bit = [r for r in rows if int(r["InternalFlagsHex"], 16) & 0x8]
    _fx(len(bit) > 41, "fewer rows with bit 0x08 than the 41 that hold it alone (K14 census): %d" % len(bit))
    unnamed = [r for r in bit if "DataInRecord" not in r["InternalFlags"].split("|")]
    assert not unnamed, [(r["FullPath"], r["InternalFlags"]) for r in unnamed[:5]]
    alone = [r for r in bit if r["InternalFlagsHex"] == "0x8"]
    assert len(alone) == 41 and all(r["InternalFlags"] == "DataInRecord" for r in alone), len(alone)
    assert all(r["DataResidency"] == "inline" for r in bit), [r["FullPath"] for r in bit
                                                              if r["DataResidency"] != "inline"][:5]
    files_inline = [r for r in rows if r["DataResidency"] == "inline" and r["IsDirectory"] in ("False", "false")]
    assert all(int(r["InternalFlagsHex"], 16) & 0x8 for r in files_inline), [
        r["FullPath"] for r in files_inline if not int(r["InternalFlagsHex"], 16) & 0x8][:5]


def test_qa_details_and_refsanalysis_attributes_name_it():
    img = _img(SAMPLE)
    rc, out, err = _run(FOREFST, img, "details", SYMLINK)
    assert rc == 0 and "Internal flags:     0x28 (DataInRecord|RedirectionTrust)" in out, out[-2000:]
    rc, out, err = _run(RA, img, "attributes", SYMLINK)
    assert "IntFlags:    0x28 (DataInRecord|RedirectionTrust)" in out, (rc, out[-2000:], err[-800:])


# ═══ Q-B: where a live file's earlier map's clusters are now ═════════════════════════════════════════════════

_BASE = "metadata + extent map, not carved: the same file is live (`extract` gives its current content); "
_SAME = "this map's clusters are the live file's, at the same offsets"
_NOT_CHECKED = "where this map's clusters are now was not checked"
_OLD = "may hold that content now"


def _live_entry(status=None, ref="0x761:0x5"):
    """A RENAMED entry whose 0x1000 holder maps 3 written clusters at PLCN 10-12 (VLCN V(10)), file VCN 0-2."""
    hv = C.holder_value(3 * C.CS, 3 * C.CS, [C.ext_row(C.V(10), 0, 3)])
    vd = C.long_row([(C.key80(0x1000), hv)], size=3 * C.CS, alloc=3 * C.CS)
    return C.entry("a.bin", vd, status=status or F._ST_RENAMED, identity_ref=ref, live_refs=[ref])


def _index(*runs):
    """A live-cluster index filled by hand: runs (plcn, clusters, object_ref, path, file_vcn)."""
    assert hasattr(F, "_LiveClusterIndex"), "no _LiveClusterIndex"
    ix = F._LiveClusterIndex()
    for plcn, n, ref, path, fvcn in runs:
        ix.add(plcn, n, ref, path, fvcn)
    return ix


def _label(e, ix):
    assert hasattr(F, "_live_map_check"), "no _live_map_check"
    e["_live_map"] = F._live_map_check(e, ix, C.CS, C._tr())
    kind, label, _d = F._deleted_recoverability(e, C.CS, C._tr())
    assert kind == "live_file_map", (kind, label)
    return label


def test_qb_planted_the_live_file_s_own_clusters_at_the_same_offsets():
    e = _live_entry()
    assert _label(e, _index((10, 3, "0x761:0x5", "d/a2.bin", 0))) == _BASE + _SAME


def test_qb_planted_the_live_file_s_clusters_at_other_offsets():
    e = _live_entry()
    assert _label(e, _index((10, 3, "0x761:0x5", "d/a2.bin", 7))) == _BASE + (
        "this map's clusters are the live file's, at other offsets")


def test_qb_planted_another_live_file_s_clusters_are_named():
    e = _live_entry()
    assert _label(e, _index((8, 6, "0x770:0x2", "big/report.tmp", 0))) == _BASE + (
        "this map's clusters now lie in the extents of big/report.tmp")
    e = _live_entry()
    assert _label(e, _index((10, 1, "0x770:0x2", "big/report.tmp", 0), (11, 2, "0x771:0x3", "other.bin", 4))) == \
        _BASE + "this map's clusters now lie in the extents of other.bin and big/report.tmp"


def test_qb_planted_no_live_file_holds_the_clusters():
    """The case with no corpus instance (Q-C's: an earlier version whose clusters were freed and not reused): said,
    and still not carved (Q-C option 1 for 1.14.0)."""
    e = _live_entry()
    assert _label(e, _index((40, 2, "0x770:0x2", "big/report.tmp", 0))) == _BASE + (
        "none of this map's 3 clusters lies in a live file's extents now (stream snapshots and metadata pages are not "
        "checked): they may still hold this version's bytes")


def test_qb_planted_a_mix_is_counted():
    e = _live_entry()
    assert _label(e, _index((10, 1, "0x761:0x5", "d/a2.bin", 0), (11, 1, "0x770:0x2", "big/report.tmp", 0))) == \
        _BASE + ("of this map's 3 clusters, 1 is the live file's at the same offset, 1 lies in the extents of "
                 "big/report.tmp, 1 lies in no live file's extents (stream snapshots and metadata pages are not "
                 "checked)")


def test_qb_planted_a_refused_map_gives_the_plan_s_reason_not_a_placement():
    hv = C.holder_value(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(10), 0, 2, C.NW)])
    vd = C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS)
    e = C.entry("u.bin", vd, status=F._ST_RENAMED, identity_ref="0x761:0x5", live_refs=["0x761:0x5"])
    plan = F._entry_carve_plan(e, C.CS, C._tr())
    _fx(plan and plan["refuse"], "the planted map is not refused: %r" % (plan,))
    assert _label(e, _index((10, 2, "0x770:0x2", "big/report.tmp", 0))) == _BASE + (
        "this map makes no carve either: " + plan["refuse"])


def test_qb_planted_an_entry_not_checked_says_so():
    e = _live_entry()
    kind, label, _d = F._deleted_recoverability(e, C.CS, C._tr())
    assert kind == "live_file_map" and label == _BASE + _NOT_CHECKED and _OLD not in label, label


def test_qb_control_a_deleted_entry_s_map_is_still_carved():
    """WC-3 is about live files only: a DELETED entry with the same map is graded for a carve, whatever the index."""
    e = _live_entry(status=F._ST_DELETED)
    kind, _label_, _d = F._deleted_recoverability(e, C.CS, C._tr())
    assert kind == "extent_backed", kind


def test_qb_dates_against_the_live_file_name_the_times_that_differ():
    assert hasattr(F, "_dates_against") and hasattr(F, "_dates_words"), "no _dates_against / _dates_words"
    t = (1, 2, 3, 4)
    assert F._dates_against(t, [t]) == ("same", ())
    assert F._dates_against(t, [(1, 2, 9, 4)]) == ("differ", ("Changed",))
    assert F._dates_against(t, [(1, 7, 9, 4), (1, 2, 9, 4)]) == ("differ", ("Changed",))    # the closest live row
    assert F._dates_words({"dates": "same"}) == "copy of the current entry (same dates)"
    assert F._dates_words({"dates": "differ", "dates_differ": ("Modified", "Changed")}) == \
        "earlier version (dates differ: Modified, Changed)"


def test_qb_synthetic_volume_no_live_file_holds_the_clusters(tmp_path):
    """End to end on a synthetic volume: /d holds a.bin live (a split row whose backing is not on the volume: its
    extents are not decoded) and, in its page's free space, a copy with the same name and creation time whose holder
    maps 3 clusters at PLCN 0x40-0x42 (below the first container: physical) -- STILL PRESENT; no live file's extents
    hold them, and the live stream whose extents were not decoded is said: the view and the CSV say so."""
    import test_1132_d2_carve_extract as X
    hv = C.holder_value(3 * C.CS, 3 * C.CS, [C.ext_row(0x40, 0, 3, C.W)])
    old = C.long_row([(C.key80(0x1000), hv)], size=3 * C.CS, alloc=3 * C.CS)
    path = X._vol(tmp_path, {0x600: {"name": ""},
                             0x761: {"parent": 0x600, "name": "d",
                                     "files": [D._row(D._name_key("a.bin"), D._file_value(5, 0x761, C.FT))],
                                     "slack": [D._row(D._name_key("a.bin"), old)]}})
    rc, out, err = D._syn(path, "deleted", "-v")           # group 2: the verdict in full is under -v
    line = [ln for ln in out.splitlines() if ln.strip().startswith("a.bin")]
    _fx(line, "a.bin is not listed" + D._ctx(rc, out, err))
    want = ("none of this map's 3 clusters lies in a live file's extents now (stream snapshots and metadata pages are "
            "not checked; the extents of 1 live stream were not decoded): they may still hold this version's bytes")
    assert want in line[0] and "copy of the current entry (same dates)" in line[0], line[0]
    rc, out, err, rows = D._syn_csv(path, "deleted")
    r = [x for x in rows if x["FileName"] == "a.bin"]
    assert r and r[0]["Recoverability"].endswith(want) and r[0]["Dates"] == "same", r


# ─── the image: win10refs5g64k ─────────────────────────────────────────────────────────────────────────────────

_SAME_MAP = ("xbpt_beta_audit_333607.json", "xbpt_oscar_data_366966.json", "xbpt_papa_archive_211574.json",
             "xbpt_uniform_november_873087.json", "xbpt_cache_hotel_141725.bak", "xbpt_config_output_842495.md",
             "xbpt_foxtrot_romeo_979913.json", "xbpt_zulu_whiskey_391283.tmp")
_INDIA = "test/elvis_dir_record_449015/elvis_dir_lima_252141/elvis_dir_oscar_306778/xbpt_large_86mb_india_568540.txt"
_OTHER_FILE = {"xbpt_archive_sync_589134.csv": _INDIA, "xbpt_quebec_sierra_693317.csv": _INDIA,
               "xbpt_echo_whiskey_534063.tmp": "test/xbpt_large_99mb_report_414178.tmp"}


@pytest.fixture(scope="module")
def view64k():
    rc, out, err = _run(FOREFST, _img(IMG64K), "deleted", "-v")      # group 2: the blocks are under -v
    _fx(rc == 0, "deleted on win10refs5g64k exits %d:\n%s" % (rc, err[-2000:]))
    return out


@pytest.fixture(scope="module")
def csv64k():
    rc, out, err = _run(FOREFST, _img(IMG64K), "deleted", "--csv", "-")
    _fx(rc == 0, "deleted --csv - on win10refs5g64k exits %d:\n%s" % (rc, err[-2000:]))
    return list(csv.DictReader(io.StringIO(out)))


def _block(out, name):
    lines = out.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("    FILE %s  (" % name):
            j = i + 1
            while j < len(lines) and lines[j].startswith("      "):
                j += 1
            return lines[i:j]
    _fx(False, "no entry %s in the view" % name)


def _field(blk, key):
    got = [ln.split(key, 1)[1].strip() for ln in blk if ln.strip().startswith(key)]
    return got[0] if got else None


@pytest.mark.parametrize("name", _SAME_MAP)
def test_qb_image_the_8_copies_share_the_live_file_s_clusters(view64k, name):
    blk = _block(view64k, name)
    assert _field(blk, "Recoverable:") == _BASE + _SAME, blk
    # the four times: Created, Modified and Accessed are the live record's, Changed is not (read from the rows)
    assert _field(blk, "Version:") == "earlier version (dates differ: Changed)", blk


@pytest.mark.parametrize("name", sorted(_OTHER_FILE))
def test_qb_image_the_3_earlier_versions_name_the_file_that_holds_their_clusters(view64k, name):
    blk = _block(view64k, name)
    assert _field(blk, "Recoverable:") == _BASE + "this map's clusters now lie in the extents of " + _OTHER_FILE[name], blk
    assert _field(blk, "Version:") == "earlier version (dates differ: Modified, Changed)", blk


def test_qb_image_every_live_file_map_says_where_its_clusters_are(view64k, csv64k):
    """No entry keeps the old sentence, none is 'not checked'; the CSV says what the view says."""
    assert _OLD not in view64k
    rec = [ln.split("Recoverable:", 1)[1].strip() for ln in view64k.splitlines() if "Recoverable: " + _BASE[:40] in ln]
    _fx(len(rec) >= 104, "fewer live-file maps than the 104 counted before the change: %d" % len(rec))
    assert all(r.startswith(_BASE) and not r.endswith(_NOT_CHECKED) for r in rec), [r for r in rec
                                                                                   if not r.startswith(_BASE)][:3]
    rows = {r["FileName"]: r for r in csv64k}
    for name in _SAME_MAP + tuple(_OTHER_FILE):
        assert rows[name]["Recoverability"] == _field(_block(view64k, name), "Recoverable:"), name
        assert rows[name]["Dates"] == "differ" and rows[name]["DatesDiffer"], rows[name]


def test_qb_help_lists_the_csv_columns_the_view_writes():
    """`help deleted` names the --csv columns: exactly DELETED_CSV_COLUMNS, in order (it lacked FileAttributesHex
    before this batch, and a column added without its help line is the defect this node catches)."""
    import json
    import re
    text = json.dumps(F.CMD_HELP["deleted"])
    m = re.search(r"columns (FileName, .*?); composes", text)
    _fx(m, "no column list in `help deleted`")
    named = [re.sub(r" \(.*\)$", "", c) for c in m.group(1).split(", ")]        # "RecoverySource (where ...)"
    assert named == list(F.DELETED_CSV_COLUMNS), (named, F.DELETED_CSV_COLUMNS)
