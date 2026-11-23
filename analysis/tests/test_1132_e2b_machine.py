"""Wave E step E2b (1.14.0, `analysis/reports/v1.13.2/fixes/E2b_NOTES.md`): the machine outputs -- one vocabulary in
PascalCase (decision 38, K21), `files --json` = the CSV (O7 / N168, decision 37: IsResident removed), and the OC items
(one test group each, a control each).

The outputs are E2a's: `test_1132_e2a_forms._FORMS` run once per volume (the module cache is shared), so these tests
cost no second run of the tools.
"""
import csv
import io
import json
import os
import re
import subprocess
import sys

import pytest

import test_1132_e2a_forms as E2A                        # the forms, the runner, the walkers (E2a's)

F = E2A.F


@pytest.fixture(scope="module", params=E2A._IMAGES, ids=lambda n: os.path.basename(n).split(".")[0])
def outs(request, tmp_path_factory):
    """E2a's outputs of the volume (one run per volume per session: E2a's module cache)."""
    return E2A._outputs(request.param, tmp_path_factory)

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# K21 -- every JSON key and every CSV header in PascalCase; one name per fact
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

_PASCAL = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_MIXED_ACRONYM = re.compile(r"(?:Plcn|Vlcn|Oid|Uuid|Lsn|Lcn|Vcn|Guid|Crc|Vbr|Supb|Chkp|Usn(?!Journal))(?![a-z])")
_PRODUCT_CASE = re.compile(r"^Refs(?=[A-Z0-9]|$)|Mlog(?![a-z])")
# maps keyed by DATA (a residency word, a root-table name, an attribute type, a special-type or tag name, a page
# type): their keys are values, written as the values are written elsewhere -- not field names
_DATA_MAPS = {"Residency", "RootTableRows", "Counts", "NameCounts", "Attributes", "PageTypes", "ByTag", "Tiers",
              "ZeroFilledClusters", "Opcodes", "Actions", "Classes", "ByReason", "Reasons", "ByType",
              "SourceCounts"}     # E2c: timeline's counts keyed by the Source column's values (USN, MLog, $SI)


