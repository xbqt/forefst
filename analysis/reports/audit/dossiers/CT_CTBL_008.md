# Dossier — CT_CTBL_008 (LITERATURE)

**Claim (this audit tests):** 0x98-0xA0: number of clusters (4K, Prade)

**Canonical claim (reference_table.csv):** Content: 0x98-0xA0: number of clusters (4K, Prade)

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — value+0x18 (CPC, u32) holds 16384(4K)/1024(64K) on 796688/796688 rows; trailing copy at 0x98(160B)/0xD8(224B). The 'number of clusters'=CPC is the count of clusters in the container.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- LITERATURE (Prade). The CPC trailing copy at value+0x98. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_CTBL_008.csv`
- corrected registry note: DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NOT_TESTED): Prade '0x98-0xA0 number of clusters (4K)'. On disk, 0x98 (for 160B rows) holds the CPC trailing copy (=16384), which IS the number of clusters per container. So Prade's offset+semantic are essentially correct: 0x98=cluster count(=

## Proof links
- `proofs/validation/CT_CTBL_008.csv` (matrix) — 
