# Dossier — FS_OTBL_SA_006 (BEHAVIORAL)

**Claim (this audit tests):** MsInitializeWellKnownObjectId: trivial 12-byte helper constructing 128-bit SmsBigIdentifier from a 64-bit well-known OID value (e.g. 0x600=root dir, 0x500=volume info). Sets upper 8 bytes to 0.

**Canonical claim (reference_table.csv):** File System: MsInitializeWellKnownObjectId: trivial 12-byte helper constructing 128-bit SmsBigIdentifier from a 64-bit well-known OID value (e.g. 0x600=root dir, 0x500=volume info). Sets upper 8 bytes to 0.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/MsInitializeWellKnownObjectId__decomp.txt
- Static driver evidence: trivial helper that initializes well-known object ids. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_SA_006.csv`
- corrected registry note: See ObjectIdLifecycle.md

## Proof links
- `proofs/static/MsInitializeWellKnownObjectId__decomp.txt` (static) — MsInitializeWellKnownObjectId
- `proofs/validation/FS_OTBL_SA_006.csv` (matrix) — 
