"""E2c (1.14.0): the MLog words (decision 49 point 6; the inventory's directions) -- on E2a's three volumes, from E2a's
runs (one run per volume per session).

  P8-1   `mlog --csv` and `--json` name the class DerivedAction; every value is a class `mlog --info` lists
         (MLOG_FILE_OPS + MLOG_LOW_LEVEL); no row carries a retired name (REPARENT, WRITE: they named what the records
         do not show -- REPARENT rows had no move in the workload log 162 times of 195, WRITE rows no write 119 of 158).
  P8-2   the derived mark: `mlog --parse`'s legend says the class is derived from the opcode pattern; every MLog event
         of `timeline` (text, CSV, JSON) ends in "(derived)" or "(derived) [MLog time unreliable]".
  P8-3   the help and `mlog --info` describe TABLE_REPARENTED and DATA_OR_REPARSE_WRITE by the records they show.
  P9-1   TimeSource: a dated MLog row carries one of the two sources, an undated row none (mlog CSV / JSON; timeline
         CSV / JSON, whose USN and $SI rows name theirs).
  P10-1  the path is the live tree's TODAY: PathToday / ParentPathToday (mlog), PathToday beside the source's Name
         (timeline), and the texts say so.
  N189-1 the parse legend and the timeline caveat say a row's time is the LATEST FILETIME of its log payload, which
         can merge up to 15 transactions.
"""
import csv
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_e2a_forms as E2A                        # noqa: E402  (the runner and its cache)

F = E2A.F
CLASSES = set(F.MLOG_FILE_OPS) | set(F.MLOG_LOW_LEVEL)
SOURCES_MLOG = {"latest FILETIME of the log payload", "paired $SI update"}
SOURCES_TIMELINE = SOURCES_MLOG | {"USN record", "$SI field"}


@pytest.fixture(scope="module", params=E2A._IMAGES, ids=lambda n: os.path.basename(n).split(".")[0])
def outs(request, tmp_path_factory):
    return E2A._outputs(request.param, tmp_path_factory)


def _csv(text):
    return list(csv.DictReader(io.StringIO(text)))


def _get(outs, fid):
    if fid not in outs:
        pytest.skip("%s not run on this volume" % fid)
    return outs[fid]


def _mlog_rows(outs):
    rc, out, _err = _get(outs, "mlog-csv")
    rows = _csv(out)
    rcj, outj, _e = _get(outs, "mlog-json")
    doc = json.loads(outj)
    jrows = doc.get("Transactions") or []
    return rows, jrows


def test_p8_1_the_class_is_derived_action_and_a_listed_class(outs):
    rows, jrows = _mlog_rows(outs)
    if not rows:
        pytest.skip("no MLog row on this volume")
    assert list(rows[0])[:4] == ["Seq", "Timestamp", "TimeSource", "DerivedAction"], list(rows[0])
    for r in rows + jrows:
        assert "Action" not in r and "action" not in r, sorted(r)
        assert r["DerivedAction"] in CLASSES, r["DerivedAction"]
        assert r["DerivedAction"] not in ("REPARENT", "WRITE")
    assert len(rows) == len(jrows)


def test_p8_2_the_derived_mark(outs):
    _rc, out, _err = _get(outs, "mlog-parse")
    if "No log payloads found" not in out and "Log payloads:" in out:
        # group 1b (review 13): the class reads the records' keys and values too, not only the opcodes
        assert re.search(r"\[CLASS\] is DERIVED from the records", out), out[:2000]
    _rc, tl, _e = _get(outs, "timeline-csv")
    ev = [r["Event"] for r in _csv(tl) if r["Source"] == "MLog"]
    _rc, tj, _e = _get(outs, "timeline-json")
    ev += [e["Event"] for e in json.loads(tj)["Events"] if e["Source"] == "MLog"]
    bad = [e for e in ev if not re.search(r" \(derived\)( \[MLog time unreliable\])?$", e)]
    assert not bad, bad[:5]


