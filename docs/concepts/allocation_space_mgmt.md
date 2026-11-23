# Space Allocation and Free-Space Management

ReFS decides which clusters are free and which are in use with a **three-tier bitmap allocator** (Medium,
Container, Small), all sharing schema `0xe010`.

For a forensic analyst this allocator records which clusters are *live* and which are *freed*. Because ReFS does not
zero a cluster when it frees it, the allocator also decides how long deleted file data can be carved.

A freed cluster reads exactly as it did when allocated until the allocator gives it to a new write. So a claim that
a cluster is "in use" or "available" can be trusted only after the allocator's state is reconstructed.

> **There is no `$BITMAP` attribute.** An analyst arriving from NTFS — where `$Bitmap` (MFT entry 6) is the
> volume free-space map — will look for an equivalent per-file attribute here and find none: no object
> carries a `$BITMAP` attribute, and there is no such type code (the string appears only as a debug label).
> On ReFS this three-tier allocator does the job of NTFS's `$Bitmap`; its exact row layout is
> on the [Allocators](../structures/allocators.md) structure page.

## The three tiers

All three tiers are allocator tables (schema `0xe010`) holding the *same* on-disk row format; they differ
only in scope and in how their table pages are reached:

| Tier | Root | Table ID | Root addressing | Manages |
|------|------|----------|-----------------|---------|
| Medium | 1 | 0x21 | Virtual | General metadata + file data |
| Container | 2 | 0x20 | Virtual | Container Table pages |
| Small | 12 | 0x22 | **Real (physical) LCN** | Bootstrap structures |

The Medium and Container tables are reached through [virtual](virtual_addressing.md) root references, but the
**Small Allocator (root 12) is reached at a real physical LCN**. That is deliberate: the Small tier underlies the
[Container Table](../structures/container_table.md) machinery that *performs* the VLCN→PLCN translation everything
else depends on, so it cannot itself require that translation to be readable — it is the same bootstrap exception
that makes roots 7, 8 and 12 store real LCNs.

How a table is reached does not tell what its rows count. The **Medium tier's rows count physical
clusters**: a caller holding a VLCN must translate it before testing a Medium bitmap. The Container and Small tiers'
row address basis is not established.

The byte-level row decode for all three tiers lives on the [Allocators](../structures/allocators.md) structure page.

## How free vs. allocated is determined

Each managed range is described by one row. A **bitmap row** carries an allocation bitmap at offset
`+0x18` — **1 bit per cluster, where `1 = allocated`**. The row is **not a fixed size**: the bitmap is
exactly as long as its range needs, so the row measures `bitmap_offset + roundup8(ceil(range_length / 8))`.
The familiar 2,072-byte row is the one covering 16,384 clusters; rows of 152 bytes (1,024 clusters)
and 32 bytes (12 and 3 clusters) occur too. Ranges that are entirely allocated or entirely free do
not need a bitmap, so they are stored as a **compact row** that keeps the header fields and drops the
bitmap payload — the common case of a whole container fully in use, or fully free, without spending 2 KiB
on a uniform bitmap. Whether a row carries a bitmap is stated by **bit 0 of the flags** at `+0x12`, not by
the row's length; for a compact row it is the **free count** that says which of the two uniform states it
is in.

The free/used split is self-checking. Each row's free count at `+0x10` must equal its range length at
`+0x08` minus the number of set bits in the bitmap:

```text
free_count (+0x10) = range_length (+0x08) - popcount(bitmap)
```

This invariant holds on every bitmap row measured across the corpus, which makes it a useful integrity
check when parsing: a row that fails it is either misframed or tampered. (It is a bitmap-row rule: a compact
row has no bitmap, and its free count saturates at 0xFFFF rather than wrapping, so read a compact row's state
from the free count being zero or non-zero.) A cluster is therefore **"live" iff its bit is set in the
governing tier's bitmap row** (or it falls under a fully-allocated compact row).

## Allocating clusters: AllocateLcns

`AllocateLcns` is the central allocation dispatcher — it finds free clusters and flips their bitmap bits
to allocated. When a write needs space for a new metadata page or file extent, it scans the appropriate
tier's bitmap for a free run, marks that run used, and decrements the row's free count:

```text
write needs N clusters
 │
 ▼
AllocateLcns  ← finds a free run, sets bits = 1
 │ (helpers: AllocateRange, AllocateFromCandidate,
 │  AllocateFromBitmapCandidateCacheAware)
 ▼
bitmap row updated; free_count decremented
```

Because allocation only ever flips a `0` bit to `1` and never touches cluster *contents*, the bitmap is
the only place where a cluster's status changes. That is why the bitmap, not file-tree reachability, is the
authoritative record of whether a cluster is live or free.

## Recently-deallocated tracking

