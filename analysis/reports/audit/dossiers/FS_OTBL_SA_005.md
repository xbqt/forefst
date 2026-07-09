# Dossier — FS_OTBL_SA_005 (BEHAVIORAL)

**Claim (this audit tests):** RefsIsSystemObjectId: 25-byte function returns true for OIDs in 0x01-0x5FF and 0x601-0x6FF. Root directory (0x600) explicitly excluded from 'system' classification. Boundary at 0x6FF matches MsSetMinimumNewObjectId.

**Canonical claim (reference_table.csv):** File System: RefsIsSystemObjectId: 25-byte function returns true for OIDs in 0x01-0x5FF and 0x601-0x6FF. Root directory (0x600) explicitly excluded from 'system' classification. Boundary at 0x6FF matches MsSetMinimumNewObjectId.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsIsSystemObjectId__decomp.txt
- Static driver evidence: RefsIsSystemObjectId. RefsIsSystemObjectId: 25-byte function returns true for OIDs in 0x01-0x5FF and 0x601-0x6FF. Root directory (0x. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_SA_005.csv`
- corrected registry note: See ObjectIdLifecycle.md

## Proof links
- `proofs/static/RefsIsSystemObjectId__decomp.txt` (static) — RefsIsSystemObjectId
- `proofs/validation/FS_OTBL_SA_005.csv` (matrix) — 
