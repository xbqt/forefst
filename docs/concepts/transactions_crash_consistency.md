# Transactional Crash-Consistency

ReFS keeps its metadata consistent across power loss with two cooperating mechanisms: a **redo-only
metadata log (MLog)** that records committed transactions, and a **dual checkpoint** whose alternating
flush *is* the atomic commit point. Together they mean a crashed ReFS volume mounts cleanly by replaying
the log — and they leave a forensic analyst a small, decodable record of the last operations and, on
dirty volumes, a recoverable *previous* on-disk state. This page explains the model and what a
crashed-versus-clean volume looks like on disk.

## Redo-only logging, and why there is no undo

ReFS is write-ahead logged but **redo-only** — there is no undo log, and that absence is a design
consequence, not an omission. Metadata is updated by [copy-on-write](copy_on_write.md): a modified
B+-tree page is written to a *new* cluster and the old cluster is left untouched until the change
commits, so an interrupted transaction never overwrote prior state in the first place. Because nothing
was clobbered, there is nothing to roll back — the log only needs to carry *what to re-apply*, never
*what to undo*. This is the structural reason the MLog cannot hand you the previous content of a modified
file the way the NTFS `$LogFile` can (see [NTFS vs ReFS](ntfs_comparison.md)): the recovery model puts
prior content in CoW residue, not in the journal.

Three parts cooperate to make this work:

1. **The MLog** — a circular buffer of LogCore data records, each wrapping the redo entries of one
   transaction. Its on-disk format nests four layers; the byte layout lives in the
   [Metadata Log (MLog)](../structures/mlog.md) page. A separate control area holds the head/tail
   pointers and the oldest-log-record bound that decides how far back replay must reach.

2. **The dual checkpoint (CHKP)** — two checkpoint pages alternate. Each flush writes the **other** slot
   with `clock+1` and points it at the current root tables, so the higher-clock slot is the live state
   and the lower-clock slot is the **previous consistent state** — a rollback target until the next
   flush. The [Checkpoint (CHKP)](../structures/chkp.md) page documents the slot layout; the oldest log
   record still needed by the live checkpoint sits at **CHKP+0x70**, and that is where replay begins.

3. **The restarter** — `CmsRestarter`, the class that replays the log on mount through
   `CmsLogRedoQueue::PerformRedo`. It is what runs before Windows ever presents the volume to userland.

### The four-layer MLog and the commit point

Each MLog data page is one LogCore record. Past the LogCore record header (Layer 1, 0x78 bytes) and the
entry header (Layer 2), the payload is a single **redo block** (`_SmsRedoHeader`, Layer 3) whose inner
**`_SmsRedoRecord`** entries (Layer 4, ≥ 0x38 bytes each) are the actual operations. The full byte
layout is on the [MLog](../structures/mlog.md) page; the offsets that carry an analyst through a record
are:

```
_SmsRedoRecord + 0x00   record_size (u32)
_SmsRedoRecord + 0x04   opcode (u32)        <-- dispatched by PerformRedo
_SmsRedoRecord + 0x20   object_id (u64)     target OID
_SmsRedoRecord + 0x2C   flags (u32)         bit0 = txn start, bit1 = commit
```

The opcode is read at **record+0x04** (a fixed field, not a scanned position) and dispatched by `CmsLogRedoQueue::PerformRedo`. A transaction is the records of one redo block: a start
record (flags bit0) → operations → a commit record (flags bit1). The crucial point is *where* commit
actually happens: the **commit point is the checkpoint flush, not the log write**. `PerformRedo` walks
each block with `CmsRestarter::ForEachRedoInBlock` and periodically calls
`CmsRestarter::FlushAndCheckpoint` to atomically swap in the new checkpoint slot. An operation that
reached the log but whose checkpoint flush had not yet landed is therefore *logged but not committed* —
and that gap is precisely the forensic window described below.

### Replay on mount

