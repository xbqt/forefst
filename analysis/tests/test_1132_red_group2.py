"""1.13.2 RED cases still missing before fix group 2 (Bootstrap) starts: the 13 items of the group-2 brief.

Brief: `analysis/reports/v1.13.2/red/GROUP2_RED_BRIEF.md` (items 1-12, and item 13 = N215, added 2026-10-01).
Plan: `PLAN_1.13.2.md` fifth revision, group 2 row; rows A1-A4, B1 (section 2); decision 20 (section 7) and
`NEXT_STEPS_2026-10-01.md` (the maintainer's answers 3, 6, 7, 8). Sources per item: `red/RED_BATCH1_SUMMARY.md`
(M-1..M-5, B1's MISSING M1), `D14/W1W2_DEFECTS_DEDUP.md` C10 and C25, `RUNNING_LOG.md` N139, N205, N206, N207, N215,
`F1_CHECKPOINT_TIE_READING.md:330-334, :461-473` (the 26100 roots rule), `fixes/REVIEW_A11_correctness.md` s.6-7
(D2, D4). Report, with every node's observed failure: `analysis/reports/v1.13.2/red/RED_group2.md`.

The maintainer's bar: every RED fails on the CURRENT dev tools (forefst b7765bab, refsanalysis c7fb9e8d = 1.13.1 +
A11 + K7) BECAUSE of its defect, at its plain assert, and is independently confirmed.

What each RED asserts
---------------------
 1 A1 M-1   a backup superblock that fails its self-checksum: `summary` WARNS (the primary-flip RED's matcher). The
            existing `test_a1_a_backup_superblock_that_fails_its_checksum_is_named_and_exits_2[summary]` already
            asks for the copy named by role and LCN and exit 2; only the warning was missing.
 2 A2 M-2   a failed SECONDARY checkpoint (untied, and on both tie orientations) is never labelled "valid", and each
            line listing it says it failed (`integrity`: "valid"; `summary`: "signature OK").
 3 A3 M-3   exit 2 on a recorded skip (battery A3_oid_root_zero) on the refsanalysis commands that do not exit 2 yet:
            `details <path>` and `upcase` (exit 1, "not found"). The other table walkers already exit 2 since A11.
 4 B1 M1    newest copy failed: when `deleted` prints its checkpoint comparison, Current VC = 63 (in use) and
            Previous VC = 64.
 5 N139 M-5 no copy passes its self-checksum: `extract`, `search`, refsanalysis `files` and `objects` say so.
 6 C10      a checkpoint whose self-checksum cannot be computed (`cksum_ok is None`) is said to be unverified.
 7 C25      bare `refsanalysis supb` reads a backup superblock when the primary is zeroed (battery A5).
 8 A4 M-4   `boot --verify` prints one row per boot-sector copy with its own status; a flipped BACKUP is named, exit 2.
 9 N205     a copy that passes its self-checksum while its root 0xC, 7 or 8 does not verify is read, and the output
            says that the 26100 driver would reject it and which root fails.
10 V-a      no RED: measured on the current tools, the decision already holds. Controls keep it.
11 N206     the failed newest copy is never "the copy the driver would use"; the output says the driver uses the
            older passing copy, or refuses to mount when no copy passes.
12 N207     refsanalysis `supb`, `chkp`, `containers` without --verify that say a copy FAILED exit 2.
13 N215     refsanalysis `summary` and `containers` read the compression policy whatever the flags word at
            Container-Table root +0xA0 holds (0x07 on v3.4, 0x0F on v3.7+).

Exit codes (items 9 and 12; item 7's exit code is N207's rule): the exit-code assertion is in its own function, named
`..._exit_code_...`. The maintainer decided exit 2 for N205, N207 and N240 on 2026-10-01 (PLAN_1.13.2 decision 21);
the split is kept so that a later change of rule flips only those nodes.

Volumes
-------
* ``[synthetic]`` / ``[image]`` -- the `vol` fixture of `test_1132_red_a_bootstrap.py` (imported by name and
  re-exported, never `import *`): the 1 MiB synthetic ReFS 3.14 volume, and a hole-preserving scratch copy of battery
  base A (win11refsmini.raw, ~13 MB allocated) under ``$FOREFST_RED_SCRATCH``, deleted by exact path after each
  test. Its damage recipes (`damage_chkp`, `damage_supb`, `make_tie`, `zero_ot_root`) and pins are reused. A node
  that needs a real file or a real Container-Table root layout overrides the parameter to ``["image"]``.
* Read-only corpus images (item 13): win10refsmini.raw (v3.4) and win11refsmini.raw (v3.14), never written.
* ``pytest -k "not image"`` runs the synthetic half and the matcher self-test only.

How a RED can fail only because of its defect (the convention of test_1132_red_a_bootstrap.py)
-----------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``; only a plain ``assert`` states the defect. A fixture
  that is not what the case needs raises ``RedFixtureError`` (``_fx``); a property the current tool already has and
  the fix must keep raises ``KeptPropertyBroken`` (``_keep``). Neither is an AssertionError.
* New plants check their own evidence before and after: the N205 plant changes ONE byte of the root's digest in the
  newest copy's page reference, re-seals that copy with `_recompute_self_checksum` (cross-checked against the a_bootstrap
  module's own CRC32-C by `Vol.reseal`), and verifies with `refs_crc64` that the root page no longer matches that
  copy's digest while it still matches the other copy's. The C10 plant edits a byte inside the self-descriptor's
  zeroed window, so the stored CRC32-C still equals the module's own CRC32-C of the block. The N215 plant rewrites
  the policy record of the Container-Table root page and re-seals both copies' digest of it.
* Every RED has a control that passes now and differs from it only in the defect's trigger.
"""
import csv
import re
import struct
import subprocess
import sys
from types import SimpleNamespace

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402

# The a_bootstrap volume machinery, imported by name (never `import *`, which would re-collect its tests here).
import test_1132_red_a_bootstrap as _AB                   # noqa: E402
from test_1132_red_a_bootstrap import (                  # noqa: E402
    RedFixtureError, _fx, _keep, _ctx, damage_chkp, damage_supb, make_tie, zero_ot_root, _root_list,
    _own_digest, _FAIL, _lcn_re, _lines, _named_failed, _chkp_rows, _guid,
    _says_no_checkpoint_passed, FOREFST, REFSANALYSIS, CS, CHKP_DESC, ZERO_WINDOW, GUID, CLOCK_NEW, CLOCK_OLD)
from test_1132_red_b_items import _cmp_section           # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

vol = _AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module

IMAGE_ONLY = pytest.mark.parametrize("vol", ["image"], indirect=True)
PENDING = "exit 2 decided by the maintainer on 2026-10-01 (PLAN_1.13.2 decision 21)"


# ─── reading the output ───────────────────────────────────────────────────────────────────────────────────────

def _statements(text):
    """Each output line joined with its continuation lines: lines indented deeper than the first, not starting with
    '[', at most 4, never after a rule line (---/===) or a line ending in ':' (a section header)."""
    out, cur, ind, n = [], None, 0, 0
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            if cur is not None:
                out.append(cur)
            cur = None
            continue
        i = len(ln) - len(ln.lstrip())
        if cur is not None and i > ind and not s.startswith("[") and n < 4 \
                and not re.match(r"^[-=─]{6,}", cur) and not cur.endswith(":"):
            cur += " " + s
            n += 1
        else:
            if cur is not None:
                out.append(cur)
            cur, ind, n = s, i, 0
    if cur is not None:
        out.append(cur)
    return out


def _addr_re(*values):
    """Any of these values as a whole hex token (an LCN or a byte offset), case-insensitive."""
    return re.compile("|".join(_lcn_re(x).pattern.replace("(?i)", "") for x in values), re.I)


def _addr_of(ps, lcn):
    """A block's LCN, its partition-relative byte offset or its absolute byte offset."""
    return _addr_re(lcn, lcn * CS, ps + lcn * CS)


def _supb_addr(v, lcn):
    return _addr_of(v.geo.ps, lcn)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 1. A1 M-1 -- `summary` warns about a backup superblock that fails its self-checksum
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_SUPB_WARN = re.compile(r"(?im)^.*\bwarn.*\b(superblock|SUPB)\b")   # the primary-flip RED's matcher, unchanged


def _supb_warnings(out, ps, lcn):
    """Warning statements (`_SUPB_WARN`) that name this superblock copy by LCN or offset (critic C1)."""
    return [s for s in _statements(out) if _SUPB_WARN.search(s) and _addr_of(ps, lcn).search(s)]


def test_a1_m1_summary_warns_about_a_backup_superblock_that_fails_its_checksum(vol):
    lcn = damage_supb(vol, "backup")
    rc, out = vol.run(FOREFST, "summary")
    _keep(_guid(out) == GUID, "the primary is intact: its GUID is printed" + _ctx(vol, rc, out))
    assert _supb_warnings(out, vol.geo.ps, lcn), \
        "summary must warn about the backup superblock at LCN 0x%x that fails its self-checksum" % lcn \
        + _ctx(vol, rc, out)


def test_a1_m1_control_summary_prints_no_superblock_warning_on_the_undamaged_volume(vol):
    """A warning printed on every run cannot pass the RED above."""
    rc, out = vol.run(FOREFST, "summary")
    assert rc == 0 and not _SUPB_WARN.search(out), _ctx(vol, rc, out)


def test_a1_m1_control_a_zeroed_primary_superblock_already_draws_the_warning(vol):
    """The matcher hits a real superblock warning of the current tool (battery A5 shape)."""
    vol.zero(vol.at(vol.geo.supb), CS)
    rc, out = vol.run(FOREFST, "summary")
    assert rc == 2 and _SUPB_WARN.search(out), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 2. A2 M-2 -- a failed SECONDARY checkpoint is never labelled "valid" (on the tie and untied)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# After the critic (C2): also the two tie shapes whose LOWER-LCN copy failed (measured "valid" today; the label code is
