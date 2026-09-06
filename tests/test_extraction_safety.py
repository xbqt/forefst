"""Audit 4.1 — a bulk extraction must SURFACE an unwritable name, not abort the run.

The v1.7 faithful sanitizer never truncates, so it can produce a name longer than the host filesystem's
component limit. Writing it must record the failure and continue (so the examiner gets the other files + a
record), not propagate an OSError as a mid-run traceback that leaves a partial directory and no manifest.
"""
import json
import os

import pytest

import forefst as F   # REPO is on sys.path via conftest


def _fs_enforces_name_limit(tmp_path):
    try:
        open(tmp_path / ("A" * 300), "wb").close()
        return False   # host FS accepted a 300-char name — can't exercise the limit here
    except OSError:
        return True


def test_guarded_write_records_unwritable_name_and_continues(tmp_path):
    if not _fs_enforces_name_limit(tmp_path):
        pytest.skip("host filesystem does not enforce a name-length limit")
    failures = []
    # a writable name succeeds and is not recorded as a failure
    ok = F._guarded_extract_write(str(tmp_path / "normal.bin"), b"hello", failures)
    assert ok and (tmp_path / "normal.bin").read_bytes() == b"hello"
    assert failures == []
    # a name too long for the FS is RECORDED and skipped — no exception escapes
    longname = "A" * 300 + ".bin"
    r = F._guarded_extract_write(str(tmp_path / longname), b"data", failures)
    assert r is None, "an unwritable name must not be treated as written"
    assert len(failures) == 1 and failures[0]["name"] == longname
    # extraction continued: the earlier good file is still there
    assert (tmp_path / "normal.bin").exists()


def test_report_extract_failures_indexes_and_warns(tmp_path, capsys):
    # silent + no sidecar when nothing failed
    F._report_extract_failures([], str(tmp_path))
    assert capsys.readouterr().err == ""
    assert not (tmp_path / "_extract_failures.json").exists()
    # records to the index + warns to stderr when something failed
    F._report_extract_failures([{"path": "x", "name": "x", "error": "File name too long"}], str(tmp_path))
    err = capsys.readouterr().err
    assert "could not be written" in err
    idx = tmp_path / "_extract_failures.json"
    assert idx.exists() and len(json.load(idx.open())) == 1
