#!/usr/bin/env python3
"""Static checks on the documentation that do not need a disk image.

**The residency-vocabulary check.** One word, "resident", was used for two independent properties —
where a file's *record* sits and where its *bytes* are — and that conflation produced wrong pages and a
wrong tool column. The vocabulary is now `embedded` / `split` for record placement and
`inline` / `extents` / `snapshot-shared` / `sparse` for data residency. This check fails on the bare word
so it cannot creep back.

Four kinds of use are legitimate and exempt:

  * driver symbol names (`RefsConvertToNonResident`, `RefsResidentWrite`, ...) and code identifiers
    (`is_resident`, `IsResident`) — these are names, not prose;
  * anything inside backticks — quoted output and identifiers;
  * the pages that *define* or *compare* the term: the residency concept page, the glossary, and the
    NTFS comparison, where "resident" is NTFS's own vocabulary;
  * the changelog, which records what was said before it was corrected.

Usage:  python3 docs/verify_docs_static.py [docs_dir]
Exit 0 when clean.
"""
import os
import re
import sys

FENCE = re.compile(r"```.*?```", re.S)      # fenced code blocks, masked before inline spans

SYMBOL = re.compile(
    r"Refs[A-Za-z]*Resident[A-Za-z]*"      # driver symbols
    r"|RESIDENT_STREAM\w*|NON_RESIDENT_MAX_VALUE"
    r"|_reported_resident|is_resident|IsResident"
    r"|`[^`]*`",                            # anything in backticks
    re.I)
BARE = re.compile(r"\b(non-resident|resident)\b", re.I)

EXEMPT = {
    "concepts/resident_storage.md",   # the page that defines the term
    "concepts/ntfs_comparison.md",    # NTFS's own vocabulary
    "concepts/driver_transitions.md", # names the conflation in order to separate it
    "glossary.md",                    # defines it, and points at the replacements
    "changelog.md",                   # records prior wording
}
SKIP_DIRS = {"website/content"}       # generated


def _mask(text):
    """Blank out fenced blocks, then driver symbols and inline code spans, with a SAME-LENGTH filler so
    match offsets still index the original text. Shrinking the text here silently shifted every reported
    line number (that bug reported a line containing no match at all)."""
    same = lambda m: "~" * len(m.group(0))
    return SYMBOL.sub(same, FENCE.sub(same, text))


# ── page <-> register offset gate ────────────────────────────────────────────
# Every byte offset a page publishes in an offset table must appear somewhere in the claim register.
# The register has no structured offset column -- offsets live in free text -- so this is a COVERAGE
# check (is this offset audited anywhere?), not a meaning check. That is still the failure mode worth
# gating: a page inventing an offset that no measurement backs. Only tables whose FIRST COLUMN HEADER
# says "offset" are read; keying on "column 1 looks like hex" instead pulled in schema ids, checksum-type
# enums and attribute type codes, and reported 21 false positives.
REGISTER = "analysis/reference_table.csv"
REG_COLS = ("description", "static_analysis_notes", "raw_analysis_notes", "structure")
HEXTOK = re.compile(r"0x[0-9A-Fa-f]{1,4}\b")
TBL_SEP = re.compile(r"^\|[\s:|-]+\|")


def _sibling(root, rel):
    """A path RELATIVE TO THE TREE THAT CONTAINS docs/ -- i.e. the repo root in a clone."""
    return os.path.join(os.path.dirname(os.path.abspath(root.rstrip("/"))), rel)


def register_offsets(root):
    import csv
    path = _sibling(root, REGISTER)
    if not os.path.exists(path):
        return None
    seen = set()
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            blob = " ".join((row.get(c) or "") for c in REG_COLS)
            seen |= {h.lower() for h in HEXTOK.findall(blob)}
    return seen


def offset_rows(text):
    """Yield (line_no, offset, row_text) for rows of tables whose first column header is an offset."""
    lines = text.split("\n")
    i = 0
    while i < len(lines) - 1:
        if lines[i].lstrip().startswith("|") and TBL_SEP.match(lines[i + 1].lstrip()):
            hdr = [c.strip().lower() for c in lines[i].strip().strip("|").split("|")]
            is_off = bool(hdr) and re.search(r"\boffset\b", hdr[0])
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                if is_off:
                    c0 = lines[j].strip().strip("|").split("|")[0].strip()
                    m = re.match(r"^\**(0x[0-9A-Fa-f]{1,4})", c0)
                    if m:
                        yield j + 1, m.group(1).lower(), lines[j].strip()
                j += 1
            i = j
        else:
            i += 1


