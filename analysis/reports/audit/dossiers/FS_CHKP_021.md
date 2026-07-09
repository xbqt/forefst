# Dossier — FS_CHKP_021 (STRUCTURAL)

**Claim (this audit tests):** Global table 0x22: Small Allocator Table

**Canonical claim (reference_table.csv):** File System: Global table 0x22: Small Allocator Table

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Root index 12 -> Table-ID 0x22 (Small Allocator, real LCN) on 47/48; 1 outlier resolves to 0x0B (the documented 2TB allocator-root anomaly, #337).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 108/108 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md Subtable A.4b: root index 12 = Small Allocator Table, Table ID 0x22, verified at the table-root MSB+ page header +0x48 (owning-table identifier) (REAL/physical LCN — bootstrap exception). Byte-verified on v3.4+v3.14: root[12] page +0x48 = 0x22. axis=version because the root set can shrink on older/upgraded volumes (probe returns N/A where the root is absent).

## Raw-disk proof
- probe `chkp_root_table` ; validation matrix: `proofs/validation/FS_CHKP_021.csv`
- corrected registry note: Root #12 has table ID 0x22; uses REAL LCNs (bootstrap fallback); VLCN=PLCN in all images

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_021.csv` (matrix) — 
