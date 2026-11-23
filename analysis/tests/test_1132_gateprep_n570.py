"""1.14.0, gate prep (2026-11-17): N570, N571 -- a bulk export that could not write some of its files.

N570: a bulk export (deleted, snapshots, resident-all, recyclebin, metadata) that cannot write a file records it
(`_report_extract_failures`: `_extract_failures.json` and a stderr WARNING) and goes on; one that cannot write its
`export_index.csv` warns and goes on (`_ExportIndex.write`). Neither reached the exit code: an export into a directory
that takes no file wrote nothing and exited 0, "the command ran and flagged nothing". The exit rule's other half,
"work the command could not complete", is exit 2.

N571: `_bulk_hole_finish` printed "wrote <dir>/holes.json naming the N stream(s) that drew from holes" (or "wrote
<dir>/holes.json: hole coverage could NOT be determined ...") right after its own warning that holes.json could not be
written; the streams were then named nowhere.
"""
import io
import os
import stat
import subprocess
import sys
from contextlib import contextmanager, redirect_stderr

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FAILED = {"path": "/out/a.bin", "name": "a.bin", "error": "OSError: [Errno 28] No space left on device"}
STREAM = "n571_stream_that_drew_from_holes.bin"


@pytest.fixture
def clean_run(monkeypatch):
    """The run's registers empty for the test and the session's put back after it: what the test records is its own."""
    for name in ("_FINDINGS", "_VIEW_FINDINGS", "_SKIP_FINDING", "_REDUNDANCY_FINDING", "_CHKP_STALE",
                 "_JOURNAL_TAIL_DESTROYED", "_VERSION_CONTRADICTED", "_HOLE_STREAMS", "_UNDET_STREAMS",
                 "_HOLE_REFUSALS"):
        monkeypatch.setattr(F, name, [])
    monkeypatch.setattr(F, "_WALK_DAMAGE", F._DamageList())
    monkeypatch.setattr(F, "_SUPB_FELL_BACK", {})
    assert F.rc_escalate(0) == 0


@contextmanager
def read_only(path):
    """`path` as a directory that takes no file; skipped where it would (a root user writes into it anyway)."""
    os.makedirs(path, exist_ok=True)
    os.chmod(path, stat.S_IRUSR | stat.S_IXUSR)
    try:
        try:
            open(os.path.join(path, "probe"), "wb").close()
            os.remove(os.path.join(path, "probe"))
            pytest.skip("this user can write into a read-only directory")
        except OSError:
            pass
        yield str(path)
    finally:
        os.chmod(path, stat.S_IRWXU)


def _err(fn, *a):
    buf = io.StringIO()
    with redirect_stderr(buf):
        rc = fn(*a)
    return rc, buf.getvalue()


def test_n570_control_no_failed_write_leaves_the_exit_alone(clean_run, tmp_path):
    F._report_extract_failures([], str(tmp_path))
    assert F.rc_escalate(0) == 0


def test_n570_a_file_not_written_makes_the_export_exit_2(clean_run, tmp_path):
    _rc, err = _err(F._report_extract_failures, [dict(FAILED)], str(tmp_path))
    assert "1 file(s) could not be written" in err, err
    assert F.rc_escalate(0) == 2, "an export that could not write a file exits 0"
    assert any("could not be written" in t for t in F._escalation_texts()), F._escalation_texts()


def test_n570_control_an_index_written_leaves_the_exit_alone(clean_run, tmp_path):
    _rc, err = _err(F._ExportIndex(str(tmp_path)).write)
    assert os.path.isfile(tmp_path / "export_index.csv"), err
    assert F.rc_escalate(0) == 0


def test_n570_an_index_not_written_makes_the_export_exit_2(clean_run, tmp_path):
    with read_only(tmp_path / "ro") as ro:
        _rc, err = _err(F._ExportIndex(ro).write)
        assert not os.path.exists(os.path.join(ro, "export_index.csv"))
    assert "could not write" in err, err
    assert F.rc_escalate(0) == 2, "an export that could not write its index exits 0"


