# Dossier — MD_ATTR_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** File attribute bit map with bit 10 (0x400 REPARSE_POINT) and bit 9 (0x200 SPARSE_FILE). Full bit decomposition from bit 0 (ReadOnly) through bit 28 (NO_SCRUB_DATA).

**Canonical claim (reference_table.csv):** Metadata: File attribute bit map with bit 10 (0x400 REPARSE_POINT) and bit 9 (0x200 SPARSE_FILE). Full bit decomposition from bit 0 (ReadOnly) through bit 28 (NO_SCRUB_DATA).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Bit 9 (0x200 SPARSE) and bit 10 (0x400 REPARSE) both present at dirent value+0x40: sparse combo 0x220 observed (1 file), reparse combos 0x420=2047/0x10000400=8. Integrity bit 0x8000 (0x8020, 0x8420) and EA bit 0x40000 also observed, consistent with the documented bit map.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- FileAttributes bit semantics. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_002.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 12.2

## Proof links
- `proofs/validation/MD_ATTR_RA_002.csv` (matrix) — 
