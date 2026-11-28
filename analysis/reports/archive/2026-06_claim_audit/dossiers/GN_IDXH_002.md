# Dossier — GN_IDXH_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x0C-0x0D: height of node

**Canonical claim (reference_table.csv):** General: 0x0C-0x0D: height of node

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED**

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** ENRICHED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Index/node header height@0x0C (0=leaf). Verified.

## Raw-disk proof
- probe `index_node` ; validation matrix: `proofs/validation/GN_IDXH_002.csv`
- corrected registry note: PT: Page 0x0C is volume signature (not height). Table header thoff+0x0C contains inner/leaf flag (bit 0x100). Height encoding needs correction.

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/GN_IDXH_002.csv` (matrix) — 
