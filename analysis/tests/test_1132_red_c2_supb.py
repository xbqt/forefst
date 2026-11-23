"""1.13.2 (ships as 1.14.0) RED cases, wave C step C2, area `supb`: B15 (the validity of a superblock copy and the
choice between the three copies follow refs.sys) and N449 (the sentence for two differing copies that both verify).

Read first: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (settlements Q2-Q6), `fixes/WAVEC_INVENTORY.md` and
`fixes/WAVEC_CENSUS.md` (rows B15, N449), `fixes/WAVEC_READING_bootstrap.md` section 4.1 (the closure table) with its
`_evidence/reading_facts.md` S1-S11, RUNNING_LOG N450. Report: `analysis/reports/v1.13.2/fixes/RED_C2_supb.md`.

  B15 validity (Q2)  a copy is valid when it passes `ValidateSuperBlock`'s tests (S5; read twice, 17134, 26100.8115,
                     .9444, .9549, Insider 29574): its self-checksum; the 32 bytes +0x20..+0x3F = {its LCN, 0, 0, 0};
                     byte +0x04 != 0; u32 +0x74 = 2; u32 +0x70 >= 0xC0 and +0x70 + 0x10 <= the cluster; both
                     checkpoint LCNs, signed, in [0x1F, N - 3] (N = the volume's clusters; 26100.8115
                     refs_win11.decomp.c:216525-216540: `lVar2 < 0x1f || N - 3 < lVar2` rejects). There is no
                     `SUPB` signature test (S5, bootstrap N-6): the signature only selects, among copies that FAIL,
                     the copy decisions 26 / 27.1 read.
  B15 choice (Q3)    the primary when it is valid, whatever the backups' +0x68 (N450, S3); else end-2 (N - 2), unless
                     end-3 (N - 3) is valid with a strictly higher +0x68; else end-3. The redundancy list keeps its
                     order (ascending LCN: end-3, end-2).
  B15 statement (Q4) the primary valid and a backup that verifies with another +0x68: a note with both values and
                     "refs.sys reads the primary when it passes validation"; nothing where the copies agree. The primary
                     not valid: decision 27.2's finding (exit 2 in every command) names the copy read and the test the
                     primary fails (plan B15: "the tool says which copy it reads and why").
  N449 (Q5, Q6)      two copies that both verify and differ: the sentence states what is measured -- where they differ,
                     that both verify, the +0x68 values, "refs.sys reads the primary when it passes validation; +0x68
                     orders only the two backups" -- and no editing / damage conclusion (a copy that fails its
                     self-checksum keeps A13's "edited or damaged"). For the extend pattern only (all three verify, the
                     backups equal each other, carry the primary's +0x68 + 1 and differ from it only at +0x68 and
                     +0x10/+0x18) the "why": "this matches what refs.sys writes when it extends the volume: the two
                     backups with +0x68 one higher, the primary unchanged".

Exit codes of two verifying copies that differ (RED_C2_supb.md section 6, N-1; settled by the lead, C2_LEAD_SETTLEMENTS
S-E): the +0x68 note and N449's sentence add no exit; the volume's exit 2 is N417's redundancy finding and is unchanged
-- kept (`_keep`) in the Q4, N449 and Q6 nodes: summary / fastsummary / integrity / ra summary / ra supb --verify exit 2,
plain ra supb exits 0 (measured on the current tree, critic probe).

Volumes: the 1 MiB synthetic ReFS 3.14 volume of `test_1132_red_a_bootstrap.py` (N = 256: end-3 0xFD, end-2 0xFE), a
hole-preserving scratch carve of the battery's base A (`step1/win11refsmini.raw`: N = 0x7c000, end-3 0x7bffd, end-2
0x7bffe; through `test_1132_red_b_items.py`), and the two corpus volumes whose primary fails its self-checksum
(`step4continuing/win11refsmini_aftercorruption.raw`, `_openedwith34.raw`, read in place: MR-B has both backups valid with
+0x68 = 1, refs.sys reading 0x7bffe and the tool 0x7bffd).

Conventions (test_1132_red_a_bootstrap.py): every RED is ``xfail(strict=True, raises=AssertionError)``; fixture
problems raise RedFixtureError, a property the tool already has and must keep raises KeptPropertyBroken (neither is an
AssertionError); every plant is re-sealed by `fd._recompute_self_checksum` cross-checked against this module's own
CRC32-C, and checked by this module's own reading of `ValidateSuperBlock` to fail exactly the one test it names (or none);
controls (no mark) pass now and must keep passing. Matchers test values and the decided content: the copy read is taken
from every sentence that names one ("read from ... LCN x", "LCN x ..., the copy read"), the superblock `ra supb` shows
from its offset, the volume GUID `summary` prints; hex in either case or zero-padded; a statement on one line or
continued on deeper-indented lines.
"""
import re
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (synthetic volume, Vol, CRC32-C)
import test_1132_red_b_items as BI                       # noqa: E402  (base A carve, runners, scratch)
import test_1132_red_group2 as G2                        # noqa: E402  (`_statements`: a line and its continuation)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep, _red = AB._fx, AB._keep, BI._red
FOREFST, REFSANALYSIS = BI.FOREFST, BI.REFSANALYSIS
_vrun, _ctx = BI._vrun, BI._ctx

CS = AB.CS
D = AB.SUPB_DESC                                         # the self-descriptor offset (+0x78) on both volumes: 0xD0
N_OF = {"synthetic": AB._SYN_CLUSTERS, "image": 0x7C000}
G_BASE, G_HI = 517, 1000                                 # +0x68 values planted (517 in all three copies first)
CORPUS = ("step4continuing/win11refsmini_aftercorruption.raw",
          "step4continuing/win11refsmini_aftercorruption_openedwith34.raw")
CORPUS_PS, CORPUS_N = 0x1000000, 0x7C000
CMDS = {"summary": (FOREFST, "summary"), "fastsummary": (FOREFST, "fastsummary"), "integrity": (FOREFST, "integrity"),
        "files": (FOREFST, "files"), "ra-supb": (REFSANALYSIS, "supb"), "ra-chkp": (REFSANALYSIS, "chkp"),
        "ra-summary": (REFSANALYSIS, "summary"), "ra-supb-verify": (REFSANALYSIS, "supb", "--verify")}
