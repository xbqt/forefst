# B+-Tree Node (MSB+ Page)

The ReFS tables — the system tables and every directory's own tree — are B+-trees whose pages carry the signature
`"MSB+"`. The boot sector, superblock, checkpoint and log have their own formats.

Each node occupies one metadata page:

- 16 KiB (4 consecutive clusters) on 4 KiB-cluster volumes;
- 64 KiB (1 cluster) on 64 KiB-cluster volumes.

An MSB+ page is built from four regions in order: the page header, a node header, the key-value data area, and a
sorted key index.

## B+-tree row header (16 bytes)

Each row in the data area begins with this header. The header points to where the key and value live within the
row; both are measured from the start of the row.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Row size (u32) | Total byte size of the row, pad8(value offset + value length), used as the stride to the next row; the value region is always last (0x70 is a common size, not a flag) |
| 0x04 | 2 | Key offset (u16) | Byte offset from row start to key data |
| 0x06 | 2 | Key length (u16) | — |
| 0x08 | 2 | Flags (u16) | Bit `0x4`: the row was removed from the key index, by a delete or by an update that replaced it (not necessarily a deleted file). The row stays in the data area, or past its high-water when it was the last one; every unlisted row in the data areas of the test corpus carries the bit, and no listed row does. Bits `0x1` and `0x2` occur on listed rows |
| 0x0A | 2 | Value offset (u16) | Byte offset from row start to value data |
| 0x0C | 2 | Value length (u16) | — |
| 0x0E | 2 | Reserved (u16) | 0 |

Rows are written sequentially in insertion order (not necessarily sorted); the sorted key index below restores
order for lookups.

## The root descriptor — a second structure on the same page

A **root** page carries two structures, and confusing them is the most frequent mistake in this
area: an earlier correction refuted a prior-work claim by measuring the wrong one, and had to be retracted.

`_SmsIndexRoot` sits at a fixed **`page + 0x50`** and describes the *table*. The node header below
describes *one page* of it. They overlap in offsets and disagree in meaning:

| Offset | `_SmsIndexRoot` descriptor (page+0x50, root pages only) | the node header at `thoff` |
|--------|--------------------------------------------------------|-----------------------------|
| +0x00 | offset from here to the node header — this is what locates `thoff` | — |
| +0x04 | descriptor size, `0x28` — **a `u16`, not a `u32`** | The low half is `0x0028` on **every root page measured**; the upper half (+0x06) is a separate field that tracks the table — `0xE010` on allocator pages, `0x0001` on the tables of schemas `0x0130` to `0x0160` (directories, the security, volume-information and reparse tables), `0x0000` on every `0xEnnn` system table. Reading the whole `u32` as the size is wrong on **nearly three root pages in four** |
| +0x0C | **the table's schema id** (`0xe0c0` Container Table, `0xe030` Object Table, `0x130` directory …) | node level: 0 = leaf |
| +0x14 | a u16 the driver requires to equal the volume's checksum type (2 on most volumes; 4 on a SHA-256 volume, measured in embedded records), then at +0x16 a u16 integrity setting | rows on **this page** |
| +0x18 | **leaf-page / extent count for the whole table** | a u64, 0 on disk |
| +0x20 | **row count for the whole table** | end of the row-pointer array |

The two row counts are the clearest illustration: on a multi-level table the descriptor's `+0x20` counts
every row in the table while the node header's `+0x14` counts only the current page — measured at **387
versus 10** on one object tree, and **245,759 versus 2** on a large container table. A reader that takes
the node figure for the table total under-reports by whatever the tree's fan-out happens to be.

Read the descriptor when you want to know what a table *is* — its schema, its size — and the node header
when you are walking one page.

## Page layout

### 1. Page header (80 bytes)

The common metadata page header shared with SUPB and CHKP.

See [Page Header](page_header.md).

Key MSB+-specific header fields:

- **LCN slots 0--3** (offsets 0x20--0x38): the clusters of this page, as the reference that reached it addresses
  them (virtual LCNs for a page read through the Container Table).
  - On 4 KiB-cluster volumes all four slots are used, with consecutive values (`[self, self+1, self+2, self+3]`).
  - On 64 KiB-cluster volumes (where a page is 1 cluster) only slot 0 is used; slots 1-3 are 0.
- **Table OID** (16-byte identifier at 0x40--0x4F): the high half at 0x40 (`TableIdHigh`) is **always 0** in
  practice, because table OIDs are small integers; the numeric table OID (e.g. 0x02 = Object ID Table, 0x0B =
  Container Table) is `TableIdLow` at **0x48** — the field the driver reads and compares. It is retained on
  orphaned/CoW-discarded pages, enabling identification.

