"""1.13.2 RED cases for fix group G2c (group 2's close-out): N343, N345-N348, N350-N354, N356, N337 widened, and the
decision-28 control.

Context: `analysis/reports/v1.13.2/fixes/G2c_CONTEXT.md` (decisions 20-29 bind), RUNNING_LOG rows N337, N343-N356,
`fixes/REVIEW_G2_correctness_round2.md` (section 2.1 grid, section 8 O1, O4, O5, O6, O9), `fixes/REVIEW_G2_tests_round2.md`
(T4, T5), `fixes/GOLDEN_G2.md` section 6.1, `fixes/GOLDEN_G2_challenge.md` (O1, O5, O6), `fixes/GOLDEN_G2_critic.md`
(items 1, 2, 6). Report, with every node's observed failure before the fix: `analysis/reports/v1.13.2/fixes/FIX_G2c.md`.

What each RED asserts
---------------------
 1 N343  a root 0xC, 7 or 8 that does not verify against the checkpoint copy NOT in use is said, with the shared text,
         by exactly the commands that exit 2 for a self-checksum failure on that copy (grid row C08: forefst `summary`,
         `fastsummary`, `integrity`, refsanalysis `summary`, bare `supb`, `supb --verify`), and they exit 2; the
         bootstrap-only commands keep exit 0 (V-a, controls); `integrity --checksums` no longer prints PASS over it;
         `integrity`'s tie NOTE says that a copy whose roots do not verify is reported.
 2 N345  refsanalysis `summary++` `Symlinks:` over a 0x540 walk that raised or recorded damage; `summary --json`
         `schema_tables` over a root-3 walk that raised or recorded damage; the security / reparse / trash counts when
         their OID is missing from an incomplete object map -- "unreadable" (text) and null or named (JSON), A3's
         convention. A complete map without those OIDs (the synthetic volume) still prints 0 (control).
 3 N346  refsanalysis `supb` states a superblock condition once (A1 fallback, decisions 26, 27.1, 27.3), not on stderr
         AND as a stdout NOTE; the other commands already say it once (control, as N341's).
 4 N347  `verify-bundle` on a whole bundle of a volume with findings: exit 2 kept (rc_escalate), the report says the
         bundle is whole AND names the volume's finding; never "verify-bundle: PASS" beside exit 2.
 5 N348  forefst `details` path mode: "path not found" after a recorded skip exits 2 and says it is not evidence of
         absence (as refsanalysis `details`); a genuine not-found still exits 1 (control).
 6 N350  bundle input: `summary` and `integrity` print the source volume's offsets or label them as offsets in the
         bundle (with the source partition start); `integrity` names the bundle, not the temporary file.
 7 N351  (harness) the golden dedup, run as verify.sh runs it, re-runs a row in the generator's environment: a row whose
         only variance is the stdout/stderr interleaving is not rewritten (planted equivalent of winsiderv2
         `deleted --full`); a genuine starved-worker row is still repaired (control).
 8 N352  N215's "unknown" compression text on the 2 TB corpus witness says what was read: the page fails its root's
         digest, its table id; and claims no cause.
 9 N353  refsanalysis `chkp` selects as every other caller (`require_roots`): when the newest copy has no readable root
         list, it states the conditions of the copy a volume reader uses.
10 N337  `help containers` states its exit codes; `help chkp` names the superblock conditions under which it exits 2.
   wide
11 N354  (decision 29) VBR+0x40 = 0 is a finding, worded neutrally with one shared text (the value, `refsutil fixboot`,
         the default), in forefst `summary`, `fastsummary`, `integrity`, refsanalysis `summary` and `boot --verify`
         (exit 2 there; `boot --verify` has one row for it and no FAIL row); every other command keeps its exit code.
12 N356  `integrity`: "1 FAILED its self-checksum" (not "their"); refsanalysis `containers` prints its N332 warning as
         a line of its own, not as a continuation of the `Checkpoint VC:` line.
13 d28   (controls only) a +0x10/+0x60 divergence on the checkpoint copy NOT in use exits 2 in every checkpoint-reading
         command of both tools.

Volumes and discipline: as test_1132_red_g2_d27.py -- the a_bootstrap `vol` fixture (``[synthetic]`` / ``[image]``,
imported by name), ``@_red`` = ``xfail(strict=True, raises=AssertionError)``, only a plain ``assert`` states the defect,
``_fx`` for a fixture that is not what the case needs, ``_keep`` for a property the current tool already has, every RED
has a control that passes now, and every oracle is checked first on the undamaged volume. The marks were removed when
the fix landed (FIX_G2c.md): the unmarked file fails against the step's pre-fix tools (`fixes/prefix_G2c/`) at the
REDs' plain asserts and passes on the fixed tree. Read-only corpus images: the
2 TB `win11refs2tmillionsofactions.raw` (N352) and the fixboot witness (N354), skipped when absent. N351 reads the
harness from $G2C_VERIFICATION_DIR (default: <repo>/../analysis/verification), skipped when absent.
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jint                              # noqa: E402  (K21 / K10 readers)
from conftest import jdoc                              # noqa: E402  (K21: internal names)

import test_1132_red_a_bootstrap as _AB                   # noqa: E402
from test_1132_red_a_bootstrap import (                  # noqa: E402
    RedFixtureError, _fx, _keep, _ctx, damage_supb, damage_chkp, make_tie, zero_ot_root, _root_list, _FAIL,
    _lcn_re, FOREFST, REFSANALYSIS, CS, CHKP_DESC, CLOCK_OLD, CLOCK_NEW)
from test_1132_red_group2 import (                       # noqa: E402
    IMAGE_ONLY, _statements, _n205_said, _root_named, _root_ref_offset, _root_page, plant_root_failure,
    _N205_ROOTS)
from test_1132_red_group2b import (                      # noqa: E402
    plant_unknown_type, _said_unknown_type, _json_text, _edit_vbr, _BOOT_ROWS, _d26_statements, damage_d26)
from test_1132_red_g2_d27 import (                       # noqa: E402
    damage_d27_1, _d27_1_statements, _runner, _oid_root, _label_value, _json_marks_unreadable, _N338_TABLES, _boot,
    zero_root_page, _exit2_lines)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

vol = _AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module
SYNTHETIC_ONLY = pytest.mark.parametrize("vol", ["synthetic"], indirect=True)

_ROOT_IDS = ["root0xC", "root7", "root8"]


def _run_split(tool, path, *args, cwd, cli=(), env=None):
    """(rc, stdout, stderr) of one tool run; a crash or a timeout is a fixture error."""
    cmd = [sys.executable, "-B", tool, path] + list(args) + list(cli)
    try:
        r = UW.run(cmd, capture_output=True, text=True, timeout=_AB.TIMEOUT, cwd=cwd, env=env)
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed:\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 1. N343 -- a root 0xC/7/8 failure on the checkpoint copy NOT in use
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix (review 1's grid row C14, re-measured here on both volumes): every command exits 0; the
# failure reaches only `integrity --json` (`redundancy/backup_copies/checkpoints[1]/root_fail`); `integrity --checksums`
# prints "Verdict: PASS". The same copy failing its self-checksum (grid row C08) exits 2 in forefst `summary`,
# `fastsummary`, `integrity`, refsanalysis `summary`, `supb`, `supb --verify` and 0 elsewhere (V-a) -- the control below
# pins that set, and the RED requires the same set for the root failure.

def plant_root_failure_on(v, lcn, idx):
    """group2's plant_root_failure, on the copy at `lcn`: one digest byte of its root `idx` reference flipped and the
    copy re-sealed (Vol.reseal: fd._recompute_self_checksum, cross-checked with the module's own CRC32-C). The other
    copy is untouched and still verifies that root (refs_crc64 computed here)."""
    g = v.geo
    other = g.hi if lcn == g.lo else g.lo
    blk, oblk = v.block(lcn), v.block(other)
    ro, oro = _root_ref_offset(blk, idx), _root_ref_offset(oblk, idx)
    _fx(blk[ro + 0x22] == 2 and blk[ro + 0x23] == 8 and F.le32(blk, ro + 0x24) == 8,
        "root %d: not a CRC64 page reference" % idx)
    lcns = _root_list(blk)[idx]
    _fx(lcns and _root_list(oblk)[idx] == lcns, "root %d: the two copies do not share the root page" % idx)
    page = _root_page(v, lcns)
    _fx(page[:4] == b"MSB+" and F.refs_crc64(page) == F.le64(blk, ro + 0x28) == F.le64(oblk, oro + 0x28),
        "root %d does not verify against both copies before the plant" % idx)

    def edit(b):
        b[ro + 0x28] ^= 0x01
    v.reseal(lcn, edit, CHKP_DESC)
    _fx(F.refs_crc64(_root_page(v, lcns)) != F.le64(v.block(lcn), ro + 0x28),
        "root %d still verifies against the copy at 0x%x" % (idx, lcn))
    _fx(F.refs_crc64(_root_page(v, lcns)) == F.le64(v.block(other), oro + 0x28),
        "root %d no longer verifies against the other copy" % idx)
    _fx(v.verifies(lcn) is True and v.verifies(other) is True, "a copy fails its self-checksum after the plant")


_DOES_NOT = re.compile(r"(?i)does not (?:match|read|verify)|cannot be read|\bfail")


def _n343_said(out, lcn, idx):
    """Statements naming the copy at `lcn` and root `idx` with what is wrong with it (does not match / read / verify,
    or a failure word)."""
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and _root_named(s, idx) and _DOES_NOT.search(s)]


# N578 (the auditor's RC1 check O1): `deleted` is in the set that says the copy not in use's conditions and exits 2 --
# its checkpoint comparison READS that copy. It was in `_N343_QUIET`, so the C08 control below asserted the defect (a
# failed superseded copy compared, exit 0).
_N343_SAY = {"fd-summary": (FOREFST, ("summary",)), "fd-fastsummary": (FOREFST, ("fastsummary",)),
             "fd-integrity": (FOREFST, ("integrity",)), "ra-summary": (REFSANALYSIS, ("summary",)),
             "ra-supb": (REFSANALYSIS, ("supb",)), "ra-supb-verify": (REFSANALYSIS, ("supb", "--verify")),
             "fd-deleted": (FOREFST, ("deleted",))}
_N343_LIST = ("fd-summary", "fd-fastsummary", "fd-integrity", "ra-summary")    # print the shared redundancy list
_N343_QUIET = {"fd-files": (FOREFST, ("files",)), "fd-search": (FOREFST, ("search", "ok")),
               "fd-timeline": (FOREFST, ("timeline",)),
               "ra-files": (REFSANALYSIS, ("files",)), "ra-chkp": (REFSANALYSIS, ("chkp",)),
               "ra-chkp-verify": (REFSANALYSIS, ("chkp", "--verify")), "ra-containers": (REFSANALYSIS, ("containers",))}


@pytest.mark.parametrize("idx", _N205_ROOTS, ids=_ROOT_IDS)
@pytest.mark.parametrize("cmd", sorted(_N343_SAY))
def test_n343_a_root_failure_of_the_copy_not_in_use_is_said_and_exits_2(vol, cmd, idx):
    tool, args = _N343_SAY[cmd]
    rc0, out0 = vol.run(tool, *args)
    _fx(rc0 == 0 and not _n343_said(out0, vol.geo.hi, idx), "%s on the undamaged volume" % cmd + _ctx(vol, rc0, out0))
    plant_root_failure_on(vol, vol.geo.hi, idx)
    rc, out = vol.run(tool, *args)
    assert _n343_said(out, vol.geo.hi, idx), (
        "%s must say that root 0x%x does not verify against the checkpoint copy not in use (LCN 0x%x)"
        % (cmd, idx, vol.geo.hi)) + _ctx(vol, rc, out)
    if cmd in _N343_LIST:
        assert _n205_said(out, vol.geo.hi, idx), "%s: the shared text carries what the 26100 driver's first pass " \
            "does with such a copy" % cmd + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2, as for a self-checksum failure of that copy (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", sorted(_N343_QUIET))
def test_n343_control_the_bootstrap_only_commands_keep_exit_0(vol, cmd):
    """V-a (decision 20.3): a damaged copy NOT in use leaves the commands that only read through the copy in use at
    exit 0, saying nothing about it (grid row C14 today; it must stay so)."""
    tool, args = _N343_QUIET[cmd]
    rc0, _out0 = vol.run(tool, *args)          # 0, except the synthetic volume's `chkp --verify` (its CPC row: 2)
    plant_root_failure_on(vol, vol.geo.hi, 7)
    rc, out = vol.run(tool, *args)
    assert rc == rc0 and not _n343_said(out, vol.geo.hi, 7), "%s: %d -> %d" % (cmd, rc0, rc) + _ctx(vol, rc, out)


def test_n343_control_the_c08_set(vol):
    """Grid row C08 (the copy not in use fails its self-checksum): the seven commands of `_N343_SAY` and refsanalysis
    `chkp --verify` (N580) exit 2, the others keep the exit code of the undamaged volume."""
    want = dict({c: 2 for c in _N343_SAY}, **{c: vol.run(t, *a)[0] for c, (t, a) in _N343_QUIET.items()})
    want["ra-chkp-verify"] = 2      # N580 (O3): `--verify` checks each other copy's self-checksum (its roots: `supb --verify`)
    damage_chkp(vol, vol.geo.hi)
    got = {}
    for cmd, (tool, args) in sorted(list(_N343_SAY.items()) + list(_N343_QUIET.items())):
        got[cmd] = vol.run(tool, *args)[0]
    assert got == want, got


@pytest.mark.parametrize("cmd", ["fd-summary", "fd-integrity"])
def test_n343_a_root_failure_of_the_tied_copy_not_in_use_is_said_and_exits_2(vol, cmd):
    """On a tie the copy in use is slot 0 (F1); a root failure of the tied slot-1 copy is the same condition."""
    tool, args = _N343_SAY[cmd]
    make_tie(vol, slot0_higher=False)
    rc0, out0 = vol.run(tool, *args)
    _fx(rc0 == 0, "an undamaged tie exits 0" + _ctx(vol, rc0, out0))
    plant_root_failure_on(vol, vol.geo.hi, 7)
    rc, out = vol.run(tool, *args)
    assert _n343_said(out, vol.geo.hi, 7), "the tied copy's root 7 failure must be said" + _ctx(vol, rc, out)
    assert rc == 2, "rc=%d" % rc + _ctx(vol, rc, out)


def test_n343_integrity_checksums_prints_no_pass_over_it(vol):
    rc0, out0 = vol.run(FOREFST, "integrity", "--checksums")
    _fx(rc0 == 0 and re.search(r"(?m)^Verdict: PASS\b", out0), "the undamaged volume passes" + _ctx(vol, rc0, out0))
    plant_root_failure_on(vol, vol.geo.hi, 7)
    rc, out = vol.run(FOREFST, "integrity", "--checksums")
    assert not re.search(r"(?m)^Verdict: PASS\b", out), "Verdict: PASS over a copy whose root 7 fails" \
        + _ctx(vol, rc, out)
    assert rc == 2, "rc=%d" % rc + _ctx(vol, rc, out)


def _tie_note(out):
    m = re.search(r"(?ms)^\s*NOTE: both checkpoint copies share the top clock.*?(?=^\s*(?:Superblock copies|\[))", out)
    _fx(m, "no tie NOTE printed" + out[-3000:])
    return " ".join(m.group(0).split())


def test_n343_integrity_tie_note_says_a_root_failure_is_reported(vol):
    """The NOTE says the tool checks roots 0xC, 7 and 8 against each copy's digests; it must also say that a copy
    whose roots do not verify is reported (it was not, for the copy not in use)."""
    make_tie(vol, slot0_higher=False)
    rc, out = vol.run(FOREFST, "integrity")
    note = _tie_note(out)
    _keep(re.search(r"(?i)roots? 0xC, 7 and 8", note), "the NOTE names the roots it checks: %r" % note)
    assert re.search(r"(?i)\breport", note), "the tie NOTE must say a copy whose roots do not verify is reported: %r" \
        % note


def test_n343_control_the_tie_note_is_printed_on_a_tie_only(vol):
    rc, out = vol.run(FOREFST, "integrity")
    assert rc == 0 and "share the top clock" not in out, _ctx(vol, rc, out)
    make_tie(vol, slot0_higher=False)
    rc, out = vol.run(FOREFST, "integrity")
    assert rc == 0 and _tie_note(out), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 2. N345 -- N338's class: counts over a table that was not read
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _symlink_case(v, tmp_path, how):
    vlcns, plcn = _oid_root(v, 0x540)
    fail = None
    if how == "zeroed":
        _fx(v.read(v.geo.ps + plcn * CS, 4) == b"MSB+", "OID 0x540's root page is not an MSB+ page")
        v.zero(v.geo.ps + plcn * CS, 0x4000)
    else:
        fail = vlcns
    return fail


@IMAGE_ONLY
@pytest.mark.parametrize("how", ["zeroed", "raised"])
def test_n345_summary_plus_symlinks_over_an_unread_reparse_index_is_unreadable(vol, how, tmp_path):
    rc0, out0, _f0 = _runner(vol, tmp_path, REFSANALYSIS, ["summary++"])
    _fx(rc0 == 0 and re.match(r"^\d+$", _label_value(out0, "Symlinks")), "undamaged Symlinks: %r"
        % _label_value(out0, "Symlinks") + _ctx(vol, rc0, out0))
    _rj0, outj0, _fj0 = _runner(vol, tmp_path, REFSANALYSIS, ["summary++", "--json"])
    j0 = _json_text(outj0, "summary++ --json")
    _fx(isinstance(j0.get("symlinks"), int) and not _json_marks_unreadable(j0, "symlinks"), "undamaged JSON %r"
        % j0.get("symlinks"))
    fail = _symlink_case(vol, tmp_path, how)
    rc, out, fired = _runner(vol, tmp_path, REFSANALYSIS, ["summary++"], fail_vlcns=fail)
    _fx(how == "zeroed" or fired, "the planted walk failure did not fire")
    _keep("unreadable" in _label_value(out, "Reparse index"), "N338: Reparse index reads unreadable" + _ctx(vol, rc, out))
    val = _label_value(out, "Symlinks")
    assert "unreadable" in val.lower() and not re.match(r"^\d", val), "Symlinks: %r" % val + _ctx(vol, rc, out)
    _rj, outj, _fj = _runner(vol, tmp_path, REFSANALYSIS, ["summary++", "--json"], fail_vlcns=fail)
    j = _json_text(outj, "summary++ --json")
    assert _json_marks_unreadable(j, "symlinks"), "JSON symlinks=%r is presented as a count" % j.get("symlinks")


@pytest.mark.parametrize("how", ["zeroed", "raised"])
def test_n345_summary_json_schema_tables_over_an_unread_schema_root(vol, how, tmp_path):
    rj0, outj0, _f = _runner(vol, tmp_path, REFSANALYSIS, ["summary", "--json"])
    j0 = _json_text(outj0, "summary --json")
    _fx(rj0 == 0 and isinstance(j0.get("schema_tables"), int) and not _json_marks_unreadable(j0, "schema_tables"),
        "undamaged schema_tables=%r" % j0.get("schema_tables"))
    fail = None
    if how == "zeroed":
        zero_root_page(vol, 3)
    else:
        f, ps, cs, tr, roots, _om, _a, _b, _c = _boot(vol)
        f.close()
        fail = list(roots[3])
    rj, outj, fired = _runner(vol, tmp_path, REFSANALYSIS, ["summary", "--json"], fail_vlcns=fail)
    _fx(how == "zeroed" or fired, "the planted walk failure did not fire")
    j = _json_text(outj, "summary --json")
    _keep("Schema Table" in (j.get("root_tables_unreadable") or []), "root 3 is named unreadable: %r"
          % j.get("root_tables_unreadable"))
    assert _json_marks_unreadable(j, "schema_tables"), "JSON schema_tables=%r is presented as a count" \
        % j.get("schema_tables")


_N345_TOOLS = {"fd-summary": (FOREFST, "summary"), "fd-fastsummary": (FOREFST, "fastsummary"),
               "ra-summary-plus": (REFSANALYSIS, "summary++")}


@pytest.mark.parametrize("tool", sorted(_N345_TOOLS))
def test_n345_counts_of_oids_missing_from_an_incomplete_object_map_are_unreadable(vol, tool):
    path, cmd = _N345_TOOLS[tool]
    zero_ot_root(vol)                                     # every OID is missing; the walk records the zeroed page
    rc, out = vol.run(path, cmd)
    _keep(rc == 2, "the zeroed Object-Table root exits 2" + _ctx(vol, rc, out))
    vals = {label: _label_value(out, label) for _o, label, _k in _N338_TABLES.values()}
    assert all("unreadable" in v.lower() and not re.match(r"^\d", v) for v in vals.values()), \
        "counts printed over an incomplete object map: %r" % vals + _ctx(vol, rc, out)
    rcj, outj = vol.run(path, cmd, "--json")
    j = _json_text(outj, cmd + " --json")
    assert all(_json_marks_unreadable(j, key) for _o, _l, key in _N338_TABLES.values()), \
        "JSON %r" % {key: j.get(key) for _o, _l, key in _N338_TABLES.values()}


@SYNTHETIC_ONLY
@pytest.mark.parametrize("tool", sorted(_N345_TOOLS))
def test_n345_control_absent_oids_on_a_complete_map_count_0(vol, tool):
    """The synthetic volume's object map is complete and holds none of 0x530, 0x540, 0xD: 0 is the truth there."""
    path, cmd = _N345_TOOLS[tool]
    rc, out = vol.run(path, cmd)
    vals = {label: _label_value(out, label) for _o, label, _k in _N338_TABLES.values()}
    assert rc == 0 and all(re.match(r"^0\b", v_) for v_ in vals.values()), (vals, _ctx(vol, rc, out))
    rcj, outj = vol.run(path, cmd, "--json")
    j = _json_text(outj, cmd + " --json")
    assert all(j.get(key) == 0 and not _json_marks_unreadable(j, key) for _o, _l, key in _N338_TABLES.values()), j


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 3. N346 -- refsanalysis `supb` says a superblock condition twice (stderr AND a stdout NOTE)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _a1_said(out, v):
    b0 = v.geo.backups[1]          # C2 ST-S1 (a2): end-2, the copy read after the primary fails (Q3; was end-3)
    return [s for s in _statements(out) if _lcn_re(b0).search(s) and re.search(r"(?i)\bbackup\b", s)
            and re.search(r"(?i)\bread\b", s)]


def _n346_case(v, case):
    """Plant one superblock condition; returns its matcher (out -> the statements that say it)."""
    if case == "a1-fallback":
        damage_supb(v, "primary")
        return lambda out: _a1_said(out, v)
    if case == "d26":
        damage_d26(v)
        return _d26_statements
    if case == "d27-1":
        b = damage_d27_1(v)
        return lambda out: _d27_1_statements(out, b)
    if case == "d27-3-primary":
        plant_unknown_type(v, v.geo.supb, 0x78, 0x03)
        return lambda out: _said_unknown_type(out, v.geo.supb, 0x03)
    raise RedFixtureError(case)


# C2 ST-S1: the copy read after the primary fails is end-2 (a2, Q3), and the first signed backup in slot order is
# end-2 (a1, the driver's order primary, N-2, N-3; `damage_d27_1`): RED until B15 lands
# RED 1.13.2 B15 (C2 ST-S1 a2) on "a1-fallback": the fallback statement must name end-2 as the copy read (Q3); the tool
# names end-3; (C2 ST-S1 a1) on "d27-1": the first signed backup in slot order is end-2; the tool reads end-3 (the strict
# xfail marks removed: fixed in step C2, area supb)
_N346_CASES = ["a1-fallback", "d26", "d27-1", "d27-3-primary"]


@pytest.mark.parametrize("case", _N346_CASES)
def test_n346_supb_says_a_superblock_condition_once(vol, case):
    said = _n346_case(vol, case)
    rc, out = vol.run(REFSANALYSIS, "supb")
    _keep(rc == 2, "exit 2 (decisions 26, 27.x, A1)" + _ctx(vol, rc, out))
    s = said(out)
    assert len(s) == 1, "supb says the %s condition %d times: %r" % (case, len(s), s) + _ctx(vol, rc, out)


@pytest.mark.parametrize("case", _N346_CASES)
def test_n346_control_files_and_chkp_say_it_once(vol, case):
    said = _n346_case(vol, case)
    for tool, args in ((FOREFST, ("files",)), (REFSANALYSIS, ("chkp",))):
        rc, out = vol.run(tool, *args)
        assert rc == 2 and len(said(out)) == 1, (args, said(out)) + (_ctx(vol, rc, out),)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 4. N347 / 6. N350 -- bundle input
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _export_bundle(v, dest):
    """`export metadata` of the volume into `dest` (a fresh directory); returns its exit code."""
    rc, out, err = _run_split(FOREFST, v.path, "export", "metadata", dest, cwd=os.path.dirname(v.path), cli=v.geo.cli)
    _fx(os.path.exists(os.path.join(dest, "manifest.json")), "no bundle written: rc=%d\n%s\n%s" % (rc, out[-2000:],
                                                                                                    err[-2000:]))
    return rc


def _verify_bundle(bdir):
    return _run_split(FOREFST, bdir, "verify-bundle", cwd=os.path.dirname(bdir))


def _n347_plant(v, case):
    if case == "superblock-fallback":
        damage_supb(v, "primary")
        # C2 ST-S1 (a2): the copy read after the primary fails is end-2 (Q3; was end-3)
        return lambda out: [s for s in _statements(out) if _lcn_re(v.geo.backups[1]).search(s)
                            and re.search(r"(?i)superblock|SUPB", s)]
    if case == "root-of-the-copy-in-use":
        plant_root_failure(v, 7)
        return lambda out: [s for s in _statements(out) if _lcn_re(v.geo.lo).search(s) and _root_named(s, 7)]
    raise RedFixtureError(case)


@IMAGE_ONLY                 # the synthetic volume's Object Table is empty: its bundle is refused as EMPTY
@pytest.mark.parametrize("case", [
    # RED 1.13.2 B15 (C2 ST-S1 a2): the report must name end-2, the copy read after the primary fails (Q3); the volume
    # is read from end-3 (the strict xfail mark removed: fixed in step C2, area supb)
    "superblock-fallback",
    "root-of-the-copy-in-use"])
def test_n347_verify_bundle_of_a_volume_with_a_finding_says_whole_and_names_it(vol, case, tmp_path):
    b0 = str(tmp_path / "bundle_undamaged")
    _fx(_export_bundle(vol, b0) == 0, "the undamaged volume exports with exit 0")
    rc0, out0, err0 = _verify_bundle(b0)
    _fx(rc0 == 0 and re.search(r"(?m)^verify-bundle: PASS\b", out0), "a whole bundle of the undamaged volume passes"
        + "\n" + out0 + err0)
    shutil.rmtree(b0)
    said = _n347_plant(vol, case)
    b1 = str(tmp_path / "bundle_damaged")
    _export_bundle(vol, b1)
    rc, out, err = _verify_bundle(b1)
    _keep(rc == 2, "exit 2 (rc_escalate: the volume's finding)" + "\n" + out + err)
    _keep(not re.search(r"(?m)^\s*PROBLEM:", out), "the bundle itself is whole (no PROBLEM line)\n" + out)
    assert not re.search(r"(?m)^verify-bundle: PASS\b", out), "a bare PASS beside exit 2:\n" + out
    assert re.search(r"(?i)\bwhole\b", out), "the report must say the bundle is whole:\n" + out
    assert said(out), "the report (stdout) must name the volume's finding:\n" + out


def _offset_label(out, ps):
    """A statement saying the offsets are in the bundle (not the source image) and naming the source partition start."""
    return [s for s in _statements(out) if re.search(r"(?i)\boffsets?\b", s) and re.search(r"(?i)\bbundle\b", s)
            and _lcn_re(ps).search(s)]


def _supb_primary_offset(out):
    m = re.findall(r"(?im)^\s*(?:SUPB primary|\[PRIMARY\])\s+LCN 0x1e \(offset (0x[0-9a-f]+)\)", out)
    _fx(m, "no SUPB primary line" + out[-3000:])
    return [int(x, 16) for x in m]


@IMAGE_ONLY
@pytest.mark.parametrize("cmd", ["summary", "integrity"])
def test_n350_bundle_offsets_are_the_source_volumes_or_labelled(vol, cmd, tmp_path):
    ps = vol.geo.ps
    rc0, out0 = vol.run(FOREFST, cmd)
    _fx(rc0 == 0 and _supb_primary_offset(out0) == [ps + 0x1E * CS], "the image prints absolute offsets"
        + _ctx(vol, rc0, out0))
    b = str(tmp_path / "bundle")
    _fx(_export_bundle(vol, b) == 0, "export exits 0")
    with open(os.path.join(b, "manifest.json"), encoding="utf-8") as fh:
        _fx(jint(jdoc(json.load(fh), F._BUNDLE_KEYS).get("partition_start_bytes")) == ps, "the manifest records the partition start")
    rc, out, err = _run_split(FOREFST, b, cmd, cwd=str(tmp_path))
    offs = _supb_primary_offset(out)
    assert offs == [ps + 0x1E * CS] or _offset_label(out, ps), \
        "offsets of the temporary file, unlabelled: %r\n%s" % ([hex(x) for x in offs], out)
    if cmd == "integrity":
        img = re.findall(r"(?m)^\s*Image:\s+(.*)$", out)
        assert img and "rehydrated" not in img[0] and "forefst_bundle_" not in img[0], \
            "integrity names the temporary file: %r" % img


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 5. N348 -- forefst `details` path mode: "path not found" after a recorded skip
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_N348_PATH = "/test/ok.txt"                     # a 4-byte inline file of win11refsmini
_NOT_EVIDENCE = re.compile(r"(?i)not evidence|could not be read")


@IMAGE_ONLY
def test_n348_details_path_not_found_after_a_recorded_skip_exits_2(vol):
    rc0, out0 = vol.run(FOREFST, "details", _N348_PATH)
    _fx(rc0 == 0, "the path resolves on the undamaged image" + _ctx(vol, rc0, out0))
    rcn, outn = vol.run(FOREFST, "details", "/no/such/file")
    _keep(rcn == 1 and re.search(r"(?i)not found", outn), "a genuine not-found exits 1" + _ctx(vol, rcn, outn))
    zero_ot_root(vol)
    rc, out = vol.run(FOREFST, "details", _N348_PATH)
    _keep(re.search(r"(?i)path not found", out), "the lookup reports not found" + _ctx(vol, rc, out))
    assert rc == 2, "details recorded a skip and must exit 2, as refsanalysis details does (rc=%d)" % rc \
        + _ctx(vol, rc, out)
    assert [s for s in _statements(out) if re.search(r"(?i)not found", s) and re.search(r"(?i)not evidence", s)], \
        "the not-found line must say it is not evidence of absence" + _ctx(vol, rc, out)


def test_n348_control_a_genuine_not_found_still_exits_1(vol):
    rc, out = vol.run(FOREFST, "details", "/no/such/file")
    assert rc == 1 and re.search(r"(?i)not found", out) and not re.search(r"(?i)not evidence", out), _ctx(vol, rc, out)


@IMAGE_ONLY
def test_n348_control_refsanalysis_details_already_exits_2(vol):
    zero_ot_root(vol)
    rc, out = vol.run(REFSANALYSIS, "details", _N348_PATH)
    assert rc == 2 and _NOT_EVIDENCE.search(out), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 7. N351 (harness) -- the golden dedup re-runs a row in an environment the generator did not use
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# verify.sh runs the generator as `bash $VDIR/golden_gen.sh` and the dedup as `PYTHONUNBUFFERED=1 $PY
# $VDIR/golden_dedup_flakes.py ...`; the dedup's `--one-e4` re-run inherits the variable, so a row whose stdout and stderr
# interleave (winsiderv2 `deleted --full`, 38.9 MB, about 250 s) re-ran to a different hash and was rewritten as a
# "flake" (GOLDEN_G2 section 6.1). This is the planted equivalent: the REAL dedup (copied beside a planted generator that
# emits the row the way `emit_deleted_full` does, from a small program that writes a long stdout with stderr lines
# between its chunks), run with the environment verify.sh gives each of the two lines -- read from verify.sh itself, so
# the check follows the gate. The real row was also checked, before and after, by a script (FIX_G2c.md).

_N351_IMG = "analysis/rawdisk/disks/step7/winsiderv2.raw"           # a key only: the planted generator reads nothing
_N351_NOISY = r'''
import sys
for i in range(40):
    sys.stdout.write("%05d " % i + "x" * 1000 + "\n")
    if i % 7 == 3:
        sys.stderr.write("[forefst] WARNING: planted stderr line %d\n" % i)
'''
_N351_GEN = r'''#!/bin/bash
# planted golden_gen.sh: the one row emit_deleted_full would emit for "$4" (same capture, same hash)
set -u
img="$4"
out="$(%s "$(dirname "$0")/noisy.py" 2>&1)"; rc=$?
printf '%%s|%%s|rc=%%d|%%s\n' "$img" "forefst.py deleted --full" "$rc" "$(printf '%%s' "$out" | sha256sum | cut -d' ' -f1)"
'''


def _verification_dir():
    d = os.environ.get("G2C_VERIFICATION_DIR") or os.path.join(os.path.dirname(REPO), "analysis", "verification")
    if not all(os.path.isfile(os.path.join(d, x)) for x in ("verify.sh", "golden_dedup_flakes.py")):
        pytest.skip("no analysis/verification harness beside this tree (%s)" % d)
    return d


def _verify_sh_assignments(vdir, pattern):
    """The VAR=value assignments verify.sh puts in front of the command on its line matching `pattern`."""
    with open(os.path.join(vdir, "verify.sh"), encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh if re.search(pattern, ln) and not ln.lstrip().startswith("#")]
    _fx(len(lines) == 1, "verify.sh: one line expected for %r, found %r" % (pattern, lines))
    lead = re.match(r"^((?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*)", lines[0]).group(1).split()
    return dict(a.split("=", 1) for a in lead)


def _n351_setup(tmp_path):
    vdir = _verification_dir()
    d = tmp_path / "ver"
    d.mkdir()
    shutil.copy(os.path.join(vdir, "golden_dedup_flakes.py"), str(d))
    (d / "noisy.py").write_text(_N351_NOISY)
    (d / "golden_gen.sh").write_text(_N351_GEN % sys.executable)
    (d / "corpus.lst").write_text(_N351_IMG + "\n")
    base = {k: v for k, v in os.environ.items() if k != "PYTHONUNBUFFERED"}
    gen_env = dict(base, **_verify_sh_assignments(vdir, r"golden_gen\.sh\s*>\s*/tmp/v_golden\.txt"))
    dedup_env = dict(base, **_verify_sh_assignments(vdir, r"golden_dedup_flakes\.py\s+/tmp/v_golden\.txt"))

    def merged(env):
        return subprocess.run(["bash", "-c", '"%s" "%s" 2>&1' % (sys.executable, d / "noisy.py")], env=env,
                              capture_output=True, text=True).stdout
    _fx(merged(dict(base, PYTHONUNBUFFERED="1")) != merged(base), "the planted program's merged output does not depend "
        "on PYTHONUNBUFFERED: the check could not discriminate")
    r = subprocess.run(["bash", str(d / "golden_gen.sh"), str(d / "corpus.lst"), "forefstdev", "--one-e4", _N351_IMG],
                       env=gen_env, capture_output=True, text=True)
    row = r.stdout.strip()
    _fx(re.match(r"^%s\|forefst\.py deleted --full\|rc=0\|[0-9a-f]{64}$" % re.escape(_N351_IMG), row),
        "the planted generator emitted %r" % row)
    return d, row, dedup_env


def _n351_dedup(d, tmp_path, fresh_row, base_row, env):
    fresh, base = tmp_path / "fresh.txt", tmp_path / "base.txt"
    fresh.write_text(fresh_row + "\n")
    base.write_text(base_row + "\n")
    r = subprocess.run([sys.executable, str(d / "golden_dedup_flakes.py"), str(fresh), str(base)], env=env,
                       cwd=str(tmp_path), capture_output=True, text=True)
    _fx(r.returncode == 0 and "Traceback" not in r.stderr, "the dedup crashed: %s" % r.stderr[-2000:])
    return r.stdout + r.stderr, fresh.read_text()


def _zero_hash(row):
    return re.sub(r"\|[0-9a-f]{64}$", "|" + "0" * 64, row)


def test_n351_the_dedup_rewrites_nothing_when_only_the_stream_interleaving_could_differ(tmp_path):
    d, row, env = _n351_setup(tmp_path)
    out, fresh = _n351_dedup(d, tmp_path, row, _zero_hash(row), env)
    assert "re-ran" not in out and fresh == row + "\n", \
        "the dedup rewrote the generator's row (a false flake):\n%s\nfresh now: %s" % (out, fresh)


def test_n351_control_a_starved_worker_row_is_still_repaired(tmp_path):
    """A row whose hash is not what the generator produces (a starved worker's partial output) is re-run serially and
    replaced by the generator's value."""
    d, row, env = _n351_setup(tmp_path)
    starved = re.sub(r"\|[0-9a-f]{64}$", "|" + "1" * 64, row)
    out, fresh = _n351_dedup(d, tmp_path, starved, _zero_hash(row), env)
    assert "re-ran" in out and fresh.strip().rsplit("|", 1)[1] != "1" * 64, out


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 8. N352 -- N215's "unknown" compression text on a Container-Table root that fails its digest
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The 2 TB witness (read-only): the copy in use's roots 0xC, 7 and 8 all fail their digests; root 7's page carries table
# id 0xc and root 8's 0xb, so the tool's Container-Table selection (table id 0xb first) reads root 8's page, whose
# descriptor ends at +0x58. 1.13.2-dev said "holds no policy record where this tool reads it (its descriptor ends at
# +0x58)" and the code blamed an inner node -- v2's root page is an inner node too and its policy reads. The facts the
# text must carry are read here from the bytes.

_N352_WITNESS = "win11refs2tmillionsofactions.raw"


def _n352_facts(p):
    ps = F.find_refs_partition(p)[0]
    _fx(ps is not None, "no ReFS partition in the witness")
    with open(p, "rb") as f:
        cs = F.parse_vbr(f, ps)[0]
        sel = F.checkpoint_select(f, ps, cs, F.parse_supb(f, ps, cs), require_roots=True)
        use = sel["in_use"]
        ct = F._select_ct_root(f, ps, cs, use["roots"])
        ri = [i for i in (7, 8) if list(use["roots"][i]) == list(ct)]
        _fx(len(ri) == 1, "the Container-Table root read is not root 7 or 8")
        f.seek(ps + ct[0] * cs)
        pg = f.read(cs)
    _fx(pg[:4] == b"MSB+" and 0x50 + F.le32(pg, 0x50) < 0xE4 and ri[0] in {i for i, _w in use["root_fail"]},
        "the witness's Container-Table root page is not a short-descriptor page failing its digest")
    return ri[0], F.le64(pg, 0x48), ct[0]


@pytest.mark.parametrize("cmd", ["summary", "containers"])
def test_n352_unknown_compression_says_what_was_read(cmd, tmp_path):
    p = _corpus_image(_N352_WITNESS)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % _N352_WITNESS)
    ri, tid, lcn = _n352_facts(p)
    rc, out, err = _run_split(REFSANALYSIS, p, cmd, cwd=str(tmp_path))
    s = [x for x in _statements(out) if re.search(r"(?i)compression", x) and re.search(r"(?i)unknown|not read", x)]
    _fx(len(s) == 1, "one compression line expected: %r" % s)
    s = s[0]
    assert re.search(r"(?i)\bdigest\b", s) and re.search(r"(?i)does not match|\bfails?\b", s) \
        and re.search(r"(?i)\broot %d\b" % ri, s), "the page read fails root %d's digest: %r" % (ri, s)
    assert re.search(r"(?i)table id 0x0*%x\b" % tid, s), "its table id (0x%x) must be said: %r" % (tid, s)
    assert not re.search(r"(?i)inner node|header at", s), "a cause the bytes do not support: %r" % s


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 9. N353 -- refsanalysis `chkp` selects without `require_roots`
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Plant: the older copy's root 7 fails its digest (re-sealed), then the newest copy's root count (+0x90) is set to 0
# and re-sealed: it verifies but has no root list, so bootstrap (`require_roots=True`) reads the older copy and says
# its root 7 failure. Measured before the fix: `chkp` selects the newest copy (no root list), says nothing, rc 0.

