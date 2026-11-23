"""1.13.2 RED cases for decision 27 (fix group 2, the first review round's leftovers): 27.1, 27.3, N331's message,
N332-N338.

Context: `analysis/reports/v1.13.2/fixes/G2_CONTEXT.md` ("Added 2026-10-02 (later) -- decisions 26 and 27"),
PLAN_1.13.2 decision 27, RUNNING_LOG rows N330-N340, `fixes/REVIEW_G2_correctness.md` F2-F6, F9, F11, F12 and
`fixes/REVIEW_G2_tests.md` N3, N4. Report, with every node's observed failure before the fix:
`analysis/reports/v1.13.2/fixes/FIX_G2.md`, section "Decision 27 (follow-up)".

What each RED asserts
---------------------
 1 27.1 / N330  the primary superblock has NO signature and every backup that has one fails its self-checksum: the
                first signed backup in slot order is read, the finding names it and says it failed, exit 2 in every
                command, no --partition-start hint (today: exit 1 with the hint). A verified backup is still the copy
                read (control); no signature anywhere still exits 1 with the hint (group2b's d26 control).
 2 27.2         no RED: a primary that fails while a backup verifies already exits 2 in every command; pinned for
                `files` by test_1132_red_group2b.py::test_d26_control_backups_that_verify_are_still_the_copy_read.
 3 27.3         the copy the volume view is read from cannot be verified (unknown checksum type): the checkpoint copy
                in use, or the superblock copy read (the primary, or a backup the tool fell back to) -- every command
                exits 2 and the copy is said to be "cannot be verified (unknown checksum type 0xNN)", never FAILED and
                never "passes its checks" (today: `files`, `search`, refsanalysis `files`/`chkp`/`containers`/`supb`
                exit 0). A copy NOT in use keeps V-a (controls).
 4 N331         the message for a superblock fallback claims nothing about the driver (today: "as the driver falls
                back to a backup copy that passes its checks"). The comment in `parse_supb` is not testable (no RED).
 5 N332         refsanalysis `chkp`, `chkp --verify`, `containers`, `supb`, `supb --verify` report a root 0xC, 7 or 8
                of the checkpoint copy in use that does not match its digest (forefst's N205 text) and exit 2;
                `chkp --verify` has a row for that check.
 6 N333         `chkp --verify`'s Result line does not count a check that could not be made as FAILED.
 7 N334         "the checkpoint copy in use", not "the in use checkpoint copy".
 8 N335         a SUPB/CHKP whose header declares no self-descriptor (pointer 0/0) fails its self-checksum, as in the
                26100 driver (today: the old descriptor scan reads it as "checksum OK").
 9 N336         "unreadable" / "not read" survives a damage register that is full (its 500-entry cap): root counts,
                the 0x520 table, the change-journal lookup and the banner's USN state.
10 N337         `help supb` / `help chkp` state that the bare commands exit 2 when they mark a copy FAILED and when
                the copy in use has a root that does not verify.
11 N338         `Security descs`, `Reparse index`, `Trash table` in forefst summary/fastsummary and refsanalysis
                summary++ say "unreadable" (text) and are marked as such (JSON) over a walk that raised or recorded
                damage (today: 0).
12 N340         no RED: a control edit (the unused alias) and a lost space.
13 N341         (class site placed by the lead) refsanalysis `supb`, `chkp`, `containers` say a +0x10/+0x60 clock
                divergence of the checkpoint copy in use in forefst's words and exit 2; a copy that FAILED is still said
                once, in the command's own words (control); `supb --raw`, which says nothing about a failed newest
                copy, says it in forefst's words and exits 2.
14 N336 widened (placed by the lead) the "N metadata page(s) could not be read" summary and `files`' written-file
                lines print the number of damage notes recorded, not the 500-entry list's length (group 3, N368:
                the number of DISTINCT pages the notes name; the in-process plant walks distinct pages).

Volumes and discipline: as test_1132_red_group2b.py -- the a_bootstrap `vol` fixture (``[synthetic]`` / ``[image]``,
imported by name), ``@_red`` = ``xfail(strict=True, raises=AssertionError)``, only a plain ``assert`` states the
defect, ``_fx`` for a fixture that is not what the case needs, ``_keep`` for a property the current tool already has,
every RED has a control that passes now, and every "the volume is read" oracle is checked first on the undamaged
volume. Read-only corpus image: step5/testchecksums/win11refslasttests_baseline_corrupted.raw (item 5's witness).
In-process nodes (items 8 and 9) give every forefst run register a fresh value through monkeypatch.
The marks were removed when the fix landed (FIX_G2.md, "Decision 27 (follow-up)"): the unmarked file fails against
the step's pre-fix tools (`fixes/prefix_G2f/`) at the REDs' plain asserts and passes on the fixed tree.
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
    RedFixtureError, _fx, _keep, _ctx, damage_supb, damage_chkp, _own_digest, _FAIL, _lcn_re,
    _named_failed, _reads_checkpoint, _guid, _virtual_clock, FOREFST, REFSANALYSIS, CS, SUPB_DESC, CHKP_DESC,
    ZERO_WINDOW, GUID, GUID_RAW, CLOCK_NEW, CLOCK_OLD)
from test_1132_red_group2 import (                       # noqa: E402
    IMAGE_ONLY, _statements, _UNVERIFIED, _DRIVER, _N205_ROOTS, plant_root_failure, _n205_said, _root_named)
from test_1132_red_group2b import (                      # noqa: E402
    plant_unknown_type, _said_unknown_type, _called_failed, _D26_RUNS, _PS_HINT, _NO_SUPB_VERIFIES, _files_listing,
    plant_unreadable_520, _run, _json_text, _edit_vbr, _BOOT_ROWS, _help)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402


# `_st_s1` (C2 ST-S1's RED mark for the nodes B15's decided output changed) removed in step C2, area supb

vol = _AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 1. 27.1 / N330 -- no signed primary; the signed backups fail their self-checksum
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def damage_d27_1(v, b0_zeroed=False):
    """Zero the primary superblock (no signature). Each backup kept gets one byte flipped at +0x400 -- inside the
    hashed cluster, outside the GUID, the checkpoint list and the self-descriptor -- so it keeps its signature, GUID
    and list and fails its self-checksum. b0_zeroed: the first backup SLOT is zeroed as well, so the first SIGNED backup
    in slot order is the second. Returns the backup that must be read.
    C2 ST-S1 (a1): slot order is the driver's -- primary 0x1E, then N-2 (end-2, `geo.backups[1]`), then N-3 (end-3,
    `geo.backups[0]`; closure B-4.1 row 1, five builds) -- so the first signed backup is end-2, end-3 when end-2 is
    zeroed (it was end-3, end-2, the tool's order before B15)."""
    g = v.geo
    v.zero(v.at(g.supb), CS)
    signed = []
    for i, b in enumerate((g.backups[1], g.backups[0])):         # (a1): N-2, then N-3
        if b0_zeroed and i == 0:
            v.zero(v.at(b), CS)
        else:
            v.flip(v.at(b, 0x400))
            signed.append(b)
    _fx(not any(v.block(g.supb)), "the primary is not zeroed")
    for b in signed:
        blk = v.block(b)
        _fx(blk[:4] == b"SUPB" and v.refs(b) == [g.lo, g.hi] and blk[0x50:0x60] == GUID_RAW,
            "backup 0x%x lost its signature, checkpoint list or GUID" % b)
        _fx(v.verifies(b) is False and blk[SUPB_DESC + 0x28:SUPB_DESC + 0x2C] != _own_digest(blk, SUPB_DESC),
            "backup 0x%x still verifies" % b)
    if b0_zeroed:
        _fx(not any(v.block(g.backups[1])), "the first backup slot (end-2) is not zeroed")
    return signed[0]


_READ_FROM = r"(?i)\bread from\b[^.;]{0,80}?\bLCN 0x0*%x(?![0-9a-z])"


def _d27_1_statements(out, lcn):
    """Decision 27.1's finding: no superblock copy passes (verifies), the volume is READ FROM the backup at `lcn` (the
    LCN that follows "read from", not one listed among the copies tried), and that copy failed."""
    return [s for s in _statements(out) if _NO_SUPB_VERIFIES.search(s) and re.search(_READ_FROM % lcn, s)
            and re.search(r"(?i)\bbackup\b", s) and _FAIL.search(s)]


def _d27_reads(v, key, out, before, read_lcn):
    """[(property, holds)] -- what shows that the volume was READ, per command; the superblock shown by `supb -v` is
    the copy at `read_lcn`. `before` is the same command's output on the undamaged volume."""
    g = v.geo
    if key == "files":
        return [("the same CSV listing as on the undamaged volume", _files_listing(out) == _files_listing(before)),
                ("the same entry count", re.findall(r"Done\. (\d+) entr(?:y|ies)", out) ==
                 re.findall(r"Done\. (\d+) entr(?:y|ies)", before))]
    if key in ("summary", "integrity"):
        return [("the newest checkpoint is read (vclock %d, checksum OK)" % CLOCK_NEW,
                 bool(_reads_checkpoint(out, g.lo, CLOCK_NEW)))]
    if key == "ra-supb-v":
        return [("the superblock shown is the copy read (LCN 0x%x)" % read_lcn,
                 bool(re.search(r"(?m)^SUPB offset:\s+0x%x\s*$" % v.at(read_lcn), out))),
                ("its checkpoint list is read",
                 bool(re.search(r"checkpoint_in_use\s+checkpoint #1 @ 0x%x \(vc=%d\b" % (v.at(g.lo), CLOCK_NEW), out)))]
    if key == "ra-summary":
        return [("the checkpoint in use is read", _virtual_clock(out) == CLOCK_NEW
                 and bool(re.search(r"Copy in use:\s+LCN 0x%x\b" % g.lo, out)))]
    raise RedFixtureError("no oracle for %s" % key)


def _d27_before(v, key):
    tool, args = _D26_RUNS[key]
    rc, before = v.run(tool, *args)
    _fx(rc == 0, "%s: the undamaged volume does not exit 0 (rc=%d)" % (key, rc) + _ctx(v, rc, before))
    _fx(all(ok for _p, ok in _d27_reads(v, key, before, before, v.geo.supb)), "%s: the read oracle fails on the "
        "undamaged volume: %r" % (key, _d27_reads(v, key, before, before, v.geo.supb)) + _ctx(v, rc, before))
    _fx(not _PS_HINT.search(before) and not [s for s in _statements(before) if _NO_SUPB_VERIFIES.search(s)],
        "%s: the undamaged output already carries a hint or a finding" % key + _ctx(v, rc, before))
    if key == "files" and v.geo.kind == "image":
        _fx(len(_files_listing(before)) > 1, "files lists no entry on the undamaged image")
    return before


# RED 1.13.2 B15 (C2 ST-S1 a1): the first signed backup in slot order is end-2 (the driver's order: primary, N-2,
# N-3); the tool reads end-3, its first backup (the strict xfail mark removed: fixed in step C2, area supb)
@pytest.mark.parametrize("key", sorted(_D26_RUNS))
def test_d27_1_no_signed_primary_reads_the_first_signed_backup_says_it_failed_and_exits_2(vol, key):
    tool, args = _D26_RUNS[key]
    before = _d27_before(vol, key)
    b = damage_d27_1(vol)
    rc, out = vol.run(tool, *args)
    _keep(_named_failed(out, b), "the failed backup is named by its LCN" + _ctx(vol, rc, out))
    assert rc == 2, "decision 27.1: a volume readable from a signed backup exits 2, never 1 (rc=%d)" % rc \
        + _ctx(vol, rc, out)
    assert not _PS_HINT.search(out), "no --partition-start hint while a backup carries the SUPB signature" \
        + _ctx(vol, rc, out)
    assert _d27_1_statements(out, b), "the finding must be said: no superblock copy passes its self-checksum; read " \
        "from the backup at LCN 0x%x, which failed" % b + _ctx(vol, rc, out)
    missing = [p for p, ok in _d27_reads(vol, key, out, before, b) if not ok]
    assert not missing, "the volume must be read: %r" % missing + _ctx(vol, rc, out)
    if key in ("summary", "ra-summary"):
        assert _guid(out) == GUID, "the GUID is the backup's (%r)" % _guid(out) + _ctx(vol, rc, out)


@pytest.mark.parametrize("key", ["files", "ra-supb-v"])
def test_d27_1_the_first_SIGNED_backup_is_read_when_backup_0_has_no_signature(vol, key):
    tool, args = _D26_RUNS[key]
    before = _d27_before(vol, key)
    b = damage_d27_1(vol, b0_zeroed=True)
    # C2 ST-S1 (a1): the first backup slot is end-2 (N-2); zeroed, the first SIGNED backup is end-3 (N-3)
    _fx(b == vol.geo.backups[0], "end-3 is not the signed one")
    rc, out = vol.run(tool, *args)
    _keep(_named_failed(out, b), "the failed end-3 is named by its LCN" + _ctx(vol, rc, out))
    assert rc == 2 and not _PS_HINT.search(out), "exit 2, no hint (rc=%d)" % rc + _ctx(vol, rc, out)
    assert _d27_1_statements(out, b), "the finding names end-3 (LCN 0x%x) as the copy read" % b + _ctx(vol, rc, out)
    assert not _d27_1_statements(out, vol.geo.backups[1]), "end-2 has no signature and is not read" \
        + _ctx(vol, rc, out)
    missing = [p for p, ok in _d27_reads(vol, key, out, before, b) if not ok]
    assert not missing, "the volume must be read from end-3: %r" % missing + _ctx(vol, rc, out)


@pytest.mark.parametrize("key", sorted(_D26_RUNS))
def test_d27_1_control_a_verified_backup_is_still_the_copy_read(vol, key):
    """A1 kept: no signature on the primary, the first backup slot fails, the second verifies -- the second is read,
    exit 2, no 'no superblock copy passes' statement, no hint. C2 ST-S1 (a1): the first slot is end-2 (N-2), the
    second end-3 (N-3), the driver's order."""
    tool, args = _D26_RUNS[key]
    g = vol.geo
    b1 = g.backups[0]                                            # (a1): end-3, the second slot, verifies
    vol.zero(vol.at(g.supb), CS)
    vol.flip(vol.at(g.backups[1], 0x400))                        # (a1): end-2, the first slot, fails
    _fx(vol.verifies(g.backups[1]) is False and vol.verifies(b1) is True, "the backups are not failed / verified")
    rc, out = vol.run(tool, *args)
    assert rc == 2, _ctx(vol, rc, out)
    assert [s for s in _statements(out) if _lcn_re(b1).search(s) and re.search(r"(?i)\bbackup\b", s)
            and re.search(r"(?i)\bread\b", s)], "the verified backup read is named" + _ctx(vol, rc, out)
    assert not [s for s in _statements(out) if _NO_SUPB_VERIFIES.search(s)] and not _PS_HINT.search(out), \
        _ctx(vol, rc, out)
    if key == "ra-supb-v":
        assert re.search(r"(?m)^SUPB offset:\s+0x%x\s*$" % vol.at(b1), out), _ctx(vol, rc, out)
    if key in ("summary", "ra-summary"):
        assert _guid(out) == GUID, _ctx(vol, rc, out)


def test_d27_1_matcher_accepts_the_decided_wording_and_rejects_todays_lines():
    ok = ["[forefst] WARNING: no superblock copy passes its self-checksum (primary at LCN 0x1e: all zeros; backups: "
          "LCN 0xfd: self-checksum FAILED (CRC32-C); LCN 0xfe: self-checksum FAILED (CRC32-C)); this view is read "
          "from the backup copy at LCN 0xfd (offset 0xfd000), which FAILED its self-checksum (CRC32-C)",
          "no SUPB copy verifies; read from the backup at LCN 0xfd, which failed"]
    for s in ok:
        assert _d27_1_statements(s, 0xFD), s
    other = ("no superblock copy passes its self-checksum (backups: LCN 0xfd: no SUPB signature; LCN 0xfe: "
             "self-checksum FAILED (CRC32-C)); this view is read from the backup copy at LCN 0xfe, which FAILED")
    assert _d27_1_statements(other, 0xFE) and not _d27_1_statements(other, 0xFD), other
    bad = ["forefst: error: superblock (SUPB) not found at LCN 0x1e (offset 0x1e000): expected 'SUPB', got b'\\x00', "
           "and no usable backup superblock was found (LCN 0xfd: self-checksum FAILED (CRC32-C); LCN 0xfe: "
           "self-checksum FAILED (CRC32-C)). If this is a raw partition image, check --partition-start",
           "no superblock copy passes its self-checksum; this view is read from the primary, which FAILED",
           "[forefst] WARNING: the primary superblock (SUPB) at LCN 0x1e (offset 0x1e000) is not usable (all zeros); "
           "the volume is read from the backup copy at LCN 0xfd (offset 0xfd000)"]
    for s in bad:
        assert not _d27_1_statements(s, 0xFD), s


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 3. 27.3 -- the copy the volume view is read from cannot be verified: EVERY command exits 2
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix (both volumes): with an unknown checksum type (0x03) in the declared self-descriptor of the
# checkpoint copy in use, or of the primary superblock, `files`, `search`, refsanalysis `files`, `chkp`, `containers`
# and `supb` exit 0; `summary`/`fastsummary`/`integrity` exit 2 (decision 22). A primary that fails with a backup
# whose type is unknown: the tool reads that backup and says "as the driver falls back to a backup copy that passes
# its checks".

_EVERY = {"files": (FOREFST, ("files",)), "search": (FOREFST, ("search", "ok")),
          "ra-files": (REFSANALYSIS, ("files",)), "ra-chkp": (REFSANALYSIS, ("chkp",)),
          "ra-containers": (REFSANALYSIS, ("containers",)), "ra-supb": (REFSANALYSIS, ("supb",))}
_REDUNDANCY = {"summary": (FOREFST, ("summary",)), "fastsummary": (FOREFST, ("fastsummary",)),
               "integrity": (FOREFST, ("integrity",))}
_T = 0x03


def _plant_27_3(v, which):
    g = v.geo
    if which == "chkp-in-use":
        return g.lo, plant_unknown_type(v, g.lo, 0x58, _T)
    if which == "supb-primary":
        return g.supb, plant_unknown_type(v, g.supb, 0x78, _T)
    raise RedFixtureError(which)


def _files_before(v, key):
    if key != "files":
        return None
    rc, out = v.run(FOREFST, "files")
    _fx(rc == 0 and (v.geo.kind != "image" or len(_files_listing(out)) > 1), "files on the undamaged volume"
        + _ctx(v, rc, out))
    return out


@pytest.mark.parametrize("key", sorted(_EVERY))
@pytest.mark.parametrize("which", ["chkp-in-use", "supb-primary"])
def test_d27_3_the_copy_read_cannot_be_verified_every_command_exits_2(vol, which, key):
    tool, args = _EVERY[key]
    before = _files_before(vol, key)
    lcn = _plant_27_3(vol, which)[0]
    rc, out = vol.run(tool, *args)
    if before is not None:
        _keep(_files_listing(out) == _files_listing(before), "the same copy is read (the same listing)"
              + _ctx(vol, rc, out))
    assert not _called_failed(out, lcn), "the copy is called failed: %r" % _called_failed(out, lcn) \
        + _ctx(vol, rc, out)
    assert rc == 2, "decision 27.3: the copy the view is read from cannot be verified -> exit 2 (rc=%d)" % rc \
        + _ctx(vol, rc, out)
    assert _said_unknown_type(out, lcn, _T), "the copy at LCN 0x%x must be said to be unverifiable, unknown " \
        "checksum type 0x%02x" % (lcn, _T) + _ctx(vol, rc, out)


# RED 1.13.2 B15 (C2 ST-S1 a2): after the primary fails, end-2 is read (both backups usable, equal +0x68: Q3); the
# plant aimed at the copy read moves to end-2, and the tool reads end-3 (the strict xfail mark removed: fixed in
# step C2, area supb)
@pytest.mark.parametrize("key", ["files", "ra-supb"])
def test_d27_3_a_backup_read_after_a_fallback_that_cannot_be_verified_is_said_so(vol, key):
    tool, args = _EVERY[key]
    g = vol.geo
    b0 = g.backups[1]                                            # C2 ST-S1 (a2): end-2, the copy read (Q3)
    vol.flip(vol.at(g.supb, 0x400))
    _fx(vol.verifies(g.supb) is False, "the primary still verifies")
    plant_unknown_type(vol, b0, 0x78, _T)
    _fx(F.supb_validate(vol.block(b0), CS, b0)["cksum_ok"] is None, "end-2 is not unverifiable")
    rc, out = vol.run(tool, *args)
    _keep(rc == 2, "a superblock fallback exits 2" + _ctx(vol, rc, out))
    assert [s for s in _statements(out) if _lcn_re(b0).search(s) and re.search(r"(?i)\bread\b", s)], \
        "the backup read (end-2, LCN 0x%x) is named" % b0 + _ctx(vol, rc, out)       # C2 ST-S1 (a2): was a _keep
    passes = [s for s in _statements(out) if _lcn_re(b0).search(s)
              and re.search(r"(?i)\bpass(es)? its (checks|self-checksum)\b", s)]
    assert not passes, "the backup read is said to pass its checks: %r" % passes + _ctx(vol, rc, out)
    assert not _called_failed(out, b0), "the backup is called failed: %r" % _called_failed(out, b0) \
        + _ctx(vol, rc, out)
    assert _said_unknown_type(out, b0, _T), "the backup read must be said to be unverifiable, unknown checksum " \
        "type 0x%02x" % _T + _ctx(vol, rc, out)


@pytest.mark.parametrize("which", ["chkp-older", "supb-backup"])
def test_d27_3_control_a_copy_not_in_use_keeps_v_a(vol, which):
    """V-a: the copy that cannot be verified is NOT the one the view is read from (the older checkpoint copy; a
    backup superblock while the primary verifies): the bootstrap-only commands exit 0, summary/fastsummary/integrity
    exit 2 and say the copy cannot be verified, never that it failed."""
    g = vol.geo
    lcn = g.hi if which == "chkp-older" else g.backups[0]
    plant_unknown_type(vol, lcn, 0x58 if which == "chkp-older" else 0x78, _T)
    for key, (tool, args) in sorted(_EVERY.items()):
        rc, out = vol.run(tool, *args)
        assert rc == 0, key + _ctx(vol, rc, out)
    for key, (tool, args) in sorted(_REDUNDANCY.items()):
        rc, out = vol.run(tool, *args)
        assert rc == 2 and _said_unknown_type(out, lcn, _T) and not _called_failed(out, lcn), key \
            + _ctx(vol, rc, out)


def test_d27_3_control_the_undamaged_volume_exits_0_in_every_command(vol):
    for key, (tool, args) in sorted(_EVERY.items()):
        rc, out = vol.run(tool, *args)
        assert rc == 0 and not [s for s in _statements(out) if _UNVERIFIED.search(s)], key + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 4. N331 -- the superblock fallback message claims nothing about the driver
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The tool's rule is its own (signature + self-checksum, primary preferred); the 26100 driver's ValidateSuperBlock
# checks more and ChooseSuperBlock ranks copies by +0x68 (review 1 F5; plan item B15). Decision 27.4: say what the tool
# does, claim nothing about the driver.

# RED 1.13.2 B15 (C2 ST-S1 a2): after the primary fails, the fallback statement names end-2 as the copy read (Q3);
# the tool names end-3 (the strict xfail mark removed: fixed in step C2, area supb)
def test_n331_the_superblock_fallback_message_claims_nothing_about_the_driver(vol):
    b0 = vol.geo.backups[1]                                      # C2 ST-S1 (a2): end-2, the copy read (Q3)
    damage_supb(vol, "primary")
    rc, out = vol.run(FOREFST, "files")
    said = [s for s in _statements(out) if _lcn_re(b0).search(s) and re.search(r"(?i)\bbackup\b", s)
            and re.search(r"(?i)\bread\b", s)]
    _keep(rc == 2, "the fallback exits 2" + _ctx(vol, rc, out))
    assert said, "the fallback statement names end-2 (LCN 0x%x) as the copy read" % b0 \
        + _ctx(vol, rc, out)                                     # C2 ST-S1 (a2): was part of the _keep
    assert not [s for s in said if _DRIVER.search(s)], "the fallback statement claims the driver's choice: %r" \
        % said + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 5. N332 -- refsanalysis supb/chkp/containers and the root 0xC/7/8 failure of the checkpoint copy in use
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix: forefst `files`/`summary` print the N205 statement and exit 2; refsanalysis `chkp --verify`
# prints "Result: 19/19 checks passed" and exits 0; `chkp`, `containers`, `supb`, `supb --verify` say nothing, rc 0.

_N332 = {"chkp": ("chkp",), "chkp-verify": ("chkp", "--verify"), "containers": ("containers",),
         "supb": ("supb",), "supb-verify": ("supb", "--verify")}
_ROOT_IDS = ["root0xC", "root7", "root8"]
_N332_WITNESS = "win11refslasttests_baseline_corrupted.raw"


@pytest.mark.parametrize("idx", _N205_ROOTS, ids=_ROOT_IDS)
@pytest.mark.parametrize("cmd", sorted(_N332))
def test_n332_refsanalysis_reports_the_root_failure_of_the_copy_in_use_and_exits_2(vol, cmd, idx):
    plant_root_failure(vol, idx)
    rc, out = vol.run(REFSANALYSIS, *_N332[cmd])
    assert _n205_said(out, vol.geo.lo, idx), (
        "refsanalysis %s must say that the 26100 driver's first pass rejects the checkpoint copy in use (LCN 0x%x): "
        "root 0x%x does not verify" % (cmd, vol.geo.lo, idx)) + _ctx(vol, rc, out)
    assert rc == 2, "refsanalysis %s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("idx", _N205_ROOTS, ids=_ROOT_IDS)
def test_n332_chkp_verify_has_a_failing_row_for_the_roots_of_the_copy(vol, idx):
    plant_root_failure(vol, idx)
    rc, out = vol.run(REFSANALYSIS, "chkp", "--verify")
    rows = [ln for ln in out.splitlines() if re.match(r"\s*\[FAIL\]", ln) and _root_named(ln, idx)]
    assert rows, "a [FAIL] row must name root 0x%x" % idx + _ctx(vol, rc, out)
    assert not re.search(r"Result: (\d+)/\1 checks passed", out), "every check reported passed" + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", ["chkp-verify", "containers", "supb-verify"])
def test_n332_image_witness_refsanalysis_reports_the_root_failure(cmd):
    p = _corpus_image(_N332_WITNESS)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % _N332_WITNESS)
    ps, _why = F.find_refs_partition(p)
    _fx(ps is not None, "no ReFS partition in the witness")
    with open(p, "rb") as f:
        cs = F.parse_vbr(f, ps)[0]
        sel = F.checkpoint_select(f, ps, cs, F.parse_supb(f, ps, cs), require_roots=True)
    use = sel["in_use"]
    _fx(use is not None and [i for i, _w in use["root_fail"]] == [7], "the witness's copy in use does not fail root 7 "
        "alone: %r" % (use and use["root_fail"],))
    rc, out = _run(REFSANALYSIS, p, *_N332[cmd], cwd=os.path.dirname(REFSANALYSIS))
    _keep(not re.search(r"(?i)traceback", out), "no crash")
    assert _n205_said(out, use["lcn"], 7), "the root 7 failure of the copy in use (LCN 0x%x) must be said" \
        % use["lcn"] + "\n" + out[-4000:]
    assert rc == 2, "rc=%d" % rc + "\n" + out[-4000:]


