"""1.13.2 (ships as 1.14.0) RED cases, wave C step C2, area `chkp_a`: N373 (the validity of a checkpoint copy follows
refs.sys `ValidateCheckpointRecord`, in one definition, and a copy refs.sys rejects is reported).

Read first: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (Q7, Q-M1 = decision 43), `fixes/WAVEC_INVENTORY.md` and
`fixes/WAVEC_CENSUS.md` (row N373), `fixes/WAVEC_READING_bootstrap.md` section 4.2 (the closure table) with its
`_evidence/reading_facts.md` V1-V8 and C1-C3, RUNNING_LOG N373. Report: `analysis/reports/v1.13.2/fixes/RED_C2_chkp_a.md`.

The driver's tests (`CmsVolume::ValidateCheckpointRecord`, its lambda on 26100.x / Insider; read by the prep and again
for this file: 17134 refs_win10.decomp.c:118527-118583, 26100.8115 refs_win11.decomp.c:217196-217253, 26100.8972
refs.decomp.c:216238-216267, 26100.9549 refs.decomp.c:216425-216467, Insider 29574 winsider-refs.decomp.c:285228-285291;
`size` = the record = one cluster, E118):
  V1  the self-checksum (unchanged: decision 27.3 for a type this tool cannot compute).
  V2  n = u32 +0x90: 4 < n <= size / 4.
  V3  (26100.x, Insider; 17134 has no indirect form) flag +0x78 & 0x200: VersionCheck(0x30B), +0x94 + +0x98 <= size,
      +0x98 >= 4, +0x98 >= 4n.
  V5  each of the n offsets (the table at +0x94, or at the offset +0x94 holds when flag 0x200 is set,
      `GetGlobalTableOffset`): >= 4n + K (K = 0x98 on 17134, 0xA8 on 26100.x, 0xB0 on Insider 29574), <= size,
      offset + 0x28 <= size, 8-aligned, the digest length at +0x24 <= size, offset + 0x28 + length <= size.
  V7  the area +0x88 / +0x8C: 26100.x / Insider: length 0, or 4n + K <= offset and offset + length <= size; 17134:
      length <= size, offset <= size, (4n + 0x98 <= offset or length 0), offset + length <= size.
  V4, V6 (feature-gated; decision 43 Q-M1) n < 0x1B (Feature_2834018616) and a root digest length <= 0x20
      (Feature_1069541689): present on 26100.8972, .9444 and .9549 (8972 :216248-216249, :216266-216267), absent on
      26100.8115, .8521 and Insider 29574.
  V8  V1-V7 run in both passes of `ReadLatestCheckpoint`, before and independently of the strict root reads.

What the RED nodes assert (Q7, decision 43; closure B-4.2 rows 3-7):
  (a) a copy that passes its self-checksum but that refs.sys rejects (V2, V3, V5, V7) is not the copy the volume is
      read from (closure rows 3-6 "add to candidacy"; Q1/Q7 "a copy fails when any build read rejects it"), and every
      command of both tools says so -- naming the copy, the test it fails and the builds that reject it -- and exits 2;
  (b) such a copy that is not in use (the older one): V-a -- forefst `summary`, `fastsummary`, `integrity`,
      refsanalysis `summary`, `supb` and `supb --verify` say it and exit 2; the commands that only read through the
      copy in use keep their exit code (control);
  (c) both copies rejected: the newest is read anyway (row 10, unchanged; the lead's N-1 (c): exit 2 everywhere):
      every command names the copy in use with why and exits 2; the V-a set also names the older copy with why
      (it is not in use); the text does not say that a copy fails its self-checksum (both pass it);
  (d) a copy that only some builds reject (K by build): the statement names the builds that reject it and does not
      name 26100.x among them when only Insider 29574 rejects it;
  (e) the feature-gated tests (V4, V6): stated with no change to the exit code or the choice -- the statement names the
      copy, the test, that the builds reject it "when <feature> is enabled" and that the volume does not show whether
      it is (decision 43); the ST-C2 nodes (C2_LEAD_SETTLEMENTS) ask that the builds named are 26100.8972, .9444 and
      .9549 and that Insider 29574, 26100.8115 and .8521 (which make neither test) are not named as rejecting it;
  (f) the N361 / N362 plants (root count 0, a root without an offset) are records refs.sys rejects in every pass
      (V2, V5): the statement now names the builds (the census's "N361/N362 wording adjusted"), and a copy in use
      whose root 7 has no offset is no longer the copy the volume is read from.
17134 (ST-C1, settled by the lead): a build's tests apply only to volumes that build mounts; 17134 mounts version
<= 3.4 only (`RefsMountVolume`, intake A68), so its tests apply only to such volumes (records without flag 0x200), and
the output makes no claim about 17134: no N373 statement on these v3.14 volumes names it (`_names_17134`). The oracle
models 17134 only for a record without flag 0x200 on a volume of version <= 3.4. The corpus controls require no
statement on any corpus volume.

Volumes: the 1 MiB synthetic ReFS 3.14 volume and a scratch carve of the battery's base A (`step1/win11refsmini.raw`)
of `test_1132_red_a_bootstrap.py` (both: flags 0x682, n = 13, the offset table at 0xA8 with +0x98 = 0x38, the
self-descriptor at 0xE0, root descriptors at 0x110 + 0x30 i, the area 0x380 / 0x20; "lo" = slot 0 = the newer copy,
vclock 64; "hi" = slot 1, vclock 63), and corpus volumes read in place (one per checkpoint layout, MR-B).

Conventions (test_1132_red_a_bootstrap.py): every RED is ``xfail(strict=True, raises=AssertionError)``; fixture
problems raise RedFixtureError, a property the tool already has and must keep raises KeptPropertyBroken (neither is an
AssertionError); every plant is re-sealed here (the declared self-descriptor zeroed, this module's own CRC32-C) and
checked with the tool's verifier, and checked by this module's own reading of the driver's tests (`driver_failures`)
to fail exactly the test it names; controls (no mark) pass now and must keep passing. Matchers: a statement is a line
with its deeper-indented continuation lines (`_statements`); hex in either case or zero-padded, or decimal.
"""
import os
import re
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (synthetic volume, Vol, CRC32-C, `vol`)
import test_1132_red_group2 as G2                        # noqa: E402  (`_statements`, `_REJECT`, `_root_named`)
import test_1132_red_g2c as G2C                          # noqa: E402  (the command sets of decision 28 and V-a)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
FOREFST, REFSANALYSIS, CS = AB.FOREFST, AB.REFSANALYSIS, AB.CS
CLOCK_NEW, CLOCK_OLD = AB.CLOCK_NEW, AB.CLOCK_OLD
_ctx, _lcn_re, _statements = AB._ctx, AB._lcn_re, G2._statements