def plant_no_root_list(v, lcn):
    def edit(b):
        struct.pack_into("<I", b, 0x90, 0)
    v.reseal(lcn, edit, CHKP_DESC)
    with open(v.path, "rb") as fh:
        _fx(F.parse_chkp(fh, v.geo.ps, CS, lcn)[2] == [], "the copy at 0x%x still has a root list" % lcn)


def _n353_plant(v):
    plant_root_failure_on(v, v.geo.hi, 7)
    plant_no_root_list(v, v.geo.lo)


@pytest.mark.parametrize("args", [("chkp",), ("chkp", "--verify")], ids=["chkp", "chkp-verify"])
def test_n353_chkp_states_the_conditions_of_the_copy_a_volume_reader_uses(vol, args):
    _n353_plant(vol)
    rc, out = vol.run(REFSANALYSIS, *args)
    assert _n205_said(out, vol.geo.hi, 7), "chkp must say that root 7 of the checkpoint copy a volume reader uses " \
        "(LCN 0x%x) does not verify" % vol.geo.hi + _ctx(vol, rc, out)
    assert rc == 2, "rc=%d" % rc + _ctx(vol, rc, out)


def test_n353_control_bootstrap_and_supb_read_the_older_copy(vol):
    _n353_plant(vol)
    for tool, args in ((FOREFST, ("files",)), (REFSANALYSIS, ("supb",))):
        rc, out = vol.run(tool, *args)
        assert rc == 2 and _n205_said(out, vol.geo.hi, 7), args + (_ctx(vol, rc, out),)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 10. N337 widened -- `help containers`, `help chkp`
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _help_text(cmd, tmp_path):
    rc, out, err = _run_split(REFSANALYSIS, "help", cmd, cwd=str(tmp_path))
    _fx(rc == 0 and "usage:" in out, "no help for %s" % cmd)
    return out


