# MLog redo records

The records the [MLog](mlog.md) holds, read for what they do: the redo opcodes and the driver handler each one
calls, how a log payload's records are grouped into one action, and the time a row carries. The log's structure --
its records' four layers, the control record, where the log lives and how it is replayed -- is on the
[MLog](mlog.md) page.

## Redo opcodes

The opcode is read at `_SmsRedoRecord + 0x04` and dispatched by `CmsLogRedoQueue::PerformRedo`. Opcode
counts vary by driver build.

| Version | Distinct handler functions | Opcode values | Range | Non-handler values |
|---------|----------|--------------|-------|--------------------|
| v3.4 (Win10 17134) | 26 | 29 | 0x00–0x1C (contiguous) | 2 (0x12, 0x15 → no handler) |
| v3.14 (Win11 26100) | ~39 | 44 | 0x00–0x2B (contiguous) | 3 (0x12, 0x15 → no handler; 0x17 → explicit error) |
| v3.14 (Insider 29574) | — | 45 | 0x00–0x2C (contiguous) | 4 (0x12, 0x15, 0x2C → no handler; 0x17 → explicit error) |
| v3.14 (Insider 29659) | — | 45 | 0x00–0x2C (contiguous) | 5 (0x12, 0x15, 0x16, 0x2C → no handler; 0x17 → explicit error) |
| v3.14 (Insider 29683) | — | 46 | 0x00–0x2D (contiguous) | 5 (0x12, 0x15, 0x16, 0x2C → no handler; 0x17 → explicit error) |

The dispatched opcode ranges are **contiguous**: every in-range value has its own branch. In both versions the
branches of **0x12 and 0x15 call no handler**: they go straight to the common end of `PerformRedo`, the step every
record ends with. The driver's analysis pass (`CmsRestarter::PreAnalyzeOneRecord`) acts on 0x12, and on no other
opcode: it counts the record and raises the event `TreeUpdateRecordFound` (when that event is enabled), so 0x12 is
a **tree-update record**.
v3.14 0x17 returns NTSTATUS `0xC0000427`, the same generic unhandled-opcode error as an out-of-range value; the
v3.4 driver (17134) has no such error: an out-of-range value calls no handler. The Insider 29574 driver also accepts
0x2C and calls no handler for it; Insider 29659 and 29683 also call none for 0x16 (26100 and 29574 parse its value as a
range and do not use it).

**0x2D, a table deletion (Insider 29683).** Insider 29683 logs every table deletion with opcode 0x2D, where 26100 and the
earlier Insider builds log it with 0x0F; its replay of 0x2D is the one of 0x0F (`RedoDeleteTable`). 26100, Insider 29574
and 29659 refuse 0x2D at replay. A 0x2D record in a log is therefore a table deletion written by a driver that logs it
so, of the builds read Insider 29683 only. Read in the decompiled driver and its instructions, on 29574, 29659 and
29683; no test volume holds such a record.

Cross-version: the v3.4 core (0x00–0x1C) carries forward almost unchanged (4 renamed, 0x16 emptied of its
handler, 0x17 turned into an error, 0 removed); v3.14 adds 0x1D–0x2B (15 new values, mainly stream / table-set /
refcount).

**Which table a log is read with.** An opcode's meaning is the meaning in the driver that wrote the record, and
neither the log nor the volume records which build that was. Two values mean different things in the two tables:

| Opcode | ReFS 3.4 (17134) | ReFS 3.14 (26100, Insider) | On disk |
|--------|------------------|----------------------------|---------|
| 0x16 | `RedoReadCacheInvalidation` | no handler of its own (see the table below) | on no ReFS 3.4 or ReFS 3.14 corpus volume |
| 0x17 | `RedoGenerateChecksum` | refused (NTSTATUS 0xC0000427) | on none of them |

forefst reads a log with its volume's format table: 3.4 with the 3.4 table, 3.7 and later with the 3.14 table. A
volume upgraded from 3.4 is read with the 3.14 table: on the corpus's two such volumes the log in use holds 0x1F among
its records (a value of the 3.14 table only) and none of 0x16 and 0x17 (the two values the tables read differently):
10,456 records on `win10to11refs4g` (two images of it), with no record of an earlier log, and 885 on
`labM_after_rebuilt`.

