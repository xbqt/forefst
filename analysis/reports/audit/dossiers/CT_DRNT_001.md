# Dossier — CT_DRNT_001 (BEHAVIORAL)

**Claim (this audit tests):** Starting LCN of data run

**Canonical claim (reference_table.csv):** Content: Starting LCN of data run

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Extent-run entry within the 0x40 value (VLCN). Detailed run-table format; disk-grounded by MD_DATA_RA_004/005. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_DRNT_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/CT_DRNT_001.csv` (matrix) — 