vol = AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module


# ─── this module's own reading of ValidateCheckpointRecord (the oracle the plants are checked against) ────────────

K = (("17134", 0x98), ("26100", 0xA8), ("29574", 0xB0))
le32 = F.le32


def driver_failures(raw, cs=CS, version=(3, 14)):
    """{build: [failed tests]} for '17134', '26100' (26100.x, every build read), '29574' (Insider), and '26100f' (the
    feature-gated tests V4/V6 of 26100.8972/.9444/.9549 with the feature enabled; only those tests). V5/V7 are
    evaluated only when V2 and V3 pass, as the driver returns at the first failure. '17134' is None for a record with
    flag 0x200 or on a volume of a version above 3.4 (ST-C1, settled: a build's tests apply only to volumes that build
    mounts; 17134 mounts version <= 3.4 only, intake A68; it has no indirect form either). V1 (the self-checksum) is
    not modelled: every plant keeps it valid."""
    n, flag = le32(raw, 0x90), le32(raw, 0x78) & 0x200
    a88, l8c = le32(raw, 0x88), le32(raw, 0x8C)
    out = {}
    for b, k in K:
        if b == "17134" and (flag or tuple(version) > (3, 4)):
            out[b] = None
            continue
        f = []
        if not 4 < n <= cs // 4:
            f.append("V2")
        if b != "17134" and flag:
            t94, t98 = le32(raw, 0x94), le32(raw, 0x98)
            if not (version >= (3, 11) and t94 + t98 <= cs and t98 >= 4 and t98 >= 4 * n):
                f.append("V3")
        if not f:
            base, lo = (le32(raw, 0x94) if flag else 0x94), 4 * n + k
            for i in range(n):
                if base + 4 * i + 4 > cs:
                    f.append("V5 root %d (table past the record)" % i)
                    break
                off = le32(raw, base + 4 * i)
                if off < lo or off > cs or off + 0x28 > cs or off % 8:
                    f.append("V5 root %d offset 0x%x" % (i, off))
                    continue
                ln = le32(raw, off + 0x24)
                if ln > cs or off + 0x28 + ln > cs:
                    f.append("V5 root %d digest length 0x%x" % (i, ln))
            area_ok = (l8c <= cs and a88 <= cs and (lo <= a88 or l8c == 0) and a88 + l8c <= cs) if b == "17134" else \
                (l8c == 0 or (lo <= a88 and a88 + l8c <= cs))
            if not area_ok:
                f.append("V7")
        out[b] = f
    g = []
    if n >= 0x1B:
        g.append("V4")
    base = le32(raw, 0x94) if flag else 0x94
    for i in range(min(n, cs // 4)):
        if base + 4 * i + 4 > cs:
            break
        off = le32(raw, base + 4 * i)
        if off + 0x28 <= cs and le32(raw, off + 0x24) > 0x20:
            g.append("V6 root %d" % i)
    out["26100f"] = g
    return out


def _rejecting(raw):
    """The builds (of '26100', '29574'; '17134' where modelled) whose tests fail, without the feature-gated ones."""
    return sorted(b for b, f in driver_failures(raw).items() if b != "26100f" and f)


# ─── plants: each edits one copy, re-seals it, and checks what the driver makes of it ─────────────────────────────

SELF_TO, TABLE_TO = 0x3C0, 0x400      # the relocated layout: free bytes on both volumes (0x3A0..0xFFF are zero)
ROOT2_OFF = 0x170                     # root 2's descriptor on both volumes


def _seal(v, lcn, edit, what):
    """Apply `edit` to the copy at `lcn` and recompute its self-checksum over one cluster with the DECLARED descriptor
    (+0x58 / +0x5C) zeroed -- the driver's ComputeOrVerifySelfChecksumBlock -- with this module's own CRC32-C; then
    the tool's verifier must accept it."""
    b = bytearray(v.block(lcn))
    edit(b)
    d, dl = le32(b, 0x58), le32(b, 0x5C)
    _fx(0x40 <= d and d + dl <= CS and dl >= 0x2C and b[d + 0x22] == 1 and le32(b, d + 0x24) == 4,
        "0x%x: the self-descriptor at 0x%x is not a CRC32-C descriptor" % (lcn, d))
    w = bytearray(b)
    w[d:d + dl] = b"\0" * dl
    struct.pack_into("<I", b, d + 0x28, AB._crc32c(bytes(w)))
    v.write(v.at(lcn), bytes(b))
    _fx(v.verifies(lcn) is True, "0x%x does not verify after re-sealing (%s)" % (lcn, what))
    v.ops.append("%s @0x%x" % (what, lcn))


def _move(b, src, dst, n):
    blk = bytes(b[src:src + n])
    b[src:src + n] = b"\0" * n
    b[dst:dst + n] = blk


def _relocate(b):
    """The self-descriptor 0xE0 -> 0x3C0 and the offset table 0xA8 -> 0x400: frees 0xA8..0x110 for a root descriptor."""
    _fx(le32(b, 0x58) == 0xE0 and le32(b, 0x5C) == 0x30 and le32(b, 0x94) == 0xA8 and le32(b, 0x98) == 0x38
        and not any(b[SELF_TO:TABLE_TO + 0x80]), "the record is not the layout the relocation expects")
    _move(b, 0xE0, SELF_TO, 0x30)
    struct.pack_into("<I", b, 0x58, SELF_TO)
    _move(b, 0xA8, TABLE_TO, 0x38)
    struct.pack_into("<I", b, 0x94, TABLE_TO)


def _move_root(b, idx, dst):
    t = le32(b, 0x94)
    src = le32(b, t + 4 * idx)
    _move(b, src, dst, 0x30)
    struct.pack_into("<I", b, t + 4 * idx, dst)


def _count27(b):
    """n = 27 with every other test passing: the table (0x6C bytes) at 0x400, root 0 moved above 4n + 0xB0 = 0x11C,
    roots 13..26 empty descriptors (no LCN, digest length 0)."""
    _relocate(b)
    t = TABLE_TO
    _move_root(b, 0, 0x470)
    for j in range(13, 27):
        struct.pack_into("<I", b, t + 4 * j, 0x4A0 + 0x30 * (j - 13))
    struct.pack_into("<I", b, 0x90, 27)
    struct.pack_into("<I", b, 0x98, 27 * 4)


def _put(off, val):
    return lambda b: struct.pack_into("<I", b, off, val)


def _root_field(idx, field, val):
    def edit(b):
        t = le32(b, 0x94)
        struct.pack_into("<I", b, le32(b, t + 4 * idx) + field, val)
    return edit


def _root_offset(idx, val):
    def edit(b):
        struct.pack_into("<I", b, le32(b, 0x94) + 4 * idx, val)
    return edit


def _seq(*edits):
    def edit(b):
        for e in edits:
            e(b)
    return edit


# The test words a statement must carry (any wording of the field: the plan fixes no term; the critic broadened
# the writer's "root count" / "offset table" / "align" to the synonyms a correct text may use)
_W_COUNT = r"(?i)\broot count\b|\bnumber of roots\b|\bcount of roots\b|\b(?:0x[0-9a-f]+|\d+) roots?\b|\+?0x90\b"
_W_TABLE = r"(?i)offset table|indirect (?:root )?table|root (?:offset )?table|table (?:length|size)|\+?0x9[48]\b"
_W_ALIGN = r"(?i)align|multiple of 8|8-byte|%\s?8\b|mod(?:ulo)? 8\b"
_W_LOW = r"(?i)offset|\bbelow\b|\bminimum\b|lower bound|\bless than\b|\b4n\b"
_W_PAST = r"(?i)offset|\bpast\b|\bbeyond\b|\bend of the (?:record|cluster|copy)\b|\bexceed"

# name: (edit, {build: expected non-empty?} for 26100 / 29574, feature-gated expected, the test words, the value)
PLANTS = {
    # V2 -- the root count
    "count4": (_put(0x90, 4), ("26100", "29574"), [], _W_COUNT, 4),
    "count0": (_put(0x90, 0), ("26100", "29574"), [], _W_COUNT, 0),
    # V3 -- the indirect offset table
    "table_short": (_put(0x98, 0x30), ("26100", "29574"), [], _W_TABLE, 0x30),
    "table_past": (_put(0x98, 0xF60), ("26100", "29574"), [], _W_TABLE, 0xF60),
    # V5 -- one root's offset or digest length (root 2: not one of the strict roots 0xC, 7, 8)
    "root_unaligned": (lambda b: (_move_root(b, 2, 0x3A4)), ("26100", "29574"), [], _W_ALIGN,
                       0x3A4),
    "root_digest_past": (_root_field(2, 0x24, 0xFD0), ("26100", "29574"), ["V6 root 2"], r"(?i)digest|length",
                         0xFD0),
    "root7_noref": (_root_offset(7, 0), ("26100", "29574"), [], r"(?i)offset|no reference|records no", None),
    # (critic) V5's "offset + 0x28 <= size" (26100.8115 refs_win11.decomp.c:217232): root 2's offset 0xFE0 is 8-aligned,
    # above 4n + K and <= size, but its descriptor would end at 0x1008; today parse_chkp only empties that root
    "root_past": (_root_offset(2, 0xFE0), ("26100", "29574"), [], _W_PAST, 0xFE0),
    # V7 -- the area +0x88 / +0x8C
    "area_past": (_put(0x88, 0xFF0), ("26100", "29574"), [], r"(?i)\+?0x88\b|\barea\b", 0xFF0),
    # K by build (V7 and V5): 26100.x and Insider reject / only Insider rejects
    "area_k26": (_put(0x88, 0xD0), ("26100", "29574"), [], r"(?i)\+?0x88\b|\barea\b", 0xD0),
    "area_k29": (_put(0x88, 0xE0), ("29574",), [], r"(?i)\+?0x88\b|\barea\b", 0xE0),
    "root_k26": (_seq(_relocate, lambda b: _move_root(b, 2, 0xD0)), ("26100", "29574"), [], _W_LOW, 0xD0),
    "root_k29": (_seq(_relocate, lambda b: _move_root(b, 2, 0xE0)), ("29574",), [], _W_LOW, 0xE0),
    "relocated_ok": (_seq(_relocate, lambda b: _move_root(b, 2, 0x440)), (), [], None, None),
    # V4, V6 -- feature-gated (decision 43)
    "v6_digest33": (_root_field(2, 0x24, 0x21), (), ["V6 root 2"], r"(?i)digest|length", 0x21),
    "v4_count27": (_count27, (), ["V4"], _W_COUNT, 27),
}


def plant(v, lcn, name, other_clean=True):
    """Apply plant `name` to the copy at `lcn`; check it fails exactly the builds it names (and the feature-gated
    test it names), and (other_clean) that the other copy is untouched and passes every test."""
    edit, builds, feat, _w, _val = PLANTS[name]
    other = v.geo.hi if lcn == v.geo.lo else v.geo.lo
    ob = v.block(other)
    _fx(not _rejecting(v.block(lcn)) and not driver_failures(v.block(lcn))["26100f"],
        "0x%x already fails a driver test before the plant" % lcn)
    _seal(v, lcn, edit, name)
    raw = v.block(lcn)
    df = driver_failures(raw)
    _fx(_rejecting(raw) == sorted(builds), "%s: rejected by %r, expected %r (%r)" % (name, _rejecting(raw), builds, df))
    _fx(df["26100f"] == feat, "%s: feature-gated %r, expected %r" % (name, df["26100f"], feat))
    _fx(v.block(other) == ob and (not other_clean or not _rejecting(ob)), "the other copy moved or fails a driver test")
    _fx(v.clocks(v.geo.lo) == (CLOCK_NEW, CLOCK_NEW) and v.clocks(v.geo.hi) == (CLOCK_OLD, CLOCK_OLD), "clocks moved")
    return raw


def select(v):
    """THE checkpoint selection of both tools (`checkpoint_select`, single source), as bootstrap calls it."""
    with open(v.path, "rb") as fh:
        return F.checkpoint_select(fh, v.geo.ps, CS, F.parse_supb(fh, v.geo.ps, CS), require_roots=True)


# ─── reading the output ───────────────────────────────────────────────────────────────────────────────────────────

ROOT_OF = {"root_unaligned": 2, "root_digest_past": 2, "root7_noref": 7, "root_k26": 2, "root_k29": 2,
           "v6_digest33": 2, "root_past": 2}
_ACCEPT_OR_NOT = re.compile(r"(?i)\baccept|\bpass(?:es|ed)?\b|\bnot\b|\bneither\b|\bnor\b|would (?:use|mount)")
_FEATURE = re.compile(r"(?i)\bfeature")          # "feature", or its driver name "Feature_2834018616" (critic)
_ENABLED = re.compile(r"(?i)\benabled\b")
_NOT_SHOWN = re.compile(r"(?i)(?:volume|image) does not (?:show|record|say|tell)|does not show whether|cannot be "
                        r"(?:told|read|seen) from the (?:volume|image)|not recorded (?:on|in) the (?:volume|image)")
_STALE = r"(?i)\bchanges committed after vclock %d are not in it\b"
_BUILD_RE = re.compile(r"17134|26100|29574")


def _num(v):
    """A value as the tool may print it: decimal, or hex with 0x (either case, zero-padded)."""
    return r"(?i)(?<![0-9a-z])(?:%d|0x0*%x)(?![0-9a-z])" % (v, v)


def _root_re(idx):
    if idx == 7:
        return None                                      # G2._root_named: "root 7" or "Container Table"
    return re.compile(r"(?i)\broot\s*(?:#|index|idx|no\.?)?\s*(?:0x0*%x|%d)\b" % (idx, idx))


def _root_ok(s, idx):
    return G2._root_named(s, 7) if idx == 7 else _root_re(idx).search(s)


def _said(out, lcn, name):
    """The N373 statements about the copy at `lcn` for plant `name`: they name the copy (its LCN), carry a rejection
    word, name the test (its words, the value it holds and, for a root test, the root) and every build that rejects
    the copy (26100.x, Insider 29574; 17134 is not asserted: ST-1)."""
    _e, builds, _feat, words, val = PLANTS[name]
    idx = ROOT_OF.get(name)
    return [s for s in _statements(out)
            if _lcn_re(lcn).search(s) and G2._REJECT.search(s)
            and (words is None or re.search(words, s)) and (val is None or re.search(_num(val), s))
            and (idx is None or _root_ok(s, idx)) and all(b in s for b in builds)]


def _said_feature(out, lcn, name):
    """Decision 43 (Q-M1): '<builds> reject this copy when <feature> is enabled; the volume does not show whether it
    is' -- the copy, the test (words, value, root), 26100, 'feature', 'enabled', the not-shown clause."""
    _e, _b, _feat, words, val = PLANTS[name]
    idx = ROOT_OF.get(name)
    return [s for s in _statements(out)
            if _lcn_re(lcn).search(s) and G2._REJECT.search(s) and re.search(words, s) and re.search(_num(val), s)
            and (idx is None or _root_ok(s, idx)) and "26100" in s and _FEATURE.search(s) and _ENABLED.search(s)
            and _NOT_SHOWN.search(s)]


def _names_rejecting(s, build):
    """A clause of `s` that lists `build` among the builds that reject the copy (not as accepting it)."""
    return [c for c in re.split(r";|\.\s+|,\s*(?:but|while|whereas)\s|\swhile\s", s)
            if build in c and G2._REJECT.search(c) and not _ACCEPT_OR_NOT.search(c)]


def _names_26100_rejecting(s):
    return _names_rejecting(s, "26100")


def _names_17134(out, lcn):
    """ST-C1 (settled): the output makes no claim about 17134 -- a statement naming the copy at `lcn` with a rejection
    word that names 17134 (17134 does not mount a v3.14 volume, so no claim about it is made)."""
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and G2._REJECT.search(s) and "17134" in s]


def _reject_claims(out):
    """Every statement that says a refs.sys build rejects something, other than the 26100 strict-pass rule of N205
    (roots 0xC, 7, 8) -- the corpus controls' oracle: none may appear on a volume no build rejects."""
    return [s for s in _statements(out) if G2._REJECT.search(s) and _BUILD_RE.search(s)
            and "first (strict) pass" not in s]


_CKSUM_FAILED = re.compile(r"(?i)\bfail(?:s|ed|ing)?\s+(?:its\s+|the\s+|a\s+)?(?:own\s+)?self-checksum"
                           r"|\bchecksum\s*(?:\([^)]*\)\s*)?(?:[:=]\s*)?(?:fail(?:s|ed)?|mismatch)\b")


def _claims_cksum_failed(out, lcn):
    """A statement naming the copy at `lcn` that says it failed its self-checksum (N372's rule: a copy that passes it
    is never said to fail it -- the stale-view text of a self-checksum failure must not be reused for a rejection)."""
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and _CKSUM_FAILED.search(s)]