Freeing a cluster is **not** the same as making it reusable. When clusters are released the driver does
**not** clear them, and the driver's code keeps a *recently-deallocated* set of ranges that is emptied at a
checkpoint:

```text
free clusters → the recently-deallocated set     ← range parked, not yet reusable
    ...the allocator consults it (CheckRecentlyDeallocated on 17134,
       RecentlyDeallocatedForAllocator on 26100) before reusing a range
checkpoint → EmptyRecentlyDeallocated            ← ranges released to the free pool
```

`EmptyRecentlyDeallocated` is called from the checkpoint (`CmsVolume::Checkpoint` on 26100.8115 and .9444,
`NotifyCheckpointFlushCompletion` on 17134) and at shutdown. Read from those call sites, it is the moment parked
ranges become reusable; until it runs, those clusters are off-limits to `AllocateLcns` and their contents stay
intact. The mask/unmask routines (`UnmaskRecentlyDeallocated`, `MaskUnmaskRecentlyDeallocatedTrim`,
`DeleteFromRecentlyDeallocatedOrTrim`) manage which parked ranges are still pending.

This fits copy-on-write: until the next checkpoint is written, the tree of the last checkpoint — the one a crash
would restart from (see [transactions](transactions_crash_consistency.md)) — can still reference the freed clusters.
That reason is an inference from the call structure, not traced, and the lifecycle was not measured on disk. Its
forensic side effect is to *widen* the window in which freshly-deleted data survives.

## Forensic implications

**Distinguishing live from freed clusters.** A cluster is live iff its bit is set in the governing
allocator row (or it falls under a fully-allocated compact row). To classify any LCN, resolve it to the
tier that owns it (Medium for most data and metadata; Container and Small for their own pages), then test
the bit at `+0x18` (a Medium bit is indexed by the physical cluster: translate a VLCN first). Do not trust
file-tree reachability alone: a cluster can be unreferenced by any live file yet still marked allocated — for
example while it sits in the recently-deallocated set — and, conversely, a cluster marked free may still hold
complete, recoverable content.

**Why deleted data survives, and for how long.** ReFS frees clusters but does not zero them, so
freed content persists until the allocator reuses the clusters. The recovery outcome falls into three
tiers, set by whether a live map still names the cluster (the [Block Refcount table](../structures/block_refcount.md)
counts only clone and deduplication references, so it does not decide this):

- **Still referenced:** a live map still names the clusters (a stream snapshot's extents, a clone's), so the
  allocator cannot free them yet — guaranteed survival while that map lives.
- **Freed, not yet reallocated:** no live map names them; data survives until `AllocateLcns` reuses the
  clusters.
- **Reallocated:** overwritten by a new allocation — gone.

**What bounds carving success.** The carving window is bounded by reuse, and the recently-deallocated set
*extends* it: ranges still parked there are shielded from `AllocateLcns` until `EmptyRecentlyDeallocated`
releases them, so freshly-deleted content is *more* likely to survive than the raw bitmap alone implies.

Carving can succeed on:

- any free-bitmap cluster not yet overwritten;
- recently-deallocated ranges still pending release.

It fails wherever `AllocateLcns` has already re-handed a range to a new write. Scope a carve to clusters whose
allocator bit is `0` *or* that resolve to a recently-deallocated range, and treat any cluster with a set bit and a
live owner as overwritten unless it is shared (a snapshot's or a clone's). The end-to-end recovery procedure is on
the [deletion recovery](deletion_recovery.md) page, and the survival categories are summarised under
[what survives](what_survives.md).

**Cross-check the bitmap; do not assume it.** The bitmap is authoritative for whether a cluster is *live*,
but it does not show whether the cluster's content has been overwritten. A `free` bit means "available for reuse," not "wiped" — so pair the
bitmap with the maps that still name a cluster (a snapshot's, a clone's) and the metadata tree before drawing any
conclusion about whether a cluster's bytes are still the file's.

## Version and state differences

The **row format itself is version-invariant** — the same fields in the same places, the bitmap at `+0x18`
whenever one is present — across all versions from v3.4 through Insider. What changed across versions is
narrower:

- **The format byte at `+0x15`.** The two bytes at `+0x14` are a pair: `+0x14` is the **bitmap offset**
  (`0x18` when the row carries a bitmap, `0` when it does not) and `+0x15` is a **format byte** whose value
  is 1 or 2. It is **tier**-dependent as much as version-dependent: the Container and Small tiers are format
  1 on every version, while the Medium tier is 1 on v3.4 and 2 on v3.7+.