def test_n571_control_holes_json_written_is_said_written(clean_run, tmp_path):
    F._HOLE_STREAMS.append({"file": str(tmp_path / STREAM), "what": STREAM, "hole_bytes": 4096})
    rc, err = _err(F._bulk_hole_finish, str(tmp_path))
    assert os.path.isfile(tmp_path / "holes.json")
    assert "wrote %s naming the 1 stream(s)" % (tmp_path / "holes.json") in err, err
    assert rc == 2


def test_n571_holes_json_not_written_is_not_said_written(clean_run, tmp_path):
    with read_only(tmp_path / "ro") as ro:
        F._HOLE_STREAMS.append({"file": os.path.join(ro, STREAM), "what": STREAM, "hole_bytes": 4096})
        rc, err = _err(F._bulk_hole_finish, ro)
        holes = os.path.join(ro, "holes.json")
        assert not os.path.exists(holes)
    assert "wrote " + holes not in err, err
    assert STREAM in err, "the stream that drew from holes is named nowhere:\n" + err
    assert rc == 2


def test_n571_undetermined_coverage_not_written_is_not_said_written(clean_run, tmp_path):
    with read_only(tmp_path / "ro") as ro:
        F._UNDET_STREAMS.append({"file": os.path.join(ro, STREAM), "what": STREAM,
                                 "reason": "hole coverage could not be determined on this host"})
        rc, err = _err(F._bulk_hole_finish, ro)
        holes = os.path.join(ro, "holes.json")
        assert not os.path.exists(holes)
    assert "wrote " + holes not in err, err
    assert STREAM in err, "the stream whose coverage is unknown is named nowhere:\n" + err
    assert rc == 2


def _export(img, out_dir):
    return subprocess.run([sys.executable, os.path.join(REPO, "forefst.py"), img, "export", "resident-all", out_dir],
                          capture_output=True, text=True, timeout=600)


INLINE_IMG = "step3/win11refs2tsnapshots.raw"     # 9 inline files (its public sample); the golden's export row exits 0


def test_n570_image_control_the_export_into_a_writable_directory_exits_0(tmp_path):
    img = _corpus_image(INLINE_IMG)
    if img is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % INLINE_IMG)
    r = _export(img, str(tmp_path / "out"))
    assert r.returncode == 0, r.stderr
    assert "could not be written" not in r.stderr, r.stderr


def test_n570_image_the_export_into_a_read_only_directory_exits_2(tmp_path):
    img = _corpus_image(INLINE_IMG)
    if img is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % INLINE_IMG)
    with read_only(tmp_path / "ro") as ro:
        r = _export(img, ro)
        assert os.listdir(ro) == []
    assert "could not be written" in r.stderr, r.stderr
    assert r.returncode == 2, "exit %d for an export that wrote none of its files:\n%s" % (r.returncode, r.stderr)


def test_n570_control_a_recovery_log_written_leaves_the_exit_alone(clean_run, tmp_path):
    p = str(tmp_path / "recovery_log.txt")
    _rc, err = _err(F._write_recovery_log, p, "x.raw", 3, 14, "recovery", "", 0, [], [], None)
    assert os.path.isfile(p), err
    assert F.rc_escalate(0) == 0


def test_n570_a_recovery_log_not_written_makes_the_run_exit_2(clean_run, tmp_path):
    with read_only(tmp_path / "ro") as ro:
        p = os.path.join(ro, "recovery_log.txt")
        got, err = _err(F._write_recovery_log, p, "x.raw", 3, 14, "recovery", "", 0, [], [], None)
        assert got is None and not os.path.exists(p)
    assert "could not be written" in err, err
    assert F.rc_escalate(0) == 2, "a run whose recovery log could not be written exits 0"


XTARGET = "System Volume Information/IndexerVolumeGuid"     # the golden's extract target on step1/win10refsmini.raw


def _extract(img, out):
    return subprocess.run([sys.executable, os.path.join(REPO, "forefst.py"), img, "extract", XTARGET, "-o", out],
                          capture_output=True, text=True, timeout=600)


def _name_max_255(tmp_path):
    """the host takes a name of 255 bytes and refuses one of 256"""
    try:
        open(tmp_path / ("b" * 255), "wb").close()
        os.remove(tmp_path / ("b" * 255))
    except OSError:
        return False
    try:
        open(tmp_path / ("b" * 256), "wb").close()
        os.remove(tmp_path / ("b" * 256))
        return False
    except OSError:
        return True