```
mount:
  pick the higher-virtual-clock CHKP copy that passes its self-checksum
  # self-checksum is cluster-size-dependent: CRC32-C/4B on 4K, CRC64/8B on 64K, SHA-256/32B on SHA-256
  start_lsn = CHKP+0x70   (oldest log record still needed)
  for each LogCore record from start_lsn forward (LSN at record+0x28):
    if entry type (record+0x78+0x30) == 2 (data record):
      redo = record + le32(record,0x54) + le32(record+le32(record,0x54),0x28)
      for each _SmsRedoRecord in the redo block:   # ForEachRedoInBlock
        PerformRedo(opcode @ +0x04)                # re-apply the operation
        FlushAndCheckpoint()                       # new consistent commit point
```

There is **no analysis-then-undo cycle** — only an analysis pass (find dirty pages / the oldest LSN) and
a redo pass. If the higher-clock checkpoint fails its self-checksum, the restarter falls back to the
lower-clock valid copy; if both fail, mount fails with `-0x3fffffce`. This dual-copy fallback is the same
redundancy discipline that protects the SUPB and backup VBR — see [Redundancy](redundancy.md), which also
documents why the self-checksum width tracks the cluster size.

## Forensic implications

- **A crashed volume and a clean volume look different on disk, and the difference is your leverage.**
  After a clean unmount, *both* CHKP copies point at the **same** root tables, so a single-image
  checkpoint comparison yields nothing. On a **dirty/crashed** volume the two checkpoints diverge: the
  lower-clock slot still references the *previous* root tables. This is exactly why
  **checkpoint-differential recovery only works on dirty volumes** — it compares Object Table entries
  between the current and previous checkpoint, and objects present in the old but absent from the current
  were deleted in that window. On a cleanly unmounted image you must instead fall back to orphan-page
  scanning or CoW version recovery (see [Deletion Recovery](deletion_recovery.md)).

- **Uncommitted-but-logged operations are recoverable from the MLog.** Operations written to the log
  whose checkpoint flush had not yet landed are still sitting in the data area as redo records. Decoding
  those entries — opcode at record+0x04, target OID at +0x20, and the embedded FILETIMEs carried in
  InsertRow/UpdateRow value data ([MLog](../structures/mlog.md) documents the per-opcode value layout) —
  reconstructs the last operations before the crash, including ones the live checkpoint never committed.

- **The log proves *what happened*, not *what was overwritten*.** Redo-only means the MLog carries **no
  pre-images**, so it cannot hand you the previous content of a modified file. Recovery of prior *content*
  comes from copy-on-write residue — CoW-protected clusters (refcount ≥ 2) and old clusters that are
  unreferenced but not yet reallocated — not from the log. See [Copy-on-Write](copy_on_write.md) and
  [Deletion Recovery](deletion_recovery.md). Do not expect to "undo" a write from the journal.

- **Replay has already run by the time you image a *mounted* volume.** Because the driver replays on
  mount, an image taken after Windows mounted the volume reflects the post-replay state; the
  uncommitted-transaction window is visible only on an image captured from a volume that crashed and was
  **never re-mounted**. Image dirty volumes read-only and before any mount.

- **The checkpoint clock is an activity and tamper signal.** The virtual clock at CHKP+0x60 increments
  once per flush, and the lower-clock slot is the immediately-prior consistent state. A large clock gap
  between the two slots — or against an expected baseline — indicates the volume was dirty when imaged,
  and is a quick triage flag for whether checkpoint-differential recovery is even available.

## Version and state differences

- **The opcode set grows with version.** v3.4 dispatches 29 values (0x00–0x1C, contiguous, no gaps);
  v3.14 dispatches 44 values (0x00–0x2B), of which only **0x17** is an explicit unhandled-opcode error
  (NTSTATUS `0xC0000427`) — every other in-range value is a real handler. The v3.4 core carries forward
  almost unchanged (4 renamed, 0x17 became an error, 0 removed); v3.14 adds 0x1D–0x2B (stream,
  table-set, and refcount ops). The full per-version dispatch table is on the
  [MLog](../structures/mlog.md) page.

