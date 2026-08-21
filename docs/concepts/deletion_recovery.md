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
directories) removes the directory row with `MsDeleteRow`. For a **non-resident file or a directory** it then
**reparents the object to the [Trash Table](../structures/trash_table.md)** (OID 0x0D, schema 0xe0d0) via
`MsReparentFileToTrash` and `CmsTrashTable::AddFileTable`; a background work item, `TrashCleanerWorkItemMethod`,
later calls `DeleteFileTable` to free the data extents. A **resident (inline) file bypasses the Trash entirely**
— it is removed in a single transaction by `RefsDeleteResidentDataScbAndCommit`, so the Trash queue only ever
holds non-resident files and directories. Two consequences follow directly, and both are recoverable: a
reparented object lingers in the Trash Table until the cleaner runs, and — because the directory row is *removed
from the offset array* rather than scrubbed — its body survives in page slack. Each of the methods below exploits
one of the seams this leaves behind.

## Two modes, and how the methods map to them

The `deleted` command runs these methods behind **two simple modes**, so an analyst chooses a depth rather than
juggling individual scans:

- **`deleted`** — *recovery* (the default, quick). Runs the Trash table, the checkpoint differential, and the
  B+-tree node-slack scan over the **live pages only** (the pages the tree walk already reads). It recovers the
  common in-tree deletions in seconds.
- **`deleted --full`** — *complete*. Everything in recovery, plus a bounded full-volume scan of **orphan pages**
  (the freed pages of deleted objects), and it carves non-resident extent-backed content on export.

Fine-grained flags still override the presets for power users: `--no-slack` (fast Trash+checkpoint pass),
`--trash` (Trash only), `--scan-pages`, `--orphans` (a low-confidence Object-Table-orphan tier), `--carve`,
`--max-scan N`, `--search SUB`. Each mode prints a one-line pointer to the other. Two related paths live in their
own commands: **stream snapshots** (`snapshots`, Method 4 below) and the **Windows Recycle Bin** (`recyclebin`).

| Method | What it reads | Mode | Recovers |
|--------|---------------|------|----------|
| 1 — Trash table | OID 0x0D queue | recovery | Whole non-resident files/dirs not yet reclaimed |
| 2 — Checkpoint differential | two checkpoints' Object Tables | recovery | OIDs deleted in the last transaction batch (empty after clean unmount) |
| 3 — Orphan-object scan | OID Table ∖ tree | `--orphans` (opt-in) | Object-Table directory OIDs unlinked from the tree — low confidence |
| 5 — B+-tree node slack | metadata-page free space | recovery (live pages) / `--full` (+ orphan pages) | Deleted names, inline `$SI`, and carve-able non-resident extent maps — **the primary method** |
| 4 — Stream snapshots | `$SNAPSHOT` (type 0xB0) | `snapshots` command | **Exact prior bytes** of files that still exist |

Every method classifies its results by **file identity**, and an **export writes a recovery log** — both covered
below.

## Method 1 — Trash Table recovery

The [Trash Table](../structures/trash_table.md) is the deferred-deletion queue: any object reparented
here is a **non-resident file or a directory** whose metadata and data have **not yet been reclaimed**
(resident files never appear — they bypass the Trash, as above). Reading OID 0x0D
through the [Object Table](../structures/object_table.md) and enumerating its rows therefore yields
recently deleted objects in their entirety, before the background cleaner has freed anything. On a cleanly
maintained volume the Trash Table is usually empty — the cleaner runs promptly — so this method captures
the *narrow* window between deletion and reclamation rather than the long tail; for older deletions, fall
through to the slack scan (Method 5).

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

## Method 3 — Orphan-object scan (opt-in, low confidence)

