#!/usr/bin/env python3
"""
verify_site.py — regression gate for the generated Hugo `content/` tree.

Run after build.py. It compares every generated page against its source doc and FAILS (exit 1)
on any build-introduced prose artifact or reader-facing provenance leak. The de-jargon transform in
build.py must remove provenance WITHOUT damaging prose; this script is the contract that proves it.

Checked classes (each a historical failure mode — see analysis/reports/_runlogs/website_robustness_audit_2026-06-26.md):
  LEAK            finding-IDs / evidence grades / master§ / errata E-NN / #NNN / $CBW4 reaching the reader site
  DANGLE          a provenance removal left a dead predicate ("... is.", "behaviours are and.", "Findings:")
  PUNCT           stray punctuation from a removal ("..", ",.", " .", "—.", "()", "( ;")
  LOSTPAREN       a function call lost its "()" inside inline code (bootstrap() -> bootstrap)
  EMDASH          a clause-final em-dash was dropped, fusing two clauses into a run-on
  NOSPACE         a removal ate a real space ("word(", "**(", a raw "(file.md)" glued to a word)
  LINK            an internal .md link resolves to no published page, or points at an unpublished page

Usage:  python3 verify_site.py            # gate (exit 1 on any failure)
        python3 verify_site.py --report   # list every hit, still exits 1 on failure
        python3 verify_site.py --calibrate # self-test: plant finding-id leaks (prose / `inline code` /
                                           # ``` fence) and prove the LEAK check FIRES on each
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "content")
# N116 (1.14.0): the docs folder this site is built from -- website/'s parent, in the dev and the published tree alike;
# the default was website/../forefst/docs, which exists in neither, so every rule that compares a generated page with
# its source compared with nothing (measured 2026-11-20: pointed at the real sources, the 88 pages still pass)
DOCS = os.environ.get("REFS_DOCS", os.path.join(HERE, ".."))

# generated page -> source page  (mirrors build.py's layout)
def pairs():
    out = []
    for sec in ("concepts", "structures", "attributes", "tools"):
        d = os.path.join(CONTENT, sec)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".md") and fn != "_index.md":
                src = os.path.join(DOCS, sec, fn)
                if sec == "tools" and not os.path.isfile(src) and os.path.isfile(os.path.join(DOCS, "examples", fn)):
                    src = os.path.join(DOCS, "examples", fn)     # build.py publishes the examples as pages of tools/
                out.append((os.path.join(d, fn), src))
    gl = os.path.join(CONTENT, "glossary.md")
    if os.path.isfile(gl):
        out.append((gl, os.path.join(DOCS, "glossary.md")))
    # N223 (1.14.0): the three site-only pages build.py copies as they are (home, about, methodology) were in no pair,
    # so no rule -- the LEAK check included -- read them
    for gen_name, src_name in (("_index.md", "home.md"), ("about.md", "about.md"),
                               (os.path.join("verification", "_index.md"), "verification.md")):
        g = os.path.join(CONTENT, gen_name)
        if os.path.isfile(g):
            out.append((g, os.path.join(HERE, "pages", src_name)))
    # RC3a: the Methodology section's sub-pages (docs/methodology/*.md, published under content/verification/)
    vd = os.path.join(CONTENT, "verification")
    if os.path.isdir(vd):
        for fn in sorted(os.listdir(vd)):
            if fn.endswith(".md") and fn != "_index.md":
                out.append((os.path.join(vd, fn), os.path.join(DOCS, "methodology", fn)))
    return out

# Published page basenames (for link resolution) and the never-published set (build.py UNPUBLISHED+EXCLUDE).
def published_basenames():
    s = set()
    for dp, _, fns in os.walk(CONTENT):
        for fn in fns:
            if fn.endswith(".md"):
                s.add(fn.lower())
    return s

_METHOD_ALLOWED = ("master reference", "evidence-level jargon", "finding-ID jargon")
UNPUB = {"readme.md", "knowledge_map.md", "contributing.md", "changelog.md",
         "test_baseline_images.md", "methodology.md", "cbw4.md"}

ALPHA_ID = re.compile(r'\b(?:GN|FS|CT|MD|FN|AP)_[A-Z0-9]+(?:_[A-Z0-9]+)*_\d{3}\b')
GRADE = re.compile(r'\bE[1-4](?:\+(?:E[1-4]|RD))*\b')
LINK = re.compile(r'(?<!\!)\[([^\]]+)\]\(([^)]+)\)')


def split_code(t):
    """Prose with code masked. Masks BOTH ``` fences (dropped) AND `inline code` (replaced by a
    word-placeholder so removing it never fabricates 'space before punctuation' artifacts)."""
    parts = t.split("```")
    prose = []
    for i in range(0, len(parts), 2):
        prose.append(re.sub(r"`[^`]*`", "CODE", parts[i]))
    return "\n".join(prose)


