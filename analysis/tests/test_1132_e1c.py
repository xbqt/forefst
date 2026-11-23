"""Wave E step E1c (1.14.0, `analysis/reports/v1.13.2/fixes/WAVEE_PLAN.md`): refsanalysis (group 12), B14, C1.

What each group asserts
-----------------------
C1       refsanalysis `files`: an ObjectRef column (a directory's OID:0x0, a file's HomeOID:FileID) and a Data column
         (where a file's data is); no cell wider than its column.
N284     refsanalysis `files` lists the named streams of split records (from the backing), as forefst `specials ads`.
N290     refsanalysis headers name the image by forefst's rule (its file name, or the bundle).
N152     the schema check expects schema 0x200 only from format 3.14 (absent on every older healthy volume).
"""
import csv
import io
import os
import re

import pytest

from _repo import REPO                                   # noqa: F401  layout-independent; see _repo.py

import test_1132_red_b2_wording as W                     # noqa: E402  (the runners)

_SPECIALS = "step3/win11refs2tspecials.raw"


def _ra_files(tmp_path, *extra):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, _SPECIALS, "files", *extra)
    assert rc in (0, 2), W._ctx(rc, out[:2000], err)
    return out


def test_c1_files_columns_name_what_they_hold(tmp_path):
    out = _ra_files(tmp_path)
    hdr = next(l for l in out.splitlines() if l.strip().startswith("Type "))
    assert re.match(r"^\s+Type\s+ObjectRef\s+Data\s+Path$", hdr), hdr
    cols = [m.start() for m in re.finditer(r"\S+", hdr)]
    for l in out.splitlines():
        m = re.match(r"^  (FILE|DIR ) (\S+)\s+(\S*)\s+", l)
        if not m:
            continue
        assert re.fullmatch(r"0x[0-9a-f]+:0x[0-9a-f]+", m.group(2)), l
        assert l[cols[2] - 1] == " " and (m.group(1) == "DIR " or m.group(3) in
                                          ("inline", "extents", "snapshot-shared", "unallocated", "unknown")), l


def _specials_rows(text):
    """The row count of `specials ads`' text table. Acceptance 1.14.0 (N292): the rows lead with the ObjectRef under a
    header line (OBJECTREF ... STREAM ...); the rows end at the first blank line."""
    lines = text.splitlines()
    hi = next((i for i, ln in enumerate(lines) if "OBJECTREF" in ln and "STREAM" in ln), None)
    n = 0
    for ln in (lines[hi + 1:] if hi is not None else []):
        if not ln.strip():
            break
        n += 1
    return n


def test_n284_files_lists_the_streams_of_split_records(tmp_path):
    out = _ra_files(tmp_path)
    ra = len([l for l in out.splitlines() if l.startswith("   ADS ")])
    rc, sp, err = W._image_run(tmp_path, W.FOREFST, _SPECIALS, "specials", "ads")
    ff = _specials_rows(sp)
    assert ra == ff and ra > 109, (ra, ff)


def test_n290_files_header_names_the_image_by_forefsts_rule(tmp_path):
    out = _ra_files(tmp_path)
    assert re.search(r"^\s+Image:\s+win11refs2tspecials\.raw$", out, re.M), out[:600]


@pytest.mark.parametrize("name, want_rc", [("step1/win10refsmini.raw", 0), ("step1/win11refsmini.raw", 0)],
                         ids=["3.4", "3.14"])
def test_n152_schema_verify_by_format(tmp_path, name, want_rc):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, name, "schema", "--verify")
    assert rc == want_rc and "Missing 0x200" not in out, W._ctx(rc, out[-1500:], err)
    if "win11" in name:
        assert "Object schema 0x200" in out, out[-1500:]        # RC3b item 13 (E167): schemas name tables, not attributes


# ── N209: `refsanalysis all` returns the most serious section result ───────────────────────────────────────────────

