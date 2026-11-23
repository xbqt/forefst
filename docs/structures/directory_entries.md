# Directory Entries

> `key_flags` records the **record's** location, never the **bytes'** location — the two are explained in [Record placement and data residency](../concepts/placement_and_residency.md).

Directory entries (type 0x30) are B+-tree rows within a per-directory B+-tree. Each file or subdirectory appears as a type 0x30 row in its parent directory's tree. The record placement (embedded vs split) determines the value layout, and a parser must resolve that mode from the key flags before reading any field.

## B+-tree row header — 16 bytes

Every row in a B+-tree leaf begins with this header:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Row size (u32) | total byte size of the row (0x70 is the common value for a typical embedded row, **not** a constant flag) |
| 0x04 | 2 | Key offset (u16) | Byte offset from row start to key data |
| 0x06 | 2 | Key length (u16) | -- |
| 0x08 | 2 | Flags (u16) | Bit `0x4`: the row was removed from the key index, by a delete or by an update that replaced it; it stays in the data area (every unlisted row in the data areas of the test corpus carries it, no listed row does) |
| 0x0A | 2 | Value offset (u16) | Byte offset from row start to value data |
| 0x0C | 2 | Value length (u16) | -- |
| 0x0E | 2 | Reserved (u16) | 0 |

See [B+-Tree Node](btree_node.md) for the page-level node structure that holds these rows.

## Key format (type 0x30)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 2 | Entry type (u16) | Row type identifier (0x0030 = filename, 0x0020 = reverse index, 0x0040 = backing record of a split record) |
| 0x02 | 2 | Key flags (u16) | Determines value interpretation |
| 0x04 | var | Filename (UTF-16LE) | File or directory name |

### Key flags

Only **two** key_flags values exist on disk (distribution {0x01, 0x02} only, zero occurrences of 0x04):

| Value | The row is | Value Size | Description |
|-------|-----------|-----------|-------------|
| 0x01 | an **embedded record** | >84 bytes | The file's own metadata header follows in this row. Its `$DATA` may be inline **or** extent-backed — the flag does not say which |
| 0x02 | an **index entry** | 84 bytes, or 72 (the size depends on the driver and the format it was written under, below) | A pointer; the record was split out into a type-0x40 row in the file's home directory. On a *file* this is the fingerprint of a move or a hard link |

> **`key_flags` is not a residency flag.** Reading 0x01 as "resident" and 0x02 as "non-resident" is the
> most common way to mis-parse this structure. Every kf=0x01 *file* row is extent-backed on ReFS 3.4–3.10
> (none inline on the volumes measured). On 3.14 the share is a property of the volume: from none to nearly all
> of a volume's embedded rows are extent-backed on the volumes measured.
>
> Determine residency from the `$DATA` attribute's storage — see
> [Record placement and data residency](../concepts/placement_and_residency.md).

A directory is stored with **key_flags 0x02** (the index-entry value layout) and is identified by the directory attribute bit `0x10000000` at value+0x40: `RefsAddFileNameIndexEntry` ORs the `0x10000000` bit into the attribute word. There is no separate 0x04 = directory flag.

The index-entry value length is **72 or 84 bytes**. The 26100 and Insider drivers' `RefsAddFileNameIndexEntry` sets
`0x54` (84) on a volume of format 3.9 or later and `0x48` (72) below; on the corpus, the volumes formatted at 3.4, 3.7
and 3.9 by their own drivers hold 72-byte entries and those formatted at 3.10 or later hold 84.

**That length is fixed when the entry is written, and is never rewritten afterwards — so it is a property of
the entry, not of the volume.** A volume upgraded across the v3.10 boundary carries **both layouts side by
side**: its pre-upgrade entries keep the 72-byte form while the newer driver writes 84-byte entries for
anything new. Take the size from the row's own length; keying on the volume version misparses every retained
entry on an upgraded volume.

Across the corpus every natively-formatted volume carries a single size matching its format-time version, and
exactly the upgraded volumes carry a mixture. Every field below sits at or under `value+0x44`, which is identical
in both layouts, so testing the length as a **range** is both correct and version-independent.

## Embedded-record value (key_flags = 0x01)

