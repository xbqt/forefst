# Dossier — GN_DTCT_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** BitLocker and NTFS volumes correctly detected as non-ReFS by all tools (graceful failure with clear error messages)

**Canonical claim (reference_table.csv):** General: BitLocker and NTFS volumes correctly detected as non-ReFS by all tools (graceful failure with clear error messages)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Detection] BitLocker and NTFS volumes correctly detected as non-ReFS by all tools (graceful failure with clear error mess — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_DTCT_RA_001.csv`
- corrected registry note: Tested with win11refsbitlocked (-FVE-FS- signature) and win11ntfs (NTFS signature). Tools reject with descriptive errors

## Proof links
- `proofs/validation/GN_DTCT_RA_001.csv` (matrix) — 
