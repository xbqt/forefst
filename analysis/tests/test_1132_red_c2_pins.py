"""1.13.2 (ships as 1.14.0) PIN cases, wave C step C2, area `pins`: RV-10 (a test-only pin of step C1's C-5 change to
the live instrument `analysis/tools/analysis_scripts/timestomp_source_census.py`).

Read first: `analysis/reports/v1.13.2/fixes/REVIEW_C1_correctness.md` (RV-10, section 6), `fixes/C1_LEAD_SETTLEMENTS.md`
(C-5: the live instrument's label read, `timestomp_source_census.py:65`, N433's class) and `fixes/FIX_C1_mlog.md`
section 4 (the C-5 check: `census_one` on win11refsmini gives `mlog_records` 746; a missing label is a skip note and
exit 1). Report: `analysis/reports/v1.13.2/fixes/RED_C2_pins.md`.

What C-5 changed. N437 (step C1) renamed `mlog --stats`'s count line from `Total records:` to `Redo records:`. The census
read the old label (`re.search(r"Total records:\\s*(\\d+)")`) and wrote 0 when it found none, so after the rename it
wrote 0 on every volume: a zero that looks measured, for a count it never read. Since C-5 the census reads the
`Redo records:` line; takes the tool's "No redo records found" as a measured 0; otherwise records no value (an empty
CSV cell) and a skip note naming the image and the exit; and, when `mlog --stats` exited 0 without the count, `main()`
returns 1 and names the missing label.

These are PINS, not REDs: every node passes on the current tree and carries no xfail mark; the pins RV10-1..RV10-4 fail
on the census as it was before C-5 (`fixes/prefix_C1/analysis_scripts/timestomp_source_census.py`, sha256 eca0cfa8...)
run with the current tools (shown in a make_tp_workspace.sh copy of `fixes/prefix_C2` with only that file swapped;
RED_C2_pins.md section 4), and the controls RV10-C, RV10-C2 pass on both.
  RV10-1  real tool, step1/win11refsmini: `census_one` gives `mlog_records` 746, the count on the tool's own
          `Redo records:` line (746: CLAUDE.md's 2026-09-26 re-measure, FIX_C1_mlog section 4, and this node).
  RV10-2  the tool's line as printed (`  Redo records:       746`, canned; no image needed): the CSV cell is 746 and
          main() returns 0.
  RV10-3  `mlog --stats` exits 0 without a `Redo records:` line (the pre-N437 label, or another one): main() returns 1
          and says which label is missing on which image; the CSV cell is empty, not 0 and not the other label's count.
  RV10-4  `mlog --stats` exits 2 with a statement and no count: the CSV cell is empty, not 0, and a skip note names the
          image and the exit.
  RV10-C  control (passes before and after C-5): "No redo records found" is a measured 0 and main() returns 0, so the
          exit 1 of RV10-3 is not unconditional.
  RV10-C2 control (passes before and after C-5; added by the RED critic, RED_C2_pins_critic.md): `mlog --stats` exits
          2 (a statement, no count) or the census's own run times out (exit -1, no output): main() returns 0 and
          raises no label alarm -- C-5's exit 1 is for a run that exited 0 without the label (`if rc == 0`), not for a
          volume whose log the tool could not read; that one is RV10-4's skip note.
The census is loaded from dirname(REPO)/analysis/tools/analysis_scripts/ (as test_1132_red_c1_instruments.py loads
refs_mlog.py), so FOREFST_REPO selects the tree; a fresh module per node (its skip lists are module globals), with its
TOOL pointed at REPO's forefst.py (the file hard-codes /workspace/refs/forefstdev/forefst.py).
"""
import csv
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (RedFixtureError, _fx)
import test_1132_red_mlog_chkp as MC                     # noqa: E402  (corpus: an image by its step path)

RedFixtureError = AB.RedFixtureError
_fx = AB._fx

WS = os.path.dirname(REPO)                               # the workspace (or the USB mirror) holding forefstdev/
CENSUS = os.path.join(WS, "analysis", "tools", "analysis_scripts", "timestomp_source_census.py")
IMG = "step1/win11refsmini.raw"
MINI_REDO_RECORDS = 746                                  # win11refsmini, `mlog --stats` of the dev tool (see RV10-1)
REDO_LINE = re.compile(r"(?m)^\s*Redo records:\s*(\d+)\s*$")
TIMEOUT = 900

