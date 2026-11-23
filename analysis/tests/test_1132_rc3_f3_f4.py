"""F3 / F4 (1.14.0 RC3, the auditor's RC2 check of 2026-11-19): two clean answers on a damaged copy, both in 1.13.1.

F3: with every record of the volume's log destroyed, the tail check (A7, `mlog_tail_check`) took the log start as the
tail; the start equals the end on most volumes, so `mlog --stats` said "Log may be clean" and `summary --mlog`
"Newest records: none missing (the log end checked)", exit 0. The census of 2026-11-20 (RC1D/rc3/f3_census.jsonl: 124
ReFS volumes of corpus.lst) found no volume without a record of its own log (the fewest: 56), so a data area that holds
no record of this log, below a log end past its first block, is a finding: its records are missing, and how many
cannot be counted (no record anchors the count).

F4: `files` built its security map (`build_security_map`, object 0x530) with a walk that did not name its object, so
the root page was never checked against the digest the Object Table recorded for it: with one bit flipped (an ACE's
type, ALLOWED -> DENIED), `files --csv` / `--json` printed the altered entry and exited 0, also from a bundle.

Base: step5/win11refstestmftecmd.raw (4 KiB clusters, partition at 0x1000000). Its MLog data area starts at LCN 0x8000;
its log's records are in blocks 0x1-0x12d8 (LCN 0x8001-0x92d8), the log end at block 0x12d9 (the auditor's figures,
read back from the bytes). The security table's root page is at image offset 0x3200000 (MSB+); the auditor's flip is
bit 0 of the byte at 0x3200618. Each case runs on a hole-preserving scratch copy deleted by its exact path; the
premises are checked on the copy before the tool runs. RED: the four damaged cases fail on the RC2 tool (forefst
308d761a); the controls pass on both.
"""
import io
import os
import re
import sys
import tempfile
import shutil
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402

BASE = "step5/win11refstestmftecmd.raw"
CAP = 600 << 20                                          # the base allocates about 381 MiB
PS = 0x1000000
MLOG_DS = 0x8000                                         # the data area's first LCN (block 0)
FIRST, LAST = 0x1, 0x12D8                                # this log's records, by block
SECURITY_ROOT = 0x3200000
FLIP_AT = 0x618

_NO_RECORD = re.compile(r"the data area holds no record of this log")
_CLEAN_LOG = re.compile(r"Log may be clean|none missing")
_SEC_ALTERED = re.compile(r"object 0x530 does not match|root page of object 0x530 does not match")


def _flat(text):
    return " ".join(text.split())


def _block(n):
    return PS + (MLOG_DS + n) * 0x1000


def _zero_log(path):
    """Zero this log's 4,824 record blocks, after checking the first and last carry the MLog magic."""
    for n in (FIRST, LAST):
        MC._fx(MC.read_block(path, _block(n), 4) == b"MLog", "no MLog record in block 0x%x" % n)
    MC._fx(not any(MC.read_block(path, _block(LAST + 1), 0x1000)), "block 0x%x is not empty" % (LAST + 1))
    with open(path, "r+b") as fh:
        fh.seek(_block(FIRST))
        for _ in range(FIRST, LAST + 1):
            fh.write(b"\0" * 0x1000)
    MC._fx(not any(MC.read_block(path, _block(LAST), 0x1000)), "the zeroing did not land")


def _flip_security(path):
    MC._fx(MC.read_block(path, SECURITY_ROOT, 4) == b"MSB+", "no MSB+ at 0x%x" % SECURITY_ROOT)
    MC._fx(MC._holes(path, SECURITY_ROOT + FLIP_AT, 1) == [], "the byte is a hole in the copy")
    with open(path, "r+b") as fh:
        fh.seek(SECURITY_ROOT + FLIP_AT)
        b = fh.read(1)[0]
        fh.seek(SECURITY_ROOT + FLIP_AT)
        fh.write(bytes([b ^ 0x01]))
    MC._fx(MC.read_block(path, SECURITY_ROOT + FLIP_AT, 1) == bytes([b ^ 0x01]), "the flip did not land")


def _assert_f3(rc, text, what):
    t = _flat(text)
    assert rc == 2 and _NO_RECORD.search(t) and not _CLEAN_LOG.search(t), \
        "every record of the log is gone: %s must say the data area holds no record of this log, never 'none " \
        "missing' or 'Log may be clean', and exit 2" % what + MC._ctx(rc, text[-3000:])


