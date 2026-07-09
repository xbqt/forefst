# Dossier — AP_EVNT_004 (BEHAVIORAL)

**Claim (this audit tests):** File renaming: 0x02->0x05->0x01->0x04->0x04

**Canonical claim (reference_table.csv):** Application: File renaming: 0x02->0x05->0x01->0x04->0x04

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Event Patterns] File renaming: 0x02->0x05->0x01->0x04->0x04 — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_EVNT_004.csv`
- corrected registry note: First 4 opcodes DELETE REPARENT INSERT UPD_DATA match our MOVE pattern (23x): DELETE REPARENT INSERT UPD_DATA SET_OBJREC UPD_DATA INSERT. Core 0x02 0x05 0x01 0x04 confirmed. Lee's 'renaming' is actually a move operation. Same-directory rename uses DELETE DELETE INSERT INSERT (no REPARENT).

## Proof links
- `proofs/validation/AP_EVNT_004.csv` (matrix) — 
