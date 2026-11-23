# Reparse Points

A reparse point is a per-file tag plus payload that redirects path resolution — a symlink, junction,
mount point, app-execution alias, or WSL special file.

- The per-file payload is the `$REPARSE_POINT` attribute (type 0xC0).
- On top of that, ReFS keeps a global **Reparse Index** (OID 0x540 / 0x541, table schema 0x160) so that "list every
  file with reparse tag X" is a range-scan instead of a whole-tree walk.

This page documents the index's on-disk core; the per-file buffer and the reparse-tag table live in
[$REPARSE_POINT](../attributes/REPARSE_POINT.md).

## Reparse Index key — 24 bytes (fixed); value is EMPTY

The Reparse Index is a **pure existence index**: every row has a **0-byte value**, so the key itself is
the index entry. `0x540` and `0x541` are the two copies of one failover pair — neither is a primary — and are
**byte-for-byte identical** (same key set on every analysed volume). Decoded on disk:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Instance marker (u32) | 0x80000001 (single-instance) |
| 0x04 | 4 | Reparse tag (u32) | `IO_REPARSE_TAG_*` value — the primary sort key. The tag multiset matches the on-disk reparse tags exactly |
| 0x08 | 8 | Entry ordinal (u64) | A small per-entry ordinal (2–32 observed) — the low (`FileID`) half of the reparse file's 128-bit file reference. Driver: `[fcb+0x58]+0xf8`. |
| 0x10 | 8 | Home (creation) directory OID (u64) | The OID of the directory the reparse file was **created in** — the home half of its [FileRef](../concepts/file_ids.md); ReFS files have no own OID. Driver: `[fcb+0x58]+0x100`. This is the *creation* directory, frozen: it equals the current parent for a file that has never been moved, and stays at the creation directory when the file is relocated. Disk-verified that every index row sits at its file's creation directory: for every never-moved file measured, and for every relocated reparse object measured (home ≠ current parent), indexed at the creation directory with none at the current parent. |

Sorting by `(tag, …)` is what makes "enumerate all files with reparse tag X" an index range-scan rather
than a tree walk.

## The 0x540 / 0x541 mirror

The mount opens the index through `InitializeReparseIndexTable`, which calls `MsCreateDurableFailoverTableObject` — the
same durable-failover pattern used by other system tables, so `0x540` and `0x541` are two full copies of one table, not
a copy and a delta. Both are present on every image, on every format read (3.4 to 3.14). On every volume measured, the
tag multiset in the index matches the actual on-disk reparse tags, which is the invariant a forensic tool can check the
index against.

## WSL Linux symlink payload (LX_SYMLINK, tag 0xA000001D)

The general per-file buffer layout and the full reparse-tag table are on the
[$REPARSE_POINT](../attributes/REPARSE_POINT.md) page. One tag-specific payload is recorded only here —
the WSL Linux-symlink buffer, which carries a UTF-8 target rather than the UTF-16LE substitute/print-name
pair used by Windows symlinks:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Flags / version (u32) | WSL version flags |
| 0x04 | var | Target path | UTF-8 Linux-style path, no NUL terminator (length = ReparseDataLength − 4) |

WSL writes a *Windows* `IO_REPARSE_TAG_SYMLINK` (0xA000000C) when the link target is representable as a
Windows path (a relative name that resolves), and a *Linux* `LX_SYMLINK` (0xA000001D) when it is not — an
absolute Linux path (`ln -s /etc/passwd`) or an ext4 symlink copied with `cp -a`. In the Linux form the
version field is `2` and the UTF-8 target begins at buffer+0x0C (data+0x04), with `ReparseDataLength = 4 +
len(target)`.

## Driver functions

| Function | Purpose |
|----------|---------|
| `RefsSetReparsePointInternal` | Sets reparse data on a file. Writes the type-0xC0 attribute and updates the reparse index. |
| `RefsDeleteReparsePointInternal` | Calls `RefsDeleteAttributeRecord()` to remove the 0xC0 attribute and its index entry. |
| `RefsGetReparsePoint` | Retrieves reparse data for a file. |
| `RefsFlushReparseIndex` | Persists pending reparse-index changes to OID 0x540 / 0x541. |
| `InitializeReparseIndexTable` | Called at every mount from `RefsMountVolume`: opens the reparse index (OIDs 0x540 / 0x541, schema 0x160). 26100.9444 does not create a missing one; 17134 and Insider 29574 create it at mount when a mount condition holds. |

