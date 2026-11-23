"""1.13.2 RED cases for fix group G2c2 (group 2's second close-out): N361, N362, N363, N364.

Context: `analysis/reports/v1.13.2/fixes/G2c2_CONTEXT.md` (PLAN_1.13.2 decisions 20-29, `G2_CONTEXT.md` and
`G2c_CONTEXT.md` bind), RUNNING_LOG rows N361-N364; sources `fixes/REVIEW_G2c_correctness.md` section 6 (R1, R5, R6,
R7), `fixes/REVIEW_G2c_tests.md` section 6 (T1, T2, T4), `fixes/GOLDEN_G2c_critic.md` (C-1, C-2),
`fixes/GOLDEN_G2c_challenge.md` (B1). Report, with every node's observed failure before the fix:
`analysis/reports/v1.13.2/fixes/FIX_G2c2.md`.

What each RED asserts
---------------------
 1 N361 (a)  refsanalysis `supb --verify` has a roots row for EVERY checkpoint copy (its help: "one row each"),
             including a copy whose root list cannot be read and a copy without a CHKP signature; such a row does not
             read OK, and the command exits 2 (any row that does not pass).
 2 N361 (b)  a checkpoint copy whose +0x60 is higher than the copy in use's but whose root list cannot be read (it
             passes its self-checksum, fails it, or cannot be verified) makes the view STALE: every command of both
             tools exits 2 and says so, worded as the stale view is ("this view is read from the copy at LCN x
             (vclock v): changes committed after vclock v are not in it"), naming why the newer copy is not used (its
             root list could not be read), and claiming nothing about the driver (what the driver does with a copy
             without a root list is not traced). Controls: a newer copy that fails its self-checksum (already a stale
             view); the copy without a root list is the OLDER one (a redundancy condition: V-a).
   N361 (c)  (the lead's placement of the fixer's open item, 2026-10-08) decision 28 on a copy without a root list: a
             +0x10/+0x60 divergence on a checkpoint copy whose root list cannot be read -- older or newer than the copy
             in use -- is said with decision 28's shared text and exits 2 in every command of both tools, as on any
             other copy (control: the same divergence on a copy with a root list, already so).
 3 N362      a root 0xC, 7 or 8 that cannot be checked (no reference, or a checksum type this tool does not compute) is
             said by the shared checkpoint conditions, worded "cannot be verified" and never "failed": on the copy in
             use a `view` condition (every command exits 2); on the copy not in use a `redundancy` condition (forefst
             `summary`, `fastsummary`, `integrity`, refsanalysis `summary` and `supb --verify` say it and exit 2; the
             commands that only read through the copy in use keep their exit code: control). The N205 text of a copy
             in use whose root fails does not say that the other copy passes the 26100 first pass when one of that
             copy's roots could not be checked.
 4 N363      `verify-bundle` says what it counted -- the findings recorded while reading the bundle's bootstrap
             structures -- and never "the volume it carries has N finding(s)" / "has no finding" (its report line, its
             help and its -h text); its exit code is unchanged.
 5 N364      (R5) both `single_source.tsv` copies have rows for `container_size_zero_text` and `_metadata_incomplete`;
             (R6) `supb --verify` and `chkp --verify` word the roots check of one copy the same way (match, does not
             match, cannot be verified); (T4) `boot --verify` on a zero container size does not pad its table to the
             width of the shared text (the finding is printed below the table); (B1) refsanalysis `supb`'s fallback
             NOTE says again that the backup copy shown passes its self-checksum. R7 (a code comment) has no oracle
             and no RED.

Volumes and discipline: as test_1132_red_g2c.py -- the a_bootstrap `vol` fixture (``[synthetic]`` / ``[image]``,
imported by name), ``@_red`` = ``xfail(strict=True, raises=AssertionError)``, only a plain ``assert`` states the defect,
``_fx`` for a fixture that is not what the case needs, ``_keep`` for a property the current tool already has, every RED
has a control that passes now, and every oracle is checked first on the undamaged volume. The marks were removed when
the fix landed (FIX_G2c2.md): the unmarked file fails against the step's pre-fix tools (`fixes/prefix_G2c2/`) at the
REDs' plain asserts and passes on the fixed tree. The plants are the
reviewers' and the critic's probes (`probe_n353b-d.py`, `probe_crit.py`), rebuilt with the RED files' own helpers.
N364 R5 reads the harness from $G2C_VERIFICATION_DIR (default: <repo>/../analysis/verification), skipped when absent.
"""
import os
import re
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402

import test_1132_red_a_bootstrap as _AB                   # noqa: E402
from test_1132_red_a_bootstrap import (                  # noqa: E402
    RedFixtureError, _fx, _keep, _ctx, damage_supb, damage_chkp, _FAIL, _lcn_re, FOREFST, REFSANALYSIS, CS,
    CHKP_DESC, CLOCK_OLD, CLOCK_NEW)
from test_1132_red_group2 import (                       # noqa: E402
    IMAGE_ONLY, _statements, _n205_said, _root_named, _root_ref_offset, plant_root_failure, _UNVERIFIED)
from test_1132_red_group2b import plant_unknown_type      # noqa: E402
from test_1132_red_g2c import (                          # noqa: E402
    plant_no_root_list, plant_root_failure_on, plant_container_zero, _n343_said, _n354_said, _export_bundle,
    _verify_bundle, _run_split, _verification_dir, _D28, _N343_QUIET, _N343_LIST, _N343_SAY, _DIVERGE_HI)

