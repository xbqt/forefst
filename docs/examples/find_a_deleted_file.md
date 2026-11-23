# Recover a Deleted File from a ReFS Image

**Goal:** run the `deleted` command's recovery methods against one real image and read what each method finds,
and why the others find nothing.

## Setup

Image: a native ReFS 3.14 test volume, the last frame of the `step5/testatomic` lab chain of the test corpus (the
frame whose name ends `_filedeletedwithexplorer_unmount.raw`; the commands below give its full name).

Its file name lists the chain's actions, ending with a file **deleted with Explorer** and an **unmount**, but this
frame holds none of them:

- `files` lists 10 objects, all of them `$RECYCLE.BIN`, `System Volume Information` and their contents;
- there is no `test` directory, and the volume has no change journal.

Nothing a user created is on it, so nothing a user deleted can be recovered from it: what the methods below find is
files the system itself created and deleted (BitLocker's `FVE2.*` metadata files).

So the image tests whether the tool labels what it finds correctly. The easy recovery paths find nothing here — the Trash Table is
empty, its usual state, and the two checkpoints list the same files, as they usually do when nothing changed
between the last two checkpoints — and the scans find only system rows.

## Steps

### Step 1 — The fast metadata methods: Trash Table + checkpoint diff (`deleted --no-slack`)

```text
$ forefst.py win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile_filedeletedwithexplorer_unmount.raw deleted --no-slack
[...]
  ReFS version: 3.14
  Cluster size: 4 KiB
  Checkpoints:  2 (VC: 46 in use; 45 superseded)
  Objects:      19
  What this is: rows RECOVERED from metadata pages (best effort), not the volume's current content;
                each entry says what it is (DELETED, RENAMED, ...) and what decided it.

── Trash Table (OID 0xd) ──
  Empty (0 rows)

── Checkpoint Comparison ──
  Current checkpoint: VC=46 (LCN 0x1e3f4, in use)
  Previous checkpoint: VC=45 (LCN 0x2874, superseded)
  Same files and paths in both checkpoints (content and metadata are not compared)

── Recovery methods ──
  Mode: recovery.  Ran: Trash table (0xd), checkpoint diff.
  Slack scan SKIPPED (--no-slack). Run `deleted` (the default) to recover deleted rows.
[...]
```

`--no-slack` runs only the two fast metadata methods, and on this clean image **both correctly find
nothing**:

- **Trash Table (OID 0x0D):** `Empty (0 rows)`. A delete goes through the Trash only for an object whose data
 stream set holds two or more tables (a file with a stream snapshot, for one), and what enters it is removed
 later, so an empty Trash Table says nothing about whether files were deleted. See
 [Trash Table](../structures/trash_table.md).
- **Checkpoint differential:** the two checkpoints (VC 46 in use, VC 45 superseded) list the same files and paths,
 so the comparison finds no file that one has and the other lacks. It compares names and paths only, not content
 or metadata. The two trees differ only when a root table changed between the last two checkpoints.

So the metadata-only pass reports nothing here. That is the correct result for *these two methods*. Other
methods can still find rows: the default `deleted` run adds the B+-tree node-slack scan (Step 2).

### Step 2 — The strong method: B+-tree node slack (`forefst deleted`, Method 5)

`--full` adds the whole-volume orphan-page scan:

```text
$ forefst.py win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile_filedeletedwithexplorer_unmount.raw deleted --full
[...]
── B+-tree Node Slack Scan (Method 5) ──
  Recovering deleted directory entries from metadata-page free space
  (ReFS deletion removes the row's index slot and marks the row; the row body persists).
  Orphan-page scan: scanned 1032192 of 1032192 clusters (100% of the volume); 1025412 of them are
                    image holes: no page can be read there
  Orphan-page scan: 1 earlier ReFS volume wrote pages here: the area was formatted again at least 1
                    time (28 metadata page(s) carry another volume's signature at the address they
                    name: 0xe23e6f3f on 28; this volume's is 0x7d58351a). They are not this volume's
                    pages, and their rows are not listed (the first at cluster 0xc04); `deleted
                    --earlier-volumes` lists them.
  Scanned 55 live pages + 8 orphan pages with recoverable slack rows; set aside by structure: 9
  index-node separator row(s) (a child-page reference, not a directory entry), 1 row-shaped
  record(s) inside another row (an embedded record's sub-records), 3 name(s) with control characters

  ── What was found, and what can be recovered ──
                                    bytes in  carve     metadata  directory  empty  total
                                    the row   possible  only
    DELETED                               0         0         0          0      0      0
    DELETED, OR RENAMED                   0        19         2          0      0     21
    RENAMED                               0         0         0          0      0      0
    SAME FILE, OTHER CREATION TIME        0         0         0          0      0      0
    STILL PRESENT (the file is live)      2*        0         1          5      1      9
    * the file is live: those bytes are not written; `extract` gives its current content
    bytes in the row: `export deleted` writes them as the row holds them. carve possible: the row's extent
      map survives; `export deleted --carve` (or --full) reads those clusters, best effort -- they may hold
      other data since. metadata only: the name, times and attributes, no content.

  ── DELETED, OR RENAMED: 21 (no live file has this name + creation time; a rename is not ruled out) ──
    RECOVER        CREATED                       NAME                                           FOUND IN
    carve          2026-05-23T08:46:26.7071666Z  FVE2.{09cf57b8-9e6c-43d4-ae1f-0408882a397d}.1  System Volume Information
    carve          2026-05-23T08:46:26.7156928Z  FVE2.{09cf57b8-9e6c-43d4-ae1f-0408882a397d}.2  System Volume Information
[...]
    carve          2026-05-23T08:46:26.6836578Z  FVE2.{e40ad34d-dae9-4bc7-95bd-b16218c10f72}.3  System Volume Information
    metadata only  2026-05-23T08:46:26.6890224Z  FVE2.{aff97bac-a69b-45da-aba1-2cfbce434750}.1  System Volume Information
    metadata only  2026-05-23T08:46:26.6911445Z  FVE2.{aff97bac-a69b-45da-aba1-2cfbce434750}.2  System Volume Information

  ── STILL PRESENT: 9 (a live file has this name + creation time) ──
    RECOVER        CREATED                       NAME                                         FOUND IN
    bytes in row*  2026-05-23T08:46:27.9564109Z  IndexerVolumeGuid                            System Volume Information
    bytes in row*  2026-05-23T08:48:26.4390037Z  desktop.ini                                  $RECYCLE.BIN/S-1-5-21-3829591975-2821165226-2477612932-1001
    metadata only  2026-05-23T08:46:26.2298363Z  WPSettings.dat                               System Volume Information
[...]
    directory      2026-05-23T08:46:26.2277167Z  System Volume Information                    .  [earlier version: Modified, Changed, Accessed differ]
    empty          2026-05-23T08:50:18.0922658Z  FVE2.{8252fd17-a486-4ad4-b1ca-f4fe64d23218}  System Volume Information

  NOTE: rows found in metadata pages (in their free space, or still listed on an old page), not the volume's
        current content. FOUND IN is the directory whose page held the row (its path today), not necessarily
        where the file was deleted from. One line stands for every copy of a row.
  -v: each entry's locator, both times, the copies found, and why it cannot be carved
  To recover: `export deleted DIR --full` carves the 19 whose extent map survives (best effort).
[...]
```

The table comes first: each status by what can be recovered from its rows. Then each entry is one line -- what
can be recovered, its creation time, its name, the folder whose page held the row -- and `-v` prints each entry's
block instead, with where its row lies, both times and the copies found:

```text
$ forefst.py win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile_filedeletedwithexplorer_unmount.raw deleted --full -v
[...]
    FILE FVE2.{09cf57b8-9e6c-43d4-ae1f-0408882a397d}.1  (embedded record, slack of a live page @ cluster 0xc00 off 0x2e50, image offset 0x1c02e50)
      Found in a page of: System Volume Information  (table 0x701; where it was found, not necessarily where it was deleted from)
      Created:  2026-05-23T08:46:26.7071666Z
      Modified: 2026-05-23T08:46:26.7092845Z
      Copies: 6 copies found (their dates differ); shown: the longest copy (the most bytes)
      Recoverable: metadata + carve (the data is in extents whose map survives; `export deleted --carve`)
[...]
```

The plain `deleted` run (live pages only) recovers 13 of these 21 rows (and 2 of the 9 STILL PRESENT ones); the
other 8 sit in **old pages** — pages the live tree no longer references — which only the `--full` scan reaches.
That scan reads every cluster of the volume: here 1,032,192 clusters, 1,025,412 of them holes in this sparse
image, in about two seconds. On a large volume it takes far longer: on this project's host, 25.5 minutes for a 2 TiB
volume (see [Deletion Recovery](../concepts/deletion_recovery.md)).

This is where recovery succeeds. ReFS deletion (`CmsBPlusTable::DeleteFromIndex`) removes the
deleted row's slot from the page's **offset array**, marks the row as removed from the index (bit 0x4 of its +0x08 flags, which an update that replaces a row also sets) and queues *delayed* compaction — the **row body is
not scrubbed**. So the deleted directory entry's name, with the timestamps and attributes its entry carries,
survives in the page's **node slack** (bytes not referenced by the live offset array) until a later copy-on-write
rewrite reuses the space.

- Each recovered row is a type-0x30 directory entry: a name plus the MACB timestamps and attributes of its
 entry (the fields [`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) documents). Under `-v`, the
 `cluster 0x… off 0x…` locator (and the image offset beside it) is exactly where the row body sits.
- **Where the row was found** is in each locator (`-v`): `slack of a live page` is the free space of a page the live tree
 still uses; on an **old page** (one the live tree no longer references) a row is either in its free space
 (`slack of an old page`) or one the page still lists (`listed on an old page`). `FOUND IN` names that
 page's directory by its path today — where the row was found, not necessarily where the file was deleted from.
- **What each entry is** matters most, and it is decided by **file identity**: the name plus the
 creation time, and the identity (ObjectRef) the row records where it records one.
  - `DELETED` — the recorded identity is live nowhere.
  - `DELETED, OR RENAMED` — no live file has this name and creation time, and the row records no identity the
    tool can check, so a rename or a move is not ruled out (all 21 here).
  - `RENAMED` and `SAME FILE, OTHER CREATION TIME` — the recorded identity is live under another name or with
    another creation time.
  - `STILL PRESENT` — a live file has this name and creation time (here, for example, `WPSettings.dat` and
    `desktop.ini`, both copies of the current entry).

  The creation time survives a move or a rename, so it separates the same file relocated from a different file
  that merely reuses the name — two unrelated `Shield.png` in different folders are judged independently, and a
  common filename deleted from one folder is never masked by an unrelated live copy elsewhere.
- **Pages of an earlier volume are not this volume's.** 28 pages on this disk carry another volume's signature at
 header `+0x0C` (0xe23e6f3f; this volume's is 0x7d58351a): the area was formatted again. They are already on the
 disk in the first frame of the action chain, before any file was created, so they were not written for this
 volume. Their rows are not this volume's deleted files, so they are not listed; the line above says how many
 there are and where the first is, and `deleted --earlier-volumes` lists them.
- **Extent-backed deleted files carve too.** The table counts 19 of the 21 under `carve possible`: the file's
 data is in separate extents, and the extent map survived — in the name row itself for an embedded record (as
 for the row shown above), or in a type-0x40 backing row found in slack for a split record.
 `export deleted --full` (or `--carve`) carves them best effort, as `content/<name>.carved` — the clusters may have
 been reused since the deletion. The other 2 maps hold only sparse holes, so there is nothing to carve.
- **Rows that cannot be directory entries are set aside**, and the `Scanned` line counts them: index-node
 separator rows (a child-page reference), a record inside another row, and names with control characters (3 here).
 The 21 listed rows have two plausible timestamps each (creation and modification between 2009-11 and 2050-12),
 which does not show that a row is whole.
- **What the names are:** the recovered entries are `FVE2.{...}` BitLocker metadata files, which BitLocker itself
 creates and deletes: this volume holds no user file, live or deleted, and `recyclebin` finds no `$I` file on it (the bin holds only
 its `desktop.ini`). The method works; what it finds depends on the image.

### Step 3 — The broad method: orphan MSB+ page scan (`deleted --scan-pages`)

```text
$ forefst.py win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile_filedeletedwithexplorer_unmount.raw deleted --scan-pages
[...]
── Orphaned Page Scan ──
  Current tree references 55 metadata pages (the scan skips them)
  Orphan-page scan: scanned 1032192 of 1032192 clusters (100% of the volume); 1025412 of them are
                    image holes: no page can be read there
  Orphan-page scan: 1 earlier ReFS volume wrote pages here: the area was formatted again at least 1
                    time (28 metadata page(s) carry another volume's signature at the address they
                    name: 0xe23e6f3f on 28; this volume's is 0x7d58351a). They are not this volume's
                    pages, and their rows are not listed (the first at cluster 0xc04); `deleted
                    --earlier-volumes` lists them.
  Found 52 orphaned MSB+ leaf pages
  Rows set aside by structure: 2 name(s) with control characters

  ── What was found, and what can be recovered ──
                                    bytes in  carve     metadata  directory  empty  total
                                    the row   possible  only
    DELETED                               0         0         0          0      0      0
    DELETED, OR RENAMED                   0        21         0          0      0     21
    RENAMED                               0         0         0          0      0      0
    SAME FILE, OTHER CREATION TIME        0         0         0          0      0      0
    STILL PRESENT (the file is live)      2*        0         0          5      1      8
    * the file is live: those bytes are not written; `extract` gives its current content
    bytes in the row: `export deleted` writes them as the row holds them. carve possible: the row's extent
      map survives; `export deleted --carve` (or --full) reads those clusters, best effort -- they may hold
      other data since. metadata only: the name, times and attributes, no content.

  ── DELETED, OR RENAMED: 21 (no live file has this name + creation time; a rename is not ruled out) ──
    RECOVER        CREATED                       NAME                                           FOUND IN
    carve          2026-05-23T08:46:26.7071666Z  FVE2.{09cf57b8-9e6c-43d4-ae1f-0408882a397d}.1  System Volume Information
    carve          2026-05-23T08:46:26.7156928Z  FVE2.{09cf57b8-9e6c-43d4-ae1f-0408882a397d}.2  System Volume Information
[...]

  ── STILL PRESENT: 8 (a live file has this name + creation time) ──
    RECOVER        CREATED                       NAME                                         FOUND IN
    bytes in row*  2026-05-23T08:46:27.9564109Z  IndexerVolumeGuid                            System Volume Information
    bytes in row*  2026-05-23T08:46:26.2298363Z  WPSettings.dat                               System Volume Information
[...]
── B+-tree Node Slack Scan (Method 5) ──
[...]
  To recover: `export deleted DIR --carve` carves the 32 whose extent map survives (best effort).
[...]
```

The orphan page scan reads every **old page** of the volume — each MSB+ leaf page the live tree does not
reference — and lists the rows each page's **offset array** still holds, checked against the live tree in the
same way. It finds rows the slack scan does not, and the slack scan finds rows it does not: the scan lists only
the rows an old page still indexes, the slack scan also reads the free space between them. `--scan-pages` runs
the live-page slack scan too (13 + 2 rows here, not shown); each scan prints its own table, and the `To recover:`
line counts what both found. The two methods
are complementary: run both on a volume that matters.

Both scans cover the **whole volume**: the coverage line above states it explicitly, with the clusters that are
holes in the image, where no page can be read; a run bounded with `--max-scan` says so instead — a page-level
search that stopped part-way would report "not found" for a file still sitting on the disk. A cluster the scan
cannot read is counted too: the line then gives the clusters read and says **INCOMPLETE**, and the run exits 2.

### Step 4 — Method 4 (stream snapshots) does not apply to this image

For earlier versions of files that still exist, [`$SNAPSHOT`](../attributes/SNAPSHOT.md) stream-snapshot recovery
is the deterministic content path; it does not bring back a deleted file.

`snapshots` finds none on this image (`Files with snapshots: 0`); the `snapshot` in the frame's file name, like its
other words, names a step of the chain that this frame does not hold. So Method 4 is not applicable here.

For a worked snapshot extraction see [Recover credentials, alternate streams and earlier file
versions](recover_credentials_and_prior_versions.md) (`forefst.py <image> snapshots --extract DIR`).

## What this tells you

- On a volume where nothing changed between the last two checkpoints, the two fast metadata methods
 (`deleted --no-slack`: Trash Table + checkpoint diff) can return **nothing** — an empty Trash Table (its usual
 state) and two checkpoints that list the same files are expected, not a parsing failure.
- **B+-tree node slack (Method 5)** recovers deleted directory entries with their timestamps on this image —
 21 rows under `--full` (13 from live pages alone), each with two plausible timestamps; 3 names with control
 characters are set aside.
- The **orphan page scan (`--scan-pages`)** lists the rows the old pages still index (21 `DELETED, OR RENAMED` and
 8 `STILL PRESENT` here); it and the slack scan each find rows the other does not.
- **A disk can hold metadata pages written for an earlier volume** (another volume signature at `+0x0C`). Both
 scans leave them out and say so; `deleted --earlier-volumes` lists them.
- What recovery finds **depends on the image**: the recovered names are BitLocker `FVE2` files, because this
 volume holds no user file, whatever its file name says. Always corroborate a single slack row (timestamps, neighbours, its
 status) before relying on it.
- **OID gaps remain deletion evidence** independent of all the above: the volume reports 19 objects. Only
 directories draw user OIDs (from 0x701 up), so a missing OID between present ones means a **directory** that no
 longer exists — normally a deleted one, possibly a creation that failed — and the gap survives even full page
 reallocation. (Files carry no OID, so a deleted *file* leaves no gap — that is what the slack-row recovery above
 is for.)

## See also

- [Deletion Recovery](../concepts/deletion_recovery.md) — the five methods in full (this page runs Methods 1, 2 and
 5 and the `--scan-pages` scan, and checks Method 4)
- [Forensic Analysis Workflow](../concepts/forensic_analysis_workflow.md) — where Step 5 (recover) sits in the 7-stage runbook
- [Copy-on-Write](../concepts/copy_on_write.md) — why deleted/old rows survive in slack and orphan pages
- [Trash Table](../structures/trash_table.md) — Method 1 deferred-deletion queue (OID 0x0D)
- [Object Table](../structures/object_table.md) — Method 3 orphan-OID detection
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the MACB timestamps each recovered row carries
- [$SNAPSHOT](../attributes/SNAPSHOT.md) — Method 4 deterministic prior-content recovery (not present on this image)
- Master reference: `structure_reference.md` §I (Deleted-File Recovery) — §I.1 Trash, §I.2 checkpoint differential,
 §I.3 node slack, §I.4 orphan-object scan, §I.5 CoW prior states

<!-- findings: FS_CHKP_RA_014 -->