SUBSET = ("fd-summary", "fd-files", "ra-chkp", "ra-supb")
EVERY = tuple(sorted(G2C._D28))
VA_SAY = tuple(sorted(G2C._N343_SAY))
VA_QUIET = tuple(sorted(G2C._N343_QUIET))
VA_LIST = tuple(G2C._N343_LIST)
_ALL_BUILDS = ("count4", "table_short", "table_past", "root_unaligned", "root_digest_past", "root_past", "area_past")


def _run(v, cmd):
    tool, args = dict(G2C._D28, **G2C._N343_SAY, **G2C._N343_QUIET)[cmd]
    return v.run(tool, *args)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# (a) the NEWEST copy (lo, slot 0, vclock 64) passes its self-checksum but refs.sys rejects it
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix (probe1/probe3, evidence README): every plant below leaves the tools silent -- forefst
# `summary` "CHKP primary LCN 0x48 -- checksum OK, vclock=64, in use", Virtual clock 64, rc 0 (the image's count4:
# rc 2 from an Object-Table / container-mapping finding that follows from reading a copy with 4 roots; ra chkp/supb 0).

_A1 = [(p, c) for p in ("root_unaligned",) for c in EVERY] + \
      [(p, c) for p in _ALL_BUILDS if p != "root_unaligned" for c in SUBSET]


