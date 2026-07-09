# Dossier — GN_IENT_004 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x08-0x0A: flags (0x4 deleted)

**Canonical claim (reference_table.csv):** General: 0x08-0x0A: flags (0x4 deleted)

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — flags (u16@0x08): observed values on LIVE pages = {0x00, 0x01, 0x02} (e.g. {0:862,1:22,2:2}); the 0x04 'deleted' value does NOT appear in live consistent trees.

**Original audit verdict:** INFERRED (disk held 112/112 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Index entry flags@0x08 (0x4=deleted). Structure verified.

## Raw-disk proof
- probe `index_node` ; validation matrix: `proofs/validation/GN_IENT_004.csv`
- corrected registry note: PT: Row descriptor flags at +4. Deletion flag 0x4 confirmed via Ghidra (RefsCommonCleanup) | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Offset/field at 0x08 confirmed on disk. The specific 0x04=deleted semantic is E2/Ghidra-derived (RefsCommonCleanup) and not observable in live pages (deleted rows are pruned via CoW); cannot be disk-confirmed without a torn/old Co

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/GN_IENT_004.csv` (matrix) — 
