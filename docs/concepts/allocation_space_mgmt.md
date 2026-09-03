# Space Allocation and Free-Space Management

ReFS decides which clusters are free and which are in use with a **three-tier bitmap allocator** (Medium,
Container, Small), all sharing schema `0xe010`. For a forensic analyst this allocator is the authority
that separates *live* clusters from *freed* clusters — and because ReFS never zeroes a cluster on free, it
is also what bounds how long deleted file data stays carveable. A freed cluster reads exactly as it did
when allocated until the allocator hands it to a new write, so reconstructing the allocator's view is the
precondition for trusting any claim that a cluster is "in use" or "available."

> **There is no `$BITMAP` attribute.** An analyst arriving from NTFS — where `$Bitmap` (MFT entry 6) is the
> volume free-space map — will look for an equivalent per-file attribute here and find none: no object
> carries a `$BITMAP` attribute, and there is no such type code (the string appears only as a debug label).
> The role NTFS gives to `$Bitmap` is played instead by this three-tier allocator; its exact row layout is
> on the [Allocators](../structures/allocators.md) structure page.

## The three tiers

All three tiers are allocator tables (schema `0xe010`) holding the *same* on-disk row format; they differ
only in scope and addressing:

| Tier | Root | Table ID | Addressing | Manages |
|------|------|----------|------------|---------|
| Medium | 1 | 0x21 | Virtual | General metadata + file data |
| Container | 2 | 0x20 | Virtual | Container Table pages |
| Small | 12 | 0x22 | **Real (physical) LCN** | Bootstrap structures |

Two of the tiers live in [virtual address space](virtual_addressing.md), but the **Small Allocator
(root 12) is addressed in real physical LCNs**, not virtual. That is deliberate: the Small tier underlies
the [Container Table](../structures/container_table.md) machinery that *performs* the VLCN→PLCN
translation everything else depends on, so it cannot itself require that translation to be readable — it
is the same bootstrap exception that makes roots 7, 8 and 12 store real LCNs. The byte-level row decode
for all three tiers lives on the [Allocators](../structures/allocators.md) structure page.

## How free vs. allocated is determined

Each managed range is described by one row. A **bitmap row** carries an allocation bitmap at offset
`+0x18` — **1 bit per cluster, where `1 = allocated`**. The row is **not a fixed size**: the bitmap is
exactly as long as its range needs, so the row measures `bitmap_offset + roundup8(ceil(range_length / 8))`.
The familiar 2,072-byte row is simply the one covering 16,384 clusters; rows of 152 bytes (1,024 clusters)
and 32 bytes (a dozen clusters or fewer) occur too. Ranges that are entirely allocated or entirely free do
not need a bitmap at all, so they collapse to a **compact row** that keeps the header fields and drops the
bitmap payload — the common case of a whole container fully in use, or fully free, without spending 2 KiB
on a uniform bitmap. Whether a row carries a bitmap is stated by **bit 0 of the flags** at `+0x12`, not by
the row's length; for a compact row it is the **free count** that says which of the two uniform states it
is in.

The free/used split is self-checking. Each row's free count at `+0x10` must equal its range length at
`+0x08` minus the number of set bits in the bitmap:

```
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

```
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
the single point where a cluster's status changes — which is exactly why the bitmap, not file-tree
reachability, is the authoritative live/free signal.

## Recently-deallocated tracking

Freeing a cluster is **not** the same as making it reusable. When clusters are released the driver does
**not** clear them and does **not** immediately return them to the free pool for re-handout. Instead it
records the range in a *recently-deallocated* set, gated by checkpoint and transaction boundaries:

```
free clusters → MergeIntoRecentlyDeallocated   ← range parked, NOT yet reusable
    ...the allocator consults CheckRecentlyDeallocated /
       RecentlyDeallocatedForAllocator before reusing a range (avoids handing
       back clusters a not-yet-committed transaction may still reference, or
       that a snapshot still needs)
checkpoint advances → EmptyRecentlyDeallocated  ← ranges released to the free pool
```