def check_page(gen_path, src_path, pub, gen=None, src=None):
    base = os.path.basename(gen_path)
    rel = os.path.relpath(gen_path, CONTENT)
    is_about_or_gloss = base in ("about.md", "glossary.md")
    # N223 (1.14.0): the Methodology page (content/verification.md) explains the evidence model, so the words of that
    # model are its subject, not jargon leaking into a reference page; ids, erratum numbers and #NNN stay forbidden there
    is_method = os.path.dirname(gen_path) == os.path.join(CONTENT, "verification")    # the Methodology section
    if gen is None:
        gen = open(gen_path, encoding="utf-8").read()
    if src is None:
        src = open(src_path, encoding="utf-8").read() if os.path.isfile(src_path) else ""
    prose = split_code(gen)
    hits = []

    def H(cls, msg):
        hits.append((cls, rel, msg))

    # ---- LEAK ----
    # A finding-ID must not reach the reader even inside `inline code` or a ``` fence (it renders
    # verbatim), so scan the RAW generated text — NOT the code-masked prose. ALPHA_ID is a specific
    # finding-id shape (fixed prefixes + _NNN); no legitimate code token matches it, so raw scanning
    # is false-positive-free. (The masked-prose scans below stay for grade/RD/§, which CAN appear
    # legitimately inside code and must not false-positive.) Mirrors the raw repo-filename scan below.
    for m in ALPHA_ID.finditer(gen):
        H("LEAK", f"finding-ID {m.group(0)!r}")
    if not is_about_or_gloss:
        for m in GRADE.finditer(prose):
            H("LEAK", f"evidence grade {m.group(0)!r}")
        for m in re.finditer(r'\(\s*RD\b[^)]*\)|\bRD-(?:verified|confirmed|proven|observed)\b', prose):
            H("LEAK", f"RD token {m.group(0)[:24]!r}")
    for pat, lbl in [(r'(?<![A-Za-z])§[A-Z][\w.]*', 'master §'),
                     (r'\b[Mm]aster\s+§', 'master §'),
                     (r"\bthe master's\b", "the master's (register ref)"),
                     (r'\bmaster reference\b', 'master reference'),
                     (r'\bmaster thesis\b', 'master thesis'),
                     (r'\bfindings register\b', 'findings register'),
                     (r'\berrata\s+E-?\d{2,}\b', 'errata'),
                     (r'\bErratum\s+E-?\d+\b', 'erratum'),
                     (r'\bE-\d{2,}\b', 'errata E-NN'),
                     # a BARE errata id, E10–E999 no leading zero (catches the "(FN_LINK_003 / E59)" ->
                     # "(/ E59)" half-strip). Excludes E01–E09 (EnCase image format) and single-digit grades.
                     (r'\bE[1-9]\d\d?\b', 'errata E-NN (bare)'),
                     (r'\$CBW4|\bCBW4\b', '$CBW4 back-reference'),
                     (r'\bGrades are E1\b', 'grade legend'),
                     (r'\bevidence levels?\b', 'evidence-level jargon'),
                     (r'\bfinding[- ]?IDs?\b', 'finding-ID jargon'),
                     (r'\baudited (?:claim|structure)\b', 'audited-claim jargon'),
                     (r'(?<![\w.])§?(?:sub)?[Tt]able\s+[A-J]\.\d+[a-z]?\b', 'appendix subtable ref'),
                     (r'(?<![\w.,])[A-J]\.\d+[a-z]\b', 'bare appendix ref'),
                     (r'(?m)^\s*Findings?:\s', 'Findings: lead-in'),
                     (r'\bopen question [A-Z]\d\b', 'open-question code')]:
        if is_method and lbl in _METHOD_ALLOWED:
            continue
        for m in re.finditer(pat, prose):
            H("LEAK", f"{lbl}: {m.group(0)[:30]!r}")
    # repo-internal filenames must not appear even inside inline code (they render to the reader)
    for m in re.finditer(r'\b(?:structure_reference|reference_table|findings_register|open_questions)\b', gen):
        if is_method:
            continue                          # N223: the Methodology page links the register by its file name
        H("LEAK", f"repo filename in output: {m.group(0)!r}")

    # ---- DANGLE ----  dead predicate left by a removal
    for m in re.finditer(r'\b(is|are)\.\s+(See|The|Findings|It|These|This|A\b)', prose):
        H("DANGLE", f"dead predicate {m.group(0)[:24]!r}")
    for m in re.finditer(r'\bare and\.', prose):
        H("DANGLE", "'are and.'")
    for m in re.finditer(r'\b(is|are)\s+finding[s]?\b', prose):
        H("DANGLE", f"'{m.group(0)}' (un-removed finding scaffold)")
    for m in re.finditer(r'\b(is|are)\.\s*$', prose, re.M):
        H("DANGLE", "line ends with bare 'is.'/'are.'")

    # ---- PUNCT ----  (prose only; allow numeric ranges like 3..511, 0x00..0x1B)
    for m in re.finditer(r'(?<![.\d])[A-Za-z)],?\s*\.\.(?!\.)(?!\d)', prose):
        H("PUNCT", f"double period {m.group(0)[-6:]!r}")
    for m in re.finditer(r'[A-Za-z],\.', prose):
        H("PUNCT", f"comma-period {m.group(0)!r}")
    for m in re.finditer(r'—\s*[.;,]', prose):
        H("PUNCT", "em-dash then punctuation")
    for m in re.finditer(r'\(\s*\)|\(\s*[;,]|[;,]\s*\)', prose):
        H("PUNCT", f"broken paren {m.group(0)!r}")
    # space-before-punctuation, but NOT in table rows (alignment spacing) and not after CODE placeholder edges
    for line in prose.split("\n"):
        if "|" in line:
            continue
        for m in re.finditer(r'[A-Za-z0-9)*`] ([.,;])(?:\s|$)', line):
            H("PUNCT", f"space before {m.group(1)!r} in {line.strip()[:40]!r}")

    # ---- NOSPACE ----  a removal glued tokens together (a word fused to bold-open-paren,
    # NOT the legitimate "**(ParentOID, ChildOID)**" bold parenthetical)
    for m in re.finditer(r'[A-Za-z]\*\*\(', prose):
        H("NOSPACE", f"word glued to '**(' (lost space): {m.group(0)!r}")
    for m in re.finditer(r'[a-z]\(([a-z_]+\.md)[^)]*\)', prose):
        H("NOSPACE", f"raw md filename glued: {m.group(0)[:28]!r}")

    # ---- TRUNCATED ----  a removal took a sentence's only verb/terminator, leaving a paragraph
    # that ends on a bare word (no terminal punctuation) — e.g. "… makes ReFS a peer driver "
    glines = gen.split("\n")
    infence = False
    for k, raw in enumerate(glines):
        if raw.lstrip().startswith("```"):
            infence = not infence; continue
        if infence or not raw.strip():
            continue
        if raw[:1] in (" ", "\t"):                        # indented continuation of a list/def — skip
            continue
        st = re.sub(r"`[^`]*`", "CODE", raw).rstrip()     # mask inline code in THIS line only
        nxt = glines[k + 1].strip() if k + 1 < len(glines) else ""
        para_end = (k + 1 >= len(glines) or nxt == "" or nxt.startswith("#"))
        nb = next((glines[m].strip() for m in range(k + 1, len(glines)) if glines[m].strip()), "")
        if nb.startswith("```"):                          # a lead-in sentence to a code block — legit
            continue
        is_prose = not re.match(r'^\s*([#>|]|[-*+]\s|\d+\.\s|!\[|\[|<)', st) and "|" not in st
        if para_end and is_prose and re.search(r'[a-z,;]$', st) and len(st.split()) > 3:
            H("TRUNCATED", f"paragraph ends without terminal punctuation: …{st[-40:]!r}")

    # ---- LOSTPAREN ----  inline-code func() that lost its ()
    src_fn = len(re.findall(r'`[^`]*\b\w+\(\)[^`]*`', src))
    gen_fn = len(re.findall(r'`[^`]*\b\w+\(\)[^`]*`', gen))
    if gen_fn < src_fn:
        H("LOSTPAREN", f"inline `func()` count {src_fn} -> {gen_fn} (lost {src_fn - gen_fn})")

    # ---- EMDASH ----  a clause-final em-dash dropped, fusing two clauses into a run-on.
    # Precise: source "p1 —\n p2" becomes gen "p1 p2" (the two clauses appear adjacent, no dash).
    if src:
        gnl = re.sub(r"\s+", " ", re.sub(r"`[^`]*`", "", gen))
        for m in re.finditer(r'(\w+(?:\s+\w+){2,3})[ \t]*—[ \t]*\n[ \t]*(\w+(?:\s+\w+){1,2})', src):
            join = re.sub(r"\s+", " ", m.group(1) + " " + m.group(2))
            if join in gnl:
                H("EMDASH", f"clause-final em-dash dropped: {join[:50]!r}")

    # ---- LINK ----
    pr = split_code(gen)
    for m in LINK.finditer(pr):
        tgt = m.group(2).strip()
        if tgt.startswith(("http://", "https://", "#", "mailto:", "/")):
            continue
        b = os.path.basename(tgt.split("#")[0]).lower()
        if not b.endswith(".md"):
            continue
        if b in UNPUB:
            H("LINK", f"link to unpublished page {tgt!r}")
        elif b not in pub:
            H("LINK", f"link resolves to no published page: {tgt!r}")
    # a build must not DESTROY links: a "[text](page.md)" link to a PUBLISHED page must survive
    # (a stripped destination leaves bare "[text]" which earlier checks can't see).
    src_pr = split_code(src)
    def published_md_links(t):
        out = []
        for m in LINK.finditer(t):
            b = os.path.basename(m.group(2).split("#")[0]).strip().lower()
            if b.endswith(".md") and b in pub:
                out.append(b)
        return sorted(out)
    s_links, g_links = published_md_links(src_pr), published_md_links(pr)
    if len(g_links) < len(s_links):
        from collections import Counter
        missing = Counter(s_links) - Counter(g_links)
        H("LINK", f"destroyed {sum(missing.values())} link(s) to published pages: {dict(missing)}")
    for m in re.finditer(r'(?<!\])\[([A-Z][A-Za-z0-9 /+.\-]{3,})\](?!\()', pr):  # orphaned link text
        H("LINK", f"orphaned link text (destination stripped): {m.group(0)[:40]!r}")

    return hits


