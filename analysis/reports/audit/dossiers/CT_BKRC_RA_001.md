# Dossier — CT_BKRC_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Deep row structure: Key=[StartLCN(u64), BlockCount(u64)]. Value=28B header + BlockCount*u16 refcount array + 4B trailing (2080B for bc=0x400). Header: StartLCN(redundant), BlockCount(redundant), ModificationStamp(u64), TotalRefCount(u32). Array entry bitfield: RefCount(13:0), Flag14(14), Shared(15). TotalRefCount=sum(entry&0x3FFF). Dedup flags 0x8000/0x4000 on dedup volumes. Table exists from v3.4 (empty) but populated only on v3.14+. 1305 rows across 83 images; 1302/1302 sum verification matches

**Canonical claim (reference_table.csv):** Content: Deep row structure: Key=[StartLCN(u64), BlockCount(u64)]. Value=28B header + BlockCount*u16 refcount array + 4B trailing (2080B for bc=0x400). Header: StartLCN(redundant), BlockCount(redundant), ModificationStamp(u64), TotalRefCount(u32). Array entry bitfield: RefCount(13:0), Flag14(14), Shared(15). TotalRefCount=sum(entry&0x3FFF). Dedup flags 0x8000/0x4000 on dedup volumes. Table exists from v3.4 (empty) but populated only on v3.14+. 1305 rows across 83 images; 1302/1302 sum verification matches

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — block-refcount value 0x820; TotalRefCount@0x18=sum, array@0x1C, 230/230

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 37/37 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Block Ref Count (root 6) rows have 16-byte keys [StartLCN, BlockCount]. N/A on volumes without clones/dedup (empty BRC).

## Raw-disk proof
- probe `root_row` ; validation matrix: `proofs/validation/CT_BKRC_RA_001.csv`
- corrected registry note: See ra_step4_24_block_refcount_table_report.md

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/CT_BKRC_RA_001.csv` (matrix) — 
