#!/usr/bin/env python3
"""
build.py — generate the Hugo `content/` tree from the documentation .md files.

You only ever edit Markdown: the docs in forefst/docs/, and the site-only pages under
website/pages/ (Home, About, and the per-section intros in website/pages/sections/).
This script assembles content/ from them:

  * copies docs/{concepts,structures,attributes,tools,examples}/*.md into content/
  * strips the analysis-only "**Status:** … E2/RD … Findings …" footer from every page
  * de-jargons the body for the reader-facing site: removes the repository provenance
    (finding-IDs, evidence grades E1/E2/E3/RD, master/structure_reference §, errata, the
    "Findings:" summary and the "how this was verified" pointer) WITHOUT damaging prose.
    All de-jargon surgery runs on prose only — fenced ``` blocks and `inline code` are masked
    first and restored after, so code (including `func()` calls) is never touched; removals
    repair the sentence (no dangling "is.", no "are and.", no stray punctuation); line-ending
    em-dashes and list indentation are never altered. The SOURCE docs keep every token for
    repository traceability — only the generated site is de-jargoned.
  * derives each page's title from its first `# H1` and a sort key that IGNORES a leading `$`
  * groups the Concepts into subsections (General first)
  * folds the worked examples under Tools
  * drops the `$CBW4` page and its inline mentions (a debunked prior-work name)
  * unwraps links to files the site does not publish (README, knowledge map, CONTRIBUTING, …)

Re-run after editing any Markdown:  python3 build.py   →   hugo server
The build ends by running verify_site.py — the regression gate that FAILS on any leaked token
or prose artifact. Keep it green.
"""
import os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
def _default_docs():
    # Locate the docs/ tree by content (a dir holding concepts/ + structures/), so this works whether
    # website/ lives inside docs/ (docs/website/ -> docs is the parent), beside docs/, or beside forefst/.
    for c in (os.path.join(HERE, ".."),
              os.path.join(HERE, "..", "docs"),
              os.path.join(HERE, "..", "forefst", "docs")):
        if os.path.isdir(os.path.join(c, "concepts")) and os.path.isdir(os.path.join(c, "structures")):
            return c
    return os.path.join(HERE, "..", "forefst", "docs")
DOCS = os.environ.get("REFS_DOCS") or _default_docs()
CONTENT = os.path.join(HERE, "content")
PAGES = os.path.join(HERE, "pages")
SECTION_PAGES = os.path.join(PAGES, "sections")

SECTIONS = ["concepts", "structures", "attributes", "tools"]

# Pages never published to the site (by basename).
# (The debunked $CBW4 / $PAGE pages were removed from docs/ entirely; any residual
# inline $CBW4 mention is still stripped by scrub_cbw4 below.)
EXCLUDE = {"README.md"}

# Links to these basenames are unwrapped to plain text (repo-internal, not on the site).
UNPUBLISHED = {"readme.md", "knowledge_map.md", "contributing.md", "changelog.md",
               "test_baseline_images.md", "methodology.md"}

# Ordered subsections for grouped sections (concepts, structures). Each page is placed in the first
# group that lists it; a page listed nowhere falls into the LAST group. Order WITHIN a group follows
# its file list here (emitted as the page `sort` key). Edit freely — this only drives site grouping.
CONCEPT_GROUPS = [
    ("General", [
        "ntfs_comparison.md", "version_detection.md", "version_evolution.md", "driver_architecture.md",
    ]),
    ("On-disk mechanics", [
        "bootstrap_chain.md", "architecture.md", "virtual_addressing.md", "cluster_page_size.md",
        "resident_storage.md", "copy_on_write.md", "allocation_space_mgmt.md",
        "transactions_crash_consistency.md",
    ]),
    ("Integrity & redundancy", [
        "checksum_architecture.md", "integrity_streams.md", "redundancy.md",
    ]),
    ("Files, metadata & features", [
        "object_ids_fileids.md", "oid_allocation.md", "attributes.md", "hard_links.md",
        "snapshots_versioning.md", "wsl_metadata.md", "compression.md", "deduplication.md",
        "tiering.md",
    ]),
    ("Forensics & recovery", [
        "deletion_recovery.md", "what_survives.md", "timestomp_detection.md", "artifact_timeline.md",
        "forensic_analysis_workflow.md", "tool_artifact_map.md",
    ]),
    ("Background & context", [
        "file_systems.md", "windows_file_systems.md", "carrier_categories.md",
    ]),
]
STRUCTURE_GROUPS = [
    ("Boot & bootstrap", [
        "vbr.md", "supb.md", "chkp.md", "system_oids.md",
    ]),
    ("B+-tree rows & pages", [
        "btree_node.md", "page_header.md", "page_references.md", "directory_entries.md",
        "extent_descriptors.md", "reverse_index.md",
    ]),
    ("System tables (the 13 roots)", [
        "object_table.md", "schema_table.md", "parent_child_table.md", "container_table.md",
        "container_index.md", "allocators.md", "block_refcount.md", "integrity_state.md",
        "volume_info.md", "security_descriptors.md", "reparse_points.md", "upcase_table.md",
        "trash_table.md",
    ]),
    ("Journals & logs", [
        "usn_journal.md", "mlog.md",
    ]),
]
SECTION_GROUPS = {"concepts": CONCEPT_GROUPS, "structures": STRUCTURE_GROUPS}

