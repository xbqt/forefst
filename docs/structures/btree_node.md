# B+-Tree Node (MSB+ Page)

All ReFS metadata is stored in B+-trees with the signature `"MSB+"`. Each node occupies one metadata page: 16 KiB (4 consecutive clusters) on 4 KiB-cluster volumes, or 64 KiB (1 cluster) on 64 KiB-cluster volumes. An MSB+ page is built from four regions in order: the page header, a node header, the key-value data area, and a sorted key index.

## B+-tree row header (16 bytes)

Each row in the data area begins with this header. The header points to where the key and value live within the row; both are measured from the start of the row.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Row size (u32) | Total byte size of the row, used as the stride to the next row. The value region is always last. (0x70 is the common value for a typical resident row, but it is a size, not a constant flag.) |
| 0x04 | 2 | Key offset (u16) | Byte offset from row start to key data |
| 0x06 | 2 | Key length (u16) | — |
| 0x08 | 2 | Reserved (u16) | — |
| 0x0A | 2 | Value offset (u16) | Byte offset from row start to value data |
| 0x0C | 2 | Value length (u16) | — |
| 0x0E | 2 | Reserved (u16) | — |

Rows are written sequentially in insertion order (not necessarily sorted); the sorted key index below restores order for lookups.

## Page layout

### 1. Page header (80 bytes)

The common metadata page header shared with SUPB and CHKP. See [Page Header](page_header.md).

Key MSB+-specific header fields:
- **LCN slots 0--3** (offsets 0x20--0x38): cluster addresses of this page's extent. On 4 KiB-cluster volumes, all four slots are used with consecutive values (`[self, self+1, self+2, self+3]`). On 64 KiB-cluster volumes (where a page is 1 cluster), only slot 0 is meaningful.
- **Table OID** (16-byte identifier at 0x40--0x4F): the high half at 0x40 (`TableIdHigh`) is **always 0** in practice, because table OIDs are small integers; the numeric table OID (e.g. 0x02 = Object ID Table, 0x0B = Container Table) is `TableIdLow` at **0x48** — the field the driver reads and compares. It is retained on orphaned/CoW-discarded pages, enabling identification.

### 2. Node header

A per-page node header (`_SmsIndexHeader`) follows the page header on every node, root and non-root alike. It describes that page's own row set:
- Data-area boundaries (the row-data high-water cursor and free-space size)
- Row-pointer (key index) array boundaries
- Node type at +0x0C (**0 = leaf, nonzero = internal/index node**) and node flags at +0x0D (bit 0 set marks an index page)
- The **per-node** row/key count at +0x14 — the number of rows on this page (children for an inner node, leaf rows for a leaf). This is *not* the whole-table total.

On root nodes only, an **index root descriptor** (`_SmsIndexRoot`, Prade's "Index Root") precedes the node header at page+0x50, providing table-level metadata: the schema id, the leaf-extent count, and the **total row count for the whole table** (distinct from the per-node count above — on a multi-level tree they diverge cleanly). See the [Schema Table](schema_table.md) for how the schema id selects key comparison rules.

### 3. Data area (key-value pairs)

Contains the actual row data: each row is the 16-byte row header above followed by its key and value bytes.

### 4. Key index (sorted offsets)

An array of offsets into the data area, maintained in sorted order according to the table's key comparison rules (defined by the [Schema Table](schema_table.md)). A binary search on this array locates a row without scanning the entire data area.

## Inner vs leaf nodes

| Property | Inner Node | Leaf Node |
|----------|-----------|-----------|
| Contains user data | No | Yes |
| Value content | Page references to child nodes | Actual key-value data |
| Key content | Separator keys (routing) | Full keys |
| Node-type byte (header +0x0C) | Nonzero | 0 |

Inner node values are [page references](page_references.md) (48, 72, or 104 bytes depending on checksum configuration) that point to child pages. The page reference format matches the one stored in the [Checkpoint](chkp.md) root pointer list.

## Tree depth

Observed depths range from 1 (a root-only leaf, for small tables) to 2+ levels (a root inner node over leaf nodes). Tens of thousands of entries fit comfortably in a 2-level tree.

## Orphaned pages

When copy-on-write replaces a page, the old page becomes orphaned but retains its original Table OID (the numeric value at header offset **0x48** = `TableIdLow`; the 0x40 high half is always 0). This enables forensic identification of discarded pages — they belong to a known table but are no longer reachable from the current checkpoint.

## Driver functions

| Function | Purpose |
|----------|---------|
| `MsInsertRow` | Inserts a key-value pair into a B+-tree. Handles page splits when a leaf is full. |
| `MsDeleteRow` | Removes a key-value pair. Handles page merges when occupancy drops. |
| `MsLookupAllocation` | Queries allocation state via B+-tree lookup. Core read path. |
| `EnumerateBPlusTable` | Iterates all entries in a B+-tree in key order. |
| `MsAllocateRowWithBuffer` | Allocates a B+-tree row with a pre-sized buffer for the value. |

## Cross-references

- [Page Header](page_header.md) — the 80-byte header shared by all metadata pages
- [Page References](page_references.md) — the format used in inner node values
- [Schema Table](schema_table.md) — defines key comparison rules per table type
- [Checkpoint (CHKP)](chkp.md) — root pointers to the top-level B+-trees

## Evidence

The B+-tree storage engine and the MSB+ page model are confirmed in the driver (E2: the `CmsBPlusTable` / `CmsTable` classes) and raw-disk verified across the corpus (RD: every metadata page carries the `MSB+` signature). The row header, node header, and index-root descriptor offsets are decompiled-confirmed (E2) and re-measured on disk (RD): the node-type byte and the per-node count at header +0x14 hold on every leaf/inner page measured, and the index-root total-row count tracks an independent leaf-walk. The 0x40/0x48 table-OID split (always-0 high half, numeric low half) is the same. The insert/delete/lookup/enumerate/allocate functions are PDB symbols in the driver. Findings: **GN_ARCH_001**, **GN_ARCH_005**, **GN_PAGE_007**, **GN_IDXR_004**. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
