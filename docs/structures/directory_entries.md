# Directory Entries

Directory entries (type 0x30) are B+-tree rows within a per-directory B+-tree. Each file or subdirectory appears as a type 0x30 row in its parent directory's tree. The storage mode (resident vs non-resident) determines the value layout, and a parser must resolve that mode from the key flags before reading any field.

## B+-tree row header — 16 bytes

Every row in a B+-tree leaf begins with this header:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Row size (u32) | total byte size of the row (0x70 is the common value for a typical resident row, **not** a constant flag) |
| 0x04 | 2 | Key offset (u16) | Byte offset from row start to key data |
| 0x06 | 2 | Key length (u16) | -- |
| 0x08 | 2 | Reserved (u16) | a candidate deleted-row bit `0x04` here is E2-only and disk-**unconfirmable** (GN_IENT_004) — not relied upon |
| 0x0A | 2 | Value offset (u16) | Byte offset from row start to value data |
| 0x0C | 2 | Value length (u16) | -- |
| 0x0E | 2 | Reserved (u16) | -- |

See [B+-Tree Node](btree_node.md) for the page-level node structure that holds these rows.

## Key format (type 0x30)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 2 | Entry type (u16) | Row type identifier (0x0030 = filename, 0x0020 = reverse index, 0x0040 = extent descriptor) |
| 0x02 | 2 | Key flags (u16) | Determines value interpretation |
| 0x04 | var | Filename (UTF-16LE) | File or directory name |

### Key flags

Only **two** key_flags values exist on disk (distribution {0x01, 0x02} only, zero occurrences of 0x04):

| Value | Type | Value Size | Description |
|-------|------|-----------|-------------|
| 0x01 | Resident file | >84 bytes | File with inline data |
| 0x02 | Non-resident file | 84 bytes (v3.10+) / 72 bytes (v3.4–v3.9) | File with extent references |

A directory is stored with **key_flags 0x02** (the non-resident value layout) and is identified by the directory attribute bit `0x10000000` at value+0x40: `RefsAddFileNameIndexEntry` ORs the `0x10000000` bit into the attribute word. There is no separate 0x04 = directory flag.

The non-resident value length is **72 bytes on v3.4–v3.9 and 84 bytes on v3.10+** (measured across all corpus images) — the driver `RefsAddFileNameIndexEntry` sets `local_a8 = 0x54` (84) for v3.10+ volumes and `0x48` (72) for older ones.

## Resident file value (key_flags = 0x01) — variable size

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 40 | Structural metadata | Stream index (8B) + internal B+-tree management fields (32B) |
| 0x28 | 8 | Creation time | FILETIME (100 ns since 1601-01-01) |
| 0x30 | 8 | Modification time | FILETIME |
| 0x38 | 8 | Metadata change time | FILETIME |
| 0x40 | 8 | Last access time | FILETIME |
| 0x48 | 4 | File attributes (u32) | Win32 flags + ReFS extensions |
| 0x4C | 4 | Internal flags (u32) | ReFS-specific state |
| 0x50 | 8 | Security ID (u64) | Links to Security Descriptors table (OID 0x530) |
| 0x58 | 8 | File size (u64) | Logical file/stream size (= $DATA size). Equals the $DATA sub-record size on every measured v3.14 file, and is nonzero even on USN-inactive images — decisively FileSize. |
| 0x60 | 8 | Allocated size (u64) | Allocation ≥ file size (roundup-to-cluster on most; inline byte count for tiny files). |
| 0x68 | 8 | LastUsn (u64) | File's last USN = virtual byte offset of its most recent `$UsnJrnl:$J` record (OID 0x520). 0 if the journal is inactive. This (offset 0x68) is the per-file USN. |
| 0x70 | 8 | UsnJournalId (u64) | Journal epoch ID (one per volume); 0 if journal inactive. |
| 0x80 | 8 | NextFileId (u64) | Directory child-creation ordinal (mirrors $SI+0x58). |
| 0xA8+ | var | Embedded sub-record chain | $DATA / ADS / snapshot / EA / $EFS rows. **There is NO embedded $SI sub-record**: the type-0x30 value is an *index entry* that carries the USN-journal fields inline at 0x68/0x70. Version-dependent; see below. |

