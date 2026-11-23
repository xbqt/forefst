# Container Table

The Container Table (roots #7/#8, schema 0xe0c0) maps virtual container IDs to physical disk
locations.

It is the second level of ReFS's two-level address translation:

- a file's extent map — a B+-tree node inside its `$DATA` value, whose leaf rows are the 24-byte
  [extent entries](extent_descriptors.md) — maps VCN to VLCN;
- the Container Table translates VLCN to physical LCN (PLCN).

Roots #7 and #8 are a failover pair: two copies of the table, read by slot (root #7 first; [Failover](#failover)).

## Key — 16 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Container ID (u64) | Starts at 2 |
| 0x08 | 8 | Constant tag (u64) | Always `0x0000000100000000` |

## Value — 160-byte row (4 KiB clusters, CRC64)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Container ID (u64) | Redundant copy of key |
| 0x08 | 8 | Constant tag (u64) | Redundant copy of key |
| 0x10 | 1 | Version byte | 1 on every corpus row |
| 0x14 | 4 | Container flags (u32) | See Container flags below |
| 0x18 | 4 | Clusters per container (CPC) (u32) | 16,384 (4 KiB) or 1,024 (64 KiB) |
| 0x1C | 4 | Padding | — |
| 0x20 | 8 | Allocated clusters (u64 on v3.4) | The container's allocated clusters on v3.4; **all-ones (`0xFFFFFFFFFFFFFFFF`) is a sentinel, not a count** ([below](#the-allocation-counts-0x20-and-0x28)) |
| 0x28 | 4 | A second allocation count (one driver reading, 26100.9444) | On v3.4 not the same number as `+0x20`; its width is not decided ([below](#the-allocation-counts-0x20-and-0x28)) |
| 0x30 | 28 | Compression fields | the format (+0x30), unit (+0x34), units per header (+0x3A) and header checksum type (+0x44) are 0 on every corpus row (no corpus container is compressed); `+0x3C` is the SMR write head (one driver reading) |
| 0x4C | 4 | Mapping-range count (u32) | 1 on every corpus row |
| 0x50 | 64 | k = 4 units of 16 bytes | — |
| 0x90 | 8 | Range 0: start (u64) | the physical start cluster |
| 0x98 | 8 | Range 0: length (u64) | in clusters; the CPC on every corpus row |

### The allocation counts (0x20 and 0x28)

**`+0x20`.** On every v3.4 volume measured the sum over the rows equals the allocator's used clusters exactly, so
this counts the container's allocated clusters, not free ones.

- After an upgrade to v3.14 the rows keep their v3.4 counts and stop following the allocator (they differ from it by
  a few dozen clusters on the upgraded volume measured).
- **All-ones is a sentinel, not a count.** It reads that way on about 95 % of the corpus's rows: every row of every
  v3.14 volume (except a volume upgraded from v3.4, whose rows keep real v3.4 counts) and every row on the v3.7, v3.9
  and v3.10 volumes. On the native v3.4 volumes it is never the sentinel. Check for the sentinel before treating
  this as a number.
- refs.sys 26100.x and Insider read `+0x20` as a u32 and `+0x24` as a compacted length, 17134 `+0x20` as a u64 (one
  reading).

**`+0x28`.** On v3.4 this and `+0x20` are **not the same number**: they agree on nearly every row and differ on a
few, and the differing rows are large enough to move volume totals (about 5 % over the v3.4 volumes measured).

Its high dword, +0x2C to +0x2F, is 0 on every row of the corpus but those of one v3.7 volume, which hold all-ones in
the 8 bytes at 0x28: its width is not decided.

## Value — 224-byte row (64 KiB clusters or SHA-256)

Same first 0x50 bytes. The units before the ranges are k = 8 (128 bytes), so range 0 — the physical start
cluster and the range length — moves to offset 0xD0. The 160-byte and 224-byte forms do not stack:
either a SHA-256 checksum or a 64 KiB cluster size produces the 224-byte row, never a larger one.

## Universal parsing rule

**Critical correctness requirement.** The physical start cluster is NOT at a fixed offset. Hard-coding
0x90 computes wrong physical addresses on any non-default (224-byte) volume and corrupts every result
derived from them. The position-independent rule is:

- **CPC** always at `value + 0x18`
- **Mapping ranges** after the `value + 0x50` area: the value is `(k + 5 + count) × 16` bytes, where `count` is the
  number of mapping ranges (u32 at `value + 0x4C`) and `k` is fixed per volume (4 on 160-byte rows, 8 on 224-byte
  rows); range `i` is `{u64 start, u64 length}` at `0x50 + 16 × (k + i)`
- **Physical start** = the start of the FIRST range. Every row of the corpus holds one range (both copies of the
  table, every volume), so the first range is also the last 16 bytes of the value: `value[len − 16]` (0x90 on
  160-byte rows, 0xD0 on 224-byte rows)

## How the tools read the table

`forefst` and `refsanalysis` read the table through one reader and check each row the way refs.sys reads it. A row
is translated only when it maps its container linearly: a version byte of 1 (or a row of at least 0x58 bytes), a
whole `k` equal to the volume's, one mapping range, and none of the flags 0x2
(compressed), 0x8 (compacted) or 0x800 (a Container Index row the container needs was not found: refs.sys refuses
the container). Any other row is listed with its reason by `summary`, `integrity` and `refsanalysis containers`
("Container not read: 0x5: it is compressed (reading compressed containers is not supported)"), and an address in
that container is not read as its data: a read there is a recorded skip and the command exits 2. The same holds for
an address in a container the table has no row for.

Two more checks:

- **Overlapping containers.** Two translated containers whose clusters overlap mean at least one row is wrong. Every
  command says so ("the Container Table maps containers 0x3 and 0x12 onto overlapping clusters ...") and exits 2.
- **The page read is the page asked for.** A metadata page records, in its header's LCN tuple (`+0x20` to `+0x3F`), the
  address it was written for: the reference's LCNs, virtual where the reference is virtual. The B+-tree walk compares that
  tuple with the address it read the page for and does not use a page that records another one (its rows belong to
  another table); the page is named among the pages that could not be read and the command exits 2. On the corpus the
  tuple equals the address asked for on every page read for this measurement (4 KiB and 64 KiB clusters).

**What the checks cannot see.** A container moved to other clusters together with every digest that covers it
recomputed (the table pages' digests in their parent references and in the checkpoint, and the checkpoint's own
checksum) leaves a table that is consistent in every respect the image records. Such a re-signed move cannot be
detected from the image: the tools read the moved table as the volume's.

## Container flags (offset +0x14)

| Mask | Meaning (refs.sys 26100.9444; 0x0002 and 0x0008 also 17134) |
|------|---------|
| 0x0002 | the container is compressed: refs.sys reads it through its compressed range, not a physical mapping |
| 0x0008 | the container is compacted: its clusters are found through the Container Index |
| 0x0080 \| 0x0800 | set together when a Container Index row the container needs is not found; refs.sys refuses a container with 0x0800. The tools read such a container through its one range when it is neither compressed nor compacted, and say so |
| 0x4000 | every cluster of the container is allocated |

Of the other bits seen on disk, one driver reading (26100.9444) names 0x0040 (reserved) and 0x2000 (no cluster of the
container allocated); 0x0001, 0x0200 and 0x0400 are not decoded here. On the corpus no row
carries 0x0002, 0x0008, 0x0080 or 0x0800. `refsanalysis containers -v` names the four meanings
above in its Type column and shows every bit in hex in its Flags column.

## Address translation (VLCN to PLCN)

```text
shift = CPC.bit_length()   # 15 for 4 KiB clusters, 11 for 64 KiB
mask  = CPC - 1
container_index     = vlcn >> shift
offset_in_container = vlcn & mask
physical_LCN        = container_map[container_index] + offset_in_container
```

`container_map` is keyed by the **Container-Table row key** — the Container ID `u64` at row key `+0x00` — and its
value is that row's physical start cluster. Container ids start at **2** (the minimum key on every volume measured),
so `container_index` is that id directly, not an index into a zero-based array.

`forefst` makes the same bridge internally: `container_table_read` keys its map on the row key's `le64(key, 0)`, and
the translator looks up `map[vlcn >> shift]`.

Or equivalently, once the container's physical start is known:

```text
physical_LCN = container_phys_start + (vlcn & (CPC - 1))
```

The driver holds `log2(CPC)` in its volume structure — at +0x50 on the 26100 and Insider builds, +0x4C on 17134 —
and adds 1 before shifting (`GetContainerIdFromRealRange`), which equals `CPC.bit_length()` for powers of two.

The mask `CPC - 1` is correct despite the wider shift because `IsValidContainerLcn` confirms bit `log2(CPC)` (bit 14
for 4 KiB) must be zero in any valid container LCN, so that bit always falls through harmlessly.

## Container count scaling

The number of containers scales linearly with volume size at 64 MiB per container
(`bytes_per_container` lives in the [VBR](vbr.md) at offset 0x40):

| Volume size | Cluster size | Containers | Formula |
|-------------|--------------|-----------|---------|
| 2 GiB | 4 KiB | 31 | volume / 64 MiB |
| 4 GiB | 4 KiB | 63 | |
| 8 GiB | 4 KiB | 127 | |
| 110 GiB | 4 KiB | 1,759 | |
| 2 TiB | 4 KiB | 32,767 | |
| 15 TiB | 64 KiB | 245,759 | |

## Addressing mode

The Container Table (roots #7 and #8) uses **real (physical) LCNs** as a bootstrap exception. It cannot
use virtual addressing because it IS the virtual-to-physical translation layer. This is one of only
three roots that use real addressing — roots #7, #8 (this table) and #12 (the small allocator); every
other root is virtual.

## Failover

Roots #7 and #8 form a failover pair. The driver opens them by slot — root #7 first — and reads root #8 only
when root #7 fails its check. The table IDs on their pages (0x0B and 0x0C, usually in that order and swapped on one
volume measured) do not decide which copy is read.

The two copies normally hold the same rows; on some volumes (an upgraded one among them) they were measured to
differ in rows' flags word (+0x14: bits 0x2000 and 0x4000, set in root #7 only).

`summary`, `fastsummary`, `integrity` and `refsanalysis summary` compare the two copies row by row:

- a difference only in the flags word is a note (the exit code does not change);
- any other difference is a redundancy finding (exit 2 there) and a note in every other command.

The table cannot be opened only when both copies fail.

## Driver functions

| Function | Purpose |
|----------|---------|
| `GetContainerIdFromRealRange` | Computes container index from a real LCN: reads `log2(CPC)` from the volume structure (+0x50; +0x4C on 17134) and adds 1 before shifting. |
| `IsValidContainerLcn` | Validates that bit `log2(CPC)` is zero in a container LCN. Returns false if the boundary bit is set. |
| `ValidateCheckpointRecordCallback` | Validates a checkpoint record as the mount reads it: its self-checksum, root count and root offsets, its optional areas, and on the first (strict) pass roots 0xC, 7 and 8 (26100.9444). |
| `WalkContainers` | Calls a function for each container from a cursor's position: the table rows the cursor admits, then the containers created in memory but not yet in the table (26100.9444). |
| `CmsVolumeContainer` | Container-level operations (allocation, deallocation, move). |

## Compression policy (root-page extended header)

The volume **compression policy** is stored in the Container Table **root page**, in the root data that follows the
80-byte page header and the 40-byte index-root descriptor (page+0x50 to +0x77). It sits outside every row, so it is
invisible to normal row / B+-tree walking.

The offsets below hold when the Container Table root is a single leaf page, as on every volume measured except a few
large volumes whose root is an inner node; where the record lives on those is not established.

| Offset | Size | Field | Values |
|--------|------|-------|--------|
| 0x98 | 4 | reserved compaction containers | the root data's `+0x20`: the number of containers reserved for compaction |
| 0xA0 | 4 | flags word | `0x07` on a v3.4-format volume, `0x0F` from v3.7 on — version-keyed, not constant (its bits below) |
| 0xA4 | 2 | format | ReFS 3.14 (refs.sys 26100 and Insider): 0 = None, 1 = LZ4, 2 = ZSTD, 3 = LZ4QAT; ReFS 3.4 (refs.sys 17134): 2 = LZNT1, 3 = XPRESS, 4 = XPRESS_HUFF, 5 = LZX |
| 0xA6 | 2 | level (i16) | signed |
| 0xA8 | 4 | Chunk size | bytes (power of two) |

The flags word is the root data's `+0x28`. Its bits as the driver sets them (one reading):

- 0x1: the allocator's reserved state migrated;
- 0x2: needed with 0x1 for compaction;
- 0x4: set at a mount of a volume of version 3.3 or later that is not write-protected;
- 0x8: the allocation-status mode, where the allocated counts live in the allocator (so from v3.7 on the rows'
  `+0x20` holds the sentinel).

Measured over every volume in the corpus whose Container Table root is a leaf: the flags word is `0x07` on every
v3.4 page and `0x0F` on every v3.7-and-later one, at either cluster size and under either checksum algorithm.

Where compression is actually configured, `format` reads 1 (LZ4) or 2 (ZSTD), `level` 1–15, and `chunk_size` 4, 32,
128 or 256 KiB. `format` 3 (LZ4QAT) is defined by the driver but has no instance on disk here.

A container whose data is compressed carries flag 0x2 in its Container Table row (above), and its compression
headers are rows of the [Container Index](container_index.md) (type 7). Reading compressed or compacted containers
is not supported by the tools: such a container is listed and not read. Full details:
[Compression](../concepts/compression.md).

## Raw example

A Container-Table leaf row on a CRC64 / 4 KiB-cluster v3.14 image (160-byte value), mapping virtual container **3** to its physical location:

```text
header:    b0 00 00 00 10 00 10 00  00 00 10 00 a0 00 00 00   <- row_size 0xb0; key_off/key_len 0x10/0x10; value_off/value_len 0x10/0xa0
key:       03 00 00 00 00 00 00 00  00 00 00 00 01 00 00 00   <- container id = 3
val+0x00:  03 00 00 00 ...                                    <- container id (echoed)
val+0x18:  00 40 00 00                                        <- cluster count = 0x4000 (16384 = clusters/container)
val+0x90:  00 c0 01 00 00 00 00 00                            <- physical start cluster (PLCN) = 0x1c000 (114688)
```

The **value offset is at row+0x0A and reads `0x10`** — the value begins immediately after the 16-byte key,
so `key_off == value_off == 0x10`. Measured over every Container-Table leaf row of four volumes (4 KiB and
64 KiB clusters, CRC64 and SHA-256): `(key_off, key_len, value_off, value_len, row_size)` is
`(0x10, 0x10, 0x10, 0xa0, 0xb0)` on the 160-byte rows and `(0x10, 0x10, 0x10, 0xe0, 0xf0)` on the 224-byte ones
(64 KiB / SHA-256) — **no row carries value_off 0x20**.

Virtual container 3 resolves to physical cluster **114688**, so any VLCN inside it translates as
`PLCN = 114688 + (vlcn mod 16384)`.

The value is 160 bytes on this CRC64 / 4 KiB-cluster volume (it grows to 224 bytes on SHA-256 or 64 KiB-cluster
volumes), and the physical start cluster is read **position-dependently** at `value_end − 16` — a fixed offset fails
across the two size classes.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — roots #7 and #8 in the root-pointer list
- [Container Index](container_index.md) — the rows a compressed or compacted container needs (root #10)
- [Extent Records](extent_descriptors.md) — the extent entries hold VLCNs that require this table for translation
- [Allocators](allocators.md) — the three-tier allocator manages space within containers
- [Compression](../concepts/compression.md) — the root-page compression policy header (0xA0) lives here
- [VBR](vbr.md) — `bytes_per_container` at offset 0x40

## Evidence

The key/value layouts, the universal `value[len−16]` physical-start rule, the 160-vs-224-byte row sizing
(SHA-256 or 64 KiB → 224 bytes), the count-scaling table, and the VLCN→PLCN formula
(`PLCN = container_map[VLCN >> shift] + (VLCN & mask)`, shift = 15 for 4 KiB / 11 for 64 KiB) are
decoded from the disk across the corpus and corroborated in the driver: `CmsVolumeContainer` manages
container-level operations, `GetContainerIdFromRealRange` / `IsValidContainerLcn` implement the translation. The
roots-7/8/12 real-LCN bootstrap exception is confirmed on the disk.

The container flags' meanings above are the driver's (0x0002, 0x0008, 0x0080 | 0x0800 and 0x4000 read twice, on
26100.8115 and 26100.9444 with 17134 cross-checks; 0x0040 and 0x2000 once); the field `+0x28`'s width is not
decided (its high dword is 0 on every row but the 63 of one v3.7 volume).

The compression policy record at 0xA0–0xA8 (flags / format / level / chunk) is measured on the disk, with clean
before/after images across LZ4 and ZSTD.

The counts behind the text:

- `+0x20` on v3.4: the sum over the rows equals the allocator's used clusters on each of the 9 v3.4 volumes
  measured (e.g. 180,484 on `win10refsmini`); after the upgrade, 210,058 against 210,086 on `win10to11refs4g`;
- the all-ones sentinel at `+0x20`: 762,252 of 797,837 rows — every row of all 90 v3.14 volumes except the two
  upgraded `win10to11refs4g` images (63 rows each, real v3.4 counts), and every row on the v3.7, v3.9 and v3.10
  volumes; on the 12 native v3.4 volumes, 0 of 35,459;
- `+0x28` against `+0x20` on v3.4: they agree on 35,391 rows and differ on 68; summed over the 12 v3.4 volumes,
  `+0x20` = 5,515,590 and `+0x28` = 5,227,204. Its high dword is 0 on 797,774 of the 797,837 rows; the other 63
  are all on one v3.7 volume;
- the minimum container id is 2 on all 113 bootstrappable volumes measured;
- range 0's length is the CPC on 795,913 rows of the tables in use (117 volumes); every row holds one range
  (1,591,826 rows, both copies, 117 volumes), and none carries 0x0002, 0x0008, 0x0080 or 0x0800;
- the page-address check: the LCN tuple equals the address asked for on all 66,153 pages read (every checkpoint
  root's tree and up to 1,500 objects per volume, 117 volumes);
- the root-page flags word, over the 85 volumes whose Container Table root is a leaf: `0x07` on all 13 v3.4 pages,
  `0x0F` on all 72 v3.7-and-later ones; the four 2 TB volumes whose root is an inner node read `0x4004` there, a
  different frame;
- the row header: 136,664 Container-Table leaf rows on `win11refsmini`, `win10refsmini`,
  `win11refs2tmillionsofactions` and `win11refs2t64ksha256checksums`: `(0x10, 0x10, 0x10, 0xa0, 0xb0)` on 69,552
  rows, `(0x10, 0x10, 0x10, 0xe0, 0xf0)` on 67,112, 0 with value_off 0x20.

See [how this was verified](../methodology.md) for the method.

<!-- findings: AP_REDO_037, CT_CTBL_001, CT_CTBL_002, CT_CTBL_003, CT_CTBL_004, CT_CTBL_005, CT_CTBL_006,
               CT_CTBL_007, CT_CTBL_008, CT_CTBL_009, CT_CTBL_010, CT_CTBL_011, CT_CTBL_RA_003,
               CT_CTBL_RA_004, FS_CHKP_016, FS_CHKP_017, FS_CHKP_019, GN_ARCH_003, GN_ARCH_RA_001 -->