# Per-section meta descriptions for SEO — emitted into each section _index front matter
# (drives <meta name="description"> + Open Graph on the section landing pages).
SECTION_DESCRIPTIONS = {
    "concepts":   "How ReFS works: copy-on-write, virtual addressing, the object model, deletion recovery, and timestomp detection — the mechanisms behind the on-disk format.",
    "structures": "Byte-level on-disk layouts of every ReFS metadata structure — VBR, superblock, checkpoint, B+-tree pages, the 13 system tables, and the journals.",
    "attributes": "The ReFS attribute set decoded — $STANDARD_INFORMATION, $DATA, $EA (WSL $LX*), $REPARSE_POINT, $EFS, and more.",
    "tools":      "forefst.py and refsanalysis.py — open-source, pure-Python forensic and structural analysis for ReFS volumes.",
}

def grouping_for(basename, groups):
    """(group_name, group_order_index, sort_within_group) for a page in a grouped section."""
    for gi, (g, files) in enumerate(groups):
        if basename in files:
            return g, gi, files.index(basename)
    last = len(groups) - 1
    return groups[last][0], last, 99

# Each page may carry one or more figures (svg, caption), inserted after the lead paragraph.
# SVGs live in website/assets/diagrams/ and are inlined + themed by the image render hook.
DIAGRAMS = {
    "bootstrap_chain.md":     [("bootstrap-chain.svg",      "The bootstrap chain: VBR → SUPB → CHKP → the 13 root tables."),
                               ("boot-mbr-gpt.svg",         "Where the volume begins: BIOS/MBR vs UEFI/GPT boot, and the ReFS partition.")],
    "btree_node.md":          [("btree-traversal.svg",      "A Minstore B+-tree: a lookup descends from the root through internal nodes to the leaf rows."),
                               ("btree-node.svg",           "Inside one node: header, sorted index of offsets, key/value rows, and free space (where deleted rows persist).")],
    "virtual_addressing.md":  [("virtual-addressing.svg",   "Virtual-to-physical cluster translation through the Container Table.")],
    "version_evolution.md":   [("version-timeline.svg",     "ReFS on-disk versions, 3.4 → 3.14 (with the two-stage 3.10→3.14 transition).")],
    "architecture.md":        [("volume-overview.svg",      "Structural overview of a ReFS 3.14 volume: how the metadata structures reference each other."),
                               ("two-layer.svg",            "The two layers of ReFS: the Minstore B+-tree engine below, the object/file layer above.")],
    "resident_storage.md":    [("resident-nonresident.svg", "Resident (inline) vs non-resident (extent-mapped) storage of a file's content.")],
    "ntfs_comparison.md":     [("ntfs-allocation.svg",      "The NTFS model for contrast: a directory entry points to an MFT record holding metadata and data runs.")],
    "hard_links.md":          [("namespace-graph.svg",      "A tree namespace vs a directed-graph namespace — what hard links turn the file system into.")],
    "deletion_recovery.md":   [("ntfs-deletion.svg",        "The NTFS deletion baseline: the three steps that leave content recoverable.")],
    "file_systems.md":        [("storage-hierarchy.svg",    "The storage abstraction stack, from physical disk up to the file system.")],
    "cluster_page_size.md":   [("sectors-clusters-slack.svg","Sectors, clusters, file data, and slack space.")],
    "windows_file_systems.md":[("windows-architecture.svg", "Simplified Windows architecture relevant to file-system processing (adapted from Windows Internals)."),
                               ("windows-file-open.svg",    "Conceptual view of a local Windows file-open operation (adapted from Windows Internals).")],
}

