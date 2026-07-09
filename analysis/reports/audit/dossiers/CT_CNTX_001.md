# Dossier — CT_CNTX_001 (BEHAVIORAL)

**Claim (this audit tests):** Named but no field layout provided

**Canonical claim (reference_table.csv):** Content: Named but no field layout provided

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Root 10 presence disk-verified in FS_CHKP_019; internal layout not decoded. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_CNTX_001.csv`
- corrected registry note: Container Index Table (root #10, ID 0x0E) exists with valid MSB+ pages in all images

## Proof links
- `proofs/validation/CT_CNTX_001.csv` (matrix) — 