# the same line, fd:15309), and no copy passing (both rows "valid" in integrity).

_VALID_LABEL = re.compile(r"(?i)(?<!not )\bvalid\b")             # "invalid" and "not valid" do not match
_M2_CASES = {"untied": (None, ("hi",)),                           # case: (tie slot0_higher, the copies damaged)
             "tie-slot0-lower": (False, ("hi",)), "tie-slot0-higher": (True, ("hi",)),
             "tie-slot0-lower_lower-lcn-failed": (False, ("lo",)),
             "tie-slot0-higher_lower-lcn-failed": (True, ("lo",)),
             "no-copy-passes": (None, ("lo", "hi"))}


def _fail_copies(v, case):
    """Damage the copies the case names. Untied, the failed older copy is the secondary; on a tie (F1 s.5, either slot
    order) the driver keeps the copy that passes, so the failed one -- lower or higher LCN -- is the secondary too;
    with no copy passing both rows fail. Returns the failed LCNs."""
    if case not in _M2_CASES:
        raise RedFixtureError("unknown case %s" % case)
    tie, which = _M2_CASES[case]
    if tie is not None:
        make_tie(v, slot0_higher=tie)
    failed = [getattr(v.geo, w) for w in which]
    for lcn in failed:
        damage_chkp(v, lcn)
    return failed


def _own_lines(out, lcn, v):
    """Lines that name this copy and not the other one."""
    other = v.geo.hi if lcn == v.geo.lo else v.geo.lo
    return [ln for ln in _lines(out, lcn) if not _lcn_re(other).search(ln)]


def _valid_labels(out, failed, v):
    """Lines that name a failed copy (and not the other copy) and call something on them "valid"."""
    return [ln for lcn in failed for ln in _own_lines(out, lcn, v) if _VALID_LABEL.search(ln)]


@pytest.mark.parametrize("cmd", [("integrity",), ("summary",)], ids=["integrity", "summary"])
@pytest.mark.parametrize("case", list(_M2_CASES))
def test_a2_m2_a_failed_checkpoint_copy_is_never_labelled_valid(vol, case, cmd):
    failed = _fail_copies(vol, case)
    rc, out = vol.run(FOREFST, *cmd)
    _keep(rc == 2, "a failed copy is already a finding (exit 2), untied and, since A11, tied" + _ctx(vol, rc, out))
    _keep(any(_named_failed(out, lcn, r"chkp|checkpoint") for lcn in failed),
          "a finding already names a failed copy" + _ctx(vol, rc, out))
    listing = [ln for lcn in failed for ln in _chkp_rows(out, lcn) if ln in _own_lines(out, lcn, vol)]
    _keep(all(_chkp_rows(out, lcn) for lcn in failed), "each failed copy is listed" + _ctx(vol, rc, out))
    assert not _valid_labels(out, failed, vol), "a failed copy is labelled valid: %r" % _valid_labels(
        out, failed, vol) + _ctx(vol, rc, out)
    assert all(_FAIL.search(ln) for ln in listing), "each line listing a failed copy must say it failed: %r" \
        % listing + _ctx(vol, rc, out)


def test_a2_m2_control_an_intact_secondary_is_listed_without_a_failure_word(vol):
    """The listing assertion discriminates: on the undamaged volume the secondary's line carries no failure word."""
    for cmd in (("integrity",), ("summary",)):
        rc, out = vol.run(FOREFST, *cmd)
        rows = _chkp_rows(out, vol.geo.hi)
        assert rc == 0 and rows and not [ln for ln in rows if _FAIL.search(ln)], cmd + (_ctx(vol, rc, out),)


@pytest.mark.parametrize("args", [("chkp",), ("chkp", "-v", "--verify")], ids=["chkp", "chkp-v-verify"])
def test_a2_m2_control_refsanalysis_chkp_never_labels_the_failed_secondary_valid(vol, args):
    """Measured for the brief: refsanalysis `chkp` shows `checkpoint_select`'s `newest` (ra:1729-1741), which here is
    the intact newer copy, so it prints no line labelling the failed older copy "valid" -- no RED is possible there;
    this keeps it so."""
    failed = _fail_copies(vol, "untied")
    rc, out = vol.run(REFSANALYSIS, *args)
    assert not _valid_labels(out, failed, vol), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 3. A3 M-3 -- exit 2 on a recorded skip, on every refsanalysis command that walks the tables (A3_oid_root_zero)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured on both volumes (current tools): summary, summary++, all, files, files -v, attributes, objects,
# objects --verify, schema, schema --verify, parentchild, parentchild --verify, allocators and oid30 record the skip
# and exit 2 (A11's rc_escalate). `details <path>` and `upcase` record it and exit 1 with "not found": rc_escalate
# raises only a success code. containers, chkp, supb and boot record no skip. (`chkp --verify` does read root 0's
# page signature: on this damage it prints "1 check(s) FAILED (18/19 passed)" with rc 0 -- not a recorded skip, so
# outside M-3; critic N-a.)
# The two REDs run on [image] only: the synthetic volume has no file and no Upcase table, so there a "not found"
# would not be caused by the damage (the control below proves it is on the image).
# After the critic (M1): an unconditional "not found -> exit 2" passed both REDs and every control. A genuine
# not-found -- nothing skipped -- exits 1 today and must keep doing so: each RED checks it on the undamaged image
# before the damage (`_keep`), and a control checks it on both volumes (`upcase` on the synthetic volume, which has
# no Upcase table, and `details` of a path that does not exist).

_A3_RED = {"details": ("details", "/test/ok.txt"), "upcase": ("upcase",)}
_A3_ALREADY = [("summary++",), ("all",), ("files", "-v"), ("schema",), ("schema", "--verify"), ("parentchild",),
               ("parentchild", "--verify"), ("objects", "--verify"), ("allocators",), ("oid30",)]
_SKIP_SAID = re.compile(r"(?i)could not be read|unreadable")
_NOT_FOUND = ("details", "/no/such/file")


@IMAGE_ONLY
@pytest.mark.parametrize("cmd", sorted(_A3_RED))
def test_a3_m3_refsanalysis_exits_2_on_a_recorded_skip(vol, cmd):
    rc0, out0 = vol.run(REFSANALYSIS, *_NOT_FOUND)
    _keep(rc0 == 1 and not _SKIP_SAID.search(out0), "a genuine not-found (nothing skipped) exits 1: exit 2 must come "
          "from the recorded skip, not from 'not found'" + _ctx(vol, rc0, out0))
    zero_ot_root(vol)                                     # battery A3_oid_root_zero
    rc, out = vol.run(REFSANALYSIS, *_A3_RED[cmd])
    _keep(_SKIP_SAID.search(out), "the skip is recorded and reported" + _ctx(vol, rc, out))
    assert rc == 2, "refsanalysis %s recorded a skip and must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@IMAGE_ONLY
def test_a3_m3_control_details_and_upcase_exit_0_on_the_undamaged_image(vol):
    """The exit 1 above is caused by the zeroed root: on the undamaged image both commands succeed."""
    for cmd in sorted(_A3_RED):
        rc, out = vol.run(REFSANALYSIS, *_A3_RED[cmd])
        assert rc == 0 and not _SKIP_SAID.search(out), cmd + _ctx(vol, rc, out)


def test_a3_m3_control_a_genuine_not_found_still_exits_1(vol):
    """Critic M1: on the undamaged volumes a not-found that skipped nothing exits 1 -- a fix that maps every
    "not found" to exit 2 fails here."""
    rc, out = vol.run(REFSANALYSIS, *_NOT_FOUND)
    assert rc == 1 and re.search(r"(?i)not found", out) and not _SKIP_SAID.search(out), _NOT_FOUND + (_ctx(vol, rc, out),)
    if vol.geo.kind == "synthetic":
        # sanctioned (the lead, 2026-10-22, C1 ST-1; Q10 / N427): a required structure missing from an Object Table read in full is a finding, exit 2
        rc, out = vol.run(REFSANALYSIS, "upcase")
        assert rc == 2 and re.search(r"(?i)Upcase Table.*neither copy is in the Object Table", out) \
            and not _SKIP_SAID.search(out), ("upcase",) + (_ctx(vol, rc, out),)


def test_a3_m3_control_the_other_table_walking_commands_already_exit_2(vol):
    """Measured: every other table-walking command records the skip and exits 2 (kept)."""
    zero_ot_root(vol)
    bad = []
    for args in _A3_ALREADY:
        rc, out = vol.run(REFSANALYSIS, *args)
        if rc != 2 or not _SKIP_SAID.search(out):
            bad.append((args, rc, out[-1500:]))
    assert not bad, bad


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 4. B1 M1 -- newest copy failed: `deleted` compares the copy in use (63) with the other copy (64)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# After the critic (S3): the RED passes on "no comparison printed" only when there is no comparison section AND no
# line starting with "Previous"; a printed comparison whose clocks cannot be read fails (it no longer goes green on a
# reword such as "vclock 64"), and the clock may be written VC, vclock or virtual clock.
# Re-check (R2): "never a copy compared with itself" is now observable on [image]. Both copies share all 13 roots, so
# before the newest copy is damaged it is re-sealed with its root-0 (Object Table) reference replaced by root 3's
# (Schema Table) -- `plant_previous_witness`. The tool never reads that copy (it fails its self-checksum), but a
# correct "Previous" is built from it and holds none of the volume's names, so the comparison lists them; a fix that
# only relabels the lines and still builds "Previous" from the copy in use prints "Same top-level files in both".
# The oracle is wording-free: some name of the volume (`files`, taken before the damage) appears in the comparison.
# On [synthetic] the tables are empty and both fixes print the same, so that node checks the labels only.