Among the 3.14 builds read no value has two meanings: values were added (0x2C, 0x2D) or their branch emptied (0x16),
none given another operation. Three cases are not covered by a driver reading:

1. ReFS 3.7–3.13 -- no driver of those versions was read, so their names are the 3.14 driver's (the logs of the
   corpus's 3.7, 3.9 and 3.10 volumes (5) hold only values of the 3.14 table, 0x1F and 0x20 among them, which the
   3.4 table does not have);
2. a newer driver writing to an older volume without upgrading it -- a refused upgrade does not stop the mount
   (26100: the `RefsDisableVolumeUpgrade` setting), and which opcodes its writers then use is not read; the two
   tables differ on 0x16 and 0x17 only, no 26100 build read writes 0x16 with a fixed opcode, and 26100 refuses 0x17;
3. a build not read that gives a value another meaning.

`mlog --info` lists the opcodes with the builds that dispatch them, from one per-build table in the tool; a value
outside the table is labelled `UNKNOWN_0x..` and never decides a class.

### v3.14 dispatch table (46 opcode values over the builds read)

One table for every 3.14 build read: no value means two different operations among them. The four build columns say
what each build's `PerformRedo` does with the value: `handler` (the branch replays the operation -- through the
handler named, or inline, through the table set's v-table or a function of another name where the Handler column
says so), `no handler` (the branch goes to the common end), `refused` (NTSTATUS 0xC0000427, the generic
unhandled-opcode error). The 26100 column holds for
the eight Windows 11 builds read (.8115 to .9974: one dispatch). **On disk** counts the corpus's 107 ReFS 3.14
volumes whose log in use holds the value; a value at 0 is known from the driver only.