# RED 1.13.2 N373: a copy refs.sys rejects (V2/V3/V5/V7: every build read) is said -- the copy, the test, the builds
# -- and every command exits 2 (Q7; closure B-4.2 rows 3-6); today every command is silent (the strict xfail mark
# removed: fixed in step C2, area chkp_a)
@pytest.mark.parametrize("name,cmd", _A1, ids=["%s-%s" % x for x in _A1])
def test_n373_a_the_newest_copy_refs_sys_rejects_is_stated_and_exits_2(vol, name, cmd):
    plant(vol, vol.geo.lo, name)
    rc, out = _run(vol, cmd)
    assert _said(out, vol.geo.lo, name), (
        "%s must say that refs.sys (26100.x, Insider 29574) rejects the checkpoint copy at LCN 0x%x (%s), naming the "
        "test" % (cmd, vol.geo.lo, name)) + _ctx(vol, rc, out)
    assert not _names_17134(out, vol.geo.lo), "ST-C1: the output makes no claim about 17134 (it does not mount a v3.14 " \
        "volume): %r" % _names_17134(out, vol.geo.lo) + _ctx(vol, rc, out)
    assert not _claims_cksum_failed(out, vol.geo.lo), "the copy at LCN 0x%x passes its self-checksum" % vol.geo.lo + \
        _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


