"""1.13.2 (ships as 1.14.0) RED cases, wave C step C2, area `chkp_b`: N394 and N384 (a checkpoint copy that cannot be
read) and N376 (the redundancy scanner's per-copy JSON record).

Read first: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (Q25, Q26), `fixes/WAVEC_INVENTORY.md` and
`fixes/WAVEC_CENSUS.md` (rows N394, N384, N376), `fixes/WAVEC_READING_bootstrap.md` section 4.2, RUNNING_LOG N394, N384,
N376, and T1 / T1a / T1b (`fixes/GROUP3_PREP.md`). Report: `analysis/reports/v1.13.2/fixes/RED_C2_chkp_b.md`.

The decided output (settled; WAVEC_BRIEF Q25, Q26, T1):
  Q25 (N394, N384)  a checkpoint copy that cannot be read is a `view` condition (T1: its clock is unknown, so whether
            the view is read from the newest checkpoint cannot be known; decision 28's reason): exit 2 in every command
            of both tools, no placeholder fields, and it is said with its cause -- past the image end, or a read the
            host (or the tool, past any file offset) refuses.
  Q26 (N376)  the per-copy record of `summary --json`, `fastsummary --json` and `integrity --json`: `roots_ok`
            corrected in place (true only when every root 0xC, 7, 8 was checked and passed); `use` on every copy
            (decision 25.4 / K18 words); the new key `RootUnchecked` (a list, always present, `[]` when none).

What the RED nodes assert (measured before the fix: `fixes/C2_red_evidence/chkp_b/`, probes 1-6):
  N394 (a)  a copy whose READ fails (its reference too large for any file offset, re-sealed into all three superblock
            copies, the g2c3 N371 plant as C2 ST-S1 (c) settles it; LCN 0x123456789abcdef so that no number in the
            tool's error text is the LCN): every form of T1b's representative surface names the copy, says it could
            not be read, gives the cause, and exits 2. Today only the redundancy list (fd `summary`, `fastsummary`,
            `integrity`, ra `summary`) and ra `supb --verify` say it (controls); the other forms record an anonymous
            skip ("bootstrap skipped a bootstrap structure: OffsetTooLarge ...") and ra `supb`, `supb -v`, `supb -vv`
            exit 0. The same for the copy in slot 0, and for a reference the host refuses (EINVAL, modelled in the
            tool's process as g2c3 K-6 does).
  N394 (b)  no placeholder field: ra `supb` prints `vc=? ac=?`, `supb -v` / `-vv` `sig=???? vc=? ac=? ver=?.?` today;
            `supb --verify`'s checksum row says "no CHKP signature" for a copy of which nothing was read.
  N394 (c)  the shared condition table (`_checkpoint_conditions`, one definition) files such a copy as a `view`
            condition, as it files a copy that was read without a signature (N374); today `redundancy`.
  N384 (a)  refsanalysis `chkp`, `chkp -v`, `chkp -vv`, `chkp --verify` name a copy whose read fails (LCN, could not
            be read, the cause) and exit 2; today an anonymous skip ("cmd_chkp skipped a checkpoint: ...").
  N384 (b)  a copy past the image end (a truncated image; the primary superblock's second reference inside the
            volume, past the image end, re-sealed -- a superblock every build accepts, closure B-4.1 row 8): every
            form says it with that cause. Today every form says "nothing could be read there" (N374 made it a view
            condition: exit 2 and the statement are controls); the copy rows of fd `summary` / `fastsummary` /
            `integrity` and `supb --verify`'s roots row say "no CHKP signature" for it; the JSON `Unreadable` value
            carries the same text.
  N376      `RootUnchecked` on every record; it lists root 7 when root 7's reference declares checksum type 3 (the g2c2
            N362 `type` plant, which no driver test rejects); `roots_ok` false for a copy whose root 7 does not verify
            or cannot be verified; `use` = "superseded" on the older copy without a root list (today null).
Controls: the undamaged volume (no copy said unreadable, no placeholder), the forms that already state the copy, the
past-the-end exit and statement, `roots_ok` / `use` where right today, the copy rows' "(roots unreadable)" (a text
consumer of `roots_ok`: it must not move when `roots_ok` is corrected), and a copy that fails its self-checksum
stays a `redundancy` condition (V-a).

Volumes: the 1 MiB synthetic ReFS 3.14 volume and a scratch carve of the battery's base A (`step1/win11refsmini.raw`)
of `test_1132_red_a_bootstrap.py` ("lo" = slot 0 = the newer copy, vclock 64; "hi" = slot 1, vclock 63).

Conventions (test_1132_red_a_bootstrap.py): every RED is ``xfail(strict=True, raises=AssertionError)``; fixture
problems raise RedFixtureError, a property the tool already has and must keep raises KeptPropertyBroken (neither is an
AssertionError); every plant checks that it landed; controls (no mark) pass now and must keep passing. Matchers: a
statement is a line with its deeper-indented continuation lines (`_statements`); an LCN in hex, either case or
zero-padded; the cause and the "could not be read" words are matched by meaning (several phrasings), not one text.
"""
import errno
import json
import os
import re
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (synthetic volume, Vol, `vol`, damage recipes)
import test_1132_red_group2 as G2                        # noqa: E402  (`_statements`)
import test_1132_red_g2c as G2C                          # noqa: E402  (N343 / N361 plants, `_run_split`)
import test_1132_red_g2c2 as G2C2                        # noqa: E402  (N362 `plant_root_unchecked`)
import test_1132_red_g2c3 as G2C3                        # noqa: E402  (the modelled file system of K-6)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep, _ctx, _lcn_re = AB._fx, AB._keep, AB._ctx, AB._lcn_re
FOREFST, REFSANALYSIS, CS = AB.FOREFST, AB.REFSANALYSIS, AB.CS
_statements = G2._statements

vol = AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module


# ─── the representative surface (T1b, GROUP3_PREP) and the JSON forms (N376) ─────────────────────────────────────

