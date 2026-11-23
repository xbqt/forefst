# USN Journal

The USN (Update Sequence Number) Journal records changes to files and directories on the volume, for as long as
the volume has a journal.

ReFS uses the `USN_RECORD_V3` format with 128-bit file IDs (NTFS uses the older `USN_RECORD_V2`
form with a 64-bit file reference).

A freshly formatted data volume has **no journal**: one must be created, for example with
`fsutil usn createjournal`.

**On-disk ReFS journal records are version 3.** ReFS's 128-bit file IDs require the `USN_RECORD_V3` layout;
`fsutil usn queryjournal` on ReFS reports `Maximum record version supported : 3`.

Version 2 (NTFS's 64-bit form) and version 4 (`USN_RECORD_V4`, the NTFS-only range-tracking / extent record —
`fsutil usn enablerangetracking` refuses a ReFS volume with *"A local NTFS volume is required for this
operation"*) do **not** occur on a ReFS journal.

The parser implements only the **V3 field layout**. A V2 or V4 record (a non-ReFS journal, or crafted or damaged
input) is stepped over as a record and **not decoded** — V3 offsets would fabricate its fields — and the tool
states how many such records it refused.

## USN_RECORD_V3 layout

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Record length (u32) | Total record size = `pad8(0x4C + UTF-16 name byte length)`: at least 80 (0x50), every record 8-byte aligned, **80–408 B** observed (see below) |
| 0x04 | 2 | Major version (u16) | 3 on every ReFS record (the 128-bit File ID requires the V3 layout) |
| 0x06 | 2 | Minor version (u16) | Always 0 |
| 0x08 | 16 | File ID (u128) | See 128-bit File ID structure below |
| 0x18 | 16 | Parent file ID (u128) | Same format: the parent directory **when the record was written** (see below) |
| 0x28 | 8 | USN (u64) | The record's own USN = its **virtual byte offset** in the journal (see below) |
| 0x30 | 8 | Timestamp (FILETIME) | 100 ns ticks since 1601-01-01 |
| 0x38 | 4 | Reason (u32) | See Reason codes below |
| 0x3C | 4 | Source info (u32) | The USN source flags (`USN_SOURCE_*`) a process set on its handle with `FSCTL_MARK_HANDLE`; **0** where none was set (see below) |
| 0x40 | 4 | Security ID (u32) | **0** in every ReFS record: refs.sys writes 0 there (`RefsPostUsnChange`) |
| 0x44 | 4 | File attributes (u32) | The file's WIN32_FILE_ATTRIBUTE flags when the record was written |
| 0x48 | 2 | File name length (u16) | In bytes |
| 0x4A | 2 | File name offset (u16) | Offset from record start |
| 0x4C | var | File name (UTF-16LE) | — |

**Record length.** The size is dominated by the name, and there is no ceiling below the 592 B that a 255-character
name gives. On the Insider boot volume measured (two captures of it) the maximum is **408 B** and more than a
thousand records exceed 312 B in each capture. The long ones are legitimate WinSxS component names, so do not
treat a record above 312 B as malformed.

**Parent file ID.** Unlike the File ID at 0x08 — the file's fixed identity — it tracks where the name lives, so it
**changes when the file is moved** to another directory. Its ordinal (lower 8 bytes) is always **0**: a directory
is addressed as `OID:0`, so the parent reference reduces to the parent directory's own OID. It can be **absent**:
a few hundred records on each of three lab volumes carry an empty name AND parent OID `0x0`, so a reader must
handle a record with neither.

**USN.** Monotonic **within one journal instance**, and it can far exceed the `$J` stream size because the
journal is an in-place ring (below). It is **not globally unique on the volume**: `fsutil usn createjournal` over
an existing journal restarts numbering at 0 **without changing the UsnJournalId**, so USNs are reused (a
`deletejournal` followed by `createjournal` gives a new id). Measured on a lab volume:
Windows' own `fsutil queryjournal` before and after shows the same journal id, with `Next Usn 0` after the
restart. After such a restart a file's `$SI+0x40` LastUsn may point at **another object's** record: a few files
do, and a few dozen more resolve to no record at all.

**Source info.** refs.sys copies the flags from the handle into the record (`RefsMarkHandle` -> `RefsCommonWrite`
-> `RefsWriteUsnJournalChanges`, read on 26100.8115, 26100.9444 and Insider 29574). No corpus journal carries a
non-zero value, which shows that no process of the corpus set them, not that the field is unused.

## 128-bit File ID structure

| Component | Size | Meaning |
|-----------|------|---------|
| First 8 bytes (`+0x08`) | u64 | Per-directory entry **ordinal** — monotonically allocated, **never reused after deletion** (a deleted ordinal stays a permanent gap) |
| Second 8 bytes (`+0x10`) | u64 | For a file, the **creation (home) directory's** Object Table OID — the directory the file was born in, frozen for the life of the object. For a directory, its own OID (with ordinal 0) |

Read them in that order **on disk**: record 0 of a lab volume's journal runs
`58 00 00 00 | 03 00 | 00 00 | 00*8 | 0c 07 …`, i.e. `+0x08` is the ordinal `0` and `+0x10` is the OID `0x70c`;
the parent pair at `+0x18`/`+0x20` is likewise ordinal `0` then parent OID `0x705`.

"Upper/lower half of a u128" describes the numeric value, not the byte order, and reading the first 8 bytes as
the OID gets both fields wrong.

This File ID is exactly the `(HomeOID, ordinal)` FileRef described in [File IDs](../concepts/file_ids.md).
The upper 8 bytes name the creation directory and the lower 8 bytes the object's ordinal there:

- on a volume with hard-link support, that directory's [B+-tree](btree_node.md) holds the file's record — in its
  name row, or in a type-0x40 backing once a move or a hard link split the record out of it;
- on a volume without hard-link support, a moved file's record moves whole to the new directory, and the creation
  directory keeps a forwarding row (type 0x20) to it.

The File ID is **stable in two senses**. It is *temporally* stable — the ordinal is never re-used within
its directory, so a deleted file's File ID is never reassigned to a later file. It is also *spatially*
stable — **renaming or moving a file does not change its File ID.** The upper half is the *creation*
directory, not the current parent, so when a file is moved the File ID (0x08) stays fixed while the Parent
file ID (0x18) changes to the new directory. Across every real cross-directory move measured on the corpus's v3.14
volumes, the File ID was unchanged. A USN record therefore points to the same file across the whole
journal, through any number of renames and moves.

## Reason codes

Reason codes are bitmask flags. A single record can combine multiple flags (e.g.
`0x80000100` = FILE_CREATE + CLOSE).

| Code (hex) | Name | Description |
|------------|------|-------------|
| 0x00000001 | DATA_OVERWRITE | Default data stream content overwritten |
| 0x00000002 | DATA_EXTEND | Default data stream extended |
| 0x00000004 | DATA_TRUNCATION | Default data stream truncated |
| 0x00000010 | NAMED_DATA_OVERWRITE | Named data stream (ADS) overwritten |
| 0x00000020 | NAMED_DATA_EXTEND | Named data stream extended |
| 0x00000040 | NAMED_DATA_TRUNCATION | Named data stream truncated |
| 0x00000100 | FILE_CREATE | File or directory creation |
| 0x00000200 | FILE_DELETE | File or directory deleted |
| 0x00000400 | EA_CHANGE | Extended attributes changed |
| 0x00000800 | SECURITY_CHANGE | Security descriptor (ACL) changed |
| 0x00001000 | RENAME_OLD_NAME | Source name in rename operation |
| 0x00002000 | RENAME_NEW_NAME | Target name in rename operation |
| 0x00004000 | INDEXABLE_CHANGE | Content indexing attribute changed |
| 0x00008000 | BASIC_INFO_CHANGE | Timestamps or file attributes changed |
| 0x00010000 | HARD_LINK_CHANGE | Hard link count changed |
| 0x00020000 | COMPRESSION_CHANGE | Compression state changed |
| 0x00040000 | ENCRYPTION_CHANGE | EFS encryption state changed |
| 0x00080000 | OBJECT_ID_CHANGE | Object ID changed |
| 0x00100000 | REPARSE_POINT_CHANGE | Reparse point set or removed |
| 0x00200000 | STREAM_CHANGE | Named data stream added or removed |
| 0x00400000 | TRANSACTED_CHANGE | Change within a TxF transaction |
| 0x00800000 | INTEGRITY_CHANGE | Data integrity attribute changed |
| 0x80000000 | CLOSE | Handle closed (OR-ed with the final reason) |

## Forensic patterns

An operation is identified by its combination of reason codes, not by a single flag:

| Operation | USN signature |
|-----------|---------------|
| Rename (same directory) | Two records, RENAME_OLD_NAME (0x1000) with the old name, then RENAME_NEW_NAME (0x2000) with the new; same File ID **and** same Parent file ID, only the name differs |
| Move (to another directory) | RENAME_OLD_NAME + RENAME_NEW_NAME; **same File ID**, but the **Parent file ID changes** (old directory → new directory) — the file's identity is preserved, only its location moves |
| Sparse flag set | Basic info change (0x8000); file attributes change from 0x20 to 0x220 |
| EFS encrypt/decrypt | Transient `EFS0.LOG` in system directory (OID 0x701); reason 0x40000 |
| $RECYCLE.BIN creation | Not a deletion signal: on the test volume whose 23 captures were kept, `$RECYCLE.BIN` is in the root from the first capture, before any file was deleted |
| Junction creation | Reparse point change (0x100000) as a separate event |
| Symlink creation | Reparse change combined with create (0x100100) |
| ADS on symlink | No record: writing an ADS to a symlink fails on ReFS (Windows refuses it on NTFS too) |

## Storage location

The Change Journal is stored as a file entry inside OID 0x520, the **FS Metadata directory** — the
ReFS equivalent of NTFS `$Extend` (see [System OIDs](system_oids.md)). When journaling is active a
type 0x30 B+-tree row appears with key `"Change Journal"` (UTF-16LE). Fresh volumes have no such
entry — it is created by `RefsCreateUsnJournal` and removed by `RefsDeleteUsnJournal`.

### Change Journal file entry structure

The "Change Journal" filename entry in OID 0x520 carries a `stream_count` field (3 on v3.14). Its value
length is **704 B on most volumes that have one**; the other lengths measured are 856 B, 3016 B, 720 B, 800 B and
3576 B. The value holds three sub-records after the standard
directory-entry header (the embedded sub-record markers are described in
[Directory Entries](directory_entries.md)). **Their offsets are not fixed** — locate them by walking the
records, never by seeking a constant:

| Sub-record | Type | Identified by | Content |
|------------|------|---------------|---------|
| 1 | Multi-instance (0x80000002) | type `0x000E0080`, sub_id `0x8` | A 40-byte value with **no node header and no extents** — stream-set metadata, not `$J` |
| 2 | Multi-instance (0x80000002) | type `0x000E0080`, sub_id `0x1000` | **The `$J` extents** — its value *is* the extent node (hdr `0x88`, level 0) |
| 3 | Single-instance (0x80000001) | type `0xF0` | **`$Max`** — a 44-byte value, at content `+0x280` / `+0x290` / `+0x150` depending on layout |

The `$J` data stream holds the `USN_RECORD_V3` records; it is extent-backed. The
`$Max` stream holds the journal size parameters: it is the type-0xF0 attribute (single-instance marker
0x80000001) on the Change Journal file, which `RefsSetupUsnJournal` creates unnamed — not the logged utility
stream, type 0x100, which carries `$EFS`. Its place in the value varies with the layout (the table above).

The `$Max` value is 44 bytes: the 12-byte sub-record header, then four u64 fields. It is stored inline (it has no
extents), and its fields start at `+0x0C`, so a read on 8-byte boundaries from the start of the value misses every
one of them by four bytes.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | 0x20 (32): the four fields |
| 0x08 | 4 | Content offset | 0x0C, on every journal measured |
| 0x0C | 8 | MaximumSize | the journal's configured size: equal to the `$J` allocation on every journal measured (32, 64 and 128 MiB) |
| 0x14 | 8 | AllocationDelta | 0 on every journal measured |
| 0x1C | 8 | UsnJournalID | FILETIME-shaped; the same across states of one volume, different between volumes |
| 0x24 | 8 | LowestValidUsn | named after the NTFS `$Max` field (the journal's lowest valid USN); its value is not measured here |

`$J` is a **bounded rolling log**: it is pre-allocated to a fixed size set by `$Max` (at least 32 MiB, the
driver's floor; the corpus holds 32, 64 and 128 MiB journals) and, once full, the oldest records are overwritten
**in place** as new ones are appended (observed: the ring below) — so once it has wrapped, its records fill the
entire allocation. forefst therefore reads the **whole allocated window** (every extent),
not a shorter "logical size" — the two multi-instance markers each carry a fixed data-stream *type* tag
(`0x000E0080` = 917,632), not a byte length, and capping the read at that constant would truncate every
journal larger than ~896 KiB.

The journal does nonetheless **declare its own lengths**, in the embedded `$DATA` row whose inline-header
offset (value+0x00) is `0x88`: allocated size, stream size, valid data length and disk allocation at
`+0x30`, `+0x38`, `+0x40`, `+0x48`. On all 21 corpus volumes that have a journal, exactly one row matches
and **all four equal the sum of the `$J` extents' clusters** — across 32, 64 and 128 MiB allocations, both
cluster sizes and a 4Kn volume. Reading the whole allocation is still the right thing for recovery, since
records fill it; but a declared length that *disagrees* with the allocation is evidence that the
declaration was truncated or edited, and `usn --info` reports both the declared values and any mismatch.

Each record is self-describing (a record length and its own USN).

**`$J` is framed in 4 KiB pages, and a record never straddles one.** Over the journals measured, **no
record crosses a 4 KiB boundary**. When the next record would not fit in the remaining bytes of a page, the
writer zero-pads and starts it at the next boundary: every inter-record gap measured is smaller than 4096 B and
ends exactly on a 4 KiB boundary, and in all but one the record that follows would not have fitted in the gap.

A reader that walks record-to-record by declared length alone will land in padding; skip to the next 4 KiB
boundary instead.

A partially-filled journal's tail is **not simply zeros** either: it can hold records of an earlier numbering (a
journal created again restarts at USN 0 over the old one, see *Recreation* below), so 'the zero tail is skipped'
must not be read as 'everything after the last record is empty'.

A record's USN is its **virtual byte offset** in `$J` (its file offset until the journal wraps), so a file's
`LastUsn` (`$SI+0x40`) names that file's most recent record, and the record is found in the journal **while it is
still inside the live window**; only changes older than the window's oldest surviving record have been
overwritten and are gone.

> **The journal is an in-place ring.** A record whose USN is *X* sits at byte offset *X* **modulo the allocation**,
> the extents begin at file VCN 0, and old records are overwritten where they lie — the buffer is never trimmed
> from the front.
>
> The practical consequences:
>
> - the whole allocation must be read;
> - **byte order is not time order**, because after a wrap the newest records sit at the *start* of the buffer
>   and the oldest in the middle;
> - a highest USN larger than the stream size is normal rather than a sign of damage.
>
> On the one corpus volume whose journal has wrapped, the buffer holds two generations side by side — the older
> one filling the end of the window, the newer one its start up to the write head — and every one of its records
> sits exactly at its USN modulo that window.

**The USN orders the writes; the times do not.** A record's time comes from the system clock when it is written,
and the clock can step back. On one corpus volume it stepped back six times inside one wrapped USN sequence (one step
of about an hour and five of about nine, at records written during boot), and about a third of the journal's
records are dated before the journal's own creation time. Sort a journal by USN, and read a backward step in time as
the clock's, not as a second journal: a journal created again restarts its numbering at USN 0 instead.

### Activation detection

| Image state | OID 0x520 row count | Change Journal entry |
|-------------|---------------------|----------------------|
| Fresh (never activated) | 1 (descriptor only) on format 3.9 and later; 3.4 and 3.7 volumes, and volumes upgraded from them, also hold three down-level children | Absent |
| Active journaling | 3+ | Present (type 0x30, "Change Journal") |
| Deactivated | Varies | `$J` stays as it was: deactivating changes only the driver's in-memory state, and deleting the journal removes its file as a file delete (26100.9444) |

### Recreation: a journal that starts at USN 0 on a volume that has been used

`fsutil usn createjournal` over an existing journal **restarts the numbering at USN 0 and keeps the journal id**,
and the records before the call are no longer served as the journal. refs.sys grows a journal to a requested size but
never shrinks it, with a 32 MiB floor, at most half the volume and 4 GiB, rounded to 256 KiB, and an allocation delta
of 0: a request for a 1 MiB journal with a 256 KiB allocation delta produced a **32 MiB** journal with delta **0**. On that lab volume the window never filled, nothing was lost to wrapping, and no record
from before the call survived. The earlier records' bytes can survive, though, where the new numbering has not yet
written: on another corpus volume, re-created the same way, an earlier sequence at USN 176,128–487,944 lies above the
new numbering (USN 0–173,744), and `usn` names it with the boundary. `deletejournal` followed by `createjournal`
starts a new journal with a **new id** (its creation time).

An examiner should check this early: it takes little time, and it changes what the journal can be used
for:

| What you see | What it means |
|---|---|
| USN range starts at **0** on a volume with substantial prior activity | The journal was **created after that activity** — for the first time or again: a first creation after use looks the same (the published sample's journal was first created after a 1,000-action replay). Records from before its creation are not in it, apart from any of an earlier sequence that survive above the new numbering (the tool names them); the volume is not young |
| USN range starts at a **non-zero** value, spanning about one allocation | A normal rolling window that has wrapped once or more — the oldest records aged out — unless files carry an earlier journal's id, which shows a new journal whatever its range (the tool says so) |
| USN range starts at 0 and the volume is genuinely new | Nothing to conclude |

The middle row is what a busy volume looks like: on one Insider system volume the range runs 40,906,752 →
74,459,840 across a 32 MiB allocation — a span of exactly one window. The first row is what a journal
created again looks like: range 0 → 3,146,304 in the same 32 MiB, under a tenth of the window used, on a lab volume
that had been in use before the call (none of its earlier test files' names is in the journal). On that volume nothing else tells the re-creation
apart — no earlier record survives and the id was kept — so `usn --info` prints no re-creation statement and exits
0: a clean result does not show that the journal was never created again.

A recreated journal is not proof of intent: the driver creates a journal through one control code only, 0x900E7
(`FSCTL_CREATE_USN_JOURNAL`, which `fsutil usn createjournal` sends), for any caller whose volume handle passes one
access check (`RefsCreateUsnJournal`, 26100.9444), so the recreation does not say which program asked. It does mean
**absence of a record in the journal is not evidence the operation did not happen**, and a
timeline built from it starts at the recreation, not at the volume's birth, apart from the earlier records that
survive (listed under the boundary statement).

### How a record reaches the disk

refs.sys copies each record into a **4 KiB cache page of `$J`** (`RefsWriteUsnJournalChanges` ->
`RefsWriteFcbUsnRecordToJournal` -> `RefsUsnAppendData`: `CcPreparePinWrite` at a page start, otherwise
`CcPinRead`, then `CcSetDirtyPinnedData` with no LSN). **The record bytes never go through the log**: only the
file's 16-byte `$SI+0x40` pointer (LastUsn and journal id) is logged, as redo opcode 4, and only for a close record
that is not a delete. A record never straddles a 4 KiB page (the tail is zero-filled), and its time is read when it
is copied. Read on 17134, 26100.8115/.8521/.8972/.9444/.9549 and Insider 29574; the cache manager's later write of
the page, a `$J` held inline and references held only in data tables were not covered.

The consequence: a volume captured before that page reached the disk can hold files whose LastUsn points past the
journal's last surviving record, and after a reboot the log replay brings the pointers in. On one lab volume
captured before a reboot the live tree points up to USN 4,084,440 and page copies outside it up to 4,462,624. A
LastUsn above the last record is therefore not by itself evidence of tampering.

## Tooling

USN Journal parsing is integrated into `forefst.py` (parsing + display).
Available via `forefst.py <image> usn`:

| Mode | Description |
|------|-------------|
| Default | An activity **summary** (record count, reason-code distribution, time span) |
| `--list` (or `-v`) | The on-screen record list with reason codes and file names |
| `--csv [FILE]` | Export as CSV (a file export also prints the summary stats) |
| `--json [FILE]` | Machine-readable JSON output |
| `--info` | Journal metadata instead of records: the `$J` extents and declared lengths, `$Max`, the record count |
| `--stats` | The activity summary (what bare `usn` shows) |

Every ReFS journal record is version **3.0** (the 128-bit File ID requires the V3 layout), so the export
carries no version column.

### CSV / JSON columns

The `--csv` and `--json` exports share one field set (19 columns, in this order; a `--json` record has these keys):

| # | Column | Meaning |
|---|--------|---------|
| 1 | `USN` | The record's own USN (its virtual byte offset in the journal), decimal |
| 2 | `Timestamp` | The record's time |
| 3 | `Reason` | The reason flags' names (`FILE_CREATE\|CLOSE`) |
| 4 | `ReasonHex` | The reason bitmask in hex |
| 5 | `FileName` | The file or directory name the record carries (empty for a record that carries none) |
| 6 | `IsDirectory` | `true` for a directory's record (FileID 0: a directory self-reference) |
| 7 | `ObjectRef` | `HomeOID:FileID` — the same value as `files`' `ObjectRef` (a directory `OID:0x0`) |
| 8 | `HomeOID` | The creation (home) directory for a file, unchanged by a move; the object's **own** OID for a directory |
| 9 | `FileID` | The entry ordinal (lower half of the File ID); `0x0` for a directory |
| 10 | `ParentOID` | The parent directory's OID when the record was written |
| 11 | `FullPath` | The record's parent directory resolved **against the volume as it is in this image**, joined with the file name the record carries; one of the labels below in place of a parent that has no path. **Read the caution below before relying on it.** |
| 12 | `FileAttributes` | The attribute names |
| 13 | `FileAttributesHex` | The attribute word in hex |
| 14 | `RecordLength` | The on-disk record length |
| 15 | `SecurityId` | 0 on every ReFS record (see the layout above) |
| 16 | `SourceInfo` | The USN source flags' names (`0x0` where none was set; see the layout above) |
| 17 | `SourceInfoHex` | The same word in hex |
| 18 | `ParentFileID` | The ordinal of the parent reference: 0 on ReFS (a parent is a directory, addressed as `OID:0`) |
| 19 | `StreamOffset` | Where the record lies in `$J`: its byte offset in the stream, in hex |

`usn --info` checks a file's journal pointer only at the end of the journal: it compares the highest `LastUsn` the
files hold with the last record, so a `LastUsn` inside the journal's range that names no record, or another object's
record, draws no warning (after the restart described in the layout above, a few files of the lab volume point at another
object's record and a few dozen at none). Before citing a file's `LastUsn` as its last journal event, find that USN in the
export and check that the record's `ObjectRef` is the file's.

### Caution: `FullPath` is resolved against the CURRENT volume, not against the moment of the event

The journal is a historical record; the `FullPath` column is not. It is built by looking the record's
`ParentOID` up in the directory tree **as that tree exists in the image being read**, and joining the
result with the file name stored in the record. Two consequences follow, and both matter when the
column is used as evidence:

- **A parent that no longer exists cannot be resolved.** The column then shows `<oid 0x…>` — the
  directory's object is gone from the Object Table, so there is no path to give. On a real Windows
  installation this is the majority case: **more than half the records** measured on one installation. A
  freshly built lab volume shows none, so the effect shows only on a system where directories
  have been created and deleted over time.
- **A parent that was unlinked but not yet reclaimed** shows `<unlinked 0x…>`: its object is still in the
  Object Table, but no directory holds a name for it, so it has no path either. On the same installation
  **about 4 % of the records**, under about a hundred such directories. Its remaining contents can still be read —
  `deleted --orphans` reports them.
- **A parent the tool cannot look up** shows `<undetermined 0x…>` when the Object Table, or the directory tree
  the tool walks from the root, was read only in part (a page or a table could not be read, so whether the
  directory exists, or where it is, is not determined), and `<system 0x…>` for a system object (an OID below
  0x700).
- The others (**about 42 %** on that installation) get a path, because their parent directory exists in the
  image; a few carry no name at all. How many of those parents were renamed or moved after the event was not measured. That path is
  where the parent is today, so it is where the event happened only if the
  parent was not renamed or moved since:
- **A parent that was renamed or moved after the event resolves to its CURRENT location.** The row then
  joins a present-day directory path to a historical file name, and the combination was never a real
  path at any moment.

So `FullPath` gives where the file would be today, given where its parent is today, not where the file
was when the event happened. For that, use `ParentOID` together with the journal's own record of
directory creates, renames and deletes. Reconstructing the tree as it stood at event time is the correct
method, and the tool does not do it yet.

Directories **do** get USN records: a directory self-reference has FileID 0, which is why `IsDirectory` reads
`true`. `SecurityId` and `ParentFileID` are 0 on every ReFS record and are kept for the record layout's
completeness; `SourceInfo` carries the source flags a process set (see the layout above).

## Cross-references

- [Directory Entries](directory_entries.md) — per-file LastUsn at value offset **0x68** of the embedded record (or of a split record's type-0x40 backing); value+0x58 holds FileSize; UsnJournalId at 0x70
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — per-file LastUsn at **$SI+0x40**, UsnJournalId at $SI+0x48 ($SI+0x30 is not a USN: in a file's record it holds a cached copy of the file size, and it is 0 in a directory's own row)
- [System OIDs](system_oids.md) — OID 0x520 hosts the Change Journal file entry
- [File IDs](../concepts/file_ids.md) — how the 128-bit File ID maps to a B+-tree location

## Evidence

The recreation signal was measured in the lab: 1 MiB requested, 32 MiB and delta 0 granted, no wrap, and no
pre-call record surviving; contrasted against an Insider system volume whose range spans exactly one allocation, and
against a volume re-created the same way whose earlier sequence survives above the new numbering.

The `USN_RECORD_V3` layout and the 128-bit File ID split (upper = the creation/home directory OID, lower =
entry ordinal) are decoded from the disk across the corpus; the reason-code names are Microsoft's, and the codes
are read from the records. That the upper half is the *creation* directory and is **frozen across rename and
move** — while the Parent file ID at 0x18 follows the parent — is disk-proven on 1,858 cross-directory `RENAME_OLD_NAME`/`RENAME_NEW_NAME`
pairs across nine v3.14 volumes (File ID unchanged in every case) and corroborated in the driver
(`RefsMoveFile` migrates only the FileId-resolution index, never the stored reference). The record length range and the
`pad8` rule are measured corpus-wide (driver minimum 80 (0x50), observed 80–408 B, 8-byte aligned). The
USN ↔ `$SI+0x40` LastUsn link is both decompiled and disk-proven — on `winsider` 13,550 of 13,550 in-window
LastUsns of the current journal resolve to a `$J` record naming that file (after a restart at USN 0, stale
pointers do not). Journal activation, the OID 0x520 Change Journal entry,
and the type-0xF0 `$Max` attribute are corroborated in the driver
(`RefsSetupUsnJournal`, `RefsWriteFcbUsnRecordToJournal`) and verified on disk. The `$Max` layout is measured on
the 21 corpus volumes that have a journal (content offset 12, MaximumSize equal to the `$J` allocation and
AllocationDelta 0 on all 21); its UsnJournalID was compared with the journal id `fsutil` reports on one lab volume,
and they are equal. The in-place ring is
**observed, not assumed**: across 14 corpus journals all 338,439 records sit at their USN modulo the
allocation, and on the one volume whose journal has wrapped — a highest USN of 2.22 windows, every record's USN
past the end of the window — the buffer holds two generations cleanly split by position, which
front-trimming cannot produce. The two quantities compared there are independent: the offset comes from the
linear scan position, the USN from the record body.

See [how this was verified](../methodology.md) to trace these statements to the exact images and
measurements in `analysis/`.

The remaining field-level statements on this page are each registered with their own evidence tier and witness in
the claim register.

The counts behind the text:

- record length: on `winsider` (217,892 records) the maximum is 408 B and 1,779 records exceed 312 B (320 B ×488,
  328 ×379, 336 ×741, 344 ×119, 352 ×4, 360 ×4, 368 ×2, 384 ×38, 408 ×4); `winsiderv2`, a later capture of the same
  volume, reaches 408 B with 1,644 over 312;
- the absent parent: 234 records on each of `lab314_main`, `lab314_main_step3` and `lab314_main_step3_dirty`;
- the USN restart, on `lab314_main`: `fsutil queryjournal` shows the id `0x01dd3e1feaee8191` with `Next Usn 0`,
  then `First USN 0, Next USN 3142048`; afterwards 8 of 4,680 files' `$SI+0x40` LastUsn point at another object's
  record, and 38 more at no record;
- the source info at `+0x3C`: 0 on every record of 38 corpus journals;
- the on-disk File ID example: record 0 of `lab314_main`'s journal, at physical `0x19008000`;
- the File ID across moves: 1,858 real cross-directory moves, the File ID unchanged in every case;
- the ring, on the one wrapped journal (`winsider`): all 217,892 records at their USN modulo the window, the older
  generation at offsets 7,352,320–33,554,168 and the newer at 0–7,350,976 (the write head at about 7.35 MB of the
  32 MiB window); 75,448 of them are dated before the journal's own creation time;
- `FullPath` on that installation (217,892 records): `<oid 0x…>` on 118,172 (54.2 %), `<unlinked 0x…>` on 8,931
  (4.1 %) under 108 directories, a path on 90,597 (41.6 %), of which 192 carry no name;
- the Change Journal entry's value length: 704 B on 30 of the 43 corpus volumes that have one; 856 B on 6 (images of
  one volume), 3016 B on 4, and 720 B, 800 B and 3576 B on one each;
- the 4 KiB framing: 7 journals (332,745 records), 0 records across a 4 KiB boundary; 10,499 inter-record gaps, the
  largest 1,216 B (on `winsider`), and in 10,498 of 10,499 the next record would not have fitted in the gap.

<!-- findings: AP_CHJN_001, AP_CHJN_002, AP_CHJN_004, FS_OTBL_005, GN_ARCH_RA_002, MD_EFS_RA_001, MD_EFS_RA_002, MD_LK_RA_003, MD_LK_RA_004, MD_SF_RA_002, MD_SI_RA_013, MD_SI_RA_015, MD_USN_RA_001, MD_USN_RA_002, MD_USN_RA_003, MD_USN_RA_004, MD_USN_RA_007, MD_USN_RA_008, MD_USN_RA_009, MD_USN_RA_010, MD_USN_SA_001 -->
