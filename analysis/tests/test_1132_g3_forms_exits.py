"""The code half, group 3 (machine forms and exits), 1.14.0: RUNNING_LOG N534, N536, N538, N539, N540, N544, N545,
N546, N548, N553 (b)-(d) (`analysis/reports/v1.13.2/RC1D/G3/DESIGN.md`).

  N534  every machine-output FILE and `extract -o FILE` is written as `<FILE>.partial` and renamed when complete, so a
        write that stops part-way leaves no file under FILE's name: `mlog --csv FILE`, `export reparse -o FILE`, an
        export's `export_index.csv`, `extract`'s sidecar and its `-o FILE` were written directly under the name.
  N536  gate 1f's negative control expects the "none" sidecar a clean file gets (B12, 1.14.0) and checks its status.
  N538  a reader that closes a pipe stderr is merged into (`2>&1 | head`) ends the run quietly, as `| head` does -- not
        with exit 120 (the end-of-run note on stderr failed at the interpreter's exit).
  N539  the boot-sector checksums in JSON are `0x%04x` strings, the text's form (they were integers).
  N540  a directory the path map's walk did not reach is `<undetermined 0x..>` when that walk read the tree in part
        (a table that raised, a page it could not read, the depth cutoff), not `<unlinked 0x..>`.
  N544  (a) an error on an output FILE names FILE, not `<FILE>.partial`; (b) a FILE that is not a regular file (a
        device, a FIFO) is written directly (`files --csv /dev/null` was refused: `/dev/null.partial`).
  N545  the maintainer's rule (b), 2026-11-12: an export's statements go to stderr when stdout carries the export, to
        stdout when the export goes to a FILE -- `mlog`'s, `timeline`'s MLog source's, `timestomp`'s creation-time note.
  N546  `help extract` lists `-o FILE` / `--output FILE` and `--fill-holes`, and writes `HomeOID:FileID`.
  N548  over a bundle that does not carry the Container Table's pages the statements say so (not a failed check, not
        a corrupt table) and name the bundle (not the reader's temporary `r.raw`).
  N553  (b) refsanalysis `details --json` carries the journal id and the packed EA size its text prints; (c) the
        reparse JSON writes the tag's name once; (d) `Marker` is a hex word; the stale comment above the container
        counts.

Written RED before the fix (the run is recorded in `analysis/reports/v1.13.2/RC1D/G3/`). Volumes: win11refsmini
(step1), the public sample, win11refs2tspecials, win11refs2gtargeted_reformated, win11refs2tsnapshots (gate 1f).
"""
import json
import os
import re
import resource
import signal
import stat
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
RA = os.path.join(REPO, "refsanalysis.py")
MINI314 = "step1/win11refsmini.raw"
SAMPLE = "step5/win11refstestmftecmd.raw"
SPECIALS = "step3/win11refs2tspecials.raw"
REFORMATTED = "step6/win11refs2gtargeted_reformated.raw"
SNAPSHOTS = "step3/win11refs2tsnapshots.raw"
INLINE = "/test/ok.txt"                                  # a 4-byte inline file of win11refsmini
EXTENTS = "/test/xbpt_beta_sierra_570651.json"           # an extent-mapped file of the public sample (71,395 bytes)


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _run(argv, timeout=1800, **kw):
    return subprocess.run([sys.executable, "-B"] + argv, capture_output=True, text=True, timeout=timeout, **kw)


def _fsize(n):
    def f():
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (n, n))
    return f


def _left(dest):
    """The files a stopped write left under FILE's name or its temporary name."""
    return [p for p in (dest, dest + ".partial") if os.path.exists(p)]


def _error_lines(err):
    return [ln for ln in err.splitlines() if re.match(r"(forefst|refsanalysis): error: ", ln)]


# ═══ N534: no file under FILE's name is left incomplete ═══════════════════════════════════════════════════════════

def test_n534_mlog_csv_file_that_stops_part_way_leaves_no_file(tmp_path):
    dest = str(tmp_path / "m.csv")
    r = _run([FOREFST, _img(MINI314), "mlog", "--csv", dest], preexec_fn=_fsize(4096))
    assert "Traceback" not in r.stderr, r.stderr[-1500:]
    assert r.returncode == 1, (r.returncode, r.stderr[-1500:])
    assert any("m.csv" in ln for ln in _error_lines(r.stderr)), r.stderr[-1500:]
    assert _left(dest) == [], _left(dest)


def test_n534_control_mlog_csv_file_is_written_whole(tmp_path):
    """Control (and the premise of the test above): with no limit the CSV is written, larger than the limit used."""
    dest = str(tmp_path / "m.csv")
    r = _run([FOREFST, _img(MINI314), "mlog", "--csv", dest])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    assert _left(dest) == [dest] and os.path.getsize(dest) > 4096, _left(dest)


