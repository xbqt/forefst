# Dossier — GN_ALLC_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Win11 allocator unification: CmsAllocatorBase(42)+CmsGlobalAllocator(43) -> CmsAllocator(106). Allocation zones: 9->13

**Canonical claim (reference_table.csv):** General: Win11 allocator unification: CmsAllocatorBase(42)+CmsGlobalAllocator(43) -> CmsAllocator(106). Allocation zones: 9->13

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2 (win11+)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsAllocatorBase. Win11 allocator unification: CmsAllocatorBase(42)+CmsGlobalAllocator(43) -> CmsAllocator(106). Allocation zone. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_ALLC_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_ALLC_SA_001.csv` (matrix) — 
