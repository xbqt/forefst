"""1.13.2 RED cases for closing fix group A11: the exit-code sites A11's review and the completeness audit found after
the group ran (`analysis/reports/v1.13.2/NEXT_STEPS_2026-10-01.md` step 2; `fixes/FIX_A11.md`, closure section).

* K7 -- the plan's A11 clause (b) asks the call-site lint to fail on a "command return of an rc that does not pass
  through rc_escalate". The lint checked exits and the `__main__` block only. The shape it missed is a caller that
  runs a command and DROPS its return code, or catches a command's SystemExit and drops the code: `refsanalysis all`
  (ra cmd_all) does both, and forefst's `export reparse -o FILE` drops `cmd_reparse`'s code (latent: `cmd_reparse`
  returns 0 today).
* The latent forefst site itself, as a unit RED: `export reparse -o FILE` must return the code `cmd_reparse` returns.

Same discipline as the other 1.13.2 RED files: only a plain ``assert`` states the defect; a fixture that is not what
the case needs raises ``RedFixtureError``. No corpus image is read.
"""
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402

from test_1132_red_a_bootstrap import _fx                          # noqa: E402  (T-4: the unused imports removed)
from test_1132_red_a_verdicts import _lint_red             # noqa: E402


# ═══ K7: the lint fails on a command whose exit code is dropped ══════════════════════════════════════════════════

# Each plant is the shape of a live site (ra cmd_all, fd cmd_export_reparse), wrapped in a def with a unique name and
# appended to a copy of the tool in a scratch tree (the a_verdicts lint machinery, imported by name).
_PLANTS_DISCARD = {
    # ra cmd_all: a section's return code is never read
    "ra-handler-rc-dropped": ("refsanalysis.py", '''
        def _red_plant_ra_handler_rc_dropped(image, partition_start):
            handler = _HANDLERS.get("summary")
            handler(image, [], partition_start)
            return 0
    '''),
    # ra cmd_all: a section's SystemExit is caught and its code dropped
    "ra-handler-systemexit-dropped": ("refsanalysis.py", '''
        def _red_plant_ra_handler_systemexit_dropped(image, partition_start):
            try:
                rc = cmd_summary(image, [], partition_start)
            except SystemExit:
                print("  [summary] failed", file=sys.stderr)
                return 0
            return rc
    '''),
    # fd cmd_export_reparse -o: the inner command's return code is never read
    "fd-cmd-rc-dropped": ("forefst.py", '''
        def _red_plant_fd_cmd_rc_dropped(image, partition_start):
            cmd_reparse(image, ["--json"], partition_start)
            return 0
    '''),
}


@pytest.mark.parametrize("pid", sorted(_PLANTS_DISCARD))
def test_k7_lint_fails_on_a_planted_command_whose_exit_code_is_dropped(tmp_path, pid):
    _lint_red(tmp_path, _PLANTS_DISCARD, pid)


# ═══ fd cmd_export_reparse -o: the code of the command it wraps ═════════════════════════════════════════════════

@pytest.mark.parametrize("inner_rc", [1, 2])
def test_k7_export_reparse_to_a_file_returns_the_code_of_cmd_reparse(tmp_path, monkeypatch, inner_rc):
    calls = []

    def _fake_cmd_reparse(image, remaining, partition_start):
        calls.append(list(remaining))
        print("reparse inventory (fake)")
        return inner_rc

    monkeypatch.setattr(F, "cmd_reparse", _fake_cmd_reparse)
    out = tmp_path / "reparse.txt"
    rc = F.cmd_export_reparse("unused.raw", ["-o", str(out)], None)
    _fx(calls == [[]], "cmd_export_reparse did not call cmd_reparse once with no extra arguments: %r" % calls)
    _fx(out.is_file() and "reparse inventory (fake)" in out.read_text(), "the inventory was not written to -o FILE")
    assert rc == inner_rc, "`export reparse -o FILE` returned %r; cmd_reparse returned %d" % (rc, inner_rc)


def test_k7_control_export_reparse_to_the_screen_returns_the_code_of_cmd_reparse(monkeypatch, capsys):
    """Control: without -o the same function already returns cmd_reparse's code, so the RED above fails only on the
    -o path."""
    monkeypatch.setattr(F, "cmd_reparse", lambda image, remaining, partition_start: 2)
    assert F.cmd_export_reparse("unused.raw", [], None) == 2