# `mlog --stats` record sections, as forefst.py prints them (cmd_mlog, "Redo Records")
TOOL_LINES_746 = ("  Redo records:       746\n"
                  "  Transaction starts: 362\n"
                  "  Transaction commits: 362\n")
TOOL_LINES_NONE = ("  No redo records found in data area.\n"
                   "  (Log may be clean — all transactions checkpointed.)\n")
MLOG_RC2_STATEMENT = "  The log's control area could not be read: the volume needs a look.\n"   # canned: no count

_LOADS = [0]


def _census():
    """A fresh instance of the census module, run against REPO's forefst.py."""
    _fx(os.path.isfile(CENSUS), "timestomp_source_census.py not found at %s" % CENSUS)
    _LOADS[0] += 1
    spec = importlib.util.spec_from_file_location("timestomp_source_census_pin%d" % _LOADS[0], CENSUS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    missing = [n for n in ("census_one", "main", "run", "ROOT", "TOOL", "_SKIPPED") if not hasattr(mod, n)]
    _fx(not missing, "the census has no %s any more: this harness no longer fits it" % ", ".join(missing))
    mod.TOOL = os.path.join(REPO, "forefst.py")
    return mod


def _canned(mlog_rc, mlog_out):
    """A `run` stand-in for the four commands census_one makes, answered as a readable ReFS 3.14 volume would; only
    the answer to `mlog --stats` varies."""
    calls = []

    def run(img, argv, timeout=2400):
        calls.append(tuple(argv))
        if argv[:1] == ["fastsummary"]:
            return 0, json.dumps({"refs_version": "3.14", "objects": 24})
        if argv[:1] == ["usn"]:
            return 0, "USN Journal Statistics (3 records)\n  Time range: 2026-01-01 .. 2026-01-02\n"
        if argv[:1] == ["mlog"]:
            return mlog_rc, mlog_out
        if argv[:1] == ["specials"]:
            return 0, "snapshot  (0)\n  (none)\n"
        raise RedFixtureError("the census ran a command this harness does not answer: %r" % (argv,))
    return run, calls


def _main(tmp_path, monkeypatch, capsys, mlog_rc, mlog_out):
    """main() over a one-image corpus list whose `mlog --stats` answer is (mlog_rc, mlog_out).
    Returns (main's return value, the image's CSV row, stderr, the module's skip notes)."""
    mod = _census()
    root = tmp_path / "ws"
    (root / "analysis" / "verification").mkdir(parents=True)
    (root / "img").mkdir()
    (root / "img" / "canned.raw").write_bytes(b"")
    (root / "analysis" / "verification" / "corpus.lst").write_text("img/canned.raw\n")
    out = tmp_path / "out"
    run, calls = _canned(mlog_rc, mlog_out)
    monkeypatch.setattr(mod, "ROOT", str(root))
    monkeypatch.setattr(mod, "run", run)
    monkeypatch.setattr(sys, "argv", ["timestomp_source_census.py", "--out", str(out)])
    rc = mod.main()
    err = capsys.readouterr().err
    _fx(("mlog", "--stats") in calls, "the census did not run `mlog --stats` (calls: %r)" % (calls,))
    _fx((out / "census.csv").is_file(), "main() wrote no census.csv")
    with open(str(out / "census.csv"), newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    _fx(len(rows) == 1 and "mlog_records" in rows[0], "census.csv is not one row with `mlog_records`: %r" % (rows,))
    return rc, rows[0], err, list(mod._SKIPPED)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# RV10-1  the census and the tool agree on a corpus volume
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_rv10_1_census_reads_the_redo_count_the_tool_prints_on_win11refsmini():
    img = MC.corpus(IMG)
    # the tool's side first, so a label the tool no longer prints is reported as that, not as a census misread
    r = subprocess.run([sys.executable, os.path.join(REPO, "forefst.py"), img, "mlog", "--stats"],
                       capture_output=True, text=True, timeout=TIMEOUT, cwd=REPO)
    assert r.returncode == 0 and REDO_LINE.findall(r.stdout) == [str(MINI_REDO_RECORDS)], (
        "`mlog --stats` on %s: exit %d, `Redo records:` lines %r (expected exit 0 and one line of %d): the label "
        "the census reads is not the tool's" % (IMG, r.returncode, REDO_LINE.findall(r.stdout), MINI_REDO_RECORDS))
    mod = _census()
    row = mod.census_one(img)
    _fx(row.get("readable") == "yes",
        "`fastsummary --json -q` did not exit 0 on %s, so census_one stopped before `mlog --stats`: %r" % (IMG, row))
    assert row.get("mlog_records") == MINI_REDO_RECORDS, (
        "the census read mlog_records=%r on %s; `mlog --stats` counts %d redo records there under the label "
        "`Redo records:` (RV-10: the label the census reads)" % (row.get("mlog_records"), IMG, MINI_REDO_RECORDS))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# RV10-2 .. RV10-4, RV10-C  canned `mlog --stats` answers (no image)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_rv10_2_census_reads_the_redo_records_line_as_the_tool_prints_it(tmp_path, monkeypatch, capsys):
    rc, row, err, skipped = _main(tmp_path, monkeypatch, capsys, 0, TOOL_LINES_746)
    assert row["mlog_records"] == "746", (
        "the census wrote mlog_records=%r for `  Redo records:       746`" % row["mlog_records"])
    assert rc == 0 and "missing" not in err, "main() returned %r with the label present (stderr: %r)" % (rc, err)


@pytest.mark.parametrize("label_line", [
    "  Total records:      746\n",                      # the label before N437
    "  Records:            746\n",                      # any other label
], ids=["pre_N437_label", "other_label"])
def test_rv10_3_census_exits_1_and_names_the_label_when_mlog_stats_exits_0_without_it(
        tmp_path, monkeypatch, capsys, label_line):
    rc, row, err, skipped = _main(tmp_path, monkeypatch, capsys, 0, label_line + "  Transaction starts: 362\n")
    assert rc == 1, (
        "main() returned %r although `mlog --stats` exited 0 without a `Redo records:` line (%r): the census "
        "measured nothing and must say so (exit 1)" % (rc, label_line.strip()))
    assert "Redo records" in err and "missing" in err and "canned.raw" in err, (
        "stderr does not name the missing `Redo records:` label and the image: %r" % err)
    assert row["mlog_records"] == "", (
        "the census wrote mlog_records=%r for a count it did not read (an empty cell, not a measured value, "
        "is what it read)" % row["mlog_records"])


def test_rv10_4_a_failed_mlog_run_is_a_skip_note_not_a_zero(tmp_path, monkeypatch, capsys):
    rc, row, err, skipped = _main(tmp_path, monkeypatch, capsys, 2, MLOG_RC2_STATEMENT)
    assert row["mlog_records"] == "", (
        "the census wrote mlog_records=%r where `mlog --stats` exited 2 and printed no count" % row["mlog_records"])
    notes = [s for s in skipped if "canned.raw" in s and re.search(r"\bexit 2\b", s)]
    assert notes, "no skip note names the image and `mlog --stats`'s exit 2: %r" % (skipped,)


def test_rv10_c_control_no_redo_records_is_a_measured_zero_and_exit_0(tmp_path, monkeypatch, capsys):
    rc, row, err, skipped = _main(tmp_path, monkeypatch, capsys, 0, TOOL_LINES_NONE)
    assert row["mlog_records"] == "0", (
        "the census wrote mlog_records=%r for \"No redo records found\" (a measured 0)" % row["mlog_records"])
    assert rc == 0 and "missing" not in err, (
        "main() returned %r for a volume the tool says has no redo record (stderr: %r)" % (rc, err))


@pytest.mark.parametrize("mlog_rc,mlog_out", [
    (2, MLOG_RC2_STATEMENT),                            # the tool ran and stated why there is no count
    (-1, ""),                                           # the census's own run() on a timeout
], ids=["mlog_exit_2", "census_timeout"])
def test_rv10_c2_control_a_failed_mlog_run_raises_no_label_alarm_and_exits_0(
        tmp_path, monkeypatch, capsys, mlog_rc, mlog_out):
    rc, row, err, skipped = _main(tmp_path, monkeypatch, capsys, mlog_rc, mlog_out)
    assert rc == 0 and "missing" not in err, (
        "main() returned %r with a label alarm (stderr: %r) where `mlog --stats` exited %d without a count: C-5's "
        "exit 1 is for a run that exited 0 without the `Redo records:` label, not for a volume whose log the tool "
        "could not read (that is a skip note, RV10-4)" % (rc, err, mlog_rc))
