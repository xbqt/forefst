# Copy-on-Write (CoW)

Copy-on-write is the rule that makes ReFS recoverable: **no metadata page is ever overwritten in
place.** Every modification writes a *new* copy of the affected page and propagates the pointer change
up the B+-tree to a fresh root, so the pre-change page survives on disk until the allocator happens to
reclaim its space. For a forensic analyst this is the foundation of almost every single-image recovery
path on ReFS — superseded pages, stream snapshots, refcount-protected clusters — and it is why ReFS,
unlike NTFS, never needs an undo journal. This page explains the update mechanism, why it produces the
artifacts it does, and what each artifact is worth in practice.

## How a CoW update propagates

A modification never touches the pinned page in memory; instead the change becomes a transaction that is
committed by writing entirely new clusters. The sequence is:

1. The modified **leaf node** is written to a **newly allocated** location — the clusters come from the
   [allocators](../structures/allocators.md) via `CmsAllocator::AllocateLcns`, exactly the same
   allocate-new step that [virtual addressing](virtual_addressing.md) lets ReFS perform without
   rewriting any per-file extent table.
2. The parent node has to point at the new leaf, but the parent is itself immutable — so a **new copy of
   the parent** is written, with the updated child [page reference](../structures/page_references.md).
3. Propagation continues up the B+-tree: every node on the path from the leaf to the root is re-copied.
4. The new **root** pointer is recorded in a new [checkpoint (CHKP)](../structures/chkp.md).
5. A single atomic write of the checkpoint is the **commit point** — until that write lands, nothing on
   disk references the new chain, so a crash mid-update simply leaves the old chain in force.
6. The **old pages persist** on disk until the allocator reuses their clusters.

The driver entry point for this path is `MsUpdateDataWithRoot`, which dispatches into the per-table
`CmsBPlusTable::UpdateDataWithRoot`; the re-rooting itself is managed by the `CmsCowRootComposite`
class, whose name records the design directly. The same propagation underlies the file-create chain
(`RefsFsdCreate` → … → `MsUpdateDataWithRoot` → checkpoint).

## Why this produces redo-only recovery

Copy-on-write makes **undo logging unnecessary**, and that single fact reshapes the on-disk forensics.
Consider a crash partway through a transaction:

- The old, pre-transaction pages are still intact — nothing overwrote them.
- The on-disk checkpoint still points at those old pages.
- The volume is therefore *already* in a consistent state; there is nothing to roll back.

Because there is nothing to undo, the [MLog](../structures/mlog.md) records only **redo** operations.
This is the structural opposite of the NTFS `$LogFile`, which must store both redo *and* undo records
precisely because NTFS overwrites in place and must be able to reverse a half-applied change. The
[transaction and crash-consistency](transactions_crash_consistency.md) model formalizes this as a
two-pass recovery (analyze, then redo) with no undo pass.

The driver makes the discipline concrete. `UpdateDataWithRoot` never patches the pinned page bytes: it
records the change through `CmsTransactionContext::AddRedoRecord` and reserves an undo *slot* via
`AllocateUndo`, so the commit writes new pages rather than mutating old ones. If either the undo slot or
the redo record cannot be obtained, the transaction **aborts** — and because nothing was overwritten,
the old pages simply stay reachable. That abort-leaves-old-state-intact behavior is the mechanical
reason recovery can be redo-only.

```c
// MsUpdateDataWithRoot (Win11 v3.14 driver) — thin dispatcher into the virtual table method
void MsUpdateDataWithRoot(CmsTransactionContext *param_1, CmsBPlusTable *param_2, ...)
{
    if (*(code **)(*(longlong *)param_2 + 0x10) == CmsBPlusTable::UpdateDataWithRoot)
        CmsBPlusTable::UpdateDataWithRoot(param_2,param_1,param_3,param_4,param_5,param_6);
    else
        (**(code **)(*(longlong *)param_2 + 0x10))(param_2);
}
```

```c
// CmsBPlusTable::UpdateDataWithRoot (Win11 v3.14 driver, excerpt)
pSVar4 = AllocateUndo(this,param_1,0xc,uVar7,param_3,param_4, ...);   // reserve undo slot
if (pSVar4 == 0) { lVar3 = -0x3fffff66; goto LAB_abort; }            // abort -> no overwrite
lVar3 = CmsTransactionContext::AddRedoRecord(param_1,this,4, ...);    // redo record, not in-place
```

## What CoW leaves on disk

After any CoW update there are **two complete page chains** on the volume: the *new* chain the current
checkpoint references, and the *old* chain that nothing references any more. Both are byte-for-byte
intact — only their reachability changed. On a lightly-used volume these unreferenced layers accumulate
and several generations of past file-system state can coexist; on a busy volume the allocator reclaims
old clusters faster and history is shallower.

### Superseded pages

Because old pages are never zeroed, a signature scan for the `"MSB+"` B+-tree marker in the
[page header](../structures/page_header.md) across a raw image can surface historical metadata that the
live tree no longer points at. Whether a given old page is still usable depends on its cluster's status,
which sorts into three categories:

- **CoW-protected (refcount ≥ 2):** the clusters are still referenced by another object (a snapshot, a
  clone, or a hard link) and carry a refcount ≥ 2 in the [Block Refcount table](../structures/block_refcount.md);
  the allocator will not reclaim them, so survival is **guaranteed**.
- **Unreferenced but not reallocated (refcount = 0):** nothing points at the clusters, but the allocator
  has not reused them yet — the data survives until it does.
