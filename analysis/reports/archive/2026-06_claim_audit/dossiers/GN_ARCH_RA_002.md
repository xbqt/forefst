# Dossier — GN_ARCH_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** NTFS and ReFS both reject ADS on symlink targets — OS limitation not filesystem-specific

**Canonical claim (reference_table.csv):** General: NTFS and ReFS both reject ADS on symlink targets — OS limitation not filesystem-specific

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Architecture] NTFS and ReFS both reject ADS on symlink targets — OS limitation not filesystem-specific — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_ARCH_RA_002.csv`
- corrected registry note: Same Set-Content error on symlinks for both NTFS and ReFS during Generate-FSActivitySpecials

## Proof links
- `proofs/validation/GN_ARCH_RA_002.csv` (matrix) — 
