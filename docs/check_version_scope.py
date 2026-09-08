#!/usr/bin/env python3
"""A page must not present a claim as holding on a format the claim was never verified on.

D12.1 split the register's single version field into `format_claimed` (what the claim is ABOUT) and
`format_verified` (what it was CHECKED on). They disagree on 69 rows. Those rows are not wrong — a claim
may legitimately be about a format nobody has imaged — but when such a row is cited on a reader page, the
page presents the wider scope as established. That is what this check counts.

What it does NOT do, deliberately: flag every mention of a version. A first attempt did, and reported 41 of
81 pages, because naming a boundary ("the ceiling applies from format 3.11") is not claiming a measurement
there, and no corpus image exists for 3.11/3.12/3.13 at all. A gate that fires on half the documentation is
one people learn to ignore.

It also refuses to judge a page whose cited findings are all `format_verified = unknown` — an empty
comparison set makes every claim look excessive. Four statements were flagged that way in testing; all four
were false.

  python3 check_version_scope.py [docs_root]     # exit 1 if the count rises above the pinned baseline
"""
import csv, glob, os, re, sys

BASELINE = 0           # page-language over-claims, measured 2026-09-08 after the D12.1 citation pass
ID = re.compile(r"\b((?:GN|FS|CT|MD|FN|AP)_[A-Z0-9]+(?:_[A-Z0-9]+)*_\d{3})\b")
DIRS = ("attributes", "structures", "concepts", "tools", "examples")
# verification language within ~60 characters of a version token, in either order
CLAIM = re.compile(r"(verified|measured|confirmed|raw-disk|disk-proven|proven)[^.\n]{0,60}?\bv?(3\.\d{1,2})\b"
                   r"|\bv?(3\.\d{1,2})\b[^.\n]{0,60}?(verified|measured|confirmed|raw-disk|disk-proven)", re.I)


def _register(root):
    for cand in (os.path.join(root, "..", "analysis", "reference_table.csv"),
                 "/workspace/refs/forclaude/reference/reference_table.csv"):
        if os.path.exists(cand):
            return list(csv.DictReader(open(cand, encoding="utf-8")))
    return None


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    reg = _register(root)
    if reg is None or "format_verified" not in reg[0]:
        print("version scope: SKIP (no register with D12.1 columns beside the docs tree)")
        return 0
    by_id = {r["ref_id"]: r for r in reg}

    judged = 0
    hits = []
    for d in DIRS:
        for p in sorted(glob.glob(os.path.join(root, d, "*.md"))):
            if os.path.basename(p) == "README.md":
                continue
            rel = os.path.relpath(p, root)
            text = open(p, encoding="utf-8", errors="replace").read()
            verified = set()
            for c in set(ID.findall(text)):
                r = by_id.get(c)
                if r and r["format_verified"] != "unknown":
                    verified |= {x for x in r["format_verified"].split(";") if x}
            if not verified:
                continue                 # nothing known to compare against: cannot judge this page
            judged += 1
            for m in CLAIM.finditer(text):
                v = m.group(2) or m.group(3)
                if v and v not in verified:
                    hits.append((rel, text[:m.start()].count("\n") + 1, v,
                                 " ".join(m.group(0).split())[:80]))

    # An informational count, NOT a pass/fail: how many over-scoped register rows are cited anywhere.
    # It rises whenever citations are added, so it measures coverage, not correctness.
    over_cited = 0
    for r in reg:
        claimed = {x for x in (r["format_claimed"] or "").split(";") if x}
        ver = {x for x in (r["format_verified"] or "").split(";") if x}
        if claimed and r["format_verified"] != "unknown" and claimed - ver:
            if any(r["ref_id"] in open(q, encoding="utf-8", errors="replace").read()
                   for d in DIRS for q in glob.glob(os.path.join(root, d, "*.md"))):
                over_cited += 1

    if judged == 0:
        print("version scope: FAIL — 0 pages could be judged; the check compared nothing")
        return 1
    print(f"version scope: {judged} page(s) judged; {len(hits)} statement(s) claim verification on a format "
          f"their cited findings were not verified on (baseline {BASELINE}); "
          f"{over_cited} over-scoped register row(s) are cited somewhere [informational]")
    for h in hits[:10]:
        print(f"    {h[0]}:{h[1]} claims {h[2]}: {h[3]!r}")
    if len(hits) > BASELINE:
        print(f"FAIL — {len(hits) - BASELINE} page statement(s) claim more than was verified")
        return 1
    print("PASS — no page claims verification on a format its findings lack")
    return 0


if __name__ == "__main__":
    sys.exit(main())
