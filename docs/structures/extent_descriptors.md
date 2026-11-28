# Extent Records

An extent record maps a run of a file's logical clusters (VCNs) to virtual cluster numbers (VLCNs).

A file's extent records are the rows of a small B+-tree node held in its `$DATA` record, at offset `0x88` of
that record (see [Where the extent records live](#where-the-extent-records-live--a-b-tree-node)).

That `$DATA` record sits in the file's name row or, when a move or a hard link split the record out of the
name row, in its type-0x40 backing record. A type-0x40 row is that backing, not an extent: it can hold the
file's data inline and then carries no extent at all.

A VLCN is not a physical address: it must be translated through the [Container Table](container_table.md)
to obtain the physical cluster where the data actually lives.

Every extent, even a single contiguous run, is one record: a 24-byte fixed part, followed by one 4-byte
CRC32-C per cluster when the run carries per-cluster checksums.

> **Do not sanity-check a VLCN against the volume's cluster count.** The virtual address space is *wider*
> than the physical one — it starts above the first container and runs roughly twice as far — so a valid
> extent can name a cluster number larger than the volume has. The only sound test is whether the
> Container Table can translate it.
>
> Getting this wrong loses data without any error: a decoder that walks extents in order and stops at the first
> "implausible" one throws the **whole** map away, and the file then looks as though it had no extents at
> all. On one volume measured that mistake hid the contents of more than nine files in ten. With the check
> corrected and the node walk below, every file of that volume reads back byte-perfect.

## Extent Entry — 24 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Virtual LCN (VLCN) (u64) | Requires Container Table for physical translation |
| 0x08 | 2 | Flags (u16) | See Extent Flags below |
| 0x0A | 2 | Record size (u16) | `24` for a plain run; `24 + run_length*4` when the run carries per-cluster checksums, the trailing 4-byte values being them |
| 0x0C | 8 | File VCN (u64) | Cluster index within file; with the run length, the row's key |
| 0x14 | 4 | Run length (u32) | Number of contiguous clusters |

## Extent Flags

The flags occupy **two** bytes at `extent+0x08`; the two bytes above them are the record size. Read as one
32-bit value the pair reads `(record_size << 16) | flags`, which is why the plain-record constants seen on
disk all begin `0x18` — that leading `0x18` is **24**, the size of a plain record, not a flag bit. A
checksummed record's constant begins with its own size: `0x1C00D0` for a 28-byte record, `0x2400D0` for 36.

| Flags | Record size | Meaning |
|-------|-------------|---------|
| 0x0040 | 24 | Data run, **allocated but not written as of this row version** (bit 0x10 clear) — never read; the range is zero-filled |
| 0x0050 | 24 | Data run, **written** (bit 0x10 set) — its clusters hold the file's bytes |
| 0x0060 | 24 | **Sparse hole** — identified by **bit 0x20**. Its run is a zero-filled hole, never read from disk (see below) |
| 0x00d0 | 24 + run*4 | **Per-cluster checksums present** (bit 0x80 set, over the 0x0050 run flags): one CRC32-C (Castagnoli poly `0x82f63b78`) per cluster of the run, after the 24-byte fixed part |

Measured across every extent record of the volumes measured: the record size is `24 + (bit 0x80 ? run*4 : 0)`
in **every** case, with no exception. In that census the flag values were `0x0040`, `0x0050`, `0x0060`
(plain) and `0x00d0` (checksummed).

**Bit 0x04** (`0x0044`, `0x0054`, `0x0064`) marks, on the rows read, a slot the node's key index does not
list: a superseded row, not part of the current map (see [below](#where-the-extent-records-live--a-b-tree-node)).
What the driver means by the bit has not been read.

**Where the checksums appear.** On the volumes measured, the inline CRC32-C occurs on 4 KiB-cluster volumes,
on format 3.4 as on 3.14. SHA-256 volumes and 64 KiB-cluster volumes carry none in the extent record.

Most integrity files also hold runs without a checksum: typically the first cluster is checksummed and the
rest of the file is one run whose record (flags `0x0040`, 24 bytes) has no CRC slot. A file's CRC check
covers only its checksummed clusters.

Run cardinality is carried explicitly by the Run length field at extent+0x14, not by the flag bits:
both 0x0040 and 0x0050 appear with single-cluster and multi-cluster runs.

**Bit 0x10 means "written", as of the row version that carries it.** A run whose flags word is known and
has bit 0x10 clear was allocated but not yet written when that row version was committed, and its
clusters are not the file's content: they are zero-filled, never read. Three measurements fix the
meaning — a purpose-built lab volume whose files all extract byte-exact only under this rule, a real
installation where the clear-bit runs of pre-allocated files hold **another file's bytes** (hundreds of runs,
among them readable text), and the inverse control, a file whose genuinely written zeros must still be read.

Two qualifications follow from that measurement:

- **The bit belongs to the row version, not to the cluster.** A deleted remnant is often an earlier
  version of a file that is still live, committed between allocation and the write. For the same VLCN the
  live row can carry `0x00D0` (written) while the remnant carries `0x0040` (not written). Recovering that
  remnant zero-fills the run — which is what the file held at that moment — even though the clusters hold
  data now, and a carve reports how many non-zero bytes lie under the zeros it wrote.
- **A flags word of 0 is unknown, not "unwritten".** The heuristic marker-scan decoder recovers no flags,
  so its runs carry 0; treating 0 as "not written" would zero real content. Only a positively known flags
  word with bit 0x10 clear marks a run unwritten.

**Records are 8-byte aligned**, so the step from one record to the next is `record_size` rounded up to a
multiple of 8 — **the size and the step are different quantities**, and a reader must step by the second.

- A checksummed single-cluster record is 28 bytes (24 + one 4-byte CRC32-C) and is followed 32 bytes later.
- A three-cluster one is 36 bytes, followed 40 bytes later. The bytes in between are padding, not a field.
- A plain record is already a multiple of 8 and needs none.

Measured on one sample volume, over the files a record-by-record walk reached: stepping by the aligned step
reaches every checksummed cluster in them, stepping by the record size misses about one in ten, and wherever
a record follows a 28-byte one it starts at +32, never at +28.

A node's records are the ones its key index names — a node can keep a superseded record in a slot the index no
longer points at — so a complete reader follows the index, and descends into child pages where the map spans
more than one node. That is how `integrity --checksums` reads them, and every checksummed cluster on that
volume matches its stored CRC-32C.

Checksummed and plain records share the same 24-byte fixed part; they differ only in the trailing checksums and
the record size that implies. Whether a record's clusters hold this version's bytes is decided by bit 0x10,
not by the record kind.

## No single-extent "shortcut" form

There is **no** compact 16-byte single-extent form. A contiguous file uses the standard extent record (one
record, `run_length` = the whole contiguous run). Extent-backed files resolve through their extent node, with
each record read at its offset in the key index; sampled single-extent files content-match (the record's VLCN
at `+0x00` → PLCN holds the file's bytes).

A 16-byte "shortcut" read in this region is the `$DATA` sub-record header, misread: the bytes
`02000080 80000e00 …` decode as the multi-instance marker `0x80000002` followed by the `$DATA` descriptor
`0x000E0080` — i.e. the "VLCN" is the descriptor, not a cluster.

See [The extent-bearing `$DATA` record](#the-extent-bearing-data-record) below.

## VCN ordering

Extents may be stored **out of order** on disk. A parser must sort by `file_VCN` before reassembling file
content — roughly half of multi-extent entries observed are unsorted.

## VLCN to PLCN translation

A VLCN must be resolved through the Container Table to reach the physical disk address:

```text
physical_LCN = container_phys_start + (vlcn & (CPC - 1))
```

Where CPC (clusters per container) is read from the Container Table at `value + 0x18`, and the container
index is computed as `vlcn >> CPC.bit_length()` (shift = 15 for 4 KiB clusters, 11 for 64 KiB).

See [Container Table](container_table.md) for the full address-translation formula and the failover/checksum
details.

## The extent-bearing `$DATA` record

When a file's main `$DATA` (type 0x80) is in extents, its record is the extent-bearing form: a 0x88-byte
header, then the extent node. On v3.7 and later its key carries the multi-instance marker `0x80000002` and the
descriptor `0x000E0080`; a v3.4 key carries no instance marker.

It is distinct from the smaller inline-form `$DATA` record (single-instance marker `0x80000001`, summary size
`0x30`), which holds the bytes themselves. On every record read, a file's main stream has one form or the
other, never both.

### $DATA sub-record header (offsets are the v3.7+ layout)

| Offset (v3.7+) | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Inner header size (u32) | Typically 0x88 (all versions) |
| 0x0C | 4 | Summary size (u32) | 0x200 on v3.14+, **0x1A0** on v3.4–v3.10 (the inline-form $DATA record uses 0x30) |
| 0x2C | 2 | Flags offset (u16) | 0x28: the stream flags are at 0x28 + this value |
| 0x30 | 8 | Total allocated (u64) | The file's whole allocation, blocks shared with a snapshot included |
| 0x38 | 8 | Stream size (u64) | Logical file size |
| 0x40 | 8 | Valid data length (u64) | -- |
| 0x48 | 8 | Disk allocated (u64) | What this stream's own extents cover (see below) |
| 0x50 | 4 | Stream flags (u32) | bit 31 = the stream is sparse, bit 30 = it is encrypted ([$DATA](../attributes/DATA.md)); the low 16 bits read 1, not decoded |
| 0x54 | 4 | (not decoded) | 0 |

On **ReFS v3.4** the four size fields shift **+4** (total allocated 0x34, stream size **0x3C**, valid data
length 0x44); the disk-allocated slot (0x4C) is 0 and the allocation is carried by the total-allocated field. The
shift is the stream flags, which v3.4 keeps at 0x28, before the sizes.
The inner header size (0x88) and the extent sub-record at +0x88 are unchanged across versions.

A record of this form is extent-backed by its form, whatever `disk_alloc` says. On v3.7 and later, a
`disk_alloc` of 0 with a stream size above 0 means one of two things:

- **snapshot-shared**: a snapshot sub-record for the same stream exists, and the live bytes are the snapshot's
  blocks ([Snapshots](../concepts/snapshots_versioning.md));
- **unallocated**: no snapshot sub-record exists, and nothing was ever written.

With a stream size of 0 it is an empty stream.

### The extent map (at the inner header size, +0x88)

At `inner_header_size` the value holds the file's extent map: a B+-tree node whose leaf rows are the
[extent records](#extent-entry--24-bytes) above (24 bytes, or 24 + 4 × run with checksums). Its header and rows are described in
[Where the extent records live](#where-the-extent-records-live--a-b-tree-node) below. Snapshot and copy-on-write
$DATA reuse the same extent format (the driver routes them through the same allocation-lookup routine as ordinary
file reads).

## Where the extent records live — a B+-tree node

A file's extent records are not a bare list. They are the rows of a small **B+-tree node** held inside the
file's own `$DATA` record, at offset `0x88` of that record. A file with a single run looks like a plain
array because the node holds one row; a fragmented or large file needs more, and then the node framing has
to be read.

The node begins with a 40-byte header:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| +0x00 | 4 | Header size | `0x28` — identifies the node |
| +0x04 | 4 | End of the rows | Every row the index array of a valid node names lies in [+0x28, +0x04), on every node reading measured (live files and deleted remnants) |
| +0x0C | 1 | Node level | `0` = leaf: the rows **are** extent records. Non-zero = the rows point at a child page |
| +0x10 | 4 | Key-index array **start** | Offset, relative to the node, of the row-pointer array |
| +0x14 | 4 | Row count | Rows on this node |
| +0x20 | 4 | Key-index array **end** | One past the last entry |
| +0x24 | 4 | — | 0 on every node measured |

This is the same node header the [B+-tree page](btree_node.md) uses, and the same invariant applies:
**`(u32@+0x20 − u32@+0x10) / 4 == u32@+0x14`**. Read the array's start from `+0x10`; deriving it by
subtracting `4 × row_count` from a value at `+0x20` gives the same answer on a well-formed node, but it
cannot tell a damaged header from a good one, and it treats `+0x20` as an 8-byte field when `+0x24` is a
separate word.

Rows are addressed by that **trailing index** of 4-byte slots — a 2-byte row offset plus a 2-byte word that
is **not reliably the row's file VCN**: it reads `0xFFFF` on **leaf rows of a few images whose own file VCN is
below 0xFFFF**, and the file VCN's low 16 bits on every row of the four public v3.14 samples.
Read the file VCN from inside the row. Worked case, on a v3.7 volume: OID 0x701, sub_id 0x1000, count 1, key-index
bytes `28 00 ff ff` — row offset 0x28, the word 0xFFFF, and that row's file VCN is 0 with run 1.

Two further consequences for anyone walking these rows:

* **The extent area is not `0x28 + 24 × count`.** The node header's `+0x04` disagrees with that formula on
  **about one extent-node header in five**. On a SHA-256 volume, OID 0x707's header says count 2 and end
  `0x70`, and the area holds **three** 24-byte slots (`0x28`, `0x40`, `0x58`) of which the key index lists
  only two — the slot at `0x28` is **unindexed**.
* **Rows are not a contiguous array in key-index order** on **about half the multi-row nodes**.

An unindexed slot still holds a well-formed row, but not one of the current map. On the rows read it is a
superseded version, flagged with bit 0x04: it can witness an earlier map of the file, and merged into the
current one it repeats clusters the live rows already cover (on one example read, its VLCN equals the first
live row's and its run spans the live runs).

A deleted remnant's index array can also be zeros while the header and some or all rows survive (on some node
readings of several volumes): an entry that names no row of the node makes it a node whose header does not
validate, and its rows are then read by position.

When the map outgrows one node, the level byte becomes non-zero and each row's value is a **48-byte node
reference** holding four cluster numbers. Those are *virtual* cluster numbers — translate them through the
Container Table — and together they address one metadata page: 16 KiB (four clusters) on a 4 KiB-cluster
volume, 64 KiB (one cluster, the other three entries 0) on a 64 KiB-cluster volume. That page carries the same
node structure again, at offset `0x50 + <the 32-bit value at page+0x50>`, so the walk repeats unchanged.

**Picking the right record.** A file that has stream snapshots carries one `$DATA` record per version, all
keyed alike and all the same size. They are told apart by a sub-stream id in the key at `key+0x10`:
**`0x1000` is the live stream**, and `0x1001`, `0x1002` and so on are the snapshots, oldest first. A reader
that picks by size or takes the first match will read a snapshot's extents and hand back an older version of
the file as though it were the current one.

## How the map is read, and where its record sits

Every extent map is the same B+-tree node. forefst has three readings of it and tries them in this order:

1. the node walk through the key index, as described above;
2. an embedded index-array reading — on a v3.4 record, whose `$DATA` key carries no instance marker, this is
   the reading that answers;
3. a positional reading of the rows as a contiguous array.

On the corpus the node walk decodes about 99 % of the extent-backed streams and the index-array reading
about 1 %; the positional reading decodes none. A share is a property of the order the readings are tried in,
not of the volume. The counts are in the Evidence section.

**Where the `$DATA` holder sits** is a separate question:

| holder location | share of the streams |
|---|---|
| the object's embedded attribute tree | about 38 % |
| a separate record in the home object's tree | about 35 % |
| a separate record in the directory's own tree | about 25 % |
| inline in the name row | about 2 % |

A reader cannot choose how to parse a map from where the record lives: it reads the node the record contains.

**Which reading a reader should trust.** The node walk is authoritative: its rows are addressed by the node's
index array, and a row the index array does not reference is not part of the current map (it can be a
superseded version of a row).

A reader that walks the record's bytes positionally instead can pick such a row up, or match a value that
merely looks like an entry — and the usual guard, that the runs exactly cover the file's allocation, does not
catch it, because a wrong single run of the right length covers just as well. Reading the node structurally
is what distinguishes them.

**By version.** The node is not a 3.14 feature: it is the extent map on every format read, 3.4 to 3.14.

**Maps that outgrow one node.** A small number of streams have so many runs that the node becomes an index node
whose rows point at child pages, as described above. Rare, but the reason the form exists: no flat array walk
reaches those extents.

## Forensic notes

- Two-level translation (VCN → VLCN → PLCN) is fundamental to ReFS. A parser that treats VLCN values as
  direct physical addresses — a common mistake for NTFS-trained tools — will read wrong data.
- Sorting by `file_VCN` is mandatory before content reassembly.
- Every extent record (including a single contiguous run) has a 24-byte fixed part; a checksummed one adds
  4 bytes per cluster, and records sit at 8-byte-aligned steps. There is no 16-byte single-extent form: a
  `0x80000002` marker in this region is the embedded $DATA sub-record header, not an extent.

## Cross-references

- [Container Table](container_table.md) — VLCN-to-PLCN translation
- [Directory Entries](directory_entries.md) — a split record's name row points at its type-0x40 backing,
  whose `$DATA` record holds the stream (inline, or an extent map)
- [Record placement and data residency](../concepts/placement_and_residency.md) — when a file's data is inline instead of in extents
  (on format 3.11 and later, streams under 2 KiB; on 3.10 and earlier, main data is always in extents)
- [B+-tree node](btree_node.md) — the node header the extent map shares

## Sparse files: logical size against allocated size

A sparse region is **unallocated**, so the gap between a file's logical size and its allocated size is
what identifies one. A 64 KiB file with a punched middle was measured at 65,536 logical against **8,192
allocated** — two clusters backing a sixteen-cluster file — carrying `Archive|SparseFile`. A *fully*
sparse file goes further: its allocated size is **0**. Both measured on format 3.14.

The extent map shows where the holes lie. A range without allocation appears in one of two ways, and a
reader must accept both:

- an explicit hole row (bit 0x20), whose run is zero-filled;
- a gap between rows: the rows tile only the allocated clusters, at their logical positions.

Extraction fills the hole with zeros, which is what the volume holds there. A file hole is never read from
the image. On a sparsely-stored raw image, zeros read from a region the acquisition never captured look the
same as a file's own zeros; `extract` names such ranges — see the note on image holes in
[what survives](../concepts/what_survives.md).

## Evidence

The reading shares are measured through the shipped order (node walk, then index array, then positional
array) over 117 readable images and 261,339 extent-backed streams:

| reading | streams | share |
|---|---|---|
| the node walk through the key index | 259,033 | 99.1 % |
| the embedded index-array reading | 2,251 | 0.9 % |
| the positional (contiguous-array) reading | 0 | 0.0 % |

55 streams were not attributed to a reading. A share measured under another order is a different number, so
any figure must name the order it was taken under.

The holder-location counts are a raw-disk census of 102 images and 109,588 extent-backed streams, every one
attributed; 139 of those streams have maps that outgrow one node:

| holder location | streams | share |
|---|---|---|
| the object's embedded attribute tree | 41,362 | 37.7 % |
| a separate record in the home object's tree | 38,187 | 34.8 % |
| a separate record in the directory's own tree | 27,482 | 25.1 % |
| inline in the name row | 2,557 | 2.3 % |

The extent record's fixed part (VLCN at `0x00`, flags at `0x08`, record size at `0x0A`, file VCN at `0x0C`,
run length at `0x14`) is decoded from the disk and corroborated in the driver: `CmsStream::LookupAllocation`
(with `AddAllocation` / `DeleteAllocation`) reads the VLCN at `+0x00`, the flags at `+0x08`, the file VCN as a
64-bit value at `+0x0C` and the run length at `+0x14`. The VLCN→PLCN translation formula is confirmed in the
driver's `CmsVolumeContainer` container subsystem and verified on disk across the corpus.

The extent-flag meanings are verified on disk: flags `0x0040` marks a run allocated but not written as of
its row version, `0x0050` a written run, `0x00d0` a written run with per-cluster checksums, and the `0x0050`
vs `0x0040` distinction (bit 0x10) is *not* run cardinality — both occur with single- and multi-cluster runs.
A plain record is 24 bytes; the 16-byte region at the descriptor is the embedded $DATA sub-record header.
Snapshot and copy-on-write `$DATA` use the same extent format: the driver reads them through the same
`CmsStream::LookupAllocation` routine, and snapshot content recovery confirms it on disk.

The checksum appended to an integrity record is CRC32-C (Castagnoli, poly `0x82f63b78`) of the 4 KiB
cluster: confirmed in the driver — the `crc32c_4096` kernels via `ComputeOneChecksum` (which uses the
4096-byte path only when the span is one cluster) — and on disk: every one of the 55,586 checksummed clusters
in 189 files on `win11refstestmftecmd` matches its stored CRC-32C, and 3,929 of 3,929 on a v3.4 integrity
volume (a cross-algorithm control ruled out plain CRC-32 and CRC64). On `win11refs2g_setintegritystreams1`,
204 of 209 integrity files also hold runs without a CRC slot.

The sparse-hole entry is identified by **flags bit 0x20**, and that bit alone: a hole's VLCN *mirrors its
file VCN*, so it is usually non-zero (for example `file_vcn=1, VLCN=0x1, run=25343, flags=0x180060`).
Measured across all six extent-decoding paths on four volumes — 8,864 accepted records — every record
carrying `VLCN == 0` also carries bit 0x20, and records carry bit 0x20 without a zero VLCN, so the flag is
the discriminator. A hole's run is zero-filled and never read from disk.

`VLCN == 0` remains a read-time floor rather than a hole test: `VLCN 0 → PLCN 0` is the boot region on every
volume, so cluster 0 is never a file's content. An entry with a zero VLCN and **no** 0x20 flag is a
malformed record — it is rejected, so the surrounding map fails its cover check cleanly, rather than being
served as a run of zeros.

The gap form of a hole, on the lab's sparse file: a file of 16 clusters with 2 allocated appears as one entry
at file VCN 0 and one at file VCN 15; the uncovered range is the hole.

The 24-byte extent entry, the integrity-stride flags, the inline CRC32-C element (polynomial 0x82f63b78), the sparse
hole (flags bit 0x20), the retracted single-extent shortcut, the multi-instance $DATA sub-record, the snapshot
extents' reuse of the format, the stream-flags field, the logical-versus-allocated signal, the `alloc_size = 0`
case of a fully sparse file and the key shape of an extent-backed named stream's extent record (key offset
`0x10`, key size `0x50`, attribute type `0x0003`) are registered findings, each with its evidence tier and witness in the claim register; so are
the page's remaining field-level statements.

The other counts behind the text:

- the VLCN check: on one 4 GB volume (`win11bidule`) a decoder that stopped at the first "implausible" VLCN hid
  the contents of 583 of its 629 files; with the check corrected, 608 of 629 match the volume's own SHA-256
  inventory, and with the node walk 629 of 629 (the last 21 are all larger than 1 MB);
- the record size `24 + (bit 0x80 ? run*4 : 0)`: 48,474 extent records on 40 volumes, no exception;
- bit 0x10: the lab volume's files extract byte-exact only under the rule (7 of 7); the real installation's
  clear-bit runs hold another file's bytes in 693 runs;
- the aligned step, on `win11refstestmftecmd`, over the 23 files a record-by-record walk reached: the aligned
  step reaches all 142 checksummed clusters there, the record size only 127, and 29 of 29 stops after a 28-byte
  record find a valid record at +32; `integrity --checksums`, following the key index and child pages, reads
  55,586 checksummed clusters in 189 files on that volume, every one matching its stored CRC-32C;
- the node's `+0x04`: 1,169,631 node readings on 141 volumes, 0 rows outside [+0x28, +0x04); a zeroed index array
  with a surviving header on 118 node readings of 21 volumes;
- the key-index word: `0xFFFF` on 1,364 leaf rows of three images whose own file VCN is below 0xFFFF; the file
  VCN's low 16 bits on 345 of 345 rows of the four public v3.14 samples; the worked case is `win1121h2test`;
- `0x28 + 24 × count` disagrees with `u32@ihdr+0x04` on 486 of 2,172 extent-node headers (the unindexed slot
  example: `win11refs2g_sha256checksums` OID 0x707); rows are out of key-index order on 961 of 1,865 multi-row
  nodes.

See [how this was verified](../methodology.md) to trace these statements to the exact images and measurements in
`analysis/`.

<!-- findings: CT_DRNT_001, CT_DRNT_002, CT_DRNT_003, CT_DRNT_RA_001, MD_ADS_RA_002, MD_DATA_RA_001, MD_DATA_RA_002, MD_DATA_RA_007, MD_DATA_RA_009, MD_DATA_RA_011, MD_DATA_RA_013, MD_DATA_RA_014, MD_DATA_RA_023, MD_DATA_RA_024, MD_DATA_RA_028, MD_DATA_RA_030, MD_SF_RA_004, MD_SF_RA_005, MD_SNAP_RA_003 -->
