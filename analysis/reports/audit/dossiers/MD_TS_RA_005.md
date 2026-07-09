# Dossier — MD_TS_RA_005 (ABSENCE)

**Claim (this audit tests):** ReFS does NOT support 8.3 short file names. fsutil file setshortname returns 'A local NTFS volume is required'. Format-Volume -ShortFileNameSupport $true returns 'Not Supported'. No RefsSetShortName function exists in refs.sys.

**Canonical claim (reference_table.csv):** Metadata: ReFS does NOT support 8.3 short file names. fsutil file setshortname returns 'A local NTFS volume is required'. Format-Volume -ShortFileNameSupport $true returns 'Not Supported'. No RefsSetShortName function exists in refs.sys.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ABSENCE (finding #335): no 8.3 short names; fsutil setshortname fails. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_TS_RA_005.csv`
- corrected registry note: Tested on win11refs8gtest4timestamps.raw. See ra_step4_17_4th_timestamp_report.md

## Proof links
- `proofs/validation/MD_TS_RA_005.csv` (matrix) — 
