# Dossier — FS_DEL_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** ReFS file deletion flow: RefsDeleteFile → MsDeleteRow (removes from directory B+ tree) → MsReparentFileToTrash → CmsTrashTable::AddFileTable (OID 0xD queues for cleanup) → background TrashCleanerWorkItemMethod → DeleteFileTable (frees data extents). CoW ensures old directory pages persist. Recovery: (1) Trash Table scan (2) checkpoint comparison (3) orphaned MSB+ page scan.

**Canonical claim (reference_table.csv):** File System: ReFS file deletion flow: RefsDeleteFile → MsDeleteRow (removes from directory B+ tree) → MsReparentFileToTrash → CmsTrashTable::AddFileTable (OID 0xD queues for cleanup) → background TrashCleanerWorkItemMethod → DeleteFileTable (frees data extents). CoW ensures old directory pages persist. Recovery: (1) Trash Table scan (2) checkpoint comparison (3) orphaned MSB+ page scan.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — Deletion flow (RefsDeleteFile -> MsDeleteRow -> MsReparentFileToTrash -> CmsTrashTable::AddFileTable OID 0xD -> TrashCleanerWorkItemMethod -> DeleteFileTable) is an E2 driver call-chain. The disk-observable end-states (Trash Table at OID 0xD, CoW old directory pages) are real - build_trash_set reads OID 0xD - but the call sequence itself is static-only.

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsDeleteFile__decomp.txt
- Static driver evidence: the deletion path RefsDeleteFile -> MsDeleteRow/DeleteFromIndex removes only the offset-array slot (finding #334, deleted --slack). Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_DEL_RA_001.csv`
- corrected registry note: All 66 test images: empty trash tables and identical checkpoints (no recent deletions). 1222 orphaned leaf pages on millionsofactions image but contain allocator rows not directory entries. Tool: refs_deleted.py

## Proof links
- `proofs/static/RefsDeleteFile__decomp.txt` (static) — RefsDeleteFile
- `proofs/validation/FS_DEL_RA_001.csv` (matrix) — 
