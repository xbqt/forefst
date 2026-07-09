# Compression

ReFS compression is the feature most likely to make a file's bytes on disk look like noise to a
naive parser, and it is invisible to every standard Windows tool. There is **no compression flag on
a file, an extent, or a directory entry** — nothing in a file's metadata announces that its content
is compressed. Compression is a property of the **container** the data lives in, governed by a single
volume-wide policy stored in one obscure corner of the [Container Table](../structures/container_table.md)
root page. An analyst who reads a compacted container's clusters as plaintext gets garbage and no
warning. This page explains where the policy lives, how the driver chooses an algorithm, how the
compressed payload is framed on disk, and what it takes to read it back.

## Compression is per-container, not per-file

NTFS compresses individual files and records the fact in the file's own attributes. ReFS does the
opposite: it compresses at the level of a **container** — the same 64 MiB physical region that
[virtual addressing](virtual_addressing.md) translates VLCNs into — and stores compressed data only
inside containers that the dedup/compaction engine has *compacted*. Two consequences follow that
matter for forensics:

- A file's [extent descriptors](../structures/extent_descriptors.md) (type `0x40` entries) carry **no
  compression bit**. The extent still points at a VLCN; whether the bytes behind that VLCN are
  compressed depends entirely on the container, not the file. You cannot tell from a file's metadata
  alone whether its data is compressed.
- Because compression rides on the same compaction machinery as deduplication
  ([block refcount](../structures/block_refcount.md) is the shared tracking table), enabling
  `Enable-ReFSDedup -Type DedupAndCompress` is what actually compresses data. The `refsutil compression /c`
  command only *writes the policy parameters*; it does not compress anything by itself.

A container that holds compressed data is marked by **bit `0x800`** in the in-memory `SmsContainer`
flags word at `+0x264` (loaded from the container-table row). Its compressed payload is described by
one or more **`_SmsContainerCompressionHeader`** rows — row type code **`0x64` (100)** — kept in the
per-container index table at `CmsVolumeContainer+0x48`. Those two facts, the flag and the header row,
are the entire on-disk handle a tool has to find compressed data.

## The volume policy: where it lives and what it says

A single record carries the whole volume's compression policy: the format, the level, and the chunk
size. It is held in memory as `_SmsCompressionParameters` and persisted in two places — once inside the
running `CmsVolumeContainer`, and once on disk in the **extended header of the Container Table root
page at offset `0xA0`**. That on-disk location is deliberately out of reach of an ordinary B+-tree
walk: the standard page header ends at `0x70`, and the `0x70`–`0xBF` window is a set of
Container-Table-specific extended fields that normal row/node traversal never visits. This is why no
generic ReFS parser surfaces compression — you have to read those raw bytes directly.

The on-disk record:

| Offset | Size | Field | Values |
|--------|------|-------|--------|
| `0xA0` | u32 | prefix | always `0x0F` |
| `0xA4` | u16 | format | 0 = None, 1 = LZ4, 2 = ZSTD, 3 = LZ4QAT |
| `0xA6` | i16 | level | signed (e.g. 9 for LZ4) |
| `0xA8` | u32 | chunk size | bytes (e.g. `0x10000` = 64 KiB) |

