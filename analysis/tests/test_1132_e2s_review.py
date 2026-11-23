"""E2 close (1.14.0): the review's findings (fixes/REVIEW_WAVEE2.md; fixes/E2cd_NOTES.md section 9). RED on
fixes/prefix_E2close (forefst f85ca2fe, refsanalysis a9dd7326).

  M1  `export deleted`'s JSON index is the CSV index typed: every record has every CSV column, also a checkpoint-
      comparison or Trash-table row (labFbeforereboot: 5,057 of 6,633 records lacked SHA256 / RenameReason).
  M2  `files`' help states the CSV's column count from the column list and names its three Hex columns (it said 39).
  M3  a boolean in text is a word (K19): `reparse -v` Relative, refsanalysis `parentchild -vv` Key == Value.
  S3  a flag word in a machine output is names + hex (K14 A, the maintainer's A1): the checkpoint flags, the security
      descriptor's control word, an ACE's flags and access mask, the USN source info, a symlink's flags, a redo
      record's flags. (Recorded exceptions: the MLog control area's flags, which have no name table; the FS Metadata
      children's word at value+0x80, whose meaning is open -- OPEN_QUESTIONS_REVIEW Q33; RUNNING_LOG N524.)
  S4  R4 / K14 text forms: identifiers and offsets unpadded (refsanalysis TableID, the field tables' offset column,
      bootedit's diff offsets, usn --info's offsets and reason legend, the MLog schema ids), a flag word hex first
      (`usn -v` Source), the structure dump's flag words as text, an unknown ACE type `unknown (0x..)`.
  S5  `files` ends a write failure with the error line every command prints, never a traceback; no partial file left.
"""
import csv
import io
import json
import os
import re
import resource
import signal
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

_fx = AB._fx
FOREFST = os.path.join(REPO, "forefst.py")
RA = os.path.join(REPO, "refsanalysis.py")
MINI314 = "step1/win11refsmini.raw"
MINI34 = "step1/win10refsmini.raw"
SPECIALS = "step3/win11refs2tspecials.raw"
SAMPLE = "step5/win11refstestmftecmd.raw"
LABF = "step7/labFbeforereboot.raw"


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


def _doc(text):
    return json.loads(text[text.index("{"):])


def _lines(text, rx):
    return [ln for ln in text.splitlines() if re.search(rx, ln)]


# ═══ M1 ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_m1_every_index_json_record_has_every_csv_column(tmp_path):
    d = str(tmp_path / "x")
    rc, out, err = _run(FOREFST, _img(LABF), "export", "deleted", d)
    with open(os.path.join(d, "deleted_files.csv"), encoding="utf-8") as fh:
        rdr = csv.reader(fh)
        head = next(rdr)
        rows = list(rdr)
    with open(os.path.join(d, "deleted_files.json"), encoding="utf-8") as fh:
        recs = json.load(fh)
    _fx(len(recs) == len(rows) and rows, "premise: %d records, %d rows" % (len(recs), len(rows)))
    kinds = {r.get("RecoverySource") for r in recs}
    _fx("checkpoint comparison" in kinds, "premise: no checkpoint-comparison row on labFbeforereboot: %r" % kinds)
    bad = [(i, sorted(set(head) - set(r)), sorted(set(r) - set(head))) for i, r in enumerate(recs) if set(r) != set(head)]
    assert not bad, "%d of %d records with another key set: %r" % (len(bad), len(recs), bad[:3])


def test_m1_the_json_values_are_the_csv_cells():
    """The deleted rows' JSON is `json_null(machine_forms(rows))` over the same dicts the CSV writes: an empty cell is
    null, every other cell its value (the index's typed form)."""
    rows = F._deleted_rows([], [], index=True, ckpt=[("added", [], ["a/b.txt"], "0x704:0x1")],
                           trash=[{"oid": 0x9, "key_hex": "01", "value_hex": "02"}])
    assert rows, "no rows built"
    for r in rows:
        assert set(F.DELETED_INDEX_COLUMNS) <= set(r), sorted(set(F.DELETED_INDEX_COLUMNS) - set(r))


# ═══ M2 ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_m2_the_files_help_states_the_column_count_and_the_hex_columns():
    r = subprocess.run([sys.executable, "-B", FOREFST, "help", "files"], capture_output=True, text=True, timeout=120)
    txt = re.sub(r"\s+", " ", r.stdout + r.stderr)
    n = len(F.CSV_COLUMNS)
    m = re.search(r"(\d+)-column CSV", txt)
    assert m and int(m.group(1)) == n, (m and m.group(0), n)
    for c in ("FileAttributesHex", "InternalFlagsHex", "ReparseTagHex"):
        assert c in txt, c