T1B = {"fd-files": (FOREFST, ("files",)), "fd-search": (FOREFST, ("search", "ok")),
       "fd-timeline": (FOREFST, ("timeline",)), "fd-deleted": (FOREFST, ("deleted",)),
       "fd-summary": (FOREFST, ("summary",)), "fd-fastsummary": (FOREFST, ("fastsummary",)),
       "fd-integrity": (FOREFST, ("integrity",)), "ra-files": (REFSANALYSIS, ("files",)),
       "ra-summary": (REFSANALYSIS, ("summary",)), "ra-supb": (REFSANALYSIS, ("supb",)),
       "ra-supb-v": (REFSANALYSIS, ("supb", "-v")), "ra-supb-vv": (REFSANALYSIS, ("supb", "-vv")),
       "ra-supb-verify": (REFSANALYSIS, ("supb", "--verify")), "ra-chkp": (REFSANALYSIS, ("chkp",)),
       "ra-chkp-v": (REFSANALYSIS, ("chkp", "-v")), "ra-chkp-vv": (REFSANALYSIS, ("chkp", "-vv")),
       "ra-chkp-verify": (REFSANALYSIS, ("chkp", "--verify")), "ra-containers": (REFSANALYSIS, ("containers",))}
SUPB_FORMS = ("ra-supb", "ra-supb-v", "ra-supb-vv", "ra-supb-verify")
CHKP_FORMS = ("ra-chkp", "ra-chkp-v", "ra-chkp-vv", "ra-chkp-verify")
JSON_FORMS = {"fd-summary-json": ("summary", "--json"), "fd-fastsummary-json": ("fastsummary", "--json"),
              "fd-integrity-json": ("integrity", "--json")}
ROW_FORMS = ("fd-summary", "fd-fastsummary", "fd-integrity")      # print one status row per checkpoint copy


# ─── plants (each checks that it landed) ─────────────────────────────────────────────────────────────────────────

HUGE_LCN = 0x123456789ABCDEF        # ps + LCN x 4096 > 2**63 - 1: no file offset; no number of the error text is it
HOST_LCN = 1 << 38                  # g2c3 K-6: offset ~2**50, refused by the modelled file system (EINVAL)
PASTEND = {"synthetic": (0xF8, 0xF0 * CS), "image": (0x7BF00, 0x7C000000)}    # (reference, truncated image size)


def _vbr_clusters(v):
    """N from the boot sector: total sectors x bytes per sector // cluster size (closure B-4.1 row 8's bound)."""
    b = v.read(v.geo.vbr, 512)
    bps, spc = F.le32(b, 0x20), F.le32(b, 0x24)
    _fx(bps * spc == CS, "%s: cluster size %d x %d" % (v.geo.kind, bps, spc))
    return F.le64(b, 0x18) * bps // CS


def plant_supb_ref(v, slot, value):
    """Every superblock copy's checkpoint reference `slot` (+0xC0 + 8 slot) set to `value`, each copy re-sealed. C2
    ST-S1 (c) (fixes/C2_LEAD_SETTLEMENTS.md, the g2c3 N371 plant): the value is outside [0x1F, N - 3], so no copy
    passes ValidateSuperBlock (closure B-4.1 row 8) and decision 26 reads the primary with its finding -- the
    reference is still read, and the copy's read fails."""
    g = v.geo
    want = [g.lo, g.hi]
    want[slot] = value

    def edit(b):
        struct.pack_into("<Q", b, 0xC0 + 8 * slot, value)
    for lcn in (g.supb,) + tuple(g.backups):
        v.reseal(lcn, edit, AB.SUPB_DESC)
        _fx(v.refs(lcn) == want and v.verifies(lcn) is True, "the checkpoint list of the superblock copy at 0x%x is %r"
            % (lcn, v.refs(lcn)))
    _fx(value > _vbr_clusters(v) - 3, "0x%x is inside the volume" % value)
    return value


def plant_past_end(v):
    """The primary superblock's second reference set to an LCN inside the volume ([0x1F, N - 3]: a superblock every
    build accepts) and the image truncated before that LCN: the copy lies past the image end (N384's shape, B3's
    truncated image). The copy in slot 0 and every root page stay inside the image."""
    g = v.geo
    ref, size = PASTEND[g.kind]
    n = _vbr_clusters(v)
    _fx(0x1F <= ref <= n - 3, "0x%x is outside [0x1f, 0x%x]" % (ref, n - 3))

    def edit(b):
        struct.pack_into("<Q", b, 0xC8, ref)
    v.reseal(g.supb, edit, AB.SUPB_DESC)
    _fx(v.refs(g.supb) == [g.lo, ref] and v.verifies(g.supb) is True, "the primary's list is %r" % v.refs(g.supb))
    os.truncate(v.path, size)
    v.ops.append("truncate 0x%x" % size)
    _fx(os.path.getsize(v.path) == size <= g.ps + ref * CS, "the copy at 0x%x is not past the image end" % ref)
    sel = select(v)
    _fx([c["lcn"] for c in sel["copies"]] == [g.lo, ref] and not sel["copies"][1]["raw"]
        and sel["in_use"] is not None and sel["in_use"]["lcn"] == g.lo and sel["in_use"]["vc"] == AB.CLOCK_NEW,
        "after the plant: %r" % [(hex(c["lcn"]), len(c["raw"]), c["vc"]) for c in sel["copies"]])
    return ref


def select(v, lcns=None, fh_wrap=None):
    """THE checkpoint selection of both tools (`checkpoint_select`, single source), as bootstrap calls it; `lcns`
    replaces the superblock's list (an in-process plant), `fh_wrap` wraps the image file (a modelled file system)."""
    with open(v.path, "rb") as fh:
        f = fh_wrap(fh) if fh_wrap else fh
        return F.checkpoint_select(f, v.geo.ps, CS, lcns if lcns is not None else F.parse_supb(f, v.geo.ps, CS),
                                   require_roots=True)


class _RefusingFile:
    """The image file as a file system that cannot hold an offset past g2c3's _FS_MAX_OFFSET serves it: a seek there
    raises OSError(EINVAL) before any I/O, as ext4's lseek does (g2c3 K-6, measured on the gate host)."""

    def __init__(self, fh):
        self._fh, self.refused = fh, []

    def seek(self, off, whence=0):
        if whence == 0 and off > G2C3._FS_MAX_OFFSET:
            self.refused.append(off)
            raise OSError(errno.EINVAL, "Invalid argument")
        return self._fh.seek(off, whence)

    def __getattr__(self, name):
        return getattr(self._fh, name)