# On the synthetic volume `chkp --verify` already exits 2 ("CPC mismatch: Container Table=0x0, VBR=0x4000": its one
# Container Table row carries no CPC), so there the rc assertion of the `chkp-verify` nodes above holds already; their
# statement assertion discriminates on both volumes, the rc assertion on the image.
def test_n332_control_the_undamaged_volume_says_nothing_and_exits_0(vol):
    for cmd, args in sorted(_N332.items()):
        rc, out = vol.run(REFSANALYSIS, *args)
        assert not [s for s in _statements(out) if "26100" in s], cmd + _ctx(vol, rc, out)
        if cmd == "chkp-verify" and vol.geo.kind == "synthetic":
            # acceptance 1.14.0 E2 close (review S4, K28): the count in decimal
            assert rc == 2 and re.search(r"(?m)^\s*\[WARN\] CPC mismatch: Container Table=0\b", out), _ctx(vol, rc, out)
            continue
        assert rc == 0, cmd + _ctx(vol, rc, out)
        if cmd == "chkp-verify":
            assert re.search(r"Result: (\d+)/\1 checks passed", out), _ctx(vol, rc, out)


def test_n332_control_forefst_files_already_states_it(vol):
    plant_root_failure(vol, 7)
    rc, out = vol.run(FOREFST, "files")
    assert rc == 2 and _n205_said(out, vol.geo.lo, 7), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 6. N333 -- `chkp --verify`'s Result line counts a check that could not be made as FAILED
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix: "[WARN] CHKP self-checksum cannot be verified (unknown checksum type 0x03)" and, on a
# `refsutil fixboot` VBR (+0x40 zero), "[WARN] CPC ... cannot be compared", each followed by
# "Result: 1 check(s) FAILED (18/19 passed)". Exit 2 stays (decisions 21, 22).