| Opcode | Handler | Category | 26100 | Insider 29574 | Insider 29659 | Insider 29683 | On disk |
|--------|---------|----------|-------|---------------|---------------|---------------|---------|
| 0x00 | OpenTableFromTablePath | Table mgmt | handler | handler | handler | handler | 107 |
| 0x01 | RedoInsertRow | B+-tree core | handler | handler | handler | handler | 107 |
| 0x02 | RedoDeleteRow | B+-tree core | handler | handler | handler | handler | 107 |
| 0x03 | RedoUpdateRow | B+-tree core | handler | handler | handler | handler | 107 |
| 0x04 | RedoUpdateDataWithRoot | B+-tree core | handler | handler | handler | handler | 107 |
| 0x05 | RedoReparentTable | Table mgmt | handler | handler | handler | handler | 90 |
| 0x06 | RedoAllocate | Allocator | handler | handler | handler | handler | 106 |
| 0x07 | RedoFree | Allocator | handler | handler | handler | handler | 107 |
| 0x08 | RedoSetRangeState | Allocator | handler | handler | handler | handler | 107 |
| 0x09 | RedoSetRangeState (shared) | Allocator | handler | handler | handler | handler | 48 |
| 0x0A | RedoDuplicateExtents | Dedup/clone | handler | handler | handler | handler | 51 |
| 0x0B | RedoModifyStreamExtent | Stream | handler | handler | handler | handler | 10 |
| 0x0C | CmsStream::StripAllChecksums | Integrity | handler | handler | handler | handler | 2 |
| 0x0D | CmsBPlusTable::SetIntegrityInformation | Integrity | handler | handler | handler | handler | 84 |
| 0x0E | RedoSetParentId | Namespace | handler | handler | handler | handler | 107 |
| 0x0F | RedoDeleteTable (written by `DeleteTable`; Insider 29683 writes a table deletion as 0x2D: the paragraph on 0x2D above) | Table mgmt | handler | handler | handler | handler | 107 |
| 0x10 | CmsBPlusTable::SetObjectRecordPayload | B+-tree core | handler | handler | handler | handler | 107 |
| 0x11 | RedoAddSchema | Schema | handler | handler | handler | handler | 4 |
| 0x12 | (no handler) — a tree-update record, read by the analysis pass | Tree update | no handler | no handler | no handler | no handler | 58 |
| 0x13 | RedoAddContainer | Container | handler | handler | handler | handler | 0 |
| 0x14 | RedoMoveContainer | Container | handler | handler | handler | handler | 0 |
| 0x15 | (no handler) | -- | no handler | no handler | no handler | no handler | 0 |
| 0x16 | no handler of its own: 26100 and Insider 29574 parse the value as a range and use it no further (the tool's name for it, `RedoSetRangeState (range variant)`, is unconfirmed) | Allocator | value parsed, not used | value parsed, not used | no handler | no handler | 0 |
| 0x17 | ERROR (NTSTATUS 0xC0000427, generic unhandled-opcode) | -- | refused | refused | refused | refused | 0 |
| 0x18 | RedoContainerCompaction | Container | handler | handler | handler | handler | 0 |
| 0x19 | RedoDeleteCompressionUnitOffsets | Compression | handler | handler | handler | handler | 0 |
| 0x1A | (no handler of its own) — `PerformRedo` inserts the row itself; the record is written by `InsertContainerCompressionHeaders`, and Insider 29659 / 29683 replay it with `RedoAddCompressionUnitOffsets` (the v3.4 handler's name) | Compression | handler | handler | handler | handler | 0 |
| 0x1B | RedoGhostExtents | Dedup/clone | handler | handler | handler | handler | 0 |
| 0x1C | RedoCompactionUnreserve | Container | handler | handler | handler | handler | 0 |
| 0x1D | CmsBPlusTable::UnlinkParentObjectId | Hard links | handler | handler | handler | handler | 12 |
| 0x1E | CmsTableSetBase::PrepareEntryForMerge | Table set | handler | handler | handler | handler | 2 |
| 0x1F | RedoUpdateStreamSummary | Stream | handler | handler | handler | handler | 107 |
| 0x20 | CmsStream::UpdateStreamUserPayload | Stream | handler | handler | handler | handler | 73 |
| 0x21 | RedoStreamPersistFastRunInsertion | Stream | handler | handler | handler | handler | 29 |
| 0x22 | RedoTableSetSummaryUpdate | Table set | handler | handler | handler | handler | 0 |
| 0x23 | RedoTableSetShadowTreeUpdate | Table set | handler | handler | handler | handler | 0 |
| 0x24 | RedoTableSetCommitMerge | Table set | handler | handler | handler | handler | 2 |
| 0x25 | Weak-reference purge of a table set: replayed through the table set's own handler (vtable +0x08); written by `LogRedoForWeakRefPurge`; Insider 29659 / 29683 name the handler `RedoTableSetWeakRefPurge` | Table set | handler | handler | handler | handler | 0 |
| 0x26 | RedoTableSetStrongRefMerge | Table set | handler | handler | handler | handler | 2 |
| 0x27 | RedoSetDefaultCompressionParameters | Compression | handler | handler | handler | handler | 10 |
| 0x28 | CmsBlockRefcount::BreakWeakReferences | Dedup/clone | handler | handler | handler | handler | 0 |
| 0x29 | RedoDuplicateCluster | Dedup/clone | handler | handler | handler | handler | 3 |
| 0x2A | RedoChangeRangeEncryptedState | Encryption | handler | handler | handler | handler | 13 |
| 0x2B | Strong-reference merge (single) of a table set: replayed through the table set's own handler (vtable +0x18); written by `LogRedoForStrongRefMergeSingle`; Insider 29659 / 29683 name the handler `RedoTableSetStrongRefMergeSingle` | Table set | handler | handler | handler | handler | 0 |
| 0x2C | (no handler on the Insider builds; refused on 26100) | -- | refused | no handler | no handler | no handler | 0 |
| 0x2D | RedoDeleteTable, as 0x0F (written by `DeleteTable` on Insider 29683, which no longer writes 0x0F) | Table mgmt | refused | refused | refused | handler | 0 |

On every 3.14 build read, 0x17 returns NTSTATUS 0xC0000427 (the same generic unhandled-opcode error as an
out-of-range value). On 26100, 0x25 and 0x2B dispatch through the `CmsTableSetBase` v-table; Insider 29659 / 29683 call
handlers of their own (the names in the table), and the records' writers name the operation on both.

The v3.4 (17134) table is this one up to 0x1C, except for the values named above: 0x00 `OpenTable`, 0x0C
`RedoStripMetadataStreamExtent`, 0x0D `RedoSetIntegrity` and 0x18 `RedoContainerCompression` (the same operations
under other names), 0x1A `RedoAddCompressionUnitOffsets`, 0x16 `RedoReadCacheInvalidation` and 0x17
`RedoGenerateChecksum`.

## Transaction structure

A transaction's first record carries the **transaction-start flag** (record flags bit 0, at record+0x2C — the
same flag the driver's replay tests) and its last record the **commit flag** (bit 1, set by
`CmsMemLog::MergeTxLog`). A data record's payload holds one or more merged redo blocks; on the volumes measured
each block held one transaction, so a block's records run from a start flag to a commit flag.

### Event timestamps — the time a row carries

Some operations carry their own time and some do not. A **create or write** embeds the object's updated
`$STANDARD_INFORMATION` in its own records, so a time reads straight out of the transaction: the value that
transaction wrote.

On the v3.4 volume measured, a **rename or a permanent delete carried no inline time**: the object's new `$SI`
followed as a *separate* `$SI`-update in the **next** log block, whose MACB timestamps sit at that block's offset
**+0x140** (6 of 6 events matched). This has not been checked on a 3.14 volume.

`mlog --parse` gives a row the latest time its payload's records carry (a `$SI` update gives the latest of its four
times; a volume-information update its write time). Only when the payload carries none,
and its action is a rename, a move, a deletion, a name removal or a table move, does it take the time from a
`$SI`-update in the next block (the CSV's `TimeSource` says which). A payload can merge up to 15 redo blocks, so a
row's time belongs to one of them, not necessarily to the action the row names. The same time flows into
`timeline`.

### Concrete actions — grouping redo opcodes into what a user did

One file operation is **not** one redo record. ReFS writes a file operation as a cluster of low-level B+-tree
redo opcodes (open a table, insert a row, set a parent id, update a stream summary, allocate clusters…), often
split across several transactions. `forefst mlog --parse` groups the opcodes of each log payload (which can merge up
to 15 transactions) into a single **concrete action**: a move or a rename from the file's own records (its name link replaced) or the
directories of the names removed and added, a deletion only from a record that destroys a table (`RedoDeleteTable`)
— a bare `RedoDeleteRow` or reparent record decides nothing on its own. Every action is still backed by its raw redo records; `mlog --parse
-v` prints each one as `opcode  name  target_oid  @PLCN+offset  key`, so any field can be verified against the
raw disk bytes. The action is **derived** from the records' opcode pattern (`mlog --info` lists the rules), not
read from the log. Actions are reported in two groups.

**File operations — what a user did:**

| Action | How it is decided | Notes |
|--------|-------------------|-------|
| CREATE | a NEW name entry no removed name pairs with (where the payload also removes a name, only names whose file lost them -- its link row removed) — or the fragment that opens the table and sets its parent | new files, new directories, copies. A hard link also inserts a name and is not separable from CREATE per payload (the `-v` records distinguish it). |
| DATA_OR_REPARSE_WRITE | a non-name row inserted together with an object-record or data update (`InsertRow` + `SetObjectRecordPayload`/`UpdateDataWithRoot`) | a data write, a reparse-point write or a marked-file creation: the records do not tell which. A file created in the same payload is CREATE. Data updates with no row insert show as MODIFY, or as STREAM_UPD when the payload holds a stream-summary record. |
| RENAME | one file's name changed in the **same** directory, read from its own records ("MOVE vs RENAME" below) | shown as `(same parent 0x..: old → new)`; decided by the directories alone: `(names not paired; same parent 0x..)`. |
| MOVE | moved to **another** directory, the name kept | shown as `(parent 0x<old> → 0x<new>)`; decided by the directories alone: `(names not paired; parent 0x<old> → 0x<new>)`, which says nothing of the name; with more than one directory on a side, `(names not paired; parents undetermined: old .., new ..)`. |
| MOVE_AND_RENAME | moved to another directory under a **new name** | shown as `(parent 0x<old> → 0x<new>: old → new)`; a deletion to the Recycle Bin is one. |
| MOVE_OR_RENAME | names removed and added that the file's records do not pair (a ReFS 3.4 directory), whose directory sets **overlap without being equal** | the records do not say which; shown as `(parents undetermined: old .., new ..)`. |
| DELETE | the object's **own B+-tree table is destroyed** (`RedoDeleteTable`: 0x0F; 0x2D on Insider 29683) | shown as `(object table destroyed)`. See "DELETE vs a row removal" below. |

**Low-level / metadata records — the B+-tree redo that accompanies the file operations (kept as facts):**

| Group | Opcodes | Meaning |
|-------|---------|---------|
| STREAM_UPD | UpdateStreamSummary / UserPayload (0x1F/0x20) | a payload with a stream-summary record and no name change, table deletion, create fragment or reparent; it can hold a data write too |
| TABLE_REPARENTED | RedoReparentTable (0x05) that moves no name | the records do not show a move or rename: a table moved out of its name row (making a hard link does it) or into another table |
| ENTRY_REMOVE | a name removed with no new name for it, no table destroyed (`no entry added for it`); or a row removed that is not a directory entry (`a row removed, not a directory entry`) | the first: the deletion of that name (a file's or one of its hard links'); whether the file's own table was destroyed is shown only by a DELETE row |
| ALLOCATE | RedoAllocate (0x06) with no row insert | cluster allocation; a payload that only frees clusters (0x07) is MODIFY |
| CONTAINER | AddContainer / MoveContainer (0x13/0x14) | container-table change |
| TREE_UPDATE | tree-update records (0x12) and nothing else | no redo handler replays them; the driver's analysis pass reads them. In any other transaction 0x12 and 0x15 (no handler either) do not decide the action |
| DEDUP | BreakWeakReferences / DuplicateCluster (0x28/0x29) | block-clone / dedup |
| EXTENT_MOD | DuplicateExtents / ModifyStreamExtent / FastRunInsertion (0x0A/0x0B/0x21) | extent-level change |
| MODIFY | UpdateRow / UpdateData / SetRangeState / SetObjectRecordPayload / … | metadata-or-data update with no new/removed name row (includes timestamp changes) |
| UPDATE / INSERT / OP | a non-name row swap / a lone insert / an unclassified combination | |

What two of the classes stood for on one public sample volume, against the log of the workload that made it (one
volume, one workload: a correspondence, not a rule):

- about three DATA_OR_REPARSE_WRITE rows in four fall within 2 s of a symbolic link's creation, and a few within 2 s
  of a data write or of a marked file's creation;
- of the TABLE_REPARENTED rows, about one in eight falls within 2 s of a move, and about two in three are names the
  workload made hard links, which moves the record out of its name row.

#### MOVE vs RENAME — read from the file's own records

A rename and a move look almost identical in the log: the old name entry is removed (`RedoDeleteRow`) and a new one
inserted (`RedoInsertRow`) -- or, for a file still embedded in its name row, `RedoReparentTable` alone moves it to the
new name -- and the same records serve a rename and a move. Nor do the directories of a payload's name entries decide
it: a payload can merge up to 15 redo blocks, and moving a file out of its name row (its first move or hard link)
writes its name back into the same directory first. forefst reads one file's change from that file's own records:

- a file with its own record: its `$OBJ_LINK` row (the parent and the name, see [OBJ_LINK](../attributes/OBJ_LINK.md))
  is deleted as the old parent and name and inserted as the new, in one table and one transaction;
- a file still embedded in its name row: `RedoReparentTable` moves its table from the old name row to the new one --
  the record's path is the old place, value 0 the new parent's table path, value 1 the new row key
  (`CmsEmbeddedComposite::Reparent` logs it so on the builds read: 17134, 26100.9444, Insider 29683).

The same directory: **RENAME**; another directory, the name kept: **MOVE**; both: **MOVE_AND_RENAME**. A pair is read
inside its own transaction first, so a name freed in one transaction and taken in another (an atomic save, a log
rotation) hides neither file's change; the names left over are followed over the payload: a name inserted and removed
again, or removed and inserted again, is no change. A name removed with no new name for it is **ENTRY_REMOVE**. Where
the file's records give no pair (a ReFS 3.4 directory carries no `$OBJ_LINK`; on the corpus, a few hundred rows of 3.4
volumes and about a hundred of 3.14 volumes), the
directories of the names removed and added decide, and the detail says `names not paired`: the same RENAME, others
MOVE, sets that overlap without being equal **MOVE_OR_RENAME**. Where a side names more than one directory, both sets
are shown (`parents undetermined: old .., new ..`, or `same parents ..` when they are equal), never one picked. Such a
row does not show that the two names are one file.

