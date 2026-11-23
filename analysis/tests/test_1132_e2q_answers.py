"""E2 (1.14.0): the maintainer's answers of 2026-10-30 (fixes/E2a_NOTES.md section 1).

  Q-A = A1  a flag word or a reparse tag in CSV / JSON is two fields, the names and the hex (K14 A): FileAttributes /
            FileAttributesHex, InternalFlags / InternalFlagsHex, ReparseTag / ReparseTagHex -- `files` 42 columns; one
            form per key in every document (a directory's `details` structure dump included).
  Q-B = B1  InternalFlags: every value read is printed, a bit with no name as its hex -- 1.13.1 printed only the named
            bits; a word that was not read stays blank, never `0x0`. (Bit 0x8 had no name then; the labs-and-driver
            batch's Q-A named it `DataInRecord`, test_1132_ld_qab.py: the nodes below expect the name, and the
            unnamed-bit rule is tested with 0x4.)
  Q-D = D3  the MLog section (N416, decision 41) is `summary`'s (both tools), built by `mlog`'s functions: its findings
            reach the exit; `fastsummary` names `mlog` for it. The tail check's "not checked" is never read as "none
            missing", nor an uncomputed copy check as "failed".
Images: the public sample (win11refstestmftecmd: 1,744 rows, 41 with InternalFlags 0x8 alone -- the K14 census,
scratchpad flags.tsv), labFbeforereboot for the MLog finding (a scratch copy, its newest records zeroed as A7's node).
"""
import csv
import io
import json
import os
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions)
import test_1132_red_mlog_chkp as MC                     # noqa: E402  (scratch_copy, _zero_range)
import test_1132_red_waveb_mlog as WB                    # noqa: E402  (LABF)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

_fx = AB._fx
SAMPLE = "step5/win11refstestmftecmd.raw"
FOREFST = os.path.join(REPO, "forefst.py")
RA = os.path.join(REPO, "refsanalysis.py")
SYMLINK = ("/test/elvis_dir_record_449015/elvis_dir_papa_104235/elvis_dir_sync_718743/elvis_dir_gamma_109016/"
           "elvis_dir_zulu_984398/elvis_dir_cache_558805/xbpt_symlink_gamma_582874.lnk")   # 0x28, a symlink


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


@pytest.fixture(scope="module")
def sample_files():
    rc, out, err = _run(FOREFST, _img(SAMPLE), "files", "--csv")
    _fx(rc == 0, "files --csv on the sample exits %d:\n%s" % (rc, err[-2000:]))
    rdr = csv.DictReader(io.StringIO(out))
    return rdr.fieldnames, list(rdr)


def _names(v, table):
    return F.flag_names(v, table) or "0x0"


# ─── Q-A = A1 ─────────────────────────────────────────────────────────────────────────────────────────────────────

def test_a1_files_csv_has_42_columns_each_hex_field_after_its_names(sample_files):
    cols, _rows = sample_files
    assert len(cols) == 42, (len(cols), cols)
    for k in ("FileAttributes", "ReparseTag", "InternalFlags"):
        assert cols[cols.index(k) + 1] == k + "Hex", (k, cols)


def test_a1_every_row_names_the_bits_its_hex_field_holds(sample_files):
    """The two fields are one value: the names are `flag_names` of the hex (`0x0` for a zero word), the tag's name its
    REPARSE_TAGS name; both blank only together."""
    _cols, rows = sample_files
    bad = []
    for r in rows:
        for k, table in (("FileAttributes", F.FILE_ATTR_FLAGS), ("InternalFlags", F._INTERNAL_FLAG_LABELS)):
            h = r[k + "Hex"]
            if (h == "") != (r[k] == "") or (h and _names(int(h, 16), table) != r[k]):
                bad.append((r["FullPath"], k, r[k], h))
        t = r["ReparseTagHex"]
        if (t == "") != (r["ReparseTag"] == "") or (t and F.reparse_tag_name(int(t, 16)) != r["ReparseTag"]):
            bad.append((r["FullPath"], "ReparseTag", r["ReparseTag"], t))
        if t and len(t) != 10:
            bad.append((r["FullPath"], "ReparseTagHex padded to 32 bits", t))
    assert not bad and len(rows) == 1744, (len(rows), bad[:5])