The resident value is an *index entry* that mirrors the file's own type-0x10 $STANDARD_INFORMATION at every offset **except 0x58/0x60**, where it carries FileSize / AllocatedSize instead of the $SI's (always-0) USN / DataSize fields. The own-row $SI total size is 116 bytes (0x74) on Win10 and 124 bytes (0x7C) on Win11. See [Standard Information](../attributes/STANDARD_INFORMATION.md) for that separate structure, and [Resident Storage](../concepts/resident_storage.md) for the threshold that keeps a file inline.

### Sub-record row count (offset 0x20 in resident value)

The value+0x20 field is a **count of embedded sub-record rows** in the resident file's inline B+-tree (the inline file object's sub-record table: 1 default $DATA + one row per ADS, snapshot, reparse, EA, and $EFS). It is **NOT** a fixed 1-6 enum. It equals the parsed sub-record row count in the large majority of resident files (the residual are deleted/marker rows). The count is unbounded: values up to **14** have been observed (e.g. a file with 12 ADS).

The values below are common cases (consequences of the count), not an exhaustive enumeration:

| Row Count | Common case |
|-----------|-------------|
| 1 | Normal file (default data stream only) |
| 2 | One extra component — sparse file or reparse point/symlink |
| 3 | Encrypted file ($DATA + $EFS), or EA/WSL file, or file with 1 ADS |
| 4 | File with 1 snapshot, or 2 ADS, or reparse + EA |
| 5+ | More ADS and/or snapshots (e.g. count=14 with 12 ADS) |

### Embedded sub-record markers

| Marker | Meaning |
|--------|---------|
| 0x80000001 | Single-instance attribute (reparse 0xC0, EA info 0xD0, EA 0xE0) |
| 0x80000002 | Multi-instance attribute ($DATA 0x80, $SNAPSHOT 0xB0) |

Sub-records begin at offset 0xA8+ and form a chain. Single-instance sub-records carry one attribute each; multi-instance sub-records may appear multiple times for streams with the same descriptor.

### ADS and snapshot sub-records (descriptor 0x000500B0)

Both alternate data streams (ADS) and snapshot streams are stored as multi-instance sub-records with the same descriptor 0x000500B0. The StreamSummary.Flags field (u16) at the start of the StreamSummary region discriminates them: **0 = ADS, 2 = snapshot**. See [$SNAPSHOT](../attributes/SNAPSHOT.md) for the value format.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Marker (u32) | 0x80000002 (multi-instance) |
| 0x04 | 4 | Descriptor (u32) | 0x000500B0 |
| 0x08 | var | Stream name | UTF-16LE null-terminated |
| -- | 0-6 | Alignment padding | Pad to (offset - marker_start) % 8 == 4 |

**Sub-record header** (immediately after alignment):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| +0x00 | 4 | Padding (u32) | Always 0 |
| +0x04 | 4 | Data area size (u32) | Value length minus 12 |
| +0x08 | 4 | Content offset (u32) | Always 0x0C |
| +0x0C | 4 | Summary size (u32) | Always 0x30 (48 bytes) |
| +0x10 | 2 | StreamSummary flags (u16) | **0 = ADS, 2 = snapshot** (bit 1 set by `RefsCreateStreamSnapshot`) |
| +0x12 | 6 | Reserved | Always 0 |
| +0x18 | 8 | Allocated size (u64) | Cluster-aligned allocation |
| +0x20 | 8 | Stream size (u64) | Logical content length |
| +0x3C | var | Inline content | Present when SS flags = 0 (ADS only) |
| +0x44 | 8 | Stream index (u64) | Present when SS flags = 2 (snapshots only); links to DATA sub-record |

**Snapshot extent linking**: When SS flags = 2, the entry is a snapshot stream (NOT an ADS). The stream_index at header+0x44 matches a 0x000E0080 (DATA) sub-record's stream_index at sub_rec+0x08 within the same value, providing the extent table for the snapshot's content. See [$NAMED_DATA](../attributes/NAMED_DATA.md) and [$SNAPSHOT](../attributes/SNAPSHOT.md) for the value format.

### DATA sub-records (descriptor 0x000E0080)

Extent tables for non-resident content are stored in multi-instance sub-records with descriptor 0x000E0080. Multiple DATA sub-records may coexist in one value (default $DATA, ADS streams, internal streams).

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Marker (u32) | 0x80000002 |
| 0x04 | 4 | Descriptor (u32) | 0x000E0080 |
| 0x08 | 8 | Stream index (u64) | Matches ADS header+0x44 or default stream 0x0008 |
| 0x10 | var | Extent table | See [Extent Descriptors](extent_descriptors.md) |