SENTENCE_CMDS = ("summary", "fastsummary", "integrity", "ra-summary", "ra-supb-verify")   # LB69's set (N417's sentence)
NOTE_CMDS = ("summary", "fastsummary", "integrity", "ra-supb")                            # Q4's set


# ─── volumes ──────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.fixture(params=["synthetic", "image"])
def vol(request, tmp_path):
    if request.param == "synthetic":
        yield BI._synthetic_vol(tmp_path)
        return
    with BI._image_vol() as v:
        yield v


@pytest.fixture
def syn(tmp_path):
    return BI._synthetic_vol(tmp_path)


def _n(v):
    return N_OF[v.geo.kind]


def _e3(v):
    return v.geo.backups[0]                              # end-3 = N - 3, the tool's first backup today


def _e2(v):
    return v.geo.backups[1]                              # end-2 = N - 2, refs.sys's first backup (S1)


def _supb_lcns(v):
    return {v.geo.supb} | set(v.geo.backups)


def _pin_geo(v):
    """N from the boot sector's own bytes, and the two backups at N - 3 and N - 2 (the driver's slots, S1)."""
    vbr = v.read(v.geo.vbr, 512)
    n = F.le64(vbr, 0x18) * F.le32(vbr, 0x20) // CS
    _fx(n == _n(v) and _e3(v) == n - 3 and _e2(v) == n - 2, "%s: N = 0x%x, backups %r" % (v.geo.kind, n, v.geo.backups))
    for lcn in sorted(_supb_lcns(v)):
        _fx(_driver_failures(v.block(lcn), lcn, n) == [], "%s: SUPB 0x%x is not valid before any plant: %r"
            % (v.geo.kind, lcn, _driver_failures(v.block(lcn), lcn, n)))


# ─── ValidateSuperBlock, this module's own reading (S5), and the plants ────────────────────────────────────────

def _driver_failures(blk, lcn, n):
    """The `ValidateSuperBlock` tests this block fails, in the driver's order; [] = valid. The checkpoint LCNs are tested
    only when +0x70 passes (the driver reads them from +0x70), both of them whatever +0x74 says (its loop runs twice)."""
    out = []
    if len(blk) < 0xC0:
        return ["size"]
    if not (F.le32(blk, 0x78) == D and blk[D + 0x28:D + 0x2C] == AB._own_digest(blk, D)):
        out.append("checksum")
    if blk[0x20:0x40] != struct.pack("<4Q", lcn, 0, 0, 0):
        out.append("tuple")
    if blk[4] == 0:
        out.append("b04")
    if F.le32(blk, 0x74) != 2:
        out.append("cnt74")
    o = F.le32(blk, 0x70)
    if not (o >= 0xC0 and o + 0x10 <= CS):
        out.append("off70")
    elif any(not (0x1F <= c <= n - 3) for c in struct.unpack_from("<2q", blk, o)):
        out.append("ckpt")
    return out


def _reseal(v, lcn, edit):
    """Edit one superblock copy and re-seal it: fd._recompute_self_checksum, cross-checked against this module's own
    CRC32-C (not the tool's verifier, which keys its descriptor on the signature)."""
    b = bytearray(v.block(lcn))
    recipe = F._self_checksum_recipe(bytes(b), CS)
    _fx(recipe == (D, 1, 4, AB.ZERO_WINDOW), "0x%x: unexpected self-checksum recipe %r" % (lcn, recipe))
    edit(b)
    out = F._recompute_self_checksum(b, CS, recipe)
    _fx(bytes(out[D + 0x28:D + 0x2C]) == AB._own_digest(out, D),
        "0x%x: fd._recompute_self_checksum disagrees with an independent CRC32-C" % lcn)
    v.write(v.at(lcn), bytes(out[:CS]))
    _fx(v.block(lcn) == bytes(out[:CS]), "the re-sealed copy at 0x%x did not land" % lcn)
    v.ops.append("reseal 0x%x" % lcn)


def _q(off, val):
    return lambda b: struct.pack_into("<Q", b, off, val)


def _i(off, val):
    return lambda b: struct.pack_into("<I", b, off, val)


def _g68(val):
    return _q(0x68, val)


def _both(*edits):
    def e(b):
        for x in edits:
            x(b)
    return e


def _move_refs(v, off):
    """+0x70 = off, the checkpoint pair written there (the area checked to be zero first)."""
    lo, hi = v.geo.lo, v.geo.hi

    def e(b):
        _fx(not any(b[off:off + 0x10]) or off == 0xB8, "SUPB +0x%x is not free" % off)
        struct.pack_into("<I", b, 0x70, off)
        struct.pack_into("<2Q", b, off, lo, hi)
    return e


def _flip_sig_to_zero(b):
    b[0:4] = b"\0\0\0\0"


# name -> (edit factory(v, lcn), the one test it fails, the words that name that test)
PLANTS = {
    "tuple-lcn": (lambda v, lcn: _q(0x20, lcn + 1), "tuple"),
    "tuple-tail": (lambda v, lcn: _q(0x28, 1), "tuple"),
    "tuple-last": (lambda v, lcn: _q(0x38, 1), "tuple"),
    "b04-zero": (lambda v, lcn: _i(0x04, 0), "b04"),
    "b04-byte": (lambda v, lcn: _i(0x04, 0x100), "b04"),            # byte +0x04 = 0, the u32 is not
    "cnt74-1": (lambda v, lcn: _i(0x74, 1), "cnt74"),
    "cnt74-3": (lambda v, lcn: _i(0x74, 3), "cnt74"),
    "off70-low": (lambda v, lcn: _move_refs(v, 0xB8), "off70"),
    "off70-end": (lambda v, lcn: _i(0x70, CS - 8), "off70"),
    "ckpt-low": (lambda v, lcn: _q(0xC8, 0x1E), "ckpt"),
    "ckpt-high": (lambda v, lcn: _q(0xC8, _n(v) - 2), "ckpt"),
    "ckpt-negative": (lambda v, lcn: _q(0xC8, (1 << 64) - 1), "ckpt"),
}
EDGES = {                                                # valid to the driver: the bounds are inclusive
    "ckpt-0x1f": lambda v, lcn: _q(0xC8, 0x1F),
    "ckpt-n-3": lambda v, lcn: _q(0xC8, _n(v) - 3),
    "off70-edge": lambda v, lcn: _move_refs(v, CS - 0x10),
}