`EmptyRecentlyDeallocated` is the moment parked ranges become genuinely reusable; until it runs, those
clusters are off-limits to `AllocateLcns` and their contents are preserved intact. The mask/unmask
routines (`UnmaskRecentlyDeallocated`, `MaskUnmaskRecentlyDeallocatedTrim`,
`DeleteFromRecentlyDeallocatedOrTrim`) manage which parked ranges are still pending. This mechanism
exists for crash-consistency — it is what keeps the allocator from reusing space a half-committed
[transaction](transactions_crash_consistency.md) could roll back into — but its forensic side effect is
to *widen* the window in which freshly-deleted data survives.

## Forensic implications

**Distinguishing live from freed clusters.** A cluster is live iff its bit is set in the governing
allocator row (or it falls under a fully-allocated compact row). To classify any LCN, resolve it to the
tier that owns it (Medium for most data and metadata; Container and Small for their own pages), then test
the bit at `+0x18`. Do not trust file-tree reachability alone: a cluster can be unreferenced by any live
file yet still marked allocated — for example when it is [copy-on-write](copy_on_write.md)-shared or sitting
in the recently-deallocated set — and, conversely, a cluster marked free may still hold complete,
recoverable content.

**Why deleted data survives, and for exactly how long.** ReFS frees clusters but never zeroes them, so
freed content persists until the allocator reuses the clusters. The recovery outcome falls into three
tiers, set by the cluster's [block reference count](../structures/block_refcount.md):

- **CoW-protected (refcount ≥ 2):** guaranteed survival — both checkpoints reference the clusters, so
  the allocator cannot free them yet.
- **Unreferenced but not reallocated (refcount = 0):** data survives until `AllocateLcns` reuses the
  clusters.
- **Reallocated:** overwritten by a new allocation — gone.

**What bounds carving success.** The carving window is bounded by reuse, and the recently-deallocated set
*extends* it: ranges still parked there are shielded from `AllocateLcns` until `EmptyRecentlyDeallocated`
releases them, so freshly-deleted content is *more* likely to survive than the raw bitmap alone implies.
Carving will succeed on (a) any free-bitmap cluster not yet overwritten, and (b) recently-deallocated
ranges still pending release; it fails wherever `AllocateLcns` has already re-handed a range to a new
write. Scope a carve to clusters whose allocator bit is `0` *or* that resolve to a recently-deallocated
range, and treat any cluster with a set bit and a live owner as overwritten unless it is CoW-shared. The
end-to-end recovery procedure is on the [deletion recovery](deletion_recovery.md) page, and the survival
categories are summarised under [what survives](what_survives.md).

**Cross-check the bitmap; do not assume it.** The bitmap is authoritative for *live state* but says
nothing about *content freshness*. A `free` bit means "available for reuse," not "wiped" — so pair the
bitmap with the refcount (CoW protection) and the metadata tree before drawing any conclusion about
whether a cluster's bytes are still the file's.

## Version and state differences

The **row format itself is version-invariant** — the same fields in the same places, the bitmap at `+0x18`
whenever one is present — across all versions from v3.4 through Insider. What changed across versions is
narrower:

- **The format byte at `+0x15`.** The two bytes at `+0x14` are a pair: `+0x14` is the **bitmap offset**
  (`0x18` when the row carries a bitmap, `0` when it does not) and `+0x15` is a **format byte** whose value
  is 1 or 2. It is **tier**-dependent as much as version-dependent: the Container and Small tiers are format
  1 on every version, while the Medium tier is 1 on v3.4 and 2 on v3.7+.
