#!/usr/bin/env python3
"""Generate the per-directory README indexes and the central KNOWLEDGE_MAP.md
from each page's H1 + intro, plus structural identifiers from index_meta.tsv.

Provenance model:
  - Pages carry NO provenance footer. Verification status, evidence grades, and finding
    IDs live centrally in `audit_dates.tsv` (the audit register); pages keep only a body
    `## Evidence` prose section.
  - Per-directory READMEs stay CLEAN (no evidence/status columns):
      structures -> 'System tables' + 'On-disk formats & row types'
      attributes -> Attribute, Type ID, Schema, Versions, Function
      tools      -> Tool, Purpose, Key subcommands
      concepts   -> Page, Summary
  - KNOWLEDGE_MAP.md keeps the provenance columns (Master / Findings / Evidence / Status),
    now sourced from `audit_dates.tsv` — it is the where-every-fact-lives index.

Stdlib only.
  python3 build_docs_index.py            # regenerate READMEs + KNOWLEDGE_MAP.md
  python3 build_docs_index.py --check    # verify-only (non-zero exit if drift / register mismatch)
  python3 build_docs_index.py --preview  # print proposed READMEs to stdout, write nothing
"""
import os, re, sys, glob, csv, io

DOCS_ROOT = os.environ.get("DOCS_ROOT") or os.path.dirname(os.path.abspath(__file__))
HERE = DOCS_ROOT
CONTENT_DIRS = []
# All content dirs (attributes/, structures/, concepts/, tools/) have hand-written forensic-reference READMEs (not auto-generated); KNOWLEDGE_MAP still indexes them.
MAP_ONLY_DIRS = ["attributes", "structures", "concepts", "tools", "examples"]
BOLD_PREAMBLE_RE = re.compile(r"^\*\*[^*]+:")   # a '**Key:** value' metadata preamble line
# a '**Key:** value' line whose value IS the summary (prose), not a metadata field
SUMMARY_LABEL_RE = re.compile(r"^\*\*(?:Description|Purpose|Summary|Overview):\*\*\s*(.+)$")

AUDIT_REGISTER = f"{HERE}/audit_dates.tsv"

def audit_register():
    """page -> {status, evidence, findings, last_audited, note} from the central register
    (excludes comment/header lines). This is where the per-page provenance now lives."""
    reg = {}
    if not os.path.exists(AUDIT_REGISTER):
        return reg
    for ln in open(AUDIT_REGISTER, encoding="utf-8"):
        if ln.startswith("#") or ln.startswith("page\t") or not ln.strip():
            continue
        p = ln.rstrip("\n").split("\t")
        p += [""] * (6 - len(p))
        reg[p[0]] = {"status": p[1], "evidence": p[2], "findings": p[3],
                     "last_audited": p[4], "note": p[5]}
    return reg

def tracked_pages():
    """every docs/*.md whose provenance is tracked in the register — i.e. all pages except
    the _templates/ scaffolding and the auto-generated KNOWLEDGE_MAP.md."""
    out = set()
    for p in glob.glob(f"{HERE}/**/*.md", recursive=True):
        rel = os.path.relpath(p, HERE)
        if (rel.startswith("_templates/") or rel.startswith("website/")
                or os.path.basename(p) == "KNOWLEDGE_MAP.md"):
            continue                            # website/ = the Hugo site source, not a doc page
        out.add(rel)
    return out

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

def gen_knowledge_map(pages, reg):
    lines = ["# Knowledge Map — where every ReFS fact lives", "",
             "The single index from a topic/page to its authoritative sources: the master reference section",
             "(`structure_reference.md`, the byte-level source of truth), the finding/erratum ids, and the evidence level.",
             "**Auto-generated** by `build_docs_index.py` from each page's intro + the central `audit_dates.tsv` register — regenerate after edits.", "",
             "When a fact changes, this map shows every page that documents it (the cross-doc-drift defence).", ""]
    total = 0
    for d in CONTENT_DIRS + MAP_ONLY_DIRS:
        lines += [f"## {d}/", "", "| Page | Topic | Master § | Findings | Evidence | Status |",
                  "|------|-------|----------|----------|----------|--------|"]
        for p in pages[d]:
            rel = f"{d}/{os.path.basename(p['path'])}"
            r = reg.get(rel, {})
            lines.append(f"| [{os.path.basename(p['path'])}]({rel}) | {p['summary'] or '—'} | "
                         f"{r.get('master') or '—'} | {r.get('findings') or '—'} | "
                         f"{r.get('evidence') or '—'} | {r.get('status') or '—'} |")
            total += 1
        lines.append("")
    lines += ["---",
              f"*{total} pages indexed. Provenance (status · evidence · findings · date): `audit_dates.tsv`. "
              "Claim register: `analysis/reference_table.csv` (repo root). Per-claim proof harness: `analysis/reports/audit/`.*", ""]
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
    reg = audit_register()
    if preview:
        for d in CONTENT_DIRS:
            print("=" * 80)
            print(f"### PROPOSED {d}/README.md ###")
            print("=" * 80)
            print(gen_readme(d, pages[d], meta))
        return
    drift = 0
    for d in CONTENT_DIRS:
        new = gen_readme(d, pages[d], meta)
        rp = f"{HERE}/{d}/README.md"
        old = open(rp).read() if os.path.exists(rp) else ""
        if new != old:
            drift += 1
            if not check: open(rp, "w").write(new)
    km = gen_knowledge_map(pages, reg)
    kp = f"{HERE}/KNOWLEDGE_MAP.md"
    old = open(kp).read() if os.path.exists(kp) else ""
    if km != old:
        drift += 1
        if not check: open(kp, "w").write(km)
    tp = tracked_pages()
    missing = sorted(tp - set(reg))     # tracked page absent from the register
    orphan  = sorted(set(reg) - tp)     # register row with no matching page on disk
    if missing:
        print("PAGES MISSING FROM audit_dates.tsv:", *missing, sep="\n  ")
    if orphan:
        print("audit_dates.tsv ROWS WITH NO MATCHING PAGE:", *orphan, sep="\n  ")
    if check:
        if drift or missing or orphan:
            print(f"DRIFT: {drift} index file(s) out of date; {len(missing)} page(s) missing from the "
                  f"register; {len(orphan)} orphan register row(s).")
            sys.exit(1)
        print("indexes up to date; every page is in the audit register.")
    else:
        print(f"regenerated {len(CONTENT_DIRS)} READMEs + KNOWLEDGE_MAP.md "
              f"({sum(len(pages[d]) for d in CONTENT_DIRS + MAP_ONLY_DIRS)} pages indexed).")

if __name__ == "__main__":
    main()