A name-entry record's directory is the table the record applies to. A record that carries a table path names it:
component 0 of the path, the table's object id at component + 0x14. A record without a path (table path length 0 --
the new-name `InsertRow` of a rename is one) applies to the table the driver's redo pass keeps **current**
(`CmsLogRedoQueue::PerformRedo`): the previous record's. The redo pass leaves no table current after a record whose
branch uses no table (0x11-0x16, 0x18, 0x19, 0x1A, 0x1C and, on ReFS 3.14, 0x27), after a table deletion
(`RedoDeleteTable`), after a table-set commit merge (0x24, `RedoTableSetCommitMerge`) and after a value no build
dispatches (read on 26100.8115 and .9818, Insider 29574 and 29683, and 17134).

The current table belongs to a redo queue and is kept from one redo block to the next: a block whose first record
does not start a transaction stays on the previous block's queue (`RedoOneRecordBlock`, read on 26100.9818), so the
table carries into it -- forefst follows it from the previous block of the payload, and from the previous payload when that
payload is the log record right before it. A block that starts a transaction goes to a queue the driver picks by
object id, whose table the log does not record: a record there that names no table is left undetermined. `mlog
--parse -v` marks a table taken from an earlier record `(inherited)` and an undetermined one `(none)`. The record is the
directory's **own** name entry only when that table's path has one component: a deeper path names a table embedded
in one of the directory's rows -- the name rows of a file's alternate data streams are written so -- and such a row is
not one side of a rename or a move. The record's +0x20 does not name its table: it is the allocator clock (see the
record layout above), and one value is shared by records of different tables.

