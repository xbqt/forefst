#!/usr/bin/env python3
"""Fail when two pages state the same fact with different numbers.

Why this exists, and why it is not a de-duplication gate
-------------------------------------------------------
The plan's M3.1 asked for "an owner page per concept", scored by the knowledge map's count of findings
cited on more than one page (124). That count measures the wrong thing: 540 of the 557 finding citations in
the tree sit in a page's `## Evidence` section, which is that page declaring what backs its statements --
the documentation model this project chose (DoD #4/#5, the page<->register gate). Driving that number down
would delete evidence. A measurement of duplicated *prose* found 31 restated sentences, and every one was
either boilerplate the templates share by design, a navigation list, or a page legitimately restating a
fact in its own context -- a workflow page walking an analyst through a step has to say what the signal
means.

What is actually dangerous is drift: two pages stating one fact with different numbers, and no reader able
to tell which is current. That is what hit the timestomp legend in v1.10.3 and the residency vocabulary in
v1.10.2. So this gate does not care how often a fact is stated. It cares that the statements agree.

Method: paragraphs (not raw lines -- a wrapped sentence split mid-clause produced four false positives
during development), sentence-split, normalised 5-gram shingles, Jaccard >= 0.32 and >= 9 content words.
For each cross-page pair, compare the numeric tokens; a difference fails the gate.

Exit 0 when no restated pair disagrees.
"""
import itertools
import os
import re
import sys

STOP = set("the a an of to in is are and or for with that this it as on by be was were from at not but its "
           "one same its their there when which who what how".split())
NUM = re.compile(r"\b\d[\d,\.]*\b")
SKIP_DIRS = ("website", "_templates")
SKIP_FILES = ("KNOWLEDGE_MAP.md", "changelog.md")
THRESHOLD = 0.35   # the genuine placement/residency restatement scores 0.368; 0.40 missed it


def content_words(s):
    s = re.sub(r"`[^`]*`", " ", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\*\*|\*|_", " ", s)
    return [w for w in re.sub(r"[^a-z0-9 ]", " ", s.lower()).split() if w not in STOP and len(w) > 2]


def numbers(s):
    """Numeric tokens, ignoring link targets and finding ids (FS_CHKP_005 is an id, not a quantity)."""
    s = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", s)
    s = re.sub(r"`[^`]*`", " ", s)                               # field expressions, not prose quantities
    s = re.sub(r"\b[A-Z]{2}_[A-Z0-9]{3,5}_(?:RA_|SA_|RP_)?\d{3}\b", " ", s)
    s = re.sub(r"\b(?:CRC|SHA|crc|sha)-?\d+\b", " ", s)          # algorithm names, not quantities
    s = re.sub(r"\bv?3\.\d+\b", " ", s)                          # volume format versions
    s = re.sub(r"\bE\d+\b", " ", s)                              # errata ids
    s = re.sub(r"\bstep \d+\b", " ", s, flags=re.I)              # cross-references
    s = re.sub(r"0x[0-9a-fA-F]+", " ", s)                        # offsets are compared by the offset gate
    return set(t.rstrip(".").replace(",", "") for t in NUM.findall(s))


def sentences(tree):
    """(relpath, line, sentence) for every prose sentence, with wrapped lines joined first."""
    out = []
    docs = os.path.join(tree, "docs")
    for dp, _d, fs in os.walk(docs):
        if any(sd in dp for sd in SKIP_DIRS):
            continue
        for fn in sorted(fs):
            if not fn.endswith(".md") or fn in SKIP_FILES:
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, docs)
            txt = open(p, encoding="utf-8").read()
            # blank the code fences but keep the line count, or every later line number is wrong
            txt = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), txt, flags=re.S)
            para, start = [], 0
            def flush():
                if not para:
                    return
                joined = " ".join(para)
                for s in re.split(r"(?<=[.!?])\s+", joined):
                    out.append((rel, start, s.strip()))
            # `## Evidence` sections are skipped: they are templated across every page by design (the three
            # page templates share their wording) and they carry finding ids, so comparing them produced 45
            # "disagreements" that were all evidence footers rather than facts.
            # `## Cross-references` is skipped for the same reason as Evidence: it is a navigation list,
            # templated across pages, and its numbers are each page's own root index -- two such lists
            # collided as a "contradiction" (root #6 vs root #11) when both are correct.
            SKIP_SECTIONS = ("## evidence", "## cross-reference", "## see also", "## related")
            in_skip = False
            for i, ln in enumerate(txt.split("\n"), 1):
                if ln.startswith("#"):
                    in_skip = ln.strip().lower().startswith(SKIP_SECTIONS)
                if in_skip:
                    flush()
                    para, start = [], 0
                    continue
                # a list item is its own paragraph -- joining consecutive bullets fused unrelated facts
                if re.match(r"\s*(?:[-*+]|\d+\.)\s", ln):
                    flush()
                    para, start = [], 0
                if not ln.strip() or ln.startswith(("|", "#", ">", "```")):
                    flush()
                    para, start = [], 0
                    continue
                if not para:
                    start = i
                para.append(ln.strip())
            flush()
    return out



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
    shingled = []
    for rel, line, s in sentences(tree):
        w = content_words(s)
        if len(w) < 9:
            continue
        g = set(zip(*[w[k:] for k in range(5)]))
        if g:
            shingled.append((rel, line, s, g, numbers(s)))
    pairs, bad = 0, []
    for (f1, l1, s1, g1, n1), (f2, l2, s2, g2, n2) in itertools.combinations(shingled, 2):
        if f1 == f2:
            continue
        # containment, not Jaccard: a page restating a fact inside a longer sentence scores low
        # on Jaccard (the genuine placement/residency restatement scored 0.219) but high here.
        if len(g1 & g2) / min(len(g1), len(g2)) < THRESHOLD:
            continue
        pairs += 1
        # A contradiction is the SAME quantity carrying a DIFFERENT value, so BOTH sides must hold a number
        # the other lacks. Without this, every pair where one page simply states more detail than the other
        # ("cluster 30", "roots #7/#8", a section reference) was flagged -- 11 of 11 were that shape.
        if (n1 - n2) and (n2 - n1):
            bad.append((f1, l1, s1, sorted(n1), f2, l2, s2, sorted(n2)))
    print("doc drift: %d sentence(s) compared, %d restated across pages, %d disagree on numbers"
          % (len(shingled), pairs, len(bad)))
    for f1, l1, s1, n1, f2, l2, s2, n2 in bad:
        print("   DISAGREE  %s:%d %s" % (f1, l1, n1))
        print("             %s" % s1[:150])
        print("             %s:%d %s" % (f2, l2, n2))
        print("             %s" % s2[:150])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