def _run(v, form):
    tool, args = T1B[form]
    return v.run(tool, *args)


def _run_host(v, form):
    """A form run with the image served by g2c3's modelled file system; the planted copy's offset must be refused."""
    tool, args = T1B[form]
    rc, out, tb, refused = G2C3._run_refusing(v, tool, *args)
    _fx(not tb, "%s crashed (a crash is never the defect under test)" % form + _ctx(v, rc, out))
    _fx(v.geo.ps + HOST_LCN * CS in refused, "%s: the planted copy's offset was never refused (%r)" % (form, refused))
    return rc, out


# ─── reading the output ──────────────────────────────────────────────────────────────────────────────────────────

# critic: also the active voice ("could not read", "failed to read") and "read failed" / "read error" -- Q25 fixes the
# meaning (the copy could not be read), not the voice
_UNREAD = re.compile(r"(?i)\b(?:could not|cannot|can ?not|can't) be read\b|\bunreadable\b|\bnot readable\b"
                     r"|\bwas not read\b|\bnothing (?:could be|was) read\b"
                     r"|\b(?:could not|cannot|can ?not|can't|failed to|unable to) read\b|\bread (?:failed|error)\b")
_PAST_END = re.compile(r"(?i)\b(?:past|beyond|after|outside)\s+(?:the\s+)?(?:end\s+of\s+the\s+image|image(?:'s)?\s+end"
                       r"|image)\b|\bimage\s+(?:ends|stops)\b"
                       r"|\bimage\s+(?:is\s+)?(?:truncated|shorter)\b|\btruncated\s+image\b")     # critic: + truncated / shorter
_CAUSE_HUGE = re.compile(r"(?i)largest file offset|(?:past|beyond) any (?:possible )?file offset|larger than any file "
                         r"offset|no file offset|no file (?:can|could)|too\s*large|"     # critic: + OffsetTooLarge, any/no
                         + _PAST_END.pattern.replace("(?i)", ""))
_CAUSE_HOST = re.compile(r"(?i)\berrno 22\b|invalid argument|\beinval\b|\brefus|\breject|\bhost\b|"   # critic: + reject, host
                         + _PAST_END.pattern.replace("(?i)", ""))
# critic: a field printed with no value is a placeholder whatever stands in for the value ("?", "-", "n/a", "none",
# "unknown", nothing) -- T1a / Q25 "no placeholder fields"; none of these on the undamaged volume's 18 forms (measured)
_PLACEHOLDER = re.compile(r"(?i)\b(?:vc|ac|sig|ver)=(?:\?|-+(?!\w)|n/?a\b|none\b|null\b|unknown\b|(?=\s|$))|=\?{2,}"
                          r"|\?\.\?")
# critic: "no CHKP signature was read / could be checked" says nothing about the bytes, so it is not a claim
_NO_SIG = re.compile(r"(?i)\bno CHKP signature\b(?!\s+(?:was|could be|can be)\s+(?:read|checked|seen))|\bcarries no CHKP\b"
                     r"|\bwithout (?:a |its )?CHKP signature\b")
_ROOTS_UNREADABLE = re.compile(r"(?i)\(roots unreadable\)")


def _said(out, lcn, cause):
    """Statements naming the copy at `lcn` that say it could not be read and give `cause`."""
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and _UNREAD.search(s) and cause.search(s)]


def _no_sig_claims(out, lcn):
    """Lines AND statements (a line with its continuation lines, critic) that name the copy and say it carries no CHKP
    signature: a fix that moves the claim to a continuation line below the LCN still makes it."""
    return [t for t in out.splitlines() + _statements(out) if _lcn_re(lcn).search(t) and _NO_SIG.search(t)]


def _json_records(stdout):
    """{lcn: record} of the one per-copy checkpoint list of a forefst --json document (`bootstrap_backups.checkpoints`
    in summary / fastsummary, `redundancy.backup_copies.checkpoints` in integrity)."""
    try:
        j = json.loads(stdout)
    except ValueError:
        i, k = stdout.find("{"), stdout.rfind("}")
        _fx(0 <= i < k, "no JSON document on stdout: %r" % stdout[:300])
        j = json.loads(stdout[i:k + 1])
    found = []

    # acceptance 1.14.0 (K21, K9): the list is `Checkpoints`, each record's `LCN` a hex string
    def walk(o, path):
        if isinstance(o, dict):
            for key, x in o.items():
                if key == "Checkpoints" and isinstance(x, list) and x and \
                        all(isinstance(r, dict) and "LCN" in r for r in x):
                    found.append((path + "." + key, x))
                else:
                    walk(x, path + "." + key)
        elif isinstance(o, list):
            for i, x in enumerate(o):
                walk(x, "%s[%d]" % (path, i))
    walk(j, "")
    _fx(len(found) == 1, "per-copy checkpoint lists: %r" % [p for p, _x in found])
    return {int(r["LCN"], 16): r for r in found[0][1]}


def _f(r, name):
    """A record's field by its internal name, under its output name (K21: `roots_ok` -> RootsOK)."""
    return r.get(F.out_key(name))


def _json_run(v, form):
    rc, out, err = G2C._run_split(FOREFST, v.path, *JSON_FORMS[form], cwd=os.path.dirname(v.path), cli=v.geo.cli)
    return rc, _json_records(out), out, err


def _root_index(x):
    """One root index: an int or an index string ("0x7", "7"); None otherwise (a bool is no index)."""
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, str) and re.fullmatch(r"(?i)0x[0-9a-f]+|\d+", x):
        return int(x, 0)
    return None


def _root_indices(val):
    """The root indices a `RootUnchecked` list names: ints, [index, why] pairs (root_fail's form), {Root: index, ...}
    objects or index strings ("0x7", "7"), also inside a pair or an object (critic: hex strings, the one-form rule);
    None for an item none of these."""
    out = set()
    for it in val:
        if isinstance(it, (list, tuple)):
            out.add(_root_index(it[0]) if it else None)
        elif isinstance(it, dict):
            ks = [k for k in it if k.lower() in ("root", "index", "rootindex", "idx")]
            out.add(_root_index(it[ks[0]]) if ks else None)
        else:
            out.add(_root_index(it))
    return out


