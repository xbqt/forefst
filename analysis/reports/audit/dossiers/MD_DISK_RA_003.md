# Dossier — MD_DISK_RA_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Resident type 0x30 entry layout: stream_count at offset 0x20, file attributes at offset 0x48, file size at offset 0x58.

**Canonical claim (reference_table.csv):** Metadata: Resident type 0x30 entry layout: stream_count at offset 0x20, file attributes at offset 0x48, file size at offset 0x58.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — resident value+0x58 == FileSize, 409514/409514 v3.14

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Resident 0x30 layout; stream_count field. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DISK_RA_003.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 9.3

## Proof links
- `proofs/validation/MD_DISK_RA_003.csv` (matrix) — 
