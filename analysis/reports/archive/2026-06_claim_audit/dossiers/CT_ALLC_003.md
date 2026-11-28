# Dossier — CT_ALLC_003 (BEHAVIORAL)

**Claim (this audit tests):** Allocator for itself and Container Table

**Canonical claim (reference_table.csv):** Content: Allocator for itself and Container Table

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Allocator role (root 2 = 0x20, virtual — CT_CTBL_RA_004). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_ALLC_003.csv`
- corrected registry note: Container Allocator (root #2) uses VIRTUAL addressing (contradicts Prade claim of real addressing)

## Proof links
- `proofs/validation/CT_ALLC_003.csv` (matrix) — 