def _jctx(rec, rc, out, err):
    return "\nrecords=%s | rc=%d\n%s" % (json.dumps({hex(k): v for k, v in rec.items()}, default=str)[:3000], rc,
                                          err[-1500:])


def test_matchers():
    huge = ("[forefst] WARNING: the checkpoint copy at LCN 0x123456789abcdef could not be read (offset "
            "0x123456789abcdef000 is beyond the largest file offset, 0x7fffffffffffffff)")
    assert _said(huge, HUGE_LCN, _CAUSE_HUGE) and not _said(huge, HUGE_LCN, _PAST_END)
    skip = ("[forefst] WARNING: bootstrap skipped a bootstrap structure: OffsetTooLarge: offset 0x123456789abcdef000 "
            "is beyond the largest file offset, 0x7fffffffffffffff")
    assert not _said(skip, HUGE_LCN, _CAUSE_HUGE)          # an anonymous skip: no LCN, no "could not be read"
    host = "  [WARN] the checkpoint copy at LCN 0x4000000000 could not be read ([Errno 22] Invalid argument)"
    assert _said(host, HOST_LCN, _CAUSE_HOST) and not _said(host, HOST_LCN, _CAUSE_HUGE)
    today = ("WARNING: the checkpoint copy at LCN 0xf8 (offset 0xf8000) is unreadable: nothing could be read there. It "
             "has no clock this tool can read, so whether this view ... cannot be known")
    assert _said(today, 0xF8, re.compile(".")) and not _said(today, 0xF8, _PAST_END)
    for ok in ("the checkpoint copy at LCN 0xf8 (offset 0xf8000) cannot be read: it lies past the end of the image",
               "the checkpoint copy at LCN 0xF8 is unreadable: the image ends at offset 0xf0000, before it",
               "checkpoint copy LCN 0x0f8 could not be read (beyond the image end, 0xf0000 bytes)"):
        assert _said(ok, 0xF8, _PAST_END), ok
    assert not _lcn_re(0xF8).search("offset 0xf8000") and not _lcn_re(HUGE_LCN).search("0x123456789abcdef000")
    assert _PLACEHOLDER.search("  CHKP #2: cluster 0x7B -> 0x7B000  vc=? ac=?")
    assert _PLACEHOLDER.search("       sig=???? vc=? ac=? ver=?.?")
    assert not _PLACEHOLDER.search("  CHKP #1: cluster 0x48 -> 0x48000  vc=64 ac=61 *")
    for ph in ("vc=- ac=-", "sig=n/a", "ver=unknown", "vc= ac=61", "ac=None"):
        assert _PLACEHOLDER.search("  CHKP #2: cluster 0x7B -> 0x7B000  " + ph), ph
    assert not _PLACEHOLDER.search("    self_block=0x48 ver=3.14 sig=b'CHKP' vc=-1")
    assert _no_sig_claims("CHKP secondary   LCN 0xf8 (offset 0xf8000)  — unreadable: no CHKP signature", 0xF8)
    assert _no_sig_claims("chkp_2_roots  WARN  LCN 0xf8 (offset 0xf8000): roots ... this copy carries no CHKP "
                          "signature", 0xF8)
    assert _root_indices([7]) == {7} == _root_indices([[7, "cannot be verified"]]) == _root_indices(["0x7"]) \
        == _root_indices([{"Root": 7, "Why": "x"}])
    assert _root_indices([]) == set() and _root_indices([True]) == {None}
    # critic: the active voice, the exception's name, the host's words, a truncated image, a hex index in a pair/object
    assert _said("the tool could not read the checkpoint copy at LCN 0x123456789abcdef (OffsetTooLarge)", HUGE_LCN,
                 _CAUSE_HUGE)
    assert _said("checkpoint copy LCN 0x123456789ABCDEF: read failed, no file offset holds it", HUGE_LCN, _CAUSE_HUGE)
    assert _said("the checkpoint copy at LCN 0x4000000000: read error (the host rejected the offset)", HOST_LCN,
                 _CAUSE_HOST)
    assert _said("the checkpoint copy at LCN 0xf8 is unreadable: the image is truncated at offset 0xf0000", 0xF8,
                 _PAST_END)
    assert not _said("the checkpoint copy at LCN 0xf8 could not be read (OffsetTooLarge)", 0xF8, _PAST_END)
    assert not _no_sig_claims("chkp_2_checksum FAIL LCN 0xf8: no CHKP signature could be checked (nothing was read)",
                              0xF8)
    assert _no_sig_claims("  chkp_2_roots WARN LCN 0xf8 (offset 0xf8000): roots cannot be verified, as\n"
                          "      this copy carries no CHKP signature", 0xF8)
    assert _root_indices([["0x7", "type 3"]]) == {7} == _root_indices([{"RootIndex": "0x7"}])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N394 / N384 -- a copy whose READ fails (Q25, T1): said, with its cause, in every form; exit 2; no placeholder
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix (probe1, probe5): every forefst form and ra `files`, `chkp*`, `containers` exit 2 through an
# anonymous recorded skip; fd `summary`/`fastsummary`/`integrity`, ra `summary` say "[WARN] the checkpoint copy at LCN
# ... could not be read (offset ... is beyond the largest file offset ...)" and ra `supb --verify`'s roots row "this
# copy could not be read (...)" (exit 2); ra `supb`, `supb -v`, `supb -vv` exit 0 with placeholders.

_SAY_TODAY = ("fd-summary", "fd-fastsummary", "fd-integrity", "ra-summary", "ra-supb-verify")
_N394_WHY = ("Q25/T1: a checkpoint copy whose read fails is a view condition -- every command of both tools names "
             "it, says it could not be read with the cause, and exits 2; today an anonymous skip (or, in bare supb / "
             "supb -v / -vv, exit 0 and placeholders)")
_N384_WHY = ("Q25: refsanalysis chkp names a checkpoint copy whose read fails (its LCN, could not be read, the cause) "
             "and exits 2; today only an anonymous skip 'cmd_chkp skipped a checkpoint: ...'")


