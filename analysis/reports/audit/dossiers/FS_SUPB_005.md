# Dossier — FS_SUPB_005 (STRUCTURAL)

**Claim (this audit tests):** 0x74-0x78: number of checkpoint refs (typically 2)

**Canonical claim (reference_table.csv):** File System: 0x74-0x78: number of checkpoint refs (typically 2)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SUPB+0x74 (u32) == 2 on 48/48 (checkpoint-ref count).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_supb__forefst.txt
- structure_reference.md:126 SUPB 0x74, u32, always 2 (two alternating checkpoints). Read from SUPB@LCN 0x1E. Byte-verified.

## Raw-disk proof
- probe `supb_int` ; validation matrix: `proofs/validation/FS_SUPB_005.csv`
- corrected registry note: Always 2 checkpoint references in all 39 images

## Proof links
- `proofs/static/parse_supb__forefst.txt` (static) — parse_supb
- `proofs/validation/FS_SUPB_005.csv` (matrix) — 