vol = _AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 1. N361 (a) -- `supb --verify` has a roots row for EVERY checkpoint copy
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix (reviewer 1 R1 / reviewer 2 T1, re-measured here): `_copy_rows` skips a copy without a root
# list ("no root list: its checksum row above says what it is", ra:1157-1158) -- but that row reads OK for a copy that
# verifies, so the copy appears in the table only as "checksum OK", and `supb --verify` exits 0 for an older copy
# without a root list. A copy without a CHKP signature has no roots row either.

_ROOTS_ROW = re.compile(r"^chkp_(\d+)_roots\s+(\S+)\s+(.*?)\s*$")


def _roots_rows(out):
    """`supb --verify`'s roots rows: {slot: (result, details)}. Wave E step E1c (N377): the details column wraps; a row
    is read with its continuation lines (`conftest.unwrap_table_rows`) -- the acceptance is unchanged."""
    from conftest import unwrap_table_rows
    rows = {}
    for ln in unwrap_table_rows(out).splitlines():
        m = _ROOTS_ROW.match(ln)
        if m:
            _fx(int(m.group(1)) not in rows, "two roots rows for slot %s" % m.group(1))
            rows[int(m.group(1))] = (m.group(2), m.group(3))
    return rows


def _n361a_plant(v, shape):
    """Returns the slot (1 = lo, 2 = hi) of the copy the plant damages."""
    g = v.geo
    if shape == "rootless-newer":
        plant_no_root_list(v, g.lo)
        return 1
    if shape == "rootless-older":
        plant_no_root_list(v, g.hi)
        return 2
    if shape == "no-signature":
        v.zero(v.at(g.hi), CS)
        _fx(v.block(g.hi)[:4] != b"CHKP", "the copy at 0x%x still carries a CHKP signature" % g.hi)
        return 2
    raise RedFixtureError(shape)


@pytest.mark.parametrize("shape", ["rootless-newer", "rootless-older", "no-signature"])
def test_n361a_supb_verify_has_a_roots_row_for_every_checkpoint_copy(vol, shape):
    rc0, out0 = vol.run(REFSANALYSIS, "supb", "--verify")
    _fx(rc0 == 0 and {s: r for s, (r, _d) in _roots_rows(out0).items()} == {1: "OK", 2: "OK"},
        "the undamaged volume has two OK roots rows" + _ctx(vol, rc0, out0))
    slot = _n361a_plant(vol, shape)
    rc, out = vol.run(REFSANALYSIS, "supb", "--verify")
    rows = _roots_rows(out)
    assert sorted(rows) == [1, 2], "one roots row per checkpoint copy (help: 'one row each'): %r" % rows \
        + _ctx(vol, rc, out)
    res, det = rows[slot]
    assert res != "OK", "the roots row of the damaged copy reads OK: %r" % (rows[slot],) + _ctx(vol, rc, out)
    if shape.startswith("rootless"):
        assert re.search(r"(?i)\broot list\b", det), "the row must say the copy's root list could not be read: %r" \
            % det + _ctx(vol, rc, out)
    assert rc == 2, "a row that does not pass exits 2 (rc=%d)" % rc + _ctx(vol, rc, out)


