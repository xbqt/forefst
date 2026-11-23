"""The test instrument of group 4's A3 (1.14.0): `_unwrap` reads forefst's output with each block the tool wrapped
put back on one line -- from the tool's own record of what it wrapped (`_wraplog/`), never from the output's shape.
Checked here: the record leaves the output unchanged; it holds every wrapped block and nothing else (against a run
with wrapping off); a listing is never joined. Volumes: win11refsmini (step1), the public sample."""
import contextlib
import io
import os
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                     # noqa: E402
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
MINI314 = "step1/win11refsmini.raw"
SAMPLE = "step5/win11refstestmftecmd.raw"
_NOWRAP = ("import sys; sys.path.insert(0, %r); import forefst as F; F._WRAP_TOLERANCE = 10 ** 9; "
           "sys.argv = ['forefst.py'] + sys.argv[1:]; F.main()" % REPO)


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _flat(text):
    """Each line as (indent, words): what a wrap keeps."""
    return [(len(x) - len(x.lstrip()), x.split()) for x in text.split("\n")]


@pytest.mark.parametrize("args", [("integrity", "--checksums"), ("summary",), ("mlog", "--stats")],
                         ids=["integrity", "summary", "mlog"])
def test_the_record_leaves_the_output_unchanged_and_puts_back_exactly_what_was_wrapped(args):
    img = _img(MINI314)
    cmd = [sys.executable, "-B", FOREFST, img] + list(args)
    plain = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    r, pairs = UW.run(cmd, raw=True, capture_output=True, text=True, timeout=1800)
    assert (r.returncode, r.stdout, r.stderr) == (plain.returncode, plain.stdout, plain.stderr)
    assert pairs, "nothing wrapped in `%s`: the check below would be empty" % " ".join(args)
    for printed, before in pairs:
        assert printed in r.stdout and "\n".join(x for ln in before.split("\n") for x in F._wrap_lines(ln)) == printed
    nowrap = subprocess.run([sys.executable, "-B", "-c", _NOWRAP, img] + list(args), capture_output=True, text=True,
                            timeout=1800).stdout
    assert _flat(UW.unwrap_exact(r.stdout, pairs)) == _flat(nowrap)      # every wrapped block, and only those


def test_a_listing_is_never_joined():
    """`files` prints rows, never through `_wprint`: nothing recorded, nothing joined -- although consecutive rows can
    look exactly like a wrap of their concatenation, which is why the output's shape is never used."""
    cmd = [sys.executable, "-B", FOREFST, _img(SAMPLE), "files"]
    r, pairs = UW.run(cmd, raw=True, capture_output=True, text=True, timeout=1800)
    assert r.returncode in (0, 2) and pairs == [] and UW.unwrap_exact(r.stdout, pairs) == r.stdout


def test_in_process_recording_records_wprint_only():
    buf = io.StringIO()
    line = "  Statement: " + " ".join("word%d" % i for i in range(40))
    with UW.recording() as pairs, contextlib.redirect_stdout(buf):
        F._wprint(line)
        print("a long plain print that is not prose " * 4)
    assert pairs == [("\n".join(F._wrap_lines(line)), line)], pairs
    assert UW.unwrap_exact(buf.getvalue(), pairs).split("\n")[0] == line