def test_n337w_help_containers_states_its_exit_codes(tmp_path):
    lines = _exit2_lines(_help_text("containers", tmp_path))
    j = " ".join(lines)
    assert lines, "help containers states no exit code"
    assert re.search(r"(?i)checkpoint", j) and _FAIL.search(j), "exit 2 when a checkpoint copy FAILED: %r" % lines
    assert re.search(r"(?i)\broots?\b", j), "exit 2 for a root 0xC/7/8 of the copy in use: %r" % lines
    assert re.search(r"\+0x10\b", j) and re.search(r"\+0x60\b", j), "exit 2 for a clock divergence: %r" % lines
    assert re.search(r"(?i)superblock", j), "exit 2 under the superblock conditions: %r" % lines


def test_n337w_help_chkp_names_the_superblock_conditions(tmp_path):
    lines = [ln for ln in _exit2_lines(_help_text("chkp", tmp_path)) if re.search(r"(?i)superblock", ln)]
    j = " ".join(lines)
    assert lines and re.search(r"(?i)\bbackup\b", j) and _FAIL.search(j) and re.search(r"(?i)cannot be verified", j), \
        "help chkp: exit 2 when the superblock copy read is a backup, a copy that failed, or cannot be verified: %r" \
        % lines


def test_n337w_control_help_chkp_states_its_checkpoint_exit_2(tmp_path):
    assert [ln for ln in _exit2_lines(_help_text("chkp", tmp_path)) if re.search(r"(?i)checkpoint", ln)]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 11. N354 (decision 29) -- VBR+0x40 = 0 is a finding, worded neutrally, with one shared text
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Plant: group2b's `_edit_vbr` + `_BOOT_ROWS["container_nonzero"]` (the primary VBR's +0x40 set to 0, re-sealed) -- the
# shape `refsutil fixboot` writes (one witness: step3c fixboottest, read-only below). Measured before the fix: the four
# summaries exit 0 and print "default (VBR+0x40 is zero)" beside the container size; `boot --verify` prints two FAIL
# rows (`container_nonzero`, `container_aligned`) and exits 2.