def _plant(v, lcn, edit, want):
    _reseal(v, lcn, edit)
    got = _driver_failures(v.block(lcn), lcn, _n(v))
    _fx(got == want, "the plant at 0x%x fails %r, not %r" % (lcn, got, want))


def _fail_primary_checksum(v):
    """The primary fails its self-checksum only (one byte at +0x400, outside every tested field)."""
    v.flip(v.at(v.geo.supb, 0x400))
    _fx(_driver_failures(v.block(v.geo.supb), v.geo.supb, _n(v)) == ["checksum"], "the primary fails more than its "
        "checksum")


def _all_g68(v, val):
    for lcn in sorted(_supb_lcns(v)):
        _plant(v, lcn, _g68(val), [])


# ─── reading the output ───────────────────────────────────────────────────────────────────────────────────────

_READ_A = re.compile(r"(?i)\bread from\b(?:(?!\bnot\b|\brather than\b|\binstead of\b|\bLCN 0x)[^;.]){0,40}?"
                     r"\bLCN 0x0*([0-9a-f]+)\b")
_NEGATED = re.compile(r"(?i)\b(?:not|never|no longer)\s+(?:be\s+|been\s+)?$")
# (critic: the first LCN after "read from", never one after "not" / "rather than" / "instead of", never a negated
# "read from" -- "the volume is read from the primary, not from the backup at LCN 0xfe" names no backup as read)
_READ_B = re.compile(r"(?i)\bLCN 0x0*([0-9a-f]+)\b(?:(?!\bLCN 0x)[^;]){0,60}?,\s*the copy (?:the volume is )?read\b")
# (critic: the LCN nearest to ", the copy read" -- a statement that names another copy first is not read as naming it)
_SHOWN = re.compile(r"(?i)ReFS Superblock \(SUPB\) at offset 0x([0-9a-f]+)")
_FAILW = re.compile(r"(?i)\b(not usable|fail(?:s|ed|ing)?|invalid|not valid|reject(?:s|ed)?|does not pass|damaged)\b")
_PAYLOAD = re.compile(r"(?i)\bdiffers? in (?:its|their) payloads?\b")   # A13 / N417's sentence, by its own phrase
_NONE_VALID = re.compile(r"(?i)\bno (?:superblock )?(?:\(SUPB\) )?cop(?:y|ies) (?:is |are )?(?:valid|pass|verif)")
# the failed test, by its offset or by the name the tool gives the field (ra supb: "Checkpoint refs offset/count")
_TOKEN = {"tuple": re.compile(r"(?i)\+?0x0*(?:20|28|30|38)\b|\btuple\b|\bown LCN\b|\bself[- ]?LCN\b|\bits LCN\b"),
          "b04": re.compile(r"(?i)\+?0x0*4\b|\bbyte 4\b"),
          "cnt74": re.compile(r"(?i)\+?0x0*74\b|\bcheckpoint[- ]ref(?:erence)?s?[- ]count\b"),
          "off70": re.compile(r"(?i)\+?0x0*70\b|\bcheckpoint[- ]ref(?:erence)?s?[- ](?:list[- ])?offset\b"),
          "ckpt": re.compile(r"(?i)\bcheckpoint\b")}
_CANNOT_VERIFY = re.compile(r"(?i)\bcannot be verified\b")
_Q4 = re.compile(r"(?i)refs\.sys reads the primary(?: superblock| copy)?(?: \(SUPB\))? when it passes (?:its )?validation")
_Q5_ORDER = re.compile(r"(?i)\+0x68 orders only the two backups")
_EDIT_CONCLUSION = re.compile(r"(?i)edited or damaged|points to an? (?:edit|damage)")
_WHY = (re.compile(r"(?i)\bextend(?:s|ed|ing)? the volume\b"), re.compile(r"(?i)\bone higher\b|\+\s?1\b"),
        re.compile(r"(?i)\bunchanged\b"))
_ROW = re.compile(r"(?im)^\s*SUPB (primary|backup)\s+LCN 0x0*([0-9a-f]+)\b")


def _run(v, cmd):
    tool, *args = CMDS[cmd]
    rc, out, err = _vrun(v, tool, *args)
    return rc, out + "\n" + err, _ctx(rc, out, err, v.ops)


def _read_lcns(text, sup):
    """The superblock copies the output names as the copy read (every sentence that names one)."""
    got = set()
    for s in G2._statements(text):
        for rx in (_READ_A, _READ_B):
            got |= {int(m.group(1), 16) for m in rx.finditer(s)
                    if not (rx is _READ_A and _NEGATED.search(s[max(0, m.start() - 20):m.start()]))} & set(sup)
    return got


