# Transactional Crash-Consistency

ReFS keeps its metadata consistent across power loss with two cooperating mechanisms:

- a **redo-only metadata log (MLog)** that records committed transactions;
- a **dual checkpoint** whose alternating flush is the commit point of the on-disk tree.

Together they mean a crashed ReFS volume mounts cleanly by replaying the log. They leave a forensic analyst a
decodable record of recent operations and, when the image was taken between two checkpoint writes that changed a
root table, a *previous* on-disk state in the older checkpoint.

This page explains the model and what a crashed-versus-clean volume looks like on disk.

## Redo-only logging, and why there is no undo

ReFS is write-ahead logged but **redo-only** — there is no undo log, and that absence is a design
consequence, not an omission. Metadata is updated by [copy-on-write](copy_on_write.md): a modified
B+-tree page is written to a *new* cluster and the old cluster is left untouched, so an interrupted
transaction never overwrote prior state.

Because nothing was overwritten, there is nothing to roll back: the log only needs to carry *what to re-apply*,
never *what to undo*. This is why the MLog holds no record of what a write replaced, as the NTFS `$LogFile`'s undo
records do (see [NTFS vs ReFS](ntfs_comparison.md)): the prior content of an extent-backed file survives in the old
clusters copy-on-write leaves on disk. A small inline file is different: its bytes are written into the log with the
row that holds them (26100.9444; see below).

Three parts cooperate to make this work:

1. **The MLog** — a circular buffer of LogCore data records, each carrying one or more merged redo
   blocks (on the volumes measured, one transaction per block). Its on-disk format nests four layers; the
   byte layout lives in the [Metadata Log (MLog)](../structures/mlog.md) page. A separate control area
   holds the log start and the log end, each as of its last write; replay does not begin at the log
   start but at the checkpoint's log position (below).

2. **The dual checkpoint (CHKP)** — two checkpoint slots alternate. Each flush writes the **other** slot
   with `clock+1` and points it at the current root tables, so the higher-clock slot is the live state
   and the lower-clock slot is the **previous consistent state** — a rollback target until the next
   flush. The [Checkpoint (CHKP)](../structures/chkp.md) page documents the slot layout; the checkpoint's
   log position sits at **CHKP+0x70**, and that is where replay begins.

3. **The restarter** — `CmsRestarter`, the class that replays the log on mount through
   `CmsLogRedoQueue::PerformRedo`. It is what runs before Windows ever presents the volume to userland.

### The four-layer MLog and the commit point

Each MLog data page is one LogCore record. Past the LogCore record header (Layer 1, 0x78 bytes) and the
entry header (Layer 2), the payload holds a **chain of merged redo blocks** (`_SmsRedoHeader`, Layer 3) —
up to 15 of them, walked by `CmsRestarter::ForEachBlockInMergedBlock` — whose inner **`_SmsRedoRecord`**
entries (Layer 4, ≥ 0x38 bytes each) are the actual operations. Reading only the first block of a payload
loses most of the log: the chain, not the single block, is the unit to walk. The full byte
layout is on the [MLog](../structures/mlog.md) page; the offsets that carry an analyst through a record
are:

```text
_SmsRedoRecord + 0x00   record_size (u32)
_SmsRedoRecord + 0x04   opcode (u32)            <-- dispatched by PerformRedo
_SmsRedoRecord + 0x08   table path length (u32) 0 = applies to the table of the record before it
_SmsRedoRecord + 0x18   virtual clock (u64)     when the record was added
_SmsRedoRecord + 0x20   allocator clock (u64)   when the record was added
_SmsRedoRecord + 0x2C   flags (u32)             bit0 = txn start, bit1 = commit
```

The opcode is read at **record+0x04** (a fixed field, not a scanned position) and dispatched by
`CmsLogRedoQueue::PerformRedo`. On the volumes measured each redo block held the records of one transaction: a start
record (flags bit0) → operations → a commit record (flags bit1); the driver can continue a transaction in a
following block.

