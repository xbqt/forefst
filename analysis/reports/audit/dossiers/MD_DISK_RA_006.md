# Dossier — MD_DISK_RA_006 (PURE-RD-LAYOUT)

**Claim (this audit tests):** EFS files on disk: stream_count=3, sub-record #4 contains $EFS named stream (720 bytes) with certificate data (magic bytes $EFS in UTF-16).

**Canonical claim (reference_table.csv):** Metadata: EFS files on disk: stream_count=3, sub-record #4 contains $EFS named stream (720 bytes) with certificate data (magic bytes $EFS in UTF-16).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — EFS files (encrypted.txt/encrypted2.txt/testefs2.txt/testefs3.txt on win11refs4gattributestest2; efstest.txt on wininsiderrefs2t) ALL have stream_count@0x20==3 and encrypted attr bit 0x4000 set. The $EFS stream is a multi-instance sub-record (marker 0x80000002) with '$EFS' magic in UTF-16LE at value offset 0x280.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- EFS on disk; $EFS (0x100) disk-proven (MD_EFS_RA_005). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DISK_RA_006.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 9.7

## Proof links
- `proofs/validation/MD_DISK_RA_006.csv` (matrix) — 