## Forensic notes

- **Directories carry reparse points too.** Junctions and mount points are directory reparse points, and
  ReFS treats them as first-class — a directory can equally carry an integrity stream or extended
  attributes. The `specials reparse` subcommand enumerates both files *and* directories that hold a
  reparse tag, reconciling with `files --filter reparse`; the two list the same set. (The same holds for
  the `integrity` and `ea` categories, where directory-carried attributes are enumerated alongside files.)
- ADS (alternate data streams) cannot be written to symlink files on ReFS (Windows refuses it on NTFS too).
- The `ReparseTag` field at `$SI` offset 0x54 echoes the reparse tag for quick access without reading the
  full reparse data.

## Cross-references

- [$REPARSE_POINT](../attributes/REPARSE_POINT.md) — the per-file reparse buffer and the full reparse-tag table
- [$REPARSE (Reparse Index)](../attributes/REPARSE.md) — the index table (schema 0x160)
- [Directory Entries](directory_entries.md) — reparse data stored as embedded sub-records
- [Schema Table](schema_table.md) — the reparse index's schema 0x160
- [System OIDs](system_oids.md) — OIDs 0x540 and 0x541
- [Object Table](object_table.md) — OID resolution for the reparse-index tables
- [File IDs](../concepts/file_ids.md) — the FileRef whose home half the index key's 0x10 field records
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the reparse tag mirrored at `$SI+0x54`

## Where a split record keeps its reparse buffer

When the object's record has been split out of its name row, the reparse tag is mirrored at `backing +0x7C`
of the file's own type-0x40 backing record, the one keyed by (owner directory, file id):

- on v3.14 the `REPARSE_DATA_BUFFER` goes with the record, embedded in that backing;
- on v3.7–v3.10 the backing carries only the tag mirror; the buffer was found only in copy-on-write copies of
  older pages, not in the live tree, and where the live one is kept is not settled.

A reader that looks only at the directory entry finds a reparse flag with no buffer behind it.

## How a symlink is stored

A symbolic link to a file is a file record carrying the reparse tag `0xA000000C` and, on most links, attributes
`0x420` (reparse point, archive). The record is embedded in its directory or, when the record is split, a backing;
its attributes can carry other bits too (integrity `0x8000` on some).

A symbolic link to a directory is a directory. Its entry in the parent carries `0x10000400` (directory, reparse
point) together with any hidden, system or not-indexed bits; on format 3.14 its own row carries the same bits without
the directory bit.

The target path appears **twice** in the reparse buffer, once as the substitute name and once as the print name: the
print name is the substitute name less its `\??\` prefix on an absolute link, and the same string on a relative one.
Measured on the corpus: file links on every format, directory links on format 3.14.

## Evidence

The 24-byte index key, the empty-value/pure-existence behavior, and the byte-identical 0x540 ↔ 0x541
mirror are decoded from the disk across the corpus. That the key's 0x10 field is the **creation** directory
OID (frozen when the file is relocated), not merely the current parent, is disk-proven on 881 relocated
reparse objects — all indexed at their creation directory, none at their current parent (881/881); the never-moved
files sit at their creation directory on 262/262 rows across 13 images. The index identity (OIDs 0x540 / 0x541, schema 0x160,
durable-failover creation) and the driver functions are confirmed in the decompiled driver:
`InitializeReparseIndexTable` opens the pair with `MsCreateDurableFailoverTableObject` at mount. A split record's reparse
buffer lives in its type-0x40 backing on v3.14, with the tag mirrored at `+0x7C`. These, the symlink attribute values and the doubled target path are registered findings, each with its own evidence tier and witness in the claim register.

See [how this was verified](../methodology.md) to trace these to the exact
images and measurements in `analysis/`.

<!-- findings: FS_OTBL_RA_004, FS_REPS_RA_004, MD_LK_RA_002 -->