def test_n209_all_exits_2_when_a_section_finds_something(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, "step7/labFbeforereboot.raw", "all")
    assert "Redundancy findings (exit code 2)" in out and rc == 2, W._ctx(rc, out[-1500:], err)


def test_n209_all_exits_1_when_every_section_dies(tmp_path):
    p = tmp_path / "zeros.raw"
    p.write_bytes(bytes(1 << 20))
    rc, out, err = W._tool(W.REFSANALYSIS, str(p), "all", cwd=str(tmp_path))
    assert rc == 1, W._ctx(rc, out[-800:], err[-800:])


def test_n209_control_a_healthy_volume_exits_0(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, "step1/win11refsmini.raw", "all")
    assert rc == 0, W._ctx(rc, out[-1500:], err)


# ── N383: refsanalysis `supb` validates the cluster size as forefst does ───────────────────────────────────────────

import struct                                            # noqa: E402

import test_1132_red_b2_refsanalysis as R                # noqa: E402  (the sealed boot-sector builders)


@pytest.mark.parametrize("spc", [1 << 31, 3], ids=["2^40-byte cluster", "1536-byte cluster"])
def test_n383_supb_refuses_an_implausible_cluster_size_cleanly(tmp_path, spc):
    p = R._native_volume(str(tmp_path / "cs.raw"))
    v = bytearray(R._read(p, 0, 512))
    struct.pack_into("<I", v, 0x24, spc)
    R._set_vbrs(p, R._seal_vbr(v))
    rc, out, err = W._tool(W.REFSANALYSIS, p, "supb", cli=W._SYN, cwd=str(tmp_path))
    assert rc == 1 and "implausible ReFS cluster size" in err and "Traceback" not in err, W._ctx(rc, out, err)


# ── N370: a Result line that reads as a pass says why the exit is 2 ────────────────────────────────────────────────

def test_n370_chkp_verify_result_names_the_exit_2(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, "step4continuing/win11refsmini_aftercorruption.raw",
                                "chkp", "--verify")
    res = [l for l in out.splitlines() if l.strip().startswith("Result:")][-1]
    assert rc == 2 and "exit 2" in res, (rc, res)


def test_n370_control_a_healthy_volume_result_line(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, "step1/win11refsmini.raw", "chkp", "--verify")
    res = [l for l in out.splitlines() if l.strip().startswith("Result:")][-1]
    # N580 (O3): one row more than in RC1 -- the other checkpoint copy's self-checksum
    assert rc == 0 and res.strip() == "Result: 21/21 checks passed", (rc, res)


# ── N286 / N329 (ra half) / N346: refsanalysis `attributes` and `supb` ──────────────────────────────────────────────

import test_1132_red_a_bootstrap as AB                   # noqa: E402  (the synthetic volume and its re-sealer)


def test_n286_attributes_prints_accessed_and_the_streams(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, _SPECIALS, "attributes")
    assert re.search(r"^\s+Accessed:\s+\d{4}-", out, re.M), out[:1500]
    rc2, sp, err2 = W._image_run(tmp_path, W.FOREFST, _SPECIALS, "specials", "ads")
    ff = _specials_rows(sp)
    assert len(re.findall(r"^\s+ADS:\s+\S", out, re.M)) == ff, ff


def test_n329_attributes_wsl_values_are_the_one_decoders(tmp_path):
    img = "step6/win11refs2gtargeted.raw"
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, img, "attributes")
    blk = out.split("FILE wsltests/testblk", 1)[1].split("\n  FILE", 1)[0]
    assert "WSL Mode:    block rw-rw---- (0o660)" in blk and "WSL Dev:     7,0" in blk, blk
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, img, "attributes", "--filter", "wsl")
    assert len(re.findall(r"^  FILE ", out, re.M)) == 10, out[-2000:]
    src = open(os.path.join(W.REPO, "refsanalysis.py"), encoding="utf-8").read()
    assert "_forefst.wsl_metadata(" in src


