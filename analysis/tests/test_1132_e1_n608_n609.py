"""N608 / N609 (1.14.0, found by E1's damaged-battery cases E1_K047_fsmeta_page_flip / E1_K048_security_page_flip):
a verdict read from a table whose root page fails the digest the Object Table recorded for it.

N608: with one bit flipped in the root page of the system metadata table (OID 0x520), `usn --info` printed the
journal's entry, extents and records from that page with no warning and exited 0. Now the page is verified when the
entry is looked up (`locate_change_journal` names the object), the command exits 2 and `--info` marks the entry.

N609: with one bit flipped in the root page of the Security Descriptor Stream (OID 0x530), `security --audit` warned and
exited 2 under "VERDICT: CLEAN" (the descriptors' own hashes pass, the page holding them does not). Now the verdict is
UNDETERMINED and names the page.

Base: step6/lab314_main.raw (4 KiB clusters, partition at 0x1000000). The two root pages, 0x520 at image offset
0x1e08000 and 0x530 at 0x4e00000, are recorded with the battery (golden_e13.json, base E1B: each read back MSB+); each
case flips bit 0 of the byte at +0x100 of one page, on a hole-preserving scratch copy deleted by its exact path. The
premise (the page carries MSB+ and the byte is written data, not a hole) is checked on the copy before the tool runs.
RED: both cases fail on 1.13.1 (FOREFST_REPO=analysis/verification/versions/v1.13.1); the control passes on both.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402

BASE = "step6/lab314_main.raw"
CAP = 400 << 20                                          # the base allocates about 205 MiB
FSMETA_ROOT = 0x1E08000                                  # OID 0x520's root page (image offset)
SECURITY_ROOT = 0x4E00000                                # OID 0x530's root page
FLIP_AT = 0x100

_N608_MARK = re.compile(r"\*\*\* the root page of the system metadata table \(OID 0x520\) does not match the digest "
                        r"the Object Table recorded for it")
_NO_JOURNAL = re.compile(r"No Change Journal found|(?i:journal not activated)|USN Journal: Inactive")
_CLEAN = re.compile(r"VERDICT: CLEAN")
_UNDET_PAGE = re.compile(r"VERDICT: UNDETERMINED .*root page does not match the digest the Object Table recorded")


def _flat(text):
    """The output with its line wrapping undone (a long verdict is wrapped onto indented lines)."""
    return " ".join(text.split())


def _flip(path, page, at):
    """Flip bit 0 of the byte at page + at, after checking the page carries MSB+ and the byte is written data."""
    MC._fx(MC.read_block(path, page, 4) == b"MSB+", "no MSB+ at 0x%x: not the page the battery recorded" % page)
    MC._fx(MC._holes(path, page + at, 1) == [], "the byte at 0x%x is a hole in the copy" % (page + at))
    with open(path, "r+b") as fh:
        fh.seek(page + at)
        b = fh.read(1)[0]
        fh.seek(page + at)
        fh.write(bytes([b ^ 0x01]))
    MC._fx(MC.read_block(path, page + at, 1) == bytes([b ^ 0x01]), "the flip did not land")


def test_n608_usn_info_over_an_altered_fsmeta_root_page():
    with MC.scratch_copy(BASE, CAP) as (src, p):
        _flip(p, FSMETA_ROOT, FLIP_AT)
        rc, text = MC.run_tool(MC.FOREFST, p, "usn", "--info")
    assert rc == 2 and _N608_MARK.search(_flat(text)) and not _NO_JOURNAL.search(_flat(text)), \
        "the 0x520 root page fails its digest: usn --info must mark the entry and exit 2, never say the journal is " \
        "absent" + MC._ctx(rc, text[-3000:])


def test_n609_security_audit_is_not_clean_over_an_altered_root_page():
    with MC.scratch_copy(BASE, CAP) as (src, p):
        _flip(p, SECURITY_ROOT, FLIP_AT)
        rc, text = MC.run_tool(MC.FOREFST, p, "security", "--audit")
    assert rc == 2 and _UNDET_PAGE.search(_flat(text)) and not _CLEAN.search(text), \
        "the 0x530 root page fails its digest: the audit must be UNDETERMINED, naming the page, exit 2" \
        + MC._ctx(rc, text[-3000:])


def test_n608_n609_control_the_undamaged_volume():
    """The same commands on the base image itself (read only): no mark, a CLEAN audit, exit 0."""
    rc_u, u = MC.run_tool(MC.FOREFST, MC.corpus(BASE), "usn", "--info")
    rc_s, s = MC.run_tool(MC.FOREFST, MC.corpus(BASE), "security", "--audit")
    assert rc_u == 0 and not _N608_MARK.search(_flat(u)) and rc_s == 0 and _CLEAN.search(s) and "UNDETERMINED" not in s, \
        "undamaged lab314_main: usn --info rc %s, security --audit rc %s" % (rc_u, rc_s) + MC._ctx(rc_s, s[-1500:])


def test_n608_n609_matchers():
    assert _UNDET_PAGE.search(_flat("  VERDICT: UNDETERMINED — the security table's root page does not match the digest\n"
                                     "           the Object Table recorded for it, so the descriptors above"))
    assert _N608_MARK.search("    *** the root page of the system metadata table (OID 0x520) does not match the digest "
                             "the Object Table recorded for it: the entry below was read from that table.")
    assert _UNDET_PAGE.search("  VERDICT: UNDETERMINED — the security table's root page does not match the digest the "
                              "Object Table recorded for it, so the descriptors above were read from an altered page")
    assert not _UNDET_PAGE.search("  VERDICT: UNDETERMINED — part of the security table could not be read")
    assert _NO_JOURNAL.search("  USN Journal: Inactive (the system metadata table, OID 0x520, holds no Change Journal)")