Enabled with `deleted --orphans`. It reads the [Object Table](../structures/object_table.md) and lists every
OID that is still present there but **unreachable from the directory tree** — an object whose Object-Table entry
survives after its tree link was removed, before garbage collection reclaims it. Because an object carries its
own OID only if it is a **directory**, these orphans are deleted directory OIDs (labelled `DIR_OID_0x<oid>`,
with any recoverable child name shown as a note). The scan is **identity-filtered**: an orphan whose recovered
child is still live somewhere is dropped, so a live file is never mislabelled deleted. It is a **low-volume,
low-confidence** signal — usually a handful of OIDs, often with no child name surviving — kept as a complementary
lead. Genuine deleted directories generally recover more fully through the slack scan (Method 5), which reads the
row *bodies* the orphan scan never sees. (Distinct from the **orphan-*page*** scan that `--full` adds to Method 5:
that reads freed metadata *pages*; this reads unreferenced Object-Table *OIDs*.)

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
name is a fragment from a row whose body was partly overwritten. It records which directory each row was
**deleted from** — the owning table OID at page offset `0x48` ([page header](../structures/page_header.md)
`TableIdLow`). Implemented as `forefst.py <image> deleted`: *recovery* mode scans the **live pages** (quick);
`deleted --full` also scans **orphan pages** (the freed pages of deleted objects) for older deletions. Add
`--no-slack` for a fast Trash+checkpoint pass. **`export deleted DIR`** writes a **`deleted_files.csv`/`.json`
index** — one row per deleted entry (name, recoverability, reliability, category, and its content file if any) —
plus a **`content/`** folder holding only the *readable* recoveries: `content/<name>` for a resident file
(byte-exact) and, under `--full`/`--carve`, `content/<name>.carved` for a non-resident file (best-effort — the
clusters may have been reused, so verify). A `recovery_log.txt` audit trail is written too. The raw remnant bytes
go to `rows/` only with `--rows`; `--no-system` hides the BitLocker `FVE2.{…}` churn that otherwise dominates a
volume's deleted list.

**Deleted vs still-present — decided by file identity `(name, creation-time)`.** Each recovered row is either a
genuine deletion or a copy-on-write remnant of a file that still exists. A remnant is **deleted** only when **no
live file with the same name *and* creation-time exists anywhere on the volume**; otherwise it is **still
present**. Creation-time is the discriminator that makes this robust: it is immutable across a move or rename, so
it separates *the same file relocated* from *a different file that merely reuses the name* (two unrelated
`Shield.png` in different directories have different creation-times and are judged independently). A
copy-then-delete-original is correctly recoverable — the copy has a new creation-time, so the deleted original's
identity is live nowhere.

**Moved and renamed files are surfaced neutrally.** When a live file with the remnant's identity exists but sits
in a **different directory** than the remnant, that remnant is the file's **former location** — flagged
`[former location — the live file is in a different directory]`. The tool does not assert *which* operation
occurred (move, rename, or copy); it states the fact and leaves the interpretation to the analyst.

**Recover once, log every location.** Identical files deleted from several directories are recovered **once**
(de-duplicated by name + creation-time + type), but the **recovery log records every directory** the identity
was deleted from — so a component-store file wiped from a dozen places yields one recovered file and a complete
list of where it lived.

**Non-resident content is carve-able from slack too.** A deleted non-resident file keeps its data in
separate on-disk extents, and its **extent map lives in a type-0x40 backing record** that is unlinked from
the live tree at deletion — but whose body **survives in the same page slack** as the name row. The scan
recovers that backing, matches it to the name row by `(file_id, home-dir)` + exact size, and reconstructs
the file from those clusters (`export deleted --carve`, best-effort — the clusters may have been
reallocated). On older and upgraded volumes the extent map is instead **embedded inside the name row itself**
(a small B+-tree the file carries in place of a separate backing record); the scan decodes that embedded map
the same way and carves those files too, so non-resident deleted content is recoverable on every layout — not
just the newest one. A carve is only written when the extent map forms a complete, in-bounds picture of the
file and at least some of its clusters are still readable; a map that points outside the volume or has been
zeroed yields metadata only, never a corrupt or empty stand-in file.

**Deleted directories are reconstructed as a group.** When a directory is deleted its own page survives in
slack holding its children's rows, but its OID is gone from the tree — so those children are recovered with
an **unresolvable parent**. They are grouped under `$DELETED/DIR_OID_0x<oid>/<child>`, anchored on the one
reliable fact (the physical page they were recovered from). The deleted directory's *name* is offered only
as a **best-effort candidate**, and is explicitly flagged **ambiguous** when rename/move churn left several
conflicting names for the same OID in slack — a named ancestor path is never asserted, because the slack
holds multiple epochs and any single reconstructed name could be a pre-rename artifact.

> **Caveat.** Slack recovery is **image-dependent**: it finds only what survives in un-rewritten slack. A
> heavily rewritten or freshly compacted page may retain nothing, so a single recovered row should always
> be corroborated (timestamps, surrounding rows) before it is relied on. Carved non-resident content is
> best-effort — the extent *map* survived, but the data clusters may have been reused since deletion.

