# Dossier — MD_SF_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** Sparse file creation requires 3-step process on ReFS: (1) create file, (2) fsutil sparse setflag, (3) fsutil sparse setrange.

**Canonical claim (reference_table.csv):** Metadata: Sparse file creation requires 3-step process on ReFS: (1) create file, (2) fsutil sparse setflag, (3) fsutil sparse setrange.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (sparse-file creation sequence). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SF_RA_001.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 4.1

## Proof links
- `proofs/validation/MD_SF_RA_001.csv` (matrix) — 