- **Reallocated:** the clusters were handed to a new allocation and the old content is overwritten.

These same categories drive the deletion-recovery model; the validated survival figures (a transaction-
gap study on a 2 GiB volume) are canonical on the [Deletion Recovery](deletion_recovery.md) page rather
than duplicated here. On 24H2-era volumes a recovered cluster may also sit inside a
compacted/compressed container and need the [compression](compression.md) header-decode path before it
is plaintext.

### Stale rows inside live pages

CoW also propagates *intra-page* slack. When a row is removed from a B+-tree node, ReFS updates only the
key index — the row body is left in place in the node's data area. A later CoW copy of that page can then
carry the stale row forward into a new generation. The artifact to target is therefore a **stale row
body inside a live or superseded page**, not the fixed-size record tail an NTFS analyst expects from MFT
slack. See [Directory Entries](../structures/directory_entries.md) for the row/key-index layout this
exploits.

### Stream snapshots (explicit, refcount-protected history)

ReFS stream snapshots ([$SNAPSHOT](../attributes/SNAPSHOT.md)) are the *directly recoverable*
application of CoW: taking a snapshot freezes the file's current extents under a new stream sub-id, and
later writes allocate fresh clusters, so the snapshotted clusters are kept alive by their refcount and
the prior file content can be reconstructed in full — exactly, byte-for-byte — from a single image.
Unlike a scan for dereferenced pages, the chain here is explicit and refcount-protected. The full
recovery walk-through (the `$SNAPSHOT` → `$DATA` sub-id mapping, extent decode, and version history) is
canonical on [Stream Snapshots and File Versioning](snapshots_versioning.md), built on the
`RefsCreateStreamSnapshot` / `GetResidentStreamSummaryFromDisk` / `SetResidentStreamSummary` driver
path.

## The checkpoint-comparison limit

A natural idea — diff the two on-disk checkpoint copies to recover a prior whole-tree state — does **not**
work on a cleanly unmounted volume. After a clean unmount both CHKP copies decode to the *same* root-
table pointer list; only the virtual clock and per-page checksums differ. This holds even on a
corrupted-but-remountable volume and on heavily-modified volumes: the alternate checkpoint never carries
an older tree. Note also that comparing the *raw* CHKP bytes is misleading — the per-write clock and
checksum always differ — so a comparison must **decode** and compare the root page-references, not the
bytes. Seeing two genuinely different trees requires a **mid-transaction crash capture**, where one
checkpoint was written and the other was not. On a clean image the recoverable prior states therefore
come from stream snapshots and superseded/dereferenced pages, never from the alternate checkpoint.

## Comparison with NTFS

| Aspect | NTFS | ReFS |
|--------|------|------|
| Update model | In-place write | Copy-on-write |
| Recovery journal | Redo + undo | Redo only |
| Previous states | Read backward from `$LogFile` | Scan for dereferenced CoW pages |
| Slack space | Fixed-size MFT record tail | Stale rows in B+-tree pages |

Both file systems support the same forensic goal — reconstructing what existed before a change — but
through completely different on-disk artifacts. See [NTFS vs ReFS](ntfs_comparison.md) for the broader
contrast.

## Cross-references

- [Transactions and Crash Consistency](transactions_crash_consistency.md) — the two-pass, redo-only
  recovery that CoW makes possible
- [MLog](../structures/mlog.md) — the redo-only log; it needs no undo records *because* of CoW
- [Checkpoint (CHKP)](../structures/chkp.md) — the atomic checkpoint write is the CoW commit point
- [Page Header](../structures/page_header.md) — the `"MSB+"` signature used to scan for superseded pages
- [Allocators](../structures/allocators.md) — `CmsAllocator::AllocateLcns` supplies the new clusters and
  decides when old pages are reclaimed
- [Block Refcount Table](../structures/block_refcount.md) — refcount ≥ 2 is the "guaranteed survival"
  category for shared clusters
- [Virtual Addressing](virtual_addressing.md) — the indirection that lets CoW relocate data without
  rewriting per-file extents
- [Stream Snapshots and File Versioning](snapshots_versioning.md) — canonical for the explicit
  snapshot recovery chain
- [Deletion Recovery](deletion_recovery.md) — canonical for the recovery categories and validated
  survival figures
- [Compression](compression.md) — a recovered cluster in a compacted container needs header-decode first
- [NTFS vs ReFS](ntfs_comparison.md) — the in-place vs copy-on-write contrast

## Evidence

The allocate-new / never-overwrite / propagate-to-root path is confirmed in the driver (E2): CoW
propagation is visible in `MsUpdateDataWithRoot` → `CmsBPlusTable::UpdateDataWithRoot` and the
`CmsCowRootComposite` re-rooting class, with the change recorded through
`CmsTransactionContext::AddRedoRecord` (and an `AllocateUndo` slot) so the commit writes new pages while
the old pages stay reachable; new clusters come from `CmsAllocator::AllocateLcns` (finding GN_ARCH_002,
CONFIRMED). The redo-only recovery model — no undo pass, undo unnecessary because old pages are intact —
is confirmed by the two-pass restarter across the corpus (AP_LGFL_005, E2). The superseded-page survival
categories and the checkpoint-comparison limit are raw-disk decoded (RD): both CHKP copies always decode
to identical root-pointer lists on cleanly-unmounted and corrupted-but-remountable volumes, and the
refcount-≥2 / unreferenced / reallocated split is measured on real images. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
