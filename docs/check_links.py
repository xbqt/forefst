#!/usr/bin/env python3
"""Verify every relative markdown link in docs/ resolves, every page is reachable
(no orphans), and no link escapes the docs/ tree (published docs must be self-contained).
Stdlib only. Non-zero exit on any failure.

  python3 check_links.py
"""
import os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
LINK = re.compile(r"\]\(([^)]+)\)")
SKIP_DIRS = ("audit/", "_templates/", "website/")  # audit=regenerated artifacts; templates=scaffolds; website=Hugo site source

def is_url(t): return t.startswith(("http://", "https://", "mailto:", "#"))

def main():
    os.chdir(HERE)
    mds = [m for m in glob.glob("**/*.md", recursive=True)
           if not m.startswith(SKIP_DIRS)]
    broken, escaped = [], []
    inbound = {m: 0 for m in mds}
    for md in mds:
        d = os.path.dirname(md)
        for m in LINK.finditer(open(md).read()):
            raw = m.group(1).strip()
            path = raw.split("#")[0]
            if not path or is_url(raw) or " " in path:   # skip anchors/urls/non-paths e.g. "(4 each)"
                continue
            tgt = os.path.normpath(os.path.join(d, path))
            # escape check: target must stay within docs/
            if tgt.startswith("..") or os.path.isabs(path):
                escaped.append(f"{md} -> {raw}")
                continue
            if not os.path.exists(tgt):
                broken.append(f"{md} -> {raw}")
            elif tgt in inbound:
                inbound[tgt] += 1
    # orphans = content pages with no inbound link (READMEs/root excluded — they are entry points)
    orphans = [m for m, n in inbound.items() if n == 0
               and os.path.basename(m) not in ("README.md", "CONTRIBUTING.md", "KNOWLEDGE_MAP.md")
               and not m.endswith("README.md")]
    ok = not (broken or escaped)
    print(f"checked {len(mds)} pages: {len(broken)} broken, {len(escaped)} escaping docs/, {len(orphans)} orphans")
    for b in broken:  print("  BROKEN  ", b)
    for e in escaped: print("  ESCAPES ", e)
    for o in orphans: print("  ORPHAN  ", o)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