def test_n534_mlog_csv_into_a_directory_is_a_usage_error(tmp_path):
    """`--csv DIR`: the friendly line every other FILE output gives (`_check_out`), exit 1, no traceback."""
    r = _run([FOREFST, _img(MINI314), "mlog", "--csv", str(tmp_path)])
    assert "Traceback" not in r.stderr and r.returncode == 1, (r.returncode, r.stderr[-1500:])
    assert any("is a directory" in ln for ln in _error_lines(r.stderr)), r.stderr[-1500:]


def test_n534_export_reparse_o_file_that_stops_part_way_leaves_no_file(tmp_path):
    dest = str(tmp_path / "reparse.json")
    r = _run([FOREFST, _img(SPECIALS), "export", "reparse", "--json", "-o", dest], preexec_fn=_fsize(512))
    assert "Traceback" not in r.stderr, r.stderr[-1500:]
    assert r.returncode == 1, (r.returncode, r.stderr[-1500:])
    assert any("reparse.json" in ln for ln in _error_lines(r.stderr)), r.stderr[-1500:]
    assert _left(dest) == [], _left(dest)


def test_n534_control_export_reparse_o_file_is_written_whole(tmp_path):
    dest = str(tmp_path / "reparse.json")
    r = _run([FOREFST, _img(SPECIALS), "export", "reparse", "--json", "-o", dest])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    assert _left(dest) == [dest] and os.path.getsize(dest) > 512
    json.load(open(dest, encoding="utf-8"))


_INDEX_SNIPPET = r"""
import sys
sys.path.insert(0, %r)
import forefst as F
ix = F._ExportIndex(%r)
for i in range(300):
    ix.rows.append({"ObjectRef": "0x701:0x%%x" %% i, "FullPath": "dir/file_%%04d.txt" %% i,
                    "ContentFile": "file_%%04d.txt" %% i, "SHA256": "0" * 64, "RenameReason": ""})
ix.write()
"""


def test_n534_export_index_that_stops_part_way_leaves_no_file(tmp_path):
    """`_ExportIndex.write` past a file-size limit: its WARNING (the export goes on), and no index under the name."""
    out = str(tmp_path / "exp")
    r = subprocess.run([sys.executable, "-B", "-c", _INDEX_SNIPPET % (REPO, out)], capture_output=True, text=True,
                       timeout=120, preexec_fn=_fsize(4096))
    assert r.returncode == 0 and "Traceback" not in r.stderr, r.stderr[-1500:]
    assert "WARNING: could not write" in r.stderr and "export_index.csv" in r.stderr, r.stderr[-1500:]
    assert _left(os.path.join(out, "export_index.csv")) == [], os.listdir(out)


def test_n534_control_export_index_is_written_whole(tmp_path):
    out = str(tmp_path / "exp")
    r = subprocess.run([sys.executable, "-B", "-c", _INDEX_SNIPPET % (REPO, out)], capture_output=True, text=True,
                       timeout=120)
    assert r.returncode == 0, r.stderr[-1500:]
    p = os.path.join(out, "export_index.csv")
    assert _left(p) == [p] and os.path.getsize(p) > 4096
    assert len(open(p, encoding="utf-8").read().splitlines()) == 301


def test_n534_extract_sidecar_that_stops_part_way_leaves_no_file(tmp_path):
    """The 4-byte file is written; its sidecar (larger than 64 bytes) cannot be: the WARNING, no sidecar under its
    name."""
    dest = str(tmp_path / "ok.txt")
    r = _run([FOREFST, _img(MINI314), "extract", INLINE, "-o", dest], preexec_fn=_fsize(64))
    assert "Traceback" not in r.stderr, r.stderr[-1500:]
    assert "WARNING: could not write" in r.stderr and "ok.txt.holes.json" in r.stderr, r.stderr[-1500:]
    assert _left(dest + ".holes.json") == [], os.listdir(str(tmp_path))
    assert os.path.getsize(dest) == 4


def test_n534_extract_o_file_in_memory_that_stops_part_way_leaves_no_file(tmp_path):
    dest = str(tmp_path / "ok.txt")
    r = _run([FOREFST, _img(MINI314), "extract", INLINE, "-o", dest], preexec_fn=_fsize(2))
    assert "Traceback" not in r.stderr, r.stderr[-1500:]
    assert r.returncode == 1, (r.returncode, r.stderr[-1500:])
    assert any("ok.txt" in ln for ln in _error_lines(r.stderr)), r.stderr[-1500:]
    assert _left(dest) == [], os.listdir(str(tmp_path))