- **Tier interaction.** v3.4 enforces strict separation: container ID 0 = Medium, ID 1 = Small, ID 2 =
  Container, ID 3+ = Medium, with zero overlap. v3.14 switched to *overlapping* management — Medium covers
  the entire virtual address space and marks the specialised tiers' containers as fully-allocated compact
  rows, while the Container and Small bitmaps track individual 4-cluster page groups inside those
  containers. A parser must therefore not assume a cluster is owned by exactly one tier on v3.14.
- **Driver classes.** v3.4 split allocation across two classes, `CmsAllocatorBase` and
  `CmsGlobalAllocator`; v3.14 **unified these into a single `CmsAllocator`**, and the number of allocation
  zones grew from 9 to 13. This refactor is why a v3.14 `AllocateLcns` dispatcher looks structurally different from its
  v3.4 ancestors even though the on-disk bitmap is identical — see
  [Driver Architecture](driver_architecture.md).

**Large-volume anomaly.** On a very large (multi-terabyte) volume, root 12 — the Small Allocator, normally
Table ID `0x22` — has been observed resolving instead to a Container-Table page, by a mechanism that is
not yet understood. Do not assume root 12 → `0x22` on very large volumes; verify the Table ID from the
checkpoint root list rather than trusting the index.

## Tooling

The allocator tables are parsed as schema `0xe010` system tables; the [Allocators](../structures/allocators.md)
page gives the bitmap-row, compact-row and flag decode a tool needs. Free/allocated classification of a
target LCN follows directly from the governing row's `+0x18` bitmap, and deleted-content scope follows
from pairing that with the [block refcount](../structures/block_refcount.md) (CoW) and the
[deletion recovery](deletion_recovery.md) workflow.

## Cross-references

- [Allocators](../structures/allocators.md) — byte-level allocator row layout (bitmap row, compact row, flags) this page reasons over
- [Virtual Addressing](virtual_addressing.md) — why the Small Allocator (root 12) uses real LCNs while Medium and Container use virtual
- [Container Table](../structures/container_table.md) — the VLCN→PLCN map the Container tier feeds, and the bootstrap structure the Small tier underlies
- [Block Reference Count](../structures/block_refcount.md) — the per-cluster refcount that decides CoW protection vs. reuse eligibility
- [Copy-on-Write](copy_on_write.md) — refcount ≥ 2 sharing that guarantees a freed cluster's content survives
- [Deletion Recovery](deletion_recovery.md) — recovering freed-but-not-reused content using the bitmap and refcount
- [What Survives](what_survives.md) — the survival categories after deletion and unmount
- [Transactions and Crash Consistency](transactions_crash_consistency.md) — the checkpoint boundary that gates `EmptyRecentlyDeallocated`
- [Driver Architecture](driver_architecture.md) — the `Cms` allocator class refactor across builds

## Evidence

The three-tier model, the bitmap/compact row layouts (variable-length row, bitmap at `+0x18`,
`1 = allocated`), the `free_count = range_length − popcount(bitmap)` invariant, the tier- and
version-dependent Medium format byte, and
the v3.4-vs-v3.14 tier-interaction change are confirmed on the raw-disk corpus (RD) and corroborated in the
driver (E2). The allocation path is `AllocateLcns` with its `AllocateRange` / `AllocateFromCandidate` /
`AllocateFromBitmapCandidateCacheAware` helpers, and the deferred-reuse lifecycle runs
`MergeIntoRecentlyDeallocated → CheckRecentlyDeallocated` /
`RecentlyDeallocatedForAllocator` → `EmptyRecentlyDeallocated` (with `UnmaskRecentlyDeallocated`,
`MaskUnmaskRecentlyDeallocatedTrim`, `DeleteFromRecentlyDeallocatedOrTrim` managing pending ranges) — all
present in the driver (E2). The "freed but not zeroed" survival behaviour and the three recovery tiers are
disk-validated (RD). The class refactor (`CmsAllocatorBase` + `CmsGlobalAllocator` → unified `CmsAllocator`)
and zone expansion are E2. The large-volume root-12 anomaly is RD with an undetermined mechanism. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
