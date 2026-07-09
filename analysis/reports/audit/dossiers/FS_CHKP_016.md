# Dossier — FS_CHKP_016 (STRUCTURAL)

**Claim (this audit tests):** Global table 0x0B: Container Table

**Canonical claim (reference_table.csv):** File System: Global table 0x0B: Container Table

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Root index 7 -> Table-ID 0x0B (Container Table) on 47/48; the 1 outlier is 0x0C (the documented 2TB swap, finding #337) — set {0x0B,0x0C} at roots{7,8} preserved.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 108/108 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md Subtable A.4b: root index 7 = Container Table, Table ID 0xb, verified at the table-root MSB+ page header +0x48 (owning-table identifier) (REAL/physical LCN — bootstrap exception). Byte-verified on v3.4+v3.14: root[7] page +0x48 = 0xb. axis=version because the root set can shrink on older/upgraded volumes (probe returns N/A where the root is absent).

## Raw-disk proof
- probe `chkp_root_table` ; validation matrix: `proofs/validation/FS_CHKP_016.csv`
- corrected registry note: Root #7 has table ID 0x0B; uses REAL LCNs (bootstrap exception); VLCN=PLCN in all images

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_016.csv` (matrix) — 