def _result_line(out):
    res = re.findall(r"(?m)^\s*Result:.*$", out)
    _fx(len(res) == 1, "one Result line expected: %r" % res)
    return res[0]


def _plant_n333(v, case):
    if case == "chkp-unknown-type":
        plant_unknown_type(v, v.geo.lo, 0x58, _T)
    elif case == "vbr-container-zero":
        _edit_vbr(v, _BOOT_ROWS["container_nonzero"])
    else:
        raise RedFixtureError(case)


@IMAGE_ONLY                 # the synthetic volume's `chkp --verify` already fails its CPC check (section 5's note)
@pytest.mark.parametrize("case", ["chkp-unknown-type", "vbr-container-zero"])
def test_n333_chkp_verify_result_separates_failed_from_could_not_be_made(vol, case):
    _plant_n333(vol, case)
    rc, out = vol.run(REFSANALYSIS, "chkp", "--verify")
    _keep(rc == 2, "exit 2 (decisions 21, 22)" + _ctx(vol, rc, out))
    warn = [ln for ln in out.splitlines() if re.match(r"\s*\[WARN\]", ln) and re.search(r"(?i)cannot be "
                                                                                        r"(verified|compared)", ln)]
    _keep(len(warn) == 1 and not re.search(r"(?m)^\s*\[FAIL\]", out), "one check could not be made, none failed"
          + _ctx(vol, rc, out))
    res = _result_line(out)
    m = re.search(r"(\d+) check\(s\) FAILED", res)
    assert not (m and int(m.group(1)) > 0), "a check that could not be made is counted as FAILED: %r" % res
    assert re.search(r"(?i)\b1 (check\(s\) )?could not be made\b", res), \
        "the Result line must say that 1 check could not be made: %r" % res