What matters is *what* the checkpoint commits: the **on-disk tree changes at the checkpoint flush, not at the log
write**. At mount the restart redoes the log one record at a time (`CmsLogRedoQueue::PerformRedo`, called by
`RedoOneRecord`) and writes a new checkpoint with `CmsRestarter::FlushAndCheckpoint` (from `RedoWorkRoutine` and at the
end of `Restart`; 26100.9444). An operation that reached the log after the last checkpoint is therefore *logged but
not yet in the checkpointed tree* until the next mount replays it — and that gap is what an examiner can read (see
below).

### Replay on mount

```sh
mount:
  pick the higher-virtual-clock CHKP copy that passes its self-checksum (a tie keeps slot 0)
  # self-checksum is cluster-size-dependent: CRC32-C/4B on 4K, CRC64/8B on 64K, SHA-256/32B on SHA-256
  start_lsn = CHKP+0x70   (the chosen checkpoint's log position)
  for each LogCore record from start_lsn forward (LSN at record+0x28):
    if entry type (record+0x78+0x30) == 2 (data record):
      payload = record + le32(record,0x54) + le32(record+le32(record,0x54),0x28)
      for each merged redo block in the payload:   # ForEachBlockInMergedBlock, up to 15
        for each _SmsRedoRecord in the block:      # ForEachRedoInBlock, budget = the block's total_size
          PerformRedo(opcode @ +0x04)              # re-apply the operation
  FlushAndCheckpoint()                             # new consistent commit point (also from the redo work routine)
```

There is **no analysis-then-undo cycle** — only an analysis pass (find dirty pages / the oldest LSN) and
a redo pass. If the higher-clock checkpoint fails its self-checksum, the mount reads the lower-clock valid copy
(`ReadLatestCheckpoint`); if both fail, mount fails with `-0x3fffffce`. The SUPB and the backup VBR are protected by the
same kind of dual-copy fallback — see [Redundancy](redundancy.md), which also
documents why the self-checksum width tracks the cluster size.

## Forensic implications

- **The two checkpoint copies do NOT tell a crashed volume from a clean one.** On the volumes measured the two
  copies' 13 root pointers usually agree element for element, and the clock gap between the two slots is 1 (or 0:
  two valid copies can carry the same clock). `+0x10` equals `+0x60` on every copy measured, so the page-header
  clock separates nothing either. Their agreement is therefore not evidence of a clean dismount.

  **Checkpoint-differential recovery works only where the copies differ** — an image taken between two checkpoint
  writes that changed a root table. It compares Object Table entries between the current and previous checkpoint,
  and objects present in the old but absent from the current were deleted in that window. Where the copies agree
  (the usual case), fall back to orphan-page scanning or CoW version recovery (see
  [Deletion Recovery](deletion_recovery.md)).

- **Logged operations are readable from the MLog, including those not yet checkpointed.** The data area keeps
  every transaction its ring has not yet overwritten, from before the last checkpoint too; operations written after
  the last checkpoint are there as redo records the checkpointed tree does not hold yet. Decoding those entries:
  - the opcode at record+0x04;
  - the table the record's key path names (component 0 is its object id; a record with no path uses the table of
    the record before it);
  - the embedded FILETIMEs carried in InsertRow/UpdateRow value data ([MLog](../structures/mlog.md) documents the
    per-opcode value layout).

  This reconstructs the last operations before the crash, including ones the live checkpoint never committed.

- **The log holds what each write wrote, not what it overwrote.** Redo-only means the MLog carries **no
  pre-images**: no record holds the bytes a write replaced, so do not expect to "undo" a write from the journal.
  Recovery of an extent-backed file's prior *content* comes from what copy-on-write leaves on disk: clusters a live
  map still names (a stream snapshot's, a clone's) and old clusters that are unreferenced but not yet reallocated.
- **A small inline file's bytes can be in the log.** An inline write is logged as the row update that carries the
  file's bytes (read on 26100.9444), and that record outlives the file's deletion until the log reuses its space. On a lab volume, three
  deleted inline files were recovered from the log byte for byte; of the files deleted right after being written,
  almost none left such a record. Whether an earlier version of a modified inline file stays in the log was not
  measured: no log window of the corpus holds an inline file written twice.

  See [Copy-on-Write](copy_on_write.md) and [Deletion Recovery](deletion_recovery.md).

