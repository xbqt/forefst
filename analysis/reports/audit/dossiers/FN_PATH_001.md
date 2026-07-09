# Dossier — FN_PATH_001 (BEHAVIORAL)

**Claim (this audit tests):** OID Table + Parent-Child + dir names for full path

**Canonical claim (reference_table.csv):** File Name: OID Table + Parent-Child + dir names for full path

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral: path reconstruction (forefst walk_directory_tree does this). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FN_PATH_001.csv`
- corrected registry note: refs_dirfiles.py implements full path reconstruction via OID+Parent-Child+dir names on all images

## Proof links
- `proofs/validation/FN_PATH_001.csv` (matrix) — 