def _cmp_pair(text):
    """(Current VC, other copy's VC) from `deleted`'s comparison; None for a clock that cannot be read. N579: the other
    copy is labelled "Newer" when its clock is the greater (the newest copy failed), "Previous" otherwise."""
    def vc(which):
        m = re.search(r"(?im)^\s*%s\b[^\n]*?\b(?:VC|vclock|virtual clock)\s*[=:]?\s*(\d+)" % which, text or "")
        return int(m.group(1)) if m else None
    return vc("current"), vc("(?:previous|newer)")


def _cmp_block(out):
    """The comparison's own lines: the `── Checkpoint Comparison ──` section, or (renamed header) the lines from the
    first Current/Previous checkpoint line to the next blank or rule line."""
    sec = _cmp_section(out)
    if sec is not None:
        return sec
    lines, block = out.splitlines(), []
    for i, ln in enumerate(lines):
        if re.match(r"(?i)^\s*(current|previous|newer)\b.*checkpoint|^\s*(current|previous|newer) checkpoint", ln):
            for l2 in lines[i:]:
                if not l2.strip() or l2.strip().startswith("──"):
                    break
                block.append(l2)
            break
    return "\n".join(block)


def _volume_names(v):
    """The FileName column of `forefst files` (CSV) on the volume as it is: names of 4 characters or more."""
    rc, out = v.run(FOREFST, "files")
    _fx(rc == 0, "files failed on the undamaged volume" + _ctx(v, rc, out))
    rows = [r for r in csv.reader(out.splitlines()) if len(r) > 3 and re.match(r"0x[0-9a-f]+:0x[0-9a-f]+$", r[0])]
    names = {r[2] for r in rows if len(r[2]) >= 4}
    _fx(len(names) >= 3, "too few names on the volume: %r" % sorted(names))
    return names


def _names_listed(block, names):
    return sorted(n for n in names if re.search(r"(?<![\w.$-])%s(?![\w.-])" % re.escape(n), block or ""))


def plant_previous_witness(v):
    """R2: re-seal the NEWEST copy with its root-0 reference replaced by root 3's (the Schema Table), before it is
    damaged. Only the newest copy changes (`Vol.reseal` re-checks its self-checksum); the older copy, the one read,
    keeps the real Object Table."""
    g = v.geo
    new = v.block(g.lo)
    ro0, ro3, dlen = _root_ref_offset(new, 0), _root_ref_offset(new, 3), F.le32(new, 0x5C)
    _fx(_root_list(new)[0] != _root_list(new)[3], "roots 0 and 3 share a page")

    def edit(b):
        b[ro0:ro0 + dlen] = new[ro3:ro3 + dlen]
    v.reseal(g.lo, edit, CHKP_DESC)
    _fx(_root_list(v.block(g.lo))[0] == _root_list(new)[3], "witness: the reference was not copied")
    _fx(_root_list(v.block(g.hi))[0] == _root_list(new)[0], "witness: the older copy changed")


def _cmp_printed(out):
    """The comparison text, or None when `deleted` printed no comparison at all."""
    sec = _cmp_section(out)
    if sec is None and not re.search(r"(?im)^\s*(?:previous|newer)\b", out):
        return None
    return sec if sec is not None else out


def test_b1_m1_deleted_compares_the_copy_in_use_with_the_other_copy(vol):
    names = None
    if vol.geo.kind == "image":
        names = _volume_names(vol)
        plant_previous_witness(vol)
    damage_chkp(vol, vol.geo.lo)                          # battery A1_chkp_flip_newest
    rc, out = vol.run(FOREFST, "deleted")
    printed = _cmp_printed(out)
    if printed is None:
        return            # the brief's condition: only a PRINTED comparison is held to the rule
    cur, prev = _cmp_pair(printed)
    assert (cur, prev) == (CLOCK_OLD, CLOCK_NEW), (
        "Current VC=%r / Previous VC=%r: the copy in use has VC %d, the other copy %d"
        % (cur, prev, CLOCK_OLD, CLOCK_NEW)) + _ctx(vol, rc, out)
    if names is not None:
        assert _names_listed(_cmp_block(out), names), (
            "the comparison lists none of the volume's names although 'Previous' (the copy not in use) holds none of "
            "them: the copy in use was compared with itself:\n%s" % _cmp_block(out)) + _ctx(vol, rc, out)


@IMAGE_ONLY
def test_b1_m1_control_the_previous_witness_leaves_the_volume_view_unchanged(vol):
    """R2: the witness changes only the copy that is not read -- `files` lists the same names after the witness and
    the damage as before them (the volume is read from the older copy, which keeps the real Object Table)."""
    names = _volume_names(vol)
    plant_previous_witness(vol)
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(FOREFST, "files")
    rows = [r for r in csv.reader(out.splitlines()) if len(r) > 3 and re.match(r"0x[0-9a-f]+:0x[0-9a-f]+$", r[0])]
    assert {r[2] for r in rows if len(r[2]) >= 4} == names, _ctx(vol, rc, out)


@pytest.mark.parametrize("case", ["undamaged", "older-failed"])
def test_b1_m1_control_deleted_comparison_order_when_the_newest_copy_is_in_use(vol, case):
    """Where the copy in use is the newest (64), the current order is already Current 64 / Previous 63."""
    if case == "older-failed":
        damage_chkp(vol, vol.geo.hi)
    rc, out = vol.run(FOREFST, "deleted")
    assert _cmp_pair(_cmp_printed(out) or "") == (CLOCK_NEW, CLOCK_OLD), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 5. N139 M-5 -- no copy passes its self-checksum: every bootstrap-only command says so (D-3)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The existing D-3 RED covers forefst `files`, and its control shows `summary` already exits 2 on this damage.
# After the critic (M2): `_says_no_checkpoint_passed` (a_bootstrap, tightened there too) now needs the statement that
# NO copy passed, or every copy named as failed; a warning that only the newest copy failed no longer passes.

_M5 = {"search": (FOREFST, ("search", "ok")), "ra-files": (REFSANALYSIS, ("files",)),
       "ra-objects": (REFSANALYSIS, ("objects",))}
_EXTRACT = ("extract", "/test/ok.txt")                    # a 4-byte inline file of win11refsmini


def _no_copy_passes(v):
    damage_chkp(v, v.geo.lo)
    damage_chkp(v, v.geo.hi)


@pytest.mark.parametrize("cmd", sorted(_M5))
def test_n139_m5_no_valid_checkpoint_is_reported_by_every_bootstrap_only_command(vol, cmd):
    _no_copy_passes(vol)
    tool, args = _M5[cmd]
    rc, out = vol.run(tool, *args)
    assert _says_no_checkpoint_passed(out, (vol.geo.lo, vol.geo.hi)), \
        "%s must say that no checkpoint copy passed its self-checksum" % cmd + _ctx(vol, rc, out)
    assert rc in (1, 2), "refuse (1) or report (2), never exit 0" + _ctx(vol, rc, out)


@IMAGE_ONLY
def test_n139_m5_extract_reports_that_no_checkpoint_copy_passed(vol):
    _no_copy_passes(vol)
    rc, out = vol.run(FOREFST, *_EXTRACT)
    assert _says_no_checkpoint_passed(out, (vol.geo.lo, vol.geo.hi)), \
        "extract must say that no checkpoint copy passed its self-checksum" + _ctx(vol, rc, out)
    assert rc in (1, 2), "refuse (1) or report (2), never exit 0" + _ctx(vol, rc, out)


def test_n139_m5_control_the_same_commands_are_silent_about_checkpoints_on_the_undamaged_volume(vol):
    cmds = [_M5[k] for k in sorted(_M5)] + ([(FOREFST, _EXTRACT)] if vol.geo.kind == "image" else [])
    for tool, args in cmds:
        rc, out = vol.run(tool, *args)
        assert rc == 0 and not _says_no_checkpoint_passed(out, (vol.geo.lo, vol.geo.hi)), args + (_ctx(vol, rc, out),)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 6. C10 (N139 D-4) -- a checkpoint whose self-checksum cannot be computed (`cksum_ok is None`)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `_verify_self_checksum` returns None for a self-descriptor that declares checksum type 0 or digest length 0. An
# UNKNOWN type (3, 5, 0xff) does not give None: the descriptor scan passes over it and takes the first root page
# reference (type 2, CRC64) as the checkpoint's own descriptor, so the copy reads "FAILED (CRC64)" -- a separate
# observation, recorded in the report, not this item. The two plants below are the two ways to reach None.

_UNVERIFIED = re.compile(r"(?i)(could not|cannot|can't|unable to)( be)? (verif|check|comput)"
                         r"|\bnot (verifiable|checkable|verified|checked|computable)\b|\bunverif|\bunchecked\b"
                         r"|\bno (self-)?checksum\b|\bwithout (a )?checksum\b|checksum type 0\b")


def plant_unverifiable_checksum(v, how):
    """Make the NEWEST copy's self-checksum uncomputable: its descriptor (+0xE0) declares checksum type 0, or digest
    length 0. Both edits sit inside the window zeroed before hashing, so the stored CRC32-C still equals this module's
    own CRC32-C of the block: nothing else changed."""
    lcn = v.geo.lo
    b = bytearray(v.block(lcn))
    _fx(F._self_checksum_recipe(bytes(b), CS) == (CHKP_DESC, 1, 4, ZERO_WINDOW), "unexpected self-descriptor")
    if how == "type-0":
        b[CHKP_DESC + 0x22] = 0
    elif how == "length-0":
        struct.pack_into("<I", b, CHKP_DESC + 0x24, 0)
    else:
        raise RedFixtureError("unknown plant %s" % how)
    v.write(v.at(lcn), bytes(b))
    v.ops.append("CHKP 0x%x self-descriptor %s" % (lcn, how))
    blk = v.block(lcn)
    _fx(blk[CHKP_DESC + 0x28:CHKP_DESC + 0x2C] == _own_digest(blk, CHKP_DESC), "the block changed outside the window")
    _fx(F._verify_self_checksum(blk, CS)[0] is None, "the plant did not make cksum_ok None")
    return lcn