- **Replay has already run by the time you image a *mounted* volume.** Because the driver replays on
  mount, an image taken after Windows mounted the volume reflects the post-replay state: the replayed operations
  are in the tree, and the log no longer shows them ahead of the checkpoint (their records stay in the ring until
  it overwrites them). The not-yet-checkpointed window is visible only on an image captured from a volume that
  crashed and was **never re-mounted**. Image dirty volumes read-only and before any mount.

- **The checkpoint clock is a tamper signal, but not a dirty-volume signal.** The virtual clock at CHKP+0x60
  counts checkpoints (one per flush, not one per operation) and the lower-clock slot is the immediately-prior
  consistent state, so a divergence between the clock and the page-header clock at `+0x10` is a possible-tampering
  indication. A **clock gap does not indicate a dirty volume**: the gap is 1 (or 0) on the volumes measured,
  clean and unclean alike.

  What does carry the signal is the **log position**: on a clean dismount the checkpoint is written last,
  so the highest per-object log position equals the checkpoint's own at `+0x70`; a volume torn away
  mid-work carries objects past it. `forefst summary` reports this and exits 2.

  Its measured scope is narrow: over the corpus images **exactly one** (a lab volume captured
  before a reboot, after an unclean detach) is ahead. So ReFS does not reliably mark a dirty volume anywhere in the
  checkpoint: a negative result means "no evidence of an unclean dismount", never "this volume was cleanly
  dismounted".

## Version and state differences

- **The opcode set grows with version.** The ReFS 3.4 driver (Windows 10 17134) dispatches 29 values
  (0x00–0x1C); the Windows 11 driver (26100) dispatches 44 (0x00–0x2B), and the Insider builds read one or two
  more (0x2C, which calls no handler, and on Insider 29683 0x2D, a table deletion). On both formats 0x12 and 0x15
  call no handler; on 3.14, 0x17 returns NTSTATUS `0xC0000427`, the generic unhandled-opcode error. The v3.4 core
  carries forward almost unchanged (4 renamed, 0x17 became an error, 0 removed); v3.14 adds 0x1D–0x2B (stream,
  table-set, and refcount ops). Two values mean different things in the two tables (0x16 and 0x17), so a log is
  read with its volume format's table. The full dispatch table, per build, is on the [MLog](../structures/mlog.md)
  page.

- **Routing boundary.** The logs of the corpus's 3.7, 3.9 and 3.10 volumes hold only values of the 3.14
  table, 0x1F and 0x20 among them, which the 3.4 table does not have; forefst reads ReFS 3.7 and later with the
  3.14 table. No driver of 3.7–3.13 was read, so the names on those volumes are the 3.14 driver's.

- **The entry-header size is a build discriminator.** The Layer-2 entry header is 56 bytes on v3.4–v3.14
  and 64 bytes on Insider (the payload offset grows 0x38 → 0x40, moving the redo block from record+0xB0
  to record+0xB8). Always dereference the redo block via the offset at record+0x54 rather than a hardcoded
  position, so a parser stays correct across builds.

- **Checkpoint-differential availability does not depend on the version**: it depends on when the image was
  taken (between two checkpoint writes that changed a root table), not on a version flag.

## Tooling

`forefst.py <image> mlog` surfaces the log. The four-layer decode and per-record framing follow the driver, closed
on every block measured on v3.4 and v3.14 volumes, and `mlog` reads the logs of the corpus's v3.4, v3.7, v3.9, v3.10,
v3.14 and Insider volumes:

```sh
forefst.py <image> mlog --parse        # one row per log payload: action, path, time
forefst.py <image> mlog --stats        # opcode histogram (correctly named per version)
forefst.py <image> mlog --csv out.csv  # the same rows as CSV (those with a time are also in `timeline`)
```

For the previous-state side — checkpoint differential (where the copies differ) or CoW version recovery — use the
snapshot and recovery paths in [Snapshots & Versioning](snapshots_versioning.md) and
[Deletion Recovery](deletion_recovery.md).

## Cross-references

- [Metadata Log (MLog)](../structures/mlog.md) — the byte-level four-layer record layout, the control
  page, the per-opcode value layout, and the full per-version opcode tables this page summarizes