def test_f3_mlog_stats_with_every_record_zeroed():
    with MC.scratch_copy(BASE, CAP) as (src, p):
        _zero_log(p)
        rc, text = MC.run_tool(MC.FOREFST, p, "mlog", "--stats")
    _assert_f3(rc, text, "mlog --stats")


def test_f3_summary_mlog_with_every_record_zeroed():
    with MC.scratch_copy(BASE, CAP) as (src, p):
        _zero_log(p)
        rc, text = MC.run_tool(MC.FOREFST, p, "summary", "--mlog")
    _assert_f3(rc, text, "summary --mlog")


def test_f3_every_record_in_an_image_hole():
    """The same blocks left as an image hole of the copy: the same finding, with the hole stated."""
    with MC.scratch_copy(BASE, CAP, omit=[(_block(FIRST), _block(LAST + 1))]) as (src, p):
        MC._fx(MC._holes(p, _block(FIRST), (LAST - FIRST + 1) * 0x1000) ==
               [(_block(FIRST), _block(LAST + 1))], "the record blocks are not a hole of the copy")
        rc, text = MC.run_tool(MC.FOREFST, p, "mlog", "--stats")
    _assert_f3(rc, text, "mlog --stats (hole)")
    assert MC._HOLE.search(_flat(text)), "the blocks are an image hole: the statement must say so" + MC._ctx(rc, text[-2000:])


def test_f4_files_csv_over_an_altered_security_root_page():
    with MC.scratch_copy(BASE, CAP) as (src, p):
        _flip_security(p)
        rc, text = MC.run_tool(MC.FOREFST, p, "files", "--csv")
    assert rc == 2 and _SEC_ALTERED.search(_flat(text)), \
        "the 0x530 root page fails its digest: files --csv must name it and exit 2" + MC._ctx(rc, text[-2000:])


def test_f4_files_json_over_an_altered_security_root_page():
    with MC.scratch_copy(BASE, CAP) as (src, p):
        _flip_security(p)
        rc, text = MC.run_tool(MC.FOREFST, p, "files", "--json")
    assert rc == 2 and _SEC_ALTERED.search(_flat(text)), \
        "the 0x530 root page fails its digest: files --json must name it and exit 2" + MC._ctx(rc, text[-2000:])


def test_f4_files_from_a_bundle_of_the_altered_copy():
    with MC.scratch_copy(BASE, CAP) as (src, p):
        _flip_security(p)
        d = tempfile.mkdtemp(prefix="rc3_f4_bundle_", dir=os.path.dirname(p))
        out = os.path.join(d, "bundle")
        try:
            MC.run_tool(MC.FOREFST, p, "export", "metadata", "-o", out)
            MC._fx(os.path.isfile(os.path.join(out, "manifest.json")), "no bundle was written")
            rc, text = MC.run_tool(MC.FOREFST, out, "files", "--csv")
        finally:
            shutil.rmtree(d)
    assert rc == 2 and _SEC_ALTERED.search(_flat(text)), \
        "a bundle carries the altered page and its digest: files on it must name 0x530 and exit 2" \
        + MC._ctx(rc, text[-2000:])


def test_f3_f4_control_the_undamaged_volume():
    """The base itself (read only): the log check finds records and nothing missing; files names no altered page."""
    rc_m, m = MC.run_tool(MC.FOREFST, MC.corpus(BASE), "mlog", "--stats")
    rc_f, f = MC.run_tool(MC.FOREFST, MC.corpus(BASE), "files", "--csv")
    assert not _NO_RECORD.search(_flat(m)) and not _SEC_ALTERED.search(_flat(f)) and rc_f == 0, \
        "undamaged testmftecmd: mlog --stats rc %s, files --csv rc %s" % (rc_m, rc_f) + MC._ctx(rc_f, f[-1500:])


def test_f3_f4_matchers():
    assert _NO_RECORD.search("and the data area holds no record of this log, so its records are missing")
    assert _CLEAN_LOG.search("  (Log may be clean — all transactions checkpointed.)")
    assert _CLEAN_LOG.search("Newest records: none missing (the log end checked)")
    assert _SEC_ALTERED.search("[forefst] WARNING: metadata page for object 0x530 does not match its recorded checksum")
    assert _SEC_ALTERED.search("the root page of object 0x530 does not match the digest the Object Table recorded")
    assert not _SEC_ALTERED.search("the root page of object 0x520 does not match the digest")