A row is one log payload. When the payload holds several changes, the class names the first and the detail names
the others after `also`; a row shows its name in the directory that name entry was in (today's path of it). The detail
is for reading: names can hold its separators (`, `, `→`); `--json`'s `Entries` is the machine form.

Checked against two independent operation logs -- the public sample's Generate-FSActivity logs and a lab volume's
replay log: every move and rename forefst reads that the log also holds (698 and 242) has the class the log's paths
give, and no name forefst reads as removed is one the log renames or moves away; where the log never renames, moves
or deletes the directory, the directory a row shows is the log's (472 and 164 rows; one more row on the lab volume is
an action after its replay log, and its `$I` record gives the directory shown). A lab script on a third volume agrees
for its moves, renames, Recycle Bin deletions and deletions. Not covered by these checks: the rows the directories
alone decide (`names not paired`) -- neither log holds one.

#### DELETE vs a rename/move's row removal

`RedoDeleteRow` removes a single B+-tree row — and it fires on the OLD name entry of a rename and the source of a
move, not only on a deletion. A bare `DeleteRow` is therefore **not** evidence a file was deleted. forefst reports
**DELETE only when the object's own table is destroyed** (`RedoDeleteTable`: 0x0F; Insider 29683 logs it as 0x2D;
the handler the volume's dispatch table names). The old name of a move or rename is part of that row (above); a name
removed with no new name for it is **ENTRY_REMOVE**: that name was deleted -- a file's, or one of its hard links' --
and whether the file's own table was destroyed is shown only by a DELETE row.