def test_matchers_the_copy_read_and_the_failed_test():
    """Not a RED (critic): the matchers on hand-written lines, no tool run."""
    sup = {0x1E, 0xFD, 0xFE}
    yes = {"[forefst] WARNING: the primary superblock (SUPB) at LCN 0x1e (offset 0x1e000) is not usable (+0x74 = 3, "
           "not 2); the volume is read from the backup copy at LCN 0xfe (offset 0xfe000), which passes": {0xFE},
           "NOTE: ... shown below is the backup copy at LCN 0xfe (offset 0xfe000), the copy the volume is read from": {0xFE},
           "     SUPB backup      LCN 0x000fe (offset 0xfe000)  -- checksum OK, the copy read": {0xFE},
           "the volume is read from end-2 (LCN 0xfe) rather than end-3 (LCN 0xfd)": {0xFE},
           "the volume is read from the primary, not from the backup at LCN 0xfe": set(),
           "the backup at LCN 0xfd is not read from": set(),
           "both backups (LCN 0xfd and LCN 0xfe), the copy read is end-2": {0xFE},
           "this view is read from the primary at LCN 0x1e (offset 0x1e000)": {0x1E}}
    for line, want in yes.items():
        assert _read_lcns(line, sup) == want, (line, _read_lcns(line, sup))
    p = "the primary superblock (SUPB) at LCN 0x1e (offset 0x1e000) is not usable (%s); the volume is read from the backup"
    assert _says_not_valid(p % "+0x74 = 3, not 2", 0x1E, "cnt74")
    assert _says_not_valid(p % "its Checkpoint refs count is 3, not 2", 0x1E, "cnt74")
    assert _says_not_valid(p % "Checkpoint refs offset 0xb8 is below 0xc0", 0x1E, "off70")
    assert _says_not_valid(p % "byte 4 is 0", 0x1E, "b04")
    assert not _says_not_valid(p % "self-checksum FAILED (CRC32-C)", 0x1E, "cnt74")
    assert _says_not_valid("no superblock copy is valid (primary at LCN 0x1e: +0x74 = 1, not 2; backups: LCN 0xfd: "
                           "self-checksum FAILED)", 0x1E, "cnt74")
    assert not _says_not_valid("[WARN] the backup superblock (SUPB) at LCN 0xfd (offset 0xfd000) differs in its payload "
                               "from the copy the volume is read from (the primary at LCN 0x1e): +0x74 (1 byte) (...; a "
                               "difference points to an edited or damaged copy)", 0xFD, "cnt74", role="backup")
    assert _says_not_valid("SUPB backup LCN 0xfd (offset 0xfd000) -- fails: +0x74 = 3, not 2", 0xFD, "cnt74",
                           role="backup")


def _shown(text):
    m = _SHOWN.search(text)
    return int(m.group(1), 16) if m else None


def _value_re(x):
    return re.compile(r"(?i)(?<![0-9a-z])(?:%d|0x0*%x)(?![0-9a-z])" % (x, x))


def _primary_segments(s):
    """Each part of a statement from the word 'primary' to the next 'backup' (the primary's clause)."""
    out = []
    for m in re.finditer(r"(?i)\bprimary\b", s):
        rest = s[m.start():]
        k = re.search(r"(?i)\bbackup", rest[7:])
        out.append(rest[:7 + k.start()] if k else rest)
    return out


def _names_test(seg, test, value, n):
    if not _TOKEN[test].search(seg):
        return False
    if test != "ckpt":
        return True
    return bool(AB._lcn_re(value).search(seg) or re.search(r"(?i)0x0*1f\b|-1\b", seg) or AB._lcn_re(n - 3).search(seg))


def _says_not_valid(text, lcn, test, value=None, n=None, role="primary"):
    """Statements (never A13's "differs in its payload" sentence) naming this copy, with the failed test in the copy's
    own clause and a failure word there -- or a statement-level "no copy is valid / passes" (decision 26's form,
    "no superblock copy is valid (primary at LCN 0x1e: +0x74 = 1 ...)")."""
    hits = []
    for s in G2._statements(text):
        if _PAYLOAD.search(s) or not AB._lcn_re(lcn).search(s):
            continue
        segs = _primary_segments(s) if role == "primary" else [s]
        whole = bool(_NONE_VALID.search(s))
        if any((whole or _FAILW.search(g)) and _names_test(g, test, value, n) for g in segs):
            hits.append(s)
    return hits


def _unverifiable(text, lcn):
    """Statements calling the copy at `lcn` one whose checksum 'cannot be verified' (decision 27.3's wording)."""
    return [s for s in G2._statements(text) if AB._lcn_re(lcn).search(s) and _CANNOT_VERIFY.search(s)]


def _differs(text, lcn):
    return [s for s in G2._statements(text) if AB._lcn_re(lcn).search(s) and re.search(r"(?i)\bdiffer", s)]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B15 (Q3) -- a primary that is not valid: end-2 first, end-3 only with a strictly higher +0x68
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# RED 1.13.2 B15: a primary that fails is replaced by end-3 (the tool's first backup); refs.sys reads end-2 when
# both backups are valid with equal +0x68 (Q3; S1, S3) (the strict xfail mark removed: fixed in step C2, area supb)
@pytest.mark.parametrize("cmd", ["summary", "files", "ra-supb", "ra-chkp"])
def test_b15_a_failing_primary_is_replaced_by_end2_when_both_backups_are_valid(vol, cmd):
    _pin_geo(vol)
    _plant(vol, _e3(vol), lambda b: b.__setitem__(0x50, b[0x50] ^ 0x01), [])   # end-3's GUID tells the copies apart
    _fail_primary_checksum(vol)
    rc, text, ctx = _run(vol, cmd)
    got = _read_lcns(text, _supb_lcns(vol))
    assert got == {_e2(vol)}, "the volume must be read from end-2 (LCN 0x%x); the output names %s" % (
        _e2(vol), sorted("0x%x" % x for x in got)) + ctx
    if cmd == "summary":
        assert AB._guid(text) == AB.GUID, "summary's GUID is end-3's, not end-2's: %r" % AB._guid(text) + ctx
    if cmd == "ra-supb":
        assert _shown(text) == vol.at(_e2(vol)), "ra supb shows the copy at 0x%x" % (_shown(text) or 0) + ctx
    _keep(rc == 2, "a primary that fails exits 2 (decision 27.2)" + ctx)


