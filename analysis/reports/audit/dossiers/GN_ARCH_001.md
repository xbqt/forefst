# Dossier — GN_ARCH_001 (BEHAVIORAL)

**Claim (this audit tests):** ReFS uses Minstore B+ tree storage engine

**Canonical claim (reference_table.csv):** General: ReFS uses Minstore B+ tree storage engine

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/CmsBPlusTable__decomp.txt
- Static driver evidence: CmsBPlusTable. ReFS uses Minstore B+ tree storage engine. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_ARCH_001.csv`
- corrected registry note: All 39 images show MSB+ signature on every metadata page; B+-tree walking confirmed across all table types

## Proof links
- `proofs/static/CmsBPlusTable__decomp.txt` (static) — CmsBPlusTable
- `proofs/validation/GN_ARCH_001.csv` (matrix) — 