# D (1.14.0 RC3; the maintainer's decision 73): the checkpoint's other roots are checked at bootstrap. Root 1 (the
# Medium Allocator) at image offset 0x23a00000 and root 5 (the Object Table's duplicate) at 0x4200000 on the base, each
# one 16 KiB page of four clusters (MSB+ checked on the copy); the flip is bit 0 of the byte at +0x800.
ROOT1_PAGE, ROOT5_PAGE, ROOT_FLIP = 0x23A00000, 0x4200000, 0x800
_ROOT_NAMED = {1: re.compile(r"checkpoint root 1 \(Medium Allocator\) does not match the digest"),
               5: re.compile(r"checkpoint root 5 \(Object ID Table copy 2\), the duplicate of root 0, does not match the "
                             r"digest the checkpoint copy in use records for it; root 0 is the copy read")}


def _flip_page(path, page, at):
    MC._fx(MC.read_block(path, page, 4) == b"MSB+", "no MSB+ at 0x%x" % page)
    MC._fx(MC._holes(path, page + at, 1) == [], "the byte is a hole in the copy")
    with open(path, "r+b") as fh:
        fh.seek(page + at)
        b = fh.read(1)[0]
        fh.seek(page + at)
        fh.write(bytes([b ^ 0x01]))


def _assert_root_named(idx, page, cmd):
    with MC.scratch_copy(BASE, CAP) as (src, p):
        _flip_page(p, page, ROOT_FLIP)
        rc, text = MC.run_tool(MC.FOREFST, p, *cmd)
    assert rc == 2 and _ROOT_NAMED[idx].search(_flat(text)), \
        "checkpoint root %d's page fails its digest: %s must name it and exit 2" % (idx, " ".join(cmd)) \
        + MC._ctx(rc, text[-2000:])


def test_d_summary_names_an_altered_allocator_root():
    _assert_root_named(1, ROOT1_PAGE, ("summary",))


def test_d_files_names_an_altered_allocator_root():
    _assert_root_named(1, ROOT1_PAGE, ("files", "--csv"))


def test_d_summary_names_an_altered_object_table_duplicate():
    """Root 5 is not read while root 0 verifies: a redundancy condition (D's second correction), said by `summary`."""
    _assert_root_named(5, ROOT5_PAGE, ("summary",))


def test_d_files_keeps_its_exit_code_over_an_altered_object_table_duplicate():
    """The documented rule for a backup copy that fails: the commands that do not report redundancy read the copy in
    use and keep their exit code -- `files` names no root and exits 0 (Q8; B2's control)."""
    with MC.scratch_copy(BASE, CAP) as (src, p):
        _flip_page(p, ROOT5_PAGE, ROOT_FLIP)
        rc, text = MC.run_tool(MC.FOREFST, p, "files", "--csv")
    assert rc == 0 and not re.search(r"checkpoint root \d+ \(", _flat(text)), \
        "root 5 is a duplicate not read: files --csv names no root and exits 0" + MC._ctx(rc, text[-2000:])


def test_d_a_digest_length_the_algorithm_does_not_have_is_not_compared():
    """`_chkp_root_failures` on a hand-built record and a zeroed buffer (no image): a SHA-256 reference declaring 31 bytes, a CRC64 one
    declaring 4, cannot be verified, never 'does not match'; a declared length past the reference keeps N362's text."""
    F = MC.AB.F
    for ck, n, want in ((4, 31, "declares a 31-byte digest for SHA-256, whose digest is 32 bytes"),
                        (2, 4, "declares a 4-byte digest for CRC64, whose digest is 8 bytes"),
                        (2, 0x21, "its reference's digest length (33 bytes) runs past the reference")):
        raw = bytearray(0x1000)
        struct.pack_into("<I", raw, 0x5C, 0x48)
        struct.pack_into("<I", raw, 0x94 + 4, 0x200)
        struct.pack_into("<Q", raw, 0x200, 0x1)                      # one LCN, cluster 1 of a zeroed buffer
        raw[0x200 + 0x22] = ck
        struct.pack_into("<I", raw, 0x200 + 0x24, n)
        uw = []
        fails = F._chkp_root_failures(io.BytesIO(bytes(0x3000)), 0, 0x1000, bytes(raw), None, uw, roots=(1,))
        assert not fails and uw and want in uw[0][1], (ck, n, fails, uw)