_STREAMED = r"""
import resource, signal, sys
sys.path.insert(0, %r)
import forefst as F
F._EXTRACT_STREAM_MIN = 0          # stream every extent-mapped file (N472's path; it is taken above 256 MiB)
lim = %r
if lim:
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (lim, lim))
sys.argv = ["forefst.py"] + %r
try:
    rc = F.main()
except SystemExit as e:
    rc = e.code
sys.stdout.flush()
sys.exit(rc if isinstance(rc, int) else 1)
"""


def _streamed(argv, limit=0):
    """`forefst.py <argv>` with every extent-mapped file streamed (`_StreamedContent`), in a child process."""
    return subprocess.run([sys.executable, "-B", "-c", _STREAMED % (REPO, limit, argv)], capture_output=True,
                          timeout=1800)


def test_n534_extract_o_file_streamed_that_stops_part_way_leaves_no_file(tmp_path):
    dest = str(tmp_path / "big.bin")
    r = _streamed([_img(SAMPLE), "extract", EXTENTS, "-o", dest], limit=4096)
    err = r.stderr.decode("utf-8", "replace")
    assert "Traceback" not in err, err[-1500:]
    assert r.returncode == 1, (r.returncode, err[-1500:])
    assert any("big.bin" in ln for ln in _error_lines(err)), err[-1500:]
    assert _left(dest) == [], os.listdir(str(tmp_path))


def test_n534_control_extract_o_file_is_the_bytes_on_stdout(tmp_path):
    """Control: `-o FILE` holds the bytes the same run writes to stdout, in memory and streamed; no `.partial` is
    left beside it."""
    img = _img(MINI314)
    dest = str(tmp_path / "ok.txt")
    r = _run([FOREFST, img, "extract", INLINE, "-o", dest])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    s = subprocess.run([sys.executable, "-B", FOREFST, img, "extract", INLINE], capture_output=True, timeout=1800)
    assert open(dest, "rb").read() == s.stdout and len(s.stdout) == 4
    img = _img(SAMPLE)
    dest = str(tmp_path / "big.bin")
    r = _streamed([img, "extract", EXTENTS, "-o", dest])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    s = _streamed([img, "extract", EXTENTS])
    assert open(dest, "rb").read() == s.stdout and len(s.stdout) == 71395
    assert not [n for n in os.listdir(str(tmp_path)) if n.endswith(".partial")]


# ═══ N544: the error names FILE; a FILE that is not a regular file is written directly ═══════════════════════════

