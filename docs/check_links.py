#!/usr/bin/env python3
"""Verify every relative markdown link in docs/ resolves, every page is reachable
(no orphans), and no link escapes the docs/ tree (published docs must be self-contained).
A link's anchor (`page.md#id`, or `#id` on the same page) must be the id of a heading of that
page, formed as GitHub and the site's Markdown renderer form it (`heading_ids`).
Stdlib only. Non-zero exit on any failure.

  python3 check_links.py
  python3 check_links.py --self-test
"""
import os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
LINK = re.compile(r"\]\(([^)]+)\)")
SKIP_DIRS = ("audit/", "_templates/", "website/")  # audit=regenerated artifacts; templates=scaffolds; website=Hugo site source

def is_url(t): return t.startswith(("http://", "https://", "mailto:"))

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")


def heading_ids(text):
    """The ids of a page's headings (E14, 1.14.0): the heading's text as rendered -- a link's text kept, its target
    and any HTML tag dropped -- lower-cased, every character that is not a letter, a digit, a space, `-` or `_`
    dropped, each space a `-`; a repeated id gets `-1`, `-2` ... Headings inside a code fence are not headings."""
    ids, seen, fence = set(), {}, False
    for line in text.splitlines():
        if FENCE.match(line):
            fence = not fence
            continue
        m = None if fence else HEADING.match(line)
        if not m:
            continue
        t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", m.group(1))
        t = re.sub(r"<[^>]+>", "", t).strip().lower()
        base = "".join(c for c in t if c.isalnum() or c in " -_").replace(" ", "-")
        n = seen.get(base, 0)
        seen[base] = n + 1
        ids.add(base if n == 0 else "%s-%d" % (base, n))
    return ids

def main():
    os.chdir(HERE)
    mds = [m for m in glob.glob("**/*.md", recursive=True)
           if not m.startswith(SKIP_DIRS)]
    broken, escaped, anchors = [], [], []
    inbound = {m: 0 for m in mds}
    ids = {}
    def _ids(p):
        if p not in ids:
            ids[p] = heading_ids(open(p, encoding="utf-8").read())
        return ids[p]
    for md in mds:
        d = os.path.dirname(md)
        text = open(md, encoding="utf-8").read()
        # a link inside a code fence or an inline code span is shown, not followed
        body = re.sub(r"`[^`\n]*`", "", "\n".join("" if f else l for l, f in _fenced(text)))
        for m in LINK.finditer(body):
            raw = m.group(1).strip()
            path, _, frag = raw.partition("#")
            if is_url(raw) or " " in path:   # urls and non-paths e.g. "(4 each)"
                continue
            if not path:
                if frag and frag not in _ids(md):
                    anchors.append(f"{md} -> {raw}")
                elif not frag:
                    # N119 (1.14.0): `[x](#)` links nowhere -- a placeholder left in a page (three were in the glossary)
                    anchors.append(f"{md} -> # (an empty anchor: links nowhere)")
                continue
            tgt = os.path.normpath(os.path.join(d, path))
            # escape check: target must stay within docs/
            if tgt.startswith("..") or os.path.isabs(path):
                escaped.append(f"{md} -> {raw}")
                continue
            if not os.path.exists(tgt):
                broken.append(f"{md} -> {raw}")
                continue
            if tgt in inbound:
                inbound[tgt] += 1
            if frag and tgt.endswith(".md") and frag not in _ids(tgt):
                anchors.append(f"{md} -> {raw}")
    # orphans = content pages with no inbound link (READMEs/root excluded — they are entry points)
    orphans = [m for m, n in inbound.items() if n == 0
               and os.path.basename(m) not in ("README.md", "CONTRIBUTING.md", "KNOWLEDGE_MAP.md")
               and not m.endswith("README.md")]
    ok = not (broken or escaped or anchors)
    print(f"checked {len(mds)} pages: {len(broken)} broken, {len(anchors)} dead anchors, {len(escaped)} escaping docs/, "
          f"{len(orphans)} orphans")
    for b in broken:  print("  BROKEN  ", b)
    for a in anchors: print("  ANCHOR  ", a)
    for e in escaped: print("  ESCAPES ", e)
    for o in orphans: print("  ORPHAN  ", o)
    sys.exit(0 if ok else 1)

def _fenced(text):
    """(line, inside a code fence) for each line."""
    out, fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            fence = not fence
            out.append((line, True))
            continue
        out.append((line, fence))
    return out


def self_test():
    """E14's RED: a dead same-page anchor and a dead cross-page anchor fail; live ones (a heading with a link and
    inline code, a repeated heading) pass."""
    import tempfile, subprocess, shutil
    d = tempfile.mkdtemp(prefix="check_links_")
    try:
        shutil.copy(os.path.abspath(__file__), os.path.join(d, "check_links.py"))
        open(os.path.join(d, "README.md"), "w").write("[a](a.md) [b](b.md)\n")
        open(os.path.join(d, "b.md"), "w").write("# B\n\n## `deleted` — the view ([list](a.md) + more)\n\n## New\n\n## New\n")
        def run(a_text):
            open(os.path.join(d, "a.md"), "w").write(a_text)
            return subprocess.run([sys.executable, os.path.join(d, "check_links.py")], capture_output=True,
                                  text=True).returncode
        live = run("# A\n\n## Here\n\n[x](#here) [y](b.md#deleted--the-view-list--more) [z](b.md#new-1)\n")
        dead_same = run("# A\n\n[x](#gone)\n")
        dead_cross = run("# A\n\n[y](b.md#new-2)\n")
        in_code = run("# A\n\n`[x](#gone)`\n\n```\n[y](#gone)\n```\n")
        empty = run("# A\n\n[x](#)\n")                     # N119: a link to a bare '#'
    finally:
        shutil.rmtree(d)
    ok = live == 0 and dead_same == 1 and dead_cross == 1 and in_code == 0 and empty == 1
    print("check_links self-test: %s (live anchors %d, dead same-page %d, dead cross-page %d, links in code %d, "
          "empty anchor %d)" % ("PASS" if ok else "FAIL", live, dead_same, dead_cross, in_code, empty))
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    main()