## Non-resident file value (key_flags = 0x02) — 84 bytes (v3.10+) / 72 bytes (v3.4--v3.9)

Directories also use this layout (key_flags 0x02) and are identified by the directory attribute bit `0x10000000` at offset 0x40.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Child ordinal (u64) | Per-directory child ordinal (= the NextFileId ordinal of `$SI+0x58`). Shared by all hard-link names of one file; it is reused per directory and collides across sibling dirs under a shared home, so it is **not a globally-unique FileId**. Also indexes the type-0x40 extent descriptor. See [Hard links](#hard-links). |
| 0x08 | 8 | Home-dir backref (u64) | OID of the directory the file was first created in. Identical for every entry in/under a home dir. |
| 0x10 | 8 | Creation time | FILETIME |
| 0x18 | 8 | Modification time | FILETIME |
| 0x20 | 8 | Metadata change time | FILETIME |
| 0x28 | 8 | Last access time | FILETIME |
| 0x30 | 8 | Allocated size (u64) | Total allocated bytes (cluster-aligned) |
| 0x38 | 8 | File size (u64) | Logical content length |
| 0x40 | 4 | File attributes (u32) | Win32 flags + ReFS extensions (dir bit 0x10000000) |
| 0x44 | 4 / 12 | Padding | Zero; 4 bytes on v3.4--v3.9 (total 72), 12 bytes on v3.10+ (total 84) |

## Critical layout differences

Timestamps and most fields are at **different offsets** between resident and non-resident entries:

| Field | Resident Offset | Non-Resident Offset |
|-------|----------------|---------------------|
| Creation time | +0x28 | +0x10 |
| File attributes | +0x48 | +0x40 |
| Security ID | +0x50 | Not present (must be fetched from $SI via Object Table) |
| File size | +0x58 | +0x38 |
| Allocated size | +0x60 | +0x30 |
| LastUsn (per-file USN) | +0x68 (= $SI+0x40) | Not present (fetch from $SI) |
| UsnJournalId | +0x70 (= $SI+0x48) | Not present (fetch from $SI) |

A parser **must** resolve the storage mode from key_flags before reading any timestamp. Applying the wrong offset layout will misparse every field.

## Hard links

When a file gains a second name it is promoted to the **non-resident** layout above (key_flags 0x02), and each name becomes its own type-0x30 entry. All of one file's names share `value+0x00` (the per-directory child ordinal) and `value+0x08` (the home-dir backref) — both already in the non-resident value table above. There is no explicit on-disk HardLinkCount field, and `$SI+0x70` is a resident-layout scalar that always reads 1, so the link count is **derived** by resolving each name to its size-matched type-0x40 stream rather than read from a field. Hard links are a native v3.14 feature. See [Hard Links](../concepts/hard_links.md) for the full resolution model and forensic implications.

## Reverse index (type 0x20)

A directory's tree also carries type 0x20 rows: a per-object FileId-resolution index that maps a child index back to either the object's name (Format A) or its home-directory back-reference (Format B). Not every type 0x30 child has a corresponding type 0x20 row. The full key and value layouts are in [Reverse Index](reverse_index.md).

## Cross-references

- [Reverse Index](reverse_index.md) -- the type 0x20 FileId-resolution rows in the same directory tree
- [Extent Descriptors](extent_descriptors.md) -- non-resident files link to type 0x40 extent rows
- [Object Table](object_table.md) -- the home-dir backref in non-resident entries resolves via the Object Table
- [Standard Information](../attributes/STANDARD_INFORMATION.md) -- $SI layout differs by version
- [Resident Storage](../concepts/resident_storage.md) -- threshold rules for resident vs non-resident
- [Hard Links](../concepts/hard_links.md) -- multi-name files and the size-matched link count

## Evidence

The key/value layouts, the version size split (84/72 bytes), the {0x01, 0x02}-only key-flag census, the resident/non-resident field offsets, the sub-record markers and descriptors, and the 0 = ADS / 2 = snapshot discriminator are raw-disk decoded across the corpus (RD) and corroborated in the driver (E2): `RefsAddFileNameIndexEntry` ORs the directory bit and gates the 84/72-byte length, `RefsCreateStreamSnapshot` sets the snapshot StreamSummary bit, and the hard-link identity pair is written by `RefsLinkFileToSelf`. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