@IMAGE_ONLY
def test_n333_control_a_check_that_failed_is_still_counted_as_failed(vol):
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(REFSANALYSIS, "chkp", "--verify")
    res = _result_line(out)
    assert rc == 2 and re.search(r"\b1 check\(s\) FAILED\b", res) \
        and not re.search(r"(?i)\b[1-9]\d* (check\(s\) )?could not be made\b", res), res + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 7. N334 -- "the in use checkpoint copy"
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cmd", ["summary", "integrity"])
def test_n334_the_role_in_use_follows_the_noun(vol, cmd):
    lo = vol.geo.lo
    plant_unknown_type(vol, lo, 0x58, _T)
    rc, out = vol.run(FOREFST, cmd)
    _keep(_said_unknown_type(out, lo, _T), "the copy is said to be unverifiable" + _ctx(vol, rc, out))
    assert not re.search(r"(?i)\bthe in use checkpoint copy\b", out), "'the in use checkpoint copy'" \
        + _ctx(vol, rc, out)
    assert re.search(r"(?i)\bthe checkpoint copy in use at LCN 0x0*%x\b" % lo, out), \
        "'the checkpoint copy in use at LCN 0x%x'" % lo + _ctx(vol, rc, out)


def test_n334_control_the_other_role_words_already_read_before_the_noun(vol):
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(FOREFST, "summary")
    assert re.search(r"(?i)\bthe newest checkpoint copy \(LCN 0x0*%x\b" % vol.geo.lo, out), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 8. N335 -- a self-descriptor pointer 0/0
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The 26100 driver hands the header's pointer to ValidateLcnWithChecksum, which refuses a descriptor shorter than 0x28
# bytes, so the copy fails its checksum validation (26100.8115: ComputeOrVerifySelfChecksumBlock @1400f2924,
# refs_win11.decomp.c:201379-201382; ValidateLcnWithChecksum @1400b2a44, :153517-153533). The tool falls back to the
# 1.13.1 descriptor scan and finds the descriptor that is still there: "checksum OK".
# The plant zeroes the pointer and recomputes the digest over the descriptor the block still holds (the window the
# corpus recipe zeroes), cross-checked with this module's own CRC32-C; it does not use Vol.reseal, which requires the
# tool to accept the result.

