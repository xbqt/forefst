# Dossier — GN_IDXH_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x00-0x04: offset to data area start

**Canonical claim (reference_table.csv):** General: 0x00-0x04: offset to data area start

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED**

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Index/node header data-area-offset@0x00. Verified sane on the OT-root node.

## Raw-disk proof
- probe `index_node` ; validation matrix: `proofs/validation/GN_IDXH_001.csv`
- corrected registry note: B+-tree walker reads data area offset from page header+0x50; confirmed working on all images

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/GN_IDXH_001.csv` (matrix) — 