### Timestamp extraction

MLog records do not have a dedicated timestamp field in their headers. A record is dated by the times its values
hold, read where the value's form puts them; a record whose value holds no time there is not dated:

| Record | Value | Times read |
|--------|-------|------------|
| InsertRow (0x01) of an index entry (72 or 84 bytes) | value 1 | its four times, `+0x10` to `+0x28` |
| InsertRow (0x01) of a name row's embedded record, or of a directory's own row (row key 0x30 / 0x10) | value 1 | its `$SI` times, `+0x28` to `+0x40` |
| UpdateDataWithRoot (0x04) | value 0, a `$SI` | its four times, `+0x00` to `+0x18` |
| UpdateRow (0x03) of a whole row (two values: the key, the row) | value 1 | by the row: an index entry (72 or 84 bytes) its four times, `+0x10` to `+0x28`; the volume-information row (key 0x0520) `+0xA0`, else `+0x90`; a name row's embedded record or a directory's own row (key 0x30 / 0x10) its `$SI` times, `+0x28` to `+0x40` |

Of the times read, the latest plausible FILETIME is the record's time (between 1968 and 2108); on the
volume-information row, `+0xA0` comes first. The row of a log payload takes the latest of its records' times.

An UpdateRow with a third value rewrites part of a row: refs.sys passes value 2 to `CmsBPlusTable::UpdateInIndex` as
the offset in the row where value 1 goes (26100.9818). Value 1 is then a fragment -- on the corpus, the size fields
(`+0x10`) or the inline bytes (`+0x3C`) of a `$DATA` or named-stream row -- and holds no time: such a record is not
dated.