_N354_SAY = {"fd-summary": (FOREFST, ("summary",)), "fd-fastsummary": (FOREFST, ("fastsummary",)),
             "fd-integrity": (FOREFST, ("integrity",)), "ra-summary": (REFSANALYSIS, ("summary",)),
             "ra-boot-verify": (REFSANALYSIS, ("boot", "--verify"))}
_N354_KEEP = {"fd-files": (FOREFST, ("files",)), "ra-files": (REFSANALYSIS, ("files",)),
              "ra-supb": (REFSANALYSIS, ("supb",)), "ra-chkp": (REFSANALYSIS, ("chkp",)),
              "ra-containers": (REFSANALYSIS, ("containers",)), "ra-boot": (REFSANALYSIS, ("boot",))}
_N354_BAD = re.compile(r"(?i)\bFAIL(?:ED|S|URE)?\b|corrupt|damaged")
_N354_ROW = re.compile(r"(?i)container_nonzero|container_aligned|VBR\+0x40|container[ _]size")
_VERIFY_ROW = re.compile(r"^([a-z][a-z0-9_]+)\s{2,}(\S+)\s")


def _n354_said(out):
    """The shared finding: the field (VBR+0x40 / container size), its value 0, `refsutil fixboot`, the default 64 MiB --
    and no FAIL / corrupt / damaged word."""
    return [s for s in _statements(out) if re.search(r"(?i)VBR\+0x40|container size", s)
            and re.search(r"(?i)\b(?:is|holds|=)\s*0\b(?!x)", s) and re.search(r"(?i)refsutil fixboot", s)
            and re.search(r"(?i)\b64 MiB\b|\b0x0*4000000\b", s) and not _N354_BAD.search(s)]