def calibrate(pub):
    """Prove the LEAK gate FIRES on a planted finding-ID in EACH position — prose, `inline code`, and
    a ``` fence. The inline-code and fenced cases are exactly what the pre-hardening code-masked scan
    MISSED; because this exercises the real check_page(), reverting the ALPHA_ID scan back to the
    masked `prose` makes those two cases MISS and this calibration FAIL — so it guards the hardening."""
    ps = pairs()
    if not ps:
        print("calibration: FAIL — no pages to use as a carrier ✗"); return False
    gen0, src0 = ps[0]
    carrier = open(gen0, encoding="utf-8").read()
    ID = "FS_OTBL_SA_001"

    def leaks(text):
        return [h for h in check_page(gen0, src0, pub, gen=text) if h[0] == "LEAK" and ID in h[2]]

    ok_all = True
    ctrl = leaks(carrier)                                   # control: the clean carrier must be clean
    ctrl_ok = not ctrl
    ok_all &= ctrl_ok
    print(f"  {'control (clean carrier)':26} -> {'CLEAN ✓' if ctrl_ok else 'DIRTY ✗ ' + str(ctrl[:2])}")
    for name, text in (
        ("prose",        carrier + f"\n\nplanted {ID} in prose.\n"),
        ("`inline code`", carrier + f"\n\nplanted `{ID}` in inline code.\n"),
        ("``` fence",    carrier + f"\n\n```\nplanted {ID} in a fence\n```\n"),
    ):
        fired = bool(leaks(text))
        ok_all &= fired
        print(f"  planted in {name:15} -> {'FIRED ✓' if fired else 'MISSED ✗'}")
    print("calibration:", "PASS — gate catches prose/inline/fenced finding-id leaks ✓" if ok_all
          else "FAIL — a planted leak went undetected ✗")
    return ok_all


