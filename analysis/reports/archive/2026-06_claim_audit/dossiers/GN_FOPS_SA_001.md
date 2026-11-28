# Dossier — GN_FOPS_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** RefsCommonCleanup: LARGEST function (65050B Win10 / 61441B Win11). Handles IRP_MJ_CLEANUP (last handle close). If file marked for deletion performs actual removal via B+-tree row deletion.

**Canonical claim (reference_table.csv):** General: RefsCommonCleanup: LARGEST function (65050B Win10 / 61441B Win11). Handles IRP_MJ_CLEANUP (last handle close). If file marked for deletion performs actual removal via B+-tree row deletion.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsCommonCleanup__decomp.txt
- Static driver evidence: RefsCommonCleanup. RefsCommonCleanup: LARGEST function (65050B Win10 / 61441B Win11). Handles IRP_MJ_CLEANUP (last handle close).. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_FOPS_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/static/RefsCommonCleanup__decomp.txt` (static) — RefsCommonCleanup
- `proofs/validation/GN_FOPS_SA_001.csv` (matrix) — 
