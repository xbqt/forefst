# Deletion Recovery

> What is recoverable depends on **where the bytes were**, not on where the record was: inline content is in the deleted row that remains, extent-backed content needs its extent map.
>
> See [Record placement and data residency](placement_and_residency.md).

Deletion on ReFS zeroes nothing. When a file is deleted, the analyst has to find *where the prior bytes still are
and how long they stay there*.

[Copy-on-write](copy_on_write.md) writes every changed metadata page to a new location, and a deleted row is only
dropped from its page's offset array. So a deleted file's metadata and content frequently survive somewhere on the
volume long after the file vanishes from its directory. Most deletions free the file's clusters in the deleting
transaction; only some objects are queued for a background cleaner (below).

This page lays out the five recovery paths, what each one can reach, and the survival rules that decide whether
the bytes are still there:

- the strongest exact-content path is **Method 4 (stream snapshots)**, which reconstructs prior bytes
  deterministically — for files that still exist;
- the deepest metadata path is **Method 5 (B+-tree node slack)**, which recovers deleted directory-entry names with
  the timestamps and attributes their entry carries, which no other method reaches.

## How deletion actually works

ReFS does not scrub a deleted file. The cleanup path (`RefsCommonCleanup` → `RefsDeleteFile` / `DeleteFileOnDisk`,
and `DeleteDirectoryOnDisk` for directories) removes the directory row with `MsDeleteRow`. What happens to the
object then depends on a gate (the Windows 11 driver, refs.sys 26100 and Insider):

- it **reparents the object to the [Trash Table](../structures/trash_table.md)** (OID 0x0D, schema 0xe0d0) via
  `MsReparentFileToTrash` and `CmsTrashTable::AddFileTable` only when `RefsCheckDataSetsForDeletion` finds that one
  of the object's data stream sets holds **two or more tables** or has the set's +0x100 set — or, for a file, under
  a feature bit and a condition on the delete request, when its single-table sets hold more than 5,000 rows
  together;
- otherwise `RefsDeleteAllMinstoreStreams` and `RefsDeleteObject` delete it in place, in the same transaction.

The ReFS 3.4 driver reparents through another routine, whose condition is not read. For a reparented object a
background work item, `TrashCleanerWorkItemMethod`, later calls `DeleteFileTable` to free the data extents.

On a lab volume that deleted six objects together — a 1 MiB file, a 100 B file, a file with three small named
streams, one with a 256 KiB named stream, a directory holding a file, and a file given a stream snapshot — only the
snapshot file went through the Trash; the other five were deleted in place.

Two consequences follow, and both leave something to find:

