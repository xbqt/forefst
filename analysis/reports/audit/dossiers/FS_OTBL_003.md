# Dossier — FS_OTBL_003 (BEHAVIORAL)

**Claim (this audit tests):** Duplicate copy exists for resilience

**Canonical claim (reference_table.csv):** File System: Duplicate copy exists for resilience

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Object Table] Duplicate copy exists for resilience — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_OTBL_003.csv`
- corrected registry note: Roots #0 (ID 0x02) and #5 (ID 0x04) are duplicate Object ID Tables in all images

## Proof links
- `proofs/validation/FS_OTBL_003.csv` (matrix) — 
