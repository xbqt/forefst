#!/usr/bin/env python3
"""Assert that every page stating a registered figure states the reference's value.

Companion to check_doc_drift.py, which compares similarly-worded sentences. Figures like CPC are stated on
five pages in wording so different that similarity cannot link them (containment 0.06-0.10), and those are
precisely the numbers that drift. This gate pins each such figure to the value in forclaude/reference/ and
checks every page that states it in the registered shape.

A registered figure that matches nowhere is also a failure: the pattern has rotted, and a gate that matches
nothing reports a clean bill of health while checking nothing.

Exit 0 when every match carries the registered value and every row matches at least once.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def register(path=None):
    rows = []
    for ln in open(path or os.path.join(HERE, "doc_figures.tsv"), encoding="utf-8"):
        if ln.startswith("#") or not ln.strip():
            continue
        fid, expected, pattern, why = ln.rstrip("\n").split("\t")
        rows.append((fid, expected.strip(), re.compile(pattern), why))
    return rows


def pages(tree):
    docs = os.path.join(tree, "docs")
    for dp, _d, fs in os.walk(docs):
        if "website" in dp or "_templates" in dp:
            continue
        for fn in sorted(fs):
            if fn.endswith(".md"):
                p = os.path.join(dp, fn)
                yield os.path.relpath(p, docs), open(p, encoding="utf-8").read()



def default_tree():
    """Dev keeps the pages under forefstdev/docs; a PUBLISHED tree has docs/ at its root.

    Resolving this wrong is how a gate passes only in the maintainer's checkout -- the published golden
    once hashed an absolute path for exactly that reason. Both layouts are probed here.
    """
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if os.path.isdir(os.path.join(root, "forefstdev", "docs")):
        return os.path.join(root, "forefstdev")
    return root


def main(tree=None):
    tree = tree or default_tree()
    rows = register()
    hits = {fid: 0 for fid, _e, _r, _w in rows}
    bad = []
    for rel, txt in pages(tree):
        # Whole text, not line by line: the pages are hard-wrapped, so "over the full" ends one line and
        # "4096-byte cluster" begins the next. Scanning lines made two patterns match nothing at all.
        # Emphasis markers are blanked to spaces -- SAME LENGTH, so every offset still maps to its real
        # line. Pages write "**16,384** on 4 KiB clusters"; a pattern expecting whitespace after the number
        # silently matched nothing there, and the gate reported "0 wrong" while checking no such page.
        txt = re.sub(r"[*`]", " ", txt)
        for fid, expected, rx, _why in rows:
            for mm in rx.finditer(txt):
                hits[fid] += 1
                got = mm.group(1).replace(",", "")
                if got != expected:
                    line = txt.count("\n", 0, mm.start()) + 1
                    ctx = " ".join(txt[max(0, mm.start() - 60):mm.end() + 60].split())
                    bad.append((fid, rel, line, got, expected, ctx[:150]))
    dead = [fid for fid, n in hits.items() if n == 0]
    if os.environ.get("FIGURES_VERBOSE"):
        for fid, n in sorted(hits.items()):
            print("      %-20s %d statement(s)" % (fid, n))
    print("doc figures: %d registered, %d statement(s) checked, %d wrong, %d pattern(s) matching nothing"
          % (len(rows), sum(hits.values()), len(bad), len(dead)))
    for fid, rel, i, got, expected, ln in bad:
        print("   WRONG  %s  %s:%d states %s, reference says %s" % (fid, rel, i, got, expected))
        print("          %s" % ln)
    for fid in dead:
        print("   DEAD   %s matches no page -- the pattern rotted, so it was checking nothing" % fid)
    return 1 if (bad or dead) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