def _t1a_problems(out, lcn, form):
    """Critic: T1a / Q25 in the same run -- no placeholder field and no "no CHKP signature" claim for the copy that was
    not read, in every form and shape (slot 0, the host's refusal, the chkp forms). `supb --verify` is left out here:
    it shows both today beside its statement (a control of the statement / exit check); its two defects are the
    dedicated REDs `test_n394_supb_prints_no_placeholder...` and `test_n394_no_form_says...`."""
    if form == "ra-supb-verify":
        return []
    return [ln for ln in out.splitlines() if _PLACEHOLDER.search(ln)] + _no_sig_claims(out, lcn)


def _form_param(form, today_ok=_SAY_TODAY):
    # RED 1.13.2 N394 (`_N394_WHY`) / N384 (`_N384_WHY`, the chkp forms) on every form outside `today_ok`: the strict
    # xfail marks removed (fixed in step C2, area chkp_b)
    return pytest.param(form, id=form)


@pytest.mark.parametrize("form", [_form_param(f) for f in T1B])
def test_n394_a_copy_whose_read_fails_is_said_with_its_cause_in_every_form_and_exits_2(vol, form):
    plant_supb_ref(vol, 1, HUGE_LCN)
    rc, out = _run(vol, form)
    assert rc == 2 and _said(out, HUGE_LCN, _CAUSE_HUGE), (
        "%s: the checkpoint copy at LCN 0x%x could not be read (no file offset holds it): name it, say so with the "
        "cause, exit 2 (rc=%d)" % (form, HUGE_LCN, rc)) + _ctx(vol, rc, out)
    assert not _t1a_problems(out, HUGE_LCN, form), "%s: %r" % (form, _t1a_problems(out, HUGE_LCN, form)) \
        + _ctx(vol, rc, out)


_SLOT0 = ("fd-files", "ra-supb", "ra-chkp")


@pytest.mark.parametrize("form", [_form_param(f) for f in _SLOT0])
def test_n394_the_copy_in_slot_0_whose_read_fails_is_said_and_exits_2(vol, form):
    """The newer slot fails to read; the volume is read from the copy in slot 1 (vclock 63) -- whose clock may not be
    the newest, which only the unreadable copy could tell (T1's reason)."""
    plant_supb_ref(vol, 0, HUGE_LCN)
    rc, out = _run(vol, form)
    assert rc == 2 and _said(out, HUGE_LCN, _CAUSE_HUGE), "%s (rc=%d)" % (form, rc) + _ctx(vol, rc, out)
    assert not _t1a_problems(out, HUGE_LCN, form), "%s: %r" % (form, _t1a_problems(out, HUGE_LCN, form)) \
        + _ctx(vol, rc, out)


_HOST = ("fd-files", "fd-summary", "ra-supb", "ra-supb-v", "ra-supb-verify", "ra-chkp", "ra-containers")


@pytest.mark.parametrize("form", [_form_param(f) for f in _HOST])
def test_n394_a_copy_the_host_refuses_to_read_is_said_with_its_cause_and_exits_2(vol, form):
    """g2c3 K-6's shape: the reference at LCN 2**38 (all three superblock copies, C2 ST-S1 (c)), its offset refused
    by the modelled file system with EINVAL -- the cause Q25 calls "refused by the host"."""
    plant_supb_ref(vol, 1, HOST_LCN)
    rc, out = _run_host(vol, form)
    assert rc == 2 and _said(out, HOST_LCN, _CAUSE_HOST), "%s (rc=%d)" % (form, rc) + _ctx(vol, rc, out)
    assert not _t1a_problems(out, HOST_LCN, form), "%s: %r" % (form, _t1a_problems(out, HOST_LCN, form)) \
        + _ctx(vol, rc, out)


# RED 1.13.2 N394: Q25/T1a: no placeholder field for a checkpoint copy that could not be read; today supb prints
# 'vc=? ac=?' and supb -v / -vv 'sig=???? vc=? ac=? ver=?.?' (the strict xfail mark removed: fixed in step C2, area
# chkp_b)
@pytest.mark.parametrize("form", SUPB_FORMS)
def test_n394_supb_prints_no_placeholder_for_a_copy_whose_read_fails(vol, form):
    plant_supb_ref(vol, 1, HUGE_LCN)
    rc, out = _run(vol, form)
    bad = [ln for ln in out.splitlines() if _PLACEHOLDER.search(ln)]
    assert not bad, "%s prints placeholders for the copy it could not read: %r" % (form, bad) + _ctx(vol, rc, out)


# RED 1.13.2 N394 on [ra-supb-verify]: T1a: supb --verify's checksum row for a copy that could not be read says so;
# today 'no CHKP signature', a claim about bytes that were never read (the strict xfail mark removed: fixed in step C2,
# area chkp_b)
@pytest.mark.parametrize("form", [pytest.param("ra-supb-verify")] + list(ROW_FORMS))
def test_n394_no_form_says_a_copy_that_was_not_read_carries_no_signature(vol, form):
    plant_supb_ref(vol, 1, HUGE_LCN)
    rc, out = _run(vol, form)
    assert not _no_sig_claims(out, HUGE_LCN), "%s: %r" % (form, _no_sig_claims(out, HUGE_LCN)) + _ctx(vol, rc, out)


# --- the shared condition table (in process: the reference is passed to checkpoint_select directly) ---

def _conds(v, lcns, fh_wrap=None):
    sel = select(v, lcns, fh_wrap)
    return sel, F._checkpoint_conditions(sel, CS)


def _shape(v, shape):
    """(lcns, the planted copy's LCN, fh_wrap) of an in-process shape."""
    g = v.geo
    if shape == "huge-slot1":
        return [g.lo, HUGE_LCN], HUGE_LCN, None
    if shape == "huge-slot0":
        return [HUGE_LCN, g.hi], HUGE_LCN, None
    if shape == "host-slot1":
        return [g.lo, HOST_LCN], HOST_LCN, _RefusingFile
    raise RedFixtureError(shape)