def test_a1_json_documents_carry_one_form_per_key():
    """In every dict of `files --json`, `details` (a file, a directory: its structure dump) and `reparse --json`: a
    FileAttributes / InternalFlags / ReparseTag key holds the names, its ...Hex key the word -- never one key in two
    forms."""
    img = _img(SAMPLE)
    docs = []
    for args in (("files", "--json"), ("details", SYMLINK, "--json"), ("details", "/test", "--json"),
                 ("reparse", "--json")):
        rc, out, err = _run(FOREFST, img, *args)
        _fx(rc == 0, "%s exits %d:\n%s" % (args, rc, err[-1500:]))
        docs.append((args, json.loads(out)))
    seen, bad = {}, []

    def walk(o, where):
        if isinstance(o, dict):
            for k, table in (("FileAttributes", F.FILE_ATTR_FLAGS), ("InternalFlags", F._INTERNAL_FLAG_LABELS)):
                if k in o:
                    seen[k] = seen.get(k, 0) + 1
                    h = o.get(k + "Hex")
                    if h is None and o[k] is None:
                        continue
                    if not isinstance(h, str) or _names(int(h, 16), table) != o[k]:
                        bad.append((where, k, o[k], h))
            if "ReparseTag" in o:
                seen["ReparseTag"] = seen.get("ReparseTag", 0) + 1
                h = o.get("ReparseTagHex")
                if (h is None) != (o["ReparseTag"] is None) or (h and F.reparse_tag_name(int(h, 16)) != o["ReparseTag"]):
                    bad.append((where, "ReparseTag", o["ReparseTag"], h))
            for v in o.values():
                walk(v, where)
        elif isinstance(o, list):
            for v in o:
                walk(v, where)
    for args, d in docs:
        walk(d, " ".join(args[:1]))
    assert not bad and all(seen.get(k) for k in ("FileAttributes", "InternalFlags", "ReparseTag")), (seen, bad[:6])


def test_a1_deleted_and_specials_carry_the_hex_fields():
    for cols, k in ((F.DELETED_CSV_COLUMNS, "FileAttributesHex"), (F.EARLIER_CSV_COLUMNS, "FileAttributesHex"),
                    (F.SPECIALS_COLUMNS, "ReparseTagHex")):
        assert k in cols, (k, cols)
    assert F.EARLIER_CSV_COLUMNS.index("FileAttributesHex") == F.EARLIER_CSV_COLUMNS.index("FileAttributes") + 1


@pytest.mark.parametrize("v,table,want", [
    (None, F.FILE_ATTR_FLAGS, ("", "")), (0, F.FILE_ATTR_FLAGS, ("0x0", "0x0")), (0x20, F.FILE_ATTR_FLAGS,
                                                                                    ("Archive", "0x20")),
    (0x8, F._INTERNAL_FLAG_LABELS, ("DataInRecord", "0x8")), (0x4, F._INTERNAL_FLAG_LABELS, ("0x4", "0x4")),
    (0x28, F._INTERNAL_FLAG_LABELS, ("DataInRecord|RedirectionTrust", "0x28"))])
def test_a1_flag_cells(v, table, want):
    assert F.flag_cells(v, table) == want


def test_a1_reparse_tag_cells_and_machine_forms():
    assert F.reparse_tag_cells(0) == F.reparse_tag_cells(None) == ("", "")
    assert F.reparse_tag_cells(0xA000000C) == ("IO_REPARSE_TAG_SYMLINK", "0xa000000c")
    assert 0x80001234 not in F.REPARSE_TAGS
    assert F.reparse_tag_cells(0x80001234) == ("0x80001234", "0x80001234")          # a tag with no name: its hex
    got = F.out_keys(F.json_null(F.machine_forms({"file_attrs": 0x10000000, "internal_flags": "0x8",
                                                  "reparse_tag": "0x00000000", "flags": 0x20})))
    assert got == {"FileAttributes": "Directory_Internal", "FileAttributesHex": "0x10000000", "InternalFlags": "DataInRecord",
                   "InternalFlagsHex": "0x8", "ReparseTag": None, "ReparseTagHex": None, "Flags": "0x20"}, got