FOOTER_RE = re.compile(r"\n+-{3,}\s*\n+\*\*Status:\*\*.*\Z", re.S)
H1_RE = re.compile(r"(?m)^#\s+(.+?)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# "[label](CBW4.md)" links -> their label (other $CBW4 mentions handled in scrub_cbw4)
CBW4_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*CBW4[^)]*\)")


# ---------------------------------------------------------------------------
# De-jargon
# ---------------------------------------------------------------------------
ALPHA   = r'(?:GN|FS|CT|MD|FN|AP)_[A-Z0-9]+(?:_[A-Z0-9]+)*_\d{3}(?:[-–—]\d{3})?'
_BID    = r'\*{0,2}' + ALPHA + r'\*{0,2}'                       # optionally-bold id
_IDLIST = _BID + r'(?:\s*(?:,|/|and)\s*' + _BID + r')*'         # "**A**, **B** and **C**"
GRADE   = r'E[1-4](?:/E[1-4])*(?:\+(?:E[1-4]|RD))*'             # E1  E2+RD  E1/E2/RD …
_GR     = r'(?:' + GRADE + r'|RD)'
_SEC    = r'§[A-Z](?![A-Za-z])(?:\.[A-Za-z0-9]+)*'             # master §G.1 / §A.1a / §J — single-letter section only (not "§Three-tier"); never eats a trailing "."

# adjectival evidence shorthand -> plain reader language (KEPT: it carries reader meaning)
_EV_SUBS = [
    (r'\bRD[- ]re-verified\b', 'verified again on disk'), (r'\bRD-verified\b', 'verified on disk'),
    (r'\bRD-confirmed\b', 'confirmed on disk'), (r'\bRD-validated\b', 'validated on disk'),
    (r'\bRD-proven\b', 'proven on disk'), (r'\bRD-grounded\b', 'grounded on disk'),
    (r'\bRD-observed\b', 'observed on disk'), (r'\bRD-measured\b', 'measured on disk'),
    (r'\bRD-decoded\b', 'decoded on disk'), (r'\bRD-disproven\b', 'disproven on disk'),
    # "(RD)" after a phrase that ALREADY says raw-disk/on-disk -> just drop it (avoid "raw-disk confirmed on disk")
    (r'\b(raw-disk[- ]?confirmed)\s+\(RD\)', r'\1'),
    (r'\b(on disk)\s+\(RD\)', r'\1'),
    (r'\bconfirmed\s+\(RD\)', 'confirmed on disk'),               # the non-raw-disk case
    (r'\bE2-confirmed\s+in\b', 'confirmed in'),                   # "E2-confirmed in the X" -> "confirmed in the X" (no double "in the driver in the")
    (r'\bE2-confirmed\b', 'confirmed in the driver'), (r'\bE2-grounded\b', 'grounded in the driver'),
    (r'(?m)^(#+\s+)RD Verification\b', r'\1On-Disk Verification'),
    (r'(?m)^(#+\s+Statistics)\s*\(RD\)\s*$', r'\1'),
]


def _mask_code(t):
    store = []
    def keep(m):
        store.append(m.group(0)); return f"\x00{len(store) - 1}\x00"
    def keep_inline(m):
        # A finding-id wrapped in `inline code` (e.g. "`FS_OTBL_SA_001`") must NOT be protected as
        # code, or it leaks to the reader site (the id-stripper below runs on masked text and never
        # sees it). Unwrap such a span to its BARE id so the existing stripper removes it exactly
        # like an unbackticked one. ALPHA is specific (known prefixes + _NNN); no legitimate code
        # token (`CRC64`, `value+0x38`, `AF_UNIX`) matches, so real code is still protected.
        inner = m.group(0)[1:-1]
        if re.fullmatch(ALPHA, inner):
            return inner
        store.append(m.group(0)); return f"\x00{len(store) - 1}\x00"
    t = re.sub(r"```.*?```", keep, t, flags=re.S)   # fenced blocks (protected verbatim)
    t = re.sub(r"`[^`]*`", keep_inline, t)          # inline spans (finding-ids unwrapped, rest protected)
    return t, store


