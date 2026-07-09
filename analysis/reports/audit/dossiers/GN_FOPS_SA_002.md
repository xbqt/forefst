# Dossier — GN_FOPS_SA_002 (BEHAVIORAL)

**Claim (this audit tests):** File create chain: RefsFsdCreate->RefsCommonCreate->RefsCreateFcb(1049B)->RefsInitializeFcbAndStdInfo->RefsSetStandardInfo->MsUpdateDataWithRoot->checkpoint

**Canonical claim (reference_table.csv):** General: File create chain: RefsFsdCreate->RefsCommonCreate->RefsCreateFcb(1049B)->RefsInitializeFcbAndStdInfo->RefsSetStandardInfo->MsUpdateDataWithRoot->checkpoint

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsFsdCreate__decomp.txt
- Static driver evidence: RefsFsdCreate. File create chain: RefsFsdCreate->RefsCommonCreate->RefsCreateFcb(1049B)->RefsInitializeFcbAndStdInfo->RefsSet. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_FOPS_SA_002.csv`
- corrected registry note: (none)

## Proof links
- `proofs/static/RefsFsdCreate__decomp.txt` (static) — RefsFsdCreate
- `proofs/validation/GN_FOPS_SA_002.csv` (matrix) — 
