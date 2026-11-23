"""Read forefst's text output as the analyst reads it: one wrapped statement = one line -- exactly as the tool wrapped it.

Since 1.14.0 (PLAN 10.2 A3) forefst wraps a prose line longer than 110 characters at 100, with a hanging indent
(`_wprint`). Many tests find a statement by its line, or by a window of a few lines, so a statement that now spans more
lines than the window holds is no longer found, although its words are all there.

The output alone cannot say which lines are a wrapped statement: two data rows can look exactly like a wrap of their
concatenation (consecutive `files` rows do). So nothing here guesses. The tool's own run records what it wrapped
(`_wraplog/`: each wrapped print, the text printed and the text before wrapping), and `unwrap_exact` puts those texts
back, in the order printed, and touches nothing else.

- `run(cmd, **kw)`: `subprocess.run` with the recorder on (PYTHONPATH + FOREFST_TEST_WRAPLOG); stdout comes back with
  each wrapped block replaced by its line. `raw=True` returns (CompletedProcess as printed, pairs) instead.
- `recording()`: the same for an in-process run: `with recording() as pairs: ...`, then `unwrap_exact(text, pairs)`.

The wrapping itself (where it applies, the hanging indent, the 100 / 110 rule, data rows never wrapped) is tested in
test_1132_g4_ux.py on the raw output, never through this module; the recorder is tested in test_1132_g4_unwrap.py.
"""
import builtins
import contextlib
import json
import os
import subprocess
import sys
import tempfile

WRAPLOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wraplog")
sys.path.insert(0, WRAPLOG_DIR)
import _wraprec                                          # noqa: E402
del sys.path[0]


def unwrap_exact(text, pairs):
    """`text` (str or bytes) with each recorded wrapped block, in order, replaced by the text it was printed from. A
    block not found in `text` as printed (the tool buffered it and printed it changed) is left as is."""
    if not pairs or text is None:
        return text
    is_bytes = isinstance(text, bytes)
    out, pos = [], 0
    for printed, before in pairs:
        if is_bytes:
            printed, before = printed.encode("utf-8"), before.encode("utf-8")
        k = text.find(printed, pos)
        if k < 0:
            continue
        out += [text[pos:k], before]
        pos = k + len(printed)
    out.append(text[pos:])
    return (b"" if is_bytes else "").join(out)


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return [tuple(json.loads(ln)) for ln in fh if ln.strip()]


def run(cmd, raw=False, **kw):
    """`subprocess.run(cmd, **kw)` with the tool's wrap recorder on; stdout unwrapped exactly (see the docstring)."""
    fd, log = tempfile.mkstemp(prefix="wraplog_", suffix=".jsonl")
    os.close(fd)
    env = dict(kw.pop("env", None) or os.environ)
    env["FOREFST_TEST_WRAPLOG"] = log
    env["PYTHONDONTWRITEBYTECODE"] = "1"                 # no __pycache__ beside the recorder
    env["PYTHONPATH"] = WRAPLOG_DIR + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        r = subprocess.run(cmd, env=env, **kw)
        pairs = _read(log)
        if raw:
            return r, pairs
        r.stdout = unwrap_exact(r.stdout, pairs)
        return r
    finally:
        os.unlink(log)


@contextlib.contextmanager
def recording():
    """In-process: record what `_wprint` wraps while the block runs (yields the list of pairs)."""
    pairs = []
    real = builtins.print
    builtins.print = _wraprec.recorder(lambda printed, before: pairs.append((printed, before)), real)
    try:
        yield pairs
    finally:
        builtins.print = real
