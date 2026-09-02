# Allocator Tables

ReFS tracks free and allocated clusters with a three-tier allocator hierarchy. All three tiers share schema 0xe010 and an identical on-disk row format; they differ only in which region of the volume they manage and how their addresses are resolved.

## Bitmap Row — variable length

> **Row addresses are physical.** A row's `Range start` is a **physical** cluster number for the Medium tier —
> its span is exactly `[0, last mapped physical cluster)` on every volume measured, while the volume's
> *virtual* space starts at the first container id shifted up and is about twice as wide. That is a different
> question from the **Addressing** column in [the three tiers](#the-three-tiers) below, which says how each
> tier's own *table pages* are reached. If you hold a virtual cluster number, translate it through the
> [Container Table](container_table.md) before looking it up in a bitmap. The Container and Small tiers' row
> ranges are subsets of the physical space; their address basis has not been established.

A row is **not** a fixed size. It is `bitmap_offset + roundup8(ceil(range_length / 8))` — the bitmap holds one bit per cluster in the range and is exactly as long as that range needs. The common 2,072-byte row is simply the one covering 16,384 clusters; rows of 152 bytes (1,024 clusters) and 32 bytes (12 and 3 clusters) also occur.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Range start (LCN) (u64) | First cluster of the managed range |
| 0x08 | 8 | Range length (clusters) (u64) | Number of clusters in the range |
| 0x10 | 2 | Free count (u16) | Free clusters. **Saturates at 0xFFFF** — it does not wrap. A bitmap row can never reach that (its range is at most 16,384 clusters), so saturation only shows up on compact rows |
| 0x12 | 2 | Flags (u16) | **Bit 0 = "this row carries a bitmap"**. See Row Flags below |
| 0x14 | 1 | Bitmap offset (u8) | Where the bitmap starts: **0x18** when the row has one, **0x00** when it does not |
| 0x15 | 1 | Format byte (u8) | **1** for the Container and Small tiers on every version; **1** for Medium on v3.4 and **2** on v3.7+ |
| 0x16 | 2 | Allocated-count hint (u16) | A running count the driver keeps, where **0xFFFF means "the whole range"**. It is a hint, not an authority — see the warning below |
| 0x18 | `ceil(len/8)` | Allocation bitmap (bits) | 1 bit per cluster; 1 = allocated |

**Invariant**: `free_count = range_length - popcount(bitmap)` — holds on every bitmap row across the corpus.

> **Do not compute capacity from the field at +0x16.** It is a hint the driver maintains alongside the bitmap and lets drift: across the corpus it disagrees with the row's own bitmap on about one bitmap row in six (742 of 4,634). The driver carries routines to rebuild it and to mark it out of sync, which is what a cached statistic looks like. Count clusters from the **bitmap** instead — that is the authority.

To count clusters without ever reading a saturating or drifting field:

- **bitmap row** → allocated = `popcount(bitmap)` over exactly `range_length` bits; free = `range_length - popcount`.
- **compact row** → the range is uniform, so it is all one or all the other.

### Compact Row — 24 bytes

Used where a whole range is uniformly allocated or uniformly free and a bitmap would be redundant: flags bit 0 is clear and the bitmap offset is 0.

**Which of the two it is, is decided by the free count**, not by the hint at +0x16:

| `free_count` | Meaning |
|---|---|
| `0` | The whole range is **allocated** |
| non-zero (and equal to `min(range_length, 0xFFFF)`) | The whole range is **free** |

### Row Flags (offset +0x12)

**Bit 0 is the one that matters**: set means the row carries a bitmap, clear means it is a compact row. The driver decides where (and whether) to read a bitmap on that bit alone, in both the v3.4 and v3.14 generations. The values seen on disk follow from it:

| Value | Bit 0 | Meaning |
|-------|-------|---------|
| 0x01 | set | Bitmap row, partially allocated |
| 0x05 | set | Bitmap row, fully free |
| 0x09 | set | Bitmap row, fully free (alternative) |
| 0x02 | clear | Compact row |
| 0x06 | clear | Compact row (variant) |

## The volume's own accounting

Each allocator table keeps a **384-byte summary in its root page**, which ReFS maintains as it allocates and frees. It sits at the offset named in the table's index-root descriptor (`page + 0x50 + the u16 at page + 0x54`, in practice `page + 0x78`) and reads as a list of 64-bit values, of which two are decoded:

| Slot | Field |
|------|-------|
| 1 | Clusters covered |
| 2 | Free clusters |

This is the number ReFS itself works from, and it costs a single page read — no tree walk. `refsanalysis.py <image> allocators` prints it **beside** the totals recomputed from the rows, because the two can legitimately differ and the difference is informative:

- On **ReFS 3.4** the summary spans the whole mapped volume while the Medium tier's rows span less (the tiers are strictly separated, below) — yet the **free counts still match exactly**.
- If **both** numbers disagree, that points at a damaged volume — for example a truncated container table, where much of the volume is no longer mapped at all.

Across the corpus the summary and the recomputed rows agree on 268 of 281 tier readings, and every one of the 13 differences falls into one of those two explained cases.

## The three tiers

| Tier | Root index | Table ID | Addressing | Role |
|------|-----------|----------|------------|------|
| Medium | 1 | 0x21 | Virtual | General metadata + file data |
| Container | 2 | 0x20 | Virtual | Container Table pages |
| Small | 12 | 0x22 | **Real (physical)** | Bootstrap structures |

Most ReFS addresses are virtual and must be translated VLCN → PLCN through the [Container Table](container_table.md). The Small Allocator (root 12) is one of the three bootstrap exceptions that use real physical LCNs directly: it cannot use virtual addressing because it underlies the very translation that other structures depend on. Roots 7 and 8 (the Container Table itself) are the other two real-LCN roots.

## Three-tier interaction

The way the tiers divide up the volume changed between versions, while the row format did not.

### v3.4 — strict separation

Each tier manages separate containers with zero overlap:

- CID 0: Medium only
- CID 1: Small only
- CID 2: Container only
- CID 3+: Medium

### v3.14 — overlapping management

The Medium tier covers all containers (the entire virtual address space). The Container and Small tiers track their pages within specific containers. Where a specialised tier owns a container, Medium marks that container "fully allocated" with a compact row, and the specialised tier's bitmap tracks the individual 4-cluster page groups inside it.

### What that means when you add the tiers up

The two arrangements need opposite handling, and getting it wrong doubles or halves the answer:

- **v3.4** — the tiers *partition* the space. Medium and Container do not overlap at all, and clusters Medium does not cover are covered by another tier. To total the volume, take the **union**.
- **v3.7 and later** — Medium *contains* the others: its span covers the entire Container tier's span. **Never sum the tiers here** — Medium alone is the authority, and adding the specialised tiers counts the same clusters twice.

## What the allocator does not cover

The allocator accounts for the space the [Container Table](container_table.md) maps — no more. The tail of the volume past the last container belongs to no tier, because ReFS never creates the partial container that would be needed to reach the end of the disk.

That tail is **48 MiB on almost every volume**, whatever its version, cluster size, or size — 12,288 clusters at 4 KiB, 768 at 64 KiB. A volume that has grown its containers on demand can leave much more (a 60 GB Windows volume in the corpus has 924 containers where 956 would fit, leaving about 2 GB).

It is not free space, and it must not be reported as any. Tools should state it separately.

## Finding a tier: by table, not by root number

The checkpoint's root list has the Medium allocator at index 1, Container at 2 and Small at 12 — but the index is a convention, not an identity. On a damaged volume in the corpus, **root 12 carries the Container Table (0x0B) rather than the Small allocator**, and two other root slots are empty.

Matching the root page's own table id is necessary but still not sufficient: on those same volumes the Medium root page does claim 0x21, yet its subtree leads into pages belonging to other tables entirely. The safe rule is to check **each page** as you walk, and accept a row only from a page that claims the tier's own table id. On an undamaged volume this rejects nothing; on a damaged one it is the difference between a wrong number and a reported gap.

## Driver behaviour

The on-disk row format is unchanged across versions despite a driver refactoring. The v3.4 driver split allocator logic across the `CmsAllocatorBase` and `CmsGlobalAllocator` classes; v3.14 merged these into a single `CmsAllocator` class and expanded the number of allocation zones from 9 to 13.

Relevant driver routines: `Allocate` (the general allocation routine that finds free page groups in the bitmap) and `MsAllocateObjectId` (allocates a new OID via the allocator subsystem).

The row layout above is read straight from the driver's own codec, in both generations: v3.14 `CmsAllocator::BPlusRowToRegionEx` decodes a row (and expands the 0xFFFF hint to the full range length), `CmsAllocator::PersistRegion` writes one back, and the v3.4 `CmsGlobalAllocator::CopyBPlusRowToFv` copies one — the last of these copies exactly `range_length / 8` bitmap bytes, which is where the variable row length comes from. `CmsAllocator::LoadAllocatorSummary` is what reads the 384-byte root-page summary; the presence of `RebuildAllocatorSummary` and `MarkAllocatorSummaryOutOfSync` beside it is why the summary is cross-checked rather than trusted blindly.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — roots 1 (Medium), 2 (Container), 12 (Small) in the root-pointer list
- [Container Table](container_table.md) — the Container Allocator manages this table's pages, and supplies the VLCN→PLCN translation the Medium/Container tiers depend on
- [Container Index](container_index.md) — the by-state index the allocator subsystem consumes
- [Schema Table](schema_table.md) — all three tiers use schema 0xe010

## Reading it with the tools

```sh
python3 refsanalysis.py <image> allocators        # per-tier totals + volume capacity
python3 refsanalysis.py <image> allocators -v     # + the individual allocation ranges
python3 forefst.py <image> summary                # the capacity line, from the persisted summary
```

## Evidence

The three-tier hierarchy, the bitmap/compact row layouts, and the `free_count` invariant are raw-disk decoded across the corpus and corroborated in the driver (`CmsAllocator` / the v3.4 `CmsAllocatorBase` + `CmsGlobalAllocator` split). The Small Allocator's real-LCN bootstrap exception (roots 7, 8, 12) is raw-disk-confirmed and driver-backed. The 9→13 allocation-zone expansion is from static analysis of the v3.14 driver. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

Findings: **CT_ALLC_RA_001** (deep row structure), **FS_ALLOC_RA_001** (row format: variable-length bitmap, the two bytes at +0x14, flags bit 0, the +0x16 hint, the compact-row discriminator), **FS_ALLOC_RA_002** (the persisted summary, tier resolution, the unmapped tail, and per-page tier identification), **CT_ALLC_001/002/003** (the three tiers), **GN_ARCH_RA_001** (real-LCN bootstrap exception), **GN_ALLC_SA_001** (Win11 allocator unification, 9→13 zones), **FS_CHKP_010/011/021** (global tables 0x21/0x20/0x22).
