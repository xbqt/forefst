# Dossier — AP_EVNT_005 (BEHAVIORAL)

**Claim (this audit tests):** Directory creation: 0x00->0x00->0x04->0x10->...

**Canonical claim (reference_table.csv):** Application: Directory creation: 0x00->0x00->0x04->0x10->...

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Event Patterns] Directory creation: 0x00->0x00->0x04->0x10->... — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_EVNT_005.csv`
- corrected registry note: EXACT MATCH. All 35 CREATE transactions across 3 v3.4 images begin OPEN OPEN UPD_DATA SET_OBJREC = 0x00 0x00 0x04 0x10. Full sequence is 0x00 0x00 0x04 0x10 0x01 0x01 0x01 0x0E (Lee's '...' = INSERT INSERT INSERT SET_PARENT).

## Proof links
- `proofs/validation/AP_EVNT_005.csv` (matrix) — 
