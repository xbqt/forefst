# $DATA
<!-- site: description "A file's main data stream: its content, inline in the record or in on-disk extents." -->

> The descriptor's *form* — not the record's placement, and not the file's size — tells you whether the data is inline or in extents. See [Record placement and data residency](../concepts/placement_and_residency.md).

`$DATA` is a file's default data stream (embedded type 0x80).

- Its bytes are stored either inline in the file's record or in on-disk extents.
- Which one is decided by the volume format, the stream's size, and any conversion that moved the stream to extents
  (see [Residency](#residency)).
- Where the *record* sits (embedded in the name row, or split into a type-0x40 backing) is a separate property:
  see [Record placement and data residency](../concepts/placement_and_residency.md).

| Property | Value |
|----------|-------|
| Type code | 0x80 |
| Instances | single-instance (marker 0x80000001) for the inline form; multi-instance (marker 0x80000002) for the extent form (on 3.4 its key carries no marker). A record carries its main `$DATA` in one form, never both |
| Where it lives | the file's record: its type-0x30 name row (an embedded record) or its type-0x40 backing (a split record) |
| Size | inline form: 60 bytes (0x3C) + the allocated size; extent form: a 0x88-byte header, then the extent map |
| Added in | 3.4 or earlier: present on every format read (3.4, Windows 10 1803, driver 17134, is the oldest held). The inline form from 3.11 (the corpus holds no 3.11 to 3.13 volume; it is seen on 3.14) |

See [Directory Entries](../structures/directory_entries.md) for the sub-record chain that holds it.

## Residency

Whether the main `$DATA` is inline is a property of the volume format first:

| format | main `$DATA` |
|---|---|
| ≥ 3.11 | inline while the stream is under 2 KiB (`0x800`), extents at or above it; below 2 KiB a conversion can still have moved it to extents (below) |
| ≤ 3.10 | never inline. Every file's data is in extents — a 5-byte file still holds a whole cluster |

On ≥ 3.11 a stream under 2 KiB is in extents when something converted it:

- a stream snapshot, encryption, a block clone, a strictly-sequential or a remote setting, or an allocation or
  end-of-file setting of 2 KiB or more (the callers of `RefsConvertToNonResident`);
- creation on an integrity-streams volume, which makes a file extent-backed from its creation;
- a write made before the volume was upgraded from 3.10 or earlier.

Two further states exist on ≥ 3.11 and are neither inline nor plain extents: a stream whose descriptor is the extent
form and whose size is above 0, but which owns no allocation (`disk_alloc` at `+0x48` is 0).

- If a snapshot sub-record exists for the same stream, its bytes are the snapshot's — snapshot-shared, and still
  recoverable.
- If none does, nothing was ever written — reported as `unallocated`.
- (The word *sparse* is reserved for the `FILE_ATTRIBUTE_SPARSE_FILE` bit, which is a different fact.)

On disk the main `$DATA` is a sub-record of the file's record, in one of two forms: one single-instance entry
carrying the stream summary and the inline content, or a multi-instance entry carrying the sizes and the extent map.
A record carries one form, never both (no record measured carries both).

## Inline content — the single-instance record (format 3.11 and later)

The single-instance entry stores the stream-summary header and the inline file content.

Key (16 bytes):

<!-- site: hexfig "attr_data_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Value length (u64) | total value byte count |
| 0x08 | 4 | Marker (u32) | 0x80000001 (single-instance) |
| 0x0C | 2 | Type code (u16) | 0x0080 |
| 0x0E | 2 | Subtype (u16) | 0x0000 on every inline `$DATA` key measured |

Value:

<!-- site: hexfig-rows "attr_data_win11refstestmftecmd" "value" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | value length − 12 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | Summary size | 0x30 (48) |
| 0x10 | 8 | Reserved | 0 |
| 0x18 | 8 | Allocated size | stream allocated size (≈ file size, but not a fixed 8-byte round-up — e.g. a 129-byte file reads 129, not 136) |
| 0x20 | 8 | File size | exact stream length in bytes |
| 0x28 | 8 | Valid data length | equal to the file size (+0x20) on every inline `$DATA` value of the corpus (563,606) |
| 0x30 | 8 | Total allocated | usually equals allocated size |
| 0x38 | 2 | Checksum type | the table's checksum type: 2 on CRC64 volumes, 4 on SHA-256 volumes (see [Checksum fields](#checksum-fields)) |
| 0x3A | 2 | Integrity algorithm | 0 without integrity; the stream's per-cluster checksum type when integrity is on (see [Checksum fields](#checksum-fields)) |
| 0x3C | var | Inline content | the raw file bytes (file_size long) |

Size relationships: `value_length = 0x3C + allocated_size`, and `key[0:8] = value_length`. The minimum, 60 bytes
(0x3C), is an empty stream with no allocation.

### Checksum fields

The two u16 fields at `value+0x38` and `+0x3A` hold the stream's checksum settings; they are not a residency flag.

- `+0x38`, the table's checksum type: 4 on SHA-256 volumes, 2 otherwise (CRC64 volumes, and volumes with no data
  checksum).
- `+0x3A`, the stream's integrity algorithm: 0 without integrity. With integrity on, the driver takes it from the
  volume (26100.9444): on a CRC64 volume, 1 (CRC-32C) with 4 KiB clusters and 2 (CRC64) with larger ones. Read as one u32 with
  `+0x38`, an integrity stream on a 4 KiB-cluster CRC64 volume gives 0x10002; no corpus volume holds an integrity stream on 64 KiB
  clusters, so the CRC64 case is the driver's alone.
- Written by the driver's `RefsCreateDataAttribute`; `RefsSetIntegrity` sets the integrity algorithm.
- Measured over every inline file of the corpus (563,606 on 124 volumes): `+0x38` is 4 on every one of a SHA-256
  volume and 2 on every other; `+0x3A` is 1 on every inline file that has the integrity attribute (3) and 0 on every
  other. A file whose data is in extents has no such pair at these offsets (in that form `+0x38` is the stream size from 3.7 on): its
  integrity is in its record's table descriptor ([integrity streams](../concepts/integrity_streams.md)).

## Extent metadata — the multi-instance record

A file whose data is in extents has instead a multi-instance `$DATA` record (sub-stream id 0x1000) holding the
stream's sizes and its extent map; snapshots add one record per version.

- The key is 40 bytes on 3.7 and later: the marker 0x80000002 at `key+0x08`, type 0x0080 and subtype 0x000E (read
  as one u32, the descriptor 0x000E0080 of [Directory Entries](../structures/directory_entries.md)), the sub-stream
  id at `key+0x10`.
- The value does not use the common 12-byte sub-record header.

Value (extent record), format 3.14 layout (the offsets hold from 3.7):

<!-- site: hexfig "attr_data_ext_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Node offset | 0x88 (136) — all versions: where the extent map starts |
| 0x0C | 4 | Schema id | the data stream's table: 0x200 on 3.14; 0x1A0 on 3.4 to 3.10 |
| 0x30 | 8 | Total allocated | |
| 0x38 | 8 | Stream size | the stream size in this form (not the stream-flags field of the inline form) |
| 0x40 | 8 | Valid data length | equal to the stream size on every non-empty record measured (3.7 to 3.14); nothing is decided from it |
| 0x48 | 8 | Disk allocated | |
| 0x50 | 8 | Version count + sparse flag | low 31 bits = version count (1 for a single-version stream); bit 31 = a sparse flag in prior work, never observed set |
| 0x88 | var | Extent map | a B+-tree node holding the extent records (below) |

The extent map at `0x88` (the inner header size) is a B+-tree node: level at `+0x0C` (0 = leaf), row count at
`+0x14`, and on a leaf the rows are the extent records (24 bytes, or 24 + 4 × run with per-cluster checksums),
reached through the node's key index.

See [Where the extent records live](../structures/extent_descriptors.md#where-the-extent-records-live--a-b-tree-node).

CoW version namespace (in the key, not the value): the `sub_id` at key[16:20] selects the version:

- 0x8 = stream-set metadata / next-sub-id counter;
- 0x1000 = the live data version;
- 0x1001+ = CoW / snapshot versions.

### Format 3.4 difference (the extent record)

On format 3.4 the key is 14 bytes with no instance marker (type 0x80 at `key+0x08`), and the size fields sit 4
bytes later:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x34 | 8 | Total allocated | carries the allocation alone |
| 0x3C | 8 | Stream size | |
| 0x44 | 8 | Valid data length | |
| 0x4C | 8 | Disk allocated | 0 |
| 0x54 | 8 | Version count + sparse flag | as at 0x50 from 3.7 |

The node offset (0x88), the schema id 0x1A0 and the extent map at `0x88` are as above.

## Extracting inline content

1. Find the single-instance `$DATA` sub-record (marker 0x80000001, type 0x80).
2. Read the file size: `le64(value, 0x20)`.
3. Content starts at `value[0x3C]`, length = file_size bytes.

Note: a file's record also carries cached copies of the stream's size and allocated size, in its `$SI+0x30` /
`+0x38` slots (`value+0x58` and `value+0x60` of the name row or backing); a directory's own row holds 0 there. Where
a copy and this sub-record disagree, the sub-record is authoritative; see the cross-references.

## Cross-references

- [Directory Entries](../structures/directory_entries.md) — the sub-record chain inside type-0x30 values
- [$NAMED_DATA](NAMED_DATA.md) and [$SNAPSHOT](SNAPSHOT.md) — ADS and snapshots use the same stream-summary format
- [$STANDARD_INFORMATION](STANDARD_INFORMATION.md) — the `$SI+0x30` / `+0x38` size slots of a file's record
- [Extent Records](../structures/extent_descriptors.md) — the extent records and the node that holds them

## Evidence

Type 0x80 and the inline layout are read from the driver (`RefsCheckValidAttributeAccess`,
`GetChecksumTypeForStreams`, `SetResidentStreamSummary`) and decoded on 3.14 volumes; the extent-bearing layout is
decoded on disk across 3.4 to 3.14, among them that allocated_size is not a fixed round-up (rounded up to 8 on 18 of
19 values read) and that the `$SI+0x38` slot of a file's record holds the stream's allocated size. The page is
documented against the project's claim register. See [how this was verified](../methodology.md).

The measurements behind the text:

- One form per record: none of the 730,556 records measured carries both.
- Inline key subtype 0x0000 on 563,606 inline `$DATA` keys on 109 volumes.
- Sub-2 KiB extent-backed main streams: 86 over 24 volumes. Identified triggers: 13 encrypted and 12 snapshotted
  (callers of `RefsConvertToNonResident`), 11 written under ≤ 3.10 before an upgrade (the format gate), 6 created on
  integrity-streams volumes (extent-backed from their creation); 44 have no identified trigger.
- The allocation and end-of-file settings convert a stream only when the size set is 2 KiB or more
  (`RefsSetAllocationInfo` / `RefsSetEndOfFileInfo`, read on 26100.8115). A lab file given a 1 MiB allocation
  became extent-backed at 16 bytes; a `SetEndOfFile` before any write did not convert.
- Valid data length at `+0x40`: equal to the stream size on 75,112 of 75,112 non-empty records (3.7 to 3.14), never
  greater, never smaller.
- The 3.4 key (14 bytes, no marker) and the +4 shift of the size fields are measured on the 3.4 corpus volumes.
- The version count reads 1 on 31,662 of 31,678 stream records of a 3.14 and Insider census (the rest are
  snapshotted multi-version streams); bit 31 is set on none of them, and the census held no sparse file with extents.

<!-- findings: MD_ATTR_RA_009, MD_DATA_RA_008, MD_DATA_RA_009, MD_DATA_RA_010, MD_DATA_RA_011, MD_DATA_RA_022, MD_DATA_RA_024, MD_DATA_RA_025, MD_DATA_RA_029, MD_SI_RA_002, MD_SI_RA_016 -->