# ═══ M3 ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_m3_reparse_v_relative_is_a_word():
    rc, out, err = _run(FOREFST, _img(SPECIALS), "reparse", "-v")
    ln = _lines(out, r"^\s+Relative:")
    _fx(ln, "premise: no Relative line:\n" + out[-1500:])
    assert all(re.fullmatch(r"\s+Relative:\s+(yes|no)", x) for x in ln), ln[:3]


def test_m3_parentchild_vv_key_equals_value_is_a_word():
    rc, out, err = _run(RA, _img(MINI34), "parentchild", "-vv")
    ln = _lines(out, r"Key == Value:")
    _fx(ln, "premise: no Key == Value line:\n" + out[-1500:])
    assert all(re.fullmatch(r"\s+Key == Value:\s+(yes|no)", x) for x in ln), ln[:3]


# ═══ S3 ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def _names(v, table):
    return F.flag_names(v, table) or "0x0"


@pytest.mark.parametrize("tool,cmd", [(FOREFST, "summary"), (FOREFST, "fastsummary"), (RA, "summary")])
def test_s3_checkpoint_flags_are_names_and_hex(tool, cmd):
    rc, out, err = _run(tool, _img(MINI314), cmd, "--json")
    d = _doc(out)
    assert "CheckpointFlagNames" not in d, "the names list beside the names field (a duplicate)"
    h = d.get("CheckpointFlagsHex")
    assert h and re.fullmatch(r"0x[0-9a-f]+", h), d.get("CheckpointFlags")
    assert d["CheckpointFlags"] == _names(int(h, 16), F._CHKP_FLAG_BITS), (d["CheckpointFlags"], h)


def test_s3_security_control_and_ace_words_are_names_and_hex():
    rc, out, err = _run(FOREFST, _img(SPECIALS), "security", "--json")
    sds = _doc(out)["SecurityDescriptors"]
    _fx(sds and any(sd.get("DACL") for sd in sds), "premise: no ACL")
    for sd in sds:
        assert "ControlFlags" not in sd and sd["Control"] == _names(int(sd["ControlHex"], 16), F._SD_CONTROL_FLAGS), sd
        for ace in (sd.get("DACL") or []) + (sd.get("SACL") or []):
            assert ace["Flags"] == _names(int(ace["FlagsHex"], 16), F._ACE_FLAGS), ace
            if "MaskHex" in ace or "Mask" in ace:
                assert "MaskText" not in ace, ace
                assert ace["Mask"] == F._format_access_mask(int(ace["MaskHex"], 16), int(ace["TypeID"], 16)), ace


def test_s3_usn_source_info_is_names_and_hex():
    rc, out, err = _run(FOREFST, _img(SAMPLE), "usn", "--csv")
    rows = list(csv.DictReader(io.StringIO(out)))
    _fx(rows, "premise: no USN record")
    head = list(rows[0])
    assert "SourceInfoHex" in head and head.index("SourceInfoHex") == head.index("SourceInfo") + 1, head
    bad = [r for r in rows if r["SourceInfo"] != _names(int(r["SourceInfoHex"], 16), F.USN_SOURCE_FLAGS)]
    assert not bad, bad[:2]


def test_s3_usn_source_info_names_in_json():
    rc, out, err = _run(FOREFST, _img(SAMPLE), "usn", "--json")
    recs = _doc(out)["Records"]
    _fx(recs, "premise: no record")
    assert all(r["SourceInfo"] == _names(int(r["SourceInfoHex"], 16), F.USN_SOURCE_FLAGS) for r in recs), recs[:1]


def test_s3_symlink_flags_are_names_and_hex():
    rc, out, err = _run(FOREFST, _img(SPECIALS), "reparse", "--json")
    rd = [p["ReparseData"] for p in _doc(out)["ReparsePoints"]
          if isinstance(p.get("ReparseData"), dict) and "Flags" in p["ReparseData"]]
    _fx(rd, "premise: no symlink data")
    assert all(x["Flags"] == _names(int(x["FlagsHex"], 16), F._SYMLINK_FLAGS) for x in rd), rd[:2]