def test_n361a_control_every_copy_with_a_root_list_has_its_row(vol):
    """Since G2c: a roots row per copy that HAS a root list; a root failure of the copy not in use is a FAIL row."""
    rc, out = vol.run(REFSANALYSIS, "supb", "--verify")
    assert rc == 0 and {s: r for s, (r, _d) in _roots_rows(out).items()} == {1: "OK", 2: "OK"}, _ctx(vol, rc, out)
    plant_root_failure_on(vol, vol.geo.hi, 7)
    rc, out = vol.run(REFSANALYSIS, "supb", "--verify")
    rows = _roots_rows(out)
    assert rc == 2 and rows[1][0] == "OK" and rows[2][0] == "FAIL" and _root_named(rows[2][1], 7), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 2. N361 (b) -- a newer checkpoint copy whose root list cannot be read: a stale view
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Plant (reviewer 1's probe_n353b): the newest copy (lo, +0x60 = 64) gets root count (+0x90) 0 and is re-sealed: it
# passes its self-checksum but has no root list, so `checkpoint_select(require_roots=True)` takes it as no candidate and
# every volume reader uses the older copy (hi, vclock 63). Measured before the fix: forefst `files` and refsanalysis
# `supb`, `chkp`, `chkp --verify` ("Result: 20/20 checks passed"), `containers` exit 0 and say nothing about the newer
# copy; only `summary`, `fastsummary`, `integrity` and refsanalysis `summary` name it, as a redundancy condition ("its
# root list could not be read"), not as the stale view it is (A1/K035; decision 28's reason: the copy is chosen by
# +0x60). Variants: the newer copy also FAILS its self-checksum, or its checksum cannot be verified -- it is not used
# either way, so the view is stale either way.

def _n361b_plant(v, variant):
    g = v.geo
    plant_no_root_list(v, g.lo)
    if variant == "failed":
        v.flip(v.at(g.lo, 0x400))
        _fx(v.verifies(g.lo) is False, "the newer copy still verifies after the flip")
    elif variant == "unverifiable":
        plant_unknown_type(v, g.lo, 0x58, 0x03)
        _fx(v.verifies(g.lo) is None, "the newer copy's checksum is still verifiable")
    else:
        _fx(v.verifies(g.lo) is True, "the newer copy does not verify")
    _fx(v.clocks(g.lo) == (CLOCK_NEW, CLOCK_NEW) and v.clocks(g.hi) == (CLOCK_OLD, CLOCK_OLD), "clocks moved")
    with open(v.path, "rb") as fh:
        sel = F.checkpoint_select(fh, g.ps, CS, F.parse_supb(fh, g.ps, CS), require_roots=True)
    _fx(sel["in_use"] is not None and sel["in_use"]["lcn"] == g.hi, "the volume is not read from the older copy")


def _n361_said(out, v):
    """The stale-view statement: it names the newer copy (LCN, vclock 64) and why it is not used (its root list),
    and says the view is read from the older copy and what is missing from it -- the stale view's own words."""
    g = v.geo
    return [s for s in _statements(out)
            if _lcn_re(g.lo).search(s) and re.search(r"\bvclock %d\b" % CLOCK_NEW, s)
            and re.search(r"(?i)\broot list\b", s)
            and re.search(r"(?i)\bthis view is read from the copy at LCN 0x0*%x \(vclock %d\)" % (g.hi, CLOCK_OLD), s)
            and re.search(r"(?i)\bchanges committed after vclock %d are not in it\b" % CLOCK_OLD, s)]


_N361B_SUBSET = ("fd-files", "fd-summary", "ra-chkp", "ra-supb")
_N361B = [("verifies", c) for c in sorted(_D28)] + [(var, c) for var in ("failed", "unverifiable")
                                                    for c in _N361B_SUBSET]


@pytest.mark.parametrize("variant,cmd", _N361B, ids=["%s-%s" % p for p in _N361B])
def test_n361b_a_newer_copy_whose_root_list_cannot_be_read_makes_the_view_stale(vol, variant, cmd):
    tool, args = _D28[cmd]
    rc0, out0 = vol.run(tool, *args)
    _fx(not _n361_said(out0, vol), "%s on the undamaged volume" % cmd + _ctx(vol, rc0, out0))
    _n361b_plant(vol, variant)
    rc, out = vol.run(tool, *args)
    said = _n361_said(out, vol)
    assert said, ("%s must say that the newer checkpoint copy (LCN 0x%x, vclock %d) is not used because its root list "
                  "cannot be read, so the view read from LCN 0x%x (vclock %d) is stale"
                  % (cmd, vol.geo.lo, CLOCK_NEW, vol.geo.hi, CLOCK_OLD)) + _ctx(vol, rc, out)
    assert not [s for s in said if re.search(r"(?i)\bdriver\b", s)], \
        "a claim about the driver (not traced for a copy without a root list): %r" % said
    if variant == "failed":
        assert [s for s in said if _FAIL.search(s)], "the newer copy also failed its self-checksum: %r" % said
    if variant == "unverifiable":
        assert [s for s in said if _UNVERIFIED.search(s)], "the newer copy's checksum cannot be verified: %r" % said
    assert rc == 2, "%s must exit 2: the view is stale (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", sorted(_D28))
def test_n361b_control_a_newer_copy_that_fails_its_self_checksum_is_a_stale_view(vol, cmd):
    """A1/K035: the newer copy fails its self-checksum (its root list intact) -- every command exits 2 and names it."""
    tool, args = _D28[cmd]
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(tool, *args)
    named = [s for s in _statements(out) if _lcn_re(vol.geo.lo).search(s)
             and (_FAIL.search(s) or "not in it" in s)]
    assert rc == 2 and named, "%s (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", sorted(list(_N343_QUIET) + list(_N343_LIST)))