def _said_unverified(out, lcn):
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and _UNVERIFIED.search(s)]


@pytest.mark.parametrize("cmd", [("summary",), ("integrity",)], ids=["summary", "integrity"])
@pytest.mark.parametrize("how", ["type-0", "length-0"])
def test_c10_a_checkpoint_whose_checksum_cannot_be_computed_is_said_to_be_unverified(vol, how, cmd):
    lcn = plant_unverifiable_checksum(vol, how)
    rc, out = vol.run(FOREFST, *cmd)
    _keep(_chkp_rows(out, lcn), "the copy is listed" + _ctx(vol, rc, out))
    assert _said_unverified(out, lcn), \
        "the output must say that the checksum of the copy at LCN 0x%x could not be verified" % lcn \
        + _ctx(vol, rc, out)


def test_c10_control_a_verified_copy_is_not_called_unverified(vol):
    for cmd in (("summary",), ("integrity",)):
        rc, out = vol.run(FOREFST, *cmd)
        assert rc == 0 and _chkp_rows(out, vol.geo.lo) and not _said_unverified(out, vol.geo.lo), \
            cmd + (_ctx(vol, rc, out),)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 7. C25 -- bare `refsanalysis supb` on a zeroed primary superblock (battery A5_supb_primary_zero)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_DAMAGE_WORD = re.compile(r"(?i)\bzero|unreadable|missing|damaged|\bfail|invalid|\bbad\b|mismatch|corrupt"
                          r"|no (SUPB )?signature|not found")


def test_c25_bare_supb_reads_a_backup_superblock_when_the_primary_is_zeroed(vol):
    g = vol.geo
    vol.zero(vol.at(g.supb), CS)
    rc, out = vol.run(REFSANALYSIS, "supb")
    assert rc != 1, "supb stops on the damaged primary (rc=%d)" % rc + _ctx(vol, rc, out)
    assert GUID in out, "the superblock read from a backup carries GUID %s" % GUID + _ctx(vol, rc, out)
    src = [ln for ln in out.splitlines() if re.search(r"(?i)\bbackup\b", ln)
           and any(_supb_addr(vol, b).search(ln) for b in g.backups)]
    assert src, "the output must name the backup copy it read" + _ctx(vol, rc, out)
    assert [ln for ln in out.splitlines() if _supb_addr(vol, g.supb).search(ln) and _DAMAGE_WORD.search(ln)], \
        "the output must say the primary at LCN 0x%x is damaged" % g.supb + _ctx(vol, rc, out)


def test_c25_bare_supb_exit_code_is_2_when_it_reads_a_backup_superblock(vol):
    vol.zero(vol.at(vol.geo.supb), CS)
    rc, out = vol.run(REFSANALYSIS, "supb")
    assert rc == 2, "bare supb must exit 2 after reading a backup (rc=%d)" % rc + _ctx(vol, rc, out)


def test_c25_control_bare_supb_on_the_undamaged_volume(vol):
    rc, out = vol.run(REFSANALYSIS, "supb")
    assert rc == 0 and GUID in out, _ctx(vol, rc, out)


def test_c25_control_forefst_already_reads_a_backup_after_the_same_damage(vol):
    """The backups are intact and readable: forefst's bootstrap takes the GUID from one and exits 2."""
    vol.zero(vol.at(vol.geo.supb), CS)
    rc, out = vol.run(FOREFST, "summary")
    assert rc == 2 and _guid(out) == GUID, _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 8. A4 M-4 (decision 20.7) -- `boot --verify`: one row per boot-sector copy (primary and backup), own status
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A0 exits 0 (`test_a4_control_undamaged_volume_verifies_with_exit_0`); a PRIMARY flip exits 2 (the existing A4 RED).

_ROLE = {"primary": re.compile(r"(?i)(?<![a-z])primary(?![a-z])"),
         "backup": re.compile(r"(?i)(?<![a-z])backup(?![a-z])")}
_ROW_OK = re.compile(r"(?<![\w-])OK(?![\w-])|\[OK\]")
_ROW_FAIL = re.compile(r"(?i)(?<![\w-])FAIL(?:ED|S)?(?![\w-])|\[FAIL\]|\bmismatch")


def _copy_rows(out, role, status):
    """Verification rows of one boot-sector copy (its role word) with this status (OK rows carry no failure word)."""
    rows = [ln for ln in out.splitlines() if _ROLE[role].search(ln)]
    if status == "OK":
        return [ln for ln in rows if _ROW_OK.search(ln) and not _ROW_FAIL.search(ln)]
    return [ln for ln in rows if _ROW_FAIL.search(ln)]


def _backup_vbr_offset(v):
    """The backup boot sector: the volume's last sector, from the primary's own geometry (read here)."""
    p = v.read(v.geo.vbr, 512)
    off = v.geo.vbr + (struct.unpack_from("<Q", p, 0x18)[0] - 1) * struct.unpack_from("<I", p, 0x20)[0]
    _fx(v.read(off, 512) == p, "no identical backup boot sector at the last sector (0x%x)" % off)
    return off


def _flip_boot_sector(v, off):
    v.flip(off + 0x38)                                    # volume serial: inside the checksummed range
    b = v.read(off, 512)
    _fx(F._vbr_checksum(b, 512) != F.le16(b, 0x16), "the boot sector at 0x%x still verifies" % off)


def test_a4_m4_boot_verify_prints_an_ok_row_for_each_boot_sector_copy(vol):
    rc, out = vol.run(REFSANALYSIS, "boot", "--verify")
    _keep(rc == 0 and not _ROW_FAIL.search(out), "A0 verifies with exit 0" + _ctx(vol, rc, out))
    assert _copy_rows(out, "primary", "OK") and _copy_rows(out, "backup", "OK"), \
        "one OK row per boot-sector copy (primary and backup)" + _ctx(vol, rc, out)


def test_a4_m4_boot_verify_names_a_failed_backup_boot_sector_and_exits_2(vol):
    _flip_boot_sector(vol, _backup_vbr_offset(vol))
    rc, out = vol.run(REFSANALYSIS, "boot", "--verify")
    assert _copy_rows(out, "backup", "FAIL"), "a row must name the failed backup copy" + _ctx(vol, rc, out)
    assert _copy_rows(out, "primary", "OK"), "the intact primary keeps its own OK row" + _ctx(vol, rc, out)
    assert rc == 2, "boot --verify must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


def test_a4_m4_a_failed_primary_leaves_the_backup_row_ok(vol):
    _backup_vbr_offset(vol)                               # pins the backup before the damage
    _flip_boot_sector(vol, vol.geo.vbr)
    rc, out = vol.run(REFSANALYSIS, "boot", "--verify")
    _keep(re.search(r"(?im)checksum.*\bFAIL\b", out), "the primary's mismatch is already in the table" + _ctx(vol, rc, out))
    assert _copy_rows(out, "backup", "OK"), "the intact backup keeps its own OK row" + _ctx(vol, rc, out)
    assert _copy_rows(out, "primary", "FAIL"), "the failed row must name the primary copy" + _ctx(vol, rc, out)


def test_a4_m4_control_forefst_sees_the_backup_boot_sector_flip(vol):
    """The backup flip lands where the tools look for the backup: forefst's summary says it DIFFERS."""
    _flip_boot_sector(vol, _backup_vbr_offset(vol))
    rc, out = vol.run(FOREFST, "summary")
    assert [ln for ln in out.splitlines() if "VBR backup" in ln and re.search(r"(?i)differs|fail|mismatch", ln)], \
        _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 9. N205 (decision 20.8) -- a copy that passes its self-checksum while its root 0xC, 7 or 8 does not verify
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 26100.x validates a checkpoint copy in its first pass by its self-checksum AND by reading global-table roots 0xC,
# 7 and 8 and comparing each root block's checksum with the digest the copy records for it
# (`ValidateCheckpointRecord` lambda, 26100.8115 :217188-217197, :217281; `ValidateGlobalTableRootBlock` compares
# with the reference's +0x22/+0x24/+0x28). Insider 29574 rejects only on a read error (F1-b C-2). The plant: one
# byte of root N's digest in the NEWEST copy's page reference, that copy re-sealed. The root page itself and the
# other copy are untouched, so 26100 would take the older copy in pass 1 and Insider 29574 the newest. The tool reads
# the newest copy (decision: read it if it can be read) -- and today says nothing.
# After the critic:
# * S1 -- the finding may take two lines: the copy's LCN and the failing root in one statement, "26100" and a
#   rejection word in it or in one of the two statements before or after it.
# * S2 -- summary's `Virtual clock` is `checkpoint_select`'s `newest` (fd cmd_fastsummary), so it does not show which
#   copy is READ, and a fix that made `bootstrap` switch to the older copy passed every node. The summary nodes now
#   plant a READ WITNESS in the older copy (`plant_read_witness`): summary counts each root table through the root
#   list of the copy bootstrap reads, and root 11's count moves if the older copy is read. The witness alone changes
#   nothing (a control), and moves when the tool does read the older copy (a control: the newest copy flipped).
#   `files` has no such channel on these fixtures (it does not verify root pages against the copy it reads), so the
#   `files` nodes rely on the summary nodes and on the `integrity --checksums` control (which catches a switch inside
#   `checkpoint_select` only).