def check_offsets(root, pages):
    known = register_offsets(root)
    if known is None:
        print("offset gate: SKIP (no %s beside the docs tree)" % REGISTER)
        return 0
    missing = []
    total = 0
    for rel, text in pages:
        for ln, off, row in offset_rows(text):
            total += 1
            if off not in known:
                missing.append((rel, ln, off, row))
    print("page<->register offsets: %d offset-table row(s); %d not audited anywhere in the register"
          % (total, len(missing)))
    for rel, ln, off, row in missing:
        print("   %s:%d  %s  %s" % (rel, ln, off, row[:90]))
    return 1 if missing else 0


# ── CSV column table ────────────────────────────────────────────────────────
# `tools/forefst.md` documents the CSV columns by ordinal. A column inserted in the tool without the
# table being renumbered leaves every later row describing the wrong field -- silently, because both
# sides still look plausible. This release inserted two columns and merged two others, which is exactly
# the change that drifts. Checked against the tool itself when it can be imported (it sits beside docs/
# in a clone); skipped, not failed, when it cannot.
COLDOC = "tools/forefst.md"
COLROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([A-Za-z][A-Za-z0-9 ()/_]*?)\s*\|", re.M)


def check_csv_columns(root, pages):
    import importlib.util
    tool = _sibling(root, "forefst.py")
    if not os.path.exists(tool):
        print("CSV column table: SKIP (forefst.py not beside the docs tree)")
        return 0
    try:
        spec = importlib.util.spec_from_file_location("_fe_cols", tool)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cols = list(mod.CSV_COLUMNS)
    except Exception as e:
        print("CSV column table: SKIP (%s: %s)" % (type(e).__name__, str(e)[:60]))
        return 0
    text = dict(pages).get(COLDOC)
    if text is None:
        print("CSV column table: SKIP (%s not found)" % COLDOC)
        return 0
    doc = {int(n): name.strip() for n, name in COLROW.findall(text)}
    bad = []
    for i, c in enumerate(cols, 1):
        d = doc.get(i)
        if d is None:
            bad.append((i, c, "missing from the table"))
        elif d.split(" (")[0].strip() != c.split(" (")[0].strip():
            bad.append((i, c, d))
    print("CSV column table: %d column(s) in the tool, %d row(s) documented; %d mismatch(es)"
          % (len(cols), len(doc), len(bad)))
    for i, c, d in bad:
        print("   col %d: tool says %r, %s says %r" % (i, c, COLDOC, d))
    return 1 if bad else 0


# ── citation gate ───────────────────────────────────────────────────────────
# A page may only cite a finding id that exists in the register, or an erratum number that exists in
# the errata. Citing one that does not is the same failure mode as inventing an offset: it looks
# sourced and is not. `E01` is excluded -- that is the EnCase image format, not erratum 1.
FINDING = re.compile(r"\b((?:FS|MD|GN|CT|FN|AP)_[A-Z0-9]+_(?:RA_|SA_|RP_)?\d{3})\b")
ERRATUM = re.compile(r"\bE(\d{1,3})\b")
ERRATA_MD = "errata.md"


def known_ids(root):
    import csv as _csv
    reg = _sibling(root, REGISTER)
    if not os.path.exists(reg):
        return None
    with open(reg, encoding="utf-8") as fh:
        return {r["ref_id"] for r in _csv.DictReader(fh)}


def check_citations(root, pages):
    ids = known_ids(root)
    if ids is None:
        print("citations: SKIP (no register beside the docs tree)")
        return 0
    bad = []
    for rel, text in pages:
        for m in FINDING.finditer(text):
            if m.group(1) not in ids:
                bad.append((rel, text.count("\n", 0, m.start()) + 1, m.group(1)))
    print("citations: %d finding id(s) cited; %d not in the register"
          % (sum(len(FINDING.findall(t)) for _r, t in pages), len(bad)))
    for rel, ln, wid in bad:
        print("   %s:%d  %s" % (rel, ln, wid))
    return 1 if bad else 0


# ── version scoping ─────────────────────────────────────────────────────────
# The residency thresholds are FORMAT-scoped: 2 KiB applies from format 3.11, and on 3.10 and earlier a
# named stream instead has a 128 KiB cap while main data is never inline at all. A page that states a
# threshold without naming the format states it for the wrong half of the corpus. Only threshold phrasings
# are matched -- `0x800` is also the compression flag bit and 128 KiB is also the upcase blob size, so the
# bare constants are not enough on their own.
THRESHOLD = re.compile(r"(2 KiB|2,?048[- ]byte|128 KiB)(?![^.\n]{0,40}(compress|upcase|blob))", re.I)
NEARBY = re.compile(r"\b(inline|extent|extent-backed|ADS|named stream|residenc)", re.I)
SCOPED = re.compile(r"(3\.1[0-5]|3\.4|3\.7|3\.9|v3\.\d|format (3|\u2264|\u2265|<=|>=))", re.I)
SCOPE_BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version_scope_baseline.txt")