def _unmask(t, store):
    return re.sub(r"\x00(\d+)\x00", lambda m: store[int(m.group(1))], t)


def _tidy(s):
    """Repair punctuation left by removals. Never touches leading indentation or line-final em-dashes
    (a dash is only dropped when punctuation immediately follows it). Removals run first; a single
    whitespace/punctuation normalization pass runs LAST so earlier removals can't leave residue."""
    s = re.sub(r'\(\s*[;,]\s*', '(', s)                          # "(; X" -> "(X"  (no "/" — must not eat a link URL's slashes)
    s = re.sub(r'\s*[;,]\s*\)', ')', s)
    s = re.sub(r'\(\s*\)', '', s)
    s = re.sub(r'\(\s+', '(', s); s = re.sub(r'\s+\)', ')', s)
    s = re.sub(r'\band\s+([.;,])(?!\w)', r'\1', s)                # "A and ." -> "A." (not "and .NET")
    s = re.sub(r',\s*([.;])(?![.\d])', r'\1', s)                  # "A, ." -> "A." (but keep "(or third, ...)" ellipsis)
    s = re.sub(r'[ \t]*—[ \t]*([.;,)])', r'\1', s)               # dash stranded before punctuation/paren -> drop dash
    s = re.sub(r'\([ \t]*—[ \t]*', '(', s)                       # dash stranded just after "("
    s = re.sub(r'\*\*\s*\*\*', '', s)                            # emptied bold "****"
    s = re.sub(r'[ \t]*\n[ \t]*([.;,])[ \t]*(?=\S)', r'\1\n', s)  # orphaned leading "." -> attach to prev line (consume the trailing space too)
    s = re.sub(r'(?<!\.)\.[ \t]*\.(?=\s|$|[A-Z])', '.', s)        # "v3.14.." -> "v3.14." (only sentence context; keep "3..end", "../", "...")
    s = re.sub(r',\s*,', ',', s)
    # a copula-rewrite that collides with the source's own verb: "confirmed (…) confirmed" -> "confirmed (…)"
    s = re.sub(r'\b(confirmed|verified)\b(\s*\([^()]*\)\s*)(?:confirmed|verified)\b', r'\1\2', s)
    # final normalization (interior only — never leading indentation; never the space before an ellipsis/range)
    s = re.sub(r'(?<=\S)[ \t]{2,}(?=\S)', ' ', s)
    s = re.sub(r'[ \t]+([.,;:])(?![.\w])', r'\1', s)             # space before punct, but keep " .NET", " ...", " 0.5"
    return s