On a volume-information row, UpdateRow's `+0xA0` is the time of the last read-write mount and `+0x90` the volume's
format time, which is why `+0xA0` is tried first: `+0x90` would date every volume-information update at the moment
the volume was created. Measured on a lab volume: the last such record reads the volume's own last read-write mount
time, to the second.

Timestamps are Windows FILETIME format (100-ns intervals since 1601-01-01). Not all transactions contain
timestamps — system-level operations (allocator, container table) typically have no embedded time.

A timestamp read here is a value the transaction wrote into the metadata — a `$SI` time, a volume-information
time — not the time the log record was written. For an UpdateDataWithRoot that carries a `$SI`, the latest of its
times is taken: after a call that set the times back, that is the change time at `+0x10`, the moment of the call when
the program leaves that field to the file system (a plain copy carries its source's).

### Key component layout

InsertRow records carry structured key data. Component[0] of the key path has this 28-byte layout:

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 4 | schema0 (u32) — table schema (e.g. 0xe030 = ObjectTable) |
| 0x04 | 4 | schema1 (u32) — the table's schema (e.g. 0x0130, a directory's table) |
| 0x08 | 12 | zeros |
| 0x14 | 8 | the table's object id (u64; `ObjectIdFromRedoHelper` reads it here) — for a name row, the directory whose table holds it, not the file |

The schema pair identifies the table the record targets. Common pairs: 0xe030/0x0130 (a directory's table, reached
through the Object Table) and 0xe030/0x0160 (the reparse index).

## Operation patterns from prior work, re-measured

Lee et al., "Forensic analysis of ReFS journaling" (Forensic Science International: Digital Investigation, 2021),
published seven opcode sequences, one per filesystem operation. Re-running them against v3.4 images shows how well
the published patterns hold on other images:

- three hold in their first opcodes;
- two name the wrong operation (a write, a move);
- one carries the right opcodes in a different order;
- one does not occur as a single transaction at all.

| Operation, as published | What the v3.4 images show |
|---|---|
| directory creation `0x00 0x00 0x04 0x10 …` | **holds** — nearly every transaction that begins `OPEN OPEN` continues `UPD_DATA SET_OBJREC` |
| file deletion `0x0F 0x02 0x0F 0x02 0x04` | **dominant form** — most deletions begin `DEL_TABLE DELETE DEL_TABLE DELETE`; some begin `DELETE DEL_TABLE DELETE DEL_TABLE` |
| directory renaming `0x02 0x02 0x01 0x01 0x04 0x04` | **core confirmed** — `DELETE DELETE INSERT INSERT` |
| file creation `0x01 0x04 0x01 0x00 …` | **mislabelled** — this sequence is a **write** |
| file renaming `0x02 0x05 0x01 0x04 0x04` | first four match a **move** |
| directory deletion `0x02 0x02 0x0F 0x02 …` | same opcodes, **different order** — `DEL_TABLE DELETE …` dominates |
| file modification `0x06 0x04 0x04 0x04 0x04 0x08` | **not found** as one transaction; its parts occur separately |