def _n354_rows(out):
    """`boot --verify` table rows about the container size: (name, result, line)."""
    return [(m.group(1), m.group(2), ln) for ln in out.splitlines() for m in [_VERIFY_ROW.match(ln)]
            if m and _N354_ROW.search(ln)]


def plant_container_zero(v):
    _edit_vbr(v, _BOOT_ROWS["container_nonzero"])
    _fx(F.le64(v.read(v.geo.vbr, 512), 0x40) == 0, "VBR+0x40 is not 0")


@pytest.mark.parametrize("cmd", sorted(_N354_SAY))
def test_n354_a_zero_container_size_is_a_neutral_finding(vol, cmd):
    tool, args = _N354_SAY[cmd]
    rc0, out0 = vol.run(tool, *args)
    _fx(rc0 == 0 and not _n354_said(out0), "%s on the undamaged volume" % cmd + _ctx(vol, rc0, out0))
    plant_container_zero(vol)
    rc, out = vol.run(tool, *args)
    assert _n354_said(out), "%s must state the shared finding (VBR+0x40 = 0, refsutil fixboot, the 64 MiB default)" \
        % cmd + _ctx(vol, rc, out)
    if cmd == "ra-boot-verify":
        rows = _n354_rows(out)
        assert len(rows) == 1, "one row for the condition, not %d: %r" % (len(rows), rows) + _ctx(vol, rc, out)
        assert not [r for r in rows if r[1].upper().startswith("FAIL")], "a FAIL row: %r" % rows + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (decision 29; rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", sorted(_N354_KEEP))
def test_n354_control_every_other_command_keeps_its_exit_code(vol, cmd):
    tool, args = _N354_KEEP[cmd]
    rc0, out0 = vol.run(tool, *args)
    plant_container_zero(vol)
    rc, out = vol.run(tool, *args)
    assert rc == rc0 == 0, "%s: %d -> %d" % (cmd, rc0, rc) + _ctx(vol, rc, out)


def test_n354_control_the_formats_container_size_is_no_finding(vol):
    for cmd, (tool, args) in sorted(_N354_SAY.items()):
        rc, out = vol.run(tool, *args)
        assert rc == 0 and not _n354_said(out) and not re.search(r"(?i)refsutil fixboot", out), cmd + _ctx(vol, rc, out)


_N354_WITNESS = "win11refs2tmillionsofactions_aftersalvage_fixboottest.raw"


def _n354_witness():
    p = _corpus_image(_N354_WITNESS)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % _N354_WITNESS)
    ps = F.find_refs_partition(p)[0]
    with open(p, "rb") as fh:
        fh.seek(ps)
        _fx(F.le64(fh.read(512), 0x40) == 0, "the witness's VBR+0x40 is not 0")
    return p