def dejargon(text):
    # 0) provenance trailers handled on RAW text (distinctive strings) -------------------
    # "- Master reference: …" / "- Master **§C.7** …" / "- Master thesis appendix …" pointer bullets -> drop
    text = re.sub(r'(?m)^[ \t]*[-*]\s*Master reference:.*$\n?', '', text)
    text = re.sub(r'(?m)^[ \t]*[-*]\s*Master\s+\*\*§.*$\n?', '', text)
    text = re.sub(r'(?m)^[ \t]*[-*]\s*Master thesis appendix\b.*$\n?', '', text)
    # § inside a LINK LABEL: "[Foo §4]" -> "[Foo]" (drop the section-number suffix);
    # "[Architecture §Three-tier IRP dispatch]" -> "[Three-tier IRP dispatch]" (keep the heading)
    text = re.sub(r'\[([^\]]*?)\s*§\d+(?:\.\d+)?\s*\]', r'[\1]', text)
    text = re.sub(r'\[[^\]]*?\s+§\s*([A-Z][^\]]*)\]', r'[\1]', text)
    # the "See [how this was verified](… methodology …) …" reader-pointer -> drop (repo-facing).
    # Whitespace-flexible (the sentence wraps: "See\nhow", "in\n`analysis/`").
    text = re.sub(r'\s*See\s+\[?how\s+this\s+was\s+verified\]?(?:\s*\([^)]*\))?[\s\S]*?\.(?=\s|\Z)', '', text)
    # a "Findings: <summary>." provenance clause -> drop (the body already states the facts),
    # whether it leads a line or trails a sentence; the summary may wrap across lines.
    text = re.sub(r'(?m)^[ \t>]*\**Findings?\**:\s[\s\S]*?\.(?=\s|\Z)', '', text)
    text = re.sub(r'(?<=\.)\s+\**Findings?\**:\s[\s\S]*?\.(?=\s|\Z)', '', text)
    # the register framing and the grade-definition legend -> drop (jargon, not reader content)
    text = re.sub(r'\s*\bin the (?:master|central) reference\b(?:\s*\([^)]*\))?', '', text)
    text = re.sub(r'\s*\band the (?:central )?findings register\b', '', text)
    text = re.sub(r'\s*\bGrades are E1\b[\s\S]*?measured\)?;', '', text)
    text = re.sub(r'\s*\bGrades are E1\b[^.]*\.', '', text)
    text = re.sub(r'\.\s+the per-goal', r'. The per-goal', text)
    # the glossary entry that *defines* the grade jargon — orphaned on the site -> drop it
    text = re.sub(r'(?m)^##\s+Evidence and Method\s*\n+\*\*Evidence levels\*\*[^\n]*\n:[^\n]*\n?', '', text)

    masked, store = _mask_code(text)
    s = masked
    for pat, repl in _EV_SUBS:
        s = re.sub(pat, repl, s)

    # 1) copula -> "confirmed", preserving the subject -----------------------------------
    s = re.sub(r'\b(is|are)\s+the\s+subjects?\s+of\s+findings?\s+' + _IDLIST, r'\1 confirmed', s)  # "is the subject of finding X" -> "is confirmed"
    s = re.sub(r'\b(is|are)\s+findings?\s+' + _IDLIST + r'\s*(?:\(\s*' + _GR + r'[^()]*\))?', r'\1 confirmed', s)
    s = re.sub(r'\b(is|are)\s+' + _IDLIST + r'\s*(?:\(\s*' + _GR + r'[^()]*\))?(?=\s*[.;,)])', r'\1 confirmed', s)
    s = re.sub(r'\b(is|are)\s+' + _GR + r'\s*:', r'\1 confirmed in the driver:', s)
    s = re.sub(r'\b(is|are)\s+RD\b(?=\s+(?:on|across|for|from|in)\b)', r'\1 confirmed', s)  # "are RD on X" -> "are confirmed on X" (no double "on")
    s = re.sub(r'\b(is|are)\s+RD\b', r'\1 confirmed on disk', s)         # "is RD" / "are RD."
    s = re.sub(r'\b(is|are)\s+(?:' + GRADE + r')\b', r'\1 confirmed', s) # "are E2+RD." "is E2 (`Fn`)"

    # 2) drop remaining evidence parentheticals & inline ids -----------------------------
    s = re.sub(r'\(\s*' + _GR + r'\s*[—:\-]\s*', '(', s)                 # "(E2 — `Fn`)" -> "(`Fn`)"
    s = re.sub(r'\s*\(\s*(?:no\s+)?' + _GR + r'[^()—]*\)', '', s)        # (E2 win11 L159529) (RD, 985)
    s = re.sub(r'\s*[|·]\s*\*\*Evidence Level:\*\*[^|·\n]*', '', s)
    s = re.sub(r'(?m)^\*\*Evidence Level:\*\*[^\n]*\n?', '', s)
    s = re.sub(r'[;,]\s*(?:no\s+)?' + _GR + r'\b[^()—]*(?=\))', '', s)   # (set by X, E2) -> (set by X)
    s = re.sub(r'\bEvidence:\s*' + _GR + r'\b[^.\n]*\.', '', s)          # "Evidence: E2 (Foo)."
    # ", confirming/showing/proving <id>:" provenance tail -> drop (end the sentence)
    s = re.sub(r',\s*(?:confirming|showing|proving|demonstrating)\s+' + _IDLIST + r'\s*[:.]', '.', s)
    # the scaffold word "finding(s)" DIRECTLY before an id -> drop it (keeps the verb: "reproduces finding X" -> "reproduces").
    # Only fires when an id follows, so a legitimate gerund ("finding one is…", "finding it on disk") is untouched.
    s = re.sub(r'\b[Ff]indings?\s+(?=\*{0,2}' + ALPHA + r')', '', s)
    # same scaffold, for an internal "(audit) dossier" back-reference DIRECTLY before an id
    # (e.g. "(audit dossier `FS_OTBL_SA_001`)"). Only fires when an id follows, so "the case dossier" survives.
    s = re.sub(r'\b(?:audit\s+)?dossiers?\s+(?=\*{0,2}' + ALPHA + r')', '', s, flags=re.I)
    s = re.sub(r'\s*\*\*\s*' + _IDLIST + r'\s*\*\*', '', s)              # bold id lists
    s = re.sub(r'\s*\b' + _IDLIST + r'\b', '', s)                        # bare id lists
    # standalone grades left after a connector ("plus RD on the images" -> "plus confirmed on the images", not "…on disk on…")
    s = re.sub(r'\b(and|plus|,|;)\s+RD\b(?=\s+(?:on|across|for|from|in)\b)', r'\1 confirmed', s)
    s = re.sub(r'\b(and|plus|,|;)\s+RD\b(?=\s)', r'\1 confirmed on disk', s)
    s = re.sub(r'\b(and|plus|,|;)\s+(?:' + GRADE + r')\b(?=\s)', r'\1 confirmed', s)
    s = re.sub(r',\s+with\s*([.;])', r'\1', s)                           # "…Callback`, with." (id list removed) -> "…Callback`."

    # 3) master section refs, errata, internal register codes ----------------------------
    s = re.sub(r'\b(is|are)\s+(?:master\s+)?' + _SEC, r'\1 confirmed', s)  # "X is master §G.1." -> "X is confirmed."
    s = re.sub(r'\*\*\s*' + _SEC + r'\s*\*\*', '', s)                      # bold section refs "**§C.7**"
    s = re.sub(r'\bMaster thesis appendix\s+', '', s)
    s = re.sub(r"\bthe master's\b", 'the', s)
    s = re.sub(r'\s*\(\s*(?:see\s+)?(?:master\s+)?' + _SEC + r'\s*\)', '', s, flags=re.I)
    s = re.sub(r',?\s*(?:master\s+)?' + _SEC, '', s, flags=re.I)
    s = re.sub(r'\s*[—-]\s*(?:see\s+)?errata\s+E-?\d+\b', '', s)
    s = re.sub(r'\s*\(\s*(?:see\s+|finding\s+)?E-?\d{2,}\s*\)', '', s)
    s = re.sub(r'\s*[;,/]\s*(?:see\s+)?errata\s+E-?\d{2,}\b', '', s)
    s = re.sub(r'\bopen question [A-Z]\d\b', 'an open question', s)
    # reader-facing provenance-framing phrases (the site hides the evidence-grade / finding-ID system)
    s = re.sub(r',\s*with their evidence levels and finding IDs,\s*', ' ', s)
    s = re.sub(r'\bwith (?:their )?evidence levels?(?: and finding[- ]?IDs?)?\b', '', s)
    s = re.sub(r'\bThe audited claim behind every row is cited in\b', 'The basis for every row is given in', s)
    s = re.sub(r'\bEach goal in the bridge table is backed by an audited claim\.\s*', '', s)
    s = re.sub(r'\baudited (claim|structure)\b', r'\1', s)
    # bare appendix / subtable cross-references the author wrote WITHOUT a § (A.4a, B.6a, C.3)
    s = re.sub(r'\s*\((?:sub)?table\s+[A-J]\.\d+[a-z]?\)', '', s, flags=re.I)
    s = re.sub(r'\b(?:sub)?table\s+[A-J]\.\d+[a-z]?\s+', '', s, flags=re.I)
    s = re.sub(r',\s*[A-J]\.\d+[a-z]?(?=\s*[):])', '', s)
    s = re.sub(r'\b(the)\s+[A-J]\.\d+[a-z]?\s+(non-resident|value)\b', r'\1 \2', s)

    # 4) worked-example PLAIN-TEXT cross-refs "(vbr.md, §X)" -> drop. The (?<!\]) guard is critical:
    # it must NOT touch a markdown link destination "[text](vbr.md)" (that would destroy the link).
    s = re.sub(r'(?<!\])\s*\(([a-z_]+\.md)(?:,\s*' + _SEC + r')?\)', '', s)

    s = _tidy(s)
    return _unmask(s, store)


