# Attributes
<!-- site: description "Where ReFS keeps a file's and a directory's attributes: the records they sit in, the sub-record set, and how to tell a genuine attribute from noise." -->

In NTFS a file's metadata is a list of typed attributes inside its MFT record, and a parser that walks that list
reads the whole file. ReFS keeps the idea and many of the names (`$STANDARD_INFORMATION`, `$DATA`,
`$REPARSE_POINT`, `$EA`), but not the shape: there is no flat list in one record.

ReFS stores attributes on **two levels of B+-tree**. A tool that reads only the outer level sees a file's name and
times, and misses its data stream, its alternate data streams, its reparse data and its extended attributes.

This page explains the two levels, where each attribute sits, and how to tell a genuine attribute from bytes that
only look like one.

## Two levels

- **The outer level.** A directory or a system object has its own B+-tree, found by its object ID (OID) through
  the [Object Table](../structures/object_table.md). A file has no tree and no OID of its own: its record is a row
  of a directory's tree.
- **The inner level.** A record holds the object's `$STANDARD_INFORMATION` at `value+0x28`, then a small B+-tree
  whose root node sits inside the same value. The rows of that inner tree are the attributes (the *sub-records*).
  When they outgrow that one node, its rows move to child pages ([below](#when-the-attribute-set-outgrows-one-node)).

The first two bytes of a row's key name the row's type. A user directory's tree (OID 0x600 and above) holds four:

| Row type | What it is |
|----------|------------|
| 0x10 | The directory's **own row**: its `$STANDARD_INFORMATION` and its own attributes |
| 0x20 | The [FileId reverse index](../structures/reverse_index.md): a FileId mapped to a name or to a home directory |
| 0x30 | A [directory entry](../structures/directory_entries.md), one per child name. When the row embeds the file's record (key flags 0x01), its value **is** the file's record |
| 0x40 | A **backing record**: the record of a file split out of its name row by a move or a hard link (key flags 0x02 in the name row), kept in the file's home directory |

No row of a directory's tree has a type from 0x80 to 0x100: those codes are attributes, one level down, inside a
record.

So a record, and the attributes in it, sits in one of three places:

- a directory's own row (type 0x10);
- a file's name row (type 0x30), while the record is embedded there;
- a file's backing record (type 0x40), once a move or a hard link has split the record out.

Where the record sits says nothing about where the file's bytes are: in either place, `$DATA` holds them inline or
points to extents.

See [Record placement and data residency](placement_and_residency.md).

## Where each attribute physically lives

| Attribute | Type | A directory's own row (0x10) | A file's record (its name row 0x30, or its backing 0x40) |
|-----------|------|------------------------------|-----------------------------------------------------------|
| [`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) | none: the fixed region at `value+0x28` | yes | yes |
| [`$OBJ_LINK`](../attributes/OBJ_LINK.md) | 0x39 (0x38 on 3.4) | one row per name | in a backing only, one row per name; an embedded record has none |
| [`$I30_INDEX`](../attributes/I30_INDEX.md) | 0x90 | exactly one | — |
| [`$DATA`](../attributes/DATA.md) | 0x80 | — | the main data stream: the bytes inline, or the extent map |
| [`$NAMED_DATA`](../attributes/NAMED_DATA.md) | 0xB0 | — | one row per alternate data stream |
| [`$SNAPSHOT`](../attributes/SNAPSHOT.md) | 0xB0 | — | one row per stream snapshot |
| [`$REPARSE_POINT`](../attributes/REPARSE_POINT.md) | 0xC0 | a junction or a directory symlink | a symlink, a mount point or a WSL special file (in a backing: see below) |
| [`$EA_INFORMATION` and `$EA`](../attributes/EA_INFORMATION.md) | 0xD0 and 0xE0 | yes, rarely | yes, as one pair |
| [`$EFS`](../attributes/EFS.md) | 0x100 | not measured | an encrypted file's record, as the named stream `$EFS` |

"—": not found there on the volumes measured.

- A split file's reparse data: on 3.14 the backing holds the whole reparse buffer; on 3.7 to 3.10 it holds only
  the tag mirror, and the buffer itself is in older copy-on-write pages, not in the live tree.
- `$DATA` takes one of two forms, never both: inline (single-instance, the bytes in the record) or in extents
  (multi-instance rows that carry the extent map). Which one is a property of the stream, not of where the record
  sits: a backing can hold its file's bytes inline.

<!-- site: attribute-map -->

Three attributes are kept on system objects, not on user files or directories:

| Attribute | Where it lives |
|-----------|----------------|
| The change journal's parameters (type 0xF0, unnamed) | the Change Journal file, in the system directory OID 0x520, where a journal was activated ([below](#type-0xf0-the-change-journals-parameters)) |
| [`$VOLUME_INFORMATION`](../attributes/VOLUME_INFORMATION.md) | the system table at OID 0x500, a failover pair with OID 0x501 |
| The reparse-point index ([`$REPARSE`](../attributes/REPARSE.md)) | the system table at OID 0x540, a failover pair with OID 0x541 |

## A genuine attribute, or noise: read the key form first

A raw scan that looks for known type codes in the bytes of a value gives false results. Fragments of file content and the
rows of system tables can put a plausible byte (0x00, 0x01, a two-character string read as `0x322d`) where a type
code would sit.

An attribute row's **key** tells a genuine row from noise, and it comes in two forms:

- **The marker form**, written by a 3.7 or later driver: a 4-byte instance marker at `key+0x08`, the type code at
  `key+0x0C`.
  - `0x80000001`, **single-instance**: at most one per record.
  - `0x80000002`, **multi-instance**: zero or more per record.
- **The marker-less form**: the type code as a u32 at `key+0x08`, with no marker. It is used by:
  - every key the 3.4 driver wrote, including those a volume keeps after an upgrade from 3.4;
  - the 80-byte extent record of a large alternate data stream (`0x0003` at `key+0x08`).

Read the key form first, then check the type code against the set below. A scan that keeps only marked keys drops
every 3.4 row and every large-ADS extent record.

The types found on disk in the marker form:

| Type | Attribute | Marker | What it stores |
|------|-----------|--------|----------------|
| 0x39 | [`$OBJ_LINK`](../attributes/OBJ_LINK.md) | multi | a name and its parent directory's OID (0x38 on 3.4, with no marker) |
| 0x80 | [`$DATA`](../attributes/DATA.md) | single, or multi | the main data stream. Single-instance: the bytes inline. Multi-instance: the extent map (sub-stream 0x1000), the stream-set record (0x8) and each snapshot version (0x1001 and up) |
| 0x90 | [`$I30_INDEX`](../attributes/I30_INDEX.md) | multi | a directory's index template |
| 0xB0 | [`$NAMED_DATA`](../attributes/NAMED_DATA.md) or [`$SNAPSHOT`](../attributes/SNAPSHOT.md) | multi | an alternate data stream, or a stream snapshot ([below](#snapshots-versus-ads-one-type-two-meanings)) |
| 0xC0 | [`$REPARSE_POINT`](../attributes/REPARSE_POINT.md) | single | the reparse buffer |
| 0xD0 | [`$EA_INFORMATION`](../attributes/EA_INFORMATION.md) | single | the extended attributes' size header |
| 0xE0 | [`$EA`](../attributes/EA_INFORMATION.md) | single | the extended-attribute list (WSL's `$LX*` among them) |
| 0xF0 | unnamed | single | the change journal's parameters ([below](#type-0xf0-the-change-journals-parameters)) |
| 0x100 | [`$EFS`](../attributes/EFS.md) | multi | encryption metadata |

These codes of the driver's attribute table never appear as a sub-record of a user object on the corpus volumes:

| Type | Name (the driver's) | Where the information actually lives |
|------|---------------------|--------------------------------------|
| 0x50 | `$OBSOLETE` | not found on the corpus volumes |
| 0x60 | `$VOLUME_NAME` | the volume label: a row (key 0x510) of the volume-information table at OID 0x500 / 0x501 |
| 0x70 | [`$VOLUME_INFORMATION`](../attributes/VOLUME_INFORMATION.md) | the volume's version, flags and times: rows of the same table |
| 0xA0 | `$INDEX_ALLOCATION` | nowhere on disk as a sub-record |

The reparse-point index is not an attribute either: it is the system table at OID 0x540 / 0x541 (see
[Reparse Index](../attributes/REPARSE.md)).

The driver's own attribute-definition table (the one `RefsGetAttributeTypeCode` walks) names 15 types, from 0x10 to
0xE0 (14 on 17134, which has no 0x39): 0x90 is `$INDEX_ROOT` there and 0xA0 `$INDEX_ALLOCATION`, as in NTFS. Types 0xF0 and 0x100 are not in it: each
is created by its own code path, `RefsSetupUsnJournal` and `RefsCreateLoggedUtilityStream`.

Two NTFS attributes have no ReFS counterpart:

- `$FILE_NAME`: a name is a directory entry (a type-0x30 row), and there is no 8.3 short name;
- `$OBJECT_ID`: object IDs are not supported on ReFS (`fsutil objectid` fails), and no such sub-record exists on
  disk.

### Type 0xF0: the change journal's parameters

Type 0xF0 is an unnamed, single-instance attribute on the Change Journal file, in the system directory OID 0x520.

- It holds the journal's `$Max` parameters: maximum size, allocation delta, journal id and lowest valid USN.
- Its value is 44 bytes: a 12-byte wrapper, then the four u64 fields.
- `RefsSetupUsnJournal` writes it when a journal is created, so it exists only on a volume whose
  [USN journal](../structures/usn_journal.md) was activated. That is why it is rare.
- It is not the logged utility stream: that is type 0x100, which carries `$EFS`.

Its field layout is on the [USN Journal](../structures/usn_journal.md) page.

## The shared sub-record value header

Most sub-record values open with the same 12-byte prefix: types 0x90, 0xB0, 0xC0, 0xD0, 0xE0 and 0xF0, and the
inline (single-instance) form of `$DATA`.

| Offset | Size | Field | Value |
|--------|------|-------|-------|
| 0x00 | 4 | padding | 0, except on a type-0xB0 row, whose u16 at 0x02 is the attribute flags: bit 0x0400 a snapshot, bit 0x1000 a stream in extents, 0 on an inline alternate data stream |
| 0x04 | 4 | data-area size | the value's size minus 12 |
| 0x08 | 4 | content offset | 0x0C |

Two values do not open with it:

- the multi-instance (extent) form of `$DATA`, which opens with its own inner header (0x88 at `value+0x00` on the
  extent-bearing record);
- `$OBJ_LINK`, whose value repeats its key (see [below](#when-the-attribute-set-outgrows-one-node)).

So a parser reads the key form and the type first; only then can it tell whether the value opens with the prefix.
On a 3.4 key, which has no marker to branch on, the u32 at `value+0x00` tells: 0x88 is the extent-bearing record.

Type-specific content then begins at `value+0x0C`:

| Type | Content at `value+0x0C` | Inline data at |
|------|-------------------------|----------------|
| 0x80, single-instance (`$DATA`) | a 48-byte stream summary | `value+0x3C` (the file's bytes) |
| 0xB0 (`$NAMED_DATA` / `$SNAPSHOT`) | a 48-byte stream summary, the same shape as the inline `$DATA` | `value+0x3C` (the stream's bytes, when inline) |
| 0xC0 (`$REPARSE_POINT`) | a `REPARSE_DATA_BUFFER` (reparse tag, then its data) | `value+0x0C` |
| 0xD0 (`$EA_INFORMATION`) | PackedEaSize at 0x0C, the serialized on-disk size at 0x10; 20 bytes in all | — |
| 0xE0 (`$EA`) | a `FILE_FULL_EA_INFORMATION` chain | `value+0x0C` |

The 12-byte prefix is the same on every version, but several values change with the driver that wrote them:

- the extent-bearing `$DATA` record: on 3.4 its size fields sit 4 bytes later, and its summary size is 0x1A0 before
  3.14 and 0x200 from 3.14;
- the `$I30_INDEX` template: 148 bytes on 3.4, 140 bytes from 3.7;
- `$OBJ_LINK`: the 3.4 type-0x38 value has another shape than the 0x39 value.

PackedEaSize is also copied to `$SI+0x50` on format 3.10 and later; on 3.4 to 3.9 that offset holds the low half of
the reparse tag.

## Snapshots versus ADS: one type, two meanings

Type 0xB0 has two uses: it is both a [stream snapshot](snapshots_versioning.md) and an alternate data stream.
Two independent tests agree, and either can be used:

1. **The stream-summary flags at `value+0x10` (u16):** 0 for an alternate data stream, 2 for a snapshot. The driver
   sets the bit in `RefsCreateStreamSnapshot` (`StreamSummary |= 2`); `forefst.py` reads this.
2. **The attribute flags at `value+0x02` (u16):** bit 0x0400 (`HasSnapshot`) is set only on a snapshot, and the
   driver's `HasSnapshot` test reads it.

An alternate data stream's name is in the key, in UTF-16LE: from `key+0x10` in the marker form, from `key+0x0C` in
the 3.4 form.

The full value layout is on the [`$SNAPSHOT`](../attributes/SNAPSHOT.md) page.

## WSL extended attributes

When WSL stores Linux ownership and permissions on a ReFS file (a DrvFs mount with `-o metadata`), it does so
through `$EA_INFORMATION` and `$EA`, in the standard Windows `FILE_FULL_EA_INFORMATION` format, not in reparse
data. The names a forensic tool should recognise:

| EA name | Size | Meaning |
|---------|------|---------|
| `$LXUID` | 4 | Linux UID |
| `$LXGID` | 4 | Linux GID |
| `$LXMOD` | 4 | mode bits (the file type, `S_IFMT`, plus the permissions) |
| `$LXDEV` | 8 | device number (u32 major + u32 minor), only on device nodes |

The file attribute flag 0x40000 says that an object has extended attributes. Read it from the object's own record,
at `value+0x48`:

- a directory: its type-0x10 own row;
- a file whose record is embedded: its type-0x30 name row;
- a file whose record is split: its [type-0x40 backing](../structures/directory_entries.md).

The attribute copy cached in a name row that points to a backing (`value+0x40` of a key-flags-0x02 row) is
**incomplete, and occasionally divergent**:

- it usually drops bits the backing carries, so it is a lower bound;
- but not strictly: on a few dozen split names of the corpus it sets a bit the backing lacks, and that bit is
  always the transient Archive bit 0x20.

A tool that reads the directory entry alone reports no extended attributes for some files that have them.

WSL special files (FIFOs, sockets, character and block devices) also appear as
[reparse points](../structures/reparse_points.md) whose tag encodes the Linux file type; the type is also in the
upper bits of `$LXMOD`.

See [WSL metadata](wsl_metadata.md) for the full mapping.

## When the attribute set outgrows one node

A file's attributes normally sit in one embedded node inside its record. When they no longer fit, that node becomes
an **index node**: its level byte goes non-zero, and a row with an *empty key* points at a child page holding the
rest.

A parser that reads only the node inside the value then finds nothing, and wrongly reports that the file has no
attributes.

Inside an embedded node, `key[0:8]` is the value's length as a little-endian u64, on nearly every row measured (a
few hundred exceptions).

`key[8:]` repeating the start of the value (one buffer written once) is true **only of type 0x39 `$OBJ_LINK`**, on
every 0x39 row counted. It does **not** hold for the other sub-record types, which are the majority: 0x80 `$DATA`,
0x90 `$I30_INDEX`, 0xD0, 0xE0, 0xB0, 0xC0, 0x03 and the 3.4 type-0x38 `$OBJ_LINK`. So read the value from the value,
never from `key[8:]`, unless the row is a 0x39.

## A note on system objects

The system **tables** reuse the key position for their own identifiers, not attribute type codes. Do not feed their
rows through an attribute decoder:

- the Security Descriptors table (OID 0x530) keys on the SecurityId;
- the reparse-point index (OID 0x540 / 0x541) keys on the reparse tag and the file's 128-bit reference, behind the
  marker 0x80000001;
- the [Schema Table](../structures/schema_table.md) keys on a schema id.

OID 0x520 is different: it is an ordinary directory, and its Change Journal file carries real attributes (the type-0xF0
parameters among them).

## Cross-references

- [Record placement and data residency](placement_and_residency.md): where a record sits, and where its bytes are
- [Record placement and data residency](placement_and_residency.md): the embedded-tree row format and the inline-or-extents decision
- [Directory Entries](../structures/directory_entries.md): the type-0x30 value, and the type-0x40 backing
- [Object Table](../structures/object_table.md): locates each directory's and system object's B+-tree
- [Schema Table](../structures/schema_table.md): the schemas of the tables (a file's record, a directory's own row, a data stream; the system tables)
- [`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md): the `$SI` field layout (`value+0x28` of a record)
- [`$OBJ_LINK`](../attributes/OBJ_LINK.md): the name and parent-OID row every directory and every split record carries
- [`$DATA`](../attributes/DATA.md), [`$NAMED_DATA`](../attributes/NAMED_DATA.md) and
  [`$SNAPSHOT`](../attributes/SNAPSHOT.md): the 0x80 and 0xB0 stream sub-records
- [`$EFS`](../attributes/EFS.md): the 0x100 encryption sub-record
- [Extent Records](../structures/extent_descriptors.md): the extent map inside an extent-form `$DATA`
- [WSL metadata](wsl_metadata.md): the `$LX*` extended-attribute mapping

## Evidence

- The four row types of a user directory's tree are a census of the corpus's directory trees.
- The sub-record types are a census of the embedded rows of the corpus. It is a lower bound: a set read in rows that
  moved to child pages can only add to it.
- The driver's attribute-definition table (the one `RefsGetAttributeTypeCode` walks) was read from the binaries of
  seven builds, 17134 to Insider 29574: the same table on all of them, except that 17134 has no 0x39.
- The instance-marker scheme and the two key forms, the per-type value formats and the 12-byte prefix are decompiled
  (E2) and confirmed on disk (RD).
- Type 0xF0 is created by `RefsSetupUsnJournal` (E2) and read on the volumes where the journal is active (RD).
- The 0xB0 snapshot-or-ADS tests are E2 (`RefsCreateStreamSnapshot`, `HasSnapshot`) and agree on every snapshot row
  of the corpus's ADS census (115 snapshot rows).
- The extended-attribute bit, and the rule to read it from the backing and not from the name row's copy, are
  registered findings. Two corpus volumes carry extended attributes on split records, both images of one real
  Windows installation: there the name rows' copy misses the bit for 8,140 and 6,827 names. The only two bits that
  ever differ between the two copies are 0x40000 and the Archive bit 0x20, and 0x20 is the one that can go the other
  way: set in the name row's copy while the backing lacks it, on 57 of 223,374 size-matched split names over 8 images.
- The counts behind the key rules: `key[0:8]` is the value length on 1,441,268 of 1,441,461 embedded rows over 141
  images (193 exceptions); `key[8:]` is the start of the value on all 314,249 0x39 rows counted, and on none of the
  others: 0x80 `$DATA` 928,502 rows, 0x90 `$I30_INDEX` 87,674, 0xD0 49,353, 0xE0 49,309, 0xB0 5,828, 0xC0 4,206,
  0x03 1,526 and the 3.4 type-0x38 `$OBJ_LINK` 523, 1,127,212 rows in all (overlap on 21.8 % of embedded rows).
- No sub-record of type 0x50, 0x60, 0x70 or 0xA0 occurs in a user object: a census of every directory own row, file
  record and backing of the 124 ReFS volumes of the corpus, in both key forms (2026-11-21).
- The multi-level embedded attribute tree and `$OBJECT_ID` not being supported are registered findings.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

<!-- findings: FS_SCHM_RA_005, FS_SNAP_RA_001, MD_ATTR_002, MD_ATTR_004, MD_ATTR_005, MD_ATTR_006,
               MD_ATTR_008, MD_ATTR_009, MD_ATTR_RA_003, MD_ATTR_RA_004, MD_ATTR_RA_007, MD_ATTR_RA_016,
               MD_ATTR_RA_019, MD_ATTR_RA_020, MD_DDIR_005, MD_UNSUP_RA_001, FS_REPS_RA_004, MD_USN_RA_004 -->
