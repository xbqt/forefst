# Extent Descriptors

Extent descriptors (type 0x40) map a file's logical cluster offsets (VCNs) to virtual LCNs (VLCNs).
A VLCN is not a physical address: it must be translated through the [Container Table](container_table.md)
to obtain the physical cluster where the data actually lives. Every extent — even a single contiguous run —
is a fixed 24-byte entry.

> **Do not sanity-check a VLCN against the volume's cluster count.** The virtual address space is *wider*
> than the physical one — it starts above the first container and runs roughly twice as far — so a perfectly
> valid extent can name a cluster number larger than the volume has. The only sound test is whether the
> Container Table can translate it. Getting this wrong is quietly destructive: a decoder that walks extents
> in order and stops at the first "implausible" one throws the **whole** map away, and the file then looks
> as though it had no extents at all. On one 4 GB volume that mistake hid the contents of 583 of its 629
> files, every one of which read back byte-perfect once the check was corrected.

## Extent Entry — 24 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Virtual LCN (VLCN) (u64) | Requires Container Table for physical translation |
| 0x08 | 2 | Flags (u16) | See Extent Flags below |
| 0x0A | 2 | Record size (u16) | `24` for a plain run; `24 + run_length*4` when the run carries per-cluster checksums, the trailing 4-byte values being them |
| 0x0C | 4 | File VCN (u32) | Cluster index within file |
| 0x10 | 4 | Padding (u32) | Always zero |
| 0x14 | 4 | Run length (u32) | Number of contiguous clusters |

## Extent Flags

The flags occupy **two** bytes at `extent+0x08`; the two bytes above them are the record size. Read as one
32-bit value the pair reads `(record_size << 16) | flags`, which is why the constants seen in the wild all
begin `0x18` — that leading `0x18` is **24**, the size of a plain record, not a flag bit.

| Flags | Record size | Meaning |
|-------|-------------|---------|
| 0x0040 | 24 | Standard data-run extent (variable run_length) |
| 0x0050 | 24 | Data-run with bit 0x10 set |
| 0x0060 / 0x0064 | 24 | **Sparse hole** (bit 0x20 set): the entry has `VLCN == 0` and its run is a zero-filled hole — never read from disk (see below) |
| 0x00d0 | 24 + run*4 | **Per-cluster checksums present** (bit 0x80 set, over the 0x0050 run flags): each cluster of the run is followed by its CRC32-C (Castagnoli poly `0x82f63b78`) |

Measured across **48,474 extent records on 40 volumes**: the record size is `24 + (bit 0x80 ? run*4 : 0)`
in **every** case, with no exception. Observed flag values are `0x0040`, `0x0050`, `0x0060` (plain) and
`0x00d0` (checksummed).

Run cardinality is carried explicitly by the Run length field at extent+0x14, not by the flag bits:
both 0x0040 and 0x0050 appear with single-cluster and multi-cluster runs. The meaning of the 0x10 bit that
distinguishes 0x0050 from 0x0040 remains unresolved; it correlates with the file_attrs 0x8000 flag.

**Records are 8-byte aligned**, so the step from one record to the next is `record_size` rounded up to a
multiple of 8. A checksummed single-cluster record is 28 bytes (24 + one 4-byte CRC32-C) and is therefore
followed 32 bytes later — the 4 bytes in between are padding, not a field. A plain record is already a
multiple of 8 and needs none.

Checksummed and plain records share the same header format and both point at real file data; they differ only
in the trailing checksums and the size that implies.

## No single-extent "shortcut" form

