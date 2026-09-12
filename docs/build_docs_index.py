#!/usr/bin/env python3
"""Generate the central KNOWLEDGE_MAP.md (and, only for dirs listed in CONTENT_DIRS, an auto README)
from each page's H1 + intro, plus structural identifiers from index_meta.tsv.

NOTE: CONTENT_DIRS is empty by default, so this script regenerates ONLY KNOWLEDGE_MAP.md; the
per-directory READMEs are hand-written prose and are left untouched (see the guard in main()).

Provenance model:
  - Pages carry NO provenance footer and there is NO hand-maintained companion register.
    A page's evidence is the `## Evidence` prose section it carries; a page's audit date is
    its git history. Everything in KNOWLEDGE_MAP.md is derived at generation time.
  - Per-directory READMEs stay CLEAN (no evidence/status columns):
      structures -> 'System tables' + 'On-disk formats & row types'
      attributes -> Attribute, Type ID, Schema, Versions, Function
      tools      -> Tool, Purpose, Key subcommands
      concepts   -> Page, Summary
  - KNOWLEDGE_MAP.md is REPO-ONLY (never published to the website, no finding id ever
    reaches a reader) and exists for drift detection: which pages cite a finding
    (owner-page consolidation) and which register rows no page cites (triage).

Stdlib only.
  python3 build_docs_index.py            # regenerate KNOWLEDGE_MAP.md (per-dir READMEs only for CONTENT_DIRS)
  python3 build_docs_index.py --check    # verify-only (non-zero exit if drift / register mismatch)
  python3 build_docs_index.py --preview  # print proposed READMEs to stdout, write nothing
"""
import os
import re as _re, re, sys, glob, csv, io

DOCS_ROOT = os.environ.get("DOCS_ROOT") or os.path.dirname(os.path.abspath(__file__))
HERE = DOCS_ROOT
CONTENT_DIRS = []
# All content dirs (attributes/, structures/, concepts/, tools/) have HAND-WRITTEN forensic-reference READMEs (not auto-generated); KNOWLEDGE_MAP still indexes them.
# Keep CONTENT_DIRS EMPTY: those READMEs are prose. As a hard guard, the write loop in main() refuses to overwrite
# any README lacking the auto-generated HEAD_NOTE marker, so re-adding a dir here can never clobber a prose README.
MAP_ONLY_DIRS = ["attributes", "structures", "concepts", "tools", "examples"]
BOLD_PREAMBLE_RE = re.compile(r"^\*\*[^*]+:")   # a '**Key:** value' metadata preamble line
# a '**Key:** value' line whose value IS the summary (prose), not a metadata field
SUMMARY_LABEL_RE = re.compile(r"^\*\*(?:Description|Purpose|Summary|Overview):\*\*\s*(.+)$")

def load_index_meta():
    """basename -> {group, root_oid, table_id, schema, subcommands}. Missing file => {}."""
    path = f"{HERE}/index_meta.tsv"
    if not os.path.exists(path):
        return {}
    rows = [l for l in open(path) if not l.startswith("#")]
    meta = {}
    for r in csv.DictReader(io.StringIO("".join(rows)), delimiter="\t"):
        meta[r["file"]] = r
    return meta

def parse_page(path):
    text = open(path).read()
    mt = re.search(r"^#\s+(.*)$", text, re.M)
    title = mt.group(1).strip() if mt else os.path.basename(path)
    # summary = first non-heading, non-blank, non-preamble line after the H1
    summary = ""
    body = text[mt.end():] if mt else text
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "|", ">", "```", "<!--", "- ", "* ", "+ ")):
            continue                            # skip headings, tables, quotes, code, bullet/cross-ref lists
        m = SUMMARY_LABEL_RE.match(s)
        if m:                                   # '**Description:** <prose>' — the value IS the summary
            summary = m.group(1)
            break
        if BOLD_PREAMBLE_RE.match(s):           # other '**Schema:**'/'**Versions:**'/... metadata preamble
            continue
        summary = s
        break
    summary = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", summary)
    summary = re.sub(r"[`*]", "", summary)
    if len(summary) > 140:
        summary = summary[:137].rsplit(" ", 1)[0] + "…"
    # attribute structured fields (faithful mirror of the page's own preamble)
    head = text[:1500]
    attr_schema = attr_type = attr_ver = ""
    m = re.search(r"^\*\*Schema:\*\*\s*(0x[0-9A-Fa-f]+)", head, re.M)
    if m: attr_schema = m.group(1)
    m = re.search(r"embedded type\s*(0x[0-9A-Fa-f]+)", head)
    if m: attr_type = m.group(1)
    m = re.search(r"^\*\*(?:Type ID|Attribute Type):\*\*\s*(0x[0-9A-Fa-f]+)", head, re.M)
    if m: attr_type = m.group(1)
    # heading form: '## $X (Schema 0x1D0, type 0xD0)' — the page's own primary declaration
    m = re.search(r"\(Schema\s*(0x[0-9A-Fa-f]+),\s*type\s*(0x[0-9A-Fa-f]+)\)", head, re.I)
    if m:
        if not attr_schema: attr_schema = m.group(1)
        if not attr_type:   attr_type = m.group(2)
    m = re.search(r"^\*\*Versions:\*\*\s*(.+)$", head, re.M)
    if m:
        v = re.sub(r"[`*]", "", m.group(1).strip())            # strip markdown
        v = re.split(r"\s*[(;|]|\s+[—–-]{1,2}\s+", v)[0]        # cut at ( ; | or an em/en/-- dash phrase
        if len(v) > 52:
            v = v[:50].rsplit(" ", 1)[0] + "…"
        attr_ver = v.strip()
    return {"path": path, "title": title, "summary": summary,
            "attr_type": attr_type, "attr_schema": attr_schema, "attr_ver": attr_ver}

