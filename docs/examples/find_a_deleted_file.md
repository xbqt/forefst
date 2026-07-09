# Worked Example: Recover a Deleted File from a ReFS Image

**Goal:** run every available ReFS deletion-recovery method against one real image and read the
results honestly — which method finds what, and why the others come up empty.

## Setup

Image: a native ReFS 3.14 test volume
(referred to below as `$IMG`). This is the last frame of the `step5/testatomic` action chain: a
native **ReFS 3.14** volume that was BitLocker-encrypted, had files created and modified, then had a
file **deleted with Explorer** and was **cleanly unmounted**. A clean unmount is the worst case for
the easy recovery paths (Trash Table is drained, both checkpoints converge), which makes it a good
stress test for honest annotation.

```sh
IMG=deleted_file_test.raw   # a v3.14 ReFS test volume; file deleted via Explorer, then cleanly unmounted
```

## Steps

### Step 1 — The fast path: `forefst files --deleted` (Trash Table + orphan scan + checkpoint diff)

```sh
python3 forefst.py "$IMG" files --deleted
```

```
[forefst] ReFS 3.14 | 19 objects | cluster_size=4096
[forefst] Scanning Trash Table...
[forefst] 0 trashed entries found
[forefst] Walking directory tree...
[forefst] 6 dirs, 4 files (4 resident, 0 hard-linked, 0 snapshots)
[forefst] Scanning for orphan objects...
[forefst] 0 orphan OIDs found in Object Table
[forefst] Comparing checkpoint copies...
[forefst] Comparing checkpoints: vclock 45 vs 46
[forefst] 0 OIDs in older checkpoint only
[forefst] Done. 10 entries (0 deleted) -> CSV (stdout)
```

`--deleted` bundles three of the five methods, and on this clean image **all three come up empty —
honestly so**:

- **Method 1 (Trash Table, OID 0x0D):** `0 trashed entries`. The deferred-deletion queue was already
 drained by `TrashCleanerWorkItemMethod` before unmount, so nothing is parked there. See
 [Trash Table](../structures/trash_table.md).
- **Method 3 (orphan OID scan):** `0 orphan OIDs`. No OID appears in a live Object-Table page that is
 absent from the current table — this *OID-level* scan only looks at the Object Table itself, not at
 carved free pages (that is Step 3 below). See [Object Table](../structures/object_table.md).
- **Method 2 (checkpoint differential):** the two checkpoints decode to **vclock 45 vs 46** but
 `0 OIDs in older checkpoint only`. This reproduces finding FS_CHKP_RA_014 exactly: on a cleanly-unmounted
 volume both checkpoints resolve to the **same 13-root pointer list**, so the differential yields
 nothing. A genuine mid-transaction crash capture is required for this method to fire.

So `--deleted` reports `0 deleted` here. That is the correct answer for *these three methods* — it is
**not** the end of the story.

### Step 2 — The strong method: B+-tree node slack (`forefst deleted --slack`, Method 5)

```sh
python3 forefst.py "$IMG" deleted --slack
```

```
── B+-tree Node Slack Scan (Method 5) ──
 Recovering deleted directory entries from metadata-page free space
 (ReFS deletion removes only the row's index slot; the row body persists).
 Scanned 55 live pages + 11 orphan pages with recoverable slack rows

 DELETED (name not in the live tree): 21 [18 with valid timestamps, 3 partial remnants]

 FILE FVE2.{09cf57b8-9e6c-43d4-ae1f-0408882a397d}.1 (resident, live-slack @ cluster 3072 off 0x2e50)
 Created: 2026-05-23 08:46:26 UTC
 Modified: 2026-05-23 08:46:26 UTC
 FILE FVE2.{24e6f0ae-6a00-4f73-984b-75ce9942852d} (resident, live-slack @ cluster 3072 off 0x1dd0)
 Created: 2026-05-23 08:46:26 UTC
 Modified: 2026-05-23 08:46:26 UTC
 FILE FVE2.{c9ca54a3-6983-46b7-8684-a7e5e23499e3}.1 (resident, orphan-slack @ cluster 13316 off 0x968)
 Created: 2026-05-23 08:35:07 UTC
 Modified: 2026-05-23 08:35:40 UTC
 ... (21 deleted entries total) ...

 + 3 partial remnants (name fragment only, no valid timestamps — corroborate before use):
 'FVE2.{b' (live-slack c3072 o0x260)
 'FVE2.{c9ca54a3-6983-46b7-8684-a7e5e23499e3}.3' (live-slack c3072 o0x1c0)
 'FVE2.{e40ad34d-dae9-4bc7-95bd-b16218c10f72}.1' (live-slack c3072 o0x120)

 PRIOR VERSIONS of files still present (CoW slack remnants): 9 [9 with valid timestamps]
 $RECYCLE.BIN (orphan-slack @ cluster 52 off 0x360)
 IndexerVolumeGuid (orphan-slack @ cluster 1540 off 0x80)
 WPSettings.dat (live-slack @ cluster 3072 off 0x378)
 desktop.ini (live-slack @ cluster 14852 off 0x378)
 ... (10 prior-version remnants total) ...
```

