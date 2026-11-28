# Dossier — GN_CROT_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Win11 container rotation for flash wear leveling: CmsVolumeContainer 72->130 funcs (+81%); RotateContainers, PersistCompactionExtentsNoAbort

**Canonical claim (reference_table.csv):** General: Win11 container rotation for flash wear leveling: CmsVolumeContainer 72->130 funcs (+81%); RotateContainers, PersistCompactionExtentsNoAbort

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2 (win11+)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/CmsVolumeContainer__decomp.txt
- Static driver evidence: CmsVolumeContainer. Win11 container rotation for flash wear leveling: CmsVolumeContainer 72->130 funcs (+81%); RotateContainers, P. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_CROT_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/static/CmsVolumeContainer__decomp.txt` (static) — CmsVolumeContainer
- `proofs/validation/GN_CROT_SA_001.csv` (matrix) — 
