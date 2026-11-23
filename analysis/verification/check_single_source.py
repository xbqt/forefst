#!/usr/bin/env python3
"""DoD #1: one source of truth per computed fact.

`single_source.tsv` names each computed fact and the ONE function that computes it. This fails if a second
definition of that name appears anywhere in the two shipped tools.

Why definitions and not calls: `refsanalysis.py` calling `forefst.parse_chkp` is exactly the reuse that
makes it one source. `refsanalysis.py` defining its own `parse_chkp` is a fork, and a fork is how two
answers to one question start to drift -- which this project has already paid for twice (two name->record
resolution paths, two extent decoders whose disagreement was pinned at 18 while a wider sweep saw 144).

Limit of the definition pass, stated rather than discovered later: it checks that a NAME is defined once. It
cannot see a second implementation under a different name. That is what the corpus A/B checks are for --
assertion #27 compares the extent readings' output, not their names -- and, for two facts, the call-site pass.

The call-site pass (1.13.2, plan item A11). Checkpoint selection and the exit rule were copied INLINE, under no
name at all: `refsanalysis summary` ranked the checkpoint copies with its own `>=` over the +0x10 clock while
forefst ranked them on +0x60 among copies that pass their checksum, and refsanalysis exited through a bare
`sys.exit(handler(...))` that never saw forefst's exit rule. A definition check cannot see either. So:

  (a) clock -- a CHECKPOINT CLOCK is the first value of parse_chkp(), or `le64(<buf>, 0x10|0x60)` in a function
      that handles checkpoints (one that mentions b"CHKP" or calls parse_chkp()/checkpoint_select()), or a dict
      key such a value was stored under anywhere in either tool (`"vc"`, `"virtual_clock"`, ...), or a name or
      container that holds one. Outside the functions of the rows `checkpoint_select` and `checkpoint_parse`:
        * every READ of a checkpoint clock is a violation, and
        * every comparison (<, <=, >, >=, ==, !=), max(), min(), sorted() or .sort() over one is a violation,
      unless an `@allow` row of single_source.tsv names that site: file, function, kind (read / compare) and a
      fragment of its code. A `read` entry never exempts a `compare`, so allowing a display read cannot let a
      selection through. An `@allow` row that matches nothing is itself a failure (a stale exemption).
      `x is None` / `is not None` tests are not comparisons of the clock's value and are not flagged.
  (b) exit -- every `sys.exit(<non-constant>)`, `os._exit(<non-constant>)` and `raise SystemExit(<non-constant>)`
      must pass its code through `rc_escalate(...)`, and a `__main__` block must not drop main()'s return
      value (the shape that made `refsanalysis <image> forefst <cmd>` exit 0 where forefst exited 2).
      Constant exits (help, usage, argument errors) are allowed by rule.
  (c) discard (K7, the plan's "command return of an rc that does not pass through rc_escalate") -- a COMMAND is a
      call to a `cmd_*` function or to a name bound from `_HANDLERS`. Its return code must be used: a command
      called as a bare statement is a violation, and so is a `try` that runs a command and catches SystemExit
      without re-raising it or reading the caught exception (the code is lost). Reading the exception counts as
      using its code, so a handler that only PRINTS `e.code` and still returns 0 passes this clause -- the
      command's real exit code needs its own RED (review A11-close F1). `@allow` rows of kind `discard`
      name a site that is known and owned by a later fix; like every allow row, one that matches nothing fails.

The clock KEYS are derived over both tools together, not file by file: forefst's checkpoint_select stores the
clock under "vc", and refsanalysis re-ranking the copies it returns must be caught there too (review N1).

Limits of the call-site pass: the data flow is per function and flow-insensitive (a clock, or a checkpoint page,
passed as an argument and read or compared inside the callee is not followed -- `_check_page`'s page-clock bound
is such a site -- and neither is a clock RETURNED by a helper), and it does not see a caller that DISCARDS a
sub-command's return code by assigning it and never reading the name (clause (c) sees the bare call and the
swallowed SystemExit, not an unread variable). A clock read is recognised only as `le64(<buf>, 0x10|0x60)` with a literal offset or as
parse_chkp()'s first value: `struct.unpack_from`, `int.from_bytes` and an offset held in a named constant are not
recognised. A clock key is followed only as a literal subscript (`c["vc"]`), `.get("vc")` or a dict display: a
key held in a variable (`c[k]`), attribute access (a namedtuple or SimpleNamespace), and a key stored with
`dict(vc=...)`, `.update(vc=...)` or `.setdefault("vc", ...)` are not. A comparison is recognised in a compare
operator, max(), min(), sorted() and .sort() with the key as a lambda: a key function written with `def`,
`operator.itemgetter`, and `heapq.nlargest`/`nsmallest` are not. The exit pass does not recognise an aliased `sys`
module (`import sys as s; s.exit(rc)`). No live site uses any of these shapes (reviews A11 V5-V10 and N1 F4).

    python3 analysis/verification/check_single_source.py
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TSV = os.path.join(ROOT, "analysis/verification/single_source.tsv")
# Dev keeps the tools under forefstdev/; a PUBLISHED tree has them at the root. The list below records
# the DEV paths, and `_resolve` maps a row's owner onto whichever layout this tree actually is -- the same
# portability the hole-fixture runner needed, and found missing by rehearsing the sync.
TOOLS_DEV = ("forefstdev/forefst.py", "forefstdev/refsanalysis.py")
TOOLS_PUB = ("forefst.py", "refsanalysis.py")
TOOLS = TOOLS_DEV if os.path.exists(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "forefstdev/forefst.py")) else TOOLS_PUB

ALLOW = "@allow"                                   # first column of an allow-list row
CLOCK_FACTS = ("checkpoint_select", "checkpoint_parse")   # the rows whose functions may read/compare clocks
EXIT_RULE = "rc_escalate"
CLOCK_OFFSETS = (0x10, 0x60)
CHKP_PARSERS = {"parse_chkp", "_forefst_parse_chkp"}
CHKP_SELECTORS = {"checkpoint_select"}
_PROPAGATE = {"max", "min", "sorted", "list", "tuple", "set", "frozenset", "int", "abs", "next", "reversed",
              "iter", "dict", "enumerate", "zip", "filter", "map"}
_ORDER_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)


def _resolve(owner):
    """Map a row's recorded dev path onto this tree's layout."""
    return owner if owner in TOOLS else os.path.basename(owner)


def definitions(path):
    """Every function name defined in a file, with the line, including nested defs."""
    out = {}
    try:
        tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
    except (OSError, SyntaxError) as exc:
        print("single source: FAIL — cannot parse %s: %s" % (path, exc))
        raise SystemExit(1)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, []).append(node.lineno)
    return out


# ─── the call-site pass ───────────────────────────────────────────────────────────────────────────────────

def _norm(s):
    return re.sub(r"\s+", "", s or "")


def _const_str(node):
    idx = getattr(ast, "Index", None)                  # Python < 3.9 wraps a subscript in ast.Index
    if idx is not None and isinstance(node, idx):
        node = node.value
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _callee(node):
    """The called name: `f(...)` -> "f", `a.b.f(...)` -> "f"."""
    fn = node.func
    return fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)


def _names_in(target):
    return [n.id for n in ast.walk(target) if isinstance(n, ast.Name)]


class _Scope:
    """Flow-insensitive clock taint for one top-level function (nested defs and lambdas share its names)."""

    def __init__(self, node, keys):
        self.node, self.keys, self.tainted, self.new_keys = node, keys, set(), set()
        self.chkp = any(
            (isinstance(n, ast.Constant) and n.value == b"CHKP")
            or (isinstance(n, ast.Call) and _callee(n) in (CHKP_PARSERS | CHKP_SELECTORS))
            for n in ast.walk(node))
        self.loaded = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}

    def is_read(self, n):
        return (isinstance(n, ast.Call) and _callee(n) == "le64" and len(n.args) == 2
                and isinstance(n.args[1], ast.Constant) and n.args[1].value in CLOCK_OFFSETS and self.chkp)

    def t(self, n):
        """Does expression `n` carry a checkpoint clock (a value, or a container holding one)?"""
        if n is None:
            return False
        if isinstance(n, ast.Name):
            return n.id in self.tainted
        if isinstance(n, ast.Call):
            c = _callee(n)
            if self.is_read(n) or c in CHKP_PARSERS:
                return True
            if isinstance(n.func, ast.Name) and c in _PROPAGATE:
                return any(self.t(a) for a in n.args)
            if isinstance(n.func, ast.Attribute):
                if c == "get" and n.args and _const_str(n.args[0]) in self.keys:
                    return True
                if c in ("get", "values", "items", "copy", "pop", "setdefault"):
                    return self.t(n.func.value)
            return False
        if isinstance(n, ast.Subscript):
            return _const_str(n.slice) in self.keys or self.t(n.value)
        if isinstance(n, ast.BinOp):
            return self.t(n.left) or self.t(n.right)
        if isinstance(n, ast.UnaryOp):
            return self.t(n.operand)
        if isinstance(n, ast.BoolOp):
            return any(self.t(v) for v in n.values)
        if isinstance(n, ast.IfExp):
            return self.t(n.body) or self.t(n.orelse)
        if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
            return any(self.t(e) for e in n.elts)
        if isinstance(n, ast.DictComp):
            return self.t(n.value)
        if isinstance(n, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            return self.t(n.elt)
        if isinstance(n, ast.Lambda):
            return self.t(n.body)
        if isinstance(n, (ast.Starred, ast.NamedExpr)):
            return self.t(n.value)
        return False                           # Constant, Compare (a bool), JoinedStr, Attribute, Dict (a record)

    def _bind(self, tgt, value):
        if isinstance(tgt, ast.Name):
            if self.t(value):
                self.tainted.add(tgt.id)
        elif isinstance(tgt, ast.Subscript):
            key = _const_str(tgt.slice)
            if self.t(value):
                if key is not None:
                    self.new_keys.add(key)            # a clock stored under a key: the key now means "clock"
                else:
                    self.tainted.update(_names_in(tgt.value))
        elif isinstance(tgt, (ast.Tuple, ast.List)):
            if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(tgt.elts):
                for a, b in zip(tgt.elts, value.elts):
                    self._bind(a, b)
            elif isinstance(value, ast.Call) and _callee(value) in CHKP_PARSERS and tgt.elts:
                first = tgt.elts[0]                   # parse_chkp -> (vclock, flags, roots): only the first
                if isinstance(first, ast.Name):
                    self.tainted.add(first.id)
                elif isinstance(first, ast.Subscript) and _const_str(first.slice) is not None:
                    self.new_keys.add(_const_str(first.slice))
            elif self.t(value):
                for e in tgt.elts:
                    self.tainted.update(_names_in(e))

    def propagate(self):
        before = None
        while before != (len(self.tainted), len(self.new_keys)):
            before = (len(self.tainted), len(self.new_keys))
            self.keys = self.keys | self.new_keys
            for n in ast.walk(self.node):
                if isinstance(n, ast.Assign):
                    for tgt in n.targets:
                        self._bind(tgt, n.value)
                elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and n.value is not None:
                    self._bind(n.target, n.value)
                elif isinstance(n, (ast.For, ast.comprehension)):
                    if self.t(n.iter):
                        self.tainted.update(_names_in(n.target))
                elif isinstance(n, ast.Dict):
                    for k, v in zip(n.keys, n.values):
                        if _const_str(k) is not None and self.t(v):
                            self.new_keys.add(_const_str(k))
                elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr in ("append", "extend", "add", "insert") and n.args
                      and self.t(n.args[-1])):
                    self.tainted.update(_names_in(n.func.value))
        return self.new_keys

    def violations(self):
        out = []
        for n in ast.walk(self.node):
            if self.is_read(n):
                out.append(("read", n, "a checkpoint-clock read"))
            elif isinstance(n, ast.Call) and _callee(n) in CHKP_PARSERS:
                out.append(("read", n, "a parse_chkp() call (its first value is a checkpoint clock)"))
            elif isinstance(n, ast.Compare):
                ops = [o for o in n.ops if isinstance(o, _ORDER_OPS)]
                sides = [n.left] + list(n.comparators)
                none = any(isinstance(x, ast.Constant) and x.value is None for x in sides)
                if ops and not none and any(self.t(x) for x in sides):
                    out.append(("compare", n, "a comparison over a checkpoint clock"))
            elif isinstance(n, ast.Call):
                c = _callee(n)
                keyf = next((k.value for k in n.keywords if k.arg == "key"), None)
                if isinstance(n.func, ast.Name) and c in ("max", "min", "sorted"):
                    if any(self.t(a) for a in n.args) or self.t(keyf):
                        out.append(("compare", n, "%s() over a checkpoint clock" % c))
                elif isinstance(n.func, ast.Attribute) and c == "sort":
                    if self.t(n.func.value) or self.t(keyf):
                        out.append(("compare", n, ".sort() over a checkpoint clock"))
        # the parser call is flagged once, only when its first value is actually used
        return [v for v in out if not (v[0] == "read" and _callee(v[1]) in CHKP_PARSERS
                                       and not self._parser_result_used(v[1]))]

    def _parser_result_used(self, call):
        for n in ast.walk(self.node):
            if isinstance(n, ast.Assign) and n.value is call:
                tgt = n.targets[0]
                if isinstance(tgt, (ast.Tuple, ast.List)) and tgt.elts:
                    first = tgt.elts[0]
                    return not (isinstance(first, ast.Name) and first.id not in self.loaded)
                return True
        return True                                   # used inside an expression: its value is consumed


def _scopes(tree):
    """(top-level name, node) for every module-level function and class method, plus the module body."""
    out = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((n.name, n))
        elif isinstance(n, ast.ClassDef):
            out.extend((m.name, m) for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)))
    body = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    out.append(("<module>", ast.Module(body=body, type_ignores=[])))
    return out


def _innermost(scope_node, target):
    """The name of the innermost def containing `target` inside `scope_node`."""
    best = getattr(scope_node, "name", "<module>")
    for n in ast.walk(scope_node):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not scope_node:
            if any(x is target for x in ast.walk(n)):
                best = n.name
    return best


def _exit_violations(tree):
    out = []
    parents = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parents[c] = p

    def _escalated(expr):
        return isinstance(expr, ast.Call) and _callee(expr) == EXIT_RULE

    for n in ast.walk(tree):
        arg, what = None, None
        if isinstance(n, ast.Call):
            fn = n.func
            is_exit = ((isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name)
                        and (fn.value.id, fn.attr) in (("sys", "exit"), ("os", "_exit")))
                       or (isinstance(fn, ast.Name) and fn.id in ("exit", "quit")))
            if is_exit:
                arg, what = (n.args[0] if n.args else None), "%s(<non-constant>)" % ast.unparse(fn)
        elif isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and _callee(n.exc) == "SystemExit":
            arg, what = (n.exc.args[0] if n.exc.args else None), "raise SystemExit(<non-constant>)"
        if what and arg is not None and not isinstance(arg, ast.Constant) and not _escalated(arg):
            out.append(("exit", n, "%s that does not pass through %s" % (what, EXIT_RULE)))
    # a __main__ block must not drop main()'s return value
    for blk in tree.body:
        if not (isinstance(blk, ast.If) and "__name__" in ast.unparse(blk.test) and "__main__" in ast.unparse(blk.test)):
            continue
        esc_names = set()
        for n in ast.walk(blk):
            if _escalated(n):
                esc_names.update(x.id for a in n.args for x in ast.walk(a) if isinstance(x, ast.Name))
        for n in ast.walk(blk):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "main":
                p, ok = parents.get(n), False
                while p is not None and p is not blk:
                    if _escalated(p):
                        ok = True
                        break
                    if isinstance(p, ast.Assign):
                        ok = any(isinstance(t, ast.Name) and t.id in esc_names for t in p.targets)
                        break
                    p = parents.get(p)
                if not ok:
                    out.append(("exit", n, "main()'s return value never reaches %s" % EXIT_RULE))
    return out


def clock_keys(sources, keys=None):
    """The dict keys that hold a checkpoint clock, derived over ALL the given sources together, to a fixpoint (a
    key found in one function applies in every other function of every file). Per file is not enough: forefst's
    checkpoint_select stores the clock under "vc" and "vc_page", and refsanalysis reads the dict it returns, so a
    refsanalysis pass that started from refsanalysis's own keys passed `max(sel["copies"], key=lambda c: c["vc"])`
    (review N1, plants R1-R4)."""
    scopes = [s for src in sources for s in _scopes(ast.parse(src))]
    keys = set(keys or ())
    while True:
        found = set()
        for _name, node in scopes:
            found |= _Scope(node, keys).propagate()
        if found <= keys:
            return keys
        keys |= found


def _is_command(call, handlers):
    c = _callee(call)
    return bool(c) and (c.startswith("cmd_") or (isinstance(call.func, ast.Name) and call.func.id in handlers))


def _discard_violations(node):
    """(c): commands whose return code is dropped, in one top-level function. [(kind, node, why)]"""
    handlers = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            v = n.value
            src_tbl = v.func.value if (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                                       and v.func.attr == "get") else (v.value if isinstance(v, ast.Subscript) else None)
            if isinstance(src_tbl, ast.Name) and src_tbl.id == "_HANDLERS":
                handlers.update(t.id for t in n.targets if isinstance(t, ast.Name))
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and _is_command(n.value, handlers):
            out.append(("discard", n, "a command's return code is dropped (a bare call)"))
        elif isinstance(n, ast.Try) and any(isinstance(c, ast.Call) and _is_command(c, handlers)
                                           for b in n.body for c in ast.walk(b)):
            for h in n.handlers:
                names = ([h.type] if not isinstance(h.type, ast.Tuple) else list(h.type.elts)) if h.type else []
                if not any(isinstance(t, ast.Name) and t.id in ("SystemExit", "BaseException") for t in names) \
                        and h.type is not None:
                    continue
                reraise = any(isinstance(x, ast.Raise) for b in h.body for x in ast.walk(b))
                read = h.name is not None and any(isinstance(x, ast.Name) and x.id == h.name
                                                  for b in h.body for x in ast.walk(b))
                if not (reraise or read):
                    out.append(("discard", h, "a command's SystemExit is caught and its code dropped"))
    return out


def callsite_problems(path, src, exempt, allows, keys=None, used=None):
    """Violations of (a), (b) and (c) in one tool file, as printable strings. `allows` = the @allow rows for this
    file; `used` collects the allow rows that matched something (for the stale-entry check). `keys` = clock keys
    derived elsewhere (callsite_pass passes those of all the tools); this file's own are added here."""
    tree = ast.parse(src)
    lines = src.splitlines()
    scopes = _scopes(tree)
    keys = clock_keys([src], keys)
    problems = []
    for name, node in scopes:
        if name in exempt:
            continue
        sc = _Scope(node, keys)
        sc.propagate()
        for kind, n, why in sc.violations():
            inner = _innermost(node, n)
            code = ast.get_source_segment(src, n) or ""
            line = lines[n.lineno - 1] if 0 < n.lineno <= len(lines) else ""
            hit = None
            for i, a in enumerate(allows):
                if a["kind"] == kind and a["function"] in (name, inner) and \
                        (_norm(a["fragment"]) in _norm(code) or _norm(a["fragment"]) in _norm(line)):
                    hit = i
                    break
            if hit is not None:
                if used is not None:
                    used.add(hit)
                continue
            problems.append("%s:%d in %s: %s outside checkpoint_select: %s"
                            % (path, n.lineno, inner if inner == name else "%s (in %s)" % (inner, name),
                               why, " ".join(code.split())[:110]))
    for name, node in scopes:
        for kind, n, why in _discard_violations(node):
            inner = _innermost(node, n)
            code = ast.get_source_segment(src, n) or ""
            line = lines[n.lineno - 1] if 0 < n.lineno <= len(lines) else ""
            hit = next((i for i, a in enumerate(allows) if a["kind"] == kind and a["function"] in (name, inner)
                        and (_norm(a["fragment"]) in _norm(code) or _norm(a["fragment"]) in _norm(line))), None)
            if hit is not None:
                if used is not None:
                    used.add(hit)
                continue
            problems.append("%s:%d in %s: %s: %s" % (path, n.lineno, inner, why, " ".join(code.split())[:110]))
    for kind, n, why in _exit_violations(tree):
        problems.append("%s:%d: %s: %s" % (path, n.lineno, why, " ".join((ast.get_source_segment(src, n) or "").split())[:110]))
    return problems