# RED 1.13.2 B15: on the two corpus volumes whose primary fails, the tool reads backup 0x7bffd (end-3); refs.sys
# reads 0x7bffe (end-2): both backups are valid with +0x68 = 1 (MR-B; bootstrap N-1) (the strict xfail mark removed:
# fixed in step C2, area supb)
@pytest.mark.parametrize("cmd", ["summary", "files", "ra-supb"])
@pytest.mark.parametrize("name", CORPUS, ids=["aftercorruption", "openedwith34"])
def test_b15_corpus_a_failing_primary_is_replaced_by_end2(name, cmd):
    p = BI._image_or_skip(name)
    with open(p, "rb") as fh:
        def blk(lcn):
            fh.seek(CORPUS_PS + lcn * CS)
            return fh.read(CS)
        fh.seek(CORPUS_PS)
        vbr = fh.read(512)
        _fx(F.le64(vbr, 0x18) * F.le32(vbr, 0x20) // CS == CORPUS_N, "%s: N" % name)
        _fx(_driver_failures(blk(0x1E), 0x1E, CORPUS_N) == ["checksum"], "%s: the primary" % name)
        for b in (CORPUS_N - 3, CORPUS_N - 2):
            _fx(_driver_failures(blk(b), b, CORPUS_N) == [] and F.le64(blk(b), 0x68) == 1, "%s: backup 0x%x" % (name, b))
    tool, *args = CMDS[cmd]
    rc, out, err = BI._run(tool, p, *args)
    got = _read_lcns(out + "\n" + err, {0x1E, CORPUS_N - 3, CORPUS_N - 2})
    assert got == {CORPUS_N - 2}, "%s: the volume must be read from 0x%x (end-2); the output names %s" % (
        name, CORPUS_N - 2, sorted("0x%x" % x for x in got)) + _ctx(rc, out, err)
    if cmd == "ra-supb":
        assert _shown(out) == CORPUS_PS + (CORPUS_N - 2) * CS, "ra supb shows 0x%x" % (_shown(out) or 0)
    _keep(rc == 2, "a primary that fails exits 2" + _ctx(rc, out, err))


_TOP_BIT = 1 << 63                                       # S4: +0x68 is compared unsigned


def _ranked(v, higher):
    _pin_geo(v)
    up = _e2(v) if higher == "end2" else _e3(v)
    hi = _TOP_BIT if higher == "end3-top-bit" else 2
    _plant(v, up, _g68(hi), [])
    _fail_primary_checksum(v)
    want = {x: (hi if x == up else 1) for x in (_e3(v), _e2(v))}
    _fx(all(F.le64(v.block(x), 0x68) == w for x, w in want.items()), "the backups' +0x68 are not %r (critic: the "
        "ranking rests on them)" % want)
    return up


@pytest.mark.parametrize("cmd", ["files", "ra-supb"])
@pytest.mark.parametrize("higher", [
    # RED 1.13.2 B15: end-2's +0x68 is higher, yet the tool reads end-3 (its first backup); refs.sys keeps end-2 (Q3;
    # S3) (the strict xfail mark removed: fixed in step C2, area supb)
    "end2",
    "end3", "end3-top-bit"])
def test_b15_two_valid_backups_are_ranked_by_g68(syn, higher, cmd):
    """end3: a control -- end-3 strictly higher is read (today: as the tool's first backup; after B15: by S3).
    end3-top-bit: a control (critic) -- end-3's +0x68 = 2**63, end-2's 1: ChooseSuperBlock compares the u64 unsigned
    (S4, read twice), so end-3 is higher and read; a signed comparison would keep end-2."""
    up = _ranked(syn, higher)
    rc, text, ctx = _run(syn, cmd)
    got = _read_lcns(text, _supb_lcns(syn))
    assert got == {up}, "the backup with the higher +0x68 (LCN 0x%x) must be read; named: %s" % (
        up, sorted("0x%x" % x for x in got)) + ctx
    if cmd == "ra-supb":
        assert _shown(text) == syn.at(up), "ra supb shows 0x%x" % (_shown(text) or 0) + ctx


@pytest.mark.parametrize("cmd", ["files", "ra-supb"])
@pytest.mark.parametrize("case", [
    # RED 1.13.2 B15: end-3 fails a ValidateSuperBlock test (+0x74 = 3) with the higher +0x68 and is read; refs.sys
    # passes it over for end-2 (the strict xfail mark removed: fixed in step C2, area supb)
    "end3-invalid-higher",
    "end2-invalid"])
def test_b15_a_backup_that_fails_a_driver_test_is_passed_over(syn, case, cmd):
    """end2-invalid: a control -- end-2 fails (+0x74 = 3), end-3 is read."""
    _pin_geo(syn)
    bad, good = (_e3(syn), _e2(syn)) if case == "end3-invalid-higher" else (_e2(syn), _e3(syn))
    _plant(syn, bad, _both(_i(0x74, 3), _g68(2)) if case == "end3-invalid-higher" else _i(0x74, 3), ["cnt74"])
    _fail_primary_checksum(syn)
    rc, text, ctx = _run(syn, cmd)
    got = _read_lcns(text, _supb_lcns(syn))
    assert got == {good}, "the valid backup (LCN 0x%x) must be read; named: %s" % (
        good, sorted("0x%x" % x for x in got)) + ctx
    _keep(rc == 2, "a superblock fallback exits 2" + ctx)


# RED 1.13.2 B15: a backup without the SUPB signature that passes every ValidateSuperBlock test is skipped; refs.sys
# tests no signature (S5, bootstrap N-6) and reads it as end-2 (the strict xfail mark removed: fixed in step C2,
# area supb)
@pytest.mark.parametrize("cmd", ["summary", "files", "ra-supb"])
def test_b15_a_backup_without_the_signature_that_passes_the_driver_tests_is_valid(syn, cmd):
    """C2 S-F: such a copy is valid at every site of the choice -- the choice, `_verify_self_checksum`'s descriptor
    pointer (its checksum verifies: never "cannot be verified"), the volume GUID (summary: end-2's, never zeros)."""
    _pin_geo(syn)
    _plant(syn, _e2(syn), _flip_sig_to_zero, [])
    _fail_primary_checksum(syn)
    rc, text, ctx = _run(syn, cmd)
    got = _read_lcns(text, _supb_lcns(syn))
    assert got == {_e2(syn)}, "end-2 (LCN 0x%x, no signature, valid to refs.sys) must be read; named: %s" % (
        _e2(syn), sorted("0x%x" % x for x in got)) + ctx
    assert not _unverifiable(text, _e2(syn)), "end-2's self-checksum verifies (the descriptor at +0x78 is read without "\
        "the signature, S-F): %r" % _unverifiable(text, _e2(syn))[:1] + ctx
    if cmd == "summary":
        assert AB._guid(text) == AB.GUID, "summary's GUID must be end-2's (S-F), not %r" % AB._guid(text) + ctx


# RED 1.13.2 B15: a primary without the SUPB signature that passes every ValidateSuperBlock test is replaced by a
# backup; refs.sys reads it (S5: no signature test; Q2, bootstrap N-6) (the strict xfail mark removed: fixed in step
# C2, area supb)
@pytest.mark.parametrize("cmd", ["summary", "files", "ra-supb"])
def test_b15_a_primary_without_the_signature_that_passes_the_driver_tests_is_read(syn, cmd):
    """C2 S-F: valid at every site of the choice -- the choice, its self-checksum verifies (never "cannot be
    verified"), summary's volume GUID is the primary's (never zeros)."""
    _pin_geo(syn)
    _plant(syn, syn.geo.supb, _flip_sig_to_zero, [])
    rc, text, ctx = _run(syn, cmd)
    got = _read_lcns(text, syn.geo.backups)
    assert not got, "the primary is valid to refs.sys and must be read; a backup is named as read: %s" % sorted(
        "0x%x" % x for x in got) + ctx
    assert not _unverifiable(text, syn.geo.supb), "the primary's self-checksum verifies (S-F): %r" \
        % _unverifiable(text, syn.geo.supb)[:1] + ctx
    if cmd == "summary":
        assert AB._guid(text) == AB.GUID, "summary's GUID must be the primary's (S-F), not %r" % AB._guid(text) + ctx
    if cmd == "ra-supb":
        assert _shown(text) == syn.at(syn.geo.supb), "ra supb shows 0x%x" % (_shown(text) or 0) + ctx


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B15 (Q2) -- validity: a re-sealed primary that fails one ValidateSuperBlock test is not read
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _primary_plant(v, name):
    _pin_geo(v)
    factory, test = PLANTS[name]
    edit = factory(v, v.geo.supb)
    _plant(v, v.geo.supb, edit, [test])
    return test, F.le64(v.block(v.geo.supb), 0xC8)


def _check_primary_replaced(v, cmd, name):
    test, ck = _primary_plant(v, name)
    rc, text, ctx = _run(v, cmd)
    got = _read_lcns(text, _supb_lcns(v))
    assert got == {_e2(v)}, "%s: the primary fails ValidateSuperBlock's %s test, so the volume is read from end-2 " \
        "(LCN 0x%x); the output names %s" % (name, test, _e2(v), sorted("0x%x" % x for x in got)) + ctx
    assert _says_not_valid(text, v.geo.supb, test, ck, _n(v)), "%s: no statement says the primary (LCN 0x%x) is not " \
        "valid and names its %s test" % (name, v.geo.supb, test) + ctx
    assert rc == 2, "%s: the volume is read from a backup: exit 2 in every command (decision 27.2), rc=%d" % (name, rc) \
        + ctx


# RED 1.13.2 B15: the primary is accepted on its signature and self-checksum; ValidateSuperBlock's tuple / +0x04 /
# +0x74 / +0x70 / checkpoint-LCN tests are not made (Q2; closure 4.1 rows 4-8) (the strict xfail mark removed: fixed
# in step C2, area supb)
@pytest.mark.parametrize("cmd", ["summary", "files", "ra-supb"])
@pytest.mark.parametrize("name", sorted(PLANTS))
def test_b15_a_primary_that_fails_a_driver_test_is_not_read(syn, name, cmd):
    _check_primary_replaced(syn, cmd, name)


# RED 1.13.2 B15: on base A's carve (N = 0x7c000) the primary that fails a ValidateSuperBlock test is read (the
# strict xfail mark removed: fixed in step C2, area supb)
@pytest.mark.parametrize("name", ["tuple-lcn", "ckpt-high"])
def test_b15_image_a_primary_that_fails_a_driver_test_is_not_read(name):
    with BI._image_vol() as v:
        _check_primary_replaced(v, "files", name)


@pytest.mark.parametrize("name", sorted(EDGES))
def test_b15_control_a_primary_at_the_inclusive_bounds_is_read(syn, name):
    """Not a RED: +0x70 + 0x10 = the cluster, a checkpoint LCN = 0x1F or N - 3 pass ValidateSuperBlock (inclusive bounds,
    26100.8115 :216530-216536); the primary stays the copy read (whatever the checkpoint read at that LCN says)."""
    _pin_geo(syn)
    _plant(syn, syn.geo.supb, EDGES[name](syn, syn.geo.supb), [])
    rc, text, ctx = _run(syn, "files")
    got = _read_lcns(text, syn.geo.backups)
    assert not got, "%s: a valid primary is replaced by %s" % (name, sorted("0x%x" % x for x in got)) + ctx


# RED 1.13.2 B15: no copy is valid (primary +0x74 = 1 re-sealed, both backups fail their checksum): the tool reads
# the primary as if it were valid, says nothing and exits 0; decision 26 reads it with its finding (exit 2) (the
# strict xfail mark removed: fixed in step C2, area supb)
@pytest.mark.parametrize("cmd", ["files", "ra-supb"])
def test_b15_no_valid_copy_reads_the_signed_primary_with_its_finding(syn, cmd):
    _pin_geo(syn)
    _plant(syn, syn.geo.supb, _i(0x74, 1), ["cnt74"])
    for b in syn.geo.backups:
        syn.flip(syn.at(b, 0x400))
        _fx(_driver_failures(syn.block(b), b, _n(syn)) == ["checksum"], "backup 0x%x" % b)
    rc, text, ctx = _run(syn, cmd)
    assert rc == 2, "no superblock copy is valid: exit 2 (decision 26), rc=%d" % rc + ctx
    assert _read_lcns(text, _supb_lcns(syn)) == {syn.geo.supb}, "the statement must name the primary as the copy " \
        "read" + ctx
    assert _says_not_valid(text, syn.geo.supb, "cnt74"), "the statement must say the primary is not valid (+0x74)" + ctx


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B15 -- a backup not in use that fails a driver test (V-a: summary, fastsummary, integrity)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# RED 1.13.2 B15: a backup that fails ValidateSuperBlock's +0x74 test is listed 'checksum OK' / counted intact (it
# is named only by A13's payload sentence); after B15 it is a copy that fails (Q2; V-a) (the strict xfail mark
# removed: fixed in step C2, area supb)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary", "integrity"])
def test_b15_a_backup_that_fails_a_driver_test_is_reported_failed(syn, cmd):
    _pin_geo(syn)
    _plant(syn, _e3(syn), _i(0x74, 3), ["cnt74"])
    rc, text, ctx = _run(syn, cmd)
    assert _says_not_valid(text, _e3(syn), "cnt74", role="backup"), "no line says the backup at LCN 0x%x fails (+0x74)" \
        % _e3(syn) + ctx
    if cmd == "integrity":
        assert re.search(r"(?i)Superblock copies:\s+2\s+(?:intact|valid)\b", text), "integrity must count 2 intact " \
            "copies" + ctx
    _keep(rc == 2, "a redundancy condition exits 2 in %s (V-a)" % cmd + ctx)


def test_b15_control_a_backup_that_fails_a_driver_test_leaves_files_at_exit_0(syn):
    """Not a RED (V-a): the copy is not in use, so a bootstrap-only command exits 0 and reads the primary."""
    _pin_geo(syn)
    _plant(syn, _e3(syn), _i(0x74, 3), ["cnt74"])
    rc, text, ctx = _run(syn, "files")
    assert rc == 0 and not _read_lcns(text, syn.geo.backups), ctx


def test_b15_control_the_redundancy_list_keeps_ascending_lcn_order(vol):
    """Not a RED (Q3): the SUPB rows stay primary, end-3, end-2 when the copy read changes."""
    _pin_geo(vol)
    _fail_primary_checksum(vol)
    rc, text, ctx = _run(vol, "summary")
    rows = [int(m.group(2), 16) for m in _ROW.finditer(text)]
    assert rows == [vol.geo.supb, _e3(vol), _e2(vol)], "SUPB rows %r" % ["0x%x" % x for x in rows] + ctx


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B15 (Q4) -- the primary is valid, a backup that verifies carries another +0x68: a note; nothing where they agree
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _q4_plant(v):
    _pin_geo(v)
    _all_g68(v, G_BASE)
    _plant(v, _e2(v), _g68(G_HI), [])


# RED 1.13.2 B15: a valid primary and a backup that verifies with another +0x68: no line gives both values and says
# 'refs.sys reads the primary when it passes validation' (Q4) (the strict xfail mark removed: fixed in step C2, area
# supb)
@pytest.mark.parametrize("cmd", NOTE_CMDS)
def test_b15_q4_a_backup_with_another_g68_is_noted_with_both_values(vol, cmd):
    _q4_plant(vol)
    rc, text, ctx = _run(vol, cmd)
    _keep(not _read_lcns(text, vol.geo.backups), "the valid primary is read" + ctx)
    _keep(rc == (0 if cmd == "ra-supb" else 2), "the note adds no exit (S-E): N417's redundancy finding keeps "
          "summary / fastsummary / integrity at 2, plain ra supb at 0 (rc=%d)" % rc + ctx)
    said = [s for s in G2._statements(text) if _Q4.search(s)]
    assert said, "no line says 'refs.sys reads the primary when it passes validation'" + ctx
    both = [s for s in said if _value_re(G_BASE).search(s) and _value_re(G_HI).search(s)]
    assert both, "the note must give both +0x68 values (%d and %d): %r" % (G_BASE, G_HI, said[:2]) + ctx


def test_b15_q4_control_files_reads_the_valid_primary_and_exits_0(syn):
    """Not a RED (N450): +0x68 orders only the two backups; a valid primary is read whatever they carry."""
    _q4_plant(syn)
    rc, text, ctx = _run(syn, "files")
    assert rc == 0 and not _read_lcns(text, syn.geo.backups), ctx


@pytest.mark.parametrize("cmd", ["files", "ra-supb"])
def test_b15_control_a_valid_primary_is_read_whatever_the_backups_g68(syn, cmd):
    """Not a RED (N450, S3): both backups carry a higher +0x68; the primary is valid and read."""
    _pin_geo(syn)
    _all_g68(syn, G_BASE)
    for b in syn.geo.backups:
        _plant(syn, b, _g68(G_HI), [])
    rc, text, ctx = _run(syn, cmd)
    assert not _read_lcns(text, syn.geo.backups), ctx
    if cmd == "ra-supb":
        assert _shown(text) == syn.at(syn.geo.supb), ctx


@pytest.mark.parametrize("cmd", NOTE_CMDS)
def test_b15_q4_control_no_note_where_the_copies_agree(vol, cmd):
    """Not a RED (Q4): all three copies carry +0x68 = 517 (re-sealed): no +0x68 note."""
    _pin_geo(vol)
    _all_g68(vol, G_BASE)
    rc, text, ctx = _run(vol, cmd)
    bad = [s for s in G2._statements(text) if _Q4.search(s) or _Q5_ORDER.search(s)]
    assert not bad and rc == 0, "copies that agree get no +0x68 line: %r" % bad[:2] + ctx


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N449 (Q5) -- two copies that both verify and differ: what was measured, no editing conclusion
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _n449_plant(v, plant):
    _pin_geo(v)
    if plant == "guid":
        _plant(v, _e2(v), lambda b: b.__setitem__(0x50, b[0x50] ^ 0x01), [])
    else:
        _q4_plant(v)


_WHERE = {"guid": re.compile(r"(?i)\+?0x0*5[0-9a-f]\b|\bGUID\b"), "g68": re.compile(r"(?i)\+?0x0*68\b")}
_BOTH = re.compile(r"(?i)\bboth\b[^.;]{0,40}\b(?:pass|verif)")


def _check_n449(v, cmd, plant):
    _n449_plant(v, plant)
    rc, text, ctx = _run(v, cmd)
    lines = _differs(text, _e2(v))
    _fx(lines, "`%s` names no differing copy at LCN 0x%x" % (cmd, _e2(v)) + ctx)
    # kept (Q5: the measured facts stay; S-E: the exit stays N417's)
    _keep([s for s in lines if _WHERE[plant].search(s)], "the sentence names where the copies differ" + ctx)
    _keep([s for s in lines if _BOTH.search(s)], "the sentence says both copies pass their self-checksum" + ctx)
    _keep(rc == 2, "two verifying copies that differ: N417's redundancy finding, exit 2 (S-E), rc=%d" % rc + ctx)
    concl = [s for s in lines if _EDIT_CONCLUSION.search(s)]
    assert not concl, "both copies verify: the sentence must draw no editing or damage conclusion (N449): %r" \
        % concl[:1] + ctx
    clause = [s for s in lines if _Q4.search(s) and _Q5_ORDER.search(s)]
    assert clause, "the sentence must say 'refs.sys reads the primary when it passes validation; +0x68 orders only " \
        "the two backups' (Q5): %r" % lines[:1] + ctx
    if plant == "g68":
        assert [s for s in clause if re.search(r"(?i)\bhigher\b", s) or (_value_re(G_BASE).search(s)
                                                                          and _value_re(G_HI).search(s))], \
            "the sentence must say which copy has the higher +0x68 (%d against %d)" % (G_HI, G_BASE) + ctx


# RED 1.13.2 N449: two copies that both verify and differ: the sentence ends 'a difference points to an edited or
# damaged copy' and gives neither the +0x68 values nor refs.sys's rule (Q5) (the strict xfail mark removed: fixed in
# step C2, area supb)
@pytest.mark.parametrize("plant", ["guid", "g68"])
@pytest.mark.parametrize("cmd", SENTENCE_CMDS)
def test_n449_two_verifying_copies_that_differ_get_the_measured_sentence(syn, cmd, plant):
    _check_n449(syn, cmd, plant)


# RED 1.13.2 N449: on base A's carve: the sentence for two verifying copies concludes 'edited or damaged' (Q5) (the
# strict xfail mark removed: fixed in step C2, area supb)
@pytest.mark.parametrize("plant", ["guid", "g68"])
def test_n449_image_two_verifying_copies_that_differ_get_the_measured_sentence(plant):
    with BI._image_vol() as v:
        _check_n449(v, "summary", plant)


@pytest.mark.parametrize("cmd", ["summary", "ra-supb-verify"])
def test_n449_control_a_differing_copy_that_fails_its_checksum_keeps_edited_or_damaged(syn, cmd):
    """Not a RED (A13 branch): end-2's GUID byte flipped, not re-sealed -- it fails its self-checksum; the sentence keeps
    'edited or damaged'."""
    _pin_geo(syn)
    syn.flip(syn.at(_e2(syn), 0x50))
    _fx(_driver_failures(syn.block(_e2(syn)), _e2(syn), _n(syn)) == ["checksum"], "end-2 fails its checksum only")
    rc, text, ctx = _run(syn, cmd)
    lines = _differs(text, _e2(syn))
    assert lines and all(_EDIT_CONCLUSION.search(s) for s in lines), ctx


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N449 (Q6) -- the extend pattern, and only it, gets the "why"
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _extend(v, case):
    """All three at +0x68 = 517 first, then the case's backups / primary (each re-sealed and valid)."""
    _pin_geo(v)
    _all_g68(v, G_BASE)
    e3, e2, p = _e3(v), _e2(v), v.geo.supb
    up = _g68(G_BASE + 1)
    clocks = _both(_q(0x10, 5), _q(0x18, 6))
    guid = lambda b: b.__setitem__(0x50, b[0x50] ^ 0x01)        # noqa: E731
    plan = {"extend": {e3: _both(up, clocks), e2: _both(up, clocks)},
            "extend-g68-only": {e3: up, e2: up},
            "one-backup": {e2: up},
            "plus-2": {e3: _g68(G_BASE + 2), e2: _g68(G_BASE + 2)},
            "guid-too": {e3: _both(up, guid), e2: _both(up, guid)},
            # CB-2 (1.14.0): two backups that differ only in their header clocks (+0x10 / +0x18, the clocks of each copy's
            # write: `FormatSuperPageHeader`, S10) do not differ in content -- that is the extend pattern; "backups-differ"
            # differs in content (one backup's GUID byte)
            "backups-clocks-differ": {e3: _both(up, _q(0x10, 5)), e2: _both(up, _q(0x10, 6))},
            "backups-differ": {e3: up, e2: _both(up, guid)},
            "primary-higher": {p: up}}[case]
    for lcn, edit in sorted(plan.items()):
        _plant(v, lcn, edit, [])


def _why(text):
    return [s for s in G2._statements(text) if all(rx.search(s) for rx in _WHY)]


# RED 1.13.2 N449: the extend pattern (both backups +0x68 = the primary's + 1, equal, differing only at +0x68 and
# +0x10/+0x18) gets no 'why' sentence (Q6) (the strict xfail mark removed: fixed in step C2, area supb)
@pytest.mark.parametrize("case,cmd", [("extend", c) for c in SENTENCE_CMDS] + [("extend-g68-only", "summary"),
                                                                                ("backups-clocks-differ", "summary")])
def test_n449_q6_the_extend_pattern_gets_its_why_sentence(syn, case, cmd):
    _extend(syn, case)
    rc, text, ctx = _run(syn, cmd)
    _fx(_differs(text, _e2(syn)), "no differing-copy sentence" + ctx)
    _keep(rc == 2, "the copies differ: N417's redundancy finding, exit 2 (S-E), rc=%d" % rc + ctx)
    assert _why(text), "no sentence says the copies match what refs.sys writes when it extends the volume (the two " \
        "backups with +0x68 one higher, the primary unchanged)" + ctx


# RED 1.13.2 N449: on base A's carve: the extend pattern gets no 'why' sentence (Q6) (the strict xfail mark removed:
# fixed in step C2, area supb)
def test_n449_q6_image_the_extend_pattern_gets_its_why_sentence():
    with BI._image_vol() as v:
        _extend(v, "extend")
        rc, text, ctx = _run(v, "summary")
        _keep(rc == 2, "the copies differ: N417's redundancy finding, exit 2 (S-E), rc=%d" % rc + ctx)
        assert _why(text), "no extend 'why' sentence" + ctx


@pytest.mark.parametrize("cmd", ["summary", "integrity"])
@pytest.mark.parametrize("case", ["one-backup", "plus-2", "guid-too", "backups-differ", "primary-higher"])
def test_n449_q6_control_any_other_pattern_gets_no_why(syn, case, cmd):
    """Not a RED (Q6: the 'why' only for the exact pattern)."""
    _extend(syn, case)
    rc, text, ctx = _run(syn, cmd)
    _fx(_differs(text, _e2(syn)) or _differs(text, _e3(syn)) or _differs(text, syn.geo.supb),
        "%s: no differing-copy sentence" % case + ctx)
    assert not [s for s in G2._statements(text) if _WHY[0].search(s)], "%s: an extend sentence for another " \
        "pattern" % case + ctx