- a reparented object lingers in the Trash Table until the cleaner runs (`deleted` lists the table's row, keyed by
  the object's reference; it does not recover the object from it);
- because the directory row is *removed from the offset array* rather than scrubbed, its body survives in page
  slack.

Each method below reads one of these leftovers.

## Two modes, and how the methods map to them

The `deleted` command runs these methods behind **two simple modes**, so an analyst chooses a depth instead of
choosing individual scans:

- **`deleted`** — *recovery* (the default, quick). Runs the Trash table, the checkpoint differential, and the
  B+-tree node-slack scan over the **live pages only** (the pages the tree walk already reads). It recovers the
  common in-tree deletions in seconds on a small volume and in minutes on a large one (209 s on the 60 GiB Windows
  Insider boot volume of the corpus).
- **`deleted --full`** — *complete*. Everything in recovery, plus a scan of **every cluster on the volume** for
  **orphan pages** (pages no live tree references, which hold earlier versions of live files as well as deleted
  objects), and it carves extent-backed content on export.

Fine-grained flags still override the presets for power users: `--no-slack` (fast Trash+checkpoint pass),
`--trash` (Trash only), `--scan-pages`, `--orphans` (a low-confidence Object-Table-orphan tier), `--carve`,
`--max-scan N`, `--search SUB`. Each mode prints a one-line pointer to the other. Two related paths live in their
own commands: **stream snapshots** (`snapshots`, Method 4 below) and the **Windows Recycle Bin** (`recyclebin`).

### How long each option takes

The deep options read the whole disk once, so their cost follows the **size of the volume** and the disk's
sequential read speed — not the number of files on it. The table gives the cost of each option:

| Option | Cost | What it reads |
|--------|------|---------------|
| `deleted` (default), `--trash`, `--no-slack`, `--orphans`, `--search`, `--csv`/`--json` | **Fast** — seconds on small volumes; 209 s on the 60 GiB Insider boot volume | Only pages the tree walk already touches |
| `--carve` (on export) | **Moderate** | The data extents of each recovered extent-backed file — cost follows how much deleted data you reconstruct |
| `--full`, `--scan-pages` | **Slow**, with the volume's size — measured on this project's host: at most 6.4 s on the 101 ReFS volumes up to 8 GiB measured, 134 s and 250 s on the two 60 GiB ones, **25.5 min on a 2 TiB volume** (about 1.44 GB/s); about 3.2 h projected for 15 TiB | Every cluster on the volume, looking for orphan `MSB+` pages |
| `--full` on a multi-TB volume | **Very slow** — projected at about 3.2 h for 15 TiB from a run stopped at 30 % (1.43 GB/s) | As above; progress is printed as it runs |
| `--max-scan N` | Turns a slow scan back into a fast one | Stops after N clusters — see the warning below |

A slow scan that you chose is acceptable; a scan that stops part-way without saying so is not. The deep scan
therefore covers the
**whole volume by default**, always prints how much of the volume it examined, and marks any run bounded by
`--max-scan` as **INCOMPLETE** in both the console output and the recovery log. Deleted data lands wherever the
allocator last freed a page, so a partial scan misses files for no reason the analyst can see.

| Method | What it reads | Mode | Recovers |
|--------|---------------|------|----------|
| 1 — Trash table | OID 0x0D queue | recovery | The row of each object deleted but not yet reclaimed: its ObjectRef and its record (listed raw; the object itself is not recovered) |
| 2 — Checkpoint differential | two checkpoints' trees | recovery | Objects removed, renamed or moved between the two checkpoints (usually none) |
| 3 — Orphan-object scan | OID Table ∖ tree | `--orphans` (opt-in) | Object-Table directory OIDs unlinked from the tree — low confidence |
| 5 — B+-tree node slack | metadata-page free space | recovery (live pages) / `--full` (+ orphan pages) | Deleted names with their timestamps and attributes, and carve-able extent maps — **the primary method** |
| 4 — Stream snapshots | `$SNAPSHOT` (type 0xB0) | `snapshots` command | **Exact prior bytes** of files that still exist |

The slack scan classifies its results by the **identity** each row records, and an **export writes a recovery
log** — both covered below.

## Method 1 — Trash Table recovery

The [Trash Table](../structures/trash_table.md) is the deferred-deletion queue: any object reparented here is an
object that passed that gate (in the lab, the file given a stream snapshot), with its metadata and data **not yet
reclaimed** (every other delete is done in place and never appears here, as above). Reading OID 0x0D through the
[Object Table](../structures/object_table.md) and enumerating its rows therefore names the objects deleted but not yet
reclaimed: each row's key is the object's reference (`deleted` prints it as the row's ObjectRef) and its value the
object's record. `deleted` lists the rows raw; it does not recover the objects from them. The cleaner's removed rows
stay in the table page's free space, which `deleted` does not read. On a cleanly maintained volume the Trash Table is
usually empty — the cleaner runs promptly — so this method finds only objects deleted shortly before the image was taken,
before the cleaner ran; for older deletions, use the slack scan (Method 5).

## Method 2 — Checkpoint differential

The volume keeps two [checkpoint](../structures/chkp.md) copies, each pointing at a set of root tables.
The idea is to compare the [Object Table](../structures/object_table.md) reachable from the checkpoint in use
against the one reachable from the other checkpoint: an object present in the older tree but absent from the newer
was deleted between them. But **the two copies usually reference the same root tables**. On the
images measured (a clean, a corrupted, a busy and a pre-salvage volume, and all but one of the volumes of the blind
audit) their 13-root lists are identical, so the differential is empty; on that ReFS 3.4 volume five of the 13 roots
differ.
A difference needs a capture between two checkpoint writes that changed a root table. `deleted` compares the two
trees object by object (by ObjectRef), at any depth: the objects removed, renamed or moved, and added. Compare the
**decoded** root page-references, not the raw checkpoint bytes: the copies differ in 11 to 15 bytes even when their
trees are identical — the virtual clock (+0x10, +0x60), the allocator clock (+0x68, by 1), the page's own LCN
(+0x20) and the self-descriptor's LCN (measured on 18 volumes). (This limit is canonical on
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

This is the strongest and most deterministic single-image path, because it does not rely on un-reallocated pages at
all. If a file carries [stream snapshots](../attributes/SNAPSHOT.md) (`$SNAPSHOT`, type 0xB0), each snapshotted prior
version's **exact bytes** can be reconstructed from the same image. Taking a snapshot freezes the file's current
extents under a new stream sub-id; subsequent writes allocate fresh clusters via copy-on-write, and the snapshotted
clusters stay named by the snapshot's own extent map (the [Block Refcount table](../structures/block_refcount.md) does
not count this sharing: a snapshot adds no count). The recovery chain is explicit:

> `$SNAPSHOT val[0x44]` (`data_sub_id`, 0x1001+) → matching `$DATA` sub-record (`key+0x10 == data_sub_id`)
> → its extent rows → each file VCN from this version's map, else from the newest snapshot strictly older than it
> → holes (flag 0x20) zero-filled, never read → translate VLCN → PLCN via the
> [Container Table](../structures/container_table.md) → read → trim to stream size.

The full walk-through — the embedded sub-record headers, the extent decode, and how multiple snapshots
reconstruct an ordered version history — is canonical on
[Stream Snapshots and File Versioning](snapshots_versioning.md). Recovery here has been verified byte-for-byte
against the lab generator's specification (every current file and prior version of one lab file family) and on a
multi-megabyte, multi-extent version, and is implemented as `forefst.py <image> snapshots --show` (preview) /
`--extract DIR` (write the recovered versions).

Snapshots go with their file: deleting a snapshotted file removes its snapshots too (in the lab, the deleted
snapshotted file left metadata only), so this method recovers prior versions of files that still exist.

> **Scoping caveat.** ReFS *file-level* stream snapshots (`$SNAPSHOT`, type 0xB0) are a different thing
> from VM/disk snapshots. A volume whose history came from a hypervisor or disk-level snapshot step
> contains **no** ReFS stream snapshots, and this method finds nothing there; it applies only to files that
> actually carry a `$SNAPSHOT` sub-record.

## Method 5 — B+-tree node slack recovery

ReFS deletion (`CmsBPlusTable::DeleteFromIndex`) removes the deleted row's entry from the page's
**offset array**, marks the row as removed from the index, and queues *delayed* compaction — **the row body is not scrubbed**. So a deleted directory
entry's filename and the fields its entry carries ([MACB timestamps](../concepts/timestomp_detection.md),
attributes) survive in the **node slack**: the page bytes no longer referenced by the live offset array, until a later
copy-on-write rewrite reuses the space. This is reachable by **no other method** — the orphan scan
(Method 3) follows only a page's *live* offset array and never sees these rows.

