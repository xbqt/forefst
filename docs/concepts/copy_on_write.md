# Copy-on-Write (CoW)

Copy-on-write is the rule that makes ReFS recoverable: **no B+-tree page is ever overwritten in place.** A changed
page is written to newly allocated clusters, and the change of address propagates up the B+-tree to a new root, so
the page as it was before the change stays on disk until its clusters are allocated again.

A few fixed structures are the exception: the superblock copies and the two checkpoint slots sit at fixed addresses
and are rewritten there (each checkpoint write goes to the older of the two slots), and the log's data area is reused
as a ring.

For a forensic analyst, almost every single-image recovery path on ReFS depends on this:

- superseded pages;
- stream snapshots;
- clusters a snapshot or a clone still references.

It is also why the ReFS log needs no undo records, unlike the NTFS `$LogFile`.

This page explains the update mechanism, why it produces the artifacts it does, and what each artifact can recover in
practice.

## How a CoW update propagates

A change is applied to the page in memory; the changed page is then written to newly allocated clusters, never over
its old copy, and the checkpoint makes the new tree current. The sequence is:

1. The modified **leaf node** is written to a **newly allocated** location — the clusters come from the
   [allocators](../structures/allocators.md) via `CmsAllocator::AllocateLcns`.
2. The parent node has to point at the new leaf, but the parent is itself immutable — so a **new copy of
   the parent** is written, with the updated child [page reference](../structures/page_references.md).
3. Propagation continues up the B+-tree: every node on the path from the leaf to the root is re-copied.
4. A table's new **root** is recorded in its [Object Table](../structures/object_table.md) row, and that change
   propagates up the Object Table to its own root. The [checkpoint (CHKP)](../structures/chkp.md) records the roots
   of the global tables, and is written over the older of the two checkpoint slots.
5. The checkpoint write is the **commit point**: it makes the new tree the one a mount starts from. Until it is written,
   the previous checkpoint's tree is the one on disk, and the next mount replays onto it the transactions the log
   recorded after that checkpoint.
6. The **old pages persist** on disk until the allocator reuses their clusters.

In the driver (read on 26100.8115), the new clusters are taken when a changed page is pinned for writing:
`CmsVolume::Pin` calls `AllocateLcnForPage`, which calls `CmsAllocator::AllocateLcns`. A table's new root is pinned
the same way, and `CmsCowRootComposite::CreateNewRoot` reserves the Object Table update that records it.

`MsUpdateDataWithRoot`, which dispatches into `CmsBPlusTable::UpdateDataWithRoot`, is one of the operations that
change a page, not the propagation itself. File creation writes the new file's `$STANDARD_INFORMATION` through it
(`RefsFsdCreate` → … → `MsUpdateDataWithRoot`); like every change, the pages it changes are written to new locations.

[Virtual addressing](virtual_addressing.md) is a separate mechanism: it lets ReFS move a whole container by changing
its Container Table row, without touching any extent table.

## Why this produces redo-only recovery

Copy-on-write makes **undo records on disk unnecessary**, and this changes what an examiner can find on disk.
Consider a crash partway through a transaction:

- The old, pre-transaction pages are still intact — nothing overwrote them.
- The on-disk checkpoint still points at those old pages.
- The volume is therefore *already* in a consistent state; there is nothing to roll back.

Because there is nothing to undo, the [MLog](../structures/mlog.md) records only **redo** operations.
The NTFS `$LogFile`, by contrast, must store both redo *and* undo records,
because NTFS overwrites in place and must be able to reverse a half-applied change. The
[transaction and crash-consistency](transactions_crash_consistency.md) model formalizes this as a
two-pass recovery (analyze, then redo) with no undo pass.

Undo exists in memory only. `CmsBPlusTable::UpdateDataWithRoot` changes the pinned page in memory:

- it logs a redo record (for a table that is logged);
- it saves the old bytes in an undo record allocated in memory, so that an aborted transaction can be rolled back;
- it then copies the new bytes into the page.

If the undo record or the redo record cannot be obtained, it returns an error before it copies the new bytes, so the
page in memory is unchanged. Copy-on-write happens when that page is written: it goes to new clusters.

The reason recovery can be redo-only is therefore on disk: a changed page is written to new clusters, so the last
checkpoint's tree is still intact after a crash, and recovery only has to replay forward.

```c
// MsUpdateDataWithRoot (refs.sys 26100.8115) — thin dispatcher into the virtual table method
void MsUpdateDataWithRoot(CmsTransactionContext *param_1, CmsBPlusTable *param_2, ...)
{
    if (*(code **)(*(longlong *)param_2 + 0x10) == CmsBPlusTable::UpdateDataWithRoot)
        CmsBPlusTable::UpdateDataWithRoot(param_2,param_1,param_3,param_4,param_5,param_6);
    else
        (**(code **)(*(longlong *)param_2 + 0x10))(param_2);
}
```