def strip_footer(t):       return FOOTER_RE.sub("\n", t).rstrip() + "\n"
def first_h1(t):           m = H1_RE.search(t); return m.group(1).strip() if m else None
def yaml_escape(s):        return s.replace('\\', '\\\\').replace('"', '\\"')
def sort_key(title):       return re.sub(r"^[^0-9A-Za-z]+", "", title).lower()


SECTION_DIRS = ("concepts", "structures", "attributes", "tools", "examples")

def unwrap_unpublished_links(t):
    def repl(m):
        label, target = m.group(1), m.group(2)
        path = target.split("#")[0]
        base = os.path.basename(path).lower()
        if base == "readme.md":
            # a SECTION readme -> redirect to that section's landing page (keep the link);
            # the top-level readme -> unwrap to plain text (no landing page).
            parts = [p for p in path.replace("\\", "/").split("/") if p not in ("", ".", "..")]
            if len(parts) >= 2 and parts[-2] in SECTION_DIRS:
                sec = "tools" if parts[-2] == "examples" else parts[-2]
                return f"[{label}](/{sec}/)"
            return label
        return label if base in UNPUBLISHED else m.group(0)
    return LINK_RE.sub(repl, t)


def scrub_cbw4(t):
    """Remove every mention of the debunked prior-work name $CBW4 (the reader never saw it, so the site
    must not say it 'does not exist'). Targeted + link-safe — never eats a nested markdown link or a
    table's structure. The gate's CBW4 leak-check is the backstop if a new phrasing ever appears."""
    t = CBW4_LINK_RE.sub(r"\1", t)                                          # [label](CBW4.md) -> label
    t = re.sub(r';\s*the name \$?`?CBW4`?[^;,]*', '', t)                    # "; the name $CBW4 … is a fabrication" (keeps a following link)
    t = re.sub(r'\s*There is \*\*no `?\$?CBW4`? stream\*\*[\s\S]*?\.(?=\s|\Z)', '', t)   # the EFS back-reference sentence
    t = re.sub(r'no\s+`?\$?CBW4`?\s*/\s*', '', t)                          # "*no $CBW4 / no EFSS / no DRF*" -> "*no EFSS / no DRF*" (keep the real facts)
    t = re.sub(r"(?m)^[ \t]*[-*+] .*CBW4.*(?:\n|$)", "", t)                 # any list item mentioning it
    return t


