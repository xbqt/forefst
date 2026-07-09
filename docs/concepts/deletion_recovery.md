# Deletion Recovery

When a file is deleted on ReFS, the question for an analyst is not *whether* an entry was scrubbed in
place — ReFS rarely overwrites anything — but *where the prior bytes still live and for how long*.
Because [copy-on-write](copy_on_write.md) writes new data to new clusters and deletion is deferred to a
background cleaner, a deleted file's metadata and content frequently survive somewhere on the volume long
after the file vanishes from its directory. This page lays out the five recovery paths, what each one can
reach, and the survival rules that decide whether the bytes are still there. The strongest exact-content
path is **Method 4 (stream snapshots)**, which reconstructs prior bytes deterministically; the deepest
metadata path is **Method 5 (B+-tree node slack)**, which recovers deleted directory-entry names and
inline `$SI` that no other method can reach.

## How deletion actually works

ReFS does not erase a deleted file synchronously. The cleanup path
(`RefsCommonCleanup` → `RefsDeleteFile` / `DeleteFileOnDisk`, and `DeleteDirectoryOnDisk` for
directories) removes the directory row with `MsDeleteRow` and **reparents the object to the
[Trash Table](../structures/trash_table.md)** (OID 0x0D, schema 0xe0d0) via `MsReparentFileToTrash` and
`CmsTrashTable::AddFileTable`. A background work item, `TrashCleanerWorkItemMethod`, later calls
`DeleteFileTable` to free the data extents. Two consequences follow directly, and both are recoverable:
the object lingers in the Trash Table until the cleaner runs, and — because the directory row is *removed
from the offset array* rather than scrubbed — its body survives in page slack. Each of the five methods
below exploits one of the seams this leaves behind.

## Method 1 — Trash Table recovery

The [Trash Table](../structures/trash_table.md) is the deferred-deletion queue: any object reparented
here is a file (or directory) whose metadata and data have **not yet been reclaimed**. Reading OID 0x0D
through the [Object Table](../structures/object_table.md) and enumerating its rows therefore yields
recently deleted objects in their entirety, before the background cleaner has freed anything. On a cleanly
maintained volume the Trash Table is usually empty — the cleaner runs promptly — so this method captures
the *narrow* window between deletion and reclamation rather than the long tail; for older deletions, fall
through to Methods 3–5.

## Method 2 — Checkpoint differential

The volume keeps two [checkpoint](../structures/chkp.md) copies, each pointing at a set of root tables.
The idea is to compare the [Object Table](../structures/object_table.md) reachable from the current
checkpoint against the one reachable from the previous checkpoint: an object present in the old set but
absent from the new set was deleted between them. The catch is structural. **After a clean unmount both
checkpoint copies decode to the same 13-root pointer list** — they reference identical root tables, so the
differential is empty. This holds across the entire corpus, including corrupted and busy images. A genuine
mid-transaction crash capture, where one checkpoint was written and the other was not, is required for the
two trees to differ. One discipline matters here: compare the **decoded** root page-references, not the
raw checkpoint bytes — the per-write virtual clock and self-checksum always differ even when the trees are
identical, so a byte comparison is misleading. (This limit is canonical on
[Copy-on-Write § the checkpoint-comparison limit](copy_on_write.md).)

## Method 3 — Orphan object scan

This is the broadest method and the only one that works on a cleanly unmounted volume without snapshots.
Carve the whole image for `MSB+` page signatures, then read each page's table OID from the
[page header](../structures/page_header.md): offset **0x48** holds `TableIdLow` (the numeric OID the
driver compares), and offset 0x40 holds `TableIdHigh`, which is always 0. Any OID found inside a B+-tree
page but **not** present in the current Object Table is an **orphan** — a candidate deleted file whose old
page has not yet been overwritten. The reach of this method is bounded by reallocation: it depends entirely
on the allocator not having reused the old page, which is why volume activity and free space (below) drive
its success rate. It only ever follows a page's *live* offset array, so it cannot see rows that were
deleted *within* a still-live page — that is Method 5's job.

## Method 4 — Stream snapshot recovery

