# Dossier — AP_LGFL_004 (BEHAVIORAL)

**Claim (this audit tests):** Control Data: sequence number, start/end, next LSN, UUID

**Canonical claim (reference_table.csv):** Application: Control Data: sequence number, start/end, next LSN, UUID

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile] Control Data: sequence number, start/end, next LSN, UUID — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_004.csv`
- corrected registry note: Control page contains: sequence(0x20), UUID(0x10), data start/end(0xB8/0xC0), LSN range(0xC8/0xD0)

## Proof links
- `proofs/validation/AP_LGFL_004.csv` (matrix) — 