@pytest.mark.parametrize("cmd", ["fd-summary", "ra-boot-verify"])
def test_n354_witness_the_fixboot_volume_states_the_finding(cmd, tmp_path):
    p = _n354_witness()
    tool, args = _N354_SAY[cmd]
    rc, out, err = _run_split(tool, p, *args, cwd=str(tmp_path))
    assert _n354_said(out + "\n" + err), "%s on the fixboot witness" % cmd + "\n" + (out + err)[-4000:]
    if cmd == "ra-boot-verify":
        rows = _n354_rows(out)
        assert len(rows) == 1 and not rows[0][1].upper().startswith("FAIL"), rows
    assert rc == 2


def test_n354_control_the_fixboot_witness_keeps_its_root_statement(tmp_path):
    p = _n354_witness()
    rc, out, err = _run_split(FOREFST, p, "files", cwd=str(tmp_path))
    with open(p, "rb") as fh:
        ps = F.find_refs_partition(p)[0]
        cs = F.parse_vbr(fh, ps)[0]
        use = F.checkpoint_select(fh, ps, cs, F.parse_supb(fh, ps, cs), require_roots=True)["in_use"]
    assert rc == 2 and _n205_said(out + "\n" + err, use["lcn"], 7), (out + err)[-3000:]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 12. N356 -- wording: "1 FAILED their"; the indented warning of `containers`
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _supb_copies_line(out):
    ln = [x for x in out.splitlines() if "Superblock copies:" in x]
    _fx(len(ln) == 1, "one 'Superblock copies:' line expected: %r" % ln)
    return ln[0]


