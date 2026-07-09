# Dossier — GN_IENT_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x00-0x04: entry length

**Canonical claim (reference_table.csv):** General: 0x00-0x04: entry length

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — B+ row header entry_length (u32@0x00): self-consistent (entry_len >= max(key_off+key_len, val_off+val_len) and <= page size) on 100% of rows across 6 images spanning 4K/64K, CRC32/CRC64/SHA256, v3.4/v3.14/insider (e.g. 886/886, 1527/1527, 3141/3141, 3204/3204).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Index entry header <I6H>: entry_length@0x00. Verified row-header consistency (entry_len>0, key/value within entry) on the OT-root node.

## Raw-disk proof
- probe `index_node` ; validation matrix: `proofs/validation/GN_IENT_001.csv`
- corrected registry note: Entry parsing confirmed across all tools; entry length used for row traversal

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/GN_IENT_001.csv` (matrix) — 
