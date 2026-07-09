# Dossier — FN_DTBL_002 (STRUCTURAL)

**Claim (this audit tests):** File row: type 0x00010030 + filename

**Canonical claim (reference_table.csv):** File Name: File row: type 0x00010030 + filename

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — type-0x30 filename entries: key[0:2]==0x0030 on 525,178/525,178 rows; filename at key+0x04 decodes as UTF-16LE on 525,178/525,178; all 111 images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** ENRICHED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- 0x30 directory-entry keys with key_flags=0x0001 are file rows. Byte-verified present.

## Raw-disk proof
- probe `dirkey` ; validation matrix: `proofs/validation/FN_DTBL_002.csv`
- corrected registry note: Exact type encoding not yet verified at this level of detail

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/FN_DTBL_002.csv` (matrix) — 
