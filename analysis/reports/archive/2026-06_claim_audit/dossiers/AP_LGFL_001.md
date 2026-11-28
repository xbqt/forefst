# Dossier — AP_LGFL_001 (BEHAVIORAL)

**Claim (this audit tests):** Entry Header: 120 bytes, starts with 'MLog'

**Canonical claim (reference_table.csv):** Application: Entry Header: 120 bytes, starts with 'MLog'

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** E1

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile] Entry Header: 120 bytes, starts with 'MLog' — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_001.csv`
- corrected registry note: MLog control page: 16 fields across 256+ bytes. Version always 1, sector_size matches cluster_size. Complete field map documented from 39 images. Extends Lee's 6-field description to 16-field full layout. Merged from AP_LGFL_RA_001

## Proof links
- `proofs/validation/AP_LGFL_001.csv` (matrix) — 
