"""1.14.0, gate prep (2026-11-16): N566 -- when a bulk export cannot write its list of failed writes
(`_extract_failures.json`), its warning does not point the examiner at that file.

`_report_extract_failures` wrote the list in a `try` whose `except OSError` passed, then printed "see
<dir>/_extract_failures.json" whatever happened: on a directory that cannot take the file (full, read-only, gone),
the warning named a file that does not exist and the names of the files not written were lost. The warning now says
the list could not be written, with the reason, and names the files on stderr instead.
"""
import io
import os
import sys
from contextlib import redirect_stderr

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402

FAILURES = [{"path": "/out/a" + "x" * 300, "name": "a" + "x" * 300, "error": "OSError: File name too long"},
            {"path": "/out/b.txt", "name": "b.txt", "error": "OSError: No space left on device"}]


def _report(out_dir):
    err = io.StringIO()
    f0, v0 = len(F._FINDINGS), len(F._VIEW_FINDINGS)
    try:
        with redirect_stderr(err):
            F._report_extract_failures([dict(x) for x in FAILURES], out_dir)
    finally:
        del F._FINDINGS[f0:], F._VIEW_FINDINGS[v0:]      # N570: the finding it records is this test's, not the session's
    return err.getvalue()


def test_n566_the_list_written_the_warning_names_it(tmp_path):
    msg = _report(str(tmp_path))
    assert os.path.isfile(tmp_path / "_extract_failures.json")
    assert "2 file(s) could not be written" in msg
    assert str(tmp_path / "_extract_failures.json") in msg


def test_n566_the_list_not_written_the_warning_says_so_and_names_the_files(tmp_path):
    gone = str(tmp_path / "no_such_dir")               # the list cannot be created there
    msg = _report(gone)
    assert not os.path.exists(os.path.join(gone, "_extract_failures.json"))
    assert "2 file(s) could not be written" in msg
    assert "see " + os.path.join(gone, "_extract_failures.json") not in msg, msg
    assert "the list of them could not be written either" in msg, msg
    assert "b.txt" in msg, msg