This is the strongest and most deterministic single-image path, because it does not rely on un-reallocated
pages at all. If a file carries [stream snapshots](../attributes/SNAPSHOT.md) (`$SNAPSHOT`, type 0xB0),
each snapshotted prior version's **exact bytes** can be reconstructed from the same image. Taking a
snapshot freezes the file's current extents under a new stream sub-id; subsequent writes allocate fresh
clusters via copy-on-write, and the snapshotted clusters stay alive because their refcount in the
[Block Refcount table](../structures/block_refcount.md) is `>= 2`. The recovery chain is explicit:

> `$SNAPSHOT val[0x44]` (`data_sub_id`, 0x1001+) → matching `$DATA` sub-record (`key+0x10 == data_sub_id`)
> → 24-byte extent entries → sort by `file_vcn` → translate VLCN → PLCN via the
> [Container Table](../structures/container_table.md) → read → trim to stream size.

The full walk-through — the embedded sub-record headers, the extent decode, and how multiple snapshots
reconstruct an ordered version history — is canonical on
[Stream Snapshots and File Versioning](snapshots_versioning.md). Recovery here has been verified
byte-for-byte (MD5-identical) on chains up to **21 extents / 13.4 MB**, and is implemented as
`forefst.py <image> snapshots --show` (preview) / `--extract DIR` (write the recovered versions).

> **Scoping caveat.** ReFS *file-level* stream snapshots (`$SNAPSHOT`, type 0xB0) are a different thing
> from VM/disk snapshots. A volume whose history came from a hypervisor or disk-level snapshot step
> contains **no** ReFS stream snapshots, and this method finds nothing there; it applies only to files that
> actually carry a `$SNAPSHOT` sub-record.

## Method 5 — B+-tree node slack recovery

ReFS deletion (`CmsBPlusTable::DeleteFromIndex`) removes only the deleted row's entry in the page's
**offset array** and queues *delayed* compaction — **the row body is not scrubbed**. So a deleted directory
entry's filename and its inline `$SI` ([MACB timestamps](../concepts/timestomp_detection.md), attributes)
survive in the **node slack**: the page bytes no longer referenced by the live offset array, until a later
copy-on-write rewrite reuses the space. This is reachable by **no other method** — the orphan scan
(Method 3) follows only a page's *live* offset array and never sees these rows.

The procedure walks every live and orphan `MSB+` leaf page for type-0x30 row headers
([directory-entry keys](../structures/directory_entries.md): `key_off == 0x10`, key type 0x30, in-bounds,
decodable UTF-16 name) that are **not** in the live offset array; it decodes the name + MACB + attributes
and **grades by confidence** — high when both MACB timestamps are plausible FILETIMEs, partial when the
name is a fragment from a row whose body was partly overwritten. It then cross-flags each recovered row as
**deleted** (name absent from the live tree) versus **prior-version** (a copy-on-write remnant of a
still-living file). Implemented as `forefst.py <image> deleted --slack` (`--extract DIR` to write the
recovered rows). On the clean baseline it produced **0 false positives** — every recovered name was
genuinely absent from the live tree — with roughly 70% high-confidence and the partials flagged.

> **Caveat.** Slack recovery is **image-dependent**: it finds only what survives in un-rewritten slack. A
> heavily rewritten or freshly compacted page may retain nothing, so a single recovered row should always
> be corroborated (timestamps, surrounding rows) before it is relied on.

## What decides whether the bytes survive

For Methods 3–5 the bytes are present only if the allocator has not reused the clusters, so survival is a
race between deletion and reuse. Three conditions tilt that race, and a fourth removes it entirely:

| Factor | Effect on survival |
|--------|--------------------|
| Volume activity | Low activity → more old pages survive un-reallocated |
| Time since deletion | Less elapsed time → less chance of reuse |
| Volume free space | More free space → the allocator reuses old clusters more slowly |
| Refcount `>= 2` | **Guaranteed** survival — the clusters are still referenced (CoW-protected) |

The refcount case is categorical rather than probabilistic. A cluster range with refcount `>= 2` in the
[Block Refcount table](../structures/block_refcount.md) is shared — both a snapshot and the live version,
or two checkpoints, still reference it — so the allocator cannot reclaim it. This is what makes Method 4
deterministic. The three recovery categories follow:

| Category | Condition | Outcome |
|----------|-----------|---------|
| CoW-protected | Refcount `>= 2` | **Guaranteed** survival — both references keep the clusters alive |
| Unreferenced, not reallocated | Refcount `= 0`, clusters free | Data survives until the allocator reuses the clusters |
| Reallocated | Clusters reused | Data **overwritten** — not recoverable |