def callsite_pass(srcs, exempt, allows):
    """The call-site pass over several files, exactly as main() runs it on the two tools: the clock keys are
    derived over ALL the files first, then each file is checked with them. `srcs` = {path: source}; `exempt` =
    {path: functions allowed to read and compare clocks}; `allows` = the @allow rows (each with its "file").
    Returns (problems, indices of the allow rows that matched a site)."""
    keys = clock_keys(list(srcs.values()))
    problems, used = [], set()
    for p, src in srcs.items():
        idx = [i for i, a in enumerate(allows) if a["file"] == p]
        u = set()
        problems += callsite_problems(p, src, exempt.get(p, set()), [allows[i] for i in idx], keys=keys, used=u)
        used |= {idx[i] for i in u}
    return problems, used


# The self-test's provider: the one function allowed to read clocks (exempt, like checkpoint_select), in ANOTHER
# file than the cases. It stores the clock under "vc", so every case that needs that key gets it the way
# refsanalysis gets it from forefst -- across files -- and no case is handed a key the real run would not derive.
_SELF_TEST_PROVIDER = ("provider.py", "def checkpoint_select(fh, ps, cs, ls):\n    out = []\n    for l in ls:\n"
                       "        vc, fl, r = parse_chkp(fh, ps, cs, l)\n        out.append({'vc': vc})\n"
                       "    return {'copies': out}\n")


