"""Test instrument (PLAN 10.2 A3, 1.14.0), active only when FOREFST_TEST_WRAPLOG names a file: each line forefst's
`_wprint` wraps is recorded there, one JSON line `[text printed, text before wrapping]` per wrapped print, in the
order printed. The output is unchanged. `_unwrap.run` puts this folder first on PYTHONPATH and reads the file. Then
the sitecustomize this one shadows (the system's, if any) is run, as Python would have run it."""
import os
import sys

_LOG = os.environ.get("FOREFST_TEST_WRAPLOG")
if _LOG:
    import builtins
    import json
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _wraprec
    del sys.path[0]
    _fh = open(_LOG, "a", encoding="utf-8")

    def _sink(printed, before):
        _fh.write(json.dumps([printed, before]) + "\n")
        _fh.flush()                                      # complete even when the tool leaves through os._exit

    builtins.print = _wraprec.recorder(_sink, builtins.print)

_HERE = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
for _d in sys.path:
    _p = os.path.join(os.path.realpath(_d or os.curdir), "sitecustomize.py")
    if os.path.dirname(_p) != _HERE and os.path.isfile(_p):
        with open(_p, encoding="utf-8") as _f:
            exec(compile(_f.read(), _p, "exec"), {"__name__": "sitecustomize", "__file__": _p})
        break
