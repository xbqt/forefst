# Dossier — AP_LGFL_005 (BEHAVIORAL)

**Claim (this audit tests):** ReFS is redo-only (no undo operations)

**Canonical claim (reference_table.csv):** Application: ReFS is redo-only (no undo operations)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile] ReFS is redo-only (no undo operations) — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_005.csv`
- corrected registry note: No undo-related structures found in MLog control or data areas across all 39 images

## Proof links
- `proofs/validation/AP_LGFL_005.csv` (matrix) — 
