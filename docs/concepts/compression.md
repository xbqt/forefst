# Compression

ReFS compression makes a file's bytes on disk unreadable to a parser that does not decompress them.

There is **no compression flag on a file, an extent, or a directory entry**: nothing in a file's metadata announces
that its content is compressed. Compression is a property of the **container** the data lives in. A volume-wide policy,
stored in the [Container Table](../structures/container_table.md) root page, says how containers are compressed, and
each compressed container records the format and unit it was compressed with.

An analyst who reads a compressed container's clusters as plaintext gets unreadable bytes and no warning.

This page explains where the policy lives, how the driver chooses an algorithm, how the compressed payload is framed
on disk, and what it takes to read it back. The policy is measured on disk; the container half is read from the driver
only, because no volume measured holds a compressed container.

## Compression is per-container, not per-file

NTFS compresses individual files and records the fact in the file's own attributes. ReFS does the opposite: it
compresses at the level of a **container** — the same 64 MiB physical region that
[virtual addressing](virtual_addressing.md) translates VLCNs into — and stores compressed data only inside containers
that the container-compaction code has *compacted*. Two consequences follow that matter for forensics:

- A file's extent map (the extent rows of the node inside its `$DATA` value, see
  [extent records](../structures/extent_descriptors.md)) carries **no compression bit**. The extent still points
  at a VLCN; whether the bytes behind that VLCN are compressed depends entirely on the container, not the file. You
  cannot tell from a file's metadata alone whether its data is compressed.
- Data is compressed only when the ReFS dedup engine runs a job (for example `Start-ReFSDedupJob`) on a volume enabled
  with `Enable-ReFSDedup -Type DedupAndCompress`. The `refsutil compression /c` command only *writes the policy
  parameters*; it does not compress anything by itself.

The driver compresses a container in its container-compaction code (`CompactAndCompressContainer`). The
[block refcount](../structures/block_refcount.md) table, which counts the dedup engine's shared clusters, is not
involved.

On disk, a compressed container is recorded in two places:

- **Its row in the Container Table.** The flags at value+0x14 carry bit **`0x2`** (compressed) and bit **`0x8`**
  (compacted); the format, the compression unit and the checksum type the container was compressed with are at
  value+0x30, +0x34 and +0x44. (In memory the driver holds the row at `SmsContainer+0x250`, so the flags are
  `SmsContainer+0x264`.)
- **Its `_SmsContainerCompressionHeader` rows** in the Container Index (checkpoint root 10), each keyed by the
  header's first 16 bytes: {container id, header index, 7}.

Bit `0x800` is not a compression flag. Set together with `0x80`, it marks a container whose Container Index row could
not be found, and the driver then refuses the container.

## The volume policy: where it lives and what it says

The volume's compression policy is a format, a level and a chunk size, plus three percentage thresholds and a flags
word. It is stored in the Container Table root page, in the root data that follows the 80-byte page header and the
40-byte index-root descriptor (page+0x50 to +0x77). The driver loads it into `CmsVolumeContainer` at mount, and a
change is journaled (below).

The record sits outside every row, so a parser that only walks rows will not see it: the root page's bytes must be
read directly.

The offsets below hold when the Container Table root is a single leaf page, as on every volume measured except a few
large volumes whose root is an inner node; where the record lives on those is not established.

| Offset | Size | Field | Values |
|--------|------|-------|--------|
| `0xA0` | u32 | flags word (container-manager state, not part of the policy) | `0x07` on a v3.4-format volume, `0x0F` from v3.7 on |
| `0xA4` | u16 | format | ReFS 3.14 (refs.sys 26100 and Insider): 0 = None, 1 = LZ4, 2 = ZSTD, 3 = LZ4QAT; ReFS 3.4 (refs.sys 17134): 2 = LZNT1, 3 = XPRESS, 4 = XPRESS_HUFF, 5 = LZX |
| `0xA6` | i16 | level | signed (e.g. 9 for LZ4) |
| `0xA8` | u32 | chunk size | bytes (e.g. `0x10000` = 64 KiB) |

The two drivers number their codecs differently, so the format is read with the numbering of the volume's format
version. No driver of ReFS 3.5–3.10 has been read, and every such volume of the corpus reads 0.