A gap-analysis run on one modestly active 2 GiB volume illustrates the shape of this — the fractions
below are a single-volume snapshot (small denominators), not general survival rates. Across a window of
266 transactions, of the non-resident files that had been modified, **about half still had their old
data fully intact**, roughly **6%** of old clusters were refcount-protected (and so guaranteed), and
about **62%** of old metadata pages remained valid:

| Metric | Value |
|--------|-------|
| Modified user objects | 39 |
| Modified system objects | 7 |
| Non-resident files analysed | 18 |
| Files with old data fully intact | 9/18 (50%) |
| Old clusters with refcount `>= 2` (CoW-protected) | 76/1,181 (6.4%) |
| Old metadata pages still valid | 13/21 (61.9%) |

## Deletion leaves a permanent fingerprint in the OID sequence

Independent of whether any content survives, deletion leaves a permanent record in the object-id space.
[Object IDs](object_ids_fileids.md) are 64-bit, monotonically increasing, and **never reused after
deletion** (user OIDs start at 0x701, set by `MsSetMinimumNewObjectId`; see
[OID Allocation](oid_allocation.md)). A **gap in the OID sequence is therefore permanent evidence of a past
deletion** — if 0x720, 0x721, and 0x723 exist but 0x722 does not, a file was created and deleted, and no
later activity can hide that. **OID density** (present OIDs ÷ range) quantifies the deletion history of a
volume: a freshly formatted volume is essentially 100% dense, while a worked volume falls to roughly
55–79%. This is one of the clearest forensic advantages ReFS has over NTFS, whose MFT records *are* reused
and so erase their own deletion evidence over time — see [NTFS vs ReFS](ntfs_comparison.md) for the full
contrast.

## Cross-references

- [Copy-on-Write](copy_on_write.md) — the update model that makes recovery possible; canonical for the CoW-vs-NTFS update-model contrast and the checkpoint-comparison limit
- [Stream Snapshots and File Versioning](snapshots_versioning.md) — the full Method 4 recovery walk-through
- [Stream Snapshots ($SNAPSHOT)](../attributes/SNAPSHOT.md) — the on-disk sub-record Method 4 reads
- [Trash Table](../structures/trash_table.md) — Method 1, the deferred-deletion queue (OID 0x0D)
- [Object Table](../structures/object_table.md) — Method 3 orphan detection works against the live OID set
- [System OIDs](../structures/system_oids.md) — OID 0x0D is the Trash Table
- [Block Refcount table](../structures/block_refcount.md) — refcount `>= 2` is the "guaranteed survival" rule
- [Object IDs and File IDs](object_ids_fileids.md) · [OID Allocation](oid_allocation.md) — why OID gaps are permanent deletion evidence
- [What Survives](what_survives.md) — the broader inventory of recoverable artifacts on a ReFS volume
- [NTFS vs ReFS](ntfs_comparison.md) — OID-gap evidence vs reusable MFT records; log-wrap vs CoW recovery windows
- [MLog](../structures/mlog.md) — redo-only logging carries no pre-images, so it is not a direct prior-state source

## Evidence

The deletion flow — `RefsDeleteFile` / `DeleteFileOnDisk` → `MsDeleteRow` →
`MsReparentFileToTrash` → `CmsTrashTable::AddFileTable` (OID 0x0D) → background
`TrashCleanerWorkItemMethod` → `DeleteFileTable` — is confirmed in the decompiled driver (E2); the Trash
Table OID 0x0D / schema 0xe0d0 and its empty-on-clean-volume state are also raw-disk verified (RD). The
page-header OID at offset 0x48 (`TableIdLow`) with offset 0x40 always 0 is RD-verified.
The checkpoint differential decoding to identical 13-root pointer lists across the corpus is RD
(finding **FS_CHKP_RA_014**). Method 5 — `CmsBPlusTable::DeleteFromIndex` removing only the offset-array entry and
leaving the row body in slack — is E2 for the deletion mechanism and RD for the recovery (0 false positives
on the baseline; finding **FS_DEL_RA_005**). The survival metrics and recovery categories are RD on a 266-transaction
gap analysis. OID monotonicity, no-reuse, and the 55–79% worked-volume density are RD. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
