# Dossier — FS_CHKP_019 (STRUCTURAL)

**Claim (this audit tests):** Global table 0x0E: Container Index Table

**Canonical claim (reference_table.csv):** File System: Global table 0x0E: Container Index Table

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Root index 10 -> Table-ID 0x0E (Container Index Table) on 48/48.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md Subtable A.4b: root index 10 = Container Index Table, Table ID 0xe, verified at the table-root MSB+ page header +0x48 (owning-table identifier). Byte-verified on v3.4+v3.14: root[10] page +0x48 = 0xe. axis=version because the root set can shrink on older/upgraded volumes (probe returns N/A where the root is absent).

## Raw-disk proof
- probe `chkp_root_table` ; validation matrix: `proofs/validation/FS_CHKP_019.csv`
- corrected registry note: Root #10 has table ID 0x0E; valid MSB+ pages in all images

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_019.csv` (matrix) — 