def _self_test():
    """The pass must be able to fail. Known answers, run every time, through callsite_pass (main's own path)."""
    cases = [
        ("def f(fh, ps, cs, l):\n    vc, fl, r = parse_chkp(fh, ps, cs, l)\n    if vc >= 3:\n        pass\n", 2),
        ("def f(raw):\n    if raw[:4] == b'CHKP':\n        x = le64(raw, 0x60)\n    return x\n", 1),
        ("def f(raw):\n    x = le64(raw, 0x60)\n    return x\n", 0),               # not a checkpoint function
        ("def f(recs):\n    return max(recs, key=lambda c: c['vc'])\n", 1),
        ("def f(r):\n    return r.get('vc') is not None\n", 0),
        ("def f(fh, ps, cs, ls):\n    out = []\n    for l in ls:\n        vc, fl, r = parse_chkp(fh, ps, cs, l)\n"
         "        out.append((vc, l))\n    out.sort(key=lambda x: x[0])\n", 2),
        ("import sys\ndef f(rc):\n    sys.exit(rc)\n", 1),
        ("import sys\ndef f(rc):\n    sys.exit(rc_escalate(rc))\n    sys.exit(1)\n", 0),
        ("if __name__ == '__main__':\n    main()\n", 1),
        ("import sys\nif __name__ == '__main__':\n    _r = main()\n    sys.exit(rc_escalate(_r))\n", 0),
        # N1: a re-selection over the provider's copies, keyed by a clock only the OTHER file stores
        ("def g(f, ps, cs, ls):\n    return max(checkpoint_select(f, ps, cs, ls)['copies'], key=lambda c: c['vc'])\n",
         1),
        # N1 review F3: a chain vc -> vc2 -> vc3 stored in functions that come AFTER the one comparing vc3, so each
        # key is known only one round after the previous one; derivation that stops after one or two rounds misses it
        ("def h(rs):\n    return max(rs, key=lambda c: c['vc3'])\ndef g3(c, r):\n    r['vc3'] = c['vc2']\n"
         "def g2(c, r):\n    r['vc2'] = c['vc']\n", 1),
        # K7 (c): a command's return code dropped, as a bare call or through a swallowed SystemExit
        ("def a(img):\n    handler = _HANDLERS.get('x')\n    handler(img, [], 0)\n    return 0\n", 1),
        ("def a(img):\n    cmd_x(img, [], 0)\n    return 0\n", 1),
        ("def a(img):\n    rc = cmd_x(img, [], 0)\n    return rc\n", 0),
        ("def a(img):\n    try:\n        rc = cmd_x(img, [], 0)\n    except SystemExit:\n        return 0\n"
         "    return rc\n", 1),
        ("def a(img):\n    try:\n        rc = cmd_x(img, [], 0)\n    except SystemExit as e:\n"
         "        return rc_escalate(e.code)\n    return rc\n", 0),
        # review A11-close F2: each sub-rule of (c) has a case
        ("def a(img):\n    handler = _HANDLERS['x']\n    handler(img, [], 0)\n    return 0\n", 1),
        ("def a(img):\n    try:\n        rc = cmd_x(img, [], 0)\n    except BaseException:\n        return 0\n"
         "    return rc\n", 1),
        ("def a(img):\n    try:\n        rc = cmd_x(img, [], 0)\n    except:\n        return 0\n    return rc\n", 1),
        ("def a(img):\n    try:\n        rc = cmd_x(img, [], 0)\n    except SystemExit:\n        print('x')\n"
         "        raise\n    return rc\n", 0),
    ]
    pfile, psrc = _SELF_TEST_PROVIDER
    fails = []
    for src, want in cases:
        # the case file FIRST: a derivation that kept only the first file's keys must fail here (N1 review F2)
        problems, _used = callsite_pass({"t.py": src, pfile: psrc}, {pfile: {"checkpoint_select"}}, [])
        got = len(problems)
        if got != want:
            fails.append((src, want, got))
    return fails, len(cases)


