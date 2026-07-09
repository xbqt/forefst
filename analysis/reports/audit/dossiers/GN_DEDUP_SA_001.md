# Dossier — GN_DEDUP_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Win11 native dedup: 7 new functions (MsIsDedupEnabled, MsDisableDedup, RefsQueryVolumeDedupInfo). CmsBlockRefcount grows 23->27 funcs

**Canonical claim (reference_table.csv):** General: Win11 native dedup: 7 new functions (MsIsDedupEnabled, MsDisableDedup, RefsQueryVolumeDedupInfo). CmsBlockRefcount grows 23->27 funcs

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** INFERRED · **Evidence:** E2 (win11+)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/MsIsDedupEnabled__decomp.txt
- Static driver evidence: MsIsDedupEnabled. Win11 native dedup: 7 new functions (MsIsDedupEnabled, MsDisableDedup, RefsQueryVolumeDedupInfo). CmsBlockRefc. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_DEDUP_SA_001.csv`
- corrected registry note: NORMALIZED 2026-06-19 (was NOT_CONFIRMED: static function-count evidence, no disk-visible structural effect): Dedup-enabled image (win11refs8gdedup) shows no structural difference; refsutil dedup returns 'not supported'

## Proof links
- `proofs/static/MsIsDedupEnabled__decomp.txt` (static) — MsIsDedupEnabled
- `proofs/validation/GN_DEDUP_SA_001.csv` (matrix) — 
