# Dossier — GN_IENT_006 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x0C-0x0E: value length

**Canonical claim (reference_table.csv):** General: 0x0C-0x0E: value length

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — value_length (u16@0x0C): yields valid values (resident 124B $SI, 84B/72B non-resident, type-0x40 extent values) on 100% of rows; all 111 images parse.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Index entry value_length@0x0C (verified val_off+val_len<=entry_len).

## Raw-disk proof
- probe `index_node` ; validation matrix: `proofs/validation/GN_IENT_006.csv`
- corrected registry note: Value length at position 5; validated by successful parsing of all table types

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/GN_IENT_006.csv` (matrix) — 
