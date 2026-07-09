# Dossier — FS_SUPB_001 (STRUCTURAL)

**Claim (this audit tests):** Located at cluster 0x1E (30)

**Canonical claim (reference_table.csv):** File System: Located at cluster 0x1E (30)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SUPB signature present at cluster 0x1E (30) on 48/48 unique ReFS images (all versions/cluster/cksum). parse_supb reads it there and bootstrap succeeds.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_supb__forefst.txt
- structure_reference.md:117 SUPB at LCN 0x1E. supb_int reads LCN 0x1E and asserts the 4-byte signature == 'SUPB' (le32=1112560979). Byte-verified.

## Raw-disk proof
- probe `supb_int` ; validation matrix: `proofs/validation/FS_SUPB_001.csv`
- corrected registry note: SUPB found at partition_start + 30*cluster_size in all 39 images

## Proof links
- `proofs/static/parse_supb__forefst.txt` (static) — parse_supb
- `proofs/validation/FS_SUPB_001.csv` (matrix) — 
