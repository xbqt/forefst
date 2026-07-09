# Dossier — CT_CTBL_005 (LITERATURE)

**Claim (this audit tests):** 0x20-0x28: free clusters in container (Prade)

**Canonical claim (reference_table.csv):** Content: 0x20-0x28: free clusters in container (Prade)

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — value+0x20 (u64) on REAL container rows (v3.4 win10): always <= CPC, e.g. free20=4 for partially-used, =16384 for fully-free containers - behaves like a free-cluster count. On all-0xFF sentinel rows (unused containers) the whole 0x20-0x2F block is 0xFF. hi-dword@0x2C==0 on 796625/796688 real rows (the 63 nonzero are 0xFF sentinels).

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- LITERATURE (Prade). Field within the CT value; disk-grounded by CT_CTBL_RA_006. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_CTBL_005.csv`
- corrected registry note: Row field interpretation not yet implemented in detail | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NOT_TESTED): Prade '0x20-0x28 free clusters' - the OFFSET holds a value consistent with a free-cluster count (<=CPC, varies with usage) but the SEMANTIC 'free clusters' is not E2-confirmed (no driver symbol tied). Note structure_reference dist

## Proof links
- `proofs/validation/CT_CTBL_005.csv` (matrix) — 
