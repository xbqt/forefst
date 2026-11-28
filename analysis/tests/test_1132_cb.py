"""1.14.0, the conformance batch (decision 42 S1): the latent rows of `analysis/reports/v1.13.2/fixes/CONFORMANCE_BATCH.md`,
fixed in direct mode (decision 46) -- before -> after per group in `fixes/CB_NOTES.md`, the prep in
`fixes/CONFORMANCE_PREP.md`, the measurements in `fixes/CB_evidence/`. About five nodes per row: the wrong case, its
variants, a control that must not change, a corpus image where one shows it.
"""
import ast
import io
import json
import os
import re
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
import refsanalysis as RA                                # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
RAPY = os.path.join(REPO, "refsanalysis.py")
MINI314 = "step1/win11refsmini.raw"
MINI34 = "step1/win10refsmini.raw"
SPECIALS = "step3/win11refs2tspecials.raw"
CORRUPT_CT = "step5/testchecksums/win11refslasttests_baseline_corrupted.raw"
MILLIONS = "step3/win11refs2tmillionsofactions.raw"


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _run(tool, img, *args, timeout=900):
    return UW.run([sys.executable, "-B", tool, img] + list(args), capture_output=True, text=True,
                  timeout=timeout)


def _sparse_copy(src, dst):
    """A hole-preserving copy (SEEK_DATA / SEEK_HOLE) of a corpus image, for a plant."""
    fi = os.open(src, os.O_RDONLY)
    fo = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        size = os.fstat(fi).st_size
        os.ftruncate(fo, size)
        off = 0
        while off < size:
            try:
                d = os.lseek(fi, off, os.SEEK_DATA)
            except OSError:
                break
            h = os.lseek(fi, d, os.SEEK_HOLE)
            os.lseek(fi, d, os.SEEK_SET)
            os.lseek(fo, d, os.SEEK_SET)
            left = h - d
            while left:
                b = os.read(fi, min(left, 1 << 20))
                os.write(fo, b)
                left -= len(b)
            off = h
    finally:
        os.close(fi)
        os.close(fo)
    return dst


def _write_at(path, off, data):
    with open(path, "r+b") as fh:
        fh.seek(off)
        fh.write(data)


def _boot(rel):
    return F.bootstrap(_img(rel))


# ==== G6: labels and text forms =====================================================================================

def test_q33_the_fs_metadata_children_carry_their_file_id_on_v34():
    """Q33: value+0x80 of the three down-level objects is their file id (0x100 / 0x200 / 0x400), read as 8 bytes."""
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI34)
    fm = F.fs_metadata_read(f, ps, cs, tr, om, "test", detail=True)
    got = {c["name"]: c.get("file_id") for c in fm["children"]}
    assert got == {"Reparse Index": 0x400, "Security Descriptor Stream": 0x200, "Volume Direct IO File": 0x100}, got
    assert all("flags" not in c for c in fm["children"]), fm["children"]


def test_q33_every_child_has_the_file_id_key_on_v314():
    """The control: a native v3.14 volume (no down-level object) -- whatever children it has carry `file_id`."""
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    fm = F.fs_metadata_read(f, ps, cs, tr, om, "test", detail=True)
    assert all("file_id" in c and "flags" not in c for c in fm["children"]), fm["children"]


def test_q33_summary_json_names_the_file_id():
    r = _run(FOREFST, _img(MINI34), "summary", "--json")
    assert r.returncode in (0, 2), r.stderr[-1500:]
    doc = json.loads(r.stdout)
    kids = doc["FSMetadata"]["Children"]
    assert {k["Name"]: k["FileID"] for k in kids}["Reparse Index"] == "0x400", kids
    assert not any("Flags" in k for k in kids), kids


def test_q33_refsanalysis_summary_plus_prints_the_file_id_and_no_degenerate_tag():
    r = _run(RAPY, _img(MINI34), "summary++")
    assert "Reparse Index  (file id 0x400)" in r.stdout, r.stdout[-2000:]
    assert "degenerate:" not in r.stdout


def test_q33_parentchild_v_prints_the_file_id():
    r = _run(RAPY, _img(MINI34), "parentchild", "-v")
    assert "Volume Direct IO File  (file id 0x100)" in r.stdout, r.stdout[-2000:]
    assert "flags=0x" not in r.stdout


def test_c1_10_one_table_of_system_object_names():
    """C1-10: the path labels and the long names come from one table; refsanalysis takes forefst's."""
    assert F.KNOWN_SYSTEM_OIDS.keys() == F.SYSTEM_OID_NAMES.keys() == F._KNOWN_OIDS.keys()
    assert RA._KNOWN_OIDS is F._KNOWN_OIDS
    assert not hasattr(RA, "_PC_OID_NAMES")
    assert RA._pc_oid_name(0x9) == "Logfile Information Table"


def test_c1_14_a_pairs_copies_have_distinct_path_labels():
    for a, b in ((0x7, 0x8), (0x9, 0xA), (0x500, 0x501), (0x540, 0x541)):
        la, lb = F.KNOWN_SYSTEM_OIDS[a], F.KNOWN_SYSTEM_OIDS[b]
        assert la != lb and la.endswith("(0x%x)" % a) and lb.endswith("(0x%x)" % b), (la, lb)
        assert F._KNOWN_OIDS[a] == F._KNOWN_OIDS[b]          # one table, two copies


def test_cb9_no_primary_or_duplicate_label():
    """CB-9: 0x500 / 0x501 and 0x540 / 0x541 are failover pairs like the others; no label says 'pri' or 'dup'."""
    names = list(F.KNOWN_SYSTEM_OIDS.values()) + list(F._KNOWN_OIDS.values())
    assert not [n for n in names if re.search(r"\b(pri|dup|primary|duplicate)\b", n, re.I)], names
    for src in (FOREFST, RAPY):
        with open(src, encoding="utf-8") as fh:
            s = fh.read()
        assert '"VolumeInfo(pri)"' not in s and '"Reparse Index (dup)"' not in s and '"Volume Info (dup)"' not in s


def test_c1_14_the_pairs_are_named_in_the_drivers_order():
    assert F.REQUIRED_STRUCTURES["upcase"][1] == F.SYSTEM_TABLE_PAIRS["upcase"][1] == (0x8, 0x7)
    with open(FOREFST, encoding="utf-8") as fh:
        s = fh.read()
    assert "(OID 0x9 and OID 0xa)" not in s and "(OID 0xa and OID 0x9)" in s


def test_cb4_the_codec_is_named_by_the_format_versions_driver():
    n = RA._comp_fmt_name
    assert (n(0, 3, 14), n(1, 3, 14), n(2, 3, 14), n(3, 3, 14)) == ("none", "LZ4", "ZSTD", "LZ4QAT")
    assert (n(2, 3, 4), n(3, 3, 4), n(4, 3, 4), n(5, 3, 4)) == ("LZNT1", "XPRESS", "XPRESS_HUFF", "LZX")
    assert n(2, 3, 15) == "ZSTD"                                         # 3.14 and later: 26100's numbering
    assert "no ReFS 3.9 driver was read" in n(2, 3, 9) and n(0, 3, 9) == "none"
    assert n(1, 3, 4).startswith("unknown")                              # 17134 has no 1


def test_we8_the_sd_control_word_is_hex_first_names_joined_by_bar():
    assert F.flag_text(0x9004, F._SD_CONTROL_FLAGS) == "0x9004 (SE_DACL_PRESENT|SE_DACL_PROTECTED|SE_SELF_RELATIVE)"
    r = _run(FOREFST, _img(MINI314), "security", "-v")
    ctl = [l for l in r.stdout.splitlines() if l.strip().startswith("Control:")]
    assert ctl and not [l for l in ctl if ", SE_" in l], ctl[:3]


def _printed_literals(path):
    """Every string literal of `path` that is not a docstring and not a `_MODULE_REGISTERS` description."""
    with open(path, encoding="utf-8") as fh:
        t = ast.parse(fh.read())
    skip = set()
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and n.body \
                and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant):
            skip.add(id(n.body[0].value))
        if isinstance(n, ast.Assign) and any(getattr(x, "id", None) == "_MODULE_REGISTERS" for x in n.targets):
            skip.update(id(c) for c in ast.walk(n.value) if isinstance(c, ast.Constant))
    return [(n.lineno, n.value) for n in ast.walk(t)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip]


@pytest.mark.parametrize("tool", [FOREFST, RAPY], ids=["forefst", "refsanalysis"])
def test_wd3_no_internal_id_in_a_printed_string(tool):
    """WD-3 (N488): no finding id or erratum number in a string the tools can print (decision: docs and tool text carry
    no ids)."""
    bad = [(ln, v[:90]) for ln, v in _printed_literals(tool)
           if re.search(r"\b(E\d{1,3}|N\d{3}|K\d{3}|WC-\d|WD-\d|WE-\d|CB-\d+|RC-\d+)\b|erratum", v)]
    assert not bad, bad[:8]