def test_d_control_the_undamaged_volume_names_no_root():
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(BASE), "summary")
    assert not re.search(r"checkpoint root \d+ \(", _flat(text)), "undamaged testmftecmd: a root named" \
        + MC._ctx(rc, text[-1500:])


# D, correction (2026-11-20, RC1D/rc3/patch/apply_rc3_db.py): a root D cannot check is stated, never left out, and a
# root whose address cannot be translated is not read at the untranslated address. Root 1's reference in the copy in use
# (LCN 0x1e3f4, the reference at +0x140) is given checksum type 5 (XXH64, which the tool does not compute) and the copy
# re-sealed with the tool's own recipe (premises checked); and a bundle of win11refsmini that carries no B+-tree page
# (so no Container Table) is read.
CHKP_IN_USE, ROOT1_REF = 0x1E3F4, 0x140
_UNVERIFIABLE = re.compile(r"checkpoint root 1 \(Medium Allocator\) cannot be verified \(its reference declares "
                           r"checksum type 0x5")
_UNTRANSLATED = re.compile(r"checkpoint root \d+ \([^)]*\) cannot be verified \(its address, VLCN 0x[0-9a-f]+, cannot "
                           r"be translated through the Container Table in use\)")
_ROOT_STATED_AT_AN_ADDRESS = re.compile(r"checkpoint root \d+ \([^)]*\) (is in a hole|is not carried|reads as zeros|"
                                        r"does not match|cannot be read)")


def test_d_a_root_that_cannot_be_verified_is_said():
    F = MC.AB.F
    with MC.scratch_copy(BASE, CAP) as (src, p):
        at = PS + CHKP_IN_USE * 0x1000
        b = bytearray(MC.read_block(p, at, 0x1000))
        MC._fx(b[:4] == b"CHKP" and F._verify_self_checksum(bytes(b), 0x1000)[0] is True, "the copy in use does not verify")
        olb = F.le32(b, 0x94) if F.le32(b, 0x78) & 0x200 else 0x94
        MC._fx(F.le32(b, olb + 4) == ROOT1_REF and b[ROOT1_REF + 0x22] == 2 and F.le64(b, ROOT1_REF) == 0x5AA00,
               "root 1's reference is not where the premise says")
        recipe = F._self_checksum_recipe(bytes(b), 0x1000)
        b[ROOT1_REF + 0x22] = 5
        out = F._recompute_self_checksum(b, 0x1000, recipe)
        with open(p, "r+b") as fh:
            fh.seek(at)
            fh.write(bytes(out[:0x1000]))
        MC._fx(F._verify_self_checksum(MC.read_block(p, at, 0x1000), 0x1000)[0] is True, "the re-sealed copy does not verify")
        rc, text = MC.run_tool(MC.FOREFST, p, "summary")
    assert rc == 2 and _UNVERIFIABLE.search(_flat(text)), \
        "root 1's reference declares a checksum type the tool does not compute: summary must say it cannot be " \
        "verified and exit 2" + MC._ctx(rc, text[-2000:])


def test_d_a_bundle_without_the_container_table_reads_no_untranslated_root():
    with MC.scratch_copy("step1/win11refsmini.raw", 64 << 20) as (src, p):
        d = tempfile.mkdtemp(prefix="rc3_d_bundle_", dir=os.path.dirname(p))
        out = os.path.join(d, "bundle")
        try:
            MC.run_tool(MC.FOREFST, p, "export", "metadata", "-o", out, "--what", "vbr,chkp,supb,mlog,usn")
            MC._fx(os.path.isfile(os.path.join(out, "manifest.json")) and
                   not any(n.startswith(("metadata_", "object_")) for n in os.listdir(out)),
                   "the bundle was not written, or carries B+-tree pages")
            rc, text = MC.run_tool(MC.FOREFST, out, "summary")
        finally:
            shutil.rmtree(d)
    t = _flat(text)
    assert _UNTRANSLATED.search(t) and not _ROOT_STATED_AT_AN_ADDRESS.search(t), \
        "no Container Table is carried: D's roots must be said to be unverifiable, never stated at an untranslated " \
        "address" + MC._ctx(rc, text[-3000:])