def test_n570_image_control_extract_with_its_sidecar_written_exits_0(tmp_path):
    img = _corpus_image("step1/win10refsmini.raw")
    if img is None:
        pytest.skip("step1/win10refsmini.raw not in this tree (a clone ships no images)")
    out = str(tmp_path / "x.bin")
    r = _extract(img, out)
    assert r.returncode == 0, r.stderr
    assert os.path.isfile(out) and os.path.isfile(out + ".holes.json"), r.stderr


def test_n570_image_extract_whose_sidecar_cannot_be_written_exits_2(tmp_path):
    """FILE (246 bytes; `<FILE>.partial` 254) is written; `<FILE>.holes.json` (257) is not"""
    img = _corpus_image("step1/win10refsmini.raw")
    if img is None:
        pytest.skip("step1/win10refsmini.raw not in this tree (a clone ships no images)")
    if not _name_max_255(tmp_path):
        pytest.skip("the host's name limit is not 255 bytes")
    out = str(tmp_path / ("c" * 242 + ".bin"))
    r = _extract(img, out)
    assert os.path.isfile(out), r.stderr
    assert not os.path.exists(out + ".holes.json")
    assert "could not write" in r.stderr, r.stderr
    assert r.returncode == 2, "exit %d for an extract whose sidecar was not written:\n%s" % (r.returncode, r.stderr)


def test_n572_control_a_short_output_name_is_written(tmp_path):
    p = str(tmp_path / "out.csv")
    pf = F._PartialFile(p)
    pf.fh.write("a,b\n")
    pf.close(True)
    assert open(p, encoding="utf-8").read() == "a,b\n"
    assert os.listdir(tmp_path) == ["out.csv"]


def test_n572_an_output_name_the_host_takes_is_written_though_its_partial_name_is_too_long(tmp_path):
    """N572: 1.14.0 writes FILE as `<FILE>.partial` first (N534); a FILE name of 248-255 bytes, which the host takes,
    made a partial name it does not (256-263), and the run failed with "File name too long" for FILE"""
    if not _name_max_255(tmp_path):
        pytest.skip("the host's name limit is not 255 bytes")
    name = "d" * 251 + ".csv"                                # 255 bytes: the host's limit
    p = str(tmp_path / name)
    pf = F._PartialFile(p)
    pf.fh.write("a,b\n")
    pf.close(True)
    assert open(p, encoding="utf-8").read() == "a,b\n"
    assert os.listdir(tmp_path) == [name], os.listdir(tmp_path)


def test_n572_a_failed_write_under_the_short_partial_name_leaves_nothing(tmp_path):
    if not _name_max_255(tmp_path):
        pytest.skip("the host's name limit is not 255 bytes")
    p = str(tmp_path / ("e" * 251 + ".csv"))
    pf = F._PartialFile(p)
    pf.fh.write("a,b\n")
    pf.close(False)
    assert os.listdir(tmp_path) == []


def test_n570_control_a_restore_log_written_leaves_the_exit_alone(clean_run, tmp_path):
    import refsanalysis as RA
    target = tmp_path / "copy.raw"
    target.write_bytes(b"\0" * 4096)
    log = str(tmp_path / "restore.log")
    _rc, err = _err(RA._apply_copy_restores, str(target), [], str(target), log)
    assert os.path.isfile(log), err
    assert F.rc_escalate(0) == 0


def test_n570_a_restore_log_not_written_makes_bootedit_exit_2(clean_run, tmp_path):
    """`bootedit repair` changed the image and could not write the log of what it changed"""
    import refsanalysis as RA
    target = tmp_path / "copy.raw"
    target.write_bytes(b"\0" * 4096)
    with read_only(tmp_path / "ro") as ro:
        log = os.path.join(ro, "restore.log")
        lines, err = _err(RA._apply_copy_restores, str(target), [], str(target), log)
        assert not os.path.exists(log)
    assert "the restore log could not be written" in err, err
    assert not any("logged in" in l for l in lines), lines
    assert F.rc_escalate(0) == 2, "bootedit exits 0 without the log of what it changed"