def test_we4_timestomps_journal_line_uses_the_state_word():
    st = {"seqs": [{"lo": 0, "hi": 9, "first_ts": 133000000000000000, "last_ts": 133000000100000000,
                    "min_ts": 133000000000000000}], "steps": 0}
    assert F._usn_coverage_lines(st)[0].startswith("Active; it starts at USN 0")
    assert F._usn_coverage_lines({"seqs": [], "steps": 0})[0].startswith("Active, but it holds no record")
    two = {"seqs": st["seqs"] * 2, "steps": 0}
    assert F._usn_coverage_lines(two)[0].startswith("Active; its numbering restarted")


@pytest.mark.parametrize("args,word,max_rest", [
    (["files", "--csv", "-", "extra"], "extra", "options only"),
    (["files", "extra", "--csv", "-"], "extra", "options only"),
    (["search", "foo", "bar"], "bar", "one argument"),
], ids=["after-options", "before-options", "search-two-words"])
def test_we5_a_stray_word_gets_the_one_rule(args, word, max_rest):
    r = _run(FOREFST, _img(MINI314), *args)
    assert r.returncode == 1
    assert "unexpected argument: '%s' (this command takes %s)" % (word, max_rest) in r.stderr, r.stderr[-800:]
    assert "usage:" not in r.stderr


def test_we5_an_unknown_option_keeps_argparses_error():
    r = _run(FOREFST, _img(MINI314), "files", "--bogus")
    assert r.returncode == 1 and "unrecognized arguments: --bogus" in r.stderr, r.stderr[-800:]


# ==== G1: pair readers and boot-sector fields =======================================================================

def _ct_copy(rel):
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(rel)
    sel = F.checkpoint_select(f, ps, cs, cl, require_roots=True)
    return F.container_table_copy(f, ps, cs, sel["in_use"]["raw"], sel["in_use"]["roots"]), (f, ps, cs, roots)


def test_cb11_a_healthy_volume_reads_root_7_and_says_nothing():
    c, _ = _ct_copy(MINI314)
    assert (c["state"], c["index"], c["text"], c["flags"]) == ("primary", 7, None, [])


def test_cb11_root_8_is_read_when_root_7_fails():
    """step5/testchecksums: root 7 (id 0x0b) fails its digest, root 8 passes -- refs.sys reads root 8; 1.13.1 read root 7."""
    c, _ = _ct_copy(CORRUPT_CT)
    assert (c["state"], c["index"]) == ("duplicate", 8), c
    assert "its first copy, root 7" in c["text"] and "second copy, root 8" in c["text"]


def test_cb11_cb3_both_copies_fail_and_carry_bit_8():
    c, _ = _ct_copy(MILLIONS)
    assert (c["state"], c["index"]) == ("neither", 7), c
    assert len(c["flags"]) == 2 and all("bit 0x8" in t for t in c["flags"]), c["flags"]


def test_cb11_without_a_checkpoint_copy_root_7_is_taken():
    c, (f, ps, cs, roots) = _ct_copy(MINI314)
    assert F.container_table_copy(f, ps, cs, None, roots)["index"] == 7


def test_cb11_bootstrap_says_which_copy_it_reads():
    r = _run(FOREFST, _img(CORRUPT_CT), "fastsummary")
    assert "Container Table: its first copy, root 7" in r.stderr, r.stderr[-2000:]
    assert r.returncode == 2


def test_cb1_the_object_tables_primary_is_root_0():
    assert F._select_ot_root_index(None, 0, 4096, None, [[5], [9]]) == 0
    assert F._select_ot_root_index(None, 0, 4096, None, []) == 0


def test_s3_bit_8_is_a_redundancy_condition_not_a_view_finding(monkeypatch):
    """Review S3: bit 0x8 on a Container Table / Object Table root is V-a's, as the same bit on the system-table pairs:
    no finding of the view (1.14.0's first form made every command exit 2), a redundancy condition of the summaries."""
    monkeypatch.setattr(F, "_FINDINGS", [])
    monkeypatch.setattr(F, "_VIEW_FINDINGS", [])
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MILLIONS)
    assert not [t for _k, t in F._FINDINGS if "bit 0x8" in t], F._FINDINGS
    red = F.system_table_findings(f, ps, cs, tr, om)
    assert len([t for t in red if "Container Table's root" in t and "bit 0x8" in t]) == 2, red


def _s2_chk(cktype, stored):
    chk = bytearray(0x200)
    struct.pack_into("<I", chk, 0x78, 0)                          # the direct root-offset list at +0x94
    struct.pack_into("<I", chk, 0x94, 0x100)                      # root 0's descriptor at +0x100
    struct.pack_into("<4Q", chk, 0x100, 0x1000, 0, 0, 0)          # its reference: LCN 0x1000
    chk[0x100 + 0x22] = cktype
    if cktype == 2:
        struct.pack_into("<Q", chk, 0x100 + 0x28, stored)
    return bytes(chk)


def _s2_page(own):
    pg = bytearray(16384)
    pg[:4] = b"MSB+"
    struct.pack_into("<4Q", pg, 0x20, own, 0, 0, 0)
    struct.pack_into("<I", pg, 0x50, 0x4000)                      # no rows: the walk stops after the tests
    return bytes(pg)


@pytest.mark.parametrize("cktype,own,bad,listed", [(2, 0x2000, 1, ["CRC64"]), (0, 0x2000, 1, ["address"]),
                                                    (0, 0x1000, 0, [])],
                         ids=["digest-fails-and-wrong-address", "no-checksum-wrong-address", "control"])
def test_s2_a_wrong_address_page_reaches_the_verdict_once(monkeypatch, cktype, own, bad, listed):
    """Review S2 (the reviewer's probe as a node): on a volume without page checksums the wrong address is the only
    test and it now counts; a page whose digest already failed is listed once."""
    monkeypatch.setattr(F, "_read_full_page", lambda f, ps, cs, slots, use_tr: _s2_page(own))
    st = F._verify_page_checksums(None, 0, 4096, None, _s2_chk(cktype, 0x1234), 0x68, 1, full=False)
    assert st["crc64_bad"] + st["sha_bad"] + st["wrong_address"] == bad, st
    assert [m[3] for m in st["mismatches"]] == listed, st["mismatches"]


def test_cb3_the_root_descriptor_bit():
    pg = bytearray(b"MSB+" + b"\0" * 0x60)
    assert not F._root_flag_bit(bytes(pg))
    pg[0x58] = 0x08
    assert F._root_flag_bit(bytes(pg))
    pg[:4] = b"\0\0\0\0"
    assert not F._root_flag_bit(bytes(pg))                       # not a B+ page: no descriptor to test


def test_cb2_the_superblock_payload_masks_the_copys_clocks():
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    blk = bytearray(F._seek_read(f, ps + F.SUPB_LCN * cs, cs))
    a = bytearray(blk)
    a[0x10:0x20] = b"\x11" * 16                                   # another write's clocks
    assert F._supb_payload(bytes(a)) == F._supb_payload(bytes(blk))
    b = bytearray(blk)
    b[0x50] ^= 0xFF                                               # the volume GUID: shared, still compared
    assert F._supb_payload(bytes(b)) != F._supb_payload(bytes(blk))


def test_cb5_bytes_per_sector_is_the_u32_the_driver_tests():
    def v(bps):
        b = bytearray(512)
        struct.pack_into("<I", b, 0x20, bps)
        return bytes(b)
    assert [F._vbr_bytes_per_sector(v(x)) for x in (512, 0x600, 4096, 0x1000)] == [512, 0x600, 4096, 4096]
    assert F._vbr_bytes_per_sector(v(0x10200)) == 512            # u16 0x200, but the u32 is out of range
    assert F._vbr_bytes_per_sector(v(0x100)) == 512 and F._vbr_bytes_per_sector(b"\0" * 0x20) == 512


def _long_boot_copy(n=1024):
    """win11refsmini's boot sector with +0x14 = n (> 512, legal on a 4Kn device) and its checksum made over n bytes."""
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    b = bytearray(F._seek_read(f, ps, 512)) + bytearray(n - 512)
    struct.pack_into("<H", b, 0x14, n)
    struct.pack_into("<H", b, 0x16, F._vbr_checksum(bytes(b), n))
    return bytes(b)


def test_c2_6_one_checksum_over_the_copys_own_length():
    b = _long_boot_copy()
    stored, computed = F.boot_sector_checksum(b)
    assert stored == computed == F._vbr_checksum(b, 1024)
    assert F.boot_sector_checksum(b[:512])[1] is None             # 512 bytes cannot carry a 1024-byte sum


def test_c2_6_no_checksum_over_an_out_of_range_length():
    b = bytearray(_long_boot_copy()[:512])
    struct.pack_into("<H", b, 0x14, 0x40)
    assert F.boot_sector_checksum(bytes(b))[1] is None
    struct.pack_into("<H", b, 0x14, 512)
    assert F.boot_sector_checksum(bytes(b))[1] == F._vbr_checksum(bytes(b), 512)   # the control


