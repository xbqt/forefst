# Dossier — GN_ARCH_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Two-layer namespace separation: Refs* (1248 funcs) vs Cms*/Ms* (871 core funcs) in Win10; Refs* (1084) vs Cms*/Ms* (552 core classes) in Win11

**Canonical claim (reference_table.csv):** General: Two-layer namespace separation: Refs* (1248 funcs) vs Cms*/Ms* (871 core funcs) in Win10; Refs* (1084) vs Cms*/Ms* (552 core classes) in Win11

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/Refs__decomp.txt
- Static driver evidence: Refs. Two-layer namespace separation: Refs* (1248 funcs) vs Cms*/Ms* (871 core funcs) in Win10; Refs* (1084) vs Cms*. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_ARCH_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/static/Refs__decomp.txt` (static) — Refs
- `proofs/validation/GN_ARCH_SA_001.csv` (matrix) — 