_PTR = {"supb": (0x78, SUPB_DESC), "chkp": (0x58, CHKP_DESC)}


def plant_pointer(v, which, length=0):
    """Set the header's self-descriptor pointer of the primary SUPB / the newest CHKP to (0, 0) -- or, with `length`,
    keep the offset and declare that length -- and recompute the stored digest. Returns the block's LCN."""
    ptr, desc = _PTR[which]
    lcn = v.geo.supb if which == "supb" else v.geo.lo
    b = bytearray(v.block(lcn))
    recipe = F._self_checksum_recipe(bytes(b), CS)
    _fx(recipe == (desc, 1, 4, ZERO_WINDOW), "0x%x: unexpected self-checksum recipe %r" % (lcn, recipe))
    _fx(F.le32(b, ptr) == desc and F.le32(b, ptr + 4) == 0x30, "0x%x: the header does not declare 0x%x/0x30"
        % (lcn, desc))
    struct.pack_into("<II", b, ptr, desc if length else 0, length)
    out = F._recompute_self_checksum(b, CS, recipe)
    _fx(bytes(out[desc + 0x28:desc + 0x2C]) == _own_digest(out, desc),
        "0x%x: fd._recompute_self_checksum disagrees with an independent CRC32-C" % lcn)
    v.write(v.at(lcn), bytes(out[:CS]))
    blk = v.block(lcn)
    _fx(F.le32(blk, ptr) == (desc if length else 0) and F.le32(blk, ptr + 4) == length, "the pointer did not land")
    _fx(blk[desc + 0x28:desc + 0x2C] == _own_digest(blk, desc), "the digest does not match the block")
    v.ops.append("0x%x: self-descriptor pointer -> %s, digest recomputed" % (lcn, "0x%x/0x%x" % (desc, length)
                                                                            if length else "0/0"))
    return lcn


@pytest.mark.parametrize("which", sorted(_PTR))
def test_n335_a_pointer_0_0_fails_the_self_checksum(vol, which):
    lcn = plant_pointer(vol, which)
    ok, name = F._verify_self_checksum(vol.block(lcn), CS)
    assert ok is False, "pointer 0/0 must fail as in the 26100 driver (got %r, %r)" % (ok, name)


def test_n335_integrity_names_the_primary_whose_pointer_is_0_0_failed(vol):
    lcn = plant_pointer(vol, "supb")
    rc, out = vol.run(FOREFST, "integrity")
    assert _named_failed(out, lcn, r"\bprimary\b"), "the primary (LCN 0x%x) must be named as failed" % lcn \
        + _ctx(vol, rc, out)
    assert rc == 2, "rc=%d" % rc + _ctx(vol, rc, out)


@pytest.mark.parametrize("which", sorted(_PTR))
def test_n335_control_a_declared_pointer_shorter_than_0x28_already_fails(vol, which):
    lcn = plant_pointer(vol, which, length=0x27)
    assert F._verify_self_checksum(vol.block(lcn), CS)[0] is False


def test_n335_control_the_declared_descriptors_verify(vol):
    for lcn in (vol.geo.supb, vol.geo.lo):
        assert F._verify_self_checksum(vol.block(lcn), CS) == (True, "CRC32-C")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 9. N336 -- "unreadable" / "not read" decided by the growth of a capped list
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `_walk_note_damage` stops appending at 500 entries. In-process: every forefst run register gets a fresh value
# (monkeypatch), the damage list is filled to its cap, then the reader runs over a zeroed root. A zeroed page records
# damage only (`_walk_note_damage`), no skip, so the reader sees nothing grow. The banner's USN state (forefst main) runs
# in the tool's own process through a runner that fills the list before main().

_CAP = 500
_EXTRA_REGISTERS = ("_SKIP_NOTES", "_SKIP_EXPECTED", "_SKIP_FINDING", "_FINDINGS", "_WALK_DAMAGE",
                    "_WALK_DAMAGE_REPORTED", "_DEFERRALS", "_OBJ_ROOT_REF", "_OBJ_ROOT_VERIFIED", "_OBJ_ROOT_LCNS",
                    "_ALL_TRS", "_OT_MAX_LSN", "_CHKP_STALE", "_SUPB_FELL_BACK")


def _fresh(monkeypatch):
    """A fresh, empty value for every list/dict/set register the exit rule reads (from its own code) and for the
    skip and damage machinery; monkeypatch restores the module afterwards."""
    for name in sorted(set(F.rc_escalate.__code__.co_names) | set(_EXTRA_REGISTERS)):
        cur = vars(F).get(name)
        if isinstance(cur, (list, dict, set)):
            monkeypatch.setattr(F, name, type(cur)())


def _fill_to_cap():
    F._WALK_DAMAGE.extend(("red-prefill", "entry %d" % i) for i in range(_CAP))
    F._walk_note_damage("red-prefill", "one more")
    _fx(len(F._WALK_DAMAGE) == _CAP, "the damage list is not at its cap (%d entries)" % len(F._WALK_DAMAGE))


def _boot(v):
    return F.bootstrap(v.path, v.geo.ps)


_N336_ROOT = 11          # Integrity State: translated, not read by bootstrap


