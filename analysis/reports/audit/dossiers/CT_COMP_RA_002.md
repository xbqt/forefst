# Dossier — CT_COMP_RA_002 (ABSENCE)

**Claim (this audit tests):** Compression requires dedup engine + background job; refsutil compression /c only sets parameters, does not compress existing data

**Canonical claim (reference_table.csv):** Content: Compression requires dedup engine + background job; refsutil compression /c only sets parameters, does not compress existing data

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (compression mechanism). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_COMP_RA_002.csv`
- corrected registry note: Confirmed during compression image creation: /c sets params but actual compression happens via dedup engine

## Proof links
- `proofs/validation/CT_COMP_RA_002.csv` (matrix) — 
