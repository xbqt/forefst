# Dossier — FS_OTBL_RA_004 (BEHAVIORAL)

**Claim (this audit tests):** OID 0x501 = Volume Information Table (failover/duplicate). Created alongside OID 0x500 by InitializeVolumeInfoTable using MsCreateDurableFailoverTableObject with schema 0x150 and count=2.

**Canonical claim (reference_table.csv):** File System: OID 0x501 = Volume Information Table (failover/duplicate). Created alongside OID 0x500 by InitializeVolumeInfoTable using MsCreateDurableFailoverTableObject with schema 0x150 and count=2.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OID 0x500 present 113/113 and OID 0x501 (failover/duplicate) present 113/113.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- OID 0x501 is the failover/duplicate Volume Information table (pairs with 0x500, verified via FS_VINF_*). Structural-duplicate claim; cited (the primary 0x500 rows are disk-verified in FS_VINF_001/002/003).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_OTBL_RA_004.csv`
- corrected registry note: OID 0x501 present on all 48 images. Same failover pattern as 0x07/0x08 and 0x09/0x0A

## Proof links
- `proofs/validation/FS_OTBL_RA_004.csv` (matrix) — 