def test_p8_3_the_two_classes_are_described_by_their_records(outs):
    _rc, info, _e = _get(outs, "mlog-info")
    for cls, words in (("TABLE_REPARENTED", "RedoReparentTable"), ("DATA_OR_REPARSE_WRITE", "SetObjectRecord")):
        m = re.search(r"(?ms)^  %s\s+(.*?)\n  [A-Z_]{3,}\s" % cls, info)
        assert m and words in m.group(1) and "the records do not" in m.group(1), (cls, m and m.group(1))
    for old in ("REPARENT ", "WRITE "):
        assert not re.search(r"(?m)^  %s" % old, info), old


def test_p9_1_time_source(outs):
    rows, jrows = _mlog_rows(outs)
    for r in rows + jrows:
        if r["Timestamp"]:
            assert r["TimeSource"] in SOURCES_MLOG, r
        else:
            assert r["TimeSource"] in ("", None), r
    _rc, tl, _e = _get(outs, "timeline-csv")
    _rc, tj, _e = _get(outs, "timeline-json")
    trows = _csv(tl) + json.loads(tj)["Events"]
    for r in trows:
        if r["Timestamp"]:
            assert r["TimeSource"] in SOURCES_TIMELINE, r
            if r["Source"] == "MLog":
                assert r["TimeSource"] in SOURCES_MLOG, r
        else:
            assert r["TimeSource"] in ("", None), r


def test_p10_1_the_path_is_today(outs):
    rows, jrows = _mlog_rows(outs)
    for r in rows[:1] + jrows[:1]:
        assert {"PathToday", "ParentPathToday"} <= set(r) and "Path" not in r and "FullPath" not in r, sorted(r)
    _rc, tl, _e = _get(outs, "timeline-csv")
    hdr = next(csv.reader(io.StringIO(tl)), [])
    assert "PathToday" in hdr and "Name" in hdr and "FullPath" not in hdr, hdr
    _rc, txt, _e = _get(outs, "timeline")
    if "MLog" in txt:
        assert re.search(r"(?i)path today|PathToday", txt), txt[:1500]


def test_n189_1_the_time_is_the_payloads_latest(outs):
    _rc, out, _err = _get(outs, "mlog-parse")
    if "Log payloads:" in out:
        # N646 (RC3b item 1): the latest time the records carry, read where each value's form keeps its times; a payload
        # merges up to 15 redo blocks (E97), not transactions
        assert "A row's time is the latest time its log payload's records carry" in out
        assert "merge up to 15 redo blocks" in out
    _rc, txt, _e = _get(outs, "timeline")
    if "MLog" in txt:
        assert re.search(r"the latest time its log payload's records carry \(a payload can merge up to 15 redo",
                         txt), txt[:2000]


def test_mlog_time_source_unit():
    assert F.mlog_time_source({"ts_str": ""}) == ""
    assert F.mlog_time_source({"ts_str": "2026-05-16T16:55:20.9805996Z"}) == "latest FILETIME of the log payload"
    assert F.mlog_time_source({"ts_str": "2026-05-16T16:55:20.9805996Z", "ts_paired": True}) == "paired $SI update"


def test_q_c_file_selects_a_files_mlog_events(tmp_path):
    """Q-C: `timeline --file NAME --source MLOG` keeps the MLog rows whose path today contains NAME -- each of them, and
    no other (the help says so); on the public sample, a file `mlog --csv` names."""
    img = E2A._corpus_image("win11refstestmftecmd.raw")
    if img is None:
        pytest.skip("no corpus")
    rc, out, err = E2A._run(E2A._F, img, ["mlog", "--csv"], str(tmp_path))
    names = [r for r in _csv(out) if r["Name"].startswith("xbpt_") and r["Timestamp"]]
    assert names, err[-500:]
    nm = names[0]["Name"]
    lo = nm.lower()                                      # --file matches without case
    want = {(r["Name"], r["PathToday"]) for r in _csv(out) if lo in (r["PathToday"] or r["Name"]).lower() and r["Timestamp"]}
    rc, tl, err = E2A._run(E2A._F, img, ["timeline", "--csv", "--source", "MLOG", "--file", nm], str(tmp_path))
    got = {(r["Name"], r["PathToday"]) for r in _csv(tl)}
    assert got and got <= want and all(lo in p.lower() for _n, p in got), (sorted(got)[:5], sorted(want)[:5])
