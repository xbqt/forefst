# Dossier — MD_TS_RA_001 (ABSENCE)

**Claim (this audit tests):** Last access time (offset 0x40 in $SI) updated on read operations when RefsDisableLastAccessUpdate=0. Independent of Last Write Time. Verified: cat ok.txt changed LastAccessTime from 3:30:03 to 3:30:27 while LastWriteTime stayed at 3:30:03.

**Canonical claim (reference_table.csv):** Metadata: Last access time (offset 0x40 in $SI) updated on read operations when RefsDisableLastAccessUpdate=0. Independent of Last Write Time. Verified: cat ok.txt changed LastAccessTime from 3:30:03 to 3:30:27 while LastWriteTime stayed at 3:30:03.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — Last-access-time field exists at $SI+0x18 (type-0x10) / value+0x40 (resident index entry) and holds sane FILETIMEs (409401/409514 resident entries have all 4 timestamps @0x28..0x40 sane). Whether reads update it (gated by RefsDisableLastAccessUpdate=0) is a live-filesystem behavioral property not observable in static disk images.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (atime update). NOTE: $SI+0x40 is LastUsn per E27; access time is at $SI+0x18 (disk-proven MD_FTBL_004). Cited with offset caveat.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_TS_RA_001.csv`
- corrected registry note: Manual test on win11refs8gtest4timestamps.raw with registry RefsDisableLastAccessUpdate=0. Raw disk verification at offset 0x40. See ra_step4_17_4th_timestamp_report.md

## Proof links
- `proofs/validation/MD_TS_RA_001.csv` (matrix) — 