# ─── Q-B = B1 ─────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("v,want", [(0x8, "0x8 (DataInRecord)"), (0x4, "0x4"), (0x2c, "0x2c (DataInRecord|RedirectionTrust|0x4)"),
                                    (0x28, "0x28 (DataInRecord|RedirectionTrust)"), (0x20, "0x20 (RedirectionTrust)"),
                                    (0, "0x0 (none set)"), (None, "")])
def test_b1_internal_flags_text(v, want):
    assert F.internal_flags_str(v) == want


def test_b1_files_prints_bit_0x8_on_the_41_rows_that_hold_it_alone(sample_files):
    """The census (K14, the walk's own field) counted 41 rows of the sample with 0x8 alone; 1.13.1 printed nothing
    for them (named `DataInRecord` since Q-A)."""
    _cols, rows = sample_files
    alone = [r for r in rows if r["InternalFlagsHex"] == "0x8"]
    assert len(alone) == 41 and all(r["InternalFlags"] == "DataInRecord" for r in alone), (len(alone), alone[:2])


def test_b1_control_a_word_not_read_stays_blank_never_0x0():
    """A split row whose backing is not resolved: the walk read no internal-flags word for it."""
    r = {"oid": 0, "is_dir": False, "is_resident": False, "file_attrs": 0x20, "parent_oid": 0x701, "name": "x"}
    cells = F._csv_fields(r, {}, "3.14")
    assert (cells["InternalFlags"], cells["InternalFlagsHex"]) == ("", ""), cells
    r["internal_flags"] = 0
    cells = F._csv_fields(r, {}, "3.14")
    assert (cells["InternalFlags"], cells["InternalFlagsHex"]) == ("0x0", "0x0"), cells


def test_b1_details_and_refsanalysis_attributes_print_0x8():
    img = _img(SAMPLE)
    rc, out, err = _run(FOREFST, img, "details", SYMLINK)
    assert rc == 0 and "Internal flags:     0x28 (DataInRecord|RedirectionTrust)" in out, out[-2000:]
    rc, out, err = _run(RA, img, "attributes", SYMLINK)
    assert "IntFlags:    0x28 (DataInRecord|RedirectionTrust)" in out, (rc, out[-2000:], err[-800:])


# ─── Q-D = D3 ─────────────────────────────────────────────────────────────────────────────────────────────────────

def _mlog_section(text):
    i = text.find("MLog (from one pass over the log)")
    return text[i:].split("\n\n")[0] if i >= 0 else None


def test_d3_summary_has_the_mlog_section_with_mlogs_own_facts():
    """The section states the copy in use, its check, the log version, start and end -- the values `mlog --json`
    reads (MLogInfo / the control copies), from the same functions."""
    img = _img(SAMPLE)
    rc, out, err = _run(FOREFST, img, "summary", "--json", "--mlog")     # A1 (1.14.0): the pass runs with --mlog
    _fx(rc == 0, "summary --json exits %d" % rc)
    m = json.loads(out).get("MLog")
    rc2, out2, _e = _run(FOREFST, img, "mlog")                  # the default view: control area, data, records
    assert m and m["ControlCopySlot"] in (0, 1) and m["ControlCopyPLCN"].startswith("0x"), m
    assert m["ControlCopyVerifies"] is True and m["LogVersion"] == 1 and m["NewestRecordsMissing"] is False, m
    assert m["LogStart"] == "0x00000004000012d9" == m["LogEnd"] and m["LogBlocks"] == 65536, m
    assert m["Statements"] == [] and m["EarlierLogRecords"] == 0, m
    assert "Log start:         0x00000004000012d9" in out2 and "Control PLCN:      %s  (copy %d, in use" % (
        m["ControlCopyPLCN"], m["ControlCopySlot"]) in out2, out2[:2500]
    rc, out, err = _run(FOREFST, img, "summary", "--mlog")
    sec = _mlog_section(out)
    assert rc == 0 and sec and "Log start:          0x00000004000012d9 (generation 4, offset 0x12d9)" in sec \
        and "Newest records:     none missing (the log end checked)" in sec, sec