def test_n346_a_fuzzed_checkpoint_count_is_said_once(tmp_path):
    p = str(tmp_path / "count.raw")
    AB._build_synthetic(p)
    v = AB.Vol(AB.SYN, p)
    # every copy: with one copy fuzzed the tool reads a backup (B15) and never reaches the clamp
    for lcn in (AB.SYN.supb,) + tuple(AB.SYN.backups):
        v.reseal(lcn, lambda b: struct.pack_into("<I", b, 0x74, 0x40), 0xD0)
    rc, out, err = W._tool(W.REFSANALYSIS, p, "supb", cli=W._SYN, cwd=str(tmp_path))
    n = len(re.findall(r"checkpoint-ref count 64 implausible", err))
    assert n == 1, "said %d times:\n%s" % (n, err[-1500:])


# ── C7 / N161 (ra half), N162 / N359 (ra help) ─────────────────────────────────────────────────────────────────────

def test_c7_n161_no_bare_resident_word_in_refsanalysis_text():
    import ast as _ast
    bare = re.compile(r"(?i)(?<![\w-])(?:non-?)?resident(?![\w-])")
    tree = _ast.parse(open(os.path.join(W.REPO, "refsanalysis.py"), encoding="utf-8").read())
    parents = {c: n for n in _ast.walk(tree) for c in _ast.iter_child_nodes(n)}
    bad = [(n.lineno, n.value[:90]) for n in _ast.walk(tree)
           if isinstance(n, _ast.Constant) and isinstance(n.value, str) and bare.search(n.value)
           and not isinstance(parents.get(n), _ast.Expr) and not re.fullmatch(r"(non-)?resident", n.value)]
    assert not bad, bad


@pytest.mark.parametrize("cmd", ["summary", "summary++", "all", "files", "attributes", "details", "objects", "schema",
                                 "parentchild", "allocators", "upcase", "oid30", "bootedit", "forefst"])
def test_n359_every_refsanalysis_help_entry_states_its_exit_codes(tmp_path, cmd):
    rc, out, err = W._run([os.path.join(W.REPO, "refsanalysis.py"), "help", cmd], cwd=str(tmp_path))
    assert "Exit codes:" in out and re.search(r"^\s+2\s+a finding", out, re.M), out[-800:]


def test_n162_refsanalysis_help_sentences(tmp_path):
    src = open(os.path.join(W.REPO, "refsanalysis.py"), encoding="utf-8").read()
    assert "384-byte block" not in src and "run all structure tools" not in src
    assert "usn/mlog/timeline/timestomp/extract/" + "\n" not in src     # the passthrough list that missed commands


# ── N377: the verify table's width; a copy never read is "not read" ────────────────────────────────────────────────

import refsanalysis as RA                                # noqa: E402


def test_n377_a_long_reason_wraps_inside_its_column(capsys):
    reason = " ".join("word%02d" % i for i in range(40))                 # 279 characters of words
    RA._print_table(["check", "result", "detail"], [["copy_0", "FAIL", reason], ["copy_1", "OK", "short"]])
    lines = [l.rstrip() for l in capsys.readouterr().out.splitlines() if l.strip()]
    # review RE1-19: the width read with a default, so the node fails by its assertion on a tree without the wrap
    assert max(len(l) for l in lines) <= len("copy_0  result  ") + getattr(RA, "_TABLE_LAST_COL", 80), lines
    assert sum(1 for l in lines if l.strip().startswith("word")) >= 3     # continuation lines
    from conftest import unwrap_table_rows                                  # the words, in order, once each
    row = next(l for l in unwrap_table_rows("\n".join(lines)).splitlines() if l.startswith("copy_0"))
    assert row.split(None, 2)[2] == reason, row


def test_n377_a_token_is_never_split(capsys):
    """Not a RED (review RE1-19): guards the wrap the E1 close added -- a tree without any wrap passes it too."""
    token = "/a/" + "x" * 120 + "/file.txt"
    RA._print_table(["check", "result", "detail"], [["copy_0", "FAIL", "path " + token]])
    out = capsys.readouterr().out
    assert token in out.splitlines()[2] or any(l.strip() == token for l in out.splitlines()), out