```c
// CmsBPlusTable::UpdateDataWithRoot (refs.sys 26100.8115, excerpt)
pSVar4 = AllocateUndo(this,param_1,0xc,uVar7,param_3,param_4, ...);   // undo record, in memory
if (pSVar4 == 0) { lVar3 = -0x3fffff66; goto LAB_exit; }             // no undo record: return, page unchanged
lVar3 = CmsTransactionContext::AddRedoRecord(param_1,this,4, ...);    // redo record (skipped for an unlogged table)
FormatUndoRecord(this,param_1,pSVar4,0,pvVar9,param_3,param_4);       // the undo record keeps the old bytes
memcpy(pvVar9 + param_4,param_2,param_3);                             // the new bytes go into the pinned page
```

## What CoW leaves on disk

After a copy-on-write update, the pages on the changed path exist twice: the new copies, which the current tree
references, and the old ones, which it no longer references. Unchanged subtrees are shared by the old and the new
tree. The older of the two checkpoints can still point at the old pages until its slot is next written.

The old copies are intact byte for byte; the only change is that the current tree no longer references them.

On a lightly-used volume these unreferenced layers accumulate and several generations of past file-system state can
coexist. On a busy volume old clusters are likely to be reused sooner (not measured).

### Superseded pages

Because old pages are not zeroed, a signature scan for the `"MSB+"` B+-tree marker in the
[page header](../structures/page_header.md) across a raw image can surface historical metadata that the
live tree no longer points at. An old page is usable while its clusters have not been allocated again.

For file-data clusters, the survival states are:

- **Still referenced:** a live map still names the clusters — a stream snapshot's extents, or a clone or a
  deduplicated file sharing them — so the allocator does not reclaim them while that map lives. The
  [Block Refcount table](../structures/block_refcount.md) counts only the clone and deduplication references
  beyond the first: a snapshot or a hard link adds no count, so the table does not show this category.
- **Freed, not yet reallocated:** nothing references the clusters, but the allocator has not reused them
  yet — the data survives until it does.
- **Reallocated:** the clusters were handed to a new allocation and the old content is overwritten.

The deletion-recovery model uses the same states; the survival figures measured on one 2 GiB volume are on the
[Deletion Recovery](deletion_recovery.md) page rather than duplicated here.

On a volume where compression is enabled, a recovered cluster may sit in a compressed container and need the
[compression](compression.md) header decode before it is plaintext. A compacted container, compressed or not, is
found through the Container Index, not mapped directly. None of the volumes measured holds either kind.

### Stale rows inside live pages

CoW also propagates *intra-page* slack. When a row is removed from a B+-tree node, ReFS updates only the
key index — the row body is left in place in the node's data area. A later CoW copy of that page can then
carry the stale row forward into a new generation. The artifact to target is therefore a **stale row
body inside a live or superseded page**, not the fixed-size record tail an NTFS analyst expects from MFT
slack.

See [B+-Tree Node](../structures/btree_node.md) for the key index and
[Directory Entries](../structures/directory_entries.md) for the row header.

### Stream snapshots (explicit history)

ReFS stream snapshots ([$SNAPSHOT](../attributes/SNAPSHOT.md)) are the *directly recoverable*
application of CoW: taking a snapshot freezes the file's current extents under a new stream sub-id, and
later writes allocate fresh clusters, so the snapshotted clusters stay named by the snapshot's own extent map.

The prior content of a file that still exists can be reconstructed byte-for-byte from a single image, by resolving
each block across the versions. Two limits:

- a deleted file's snapshots are removed with it;
- a snapshot taken while a file was inline did not survive the file's rewrite past 2 KiB in the one case seen (a
  v3.14 volume).

Unlike a scan for dereferenced pages, the chain here is explicit. The full
recovery walk-through (the `$SNAPSHOT` → `$DATA` sub-id mapping, extent decode, and version history) is
canonical on [Stream Snapshots and File Versioning](snapshots_versioning.md), built on the
`RefsCreateStreamSnapshot` / `GetResidentStreamSummaryFromDisk` / `SetResidentStreamSummary` driver
path.

## The checkpoint-comparison limit

Comparing the two on-disk checkpoint copies to recover a prior whole-tree state usually finds **nothing** on a
cleanly unmounted volume. The two CHKP copies usually decode to the *same* root-table pointer list:
on the images measured (clean, corrupted-but-remountable, busy and pre-salvage volumes) and on all but one of the
volumes of the blind audit (on that ReFS 3.4 volume five of the 13 roots differ).

Comparing the *raw* CHKP bytes is misleading all the same. Even when their trees are identical, the copies differ in
a few bytes:

- the copy's own LCN (+0x20) and its self-descriptor's LCN;
- the checksum;
- the allocator clock (+0x68), on every pair byte-compared;
- usually the checkpoint clock (+0x10, +0x60) — two valid copies can carry the same clock.

So a comparison must **decode** and compare the root page-references, not the bytes.

Seeing two different trees needs a capture between two checkpoint writes that changed a root table. On a cleanly
closed image the prior states therefore come from stream snapshots and superseded pages; still compare the two
checkpoints, because on an image that was not cleanly closed the older one can carry a prior tree.

The same holds between two **images** of one volume: a comparison of images is a comparison of their checkpoints.
`files --cow-before` compares two images object by object. On a series of captures of one test volume, taken after
steps that each changed files, it found no difference between any two: every capture was read from the same
checkpoint, so the changes were not yet in any checkpoint (their records may be in the log: `mlog`).

`files --cow-before` says so when both images are read from a checkpoint with the same virtual clock. Compare the two
images' checkpoint clocks (`fastsummary --json`, `CheckpointVirtualClock`) before reading an empty comparison as
"nothing changed".

## Comparison with NTFS

| Aspect | NTFS | ReFS |
|--------|------|------|
| Update model | In-place write | Copy-on-write |
| Recovery journal | Redo + undo | Redo only |
| Previous states | Read backward from `$LogFile` | Stream snapshots; superseded pages found by an MSB+ scan; the older checkpoint when it differs; the values earlier MLog records wrote, while the log keeps them |
| Slack space | Fixed-size MFT record tail | Stale rows in B+-tree pages |

Both file systems support the same forensic goal — reconstructing what existed before a change — but their metadata
artifacts differ: NTFS overwrites in place and keeps undo information in `$LogFile`; ReFS leaves superseded pages
behind. The change journal (`$UsnJrnl:$J`) exists on both.

See [NTFS vs ReFS](ntfs_comparison.md) for the broader
contrast.

## Cross-references

- [Driver Evolution](driver_evolution.md) — taking a stream snapshot is one of the residency triggers

- [Transactions and Crash Consistency](transactions_crash_consistency.md) — the two-pass, redo-only
  recovery that CoW makes possible
- [MLog](../structures/mlog.md) — the redo-only log; it needs no undo records *because* of CoW
- [Checkpoint (CHKP)](../structures/chkp.md) — the atomic checkpoint write is the CoW commit point
- [Page Header](../structures/page_header.md) — the `"MSB+"` signature used to scan for superseded pages
- [Allocators](../structures/allocators.md) — `CmsAllocator::AllocateLcns` supplies the new clusters; freed
  clusters are handed out again from the allocator's bitmap
- [Block Refcount Table](../structures/block_refcount.md) — the clone and deduplication counts; a snapshot's
  sharing is not counted there
- [Virtual Addressing](virtual_addressing.md) — the indirection that lets ReFS move a whole container without
  rewriting per-file extents
- [Stream Snapshots and File Versioning](snapshots_versioning.md) — canonical for the explicit
  snapshot recovery chain
- [Deletion Recovery](deletion_recovery.md) — the recovery methods and the survival figures measured on one volume
- [Compression](compression.md) — a recovered cluster in a compressed container needs the header decode first
- [NTFS vs ReFS](ntfs_comparison.md) — the in-place vs copy-on-write contrast

## Evidence

The allocate-new step is in the driver (refs.sys 26100.8115): a page pinned for writing gets new clusters
(`CmsVolume::Pin` → `AllocateLcnForPage` → `CmsAllocator::AllocateLcns`), and a table's new root is pinned the same
way and recorded through an Object Table update (`CmsCowRootComposite::CreateNewRoot`).
`CmsBPlusTable::UpdateDataWithRoot` logs a redo record, keeps the old bytes in an undo record allocated in memory
(`AllocateUndo`, `FormatUndoRecord`) and then copies the new bytes into the pinned page. The file-create chain to
`MsUpdateDataWithRoot` was read on 17134.

The redo-only recovery model is confirmed in the driver: the restarter has an analysis pass and a redo pass and no
undo pass (read on 17134, 26100.8115 to .9444 and Insider 29574). The survival states and the checkpoint-comparison
limit were read on disk, on the volumes described above.

The counts behind the text:

- the two checkpoint copies decode to the same root list on 25 of the 26 volumes of the first blind audit;
- the raw-byte differences between the copies, 11 to 15 bytes, were measured on 18 volumes (the allocator clock
  differs by exactly 1 on all 18); the natural clock tie is on one "millions of actions" volume;
- the `files --cow-before` series is 23 captures of one test volume, all read from checkpoint virtual clock 46 (the
  other copy holds 45).

See [how this was verified](../methodology.md) for the method.

<!-- findings: AP_LGFL_005, GN_ARCH_002, GN_FOPS_SA_002 -->