def test_n361b_control_an_older_copy_without_a_root_list_is_a_redundancy_condition(vol, cmd):
    """V-a (decision 20.3): the copy without a root list is the OLDER one (not in use, not newer). The commands that
    only read through the copy in use keep their exit code and say nothing about it; `summary`, `fastsummary`,
    `integrity` and refsanalysis `summary` list it and exit 2."""
    tool, args = dict(_N343_QUIET, **_N343_SAY)[cmd]
    rc0, _out0 = vol.run(tool, *args)
    plant_no_root_list(vol, vol.geo.hi)
    rc, out = vol.run(tool, *args)
    named = [s for s in _statements(out) if _lcn_re(vol.geo.hi).search(s) and re.search(r"(?i)\broot list\b", s)]
    if cmd in _N343_QUIET:
        assert rc == rc0 and not named, "%s: %d -> %d" % (cmd, rc0, rc) + _ctx(vol, rc, out)
    else:
        assert rc == 2 and named and not [x for x in named if "not in it" in x], cmd + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 2c. N361 (c) -- decision 28 on a copy without a root list (the lead's placement, 2026-10-08)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `_checkpoint_conditions` stops at a copy whose root list cannot be read ("its root list could not be read",
# `continue`) before its clock test, so a +0x10/+0x60 divergence on such a copy was not said. Measured before this
# addition (the fixer's probe `rootless_hi_diverge`): the older copy without a root list and +0x10 = 58, +0x60 = 63 --
# forefst `files` and refsanalysis `chkp` exit 0 and are silent; `summary` exits 2 with "its root list could not be
# read" only. Decision 28: a divergence on EITHER copy exits 2 in every command of both tools (the copy is chosen by
# +0x60, so a divergence puts the choice itself in doubt). Shapes: the copy without a root list is the older one (not
# in use) or the newer one (then also N361 (b)'s stale view). Control: the same divergence on a copy WITH a root list.

def plant_clock_divergence(v, lcn, roots=True):
    """The copy at `lcn` gets +0x10 = 58 while +0x60 keeps its clock (re-sealed); with roots=False its root count is
    set to 0 first (N361's plant). Checked: the clocks, both copies verify, and the root list as asked."""
    g = v.geo
    clk = CLOCK_NEW if lcn == g.lo else CLOCK_OLD
    if not roots:
        plant_no_root_list(v, lcn)

    def edit(b):
        struct.pack_into("<Q", b, 0x10, _DIVERGE_HI)
    v.reseal(lcn, edit, CHKP_DESC)
    _fx(v.clocks(lcn) == (_DIVERGE_HI, clk), "the clocks of 0x%x are %r" % (lcn, v.clocks(lcn)))
    _fx(v.verifies(g.lo) is True and v.verifies(g.hi) is True, "a copy fails its self-checksum after the plant")
    with open(v.path, "rb") as fh:
        rl = F.parse_chkp(fh, g.ps, CS, lcn)[2]
    _fx(bool(rl) == roots, "the copy at 0x%x: root list %r" % (lcn, bool(rl)))
    return clk


def _clock_said(out, lcn, clk):
    """Decision 28's statement for the copy at `lcn`: its +0x10 (58) and its +0x60 (`clk`)."""
    return [s for s in _statements(out) if _lcn_re(lcn).search(s)
            and re.search(r"\+0x10\b[^;]{0,40}?\b%d\b" % _DIVERGE_HI, s)
            and re.search(r"\+0x60\b[^;]{0,40}?\b%d\b" % clk, s)]


_N361C_SHAPES = {"older": "hi", "newer": "lo"}


@pytest.mark.parametrize("shape", sorted(_N361C_SHAPES))
@pytest.mark.parametrize("cmd", sorted(_D28))
def test_n361c_a_clock_divergence_on_a_copy_without_a_root_list_exits_2_everywhere(vol, cmd, shape):
    tool, args = _D28[cmd]
    lcn = getattr(vol.geo, _N361C_SHAPES[shape])
    rc0, out0 = vol.run(tool, *args)
    _fx(not [s for s in _statements(out0) if re.search(r"\+0x10\b[^;]{0,40}?\b%d\b" % _DIVERGE_HI, s)],
        "%s on the undamaged volume" % cmd + _ctx(vol, rc0, out0))
    clk = plant_clock_divergence(vol, lcn, roots=False)
    rc, out = vol.run(tool, *args)
    assert _clock_said(out, lcn, clk), ("%s must say the +0x10/+0x60 divergence of the %s checkpoint copy (LCN 0x%x, "
                                        "+0x10 = %d, +0x60 = %d), whose root list cannot be read"
                                        % (cmd, shape, lcn, _DIVERGE_HI, clk)) + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (decision 28: a divergence on either copy; rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("shape", sorted(_N361C_SHAPES))
@pytest.mark.parametrize("cmd", sorted(_D28))
def test_n361c_control_the_divergence_on_a_copy_with_a_root_list_exits_2_everywhere(vol, cmd, shape):
    """Decision 28 as it stands: the same divergence on a copy WITH a root list -- the older copy (G2c's control) or
    the newer copy in use -- is said with the shared text and exits 2 in every command."""
    tool, args = _D28[cmd]
    lcn = getattr(vol.geo, _N361C_SHAPES[shape])
    clk = plant_clock_divergence(vol, lcn, roots=True)
    rc, out = vol.run(tool, *args)
    assert rc == 2 and _clock_said(out, lcn, clk), "%s (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 3. N362 -- a root 0xC/7/8 that cannot be checked: "cannot be verified", by the shared conditions
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Plants (the critic's `unchk_lo` / `unchk_hi`, probe_crit.py): root 7's page reference declares checksum type 3 (not
# CRC64 or SHA-256), the copy re-sealed; and a second shape: root 0xC has no reference (its entry in the copy's root
# offset table is 0), re-sealed. `_chkp_root_failures` lists such a root in `root_unchecked`. Measured before the fix:
# only refsanalysis `supb --verify` (a WARN roots row, "cannot be checked"; exit 2 on either copy) and `chkp --verify`
# (on the copy in use) say it; forefst `summary`/`integrity`, refsanalysis `summary`, `files` ... exit 0 and are silent
# (`_checkpoint_conditions` never reads `root_unchecked`). Decision 27.3's rule, applied to roots: the copy in use ->
# `view` (every command exits 2); a copy not in use -> `redundancy` (V-a).

_CANNOT_VERIFY = re.compile(r"(?i)\bcannot be verified\b")


def plant_root_unchecked(v, lcn, idx, how, other_clean=True):
    """how='type': root `idx`'s page reference in the copy at `lcn` declares checksum type 3; how='noref': the copy's
    root offset table entry for `idx` is 0 (no reference). The copy is re-sealed (Vol.reseal). Checked: that copy lists
    exactly `idx` as unchecked and no root as failing, the copy in use is still lo, and (other_clean) the other copy
    verifies all three roots."""
    g = v.geo
    blk = v.block(lcn)
    olb = F.le32(blk, 0x94) if F.le32(blk, 0x78) & 0x200 else 0x94
    ro = _root_ref_offset(blk, idx)
    _fx(ro and blk[ro + 0x22] == 2 and F.le32(blk, ro + 0x24) == 8, "root %d of 0x%x is not a CRC64 reference"
        % (idx, lcn))

    def edit(b):
        if how == "type":
            b[ro + 0x22] = 3
        else:
            struct.pack_into("<I", b, olb + 4 * idx, 0)
    v.reseal(lcn, edit, CHKP_DESC)
    with open(v.path, "rb") as fh:
        sel = F.checkpoint_select(fh, g.ps, CS, F.parse_supb(fh, g.ps, CS), require_roots=True)
    by = {c["lcn"]: c for c in sel["copies"]}
    _fx(by[lcn]["root_unchecked"] == [idx] and not by[lcn]["root_fail"],
        "0x%x: unchecked %r, failing %r" % (lcn, by[lcn]["root_unchecked"], by[lcn]["root_fail"]))
    other = g.hi if lcn == g.lo else g.lo
    _fx(not other_clean or (not by[other]["root_unchecked"] and not by[other]["root_fail"]),
        "the other copy does not verify its roots")
    _fx(sel["in_use"]["lcn"] == g.lo, "the copy in use moved")


def _n362_said(out, lcn, idx):
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and _root_named(s, idx) and _CANNOT_VERIFY.search(s)]


def _n362_called_failed(out, lcn, idx):
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and _root_named(s, idx) and _FAIL.search(s)
            and not _UNVERIFIED.search(s)]


_N362_SHAPES = {"type7": ("type", 7), "noref0xC": ("noref", 0xC)}
_N362_IN_USE = [("type7", c) for c in sorted(_D28)] + [("noref0xC", c) for c in
                                                       ("fd-files", "fd-summary", "ra-supb-verify", "ra-chkp-verify")]
_N362_VA = {"fd-summary": (FOREFST, ("summary",)), "fd-fastsummary": (FOREFST, ("fastsummary",)),
            "fd-integrity": (FOREFST, ("integrity",)), "ra-summary": (REFSANALYSIS, ("summary",)),
            "ra-supb-verify": (REFSANALYSIS, ("supb", "--verify"))}


@pytest.mark.parametrize("shape,cmd", _N362_IN_USE, ids=["%s-%s" % p for p in _N362_IN_USE])
def test_n362_a_root_of_the_copy_in_use_that_cannot_be_checked_is_said_and_exits_2(vol, shape, cmd):
    how, idx = _N362_SHAPES[shape]
    tool, args = _D28[cmd]
    rc0, out0 = vol.run(tool, *args)
    _fx(not _n362_said(out0, vol.geo.lo, idx), "%s on the undamaged volume" % cmd + _ctx(vol, rc0, out0))
    if how == "noref":
        # C2 ST-C3 (C2_LEAD_SETTLEMENTS, third table): root 0xC at offset 0 fails refs.sys's V5 in every pass (N373),
        # so a copy carrying it alone is not the copy in use once N373 lands. The plant goes into BOTH copies: no copy
        # is then valid, the newest (lo) is read anyway (closure B-4.2 row 10), and N362's purpose and rc 2 hold.
        plant_root_unchecked(vol, vol.geo.hi, idx, how)
        plant_root_unchecked(vol, vol.geo.lo, idx, how, other_clean=False)
    else:
        plant_root_unchecked(vol, vol.geo.lo, idx, how)
    rc, out = vol.run(tool, *args)
    assert _n362_said(out, vol.geo.lo, idx), ("%s must say that root 0x%x of the checkpoint copy in use (LCN 0x%x) "
                                               "cannot be verified" % (cmd, idx, vol.geo.lo)) + _ctx(vol, rc, out)
    assert not _n362_called_failed(out, vol.geo.lo, idx), "a root that cannot be checked is called failed: %r" \
        % _n362_called_failed(out, vol.geo.lo, idx) + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2: the copy the view is read from cannot be verified (rc=%d)" % (cmd, rc) \
        + _ctx(vol, rc, out)


@pytest.mark.parametrize("shape", sorted(_N362_SHAPES))
@pytest.mark.parametrize("cmd", sorted(_N362_VA))
def test_n362_a_root_of_the_copy_not_in_use_that_cannot_be_checked_is_said_by_the_va_set(vol, cmd, shape):
    how, idx = _N362_SHAPES[shape]
    tool, args = _N362_VA[cmd]
    rc0, out0 = vol.run(tool, *args)
    _fx(rc0 == 0 and not _n362_said(out0, vol.geo.hi, idx), "%s on the undamaged volume" % cmd + _ctx(vol, rc0, out0))
    plant_root_unchecked(vol, vol.geo.hi, idx, how)
    rc, out = vol.run(tool, *args)
    assert _n362_said(out, vol.geo.hi, idx), ("%s must say that root 0x%x of the checkpoint copy not in use (LCN 0x%x) "
                                               "cannot be verified" % (cmd, idx, vol.geo.hi)) + _ctx(vol, rc, out)
    assert not _n362_called_failed(out, vol.geo.hi, idx), "called failed: %r" \
        % _n362_called_failed(out, vol.geo.hi, idx) + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2, as for a copy not in use whose checksum cannot be verified (rc=%d)" % (cmd, rc) \
        + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", sorted(_N343_QUIET))
def test_n362_control_the_bootstrap_only_commands_keep_their_exit_code(vol, cmd):
    """V-a: a copy NOT in use whose root cannot be checked leaves the commands that only read through the copy in use
    at the undamaged exit code, saying nothing about it."""
    tool, args = _N343_QUIET[cmd]
    rc0, _out0 = vol.run(tool, *args)
    plant_root_unchecked(vol, vol.geo.hi, 7, "type")
    rc, out = vol.run(tool, *args)
    assert rc == rc0 and not _n362_said(out, vol.geo.hi, 7), "%s: %d -> %d" % (cmd, rc0, rc) + _ctx(vol, rc, out)


_PASSES_THAT_PASS = re.compile(r"(?i)\bpasses that pass\b")


def test_n362_the_n205_text_claims_no_pass_for_a_copy_with_a_root_not_checked(vol):
    plant_root_failure(vol, 7)                                   # the copy in use: root 7 fails (N205)
    plant_root_unchecked(vol, vol.geo.hi, 8, "type", other_clean=False)   # the other copy: root 8 not checkable
    rc, out = vol.run(FOREFST, "files")
    _keep(rc == 2 and _n205_said(out, vol.geo.lo, 7), "the copy in use's root 7 failure is said" + _ctx(vol, rc, out))
    claims = [s for s in _statements(out) if _PASSES_THAT_PASS.search(s)]
    assert not claims, "the other copy is said to pass the 26100 first pass, but its root 8 could not be checked: %r" \
        % claims + _ctx(vol, rc, out)


def test_n362_control_the_n205_text_says_the_other_copy_passes_when_it_does(vol):
    plant_root_failure(vol, 7)
    rc, out = vol.run(FOREFST, "files")
    assert rc == 2 and [s for s in _statements(out) if _PASSES_THAT_PASS.search(s) and _lcn_re(vol.geo.hi).search(s)], \
        _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 4. N363 -- `verify-bundle` says what it counted
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The critic's C-1: `verify-bundle` only bootstraps the rehydrated volume, so the findings it names are the ones
# recorded while reading the bundle's bootstrap structures; the redundancy checks of `summary`/`integrity` (copies the
# volume is not read from) are not run. Its line "the volume it carries has N finding(s)" and its help ("exit 0 ...
# the volume it carries has no finding") claim the volume's findings. Plant (the step5 witness's shape): root 7 fails
# on the copy in use (recorded by bootstrap) AND root 8 fails on the copy not in use (a redundancy condition only).

_VOLUME_CLAIM = re.compile(r"(?i)\bvolume (?:it carries )?has (?:no|a|\d+) finding")


def _verify_bundle_help(tmp_path):
    """The three places the contract is stated: CMD_HELP's example and notes, and the CLI -h text."""
    h = F.CMD_HELP["verify-bundle"]
    rc, out, err = _run_split(FOREFST, "help", "verify-bundle", cwd=str(tmp_path))
    _fx(rc == 0 and "verify-bundle" in out, "no -h text: rc=%d %s" % (rc, err[-500:]))
    return {"ex": " ".join(n for _e, n in h["ex"]), "notes": " ".join(h.get("notes") or []), "-h": " ".join(out.split())}


@IMAGE_ONLY                 # the synthetic volume's Object Table is empty: its bundle is refused as EMPTY
def test_n363_verify_bundle_names_what_it_counted(vol, tmp_path):
    g = vol.geo
    plant_root_failure(vol, 7)
    plant_root_failure_on(vol, g.hi, 8)
    b = str(tmp_path / "bundle")
    _export_bundle(vol, b)
    rcs, outs, errs = _run_split(FOREFST, b, "summary", cwd=str(tmp_path))
    _fx(rcs == 2 and _n205_said(outs + errs, g.lo, 7) and _n343_said(outs, g.hi, 8),
        "summary on the bundle lists both findings (the copy in use's root 7, the other copy's root 8)\n" + outs[-3000:])
    rc, out, err = _verify_bundle(b)
    _keep(rc == 2 and re.search(r"(?i)\bwhole\b", out), "exit 2, the bundle is whole\n" + out + err)
    line = [ln for ln in out.splitlines() if re.search(r"(?i)finding\(s\)", ln)]
    _fx(len(line) == 1, "one count line expected: %r" % line)
    assert not _VOLUME_CLAIM.search(line[0]), "the count is called the volume's, but summary on the bundle lists " \
        "another finding: %r" % line[0]
    assert re.search(r"(?i)\brecorded\b", line[0]) and re.search(r"(?i)\bbootstrap", line[0]), \
        "the count line must say what was counted (the findings recorded while reading the bootstrap structures): %r" \
        % line[0]


def test_n363_the_help_says_what_verify_bundle_counts(tmp_path):
    texts = _verify_bundle_help(tmp_path)
    bad = {k: t for k, t in texts.items() if _VOLUME_CLAIM.search(t)}
    assert not bad, "the help claims the volume's findings: %r" % bad
    assert all(re.search(r"(?i)\brecorded (?:no |a )?finding", t) for t in texts.values()), \
        "the help must say what is counted (the findings recorded while reading the bootstrap structures): %r" % texts


@IMAGE_ONLY
def test_n363_control_a_bundle_whose_only_finding_is_a_redundancy_condition_passes(vol, tmp_path):
    """V-a: a finding only `summary` and `integrity` see (the copy not in use) -- `verify-bundle` reads the bundle's
    bootstrap structures, records nothing and exits 0 with PASS, while `summary` on the bundle exits 2 and names it."""
    plant_root_failure_on(vol, vol.geo.hi, 8)
    b = str(tmp_path / "bundle")
    _export_bundle(vol, b)
    rc, out, err = _verify_bundle(b)
    assert rc == 0 and re.search(r"(?m)^verify-bundle: PASS\b", out), out + err
    rcs, outs, _errs = _run_split(FOREFST, b, "summary", cwd=str(tmp_path))
    assert rcs == 2 and _n343_said(outs, vol.geo.hi, 8), outs[-3000:]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 5. N364 -- G2c's own tidy
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# --- R5: two shared definitions refsanalysis imports are rows of single_source.tsv (both copies) ---

def _tsv_functions(path):
    with open(path, encoding="utf-8") as fh:
        return {p[1] for p in (ln.rstrip("\n").split("\t") for ln in fh)
                if len(p) >= 3 and p[0] and not p[0].startswith("#") and p[0] != "@allow"}


def _tsv_copies():
    vdir = _verification_dir()
    copies = [os.path.join(vdir, "single_source.tsv")]
    dev = os.path.join(REPO, "analysis", "verification", "single_source.tsv")
    if os.path.isfile(dev) and os.path.abspath(dev) != os.path.abspath(copies[0]):
        copies.append(dev)
    return copies


def test_n364_r5_the_shared_definitions_are_rows_of_single_source_tsv():
    copies = _tsv_copies()
    if len(copies) == 2:
        with open(copies[0], "rb") as a, open(copies[1], "rb") as b:
            _keep(a.read() == b.read(), "the two single_source.tsv copies differ: %r" % copies)
    for p in copies:
        funcs = _tsv_functions(p)
        missing = [n for n in ("container_size_zero_text", "_metadata_incomplete") if n not in funcs]
        assert not missing, "%s has no row for %r" % (p, missing)


def test_n364_r5_control_group_2s_shared_helpers_are_rows():
    for p in _tsv_copies():
        assert {"_view_conditions", "table_row_count", "checkpoint_select"} <= _tsv_functions(p), p


# --- R6: one wording for the roots check in `supb --verify` and `chkp --verify` ---

_SUPB_ROOTS_DET = re.compile(r"^LCN 0x[0-9a-f]+ \(offset 0x[0-9a-f]+\): (.*)$")
_CHKP_ROOTS_LINE = re.compile(r"^\s*\[(OK|FAIL|WARN)\]\s+(.*?)\s*$")


def _norm(t):
    t = t.strip().rstrip(".")
    return (t[:1].lower() + t[1:]) if t else t


def _supb_roots_text(out, slot):
    rows = _roots_rows(out)
    _fx(slot in rows, "no roots row for slot %d" % slot)
    res, det = rows[slot]
    m = _SUPB_ROOTS_DET.match(det)
    _fx(m, "unexpected roots row details: %r" % det)
    return res, _norm(m.group(1))


def _chkp_roots_text(out):
    hits = [(m.group(1), m.group(2)) for ln in out.splitlines() for m in [_CHKP_ROOTS_LINE.match(ln)]
            if m and re.search(r"(?i)\broots?\b", m.group(2))
            and re.search(r"(?i)digest|root list|cannot be (?:verified|checked)", m.group(2))]
    _fx(len(hits) == 1, "one roots check line expected in chkp --verify: %r" % hits)
    return hits[0][0], _norm(hits[0][1])


def _r6_state(v, state):
    if state == "fail":
        plant_root_failure(v, 7)
    elif state == "unchecked":
        plant_root_unchecked(v, v.geo.lo, 7, "type")


_R6_RESULT = {"ok": "OK", "fail": "FAIL", "unchecked": "WARN"}


@pytest.mark.parametrize("state", sorted(_R6_RESULT))
def test_n364_r6_supb_verify_and_chkp_verify_word_the_roots_check_the_same_way(vol, state):
    _r6_state(vol, state)
    rcs, outs = vol.run(REFSANALYSIS, "supb", "--verify")
    rcc, outc = vol.run(REFSANALYSIS, "chkp", "--verify")
    s_res, s_text = _supb_roots_text(outs, 1)                # slot 1 = lo = the copy in use, which chkp decodes
    c_res, c_text = _chkp_roots_text(outc)
    _keep(s_res == c_res == _R6_RESULT[state], "the results: supb %s, chkp %s" % (s_res, c_res))
    assert s_text == c_text, "one check, two wordings:\n  supb --verify: %r\n  chkp --verify: %r" % (s_text, c_text)


@pytest.mark.parametrize("state", sorted(_R6_RESULT))
def test_n364_r6_control_both_commands_report_the_state(vol, state):
    _r6_state(vol, state)
    rcs, outs = vol.run(REFSANALYSIS, "supb", "--verify")
    rcc, outc = vol.run(REFSANALYSIS, "chkp", "--verify")
    assert _supb_roots_text(outs, 1)[0] == _chkp_roots_text(outc)[0] == _R6_RESULT[state], (outs[-2000:], outc[-2000:])


# --- T4: `boot --verify` on a zero container size: the table is not padded to the shared text ---

def _verify_table(out):
    lines = out.splitlines()
    starts = [k for k, ln in enumerate(lines) if re.match(r"^Check\s+Result\s+Details", ln)]
    _fx(len(starts) == 1, "one verify table expected")
    tbl = []
    for ln in lines[starts[0]:]:
        if not ln.strip():
            break
        tbl.append(ln)
    return tbl


def test_n364_t4_boot_verify_is_not_padded_to_the_shared_text(vol):
    rc0, out0 = vol.run(REFSANALYSIS, "boot", "--verify")
    w0 = max(len(ln) for ln in _verify_table(out0))
    _fx(rc0 == 0 and w0 < 160, "the undamaged table is %d wide" % w0 + _ctx(vol, rc0, out0))
    plant_container_zero(vol)
    rc, out = vol.run(REFSANALYSIS, "boot", "--verify")
    _keep(rc == 2 and _n354_said(out), "the shared finding is said, exit 2 (decision 29)" + _ctx(vol, rc, out))
    w = max(len(ln) for ln in _verify_table(out))
    assert w <= w0, "the table is %d characters wide (undamaged: %d): every row is padded to the shared text" \
        % (w, w0) + _ctx(vol, rc, out)


def test_n364_t4_control_the_undamaged_table_is_narrow(vol):
    rc, out = vol.run(REFSANALYSIS, "boot", "--verify")
    tbl = _verify_table(out)
    assert rc == 0 and max(len(ln) for ln in tbl) < 160 and not _n354_said(out), _ctx(vol, rc, out)


# --- B1: refsanalysis `supb`'s fallback NOTE states the backup copy's checksum result ---

def _b1_said(out, v):
    b0 = v.geo.backups[1]          # C2 ST-S1 (a2): end-2, the copy shown after the primary fails (Q3; was end-3)
    return [s for s in _statements(out) if _lcn_re(b0).search(s) and re.search(r"(?i)\bread from\b", s)
            and re.search(r"(?i)\bpasses its self-checksum \(CRC32-C\)", s)]


_B1_FORMS = {"supb": ("supb",), "supb-v": ("supb", "-v"), "supb-vv": ("supb", "-vv"), "supb-raw": ("supb", "--raw")}


# `_st_s1` (C2 ST-S1's RED mark for the nodes B15's decided output changed) removed in step C2, area supb


# RED 1.13.2 B15 (C2 ST-S1 a2): the NOTE must name end-2, the copy read after the primary fails (Q3); the tool shows
# end-3 (the strict xfail mark removed: fixed in step C2, area supb)
@pytest.mark.parametrize("form", sorted(_B1_FORMS))
def test_n364_b1_supb_fallback_note_states_the_backups_checksum_result(vol, form):
    rc0, out0 = vol.run(REFSANALYSIS, *_B1_FORMS[form])
    _fx(rc0 == 0 and not _b1_said(out0, vol), "%s on the undamaged volume" % form + _ctx(vol, rc0, out0))
    damage_supb(vol, "primary")
    rc, out = vol.run(REFSANALYSIS, *_B1_FORMS[form])
    _keep(rc == 2, "the fallback exits 2" + _ctx(vol, rc, out))
    assert _b1_said(out, vol), "%s: the NOTE must say the backup copy shown passes its self-checksum (CRC32-C)" \
        % form + _ctx(vol, rc, out)


def test_n364_b1_control_supb_verify_states_it_in_its_row(vol):
    damage_supb(vol, "primary")
    rc, out = vol.run(REFSANALYSIS, "supb", "--verify")
    assert rc == 2 and re.search(r"(?m)^supb_backup_checksum\s+OK\s+LCN 0x0*%x\b" % vol.geo.backups[0], out), \
        _ctx(vol, rc, out)


def test_matchers():
    """The oracles above, on hand-written lines (no tool run)."""
    g = _AB.IMG

    class _V:
        geo = g
    s = ("[forefst] WARNING: the newest checkpoint copy (LCN 0x13f8, vclock 64) passes its self-checksum, but its "
         "root list could not be read (no root references), so this tool does not read the volume from it; this "
         "view is read from the copy at LCN 0xee34 (vclock 63): changes committed after vclock 63 are not in it")
    assert _n361_said(s, _V) and not _n361_said(s.replace("0xee34", "0x13f9"), _V)
    assert _n362_said("x: the checkpoint copy in use at LCN 0x13f8 (vclock 64): root 7 (Container Table) cannot be "
                      "verified (...)", 0x13f8, 7)
    assert not _n362_said("root 7 (Container Table) cannot be checked LCN 0x13f8", 0x13f8, 7)
    assert _VOLUME_CLAIM.search("the volume it carries has 2 finding(s)") and _VOLUME_CLAIM.search(
        "the volume it carries has no finding") and not _VOLUME_CLAIM.search("reading it recorded 2 finding(s)")
    assert _norm("Roots 0xC, 7 and 8 match.") == "roots 0xC, 7 and 8 match"
