# Dossier — FS_OTBL_SA_004 (BEHAVIORAL)

**Claim (this audit tests):** MsSetMinimumNewObjectId: format-time initialization that HARDCODES 0x700 as minimum user OID. Called during volume format. Boundary between system OIDs (0x01-0x6FF) and user OIDs (0x700+). 166 bytes (Insider).

**Canonical claim (reference_table.csv):** File System: MsSetMinimumNewObjectId: format-time initialization that HARDCODES 0x700 as minimum user OID. Called during volume format. Boundary between system OIDs (0x01-0x6FF) and user OIDs (0x700+). 166 bytes (Insider).

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/MsSetMinimumNewObjectId__decomp.txt
- Static driver evidence: MsSetMinimumNewObjectId sets the minimum new object id at format time (user OIDs start 0x701). No disk-field obligation; proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_SA_004.csv`
- corrected registry note: See ObjectIdLifecycle.md

## Proof links
- `proofs/static/MsSetMinimumNewObjectId__decomp.txt` (static) — MsSetMinimumNewObjectId
- `proofs/validation/FS_OTBL_SA_004.csv` (matrix) — 
