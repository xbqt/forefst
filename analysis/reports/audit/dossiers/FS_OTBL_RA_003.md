# Dossier — FS_OTBL_RA_003 (BEHAVIORAL)

**Claim (this audit tests):** OID 0xD = Trash Table (CmsTrashTable). Async deleted-file cleanup queue with schema 0xe0d0. CmsTrashTable::InitializeTable sets OID=0xD and calls MsCreateDurableTableObject. Empty (0 rows) on clean volumes.

**Canonical claim (reference_table.csv):** File System: OID 0xD = Trash Table (CmsTrashTable). Async deleted-file cleanup queue with schema 0xe0d0. CmsTrashTable::InitializeTable sets OID=0xD and calls MsCreateDurableTableObject. Empty (0 rows) on clean volumes.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OID 0xD present and walkable in Object Table on 113/113 applicable images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsTrashTable::InitializeTable. OID 0xD = Trash Table (CmsTrashTable). Async deleted-file cleanup queue with schema 0xe0d0. CmsTrashTable::Ini. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_RA_003.csv`
- corrected registry note: OID 0xD present on all 48 images. B+ tree at OID 0xD shows 0 rows on clean volumes. Page has valid MSB+ signature

## Proof links
- `proofs/validation/FS_OTBL_RA_003.csv` (matrix) — 