On ReFS 3.14 the format enum has four real values; `3 = LZ4QAT` is LZ4 compressed through the driver's `CfQat` device,
not a reserved slot (see [algorithm dispatch](#algorithms-and-driver-dispatch) below).

On a volume with compression off, `0xA4` reads 0; enabling LZ4 or ZSTD flips `0xA4` and writes the configured chunk
size at `0xA8` — a clean before/after change that confirms both the format enum and the chunk-size field directly on
disk.

The same parameters live in memory as a small 0x18-byte struct, validated by
`PopulateUserCompressionParameters`:

| Off | Size | Field |
|-----|------|-------|
| `0x00` | u16 | format |
| `0x02` | i16 | level |
| `0x04` | u32 | chunk_size (bytes) |
| `0x08` | u32 | ratio/percentage field A (≤100) |
| `0x0C` | u32 | ratio/percentage field B (≤100) |
| `0x10` | u32 | ratio/percentage field C (≤100) |
| `0x14` | u32 | flags (bit0, bit1 checked) |

The three `≤100` fields are percentage thresholds (exact per-field meaning is not labelled in the driver). In the
`CmsVolumeContainer` (in memory) these land at `+0x7c` (format), `+0x7e` (level), `+0x80` (chunk),
`+0xac`/`+0xb0`/`+0xb4` (ratios), and `+0xb8` (flags), written by `SetDefaultCompressionParameters` and read back by
`MsGetVolumeCompressionParameters`.

The 26100 and Insider drivers fill `CmsVolumeContainer+0x50` onwards from the root data, so on the page the three
thresholds and the flags sit at `0xD4`, `0xD8`, `0xDC` and `0xE0` (a driver reading, not measured on disk).

Each algorithm has its own default level and validity window:

| Algorithm | Default level | Valid levels |
|-----------|---------------|--------------|
| LZ4 | 1 | 1, 3–12 (level 2 invalid) |
| ZSTD | 3 | 1–22 |
| LZ4QAT | 9 | 1–9 |

(`GetDefaultCompressionLevel` / `IsCompressionLevelValid`.) The chunk size is not an enum: it is validated only as a
non-zero power of two by `IsCompressionChunkSizeValid` —

```c
// IsCompressionChunkSizeValid (Win11 v3.14)
return x != 0 && (x & (x - 1)) == 0;
```

— so the policy accepts any power of two. When it compresses, the driver uses a unit of at least the cluster size and
at most 1 MiB.

When the chunk is 0, the driver substitutes the volume cluster size if policy flag bit 0 is set, and rejects the policy
if it is clear (see [cluster and page size](cluster_page_size.md)).

Setting the policy is journaled, so it survives a crash mid-write: it is recorded by [MLog](../structures/mlog.md)
redo opcode `0x27` (`RedoSetDefaultCompressionParameters`; the 17134 driver has no such opcode). `AddRedoRecord` is
called with 7 values; the redo handler requires at least 6 and optionally reads the 7th (the flags field).

## Algorithms and driver dispatch

The 26100 driver supports three live compression formats behind a vtable. `CmsCompression::InitializeLibrary` builds a
dispatch table indexed by format value (index 0 is unused):

```text
SupportedCompressionFormats[1] = &CmsCompressionLZ4::vftable
SupportedCompressionFormats[2] = &CmsCompressionZSTD::vftable
SupportedCompressionFormats[3] = &CmsCompressionLZ4QAT::vftable
```

`GetCompressionClass(fmt)` validates `(u16)(fmt - 1) < 3` and returns the matching class pointer; the read path then
calls `DecompressBuffer` through vtable offset `+0x30`.

**A requested LZ4 can become LZ4QAT.** `PopulateUserCompressionParameters` does `if (fmt == 1 && qat) fmt = 3;`,
where `qat` is set when the driver initialised its `CfQat` device at load (`CmsCompressionLZ4QAT::Initialize`), and
`CompressVolume` turns 3 back into 1 when that device is absent or for chunks above 64 KiB (26100.9444; the same on
Insider 29574). The redo record of a default-parameters change logs the requested format; the promoted one goes into
the driver's in-memory default, and whether it reaches `0xA4` was not traced (no volume measured carries 3). A tool
must treat 1 and 3 as the same block format (see decompressors below).

The decompressor bodies, in v3.14:

- **ZSTD** — `CmsCompressionZSTD::DecompressBuffer` sets up a static decompression context with
  `ZSTD_initStaticDCtx(workspace, 0x176c8)` (the static workspace is `0x176c8` bytes, from
  `GetDecompressionParameters`) and then calls `ZSTD_decompressDCtx`. This is the standard ZSTD
  library embedded in the driver.
- **LZ4 / LZ4QAT** — `CmsCompressionLZ4QAT::DecompressBuffer` contains a hand-rolled, inlined **LZ4
  block decoder**: token byte, the `0xF` literal/match-length extension loops, then the offset/length
  copy. It requires no scratch buffer.
- `CmsCompressionLZ4` has no `DecompressBuffer` of its own: slot `+0x30` of its vtable points to the same function as
  `CmsCompressionLZ4QAT`'s, so formats 1 and 3 decode with one LZ4 block decoder.

**None of these formats use `RtlDecompressBuffer`**: a tool cannot use the Windows decompression API; it must
implement the block codecs itself or link a matching library.

## The on-disk compressed-range header

Each compressed range inside a compacted container is described by a `_SmsContainerCompressionHeader`, a fixed
**`0x40` (64)-byte** header followed by a variable u32 array and, when checksums are enabled, per-unit checksums.

The constants below come from the driver's constructor; the field meanings from `MakeNextHeader`,
`CompressContainerBufferWithSoftware` and `CompactedRangeToCompressedRange`:

| Off | Size | Field | Meaning |
|-----|------|-------|---------|
| `0x00` | u64 | container id | first field of the row key |
| `0x08` | u32 | header index | second field of the row key; `MakeNextHeader` = prev + 1 |
| `0x0C` | u32 | constant 7 | the row key's type: the header's first 16 bytes {container id, index, 7} are its key |
| `0x10` | u64 | uncompressed range start | bytes, in the container's compacted space |
| `0x18` | u64 | uncompressed range length | bytes |
| `0x20` | u64 | compressed data start | bytes |
| `0x28` | u64 | compressed data length | bytes |
| `0x30` | u32 | flags (`_EMS_CONTAINER_COMPRESSION_HEADER_FLAGS`) | see below |
| `0x34` | u32 | unit count | |
| `0x38` | u32 | constant `0x40` | offset from header start to the end-position array |
| `0x3C` | u16 | checksum type | 0 = none; if nonzero, flags `\|= 0x2` |

The constructor sets the two structural constants and derives the checksum flag directly:

```c
// _SmsContainerCompressionHeader ctor (Win11 v3.14)
*(this + 0x0c) = 7;
*(this + 0x38) = 0x40;
*(this + 0x3c) = param_6;            // checksum type
if (param_6 != 0)
    *(this + 0x30) = param_7 | 2;    // flag bit 0x2 = per-unit checksums present
```

**End-position array.** Immediately after the 64-byte header (at `header + *(u32*)(header+0x38)`, i.e.
`header + 0x40`) sits one **u32 per unit**, with `[+0x34]` units in total. Each entry is the position where that
unit's compressed bytes **end** (the same origin as `+0x20`), so unit *i*'s compressed length is entry[*i*] −
entry[*i*−1], with entry[−1] = the low 32 bits of `+0x20`.

`GetTotalSize` computes `4 * unit_count + base`, adding a per-unit checksum width when `flags & 0x2`.
`CompactedRangeToCompressedRange` turns the stored end positions into per-unit lengths in a runtime header, and
`ReadAndDecompressCompressedRange` walks that.

**Per-unit checksums.** When `flags & 0x2` (i.e. the checksum-type at `+0x3C` is nonzero) the checksums follow the
array and are verified by `VerifyContainerCompressionHeaderChecksums` over the compressed bytes, before any unit is
decoded; a failure skips decoding.

The per-unit type is the volume's stream-checksum type (`GetChecksumTypeForStreams`): CRC32-C on 4 KiB-cluster volumes
whose metadata uses CRC64, otherwise the metadata type. The driver writes no per-unit checksums below format 3.13.

The flag bits at `+0x30`:

| Bit | Meaning |
|-----|---------|
| `0x2` | per-unit checksums present |
| `0x1` | last unit stored raw/uncompressed (the writer sets it when the last unit is shorter than the unit size) |
| `0x80000000` | runtime/in-memory only, never persisted (`MakeRuntimeHeader`) |

**Unit granularity is not 64 KiB.** Each unit decompresses to `SmsContainer+0x284` bytes (the container's compression
unit, recorded when it was compacted: a power of two from the cluster size up to 1 MiB), so the decompressed output of
a range is `(SmsContainer+0x284) * unit_count`. A tool that assumes a fixed 64 KiB unit will misalign every output
beyond the first unit.

## Reading compressed data back

The read path uses the container's own recorded format, unit size and checksum type, and the container's header rows.
It never reads the volume policy:

```text
RefsDecompressWorker
 -> MsReadCompressedContainerRange
 -> CmsVolumeContainer::ReadCompressedContainerRange
 -> ContainerRangeToCompactedRange        // container range -> compacted range (allocation bitmap)
 -> CompactedRangeToCompressedRange       // fails at once if the container carries 0x800 (behind a feature flag)
      reads unit size SmsContainer+0x284, units per header +0x28a, checksum type +0x294
      enumerates the header rows {container id, index, 7}
      builds a runtime header (MakeRuntimeHeader) holding per-unit lengths
 -> ReadAndDecompressCompressedRange
      class = GetCompressionClass(SmsContainer+0x280)      // the container's own format
      if (flags & 0x2)  VerifyContainerCompressionHeaderChecksums(...)   // all units, before decoding
      for each unit:
          if (len == unit_size || (last unit && flags & 0x1))  memcpy raw
          else                                                  class->DecompressBuffer(...)  // vtable +0x30
```

On the write side, header rows are inserted by `InsertContainerCompressionHeaders` (`CmsTable::InsertRow` with the
header's first 16 bytes as the row key; its argument 100 is the B+-tree split percentage), which journals the insert
via MLog redo `0x1a`, and removed by `DeleteContainerCompressionHeaders`. The data is produced by
`CompactAndCompressContainer` / `CompressContainerBuffer`; the writer stores a unit raw when the compressor cannot make
it smaller.

For a forensic tool to recover compressed content from a raw image it must, in order:

1. **Find the compressed containers** — bit `0x2` of the flags at value+0x14 of each Container Table row (bit `0x8` =
   compacted). The row's value+0x30, +0x34 and +0x44 give the format, unit and checksum type it was compressed with
   (the row format is on the [Container Table](../structures/container_table.md) page).
2. **Read the header rows** — map the requested range into the container's compacted space, then read the Container
   Index (root 10) rows keyed {container id, header index, 7}.
3. **Walk the end-position array** — at `header+0x40`, one u32 per unit, `[+0x34]` units; difference it into per-unit
   lengths, starting from the low 32 bits of `+0x20`.
4. **Verify, then decompress each unit** — when `flags & 0x2`, verify every unit's checksum over its compressed bytes
   first. Decode with the container's own format and unit size (the current policy at `0xA4` may have changed since
   the container was compressed); copy a unit raw when its length equals the unit size or it is the flagged last unit.

## Why this is hard to see and hard to verify

Compression policy is exposed by **no** standard interface — not `fsutil fsinfo volumeinfo`, not `Get-Volume`, not any
metadata API. `refsutil compression /q` reports it, and it can be read directly from the Container Table root page.

`Get-ReFSDedupStatus` prints a format and a level too, but on the one volume where both were read, its values did not
match the policy `refsutil` reported.

For forensics, this is the main point: a volume can be compressing data with nothing in any file's metadata to
indicate it.

**A limitation that stays.** The volume-policy record and the algorithm dispatch are established: the policy is
confirmed on disk with before/after images, and the dispatch and codecs are read straight from the driver.

But the container half (the flags, the header rows and the read path) is decoded **from driver code only**. It is not
yet validated against an on-disk compressed range, and no real compressed cluster has been round-tripped end to end
through LZ4 or ZSTD. In the lab, a dedup job on a volume enabled for compression deduplicated data and compressed none;
why is not established, and no lab to produce a compressed container is planned.

The tools therefore read no compressed container: `refsanalysis containers` lists each one with the reason, and a read
into one is a recorded skip (exit 2); of compression they report the policy only.

Still open:

- an on-disk header witness (no volume measured holds a compressed container);
- the code that writes the root data back to the page (the load is read);
- the header layout on other drivers: the 17134 driver (ReFS 3.4) has a different codec set and its own
  `RedoAddCompressionUnitOffsets` handler, and the layout above was read on 26100 builds only.

## Cross-references

- [Container Table](../structures/container_table.md) — its root page carries the volume compression policy, and each row's flags at value+0x14 mark compressed (`0x2`) and compacted (`0x8`) containers; the header rows are in the Container Index (root 10)
- [Virtual Addressing](virtual_addressing.md) — compression operates on the same 64 MiB containers that VLCN→PLCN translation is built around
- [Block Refcount](../structures/block_refcount.md) — the dedup engine's per-cluster counts; compression does not use it
- [Extent Records](../structures/extent_descriptors.md) — the extent rows of a file's extent map, which carry no compression bit; compression is a container property, not a file property
- [MLog](../structures/mlog.md) — journals the policy change (redo `0x27`) and the header-row inserts (redo `0x1a`) so they survive a crash
- [Allocators](../structures/allocators.md) — supply the target clusters when the container code compacts and compresses a container
- [Cluster and Page Size](cluster_page_size.md) — the cluster size is the chunk fallback (policy flag bit 0) and the smallest compression unit
- [VBR](../structures/vbr.md) — where the volume's checksum type is selected; the per-unit compression checksum type is derived from it (CRC32-C on 4 KiB-cluster CRC64 volumes; none below format 3.13)

## Evidence

- **The policy record** at Container Table root `0xA0`–`0xA8` is measured on disk, with clean before/after images
  across LZ4 and ZSTD. Over the 85 corpus volumes whose Container Table root is a leaf, the flags word reads `0x07` on
  13 of 13 v3.4 pages and `0x0F` on 72 of 72 v3.7+ pages; the four 2 TB volumes whose root is an inner node read
  `0x4004` there, a different frame. Ten volumes have a policy configured: format 1 (LZ4) on 7, 2 (ZSTD) on 3, levels
  1–15, chunk sizes 4, 32, 128 and 256 KiB. Format 3 has no on-disk instance.
- **The codec numbering** is read on the refs.sys 26100 builds (twice) and Insider 29574 (once); 17134 numbers its
  codecs 2 LZNT1, 3 XPRESS, 4 XPRESS_HUFF, 5 LZX (twice). The 26100 driver embeds the ZSTD and LZ4 libraries; the
  17134 driver has LZNT1, LZX, XPRESS and XPRESS_HUFF classes instead.
- **The dispatch and the decoders** are read on 26100.8115: `CmsCompression::InitializeLibrary`, `GetCompressionClass`,
  the LZ4→LZ4QAT promotion (`PopulateUserCompressionParameters`; on 26100.9444 `SetDefaultCompressionParameters` logs
  the requested format), `CmsCompressionZSTD::DecompressBuffer` with `ZSTD_decompressDCtx` and the
  inlined LZ4 block decoder. Slot `+0x30` of the LZ4 and LZ4QAT vtables holds the same function, read from the driver
  binary.
- **The container flags** (`0x2` compressed, `0x8` compacted, `0x80`|`0x800` a needed Container Index row missing) are
  read twice (26100.8115 and 26100.9444, with 17134 cross-checks); no corpus Container Table row carries any of them.
- **The header rows** as Container Index rows of key type 7, and the split percentage, are read on 26100.9444 and
  26100.8115. The header's field meanings, the end-position array, the raw-unit rule, the verify-first order and the
  per-unit checksum type are read on 26100.8115 (`MakeNextHeader`, `CompressContainerBufferWithSoftware`,
  `CompactedRangeToCompressedRange`, `ReadAndDecompressCompressedRange`, `GetChecksumTypeForStreams`,
  `CompressVolume`). None of this is checked against disk.
- **The journaling opcodes**: `0x27` (`RedoSetDefaultCompressionParameters`, 26100 and Insider builds) for the policy,
  and `0x1a` for header-row inserts, whose writer `InsertContainerCompressionHeaders` names it on 26100.9818 and
  Insider 29683.
- **The visibility and the dedup-engine requirement** are measured in the lab, on five stages of one v3.14 volume
  (the policy set with `refsutil compression /c`, then a dedup job): `fsutil` and `Get-Volume` showed nothing; the job
  deduplicated 35.8 MiB and compressed 0 bytes; `Get-ReFSDedupStatus` printed LZ4, level 1, chunk 0 B where the policy
  was ZSTD.

See [how this was verified](../methodology.md) to trace these statements to the exact
images and measurements in `analysis/`.

<!-- findings: AP_REDO_026, AP_REDO_037, CT_COMP_RA_001, CT_COMP_RA_002, CT_COMP_RA_003, GN_COMP_SA_001 -->