def test_d3_refsanalysis_summary_prints_the_same_section():
    img = _img(SAMPLE)
    _rc, out, _e = _run(FOREFST, img, "summary", "--mlog")
    rc, out2, err2 = _run(RA, img, "summary", "--mlog")
    assert rc == 0 and _mlog_section(out) and _mlog_section(out) == _mlog_section(out2), (_mlog_section(out2),
                                                                                          err2[-800:])


def test_d3_fastsummary_names_mlog_and_reads_no_log():
    img = _img(SAMPLE)
    rc, out, err = _run(FOREFST, img, "fastsummary")
    assert rc == 0 and "MLog:  not read by `fastsummary`; `summary --mlog` or `mlog` reads the log" in out \
        and _mlog_section(out) is None, out[-1500:]
    rc, out, err = _run(FOREFST, img, "fastsummary", "--json")
    d = json.loads(out)
    assert rc == 0 and "MLog" in d and d["MLog"] is None, sorted(d)[:40]


def test_d3_summary_exits_2_on_the_mlogs_finding_and_states_it(tmp_path):
    """The synthetic volume (a_bootstrap's: an empty log, `summary` exits 0) with its control copies' log end 5 blocks
    past the log start and nothing written there: the newest records are missing. `mlog` exits 2 and says so; so do both
    `summary` commands now, with the same sentence. (labFbeforereboot cannot show the exit: its summary exits 2 already,
    the dirty volume's finding.)"""
    p = str(tmp_path / "target.raw")
    AB._build_synthetic(p)
    ps = ("--partition-start", "0")
    rc0, out0, err0 = _run(FOREFST, p, "summary", "--mlog", *ps)
    _fx(rc0 == 0 and "Newest records:     none missing (the log end checked)" in (_mlog_section(out0) or ""),
        "the intact synthetic volume: summary exits %d\n%s\n%s" % (rc0, _mlog_section(out0), err0[-1500:]))
    with open(p, "r+b") as fh:
        for lcn, seq in zip(AB._SYN_LOG_CTRL, (51, 50)):
            fh.seek(lcn * AB.CS)
            fh.write(MC.control_block(AB._VOLSIG, AB._SYN_LOG_UUID, seq, AB._SYN_LOG_DS, AB._SYN_LOG_DE, MC.lsn(1, 0),
                                      MC.lsn(1, 5), 3))
    rc_m, out_m, err_m = _run(FOREFST, p, "mlog", *ps)
    rc1, out1, err1 = _run(FOREFST, p, "summary", "--mlog", *ps)
    rc2, out2, err2 = _run(RA, p, "summary", "--mlog", *ps)
    sec = _mlog_section(out1) or ""
    said = [l.strip() for l in sec.splitlines() if "are missing" in l]
    assert rc_m == 2 and rc1 == 2 and rc2 == 2 and said and "Newest records:     MISSING" in sec, (rc_m, rc1, rc2, sec)
    assert said[0] in (out_m + err_m) and said[0] in out2, (said, (out_m + err_m)[-1500:])


def test_d3_control_unchecked_tail_and_uncomputed_check_are_not_read_as_facts():
    out = []
    assert F.mlog_tail_check(None, 0, 4096, {}, None, None, outcome=out) == [] and out == ["not checked"]
    buf = io.StringIO()
    sys_stdout, sys.stdout = sys.stdout, buf
    try:
        F._print_mlog_section({"control_copy_slot": 1, "control_copy_plcn": 0x10, "control_copy_verifies": None,
                               "newest_records_missing": None, "statements": []})
    finally:
        sys.stdout = sys_stdout
    t = buf.getvalue()
    assert "its check could not be computed" in t and "Newest records:     not checked" in t, t