def _keys_outside_data_maps(o, parent=None, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            data = parent in _DATA_MAPS
            if not data:
                yield path + "/" + str(k), str(k)
            yield from _keys_outside_data_maps(v, None if data else str(k), path + "/" + str(k))
    elif isinstance(o, list):
        for v in o:
            yield from _keys_outside_data_maps(v, parent, path + "[]")


def _json_key_names(outs):
    for fid, (rc, out, err) in outs.items():
        if E2A._is_json_form(fid):
            for doc in E2A._json_docs(out):
                for p, k in _keys_outside_data_maps(doc):
                    yield fid, p, k


def test_k21_control_the_rules():
    assert _PASCAL.match("ObjectRef") and not _PASCAL.match("object_ref") and not _PASCAL.match("full path")
    assert _MIXED_ACRONYM.search("CheckpointLcn") and not _MIXED_ACRONYM.search("CheckpointLCN")
    assert _PRODUCT_CASE.search("RefsVersion") and not _PRODUCT_CASE.search("ReFSVersion")
    assert not _MIXED_ACRONYM.search("UsnJournalId".replace("Usn", "USN"))


def test_k21_every_json_key_is_pascalcase(outs):
    bad = sorted({"%s %s" % (fid, re.sub(r"\[\]", "", p)) for fid, p, k in _json_key_names(outs)
                  if not _PASCAL.match(k) and not re.fullmatch(r"0x[0-9a-f]+", k)})
    assert not bad, "%d JSON keys not in PascalCase:\n  " % len(bad) + "\n  ".join(bad[:25])


def test_k21_acronyms_and_product_names_keep_their_case(outs):
    bad = sorted({"%s %s" % (fid, k) for fid, p, k in _json_key_names(outs)
                  if _MIXED_ACRONYM.search(k) or _PRODUCT_CASE.search(k)})
    assert not bad, "keys with Lcn/Oid/Usn/... or Refs/Mlog: %r" % bad[:20]


def test_k21_every_csv_header_is_pascalcase(outs):
    bad = sorted({"%s %s" % (fid, h) for fid, rows in E2A._csv_tables(outs) for h in rows[0] if not _PASCAL.match(h)})
    assert not bad, "CSV headers not in PascalCase:\n  " + "\n  ".join(bad[:25])


# one name per fact (the `files` vocabulary): names that the release retires in every output
_RETIRED_NAMES = {"Path": "FullPath", "IsDir": "IsDirectory", "FileRef": "ObjectRef", "Id": "ObjectRef",
                  "Filename": "FileName", "FileAttrs": "FileAttributes", "CreateTime": "Created",
                  "ModifyTime": "Modified", "ChangeTime": "Changed", "AccessTime": "Accessed", "Oid": "OID",
                  "RefsVersion": "ReFSVersion", "IsResident": "(removed, decision 37)"}


def test_k21_one_name_per_fact(outs):
    names = {k for fid, p, k in _json_key_names(outs)} | {h for fid, rows in E2A._csv_tables(outs) for h in rows[0]}
    bad = sorted("%s (use %s)" % (n, _RETIRED_NAMES[n]) for n in names if n in _RETIRED_NAMES)
    assert not bad, "a fact under a name other than the `files` one: %r" % bad


def test_k21_a_full_path_is_under_fullpath(outs):
    """A value that is a path of the volume (it contains '/' and no space-separated prose) sits under FullPath,
    ParentPath, CreationDir, LiveFile, OriginalPath (a Windows path), or a key ending in Path / Paths."""
    ok = re.compile(r"(FullPath|ParentPath|CreationDir|LiveFile|OriginalPath|RecoveredFrom|Paths?|PathToday|Location|"
                    r"Target|ContentFile|RowFile|File|SourcePath|Image|Note|Reason|Why|Statement|Text|"
                    r"Basis)$")                          # timestomp's Basis is a word pair (`journal/link`), not a path
    bad = set()
    for fid, (rc, out, err) in outs.items():
        if not E2A._is_json_form(fid):
            continue
        for doc in E2A._json_docs(out):
            for p, k, v in E2A._jwalk(doc):
                if isinstance(v, str) and "/" in v and " " not in v and not v.startswith("0x") \
                        and not ok.search(k) and _PASCAL.match(k):
                    bad.add("%s %s=%r" % (fid, k, v[:60]))
    assert not bad, "a path under a key that does not say path: %r" % sorted(bad)[:12]


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# O7 / N168 -- `files --json` carries the CSV's fields, names and values; IsResident is gone (decision 37)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return F.csv_list_cell(v)
    return str(v)


@pytest.mark.parametrize("form", ["files-json", "files-jsonl"])
def test_o7_files_json_is_the_csv(outs, form):
    rows = list(csv.DictReader(io.StringIO(outs["files-csv"][1])))
    docs = E2A._json_docs(outs[form][1])
    recs = docs[0] if form == "files-json" else docs
    assert rows and len(recs) == len(rows), "%d JSON records, %d CSV rows" % (len(recs), len(rows))
    hdr = list(rows[0].keys())
    assert list(recs[0].keys()) == hdr, "the JSON keys are not the CSV's columns in order:\n %r\n %r" % (
        list(recs[0].keys())[:12], hdr[:12])
    bad = []
    for r, j in zip(rows, recs):
        for c in hdr:
            if _cell(j.get(c)) != r[c]:
                bad.append("%s %s: csv %r json %r" % (r["ObjectRef"], c, r[c][:40], j.get(c)))
                break
        if len(bad) >= 8:
            break
    assert not bad, "JSON values that differ from the CSV's:\n  " + "\n  ".join(bad)


def test_o7_isresident_is_gone(outs):
    names = {k for fid, p, k in _json_key_names(outs)} | {h for fid, rows in E2A._csv_tables(outs) for h in rows[0]}
    assert not ({"IsResident", "is_resident"} & names), "IsResident is still written"
    assert len(next(rows for fid, rows in E2A._csv_tables(outs) if fid == "files-csv")[0]) in (39, 42), \
        "the files CSV has neither 39 columns nor 42 (Q-A's three hex columns)"


def test_o7_filter_resident_is_refused(tmp_path):
    img = E2A._corpus_image("step1/win10refsmini.raw")
    if img is None:
        pytest.skip("no corpus")
    rc, out, err = E2A._run(E2A._F, img, ["files", "--filter", "resident"], str(tmp_path))
    assert rc == 1 and "resident" in err and not out.strip(), (rc, out[:200], err[-400:])


def test_o7_control_filter_inline_still_filters(tmp_path):
    img = E2A._corpus_image("step1/win10refsmini.raw")
    if img is None:
        pytest.skip("no corpus")
    rc, out, err = E2A._run(E2A._F, img, ["files", "--filter", "directory", "--csv"], str(tmp_path))
    assert rc in (0, 2) and out.startswith("ObjectRef,"), (rc, err[-300:])


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N302 search, N303 details, N292 specials / ads
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

_SEARCH_COLUMNS = ["ObjectRef", "FullPath", "FileName", "IsDirectory", "FileSize", "DataResidency", "Created",
                   "Modified", "ParentOID"]


def _csv_rows(outs, fid):
    return list(csv.DictReader(io.StringIO(outs[fid][1])))


def test_n302_search_has_one_column_list_in_every_format(outs):
    rows = _csv_rows(outs, "search-csv")
    assert rows and list(rows[0].keys()) == _SEARCH_COLUMNS, list(rows[0].keys()) if rows else "no rows"
    for fid in ("search-json", "search-jsonl"):
        docs = E2A._json_docs(outs[fid][1])
        recs = docs[0] if fid == "search-json" else docs
        assert recs and list(recs[0].keys()) == _SEARCH_COLUMNS, (fid, list(recs[0].keys()))
        assert len(recs) == len(rows), (fid, len(recs), len(rows))


def test_n302_search_directory_rows_are_files_rows(outs):
    rows = [r for r in _csv_rows(outs, "search-csv") if r["IsDirectory"] == "true"]
    assert rows, "no directory matched 'a'"
    assert all(re.fullmatch(r"0x[0-9a-f]+:0x0", r["ObjectRef"]) and r["DataResidency"] == "" for r in rows), rows[:3]


def test_n302_search_screen_prints_bytes_and_the_full_time(outs):
    out = outs["search"][1]
    assert not re.search(r"\d (KiB|MiB|KB|MB)\b", out), "a size in units on the search screen"
    assert E2A._NEW_TIME.search(out), "no full time on the search screen"


def test_n303_details_file_json_is_the_files_record_first(outs):
    rec = E2A._json_docs(outs["details-file-json"][1])[0]
    hdr = list(csv.DictReader(io.StringIO(outs["files-csv"][1])).fieldnames)
    assert list(rec.keys())[:len(hdr)] == hdr, list(rec.keys())[:8]


def test_n303_details_directory_json_leads_with_its_identity(outs):
    rec = E2A._json_docs(outs["details-dir-json"][1])[0]
    assert re.fullmatch(r"0x[0-9a-f]+:0x0", rec.get("ObjectRef") or "") and rec.get("FullPath") \
        and rec.get("IsDirectory") is True and "Structure" in rec, list(rec.keys())


def test_n303_details_jsonl_is_the_files_row(outs):
    rec = E2A._json_docs(outs["details-file-jsonl"][1])[0]
    hdr = list(csv.DictReader(io.StringIO(outs["files-csv"][1])).fieldnames)
    assert list(rec.keys()) == hdr, list(rec.keys())[:8]


_SPECIALS_COLUMNS = ["Type", "ObjectRef", "FullPath", "IsDirectory", "Stream", "StreamSize", "DataResidency",
                     "ReparseTag", "ReparseTagHex", "ReparseTarget", "HardLinkCount", "HardLinkNames", "FileSize",
                     "AllocatedSize", "SnapshotCount"]     # acceptance 1.14.0 (Q-A A1): the tag's hex beside its name


def test_n292_specials_without_a_type_gives_counts_in_every_format(outs):
    rows = _csv_rows(outs, "specials-csv")
    assert rows and list(rows[0].keys()) == ["Type", "Objects", "Names"], rows[:2]
    doc = E2A._json_docs(outs["specials-json"][1])[0]
    assert isinstance(doc, list) and {r["Type"] for r in doc} == {r["Type"] for r in rows}, str(doc)[:300]


def test_n292_ads_rows_carry_identity_stream_size_and_residency(outs):
    rows = _csv_rows(outs, "ads-csv")
    if not rows:
        pytest.skip("no named stream on this volume")
    assert list(rows[0].keys()) == _SPECIALS_COLUMNS, list(rows[0].keys())
    bad = [r for r in rows if not (r["ObjectRef"] and r["Stream"] and r["StreamSize"].isdigit() and r["DataResidency"])]
    assert not bad, bad[:3]
    recs = E2A._json_docs(outs["ads-json"][1])[0]
    assert len(recs) == len(rows) and isinstance(recs[0]["StreamSize"], int), (len(recs), recs[:1])


def test_n292_the_text_rows_lead_with_the_objectref(outs):
    out = outs["specials-ads"][1]
    if "OBJECTREF" not in out and "(none)" in out:
        pytest.skip("no named stream")
    assert re.search(r"^  0x[0-9a-f]+:0x[0-9a-f]+ ", out, re.M), out[:600]


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N245, N250, N305, N306 -- the volume commands' JSON
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _doc(outs, fid):
    return E2A._json_docs(outs[fid][1])[0]


@pytest.mark.parametrize("fid", ["summary-json", "fastsummary-json", "ra-summarypp-json"])
def test_n245_the_mapped_container_count_is_not_usage(outs, fid):
    d = _doc(outs, fid)
    assert not ({"ContainersUsed", "ContainersFree", "UtilizationPercent"} & set(d)), sorted(set(d))[:40]
    cap = d.get("Capacity") or {}
    assert "UsedPercent" in cap and "FreeBytes" not in cap and "Free" not in cap, cap


def test_n250_integrity_has_one_findings_list(outs):
    d = _doc(outs, "integrity-json")
    assert "RedundancyFindings" in d and "Redundancy" not in d, sorted(d)
    assert "BootstrapBackups" in d and "RedundancyNotes" in d, sorted(d)


def test_n305_integrity_and_summary_name_a_fact_once(outs):
    i, s = _doc(outs, "integrity-json"), _doc(outs, "summary-json")
    for k in ("Checksum", "ContainersMapped", "CheckpointVirtualClock", "ClusterSize", "ReFSVersion"):
        assert k in i and k in s, (k, k in i, k in s)
    assert "ChecksumType" not in i and "ContainerMapEntries" not in i
    assert "CheckpointLCN" not in s and s["BootstrapBackups"]["CheckpointUsedLCN"], "the copy in use's LCN twice"
    # acceptance 1.14.0 E2 close (review S3, K14 A): the decode is the names field, the word beside it; no list twice
    assert "CheckpointFlagNames" not in s and re.fullmatch(r"0x[0-9a-f]+", s.get("CheckpointFlagsHex") or ""), s
    assert s["CheckpointFlags"] == (F.flag_names(int(s["CheckpointFlagsHex"], 16), F._CHKP_FLAG_BITS) or "0x0") \
        and not s["CheckpointFlags"].startswith("0x"), "the flag decode is text-only"


def test_n306_refsanalysis_summary_states_forefst_summarys_facts(outs):
    fs, ra = _doc(outs, "summary-json"), _doc(outs, "ra-summarypp-json")
    missing = sorted(set(fs) - set(ra) - {"Tool"})
    assert not missing, "facts forefst summary states that refsanalysis summary does not: %r" % missing
    differ = sorted(k for k in set(fs) & set(ra) if fs[k] != ra[k] and k not in ("Tool", "SummaryMode"))
    assert not differ, "the two summaries differ on %r" % differ[:10]


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N258, N308 / N309, N312 -- usn and timeline
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n308_usn_csv_and_json_carry_one_record(outs):
    rows = _csv_rows(outs, "usn-csv")
    doc = _doc(outs, "usn-json")
    recs = doc["Records"]
    if not rows:
        assert recs == [] and outs["usn-csv"][1].strip().count("\n") == 0, "no journal: not an empty document"
        return
    assert list(rows[0].keys()) == list(recs[0].keys()), (list(rows[0].keys()), list(recs[0].keys()))
    for r, j in list(zip(rows, recs))[:500]:
        for c in r:
            assert _cell(j[c]) == r[c], (c, r[c], j[c])
    assert all(r["StreamOffset"].startswith("0x") for r in rows[:50]), "no $J offset in the export"


def test_n258_usn_json_journal_carries_the_info_facts(outs):
    j = _doc(outs, "usn-json")["Journal"]
    if j is None:
        pytest.skip("no journal on this volume")
    for k in ("ChangeJournalEntry", "JRuns", "JAllocatedSize", "JDeclared", "JournalID"):
        assert k in j, (k, sorted(j))
    assert re.fullmatch(r"0x[0-9a-f]{16}", j["JournalID"]), j["JournalID"]


def test_n312_usn_without_a_journal_gives_an_empty_valid_document(outs):
    rc, out, err = outs["usn-csv"]
    if _doc(outs, "usn-json")["Journal"] is not None:
        pytest.skip("this volume has a journal")
    assert out.strip() and "\n" not in out.strip() and out.startswith("USN,"), out[:200]
    assert "Change Journal" in err, err[-300:]


def test_n312_usn_refuses_two_formats(tmp_path):
    img = E2A._corpus_image("step1/win10refsmini.raw")
    if img is None:
        pytest.skip("no corpus")
    rc, out, err = E2A._run(E2A._F, img, ["usn", "--csv", "--json"], str(tmp_path))
    assert rc == 1 and "one of" in err and not out.strip(), (rc, out[:200], err[-300:])


def test_n312_timeline_json_is_an_envelope(outs):
    d = _doc(outs, "timeline-json")
    assert isinstance(d, dict) and isinstance(d.get("Events"), list) and "SourceCounts" in d, str(d)[:200]
    rows = _csv_rows(outs, "timeline-csv")
    assert rows and list(rows[0].keys()) == ["Timestamp", "TimeSource", "Source", "OID", "Name", "PathToday",
                                             "Event"], rows[:1]


def test_q_c_timeline_name_and_path_today(outs):
    """Q-C (settled from decisions 48 and 49.6, N255 and PLAN_1.14 T2): a row's Name is the name its source carries,
    PathToday the live tree's path -- a USN row has none (its path at the event is not read), a $SI row's PathToday ends
    in its Name, an MLog row carries `mlog --csv`'s Name and PathToday for its payload."""
    rows = _csv_rows(outs, "timeline-csv") + (_doc(outs, "timeline-json") or {}).get("Events", [])
    usn = [r for r in rows if r["Source"] == "USN"]
    assert all(not r["PathToday"] and "/" not in (r["Name"] or "") for r in usn), [r for r in usn if r["PathToday"]][:3]
    si = [r for r in rows if r["Source"] == "$SI"]
    assert all(r["PathToday"] and r["PathToday"].rsplit("/", 1)[-1] == r["Name"] for r in si), \
        [r for r in si if not r["PathToday"] or r["PathToday"].rsplit("/", 1)[-1] != r["Name"]][:3]
    pairs = {(r["Name"] or "", r["PathToday"] or "") for r in _csv_rows(outs, "mlog-csv")}
    ml = [r for r in rows if r["Source"] == "MLog"]
    assert all(((r["Name"] or ""), (r["PathToday"] or "")) in pairs for r in ml), \
        [r for r in ml if ((r["Name"] or ""), (r["PathToday"] or "")) not in pairs][:3]


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N313 / N314 timestomp
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n313_timestomp_has_one_key_set(outs):
    rows = _csv_rows(outs, "timestomp-csv")
    d = _doc(outs, "timestomp-json")
    want = ["ObjectRef", "FullPath", "RecordPlacement", "DataResidency", "Confidence", "Basis", "Signals",
            "EvidenceRefs", "Created", "Modified", "Changed", "Accessed"]
    if rows:
        assert list(rows[0].keys()) == want, list(rows[0].keys())
    assert "Rows" in d and "Suspects" not in d, sorted(d)
    if d["Rows"]:
        assert list(d["Rows"][0].keys()) == want, list(d["Rows"][0].keys())


def test_n314_timestomp_storage_is_split_into_both_axes(outs):
    rows = _csv_rows(outs, "timestomp-csv")
    assert all("Storage" not in r for r in rows)
    bad = [r for r in rows if r["DataResidency"].startswith("0x") or r["DataResidency"].startswith("(")]
    assert not bad, bad[:3]


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# E-1 / N315 -- N318 deleted
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _text_entry_counts(text):
    """The entries the view prints, by its one-line sections' heads `  ── <STATUS>: N (...) ──` (group 2, PLAN 10.2 E;
    slack and page scans): the tool's own labels (`_STATUS_LABEL`), each followed by its count."""
    heads = "|".join(re.escape(h) for h in F._STATUS_LABEL.values())
    return sum(int(m.group(1)) for m in re.finditer(r"^  ── (?:%s): (\d+) \(" % heads, text, re.M))


def test_e1_every_entry_the_view_prints_is_a_row(outs):
    n_text = _text_entry_counts(outs["deleted"][1])
    rows = _csv_rows(outs, "deleted-csv")
    slack = [r for r in rows if r["RecoverySource"] not in ("Trash table", "checkpoint comparison", "orphan")]
    assert len(slack) == n_text, "the view prints %d entries, the CSV has %d of them" % (n_text, len(slack))


def test_e1_still_present_entries_are_rows_with_their_status(outs):
    if "STILL PRESENT" not in outs["deleted"][1]:
        pytest.skip("no STILL PRESENT entry on this volume")
    rows = _csv_rows(outs, "deleted-csv")
    assert any(r["Status"] == "still present" for r in rows), sorted({r["Status"] for r in rows})


@pytest.mark.parametrize("fid", ["deleted-json", "deleted-jsonl", "export-deleted/deleted_files.json"])
def test_e1_every_machine_form_carries_the_same_rows(outs, fid):
    rows = _csv_rows(outs, "deleted-csv")
    docs = E2A._json_docs(outs[fid][1])
    recs = docs[0] if not fid.endswith("jsonl") else docs
    assert len(recs) == len(rows), (len(recs), len(rows))


def test_n317_the_manifest_and_the_index_name_a_fact_once(outs):
    m = _doc(outs, "export-deleted/recovery_manifest.json")
    rec = (m.get("Records") or [{}])[0]
    for old in ("name", "tag", "plcn", "content_file", "verdict", "IsResident", "Name", "Tag", "Plcn"):
        assert old not in rec, (old, sorted(rec))
    for k in ("FileName", "RecoverySource", "Cluster", "ContentFile", "Recoverability", "Status"):
        assert k in rec, (k, sorted(rec))


def test_n318_an_orphan_row_names_itself_by_objectref():
    rows = F._deleted_rows([], [{"name": "DIR_OID_0x7a1", "oid": 0x7a1, "create_time": 0, "modify_time": 0,
                                 "file_attrs": 0x10000010, "recovered_child": "x.txt"}])
    r = rows[-1]
    assert r["ObjectRef"] == "0x7a1:0x0" and r["RecoveredFrom"] == "" and r["Status"], r
    assert r["FileAttributes"] == "Directory|Directory_Internal", r["FileAttributes"]


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N319 recyclebin, N322 / N323 reparse, N324 / N325 security, N326 status lines
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n319_recyclebin_records_are_in_the_texts_order(outs):
    recs = _doc(outs, "recyclebin-json")
    times = [r.get("DeletionTime") or "" for r in recs]
    assert times == sorted(times), times[:6]


def test_n322_reparse_json_names_each_point_by_files_names(outs):
    d = _doc(outs, "reparse-json")
    pts = d.get("ReparsePoints")
    assert isinstance(pts, list) and "Summary" in d, sorted(d)
    if pts:
        assert {"ObjectRef", "FullPath", "ReparseTag"} <= set(pts[0]) and "ReparseTagValue" not in pts[0], pts[0]
        assert all(isinstance(p["ReparseTag"], str) for p in pts if p.get("ReparseTag") is not None)


def test_n323_reparse_index_names_the_key_reference(outs):
    d = _doc(outs, "reparse-index-json")
    ents = d.get("ReparseIndex") or []
    if not ents:
        pytest.skip("no reparse index row")
    e = next(x for x in ents if "HomeOID" in x or "ObjectRef" in x)
    assert "DirOID" not in e and re.fullmatch(r"0x[0-9a-f]+:0x[0-9a-f]+", e["ObjectRef"]), e


def test_n324_security_json_honours_sid_and_audit(tmp_path):
    img = E2A._corpus_image("step1/win10refsmini.raw")
    if img is None:
        pytest.skip("no corpus")
    rc, out, err = E2A._run(E2A._F, img, ["security", "--json"], str(tmp_path))
    sds = json.loads(out)["SecurityDescriptors"]
    sid = sds[0]["SecurityId"]
    rc, out, err = E2A._run(E2A._F, img, ["security", "--json", "--sid", sid], str(tmp_path))
    one = json.loads(out)["SecurityDescriptors"]
    assert [x["SecurityId"] for x in one] == [sid], [x["SecurityId"] for x in one]
    rc, out, err = E2A._run(E2A._F, img, ["security", "--audit", "--json"], str(tmp_path))
    a = json.loads(out)["Audit"]
    assert a["Verdict"] in ("CLEAN", "FAIL", "UNDETERMINED") and a["Descriptors"] == len(sds), a


def test_n325_one_descriptor_parser_refuses_another_revision():
    import struct as _s
    sd = bytearray(64)
    sd[0] = 2                                                           # revision 2: not a security descriptor
    _s.pack_into("<HIIII", sd, 2, 0x8004, 20, 0, 0, 0)
    d = F._parse_security_descriptor(bytes(sd))
    assert "error" in d and "revision" in d["error"], d
    sd[0] = 1
    assert "error" not in F._parse_security_descriptor(bytes(sd))


def test_n326_a_status_line_goes_to_stderr(tmp_path):
    img = E2A._corpus_image("step1/win10refsmini.raw")
    if img is None:
        pytest.skip("no corpus")
    dest = str(tmp_path / "ads.json")
    rc, out, err = E2A._run(E2A._F, img, ["ads", "--json", dest], str(tmp_path))
    assert "Wrote" not in out and "Wrote" in err, (out[-200:], err[-200:])


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N443 / N460 -- one failure rule for a machine output
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n443_a_failed_file_write_leaves_no_file_under_its_name(tmp_path):
    dest = str(tmp_path / "out.json")
    with pytest.raises(OSError) as ei:
        F._emit_records(_Failing(), ["a"], "jsonl", dest)
    assert not os.path.exists(dest) and not os.path.exists(dest + ".partial"), os.listdir(tmp_path)
    assert ei.value.filename == dest


class _Failing(list):
    """A record list whose second element fails to be read (a read error part-way through an export)."""
    def __iter__(self):
        yield {"a": 1}
        raise OSError(5, "Input/output error")

    def __len__(self):
        return 2


def test_n443_a_failed_stdout_stream_says_it_is_incomplete(capsys):
    with pytest.raises(OSError):
        F._emit_records(_Failing(), ["a"], "jsonl", None)
    err = capsys.readouterr().err
    assert "INCOMPLETE" in err, err


def test_n443_control_a_complete_write_is_renamed(tmp_path):
    dest = str(tmp_path / "ok.csv")
    F._emit_records([{"a": 1}], ["a"], "csv", dest)
    assert open(dest).read().splitlines() == ["A", "1"] and not os.path.exists(dest + ".partial")


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# E-2 -- the bundle's format
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_e2_a_bundle_manifest_carries_its_format_and_the_output_names(outs):
    rc, text, err = outs["export-metadata/manifest.json"]
    d = json.loads(text)
    assert list(d.keys())[0] == "BundleFormat" and d["BundleFormat"] == F.BUNDLE_FORMAT, list(d.keys())[:4]
    a = d["Artifacts"][0]
    assert "File" in a and "SHA256" in a, a
    lcns = [x["LCN"] for x in d["Artifacts"] if "LCN" in x]
    assert lcns and all(re.fullmatch(r"0x[0-9a-f]+", x) for x in lcns), lcns[:4]


def test_e2_an_older_bundle_is_refused_with_the_versions_named(tmp_path):
    b = tmp_path / "old_bundle"
    b.mkdir()
    (b / "manifest.json").write_text(json.dumps({"image": "x.raw", "cluster_size": 4096, "refs_version": "3.14",
                                                 "artifacts": []}))
    (b / "sha256sums.txt").write_text("")
    img = str(b)
    p = subprocess.run([sys.executable, "-B", E2A.FOREFST, img, "verify-bundle"], capture_output=True, text=True)
    assert p.returncode == 1 and "1.12.1-1.13.1" in p.stderr and "Traceback" not in p.stderr, (p.returncode,
                                                                                                p.stderr[-400:])
    p = subprocess.run([sys.executable, "-B", E2A.FOREFST, img, "summary"], capture_output=True, text=True)
    assert p.returncode == 1 and "1.12.1-1.13.1" in p.stderr and "Traceback" not in p.stderr, (p.returncode,
                                                                                                p.stderr[-400:])
