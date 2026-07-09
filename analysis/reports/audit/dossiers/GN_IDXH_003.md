# Dossier — GN_IDXH_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x0D-0x0E: flags (0x1 inner, 0x2 root, 0x4 stream)

**Canonical claim (reference_table.csv):** General: 0x0D-0x0E: flags (0x1 inner, 0x2 root, 0x4 stream)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED**

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Index/node header flags@0x0D (0x1 inner/0x2 root/0x4 stream). Verified flags use only those bits.

## Raw-disk proof
- probe `index_node` ; validation matrix: `proofs/validation/GN_IDXH_003.csv`
- corrected registry note: Inner node flag (0x100 in our encoding at trailer[3]) distinguishes internal from leaf nodes; confirmed by B+-tree walking

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/GN_IDXH_003.csv` (matrix) — 