# RED 1.13.2 N373: a copy refs.sys rejects is not the copy the volume is read from (closure B-4.2 rows 3-6 'add to
# candidacy'): the older valid copy is read and the view is stale; today the rejected copy is read (vclock 64) (the
# strict xfail mark removed: fixed in step C2, area chkp_a)
@pytest.mark.parametrize("name", _ALL_BUILDS)
def test_n373_a_the_newest_copy_refs_sys_rejects_is_not_the_copy_read(vol, name):
    plant(vol, vol.geo.lo, name)
    sel = select(vol)
    assert sel["in_use"] is not None and sel["in_use"]["lcn"] == vol.geo.hi, \
        "checkpoint_select reads 0x%x; refs.sys rejects 0x%x, so the copy read is 0x%x" % (
            sel["in_use"]["lcn"] if sel["in_use"] else -1, vol.geo.lo, vol.geo.hi)
    for tool in (FOREFST, REFSANALYSIS):
        rc, out = vol.run(tool, "summary")
        assert AB._virtual_clock(out) == CLOCK_OLD, "summary (%s): Virtual clock %r, expected %d" % (
            os.path.basename(tool), AB._virtual_clock(out), CLOCK_OLD) + _ctx(vol, rc, out)
        assert re.search(_STALE % CLOCK_OLD, out), "the view read from vclock %d is stale: the stale-view clause" % \
            CLOCK_OLD + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# (b) the OLDER copy (hi, not in use) passes its self-checksum but refs.sys rejects it: V-a (decision 20.3)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_B1 = [(p, c) for p in ("root_unaligned", "count4") for c in VA_SAY]


# RED 1.13.2 N373: an older copy refs.sys rejects is a redundancy condition (V-a): summary, fastsummary, integrity,
# ra summary, ra supb (--verify) say it and exit 2; today they are silent and exit 0 (the strict xfail mark removed:
# fixed in step C2, area chkp_a)
@pytest.mark.parametrize("name,cmd", _B1, ids=["%s-%s" % x for x in _B1])
def test_n373_b_the_older_copy_refs_sys_rejects_is_said_by_the_va_set(vol, name, cmd):
    plant(vol, vol.geo.hi, name)
    rc, out = _run(vol, cmd)
    assert _said(out, vol.geo.hi, name), (
        "%s must say that refs.sys rejects the older checkpoint copy at LCN 0x%x (%s)" % (cmd, vol.geo.hi, name)) + \
        _ctx(vol, rc, out)
    assert not _names_17134(out, vol.geo.hi), "ST-C1: the output makes no claim about 17134 (it does not mount a v3.14 " \
        "volume): %r" % _names_17134(out, vol.geo.hi) + _ctx(vol, rc, out)
    assert not _claims_cksum_failed(out, vol.geo.hi), "the copy at LCN 0x%x passes its self-checksum" % vol.geo.hi + \
        _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", VA_QUIET)
def test_n373_b_control_the_bootstrap_only_commands_keep_their_exit_code(vol, cmd):
    """V-a: the commands that only read through the copy in use keep their exit code and say nothing about it."""
    rc0, _o = _run(vol, cmd)
    plant(vol, vol.geo.hi, "root_unaligned")
    rc, out = _run(vol, cmd)
    named = [s for s in _statements(out) if _lcn_re(vol.geo.hi).search(s) and G2._REJECT.search(s)]
    assert rc == rc0 and not named, "%s: %d -> %d, %r" % (cmd, rc0, rc, named) + _ctx(vol, rc, out)


def test_n373_b_control_the_copy_in_use_stays_the_newer_one(vol):
    plant(vol, vol.geo.hi, "root_unaligned")
    assert select(vol)["in_use"]["lcn"] == vol.geo.lo


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# (c) both copies rejected: the newest is read anyway (closure row 10, unchanged)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_NO_CKSUM_PASS = re.compile(r"(?i)\b(?:no|neither) checkpoint copy passes its self-checksum\b")


def _both(v):
    plant(v, v.geo.lo, "root_unaligned")
    plant(v, v.geo.hi, "root_unaligned", other_clean=False)


