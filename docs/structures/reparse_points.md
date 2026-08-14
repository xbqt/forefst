# Reparse Points

A reparse point is a per-file tag plus payload that redirects path resolution — a symlink, junction,
mount point, app-execution alias, or WSL special file. The per-file payload is the `$REPARSE_POINT`
attribute (type 0xC0, schema 0x1C0 on v3.7+ / schema 0x170 on v3.4). On top of that, ReFS keeps a global
**Reparse Index** (OID 0x540 / 0x541, schema 0x160) so that "list every file with reparse tag X" is a
range-scan instead of a whole-tree walk. This page documents the index's on-disk core; the per-file
buffer and the reparse-tag table live in [$REPARSE_POINT](../attributes/REPARSE_POINT.md).

## Reparse Index key — 24 bytes (fixed); value is EMPTY

The Reparse Index is a **pure existence index**: every row has a **0-byte value**, so the key itself is
the index entry. `0x540` (primary) and `0x541` are **byte-for-byte identical mirrors** (same key set on
every analysed volume). Decoded on disk:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Instance marker (u32) | 0x80000001 (single-instance) |
| 0x04 | 4 | Reparse tag (u32) | `IO_REPARSE_TAG_*` value — the primary sort key. The tag multiset matches the on-disk reparse tags exactly |
| 0x08 | 8 | Entry ordinal (u64) | A small per-entry ordinal (2–32 observed) — the low (`FileId`) half of the reparse file's 128-bit file reference. Driver: `[fcb+0x58]+0xf8`. |
| 0x10 | 8 | Home (creation) directory OID (u64) | The OID of the directory the reparse file was **created in** — the home half of its [FileRef](../concepts/file_ids.md); ReFS files have no own OID. Driver: `[fcb+0x58]+0x100`. This is the *creation* directory, frozen: it equals the current parent for a file that has never been moved, and stays at the creation directory when the file is relocated. Disk-verified that every index row sits at its file's creation directory — 262/262 for never-moved files across 13 images, and, on 881 relocated reparse objects (home ≠ current parent), 881/881 indexed at the creation directory with none at the current parent. |

Sorting by `(tag, …)` is what makes "enumerate all files with reparse tag X" an index range-scan rather
than a tree walk.

## The 0x540 / 0x541 mirror

The index is created at format time via `InitializeReparseIndexTable`, which builds the pair with
`MsCreateDurableFailoverTableObject` — the same durable-failover pattern used by other system tables, so
`0x541` is a full failover duplicate of `0x540`, not a delta. Both are present on every image, every
version v3.4 → Insider. The tag multiset in the index always matches the actual on-disk reparse tags,
which is the invariant a forensic tool can check the index against.

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
| `InitializeReparseIndexTable` | Initializes OIDs 0x540 / 0x541 with schema 0x160 at format time. |

## Forensic notes

- **Directories carry reparse points too.** Junctions and mount points are directory reparse points, and
  ReFS treats them as first-class — a directory can equally carry an integrity stream or extended
  attributes. The `specials reparse` subcommand enumerates both files *and* directories that hold a
  reparse tag, reconciling with `files --filter reparse`; the two list the same set. (The same holds for
  the `integrity` and `ea` categories, where directory-carried attributes are enumerated alongside files.)
- ADS (alternate data streams) cannot be written to symlink files on ReFS.
- The `ReparseTag` field at `$SI` offset 0x54 echoes the reparse tag for quick access without reading the
  full reparse data.

## Cross-references

- [$REPARSE_POINT](../attributes/REPARSE_POINT.md) — the per-file reparse buffer and the full reparse-tag table
- [$REPARSE (Reparse Index)](../attributes/REPARSE.md) — schema 0x160, the index attribute
- [Directory Entries](directory_entries.md) — reparse data stored as embedded sub-records
- [Schema Table](schema_table.md) — schemas 0x160, 0x170, 0x1C0
- [System OIDs](system_oids.md) — OIDs 0x540 and 0x541
- [Object Table](object_table.md) — OID resolution for the reparse-index tables
- [File IDs](../concepts/file_ids.md) — the FileRef whose home half the index key's 0x10 field records
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the reparse tag mirrored at `$SI+0x54`

## Evidence

The 24-byte index key, the empty-value/pure-existence behavior, and the byte-identical 0x540 ↔ 0x541
mirror are raw-disk decoded across the corpus (RD). That the key's 0x10 field is the **creation** directory
OID (frozen when the file is relocated), not merely the current parent, is disk-proven on 881 relocated
reparse objects — all indexed at their creation directory, none at their current parent. The index identity (OIDs 0x540 / 0x541, schema 0x160,
durable-failover creation) and the driver functions are confirmed in the decompiled driver (E2):
`InitializeReparseIndexTable` builds the pair with `MsCreateDurableFailoverTableObject`. See [how this was verified](../methodology.md) to trace these to the exact
images and measurements in `analysis/`.
