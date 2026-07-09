# Dossier — AP_REDO_040 (BEHAVIORAL)

**Claim (this audit tests):** MLog opcode-to-operation sequences: CREATE=INSERT+INSERT+SET_OBJREC (99.9%), DELETE=DELETE/DEL_TABLE chain, RENAME=DELETE+DELETE+INSERT+INSERT, MOVE=DELETE+REPARENT+INSERT. 15 opcodes observed on v3.14 (of 37), 12 on v3.4.

**Canonical claim (reference_table.csv):** Application: MLog opcode-to-operation sequences: CREATE=INSERT+INSERT+SET_OBJREC (99.9%), DELETE=DELETE/DEL_TABLE chain, RENAME=DELETE+DELETE+INSERT+INSERT, MOVE=DELETE+REPARENT+INSERT. 15 opcodes observed on v3.14 (of 37), 12 on v3.4.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [MLog] MLog opcode-to-operation sequences: CREATE=INSERT+INSERT+SET_OBJREC (99.9%), DELETE=DELETE/DEL_TABLE chain, RE — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_REDO_040.csv`
- corrected registry note: 245K+ transactions across 5 images. v3.4 opcode 0x04 at 27% replaced by 0x10+0x1F in v3.14. Report: report_mlog_opcode_sequences.txt

## Proof links
- `proofs/validation/AP_REDO_040.csv` (matrix) — 
