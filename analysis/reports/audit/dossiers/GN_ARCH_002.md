# Dossier — GN_ARCH_002 (BEHAVIORAL)

**Claim (this audit tests):** Copy-on-Write / Allocate-on-Write update policy

**Canonical claim (reference_table.csv):** General: Copy-on-Write / Allocate-on-Write update policy

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/MsUpdateDataWithRoot__decomp.txt
- Static driver evidence: MsUpdateDataWithRoot. Copy-on-Write / Allocate-on-Write update policy. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_ARCH_002.csv`
- corrected registry note: Virtual clock increments at each checkpoint confirm CoW model; old pages visible in log data area scans

## Proof links
- `proofs/static/MsUpdateDataWithRoot__decomp.txt` (static) — MsUpdateDataWithRoot
- `proofs/validation/GN_ARCH_002.csv` (matrix) — 
