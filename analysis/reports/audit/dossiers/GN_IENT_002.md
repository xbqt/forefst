# Dossier — GN_IENT_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x04-0x06: key offset

**Canonical claim (reference_table.csv):** General: 0x04-0x06: key offset

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — key_offset (u16@0x04): in-bounds (row+key_off+key_len <= page; key_off>=16) on 100% of rows across all tested images/cluster-sizes/versions.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Index entry key_offset@0x04 (verified key_off>=0x10, key within entry).

## Raw-disk proof
- probe `index_node` ; validation matrix: `proofs/validation/GN_IENT_002.csv`
- corrected registry note: Key offset at position 1 in row header struct; used by all B+-tree parsers

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/GN_IENT_002.csv` (matrix) — 
