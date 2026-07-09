# Dossier — FS_CHKP_015 (STRUCTURAL)

**Claim (this audit tests):** Global table 0x05: Block Reference Count Table

**Canonical claim (reference_table.csv):** File System: Global table 0x05: Block Reference Count Table

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Root index 6 -> Table-ID 0x05 (Block Refcount) on 47/48; 1 image root6 page all-zero (edge).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 108/108 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md Subtable A.4b: root index 6 = Block Reference Count Table, Table ID 0x5, verified at the table-root MSB+ page header +0x48 (owning-table identifier). Byte-verified on v3.4+v3.14: root[6] page +0x48 = 0x5. axis=version because the root set can shrink on older/upgraded volumes (probe returns N/A where the root is absent).

## Raw-disk proof
- probe `chkp_root_table` ; validation matrix: `proofs/validation/FS_CHKP_015.csv`
- corrected registry note: Root #6 has table ID 0x05; valid MSB+ pages

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_015.csv` (matrix) — 
