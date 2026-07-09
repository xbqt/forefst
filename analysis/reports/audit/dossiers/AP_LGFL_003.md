# Dossier — AP_LGFL_003 (BEHAVIORAL)

**Claim (this audit tests):** Log Record: contains redo records with opcodes

**Canonical claim (reference_table.csv):** Application: Log Record: contains redo records with opcodes

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile] Log Record: contains redo records with opcodes — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_003.csv`
- corrected registry note: refs_mlog.py parses redo records from two-layer structure (_SmsRedoHeader → _SmsRedoRecord) on 25/25 images. All opcodes match E2 dispatch tables. Replaces broken refs_logfile.py (E10).

## Proof links
- `proofs/validation/AP_LGFL_003.csv` (matrix) — 
