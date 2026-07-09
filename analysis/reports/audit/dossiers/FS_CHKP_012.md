# Dossier — FS_CHKP_012 (STRUCTURAL)

**Claim (this audit tests):** Global table 0x01: Schema Table

**Canonical claim (reference_table.csv):** File System: Global table 0x01: Schema Table

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Root index 3 -> Table-ID 0x01 (Schema Table) on 47/48; 1 image had root3 page all-zero (edge image).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (win10)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md Subtable A.4b: root index 3 = Schema Table, Table ID 0x1, verified at the table-root MSB+ page header +0x48 (owning-table identifier). Byte-verified on v3.4+v3.14: root[3] page +0x48 = 0x1. axis=version because the root set can shrink on older/upgraded volumes (probe returns N/A where the root is absent).

## Raw-disk proof
- probe `chkp_root_table` ; validation matrix: `proofs/validation/FS_CHKP_012.csv`
- corrected registry note: Root #3 has table ID 0x01; parsed by refs_schema.py on all images

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_012.csv` (matrix) — 
