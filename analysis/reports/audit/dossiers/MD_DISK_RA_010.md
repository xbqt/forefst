# Dossier — MD_DISK_RA_010 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Type 0x20 entries (kf=0x8000): secondary filename index mapping stream indices to filenames. Key format: attr_type(0x20) + kf(0x8000) + stream_idx. Value: header + filename_len(u16) + UTF-16LE filename. Enables reverse lookup from stream index to filename.

**Canonical claim (reference_table.csv):** Metadata: Type 0x20 entries (kf=0x8000): secondary filename index mapping stream indices to filenames. Key format: attr_type(0x20) + kf(0x8000) + stream_idx. Value: header + filename_len(u16) + UTF-16LE filename. Enables reverse lookup from stream index to filename.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Type 0x20 entries with kf=0x8000 present on 113/113. Key (24B): attr_type 0x20@+0x00, kf 0x8000@+0x02, reserved 4B@+0x04, stream_idx u32@+0x08. Value carries the stream filename (e.g. OID 0x701 stream_idx=2 value -> 'WPSettings.dat'). Secondary filename index mapping stream indices to filenames.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Type 0x20 FileId index (finding #333); disk-proven present (FN_DTBL_003). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DISK_RA_010.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 9.4

## Proof links
- `proofs/validation/MD_DISK_RA_010.csv` (matrix) — 