def test_n356_integrity_one_failed_superblock_copy_is_its(vol):
    damage_supb(vol, "backup")
    rc, out = vol.run(FOREFST, "integrity")
    ln = _supb_copies_line(out)
    _keep(re.search(r"\b1 FAILED\b", ln), "one copy is counted as failed: %r" % ln)
    assert re.search(r"\b1 FAILED its self-checksum\b", ln), "grammar: %r" % ln


def test_n356_control_two_failed_copies_are_their(vol):
    for b in vol.geo.backups:
        vol.flip(vol.at(b, 0x50))
    rc, out = vol.run(FOREFST, "integrity")
    assert re.search(r"\b2 FAILED their self-checksum\b", _supb_copies_line(out)), _ctx(vol, rc, out)


def _indent(ln):
    return len(ln) - len(ln.lstrip())


def test_n356_containers_warning_is_a_line_of_its_own(vol):
    plant_root_failure(vol, 7)
    rc, out = vol.run(REFSANALYSIS, "containers")
    warn = [ln for ln in out.splitlines() if "WARNING:" in ln]
    vc = [ln for ln in out.splitlines() if "Checkpoint VC:" in ln]
    _keep(warn and len(vc) == 1 and rc == 2, "containers says the root failure (N332)" + _ctx(vol, rc, out))
    assert all(_indent(w) <= _indent(vc[0]) for w in warn), \
        "the warning is indented as a continuation of %r: %r" % (vc[0], warn)


