#!/usr/bin/env python3
"""A claim this project has RETRACTED must not reappear in a live page or in the tools.

The hard-link claim ("a name-scoped timestomp leaves the sibling names at the true birth") was reported
corrected twice and was still on eleven live pages AND inside forefst.py -- printed output included -- when
a third review found it. Every gate passed throughout, because none of them could see it:

  * check_doc_drift.py compares sentences across pages for NUMERIC disagreement. This claim has no numbers.
  * check_doc_vocabulary.py is deliberately scoped to retired output tokens INSIDE FENCED CODE BLOCKS,
    because flagging prose there would over-reach.

So a retired PROSE claim had no owner. This is that owner.

Scope: the published docs and both tools. The CHANGELOG is excluded by design -- it is a historical record
and a released entry is never rewritten, so a retired claim legitimately survives in an old entry.

Matching: hard wraps are joined before matching, because a claim split across two lines is the normal case
and a line-by-line scan misses it (the same defect the figures register had). Each entry carries an
`unless` regex so that text STATING the correction -- which necessarily quotes the claim -- does not fire.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retired_claims.tsv")


def _tree():
    """Dev keeps the pages under forefstdev/docs; a PUBLISHED clone has docs/ at its root.

    Resolving this wrong is how a gate passes only in the maintainer's checkout. Both layouts are probed,
    so a reader can run this against the published tree and see for themselves that a retracted claim is
    absent -- which is the whole point of shipping it.
    """
    override = os.environ.get("FOREFST_TREE")
    if override:
        return os.path.join(ROOT, override)
    if os.path.isdir(os.path.join(ROOT, "forefstdev", "docs")):
        return os.path.join(ROOT, "forefstdev")
    return ROOT


TREE = _tree()
DOCS = os.path.join(TREE, "docs")
TOOLS = [os.path.join(TREE, "forefst.py"), os.path.join(TREE, "refsanalysis.py")]
README = os.path.join(TREE, "README.md")
EXCLUDE_NAMES = {"changelog.md"}
# N592 (1.14.0): only website/content/ is generated (build.py, from the pages above it); website/pages/ holds
# hand-written published pages (home, about, Methodology, ReFS Forensics 101), which the whole-website
# exclusion left unchecked.
EXCLUDE_DIRS = {os.path.join("website", "content")}


def load_spec():
    rows = []
    with open(SPEC, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            if p[0] == "id":
                continue
            if len(p) < 5:
                continue
            rows.append({"id": p[0], "pattern": p[1], "unless": p[2],
                         "retired_by": p[3], "correct": p[4]})
    return rows


def targets():
    for dirpath, dirnames, filenames in os.walk(DOCS):
        dirnames[:] = [d for d in dirnames
                       if os.path.relpath(os.path.join(dirpath, d), DOCS) not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn.endswith(".md") and fn not in EXCLUDE_NAMES:
                yield os.path.join(dirpath, fn)
    for t in TOOLS:
        if os.path.exists(t):
            yield t
    # N408 (1.14.0): the repository's front page is published too
    if os.path.exists(README):
        yield README
    # N613 (1.14.0): the site's own text -- hugo.toml (tagline, description) and the layout templates (the home page
    # <title> carried E96's 'v3.4-3.15', which no .md page held) -- is published too
    site = os.path.join(DOCS, "website")
    if os.path.exists(os.path.join(site, "hugo.toml")):
        yield os.path.join(site, "hugo.toml")
    for dirpath, _d, filenames in os.walk(os.path.join(site, "layouts")):
        for fn in sorted(filenames):
            if fn.endswith(".html"):
                yield os.path.join(dirpath, fn)
    # N328 (1.14.0): the published corpus samples' pages (analysis/samples/corpus/README.md, corpus_description.md)
    # carried retracted readings (0x2C a format-time field, checkpoint flag 0x400 = CRC64) that no gate read
    corpus = os.path.join(TREE, "analysis", "samples", "corpus")
    if os.path.isdir(corpus):
        for fn in sorted(os.listdir(corpus)):
            if fn.endswith(".md"):
                yield os.path.join(corpus, fn)


def sentences(text):
    """(sentence, line_number) with hard wraps joined."""
    out, buf, start = [], [], 1
    for i, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            if buf:
                out.append((" ".join(buf), start)); buf = []
            continue
        if not buf:
            start = i
        buf.append(line.strip())
    if buf:
        out.append((" ".join(buf), start))
    split = []
    for para, ln in out:
        for s in re.split(r"(?<=[.!?])\s+", para):
            if s.strip():
                split.append((s.strip(), ln))
    return split


def main():
    spec = load_spec()
    if not spec:
        print("retired claims: FAIL - the specification is empty; the gate would pass vacuously")
        return 1

    hits, scanned, unreadable = [], 0, []
    for path in targets():
        scanned += 1
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            # A file this gate cannot read is a file it cannot clear. Silence here would let an
            # unreadable page pass as clean, which is the defect this repository's lint exists to stop.
            unreadable.append("%s: %s" % (os.path.relpath(path, ROOT), e))
            continue
        for sent, ln in sentences(text):
            for e in spec:
                if not re.search(e["pattern"], sent, re.I):
                    continue
                if e["unless"] and re.search(e["unless"], sent, re.I):
                    continue
                hits.append((os.path.relpath(path, ROOT), ln, e["id"], sent[:110], e["correct"]))

    # Dead-pattern guard: every pattern must still match the claim it retired, or it has silently
    # stopped protecting anything. Each entry's own `correct` line is NOT the claim, so a canary is used.
    CANARY = {
        # N613 (1.14.0): E96's coverage claim, as the home page's <title> template wrote it
        "coverage-3-4-to-3-15":  "the Resilient File System on-disk format (v3.4–3.15)",
        "hl-sibling-true-birth": "a name-scoped timestomp leaves the sibling names at the true birth",
        "hl-latest-authentic":   "the latest Created among the siblings is the authentic birth",
        "hl-never-clean-sibling": "flagged on the backdated name and never on the clean sibling",
        "hl-stomp-causes-divergence": "the names disagree on Created, which a name-scoped stomp is the natural cause of",
        # E97-E100, retired 2026-09-19. Each canary is the claim AS THE PROJECT ONCE WROTE IT.
        "hole-is-vlcn-zero":       "an inline extent record with VLCN == 0 is a sparse hole, not a readable extent",
        "integrity-flag-run-one":  "each checksummed cluster is its own extent with flag 0x1C00D0 and run_length 1",
        "mlog-budget-minus-first": "remaining = total_size - first_record_offset",
        "mlog-commit-always-zero": "commit is marked at the checkpoint layer, so this is 0 on every volume, healthy or not",
        "vbr-sector-always-512":   "| 0x20 | 4 | Bytes per sector | u32 | 512 (always) |",
        # E113, retired 2026-09-23 -- each is the v1.13.0 text verbatim (changelog / RC3 evidence).
        "n94-carves-invented":     "Deleted-content recovery refuses two kinds of invented bytes.",
        "carve-cover-coincidence": "a misaligned walk whose cluster counts summed to exactly the file's allocation by coincidence, satisfying the cover guard",
        "gfsareplay-is-metadata":  "nine of the fourteen open with GFSAREPLAY, a filesystem-internal signature",
        # E123, retired 2026-10-24 -- docs/structures/mlog.md's v3.14 table row as it stood to wave C's close.
        "redo-0x12-move-container": "| 0x12 | RedoMoveContainer (shared) | Container |",
        # K080 (B4), retired 2026-10-24 -- the 1.13.1 help (fd:16329) and the timestomp page's signal table verbatim.
        "timestomp-future-tier":   "a count of heuristic signals never reaches it. MEDIUM is CHANGE_LATE without PRE_FORMAT, or FUTURE.",
        "timestomp-last-metadata-write": "| **FUTURE** | Created after the volume's last metadata write | intrinsic + volume | medium\\* |",
        # 1.14.0 RC1-docs: docs/structures/mlog.md's "Transaction structure" (I4) and
        # docs/concepts/timestomp_detection.md's snapshot cross-check (I5), verbatim as they stood to 1.13.1.
        "mlog-commit-always-zero-on-disk": "The commit flag (bit 1) is **always 0 on disk** — a commit is recorded at the checkpoint/log-core layer",
        "snapshot-backdate-below-impossible": "A creation time backdated below a snapshot of the same file is impossible.",
        # 1.14.0 RC1-docs, N408 / N440: each canary is the 1.13.1 text verbatim (tool output, or the page as it stood).
        "usn-journal-tail-destroyed": "679888 bytes of journal after the last surviving record were DESTROYED (zeroed or overwritten).",
        "usn-empty-never-written-or-wiped": "this is a journal that was never written OR one that was wiped, and the stream cannot distinguish them",
        "hole-acquisition-gap": "is not present in this image (acquisition gap, not damage)",
        "mlog-95-control-pages": "all 599,039 data records and all 95 control pages recompute exactly.",
        "timeline-correlates-sources": "The super-timeline correlates USN, MLog, and `$SI` events by identity/name and time",
        "redo-0x20-object-id": "| 0x20 | 8 | object_id (u64) | Target OID (from `ObjectIdFromRedoHelper`) |",
        "mlog-parse-each-transaction": "`forefst mlog --parse` groups the opcodes of each transaction into a single concrete action",
        "isresident-column": "Is `IsResident` still there? Yes, deprecated: it is `True` exactly when `DataResidency` is `inline`.",
        "mlog-control-field-labels": "| +0x18 | 8 | LSN oldest | Oldest active LSN |",
        # docs part 2 (2026-11-16): docs/concepts/version_evolution.md:90 and docs/structures/page_references.md:115,
        # verbatim as they stood to 1.14.0 RC1-docs (the readings E141 refuted and E158 replaced).
        "chkp-0x400-crc64": ("| CHKP flag 0x0400 | CRC64 metadata verification **activated** |",
                             # RC3 (N328): the corpus README's wording, which the first pattern let through
                             "| 3.14 (upgraded) | 0x2602 | 48 bytes | +0x200 (indirect root list), +0x400 (CRC64 metadata checksums) |"),
        # RC3 (N328; erratum E5's amendment): the 0x2C format-time reading, as the concept pages and the corpus README wrote it
        # RC3 (E166, 2026-11-21): the master's own sentence of 2026-07-05, verbatim
        # E167-E170 (RC3a, 2026-11-21): the pages and the master as they stood before the N158 / d6 corrections, verbatim
        "schema-type-plus-0x100": ("Schema ID = type code + 0x100 (for per-object attributes).",
                                   "For attribute schemas: schema ID = embedded type code + 0x100.",
                                   "The real ReFS attributes, by schema (cross-checked against the master schema roster). Type code = schema − 0x100."),
        "schema-0x1e0-is-ea": ("0x1e0=$EA; 0x1f0=$LOGGED_UTILITY_STREAM.", "| Schema 0x1E0 | `$EA` (WSL extended-attribute body) |"),
        "schema-0x1b0-snapshot": ("| Schema 0x1B0 | `$SNAPSHOT` — stream snapshot support |",
                                  "`$SNAPSHOT` / schema 0x1B0 is gated **v3.7+** (the version-gating matrix lists 0x1B0 as present from v3.7 through Insider)."),
        "schema-0x1f0-max": ("USN_RECORD_V3 (128-bit FileIDs); $Max at schema 0x1F0 |",
                             "| Schema 0x1F0 | `$LOGGED_UTILITY_STREAM` (USN `$Max` metadata) |"),
        # 1.14.1 D1 (2026-11-27, N676 / N679): E167's sweep missed the table form; the pages and the master verbatim
        "schema-attr-names": ("| 0x1B0 | $SNAPSHOT | — | Y | Y | Y | Y | Y |",
                              "| 0x200 | $EFS | — | — | — | — | Y | Y |",
                              "attaches to a file, registered as **attribute schemas**. The set grew from **12 attribute schemas** in",
                              "Stored via attribute schemas: $EA\\_INFORMATION (0x1D0) for packed/unpacked sizes; $EA (0x1E0) for EA body."),
        # E182 (1.14.1, 2026-11-27, N682): the pages as they stood (DATA.md and extent_descriptors.md as published in
        # 1.14.0; the 1.14.1 dev sentence of item W)
        "data-version-count": ("| 0x50 | 8 | Version count + sparse flag | low 31 bits = version count (1 for a single-version stream); bit 31 = a sparse flag in prior work, never observed set |",
                               "| 0x50 | 8 | Version count + sparse flag (u64) | low31 = stream version count (=1 for a single-version file, N for an N-version snapshotted file); bit 31 = sparse flag |"),
        "data-v34-flags-0x54": "| 0x54 | 8 | Version count + sparse flag | as at 0x50 from 3.7 |",
        "data-only-sparse-files": ("attribute 0x200, no extent): `+0x50` reads `0x80000001`, a version count of 1 with bit 31 set. No other sparse file is in the corpus.",
                                   "the corpus's only sparse files; clear on the 31,678 stream records of the census, which held none."),
        # U (2026-11-21, N665): the pages as they stood before the U round
        'vinfo-0x540-schema-count': ('| 0x540 | 16 bytes — schema count (u32) at +0x00, flags (u32) at +0x04, a u32 (=1, purpose unknown) at +0x08 |',
                                     # RC3b item 11: refsanalysis `summary --plus`, as 1.13.1 / RC3 printed it
                                     "print(f\"  Schema count:       {summary['schema_count_500']}\")"),
        'objlink-name-null-terminated': '| 0x5E | var | Filename | UTF-16LE, null-terminated |',
        'heat-promotes-tiers': '- hot blocks are promoted to the fast tier; cold blocks are demoted to the slow tier;',
        'driver-fn-purposes-u': ('Frees data extents and removes the file table. Runs asynchronously after checkpoint.', "1. **Analysis pass**: starts at the chosen checkpoint's log position (CHKP+0x70) and identifies dirty pages and active transactions.", '| Deactivated | Varies | May persist with zeroed extents |'),
        'imports-clustered-edition': ('| `msrpc.sys` | Kernel-mode RPC | clustered-storage communication |', 'The embedded SymCrypt library is an Insider-build addition tied to early-boot and attestation, not a v3.14 component.'),
        'recyclebin-first-deletion': '| $RECYCLE.BIN creation | Created on demand at first Explorer deletion |',
        'bkrc-0x10-low-byte-varies': '| 0x10 | 8 | Not settled (u64) | Low bytes 0xE4 and 0xF0 measured; the driver reading differs ([below](#evidence)) |',
        'upcase-387-rows-unscoped': 'On disk the table is **not** a flat 128 KiB blob — it is a **387-row B+-tree** (schema 0xe090):',
        'reparse-188-548': 'Value sizes range roughly 188–548 bytes, depending on the path-string length.',
        'wsl-mismatch-tampered': 'disagrees with the reparse tag, one of the two artifacts was tampered with or carried over incorrectly.',
        'sd-hash-tampering': 'recomputed hash indicates it was altered after write (tampering or corruption).',
        # Z (2026-11-21, N668): the pages as they stood before the Z round
        'row-flags-deleted-unconfirmed': '| 0x08 | 2 | Reserved (u16) | a candidate deleted-row bit `0x04` here is read only in the driver and **cannot be confirmed on disk** — not relied upon |',
        'dir-entry-0x44-padding': 'The two forms differ only in the padding at the end (offset 0x44).',
        'page-0x08-reserved': '| 0x08 | 4 | Reserved (u32) | Always 0 |',
        'objlink-0x0c-reserved': '| 0x08 | 4 | Parent OID | |',
        'sd-key-value-size-u32': '| 0x00 | 4 | Value size (u32) | Total value byte count (the key echoes the value length) |',
        # V (2026-11-21, N667): docs/structures/reparse_points.md as it stood
        'symlink-embedded-entry-only': 'A symlink is an embedded-record entry carrying attributes `0x420` for a file link or `0x10000400` for a directory link,',
        # V (2026-11-21, N666): docs/structures/page_header.md as it stood
        'page-clocks-allocator-pertable': ('| 0x10 | 8 | Virtual allocator clock (u64) | Increments for CHKP/MSB+; on a SUPB copy, the checkpoint clock when that copy was written ([below](#superblock-clocks-0x10-and-0x18)) |',
                                           "| 0x18 | 8 | Tree update clock (u64) | Last modification clock for this page's table; on a SUPB copy, the value when that copy was written |"),
        # U03 (2026-11-21, N665): docs/concepts/hard_links.md as it stood
        "si70-pdb-name": "The field at [`$SI`](../attributes/STANDARD_INFORMATION.md) offset 0x70 — whose PDB name *is* \"HardLinkCount\" — behaves differently in the two record forms:",
        "si-0x38-pdb-name": ("0 in a directory's own row. The PDB label (`LastMftChangeTime`) notwithstanding, it is not a timestamp",
                             'PDB names it "LastMftChangeTime" but it is not a timestamp.'),
        "record-structural-metadata": ("| 0x08 | 32 | Structural metadata | Stream index (8 B) + internal B+-tree management fields (24 B) |",),
        "type-0x50-volinfo": ("| 0x50 | [`$VOLUME_INFORMATION`](../attributes/VOLUME_INFORMATION.md) | the volume information, in the system table at OID 0x500 / 0x501, never a per-file row |",
                              "Schema 0x150 / type 0x50, the OID 0x500/0x501 storage, and the blob layout are read in the decompiled driver"),
        "type-0x60-reparse-index": ("| 0x60 | the reparse-point index | the system table at OID 0x540 / 0x541 |",
                                    "Type 0x60 is never an embedded sub-record of an object's record: its rows are those of a system table."),
        "oid530-no-schema": ("OID 0x530 is a **stream-type table without a schema** — unlike most other ReFS tables it does not use a schema-typed B+-tree.",
                             "| 0x530 | Security Descriptors | — | SID/ACL data (stream-type, no schema) |"),
        "chkp-area-not-decoded": ("0 when there is no area. Its content is not decoded |",),
        "vbr-0x04-not-decoded": ("| 2 | 0x04 | Meaning not decoded. Set on every volume measured whose flags were not edited by hand | v3.4 |",),
        # E171 (RC3a, 2026-11-21): the timestomp page and the register as they stood, verbatim; E167's mlog.md residue
        "mlog-no-stomp-record": ("The log does not record the stomp; the evidence is the file's **creation**",
                                 "A backdated $SI write leaves NO MLog transaction of its own -- the log records the file's creating transaction"),
        "schema-0x130-file-name": ("| 0x04 | 4 | schema1 (u32) — attribute schema (e.g. 0x0130 = $FILE_NAME) |",
                                   "Common pairs: 0xe030/0x0130 (ObjectTable/$FILE_NAME), 0xe030/0x0160 (ObjectTable/ReparseIndex)."),
        "log-no-prior-values": ("Prior state therefore comes from [snapshots](../attributes/SNAPSHOT.md) and superseded CoW pages, never from log undo.",
                                "so do not look in the log for prior values",
                                "redo-only logging carries no pre-images, so it is not a direct prior-state source"),
        "mlog-cannot-give-content": ("This is why the MLog cannot give you the previous content of a modified file the way the NTFS",
                                     "Redo-only means the MLog carries **no pre-images**, so it cannot hand you the previous content of a modified file."),
        # E172 / E173 (RC3a, 2026-11-21): the pages and the master as they stood before N655, verbatim
        "ot-key-8-bytes": ("The Object Table (schema 0xe030) is the master OID-to-table map: an 8-byte key (the OID at offset 0x00)",
                           "of what they manage is the [Object Table](../structures/object_table.md), whose 8-byte key *is* the OID.",
                           "- [Object Table](../structures/object_table.md) — the B+-tree whose 8-byte key is the OID"),
        "oid-mount-not-traced": ("- How the counter is restored at mount is not settled. The driver has a `_CmsKey::RightMost` key used with",
                                 "**At mount — not traced.** How the counter is restored at mount is not read in the driver",
                                 "That a failed creation leaves a gap is read in the driver (26100.9444), not measured, and how the counter is restored at mount is not traced."),
        "oid-never-reused-unscoped": ("OIDs are **64-bit, monotonically increasing, and never reused after deletion** — this no-reuse property is",
                                      "  - An object has a **64-bit Object ID that is monotonic and never reused**: the closest thing ReFS has to an inode.",
                                      "- [Object IDs](object_ids.md) — step 4: OID 0x701 boundary and the never-reused rule",
                                      "- the [Object-ID space](../structures/system_oids.md) (64-bit OIDs, never reused).",
                                      "OID gaps are deletion evidence that lasts: OIDs are monotonically increasing and **never reused**, and only"),
        # E174 (RC3a, 2026-11-21): the pages as they stood before N656, verbatim (the name "Session Activity Table" joins in
        # RC3b, when the tools' labels change)
        "heat-0x30-mount-session": ("| 0x30 | Session Activity Table | 0xe130 | v3.10+ only; mount session forensics |",
                                    # RC3b item 5: the tools' labels, verbatim
                                    '0x30: ("SessionActivity", "Session Activity Table"),',
                                    '("oid30",       "OID 0x30 session activity analysis",',
                                    '"oid30": {"tag": "OID 0x30 session-activity analysis",',
                                    # tiering.md as it stood to 2026-11-21 (N664)
                                    "no volume measured uses tiered storage, and the engine's heat table is empty on every test volume.",
                                    "Present from v3.10 onwards, and created when an older volume is upgraded. It is a B+-tree of per-mount-session",
                                    "- The Session Activity Table (0x30) provides mount session history.",
                                    "  registered in the Schema Table, and with 0 rows on every test volume.",
                                    "on-disk `0xe130` heat rows (the persistence table exists but carries no rows on every test volume measured, none of"),
        # E175 (RC3a, 2026-11-21): reverse_index.md and the master as they stood before N658, verbatim
        # E181 amended (RC3a Y / RC3b item 14): the tool's Method 5 header and the pages, verbatim
        "del-only-slot": ("  (ReFS deletion removes only the row's index slot; the row body persists).",
                          "ReFS deletion (`CmsBPlusTable::DeleteFromIndex`) removes only the deleted row's entry in the page's **offset array** and queues *delayed* compaction",
                          "deleting a name row removes only its slot in the page's offset array, and its bytes",
                          "(`CmsBPlusTable::DeleteFromIndex`) removes only the row's slot in the offset array"),
        # MD_TS_RA_010 (RC3b): the copy explanation of PRE_FORMAT + CHANGE_LATE, verbatim (tool comment, page, legend)
        "copy-change-time-now": ("original values -- before this volume existed -- and the change time to the copy moment.",
                                 "writes the original create/modify, which predate this volume when the source does (`PRE_FORMAT`), and sets the change time to the moment of the copy (`CHANGE_LATE`).",
                                 "writes the original create/modify — before this volume existed, so `PRE_FORMAT` — and sets the change time to the moment of the copy, so `CHANGE_LATE`."),
        # E170 amended (RC3b D2): the master's and chkp.md's sentences, verbatim
        "usn-cursor-after-checkpoint": ("volumes the journal holds records written after the last checkpoint (at or past NextUsn).",
                                        "on 6 volumes the journal holds 2,353 to 43,734 records at or past the Next USN;"),
        "ri-coverage-old": ("record, Format B for a type-0x40 backing), so the additional *names* of a multi-name file have none of their own. Files whose record is embedded in its name row — identified by the sentinel at child_oid (val+0x08), at or above 0x10000000000 — typically lack type 0x20 entries.",
                            "On every directory measured, the type 0x20 count is <= the type 0x30 child count.",
                            "| 0x0A | 2 | Name byte length (u16) | UTF-16LE length including null terminator |",
                            "  (FileId + home-dir OID) — created for subdirectories and cross-directory links.",
                            "- **Format A (`type_flag = 0`):** the child's **filename** (`name_off@0x08`, `name_len@0x0A`, then UTF-16LE) — created for non-resident child names."),
        # E176 (RC3a, 2026-11-21): integrity_state.md as it stood before N660, verbatim
        "ist-state-config": ("| 0x10 | 4 | State (u32) | default 0x0002ffff on quiescent single-row images |",
                             "| 0x14 | 4 | Config (u32) | default 0x00000100 on quiescent single-row images |",
                             "mechanism. The `State` value 0x0002ffff likely represents the \"default/clean\" state."),
        "chkp-0x94-by-cluster": ("`CHKP+0x94` is an in-page offset (0xA8 on 4K, 0xB0 on 64K — always << page size) to a "
                                 "root-list region within the same checkpoint record",),
        "vbr-0x2c-format-time": ("The VBR format-time fields (0x2A, 0x2C, 0x48) are never modified during an upgrade",
                                 "Volume flags (offset 0x2C) — format-time capability bits."),
        # E164 (N180, 2026-11-20): FN_LINK_004's and FN_LINK_002's static notes, verbatim as the register stood before 2026-11-20
        "linkself-copies-identity": ("RefsLinkFileToSelf copies the (home,ordinal) identity into each name and adds a type-0x39 back-pointer, allocating no new stream.",
                                     "RefsLinkFileToSelf/RefsAddLink copy the home pair under tag 0x80000040."),
        "chkp-0x400-meaning-not-read": "| CHKP flags bit 0x400 | Not set | Set (its meaning in the driver is not read) |",
        # Decision 65 (2026-11-17): docs/methodology.md:12 and website/pages/verification.md:8-9, verbatim as they
        # stood to 1.14.0 RC1 (N123), and verification.md:86-87 (N591).
        "method-every-claim-both-sources": "A structural claim is accepted only when **two independent sources agree**: the **decompiled driver code**",
        # two wordings the pages carried (N591's, and methodology.md section 10's, found 2026-11-18): each must match
        "method-no-claim-single-image": ("Where neither the code nor the disk could settle a question, it is left as an open question rather than asserted — and no claim rests on a single image.",
                                         "Where neither axis could settle a question it is recorded as an open question, not asserted. No claim here depends on a single image."),
        # E161 (N595, 2026-11-18): docs/concepts/hard_links.md:184 and :72-74 and concepts/file_systems.md:126, verbatim
        # as they stood to 1.14.0 RC1 (the docs step of E161 had corrected the attribute page only).
        "si70-link-count-decoy": "- **The `$SI+0x70` field is a decoy.** It is present only in embedded (key flags `0x01`) values and is always 1 across the entire corpus",
        "si70-no-count-on-disk": ("ReFS also takes an unusual implementation route: it stores **no explicit hard-link count on disk**, so the link relationship has to be *reconstructed*",
                                  # N604 (2026-11-18): five more wordings, verbatim as they stood to 1.14.0 RC1
                                  "fields by hand, because ReFS stores **no explicit hard-link count anywhere**.",
                                  "cannot serve as a hard-link counter — it never exceeds 1, because resident files cannot be hard-linked",
                                  "**`$SI + 0x70` is not a hard-link counter.** It is a resident-layout field that is always 0 or 1",
                                  "- [Hard Links](hard_links.md) — the multi-name graph, reconstructed without a count field",
                                  "## Why ReFS has no link counter",
                                  "and the absence of a flat metadata table or an on-disk hard-link count"),
        # E162 / E163 (2026-11-18): the readings as the master, E74 and the tools wrote them
        "alloc-tail-no-tier": ("The physical tail beyond the last container belongs to no tier: exactly 48 MiB on 90/95 images",
                               "Capacity covers the container-mapped space. The tail of the volume past the last container belongs to no tier and is reported separately"),
        "redo-table-empty-at-block-start": "after RedoTableSetCommitMerge (0x24), and at a redo block's start (26100.8115 / .9818)",
        # H2 (2026-11-18): the 1.13.1 timestomp text, verbatim
        "ts-last-real-write": "Conf   Basis         Claimed birth         Last real write       Path",
        "ts-round-low-only": "ROUND_TIMESTAMPS       created AND modified are whole-second (.0000000) — a tool often sets a date with no sub-second time; LOW only (driver packages / archive extraction also produce whole-second times)",
        # N602 (2026-11-18): concepts/file_systems.md:165-166, :170-171 and concepts/checksum_architecture.md:5-9,
        # verbatim (hard wraps joined) as they stood to 1.14.0 RC1 (E141's docs step had left them)
        "chk-v34-no-metadata-checksum": ("CRC64 by default on v3.14; *off* on original v3.4 volumes, which format with no metadata checksums",
                                         "on older volumes they are written but never checked, so the same byte that the driver would reject on a v3.14 volume mounts silently on a v3.4 one"),
        # N604 (2026-11-18): concepts/version_evolution.md:6, :24, :76-77, :81, :271, version_detection.md:149,
        # file_systems.md:213 and checksum_architecture.md:99, verbatim as they stood to 1.14.0 RC1
        "chk-crc64-enforced-314": ("Microsoft changed the size of a [page reference](../structures/page_references.md), switched on metadata checksums, added and retired",
                                   "| 3.14 | Win11 24H2 | 2024 | CRC64 verification active, indirect root list |",
                                   "Declaring CRC64 here (0x2A = 0x02) does not yet mean the checksums are *verified*; that happens at v3.14.",
                                   "CRC64 verification becomes active, and the checkpoint can store its root list indirectly rather than inline.",
                                   "- [Checksum Architecture](checksum_architecture.md) — CRC64 declared at v3.10, enforced at v3.14",
                                   "why CRC64 is declared at v3.10 but only enforced at v3.14, and how upgraded volumes activate it at runtime",
                                   "metadata checksummed by default on current versions (but never on original v3.4)",
                                   "applied to every B+-tree page when CRC64 verification is active.",
                                   "| VBR checksum algorithm (0x2A) | 0x0000 (no CRC64) |",
                                   "These are written once, at format time, and are **never** touched by an upgrade."),
        "hardlinks-native-314-only": "reparse points from the earliest version with hard links gated to native v3.14",
        # N605 (2026-11-18): concepts/ntfs_comparison.md:18, :30, :98-100, :239-242, verbatim as they stood to 1.14.0 RC1
        "usn-ref-parent-oid": ("| Change journal | `USN_RECORD_V2` (64-bit file ID) | `USN_RECORD_V3` (128-bit: parent OID + entry index) |",
                               "128-bit references: the upper 8 bytes are the **parent directory's Object Table OID** and the lower 8",
                               "The same monotonic counter underlies the [USN](../structures/usn_journal.md) 128-bit file IDs.",
                               "| File identification | MFT record number (reusable) | Object ID (64-bit, monotonic, never reused) |"),
        "chk-proves-genuine": ("a recomputable checksum proves a *metadata* page is genuine",
                               "a checksum you can recompute is a way to *prove* a metadata page is the original on-disk content"),
    }
    dead = []
    for e in spec:
        c = CANARY.get(e["id"])
        if c is None:
            dead.append("%s has no canary: the gate cannot prove the pattern still matches" % e["id"])
            continue
        for one in (c if isinstance(c, tuple) else (c,)):       # a claim the pages carried in several wordings
            if not re.search(e["pattern"], one, re.I):
                dead.append("%s no longer matches its own canary: %r" % (e["id"], one))
    if dead:
        print("retired claims: FAIL - %d dead pattern(s)" % len(dead))
        for d in dead:
            print("   - %s" % d)
        return 1

    if unreadable:
        print("retired claims: FAIL - %d file(s) could not be read, so they were not checked"
              % len(unreadable))
        for u in unreadable:
            print("   - %s" % u)
        return 1

    if hits:
        print("retired claims: FAIL - %d occurrence(s) of a retracted claim in %d file(s) scanned"
              % (len(hits), scanned))
        for f, ln, cid, sent, correct in hits[:20]:
            print("   %s:%d  [%s]" % (f, ln, cid))
            print("      %s" % sent)
            print("      say instead: %s" % correct)
        return 1
    print("retired claims: PASS - %d claim(s) checked over %d file(s); none reappeared, all patterns live"
          % (len(spec), scanned))
    return 0


if __name__ == "__main__":
    sys.exit(main())
