# Trash Table

The Trash Table (OID 0x0D, schema 0xe0d0) is an asynchronous deletion queue. When a non-resident file or directory is deleted, its OID is reparented into this table for deferred background cleanup rather than being freed immediately. This makes the table the single most promising on-disk location for recovering recently deleted files on ReFS.

## Key format — 16 bytes

The key contains the reparented OID of the deleted file or directory. The table holds keys only; the file's data and metadata stay in place and remain reachable through the [Object Table](object_table.md) until the background cleaner runs.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 16 | Reparented OID | OID of the deleted file or directory, moved here from its parent directory B+-tree; still resolvable via the Object Table |

## Deletion pipeline

A non-resident delete moves through three stages, the last of which runs in the background:

1. **`RefsDeleteFile` → `MsDeleteRow`**: Removes the file's entry from its parent directory B+-tree.
2. **`MsReparentFileToTrash` → `CmsTrashTable::AddFileTable`**: Moves the file's OID to the Trash Table (OID 0x0D) for deferred cleanup. Data extents and metadata remain intact at this stage.
3. **Background `TrashCleanerWorkItemMethod` → `CmsTrashTable::DeleteFileTable`**: Frees data extents and removes the file table. Runs asynchronously after checkpoint.

## Resident file bypass

Resident (inline) files bypass the Trash Table entirely. They are deleted directly via `RefsDeleteResidentDataScbAndCommit`, which removes the inline data and directory entry in a single transaction without staging through the trash queue.

## Observed state

The table is empty (0 rows) on every analysed image. This is expected for cleanly unmounted test volumes, where the background trash cleaner has completed all pending deletions before capture. A populated Trash Table would therefore indicate a volume that was not cleanly unmounted, or one captured while deletions were still in flight — this is inferred from the deferred-cleanup pipeline; no populated Trash Table was observed on any test image.

## Forensic value

On a live or crash-captured volume, the Trash Table may contain entries for recently deleted files that have not yet been cleaned up. While an entry persists, the deleted object still preserves:

- The file's OID (enabling lookup in the [Object Table](object_table.md))
- Data extents (still allocated, not yet freed)
- All metadata (timestamps, attributes, security descriptors)

This is one of three ReFS deleted-file recovery paths, the other two being checkpoint differential comparison and an orphan-page scan of the Object Table.

## Version presence

Present on all versions from v3.4 through Insider.

## Cross-references

- [Object Table](object_table.md) — reparented OIDs are still resolvable via the Object Table
- [Schema Table](schema_table.md) — schema 0xe0d0
- [System OIDs](system_oids.md) — OID 0x0D

## Evidence

The OID 0x0D / schema 0xe0d0 identity and the deletion pipeline are confirmed by the decompiled driver (E2): `CmsTrashTable::InitializeTable` sets the OID to 0x0D and schema to 0xe0d0, and the `RefsDeleteFile → MsDeleteRow → MsReparentFileToTrash → CmsTrashTable::AddFileTable → TrashCleanerWorkItemMethod → CmsTrashTable::DeleteFileTable` chain is decompiled end to end. The empty-on-disk result is raw-disk verified across the corpus (RD), re-confirmed by reading the Object Table at OID 0x0D directly on v3.4 and v3.14 images. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
