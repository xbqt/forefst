# Dossier — CT_MISC_001 (BEHAVIORAL)

**Claim (this audit tests):** B+ tree balancing leaves recoverable remnants

**Canonical claim (reference_table.csv):** Content: B+ tree balancing leaves recoverable remnants

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (slack remnants); disk-demonstrated by the slack-recovery feature (finding #334). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_MISC_001.csv`
- corrected registry note: Log data area contains MSB+ pages (logged copies of old tree state); confirms CoW remnant persistence

## Proof links
- `proofs/validation/CT_MISC_001.csv` (matrix) — 
