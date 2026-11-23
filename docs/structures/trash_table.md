# Trash Table

The Trash Table (OID 0x0D, schema 0xe0d0) is an asynchronous deletion queue.

A deleted object is reparented into this table for deferred background cleanup only when
`RefsCheckDataSetsForDeletion` finds that:

- one of the object's data stream sets holds **two or more tables** or has the set's +0x100 set; or
- for a file, under a feature bit and a condition on the delete request, its single-table sets hold more than
  5,000 rows together.

Otherwise `RefsDeleteAllMinstoreStreams` and `RefsDeleteObject` delete it in place, in the same transaction (the
Windows 11 driver, refs.sys 26100 and Insider; the ReFS 3.4 driver reparents through another routine, whose
condition is not read).

On a lab volume that deleted six objects together -- a 1 MiB file, a 100 B file, a file with three small named
streams, one with a 256 KiB named stream, a directory holding a file, and a file given a stream snapshot -- only the
snapshot file went through the Trash; the other five were deleted in place.

While a row is there, the object's data and metadata are still in place.

## Row format — a 16-byte key, the object's record as value

The key is the deleted object's own **reference**, the 16 bytes the driver keeps for it and reports, packed, as its
Windows file id: `CmsTrashTable::AddFileTable` reparents the object's table under the Trash table with this key, and
the file and directory delete paths build it from the same two words of the object (the Windows 11 driver and Insider,
read twice). For a **file** it is {u64 ordinal, u64 directory}, its FileRef; for a **directory** it is {0, its own
OID}, the form by which the driver itself tells a directory from a file. In the `ObjectRef` form the tool uses, the
key reads `<+0x08>:<+0x00>`: `0x70b:0x2` for a file, `0x705:0x0` for a directory. The value carries the object's
record as its directory held it: on the removed rows the corpus holds (three files, below), the file's record, with
its timestamps and attributes.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Ordinal | A file's ordinal in its directory (its FileRef's second half); 0 for a directory |
| 0x08 | 8 | Directory / OID | A file's directory OID; a directory's own OID |

On disk, the corpus logs hold three deletions through the Trash, all of files, and each key is the file's own
reference as its change journal (or, on a volume without one, the log row that created its name) records it. No
directory is moved to the Trash in any corpus log, so the directory form rests on the driver alone. The ReFS 3.4
driver sends only files through the Trash.

## Deletion pipeline

A delete that goes through the Trash (above) moves through three stages, the last of which runs in the background:

1. **`RefsDeleteFile` → `DeleteFileOnDisk`** (`DeleteDirectoryOnDisk` for a directory): removes the name from its parent directory B+-tree (through `RefsRemoveLink` when the file's record is split, 26100.8115) and decides whether the object goes through the Trash (`RefsCheckDataSetsForDeletion`).
2. **`MsReparentFileToTrash` → `CmsTrashTable::AddFileTable`**: Moves the object's table under the Trash Table (OID 0x0D) for deferred cleanup, keyed by the object's reference (above). Data extents and metadata remain intact at this stage.
3. **Background `TrashCleanerWorkItemMethod` → `CmsTrashTable::DeleteFileTable`**: Frees data extents and removes the file table. Runs in a background work item, queued when the transaction that moved the table into the Trash commits, and at mount for the rows left in the table (17134, 26100.9444).

## Deletes that do not use the Trash

Every other delete -- one whose stream sets do not meet that condition, files and directories alike, whatever the file's size, its record's placement or where its bytes are -- is done in place: `RefsDeleteAllMinstoreStreams` and `RefsDeleteObject` remove the object's tables in the same transaction, without staging through the trash queue.

## Observed state

The table lists no row on any readable corpus volume: most deletes never use it (above), and on the lab volume the
one object that did had left it again when the volume was imaged after its dismount, under two minutes later. What the cleaner removes stays in the page's free space, though: the Trash table's page holds the removed row
of each of the three files above (four volumes, two of them images of the same lab volume), its key the file's
reference and its value the file's record, whose creation time is the file's. A row the table still lists would
indicate a volume captured while that deletion was still in progress -- inferred from the deferred-cleanup pipeline; no
such row was observed. `deleted` lists the rows the table holds; it does not read the removed rows in its free
space.

## Forensic value

On a live or crash-captured volume, the Trash Table may contain entries for recently deleted objects that went
through it (a data stream set of two or more tables, or the row condition above) and have not yet been cleaned up.
While an entry persists, the deleted object still preserves:

- The deleted object's identity: its reference, the row's key (for a directory, its OID — enabling lookup in the
  [Object Table](object_table.md)), and its record, the row's value
- Data extents (still allocated, not yet freed)
- Its record's metadata: timestamps, attributes and SecurityId (the descriptor itself is shared, in the
  [security table](security_descriptors.md))

The Trash table is one of the ReFS deleted-file recovery methods: `deleted` lists its rows, and `deleted --trash`
shows only them, as raw key/value rows rather than recovered files. The primary method is the B+-tree node-slack
scan, with checkpoint differential and an opt-in orphan-object scan alongside.

See [Deletion Recovery](../concepts/deletion_recovery.md) for the full set and the two recovery modes.

## Version presence

Present on every format read, 3.4 to 3.14 (volumes written by Insider builds included).

## Cross-references

- [Object Table](object_table.md) — where a directory's OID resolves (a file has no OID of its own)
- [Schema Table](schema_table.md) — schema 0xe0d0
- [System OIDs](system_oids.md) — OID 0x0D

## A prior-work claim this project cannot confirm

Prior work reports that large deleted files are retained here, with the threshold set by data-run count.

The driver has a condition of that kind: for a file, under a feature bit, single-table stream sets holding more
than 5,000 rows together send it through the Trash (the second condition at the top of this page); whether those
rows are the file's data runs has not been read.

**No corpus image holds a Trash table that lists a row**, so there is nothing to measure it against on disk.
The claim is recorded and left untested rather than repeated as fact; a volume imaged mid-deletion would
settle it.

## Evidence

The OID 0x0D / schema 0xe0d0 identity and the deletion pipeline are confirmed by the decompiled driver:
`CmsTrashTable::InitializeTable` sets the OID to 0x0D and schema to 0xe0d0, and the `RefsDeleteFile → DeleteFileOnDisk →
MsReparentFileToTrash → CmsTrashTable::AddFileTable → TrashCleanerWorkItemMethod → CmsTrashTable::DeleteFileTable`
chain is decompiled end to end, with the gate that decides whether it runs (`RefsCheckDataSetsForDeletion`: 26100.9444
read twice, 26100.8115 and Insider 29574 once; 17134 reparents through `MsReparentChildTableToTrash`, its condition
not read). The key was read twice in the driver, on different builds, and checked on the three files the corpus logs show going through the Trash; every page of the corpus whose header names the Trash table was read, on the 124 readable corpus volumes (none
lists a row; four hold a removed row in their free space). The retention-by-data-run-count claim stays untested for want of a non-empty instance.

See [how this was verified](../methodology.md) to trace these statements to the exact images and measurements in `analysis/`.

<!-- findings: CT_MISC_002, FS_OTBL_RA_008 -->
