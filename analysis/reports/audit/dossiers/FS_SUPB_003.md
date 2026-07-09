# Dossier — FS_SUPB_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x68-0x70: superblock version/recency

**Canonical claim (reference_table.csv):** File System: 0x68-0x70: superblock version/recency

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SUPB+0x68 (u64) == 1 on 48/48 images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_supb__forefst.txt
- structure_reference.md:124 SUPB 0x68, u64, always 1. Read from the SUPB at LCN 0x1E (supb_int) — NOT the VBR. Byte-verified on v3.4+v3.14.

## Raw-disk proof
- probe `supb_int` ; validation matrix: `proofs/validation/FS_SUPB_003.csv`
- corrected registry note: Version field always reads 1 across all images (both 3.4 and 3.14)

## Proof links
- `proofs/static/parse_supb__forefst.txt` (static) — parse_supb
- `proofs/validation/FS_SUPB_003.csv` (matrix) — 
