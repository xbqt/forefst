# Dossier — MD_SF_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** Sparse flag appears as Basic info change (0x8000) in USN with attribute changing from 0x20 to 0x220 (adding FILE_ATTRIBUTE_SPARSE_FILE bit 0x200).

**Canonical claim (reference_table.csv):** Metadata: Sparse flag appears as Basic info change (0x8000) in USN with attribute changing from 0x20 to 0x220 (adding FILE_ATTRIBUTE_SPARSE_FILE bit 0x200).

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (USN reason for sparse). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SF_RA_002.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 4.2

## Proof links
- `proofs/validation/MD_SF_RA_002.csv` (matrix) — 