### 2. Node header

A per-page node header (`_SmsIndexHeader`) follows the page header on every node, root and non-root alike. It
describes that page's own row set:

- Data-area boundaries (the row-data high-water cursor and free-space size)
- Row-pointer (key index) array boundaries
- Node type at +0x0C (**0 = leaf, nonzero = internal/index node**) and node flags at +0x0D (bit 0 set marks an index
  page)
- The **per-node** row/key count at +0x14 — the number of rows on this page (children for an inner node, leaf rows
  for a leaf). This is *not* the whole-table total.

The header is reached at `page + 0x50 + u32@(page + 0x50)`, and the fields a reader needs are:

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| +0x0C | 1 | Node level | 0 = leaf; non-zero = internal / index node |
| +0x0D | 1 | Node flags | Bit 0 marks an index page (its rows point at child pages). Prior work also assigns `0x2` = root and `0x4` = stream; only bit 0 has been re-measured here, so treat the other two as unconfirmed |
| +0x10 | 4 | Key-index array **start** | Offset, relative to the header, of the row-pointer array |
| +0x14 | 4 | Row count | Rows on **this page** |
| +0x20 | 4 | Key-index array **end** | One past the last entry |

Each key-index entry is **4 bytes**: a `u16` offset to the row (relative to the header) followed by a
`u16` **marker**.

That marker is not a count of anything, and it is **not two-valued**. Censused over every MSB+ page of the
baseline images that satisfies the page's own key-index invariant, it takes **dozens of distinct values**:

- `0xFFFF` on nearly every entry (more than 99 %);
- `0` on about one entry in seven hundred;
- the rest spread over the other values, the commonest `0x1`, `0x4001`, `0x8001`, `0x401`, `0x801` and `0xc01`,
  with a long tail including `0x3fdd`, `0x7fdd`, `0xcdc5`.

One image alone carries more than fifty distinct values. The counts are in the Evidence section.

`0` is **not confined to index pages** either: **some zeros sit on level-0 (leaf) pages**, **some are not
the last entry** of their page, and **a few pages carry more than one zero**. The common case — a single `0` on
the last entry of an index page, on a row with an empty key whose value is a page reference (the tree's
**rightmost child**) — is real and is what most zeros are, but it is a tendency, not a rule, and a reader
must not use `marker == 0` as a test for "rightmost child of an index page".

It is also a version marker. Volumes from **3.10** onward write the `0` there; **3.4 through 3.9** leave
`0xFFFF` on that same entry (on every such page measured, no exception). An **upgraded** volume keeps the old form on the pages
it inherited — the same retention that governs [directory-entry sizes](directory_entries.md), and a reminder
that the volume's current version does not tell you how any individual page was written.

> **Invariant — `(u32@+0x20 − u32@+0x10) / 4 == u32@+0x14`.** The array length and the row count must
> agree. Measured across the corpus: **no violation on any node page measured**, on ReFS 3.4, 3.7, 3.9, 3.10
> and 3.14, including the volumes an Insider build wrote. The driver's own check allows a longer array
> (`CheckIndexHeaderRecurse` tests `≥`), so the equality is what the volumes hold, not a driver rule. It is the
> cheapest structural check for "is this really a node page", and worth asserting before trusting any row on it.
>
> Note that a page is **not** one cluster: on a 4 KiB-cluster volume it is four, and the key-index array
> lives at the end of the *page*. Reading a single cluster leaves the array out of range and the row count
> reads as zero — a mistake that silently empties a scan rather than failing it.

