# Parent-Child Table

The Parent-Child Table (root #4, schema 0xe040) encodes the directory hierarchy. It
records only directory-to-directory and directory-to-security-mapping relationships;
regular files are not tracked. The first row is always **0x600 → 0x520** (root directory →
the **FS Metadata** directory, the NTFS `$Extend` equivalent), confirming that system
directories are tracked too. OID 0x520 is FS Metadata; OID 0x530 holds security
descriptors.

## Row Format -- 48 bytes

Each leaf row consists of a 16-byte B+-tree row header followed by a 32-byte key/value
region.

### B+-Tree Row Header (16 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Row size (u32) | Total byte size of the row = 0x30 (48) for this table; the next-row stride |
| 0x04 | 2 | Key offset (u16) | Byte offset from row start to key |
| 0x06 | 2 | Key length (u16) | 32 bytes |
| 0x08 | 2 | Reserved (u16) | -- |
| 0x0A | 2 | Value offset (u16) | Same as key offset |
| 0x0C | 2 | Value length (u16) | 32 bytes |
| 0x0E | 2 | Reserved (u16) | -- |

### Key/Value Region (32 bytes -- shared)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Reserved (u64) | Always 0 |
| 0x08 | 8 | Parent OID (u64) | Object ID of parent directory |
| 0x10 | 8 | Reserved (u64) | Always 0 |
| 0x18 | 8 | Child OID (u64) | Object ID of child directory |

## Key Properties

- **key_offset == val_offset** and **key_length == val_length** in every leaf row: the key
  and value occupy the same 32 bytes
- The table is a **pure set/index** with no payload beyond the relationship
- Sort order: **(ParentOID, ChildOID)** ascending
- Zero quadwords at offsets 0x00 and 0x10 on every entry
- Total leaf row = **48 bytes** (16-byte B+-tree row header + the 32-byte shared key/value)
- Format is version-invariant from v3.4 through v3.14

**Why the value overlaps the key (mechanism):** it is **caller-side**, not a schema flag.
`CmsObjectTable::AddParentChildLink` passes the *same* 32-byte buffer as both key and value
(key_len == value_len == 0x20), and `CmsHashTable::InitializeIndexEntry` detects the pointer
overlap and sets `value_offset = key_offset`, omitting the separate key copy. No branch
tests the schema definition. The schema-definition selector `u32[7]` for `0xe040` is `8` →
`CmsRulesPARENT_CHILD_LINK` (the table's *key-comparison rule* — an enum, not a value-overlap
bitfield; see [Schema Table](schema_table.md)).

## Usage

The Parent-Child Table enables top-down directory traversal without reading individual
directory B+-trees. Given a parent OID, all child directory OIDs can be found by scanning
the table for matching ParentOID values. `CmsObjectTable::AddParentChildLink` adds a
`[parent_OID, child_OID]` pair for every directory entry creation, which is what enables
this reverse lookup.

This table does **not** contain regular file entries -- only directory-to-directory links
and directory-to-security-mapping links. To enumerate files within a directory, the
directory's own per-object B+-tree must be read via the Object Table.

The table is read via [CHKP](chkp.md) **root #4**, not the Object Table — it has no
OID-table entry. Row count scales with the volume's directory count.

## Raw example

The first Parent-Child row on a v3.14 image — the root directory `0x600` mapped to FS Metadata `0x520` — is 48 bytes (16-byte header + 32-byte key/value):

```text
+0x00:  30 00 00 00 10 00 20 00  00 00 10 00 20 00 00 00    <- B+-tree row header
+0x10:  00 00 00 00 00 00 00 00  00 06 00 00 00 00 00 00    <- Reserved=0, ParentOID=0x600
+0x20:  00 00 00 00 00 00 00 00  20 05 00 00 00 00 00 00    <- Reserved=0, ChildOID=0x520
```

The header's first u32 is `30 00 00 00` = **Row size `0x30` (48 bytes)** — the stride to the next row, *not* a flags constant. Key offset `0x10`, key length `0x20`; value offset `0x10` (overlapping the key); the 32-byte key/value then carries ParentOID `0x600` and ChildOID `0x520`.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) -- root #4 in the root pointer list
- [Object Table](object_table.md) -- OIDs in this table are looked up in the Object Table
- [Directory Entries](directory_entries.md) -- per-directory B+-tree entries for individual files
- [System OIDs](system_oids.md) -- OID 0x600 is the root directory
- [Schema Table](schema_table.md) -- schema 0xe040 and the `u32[7]` key-rules selector

## Evidence

The 32-byte key/value layout (Reserved/ParentOID/Reserved/ChildOID), the 48-byte total row
size, the shared key/value overlap, the (ParentOID, ChildOID) sort order, and the zero
quadwords at 0x00/0x10 are raw-disk decoded across the corpus (RD) and version-invariant
v3.4–v3.14. The parent-child tracking mechanism is corroborated in the driver (E2):
`CmsObjectTable::AddParentChildLink`, `PreCowParentChildLink`, and
`CmsObjectTable::DoomParentChild`. The value-overlaps-key
behaviour is caller-side: `AddParentChildLink` passes the same 32-byte buffer as key and
value, and `CmsHashTable::InitializeIndexEntry` collapses the duplicate by setting
`value_offset = key_offset`; the schema `u32[7]=0x08` is the key-comparison-rules selector
(`8 → CmsRulesPARENT_CHILD_LINK`), not a value-overlap bitfield. Findings: **FS_PCTB_RA_001**, **FS_PCHL_001**, **FS_OTBL_SA_010**. See [how this was verified](../methodology.md) to trace these to the exact images
and measurements in `analysis/`.