The procedure walks every live and orphan `MSB+` page (index and leaf alike) for type-0x30 row headers
([directory-entry keys](../structures/directory_entries.md): `key_off == 0x10`, key type 0x30, in-bounds, decodable
UTF-16 name) that are **not** in the live offset array — and, on an old page (one the live tree no longer references),
the rows that page still lists as well, each worded by the live tree (`old version of an existing file` /
`deleted, seen on an old page`; its slack rows are `slack of an old page`).

It reads each page whole, and reads as a page only bytes that lie at the address they name (`+0x20`, in the page's own
cluster size): a page with another volume's signature that does is an earlier volume's (`deleted --earlier-volumes`
lists those rows, never mixed with this volume's), and bytes with a page signature that do not — this volume's or
another's — are a copy of pages inside a file's content (a deduplication index, an image or a backup of the metadata)
or a page whose address is damaged, and are counted, not read.

It decodes the name + MACB + attributes and **grades by confidence** from the creation and modification times: high
when both are plausible FILETIMEs, medium when one is, partial when neither is (for instance a row whose body was
partly overwritten).

It records the directory whose page each row was **found in** — the owning table OID at page offset `0x48` ([page
header](../structures/page_header.md) `TableIdLow`). That is where the row was found, not necessarily where the file
was deleted from: a page's free space can hold rows of another directory (on the public sample about one row in twelve
that `deleted --full` prints sits in a page of a directory under a top folder that never held that name, by the
volume's own workload log; how they get there was not read in the driver). An index (inner) page's free space can also
keep the rows of the leaf it was before the tree split, beside its own separator rows (48-byte child references with
implausible times).

Implemented as `forefst.py <image> deleted`: *recovery* mode scans the **live pages** (quick); `deleted --full` also
scans **orphan pages** (the freed pages of deleted objects) across the whole volume, which hold the older
deletions: those whose directory entry is no longer in the tree. Add `--no-slack` for a fast
Trash+checkpoint pass.

**`export deleted DIR`** writes a **`deleted_files.csv`/`.json` index** — one row per deleted entry (name,
recoverability, reliability, category, and its content file if any) — plus a **`content/`** folder holding only the
*readable* recoveries: `content/<name>` for an inline file (byte-exact) and, under `--full`/`--carve`,
`content/<name>.carved` for an extent-backed file (best-effort — the clusters may have been reused, so verify). A
`recovery_log.txt` audit trail is written too. The raw remnant bytes go to `rows/` only with `--rows`; `--no-system`
hides the BitLocker `FVE2.{…}` churn that can otherwise dominate a volume's deleted list.

**What each entry is — decided by the identity the row records.** A row found in a page is a candidate, and its
name and creation time do not say whose it is: a copy, a move by copy-and-delete or a safe-save that keeps the times
makes a *new* object with the same name and creation time, and the old object's rows survive beside the new file's own
older rows (on several corpus volumes, a few hundred remnants with a live file's name and creation time record another
object's identity). The identity the row records decides: a directory row's own OID; a split row's home + ordinal; for an
embedded row, which holds its ordinal but not its home, the FileRef of the change-journal record its `LastUsn`
(`+0x68`) names, while the journal still holds it (on the public sample about nine embedded remnants in ten
with a `LastUsn` point to a record of the same name, and about one in nine of those names another FileRef than the
page's owner would give).
Each entry then carries one of five statuses:

| Status | Meaning |
|--------|---------|
| `DELETED` | the identity the row records is live nowhere |
| `DELETED, OR RENAMED` | no live file has this name + creation time, and the row records no identity the tool can check, so a rename or a move is not ruled out |
| `RENAMED` | not deleted: the same file (by the identity the row records) is live under another name — a rename, a move with a new name and a removed hard-link name read alike |
| `SAME FILE, OTHER CREATION TIME` | not deleted: the same file is live under this name, and its creation time was set after this row was written (a lead for timestomping) |
| `STILL PRESENT` | a live file has this name + creation time, and no copy records the identity of another object |

For an entry whose file is live, the Version words say whether the row is a copy of the current entry (`same`: all
four times equal a live row's) or an earlier version (`differ`, with the times that differ named); on the corpus,
about three such entries in four are copies of the current entry. An entry found in a page of a directory
the live file is not in says so. The copies of one row found in several pages are one entry (the longest copy is
shown), and the copies are counted, with how many differ (`Copies`, `CopiesDiffer`).

**Extent-backed content is carve-able from slack too.** A deleted extent-backed file keeps its data in separate
on-disk extents, and its extent map is in its record:

- if the record was split out of the name row (the file was moved or hard-linked), the map is in a **type-0x40
  backing record**, unlinked from the live tree at deletion but whose body **survives in the same page slack** as
  the name row. The scan recovers that backing, matches it to the name row by `(file_id, home-dir)` + exact size,
  and reconstructs the file from those clusters;
- if the record was never split, the map is **embedded inside the name row itself** (a small B+-tree node), which
  is common on every version, native 3.14 included. The scan decodes that embedded map the same way and carves
  those files too.

So extent-backed deleted content can be carved whichever way the record was placed (`export deleted --carve`,
best-effort — the clusters may have been reallocated).

A carve is only written when the extent map forms a complete, in-bounds picture of the file and at least some of its
clusters are still readable; a map that points outside the volume or has been zeroed yields metadata only, never an
empty stand-in file. A carved file can still hold another file's bytes where its clusters were reused — see the CRC
check below.

**One carve plan decides what is carved.** Each surviving map goes through the same plan, which says what would be
carved and, when nothing is, why (`NoCarveReason`): every run unwritten, only sparse holes, above the size limit,
outside the volume, a malformed row; the row declares a size of 0 B (there is nothing to carve); its current stream
declares no allocation although its map holds rows; the row's size and its current stream's disagree. A file's row can
be written between its allocation and its size: on the corpus's Insider system volume (both captures), a few hundred
remnant rows declare a size of 0 with an allocation whose map is an exact cover, and on some of the still-present ones
the map is the live file's (for example an AppxBlockMap.xml: 0 B declared, 94,208 B allocated; the live file 93,864 B,
the same runs).

**A live file's map is not carved.** An entry whose file is live gets the verdict `metadata + extent map, not carved`,
which says where the map's clusters are now: the live file's at the same offsets (`extract` reads them), another live
file's (named), in no live file's extents (stream snapshots and metadata pages are not checked), or the count of each.
On the corpus about two such maps in three are the live file's clusters at the same offsets; a few lie in other live
files' extents, in none, or are mixed; the carve plan refuses the rest (more than a quarter). A copy of the
current entry can still hold a map that is not the live file's.

**A carve is checked where the map allows.** Each carved cluster is compared with the CRC-32C its map stores, where
the map stores one, and the manifest says how many matched; a run of the right length that points at the wrong
clusters is caught only by such a CRC. On the public sample's carve, of the two remnants whose map rows carried a
CRC-32C, one matched and one did not: its cluster no longer holds the bytes the map recorded. Without a stored CRC a
carve is best-effort.

**Deleted directories are reconstructed as a group.** When a directory is deleted, its freed page can survive with its
children's rows (the orphan-page scan of `deleted --full` finds it), but its OID is gone from the tree — so those
children are recovered with an **unresolvable parent**. They are grouped under `$DELETED/DIR_OID_0x<oid>/<child>`,
identified by the one reliable fact: the physical page they were recovered from. The deleted directory's *name* is
offered only as a **best-effort candidate**, and is explicitly flagged **ambiguous** when rename/move churn left
several conflicting names for the same OID in slack — a named ancestor path is never asserted, because the slack holds
rows from several points in time and any single reconstructed name could be a pre-rename artifact.

> **Caveat.** Slack recovery is **image-dependent**: it finds only what survives in un-rewritten slack. A
> heavily rewritten or freshly compacted page may retain nothing, so a single recovered row should always
> be corroborated (timestamps, surrounding rows) before it is relied on. Carved extent-backed content is
> best-effort — the extent *map* survived, but the data clusters may have been reused since deletion.

## The recovery log

An **export** writes a **recovery log** — a forensic audit trail of exactly what was recovered and how. The log
is written by `export deleted` (and by the deprecated `deleted --extract`), into the export directory as
`recovery_log.txt`, or wherever `--log PATH` says; `--log` also gives a plain view a log. A plain `deleted` view, and
its `--csv` / `--json` / `--jsonl` outputs, **never write a log file**. When written, it records the image, the ReFS
version, the mode (`recovery` / `no-slack` / `full`), the methods that ran, and every entry under its status heading
(the five statuses above), each with the page it was found in and its recoverability verdict. The log is the primary
record to cite in a report: it states why each entry has its status.

## What decides whether the bytes survive

For the slack scan (Method 5) and the orphan tier (Method 3) the bytes are present only if the allocator has not
reused the clusters, so the bytes survive only until the clusters are reused. Three conditions affect how soon that happens,
and a fourth prevents reuse:

| Factor | Effect on survival |
|--------|--------------------|
| Volume activity | Low activity → more old pages survive un-reallocated |
| Time since deletion | Less elapsed time → less chance of reuse |
| Volume free space | More free space → the allocator reuses old clusters more slowly |
| Still named by a live map (a snapshot's extents, a clone's) | **Guaranteed** survival while that map lives — the clusters are not free |

In the referenced case survival is certain, not a matter of chance: clusters a live map still names — a stream
snapshot's extents, a clone's — are not free, so the allocator cannot reuse them. This is what makes Method 4
deterministic. The [Block Refcount table](../structures/block_refcount.md) does not show it: it counts only the
clone and deduplication references beyond the first, and a cluster shared with a snapshot reads 0 there. The three
recovery categories follow:

| Category | Condition | Outcome |
|----------|-----------|---------|
| Still referenced | a live map names the clusters (a snapshot's extents, a clone's) | **Guaranteed** survival while that map lives |
| Unreferenced, not reallocated | no live map names them, the clusters are free | Data survives until the allocator reuses the clusters |
| Reallocated | Clusters reused | Data **overwritten** — not recoverable |

A gap-analysis run on one modestly active 2 GiB volume illustrates this. The fractions below are
measured on a single volume (small denominators); they are not general survival rates. Across a window of
266 transactions, of the extent-backed files that had been modified, **about half still had their old
data fully intact**, roughly **6%** of old clusters carried a Block Refcount count of 2 or more, and
about **62%** of old metadata pages remained valid (the table is in the Evidence section).

## Gaps in the OID sequence

Independent of whether any content survives, deletion leaves a permanent record in the object-id space.
[Object IDs](object_ids.md) are 64-bit, a new one is always above every live one, and an OID below one still in use is
**never issued again** (user OIDs start at 0x701, set by `MsSetMinimumNewObjectId`; see
[OID Allocation](oid_allocation.md)). A **gap in the OID sequence is therefore a permanent trace**: if 0x720,
0x721, and 0x723 exist but 0x722 does not, OID 0x722 was issued to a **directory or system object** that no longer
exists — normally a deleted one — and no later activity can hide that.

The counter is committed before the object is built, so a creation that failed would leave the same gap (that case
is not measured). Files carry no OID of their own, so a deleted *file* leaves no gap — the OID sequence tracks
deleted **objects**, i.e. directories and system tables.

**OID density** (present OIDs ÷ range) gives a lower bound on a volume's deletion history: a freshly formatted volume
is essentially 100% dense, while a worked volume falls to roughly 55–79%. Here ReFS has a forensic advantage over
NTFS: NTFS reuses its MFT records, so their deletion evidence is lost over time — see
[NTFS vs ReFS](ntfs_comparison.md) for the full contrast.

## Additional identity techniques (analysed, not built into the tool)

Two further techniques recover a deletion's **identity and timeline** — never its content — and were validated
on disk but deliberately left out of the `deleted` command. They are documented here so an analyst can apply
them by hand when the case warrants. (Separately, the log can hold a small inline file's bytes after the file is
deleted; see [Transactions and Crash Consistency](transactions_crash_consistency.md). The tool does not extract
them.)

### Journal identity — USN `FILE_DELETE` + MLog

The [USN change journal](../structures/usn_journal.md) (`$UsnJrnl:$J`) records a deletion **by name** when the
deleting handle closes: a `FILE_DELETE` (reason `0x200`) record carries the deleted file's name, its parent, and a
timestamp — independently of whether any slack remnant survives. So it can be used to check the slack
scan: it can **confirm** a recovered deletion, supply a **deletion time** the slack `$SI` does not carry, and even
**name** a deletion whose slack row is already gone. Three cautions apply:

- **The timestamp is a *close* time, not a delete instant.** Every `FILE_DELETE` record observed carries the
  `CLOSE` bit (`0x80000000`) OR-ed in, and often coalesces a file's whole create→delete→close lifecycle into one
  record. So it is best read as "the deleting handle closed at *T*", which can lag the logical delete.
- **Join by the identity the row records.** The USN 128-bit File ID is the FileRef: its low half the file's
  per-directory ordinal, its high half the directory it was created in. A split remnant records both (ordinal at
  `value+0x00`, home at `value+0x08`); an embedded remnant records its ordinal, and its `LastUsn` names the journal
  record ([Method 5](#method-5--b-tree-node-slack-recovery)). Where the row records no identity, the
  `(name, creation-time)` pair is only a lead, with a confidence flag when candidates collide.
- **Availability is narrow.** The USN journal is present on only a minority of volumes and on **no** v3.4 volume
  in the reference corpus; where absent, it says nothing (which is not the same as "no deletions"). The redo-only
  [MLog](../structures/mlog.md) (`RedoDeleteRow` / `RedoDeleteTable`, and `RedoReparentTable` for the
  Trash move) is the cross-source that spans *every* version — and no method of the tool recovers content
  from it, although its redo records carry the rows they change, so a small (inline) file's bytes can outlive the
  file there ([MLog](../structures/mlog.md)). The [type-0x20 FileId index](../structures/reverse_index.md) holds a
  second copy of a live file's name, but deletion removes that entry too; its body can survive in the index page's
  slack like the name row.

### Parent-Child ancestry for deleted directories

The [Parent-Child Table](../structures/parent_child_table.md) (checkpoint root #4) records directory→directory
edges as `(parent OID, child OID)` pairs. When a directory is deleted its edge is actively removed from the live
table — but, exactly like a directory-entry row, the edge's **body survives in the table's page slack** until a
CoW rewrite. Recovering those slack edges yields an **OID-exact ancestry chain** for a deleted directory
(`parent → grandparent → … → root`), which is far more reliable than reconstructing a path from slack *names*:
the 26100 and Insider drivers, which keep the OID counter on the volume, do not reuse an object ID, so an OID edge
is unambiguous even when rename/move churn left several conflicting names for the same directory (on a volume the
Windows 10 1803 driver writes, a deleted directory whose OID was above every live one can have its OID issued again
after a remount, and the 3.7 to 3.10 drivers were not read; see
[OID Allocation](oid_allocation.md#at-mount)). On disk this recovered every deleted directory's parent edge on lightly-used
volumes and a decreasing fraction as churn rose (and nothing where the table's own root page had been reclaimed)
— so it is a **best-effort** enhancement to the `$DELETED/DIR_OID_0x<oid>` grouping, to be reported with explicit
coverage, never asserted.

## Cross-references

- [Copy-on-Write](copy_on_write.md) — the update model that makes recovery possible; canonical for the CoW-vs-NTFS
  update-model contrast and the checkpoint-comparison limit
- [Stream Snapshots and File Versioning](snapshots_versioning.md) — the full Method 4 recovery walk-through
- [Stream Snapshots ($SNAPSHOT)](../attributes/SNAPSHOT.md) — the on-disk sub-record Method 4 reads
- [Trash Table](../structures/trash_table.md) — Method 1, the deferred-deletion queue (OID 0x0D)
- [Object Table](../structures/object_table.md) — Method 3 orphan detection works against the live OID set
- [System OIDs](../structures/system_oids.md) — OID 0x0D is the Trash Table
- [Block Refcount table](../structures/block_refcount.md) — the clone and deduplication counts (snapshot sharing is
  not counted there)
- [Object IDs](object_ids.md) · [OID Allocation](oid_allocation.md) — why OID gaps are permanent deletion evidence
- [What Survives](what_survives.md) — the broader inventory of recoverable artifacts on a ReFS volume
- [NTFS vs ReFS](ntfs_comparison.md) — OID-gap evidence vs reusable MFT records; log-wrap vs CoW recovery windows
- [MLog](../structures/mlog.md) — redo-only: no record holds the value a change replaced, but a file's earlier records,
  while the log keeps them, hold the values they wrote
- [USN Change Journal](../structures/usn_journal.md) — records a deletion by name + close-time (journal-identity
  technique)
- [Parent-Child Table](../structures/parent_child_table.md) — root #4 dir edges; OID-exact ancestry for deleted
  directories
- [Type-0x20 FileId index](../structures/reverse_index.md) — a second copy of a live file's name (removed at deletion)

## Two deletion paths leave different traces

**Explorer** routes the file through `$RECYCLE.BIN`: the `$R` entry keeps the file's home back-reference — the
directory it was created in (the source directory, unless the file had been moved before) — and a small `$I`
metadata file (188 bytes on the volume measured, stored inline) records the original full path and the deletion
time. Both survive until the bin is emptied, and `forefst recyclebin` decodes them.

**PowerShell `Remove-Item` does not.** It deletes permanently, bypassing the bin entirely, and shows up
in the change journal as reason `0x80000200`. There is no `$I` to recover an original path from — which
is why an absent recycle-bin trace is not evidence that a file was never deleted. Measured on 3.14.

## Evidence

A deletion can leave a file's record behind while taking its bytes: the `$DATA` descriptor still declares
an inline stream, and the region it points at reads as zeros. So does a file that genuinely held zeros,
and nothing in the remnant separates the two — so the tool reports its own outcome naming both, yields the
name, size and timestamps, and writes no content either way — measured on a lab volume built for it and re-measured
across the corpus.

The deletion flow — `RefsDeleteFile` / `DeleteFileOnDisk` → `MsDeleteRow` → `MsReparentFileToTrash` →
`CmsTrashTable::AddFileTable` (OID 0x0D) → background `TrashCleanerWorkItemMethod` → `DeleteFileTable` — is confirmed
in the decompiled driver (E2), as is its gate: the delete paths send an object there only when
`RefsCheckDataSetsForDeletion` finds a data stream set of two or more tables (or on the two rarer conditions above),
and every other delete is done in place in one transaction; a lab volume's log shows it (one reparent into the Trash,
for the file given a stream snapshot; the other five objects deleted in place). The Trash Table OID 0x0D / schema
0xe0d0 and its empty-on-clean-volume state are also raw-disk verified (RD). The page-header OID at offset 0x48
(`TableIdLow`) with offset 0x40 always 0 is RD-verified. The checkpoint copies' root lists are compared on disk (RD)
on the images named in Method 2. Method 5 — `CmsBPlusTable::DeleteFromIndex` removing only the offset-array entry and
leaving the row body in slack — is E2 for the deletion mechanism and RD for the recovery (0 false positives on the
baseline). Its refinements are RD-verified across the corpus (both v3.4 and v3.14): the **identity-based** status (the
identity the row records decides; a name and a creation time are a candidate only — measured on 13 corpus volumes, and
the journal link of embedded rows checked against the public sample's workload log with 0 contradictions); the
**two-mode subset** invariant (recovery-mode results are always a subset of `--full` — 0 violations across the whole
corpus); the **type-0x40 backing carve** (the deleted extent map recovered from slack reconstructs byte-for-byte
identically to the live extract path — validated on live files, and on deleted files that preserved the generator's
`GFSAREPLAY` content signature at their original clusters); and the **deleted-directory grouping** under
`$DELETED/DIR_OID_0x<oid>/` (present on 30 of the corpus's ReFS images; the name-candidate ambiguity is corroborated
against the fsactivity generation logs, which record the `RENAME_DIR` events that leave multiple names per OID in
slack). The survival metrics and recovery categories are RD on a 266-transaction gap analysis. OID monotonicity,
no-reuse, and the 55–79% worked-volume density are RD. The `$R`/`$I` structure (the 188-byte inline `$I` is one
volume's example), and `Remove-Item` bypassing the bin under USN reason `0x80000200`, are registered findings too.

The counts behind the text:

- the checkpoint copies decode to the same root list on 25 of the 26 volumes of the first blind audit;
- on the public sample, 137 of the 1,630 rows `deleted --full` prints sit in a page of a directory under a top folder
  that never held that name; 571 of the 636 embedded remnants with a `LastUsn` point to a record of the same name, and
  64 of those name another FileRef than the page's owner would give;
- 359 remnants on 13 corpus volumes carry a live file's name and creation time and another object's identity;
- the Version words: on 124 corpus images, 101,362 of the 132,352 entries whose file is live are copies of the
  current entry;
- a size of 0 with an exact-cover map: 554 remnant rows on the two captures of the Insider system volume (`winsider`,
  `winsiderv2`), the live file's map on 173 of the still-present ones;
- a live file's map: of the 48,729 such maps on 124 corpus images, 33,024 are the live file's clusters at the same
  offsets, 1,114 lie in other live files' extents, 601 in none and 152 are mixed; the carve plan refuses the other
  13,838;
- the gap analysis (one 2 GiB volume, a window of 266 transactions):

| Metric | Value |
|--------|-------|
| Modified user objects | 39 |
| Modified system objects | 7 |
| Extent-backed files analysed | 18 |
| Files with old data fully intact | 9/18 (50%) |
| Old clusters with a Block Refcount count `>= 2` | 76/1,181 (6.4%) |
| Old metadata pages still valid | 13/21 (61.9%) |

See [how this was verified](../methodology.md) to trace these statements to
the exact images and measurements in `analysis/`.

<!-- findings: AP_LGFL_RA_012, FN_PATH_001, FS_CHKP_RA_014, FS_DEL_RA_005, MD_DEL_RA_001, MD_DEL_RA_003, MD_DEL_RA_004,
               MD_DISK_RA_008 -->
