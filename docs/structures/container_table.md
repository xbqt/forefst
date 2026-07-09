# Container Table

The Container Table (roots #7/#8, schema 0xe0c0) maps virtual container IDs to physical disk
locations. It is the second level of ReFS's two-level address translation: per-object
[extent descriptors](extent_descriptors.md) map VCN to VLCN, and the Container Table translates VLCN
to physical LCN (PLCN). Roots #7 and #8 are a failover pair holding identical copies.

## Key — 16 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Container ID (u64) | Starts at 2 |
| 0x08 | 8 | Constant tag (u64) | Always `0x0000000100000000` |

## Value — 160-byte row (4 KiB clusters + CRC64 or None)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Container ID (u64) | Redundant copy of key |
| 0x08 | 8 | Constant tag (u64) | Redundant copy of key |
| 0x10 | 4 | Format version (u32) | Always 1 |
| 0x14 | 4 | Container flags (u32) | See Container flags below |
| 0x18 | 4 | Clusters per container (CPC) (u32) | 16,384 (4 KiB) or 1,024 (64 KiB) |
| 0x1C | 4 | Padding | — |
| 0x20 | 8 | Free clusters (u64) | Available clusters in this container |
| 0x28 | 4 | Free clusters (count) (u32) | The high dword 0x2C..0x2F is always 0, so this is a u32. |
| 0x30 | 32 | Reserved / uncharacterised | — |
| 0x50 | 64 | Integrity checksum buffer | 4 × 16-byte slots |
| 0x90 | 8 | Physical start cluster (u64) | **Only valid for 160-byte rows** |
| 0x98 | 4 | CPC trailing copy (u32) | Redundant |
| 0x9C | 4 | Padding | — |

## Value — 224-byte row (64 KiB clusters or SHA-256)

Same first 0x50 bytes. The integrity checksum buffer is extended to 128 bytes (8 × 16-byte slots),
and the physical start cluster moves to offset 0xD0. The 160-byte and 224-byte forms do not stack:
either a SHA-256 checksum or a 64 KiB cluster size produces the 224-byte row, never a larger one.

## Universal parsing rule

**Critical correctness requirement.** The physical start cluster is NOT at a fixed offset. Hard-coding
0x90 computes wrong physical addresses on any non-default (224-byte) volume and corrupts every result
derived from them. This is the single most important correctness requirement for a ReFS parser. The
position-independent rule is:

- **CPC** always at `value + 0x18`
- **Physical start** always at `value[len − 16]` — the 8-byte field 16 bytes from the end of the value
  (0x90 on 160-byte rows, 0xD0 on 224-byte rows)

## Container flags (offset +0x14)

| Bit | Mask | Meaning (inferred) |
|-----|------|--------------------|
| 0 | 0x0001 | Contains metadata |
| 6 | 0x0040 | Contains file data |
| 9 | 0x0200 | Specific allocation tier |
| 13 | 0x2000 | Unallocated / available |
| 14 | 0x4000 | Managed by allocator subsystem |

The flag *values* are observed on disk, but the per-bit *meanings* are **inferred from co-occurrence**,
not confirmed against the driver — no flag constant in `refs.sys` has been tied to any of these bits.
Treat the labels as hypotheses pending decompilation of the container-flags reader at `value+0x14`.

## Address translation (VLCN to PLCN)

```
shift = CPC.bit_length()   # 15 for 4 KiB clusters, 11 for 64 KiB
mask  = CPC - 1
container_index     = vlcn >> shift
offset_in_container = vlcn & mask
physical_LCN        = container_map[container_index] + offset_in_container
```

Or equivalently, once the container's physical start is known:

```
physical_LCN = container_phys_start + (vlcn & (CPC - 1))
```

The driver stores `log2(CPC)` at volume-structure offset +0x50 and adds 1 before shifting
(`GetContainerIdFromRealRange`), which equals `CPC.bit_length()` for powers of two. The mask `CPC - 1`
is correct despite the wider shift because
`IsValidContainerLcn` confirms bit `log2(CPC)` (bit 14 for 4 KiB) must be zero in any valid container
LCN, so that bit always falls through harmlessly.

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

Root #7 (table ID 0x0B) and root #8 (table ID 0x0C) form a failover pair holding duplicate copies (the order can be swapped — the invariant is the set {0x0B, 0x0C} at roots {7, 8}). If
one is corrupted (checksum mismatch), the driver silently falls back to the duplicate. Mount failure
requires corrupting both copies. On volumes with no checksum (CmsChecksumNone) the corruption is
undetected and no failover occurs.

## Driver functions

| Function | Purpose |
|----------|---------|
| `GetContainerIdFromRealRange` | Computes container index from a real LCN. Stores `log2(CPC)` at volume+0x50, adds 1 before shifting. |
| `IsValidContainerLcn` | Validates that bit `log2(CPC)` is zero in a container LCN. Returns false if the boundary bit is set. |
| `ValidateCheckpointRecordCallback` | Validates checkpoint records. |
| `WalkContainers` | Iterates all container entries in the table. |
| `CmsVolumeContainer` | Container-level operations (allocation, deallocation, move). |

## Compression policy (root-page extended header)

On ReFS 24H2 the volume **compression policy** is stored in the Container Table **root page's extended
header** — the `0x70–0xBF` region, *beyond* the standard 0x70-byte MSB+ page header, so it is invisible
to normal row / B+-tree walking:

| Offset | Size | Field | Values |
|--------|------|-------|--------|
| 0xA0 | 4 | prefix | always `0x0F` |
| 0xA4 | 2 | format | 0 = None, 1 = LZ4, 2 = ZSTD, 3 = LZ4QAT |
| 0xA6 | 2 | level (i16) | signed |
| 0xA8 | 4 | chunk_size | bytes (power of two) |

Individual containers that have actually been compacted/compressed are flagged by bit `0x800` in the
in-memory `SmsContainer` flags word at +0x264 (loaded from the container-table row), with the compressed payload
described by `_SmsContainerCompressionHeader` (type-100) rows in the per-container index table. Full
details: [Compression](../concepts/compression.md).

## Raw example

A Container-Table leaf row on a CRC64 / 4 KiB-cluster v3.14 image (160-byte value), mapping virtual container **3** to its physical location:

```text
header:    b0 00 00 00 10 00 10 00  00 00 20 00 a0 00 00 00   <- row_size 0xb0; key_len/val_len 0x10/0xa0
key:       03 00 00 00 00 00 00 00  00 00 00 00 01 00 00 00   <- container id = 3
val+0x00:  03 00 00 00 ...                                    <- container id (echoed)
val+0x18:  00 40 00 00                                        <- cluster count = 0x4000 (16384 = clusters/container)
val+0x90:  00 c0 01 00 00 00 00 00                            <- physical start cluster (PLCN) = 0x1c000 (114688)
```

Virtual container 3 resolves to physical cluster **114688**, so any VLCN inside it translates as `PLCN = 114688 + (vlcn mod 16384)`. The value is 160 bytes on this CRC64 / 4 KiB-cluster volume (it grows to 224 bytes on SHA-256 or 64 KiB-cluster volumes), and the physical start cluster is read **position-dependently** at `value_end − 16` — a fixed offset fails across the two size classes.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — roots #7 and #8 in the root-pointer list
- [Container Index](container_index.md) — alternate state-keyed index derived from this table
- [Extent Descriptors](extent_descriptors.md) — extents contain VLCNs that require this table for translation
- [Allocators](allocators.md) — the three-tier allocator manages space within containers
- [Compression](../concepts/compression.md) — the root-page compression policy header (0xA0) lives here
- [VBR](vbr.md) — `bytes_per_container` at offset 0x40

## Evidence

The key/value layouts, the universal `value[len−16]` physical-start rule, the 160-vs-224-byte row sizing
(SHA-256 or 64 KiB → 224 bytes), the count-scaling table, and the VLCN→PLCN formula
(`PLCN = container_map[VLCN >> shift] + (VLCN & mask)`, shift = 15 for 4 KiB / 11 for 64 KiB) are
raw-disk decoded across the corpus (RD) and corroborated in the driver (E2): `CmsVolumeContainer`
manages container-level operations, `GetContainerIdFromRealRange` / `IsValidContainerLcn` implement the
translation. The roots-7/8/12 real-LCN bootstrap exception is raw-disk confirmed.
The container flag *values* are RD-observed but the per-bit *meanings* are inference only (no driver
flag constant tied to them). The 0x28 field is a u32 (high dword always 0). The 24H2 compression policy header at 0xA0 (prefix/format/level/chunk)
is raw-disk verified clean before/after.
Findings: GN_ARCH_003, FS_CHKP_016, FS_CHKP_017, CT_CTBL_001–011, CT_CTBL_RA_003, CT_CTBL_RA_004,
GN_ARCH_RA_001, AP_REDO_037 (compression). See [how this was verified](../methodology.md) to trace these to the
exact images and measurements in `analysis/`.