# RED 1.13.2 N373: no copy refs.sys accepts (C2 N-1 (c): the newest read anyway, exit 2 everywhere): every command
# names the copy in use with why, the V-a set also the older copy, rc 2 in every command, and the text does not say
# that a copy fails its self-checksum (both pass it); today every command is silent and exits 0 (the strict xfail
# mark removed: fixed in step C2, area chkp_a)
@pytest.mark.parametrize("cmd", EVERY)
def test_n373_c_no_copy_refs_sys_accepts_is_stated_and_exits_2(vol, cmd):
    _both(vol)
    rc, out = _run(vol, cmd)
    for lcn in (vol.geo.lo, vol.geo.hi) if cmd in VA_SAY else (vol.geo.lo,):
        assert _said(out, lcn, "root_unaligned"), "%s must say that refs.sys rejects the copy at LCN 0x%x" % (
            cmd, lcn) + _ctx(vol, rc, out)
    for lcn in (vol.geo.lo, vol.geo.hi):
        assert not _names_17134(out, lcn), "ST-C1: the output makes no claim about 17134 (it does not mount a v3.14 " \
            "volume): %r" % _names_17134(out, lcn) + _ctx(vol, rc, out)
    assert not _NO_CKSUM_PASS.search(out) and not [x for lcn in (vol.geo.lo, vol.geo.hi)
                                                    for x in _claims_cksum_failed(out, lcn)], \
        "both copies pass their self-checksum" + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


def test_n373_c_control_the_newest_copy_is_read_anyway(vol):
    _both(vol)
    assert select(vol)["in_use"]["lcn"] == vol.geo.lo


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# (d) K by build: the minimum offset is 4n + 0x98 / 0xA8 / 0xB0 (17134 / 26100.x / Insider 29574), for the root
#     offsets (V5) and the area (V7). n = 13: 26100.x rejects below 0xDC, Insider below 0xE4.
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_K = ("area_k26", "root_k26", "area_k29", "root_k29")
_D1 = [(p, c) for p in _K for c in ("fd-summary", "ra-chkp")]


# RED 1.13.2 N373: the statement names the builds that reject the copy (Q7: K = 0x98 / 0xA8 / 0xB0), and not 26100.x
# when only Insider 29574 rejects it; today nothing is said (the strict xfail mark removed: fixed in step C2, area
# chkp_a)
@pytest.mark.parametrize("name,cmd", _D1, ids=["%s-%s" % x for x in _D1])
def test_n373_d_the_statement_names_the_builds_that_reject_the_copy(vol, name, cmd):
    plant(vol, vol.geo.lo, name)
    rc, out = _run(vol, cmd)
    said = _said(out, vol.geo.lo, name)
    assert said, "%s must say which refs.sys builds reject the copy at LCN 0x%x (%s)" % (cmd, vol.geo.lo, name) + \
        _ctx(vol, rc, out)
    if PLANTS[name][1] == ("29574",):
        assert not [c for s in said for c in _names_26100_rejecting(s)], \
            "26100.x accepts this copy (its bound is 0xDC): %r" % said
    assert not _names_17134(out, vol.geo.lo), "ST-C1: the output makes no claim about 17134 (it does not mount a v3.14 " \
        "volume): %r" % _names_17134(out, vol.geo.lo) + _ctx(vol, rc, out)
    assert not _claims_cksum_failed(out, vol.geo.lo), "the copy passes its self-checksum" + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


# RED 1.13.2 N373: a copy that any build read rejects counts failed (Q1/Q7, closure B-4.2 row 5 'add (K per Q1)'):
# the older copy is read; today the newest is (default D-1) (the strict xfail mark removed: fixed in step C2, area
# chkp_a)
@pytest.mark.parametrize("name", _K)
def test_n373_d_a_copy_any_build_rejects_is_not_the_copy_read(vol, name):
    plant(vol, vol.geo.lo, name)
    sel = select(vol)
    assert sel["in_use"]["lcn"] == vol.geo.hi, "checkpoint_select reads 0x%x (%s)" % (sel["in_use"]["lcn"], name)


@pytest.mark.parametrize("cmd", SUBSET)
def test_n373_d_control_the_relocated_layout_alone_is_accepted(vol, cmd):
    """The plants of (d) move the self-descriptor (0xE0 -> 0x3C0) and the offset table (0xA8 -> 0x400); with root 2
    moved to 0x440 every build accepts the record: no statement, the exit code and the copy in use unchanged."""
    rc0, _o = _run(vol, cmd)
    plant(vol, vol.geo.lo, "relocated_ok")
    rc, out = _run(vol, cmd)
    assert rc == rc0 and not _reject_claims(out), "%s: %d -> %d, %r" % (cmd, rc0, rc, _reject_claims(out)) + \
        _ctx(vol, rc, out)
    assert select(vol)["in_use"]["lcn"] == vol.geo.lo


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# (e) the feature-gated tests (decision 43, Q-M1): stated, no exit change, no change of the copy read
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_FEAT = ("v6_digest33", "v4_count27")
_E1 = [(p, c) for p in _FEAT for c in VA_LIST]


# RED 1.13.2 N373: decision 43: a test 26100.x makes only when a feature is enabled is stated -- the copy, the test,
# 'when <feature> is enabled', the volume does not show whether it is; today nothing is said (the strict xfail mark
# removed: fixed in step C2, area chkp_a)
@pytest.mark.parametrize("name,cmd", _E1, ids=["%s-%s" % x for x in _E1])
def test_n373_e_a_feature_gated_test_is_stated(vol, name, cmd):
    plant(vol, vol.geo.lo, name)
    rc, out = _run(vol, cmd)
    assert _said_feature(out, vol.geo.lo, name), (
        "%s must say that 26100.x rejects the copy at LCN 0x%x when a feature is enabled (%s), and that the volume "
        "does not show whether it is" % (cmd, vol.geo.lo, name)) + _ctx(vol, rc, out)


_E2 = [("v6_digest33", c) for c in EVERY] + [("v4_count27", c) for c in SUBSET]


