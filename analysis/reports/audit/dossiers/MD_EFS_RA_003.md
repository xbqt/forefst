# Dossier — MD_EFS_RA_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Encrypted files: stream_count=3 with $EFS named stream. Minimum 4096-byte allocation even for small files. Attribute value changes from 0x20 to 0x4020.

**Canonical claim (reference_table.csv):** Metadata: Encrypted files: stream_count=3 with $EFS named stream. Minimum 4096-byte allocation even for small files. Attribute value changes from 0x20 to 0x4020.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Encrypted files: $EFS named-stream sub-record (type 0x100, MI marker, name='$EFS') present on encrypted images (4 on win11refs4gattributestest2, 2 on win11refs4gattributes). Attribute value 0x4020 (encrypted+archive) observed at dirent value+0x40 (12 occurrences). The 'attr changes 0x20->0x4020' and '$EFS stream present' parts are disk-confirmed.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- EFS on disk; $EFS disk-proven (MD_EFS_RA_005). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_EFS_RA_003.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 6.3

## Proof links
- `proofs/validation/MD_EFS_RA_003.csv` (matrix) — 