def test_n544_a_the_error_names_file_not_its_partial_name(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    os.chmod(str(ro), 0o555)
    try:
        if os.access(str(ro), os.W_OK):
            pytest.skip("this user can write in a 0555 directory (root)")
        dest = str(ro / "out.csv")
        r = _run([FOREFST, _img(MINI314), "files", "--csv", dest])
        assert "Traceback" not in r.stderr and r.returncode == 1, (r.returncode, r.stderr[-1500:])
        err = _error_lines(r.stderr)
        assert any(dest in ln for ln in err), err
        assert not any(".partial" in ln for ln in err), err
    finally:
        os.chmod(str(ro), 0o755)


@pytest.mark.parametrize("argv", [
    pytest.param(["files", "--csv"], id="files-csv"),
    pytest.param(["summary", "--json"], id="summary-json"),
    pytest.param(["mlog", "--csv"], id="mlog-csv"),
])
def test_n544_b_a_device_file_is_written_directly(argv):
    """`--csv /dev/null`: written (exit 0 or 2), no error line -- it was refused (`/dev/null.partial`, exit 1)."""
    r = _run([FOREFST, _img(MINI314)] + argv + ["/dev/null"])
    assert r.returncode in (0, 2), (r.returncode, r.stderr[-1500:])
    assert not _error_lines(r.stderr), r.stderr[-1500:]


def _through_fifo(tmp_path, argv, binary=False):
    """Run the tool with FILE = a FIFO that a `cat` reads; (result, the bytes cat read)."""
    fifo = str(tmp_path / "out.fifo")
    os.mkfifo(fifo)
    got = str(tmp_path / "got")
    with open(got, "wb") as g:
        cat = subprocess.Popen(["cat", fifo], stdout=g)
        try:
            r = subprocess.run([sys.executable, "-B", FOREFST] + argv(fifo), capture_output=True, timeout=1800)
            cat.wait(timeout=120)
        finally:
            if cat.poll() is None:
                cat.kill()
                cat.wait()
    assert stat.S_ISFIFO(os.stat(fifo).st_mode), "the FIFO was replaced by a regular file"
    return r, open(got, "rb").read()


def test_n544_b_a_fifo_receives_the_csv(tmp_path):
    img = _img(MINI314)
    r, got = _through_fifo(tmp_path, lambda p: [img, "files", "--csv", p])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    s = subprocess.run([sys.executable, "-B", FOREFST, img, "files", "--csv", "-"], capture_output=True, timeout=1800)
    assert got == s.stdout and got


def test_n544_b_extract_o_a_fifo_receives_the_bytes(tmp_path):
    """A streamed extract seeks over holes and truncates its output only in a regular file (`sparse`); into a FIFO
    it writes the bytes in order (a FIFO cannot seek: the write failed)."""
    img = _img(SAMPLE)
    fifo = str(tmp_path / "out.fifo")
    os.mkfifo(fifo)
    got = str(tmp_path / "got")
    with open(got, "wb") as g:
        cat = subprocess.Popen(["cat", fifo], stdout=g)
        try:
            r = _streamed([img, "extract", EXTENTS, "-o", fifo])
            cat.wait(timeout=120)
        finally:
            if cat.poll() is None:
                cat.kill()
                cat.wait()
    assert r.returncode in (0, 2), r.stderr[-1500:]
    assert stat.S_ISFIFO(os.stat(fifo).st_mode)
    assert open(got, "rb").read() == _streamed([img, "extract", EXTENTS]).stdout


def test_n544_unit_partial_file_writes_a_device_directly():
    pf = F._PartialFile("/dev/null")
    pf.fh.write("x")
    pf.close(True)
    assert not os.path.exists("/dev/null.partial")


# ═══ N536: gate 1f ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_n536_gate_1f_hole_fixtures_pass_on_the_dev_tool():
    runner = os.path.join(os.path.dirname(REPO), "analysis", "verification", "run_hole_fixtures.py")
    if not os.path.isfile(runner):
        pytest.skip("analysis/verification/run_hole_fixtures.py is not in this tree")
    img = _img(SNAPSHOTS)
    r = subprocess.run([sys.executable, "-B", runner, "--tool", FOREFST, "--images", os.path.dirname(img)],
                       capture_output=True, text=True, timeout=3600)
    assert r.returncode == 0 and "hole fixtures: PASS" in r.stdout, r.stdout[-2500:] + r.stderr[-1500:]
    assert "3 of 3 fixture(s)" in r.stdout, r.stdout[-1500:]


def test_n536_the_control_names_the_none_sidecar():
    tsv = os.path.join(os.path.dirname(REPO), "analysis", "verification", "hole_fixtures.tsv")
    if not os.path.isfile(tsv):
        pytest.skip("analysis/verification/hole_fixtures.tsv is not in this tree")
    rows = [ln.split("\t") for ln in open(tsv, encoding="utf-8") if ln.startswith("hole")]
    ctl = [r for r in rows if r[0] == "hole8-control"]
    assert ctl and ctl[0][6].strip() == "0:written:sidecar(none)" and ctl[0][7].strip() == "0:written:sidecar(none)"
    for r in rows:
        if r[0] != "hole8-control":
            assert r[6].strip() == "2:written:sidecar(holes_present)", r


# ═══ N538 / decision 56: a closed pipe ═══════════════════════════════════════════════════════════════════════════
# The maintainer, 2026-11-15 ("1,2 ok wit your recommendation", RC1D/G3/DESIGN.md section 10): (1) a closed pipe that
# carries only progress, statements and warnings does not stop the run; (2) a closed pipe that carries the output stops
# it quietly, with exit 2 if a finding or a skip was recorded before the close, else 0. Never exit 120.

MILLIONS = "step3/win11refs2tmillionsofactions.raw"     # exit 2 on every command: its Object Table is read in part


def _merged_pipe(argv, nlines):
    """`argv 2>&1 | head -nlines`: the exit code of the tool and the lines the reader took."""
    p = subprocess.Popen([sys.executable, "-B"] + argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    got = [p.stdout.readline() for _ in range(nlines)]
    p.stdout.close()
    return p.wait(timeout=1800), got


def _stdout_pipe(argv, nlines):
    """`argv | head -nlines` (stderr discarded): the exit code."""
    p = subprocess.Popen([sys.executable, "-B"] + argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for _ in range(nlines):
        p.stdout.readline()
    p.stdout.close()
    return p.wait(timeout=3600)


@pytest.mark.parametrize("tool,argv", [
    pytest.param("forefst", ["usn"], id="forefst-usn"),
    pytest.param("forefst", ["files"], id="forefst-files"),
    pytest.param("ra", ["forefst", "usn"], id="passthrough-usn"),
])
def test_n538_merged_stderr_closed_pipe_ends_quietly(tool, argv):
    """`usn 2>&1 | head -3` exited 120 (2026-11-11): the end-of-run note on stderr failed at the interpreter's exit. Now
    quietly, with the code of what was recorded before the close -- nothing on the public sample: 0."""
    rc, got = _merged_pipe([FOREFST if tool == "forefst" else RA, _img(SAMPLE)] + argv, 3)
    assert len(got) == 3 and all(got), got
    assert rc == 0, rc


def test_n538_1_a_closed_message_pipe_does_not_stop_a_file_export(tmp_path):
    """`files --csv FILE 2>&1 | head -1`: the pipe carries only messages, so the run goes on and writes FILE, the same
    bytes as a run with no pipe, with the same exit code (it stopped at the next line and never wrote FILE, exit 120)."""
    img = _img(SAMPLE)
    ref = str(tmp_path / "ref.csv")
    r = _run([FOREFST, img, "files", "--csv", ref])
    dest = str(tmp_path / "piped.csv")
    rc, got = _merged_pipe([FOREFST, img, "files", "--csv", dest], 1)
    assert got and got[0], got
    assert rc == r.returncode, (rc, r.returncode)
    assert os.path.exists(dest) and open(dest, "rb").read() == open(ref, "rb").read()
    assert not os.path.exists(dest + ".partial")


def test_n538_1_a_closed_stderr_pipe_does_not_stop_the_run(tmp_path):
    """stderr alone into a pipe the reader closes (`2>&1 >OUT | head -1`): the run goes on; OUT is the whole output
    and the exit code the run's own (it was 120)."""
    img = _img(SAMPLE)
    full = subprocess.run([sys.executable, "-B", FOREFST, img, "usn"], capture_output=True, timeout=1800)
    out = str(tmp_path / "usn.txt")
    with open(out, "wb") as o:
        p = subprocess.Popen([sys.executable, "-B", FOREFST, img, "usn"], stdout=o, stderr=subprocess.PIPE)
        p.stderr.readline()
        p.stderr.close()
        rc = p.wait(timeout=1800)
    assert rc == full.returncode, (rc, full.returncode)
    assert open(out, "rb").read() == full.stdout


def test_n538_2_a_finding_recorded_before_the_close_is_the_exit_code():
    """`files | head -1` on a volume whose Object Table is read in part (a finding recorded at the bootstrap, before any
    output): exit 2 (it was 0). The output is far larger than a pipe's buffer, so the close stops the run."""
    img = _img(MILLIONS)
    assert _run([FOREFST, img, "summary"], timeout=3600).returncode == 2, "premise: the volume's finding"
    assert _stdout_pipe([FOREFST, img, "files"], 1) == 2


def test_n538_2_control_a_clean_volume_closed_pipe_exits_0():
    assert _stdout_pipe([FOREFST, _img(SAMPLE), "files"], 1) == 0


def test_n538_control_a_closed_stdout_alone_ends_quietly():
    p = subprocess.Popen([sys.executable, "-B", FOREFST, _img(SAMPLE), "usn"], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    p.stdout.readline()
    p.stdout.close()
    err = p.stderr.read().decode("utf-8", "replace")
    assert p.wait(timeout=1800) == 0 and "Traceback" not in err, err[-1500:]


@pytest.mark.parametrize("words,want", [
    (["img.raw", "files", "--csv", "out.csv"], True),
    (["img.raw", "files", "--csv", "-"], False),
    (["img.raw", "files", "--csv"], False),
    (["img.raw", "timeline", "--csv", "--source", "MLOG"], False),
    (["img.raw", "files", "--csv", "-o", "out.csv"], True),
    (["img.raw", "extract", "/a.txt", "-o", "a.txt"], True),
    (["img.raw", "extract", "/a.txt"], False),
    (["img.raw", "export", "deleted", "DIR"], True),
    (["img.raw", "snapshots", "--extract", "DIR"], True),
    (["img.raw", "usn", "--json", "u.json"], True),
    (["img.raw", "summary"], False),
    (["img.raw", "forefst", "mlog", "--csv", "m.csv"], True),
], ids=lambda x: " ".join(x) if isinstance(x, list) else str(x))
def test_n538_unit_output_goes_elsewhere(words, want):
    assert F._output_goes_elsewhere(words) is want


def test_n538_unit_the_guard_silences_a_closed_message_pipe_and_raises_on_an_output_pipe():
    for silence in (True, False):
        r, w = os.pipe()
        os.close(r)                                      # the reader is gone
        fd = os.dup(w)
        stream = open(w, "w", buffering=1)
        g = F._PipeGuard(stream, w, lambda s=silence: s)
        try:
            if silence:
                g.write("a line\n")
                g.write("another\n")
                g.flush()                                # silenced: no error, the descriptor points at devnull
            else:
                with pytest.raises(BrokenPipeError):
                    g.write("a line\n")
                    g.flush()
        finally:
            try:
                stream.close()
            except OSError:
                pass
            os.close(fd)


# ═══ N539: the boot-sector checksums in JSON ══════════════════════════════════════════════════════════════════════

def test_n539_unit_the_checksum_keys_take_the_text_form():
    doc = F.machine_forms({"primary_cksum_stored": 0x2c14, "primary_cksum_computed": 0x2c14,
                           "backup": [{"cksum_stored": 0x7, "cksum_computed": None}]})
    assert doc == {"primary_cksum_stored": "0x2c14", "primary_cksum_computed": "0x2c14",
                   "backup": [{"cksum_stored": "0x0007", "cksum_computed": None}]}


def _checksum_leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _checksum_leaves(v, path + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _checksum_leaves(v, "%s[%d]" % (path, i))
    elif re.search(r"(?i)checksum(stored|computed)$", path.rsplit(".", 1)[-1]):
        yield path, o


@pytest.mark.parametrize("cmd", ["summary", "fastsummary", "integrity"])
def test_n539_json_checksums_are_hex_words(cmd):
    r = _run([FOREFST, _img(MINI314), cmd, "--json"])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    leaves = list(_checksum_leaves(json.loads(r.stdout)))
    assert len(leaves) >= 2, "premise: the VBR checksums are in the document"
    bad = [(p, v) for p, v in leaves if not (v is None or (isinstance(v, str) and re.fullmatch(r"0x[0-9a-f]{4}", v)))]
    assert not bad, bad


# ═══ N540: a directory the path map's walk did not reach ═════════════════════════════════════════════════════════

def _boot(rel):
    return F.bootstrap(_img(rel), None)


def _a_subdirectory(f, ps, cs, tr, obj_map):
    """(parent OID, child OID) of a directory below a directory below the root, from the complete path map."""
    full = F.build_oid_path_map(f, ps, cs, tr, obj_map)
    by_path = {p: o for o, p in full.items() if o >= 0x701}
    for o, p in sorted(full.items()):
        if o >= 0x701 and "/" in p and p.rsplit("/", 1)[0] in by_path:
            return by_path[p.rsplit("/", 1)[0]], o
    pytest.skip("premise: no directory two levels down")


def test_n540_a_skipped_table_makes_its_subdirectories_undetermined(monkeypatch):
    f, ps, cs, tr, roots, obj_map, *_ = _boot(SAMPLE)
    parent, child = _a_subdirectory(f, ps, cs, tr, obj_map)
    real = F.walk_bplus

    def walk(f_, ps_, cs_, tr_, vl, *a, **k):
        if k.get("oid") == parent:
            raise ValueError("planted: this directory's table cannot be read")
        return real(f_, ps_, cs_, tr_, vl, *a, **k)
    monkeypatch.setattr(F, "walk_bplus", walk)
    paths = F.build_oid_path_map(f, ps, cs, tr, obj_map)
    assert child not in paths
    assert F._usn_resolve_path(child, paths, obj_map) == "<undetermined 0x%x>" % child


def test_n540_the_depth_cutoff_makes_the_levels_below_undetermined(monkeypatch):
    f, ps, cs, tr, roots, obj_map, *_ = _boot(SAMPLE)
    parent, child = _a_subdirectory(f, ps, cs, tr, obj_map)
    monkeypatch.setattr(F, "DEFAULT_DEPTH", 0)
    paths = F.build_oid_path_map(f, ps, cs, tr, obj_map)
    missing = [o for o in obj_map if o >= 0x701 and o not in paths]
    assert missing, "premise: the cutoff leaves directories unnamed"
    assert all(F._usn_resolve_path(o, paths, obj_map) == "<undetermined 0x%x>" % o for o in missing)


def test_n540_control_a_complete_walk_keeps_unlinked():
    """A directory in the Object Table that a walk of the WHOLE tree does not name is unlinked, as before."""
    f, ps, cs, tr, roots, obj_map, *_ = _boot(SAMPLE)
    paths = F.build_oid_path_map(f, ps, cs, tr, obj_map)
    oid = max(obj_map) + 1
    om = dict(obj_map)
    om[oid] = obj_map[0x600]                             # a directory in the Object Table that no name row names
    assert F._usn_resolve_path(oid, paths, om) == "<unlinked 0x%x>" % oid
    _p, child = _a_subdirectory(f, ps, cs, tr, obj_map)
    assert F._usn_resolve_path(child, paths, obj_map) == paths[child]


# ═══ N545: where an export's statements go ═══════════════════════════════════════════════════════════════════════

_EARLIER = "of an earlier volume's log are left out"     # the one MLog statement win11refs2gtargeted_reformated has


def test_n545_mlog_csv_file_puts_its_statements_on_stdout(tmp_path):
    dest = str(tmp_path / "m.csv")
    r = _run([FOREFST, _img(REFORMATTED), "mlog", "--csv", dest])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    assert _EARLIER in r.stdout and _EARLIER not in r.stderr, (r.stdout[-800:], r.stderr[-800:])


def test_n545_mlog_json_file_puts_its_statements_on_stdout(tmp_path):
    dest = str(tmp_path / "m.json")
    r = _run([FOREFST, _img(REFORMATTED), "mlog", "--json", dest])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    assert _EARLIER in r.stdout and _EARLIER not in r.stderr, (r.stdout[-800:], r.stderr[-800:])


def test_n545_control_mlog_csv_on_stdout_keeps_its_statements_on_stderr():
    r = _run([FOREFST, _img(REFORMATTED), "mlog", "--csv"])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    assert _EARLIER in r.stderr and _EARLIER not in r.stdout
    assert r.stdout.splitlines()[0].startswith("TransactionIndex") or "," in r.stdout.splitlines()[0]


def test_n545_timeline_csv_file_puts_the_mlog_statements_on_stdout(tmp_path):
    dest = str(tmp_path / "t.csv")
    r = _run([FOREFST, _img(REFORMATTED), "timeline", "--csv", dest])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    assert "earlier" in r.stdout and "MLog" in r.stdout, r.stdout[-1500:]
    assert not re.search(r"\[forefst\] .*MLog row\(s\)", r.stderr), r.stderr[-1500:]


def test_n545_control_timeline_csv_on_stdout_keeps_them_on_stderr():
    r = _run([FOREFST, _img(REFORMATTED), "timeline", "--csv"])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    assert re.search(r"\[forefst\] .*MLog row\(s\)", r.stderr), r.stderr[-1500:]
    assert r.stdout.splitlines()[0].startswith("Timestamp,"), r.stdout[:300]


_NOT_READ = "the volume's creation time is not determined"


def _timestomp_csv(monkeypatch, capsys, dest):
    """`timestomp --csv DEST` in-process with the volume's times planted as not read (no corpus volume has them
    unreadable): (stdout, stderr)."""
    real = F.volume_information_read
    monkeypatch.setattr(F, "volume_information_read",
                        lambda *a, **k: ({}, "planted: not read") if a[-1] == "timestomp" else real(*a, **k))
    rc = F.cmd_timestomp(_img(MINI314), ["--csv", dest], None)
    assert rc in (0, 2, None)
    return capsys.readouterr()


def test_n545_timestomp_csv_file_puts_its_creation_time_note_on_stdout(monkeypatch, capsys, tmp_path):
    out, err = _timestomp_csv(monkeypatch, capsys, str(tmp_path / "ts.csv"))
    assert _NOT_READ in out and _NOT_READ not in err, (out[-800:], err[-800:])


def test_n545_control_timestomp_csv_on_stdout_keeps_the_note_on_stderr(monkeypatch, capsys):
    out, err = _timestomp_csv(monkeypatch, capsys, "-")
    assert _NOT_READ in err and _NOT_READ not in out, (out[-800:], err[-800:])


# ═══ N546: help extract ══════════════════════════════════════════════════════════════════════════════════════════

def test_n546_help_extract_lists_o_file_and_fill_holes():
    r = _run([FOREFST, "help", "extract"], timeout=120)
    assert r.returncode == 0, r.stderr
    assert re.search(r"^\s+-o FILE, --output FILE\s", r.stdout, re.M), r.stdout
    assert re.search(r"^\s+--fill-holes\s", r.stdout, re.M), r.stdout


def test_n546_extract_writes_homeoid_fileid():
    r = _run([FOREFST, "help", "extract"], timeout=120)
    assert "--id HomeOID:FileID" in r.stdout and "HomeOid" not in r.stdout and "FileId" not in r.stdout
    for argv in (["extract"], ["extract", "--id", "zz"]):
        e = _run([FOREFST, _img(MINI314)] + argv)
        assert e.returncode == 1 and "HomeOID:FileID" in e.stderr and "HomeOid" not in e.stderr, e.stderr[-800:]


# ═══ N548: a bundle that does not carry the Container Table ══════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def partial_bundle(tmp_path_factory):
    d = str(tmp_path_factory.mktemp("g3b") / "pb")
    r = _run([FOREFST, _img(MINI314), "export", "metadata", "-o", d, "--what", "vbr,chkp,supb"])
    assert r.returncode == 0, r.stderr[-1500:]
    v = _run([FOREFST, d, "verify-bundle"])
    return d, v


def test_n548_container_table_line_says_not_carried(partial_bundle):
    d, v = partial_bundle
    ct = [ln for ln in v.stderr.splitlines() if "WARNING: Container Table:" in ln]
    assert ct, "premise: the Container Table line" + v.stderr[-1500:]
    assert all("is carried by this bundle" in ln and "fail their check" not in ln for ln in ct), ct


def test_n548_vlcn_line_names_the_bundle_and_no_corruption(partial_bundle):
    d, v = partial_bundle
    vl = [ln for ln in v.stderr.splitlines() if "had no container mapping" in ln]
    assert vl, "premise: the VLCN line" + v.stderr[-1500:]
    assert all("r.raw" not in ln and "corrupt" not in ln for ln in vl), vl
    assert all(os.path.abspath(d) in ln and "not carried by this bundle" in ln for ln in vl), vl


def test_n548_control_the_full_bundle_has_neither_line(tmp_path):
    d = str(tmp_path / "fb")
    r = _run([FOREFST, _img(MINI314), "export", "metadata", "-o", d])
    assert r.returncode == 0, r.stderr[-1500:]
    v = _run([FOREFST, d, "verify-bundle"])
    assert "Container Table:" not in v.stderr and "had no container mapping" not in v.stderr, v.stderr[-1500:]


def test_n548_unit_an_image_keeps_its_wording():
    """On an image the VLCN line keeps the image's name and its cause (no bundle is read)."""
    class _T:
        misses, _warned, _image, ct_absent = 3, False, "x.raw", False
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        F._warn_translator(_T())
    assert "[x.raw] 3 VLCN(s) had no container mapping" in buf.getvalue()
    assert "corrupt/truncated container table" in buf.getvalue()


# ═══ N553 ════════════════════════════════════════════════════════════════════════════════════════════════════════

JOURNALED = "/System Volume Information/MountPointManagerRemoteDatabase"   # the public sample: a file with a $J record


def test_n553_b_refsanalysis_details_json_carries_the_journal_id_and_the_ea_size():
    # 1.14.0 group 5 (N543 b): on a file with a journal record -- one without (`/test/ok.txt`) has no journal id
    img = _img(SAMPLE)
    t = _run([RA, img, "details", JOURNALED])
    j = _run([RA, img, "details", JOURNALED, "--json"])
    assert t.returncode == 0 and j.returncode == 0, (t.stderr[-800:], j.stderr[-800:])
    doc = json.loads(j.stdout)
    m = re.search(r"USN journal ID: (0x[0-9a-f]{16})", t.stdout)
    assert m, "premise: the text prints the journal id" + t.stdout[-1500:]
    assert doc.get("USNJournalID") == m.group(1), doc
    assert "PackedEASize" in doc and (doc["PackedEASize"] is None or isinstance(doc["PackedEASize"], int)), doc
    e = re.search(r"PackedEaSize:\s+(\d+)", t.stdout)
    if e:
        assert doc["PackedEASize"] == int(e.group(1))


def _reparse_json(*extra):
    r = _run([FOREFST, _img(SPECIALS), "reparse", "--json"] + list(extra))
    assert r.returncode in (0, 2), r.stderr[-1500:]
    return json.loads(r.stdout)


def _keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _keys(v)


def test_n553_c_reparse_json_writes_the_tag_name_once():
    doc = _reparse_json()
    assert doc["ReparsePoints"], "premise: reparse points"
    assert "TagName" not in set(_keys(doc)), [p.get("ReparseData") for p in doc["ReparsePoints"][:2]]
    assert all(p["ReparseTag"] for p in doc["ReparsePoints"])


def test_n553_c_d_reparse_index_json_tag_once_marker_hex():
    doc = _reparse_json("--index")
    ents = doc["ReparseIndex"]
    assert ents, "premise: index rows"
    assert "TagName" not in set(_keys(doc)), ents[:2]
    m = [e["Marker"] for e in ents if "Marker" in e]
    assert m and all(isinstance(x, str) and re.fullmatch(r"0x[0-9a-f]{8}", x) for x in m), m[:5]
    assert all(e["ReparseTag"] for e in ents)


def test_n553_the_container_counts_comment_says_what_the_code_does():
    src = open(FOREFST, encoding="utf-8").read()
    assert "keep their\n        # old values until 1.14" not in src and "old values until 1.14 (PLAN_1.13.2 decision 25.5)" \
        not in src
