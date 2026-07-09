# Dossier — GN_PAGE_005 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x18-0x20: tree update clock

**Canonical claim (reference_table.csv):** General: 0x18-0x20: tree update clock

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — page+0x18-0x20 (tree update clock): second 8-byte counter present, distinct from 0x10, non-zero on majority of MSB+ pages. Confirmed on all images as a populated u64 field.

**Original audit verdict:** INFERRED (disk held 112/112 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- structure_reference.md:105 page header 0x18 = tree update clock (last-mod clock for this page's table). Byte-verified tree(0x18) <= valloc(0x10) on the OT-root page (tree can be 0).

## Raw-disk proof
- probe `page_consistency` ; validation matrix: `proofs/validation/GN_PAGE_005.csv`
- corrected registry note: 8-byte per-tree modification counter. Non-zero in 82% of pages (343/420 in 4GB image). Distinct from VA clock at 0x10 | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Field at 0x18 confirmed on disk; 'tree update clock' label is E2/inference. Offset CONFIRMED, semantic INFERRED.

## Proof links
- `proofs/validation/GN_PAGE_005.csv` (matrix) — 
