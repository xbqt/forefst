# Dossier — FS_SUPB_004 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x70-0x74: offset to checkpoint references

**Canonical claim (reference_table.csv):** File System: 0x70-0x74: offset to checkpoint references

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SUPB+0x70 (u32) == 0xC0 on 48/48 (offset to checkpoint refs).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_supb__forefst.txt
- structure_reference.md:125 SUPB 0x70, u32, typically 0xC0 (192). Read from SUPB@LCN 0x1E. Byte-verified.

## Raw-disk proof
- probe `supb_int` ; validation matrix: `proofs/validation/FS_SUPB_004.csv`
- corrected registry note: Offset consistently at 0x70; points to checkpoint reference array

## Proof links
- `proofs/static/parse_supb__forefst.txt` (static) — parse_supb
- `proofs/validation/FS_SUPB_004.csv` (matrix) — 