_REJECT = re.compile(r"(?i)\breject|\brefus|\bskip|would not (use|accept|take)|\bnot accept")
_ROOT_NAMES = {0xC: r"small allocator", 7: r"container table(?!\s*(?:dup|duplicate|\(dup))",
               8: r"container table\s*(?:dup|duplicate|\(dup)|duplicate container table"}
_N205_ROOTS = [0xC, 7, 8]


def _root_ref_offset(chkp, idx):
    olb = F.le32(chkp, 0x94) if F.le32(chkp, 0x78) & 0x200 else 0x94
    return F.le32(chkp, olb + 4 * idx)


def _root_page(v, lcns):
    return v.read(v.at(lcns[0]), len(lcns) * CS)


def plant_root_failure(v, idx):
    g = v.geo
    new, old = v.block(g.lo), v.block(g.hi)
    ro, oro = _root_ref_offset(new, idx), _root_ref_offset(old, idx)
    _fx(new[ro + 0x22] == 2 and new[ro + 0x23] == 8 and F.le32(new, ro + 0x24) == 8,
        "root %d: not a CRC64 page reference" % idx)
    lcns = _root_list(new)[idx]
    _fx(lcns and _root_list(old)[idx] == lcns, "root %d: the two copies do not share the root page" % idx)
    page = _root_page(v, lcns)
    crc = F.refs_crc64(page)
    _fx(page[:4] == b"MSB+" and crc == F.le64(new, ro + 0x28) == F.le64(old, oro + 0x28),
        "root %d does not verify against both copies before the plant" % idx)

    def edit(b):
        b[ro + 0x28] ^= 0x01
    v.reseal(g.lo, edit, CHKP_DESC)
    _fx(F.refs_crc64(_root_page(v, lcns)) != F.le64(v.block(g.lo), ro + 0x28),
        "root %d still verifies against the newest copy" % idx)
    _fx(F.refs_crc64(_root_page(v, lcns)) == F.le64(v.block(g.hi), oro + 0x28),
        "root %d no longer verifies against the older copy" % idx)
    _fx(v.verifies(g.lo) is True and v.verifies(g.hi) is True, "a copy fails its self-checksum after the plant")


def _root_named(s, idx):
    num = r"(?:0x0*%x|%d)" % (idx, idx)
    return re.search(r"(?i)\broot\s*(?:#|index|idx|no\.?)?\s*%s\b|globaltable\[\s*%s\s*\]|\b(?:%s)\b"
                     % (num, num, _ROOT_NAMES[idx]), s)


def _n205_said(out, lcn, idx):
    """The finding: a statement naming the copy and the root that fails, with "26100" and a rejection word in it or
    in one of the two statements before or after it (a warning may take two lines; critic S1)."""
    st = _statements(out)
    hits = []
    for i, s in enumerate(st):
        if _lcn_re(lcn).search(s) and _root_named(s, idx):
            near = " ".join(st[max(0, i - 2):i + 3])
            if "26100" in near and _REJECT.search(near):
                hits.append(s)
    return hits


_WITNESS = 11                                             # Integrity State: virtual LCNs, outside {0xC, 7, 8}
_WITNESS_SRC = {"synthetic": 7, "image": 3}               # a root whose table has a different row count
_ROOT_LABEL = {3: "Schema Table", 7: "Container Table", 11: "Integrity State"}


def _root_rows(out, idx):
    m = re.search(r"(?m)^\s*%s\s+(\d+) rows?\b" % re.escape(_ROOT_LABEL[idx]), out)
    return int(m.group(1)) if m else None


def plant_read_witness(v):
    """Make the copy READ observable in summary (critic S2). In the OLDER copy only, root 11's page reference is
    replaced by root S's (the Container Table on the synthetic volume, the Schema Table on the image) and the copy is
    re-sealed. Its roots 0xC, 7 and 8 are untouched, so it still passes 26100's first pass. summary counts every root
    through the root list of the copy bootstrap reads, so 'Integrity State' keeps its own count while the newest copy
    is read and shows root S's count if the older copy is read. Run on the intact volume, BEFORE any other damage.
    Returns (the count that must stay, root S's count)."""
    g = v.geo
    src = _WITNESS_SRC[g.kind]
    rc, out = v.run(FOREFST, "summary")
    stay, moved = _root_rows(out, _WITNESS), _root_rows(out, src)
    _fx(rc == 0 and stay is not None and moved is not None and stay != moved,
        "witness: roots 11 and %d do not show different row counts (%r / %r)" % (src, stay, moved))
    old = v.block(g.hi)
    ro_w, ro_s, dlen = _root_ref_offset(old, _WITNESS), _root_ref_offset(old, src), F.le32(old, 0x5C)

    def edit(b):
        b[ro_w:ro_w + dlen] = old[ro_s:ro_s + dlen]
    v.reseal(g.hi, edit, CHKP_DESC)
    _fx(_root_list(v.block(g.hi))[_WITNESS] == _root_list(old)[src], "witness: the reference was not copied")
    _fx(_root_list(v.block(g.lo))[_WITNESS] == _root_list(old)[_WITNESS], "witness: the newest copy changed")
    return stay, moved


def _keep_newest_copy_read(v, rc, out, stay):
    _keep(_root_rows(out, _WITNESS) == stay, "the newest copy is read (decision 20.8: read it if it can be read): "
          "'Integrity State' must keep %d rows; root %d's count means bootstrap read the OLDER copy"
          % (stay, _WITNESS_SRC[v.geo.kind]) + _ctx(v, rc, out))


@pytest.mark.parametrize("cmd", ["files", "summary"])
@pytest.mark.parametrize("idx", _N205_ROOTS, ids=["root0xC", "root7", "root8"])
def test_n205_a_copy_the_26100_driver_would_reject_is_read_and_the_reason_is_stated(vol, idx, cmd):
    stay = plant_read_witness(vol)[0] if cmd == "summary" else None
    plant_root_failure(vol, idx)
    rc, out = vol.run(FOREFST, cmd)
    if stay is not None:
        _keep_newest_copy_read(vol, rc, out, stay)
    assert _n205_said(out, vol.geo.lo, idx), (
        "the output must say that the 26100 driver would reject the checkpoint copy at LCN 0x%x because root 0x%x "
        "does not verify" % (vol.geo.lo, idx)) + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", ["files", "summary"])
@pytest.mark.parametrize("idx", _N205_ROOTS, ids=["root0xC", "root7", "root8"])
def test_n205_exit_code_is_2_when_the_copy_read_is_one_the_26100_driver_would_reject(vol, idx, cmd):
    stay = plant_read_witness(vol)[0] if cmd == "summary" else None
    plant_root_failure(vol, idx)
    rc, out = vol.run(FOREFST, cmd)
    if stay is not None:
        _keep_newest_copy_read(vol, rc, out, stay)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("idx", _N205_ROOTS, ids=["root0xC", "root7", "root8"])
def test_n205_control_integrity_checksums_sees_the_planted_root_failure(vol, idx):
    """The plant is visible to a sound path: the root-table digest check of the copy in use finds one mismatch."""
    plant_root_failure(vol, idx)
    rc, out = vol.run(FOREFST, "integrity", "--checksums")
    assert rc == 2 and re.search(r"(?i)\b1 checksum mismatch", out), _ctx(vol, rc, out)


def test_n205_control_the_read_witness_alone_changes_nothing(vol):
    stay, _moved = plant_read_witness(vol)
    for cmd in ("files", "summary"):
        rc, out = vol.run(FOREFST, cmd)
        assert rc == 0, cmd + _ctx(vol, rc, out)
    assert _root_rows(out, _WITNESS) == stay, _ctx(vol, rc, out)


def test_n205_control_the_read_witness_moves_when_the_older_copy_is_read(vol):
    """The witness discriminates: with the newest copy failing its self-checksum the tool reads the older copy, and
    'Integrity State' shows root S's count."""
    _stay, moved = plant_read_witness(vol)
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(FOREFST, "summary")
    assert _root_rows(out, _WITNESS) == moved, _ctx(vol, rc, out)


def test_n205_control_the_undamaged_volume_draws_no_rejection_statement(vol):
    for cmd in ("files", "summary"):
        rc, out = vol.run(FOREFST, cmd)
        assert rc == 0 and not any(_n205_said(out, vol.geo.lo, i) for i in _N205_ROOTS) \
            and not [s for s in _statements(out) if "26100" in s and _REJECT.search(s)], cmd + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 10. V-a (decision 20.3) -- no RED: on a tie with one damaged copy the current tools already do what was decided
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured on both volumes, all four tie shapes: files, search, refsanalysis files (and extract on the image) exit 0;
# summary, fastsummary and integrity exit 2 and name the damaged copy ("secondary checkpoint @ 0x.. invalid"). A11's
# s.3.3 coupling made it so. These controls keep it through group 2.

_TIES = {"slot0-lower_slot1-failed": (False, "hi"), "slot0-lower_slot0-failed": (False, "lo"),
         "slot0-higher_slot0-failed": (True, "hi"), "slot0-higher_slot1-failed": (True, "lo")}


def _tie_with_one_damaged(v, shape):
    slot0_higher, which = _TIES[shape]
    make_tie(v, slot0_higher)
    lcn = getattr(v.geo, which)
    damage_chkp(v, lcn)
    return lcn


@pytest.mark.parametrize("shape", sorted(_TIES))
def test_v_a_control_bootstrap_only_commands_exit_0_on_a_tie_with_one_damaged_copy(vol, shape):
    _tie_with_one_damaged(vol, shape)
    cmds = [(FOREFST, ("files",)), (FOREFST, ("search", "ok")), (REFSANALYSIS, ("files",))] \
        + ([(FOREFST, _EXTRACT)] if vol.geo.kind == "image" else [])
    for tool, args in cmds:
        rc, out = vol.run(tool, *args)
        assert rc == 0, args + (_ctx(vol, rc, out),)