# RED 1.13.2 N394: T1: _checkpoint_conditions files a copy whose read fails as a `view` condition (its clock is
# unknown), as it files a copy read without a signature (N374); today `redundancy` (the strict xfail mark removed:
# fixed in step C2, area chkp_b)
@pytest.mark.parametrize("shape", ["huge-slot1", "huge-slot0", "host-slot1"])
def test_n394_the_condition_table_files_a_copy_whose_read_fails_as_a_view_condition(vol, shape):
    lcns, lcn, wrap = _shape(vol, shape)
    sel, conds = _conds(vol, lcns, wrap)
    c = next(c for c in sel["copies"] if c["lcn"] == lcn)
    # critic: the shape is "nothing was read from the copy"; whether the record carries it as read_error is the fix's
    _fx((c["read_error"] is not None or not c["raw"]) and not c["sig_ok"] and sel["in_use"] is not None
        and sel["in_use"]["lcn"] != lcn, "%s: the read did not fail (%r)" % (shape, c))
    mine = [(k, lvl, t) for k, lvl, t in conds if _lcn_re(lcn).search(t)]
    _fx(mine, "%s: no condition names the copy: %r" % (shape, conds))
    assert all(lvl == "view" for _k, lvl, _t in mine), "%s: %r" % (shape, mine)


@pytest.mark.parametrize("shape", ["huge-slot1", "host-slot1"])
def test_n394_control_the_condition_text_names_the_copy_and_the_cause(vol, shape):
    lcns, lcn, wrap = _shape(vol, shape)
    _sel, conds = _conds(vol, lcns, wrap)
    cause = _CAUSE_HOST if shape.startswith("host") else _CAUSE_HUGE
    assert any(_UNREAD.search(t) and cause.search(t) for _k, _l, t in conds if _lcn_re(lcn).search(t)), conds


def test_n394_control_an_older_copy_that_fails_its_self_checksum_stays_a_redundancy_condition(vol):
    """V-a (decisions 20.3, 21): the over-broad fix -- every condition of a copy not in use made `view` -- is excluded."""
    AB.damage_chkp(vol, vol.geo.hi)
    sel, conds = _conds(vol, None)
    _fx(sel["in_use"]["lcn"] == vol.geo.lo, "the copy in use moved")
    mine = [(k, lvl) for k, lvl, t in conds if _lcn_re(vol.geo.hi).search(t)]
    assert mine and all(lvl == "redundancy" for _k, lvl in mine), mine


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N384 -- a copy past the image end (Q25: said with that cause)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix (probe2, probe5): every T1b form exits 2 and prints "the checkpoint copy at LCN 0xf8 (offset
# 0xf8000) is unreadable: nothing could be read there. It has no clock ..." (N374's view condition) -- the cause
# (the image ends before the copy) is not said; fd summary/fastsummary/integrity rows "unreadable: no CHKP signature",
# supb --verify "chkp_2_roots WARN ... this copy carries no CHKP signature"; the JSON `Unreadable` the same text.

# RED 1.13.2 N384: Q25: a checkpoint copy past the image end is said with that cause in every form; today 'nothing
# could be read there' (the strict xfail mark removed: fixed in step C2, area chkp_b)
@pytest.mark.parametrize("form", list(T1B))
def test_n384_a_copy_past_the_image_end_is_said_with_that_cause(vol, form):
    lcn = plant_past_end(vol)
    rc, out = _run(vol, form)
    _keep(rc == 2 and _said(out, lcn, re.compile(".")), "N374: the copy is said unreadable and every form exits 2 "
          "(%s, rc=%d)" % (form, rc) + _ctx(vol, rc, out))
    assert _said(out, lcn, _PAST_END), "%s: say that the copy at LCN 0x%x lies past the image end" % (form, lcn) \
        + _ctx(vol, rc, out)


def test_n384_control_a_copy_past_the_image_end_exits_2_and_is_said_unreadable_in_every_form(vol):
    lcn = plant_past_end(vol)
    for form in T1B:
        rc, out = _run(vol, form)
        assert rc == 2 and _said(out, lcn, re.compile(".")), "%s (rc=%d)" % (form, rc) + _ctx(vol, rc, out)


# RED 1.13.2 N384: a copy past the image end is not said to carry no CHKP signature (nothing was read): today the
# copy rows say 'unreadable: no CHKP signature' and supb --verify's roots row 'this copy carries no CHKP signature'
# (the strict xfail mark removed: fixed in step C2, area chkp_b)
@pytest.mark.parametrize("form", list(ROW_FORMS) + ["ra-supb-verify"])
def test_n384_no_form_says_a_copy_past_the_image_end_carries_no_signature(vol, form):
    lcn = plant_past_end(vol)
    rc, out = _run(vol, form)
    assert not _no_sig_claims(out, lcn), "%s: %r" % (form, _no_sig_claims(out, lcn)) + _ctx(vol, rc, out)


# RED 1.13.2 N384: the per-copy JSON `Unreadable` says the copy lies past the image end (Q25: said with its cause);
# today 'nothing could be read there' (the strict xfail mark removed: fixed in step C2, area chkp_b)
@pytest.mark.parametrize("form", list(JSON_FORMS))
def test_n384_the_json_record_of_a_copy_past_the_image_end_names_the_cause(vol, form):
    lcn = plant_past_end(vol)
    rc, rec, out, err = _json_run(vol, form)
    _fx(lcn in rec, "no record for 0x%x" % lcn + _jctx(rec, rc, out, err))
    # critic: `Unreadable` (N374's key) or any other string of the copy's own record -- the plan fixes the cause, not
    # the key that carries it
    texts = [x for x in rec[lcn].values() if isinstance(x, str)]
    assert any(_PAST_END.search(t) for t in texts), "Unreadable = %r; strings %r" % (rec[lcn].get("Unreadable"), texts) \
        + _jctx(rec, rc, out, err)


# RED 1.13.2 N384: the shared condition text of a copy past the image end names the image end; today 'nothing could
# be read there' (the strict xfail mark removed: fixed in step C2, area chkp_b)
def test_n384_the_condition_text_of_a_copy_past_the_image_end_names_the_image_end(vol):
    lcn = (os.path.getsize(vol.path) - vol.geo.ps) // CS + 0x100           # RUNNING_LOG N384: image clusters + 0x100
    sel, conds = _conds(vol, [vol.geo.lo, lcn])
    # critic: a fix may record the image end as the copy's read error -- the shape is only "nothing was read"
    _fx(not sel["copies"][1]["raw"] and not sel["copies"][1]["sig_ok"], "the copy was read")
    mine = [t for _k, _l, t in conds if _lcn_re(lcn).search(t)]
    _fx(mine, "no condition names the copy")
    assert any(_PAST_END.search(t) for t in mine), mine


