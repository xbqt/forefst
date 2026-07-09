# Dossier — GN_OOP_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Win11 upper-layer OOP: 13 named C++ classes with 72 methods + ~345 lambda helpers. Win10 was purely procedural (0 classes, 1248 free functions)

**Canonical claim (reference_table.csv):** General: Win11 upper-layer OOP: 13 named C++ classes with 72 methods + ~345 lambda helpers. Win10 was purely procedural (0 classes, 1248 free functions)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [OOP] Win11 upper-layer OOP: 13 named C++ classes with 72 methods + ~345 lambda helpers. Win10 was purely procedural — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_OOP_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_OOP_SA_001.csv` (matrix) — 
