"""Test instrument (PLAN 10.2 A3, 1.14.0): a `print` that records what forefst's `_wprint` wrapped.

`recorder(sink, real_print)` returns a function to install as `builtins.print`. It calls `real_print` with exactly the
arguments it was given -- the output is unchanged -- and, when the caller is forefst's `_wprint` and the text it prints
differs from the text it was given (the line was wrapped), it hands `sink` the pair (text printed, text before
wrapping). `_wprint` is the only place forefst wraps; its own arguments (`args`, `sep`) are read from its frame.
Used by `sitecustomize.py` here (a CLI run) and by `_unwrap.recording` (an in-process run)."""
import sys


def recorder(sink, real_print):
    def print(*args, **kw):                              # noqa: A001 -- installed as builtins.print
        try:
            f = sys._getframe(1)
            if f.f_code.co_name == "_wprint" and "_wrap_lines" in f.f_globals and len(args) == 1:
                loc = f.f_locals
                before = loc["sep"].join(str(a) for a in loc["args"])
                if before != args[0]:
                    sink(args[0], before)
        except Exception:                                # the instrument never changes what the tool does
            pass
        return real_print(*args, **kw)
    return print
