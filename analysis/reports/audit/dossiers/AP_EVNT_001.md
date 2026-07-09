# Dossier — AP_EVNT_001 (BEHAVIORAL)

**Claim (this audit tests):** File creation: 0x01->0x04->0x01->0x00->0x04->0x01->0x00

**Canonical claim (reference_table.csv):** Application: File creation: 0x01->0x04->0x01->0x00->0x04->0x01->0x00

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Event Patterns] File creation: 0x01->0x04->0x01->0x00->0x04->0x01->0x00 — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_EVNT_001.csv`
- corrected registry note: Lee's pattern matches WRITE transactions (163x on 3 v3.4 images): INSERT UPD_DATA SET_OBJREC OPEN UPD_DATA INSERT OPEN = 0x01 0x04 0x10 0x00 0x04 0x01 0x00. 6/7 opcodes match Lee (position 3: 0x10 vs Lee's 0x01). Actual CREATE is a separate prior transaction: OPEN OPEN UPD_DATA SET_OBJREC INSERT INSERT INSERT SET_PARENT (35x). Lee likely described create-with-content as single operation.

## Proof links
- `proofs/validation/AP_EVNT_001.csv` (matrix) — 