def test_s3_redo_record_flags_are_names_and_hex():
    rc, out, err = _run(FOREFST, _img(MINI314), "mlog", "--json")
    recs = _doc(out).get("Records") or []
    _fx(recs, "premise: no redo record")
    for r in recs[:5000]:
        v = int(r["FlagsHex"], 16)
        assert r["Flags"] == _names(v, F._REDO_FLAGS), r
        assert r["TxnStart"] == bool(v & 1) and r["TxnCommit"] == bool(v & 2), r


# ═══ S4 ═════════════════════════════════════════════════════════════════════════════════════════════════════════

_PADDED = re.compile(r"\b0x0[0-9a-f]+\b")


@pytest.mark.parametrize("cmd", ["boot -vv", "supb -vv", "chkp -vv"])
def test_s4_refsanalysis_field_tables_and_table_ids_are_unpadded(cmd):
    rc, out, err = _run(RA, _img(MINI314), *cmd.split())
    bad = [ln for ln in out.splitlines() for m in _PADDED.finditer(ln) if len(m.group(0)) - 2 not in (4, 8, 16)]
    assert not bad, bad[:6]


def test_s4_usn_info_offsets_and_reason_legend_are_unpadded():
    rc, out, err = _run(FOREFST, _img(SAMPLE), "usn", "--info")                  # a volume with a journal: the tables
    _fx(_lines(out, r"Record length \(u32\)") and _lines(out, r"Reason codes:"), "premise: no layout table:\n" + out[-1500:])
    # R4's fixed-width words keep their width (the journal id %016x); an offset or a flag bit does not
    bad = [ln for ln in out.splitlines() for m in _PADDED.finditer(ln) if len(m.group(0)) - 2 not in (8, 16)]
    assert not bad, bad[:6]


def test_s4_usn_source_text_is_hex_first():
    assert F.usn_source_text(0x3) == "0x3 (DATA_MANAGEMENT|AUXILIARY_DATA)"
    assert F.usn_source_text(0x10) == "0x10"                       # no bit named: the hex alone (flag_text)


def test_s4_an_unknown_ace_type_is_lower_case_unknown_with_its_hex():
    acl = bytes([2, 0]) + (8 + 8).to_bytes(2, "little") + (1).to_bytes(2, "little") + b"\x00\x00"
    ace = bytes([0x15, 0x00]) + (8).to_bytes(2, "little") + b"\x00" * 4
    aces = F._parse_acl(b"\x00" * 4 + acl + ace, 4)               # an ACL at offset 0 is "no ACL" (the SD's convention)
    assert aces and aces[0]["type"] == "unknown (0x15)", aces


def test_s4_the_structure_dump_writes_its_flag_words_as_text():
    rc, out, err = _run(FOREFST, _img(MINI314), "details", "0x701")
    ln = [x for x in out.splitlines() if re.match(r"\s+(file_attrs|internal_flags)\s", x)]
    _fx(ln, "premise: no structure dump lines:\n" + out[-1500:])
    assert all(re.search(r"\s0x[0-9a-f]+ \(", x) for x in ln), ln


def test_s4_mlog_schema_ids_are_unpadded():
    assert "0x110" in F._mlog_schema_line(0x110) and "0x0110" not in F._mlog_schema_line(0x110)


# ═══ S5 ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def _limit_fsize():
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))


def test_s5_files_ends_a_file_write_failure_with_the_error_line(tmp_path):
    dest = str(tmp_path / "files.csv")
    r = subprocess.run([sys.executable, "-B", FOREFST, _img(SAMPLE), "files", "--csv", "-o", dest],
                       capture_output=True, text=True, timeout=1200, preexec_fn=_limit_fsize)
    assert "Traceback" not in r.stderr, r.stderr[-1500:]
    assert re.search(r"error: cannot write the output \(.*files\.csv\)", r.stderr), r.stderr[-1500:]
    assert r.returncode == 1, r.returncode
    assert not os.path.exists(dest) and not os.path.exists(dest + ".partial")


def test_s5_files_ends_a_stdout_write_failure_with_the_error_line():
    with open("/dev/full", "w") as full:
        r = subprocess.run([sys.executable, "-B", FOREFST, _img(SAMPLE), "files", "--csv"], stdout=full,
                           stderr=subprocess.PIPE, text=True, timeout=1200)
    assert "Traceback" not in r.stderr, r.stderr[-1500:]
    assert "error: cannot write the output" in r.stderr, r.stderr[-1500:]
    assert r.returncode == 1, r.returncode