_TBL_SEP = re.compile(r'^\s*\|[\s:|-]+\|\s*$')

def _drop_empty_table_cols(text):
    """Drop a table's trailing column(s) when its header is non-empty but every body cell is blank
    (a §-reference column whose cells the de-jargon emptied). Only tables that actually lose a column
    are rebuilt; all other tables pass through byte-for-byte (minimal change)."""
    lines = text.split("\n"); out = []; i = 0
    def cells(r): return [c.strip() for c in r.strip().strip("|").split("|")]
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and _TBL_SEP.match(lines[i + 1]):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            block = lines[i:j]
            rows = [cells(r) for r in block]
            ncol = len(rows[0]); body = rows[2:]
            keep = ncol
            while keep > 1 and body and all(len(b) == ncol for b in body) \
                    and all(b[keep - 1] == "" for b in body) and rows[0][keep - 1] != "":
                keep -= 1
            if keep < ncol:
                for k, r in enumerate(block):
                    rc = cells(r)[:keep]
                    out.append("|" + "|".join("------" for _ in range(keep)) + "|" if k == 1
                               else "| " + " | ".join(rc) + " |")
            else:
                out.extend(block)
            i = j
        else:
            out.append(lines[i]); i += 1
    return "\n".join(out)


def inject_diagram(body, basename):
    figs = DIAGRAMS.get(basename)
    if not figs:
        return body
    imgs = "\n\n".join(f"![{cap}]({svg})" for svg, cap in figs)
    parts = body.split("\n\n")
    parts.insert(2 if len(parts) > 2 else len(parts), imgs)
    return "\n\n".join(parts)


