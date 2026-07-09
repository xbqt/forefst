# Dossier — AP_EVNT_003 (BEHAVIORAL)

**Claim (this audit tests):** File modification: 0x06->0x04->0x04->0x04->0x04->0x08

**Canonical claim (reference_table.csv):** Application: File modification: 0x06->0x04->0x04->0x04->0x04->0x08

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Event Patterns] File modification: 0x06->0x04->0x04->0x04->0x04->0x08 — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_EVNT_003.csv`
- corrected registry note: 6-opcode sequence NOT found as single transaction in any v3.4 image. Individual components observed as separate transactions: ALLOC UPD_DATA (36x) + UPD_DATA (205x) + SET_RANGE (97x). Lee may have used different transaction boundary definition or different v3.4 build. Confidence lowered to Medium.

## Proof links
- `proofs/validation/AP_EVNT_003.csv` (matrix) — 