def test_n384_control_a_copy_past_the_image_end_is_a_view_condition(vol):
    lcn = (os.path.getsize(vol.path) - vol.geo.ps) // CS + 0x100
    _sel, conds = _conds(vol, [vol.geo.lo, lcn])
    mine = [lvl for _k, lvl, t in conds if _lcn_re(lcn).search(t)]
    assert mine and all(lvl == "view" for lvl in mine), conds


@pytest.mark.parametrize("form", ["fd-files", "ra-files"])
def test_n394_control_the_volume_is_still_read_from_the_other_copy(vol, form):
    """Critic: a view condition is said and the volume is still read (decision 26; never exit 1, never an empty view):
    every stdout line of the undamaged volume's listing is in the listing with the copy in slot 1 unreadable (measured
    before the fix: equal on both volumes). Excludes an over-broad fix that stops after the condition."""
    tool, args = T1B[form]
    rc0, out0, _err0 = G2C._run_split(tool, vol.path, *args, cwd=os.path.dirname(vol.path), cli=vol.geo.cli)
    _fx(rc0 == 0 and out0.strip(), "%s on the undamaged volume: rc=%d, %d bytes" % (form, rc0, len(out0)))
    plant_supb_ref(vol, 1, HUGE_LCN)
    rc, out, err = G2C._run_split(tool, vol.path, *args, cwd=os.path.dirname(vol.path), cli=vol.geo.cli)
    have = set(out.splitlines())
    lost = [ln for ln in out0.splitlines() if ln.strip() and ln not in have]
    assert rc != 1 and not lost, "%s: rc=%d, %d listing lines lost: %r" % (form, rc, len(lost), lost[:5]) \
        + _ctx(vol, rc, out + "\n" + err)


def test_control_the_undamaged_volume_says_no_copy_is_unreadable_and_prints_no_placeholder(vol):
    g = vol.geo
    for form in T1B:
        rc, out = _run(vol, form)
        assert not [s for s in _statements(out) if (_lcn_re(g.lo).search(s) or _lcn_re(g.hi).search(s))
                    and _UNREAD.search(s)], form + _ctx(vol, rc, out)
        assert not _PLACEHOLDER.search(out) and not _no_sig_claims(out, g.lo) and not _no_sig_claims(out, g.hi), \
            form + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N376 -- the per-copy JSON record (Q26): RootUnchecked, roots_ok, use
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix (probe3): no record carries `RootUnchecked` (nor `root_unchecked`); `roots_ok` is "a root
# list is present" -- true beside `root_fail: [[7, 'does not match ...']]` and beside a root 7 that cannot be verified;
# the older copy without a root list has `use: null` (vclock 63, the copy in use 64).

_JF = list(JSON_FORMS)
_COPIES = {"lo": "in use", "hi": "not in use"}


def _copy(v, which):
    return v.geo.lo if which == "lo" else v.geo.hi


# RED 1.13.2 N376: Q26: `RootUnchecked` (a list, always present, [] when every root was checked) is on every per-
# copy record of summary / fastsummary / integrity --json; today absent (the strict xfail mark removed: fixed in
# step C2, area chkp_b)
@pytest.mark.parametrize("form", _JF)
def test_n376_root_unchecked_is_on_every_copy_record_and_empty_on_the_undamaged_volume(vol, form):
    rc, rec, out, err = _json_run(vol, form)
    _fx(set(rec) == {vol.geo.lo, vol.geo.hi}, "records %r" % sorted(rec))
    assert all(isinstance(r.get("RootUnchecked"), list) and r["RootUnchecked"] == [] for r in rec.values()), \
        _jctx(rec, rc, out, err)


# RED 1.13.2 N376: Q26: `RootUnchecked` lists root 7 when root 7's reference declares a checksum type this tool does
# not compute for a root page (N362), and is [] on the other copy; today absent (the strict xfail mark removed:
# fixed in step C2, area chkp_b)
@pytest.mark.parametrize("which", sorted(_COPIES))
@pytest.mark.parametrize("form", _JF)
def test_n376_root_unchecked_lists_the_root_that_cannot_be_verified(vol, form, which):
    lcn = _copy(vol, which)
    G2C2.plant_root_unchecked(vol, lcn, 7, "type")
    rc, rec, out, err = _json_run(vol, form)
    other = vol.geo.hi if lcn == vol.geo.lo else vol.geo.lo
    _fx(set(rec) == {lcn, other}, "records %r" % sorted(rec))
    got = {k: r.get("RootUnchecked") for k, r in rec.items()}
    assert isinstance(got[lcn], list) and _root_indices(got[lcn]) == {7} and got[other] == [], \
        "RootUnchecked %r" % got + _jctx(rec, rc, out, err)


# RED 1.13.2 N376: Q26: `RootUnchecked` names the roots that could not be checked (checkpoint_select's
# root_unchecked), so a root that was checked and failed is in `root_fail` only and `RootUnchecked` stays []
# (critic: the two keys never name one root twice); today the key is absent (the strict xfail mark removed: fixed in
# step C2, area chkp_b)
@pytest.mark.parametrize("form", _JF)
def test_n376_root_unchecked_does_not_list_a_root_that_was_checked_and_failed(vol, form):
    G2C.plant_root_failure_on(vol, vol.geo.hi, 7)
    rc, rec, out, err = _json_run(vol, form)
    _keep(_root_indices(_f(rec[vol.geo.hi], "root_fail") or []) == {7}, "root_fail of the planted copy"
          + _jctx(rec, rc, out, err))
    got = {k: r.get("RootUnchecked") for k, r in rec.items()}
    assert got == {vol.geo.lo: [], vol.geo.hi: []}, "RootUnchecked %r" % got + _jctx(rec, rc, out, err)