def transform(src_path, group=None, weight=None, sort=None):
    raw = open(src_path, encoding="utf-8").read()
    body = dejargon(scrub_cbw4(unwrap_unpublished_links(strip_footer(raw))))
    body = _drop_empty_table_cols(body)
    body = inject_diagram(body, os.path.basename(src_path))
    title = first_h1(body) or os.path.splitext(os.path.basename(src_path))[0].replace("_", " ").title()
    sort_val = sort if sort is not None else sort_key(title)
    fm = ['---', f'title: "{yaml_escape(title)}"', f'sort: "{yaml_escape(sort_val)}"']
    if group is not None:
        fm.append(f'group: "{yaml_escape(group)}"')
    if weight is not None:
        fm.append(f'weight: {weight}')
    fm.append('---\n\n')
    return title, "\n".join(fm) + body


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def listed_md(d):
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, fn) for fn in sorted(os.listdir(d))
            if fn.endswith(".md") and fn not in EXCLUDE]


def section_index_body(sec, extra=""):
    """Intro for a section: from website/pages/sections/<sec>.md if present, else a default line."""
    p = os.path.join(SECTION_PAGES, f"{sec}.md")
    if os.path.isfile(p):
        return open(p, encoding="utf-8").read().rstrip() + "\n" + extra
    return f"{sec.capitalize()}.\n" + extra


def build():
    if os.path.isdir(CONTENT):
        shutil.rmtree(CONTENT)
    os.makedirs(CONTENT)
    counts = {}

    for sec in SECTIONS:
        groups = SECTION_GROUPS.get(sec)
        # section landing page
        fm = ['---', f'title: "{sec.capitalize()}"']
        if SECTION_DESCRIPTIONS.get(sec):
            fm.append(f'description: "{yaml_escape(SECTION_DESCRIPTIONS[sec])}"')
        if groups:
            fm.append("groups: [" + ", ".join(f'"{g}"' for g, _ in groups) + "]")
        fm.append("---\n\n")
        write(os.path.join(CONTENT, sec, "_index.md"), "\n".join(fm) + section_index_body(sec))

        n = 0
        for src in listed_md(os.path.join(DOCS, sec)):
            base = os.path.basename(src)
            if groups:
                grp, gw, si = grouping_for(base, groups)
                _, text = transform(src, group=grp, weight=gw, sort=f"{si:02d}")
            else:
                _, text = transform(src)
            write(os.path.join(CONTENT, sec, base), text)
            n += 1
        counts[sec] = n

    # Examples folded under Tools
    nex = 0
    if os.path.isdir(os.path.join(DOCS, "examples")):
        write(os.path.join(CONTENT, "tools", "examples", "_index.md"),
              '---\ntitle: "Examples"\nweight: 90\n---\n\nWorked, end-to-end forensic walkthroughs.\n')
        for src in listed_md(os.path.join(DOCS, "examples")):
            _, text = transform(src)
            write(os.path.join(CONTENT, "tools", "examples", os.path.basename(src)), text)
            nex += 1
    counts["tools(examples)"] = nex

    # Glossary
    gl = os.path.join(DOCS, "glossary.md")
    if os.path.isfile(gl):
        _, text = transform(gl)
        write(os.path.join(CONTENT, "glossary.md"), text)

    # Home + About (site-only Markdown)
    for src, dst in [("home.md", "_index.md"), ("about.md", "about.md")]:
        p = os.path.join(PAGES, src)
        if os.path.isfile(p):
            shutil.copyfile(p, os.path.join(CONTENT, dst))

    print("content/ generated:")
    for k, v in counts.items():
        print(f"  {k:18} {v} pages")
    print(f"  excluded: {sorted(EXCLUDE - {'README.md'})}")


if __name__ == "__main__":
    build()
    # regression gate: fail loudly if any provenance token or prose artifact reached the site
    gate = os.path.join(HERE, "verify_site.py")
    if os.path.isfile(gate):
        print()
        rc = os.system(f'{sys.executable} {gate}')
        sys.exit(0 if rc == 0 else 1)