## The recovery log

An **export** writes a **recovery log** — a forensic audit trail of exactly what was recovered and how. The log
is produced only when you export (`export deleted`, `deleted --extract`, `deleted -o FILE`) or ask for one
explicitly with `--log PATH`; a plain `deleted` **view never writes a log file**. When written, it records the
image, the ReFS version, the mode (`recovery` / `--full`), the methods that ran, and the full per-entry split:
the **deleted** files (with each remnant's source page, recoverability verdict, and — for a file deleted from
several directories — every location) and the **still-present** remnants (CoW prior versions and former
locations). The path is chosen automatically — `--log PATH` to override, otherwise `<export-dir>/recovery_log.txt`
alongside an `export deleted`, or a timestamped `forefst_recovery_<image>_<ts>.txt` in the working directory. The
log is the primary record to cite in a report: it captures the classification reasoning (why each remnant was
called deleted or still-present) that the on-screen view summarises.

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
[Object IDs](object_ids.md) are 64-bit, monotonically increasing, and **never reused after
deletion** (user OIDs start at 0x701, set by `MsSetMinimumNewObjectId`; see
[OID Allocation](oid_allocation.md)). A **gap in the OID sequence is therefore permanent evidence of a past
deletion** — if 0x720, 0x721, and 0x723 exist but 0x722 does not, a **directory or system object** was created
and deleted, and no later activity can hide that. (Files carry no OID of their own, so a deleted *file* leaves
no gap — the OID sequence tracks deleted **objects**, i.e. directories and system tables.) **OID density** (present OIDs ÷ range) quantifies the deletion history of a
volume: a freshly formatted volume is essentially 100% dense, while a worked volume falls to roughly
55–79%. This is one of the clearest forensic advantages ReFS has over NTFS, whose MFT records *are* reused
and so erase their own deletion evidence over time — see [NTFS vs ReFS](ntfs_comparison.md) for the full
contrast.

## Additional identity techniques (analysed, not built into the tool)

Two further techniques recover a deletion's **identity and timeline** — never its content — and were validated
on disk but deliberately left out of the `deleted` command. They are documented here so an analyst can apply
them by hand when the case warrants.

### Journal identity — USN `FILE_DELETE` + MLog

The [USN change journal](../structures/usn_journal.md) (`$UsnJrnl:$J`) records a deletion **by name** the moment
it happens: a `FILE_DELETE` (reason `0x200`) record carries the deleted file's name, its parent, and a timestamp
— independently of whether any slack remnant survives. That makes it a genuine cross-check on the slack scan: it
can **confirm** a recovered deletion, supply a **deletion time** the slack `$SI` does not carry, and even
**name** a deletion whose slack row is already gone. Three cautions are load-bearing:

- **The timestamp is a *close* time, not a delete instant.** Every `FILE_DELETE` record observed carries the
  `CLOSE` bit (`0x80000000`) OR-ed in, and often coalesces a file's whole create→delete→close lifecycle into one
  record. So it is best read as "the deleting handle closed at *T*", which can lag the logical delete.
- **The join is by identity, not by File ID.** A slack name row exposes no File ID, and the USN 128-bit File ID's
  low half is a per-directory entry index, not the slack ordinal — so the reliable key is the same
  `(name, creation-time)` identity used everywhere on this page, with a confidence flag when candidates collide.
- **Availability is narrow.** The USN journal is present on only a minority of volumes and on **no** v3.4 volume
  in the reference corpus; where absent, it says nothing (which is not the same as "no deletions"). The redo-only
  [MLog](../structures/mlog.md) (`RedoDeleteRow` / `RedoDeleteTable`, and `RedoReparentTable` for the
  Trash move) is the cross-source that spans *every* version — but it, too, records **identity and metadata
  changes only, never file content**. A deleted name whose type-0x30 row is gone can also be resolved from the
  [type-0x20 FileId index](../structures/reverse_index.md), which holds a second copy of the filename.

### Parent-Child ancestry for deleted directories

