# Dossier — CT_DRNT_003 (BEHAVIORAL)

**Claim (this audit tests):** Total length of data run

**Canonical claim (reference_table.csv):** Content: Total length of data run

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Extent-run length field. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_DRNT_003.csv`
- corrected registry note: PT: Extent length field at value[0x08] verified on win11refslasttests

## Proof links
- `proofs/validation/CT_DRNT_003.csv` (matrix) — 