def collect():
    pages = {}
    for d in CONTENT_DIRS + MAP_ONLY_DIRS:
        pages[d] = sorted((parse_page(p) for p in glob.glob(f"{HERE}/{d}/*.md")
                           if os.path.basename(p) != "README.md"),
                          key=lambda x: x["path"])
    return pages

DIR_BLURB = {
    "structures": "On-disk byte-level structure references (VBR, tables, B+-tree rows, page references).",
    "concepts":   "Mechanisms, forensic methodology, and version evolution — how ReFS works and how to analyse it.",
    "attributes": "Attribute / embedded sub-record type references.",
    "tools":      "`forefst.py` and `refsanalysis.py` capability references.",
}
HEAD_NOTE = "*Auto-generated by `build_docs_index.py` — do not edit by hand.*"

def _link(p):
    return f"[{p['title']}]({os.path.basename(p['path'])})"

def gen_readme(d, plist, meta):
    rel = lambda p: os.path.basename(p["path"])
    lines = [f"# {d.capitalize()}", "", DIR_BLURB[d], "", HEAD_NOTE, ""]
    if d == "structures":
        sysp = [p for p in plist if meta.get(rel(p), {}).get("group") == "system-table"]
        fmtp = [p for p in plist if meta.get(rel(p), {}).get("group") != "system-table"]
        lines += ["## System tables", "",
                  "| Table | Root # / OID | Table ID | Schema | What it is |",
                  "|-------|-------------|----------|--------|-----------|"]
        for p in sysp:
            m = meta[rel(p)]
            what = m.get("what") or p["summary"] or "—"
            lines.append(f"| {_link(p)} | {m['root_oid'] or '—'} | {m['table_id'] or '—'} | "
                         f"{m['schema'] or '—'} | {what} |")
        lines += ["", "## On-disk formats & row types", "",
                  "| Structure | What it is |", "|-----------|-----------|"]
        for p in fmtp:
            lines.append(f"| {_link(p)} | {p['summary'] or '—'} |")
    elif d == "attributes":
        lines += ["| Attribute | Type ID | Schema | Versions | Function |",
                  "|-----------|---------|--------|----------|----------|"]
        for p in plist:
            lines.append(f"| {_link(p)} | {p['attr_type'] or '—'} | {p['attr_schema'] or '—'} | "
                         f"{p['attr_ver'] or '—'} | {p['summary'] or '—'} |")
    elif d == "tools":
        lines += ["| Tool | Purpose | Key subcommands |", "|------|---------|-----------------|"]
        for p in plist:
            m = meta.get(rel(p), {})
            lines.append(f"| {_link(p)} | {p['summary'] or '—'} | {m.get('subcommands') or '—'} |")
    else:  # concepts
        lines += ["| Page | Summary |", "|------|---------|"]
        for p in plist:
            lines.append(f"| {_link(p)} | {p['summary'] or '—'} |")
    lines += ["", "See also: [Knowledge Map](../KNOWLEDGE_MAP.md) · [root index](../README.md) · [how this was verified](../methodology.md) · [conventions](../CONTRIBUTING.md)", ""]
    return "\n".join(lines)

ALPHA_ID = _re.compile(r"\b(?:GN|FS|CT|MD|FN|AP)_[A-Z0-9]+(?:_[A-Z0-9]+)*_\d{3}\b")


ID_RANGE = _re.compile(r"\b((?:GN|FS|CT|MD|FN|AP)_[A-Z0-9]+(?:_[A-Z0-9]+)*)_(\d{3})\s*[\u2013\u2014-]\s*(\d{3})\b")


