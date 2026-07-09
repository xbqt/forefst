# Dossier — GN_AMGR_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Win11 RefsAttributeManager class: centralized attribute CRUD (LookupAttribute, CreateAttribute, DeleteAttribute). Win10 was purely procedural

**Canonical claim (reference_table.csv):** General: Win11 RefsAttributeManager class: centralized attribute CRUD (LookupAttribute, CreateAttribute, DeleteAttribute). Win10 was purely procedural

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: RefsAttributeManager. Win11 RefsAttributeManager class: centralized attribute CRUD (LookupAttribute, CreateAttribute, DeleteAttribut. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_AMGR_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_AMGR_SA_001.csv` (matrix) — 