The value holds the file's whole record, so its size varies with its attributes. It is a small B+-tree table of its
own: a 40-byte descriptor (0x00 to 0x27), the file's `$STANDARD_INFORMATION` as the table's root data (from 0x28), then
the node of the table's rows, the file's sub-records (from 0xA8). A directory's type-0x10 own row has the same
structure.

<!-- site: hexfig "file_record_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Node offset (u32) | `0xA8` (0x28 + the root data's 0x80 bytes) on every record of the corpus: where the record's node begins |
| 0x04 | 2 | Descriptor size (u16) | `0x28` (40 bytes) |
| 0x06 | 2 | Not decoded (u16) | 1 on every record |
| 0x08 | 4 | Flags (u32) | 1 on every record |
| 0x0C | 4 | Schema id (u32) | The record table's schema, by the format under which the file was created or last converted: 0x180 below 3.6, 0x1C0 from 3.6 to 3.10, 0x1E0 from 3.11 ([Schema Table](schema_table.md#which-id-a-record-carries)) |
| 0x10 | 4 | Schema id, copy (u32) | Equal to 0x0C |
| 0x14 | 2 | Checksum type (u16) | The volume's checksum type: 4 on a SHA-256 volume, 2 on the other volumes measured |
| 0x16 | 2 | Integrity (u16) | 1 on a file whose data is in extents and carries integrity checksums (its file attribute 0x8000 set; 2 files with it lack the attribute, see Evidence); 0 on a directory, and on an inline file, whose integrity is in its `$DATA` value |
| 0x18 | 8 | Leaf-page count (u64) | 0 while the node is in the value; 1 when the sub-record table moved to a child page ([below](#when-the-sub-record-table-moves-into-a-child-node)) |
| 0x20 | 8 | Row count (u64) | The number of rows of the record's table: its sub-records ([below](#sub-record-row-count-offset-0x20-in-the-embedded-value)) |
| 0x28 | 8 | Creation time | FILETIME (100 ns since 1601-01-01) |
| 0x30 | 8 | Modification time | FILETIME |
| 0x38 | 8 | Metadata change time | FILETIME |
| 0x40 | 8 | Last access time | FILETIME |
| 0x48 | 4 | File attributes (u32) | Win32 flags + ReFS extensions |
| 0x4C | 4 | Internal flags (u32) | ReFS-specific state |
| 0x50 | 8 | Security ID (u64) | Links to Security Descriptors table (OID 0x530) |
| 0x58 | 8 | File size (u64) | Logical file/stream size, and nonzero even on USN-inactive images. It is a **cached copy** of the `$DATA` size, not the `$DATA` record itself: it agrees on **623,322 of 623,326** embedded rows over 117 images, and the 4 exceptions are all **stale-low on an actively-appended file**, all on the two images of one Windows installation (`winsider` `StorGroupPolicy.log` 10,792 vs 12,029; a System32 file 730 vs 876; `wpndatabase.db-wal` 3,188,912 vs 3,271,312 on `winsider` and 3,230,112 vs 3,275,432 on `winsiderv2`). Where the two disagree the `$DATA` record is authoritative. |
| 0x60 | 8 | Allocated size (u64) | Roundup-to-cluster on most rows; inline byte count for tiny files. A cached copy like 0x58, and stale with it: `wpndatabase.db-wal` on `winsider` carries 3,211,264 against a stream of 3,271,312 bytes, whose own allocation — and the extent map — is 3,276,800. While the copy is current it is the file's allocation, and it can be **below the file size** on a sparse file, which counts only the clusters it has allocated (53 embedded rows over 117 images, every one carrying the sparse attribute). Neither allocation field of the `$DATA` record reproduces it alone — it follows the disk allocation on a sparse file and the total allocation where blocks are shared ([extent records](extent_descriptors.md)). |
| 0x68 | 8 | LastUsn (u64) | File's last USN = virtual byte offset of its most recent `$UsnJrnl:$J` record (OID 0x520). 0 if the journal is inactive. This (offset 0x68) is the per-file USN. |
| 0x70 | 8 | UsnJournalId (u64) | The id of the change journal the file's LastUsn belongs to: the journal instance's id, which can change (`fsutil usn createjournal` over an existing journal keeps it; `deletejournal` then `createjournal` gives a new one, the new journal's creation time); 0 when no journal has recorded a change to the file. |
| 0x78 | 8 | PackedEaSize / ReparseTag (2 x u32) | `$SI+0x50` and `$SI+0x54` |
| 0x80 | 8 | NextFileId (u64) | In a file's record, the file's own ordinal, assigned by its directory at creation: the low half of its 128-bit file id (`$SI+0x58`) |
| 0x88 | 8 | Reference ordinal | `$SI+0x60`: with +0x90, the file's FileRef after its record moved whole (a volume without hard-link support, below); 0 otherwise |
| 0x90 | 8 | Reference directory | `$SI+0x68`: the FileRef's directory, set only with +0x88 |
| 0x98 | 4 | HardLinkCount | `$SI+0x70` (1 in an embedded record) |
| 0x9C | 8 | NextStreamSetId | `$SI+0x74`; not on v3.4, whose `$SI` is 116 bytes and ends at `value+0x9B` |
| 0xA8+ | var | Embedded sub-record chain | $DATA / ADS / snapshot / EA / $EFS rows. **There is NO embedded $SI sub-record**: the `$SI` is the table's root data from 0x28, with the USN-journal fields at 0x68/0x70. Version-dependent; see below. |

From `value+0x28` the value holds the file's `$STANDARD_INFORMATION` (a file has no type-0x10 row of its own): the
same structure as a directory's own row holds, written by the same driver code. At `$SI+0x30` / `+0x38` (`value+0x58`
/ `+0x60`) a file's record carries its file size and allocated size; a directory's own row holds 0 there. The `$SI` is 116 bytes (0x74) on format 3.4 and 124 bytes (0x7C) from 3.7. See [Standard Information](../attributes/STANDARD_INFORMATION.md) for its fields, and [Record placement and data residency](../concepts/placement_and_residency.md) for the rule that decides whether the bytes sit inline.

### Sub-record row count (offset 0x20 in the embedded value)

The value+0x20 field is a **count of embedded sub-record rows** in the embedded record's inline B+-tree (the inline file object's sub-record table: 1 default $DATA + one row per ADS, snapshot, reparse, EA, and $EFS). It is **NOT** a fixed 1-6 enum. It equals the parsed sub-record row count in the large majority of embedded records (the residual are deleted/marker rows). The count is unbounded: values up to **14** have been observed (e.g. a file with 12 ADS).

The values below are common cases (consequences of the count), not an exhaustive enumeration:

| Row Count | Common case |
|-----------|-------------|
| 1 | Normal file (default data stream only) |
| 2 | One extra component — sparse file or reparse point/symlink |
| 3 | Encrypted file ($DATA + $EFS), or EA/WSL file, or file with 1 ADS |
| 4 | File with 1 snapshot, or 2 ADS, or reparse + EA |
| 5+ | More ADS and/or snapshots (e.g. count=14 with 12 ADS) |

### When the sub-record table moves into a child node

The chain above sits directly in the value only while it is small enough to fit in one node. The inline table
is a real B+-tree, and when a file accumulates enough attributes — many alternate data streams, for instance —
ReFS promotes it: the node inside the value becomes an **index node**, and the sub-records themselves move to
a **child page** elsewhere on the volume.

The node descriptor tells you which case you are in:

| Field | Leaf — attributes are here | Index — attributes are in a child |
|-------|---------------------------|-----------------------------------|
| Level (descriptor + 0x0C) | `0` | non-zero |
| Flags (descriptor + 0x0D) | bit 0 clear | **bit 0 set** |

An index node carries one row per child. That row has an **empty key** (key offset `0x10`, key size `0`) and a
48-byte value which is a node reference: four cluster numbers, where `0` and `0xFFFFFFFFFFFFFFFF` mean
"unused". Follow a valid one and you land on an ordinary `MSB+` page — read its rows exactly as you would read
the inline ones.

**Why this matters when you are reading evidence.** In the index case the value contains *no* attributes at
all. A reader that walks only the inline offsets array finds nothing, and will report that the file has no
alternate data streams, no reparse data and no `$DATA` record. The result is wrong and no error is
reported, which is the most dangerous kind of forensic result. On the corpus it hides thousands of
attribute records, hundreds of them alternate data streams — one volume that appeared to have no ADS whatsoever
in fact has dozens of files carrying them. The file-system driver descends into the child here, and so must any
tool that wants a complete answer.

### Embedded sub-record markers

| Marker | Meaning |
|--------|---------|
| 0x80000001 | Single-instance attribute — reparse `0xC0`, EA info `0xD0`, EA `0xE0`, and **`$DATA` 0x80 in its inline-content form** (429 rows measured; this is the combination [DATA.md](../attributes/DATA.md) tells you to look for) |
| 0x80000002 | Multi-instance attribute — `$DATA` `0x80` in its extent-backed form, the `0xB0` rows (alternate data streams and stream-snapshot names), **`$OBJ_LINK` `0x39`** (498 rows), **`$I30_INDEX` `0x90`** (499 rows) and **`$EFS` `0x100`** |

The marker does **not** partition the type codes: `0x80` appears under both, and the pairs above were counted over four images. Read the marker and the type together; neither alone identifies the sub-record.

Sub-records begin at offset 0xA8+ and form a chain. Single-instance sub-records carry one attribute each; multi-instance sub-records may appear multiple times for streams with the same descriptor.

### ADS and snapshot sub-records (descriptor 0x000500B0)

Both alternate data streams (ADS) and snapshot streams are stored as multi-instance sub-records with the same descriptor 0x000500B0. The StreamSummary.Flags field (u16) at the start of the StreamSummary region discriminates them: **0 = ADS, 2 = snapshot**. See [$SNAPSHOT](../attributes/SNAPSHOT.md) for the value format.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Marker (u32) | 0x80000002 (multi-instance) |
| 0x04 | 4 | Descriptor (u32) | 0x000500B0 |
| 0x08 | var | Stream name | UTF-16LE, **not NUL-terminated** — its length comes from the key length. Measured: 0 of 254 type-0xB0 stream names and 0 of 3,830 reverse-index names carry a terminator. Worked case (`win11refs2g`, 38-byte key): `6a00…` value_length, marker `0x80000002`, type `0xB0` subtype `0x0005`, then 22 bytes of name ending `34 00` with no NUL |
| -- | 0-6 | Alignment padding | Pad to (offset - marker_start) % 8 == 4 |

**Sub-record header** (immediately after alignment):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| +0x00 | 2 | Padding (u16) | Always 0 |
| +0x02 | 2 | Attribute flags (u16) | 0 for an inline ADS; bit 0x1000 marks the extent-backed form (see [$NAMED_DATA](../attributes/NAMED_DATA.md)) |
| +0x04 | 4 | Data-area size (u32) | Value length minus 12 |
| +0x08 | 4 | Content offset (u32) | Always 0x0C |
| +0x0C | 4 | Summary size (u32) | Always 0x30 (48 bytes) |
| +0x10 | 2 | StreamSummary flags (u16) | **0 = ADS, 2 = snapshot** (bit 1 set by `RefsCreateStreamSnapshot`) |
| +0x12 | 6 | Reserved | Always 0 |
| +0x18 | 8 | Allocated size (u64) | Equal to the stream size when the bytes are inline (stored packed); see [$NAMED_DATA](../attributes/NAMED_DATA.md) |
| +0x20 | 8 | Stream size (u64) | Logical content length |
| +0x3C | var | Inline content | Present when SS flags = 0 (ADS only) |
| +0x44 | 4 | Stream index (data_sub_id) (u32) | Present when SS flags = 2 (snapshots only); links to DATA sub-record |

**Snapshot extent linking**: When SS flags = 2, the entry is a snapshot stream (NOT an ADS). The stream_index at header+0x44 matches a 0x000E0080 (DATA) sub-record's stream_index at sub_rec+0x08 within the same value, providing the extent table for the snapshot's content. See [$NAMED_DATA](../attributes/NAMED_DATA.md) and [$SNAPSHOT](../attributes/SNAPSHOT.md) for the value format.

### DATA sub-records (descriptor 0x000E0080)

A file whose main `$DATA` is in extents holds it in multi-instance sub-records with descriptor 0x000E0080. Several
coexist in one value: the stream-set record (sub-stream id 0x8), the live stream (0x1000) and, for a file with
stream snapshots, one per snapshot (0x1001 and up). An extent-backed alternate data stream keeps its extents in a
record of its own (key size 0x50), not here — see [$NAMED_DATA](../attributes/NAMED_DATA.md).

Each is identified by its 40-byte key:

| Key offset | Size | Field | Description |
|--------|------|-------|-------------|
| +0x08 | 4 | Marker (u32) | 0x80000002 |
| +0x0C | 4 | Descriptor (u32) | 0x000E0080 (type 0x0080, subtype 0x000E) |
| +0x10 | 8 | Sub-stream id (u64) | Id `0x8` is the stream-set metadata record, not the default data stream: all **1,448** records carrying it are a fixed 40-byte value with **no extent node, stream size 0 and disk-allocated 0**, so it can hold no content |

The value of the live stream's record is the extent-bearing `$DATA` record: a 0x88-byte header, then the extent
node. See [Extent Records](extent_descriptors.md).

## Index-entry value (key_flags = 0x02)

An index entry is the name row of a directory, and of a file whose record was split out into a type-0x40 backing (a
move or a hard link). It holds the name's copy of the times, sizes and attributes, and the pair that finds the record.
A directory is identified by the directory attribute bit `0x10000000` at offset 0x40.

Its size depends on the driver that wrote the entry and the volume's format at the time:

- **84 bytes** when a 26100 or Insider driver wrote it on a volume of format 3.9 or later, and on the corpus's volumes
  formatted at 3.10 or later;
- **72 bytes** when a 26100 or Insider driver wrote it below 3.9, and on the corpus's volumes formatted at 3.4, 3.7 and
  3.9 by their own drivers. The entry keeps that size after an upgrade, so an upgraded volume holds both sizes (see
  [Key flags](#key-flags)).

The two forms differ only after the reparse tag at 0x44: the 84-byte form adds the EA size and 10 more bytes.

<!-- site: hexfig "index_entry_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Child ordinal (u64) | 0 in a directory's entry (a directory is identified by its OID at 0x08). In a file's entry, the file's per-directory ordinal (`$SI+0x58` of its record), shared by all hard-link names of one file and never reused within its home directory. The same value recurs in sibling directories, so alone it is **not a globally-unique FileId**: pair it with value+0x08. It also keys the type-0x40 backing record. See [Hard links](#hard-links). |
| 0x08 | 8 | Home-dir backref (u64) | In a directory's entry, the directory's own OID. In a file's entry, the OID of the directory the file was **first created in** — not necessarily its current parent. Frozen for the life of the object: it is unchanged by a rename or a move to another directory, and is shared by every hard-link name of the file. Together with value+0x00 it is the file's `(HomeOID, FileID)` identity (see [File IDs](../concepts/file_ids.md)). |
| 0x10 | 8 | Creation time | FILETIME |
| 0x18 | 8 | Modification time | FILETIME |
| 0x20 | 8 | Metadata change time | FILETIME |
| 0x28 | 8 | Last access time | FILETIME |
| 0x30 | 8 | Allocated size (u64) | Total allocated bytes (cluster-aligned) |
| 0x38 | 8 | File size (u64) | Logical content length |
| 0x40 | 4 | File attributes (u32) | Win32 flags + ReFS extensions (dir bit 0x10000000) |
| 0x44 | 4 | Reparse tag (u32) | The object's reparse tag when its attributes carry `0x400` (reparse point), else 0 (read on the 84-byte form) |
| 0x48 | 2 | EA size (u16) | 84-byte form only: the object's packed EA size, capped at 0xFFFF |
| 0x4A | 2 | (not decoded) | 84-byte form only: 0, or a small value on ReFS 3.14 entries that carry an EA size |
| 0x4C | 8 | Reserved | 84-byte form only: 0 on every such entry of the corpus (310,882) |

The times, sizes and attributes of a file's index entry are a **cached copy** of its record's, refreshed lazily:
the size can be stale in either direction and the attributes can differ. Where they disagree, the record in the
type-0x40 backing is authoritative: its `+0x48` attributes and, for the size, its `$DATA` record (the backing's
own `+0x58` is a cached copy too). See [Hard links](#hard-links).

### Relocated files — the entry moves, the identity does not

On a volume with hard-link support, when a file is moved to another directory, ReFS relocates this type-0x30
entry into the **new** parent's B+-tree, but the object's data/metadata (its type-0x40 backing) **stays in the
creation directory's** tree.
The entry's `value+0x00` ordinal and `value+0x08` home-backref are copied unchanged, so a moved file is
recognisable on disk as one whose `value+0x08` differs from the directory it now sits in. For example, on a
real Win11 volume the file `Generate-FSActivity.ps1` was created in directory OID 0x9586 and later moved
under OID 0x9e25 (`\tools`); on disk its entry sits in 0x9e25 but still carries `value+0x08 = 0x9586` and
its ordinal `value+0x00 = 3`, and its type-0x40 backing is found in 0x9586, not 0x9e25. The same
`value+0x08 != containing directory` shape also arises for a hard-link name placed in a second directory
(told apart from a move by the link count in the backing — see below).

This is also *why*, on a volume with hard-link support, a relocated file always appears in the **split**
layout. The creation directory, which does not
change, is carried by `value+0x08`, and only the split value has that field — the embedded value
(`key_flags 0x01`) does not. So a file's entry takes the **split layout** the moment it is moved or
hard-linked, and it never reverts. On such a volume a file whose record is still **embedded** has never been
relocated: its home equals its current parent. On a volume **without** hard-link support (flags lacking 0x20) the
whole embedded record moves: it then carries the file's FileRef at value+0x90 (`$SI+0x68`, the directory) / value+0x88
(`$SI+0x60`, the ordinal), and that reference -- not (its directory : value+0x80) -- is the file's identity.

The split moves the **record**, not the **bytes**. A moved file's
`$DATA` is untouched, and for a small file it stays inline inside the backing record. Measured on a
controlled before/after move of a whole volume: the files that changed placement changed **no data
residency**, and the moved 16-byte file's `$DATA` sub-record was **byte-identical** either side — read out of the name row before the move and out of its backing record
after, with `value+0x08` still pointing at its creation directory. See
[Record placement and data residency](../concepts/placement_and_residency.md) for the two axes.

## Critical layout differences

Timestamps and most fields are at **different offsets** between an embedded record and an index entry:

| Field | Embedded record (kf 0x01) | Index entry (kf 0x02) |
|-------|----------------|---------------------|
| Creation time | +0x28 | +0x10 |
| File attributes | +0x48 | +0x40 |
| Security ID | +0x50 | Not in the dir entry — in the type-0x40 **backing** record @+0x50 |
| File size | +0x58 | +0x38 |
| Allocated size | +0x60 | +0x30 |
| LastUsn (per-file USN) | +0x68 (= $SI+0x40) | Not in the dir entry — in the type-0x40 **backing** @+0x68 |
| UsnJournalId | +0x70 (= $SI+0x48) | Not in the dir entry — in the type-0x40 **backing** @+0x70 |

A parser **must** resolve the record placement from key_flags before reading any timestamp. Applying the wrong offset layout will misparse every field.

> **SecurityId / USN of a split file:** a split file's type-0x30 index entry does not carry these,
> but they are **not** reached through the Object Table — a file has no Object-Table OID. They
> live in the file's own **type-0x40 backing record** (its `$SI` / stream-summary, keyed by home-dir OID +
> FileID) at backing value+0x50 (SecurityId), +0x68 (LastUsn), +0x70 (UsnJournalId).

## Hard links

When a file gains a second name its record is **split** out into the index-entry layout above (key_flags 0x02),
and each name becomes its own type-0x30 entry. All of one file's names share `value+0x00` (the per-directory child
ordinal) and `value+0x08` (the home-dir backref) — both already in the index-entry value table above.

The link count is `$SI+0x70` of the file's record: 1 in an embedded record, and in the type-0x40 backing of a split
record the number of the file's names, as the driver last wrote it.

Hard links exist on a volume whose boot sector carries the hard-link support bit (0x20 of the flags at +0x2C): on
the corpus, every volume natively formatted at 3.7 or later but one, and no volume formatted at 3.4 or upgraded from
it. The 3.4 driver (17134) has no hard links. See [Hard Links](../concepts/hard_links.md) for the full resolution
model and forensic implications.

## Reverse index (type 0x20)

A directory's tree also carries type 0x20 rows: a per-object FileId-resolution index that maps a child index back to either the object's name (Format A, for an embedded record) or where its record is (Format B: a backing's self-reference, or the forward pointer a move leaves in the home directory). A subdirectory has none. The full key and value layouts are in [Reverse Index](reverse_index.md).

## Cross-references

- [Reverse Index](reverse_index.md) -- the type 0x20 FileId-resolution rows in the same directory tree
- [Extent Records](extent_descriptors.md) -- the extent map inside an extent-backed `$DATA` record
- [Object Table](object_table.md) -- the home-dir backref in index entries resolves via the Object Table
- [Standard Information](../attributes/STANDARD_INFORMATION.md) -- $SI layout differs by version
- [Record placement and data residency](../concepts/placement_and_residency.md) -- the two independent axes
- [Hard Links](../concepts/hard_links.md) -- multi-name files and the size-matched link count

## Evidence

The key/value layouts, the 84/72-byte size split and its fixing at write time (proven by two controlled before/after
upgrade pairs, where the pre-upgrade entries are retained byte-for-byte beside the new ones), the {0x01, 0x02}-only
key-flag census, the embedded/index-entry field offsets, the sub-record markers and descriptors, and the 0 = ADS /
2 = snapshot discriminator are decoded from the disk across the corpus and corroborated in the driver:
`RefsAddFileNameIndexEntry` ORs the directory bit and gates the 84/72-byte length, and `RefsCreateStreamSnapshot`
sets the snapshot StreamSummary bit. A file's first hard link splits its record once (`RefsLinkFileToSelf`
re-parents the file's table under the type-0x40 key), and each further name is written by `RefsAddLink`. The page's
other field-level statements are registered findings, each with its own evidence tier and witness in the claim
register.

The counts behind the text:

- kf=0x01 file rows on 3.4–3.10: 3,153 / 442 / 701 / 250 rows over the 79 distinct volumes measured, none inline; on 3.14, the embedded rows whose
  `$DATA` is extent-backed run from 0 % (`win11refsmini`, 0 of 9) to 96.2 % (`lab314_64k` and `lab314_4kn`, 611 of
  635);
- the mixed index-entry sizes: `win1122h2test_afteropenedwithinsider` holds 482 retained 72-byte entries beside 333
  new 84-byte ones;
- the attribute records in a child node: 1,329 files across 19 volumes, 4,094 records hidden, 548 of them
  alternate data streams; `win1122h2test` goes from 0 to 60 ADS-bearing files;
- the controlled move: of 9,521 files present in both images, 5 changed placement and 0 changed data residency;
- the link count: equal to the number of size-matched names on 99.84 % of backings;
- the hard-link support bit: the one natively formatted volume without it is the one whose boot sector
  `refsutil fixboot` rewrote;
- the record's descriptor, on every record of the 124 ReFS volumes of the corpus (820,293 file records, directory own
  rows and backings): node offset 0xA8, size 0x28, the schema ids of the record's format (older ids only on volumes
  upgraded to 3.14), the row count equal to the table's rows on all but 5; the checksum type 4 on every record of the
  four SHA-256 volumes; integrity 1 on 4,034 of the 4,037 files with the attribute 0x8000 (the 3 others keep their data
  inline, where the integrity is the `$DATA` value's +0x3A) and on 2 files without it.
- The descriptor's fields are those the driver reads when it opens the record's table (`MsParseEmbeddedTableInfoFromRow`,
  `CheckEmbeddedRoot`, `CmsBPlusTable::CreateIndex`), and the `$SI` is written into the table's root data
  (`MsUpdateDataWithRoot`).

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

<!-- findings: FN_DTBL_002, FN_DTBL_006, FN_DTBL_007, GN_IDXR_RA_005, GN_IENT_004, MD_ATTR_RA_008, MD_ATTR_RA_014,
               MD_DATA_RA_012, MD_DATA_RA_021, MD_FTBL_005, MD_SI_RA_017, FS_SCHM_RA_012 -->