def check_sitemap(root):
    """RC3b (the maintainer, 2026-11-22: "be sure to update the sitemap.xml"): in the RENDERED site `root`, sitemap.xml
    lists every page Hugo wrote and no redirect page (a moved page's old address, an alias). Hugo regenerates the file
    at every build; this checks what it wrote. Returns the problems, [] when it is right."""
    sm = os.path.join(root, "sitemap.xml")
    if not os.path.isfile(sm):
        return ["no sitemap.xml in %s" % root]
    locs = set()
    for m in re.finditer(r"<loc>([^<]+)</loc>", open(sm, encoding="utf-8").read()):
        u = m.group(1)
        locs.add(re.sub(r"^[a-z]+://[^/]+/", "", u))
    pages, redirects = set(), set()
    for d, _dirs, files in os.walk(root):
        if "index.html" not in files:
            continue
        rel = os.path.relpath(d, root)
        key = "" if rel == "." else rel.replace(os.sep, "/") + "/"
        head = open(os.path.join(d, "index.html"), encoding="utf-8", errors="replace").read(2048)
        (redirects if 'http-equiv="refresh"' in head or "http-equiv=refresh" in head else pages).add(key)
    probs = ["page not in sitemap.xml: /%s" % k for k in sorted(pages - locs)]
    probs += ["redirect page listed in sitemap.xml: /%s" % k for k in sorted(locs & redirects)]
    probs += ["sitemap.xml lists a page that was not written: /%s" % k for k in sorted(locs - pages - redirects)]
    return probs