def zero_root_page(v, idx):
    f, ps, cs, tr, roots, _om, _a, _b, _c = _boot(v)
    try:
        plcn = tr.tr(roots[idx][0])
    finally:
        f.close()
    _fx(v.read(ps + plcn * CS, 4) == b"MSB+", "root %d's page is not an MSB+ page" % idx)
    v.zero(ps + plcn * CS, 0x4000)


def _root_counts(v, monkeypatch, fill):
    _fresh(monkeypatch)
    f, ps, cs, tr, roots, _om, _a, _b, _c = _boot(v)
    try:
        if fill:
            _fill_to_cap()
        return F.root_table_counts(f, ps, cs, tr, roots, "red")
    finally:
        f.close()


def test_n336_root_table_counts_past_the_cap(vol, monkeypatch):
    zero_root_page(vol, _N336_ROOT)
    counts, unreadable = _root_counts(vol, monkeypatch, fill=True)
    assert _N336_ROOT in unreadable, "root %d (zeroed) must be unreadable past the cap: counts %r" \
        % (_N336_ROOT, counts.get(_N336_ROOT))


def test_n336_control_root_table_counts(vol, monkeypatch):
    """Under the cap the zeroed root is unreadable; on the undamaged volume the full list alone marks nothing."""
    counts0, unread0 = _root_counts(vol, monkeypatch, fill=True)
    assert not unread0 and counts0.get(_N336_ROOT) is not None, (counts0, unread0)
    zero_root_page(vol, _N336_ROOT)
    _counts, unread = _root_counts(vol, monkeypatch, fill=False)
    assert unread == {_N336_ROOT}, unread


def _fs_meta(v, monkeypatch, fill):
    _fresh(monkeypatch)
    f, ps, cs, tr, _roots, obj_map, _a, _b, _c = _boot(v)
    try:
        if fill:
            _fill_to_cap()
        return F.fs_metadata_read(f, ps, cs, tr, obj_map, "red")
    finally:
        f.close()


@IMAGE_ONLY
def test_n336_fs_metadata_read_past_the_cap(vol, monkeypatch):
    plant_unreadable_520(vol)
    fm = _fs_meta(vol, monkeypatch, fill=True)
    assert fm["usn_journal"] is None, "the 0x520 table was not read: usn_journal must be None, got %r" % fm


@IMAGE_ONLY
def test_n336_control_fs_metadata_read(vol, monkeypatch):
    fm0 = _fs_meta(vol, monkeypatch, fill=True)
    assert fm0["usn_journal"] is False and fm0["rows"] > 0, fm0
    plant_unreadable_520(vol)
    assert _fs_meta(vol, monkeypatch, fill=False)["usn_journal"] is None


def _locate(v, monkeypatch, fill):
    _fresh(monkeypatch)
    f, ps, cs, tr, _roots, obj_map, _a, _b, _c = _boot(v)
    try:
        if fill:
            _fill_to_cap()
        return F.locate_change_journal(f, ps, cs, tr, obj_map), list(F._SKIP_FINDING)
    finally:
        f.close()


@IMAGE_ONLY
def test_n336_locate_change_journal_past_the_cap(vol, monkeypatch):
    plant_unreadable_520(vol)
    _res, skips = _locate(vol, monkeypatch, fill=True)
    assert "locate_change_journal" in skips, "the unread directory must be recorded: skips %r" % skips


@IMAGE_ONLY
def test_n336_control_locate_change_journal(vol, monkeypatch):
    _res0, skips0 = _locate(vol, monkeypatch, fill=True)
    assert "locate_change_journal" not in skips0, skips0
    plant_unreadable_520(vol)
    _res, skips = _locate(vol, monkeypatch, fill=False)
    assert "locate_change_journal" in skips, skips


# The runner: forefst imported as a module (the tool's own code), its registers or `walk_bplus` patched, then the CLI.
# forefst runs through `forefst.main()` + `rc_escalate` (what its __main__ does; runpy would execute a SECOND copy of
# the module that the patch does not reach); refsanalysis through runpy (it imports the patched module).
_RUNNER = r'''
import os, sys, runpy
repo, tool = sys.argv[1], sys.argv[2]
sys.path.insert(0, repo)
import forefst
_fill = int(os.environ.get("D27_PREFILL", "0"))
if _fill:
    forefst._WALK_DAMAGE.extend(("red-prefill", "entry %d" % i) for i in range(_fill))
for _i in range(int(os.environ.get("D27_RECORD", "0"))):      # section 12: notes RECORDED by the tool's own function
    forefst._walk_note_damage("red-recorded", "entry %d" % _i)
_t = os.environ.get("D27_FAIL_VLCNS", "")
target = [int(x, 16) for x in _t.split(",")] if _t else None
_orig = forefst.walk_bplus
def _walk(f, ps, cs, tr, vlcns, *a, **k):
    if target is not None and list(vlcns) == target:
        open(os.environ["D27_MARK"], "a").write("fired\n")
        raise OSError(5, "planted read failure (decision-27 step)")
    return _orig(f, ps, cs, tr, vlcns, *a, **k)
forefst.walk_bplus = _walk
sys.argv = [tool] + sys.argv[3:]
if os.path.basename(tool).startswith("forefst"):
    try:
        _rc = forefst.main()
        sys.exit(forefst.rc_escalate(0 if _rc is None else _rc))
    except SystemExit as _se:
        sys.exit(forefst.rc_escalate(0 if _se.code is None else _se.code))
else:
    runpy.run_path(tool, run_name="__main__")
'''


def _runner(v, tmp_path, tool, args, prefill=0, fail_vlcns=None, record=0):
    """(rc, out, fired)."""
    runner, mark = str(tmp_path / "d27runner.py"), str(tmp_path / "d27runner.mark")
    with open(runner, "w") as fh:
        fh.write(_RUNNER)
    if os.path.exists(mark):
        os.unlink(mark)
    env = dict(os.environ, D27_PREFILL=str(prefill), D27_MARK=mark, D27_RECORD=str(record),
               D27_FAIL_VLCNS=",".join("%x" % x for x in fail_vlcns) if fail_vlcns else "")
    rc, out = _run(runner, os.path.dirname(tool), tool, v.path, *args, cwd=str(tmp_path), env=env, cli=v.geo.cli)
    return rc, out, os.path.exists(mark)


def _banner_usn(out):
    b = [ln for ln in out.splitlines() if re.match(r"\[forefst\] ReFS \d+\.\d+ \| \d+ objects", ln)]
    _fx(len(b) == 1, "one banner line expected: %r" % b)
    return b[0]


@IMAGE_ONLY
def test_n336_banner_usn_state_past_the_cap(vol, tmp_path):
    plant_unreadable_520(vol)
    rc, out, _f = _runner(vol, tmp_path, FOREFST, ["fastsummary"], prefill=_CAP)
    assert "USN: unknown" in _banner_usn(out), _banner_usn(out) + _ctx(vol, rc, out)


@IMAGE_ONLY
def test_n336_control_banner_usn_state(vol, tmp_path):
    rc0, out0, _f = _runner(vol, tmp_path, FOREFST, ["fastsummary"], prefill=_CAP)
    assert "USN: unknown" not in _banner_usn(out0), _banner_usn(out0)
    plant_unreadable_520(vol)
    rc, out, _f = _runner(vol, tmp_path, FOREFST, ["fastsummary"])
    assert "USN: unknown" in _banner_usn(out), _banner_usn(out) + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 10. N337 -- `help supb` / `help chkp`: the bare commands' exit 2
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _exit2_lines(out):
    """Help lines that state exit code 2, other than the --verify option's own line."""
    return [ln for ln in out.splitlines() if re.search(r"(?i)\bexit(s|ing)?\b[^.;]{0,20}?\b2\b", ln)
            and not ln.strip().startswith("--verify")]