@pytest.mark.parametrize("shape", sorted(_TIES))
def test_v_a_control_summary_fastsummary_integrity_exit_2_and_name_the_damaged_copy(vol, shape):
    lcn = _tie_with_one_damaged(vol, shape)
    for cmd in ("summary", "fastsummary", "integrity"):
        rc, out = vol.run(FOREFST, cmd)
        assert rc == 2 and _named_failed(out, lcn, r"chkp|checkpoint"), cmd + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 11. N206 (A11 review D4) -- "the NEWEST checkpoint (the copy the driver would use) failed" on the untied case
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Under the driver rule A11 implements, the driver skips a copy that fails and uses the older one that passes, or
# refuses the mount (0xC0000032) when none passes (F1 3.3). The parenthesis is false every time it prints.
# After the critic (M3): both readers are bound to the CLAUSE, not the statement. Keeping "(the copy the driver would
# use)" on the failed copy and appending "; the volume was read from the older copy at LCN 0x88" passed all six
# newest-failed nodes: the old `_false_driver_copy` exempted any statement naming the passing LCN, and the old
# `_driver_uses` took the false parenthesis itself as "driver ... use" with that LCN anywhere in the statement.

_DRIVER = re.compile(r"(?i)\b(driver|refs\.sys|windows)\b")
_DRIVER_USES = re.compile(r"(?i)\b(driver|refs\.sys|windows)\b[^.;]{0,80}?\b(use|uses|used|take|takes|select|selects"
                          r"|pick|picks|read|reads|mount|mounts|falls? back|keep|keeps|choose|chooses)\b")
_REFUSES = re.compile(r"(?i)\brefus|\breject|\b(not|never|cannot|can't|won't|would not)( be)? mount"
                      r"|\bfails? (to|the) mount|0xC0000032")


_DRIVER_PHRASE = re.compile(r"(?i)\bthe copy the driver (?:would use|uses)\b|\bdriver would use\b")


def _clause_after(s, end):
    """The rest of the clause after `end`: up to . ; or a closing parenthesis, at most 80 characters."""
    return re.split(r"[.;)]", s[end:], maxsplit=1)[0][:80]


def _false_driver_copy(out, passing_lcn):
    """Statements (with a failure word) whose "the copy the driver would use" / "driver would use" does not describe
    the passing copy: that copy's LCN is neither in the rest of the same clause nor within 40 characters before the
    phrase ("LCN 0x88 (the copy the driver would use)"). With no copy passing, only "would use neither/no/none" is
    true."""
    bad = []
    for s in _statements(out):
        if not _FAIL.search(s):
            continue
        for m in _DRIVER_PHRASE.finditer(s):
            after, before = _clause_after(s, m.end()), re.split(r"[.;]", s[:m.start()])[-1][-40:]
            if passing_lcn is not None and (_lcn_re(passing_lcn).search(after) or _lcn_re(passing_lcn).search(before)):
                continue
            if re.match(r"(?i)\s*(neither|no|none)\b", after):
                continue
            bad.append(s)
            break
    return bad


def _driver_uses(out, lcn):
    """Statements saying the driver uses this copy: a driver word, a use verb, then the copy's LCN in the rest of the
    same clause."""
    return [s for s in _statements(out)
            if any(_lcn_re(lcn).search(_clause_after(s, m.end())) for m in _DRIVER_USES.finditer(s))]


def _driver_refuses(out):
    return [s for s in _statements(out) if _DRIVER.search(s) and _REFUSES.search(s)]


@pytest.mark.parametrize("cmd", ["summary", "fastsummary", "integrity"])
@pytest.mark.parametrize("case", ["newest-failed", "no-copy-passes"])
def test_n206_the_failed_newest_copy_is_never_called_the_copy_the_driver_would_use(vol, case, cmd):
    damage_chkp(vol, vol.geo.lo)
    passing = vol.geo.hi
    if case == "no-copy-passes":
        damage_chkp(vol, vol.geo.hi)
        passing = None
    rc, out = vol.run(FOREFST, cmd)
    _keep(rc == 2, "a damaged copy is already a finding (exit 2)" + _ctx(vol, rc, out))
    bad = _false_driver_copy(out, passing)
    assert not bad, "a failed copy is called the driver's copy: %r" % bad + _ctx(vol, rc, out)
    if passing is not None:
        assert _driver_uses(out, passing), \
            "the output must say the driver uses the older passing copy (LCN 0x%x)" % passing + _ctx(vol, rc, out)
    else:
        assert _driver_refuses(out), "the output must say the driver refuses the mount" + _ctx(vol, rc, out)


@pytest.mark.parametrize("case", ["undamaged", "older-failed"])
def test_n206_control_no_driver_claim_where_the_newest_copy_passes(vol, case):
    """Where the newest copy passes, no statement calls a failed copy the driver's or says the mount is refused."""
    if case == "older-failed":
        damage_chkp(vol, vol.geo.hi)
    for cmd in ("summary", "integrity"):
        rc, out = vol.run(FOREFST, cmd)
        assert not _false_driver_copy(out, None) and not _driver_refuses(out), cmd + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 12. N207 (A11 review D2) -- refsanalysis supb/chkp/containers without --verify say a copy FAILED and exit 0
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured: supb names a failed copy in all three damage cases; chkp and containers only when the NEWEST copy failed
# (chkp shows `checkpoint_select`'s `newest`, ra:1729-1741, containers the copy in use: neither prints a line for a
# failed OLDER copy). Those are the pairs below. The reporting is right today (a control); the exit code is the
# defect (exit 2 decided on 2026-10-01, decision 21). After the critic (S4): "failed" is matched in any case.

_N207 = [("supb", "newest-failed"), ("supb", "older-failed"), ("supb", "no-copy-passes"),
         ("chkp", "newest-failed"), ("chkp", "no-copy-passes"),
         ("containers", "newest-failed"), ("containers", "no-copy-passes")]
_N207_IDS = ["%s-%s" % p for p in _N207]


def _damage_copies(v, case):
    lcns = {"newest-failed": (v.geo.lo,), "older-failed": (v.geo.hi,), "no-copy-passes": (v.geo.lo, v.geo.hi)}[case]
    for lcn in lcns:
        damage_chkp(v, lcn)
    return lcns


def _says_a_copy_failed(out, lcns):
    return [ln for lcn in lcns for ln in _lines(out, lcn) if _FAIL.search(ln)]


@pytest.mark.parametrize("cmd,case", _N207, ids=_N207_IDS)
def test_n207_control_supb_chkp_containers_say_the_copy_failed(vol, cmd, case):
    """The reporting half of N207: already right (the kept precondition of the exit-code RED below)."""
    lcns = _damage_copies(vol, case)
    rc, out = vol.run(REFSANALYSIS, cmd)
    assert _says_a_copy_failed(out, lcns), _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd,case", _N207, ids=_N207_IDS)
def test_n207_supb_chkp_containers_exit_code_is_2_when_they_say_a_copy_failed(vol, cmd, case):
    lcns = _damage_copies(vol, case)
    rc, out = vol.run(REFSANALYSIS, cmd)
    _keep(_says_a_copy_failed(out, lcns), "the command says a copy FAILED" + _ctx(vol, rc, out))
    assert rc == 2, "refsanalysis %s says a copy FAILED and must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


def test_n207_control_undamaged_exits_0_and_forefst_summary_exits_2_on_each_case(vol):
    for cmd in ("supb", "chkp", "containers"):
        rc, out = vol.run(REFSANALYSIS, cmd)
        assert rc == 0, cmd + _ctx(vol, rc, out)
    for case in ("newest-failed", "older-failed", "no-copy-passes"):
        _damage_copies(vol, case)
        rc, out = vol.run(FOREFST, "summary")
        assert rc == 2, case + _ctx(vol, rc, out)
        for lcn in (vol.geo.lo, vol.geo.hi):             # restore the two copies for the next case
            if vol.verifies(lcn) is False:
                vol.flip(vol.at(lcn, 0x400))
        _fx(vol.verifies(vol.geo.lo) is True and vol.verifies(vol.geo.hi) is True, "the copies were not restored")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 13. N215 -- refsanalysis reads the compression policy only when Container-Table root +0xA0 == 0x0F
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# +0xA0 is `CmsVolumeContainer+0x78`, a flags word (bit 3 set above volume version 0x306: 0x07 on v3.4, 0x0F on
# v3.7+; E90), not a policy marker. The policy record is format +0xA4 (u16), level +0xA6 (i16), chunk +0xA8 (u32),
# three percentages +0xD4/+0xD8/+0xDC and flags +0xE0 (D14 compression critic s.5.3). Two REDs:
# * planted [image]: a configured policy (LZ4, level 9, chunk 0x8000, 70/30/40, flags 0) with +0xA0 = 0x07 -> today
#   "Compression: Not configured" and no policy section; the control is the same plant with +0xA0 = 0x0F.
# * read-only v3.4 (win10refsmini): same policy bytes as the v3.14 win11refsmini (all zero), so both must print the
#   same compression line and policy section; today v3.4 prints "Not configured" and no section.
# The four 2 TB win11refs2tmillionsofactions images are not used: their Container-Table root is an inner node whose
# frame at +0xA0 is not the policy record (E90 scope limit; le32(+0xA0) reads 0x4000 there), so the policy's location
# there is not established.
# After the critic (M4): the planted RED runs with +0xA0 = 0x07 (v3.4's value) AND with values that are neither of
# E90's two (0x00; 0x0B = bits 0, 1 and 3, the bits the driver tests, without bit 2), so a gate widened to
# `in (0x07, 0x0F)` -- still a gate on a flags word -- fails it. The 0x0F control is unchanged.
_N215_FLAGS = [0x07, 0x00, 0x0B]

