"""E2 close (1.14.0): the final check's findings (fixes/REVIEW_WAVEE2_final.md; fixes/E2cd_NOTES.md section 10). RED
on fixes/prefix_E2final (forefst 1255451f, refsanalysis 7fbfa254).

  F1  `help usn` names the columns `usn --csv` writes, from the column list (it named entry_type / file_ref /
      parent_idx, said three fields were "kept last" and did not name SourceInfoHex).
  F2  a write failure ends with the error line and exit 1, never a traceback or an exit 120, also when the output is
      small enough to stay in the buffer until the exit (`summary > /dev/full` exited 0 with nothing written), and
      through refsanalysis (its own commands and the `forefst` passthrough).
  F4  a redo record's flag word in `mlog -v` text is named by the one table `mlog --json` uses (`_REDO_FLAGS`): an
      unnamed bit is shown, not dropped.
"""
import csv
import io
import os
import re
import resource
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
RA = os.path.join(REPO, "refsanalysis.py")
MINI314 = "step1/win11refsmini.raw"
SAMPLE = "step5/win11refstestmftecmd.raw"


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _help(cmd):
    r = subprocess.run([sys.executable, "-B", FOREFST, "help", cmd], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-1500:]
    return r.stdout


# ---- F1 --------------------------------------------------------------------------------------------------------

def test_f1_usn_help_names_every_csv_column_in_order():
    """The help lists the output names of USN_CSV_COLUMNS, in their order, with their count."""
    names = [F.out_key(c) for c in F.USN_CSV_COLUMNS]
    h = " ".join(_help("usn").split())
    assert "a %d-column CSV (%s;" % (len(names), ", ".join(names)) in h, h[-1500:]


def test_f1_usn_help_has_no_internal_column_name():
    """No retired or internal key (entry_type, file_ref, parent_idx, source_info, security_id) and no 'kept last'."""
    h = _help("usn")
    for word in ("entry_type", "file_ref", "parent_idx", "source_info", "security_id", "kept last"):
        assert word not in h, word


def test_f1_usn_help_columns_are_the_csv_header():
    """Against the output itself: the header `usn --csv` writes on the public sample is the list the help names."""
    r = subprocess.run([sys.executable, "-B", FOREFST, _img(SAMPLE), "usn", "--csv"], capture_output=True, text=True,
                       timeout=1800)
    assert r.returncode in (0, 2), r.stderr[-1500:]
    header = next(csv.reader(io.StringIO(r.stdout)))
    h = " ".join(_help("usn").split())
    assert "(%s;" % ", ".join(header) in h, (header, h[-1200:])


# ---- F2 --------------------------------------------------------------------------------------------------------

def _limit_fsize():
    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))


def _to_full(argv):
    with open("/dev/full", "w") as full:
        return subprocess.run([sys.executable, "-B"] + argv, stdout=full, stderr=subprocess.PIPE, text=True,
                              timeout=1800)


@pytest.mark.parametrize("argv", [
    pytest.param(["forefst", "summary"], id="forefst-summary"),
    pytest.param(["ra", "files"], id="refsanalysis-files"),
    pytest.param(["ra", "summary"], id="refsanalysis-summary"),
    pytest.param(["ra", "forefst", "summary"], id="passthrough-summary"),
])
def test_f2_a_buffered_write_failure_is_reported(argv):
    """A small text output to a full device: the error line, exit 1, no 'Exception ignored' (exit 120), no exit 0."""
    tool = FOREFST if argv[0] == "forefst" else RA
    r = _to_full([tool, _img(MINI314)] + argv[1:])
    assert "Traceback" not in r.stderr and "Exception ignored" not in r.stderr, r.stderr[-1500:]
    assert "error: cannot write the output" in r.stderr, r.stderr[-1500:]
    assert r.returncode == 1, r.returncode


def test_f2_passthrough_ends_a_file_write_failure_with_the_error_line(tmp_path):
    """`refsanalysis IMG forefst files --csv -o F` past a file-size limit: the line, exit 1, no partial file."""
    dest = str(tmp_path / "files.csv")
    r = subprocess.run([sys.executable, "-B", RA, _img(SAMPLE), "forefst", "files", "--csv", "-o", dest],
                       capture_output=True, text=True, timeout=1800, preexec_fn=_limit_fsize)
    assert "Traceback" not in r.stderr, r.stderr[-1500:]
    assert re.search(r"refsanalysis: error: cannot write the output \(.*files\.csv\)", r.stderr), r.stderr[-1500:]
    assert r.returncode == 1, r.returncode
    assert not os.path.exists(dest) and not os.path.exists(dest + ".partial")


def test_f2_control_a_normal_run_and_a_closed_pipe_keep_their_exit():
    """Control: to /dev/null summary exits 0; `files | head -1` (a closed pipe) exits 0 with no traceback."""
    r = subprocess.run([sys.executable, "-B", FOREFST, _img(MINI314), "summary"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-1500:]
    for tool in (FOREFST, RA):
        p = subprocess.Popen([sys.executable, "-B", tool, _img(MINI314), "files"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.stdout.readline()
        p.stdout.close()
        err = p.stderr.read().decode("utf-8", "replace")
        assert p.wait(timeout=600) == 0 and "Traceback" not in err, (tool, err[-1500:])


# ---- F4 --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("v", [0x1, 0x2, 0x3, 0x2001, 0x2005, 0x4])
def test_f4_redo_flags_text_is_the_json_names(v):
    """The text form is `0x<hex> (<the names mlog --json writes>)`, the hex alone when no bit has a name (K14): one
    table for both."""
    names = F.flag_cells(v, F._REDO_FLAGS)[0]
    assert F._mlog_flags_text(v) == ("0x%x" % v if names == "0x%x" % v else "0x%x (%s)" % (v, names))


def test_f4_redo_flags_text_of_zero_is_the_k14_form():
    assert F._mlog_flags_text(0) == F.flag_text(0, F._REDO_FLAGS) == "0x0 (none set)"