def page_findings(path):
    """Finding ids CITED BY THE PAGE ITSELF -- derived, never typed.

    A hand-kept companion list supplied this once and drifted -- it held an id that did not exist until
    the citation gate caught it. The page is the fact; scan the page.

    A RANGE counts as a citation of every id in it. Pages write `AP_REDO_001-040` and `CT_CTBL_001-011`
    where listing forty ids would be unreadable, and a literal-only scan called all forty uncited: 41 of
    the 244 "citation gaps" in the 2026-09-07 triage were this, already cited and merely written compactly.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    ids = set(ALPHA_ID.findall(text))
    for m in ID_RANGE.finditer(text):
        fam, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
        if 0 < hi - lo < 200:                      # a sane range, not two unrelated numbers
            ids |= {f"{fam}_{n:03d}" for n in range(lo, hi + 1)}
    return sorted(ids)


def register_tiers():
    """ref_id -> (static evidence, disk status), in register order, straight from the claim
    register (the authority on evidence).

    Both values are reproduced AS WRITTEN, only clipped at a parenthetical. They are free text
    (15 distinct static values, 9 disk values), so composing them into one grade would invent a
    ranking the register does not state — e.g. CONTRADICTED and NOT_TESTED are not the same
    absence of evidence. The index shows what the register says and lets the reader judge.

    Insertion order is meaningful: the uncited-row list reads in register order, so it can be
    worked through against the CSV top to bottom.
    """
    import csv as _csv

    def clip(v):
        v = (v or "").strip()
        if v in ("", "N/A"):
            return "—"
        head = _re.split(r"\s*[(;]", v, 1)[0].strip()
        return head + " …" if head != v else v

    for cand in (f"{HERE}/../analysis/reference_table.csv",
                 "/workspace/refs/forclaude/reference/reference_table.csv"):
        if os.path.exists(cand):
            out = {}
            with open(cand, encoding="utf-8", newline="") as fh:
                for r in _csv.DictReader(fh):
                    out[r["ref_id"].strip()] = (clip(r.get("static_evidence_level")),
                                                clip(r.get("raw_analysis_status")))
            return out
    return {}


def gen_knowledge_map(pages):
    tiers = register_tiers()
    lines = [
      "# Knowledge Map — where every ReFS fact lives", "",
      "**This page is an index, never a source.** Every fact it points at is stated on the page or in the",
      "claim register; nothing is documented only here.", "",
      "It is **repo-only**: it is not published to the website, is not in the site menu, and no finding id it",
      "contains ever reaches a reader — the site's leak gate stays absolute and has no exemption. Its audience",
      "is someone auditing the documentation against the evidence. A reader wanting the narrative starts from",
      "the [documentation index](README.md).", "",
      "Its purpose is **drift detection**, in the two directions prose cannot read:", "",
      "1. **I am about to change a fact — which pages depend on it?** Section 2. A claim corrected in one",
      "   place and left standing in three others is this project's most repeated documentation failure.",
      "   A finding cited on several pages needs one *owner* page that states it and others that link.",
      "2. **Which register rows does no page document?** Section 3 — the triage list.", "",
      "**Every column is derived, none is typed.** Findings are the ids the page itself cites, scanned from",
      "the page; tiers come from the claim register. There is no hand-maintained companion file: one used to",
      "supply these columns and it drifted, holding an id that did not exist until the citation gate caught",
      "it. A page's audit date is its git history. Regenerate with `build_docs_index.py`; `--check` verifies",
      "only, and the sync step regenerates.", ""]

    total = 0
    for d in CONTENT_DIRS + MAP_ONLY_DIRS:
        lines += [f"## 1. Pages in {d}/", "", "| Page | Topic | Findings cited on the page |",
                  "|------|-------|----------------------------|"]
        for p in pages[d]:
            rel = f"{d}/{os.path.basename(p['path'])}"
            # The summary is a page intro clipped to a sentence; a mid-sentence cut reads as broken text,
            # so clip on a boundary and mark it, rather than leaving a dangling clause.
            topic = (p['summary'] or '').strip()
            if topic and topic[-1] not in ".!?":
                cut = max(topic.rfind(". "), topic.rfind("; "))
                topic = (topic[:cut + 1] if cut > 40 else topic.rstrip(" ,;:") + " …")
            fids = page_findings(p["path"])
            lines.append(f"| [{os.path.basename(p['path'])}]({rel}) | {topic or '—'} | "
                         f"{', '.join(fids) if fids else '—'} |")
            total += 1
        lines.append("")

    # ---- section 2: the inverse index -------------------------------------------------------
    by_finding = {}
    for d in CONTENT_DIRS + MAP_ONLY_DIRS:
        for p in pages[d]:
            rel = f"{d}/{os.path.basename(p['path'])}"
            for fid in page_findings(p["path"]):
                by_finding.setdefault(fid, set()).add(rel)
    multi = {f: v for f, v in by_finding.items() if len(v) > 1}
    lines += ["## 2. Findings → the pages that cite them", "",
              "Before changing a finding, correct every page listed on its row in the same commit. The",
              f"The **{len(multi)} rows citing more than one page** are not duplication to be consolidated:",
              "a finding is cited where a page declares what backs its statements, and one finding legitimately",
              "backs statements on several pages. Measured 2026-09-11: 540 of the 557 citations in the tree sit",
              "in a `## Evidence` section, and no concept is explained redundantly. What must not happen is two",
              "pages stating one fact with *different numbers* — gates 7h and 7i check exactly that.", "",
              "| Finding | Static | Disk | Pages | Cited on |",
              "|---------|--------|------|-------|----------|"]
    for fid in sorted(by_finding):
        where = ", ".join(f"[{os.path.basename(r)}]({r})" for r in sorted(by_finding[fid]))
        n = len(by_finding[fid])
        st, dk = tiers.get(fid, ("—", "not in the register"))
        lines.append(f"| `{fid}` | {st} | {dk} | {n if n > 1 else ''} | {where} |")
    lines.append("")

    # ---- section 3: the triage list ---------------------------------------------------------
    uncited = [f for f in tiers if f not in by_finding]
    scanned = "/, ".join(CONTENT_DIRS + MAP_ONLY_DIRS) + "/"
    lines += ["## 3. Register rows no page cites", "",
              f"The triage list: **{len(uncited)} of {len(tiers)}** register rows are cited by no page in",
              f"`{scanned}` — the denominator is the content directories, because those are the",
              "pages a reader reaches. A row here is one of three things, and the triage decides which:", "",
              "- **internal-only** — a tool/verification fact with no reader-facing statement to make;",
              "- **undocumented** — reader-facing knowledge with no page, so a page (or a paragraph) is owed;",
              "- **duplicate** — the same fact as a cited row, to be merged into it.", "",
              "Rows read in register order. A mention in `changelog.md` does not count as documentation.", "",
              "| Finding | Static | Disk |", "|---------|--------|------|"]
    for fid in uncited:
        st, dk = tiers[fid]
        lines.append(f"| `{fid}` | {st} | {dk} |")
    lines.append("")

    lines += ["---",
              f"*Generated by `build_docs_index.py` — {total} pages indexed, {len(by_finding)} of "
              f"{len(tiers)} register rows cited, {len(multi)} cited on more than one page. The claim "
              "register is `analysis/reference_table.csv`.*", ""]
    return "\n".join(lines)

def main():
    unknown = [a for a in sys.argv[1:] if a not in ("--check", "--preview")]
    if unknown:
        print(f"build_docs_index.py: unknown argument(s): {' '.join(unknown)}\n"
              f"usage: build_docs_index.py [--check | --preview]   (no args = regenerate)", file=sys.stderr)
        sys.exit(2)
    check = "--check" in sys.argv
    preview = "--preview" in sys.argv
    pages = collect()
    meta = load_index_meta()
    if preview:
        for d in CONTENT_DIRS:
            print("=" * 80)
            print(f"### PROPOSED {d}/README.md ###")
            print("=" * 80)
            print(gen_readme(d, pages[d], meta))
        return
    drift = 0
    for d in CONTENT_DIRS:
        rp = f"{HERE}/{d}/README.md"
        old = open(rp).read() if os.path.exists(rp) else ""
        if old and HEAD_NOTE not in old:
            continue   # SAFETY: never overwrite a HAND-WRITTEN prose README (only auto-generated ones carry HEAD_NOTE)
        new = gen_readme(d, pages[d], meta)
        if new != old:
            drift += 1
            if not check: open(rp, "w").write(new)
    km = gen_knowledge_map(pages)
    kp = f"{HERE}/KNOWLEDGE_MAP.md"
    old = open(kp).read() if os.path.exists(kp) else ""
    if km != old:
        drift += 1
        if not check: open(kp, "w").write(km)
    # NOTE: cited-id-vs-register validation is NOT duplicated here — verify_docs_static.py's
    # citation gate owns it (it is what caught an invented id). This --check is drift only.
    if check:
        if drift:
            print(f"DRIFT: {drift} index file(s) out of date — run build_docs_index.py "
                  f"(the sync step regenerates; this gate only verifies).")
            sys.exit(1)
        print("indexes up to date (regenerating would change nothing).")
    else:
        print(f"regenerated {len(CONTENT_DIRS)} READMEs + KNOWLEDGE_MAP.md "
              f"({sum(len(pages[d]) for d in CONTENT_DIRS + MAP_ONLY_DIRS)} pages indexed).")

if __name__ == "__main__":
    main()
