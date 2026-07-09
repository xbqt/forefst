# Dossier — GN_IENT_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x06-0x08: key length

**Canonical claim (reference_table.csv):** General: 0x06-0x08: key length

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — key_length (u16@0x06): produces valid keys (type-0x30/0x40/0x20 markers, decodable filenames) on 100% of rows; corpus key parses succeed on all 111 images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Index entry key_length@0x06 (verified key_off+key_len<=entry_len).

## Raw-disk proof
- probe `index_node` ; validation matrix: `proofs/validation/GN_IENT_003.csv`
- corrected registry note: Key length at position 2; validated by successful key extraction across all images

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/GN_IENT_003.csv` (matrix) — 