- **Tier interaction.** v3.4 enforces strict separation: container ID 0 = Medium, ID 1 = Small, ID 2 =
  Container, ID 3+ = Medium, with zero overlap. From v3.7 on, management *overlaps*: the Medium tier covers the
  whole volume and marks the specialised tiers' containers as fully-allocated compact rows, while the Container and
  Small bitmaps track individual 4-cluster page groups inside those containers.
  - A parser must therefore not assume a cluster is owned by exactly one tier from v3.7 on.
  - Never sum the tiers there: the Medium tier alone is the authority. On v3.4 the tiers are unioned.
- **Driver classes.** v3.4 split allocation across two classes, `CmsAllocatorBase` and
  `CmsGlobalAllocator`; v3.14 **unified these into a single `CmsAllocator`**, and the number of allocation
  zones grew from 9 to 13. This refactor is why a v3.14 `AllocateLcns` dispatcher looks structurally different from its
  v3.4 ancestors even though the on-disk bitmap is identical — see
  [Driver Architecture](driver_architecture.md).

**Large-volume anomaly.** On one large (2 TB) volume, root 12 — the Small Allocator, normally Table ID `0x22` —
resolves instead to a Container-Table page, by a mechanism that is not yet understood; on the same volume roots 4
and 6 are empty and root 1's subtree reaches pages of other tables. Do not assume root 12 → `0x22`: select a tier by
its table id, and accept a row only when the page that carries it claims the tier's own table id (`page+0x48`).

## Tooling

The allocator tables are parsed as schema `0xe010` system tables; the [Allocators](../structures/allocators.md)
page gives the bitmap-row, compact-row and flag decode a tool needs. Free/allocated classification of a
target LCN follows directly from the governing row's `+0x18` bitmap, and deleted-content scope follows
from pairing that with the maps that still name a cluster (a snapshot's extents; the
[block refcount](../structures/block_refcount.md) for clones and deduplication) and the
[deletion recovery](deletion_recovery.md) workflow.

`forefst.py summary` and `fastsummary` report the volume's capacity from the Medium allocator's own persisted
summary (its root page): used clusters, and not-allocated clusters (free space plus the reserve Windows keeps).

## Cross-references

- [Allocators](../structures/allocators.md) — byte-level allocator row layout (bitmap row, compact row, flags) this page reasons over
- [Virtual Addressing](virtual_addressing.md) — why the Small Allocator (root 12) is reached at a real LCN, and the Medium rows' physical ranges
- [Container Table](../structures/container_table.md) — the VLCN→PLCN map the Container tier feeds, and the bootstrap structure the Small tier underlies
- [Block Reference Count](../structures/block_refcount.md) — the per-cluster count of clone and deduplication references beyond the first (snapshot sharing is not counted)
- [Copy-on-Write](copy_on_write.md) — the update model that keeps superseded versions while a map still names them
- [Deletion Recovery](deletion_recovery.md) — recovering freed-but-not-reused content using the bitmap
- [What Survives](what_survives.md) — the survival categories after deletion and unmount
- [Transactions and Crash Consistency](transactions_crash_consistency.md) — the checkpoint boundary that gates `EmptyRecentlyDeallocated`
- [Driver Architecture](driver_architecture.md) — the `Cms` allocator class refactor across builds

## Evidence

The three-tier model, the bitmap/compact row layouts (variable-length row, bitmap at `+0x18`,
`1 = allocated`), the `free_count = range_length − popcount(bitmap)` invariant, the tier- and
version-dependent Medium format byte, and the v3.4-vs-v3.7+ tier-interaction change are confirmed on the raw-disk
corpus and corroborated in the driver (the row codec read on 26100 and 17134).

The counts behind the text:

- the row size matches the driver's formula on 4,634 of 4,634 bitmap rows, and the free-count invariant holds on
  all of them; the compact-row free-count rule resolves 1,061 of 1,061 compact rows (95 volumes);
- the Medium rows' physical addressing: the Medium span is exactly the volume's physical cluster range on every
  image measured, and 13,917 live extents on 28 images are marked allocated 99–100 % of the time by their physical
  cluster against 0–27 % by their VLCN;
- the tier interaction: Medium ∩ Container = 0 on all 9 v3.4 volumes, and the entire Container span on 86 of 86
  v3.7+ volumes;
- the root-12 anomaly is on the four images of the 2 TB "millions of actions" volume (1,368 of 7,063 rows reached
  from its tier roots sit on a page of another table); on the 91 undamaged images the page-id test rejects nothing.

The allocation path is `AllocateLcns` with its `AllocateRange` / `AllocateFromCandidate` /
`AllocateFromBitmapCandidateCacheAware` helpers, and the recently-deallocated routines named above are present in
the driver; their lifecycle is read from their call sites only. The "freed but not zeroed" survival behaviour and
the three recovery tiers are disk-validated. The class refactor (`CmsAllocatorBase` + `CmsGlobalAllocator` →
unified `CmsAllocator`) and zone expansion are driver readings.

See [how this was verified](../methodology.md) for the method.