def main():
    rows, allows = [], []
    for line in open(TSV, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if parts[0] == ALLOW:
            if len(parts) < 6 or parts[3] not in ("read", "compare", "discard"):
                print("single source: FAIL — malformed %s row (need file, function, read|compare|discard, fragment, "
                      "why): %r" % (ALLOW, line))
                return 1
            allows.append({"file": _resolve(parts[1]), "function": parts[2], "kind": parts[3],
                           "fragment": parts[4], "why": parts[5], "row": line})
            continue
        if len(parts) < 3:
            print("single source: FAIL — malformed row: %r" % line)
            return 1
        rows.append(parts[:4])
    if not rows:
        print("single source: FAIL — no facts listed; the file is the contract and it is empty")
        return 1

    defs = {p: definitions(p) for p in TOOLS}
    problems = []
    for fact, fn, owner, *_rest in rows:
        owner = _resolve(owner)
        if owner not in defs:
            problems.append("%s: owner file %r is not one of the shipped tools" % (fact, owner))
            continue
        where = [(p, lns) for p, d in defs.items() for name, lns in d.items() if name == fn]
        if not where:
            problems.append("%s: %s() is not defined anywhere — the list is stale" % (fact, fn))
            continue
        total = sum(len(lns) for _p, lns in where)
        if total > 1:
            detail = "; ".join("%s:%s" % (p, ",".join(map(str, lns))) for p, lns in where)
            problems.append("%s: %s() has %d definitions (%s) — one fact, one function"
                            % (fact, fn, total, detail))
        elif where[0][0] != owner:
            problems.append("%s: %s() is defined in %s, the list says %s"
                            % (fact, fn, where[0][0], owner))

    # the call-site pass
    st_fails, st_n = _self_test()
    for src, want, got in st_fails:
        problems.append("call-site self-test: %r expected %d finding(s), got %d — the pass cannot be trusted"
                        % (src.strip()[:60], want, got))
    exempt = {}
    for fact, fn, owner, *_rest in rows:
        if fact in CLOCK_FACTS:
            exempt.setdefault(_resolve(owner), set()).add(fn)
    srcs = {p: open(os.path.join(ROOT, p), encoding="utf-8").read() for p in TOOLS}
    cs, used = callsite_pass(srcs, exempt, allows)
    problems += ["call-site: " + c for c in cs]
    n_sites = 0
    for i, a in enumerate(allows):
        if i not in used:
            problems.append("call-site: stale %s row (matches no site): %s" % (ALLOW, a["row"]))
        else:
            n_sites += 1

    if problems:
        print("single source: FAIL — %d problem(s):" % len(problems))
        for p in problems:
            print("   " + p)
        return 1
    print("single source: PASS — %d computed fact(s), each with exactly one definition; call-site pass: 0 "
          "violations (%d allow-listed site(s); self-test %d/%d)" % (len(rows), n_sites, st_n, st_n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
