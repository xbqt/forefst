# Dossier — MD_TS_RA_004 (ABSENCE)

**Claim (this audit tests):** Attribute changes (e.g. setting ReadOnly) update ONLY the metadata change time at offset 0x38. This timestamp is NOT exposed by PowerShell Get-Item (which shows only C M A). Only visible via raw disk analysis or Win32 GetFileInformationByHandleEx.

**Canonical claim (reference_table.csv):** Metadata: Attribute changes (e.g. setting ReadOnly) update ONLY the metadata change time at offset 0x38. This timestamp is NOT exposed by PowerShell Get-Item (which shows only C M A). Only visible via raw disk analysis or Win32 GetFileInformationByHandleEx.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — Metadata-change-time field exists at $SI+0x10 (type-0x10) / value+0x38 (resident index entry), sane FILETIME corpus-wide. Whether attribute-only changes touch ONLY this field is behavioral.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (ctime-only on attr change). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_TS_RA_004.csv`
- corrected registry note: Raw disk: MFT change time 13:33:27 at offset 0x38 vs last access 13:32:09 at offset 0x40. Delta = 1:18 confirming separate update. See ra_step4_17_4th_timestamp_report.md

## Proof links
- `proofs/validation/MD_TS_RA_004.csv` (matrix) — 
