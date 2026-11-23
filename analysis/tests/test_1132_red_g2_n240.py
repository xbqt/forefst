"""1.13.2 RED case for N240 (fix group 2): `refsanalysis chkp --verify` reports a failed check that is neither the
self-checksum nor the allocator-clock check, and exits 0.

Source: `analysis/reports/v1.13.2/RUNNING_LOG.md` N240 (the group-2 RED critic's observation N-a,
`red/RED_group2_critic.md`); PLAN_1.13.2 decision 21 ("`chkp --verify` exits 2 on any failed check") and decision 25.2
(every FAIL row of a `--verify` table exits 2). Written by the group-2 fixer before the fix, as process rule "RED
first" asks; its run on the pre-fix tools is recorded in `analysis/reports/v1.13.2/fixes/FIX_G2.md`.

The damage: the Object-Table root page (root 0) is zeroed. `chkp --verify` reads every root page's signature, so
it reports "Root 0 ... expected MSB+" and "1 check(s) FAILED", while its self-checksum and allocator-clock rows stay
[OK] (the checkpoint itself is intact). Only those two checks set the exit code before the fix.

Volumes:
* ``[synthetic]`` -- the N153 volume of `test_1132_red_b2_refsanalysis.py` (a_bootstrap's volume with the Container
  Table rows' clusters-per-container set, so the undamaged volume passes every check), built in pytest's tmp dir.
* ``[image]`` -- the a_bootstrap `vol` fixture's scratch copy of win11refsmini.raw (battery A3_oid_root_zero).

Discipline as in the other RED files: ``@_red`` = strict xfail on AssertionError; only a plain ``assert`` states the
defect; ``_fx`` for a fixture that is not what the case needs, ``_keep`` for a property the tool already has.
"""
import re
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)

import test_1132_red_a_bootstrap as _AB                   # noqa: E402
from test_1132_red_a_bootstrap import _fx, _keep, _ctx, zero_ot_root, REFSANALYSIS, CS  # noqa: E402
from test_1132_red_b2_refsanalysis import (              # noqa: E402
    _n153_volume, _run, _SYN, _result_line, _bad_rows, _write)

vol = _AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module
IMAGE_ONLY = pytest.mark.parametrize("vol", ["image"], indirect=True)

_OT_ROOT = _AB._SYN_ROOT_BASE * CS                       # the synthetic volume's root 0 page (16 KiB at LCN 0xA0)


def _c(rc, out, err):
    return "\n| rc=%s\n%s\n--- stderr ---\n%s" % (rc, out[-3000:], err[-1500:])


def _ok_row(out, rx):
    return re.search(r"(?im)^\s*\[OK\]\s*" + rx, out)


def _keep_non_checksum_failure(rc, out, ctx):
    """Kept: the table reports a failed check, and the two checks that set the exit code today pass."""
    _keep(_bad_rows(out) and "FAILED" in (_result_line(out) or ""), "chkp --verify reports a failed check" + ctx)
    _keep(_ok_row(out, r"CHKP self-checksum") and _ok_row(out, r"Allocator clock"),
          "the self-checksum and allocator-clock rows pass: the failed check is another one" + ctx)


@pytest.fixture
def n240_syn(tmp_path):
    good, bad = str(tmp_path / "undamaged.raw"), str(tmp_path / "ot_root_zeroed.raw")
    _n153_volume(good, fixboot=False)
    _n153_volume(bad, fixboot=False)
    with open(bad, "rb") as fh:
        fh.seek(_OT_ROOT)
        _fx(fh.read(4) == b"MSB+", "the synthetic root 0 page is not at 0x%x" % _OT_ROOT)
    _write(bad, _OT_ROOT, b"\0" * 0x4000)
    return tmp_path, good, bad


def test_n240_chkp_verify_exits_2_on_a_failed_non_checksum_check_synthetic(n240_syn):
    d, _good, bad = n240_syn
    rc, out, err = _run(REFSANALYSIS, bad, "chkp", "--verify", cli=_SYN, cwd=str(d))
    _keep_non_checksum_failure(rc, out, _c(rc, out, err))
    assert rc == 2, "chkp --verify reports a failed check and must exit 2 (rc=%d)" % rc + _c(rc, out, err)


@IMAGE_ONLY
def test_n240_image_chkp_verify_exits_2_on_a_failed_non_checksum_check(vol):
    zero_ot_root(vol)
    rc, out = vol.run(REFSANALYSIS, "chkp", "--verify")
    _keep_non_checksum_failure(rc, out, _ctx(vol, rc, out))
    assert rc == 2, "chkp --verify reports a failed check and must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


def test_n240_control_the_undamaged_synthetic_volume_passes_every_check_with_exit_0(n240_syn):
    d, good, _bad = n240_syn
    rc, out, err = _run(REFSANALYSIS, good, "chkp", "--verify", cli=_SYN, cwd=str(d))
    assert rc == 0 and not _bad_rows(out) and "checks passed" in (_result_line(out) or ""), _c(rc, out, err)


@IMAGE_ONLY
def test_n240_control_the_undamaged_image_passes_every_check_with_exit_0(vol):
    rc, out = vol.run(REFSANALYSIS, "chkp", "--verify")
    assert rc == 0 and not _bad_rows(out) and "checks passed" in (_result_line(out) or ""), _ctx(vol, rc, out)


def test_n240_control_the_plain_command_is_not_held_to_the_verify_rule(n240_syn):
    """Without --verify the command runs no check table: the same damaged volume exits 0 (N207's rule covers only a
    copy said to have FAILED, and this checkpoint copy is intact). Kept so the fix stays scoped to --verify."""
    d, _good, bad = n240_syn
    rc, out, err = _run(REFSANALYSIS, bad, "chkp", cli=_SYN, cwd=str(d))
    assert rc == 0 and not _bad_rows(out), _c(rc, out, err)