@pytest.mark.parametrize("name,cmd", _E2, ids=["%s-%s" % x for x in _E2])
def test_n373_e_control_a_feature_gated_test_changes_neither_the_exit_code_nor_the_copy_read(vol, name, cmd):
    """Decision 43: 'stated with no change to the exit code' -- and the copy read stays the newest.
    RC3 (D, 1.14.0): every root of the copy in use is now checked against its reference, and V6's plant (root 2's digest
    length 0x21, past its reference) is also a reference the tool cannot verify, which D states as a condition of the
    view (N362's rule for the copy in use): a command that reads the volume through forefst's bootstrap exits 2 and
    states root 2; refsanalysis `chkp`, `supb` and `containers` (`_D_NO_BOOTSTRAP`), which read their structures without
    it, keep their exit code and say nothing of it."""
    rc0, _o = _run(vol, cmd)
    plant(vol, vol.geo.lo, name)
    rc, out = _run(vol, cmd)
    d = bool(_D_ROOT2.search(" ".join(out.split())))
    if name == "v6_digest33" and cmd not in _D_NO_BOOTSTRAP:
        assert rc == 2 and d, "%s: %d -> %d; D's statement of root 2 %s" % (
            cmd, rc0, rc, "found" if d else "missing") + _ctx(vol, rc, out)
    else:
        assert rc == rc0 and not d, "%s: %d -> %d%s" % (cmd, rc0, rc, "; D's statement found" if d else "") + \
            _ctx(vol, rc, out)
    assert select(vol)["in_use"]["lcn"] == vol.geo.lo


_D_NO_BOOTSTRAP = ("ra-chkp", "ra-chkp-verify", "ra-containers", "ra-supb", "ra-supb-verify")


_D_ROOT2 = re.compile(r"checkpoint root 2 \(Container Allocator\) cannot be verified \(its reference's digest length "
                      r"\(33 bytes\) runs past the reference\)")


_FEAT_BUILDS = ("8972", "9444", "9549")          # ST-C2: the 26100 builds that make V4 and V6
_FEAT_NOT = ("29574", "8115", "8521")            # ST-C2: the builds read that make neither test


# RED 1.13.2 N373: (ST-C2, settled by the lead: decision 43's build list corrected) the builds named are 26100.8972,
# .9444 and .9549 (8972: refs.decomp.c:216248-216249, :216266-216267), and Insider 29574, 26100.8115 and .8521,
# which make neither test, are not named as rejecting the copy; today nothing is said (the strict xfail mark
# removed: fixed in step C2, area chkp_a)
@pytest.mark.parametrize("name", _FEAT)
def test_n373_e_st2_the_feature_gated_statement_names_26100_8972(vol, name):
    plant(vol, vol.geo.lo, name)
    rc, out = _run(vol, "fd-summary")
    said = _said_feature(out, vol.geo.lo, name)
    assert said and all(b in s for s in said for b in _FEAT_BUILDS), \
        "the statement must name 26100.8972, .9444 and .9549: %r" % said + _ctx(vol, rc, out)
    wrong = [(b, c) for s in said for b in _FEAT_NOT for c in _names_rejecting(s, b)]
    assert not wrong, "these builds make neither feature-gated test: %r" % wrong + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# (f) the N361 / N362 plants are records refs.sys rejects in every pass (V2: root count 0; V5: a root offset of 0)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix (probe2): count0 -> "the newest checkpoint copy (LCN 0x48, vclock 64) passes its
# self-checksum, but its root list could not be read (no root references), so this tool does not read the volume from
# it; ..." (no driver claim: N361 had it untraced); root7_noref -> "the checkpoint copy in use at LCN 0x48 (vclock 64):
# root 7 (Container Table) cannot be verified (this copy records no reference for it)", the volume read from it.

_F = [(p, c) for p in ("count0", "root7_noref") for c in SUBSET]


# RED 1.13.2 N373: census 'N361/N362 wording adjusted': a root count of 0 and a root without an offset are tests
# refs.sys makes in every pass (V2, V5, read twice): the statement names the builds that reject the copy; today it
# says only that the root list / the reference cannot be read (the strict xfail mark removed: fixed in step C2, area
# chkp_a)
@pytest.mark.parametrize("name,cmd", _F, ids=["%s-%s" % x for x in _F])
def test_n373_f_the_n361_n362_plants_are_stated_as_refs_sys_rejecting_the_copy(vol, name, cmd):
    plant(vol, vol.geo.lo, name)
    rc, out = _run(vol, cmd)
    assert _said(out, vol.geo.lo, name), "%s must say that refs.sys rejects the copy at LCN 0x%x (%s)" % (
        cmd, vol.geo.lo, name) + _ctx(vol, rc, out)
    assert not _names_17134(out, vol.geo.lo), "ST-C1: the output makes no claim about 17134 (it does not mount a v3.14 " \
        "volume): %r" % _names_17134(out, vol.geo.lo) + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


# RED 1.13.2 N373: a copy in use whose root 7 has no offset is rejected by refs.sys in every pass (V5): the older
# copy is read; today the volume is read from the rejected copy (vclock 64) (the strict xfail mark removed: fixed in
# step C2, area chkp_a)
def test_n373_f_a_copy_whose_root_7_has_no_offset_is_not_the_copy_read(vol):
    plant(vol, vol.geo.lo, "root7_noref")
    got = select(vol)["in_use"]["lcn"]
    assert got == vol.geo.hi, "checkpoint_select reads 0x%x; refs.sys rejects 0x%x (root 7 has no offset)" % (
        got, vol.geo.lo)
    rc, out = vol.run(FOREFST, "summary")
    assert AB._virtual_clock(out) == CLOCK_OLD, "Virtual clock %r" % AB._virtual_clock(out) + _ctx(vol, rc, out)


def test_n373_f_control_a_copy_with_root_count_0_is_already_not_the_copy_read(vol):
    """N361: a copy without a root list is no candidate today (require_roots); it stays so."""
    plant(vol, vol.geo.lo, "count0")
    assert select(vol)["in_use"]["lcn"] == vol.geo.hi