def test_n356_control_chkp_prints_its_warning_at_the_margin(vol):
    plant_root_failure(vol, 7)
    rc, out = vol.run(REFSANALYSIS, "chkp")
    warn = [ln for ln in out.splitlines() if "WARNING:" in ln and _lcn_re(vol.geo.lo).search(ln)]
    assert warn and all(_indent(w) == 0 for w in warn), warn


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 13. Decision 28 (review 1 O6, review 2 T4) -- a clock divergence on the copy NOT in use: exit 2 everywhere (controls)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The older copy (hi) gets +0x10 = 58 while +0x60 stays 63, re-sealed: a divergence, not a checksum failure; lo stays in
# use. Grid row C16: every command of both tools that reads a checkpoint exits 2 and says it. These nodes pin it.

_DIVERGE_HI = CLOCK_OLD - 5


def plant_clock_divergence_not_in_use(v):
    g = v.geo

    def edit(b):
        struct.pack_into("<Q", b, 0x10, _DIVERGE_HI)
    v.reseal(g.hi, edit, CHKP_DESC)
    _fx(v.clocks(g.hi) == (_DIVERGE_HI, CLOCK_OLD) and v.clocks(g.lo) == (CLOCK_NEW, CLOCK_NEW),
        "the clocks are not 58/63 and 64/64: %r %r" % (v.clocks(g.hi), v.clocks(g.lo)))
    _fx(v.verifies(g.lo) is True and v.verifies(g.hi) is True, "a copy fails its self-checksum after the plant")


def _clock_said_not_in_use(out, lcn):
    return [s for s in _statements(out) if _lcn_re(lcn).search(s)
            and re.search(r"\+0x10\b[^;]{0,40}?\b%d\b" % _DIVERGE_HI, s)
            and re.search(r"\+0x60\b[^;]{0,40}?\b%d\b" % CLOCK_OLD, s)]


_D28 = {"fd-files": (FOREFST, ("files",)), "fd-search": (FOREFST, ("search", "ok")),
        "fd-timeline": (FOREFST, ("timeline",)), "fd-deleted": (FOREFST, ("deleted",)),
        "fd-summary": (FOREFST, ("summary",)), "fd-fastsummary": (FOREFST, ("fastsummary",)),
        "fd-integrity": (FOREFST, ("integrity",)), "ra-files": (REFSANALYSIS, ("files",)),
        "ra-summary": (REFSANALYSIS, ("summary",)), "ra-supb": (REFSANALYSIS, ("supb",)),
        "ra-supb-verify": (REFSANALYSIS, ("supb", "--verify")), "ra-chkp": (REFSANALYSIS, ("chkp",)),
        "ra-chkp-verify": (REFSANALYSIS, ("chkp", "--verify")), "ra-containers": (REFSANALYSIS, ("containers",))}


@pytest.mark.parametrize("cmd", sorted(_D28))
def test_d28_control_a_clock_divergence_on_the_copy_not_in_use_exits_2(vol, cmd):
    tool, args = _D28[cmd]
    plant_clock_divergence_not_in_use(vol)
    rc, out = vol.run(tool, *args)
    assert rc == 2 and _clock_said_not_in_use(out, vol.geo.hi), "%s (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


def test_d28_matcher():
    s = ("[forefst] WARNING: checkpoint copy at LCN 0x88: clock mismatch, page header +0x10 = %d vs selection clock "
         "+0x60 = %d (the driver compares +0x60; ...)" % (_DIVERGE_HI, CLOCK_OLD))
    assert _clock_said_not_in_use(s, 0x88) and not _clock_said_not_in_use(s, 0x48)
