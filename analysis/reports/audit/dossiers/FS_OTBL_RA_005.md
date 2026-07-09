# Dossier — FS_OTBL_RA_005 (BEHAVIORAL)

**Claim (this audit tests):** OIDs 0x540/0x541 = Reparse Point Index (primary/failover). Created by InitializeReparseIndexTable using MsCreateDurableFailoverTableObject with schema 0x160. References REFS_REPARSE_INDEX_FILE_NAME. Indexes reparse points by tag+OID for efficient enumeration.

**Canonical claim (reference_table.csv):** File System: OIDs 0x540/0x541 = Reparse Point Index (primary/failover). Created by InitializeReparseIndexTable using MsCreateDurableFailoverTableObject with schema 0x160. References REFS_REPARSE_INDEX_FILE_NAME. Indexes reparse points by tag+OID for efficient enumeration.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OID 0x540 present 113/113 and OID 0x541 (failover/duplicate) present 113/113.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/MsInitializeWellKnownObjectId__decomp.txt
- Static driver evidence: MsInitializeWellKnownObjectId. OIDs 0x540/0x541 = Reparse Point Index (primary/failover). Created by InitializeReparseIndexTable using MsCrea. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_RA_005.csv`
- corrected registry note: OIDs 0x540/0x541 present on all 48 images. Follows same failover pair pattern

## Proof links
- `proofs/static/MsInitializeWellKnownObjectId__decomp.txt` (static) — MsInitializeWellKnownObjectId
- `proofs/validation/FS_OTBL_RA_005.csv` (matrix) — 