def test_n373_matchers():
    """The matchers accept the decided forms in more than one wording and emit their counterexamples (critic)."""
    lo = 0x48
    a = ("[forefst] WARNING: the newest checkpoint copy (LCN 0x48, vclock 64) passes its self-checksum but fails a test "
         "that refs.sys 26100.x and Insider 29574 make: root 2's offset 0x3a4 is not a multiple of 8, so they reject "
         "it; this view is read from the copy at LCN 0x88 (vclock 63): changes committed after vclock 63 are not in it")
    assert _said(a, lo, "root_unaligned") and not _claims_cksum_failed(a, lo) and not _names_17134(a, lo)
    assert re.search(_STALE % CLOCK_OLD, a)
    for bad in ("the newest checkpoint copy (LCN 0x48, vclock 64) failed its self-checksum (CRC32-C)",
                "CHKP primary LCN 0x48 -- checksum FAILED (CRC32-C), vclock=64"):
        assert _claims_cksum_failed(bad, lo), bad
    assert _NO_CKSUM_PASS.search("no checkpoint copy passes its self-checksum (LCN 0x48, LCN 0x88)")
    c4 = ("the checkpoint copy at LCN 0x48 records 4 roots; refs.sys (26100.x, Insider 29574) rejects a copy with 4 or "
          "fewer")
    assert _said(c4, lo, "count4")
    tb = "refs.sys 26100.x and Insider 29574 reject the copy at LCN 0x48: its indirect table length +0x98 = 0x30 < 4n"
    assert _said(tb, lo, "table_short")
    assert _said("refs.sys 26100.x and Insider 29574 reject the checkpoint copy at LCN 0x48: root 2's descriptor at "
                 "0xfe0 runs past the end of the record", lo, "root_past")
    assert _said("refs.sys 26100.x and Insider 29574 reject the checkpoint copy at LCN 0x48: root 2's descriptor at "
                 "0xd0 lies below 4n + 0xA8 = 0xdc", lo, "root_k26")
    s17 = "refs.sys 17134, 26100.x and Insider 29574 reject the checkpoint copy at LCN 0x48 (root 2 offset 0x3a4)"
    assert _names_17134(s17, lo)
    k29 = ("refs.sys Insider 29574 rejects the checkpoint copy at LCN 0x48: the area at +0x88 = 0xe0 is below "
           "4n + 0xB0 = 0xe4; 26100.x accepts it")
    assert _said(k29, lo, "area_k29") and not [c for s in _said(k29, lo, "area_k29") for c in _names_26100_rejecting(s)]
    assert _names_26100_rejecting("refs.sys 26100.x and Insider 29574 reject the checkpoint copy at LCN 0x48 (area "
                                  "+0x88 = 0xe0)")
    f = ("the checkpoint copy at LCN 0x48 (vclock 64): root 2's digest length is 0x21; refs.sys 26100.8972, .9444 and "
         ".9549 reject this copy when Feature_1069541689 is enabled; the volume does not show whether it is")
    said = _said_feature(f, lo, "v6_digest33")
    assert said and all(b in x for x in said for b in _FEAT_BUILDS)
    assert not [c for x in said for b in _FEAT_NOT for c in _names_rejecting(x, b)]
    f29 = f.replace("and .9549 reject", ".9549 and Insider 29574 reject")
    assert [c for x in _said_feature(f29, lo, "v6_digest33") for c in _names_rejecting(x, "29574")]
    assert not _said_feature(f.replace("; the volume does not show whether it is", ""), lo, "v6_digest33")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# (g) corpus controls: one volume per checkpoint layout (MR-B); every build read accepts every copy (this module's
#     reading), the copy read is the driver's, and `refsanalysis chkp` claims no rejection and exits 0
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Layouts (flag 0x200, min root offset, +0x88, +0x8C, max digest length, cluster): v3.4 direct 0x138/0x680 (4K, 64K);
# indirect 0x110/0x380 (4K, 64K); SHA-256 0x128/0x4d0 (digest length 32 = the V6 bound; 4K, 64K); area length 0
# (labE); Insider 0x118/0x388 and 0x130/0x4d8; direct 0x100/0x370 (23H2).

CORPUS = ("step1/win10refsmini.raw", "step2/win10refs5g64k.raw", "step2/win11refs2g.raw", "step2/win11refs5g64k.raw",
          "step2/win11refs2g_sha256checksums.raw", "step3/win11refs2t64ksha256checksums.raw",
          "step7/labEnotdetached.raw", "step4/wininsiderrefs2t.raw", "step4/win1123h2test.raw",
          "step4/wininsiderrefs8gtest2.raw")


def _corpus(name):
    from test_image_holes_and_page_refs import _corpus_image
    import test_1132_red_b_items as BI
    p = _corpus_image(name)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % name)
    return p, BI._refs_ps(p), BI


def _driver_pick(copies):
    """ReadLatestCheckpoint (C1, F1): slot order, the first valid copy kept, replaced on a strictly greater +0x60."""
    best = None
    for c in copies:
        if best is None or c[1] > best[1]:
            best = c
    return best


@pytest.mark.parametrize("name", CORPUS)
def test_n373_g_control_no_corpus_copy_is_rejected_and_the_copy_read_is_the_drivers(name):
    p, ps, BI = _corpus(name)
    with open(p, "rb") as fh:
        cs, vmaj, vmin = F.parse_vbr(fh, ps)[:3]
        _fx(cs in (4096, 65536), "%s: cluster size %r" % (name, cs))
        lcns = F.parse_supb(fh, ps, cs)
        sel = F.checkpoint_select(fh, ps, cs, lcns, require_roots=True)
    valid = []
    for c in sel["copies"]:
        _fx(c["sig_ok"] and c["cksum_ok"] is True, "%s: copy 0x%x is not a verifying CHKP" % (name, c["lcn"]))
        df = driver_failures(bytes(c["raw"]), cs, (vmaj, vmin))
        _fx(not any(f for b, f in df.items() if f), "%s: copy 0x%x fails %r" % (name, c["lcn"], df))
        valid.append((c["lcn"], c["vc"]))
    assert sel["in_use"]["lcn"] == _driver_pick(valid)[0], "%s: the copy read is not the driver's" % name
    rc, out, err = BI._run(REFSANALYSIS, p, "chkp")
    assert rc == 0 and not _reject_claims(out + "\n" + err), "%s: ra chkp rc=%d, %r" % (
        name, rc, _reject_claims(out + "\n" + err))