For an examiner, this means that a sequence identifies an operation only up to its first few
opcodes, and that a published label may name the wrong operation. `forefst mlog --parse` classifies from
the opcodes it actually reads rather than from a fixed table of sequences.

## Cross-references

- [MLog](mlog.md) — the log's structure: the four record layers, the control record, the log's place, recovery
- [Artifact timeline](../concepts/artifact_timeline.md) — how `timeline` merges the MLog rows with the change journal
  and the `$SI` times
- [Timestomping detection](../concepts/timestomp_detection.md) — the log's record of each call that set a time

## Evidence

The redo opcode dispatch (each value branching to a PDB-named handler, except the values listed as calling none) is
decompiled from `CmsLogRedoQueue::PerformRedo`. The opcode ranges, the published operation patterns and their
re-measurement, and the page's other statements are registered findings, each with its own evidence tier and witness
in the claim register.

The counts behind the text:

- opcodes 0x16 and 0x17: on none of the 124 ReFS corpus volumes, of every format (the 9 of ReFS 3.4 included); the
  volumes upgraded from 3.4 hold 10,456 (`win10to11refs4g`, two images) and 885 (`labM_after_rebuilt`) records in the
  logs in use;
- the two classes on `win11refstestmftecmd`: of 159 DATA_OR_REPARSE_WRITE rows, 121 fall within 2 s of a symbolic
  link's creation, 3 of a data write and 2 of a marked file's creation; of 200 TABLE_REPARENTED rows, 24 fall within
  2 s of a move and 132 are names the workload made hard links;
- names not paired from the file's records: 406 rows of 3.4 volumes and 119 of 3.14 volumes;
- UpdateRow `+0xA0`, on `lab314_main_step3_dirty`: the last such record reads `2026-09-12 17:21:28`, the volume's
  `Last mount (rw): 2026-09-12 17:21:28.1422270`;
- the rename and delete times from the next block's `$SI`-update: the bi0sCTF-2024 v3.4 image, 6 of 6 events;
  on the four public v3.14 samples that rule supplies the time of 8 of 14,131 rows, not checked against a log;
- the prior-work patterns: directory creation and file deletion re-measured on two v3.4 images (`win10refs2g`,
  `win10refsmini`): 61 and 7 transactions begin `0x00 0x00 0x04 0x10` (61 of 62 and 7 of 8 of those that begin
  `0x00 0x00`), 66 and 1 begin `0x0F 0x02 0x0F 0x02` (on `win10refs2g`, 26 begin `0x02 0x0F 0x02 0x0F`); the other five
  rows (directory renaming 22×, the write 163×, the move 23×, the deletion order, the modification's parts) were
  counted on three v3.4 images with a record budget that dropped each block's last record, and are not re-measured.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

<!-- findings: AP_EVNT_001, AP_EVNT_002, AP_EVNT_003, AP_EVNT_004, AP_EVNT_005, AP_EVNT_006, AP_EVNT_007, AP_REDO_001, AP_REDO_002, AP_REDO_003, AP_REDO_004, AP_REDO_005, AP_REDO_006, AP_REDO_007, AP_REDO_008, AP_REDO_009, AP_REDO_010, AP_REDO_011, AP_REDO_012, AP_REDO_013, AP_REDO_014, AP_REDO_015, AP_REDO_016, AP_REDO_017, AP_REDO_018, AP_REDO_019, AP_REDO_020, AP_REDO_021, AP_REDO_022, AP_REDO_023, AP_REDO_024, AP_REDO_025, AP_REDO_026, AP_REDO_027, AP_REDO_028, AP_REDO_029, AP_REDO_030, AP_REDO_031, AP_REDO_032, AP_REDO_033, AP_REDO_034, AP_REDO_035, AP_REDO_036, AP_REDO_037, AP_REDO_038, AP_REDO_039, AP_REDO_040 -->
