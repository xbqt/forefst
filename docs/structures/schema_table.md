# Schema Table

The Schema Table (roots #3/#9, schema 0xe060) is self-describing: it contains one entry per table type used by the volume.

Each entry fixes the key-comparison rules that let the generic B+-tree engine order rows without knowing their meaning.

## Key format — 4 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Schema ID (u32) | Unique schema identifier — the whole key |

The row's own `key_len` field reads **4**, on every Schema-Table row measured: 598 rows over 10 volumes
spanning formats 3.4, 3.7, 3.9, 3.10, 3.14 (4 KiB and 64 KiB clusters, SHA-256), an Insider build and an
upgraded volume — key-length histogram `{4: 598}`, **0 rows with an 8-byte key**. A key reads as the bare
schema id (`04000000`, `10010000`); there is no zero-padding word inside it.

## Value — schema definition (80 bytes, 20 × u32)

Each entry's value is an 80-byte definition (20 × u32) describing the table's layout. It is byte-identical across versions for a given schema ID. Notable fields:

| Field | Byte | Meaning |
|-------|------|---------|
| `u32[0]` | +0x00 | Definition size (0x50) |
| `u32[1]` | +0x04 | Key-descriptor size (0x18, constant) |
| `u32[6]` | +0x18 | Value-descriptor size (0x38, constant) |
| `u32[7]` | +0x1C | Key-comparison-rules selector (see below) |
| `u32[9]` | +0x24 | Self schema ID |
| `u32[13]` | +0x34 | Root-data size: 0x80 for the file and directory record tables (the `$SI`: 124 bytes, 116 on 3.4), 0x60 for a data stream's table |
| `u32[18]` | +0x48 | System flag (0x01) |

The field that fixes "the key-comparison rules" is **`u32[7]` (byte +0x1C) — the key-comparison-rules selector**, a small enum (disk-observed 1..0x11 across schemas), **not a bitfield**. The driver bounds-checks it `< 0x15` and uses it to index a key-rules dispatch table. For 0xe040 (Parent-Child Table) it is `8` → `CmsRulesPARENT_CHILD_LINK`; for 0xe0c0 (Container Table) it is `10`; for 0xe130 (Heat Engine) it is `17`. The schema object is registered by `RegisterSchema`; the rules table is read by `GetKeyRulesInternal`.

## Total schema count

Across all versions, there are **36 distinct schema IDs**: 18 system schemas (0xe010 and up) and 18 schemas of object
tables (below 0xe000). Any single volume has fewer, since schemas are added and retired across versions.

### Entry counts by version

| Version | System schemas | Object-table schemas | Total |
|---------|---------------|----------------------|-------|
| v3.4 | 15 | 12 | 27 |
| v3.7 | 15 | 15 | 30 |
| v3.9 | 16 | 15 | 31 |
| v3.10 | 15 | 15 | 30 |
| v3.14 | 13 | 16 | 29 |
| Insider | 14 | 16 | 30 |
| Upgraded (union) | up to 18 | up to 18 | up to 36 |

Totals are the on-disk schema-table leaf-row count (system ID ≥ 0xe000, object-table ID < 0xe000).

- The pre-3.14 count includes **two legacy schemas `0x04` and `0x06`**, present on every v3.4–v3.10 volume and
  retired at v3.14.
- v3.4 = 0x04, 0x06 + 0x110–0x1A0 (10) = 12; v3.7 / v3.9 / v3.10 = 0x04, 0x06 + 13 = 15.
- Upgraded v3.4→v3.14 volumes keep 0x04 / 0x06, so a "union" volume can reach 36.

## System schemas (18 distinct)

| Schema ID | Name | Purpose | Versions Present |
|-----------|------|---------|------------------|
| 0xe010 | Allocator Table | Three-tier allocator (roots 1, 2, 12) | v3.4-Insider |
| 0xe030 | Object ID Table | OID-to-LCN mapping (roots 0, 5) | v3.4-Insider |
| 0xe040 | Parent-Child Table | Directory relationships (root 4) | v3.4-Insider |
| 0xe050 | Object Data Table | Vestigial (legacy) | v3.4-v3.9 |
| 0xe060 | Schema Table | Self-describing schemas (roots 3, 9) | v3.4-Insider |
| 0xe070 | Reserved / Placeholder | Vestigial (legacy) | v3.4-v3.10 |
| 0xe080 | Integrity State | Per-extent integrity tracking (root 11) | v3.4-Insider |
| 0xe090 | Upcase / Logfile Info | Unicode case mapping + MLog metadata | v3.4-Insider |
| 0xe0b0 | Block Refcount | Shared block reference counts (root 6) | v3.4-Insider |
| 0xe0c0 | Container Table | Virtual-to-physical mapping (roots 7, 8) | v3.4-Insider |
| 0xe0d0 | Trash Table | Async deletion queue (OID 0x0D) | v3.4-Insider |
| 0xe0e0 | System Directory Entry List | Vestigial (legacy) | v3.4-v3.10 |
| 0xe0f0 | System File Stream | Vestigial (legacy) | v3.4-v3.9 |
| 0xe100 | Container Index | Container lookup by state (root 10) | v3.4-Insider |
| 0xe110 | Read Cache Metadata | Read-ahead caching metadata | v3.4-Insider |
| 0xe120 | Candidate Table (Dirty Range) | Dirty page tracking for checkpoint | v3.9-Insider |
| 0xe130 | Heat Engine | The heat engine's I/O metrics by 10-minute generation: the table of OID 0x30 | v3.10-Insider |
| 0xe140 | Volume Attestation Table | TPM-bound attestation data | Insider only |

The names of 0xe050, 0xe070, 0xe0e0 and 0xe0f0 are inferred from their tables' structure; no symbol names them.

## Object and table schemas (18 distinct)

A schema describes a whole table: how its keys compare, the size of its root data, its flags. It does not describe an
attribute. An attribute (`$DATA`, `$EA`, a reparse point ...) is a row of a table and has no schema of its own.

Each file and each directory holds its own small table, embedded in a row (a file's in its name row or its backing
record, a directory's in its own row, type 0x10); the row's value starts with the table's 40-byte descriptor, whose
+0x0C is the schema id below (see
[Directory Entries](directory_entries.md#embedded-record-value-key_flags--0x01)). A data stream kept in extents has a
table of its own, in its `$DATA` record.

| Schema ID | The table it describes | Versions present |
|-----------|------------------------|------------------|
| 0x180 | A file's record table, on a volume formatted below 3.6 | v3.4-Insider |
| 0x1C0 | A file's record table, formats 3.6 to 3.10 | v3.7-Insider |
| 0x1E0 | A file's record table, formats 3.11 and later | v3.14-Insider |
| 0x190 | A directory's own-row table, formats below 3.6 | v3.4-Insider |
| 0x1D0 | A directory's own-row table, formats 3.6 to 3.10 | v3.7-Insider |
| 0x1F0 | A directory's own-row table, formats 3.11 and later | v3.14-Insider |
| 0x1A0 | A data stream's table (the `$DATA` record in extent form), formats below 3.11 | v3.4-Insider |
| 0x200 | A data stream's table, formats 3.11 and later | v3.14-Insider |
| 0x130 | A directory: the B+-tree of its names (OID 0x520, the root 0x600 and every user directory) | v3.4-Insider |
| 0x140 | The security-descriptor table (OID 0x530) | v3.4-Insider |
| 0x150 | The volume-information tables (OIDs 0x500 / 0x501) | v3.4-Insider |
| 0x160 | The reparse index (OIDs 0x540 / 0x541) | v3.4-Insider |
| 0x110 / 0x170 / 0x120 | An older set for a file's record / a directory's own row / a data stream, used by the 17134 driver on a volume whose boot sector lacks flag 0x04 ([VBR](vbr.md)); no corpus object carries them | v3.4-Insider |
| 0x1B0 | Registered with the shape of a file's record table; no driver code read uses it and no corpus object carries it: its role is not read | v3.7-Insider |
| 0x004 | Legacy fixed-format (descriptor_size=0x50) | v3.4-v3.10 |
| 0x006 | Legacy variable-format (anomalous properties) | v3.4-v3.10 |

### Which id a record carries

The driver picks the file, directory and data-stream ids when it mounts the volume, from the volume's format version.

- A new object gets the ids of the volume's format.
- An object created under an older format keeps its old id until it is opened on a volume of format 3.6 or later. The
  driver then moves its table to the current id: it rewrites the id, or re-keys the table's rows when the key format
  changed.
- So a volume upgraded from 3.4 to 3.14 holds both: on the upgraded volumes of the test corpus, 1,221 file records and
  199 directory own rows still carry an older id.

For an examiner, the id therefore says under which format an object was created or last converted, not what the
object holds. A file record with schema 0x1E0 is an ordinary 3.11+ file; it does not mean the file has an extended
attribute.

## Names, type codes and schemas

Three numbering systems meet in a record. One is not derived from another:

1. **Attribute name and type code**: the driver's attribute-definition table pairs each name with a type code (0x10
   `$STANDARD_INFORMATION`, 0x80 `$DATA`, 0x90 `$INDEX_ROOT`, 0xB0 `$NAMED_DATA`, 0xC0 `$REPARSE_POINT`, 0xD0
   `$EA_INFORMATION`, 0xE0 `$EA` ...). The type code is what a sub-record's key carries.
2. **Row type**: the first u16 of a directory row's key (0x10 own row, 0x20 reverse index, 0x30 name, 0x40 backing
   record).
3. **Schema id**: the table a record or a system object is (the table above).

The `$STANDARD_INFORMATION` is not a sub-record at all: it is the root data of the object's table, at value+0x28.

### Directory entries carry only the long name

A directory's names are its type-0x30 rows, keyed by the full long name. **ReFS has no 8.3 short names**: there is no
separate short-name entry and no short-name field (refs.sys has no 8.3-generation code; all `8dot3`/`ShortName` code
lives in fsutil.exe; `fsutil file setshortname` returns "A local NTFS volume is required").

ReFS also does **not** duplicate the four MACB timestamps in a name entry the way NTFS does in `$FILE_NAME`, so the
NTFS `$SI`-vs-`$FILE_NAME` timestomp cross-check does **not** exist on ReFS **for a single-named file**.

A **hard-linked** file differs: each name is a separate type-0x30 row carrying its own MACB (value
+0x10/+0x18/+0x20/+0x28), and those rows can diverge. This is a journal-independent lead (forefst's
`HARDLINK_MACB_MISMATCH` signal).

- A divergence of the names' Created times is evidence.
- Their Changed times diverge routinely: a hard link added later carries the time it was added.
- Agreement does not show that the times are genuine: the file's own record takes a new time for every name at once,
  and each name's row is a copy refreshed when the file is opened, read and closed through that name.

## Failover

Root #3 (table ID 0x01) and root #9 (table ID 0x06) form a failover pair.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) -- roots #3 and #9 in the root pointer list
- [Object Table](object_table.md) -- schema 0xe030 governs its key comparison
- [Container Table](container_table.md) -- schema 0xe0c0
- [Container Index](container_index.md) -- schema 0xe100
- [System OIDs](system_oids.md) -- OIDs for system tables referencing these schemas

## Evidence

The Schema Table identity (roots #3/#9, table IDs 0x01/0x06, schema 0xe060, virtual addressing) is read in the
`CmsSchemaTable` class of the driver and parsed on every analysed image. The key/value layout and the `u32[7]`
key-comparison-rules selector are read in `RegisterSchema` / `GetKeyRulesInternal`; the rows on disk are the entries of the driver's
own schema set (a data block, `RefsSchemaSet`), except words 15 / 16 of every row and the key type and a flag bit of
the stream-set schemas 0x120 / 0x1A0 (why they differ is not read). `u32[7]` is a key-comparison-rules enum
(disk-observed 1..0x11), bounds-checked `< 0x15` and used to index the key-rules dispatch table.

The measurements and readings behind the text:

- The roles: the mount's three slots (file, data stream, directory) set by format version in `RefsMountVolume`, on
  every driver build read (17134 to Insider 29683); the upgrade on open in `OpenRefsObjectForFcb` (26100.9444); 0x140 created for
  OID 0x530 by `RefsSecurityInitialize`, 0x150 / 0x160 by `InitializeVolumeInfoTable` / `InitializeReparseIndexTable` (26100.9444);
  0x110 / 0x120 / 0x170 used by 17134 only without the boot-sector flag 0x04.
- On disk: every record of the 124 ReFS volumes of the corpus (820,293 records) carries its format's id, the older ids
  only on volumes upgraded to 3.14; no object carries 0x110, 0x120, 0x170 or 0x1B0. The roots of OIDs 0x500, 0x520,
  0x530, 0x540 and the user directories carry 0x150, 0x130, 0x140, 0x160 and 0x130 on a 3.4, a 3.7 and a 3.14 volume.
  The data streams' `$DATA` records carry 0x1A0 on 3.7 and 3.10 and 0x200 on 3.14 (3,197 records).
- The 36 distinct schema IDs and the per-version entry counts are re-measured across the corpus.
- The "no 8.3 short names" and "no `$SI`-vs-`$FILE_NAME` timestomp cross-check for a single-named file" facts are
  read in the driver; the per-name hard-link exception is measured on disk.

The page is documented against the project's claim register. See [how this was verified](../methodology.md).

<!-- findings: FN_LINK_003, FS_PCTB_RA_001, FS_SCHM_001, FS_SCHM_RA_002, FS_SCHM_RA_003, FS_SCHM_RA_005,
               FS_SCHM_RA_008, FS_SCHM_RA_009, FS_SCHM_RA_010, FS_SCHM_RA_011, FS_SCHM_RA_012, FS_SCHM_RA_013,
               FS_SECD_RA_003, FS_VBR_RA_015, GN_IDXR_RA_005, MD_TS_RA_005, MD_UNSUP_RA_001 -->