There is **no** compact 16-byte single-extent form. A contiguous file uses the standard 24-byte extent
entry (one entry, `run_length` = the whole contiguous run). Non-resident files resolve via the 24-byte
stride only; sampled single-extent files content-match (24-byte VLCN@0x00 → PLCN holds the file's bytes).

This 16-byte region is the embedded $DATA sub-record header: the
bytes `02000080 80000e00 …` decode as the multi-instance marker `0x80000002` followed by the $DATA
descriptor `0x000E0080` — i.e. the "VLCN" is the descriptor, not a cluster. See the Embedded $DATA section
below.

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

## Embedded extent sub-record header — 40 bytes

When $DATA (type 0x80) appears as an embedded multi-instance sub-record in a file value, the extent list is
preceded by two headers. This is the extent-bearing $DATA stream summary (marker `0x80000002`, descriptor
`0x000E0080`) — distinct from the smaller resident-SI $DATA record.

### $DATA sub-record header (offsets are the v3.7+ layout)

| Offset (v3.7+) | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Inner header size (u32) | Typically 0x88 (all versions) |
| 0x0C | 4 | Summary size (u32) | 0x200 on v3.14+, **0x1A0** on v3.4–v3.10 (the resident-SI $DATA record uses 0x30) |
| 0x2C | 4 | Data offset (u32) | 0x28 |
| 0x30 | 8 | Total allocated size (u64) | -- |
| 0x38 | 8 | Stream size (u64) | Logical file size |
| 0x40 | 8 | Valid data length (u64) | -- |
| 0x48 | 8 | Disk allocated size (u64) | 0 = inline; >0 = non-resident |
| 0x50 | 8 | Version count (low 31) + sparse flag (bit 31) (u64) | low31 = stream version count (=1 for a single-version file, N for an N-version snapshotted file); bit 31 = sparse flag |

On **ReFS v3.4** the four size fields shift **+4** (total allocated 0x34, stream size **0x3C**, valid data
length 0x44); the disk-allocated slot (0x4C) is 0 and the allocation is carried by the total-allocated field.
The inner header size (0x88) and the extent sub-record at +0x88 are unchanged across versions.

### Extent sub-record header (at inner_header_size offset)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Sub-record size (u32) | Always 0x28 |
| 0x04 | 4 | Extent area end (u32) | 0x28 + extent_count x 24 |
| 0x0C | 4 | Flags (u32) | 0xe00 = non-resident extents; 0x600 = resident/empty |
| 0x14 | 4 | Extent count (u32) | Number of 24-byte extent entries following |

Extent entries following this header use the same 24-byte format as the [Extent Entry](#extent-entry--24-bytes)
table above. Snapshot and copy-on-write $DATA reuse this identical extent format (the driver routes them
through the same allocation-lookup routine as ordinary file reads).

## Where the extent records live — a B+-tree node

A file's extent records are not a bare list. They are the rows of a small **B+-tree node** held inside the
file's own `$DATA` record, at offset `0x88` of that record. A file with a single run looks like a plain
array because the node holds one row; a fragmented or large file needs more, and then the node framing has
to be read.

The node begins with a 40-byte header:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| +0x00 | 4 | Header size | `0x28` — identifies the node |
| +0x0C | 1 | Level | `0` = leaf: the rows **are** extent records. Non-zero = the rows point at a child page |
| +0x10 | 4 | Key-index array **start** | Offset, relative to the node, of the row-pointer array |
| +0x14 | 4 | Row count | Rows on this node |
| +0x20 | 4 | Key-index array **end** | One past the last entry |
| +0x24 | 4 | — | 0 on every node measured |

This is the same node header the [B+-tree page](btree_node.md) uses, and the same invariant applies:
**`(u32@+0x20 − u32@+0x10) / 4 == u32@+0x14`**. Read the array's start from `+0x10`; deriving it by
subtracting `4 × row_count` from a value at `+0x20` gives the same answer on a well-formed node — which is
why that reading went unnoticed — but it cannot tell a damaged header from a good one, and it treats `+0x20`
as an 8-byte field when `+0x24` is a separate word. Verified on 480 extent nodes with 0 violations.

Rows are addressed by that **trailing index** of 4-byte slots — a 2-byte row offset plus a 2-byte hint
holding the row's file VCN. Use the file VCN inside the row itself, not the hint: the hint is only 16 bits and
saturates on a file larger than 65,535 clusters.

When the map outgrows one node, the level byte becomes non-zero and each row's value is a **48-byte node
reference** holding four cluster numbers. Those are *virtual* cluster numbers — translate them through the
Container Table — and together they address one 16 KiB page. That page carries the same node structure
again, at offset `0x50 + <the 32-bit value at page+0x50>`, so the walk repeats unchanged.

**Picking the right record.** A file that has stream snapshots carries one `$DATA` record per version, all
under the same key and all the same size. They are told apart by a sub-stream id in the key at `key+0x10`:
**`0x1000` is the live stream**, and `0x1001`, `0x1002` and so on are the snapshots, oldest first. A reader
that picks by size or takes the first match will read a snapshot's extents and hand back an older version of
the file as though it were the current one.

## Forensic notes

- Two-level translation (VCN → VLCN → PLCN) is fundamental to ReFS. A parser that treats VLCN values as
  direct physical addresses — a common mistake for NTFS-trained tools — will read wrong data.
- Sorting by `file_VCN` is mandatory before content reassembly.
- Every extent (including a single contiguous run) is a 24-byte entry; there is no 16-byte single-extent
  form. A `0x80000002` marker in this region is the embedded $DATA sub-record header, not an extent.

## Cross-references

- [Container Table](container_table.md) — VLCN-to-PLCN translation
- [Directory Entries](directory_entries.md) — non-resident file values link to type 0x40 extent rows
- [Resident Storage](../concepts/resident_storage.md) — small files are stored inline, not in extents

## Evidence

The 24-byte extent entry layout (VLCN@0x00, flags@0x08, file_VCN@0x0C, padding@0x10, run_length@0x14) is
raw-disk decoded (RD) and corroborated in the driver (E2): `CmsStream::LookupAllocation` (with
`AddAllocation` / `DeleteAllocation`) reads run+0x00 VLCN, +0x0C file_vcn, +0x14 run_length. The
VLCN→PLCN translation formula is E2-confirmed in the `CmsVolumeContainer` container subsystem and verified
on disk across the corpus.

The extent-flag meanings are raw-disk verified: flags `0x0040` is the standard data run, `0x00d0` carries
per-cluster checksums, and the `0x0050` vs `0x0040` distinction (bit 0x10) is *not* run cardinality — both
occur with single- and multi-cluster runs. A plain record is 24 bytes; the 16-byte region at the descriptor is
the embedded $DATA sub-record header.
Snapshot/CoW DATA uses the identical 24-byte extent format (E2: same
`CmsStream::LookupAllocation` routine; RD content-recovery confirmed).

The checksum appended to an integrity record is CRC32-C (Castagnoli, poly `0x82f63b78`) of the 4 KiB
cluster: confirmed in the driver (E2) — the `crc32c_4096` kernels via `ComputeOneChecksum` (which uses the
4096-byte path only when the span is one cluster) — and on disk (RD), 886 checksummed clusters recomputed
across three integrity volumes with 0 mismatches (a cross-algorithm control ruled out plain CRC-32 and CRC64).
The sparse-hole entry (`VLCN == 0`, flags bit 0x20) is raw-disk verified: `VLCN 0 → PLCN 0` is the boot
region on every volume, so a zero VLCN is a hole, zero-filled and never read (213 records across 18 images,
v3.9–v3.14, 4K and 64K).

Findings: **MD_DATA_RA_001** (24-byte extent entry), **MD_DATA_RA_007** (integrity-stride flags),
**MD_DATA_RA_013** (inline CRC32-C element, poly 0x82f63b78), **MD_DATA_RA_014** (sparse VLCN==0 hole),
**MD_DATA_RA_002** (single-extent shortcut retracted), **MD_DATA_RA_009** (MI $DATA sub-record),
**MD_SNAP_RA_003** / **CT_DRNT_RA_001** (snapshot extents reuse the format), **MD_DATA_RA_011** (version-count
field). See [how this was verified](../methodology.md) to trace these to the exact images and measurements
in `analysis/`.