_POLICY = ((0xA4, "<H", 1), (0xA6, "<h", 9), (0xA8, "<I", 0x8000), (0xD4, "<I", 70), (0xD8, "<I", 30),
           (0xDC, "<I", 40), (0xE0, "<I", 0))


def _ct_root_index(v, chkp):
    """The root (7 or 8) whose page carries table id 0x0B, read by this module."""
    found = [i for i in (7, 8) if _root_page(v, _root_list(chkp)[i])[:4] == b"MSB+"
             and F.le64(_root_page(v, _root_list(chkp)[i]), 0x48) == 0x0B]
    _fx(len(found) == 1, "no single Container-Table root (table id 0x0B) among roots 7/8")
    return found[0]


def _policy_bytes(page):
    return [struct.unpack_from(fmt, page, off)[0] for off, fmt, _v in _POLICY]


def plant_compression_policy(v, flags_a0):
    g = v.geo
    idx = _ct_root_index(v, v.block(g.lo))
    lcns = _root_list(v.block(g.lo))[idx]
    _fx(_root_list(v.block(g.hi))[idx] == lcns, "the two copies do not share the Container-Table root page")
    page = bytearray(_root_page(v, lcns))
    _fx(0x50 + F.le32(page, 0x50) == 0x278, "the root's index header is not at 0x278: +0xA0..+0xE4 are not free")
    _fx(F.le32(page, 0xA0) == 0x0F and not any(_policy_bytes(page)), "the base page is not v3.7+ unconfigured")
    for off, fmt, val in _POLICY:
        struct.pack_into(fmt, page, off, val)
    struct.pack_into("<I", page, 0xA0, flags_a0)
    v.write(v.at(lcns[0]), bytes(page))
    v.ops.append("CT root 0x%x: policy LZ4/9/0x8000, +0xA0=0x%x" % (lcns[0], flags_a0))
    crc = F.refs_crc64(bytes(page))
    for lcn in (g.lo, g.hi):
        ro = _root_ref_offset(v.block(lcn), idx)

        def edit(b, ro=ro):
            struct.pack_into("<Q", b, ro + 0x28, crc)
        v.reseal(lcn, edit, CHKP_DESC)
        _fx(F.le64(v.block(lcn), ro + 0x28) == F.refs_crc64(_root_page(v, lcns)), "digest not re-sealed")


def _compression_line(out):
    m = re.search(r"(?m)^\s*Compression:\s*(.*?)\s*$", out)
    return m.group(1) if m else None


def _policy_lines(out):
    return [ln.strip() for ln in out.splitlines() if re.match(r"(?i)^\s*(format|level|chunk size):", ln)]


def _lz4_policy_shown(out):
    pl = "\n".join(_policy_lines(out))
    return bool(re.search(r"(?im)^format:\s*LZ4\b", pl) and re.search(r"(?im)^level:\s*9\b", pl)
                and re.search(r"(?im)^chunk size:.*(0x0*8000\b|\b32768\b|\b32(\.0)?\s*Ki?B\b)", pl))


@IMAGE_ONLY
@pytest.mark.parametrize("cmd", ["summary", "containers"])
@pytest.mark.parametrize("flags", _N215_FLAGS, ids=["flags0x07", "flags0x00", "flags0x0B"])
def test_n215_the_compression_policy_is_read_whatever_the_flags_word_holds(vol, flags, cmd):
    plant_compression_policy(vol, flags)
    rc, out = vol.run(REFSANALYSIS, cmd)
    if cmd == "summary":
        line = _compression_line(out)
        _keep(line is not None, "summary prints a Compression line" + _ctx(vol, rc, out))
        assert re.search(r"\bLZ4\b", line) and not re.search(r"(?i)not configured", line), \
            "Compression: %r over an LZ4 policy" % line + _ctx(vol, rc, out)
    else:
        assert _lz4_policy_shown(out), "containers must print the LZ4 policy (level 9, chunk 0x8000)" \
            + _ctx(vol, rc, out)


@IMAGE_ONLY
def test_n215_control_the_same_policy_with_0x0f_is_already_read(vol):
    plant_compression_policy(vol, 0x0F)
    rc, out = vol.run(REFSANALYSIS, "summary")
    assert rc == 0 and _compression_line(out) == "LZ4", _ctx(vol, rc, out)
    rc, out = vol.run(REFSANALYSIS, "containers")
    assert rc == 0 and _lz4_policy_shown(out), _ctx(vol, rc, out)


# ─── read-only: v3.4 against v3.14 with the same policy bytes ───────────────────────────────────────────────────

_V34, _V314 = "step1/win10refsmini.raw", "step1/win11refsmini.raw"     # N386: by step path
_PS = 0x1000000


def _ro_policy(path, version):
    """Pin a read-only image: version, both checkpoint copies' Container-Table root page, its +0xA0 and policy."""
    with open(path, "rb") as fh:
        def rd(off, n):
            fh.seek(off)
            return fh.read(n)
        vbr = rd(_PS, 512)
        _fx(vbr[3:7] == b"ReFS" and (vbr[0x28], vbr[0x29]) == version and F.le32(vbr, 0x20) * F.le32(vbr, 0x24) == CS,
            "%s: not a 4 KiB-cluster ReFS %d.%d volume at 0x%x" % ((path,) + version + (_PS,)))
        supb = rd(_PS + 0x1E * CS, CS)
        _fx(supb[:4] == b"SUPB", "%s: no superblock" % path)
        seen = set()
        for i in range(2):
            chkp = rd(_PS + F.le64(supb, 0xC0 + 8 * i) * CS, CS)
            _fx(chkp[:4] == b"CHKP", "%s: no checkpoint in slot %d" % (path, i))
            pages = [rd(_PS + _root_list(chkp)[r][0] * CS, 4 * CS) for r in (7, 8)]
            ct = [p for p in pages if p[:4] == b"MSB+" and F.le64(p, 0x48) == 0x0B]
            _fx(len(ct) == 1 and 0x50 + F.le32(ct[0], 0x50) == 0x278, "%s: Container-Table root layout" % path)
            seen.add((F.le32(ct[0], 0xA0), tuple(_policy_bytes(ct[0]))))
    _fx(len(seen) == 1, "%s: the two checkpoint copies disagree on the policy page" % path)
    return seen.pop()


def _ro_run(tool, path, *args, cwd):
    cmd = [sys.executable, "-B", tool, path] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=_AB.TIMEOUT, cwd=cwd)
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed:\n" + r.stderr[-3000:])
    return r.returncode, r.stdout + "\n" + r.stderr


def _ro_pair():
    p34, p314 = _corpus_image(_V34), _corpus_image(_V314)
    if p34 is None or p314 is None:
        pytest.skip("%s / %s not in this tree (a clone ships no images)" % (_V34, _V314))
    a34, pol34 = _ro_policy(p34, (3, 4))
    a314, pol314 = _ro_policy(p314, (3, 14))
    _fx((a34, a314) == (0x07, 0x0F), "+0xA0 is 0x%x on v3.4 and 0x%x on v3.14 (E90: 0x07 / 0x0F)" % (a34, a314))
    _fx(pol34 == pol314, "the two volumes do not hold the same policy bytes: %r / %r" % (pol34, pol314))
    return p34, p314


@pytest.mark.parametrize("cmd", ["summary", "containers"])
def test_n215_image_v34_prints_the_policy_a_v314_volume_with_the_same_bytes_prints(cmd, tmp_path):
    p34, p314 = _ro_pair()
    rc14, out14 = _ro_run(REFSANALYSIS, p314, cmd, cwd=str(tmp_path))
    rc34, out34 = _ro_run(REFSANALYSIS, p34, cmd, cwd=str(tmp_path))
    if cmd == "summary":
        want = _compression_line(out14)
        _keep(want is not None and "not configured" not in want.lower(), "v3.14 reads its policy: %r" % want)
        got = _compression_line(out34)
        assert got == want, "v3.4 prints Compression: %r, v3.14 with the same policy bytes %r" % (got, want) \
            + "\n" + out34[-3000:]
    else:
        want = _policy_lines(out14)
        _keep(want, "v3.14 prints its policy section")
        assert _policy_lines(out34) == want, "v3.4 policy lines %r, v3.14 %r" % (_policy_lines(out34), want) \
            + "\n" + out34[-3000:]


