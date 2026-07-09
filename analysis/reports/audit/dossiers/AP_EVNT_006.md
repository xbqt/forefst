# Dossier — AP_EVNT_006 (BEHAVIORAL)

**Claim (this audit tests):** Directory deletion: 0x02->0x02->0x0F->0x02->...

**Canonical claim (reference_table.csv):** Application: Directory deletion: 0x02->0x02->0x0F->0x02->...

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Event Patterns] Directory deletion: 0x02->0x02->0x0F->0x02->... — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_EVNT_006.csv`
- corrected registry note: Same opcodes {DELETE DEL_TABLE} observed but ordering differs. Dominant pattern (23x): DEL_TABLE DELETE DEL_TABLE DELETE = 0x0F 0x02 0x0F 0x02. Lee: DELETE DELETE DEL_TABLE DELETE = 0x02 0x02 0x0F 0x02. Same opcode composition different ordering — record order within a transaction may vary by context.

## Proof links
- `proofs/validation/AP_EVNT_006.csv` (matrix) — 