def test_c2_6_refsanalysis_reads_and_shows_a_long_copy(tmp_path):
    img = tmp_path / "long_vbr.raw"
    with open(img, "wb") as fh:
        fh.write(_long_boot_copy())
        fh.truncate(8 << 20)
    with open(img, "rb") as fh:
        assert len(RA._read_boot_copy(fh, 0)) == 1024
    r = _run(RAPY, str(img), "bootedit", "read", "--partition-start", "0")
    assert "Traceback" not in r.stderr, r.stderr[-1500:]
    assert "[OK]" in r.stdout and "MISMATCH" not in r.stdout, r.stdout[-1500:]


# ==== G2: checkpoint selection ======================================================================================

def test_c2_2_a_backups_version_is_not_used_for_the_record_tests(monkeypatch):
    rec = {"source": "backup", "bytes": b"\0" * 0x28 + bytes([3, 4]) + b"\0" * 0x1d6}
    monkeypatch.setattr(F, "boot_sector_copy", lambda f, ps, fresh=False: rec)
    assert F._chkp_volume_version(None, 0) is None
    rec = dict(rec, source="primary")
    assert F._chkp_volume_version(None, 0) == (3, 4)              # the control: the primary's version is used


def test_c2_2_a_volume_read_from_its_backup_says_the_tests_are_not_made(tmp_path):
    src = _img(MINI314)
    f, ps, cs, tr, roots, om, vj, vn, cl = F.bootstrap(src)
    dst = _sparse_copy(src, str(tmp_path / "zero_sector0.raw"))
    _write_at(dst, ps, b"\0" * 512)
    r = _run(FOREFST, dst, "fastsummary")
    assert "not made with its version (3.14)" in r.stderr, r.stderr[-2000:]
    assert "no checkpoint copy passes the tests refs.sys makes" not in r.stderr
    assert r.returncode == 2


def test_c2_7_the_drivers_sum_width():
    assert F._chkp_sum(0xFFFFFFF0, 0x20, "26100") == 0x10
    assert F._chkp_sum(0xFFFFFFF0, 0x20, "17134") == 0x10
    assert F._chkp_sum(0xFFFFFFF0, 0x20, "29574") == 0x100000010
    assert F._chkp_sum(0x100, 0x20, "26100") == 0x120               # no wrap: the same


def test_c2_7_a_wrapping_offset_table_passes_26100_and_fails_insider():
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    raw = bytearray(F.checkpoint_select(f, ps, cs, cl, require_roots=True)["in_use"]["raw"])
    if not F.le32(raw, 0x78) & 0x200:
        pytest.skip("this record has no indirect offset table")
    t94 = F.le32(raw, 0x94)
    struct.pack_into("<I", raw, 0x98, (0x100000000 - t94 + 0x10) & 0xFFFFFFFF)   # +0x94 + +0x98 wraps to 0x10
    keys = lambda b: [k for k, _t, _x in F._chkp_build_failures(bytes(raw), cs, b, (3, 14))]   # noqa: E731
    assert "table-end" not in keys("26100") and "table-end" in keys("29574")


def test_q40_the_version_clause_rejects_on_a_volume_below_3_11():
    """Q40 (read at instruction level on 26100.8115, 26100.9711 and Insider 29574): `VersionCheck(0x30b)`'s operand is
    the boot sector's version, so a record with the indirect offset table on a volume whose boot sector records 3.10 is
    rejected by 26100 and Insider (the batch's review M2 had stated the clause "not determined" until this reading)."""
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    raw = bytes(F.checkpoint_select(f, ps, cs, cl, require_roots=True)["in_use"]["raw"])
    if not F.le32(raw, 0x78) & 0x200:
        pytest.skip("this record has no indirect offset table")
    t = F.chkp_record_tests(raw, cs, (3, 10))
    assert t["rejected_by"] == ["26100", "29574"], t["fails"]
    assert [k for k, _x, _b in t["fails"]["26100"]] == ["table-version"], t["fails"]
    assert "needs a volume of version 3.11 or later; the boot sector records 3.10" in t["fails"]["26100"][0][1]
    assert "undetermined" not in t


def test_q40_control_a_3_14_volume_is_not_rejected():
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    raw = bytes(F.checkpoint_select(f, ps, cs, cl, require_roots=True)["in_use"]["raw"])
    t = F.chkp_record_tests(raw, cs, (3, 14))
    assert not t["rejected_by"], t["fails"]