_ROOTS_PLANTS = {"rootfail": lambda v, lcn: G2C.plant_root_failure_on(v, lcn, 7),
                 "unchecked": lambda v, lcn: G2C2.plant_root_unchecked(v, lcn, 7, "type")}


# RED 1.13.2 N376: Q26: `roots_ok` is true only when every root 0xC, 7, 8 was checked and passed; today it means 'a
# root list is present' and is true beside a root 7 that does not verify or cannot be verified (the strict xfail
# mark removed: fixed in step C2, area chkp_b)
@pytest.mark.parametrize("shape", sorted(_ROOTS_PLANTS))
@pytest.mark.parametrize("which", sorted(_COPIES))
@pytest.mark.parametrize("form", _JF)
def test_n376_roots_ok_is_false_for_a_copy_whose_root_did_not_pass(vol, form, which, shape):
    lcn = _copy(vol, which)
    _ROOTS_PLANTS[shape](vol, lcn)
    rc, rec, out, err = _json_run(vol, form)
    other = vol.geo.hi if lcn == vol.geo.lo else vol.geo.lo
    _keep(_f(rec[other], "roots_ok") is True, "the other copy's roots_ok" + _jctx(rec, rc, out, err))
    assert _f(rec[lcn], "roots_ok") is False, "roots_ok of 0x%x = %r" % (lcn, _f(rec[lcn], "roots_ok")) \
        + _jctx(rec, rc, out, err)


_ROOTS_OK_CONTROLS = {"undamaged": (lambda v: None, lambda v: {v.geo.lo: True, v.geo.hi: True}),
                      "rootless-older": (lambda v: G2C.plant_no_root_list(v, v.geo.hi),
                                         lambda v: {v.geo.lo: True, v.geo.hi: False}),
                      "past-end": (plant_past_end, lambda v: {v.geo.lo: True, PASTEND[v.geo.kind][0]: False})}


@pytest.mark.parametrize("shape", sorted(_ROOTS_OK_CONTROLS))
@pytest.mark.parametrize("form", _JF)
def test_n376_control_roots_ok_where_it_is_right_today(vol, form, shape):
    plant, want = _ROOTS_OK_CONTROLS[shape]
    plant(vol)
    rc, rec, out, err = _json_run(vol, form)
    assert {k: _f(r, "roots_ok") for k, r in rec.items()} == want(vol), _jctx(rec, rc, out, err)


# RED 1.13.2 N376: Q26 (decision 25.4 / K18): `use` on every copy with a clock -- the older copy without a root list
# (vclock 63, the copy in use 64) is 'superseded'; today null (the strict xfail mark removed: fixed in step C2, area
# chkp_b)
@pytest.mark.parametrize("form", _JF)
def test_n376_use_is_superseded_on_the_older_copy_without_a_root_list(vol, form):
    G2C.plant_no_root_list(vol, vol.geo.hi)
    rc, rec, out, err = _json_run(vol, form)
    _keep(_f(rec[vol.geo.lo], "use") == "in use", "the copy in use" + _jctx(rec, rc, out, err))
    assert _f(rec[vol.geo.hi], "use") == "superseded", "use = %r" % _f(rec[vol.geo.hi], "use") \
        + _jctx(rec, rc, out, err)


@pytest.mark.parametrize("form", _JF)
def test_n376_control_use_words_on_the_undamaged_volume(vol, form):
    rc, rec, out, err = _json_run(vol, form)
    assert {k: _f(r, "use") for k, r in rec.items()} == {vol.geo.lo: "in use", vol.geo.hi: "superseded"}, \
        _jctx(rec, rc, out, err)


# RED 1.13.2 N376: Q26: `RootUnchecked` is present (a list) on the record of a copy that could not be read too;
# today absent (the strict xfail mark removed: fixed in step C2, area chkp_b)
@pytest.mark.parametrize("form", _JF)
def test_n376_root_unchecked_is_on_the_record_of_a_copy_past_the_image_end(vol, form):
    lcn = plant_past_end(vol)
    rc, rec, out, err = _json_run(vol, form)
    _fx(lcn in rec, "no record for 0x%x" % lcn)
    assert all(isinstance(r.get("RootUnchecked"), list) for r in rec.values()), _jctx(rec, rc, out, err)


_RECORD_SHAPES = {"read-error": lambda v: plant_supb_ref(v, 1, HUGE_LCN),
                  "rootless-older": lambda v: G2C.plant_no_root_list(v, v.geo.hi) or v.geo.hi}


# RED 1.13.2 N376: Q26: `RootUnchecked` is present (a list) on every per-copy record -- also on the record of a copy
# whose read fails and of a signed copy without a root list (critic: the record's other branches); today absent (the
# strict xfail mark removed: fixed in step C2, area chkp_b)
@pytest.mark.parametrize("shape", sorted(_RECORD_SHAPES))
@pytest.mark.parametrize("form", _JF)
def test_n376_root_unchecked_is_on_the_record_of_a_copy_not_read_or_without_a_root_list(vol, form, shape):
    lcn = _RECORD_SHAPES[shape](vol)
    rc, rec, out, err = _json_run(vol, form)
    _fx(lcn in rec, "no record for 0x%x" % lcn + _jctx(rec, rc, out, err))
    assert all(isinstance(r.get("RootUnchecked"), list) for r in rec.values()), _jctx(rec, rc, out, err)


@pytest.mark.parametrize("shape", sorted(_ROOTS_PLANTS))
@pytest.mark.parametrize("form", list(ROW_FORMS))
def test_n376_control_a_copy_whose_root_list_was_read_is_not_called_roots_unreadable(vol, form, shape):
    """`_chkp_line` (summary, fastsummary) and integrity's copy rows print '(roots unreadable)' when `roots_ok` is
    false: correcting `roots_ok` in place must not make them say it of a copy whose root list was read."""
    _ROOTS_PLANTS[shape](vol, vol.geo.hi)
    rc, out = _run(vol, form)
    bad = [ln for ln in out.splitlines() if _lcn_re(vol.geo.hi).search(ln) and _ROOTS_UNREADABLE.search(ln)]
    assert not bad, "%s: %r" % (form, bad) + _ctx(vol, rc, out)
