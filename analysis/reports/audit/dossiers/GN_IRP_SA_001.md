# Dossier — GN_IRP_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Three-tier IRP dispatch: RefsFsd* (exception frame) -> RefsCommon* (logic) -> Cms* (storage). 13 dedicated + 5 dispatched = 18 handlers (Win10); 13+7=20 (Win11)

**Canonical claim (reference_table.csv):** General: Three-tier IRP dispatch: RefsFsd* (exception frame) -> RefsCommon* (logic) -> Cms* (storage). 13 dedicated + 5 dispatched = 18 handlers (Win10); 13+7=20 (Win11)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsFsd__decomp.txt
- Static driver evidence: RefsFsd. Three-tier IRP dispatch: RefsFsd* (exception frame) -> RefsCommon* (logic) -> Cms* (storage). 13 dedicated + 5. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_IRP_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/static/RefsFsd__decomp.txt` (static) — RefsFsd
- `proofs/validation/GN_IRP_SA_001.csv` (matrix) — 
