# Dossier — AP_WIPE_001 (BEHAVIORAL)

**Claim (this audit tests):** 12 tools identified by unique opcode patterns in $Logfile

**Canonical claim (reference_table.csv):** Application: 12 tools identified by unique opcode patterns in $Logfile

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Wiping Patterns] 12 tools identified by unique opcode patterns in $Logfile — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_WIPE_001.csv`
- corrected registry note: Requires controlled experiments: run each wipe tool on v3.7 image then analyze MLog via refs_mlog.py --parse.

## Proof links
- `proofs/validation/AP_WIPE_001.csv` (matrix) — 
