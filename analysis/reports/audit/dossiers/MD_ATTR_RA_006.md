# Dossier — MD_ATTR_RA_006 (STRUCTURAL)

**Claim (this audit tests):** Type 0x10 value contains embedded B+-tree with $OBJ_LINK (0x39/0x38) + $I30_INDEX (0x90) sub-records. 99.4% have exactly 2 rows. 0.3% have 3 (adds $REPARSE). <0.01% have 4 (adds $EA).

**Canonical claim (reference_table.csv):** Metadata: Type 0x10 value contains embedded B+-tree with $OBJ_LINK (0x39/0x38) + $I30_INDEX (0x90) sub-records. 99.4% have exactly 2 rows. 0.3% have 3 (adds $REPARSE). <0.01% have 4 (adds $EA).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Type-0x10 embedded mini-tree row count over 32605 OIDs: 2 rows=32514 (99.72%), 3 rows=86 (0.26%, adds 0xC0 $REPARSE), 4 rows=5 (0.015%, adds 0xD0+0xE0 $EA). $OBJ_LINK(0x38/0x39) present in 32605/32605, $I30(0x90) present in 32605/32605. The 3-row case adds 0xC0; the 4-row case adds {0xD0,0xE0}.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Embedded B+-tree in $SI value (parse_resident_btree_rows descends it). Structural; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_006.csv`
- corrected registry note: 110 images / 32721 entries: 32510 have 2 rows (99.4%), 121 have 1 row, 86 have 3 rows, 4 have 4 rows.

## Proof links
- `proofs/validation/MD_ATTR_RA_006.csv` (matrix) — 
