# Dossier — FS_VBR_013 (BEHAVIORAL)

**Claim (this audit tests):** Backup boot sector in last sector of volume

**Canonical claim (reference_table.csv):** File System: Backup boot sector in last sector of volume

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [VBR] Backup boot sector in last sector of volume — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_VBR_013.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/FS_VBR_013.csv` (matrix) — 