def main():
    report = "--report" in sys.argv
    rendered = [a for a in sys.argv[1:] if not a.startswith("--")]
    if rendered:
        probs = check_sitemap(rendered[0])
        for pr in probs:
            print("  [sitemap  ] " + pr)
        if probs:
            print("FAIL — sitemap.xml: %d problem(s)" % len(probs))
            return 1
        print("sitemap.xml: every rendered page listed, no redirect page listed")
    pub = published_basenames()
    if "--calibrate" in sys.argv:
        return 0 if calibrate(pub) else 1
    all_hits = []
    for gen, src in pairs():
        all_hits.extend(check_page(gen, src, pub))
    from collections import Counter
    by = Counter(h[0] for h in all_hits)
    if all_hits:
        # group by file for readability
        from collections import defaultdict
        d = defaultdict(list)
        for cls, rel, msg in all_hits:
            d[rel].append((cls, msg))
        if report or True:
            for rel in sorted(d):
                print(f"\n  {rel}")
                for cls, msg in d[rel]:
                    print(f"     [{cls:9}] {msg}")
        print(f"\nFAIL — {len(all_hits)} artifact(s): " + ", ".join(f"{k}={v}" for k, v in sorted(by.items())))
        return 1
    print(f"PASS — site clean ({len(pairs())} pages, 0 artifacts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
