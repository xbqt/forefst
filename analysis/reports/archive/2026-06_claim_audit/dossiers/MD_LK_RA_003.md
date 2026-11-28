# Dossier — MD_LK_RA_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** ADS cannot be set on symlink files (reparse points) on ReFS. set-content -stream fails on reparse point entries.

**Canonical claim (reference_table.csv):** Metadata: ADS cannot be set on symlink files (reparse points) on ReFS. set-content -stream fails on reparse point entries.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral constraint. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_LK_RA_003.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 8.4

## Proof links
- `proofs/validation/MD_LK_RA_003.csv` (matrix) — 
