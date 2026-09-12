#!/usr/bin/env python3
"""DoD #1: one source of truth per computed fact.

`single_source.tsv` names each computed fact and the ONE function that computes it. This fails if a second
definition of that name appears anywhere in the two shipped tools.

Why definitions and not calls: `refsanalysis.py` calling `forefst.parse_chkp` is exactly the reuse that
makes it one source. `refsanalysis.py` defining its own `parse_chkp` is a fork, and a fork is how two
answers to one question start to drift -- which this project has already paid for twice (two name->record
resolution paths, two extent decoders whose disagreement was pinned at 18 while a wider sweep saw 144).

Limit, stated rather than discovered later: this checks that a NAME is defined once. It cannot see a second
implementation under a different name. That is what the corpus A/B checks are for -- assertion #27 compares
the extent readings' output, not their names.

    python3 analysis/verification/check_single_source.py
"""
import ast
import os
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


def main():
    rows = []
    for line in open(TSV, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
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

    if problems:
        print("single source: FAIL — %d problem(s):" % len(problems))
        for p in problems:
            print("   " + p)
        return 1
    print("single source: PASS — %d computed fact(s), each with exactly one definition." % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
