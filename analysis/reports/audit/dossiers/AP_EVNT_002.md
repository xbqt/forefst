# Dossier — AP_EVNT_002 (BEHAVIORAL)

**Claim (this audit tests):** File deletion: 0x0F->0x02->0x0F->0x02->0x04

**Canonical claim (reference_table.csv):** Application: File deletion: 0x0F->0x02->0x0F->0x02->0x04

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Event Patterns] File deletion: 0x0F->0x02->0x0F->0x02->0x04 — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_EVNT_002.csv`
- corrected registry note: Core pattern DEL_TABLE DELETE DEL_TABLE DELETE = 0x0F 0x02 0x0F 0x02 observed 23x across 3 v3.4 images. Exact first-4 match. Lee's trailing 0x04 (timestamp update) appears as separate MODIFY transaction in our images.

## Proof links
- `proofs/validation/AP_EVNT_002.csv` (matrix) — 