def test_n377_a_backup_superblock_beyond_the_image_is_not_read(tmp_path):
    p = str(tmp_path / "short.raw")
    AB._build_synthetic(p)
    with open(p, "r+b") as fh:
        fh.truncate(AB.SYN.backups[0] * 4096)            # the image ends before both backup superblocks
    rc, out, err = W._tool(W.REFSANALYSIS, p, "supb", "--verify", cli=W._SYN, cwd=str(tmp_path))
    rows = [l for l in out.splitlines() if l.startswith("supb_backup_checksum")]
    assert rows and all("not read" in r and "no SUPB signature" not in r for r in rows), W._ctx(rc, out[-2000:], err)


# ── N493: the boot sector's flags, selector and GUID in the driver's terms (refsanalysis `boot`, `bootedit read`) ─────

_N493_OLD = ("Win11-cap1", "Win11-cap2", "format-time", "valid-ReFS", "recovery/dirty", "Win11-boot-behavior",
             "checksum-algo-gate", "=mounted", "(base", "+base", "Win10 or upgraded", "Win10-formatted")


def _n493_volume(tmp_path, flags, algo):
    p = R._native_volume(str(tmp_path / "flags.raw"))
    v = bytearray(R._read(p, 0, 512))
    struct.pack_into("<I", v, 0x2C, flags)
    struct.pack_into("<H", v, 0x2A, algo)
    R._set_vbrs(p, R._seal_vbr(v))
    return p


@pytest.mark.parametrize("cmd", [("boot", "-vv"), ("bootedit", "read")], ids=["boot", "bootedit-read"])
def test_n493_volume_flags_are_named_by_what_the_driver_does(tmp_path, cmd):
    p = _n493_volume(tmp_path, 0x93, 0)                 # 0x80 | 0x10 | 0x02 | 0x01, selector 0, bit 0x40 clear
    rc, out, err = W._tool(W.REFSANALYSIS, p, *cmd, cli=W._SYN, cwd=str(tmp_path))
    assert not [w for w in _N493_OLD if w in out], [w for w in _N493_OLD if w in out]
    for want in ("RefsSetBreakOnCorrupt", "writable mount", "salvage", "upgrade"):
        assert want in out, (want, out[-2500:])
    assert re.search(r"not read.*0x40", out), out[-2500:]          # selector 0 with bit 0x40 clear is not "None"


def test_n493_a_native_volume_names_its_selector_and_its_undecoded_bits(tmp_path):
    p = R._native_volume(str(tmp_path / "native.raw"))   # flags 0x66, selector 2
    rc, out, err = W._tool(W.REFSANALYSIS, p, "bootedit", "read", cli=W._SYN, cwd=str(tmp_path))
    assert "CRC64" in out and "not read" not in out, out[-2500:]
    assert "meaning not decoded" in out, out[-2500:]                # 0x04 and 0x20


# ── N346 (residue): a superblock copy read whose checksum cannot be verified is said once by `supb --verify` ──────────

def _n346_unknown_type(tmp_path):
    p = R._native_volume(str(tmp_path / "type3.raw"))
    d = struct.unpack_from("<I", R._read(p, 0x1E * 4096, 0x80), 0x78)[0]
    R._write(p, 0x1E * 4096 + d + 0x22, b"\x03")        # the primary declares checksum type 3 (no algorithm)
    return p


def test_n346_an_unverifiable_copy_read_is_said_once_by_supb_verify(tmp_path):
    p = _n346_unknown_type(tmp_path)
    rc, out, err = W._tool(W.REFSANALYSIS, p, "supb", "--verify", cli=W._SYN, cwd=str(tmp_path))
    n = len(re.findall(r"unknown checksum type 0x3\b", out + err))            # K16 (1.14.0): unpadded
    assert n == 1 and rc == 2, "said %d times:\n%s" % (n, (out + err)[-3000:])
    row = next(l for l in out.splitlines() if l.startswith("supb_primary_checksum"))
    assert "WARN" in row and "the volume is read from this copy" in " ".join(out.split()), row   # the cell wraps (N377)