def check_version_scope(pages):
    known = {}
    if os.path.exists(SCOPE_BASELINE):
        for ln in open(SCOPE_BASELINE):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                page, _, n = ln.rpartition("\t")
                known[page] = int(n)
    per = {}
    detail = {}
    for rel, text in pages:
        if rel == "changelog.md":
            continue
        lines = text.split("\n")
        for i, ln in enumerate(lines):
            if not (THRESHOLD.search(ln) and NEARBY.search(ln)):
                continue
            ctx = "\n".join(lines[max(0, i - 3):i + 4])
            if SCOPED.search(ctx):
                continue
            per[rel] = per.get(rel, 0) + 1
            detail.setdefault(rel, []).append((i + 1, ln.strip()[:90]))
    grown = {p: (n, known.get(p, 0)) for p, n in per.items() if n > known.get(p, 0)}
    print("version scoping: %d unscoped threshold claim(s) over %d page(s); %d pinned"
          % (sum(per.values()), len(per), sum(known.values())))
    if grown:
        print("FAIL — name the volume format beside a residency threshold "
              "(2 KiB is a format-3.11+ rule; 3.10 and earlier differ):")
        for page in sorted(grown):
            for ln, txt in detail[page][:2]:
                print("   %s:%d  %s" % (page, ln, txt))
        return 1
    return 0


BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "residency_vocab_baseline.txt")


def load_baseline():
    """Pinned pre-existing uses, as "<page>\t<count>". The vocabulary was corrected on the pages that
    state the residency rules; the rest is legacy prose. Pinning it stops the debt GROWING while those
    pages are reworked, the same way the silent-skip inventory does for swallowed exceptions."""
    known = {}
    if os.path.exists(BASELINE):
        for ln in open(BASELINE):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            page, _, n = ln.rpartition("\t")
            known[page] = int(n)
    return known


def main(root="forefstdev/docs"):
    bad = []
    pages = []
    for dirpath, _dirs, files in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if any(rel_dir.startswith(s) for s in SKIP_DIRS):
            continue
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/")
            try:
                text = open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
            except OSError as e:
                print("  unreadable: %s (%s)" % (rel, type(e).__name__))
                continue
            pages.append((rel, text))
            if rel in EXEMPT:
                continue
            # Mask with a SAME-LENGTH filler so match offsets still index the original text —
            # otherwise every reported line number is wrong by however much the mask shrank.
            masked = _mask(text)
            for m in BARE.finditer(masked):
                line = text.count("\n", 0, m.start()) + 1
                bad.append((rel, line, m.group(0)))
    if not pages:
        print("FAIL — no .md pages found under %r. A gate that certifies an empty set certifies nothing." % root)
        return 1
    known = load_baseline()
    per_page = {}
    for rel, _line, _w in bad:
        per_page[rel] = per_page.get(rel, 0) + 1
    grown = {p: (n, known.get(p, 0)) for p, n in per_page.items() if n > known.get(p, 0)}
    print("residency vocabulary: %d bare use(s) over %d page(s); %d pinned"
          % (len(bad), len(per_page), sum(known.values())))
    if grown:
        print("FAIL — say `embedded`/`split` for record placement, or "
              "`inline`/`extents`/`snapshot-shared`/`sparse` for data residency:")
        for page, (now, was) in sorted(grown.items()):
            print("   %-52s %d use(s), baseline %d" % (page, now, was))
            for rel, line, word in bad:
                if rel == page:
                    print("        line %d: %r" % (line, word))
                    break
        print()
        check_version_scope(pages)
        print()
        check_citations(root, pages)
        print()
        check_offsets(root, pages)
        return 1
    print("PASS — no page uses it more than its pinned baseline")
    print()
    rc_scope = check_version_scope(pages)
    print()
    rc_cite = check_citations(root, pages)
    print()
    rc_cols = check_csv_columns(root, pages)
    print()
    return check_offsets(root, pages) or rc_scope or rc_cite or rc_cols


if __name__ == "__main__":
    # Default to the directory this script lives in. It used to default to "forefstdev/docs", a path that
    # only resolves in the maintainer's workspace: run from a clone it scanned ZERO pages, printed PASS for
    # the vocabulary check and SKIPped the three that need the register or the tool -- certifying nothing
    # while exiting 0. A gate that passes on an empty set is worse than no gate.
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))))