The format enum has four real values; `3 = LZ4QAT` is hardware-accelerated LZ4, not a reserved slot
(see [algorithm dispatch](#algorithms-and-driver-dispatch) below). On a volume with compression off,
`0xA4` reads 0; enabling LZ4 or ZSTD flips `0xA4` and writes the configured chunk size at `0xA8` — a
clean before/after change that confirms both the format enum and the chunk-size field directly on disk.

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

The three `≤100` fields are percentage thresholds (exact per-field meaning is not labelled in the
driver). In the persistent `CmsVolumeContainer` these land at `+0x7c` (format), `+0x7e` (level),
`+0x80` (chunk), `+0xac`/`+0xb0`/`+0xb4` (ratios), and `+0xb8` (flags), written by
`SetDefaultCompressionParameters` and read back by `MsGetVolumeCompressionParameters`.

Each algorithm has its own default level and validity window:

| Algorithm | Default level | Valid levels |
|-----------|---------------|--------------|
| LZ4 | 1 | 1, 3–12 (level 2 invalid) |
| ZSTD | 3 | 1–22 |
| LZ4QAT | 9 | 1–9 |

(`GetDefaultCompressionLevel` / `IsCompressionLevelValid`.) The chunk size is not an enum: it is
validated only as a non-zero power of two by `IsCompressionChunkSizeValid` —

```c
// IsCompressionChunkSizeValid (Win11 v3.14)
return x != 0 && (x & (x - 1)) == 0;
```

— so any power-of-two chunk is legal. When chunk is 0, the driver falls back to the volume cluster
size (see [cluster and page size](cluster_page_size.md)). Setting the policy is journaled, so it
survives a crash mid-write: it is recorded by [MLog](../structures/mlog.md) redo opcode `0x27`
(`RedoSetDefaultCompressionParameters`, new in v3.14). `AddRedoRecord` is called with 7 values; the
redo handler requires at least 6 and optionally reads the 7th (the flags field).

## Algorithms and driver dispatch

The driver supports three live compression formats behind a vtable. `CmsCompression::InitializeLibrary`
builds a dispatch table indexed by format value (index 0 is unused):

```
SupportedCompressionFormats[1] = &CmsCompressionLZ4::vftable
SupportedCompressionFormats[2] = &CmsCompressionZSTD::vftable
SupportedCompressionFormats[3] = &CmsCompressionLZ4QAT::vftable
```

`GetCompressionClass(fmt)` validates `(u16)(fmt - 1) < 3` and returns the matching class pointer; the
read path then calls `DecompressBuffer` through vtable offset `+0x30`. One subtlety affects what an
analyst sees on disk: **LZ4 is silently promoted to LZ4QAT** when Intel QuickAssist hardware is present.
`PopulateUserCompressionParameters` does `if (fmt == 1 && qat_present) fmt = 3;`. This is a *runtime*
substitution — but note that the on-disk format field at `0xA4` can itself read 3 (LZ4QAT), so a tool
must treat 1 and 3 as the same block format (see decompressors below).

The decompressor bodies, in v3.14:

- **ZSTD** — `CmsCompressionZSTD::DecompressBuffer` sets up a static decompression context with
  `ZSTD_initStaticDCtx(workspace, 0x176c8)` (the static workspace is `0x176c8` bytes, from
  `GetDecompressionParameters`) and then calls `ZSTD_decompressDCtx`. This is the standard ZSTD
  library embedded in the driver.
- **LZ4 / LZ4QAT** — `CmsCompressionLZ4QAT::DecompressBuffer` contains a hand-rolled, inlined **LZ4
  block decoder**: token byte, the `0xF` literal/match-length extension loops, then the offset/length
  copy. It requires no scratch buffer. Crucially, **none of these formats use `RtlDecompressBuffer`** —
  a tool cannot lean on the Windows decompression API; it must implement the block codecs itself or
  link a matching library.
- A standalone `CmsCompressionLZ4::DecompressBuffer` (format index 1) was not separately located; it
  appears to share the same LZ4-block path used by LZ4QAT (unconfirmed).

## The on-disk compressed-range header

Each compressed range inside a compacted container is described by a `_SmsContainerCompressionHeader`,
a fixed **`0x40` (64)-byte** header followed by a variable u32 length array and, when checksums are
enabled, per-unit checksums. The layout below is read from the driver's own constructor:

| Off | Size | Field | Meaning |
|-----|------|-------|---------|
| `0x00` | u64 | base container Id / VLCN | container identity |
| `0x08` | u32 | header sequence index | `MakeNextHeader` = prev + 1 |
| `0x0C` | u32 | constant 7 | range/version discriminator (inferred) |
| `0x10` | u64 | compressed range LCN/offset | absolute vs container-relative undetermined |
| `0x18` | u64 | 0 | runtime range start (zero on disk) |
| `0x20` | u64 | compressed size in clusters | |
| `0x28` | u64 | 0 | runtime range length (zero on disk) |
| `0x30` | u32 | flags (`_EMS_CONTAINER_COMPRESSION_HEADER_FLAGS`) | see below |
| `0x34` | u32 | unit count | |
| `0x38` | u32 | constant `0x40` | offset from header start to the length array |
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

**Unit-length array.** Immediately after the 64-byte header (at `header + *(u32*)(header+0x38)`, i.e.
`header + 0x40`) sits one **u32 compressed length per unit**, with `[+0x34]` units in total.
`GetTotalSize` computes `4 * unit_count + base`, adding a per-unit checksum width when `flags & 0x2`.
`ReadAndDecompressCompressedRange` walks this array to find each unit's compressed length.

**Per-unit checksums.** When `flags & 0x2` (i.e. the checksum-type at `+0x3C` is nonzero) the checksums
follow the length array and are verified by `VerifyContainerCompressionHeaderChecksums`, using the
volume's checksum object selected by the checksum-type value — the same self-validating discipline
ReFS applies everywhere else (the checksum-algorithm selector itself lives at [VBR](../structures/vbr.md)
offset `0x2A` and is independent of compression).

The flag bits at `+0x30`:

| Bit | Meaning |
|-----|---------|
| `0x2` | per-unit checksums present |
| `0x1` | last unit stored raw/uncompressed (inferred from a `memcpy` decode branch) |
| `0x80000000` | runtime/in-memory only, never persisted (`MakeRuntimeHeader`) |

**Unit granularity is not 64 KiB.** Each unit decompresses to `SmsContainer+0x284` bytes (the
container's compacted cluster size), so the decompressed output of a range is
`(SmsContainer+0x284) * unit_count`. A tool that assumes a fixed 64 KiB unit will misalign every output
beyond the first unit.

## Reading compressed data back

The read path threads the policy, the container flag, and the header together:

```
RefsDecompressWorker
 -> MsReadCompressedContainerRange
 -> CmsVolumeContainer::ReadCompressedContainerRange
 -> CompactedRangeToCompressedRange        // gated by SmsContainer+0x264 & 0x800
      reads fmt = SmsContainer+0x280, level +0x282, unit size +0x284, csum type +0x294
      fetches the header (keyed by container Id, via MakeRuntimeHeader)
 -> ReadAndDecompressCompressedRange
      class = GetCompressionClass(fmt)
      for each unit:
          read u32 length from the header+0x40 array
          if (last unit && flags & 0x1)  memcpy raw
          else                            class->DecompressBuffer(...)  // vtable +0x30
      if (flags & 0x2)  VerifyContainerCompressionHeaderChecksums(...)
```

On the write side, header rows are inserted by `InsertContainerCompressionHeaders` (which calls
`CmsTable::InsertRow` with type code 100, then journals the insert via MLog redo `0x1a`) and removed by
`DeleteContainerCompressionHeaders`; the data is produced by `CompactAndCompressContainer` /
`CompressContainerBuffer`.

For a forensic tool to recover compressed content from a raw image it must, in order:

1. **Detect the compacted container** — test bit `0x800` of the flags word at `+0x264` in the
   container-table row (the row format is on the [Container Table](../structures/container_table.md) page).
2. **Read the header rows** — pull `_SmsContainerCompressionHeader` rows (type 100) from the
   per-container index table at `CmsVolumeContainer+0x48`.
3. **Walk the length array** — at `header+0x40`, one u32 per unit, `[+0x34]` units.
4. **Decompress each unit** — using the volume format (from `0xA4` / `SmsContainer+0x280`) and the unit
   size `SmsContainer+0x284`, honouring the raw-last-unit case (`flags & 0x1`) and verifying checksums
   when `flags & 0x2`.

## Why this is hard to see and hard to verify

Compression policy is exposed by **no** standard interface — not `fsutil fsinfo volumeinfo`, not
`Get-Volume`, not any metadata API. Only `refsutil compression /q` and direct reads of Container Table
root `0xA0` reveal it. That invisibility is the central forensic point: a volume can be compressing
data with nothing in any file's metadata to indicate it.

There is also a genuine open limit here. The volume-policy record at `0xA0` and the algorithm dispatch
are solidly grounded — the policy is confirmed on disk with before/after images, and the dispatch and
codecs are read straight from the driver. But the `_SmsContainerCompressionHeader` layout is decoded
**from driver code only**, not yet validated against an on-disk compressed range, and no real compressed
cluster has been round-tripped end to end through LZ4 or ZSTD. In lab attempts the dedup/compress engine
performed deduplication but not compression on unsuitable (random) data, so a truly compressed container
image is the missing piece. Specifically still unconfirmed: the meaning of the `+0x0C` constant 7,
whether `+0x10`/`+0x20` are absolute or container-relative, the raw-last-unit flag `0x1` (inferred from
a single decode branch), version stability across v3.4 and Insider (only v3.14 was read), and the
location of the code that serialises the `0x0F`-prefixed policy into the root-page header.

## Cross-references

- [Container Table](../structures/container_table.md) — its root-page extended header at `0xA0` is where the volume compression policy lives, and its rows carry the `+0x264 & 0x800` compacted-container flag a tool keys on
- [Virtual Addressing](virtual_addressing.md) — compression operates on the same 64 MiB containers that VLCN→PLCN translation is built around
- [Block Refcount](../structures/block_refcount.md) — the shared tracking table for the dedup/compaction engine that compression rides on (`DedupAndCompress`)
- [Extent Descriptors](../structures/extent_descriptors.md) — type `0x40` entries that, notably, carry no compression bit; compression is a container property, not a file property
- [MLog](../structures/mlog.md) — journals the policy change (redo `0x27`) and the header-row inserts (redo `0x1a`) so they survive a crash
- [Allocators](../structures/allocators.md) — compaction/compression is managed at the container level by the allocation engine
- [Cluster and Page Size](cluster_page_size.md) — the fallback chunk size and the per-unit decompressed size both derive from the cluster size
- [VBR](../structures/vbr.md) — the `0x2A` checksum-algorithm selector that the per-unit compression checksums reuse, independent of compression itself

## Evidence

The architecture and driver dispatch are firmly decoded (E2) from the v3.14 RTM driver: the
`_MS_COMPRESSION_FORMATS` enum and dispatch table (`CmsCompression::InitializeLibrary`,
`GetCompressionClass`), the LZ4→LZ4QAT promotion (`PopulateUserCompressionParameters`), and the
decompressor bodies (`CmsCompressionZSTD::DecompressBuffer` with `ZSTD_decompressDCtx`,
`CmsCompressionLZ4QAT::DecompressBuffer` inlined LZ4 block decode). The on-disk volume-policy record at
Container Table root `0xA0` (prefix `0x0F`, format `0xA4`, level `0xA6`, chunk `0xA8`) is raw-disk
confirmed (RD) with clean before/after images across LZ4 and ZSTD. The journaling opcodes are E2:
`0x27` (**AP_REDO_037**, `RedoSetDefaultCompressionParameters`, v3.14-only) for the policy and `0x1a`
(**AP_REDO_026**, v3.14) for header-row inserts. The static function inventory (ZSTD + LZ4 embedded at
v3.14, replacing the Win10 v3.4 LZX path) is **GN_COMP_SA_001** (E2). The compression-not-visible and
dedup-engine-required behaviours are **CT_COMP_RA_001** and **CT_COMP_RA_002** (RD). The
`_SmsContainerCompressionHeader` layout, the `+0x40` length array, the flag bits, and the read/decompress
flow are byte-accurately decoded from the driver constructor and read path (E2) but **not yet validated
against an on-disk compressed image**, and no real cluster has been round-tripped — **open question B3
remains partially open**. See [how this was verified](../methodology.md) to trace these to the exact
images and measurements in `analysis/`.