- [Checkpoint (CHKP)](../structures/chkp.md) — the dual-slot alternation, the virtual clock at +0x60, and
  the log position at +0x70 where replay begins
- [Copy-on-Write](copy_on_write.md) — why redo-only logging is sufficient, and where prior *content*
  actually survives
- [Redundancy](redundancy.md) — the checkpoint-pair / SUPB / backup-VBR fallback and the
  cluster-size-dependent self-checksum verified at mount
- [Deletion Recovery](deletion_recovery.md) — recovering prior content the log cannot provide
- [Snapshots & Versioning](snapshots_versioning.md) — CoW version recovery
- [NTFS vs ReFS](ntfs_comparison.md) — the contrast with the NTFS `$LogFile`, which *does* carry undo
  pre-images

## Evidence

The replay loop and the commit point are decoded from `CmsLogRedoQueue::RedoWorkRoutine` (refs.sys 26100.9444),
which walks a redo block and dispatches each record to `PerformRedo` through `RedoOneRecord`:

```c
pCVar5 = *(CmsRestarter **)((longlong)param_1 + 0x150);          // the restarter
...
iVar9 = CmsRestarter::ForEachRedoInBlock(..., RedoOneRecord, param_1);   // walk one redo block
...
iVar9 = CmsRestarter::FlushAndCheckpoint(pCVar5, *(undefined8 *)param_1);  // commit = checkpoint flush
```

`CmsRestarter::ForEachRedoInBlock` iterates the inner `_SmsRedoRecord` entries (start at
block+first_record_offset, advance by `record_size`, stop when `remaining < 0x38`). The redo opcode at
`_SmsRedoRecord + 0x04` is the dispatch key, and the LSN-ordered scan reads each record's LSN at
record+0x28. The four-layer record framing, the 56-vs-64-byte entry-header discriminator, and the
per-version opcode counts are decoded from the driver and re-measured on the raw-disk corpus; the CoW
version-recovery results are raw-disk validated.

The counts behind the text:

- the merged-block framing: every block closes under its own `total_size` on `win11refsmini` (364 blocks) and
  `lab314_main_step3_dirty` (75,695 blocks, chains of up to 15), and the last record of each block carries the commit
  flag there and on three v3.4 volumes;
- the checkpoint comparison: the two copies decode to the same root list on the images measured and on 25 of the 26
  volumes of the first blind audit (on its foreign ReFS 3.4 volume five roots differ); the two clocks are equal on
  one "millions of actions" volume (662 / 662);
- the log-position check covered 117 corpus images, of which only `labFbeforereboot` is ahead; the same volume
  after Windows recovered it (`labFafterreboot`) and before the lab (`labBeforeF`) come out equal;
- the 3.7, 3.9 and 3.10 logs of the routing boundary are those of five volumes.

See [how this was verified](../methodology.md) for the method.

<!-- findings: AP_LGFL_RA_012, AP_LGFL_001, AP_LGFL_002, AP_LGFL_005, AP_LGFL_RA_004, AP_LGFL_RA_007, AP_LGFL_RA_008,
               AP_LGFL_RA_009, AP_REDO_001, AP_REDO_002, AP_REDO_003, AP_REDO_004, AP_REDO_005, AP_REDO_006,
               AP_REDO_007, AP_REDO_008, AP_REDO_009, AP_REDO_010, AP_REDO_011, AP_REDO_012, AP_REDO_013,
               AP_REDO_014, AP_REDO_015, AP_REDO_016, AP_REDO_017, AP_REDO_018, AP_REDO_019, AP_REDO_020,
               AP_REDO_021, AP_REDO_022, AP_REDO_023, AP_REDO_024, AP_REDO_025, AP_REDO_026, AP_REDO_027,
               AP_REDO_028, AP_REDO_029, AP_REDO_030, AP_REDO_031, AP_REDO_032, AP_REDO_033, AP_REDO_034,
               AP_REDO_035, AP_REDO_036, AP_REDO_037, AP_REDO_038, AP_REDO_039, FS_CHKP_RA_017, FS_DEL_RA_001,
               FS_SUPB_RA_006 -->