@pytest.mark.parametrize("cmd", ["supb", "chkp"])
def test_n337_help_states_the_bare_commands_exit_2(cmd, tmp_path):
    out = _help(cmd, tmp_path)
    lines = _exit2_lines(out)
    assert [ln for ln in lines if re.search(r"(?i)checkpoint", ln) and _FAIL.search(ln)], \
        "help %s: exit 2 when a checkpoint copy is said to have FAILED: %r" % (cmd, lines)
    assert [ln for ln in lines if re.search(r"(?i)\broots?\b", ln)], \
        "help %s: exit 2 when a root 0xC/7/8 of the copy in use does not verify: %r" % (cmd, lines)


def test_n337_control_the_verify_lines_state_their_exit_code(tmp_path):
    for cmd in ("supb", "chkp"):
        out = _help(cmd, tmp_path)
        assert [ln for ln in out.splitlines() if ln.strip().startswith("--verify") and re.search(r"exits 2", ln)], out


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 11. N338 -- Security descs / Reparse index / Trash table printed as 0 over a walk that raised or recorded damage
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A3's convention (root_table_counts, review 1 F10): text "unreadable"; JSON null when the walk raised, the partial
# count when it recorded damage, and the entry named in a companion list. The RED's JSON reader accepts either form
# for either cause (null, or the key named in a top-level list), so it does not fix the companion key's name.
# win11refsmini: 12 security descriptors, 0 reparse index entries, 0 trash entries -- a printed 0 is the truth on the
# undamaged volume and must become "unreadable" over the damaged table.

_N338_TABLES = {"security": (0x530, "Security descs", "security_descriptors"),
                "reparse": (0x540, "Reparse index", "reparse_index_entries"),
                "trash": (0xD, "Trash table", "trash_table_entries")}
_N338_TOOLS = {"fd-summary": (FOREFST, "summary"), "fd-fastsummary": (FOREFST, "fastsummary"),
               "ra-summary-plus": (REFSANALYSIS, "summary++")}


def _oid_root(v, oid):
    f, ps, cs, tr, _roots, obj_map, _a, _b, _c = _boot(v)
    try:
        _fx(oid in obj_map, "no OID 0x%x on this volume" % oid)
        return list(obj_map[oid]), tr.tr(obj_map[oid][0])
    finally:
        f.close()


def _label_value(out, label):
    m = re.findall(r"(?m)^\s*%s:\s+(.*)$" % re.escape(label), out)
    _fx(len(m) == 1, "one %r line expected: %r" % (label, m))
    return m[0].strip()


def _json_marks_unreadable(j, key):
    # acceptance 1.14.0 (K21): CountsUnreadable names the fields by their output names
    name = F.out_key(key, F._SUMMARY_KEYS)
    return (key in j and j[key] is None) or any(isinstance(v, list) and (key in v or name in v) for v in j.values())


@IMAGE_ONLY
@pytest.mark.parametrize("tool", sorted(_N338_TOOLS))
@pytest.mark.parametrize("how", ["zeroed", "raised"])
@pytest.mark.parametrize("table", sorted(_N338_TABLES))
def test_n338_the_count_of_a_table_that_was_not_read_is_unreadable(vol, table, how, tool, tmp_path):
    oid, label, key = _N338_TABLES[table]
    path, cmd = _N338_TOOLS[tool]
    vlcns, plcn = _oid_root(vol, oid)
    # the undamaged volume: a count, not marked (the oracle cannot pass vacuously)
    rc0, out0, _f0 = _runner(vol, tmp_path, path, [cmd])
    _fx(rc0 == 0 and re.match(r"^\d+\b", _label_value(out0, label)), "undamaged %s: %r" % (label, _label_value(
        out0, label)) + _ctx(vol, rc0, out0))
    _rcj0, outj0, _fj0 = _runner(vol, tmp_path, path, [cmd, "--json"])
    j0 = _json_text(outj0, cmd + " --json")
    _fx(isinstance(j0.get(key), int) and not _json_marks_unreadable(j0, key), "undamaged JSON %s=%r" % (key, j0.get(key)))
    fail = None
    if how == "zeroed":
        _fx(vol.read(vol.geo.ps + plcn * CS, 4) == b"MSB+", "OID 0x%x's root page is not an MSB+ page" % oid)
        vol.zero(vol.geo.ps + plcn * CS, 0x4000)
    else:
        fail = vlcns
    rc, out, fired = _runner(vol, tmp_path, path, [cmd], fail_vlcns=fail)
    _fx(how == "zeroed" or fired, "the planted walk failure did not fire")
    _keep(rc == 2, "the run exits 2 (the walk recorded a skip or damage)" + _ctx(vol, rc, out))
    val = _label_value(out, label)
    assert "unreadable" in val.lower() and not re.match(r"^\d", val), "%s: %r" % (label, val) + _ctx(vol, rc, out)
    _rcj, outj, _fj = _runner(vol, tmp_path, path, [cmd, "--json"], fail_vlcns=fail)
    j = _json_text(outj, cmd + " --json")
    assert _json_marks_unreadable(j, key), "JSON %s=%r is presented as a count" % (key, j.get(key))


def test_n338_json_reader_accepts_both_forms():
    assert _json_marks_unreadable({"a": None}, "a") and _json_marks_unreadable({"a": 3, "x": ["a"]}, "a")
    assert not _json_marks_unreadable({"a": 0, "x": ["b"]}, "a") and not _json_marks_unreadable({"a": 0}, "a")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 13. N341 (placed by the lead, rule 8) -- a +0x10/+0x60 clock divergence of the checkpoint copy in use
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# forefst: a `view` condition -- every bootstrapping command says "checkpoint copy at LCN 0x..: clock mismatch, page
# header +0x10 = .. vs selection clock +0x60 = .." and exits 2. refsanalysis `supb`, `chkp`, `containers` select the
# checkpoint themselves and (measured before this sub-step, both volumes) say nothing and exit 0 (`chkp` prints both
# clocks in its field table, with no word). The stale and no-copy-passes conditions those commands already say in their
# own words (N207); the control below holds them to saying it once.

_DIVERGE_TO = CLOCK_NEW + 5        # the in-use copy's page-header clock (+0x10); its selection clock (+0x60) stays 64


def plant_clock_divergence(v):
    """The copy in use (lo): +0x10 = 69 while +0x60 stays 64, re-sealed (Vol.reseal: fd._recompute_self_checksum,
    cross-checked with this module's own CRC32-C) -- a clock divergence, not a checksum failure. lo stays the copy in
    use (+0x60: 64 > 63)."""
    g = v.geo

    def edit(b):
        struct.pack_into("<Q", b, 0x10, _DIVERGE_TO)
    v.reseal(g.lo, edit, CHKP_DESC)
    _fx(v.clocks(g.lo) == (_DIVERGE_TO, CLOCK_NEW) and v.clocks(g.hi) == (CLOCK_OLD, CLOCK_OLD),
        "the clocks are not 69/64 and 63/63: %r %r" % (v.clocks(g.lo), v.clocks(g.hi)))
    _fx(v.verifies(g.lo) is True and v.verifies(g.hi) is True, "a copy fails its self-checksum after the plant")
    return g.lo


def _clock_said(out, lcn):
    """forefst's statement of the divergence: the copy's LCN, +0x10 with 69 and +0x60 with 64."""
    return [s for s in _statements(out) if _lcn_re(lcn).search(s)
            and re.search(r"\+0x10\b[^;]{0,40}?\b%d\b" % _DIVERGE_TO, s)
            and re.search(r"\+0x60\b[^;]{0,40}?\b%d\b" % CLOCK_NEW, s)]


@pytest.mark.parametrize("cmd", sorted(_N332))
def test_n341_refsanalysis_says_the_clock_divergence_of_the_copy_in_use_and_exits_2(vol, cmd):
    lcn = plant_clock_divergence(vol)
    rc, out = vol.run(REFSANALYSIS, *_N332[cmd])
    assert _clock_said(out, lcn), "refsanalysis %s must say the copy in use (LCN 0x%x) has +0x10 = %d vs +0x60 = %d" \
        % (cmd, lcn, _DIVERGE_TO, CLOCK_NEW) + _ctx(vol, rc, out)
    assert rc == 2, "refsanalysis %s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