def test_we3_a_copy_the_image_ends_inside_is_not_taken():
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    last = max(cl)
    f.seek(0)
    head = f.read(ps + last * cs + cs // 2)                        # the image ends inside the last copy
    sel = F.checkpoint_select(io.BytesIO(head), ps, cs, cl, require_roots=True)
    rec = [c for c in sel["copies"] if c["lcn"] == last][0]
    assert rec["unreadable"] == "the image ends inside it (%d of %d bytes read)" % (cs // 2, cs), rec["unreadable"]
    assert rec not in sel["cands"] and not rec["sig_ok"]


def test_q4_the_feature_gated_tests_name_9711():
    assert F._CHKP_FEATURE_BUILDS == "26100.8972, .9444, .9549 and .9711"


# ==== G3: bounds wording ============================================================================================

def test_c2_3_the_bound_is_the_volume_when_n_is_not_known():
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    blk = bytearray(F._seek_read(f, ps + F.SUPB_LCN * cs, cs))
    o = F.le32(blk, 0x70)
    struct.pack_into("<q", blk, o, 5)                              # a checkpoint reference below 0x1f
    t = " ".join(x for _k, x in F.supb_validate(bytes(blk), cs, F.SUPB_LCN, None)["failures"])
    assert "outside 0x1f..the volume" in t and "0x-" not in t, t


def test_c2_3_parse_supb_does_not_take_n_from_a_failed_total(monkeypatch):
    seen = {}
    real = F.supb_validate
    def spy(blk, cs, lcn=None, n=None):
        seen.setdefault("n", n)
        return real(blk, cs, lcn, n)
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    bsc = dict(F.boot_sector_copy(f, ps), failures=[("total_sectors", "its total sectors (+0x18) is 0")],
               source="primary")
    monkeypatch.setattr(F, "boot_sector_copy", lambda f, ps, fresh=False: bsc)
    monkeypatch.setattr(F, "supb_validate", spy)
    F.parse_supb(f, ps, cs, say=False)
    assert seen["n"] is None


def test_c2_4_max_scan_before_the_image_end_is_no_finding(monkeypatch):
    monkeypatch.setattr(F, "volume_clusters", lambda f, ps, cs: 1000)
    before = len(F._findings())
    img = io.BytesIO(b"\0" * (500 * 4096))                         # the image ends at cluster 500 of 1000
    assert F._orphan_scan_bound(img, 0, 4096, 100)[3] is None      # --max-scan 100 stops first
    assert len(F._findings()) == before
    assert F._orphan_scan_bound(img, 0, 4096, None)[3] == 500       # the control: the image's end stops it
    assert F._orphan_scan_bound(img, 0, 4096, 800)[3] == 500


def test_c2_5_the_preflight_names_the_range_searched(tmp_path):
    img = tmp_path / "zeros.raw"
    with open(img, "wb") as fh:
        fh.truncate(200 << 20)
    r = _run(RAPY, str(img), "summary")
    assert r.returncode == 1 and "searched offset 0x" in r.stderr, r.stderr[-800:]
    r2 = _run(RAPY, str(img), "summary", "--partition-start", "0")
    r3 = _run(FOREFST, str(img), "summary", "--partition-start", "0")
    msg = lambda s: s.strip().splitlines()[-1].split("error: ", 1)[-1]   # noqa: E731
    assert r2.returncode == r3.returncode == 1 and msg(r2.stderr) == msg(r3.stderr), (r2.stderr, r3.stderr)
    assert "use --partition-start" not in r2.stderr


# ==== G4: run registers read as the view's ==========================================================================

def test_c1_3_incomplete_is_this_views():
    F._new_view()
    assert not F._metadata_incomplete()
    F._walk_note_damage("test", "a planted note")
    assert F._metadata_incomplete()
    F._new_view()                                                  # the next view starts clean ...
    assert not F._metadata_incomplete()
    assert F._WALK_DAMAGE.total > 0                                # ... while the run keeps its count (exit code)


def test_c1_4_the_journal_lookup_is_this_views():
    F._new_view()
    F._skip_note("locate_change_journal: test", "a planted skip", ValueError("x"), limit=0)
    assert F._journal_lookup_was_incomplete() and F._journal_unreadable_or_wiped()
    F._new_view()
    assert not F._journal_lookup_was_incomplete()


def test_c1_6_each_bulk_export_starts_empty(tmp_path):
    F._HOLE_STREAMS.append({"file": str(tmp_path / "a"), "what": "a", "hole_bytes": 4096})
    F._bulk_hole_finish(str(tmp_path))
    assert not F._HOLE_STREAMS and not F._UNDET_STREAMS and not F._HOLE_REFUSALS
    d2 = tmp_path / "second"
    d2.mkdir()
    F._bulk_hole_finish(str(d2))
    with open(d2 / "holes.json") as fh:
        assert json.load(fh)["Status"] == "none"


def test_c1_5_the_bundle_judges_only_its_own_image(tmp_path, monkeypatch):
    own = tmp_path / "rehydrated.raw"
    other = tmp_path / "other.raw"
    for p in (own, other):
        with open(p, "wb") as fh:
            fh.truncate(1 << 20)                                   # one hole
    monkeypatch.setattr(F, "_BUNDLE", {"dir": str(tmp_path), "manifest": {}, "image": str(own)})
    with open(other, "rb") as fo, open(own, "rb") as fw:
        assert F._bundle_of(fo) is None and F._bundle_of(fw) is F._BUNDLE
        assert F._image_hole_state(fo, 0, 4096, 0, 4096) == "hole"
        assert F._image_hole_state(fw, 0, 4096, 0, 4096) == "bundle-absent"


# ==== G5: statements over a table read in part =======================================================================

def test_c1_8_a_walk_from_a_missing_root_directory_says_so_once(capsys):
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    F._new_view()
    del om[0x600]
    capsys.readouterr()
    assert F.walk_directory_tree(f, ps, cs, tr, om, 0x600, 10, False) == []
    F.walk_directory_tree(f, ps, cs, tr, om, 0x600, 10, False)
    err = capsys.readouterr().err
    assert err.count("the root directory (OID 0x600)") == 1, err


def test_c1_9a_the_volume_information_reader_says_why():
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    vi, why = F.volume_information_read(f, ps, cs, tr, om, "test")
    assert why is None and vi.get("vol_create_time")
    del om[0x500]
    vi, why = F.volume_information_read(f, ps, cs, tr, om, "test")
    assert vi == {} and "not in the Object Table, which was read in full" in why, why


def test_c1_7_c1_13_one_reader_of_the_row():
    for name in ("_volume_times", "_ts_vol_times"):
        assert not hasattr(F, name), name
    with open(FOREFST, encoding="utf-8") as fh:
        assert len(re.findall(r"le16\(kd, 0\) == 0x0?520", fh.read())) <= 3   # the reader, fs_metadata and one more


def test_we6_timeline_states_the_mlog_rows_without_a_time():
    # RC3b item 1 (N646): with each record read where its value keeps its times, none of win11refs2tspecials' 33 rows
    # predates the volume any more (the old rule read a forged Created or an index entry's Accessed); the rows that
    # still do are files whose every time is older than the volume (package dates), on the two system drives
    r = _run(FOREFST, _img("step7/winsiderv2.raw"), "timeline", "--source", "MLOG")
    # F5 (1.14.1): 4 of the 7 were partial-row UpdateRows dated by a file's inline bytes (1974 / 1988 / 2003); they are
    # not dated now (analysis/reports/v1.14.1/F5/f5_rows_changed.tsv, winsiderv2 blocks 0x3c9d2, 0x41229, 0x4122d, 0x44c50)
    assert re.search(r"\b3 MLog row\(s\) carry no time: the time derived for each is earlier than the volume's "
                     r"creation", r.stdout), r.stdout[:3000]
    assert "are not compared with the volume's creation time" not in r.stdout


def test_c1_9b_the_previous_checkpoint_comparison_words():
    with open(FOREFST, encoding="utf-8") as fh:
        s = fh.read()
    assert "Object Table root is identical in both checkpoints" not in s
    r = _run(FOREFST, _img(MINI314), "deleted")
    assert r.returncode in (0, 2) and "Traceback" not in r.stderr
    assert "Same files and paths in both checkpoints" in r.stdout          # the control: both trees read in full


def test_c1_9b_a_comparison_read_in_part_says_what_the_objects_read_show():
    """win11refs2tmillionsofactions: both checkpoints' Object Tables are read in part (image holes). 1.13.2 said "Same
    files and paths in both checkpoints"; the batch's first wording said only what the comparison covers, so a reader
    could not tell that no difference was found among the objects read."""
    r = _run(FOREFST, _img(MILLIONS), "deleted")
    assert r.returncode == 2, (r.returncode, r.stderr[-1500:])
    assert "Same files and paths in both checkpoints" not in r.stdout
    assert re.search(r"No file or path differs between the two checkpoints among the objects read \(content and "
                     r"metadata are not compared\); the comparison covers the objects read only: the current Object "
                     r"Table, read in part; the previous checkpoint's Object Table, read in part; a page of the two trees "
                     r"could not be read, so an "
                     r"object on a page not read is not compared", r.stdout), r.stdout[:4000]


def test_c1_9c_parentchild_verify_over_an_unread_table(tmp_path):
    src = _img(MINI314)
    f, ps, cs, tr, roots, om, vj, vn, cl = F.bootstrap(src)
    dst = _sparse_copy(src, str(tmp_path / "pc.raw"))
    for v in roots[4]:                                             # the Parent-Child Table's root page
        _write_at(dst, ps + tr.tr(v) * cs, b"\0" * cs)
    r = _run(RAPY, dst, "parentchild", "--verify")
    assert "[WARN] Parent-Child Table: not determined" in r.stdout, r.stdout[-2000:]
    assert "[OK] No multi-parent entries" not in r.stdout and "[FAIL] Parent-Child Table is empty" not in r.stdout


def test_c1_9g_an_unchecked_primary_is_noted(monkeypatch):
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    raw = F.checkpoint_select(f, ps, cs, cl, require_roots=True)["in_use"]["raw"]
    def unchecked(f, ps, cs, raw, unchecked=None, unchecked_why=None, roots=(), tr=None, copy_words=""):
        if unchecked_why is not None:
            unchecked_why.extend((i, "a checksum type this tool cannot verify") for i in roots)
        return []
    monkeypatch.setattr(F, "_chkp_root_failures", unchecked)
    c = F.object_table_copy(f, ps, cs, tr, raw, roots)
    assert c["state"] == "primary" and "cannot be verified" in c["note"], c       # N362's words (the review N1)


def test_c1_12_a_row_missing_from_a_copy_read_in_part():
    a = {"oid": 0xA, "state": "ok", "rows": [(b"\x01\0\0\0", b"v")]}
    b = {"oid": 0x9, "state": "partial", "rows": []}
    n, w = F._system_table_rows_differ(a, b)
    assert n == 1 and "not among the rows read of OID 0x9, which was read in part" in w, w
    n, w = F._system_table_rows_differ(a, dict(b, state="ok"))
    assert "only in OID 0xa" in w                                  # the control: a copy read in full


def test_wc7_the_unverified_warning_names_the_row(capsys):
    t = {"name": "x.bin", "file_attrs": 0x8000, "extents": [{}]}
    F._integrity_unverified_said(t, None, why=["row at +0x0: flags bit 0x80=1 but row_size=24 (24+4*1 would be 28)"])
    err = capsys.readouterr().err
    assert "(row at +0x0: flags bit 0x80=1 but row_size=24" in err, err


# ==== G7: readers' address checks ===================================================================================

def _page_with(own):
    pg = bytearray(b"MSB+" + b"\0" * 0x60)
    for i, x in enumerate(own):
        struct.pack_into("<Q", pg, 0x20 + 8 * i, x)
    return bytes(pg)


def test_wc5_the_one_address_test():
    assert F._page_address_mismatch(_page_with([0x10, 0x11]), [0x10, 0x11]) is None
    assert F._page_address_mismatch(_page_with([0x10, 0x11]), [0x20, 0x21]) == ([0x10, 0x11], [0x20, 0x21])
    assert F._page_address_mismatch(_page_with([]), [0x20]) == ([], [0x20])
    assert F._page_address_mismatch(_page_with([0x10]), None) is None          # no reference names the page
    assert "records the address 0x10, not 0x20" in F._page_address_text([0x10], [0x20])


def _tr(m, cpc=0x4000, skipped=None, lengths=None):
    tr = F.Translator(m, cpc, skipped)
    if lengths:
        tr.ct = {"rows": {i: {"length": n} for i, n in lengths.items()}}
    return tr


def test_c3_3_an_offset_past_the_containers_range_is_not_mappable():
    tr = _tr({2: 0x100000}, lengths={2: 0x10})
    base = 2 << tr.shift
    assert F._vlcn_mappable(tr, base + 0x5) and not F._vlcn_mappable(tr, base + 0x20)
    assert F._vlcn_mappable(_tr({2: 0x100000}), base + 0x20)        # no length known: as before


def test_c3_3_tr_says_it_once(capsys):
    """Read linearly and said once per container, as a finding whose words say it was READ (the review N7: it was a
    skip note, "skipped")."""
    tr = _tr({2: 0x100000}, lengths={2: 0x10})
    base = 2 << tr.shift
    n = len(F._FINDINGS)
    assert tr.tr(base + 0x20) == 0x100020 and tr.tr(base + 0x21) == 0x100021
    assert len(F._FINDINGS) == n + 1 and "it is read linearly" in F._FINDINGS[-1][1]
    assert "skipped" not in capsys.readouterr().err


def test_wc3_below_the_first_container_is_the_tables_first_id():
    tr = _tr({3: 0x100000}, skipped={2: "planted"})
    assert not F._vlcn_mappable(tr, (2 << tr.shift) + 1)           # container 2 is the table's, not "below" it
    assert F._vlcn_mappable(tr, (1 << tr.shift) + 1)               # below the first id: physical
    assert F._vlcn_mappable(tr, (3 << tr.shift) + 1)


def test_wc6_the_magic_note_is_said_once(capsys):
    F._new_view()
    F._orphan_magic_unknown_said("--full")
    F._orphan_magic_unknown_said("--full")
    err = capsys.readouterr().err
    assert err.count("the volume's format magic could not be read") == 1, err


# ==== G8 / G9 ======================================================================================================

def test_cb7_the_allocator_and_the_boot_sector_disagree(monkeypatch):
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    n = F.volume_clusters(f, ps, cs)
    s = [0] * 48
    for span, ok in ((n - 64, True), (n + 64, False), (n, True)):
        s[1], s[2] = span, 10
        monkeypatch.setattr(F, "alloc_read_summary", lambda *a, **k: tuple(s))
        st = {}
        cap = F.alloc_capacity(f, ps, cs, tr, roots, status=st)
        if not ok:
            assert cap is None and "more than the %d clusters the boot sector gives" % n in st["reason"]
        elif span < n:
            assert "64 fewer than the %d clusters" % n in cap["length_disagreement"]
        else:
            assert "length_disagreement" not in cap                  # the control: equal on every corpus volume


# ==== C1-15: an unused system-table copy's damage stays out of the view's ========================================

def _zero_copy(tmp_path, oid):
    src = _img(MINI314)
    f, ps, cs, tr, roots, om, vj, vn, cl = F.bootstrap(src)
    dst = _sparse_copy(src, str(tmp_path / ("zero_%x.raw" % oid)))
    for v in om[oid]:
        _write_at(dst, ps + tr.tr(v) * cs, b"\0" * cs)
    return dst


def test_c1_15_mlog_stats_states_the_unused_logfile_copy_and_exits_2(tmp_path):
    """OID 0x9 (slot 1, not in use) unreadable: `mlog --stats` reports redundancy (LB39 / V-a: exit 2), reads the log
    through OID 0xa, and the page is NOT the view's damage (no 'could not be read ... INCOMPLETE' summary)."""
    r = _run(FOREFST, _zero_copy(tmp_path, 0x9), "mlog", "--stats")
    assert r.returncode == 2, r.stderr[-1500:]
    assert "copy OID 0x9 (root page PLCN" in r.stdout + r.stderr and "the table is read from OID 0xa" in r.stdout + r.stderr
    assert "metadata page(s) could not be read" not in r.stderr, r.stderr[-1500:]


def test_c1_15_ra_upcase_notes_the_unused_copy_with_its_exit_unchanged(tmp_path):
    """OID 0x7 (slot 1) unreadable: refsanalysis `upcase` reads OID 0x8 in full, NOTEs the copy, exit 0 (V-a: exit 2 only
    in the redundancy commands); the page is not the view's damage."""
    base = _run(RAPY, _img(MINI314), "upcase")
    r = _run(RAPY, _zero_copy(tmp_path, 0x7), "upcase")
    assert r.returncode == 0, r.stderr[-1500:]
    rows = lambda t: re.search(r"Data rows:\s+(\d+)", t).group(1)            # noqa: E731
    assert rows(r.stdout) == rows(base.stdout)
    assert "NOTE: the Upcase Table is a pair of copies, OID 0x8 and OID 0x7" in r.stderr and "cannot be read" in r.stderr
    assert "metadata page(s) could not be read" not in r.stderr


def test_c1_15_the_control_a_pair_read_in_full_says_nothing():
    r = _run(RAPY, _img(MINI314), "upcase")
    assert r.returncode == 0 and "NOTE: the Upcase Table" not in r.stderr, r.stderr[-800:]


# ==== WE-9 (test parts): words planted non-zero, values not only keys ==============================================

class _UsnRec:
    usn, timestamp, reason, filename, file_idx, file_oid, parent_oid, file_attrs = 8, 0, 0x100, "a.txt", 1, 0x701, 0x600, 0
    record_length, security_id, parent_idx, offset = 96, 0, 0, 0


def test_we9_usn_source_info_planted_non_zero_is_names_and_hex():
    """Every corpus record's SourceInfo is 0, so the corpus nodes cannot fail: a planted word."""
    for v, names in ((0x5, "DATA_MANAGEMENT|REPLICATION_MANAGEMENT"), (0x12, "AUXILIARY_DATA|0x10"), (0, "0x0")):
        r = _UsnRec()
        r.source_info = v
        rec = F._usn_record(r, {}, {})
        assert (rec["source_info"], rec["source_info_hex"]) == (names, "0x%x" % v), rec


def test_we9_symlink_flags_planted_non_zero_are_names_and_hex():
    assert F.flag_cells(0x1, F._SYMLINK_FLAGS) == ("SYMLINK_FLAG_RELATIVE", "0x1")
    assert F.flag_cells(0x3, F._SYMLINK_FLAGS) == ("SYMLINK_FLAG_RELATIVE|0x2", "0x3")      # an unnamed bit is kept
    assert F.flag_cells(0, F._SYMLINK_FLAGS) == ("0x0", "0x0") and F.flag_cells(None, F._SYMLINK_FLAGS) == ("", "")


def test_we9_m1_the_deleted_index_json_values_are_its_csv_cells(capsys):
    """M1 checked the keys only: the JSON VALUES are the CSV cells -- an empty cell is null, every other cell the
    value's text."""
    rows = F._deleted_rows([], [], index=True, ckpt=[("added", [], ["a/b.txt"], "0x704:0x1")],
                           trash=[{"oid": 0x9, "key_hex": "01", "value_hex": "02"}])
    assert rows, "no rows built"
    capsys.readouterr()
    F._emit_records(rows, F.DELETED_INDEX_COLUMNS, "csv", "-")
    cells = list(__import__("csv").DictReader(io.StringIO(capsys.readouterr().out)))
    F._emit_records(rows, F.DELETED_INDEX_COLUMNS, "json", "-")
    doc = json.loads(capsys.readouterr().out)
    recs = doc if isinstance(doc, list) else next(v for v in doc.values() if isinstance(v, list))
    assert len(recs) == len(cells) == len(rows)
    for c, j in zip(cells, recs):
        assert set(c) <= set(j), sorted(set(c) - set(j))
        for k, cell in c.items():
            v = j[k]
            if cell == "":
                assert v is None or v == [], (k, v)              # null, or an empty list for a list column
            elif isinstance(v, list):                          # a list is the JSON's form of a joined cell
                assert v and all(str(x) in cell for x in v), (k, v, cell)
            elif isinstance(v, bool):
                assert str(v).lower() == cell.lower(), (k, v, cell)
            else:
                assert str(v) == cell, (k, v, cell)


# ==== G8: census first ==============================================================================================

def test_wd1_no_walker_steps_an_extent_row_by_a_guess():
    with open(FOREFST, encoding="utf-8") as fh:
        s = fh.read()
    assert not re.search(r"_extent_row_step\([^)]*\)\)\s*or\s*24", s), "an `or 24` step is back"
    assert s.count("_extent_walk_stop(") == 3                     # the helper and its two walks of a table
    # the third, the sub-record SCAN, declines the candidate instead (no row of it kept)
    body = s.split("def _find_extents_in_subrecord(", 1)[1].split("\ndef ", 1)[0]
    assert "_extent_walk_stop(" not in body and "candidate_extents = []" in body


def test_wd1_the_stop_is_recorded():
    n = len(F._SKIP_FINDING)
    v = bytearray(0x40)
    struct.pack_into("<H", v, 0x0A, 25)                             # a size no row can have
    F._extent_walk_stop("test walker", bytes(v), 0)
    assert len(F._SKIP_FINDING) == n + 1 and F._SKIP_FINDING[-1] == "test walker"
    assert F._extent_row_step(bytes(v), 0, 1) == 0                # the premise: no legal size


class _IdTr(object):
    """A translator stub: every VLCN maps to itself (the scan resolves only an accepted set)."""
    def tr(self, v):
        return v


def _subrecord(rows, header_at=4):
    """A sub-record holding one extent-table candidate at `header_at`: start 0x20, end, capacity 0x100, count, then the
    rows from header_at + 0x20. Each row (vlcn, file_vcn, run, row_size) is 24 bytes; `row_size` goes to +0x0a."""
    n = len(rows)
    v = bytearray(header_at + 0x20 + 24 * n + 0x40)
    struct.pack_into("<II", v, header_at, 0x20, 0x20 + 24 * n)
    struct.pack_into("<I", v, header_at + 12, 0x100)
    struct.pack_into("<I", v, header_at + 20, n)
    for i, (vlcn, fvcn, run, size) in enumerate(rows):
        o = header_at + 0x20 + 24 * i
        struct.pack_into("<QHHII", v, o, vlcn, 0, size, fvcn, 0)
        struct.pack_into("<I", v, o + 20, run)
    return bytes(v)


def _scan(vd, needed):
    res = {"extents": []}
    F._find_extents_in_subrecord(vd, 0, len(vd), needed, _IdTr(), 4096, res, allow_marker_scan=False)
    return [(e["vlcn"], e["file_vcn"], e["clusters"]) for e in res["extents"]]


def test_wd1_control_the_scan_accepts_a_table_of_legal_rows():
    assert _scan(_subrecord([(0x1000, 0, 2, 24), (0x2000, 2, 1, 24)]), 3) == [(0x1000, 0, 2), (0x2000, 2, 1)]


def test_wd1_the_scan_declines_a_candidate_with_a_row_of_no_legal_size():
    """1.13.2: the illegal row was stepped over by 24 bytes and the candidate kept; WD-1 first made it a recorded skip
    (exit 2) -- wrong for a scan, where it means the candidate is not a table -- and kept the rows before it."""
    n = len(F._SKIP_FINDING)
    assert _scan(_subrecord([(0x1000, 0, 2, 24), (0x2000, 2, 1, 25)]), 3) == []
    assert len(F._SKIP_FINDING) == n                               # a declined candidate is not a skip


def test_wd1_no_part_of_a_declined_candidate_is_accepted():
    """The rows before the illegal one add up to `needed`: the candidate is still declined (the first fix's `break`
    left them in the set, and the total matched)."""
    assert _scan(_subrecord([(0x1000, 0, 3, 24), (0x2000, 3, 1, 25)]), 3) == []


def test_wd1_a_later_candidate_in_the_same_sub_record_is_still_found():
    bad = _subrecord([(0x1000, 0, 2, 24), (0x2000, 2, 1, 25)])
    good = _subrecord([(0x3000, 0, 3, 24)])
    assert _scan(bad + good, 3) == [(0x3000, 0, 3)]


@pytest.fixture(scope="module")
def kf0_vol(tmp_path_factory):
    """The N490 / N491 volume: d/a.txt is a name row whose key flags are 0 (the builder's rows) and whose backing is
    not in the volume."""
    import test_1132_red_b2_wording as W
    return W._dir_volume(str(tmp_path_factory.mktemp("cb_kf0") / "kf0.raw"), [("a.txt", 2)])


def test_we1_dataruns_lists_the_row_files_lists(kf0_vol):
    r = _run(FOREFST, kf0_vol, "dataruns", "--partition-start", "0")
    assert re.search(r"Total files analyzed:\s+1\b", r.stdout), r.stdout[-1500:]      # 1.13.2-dev: 0
    assert re.search(r"Not determined \(the record holding the data was not found\):\s+1\b", r.stdout), r.stdout[-1500:]
    f2 = _run(FOREFST, kf0_vol, "files", "--csv", "-", "--partition-start", "0")
    assert "a.txt" in f2.stdout                                    # the control: `files` listed it already


def test_we2_extract_says_the_data_record_was_not_found(kf0_vol):
    r = _run(FOREFST, kf0_vol, "extract", "/d/a.txt", "--partition-start", "0")
    assert r.returncode == 2, (r.returncode, r.stderr[-1200:])
    assert "the record holding its data" in r.stderr and "was not found" in r.stderr
    assert "file '/d/a.txt' not found" not in r.stderr


def test_we2_the_control_a_name_that_is_not_there(kf0_vol):
    r = _run(FOREFST, kf0_vol, "extract", "/d/nothere.txt", "--partition-start", "0")
    assert r.returncode == 1 and "not found" in r.stderr, (r.returncode, r.stderr[-800:])


def test_wd2_the_live_holder_is_the_0x1000_row():
    """On a volume with snapshots every file whose value holds a live $DATA holder resolves it; the offset carries the
    holder descriptor."""
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot("step3/win11refs2tsnapshots.raw")
    seen = 0
    for oid in [o for o in om if o >= 0x600]:
        for kd, vd in F.walk_bplus(f, ps, cs, tr, om[oid], oid=oid):
            if len(kd) >= 4 and F.le16(kd, 0) == 0x30 and len(vd) > F.NON_RESIDENT_MAX_VALUE \
                    and F.count_snapshots_in_resident(vd):
                off = F._live_holder_offset(vd)
                if off is not None:
                    seen += 1
                    # the holder's value: u32 +0 = the offset of its extent node, +4 = the descriptor 0x00010028 (the
                    # same offset the parser's fallback scan takes: descriptor - 4)
                    assert F.le32(vd, off + 4) == 0x00010028 and off < off + F.le32(vd, off) < len(vd)
    assert seen, "no embedded file with snapshots resolved its live holder"


def test_we7_the_manifest_reads_the_corpus_list_and_counts_versions():
    p = os.path.join(os.path.dirname(REPO), "analysis", "tools", "analysis_scripts", "build_image_manifest.py")
    if not os.path.isfile(p):
        pytest.skip("no analysis/tools in this tree")
    with open(p, encoding="utf-8") as fh:
        s = fh.read()
    assert "glob.glob" not in s and "corpus_images" in s and "snapshot_versions" in s


# ==== M1-Q: the Container Table's two copies compared row by row ====================================================

UPGRADED = "step3/win10to11refs4g.raw"


def _ct_rows_copy(idx, rows, partial=False):
    return {"idx": idx, "plcn": 0x20 + idx, "partial": partial, "rows": rows}


def _ct_val(flags, tail=b"\x00" * 8):
    return b"\x01" * 0x14 + struct.pack("<I", flags) + tail


def test_m1q_the_comparison_names_what_differs():
    """M1-Q: equal copies say nothing; a difference only in the u32 at +0x14 is 'flags' (with the bits); anything else is
    'rows'; a row missing from a copy read in part is "not among the rows read" (C1-12), not "only in"."""
    a = {1: _ct_val(0x4001), 2: _ct_val(0x2000), 3: _ct_val(0)}
    assert F._ct_copies_compare(_ct_rows_copy(7, a), _ct_rows_copy(8, dict(a)), "R") is None
    k, t = F._ct_copies_compare(_ct_rows_copy(7, a), _ct_rows_copy(8, {1: _ct_val(1), 2: _ct_val(0), 3: _ct_val(0)}), "R")
    assert k == "flags" and "of 2 row(s), in bit(s) 0x6000" in t and "container 0x1 (0x4001 in root 7, 0x1 in root 8)" in t
    k, t = F._ct_copies_compare(_ct_rows_copy(7, a), _ct_rows_copy(8, {1: _ct_val(0x4001, b"\x02" + b"\x00" * 7), 2: a[2],
                                                              3: a[3]}), "R")
    assert k == "rows" and "differ in 1 row(s): container 0x1 (+0x18: " in t
    k, t = F._ct_copies_compare(_ct_rows_copy(7, a), _ct_rows_copy(8, {1: a[1], 2: a[2]}), "R")
    assert k == "rows" and "container 0x3 only in root 7 (PLCN 0x27)" in t
    k, t = F._ct_copies_compare(_ct_rows_copy(7, a), _ct_rows_copy(8, {1: a[1], 2: a[2]}, partial=True), "R")
    assert k == "rows" and "container 0x3 is not among the rows read of root 8 (PLCN 0x28), which was read in part" in t
    assert "compared over the rows read: root 8 (PLCN 0x28) was read in part" in t


@pytest.mark.parametrize("rel,said", [
    pytest.param(MILLIONS, "of 1 row(s), in bit(s) 0x4000: container 0xce3 (0x4000 in root 7, 0x0 in root 8)",
                 id="millionsofactions"),
    pytest.param(UPGRADED, "of 55 row(s), in bit(s) 0x6000: container 0x5 (0x4001 in root 7, 0x1 in root 8)",
                 id="win10to11refs4g"),
])
def test_m1q_a_difference_only_in_the_flags_word_is_a_note_of_the_summaries(monkeypatch, rel, said):
    """M1-Q (the maintainer, 2026-11-06): the two corpus shapes (`LD/evidence/ct_copy_flag_bits.txt`) -- an rc-neutral
    note of the summaries' redundancy notes, no redundancy finding, no finding of the view."""
    monkeypatch.setattr(F, "_FINDINGS", [])
    monkeypatch.setattr(F, "_VIEW_FINDINGS", [])
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(rel)
    assert tr.ct_copy_note and said in tr.ct_copy_note and tr.ct_pair_texts == [], tr.ct_copy_note
    assert tr.ct_copy_note in F._redundancy_notes({}, tr)
    assert not [t for t in F.system_table_findings(f, ps, cs, tr, om) if "flags word" in t]
    assert not [t for _k, t in F._FINDINGS if "flags word" in t]


def test_m1q_another_difference_is_a_redundancy_condition_and_a_note_elsewhere(monkeypatch, capsys):
    """M1-Q: a difference outside the flags word is V-a, as two system-table copies that differ: in the summaries'
    redundancy list (exit 2 there), a note on stderr in every command, no finding of the view."""
    orig = F._ct_copy_rows

    def plant(f, ps, cs, roots, idx):
        c = orig(f, ps, cs, roots, idx)
        if c and idx == F._CT_ROOT_PAIR[1]:
            k = min(x for x in c["rows"] if isinstance(x, int))
            v = bytearray(c["rows"][k])
            v[0x18] ^= 1
            c["rows"][k] = bytes(v)
        return c
    monkeypatch.setattr(F, "_ct_copy_rows", plant)
    monkeypatch.setattr(F, "_FINDINGS", [])
    monkeypatch.setattr(F, "_VIEW_FINDINGS", [])
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    assert tr.ct_copy_note is None and len(tr.ct_pair_texts) == 1, (tr.ct_copy_note, tr.ct_pair_texts)
    t = tr.ct_pair_texts[0]
    assert "differ in 1 row(s)" in t and "+0x18: " in t and "the copy refs.sys opens first" in t, t
    assert t in F.system_table_findings(f, ps, cs, tr, om)
    assert ("note: %s." % t) in capsys.readouterr().err
    assert not [x for _k, x in F._FINDINGS if "differ in" in x]


def test_m1q_control_equal_copies_say_nothing():
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    assert tr.ct_copy_note is None and tr.ct_pair_texts == []


def test_m1q_summary_prints_the_note_and_keeps_it_out_of_the_findings():
    """M1-Q through the command: `summary` lists the flags-only difference as a note, and `summary --json` keeps it in
    `RedundancyNotes`, not in `RedundancyFindings`."""
    img = _img(UPGRADED)
    p = _run(FOREFST, img, "summary")
    line = next((l for l in p.stdout.splitlines() if "Container Table's two copies" in l), "")
    assert line.strip().startswith("note:") and "[WARN]" not in line, line
    js = json.loads(_run(FOREFST, img, "summary", "--json").stdout)
    assert any("Container Table's two copies" in n for n in js.get("RedundancyNotes") or []), js.get("RedundancyNotes")
    assert not any("Container Table" in x for x in js.get("RedundancyFindings") or []), js.get("RedundancyFindings")


def test_m1q_a_copy_whose_walk_raises_is_a_recorded_skip_not_a_crash(monkeypatch):
    """M1-Q: the comparison runs in every command's bootstrap; a walk of the copy that raises is recorded (`_skip_note`:
    exit 2, "could not complete") and the copies are not compared -- the command still runs."""
    f0, ps0, cs0, tr0, roots0, *_ = _boot(MINI314)
    r8 = list(roots0[F._CT_ROOT_PAIR[1]])
    orig = F.walk_bplus

    def boom(f, ps, cs, tr, vlcns, *a, **k):
        if tr is None and list(vlcns) == r8:
            raise ValueError("planted")
        return orig(f, ps, cs, tr, vlcns, *a, **k)
    monkeypatch.setattr(F, "walk_bplus", boom)
    seen = []
    monkeypatch.setattr(F, "_skip_note", lambda where, what, e: seen.append((where, what, str(e))))
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    assert tr.ct_copy_note is None and tr.ct_pair_texts == []
    assert ("container_table_copies_differ", "the Container Table's root 8", "planted") in seen, seen


# ==== Q7: checksum type 5 is named XXH64, never computed ===========================================================

def test_q7_type_5_is_named_xxh64_in_both_tools():
    assert F._CKNAME[5] == "XXH64" and RA._CHECKSUM_ALGO_MAP[5] == "XXH64"
    assert "XXH64, which this tool does not compute" in F._CK_NOT_COMPUTED[5] and "(" not in F._CK_NOT_COMPUTED[5]
    assert F._ck_types_words({"0x5": 3}) == "checksum type 0x5 (XXH64)"


def _q7_chk(cktype, dlen):
    chk = bytearray(0x200)
    struct.pack_into("<I", chk, 0x94, 0x100)
    struct.pack_into("<4Q", chk, 0x100, 0x1000, 0, 0, 0)
    chk[0x100 + 0x22] = cktype
    struct.pack_into("<I", chk, 0x100 + 0x24, dlen)
    return bytes(chk)


@pytest.mark.parametrize("cktype,dlen,none,notc", [(5, 8, 0, 1), (3, 8, 0, 1), (0, 0, 1, 0), (5, 0, 1, 0)],
                         ids=["xxh64", "type-3", "control-none", "control-no-digest"])
def test_q7_a_page_whose_checksum_is_not_computed_is_not_counted_as_unchecksummed(monkeypatch, cktype, dlen, none, notc):
    """Q7: a reference that declares a checksum this tool does not compute is counted apart (and leaves the coverage
    incomplete), never with the pages that carry no checksum; the keys exist only where such a page does."""
    monkeypatch.setattr(F, "_read_full_page", lambda f, ps, cs, slots, use_tr: _s2_page(0x1000))
    st = F._verify_page_checksums(None, 0, 4096, None, _q7_chk(cktype, dlen), 0x68, 1, full=False)
    assert st["none"] == none and st.get("not_computed", 0) == notc, st
    if notc:
        assert st["not_computed_types"] == {"0x%x" % cktype: 1}, st
    else:
        assert "not_computed" not in st and "not_computed_types" not in st, st


# ==== Q40 follow-on: the after-choice version test is a message, never a block ======================================

def _q40_sel(major=None, minor=None, version=(3, 14)):
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    sel = F.checkpoint_select(f, ps, cs, cl, require_roots=True)
    raw = bytearray(sel["in_use"]["raw"])
    if major is not None:
        struct.pack_into("<H", raw, 0x50, major)
    if minor is not None:
        struct.pack_into("<H", raw, 0x52, minor)
    sel["in_use"]["raw"] = bytes(raw)
    sel["version"] = version
    return sel, cs


@pytest.mark.parametrize("major,minor,said", [(3, 15, "records version 3.15"), (4, 0, "records version 4.0"),
                                              (3, 0x100, "records version 3.256")],
                         ids=["minor-above", "major-above", "minor-above-0xff"])
def test_q40_a_record_above_the_boot_sectors_version_is_a_view_condition(major, minor, said):
    """The maintainer (2026-11-06): refs.sys 26100 and Insider fail the mount after choosing such a record; the tool
    says so as a condition of the view and reads the volume."""
    sel, cs = _q40_sel(major, minor)
    hit = [(k, lv, t) for k, lv, t in F._checkpoint_conditions(sel, cs) if k[-1] == "record-version"]
    assert len(hit) == 1 and hit[0][1] == "view" and said in hit[0][2], hit
    assert "above the 3.14 its boot sector records" in hit[0][2] and "the volume is read as it is" in hit[0][2]


@pytest.mark.parametrize("major,minor,version", [(None, None, (3, 14)), (3, 14, (3, 14)), (3, 15, None)],
                         ids=["control-equal", "control-same", "control-backup-version-unknown"])
def test_q40_control_no_record_version_condition(major, minor, version):
    sel, cs = _q40_sel(major, minor, version)
    assert not [k for k, _lv, _t in F._checkpoint_conditions(sel, cs) if k[-1] == "record-version"]


# ==== the maintainer's rule: a system-table pair with no copy that passes is read as it is ===========================

def test_rule_a_pair_whose_copies_both_fail_their_digest_is_read_as_it_is(monkeypatch):
    """The maintainer (2026-11-06): neither copy of the Logfile Information Table passes, refs.sys does not open it --
    the tool reads the copy refs.sys opens first as it is, and says so (the summaries' redundancy list; mlog's
    statements)."""
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    monkeypatch.setattr(F, "object_root_digest_matches",
                        lambda oid, page: False if oid in (0x9, 0xA) else None)
    p = F.system_table_pair(f, ps, cs, tr, om, "lit")
    assert p["as_is"] and p["in_use"]["oid"] == 0xA and p["in_use"]["rows"], p["in_use"]["state"]
    t = F.system_table_as_is_text(p)
    assert "neither passes its check" in t and "it is read from OID 0xa, the copy refs.sys opens first, as it is" in t
    assert t in F.system_table_findings(f, ps, cs, tr, om)
    mi = F.get_mlog_info(f, ps, cs, tr, om)
    assert mi["row_len"] is not None, mi                       # the log's place is read from that copy
    monkeypatch.setattr(F, "_FINDINGS", [])
    st = F.mlog_table_statements(F.mlog_open_geometry(f, ps, cs, mi, cl))
    assert [x for x in st if "where refs.sys starts no log" in x], st
    assert [x for k, x in F._FINDINGS if k == "mlog log table" and "where refs.sys starts no log" in x], F._FINDINGS


def test_rule_control_a_pair_that_passes_is_not_read_as_it_is():
    f, ps, cs, tr, roots, om, vj, vn, cl = _boot(MINI314)
    p = F.system_table_pair(f, ps, cs, tr, om, "lit")
    assert not p["as_is"] and p["in_use"]["state"] == "ok"


# ==== E136 (Q38 read twice): the checksum type refs.sys uses, not +0x2A alone ======================================

def _bs(sel, flags):
    b = bytearray(0x200)
    struct.pack_into("<H", b, 0x2A, sel)
    struct.pack_into("<I", b, 0x2C, flags)
    return bytes(b)


@pytest.mark.parametrize("sel,flags,want,note", [
    (2, 0x66, (2, "CRC64"), None), (4, 0x66, (4, "SHA-256"), None), (5, 0x66, (5, "XXH64"), None),
    (0, 0x06, (2, "CRC64"), "+0x2a = 0x0, is not read: its flags, +0x2c = 0x6, lack 0x40"),
    (4, 0x26, (2, "CRC64"), "+0x2a = 0x4, is not read"),
], ids=["0x40-crc64", "0x40-sha256", "0x40-xxh64", "no-0x40-zero", "no-0x40-ignored-sha256"])
def test_e136_the_volume_checksum_type_is_the_selector_refs_sys_derives(sel, flags, want, note):
    t, name, n = F.volume_checksum_type(_bs(sel, flags))
    assert (t, name) == want and (n is None if note is None else note in n), (t, name, n)


@pytest.mark.parametrize("rel,name,noted", [(MINI34, "CRC64", True), (MINI314, "CRC64", False)], ids=["v34", "v314"])
def test_e136_summary_and_integrity_name_the_type_refs_sys_uses(rel, name, noted):
    """The 16 corpus volumes whose flags lack 0x40 printed "none" (+0x2A = 0) while their checkpoint's root references
    declare CRC64 (`LD/evidence/q38_census.jsonl`); they now name CRC64 and say +0x2A is not read."""
    img = _img(rel)
    js = json.loads(_run(FOREFST, img, "fastsummary", "--json").stdout)
    assert js["Checksum"] == name and (("ChecksumSelectorNote" in js) == noted), js.get("ChecksumSelectorNote")
    line = next(l for l in _run(FOREFST, img, "integrity").stdout.splitlines() if "Checksum type:" in l)
    assert name in line and (("is not read" in line) == noted), line


# ==== E141 (A139 / A140): checkpoint flag 0x400 carries no meaning the driver was not read for =====================

def test_e141_checkpoint_flag_0x400_names_no_unread_meaning():
    """No build was read testing or setting the checkpoint record's flag 0x400; it is set on every 3.14 volume of the
    corpus and on none formatted at 3.4-3.10 (`LD/evidence/chkp_flags_census.jsonl`). 1.13.1 named it
    "metadata-checksum (CRC64/SHA-256)"; on 17134 the check follows each page reference's own type (A139)."""
    names = F.chkp_flags_decoded(0x682)
    hit = [n for n in names if n.startswith("0x400 = ")]
    # N554 (1.14.0): E158 read the flag -- it marks the record's rollback-protection fields
    assert hit == ["0x400 = rollback-protection fields (+0x9c offset / +0xa0 length; ReFS 3.13+)"], names
    assert not any("checksum" in n.lower() for n in names), names


# ==== Q15 (A141): $VOLUME_INFORMATION+0xA0 is the last mount that writes, not a modification time ===================

def test_q15_summary_prints_the_volume_time_as_the_last_rw_mount():
    """`SetAndGetVolumeTimes` (RefsMountVolume -> InitializeVolumeInfoTable) writes +0xA0 at a mount whose VCB flag
    0x2000000 is clear; on LAB-L it moved at each of 5 read-write mounts and at no later write and no read-only mount.
    1.13.1 printed it as "Volume modified" (JSON `VolumeModifyTime`); the text and the JSON key name the last mount that
    can write."""
    img = _img(MINI314)
    js = json.loads(_run(FOREFST, img, "fastsummary", "--json").stdout)
    text = _run(FOREFST, img, "summary").stdout
    line = next(l for l in text.splitlines() if l.strip().startswith("Last mount (rw):"))
    assert "VolumeModifyTime" not in js, sorted(js)
    t = js["VolumeLastWritableMountTime"]
    assert t[:19].replace("T", " ") in line.replace("T", " "), (line, t)
    assert "Volume modified" not in text
    ts = json.loads(_run(FOREFST, img, "timestomp", "--json").stdout)
    assert "VolumeLastWritableMount" in json.dumps(ts) and "VolumeModified" not in json.dumps(ts)


# ==== E144 (A145): an embedded record carrying another directory's reference is identified by it ==================

def _er_value(si58, si60, si68):
    v = bytearray(0xA8)
    struct.pack_into("<QQQ", v, 0x80, si58, si60, si68)
    return bytes(v)


@pytest.mark.parametrize("vals,want", [
    ((2, 0, 0), (0x70c, 2, False)),            # never moved: its directory and $SI+0x58
    ((2, 2, 0x70b), (0x70b, 2, True)),         # moved from 0x70b (LAB-M's m1.bin): the reference it carries
], ids=["own-directory", "carries-reference"])
def test_e144_embedded_record_ref_rule(vals, want):
    assert F.embedded_record_ref(0x70c, _er_value(*vals)) == want


def test_e144_moved_records_listed_by_their_reference(tmp_path):
    """win10to11refs4g (no hard-link support, flags 0x6) holds 49 embedded records with $SI+0x68 set
    (`LD/evidence/moved_records_census.jsonl`): `files` lists each under ($SI+0x68 : $SI+0x60), as moved, and no two
    files share an ObjectRef. 1.13.1 gave them (their directory : $SI+0x58)."""
    import collections, csv
    img = _img("step3/win10to11refs4g.raw")
    f, ps, cs, tr, roots, om, vj, vn, cl = F.bootstrap(img)
    want = {}
    for oid in [o for o in om if o >= 0x600]:
        for kd, vd in F.walk_bplus(f, ps, cs, tr, om[oid], oid=oid):
            if len(kd) >= 4 and F.le16(kd, 0) == 0x30 and F.le16(kd, 2) == 1 and len(vd) >= 0x98 and F.le64(vd, 0x90):
                want[(oid, kd[4:].decode("utf-16le", "replace"))] = "0x%x:0x%x" % (F.le64(vd, 0x90), F.le64(vd, 0x88))
    f.close()
    assert len(want) == 49, len(want)
    out = str(tmp_path / "e144_files.csv")
    _run(FOREFST, img, "files", "--csv", out)
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    got, refs = {}, collections.Counter()
    for r in rows:
        if r["IsDirectory"] == "true":
            continue
        if (r["HardLinkCount"] or "1") == "1":       # a hard-link group's names share one ObjectRef by design
            refs[r["ObjectRef"]] += 1
        key = (int(r["ParentOID"], 16), r["FileName"])
        if key in want:
            got[key] = (r["ObjectRef"], r["HomeOID"], r["IsMoved"])
    assert len(got) == 49, len(got)
    for key, (ref, home, moved) in got.items():
        assert ref == want[key] and home == want[key].split(":")[0] and moved == "moved (the record's reference)", (
            key, ref, home, moved)
    dup = {k: n for k, n in refs.items() if k and n > 1}
    assert not dup, dup


def test_e144_ismoved_of_a_moved_record_is_a_string_in_every_form(tmp_path):
    """E144's IsMoved value is a string naming its source, like the others (WAVEE_QUESTIONS: a string in JSON too; K19:
    a boolean in text is a word): `files --json` carries "moved (the record's reference)" for the 49 moved records of
    win10to11refs4g and no JSON boolean; `details` of one prints it on the "Is moved" line and on the home-directory
    line (not "moved, or hard-linked ..."). The first E144 build returned True: JSON true, "Is moved: True"."""
    img = _img("step3/win10to11refs4g.raw")
    out = str(tmp_path / "e144_files.json")
    _run(FOREFST, img, "files", "--json", out)
    recs = json.load(open(out, encoding="utf-8"))
    recs = recs if isinstance(recs, list) else recs.get("files", [])
    vals = [r["IsMoved"] for r in recs]
    assert all(isinstance(v, str) for v in vals), sorted({repr(v) for v in vals if not isinstance(v, str)})
    moved = [r for r in recs if r["IsMoved"] == "moved (the record's reference)"]
    assert len(moved) == 49, len(moved)
    p = _run(FOREFST, img, "details", "/" + moved[0]["FullPath"].lstrip("/"))
    assert "Is moved:           moved (the record's reference)" in p.stdout, p.stdout[-1500:]
    home = [ln for ln in p.stdout.splitlines() if ln.startswith("  Home directory:")]
    assert len(home) == 1 and home[0].endswith(": moved (the record's reference)"), home


def test_e144_the_two_walkers_give_the_same_identity():
    """`_entry_identity` (the `_walk_dir_tree` walker: timestomp, the timeline) and `walk_directory_tree` (`files`)
    give every file the same (home, ordinal) on a volume with moved embedded records (win10to11refs4g, 49): the parity
    `_entry_identity`'s docstring states."""
    img = _img("step3/win10to11refs4g.raw")
    f, ps, cs, tr, roots, om, vj, vn, cl = F.bootstrap(img)
    a = {}
    for e in F.walk_directory_tree(f, ps, cs, tr, om, 0x600, F.DEFAULT_DEPTH, False):
        if e.get("type") == "FILE" or (not e.get("is_dir") and e.get("name")):
            a[e.get("path") or e.get("full_path")] = (e.get("home_oid") or 0, e.get("file_id") or 0)
    rows = []
    F._walk_dir_tree(f, ps, cs, tr, om, 0x600, "", 0, F.DEFAULT_DEPTH, rows)
    b = {r["path"]: (r.get("home_oid") or 0, r.get("file_id") or 0) for r in rows if r.get("type") == "FILE"}
    f.close()
    common = set(a) & set(b)
    assert len(common) >= 49, (len(a), len(b), len(common))
    diff = {p: (a[p], b[p]) for p in common if a[p] != b[p]}
    assert not diff, list(diff.items())[:5]