def test_n346_control_supb_without_verify_keeps_its_note(tmp_path):
    p = _n346_unknown_type(tmp_path)
    rc, out, err = W._tool(W.REFSANALYSIS, p, "supb", cli=W._SYN, cwd=str(tmp_path))
    assert re.search(r"^NOTE: .*unknown checksum type 0x3\b", out, re.M) and rc == 2, (rc, out[:1500])


# ── E1 close: the review's findings (`fixes/REVIEW_WAVEE1.md`) ────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", ["step4/win1121h2test.raw", "step4/win1122h2test.raw", "step4/win1123h2test.raw"],
                         ids=["3.7", "3.9", "3.10"])
def test_re1_1_fixboot_diagnosis_has_no_flags_rule_for_formats_before_3_14(tmp_path, name):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, name, "bootedit", "repair", "--dry-run")
    assert "unexpected flags" not in out and "Win10 format" not in out and rc == 0, W._ctx(rc, out[-2500:], err)


def _ff_summary_files(tmp_path, name):
    rc, out, err = W._image_run(tmp_path, W.FOREFST, name, "summary")
    m = re.search(r"^\s*Files:\s+(\d+) \(", out, re.M)
    assert m, out[:2000]
    return int(m.group(1))


@pytest.mark.parametrize("name", [_SPECIALS, "step6/win11refs2gtargeted.raw"], ids=["tspecials", "targeted"])
def test_re1_4_ra_files_and_attributes_count_files_once(tmp_path, name):
    want = _ff_summary_files(tmp_path, name)
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, name, "files")
    m = re.search(r"^  Files:\s+(\d+) \(", out, re.M)
    assert m and int(m.group(1)) == want, (want, out[:1500])
    assert not re.search(r"\d+ files[,)]", out.split("Files:", 1)[0]), out[:1500]       # no names called files
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, name, "attributes")
    m = re.search(r"^    Files:\s+(\d+) \(", out, re.M)
    assert m and int(m.group(1)) == want, (want, out[:2500])


def test_re1_6_ra_details_prints_a_split_files_allocated_size(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, _SPECIALS, "details", R._N150_PATH)
    assert re.search(r"^  Allocated size: 483328 bytes$", out, re.M), out[-2500:]


def test_re1_6_ra_details_prints_an_embedded_reparse_target(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.REFSANALYSIS, "step6/win11refs2gtargeted.raw", "details",
                                "/wsltests/lxsymlink")
    assert re.search(r"^  Reparse target: targetfile\.txt$", out, re.M), out[-2500:]


def test_re1_7_forefst_details_of_a_directory_names_its_internal_flags(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.FOREFST, "step6/win11bidule.raw", "details", "/tests/testdir")
    ls = [l for l in out.splitlines() if "Internal flags" in l]
    assert ls and all("CaseSensitive" in l for l in ls), (ls, out[-2000:])


def test_re1_8_files_log_line_counts_objects_with_their_names(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.FOREFST, _SPECIALS, "files", "--csv")
    assert re.search(r"ADS: 123 objects \(254 names\)", err), err[-2000:]


def test_re1_10_and_11_selector_and_flag_0x20_words(tmp_path):
    p = _n493_volume(tmp_path, 0x26, 0)                 # the 3.7 / 3.9 flags: 0x20 set, 0x40 clear
    rc, out, err = W._tool(W.REFSANALYSIS, p, "bootedit", "read", cli=W._SYN, cwd=str(tmp_path))
    assert "hard links supported" in out and "RefsHardlinksSupported" in out, out[-2500:]
    assert re.search(r"not read: .*26100.*17134 does not read \+0x2a", " ".join(out.split())), out[-2500:]   # K15