On root nodes only, an **index root descriptor** (`_SmsIndexRoot`, Prade's "Index Root") precedes the node header at page+0x50, providing table-level metadata: the schema id, the leaf-extent count, and the **total row count for the whole table** (distinct from the per-node count above — on a multi-level tree they diverge cleanly).

The same 40-byte descriptor heads every table embedded in a row: a file's record, a directory's own row, a data
stream's `$DATA` record in extent form (see [Directory Entries](directory_entries.md#embedded-record-value-key_flags--0x01)).

See the [Schema Table](schema_table.md) for how the schema id selects key comparison rules.

### 3. Data area (key-value pairs)

Contains the actual row data: each row is the 16-byte row header above followed by its key and value bytes.

### 4. Key index (sorted offsets)

An array of offsets into the data area, maintained in sorted order according to the table's key comparison rules
(defined by the [Schema Table](schema_table.md)). A binary search on this array locates a row without scanning the
entire data area.

## Inner vs leaf nodes

| Property | Inner Node | Leaf Node |
|----------|-----------|-----------|
| Contains user data | No | Yes |
| Value content | Page references to child nodes | Actual key-value data |
| Key content | Separator keys (routing) | Full keys |
| Node-type byte (header +0x0C) | Nonzero | 0 |

Inner node values are [page references](page_references.md) (48 bytes with CRC64, 72 with SHA-256) that point to
child pages. The [Checkpoint](chkp.md) root pointer list holds the same structure, at the size the checkpoint
declares at +0x5C: 104 bytes on a volume formatted at 3.4 to 3.9.

## Tree depth

Observed depths range from 1 (a root-only leaf, for small tables) to 2+ levels (a root inner node over leaf nodes).

## Orphaned pages

When copy-on-write replaces a page, the old page becomes orphaned but retains its original Table OID (the numeric
value at header offset **0x48** = `TableIdLow`; the 0x40 high half is always 0).

This enables forensic identification of discarded pages — they belong to a known table but are no longer reachable
from the current checkpoint. Check the page's volume signature first: another volume's pages and deduplication index
content use the same page form ([Page Header](page_header.md#volume-signature-0x0c)).

## Driver functions

| Function | Purpose |
|----------|---------|
| `MsInsertRow` | Inserts a row through `CmsBPlusTable::AddToIndex`, which splits the leaf (`InsertWithBucketSplit`) when the row does not fit (26100.9444). |
| `MsDeleteRow` | Removes the row's index entry; pages are merged later, by `OptimizeTree` at checkpoint and persist time (26100.9444). |
| `MsLookupAllocation` | Maps a stream's VCN range to a container-translated LCN run, for reads and writes (26100.9444). |
| `EnumerateBPlusTable` | Iterates all entries in a B+-tree in key order. |
| `MsAllocateRowWithBuffer` | Allocates a B+-tree row with a pre-sized buffer for the value. |

## Cross-references

- [Page Header](page_header.md) — the 80-byte header shared by all metadata pages
- [Page References](page_references.md) — the format used in inner node values
- [Schema Table](schema_table.md) — defines key comparison rules per table type
- [Checkpoint (CHKP)](chkp.md) — root pointers to the top-level B+-trees

## Evidence

The B+-tree storage engine and the MSB+ page model are confirmed in the driver (the `CmsBPlusTable` / `CmsTable`
classes) and measured on the disk across the corpus (every table page walked carries the `MSB+` signature).

The row header, node header, and index-root descriptor offsets are confirmed in the decompiled driver and re-measured
on disk: the node-type byte and the per-node count at header +0x14 hold on every leaf/inner page measured, the
key-index array length agrees with that count on **118,351 pages of every format measured with zero violations**, and
the index-root total-row count tracks an independent leaf-walk. The 0x40/0x48 table-OID split (always-0 high half,
numeric low half) is the same. The insert/delete/lookup/enumerate/allocate functions are PDB symbols in the driver.

The `_SmsIndexRoot` descriptor's fields (its size, the schema, the leaf-page count and the whole-table row count) are
confirmed both in the decompiled `CmsBPlusTable::CreateIndex` path and across 113 images / 34,207 tables, as is the
descriptor field that locates the node header. The node-flags byte's `0x2`/`0x4` bit meanings come from prior work and
are not re-measured here.

The counts behind the text:

- the descriptor size at `+0x04`: low half `0x0028` on 1,432 of 1,432 root pages; the whole `u32` read as the size
  is wrong on 1,042 of 1,432;
- the key-index marker: censused over every MSB+ page on the 25 baseline images that satisfies its own key-index
  invariant (15,169 pages, 689,639 entries), 38 distinct values: `0xFFFF` on 685,755 entries, `0` on 963, and 2,921
  entries at 36 other values (`0x1` ×1085, `0x4001` ×515, `0x8001` ×285, `0x401` ×201, `0x801` ×179, `0xc01` ×154,
  and a long tail); `win11refstestmftecmd` alone carries 51 distinct values;
- of the zeros, 67 sit on level-0 (leaf) pages and 44 are not the last entry of their page; 3 pages carry more than
  one zero;
- formats 3.4 to 3.9 leave `0xFFFF` on the rightmost-child entry on 216 of 216 pages;
- the key-index invariant: 118,351 pages, 0 violations.

See [how this was verified](../methodology.md) for the method.

<!-- findings: GN_ARCH_001, GN_ARCH_005, GN_BPT_RA_001, GN_IDXH_001, GN_IDXH_002, GN_IDXH_003, GN_IDXR_001,
               GN_IDXR_002, GN_IDXR_003, GN_IDXR_004, GN_IENT_001, GN_IENT_002, GN_IENT_003, GN_IENT_005,
               GN_IENT_006, GN_PAGE_007, GN_TREE_RP_003, GN_UTIL_SA_001 -->