- **Routing boundary.** v3.7–v3.13 emit the v3.14 opcode subset, so they must be decoded with the v3.14
  dispatch table, not the v3.4 one. Choosing the table by major version alone misnames operations on
  these intermediate builds.

- **The entry-header size is a build discriminator.** The Layer-2 entry header is 56 bytes on v3.4–v3.14
  and 64 bytes on Insider (the payload offset grows 0x38 → 0x40, moving the redo block from record+0xB0
  to record+0xB8). Always dereference the redo block via the offset at record+0x54 rather than a hardcoded
  position, so a parser stays correct across builds.

- **Checkpoint-differential availability mirrors the dirty-volume rule across all versions** — it is a
  property of the dual checkpoint, not of a version flag.

## Tooling

`forefst.py <image> mlog` surfaces the log; the four-layer decode and per-record framing are
validated across v3.4, v3.7, v3.9, v3.10, v3.14, and Insider:

```
forefst.py <image> mlog --parse        # decoded transactions: action, path, timestamp
forefst.py <image> mlog --stats        # opcode histogram (correctly named per version)
forefst.py <image> mlog --csv out.csv  # timeline export for super-timeline correlation
```

For the previous-state side — dirty-volume checkpoint differential or CoW version recovery — use the
snapshot and recovery paths in [Snapshots & Versioning](snapshots_versioning.md) and
[Deletion Recovery](deletion_recovery.md).

## Cross-references

- [Metadata Log (MLog)](../structures/mlog.md) — the byte-level four-layer record layout, the control
  page, the per-opcode value layout, and the full per-version opcode tables this page summarizes
- [Checkpoint (CHKP)](../structures/chkp.md) — the dual-slot alternation, the virtual clock at +0x60, and
  the oldest-log-record reference at +0x70 where replay begins
- [Copy-on-Write](copy_on_write.md) — why redo-only logging is sufficient, and where prior *content*
  actually survives
- [Redundancy](redundancy.md) — the checkpoint-pair / SUPB / backup-VBR fallback and the
  cluster-size-dependent self-checksum verified at mount
- [Deletion Recovery](deletion_recovery.md) — recovering prior content the log cannot provide
- [Snapshots & Versioning](snapshots_versioning.md) — CoW version recovery on dirty volumes
- [NTFS vs ReFS](ntfs_comparison.md) — the contrast with the NTFS `$LogFile`, which *does* carry undo
  pre-images

## Evidence

The replay loop and the commit point are both decoded from `CmsLogRedoQueue::PerformRedo` in the Win11
v3.14 driver (E2):

```c
pCVar5 = *(CmsRestarter **)((longlong)param_1 + 0x150);          // the restarter
...
iVar9 = CmsRestarter::ForEachRedoInBlock(...);                   // walk one redo block
...
iVar9 = CmsRestarter::FlushAndCheckpoint(pCVar5, *(undefined8 *)param_1);  // commit = checkpoint flush
```

`CmsRestarter::ForEachRedoInBlock` iterates the inner `_SmsRedoRecord` entries (start at
block+first_record_offset, advance by `record_size`, stop when `remaining < 0x38`). The redo opcode at
`_SmsRedoRecord + 0x04` is the dispatch key, and the LSN-ordered scan reads each record's LSN at
record+0x28. The four-layer record framing, the 56-vs-64-byte entry-header discriminator, and the
per-version opcode counts are decoded from the driver (E2) and re-measured on the raw-disk corpus (RD)
across v3.4 through Insider; the dual-checkpoint divergence on dirty volumes and the CoW-version-recovery
results are raw-disk validated (RD). Findings: **AP_LGFL_RA_004, AP_LGFL_002, AP_LGFL_001, AP_LGFL_RA_007, AP_LGFL_RA_008, AP_REDO_001–039, AP_LGFL_RA_009, AP_LGFL_005, FS_DEL_RA_001**.
See [how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