def test_n215_image_control_a_v314_volume_already_prints_its_policy(tmp_path):
    _p34, p314 = _ro_pair()
    rc, out = _ro_run(REFSANALYSIS, p314, "summary", cwd=str(tmp_path))
    # acceptance 1.14.0 (K24's word for no algorithm, `none`, for compression too)
    assert rc == 0 and _compression_line(out) == "none", out[-3000:]
    rc, out = _ro_run(REFSANALYSIS, p314, "containers", cwd=str(tmp_path))
    assert rc == 0 and _policy_lines(out) == ["Format:      none", "Level:       0", "Chunk size:  0 (default)"], \
        out[-3000:]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The matchers can go GREEN: a plausible corrected line is accepted, the current tool's line is rejected
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_group2_matchers_accept_corrected_wording_and_reject_the_current_lines():
    # statements: continuation joins a wrapped NOTE, never across a rule, a header or a tagged line
    st = _statements("------\n  Image:   x\n  NOTE: a\n        b\n  [WARN] c\n        d\nHeader:\n  e")
    assert st == ["------", "Image:   x", "NOTE: a b", "[WARN] c d", "Header:", "e"], st
    assert _addr_re(0x1E, 0x101E000).search("at offset 0x101E000") and not _addr_re(0x1E).search("0x1e000")
    syn = SimpleNamespace(geo=SimpleNamespace(lo=0x48, hi=0x88, ps=0))
    # 1 (C1: the warning names the failed backup copy, by LCN or offset)
    assert not _SUPB_WARN.search("  SUPB backup      LCN 0xfd (offset 0xfd000)  — signature OK")
    assert _SUPB_WARN.search("  [WARN] backup superblock (SUPB) at LCN 0xfd failed its self-checksum (CRC32-C)")
    assert _supb_warnings("  [WARN] backup superblock (SUPB) at LCN 0xfd failed its self-checksum", 0, 0xFD)
    assert _supb_warnings("[forefst] WARNING: backup SUPB at offset 0x7cffd000 failed", 0x1000000, 0x7BFFD)
    assert not _supb_warnings("  [WARN] a backup superblock failed its self-checksum", 0, 0xFD)
    assert not _supb_warnings("  [WARN] backup superblock (SUPB) at LCN 0xfe failed its self-checksum", 0, 0xFD)
    # 2
    cur = "  Checkpoint [secondary]:   LCN 0x88 — valid, vclock=63"
    assert _valid_labels(cur, [0x88], syn) and not _valid_labels("  [WARN] redundancy: secondary checkpoint @ 0x88 "
                                                                  "invalid", [0x88], syn)
    assert not _valid_labels("  Checkpoint [secondary]:   LCN 0x88 — checksum FAILED, vclock=63", [0x88], syn)
    assert not _valid_labels("  CHKP secondary   LCN 0x88 — not valid (checksum FAILED)", [0x88], syn)
    assert _valid_labels("  Checkpoint [secondary]:   LCN 0x48 — valid, vclock=64 (tied clock)", [0x48], syn)
    assert not _FAIL.search("  CHKP secondary   LCN 0x88 (offset 0x88000)  — signature OK, vclock=63")
    # 4 (S3: a reworded clock is still read; "no comparison" only when nothing is printed)
    assert _cmp_pair("  Current checkpoint: VC=64\n  Previous checkpoint: VC=63\n") == (64, 63)
    assert _cmp_pair("  Current checkpoint (in use): LCN 0x88, VC 63\n  Previous checkpoint: LCN 0x48, VC=64") == (63, 64)
    assert _cmp_pair("  Current checkpoint: vclock 64\n  Previous checkpoint: vclock 63") == (64, 63)
    assert _cmp_pair("no comparison") == (None, None)
    assert _cmp_printed("[forefst] Done.\n  Same top-level files") is None
    assert _cmp_printed("  Previous checkpoint (LCN 0x48): 64\n") is not None
    # R2: names in the comparison block, matched whole
    blk = "  Current checkpoint: VC=63\n  Previous checkpoint: VC=64\n  Files in current but NOT in old (2):\n" \
          "    + $RECYCLE.BIN\n    + hello.txt"
    assert _names_listed(blk, {"$RECYCLE.BIN", "hello.txt", "test"}) == ["$RECYCLE.BIN", "hello.txt"]
    assert not _names_listed("  Same top-level files in both (change may be in subdirectories or metadata)",
                             {"$RECYCLE.BIN", "test", "metadata.bin"})
    assert _cmp_block("x\n  Current checkpoint: VC=63\n  Previous checkpoint: VC=64\n  + test\n\nlater test") \
        == "  Current checkpoint: VC=63\n  Previous checkpoint: VC=64\n  + test"
    # 5 (M2: a warning about the newest copy alone is not "no copy passed")
    assert not _says_no_checkpoint_passed("[forefst] WARNING: the newest checkpoint (LCN 0x48, vclock 64) failed its "
                                          "self-checksum (CRC32-C)", (0x48, 0x88))
    # R1: the STALE line names both copies but says only the newest failed (the older one is the copy read)
    assert not _says_no_checkpoint_passed("[forefst] WARNING: the newest checkpoint (LCN 0x48, vclock 64) failed its "
                                          "self-checksum (CRC32-C); the volume was read from an OLDER checkpoint (LCN "
                                          "0x88, vclock 63), so this view is STALE -- changes committed after that "
                                          "older checkpoint are not reflected", (0x48, 0x88))
    assert _says_no_checkpoint_passed("[forefst] WARNING: no checkpoint copy passes its self-checksum (LCN 0x48, 0x88): "
                                      "the driver would refuse to mount this volume", (0x48, 0x88))
    # 6
    assert not _said_unverified("  CHKP primary     LCN 0x48 (offset 0x48000)  — signature OK, vclock=64", 0x48)
    assert not _said_unverified("  Checkpoint [PRIMARY  ]:   LCN 0x48 — valid, vclock=64", 0x48)
    for fixed in ("  CHKP primary     LCN 0x48 (offset 0x48000)  — checksum could not be verified (type 0), vclock=64",
                  "  Checkpoint [PRIMARY  ]:   LCN 0x48 — self-checksum not verifiable (none declared), vclock=64"):
        assert _said_unverified(fixed, 0x48), fixed
    # 8
    v1131 = ("checksum_match      OK      stored=0x2B6E, computed=0x2B6E\n"
             "bps_is_512          OK      stored=512")
    assert not _copy_rows(v1131, "primary", "OK") and not _copy_rows(v1131, "backup", "OK")
    fixed = ("checksum_primary    OK      LBA 0 stored=0x2B6E, computed=0x2B6E\n"
             "checksum_backup     FAIL    LBA 2047 stored=0x2B6E, computed=0x1234")
    assert _copy_rows(fixed, "primary", "OK") and _copy_rows(fixed, "backup", "FAIL")
    assert not _copy_rows(fixed, "backup", "OK") and not _copy_rows(fixed, "primary", "FAIL")
    # 9
    fixed = ("[forefst] WARNING: the checkpoint copy at LCN 0x48 passes its self-checksum, but root 7 (Container "
             "Table) does not verify against its digest: the 26100 driver would reject this copy (Insider 29574 "
             "rejects only on a read error); it is read anyway")
    assert _n205_said(fixed, 0x48, 7) and not _n205_said(fixed, 0x48, 8) and not _n205_said(fixed, 0x48, 0xC)
    assert _n205_said(fixed.replace("root 7 (Container Table)", "root 0xC (Small Allocator)"), 0x48, 0xC)
    assert _n205_said(fixed.replace("root 7 (Container Table)", "root 8 (Container Table copy 2)"), 0x48, 8)
    assert not _n205_said(fixed.replace("26100", "the"), 0x48, 7)
    assert not _n205_said("26100.x also requires roots 0xC, 7 and 8 to verify; it would reject a copy (LCN 0x48)",
                          0x48, 7)
    # S1: one finding over two warning lines; but not a "26100 ... reject" statement three statements away
    two = ("[forefst] WARNING: root 7 (Container Table) of the checkpoint copy at LCN 0x48 does not verify against "
           "its digest\n[forefst]          the 26100 driver would reject that copy (Insider 29574 rejects only on a "
           "read error); it is read anyway")
    assert _n205_said(two, 0x48, 7)
    far = two.replace("\n", "\n[forefst] a\n[forefst] b\n[forefst] c\n")
    assert not _n205_said(far, 0x48, 7)
    # 11
    cur = ("  [WARN] the NEWEST checkpoint (the copy the driver would use) failed its self-checksum; the volume's most "
           "authoritative structure is damaged")
    stale = ("[forefst] WARNING: the newest checkpoint (LCN 0x48, vclock 64) failed its self-checksum (CRC32-C); the "
             "volume was read from an OLDER checkpoint (LCN 0x88, vclock 63), so this view is STALE")
    assert _false_driver_copy(cur, 0x88) and _false_driver_copy(cur, None)
    assert not _driver_uses(cur + "\n" + stale + "\n  Driver version:     3.14", 0x88)
    fixed = ("  [WARN] the newest checkpoint (LCN 0x48) failed its self-checksum; the driver skips it and would use "
             "the older copy at LCN 0x88 (vclock 63)")
    assert not _false_driver_copy(fixed, 0x88) and _driver_uses(fixed, 0x88)
    refused = "  [WARN] no checkpoint copy passes its self-checksum: the driver would refuse to mount this volume"
    assert _driver_refuses(refused) and not _false_driver_copy(refused, None)
    assert not _driver_refuses(cur + "\n  Driver version:     3.14")
    # M3: the false parenthesis is not excused by the passing LCN elsewhere, nor by a refusal appended
    wrong = cur + "; the volume was read from the older copy at LCN 0x88"
    assert _false_driver_copy(wrong, 0x88) and not _driver_uses(wrong, 0x88)
    assert _false_driver_copy(cur + "; the driver would refuse to mount", None)
    right = ("  [WARN] the newest checkpoint (LCN 0x48) failed its self-checksum; the volume was read from LCN 0x88 "
             "(the copy the driver would use)")
    assert not _false_driver_copy(right, 0x88)
    assert not _false_driver_copy("  [WARN] both copies failed: the driver would use neither", None)
    # 12 (S4: any case)
    assert _says_a_copy_failed("  CHKP #1: cluster 0x48 -> 0x48000  vc=64 ac=61  (self-checksum FAILED)", (0x48,))
    assert _says_a_copy_failed("  CHKP #1: cluster 0x48 -> 0x48000  vc=64 ac=61  (self-checksum failed)", (0x48,))
    # 13
    assert _compression_line("  Compression:        Not configured") == "Not configured"
    shown = "  Format:      LZ4\n  Level:       9\n  Chunk size:  0x8000 (32.0 KB)"
    assert _lz4_policy_shown(shown) and not _lz4_policy_shown(shown.replace("LZ4", "None"))