def test_n341_control_forefst_already_says_it(vol):
    lcn = plant_clock_divergence(vol)
    for cmd in ("files", "summary"):
        rc, out = vol.run(FOREFST, cmd)
        assert rc == 2 and _clock_said(out, lcn), cmd + _ctx(vol, rc, out)


def test_n341_control_the_undamaged_volume_has_no_divergence_statement(vol):
    for cmd, args in sorted(_N332.items()):
        rc, out = vol.run(REFSANALYSIS, *args)
        assert not [s for s in _statements(out) if re.search(r"(?i)clock mismatch|\+0x10\b.*\+0x60\b", s)], \
            cmd + _ctx(vol, rc, out)


def _failed_said(out, lcn):
    """Statements naming the copy with a failure word and "self-checksum" -- how often a failed copy is said."""
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and _FAIL.search(s)
            and re.search(r"(?i)self-checksum", s)]


@pytest.mark.parametrize("cmd", ["chkp", "containers", "supb"])
def test_n341_control_a_failed_newest_copy_is_said_once_in_the_commands_own_words(vol, cmd):
    """N207: the newest copy failed (an older one is read) -- each command says it ONCE and exits 2. A fix that adds
    forefst's stale-view sentence beside the command's own note says it twice."""
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(REFSANALYSIS, cmd)
    said = _failed_said(out, vol.geo.lo)
    assert rc == 2 and len(said) == 1, "said %d times: %r" % (len(said), said) + _ctx(vol, rc, out)


def test_n341_supb_raw_states_a_failed_newest_copy_and_exits_2(vol):
    """`supb --raw` prints the hex dump only, so it is the one layout of these commands with no word of its own for a
    failed newest copy: forefst's `view` sentence is said there (once), and the run exits 2."""
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(REFSANALYSIS, "supb", "--raw")
    said = _failed_said(out, vol.geo.lo)
    assert len(said) == 1, "the failed newest copy must be said once: %r" % said + _ctx(vol, rc, out)
    assert rc == 2, "rc=%d" % rc + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", ["supb", "chkp"])
def test_n341_help_states_the_clock_divergence_exit_2(cmd, tmp_path):
    """N337's class: the bare commands' help enumerates their exit-2 conditions, so it names this one too."""
    lines = _exit2_lines(_help(cmd, tmp_path))
    assert [ln for ln in lines if re.search(r"\+0x10\b", ln) and re.search(r"\+0x60\b", ln)], \
        "help %s: exit 2 when a checkpoint copy's +0x10 and +0x60 clocks differ: %r" % (cmd, lines)


def test_n341_matcher():
    s = ("[forefst] WARNING: checkpoint copy at LCN 0x48: clock mismatch, page header +0x10 = %d vs selection clock "
         "+0x60 = %d (the driver compares +0x60; ...)" % (_DIVERGE_TO, CLOCK_NEW))
    assert _clock_said(s, 0x48) and not _clock_said(s, 0x88)
    assert not _clock_said("Virtual clock        0x10    45 00 00 00 00 00 00 00   %d" % _DIVERGE_TO, 0x48)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 14. N336 widened (placed by the lead) -- the printed number of unreadable pages past the 500-entry cap
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `_walk_damage_summary` ("N metadata page(s) could not be read") and `files`' two lines for a written file
# ("LISTING FAILED -- 0 entries written to ...: N ...", "Wrote K entries to ... -- INCOMPLETE: N ...") printed the length
# of the damage list, which stops at 500 entries. In-process: N zero pages walked by the tool's own `_walk`; CLI: the
# runner records N notes with the tool's own `_walk_note_damage` before main(), on an undamaged volume.
# Group 3 (N368, the lead's settlement of 2026-10-09; a sanctioned fixture change): a count of pages is a count of
# DISTINCT pages, so the in-process plant walks N DISTINCT pages (N head clusters), not one page N times -- the purpose,
# that the printed number does not stop at 500, is kept. The CLI runner's notes name no page, so each is one page.

_N336W = 650
_SUMMARY_N = re.compile(r"WARNING: (\d+) metadata page\(s\) could not be read")
_FILES_N = re.compile(r"(?:LISTING FAILED .{0,20}0 entries written to .*?: |Wrote \d+ entr(?:y|ies) to .*? INCOMPLETE: )(\d+) "
                      r"metadata page\(s\)/table\(s\) could not be read")


def _walk_zero_pages(monkeypatch, capsys, tmp_path, n):
    """Walks of `n` DISTINCT all-zero pages (N368: a page met twice counts once) whose clusters hold data in the file
    (not an image hole: the file holds 0x01 bytes; the page handed to the walk is zeros), so each walk records one
    "zeroed-page" note naming its own head cluster; returns the summary's printed numbers."""
    _fresh(monkeypatch)
    p = str(tmp_path / "zeros.raw")
    with open(p, "wb") as fh:
        fh.write(b"\x01" * ((n + 8) * 0x1000))
    capsys.readouterr()
    with open(p, "rb") as fh:
        for i in range(n):
            # page i: slots 4+i .. 7+i, head cluster 4+i (a slot 0 ends a page reference's slot list, so it would not
            # be checked for a hole)
            _fx(F._walk(b"\0" * 0x4000, fh, 0, 0x1000, None, 3, None, [4 + i, 5 + i, 6 + i, 7 + i]) == [],
                "a zero page gave rows")
    kinds = {k for k, _d in F._WALK_DAMAGE}
    _fx(kinds == {"zeroed-page"}, "recorded kinds %r" % kinds)
    F._walk_damage_summary()
    return [int(x) for x in _SUMMARY_N.findall(capsys.readouterr().err)]


def test_n336w_the_damage_summary_prints_the_number_of_pages_recorded_past_the_cap(monkeypatch, capsys, tmp_path):
    said = _walk_zero_pages(monkeypatch, capsys, tmp_path, _N336W)
    _fx(len(said) == 1, "one summary line expected: %r" % said)
    assert said == [_N336W], "the summary must print %d (printed %r)" % (_N336W, said)


def test_n336w_control_under_the_cap_the_summary_prints_the_number(monkeypatch, capsys, tmp_path):
    assert _walk_zero_pages(monkeypatch, capsys, tmp_path, 7) == [7]


def _files_to_file(v, tmp_path, record):
    out_csv = str(tmp_path / "listing.csv")
    rc, out, _f = _runner(v, tmp_path, FOREFST, ["files", "--csv", out_csv], record=record)
    if os.path.exists(out_csv):
        os.unlink(out_csv)
    return rc, out, [int(x) for x in _SUMMARY_N.findall(out)], [int(x) for x in _FILES_N.findall(out)]


def test_n336w_files_to_a_file_prints_the_number_recorded_past_the_cap(vol, tmp_path):
    rc, out, summ, line = _files_to_file(vol, tmp_path, _N336W)
    _fx(len(summ) == 1 and len(line) == 1, "one summary line and one files line expected: %r %r" % (summ, line)
        + _ctx(vol, rc, out))
    _keep(rc == 2, "recorded damage exits 2" + _ctx(vol, rc, out))
    assert line == [_N336W], "files' line must print %d (printed %r)" % (_N336W, line) + _ctx(vol, rc, out)
    assert summ == [_N336W], "the summary must print %d (printed %r)" % (_N336W, summ) + _ctx(vol, rc, out)


def test_n336w_control_files_to_a_file_under_the_cap(vol, tmp_path):
    rc, out, summ, line = _files_to_file(vol, tmp_path, 7)
    assert rc == 2 and summ == [7] and line == [7], (summ, line) + (_ctx(vol, rc, out),)

