# Dossier — CT_ALLC_002 (BEHAVIORAL)

**Claim (this audit tests):** Main allocator for trees and file contents

**Canonical claim (reference_table.csv):** Content: Main allocator for trees and file contents

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (win10)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Allocator role (root 1 = 0x21). Cited; row format disk-verified in CT_ALLC_RA_001.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_ALLC_002.csv`
- corrected registry note: Medium Allocator (root #1) uses virtual addressing; valid MSB+ pages in all images

## Proof links
- `proofs/validation/CT_ALLC_002.csv` (matrix) — 