The [Parent-Child Table](../structures/parent_child_table.md) (checkpoint root #4) records directory→directory
edges as `(parent OID, child OID)` pairs. When a directory is deleted its edge is actively removed from the live
table — but, exactly like a directory-entry row, the edge's **body survives in the table's page slack** until a
CoW rewrite. Recovering those slack edges yields an **OID-exact ancestry chain** for a deleted directory
(`parent → grandparent → … → root`), which is far more reliable than reconstructing a path from slack *names*:
object IDs are never reused, so an OID edge is unambiguous even when rename/move churn left several conflicting
names for the same directory. On disk this recovered every deleted directory's parent edge on lightly-used
volumes and a decreasing fraction as churn rose (and nothing where the table's own root page had been reclaimed)
— so it is a **best-effort** enhancement to the `$DELETED/DIR_OID_0x<oid>` grouping, to be reported with explicit
coverage, never asserted.

## Cross-references

- [Copy-on-Write](copy_on_write.md) — the update model that makes recovery possible; canonical for the CoW-vs-NTFS update-model contrast and the checkpoint-comparison limit
- [Stream Snapshots and File Versioning](snapshots_versioning.md) — the full Method 4 recovery walk-through
- [Stream Snapshots ($SNAPSHOT)](../attributes/SNAPSHOT.md) — the on-disk sub-record Method 4 reads
- [Trash Table](../structures/trash_table.md) — Method 1, the deferred-deletion queue (OID 0x0D)
- [Object Table](../structures/object_table.md) — Method 3 orphan detection works against the live OID set
- [System OIDs](../structures/system_oids.md) — OID 0x0D is the Trash Table
- [Block Refcount table](../structures/block_refcount.md) — refcount `>= 2` is the "guaranteed survival" rule
- [Object IDs](object_ids.md) · [OID Allocation](oid_allocation.md) — why OID gaps are permanent deletion evidence
- [What Survives](what_survives.md) — the broader inventory of recoverable artifacts on a ReFS volume
- [NTFS vs ReFS](ntfs_comparison.md) — OID-gap evidence vs reusable MFT records; log-wrap vs CoW recovery windows
- [MLog](../structures/mlog.md) — redo-only logging carries no pre-images, so it is not a direct prior-state source
- [USN Change Journal](../structures/usn_journal.md) — records a deletion by name + close-time (journal-identity technique)
- [Parent-Child Table](../structures/parent_child_table.md) — root #4 dir edges; OID-exact ancestry for deleted directories
- [Type-0x20 FileId index](../structures/reverse_index.md) — a second copy of the filename for name-fallback recovery

## Evidence

The deletion flow — `RefsDeleteFile` / `DeleteFileOnDisk` → `MsDeleteRow` →
`MsReparentFileToTrash` → `CmsTrashTable::AddFileTable` (OID 0x0D) → background
`TrashCleanerWorkItemMethod` → `DeleteFileTable` — is confirmed in the decompiled driver (E2), as is the
**resident-file bypass** (`RefsDeleteResidentDataScbAndCommit`, a single transaction that never touches the
Trash). The Trash Table OID 0x0D / schema 0xe0d0 and its empty-on-clean-volume state are also raw-disk verified (RD). The
page-header OID at offset 0x48 (`TableIdLow`) with offset 0x40 always 0 is RD-verified.
The checkpoint differential decoding to identical 13-root pointer lists across the corpus is RD
(finding **FS_CHKP_RA_014**). Method 5 — `CmsBPlusTable::DeleteFromIndex` removing only the offset-array entry and
leaving the row body in slack — is E2 for the deletion mechanism and RD for the recovery (0 false positives
on the baseline; finding **FS_DEL_RA_005**, corrected by **E64**). Its refinements are RD-verified across the
corpus (both v3.4 and v3.14): the **identity-based** deleted-vs-still-present test (a remnant is called deleted
only when no live file shares its name *and* creation-time — 0 false deletions across the USN-bearing images,
where the on-disk classification is independently checked against the live listing); the **two-mode subset**
invariant (recovery-mode results are always a subset of `--full` — 0 violations across the whole corpus); the
**type-0x40 backing carve** (the deleted non-resident extent map recovered from slack reconstructs byte-for-byte
identically to the live extract path — validated on live files, and on deleted files that preserved the
generator's `GFSAREPLAY` content signature at their original clusters); and the **deleted-directory grouping**
under `$DELETED/DIR_OID_0x<oid>/` (present on 30 of the corpus's ReFS images; the name-candidate ambiguity is
corroborated against the fsactivity generation logs, which record the `RENAME_DIR` events that leave multiple
names per OID in slack). The survival metrics and recovery categories are RD on a 266-transaction gap analysis. OID monotonicity, no-reuse, and the 55–79% worked-volume density are RD. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