This is the recovery payoff. ReFS deletion (`CmsBPlusTable::DeleteFromIndex`) removes only the
deleted row's slot in the page's **offset array** and queues *delayed* compaction — the **row body is
not scrubbed**. So the deleted directory entry's name + inline `$SI` survives in the page's
**node slack** (bytes not referenced by the live offset array) until a later copy-on-write rewrite
reuses the space.

- Each recovered row is a live type-0x30 filename entry decoded out of slack: a filename plus inline
 [`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) carrying the MACB timestamps. The
 `cluster N off 0xNNNN` locator is exactly where the orphaned row body sits.
- **DELETED vs PRIOR VERSIONS** is the load-bearing distinction: a *deleted* row's name is absent from
 the live tree (a real removal); a *prior-version* row is a CoW remnant of a file that **still
 exists** (e.g. `WPSettings.dat`, `desktop.ini` here are live), so it is an old metadata snapshot,
 not a deletion.
- Rows are **confidence-graded**: 18 here have two plausible FILETIMEs (high confidence); 3 are
 **partial remnants** — name fragments from a row whose body was partly overwritten (note `'FVE2.{b'`,
 a truncated name). Per finding FS_DEL_RA_005 the doc records **0 false positives** on the clean baseline.
- **Honest read of the names:** most recovered entries are `FVE2.{...}` BitLocker metadata files
 churned by the encryption step, not the user file the analyst clicked "delete" on in Explorer. The
 Explorer deletion moved that file through `$RECYCLE.BIN` (renamed to `$R...`), so it does not
 resurface here under its original name — a faithful illustration of *what slack actually preserves*
 versus what an analyst hopes to see. The method demonstrably works; the specific yield is
 image-dependent.

This is the **only** method that recovers these rows — confirm that with Step 3.

### Step 3 — The broad method: orphan MSB+ page scan (`deleted --scan-pages`)

```sh
python3 forefst.py "$IMG" deleted --scan-pages
```

```
── Orphaned Page Scan ──
 Current tree references 128 unique physical clusters
 Scanning up to 50000 clusters for orphaned MSB+ pages...
 Found 45 orphaned MSB+ leaf pages
 No deleted file entries found in scanned area
```

The orphan page scan carves `MSB+` leaf pages off the disk and finds **45 orphaned pages** — but
`No deleted file entries`. This is the crucial contrast with Step 2: the orphan scan follows each
page's **live offset array**, so it never sees rows that live only in **slack**. The same 11 orphan
pages that Step 2 mined for slack rows yield nothing here. This is exactly why the docs state the
slack rows are *"recoverable by no other method."*

### Step 4 — Method 4 (stream snapshots) does not apply to this image

The strongest deterministic content path is [`$SNAPSHOT`](../attributes/SNAPSHOT.md) stream-snapshot
recovery. Step 1 already told us this image has `0 snapshots`, and the `*_snapshot_*` token in the
filename was a **VM/disk** snapshot, not a ReFS *file-level* stream snapshot. So Method 4 is
not applicable here — for a real worked snapshot extraction use a v3.14 image bearing ReFS stream snapshots with
`forefst.py <image> snapshots --extract DIR` (MD5-verified up to 21 extents / 13.4 MB).

## What this tells you

- On a **cleanly-unmounted** ReFS volume the three "easy" methods (`forefst files --deleted`: Trash Table,
 orphan-OID, checkpoint diff) correctly return **nothing** — a drained trash queue and converged
 checkpoints are expected, not a parsing failure.
- **B+-tree node slack (Method 5)** is the method that actually recovers deleted directory entries +
 their `$SI` timestamps on this image — 21 deleted rows, confidence-graded, with 3 partials flagged.
- The **orphan page scan (`--scan-pages`) finds the pages but not the rows**, proving the slack scan reaches
 data no other method does.
- Recovery yield is **image-dependent and honest**: most recovered names are BitLocker `FVE2` churn,
 and an Explorer deletion routes the user file through `$RECYCLE.BIN`, so the original filename need
 not reappear. Always corroborate a single slack row (timestamps, neighbours, DELETED-vs-PRIOR flag)
 before relying on it.
- **OID gaps remain permanent deletion evidence** independent of all the above: the volume reports 19
 objects, and any missing OID between present ones is proof of a create-then-delete that survives
 even full page reallocation.

## See also

- [Deletion Recovery](../concepts/deletion_recovery.md) — the five methods in full (Methods 1–5 mapped above)
- [Forensic Analysis Workflow](../concepts/forensic_analysis_workflow.md) — where Step 5 (recover) sits in the 7-stage runbook
- [Copy-on-Write](../concepts/copy_on_write.md) — why deleted/old rows survive in slack and orphan pages
- [Trash Table](../structures/trash_table.md) — Method 1 deferred-deletion queue (OID 0x0D)
- [Object Table](../structures/object_table.md) — Method 3 orphan-OID detection
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the inline MACB timestamps decoded from each recovered row
- [$SNAPSHOT](../attributes/SNAPSHOT.md) — Method 4 deterministic prior-content recovery (not present on this image)
- Master reference: `structure_reference.md` §I (Deleted File Recovery) — §I.1 Trash, §I.3 Orphan scan, §I.4 CoW results
