# Dossier — GN_IENT_005 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x0A-0x0C: value offset

**Canonical claim (reference_table.csv):** General: 0x0A-0x0C: value offset

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — value_offset (u16@0x0A): in-bounds (row+val_off+val_len <= page; val_off>=16) on 100% of rows across all tested images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Index entry value_offset@0x0A (verified val within entry).

## Raw-disk proof
- probe `index_node` ; validation matrix: `proofs/validation/GN_IENT_005.csv`
- corrected registry note: Value offset at position 4; used for value extraction in all tools

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/GN_IENT_005.csv` (matrix) — 
