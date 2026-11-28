# Dossier — FS_SUPB_RA_004 (BEHAVIORAL)

**Claim (this audit tests):** SUPB Volume GUID at offset 0x50 (16 bytes) is non-critical for bootstrap. Corrupting the GUID does not prevent mount because the driver locates checkpoints via fixed-offset CHKP LCN pointers at SUPB+0xC0/0xC8 not via the GUID.

**Canonical claim (reference_table.csv):** File System: SUPB Volume GUID at offset 0x50 (16 bytes) is non-critical for bootstrap. Corrupting the GUID does not prevent mount because the driver locates checkpoints via fixed-offset CHKP LCN pointers at SUPB+0xC0/0xC8 not via the GUID.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Superblock] SUPB Volume GUID at offset 0x50 (16 bytes) is non-critical for bootstrap. Corrupting the GUID does not prevent — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SUPB_RA_004.csv`
- corrected registry note: Corrupted GUID volume mounted and operated normally. All files readable. See ra_step4_15_corrupted_metadata_report.md

## Proof links
- `proofs/validation/FS_SUPB_RA_004.csv` (matrix) — 
