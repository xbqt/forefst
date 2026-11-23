# Stream Snapshots and File Versioning

> A stream that has not diverged from its snapshot owns **no allocation of its own** — `DataResidency` reports it as `snapshot-shared`.
>
> See [Record placement and data residency](placement_and_residency.md).

A ReFS stream snapshot freezes a file's current content under a new stream identity, so that later
writes leave the snapshotted bytes intact and exactly recoverable from a single disk image.

For a forensic analyst this is the strongest recovery path on a ReFS volume: unlike carving free space or
diffing checkpoints, the prior version of a versioned file is reconstructed *deterministically*, from
extents that the snapshot explicitly references, so the file system does not free them — for as long as the snapshot
exists (see [how snapshots disappear](#deleting-a-snapshot-refused-by-the-snapshot-interface-done-by-a-delete)).

This page explains how a snapshot is wired into the on-disk structures, why copy-on-write makes the old bytes
survive, and the exact chain an analyst follows to recover them.

## A snapshot is not a separate file

A snapshot is **not** a second file object with its own
OID. Its record is stored in the file's own record; its content sits in clusters that the snapshot's `$DATA`
sub-record lists.

A stream snapshot is an embedded sub-record (`$SNAPSHOT`, type 0xB0) inside the file's record — in
the corpus always its embedded type-0x30 [directory-entry row](../structures/directory_entries.md) — and it points
at a sibling `$DATA` sub-record in that same record which holds the frozen extents. For every snapshot-bearing file
in the corpus, the live version, every snapshot and the metadata linking them sit inside that one name row.

That has a direct consequence for how you reach a snapshotted file: a file has no Object-Table OID of its own
(snapshot-bearing or not), so an OID lookup finds no file. Address it by path (`snapshots --file PATH`), or by its
FileRef (`HomeOID:FileID`).

The link between a `$SNAPSHOT` record and the extents it froze is a stream **sub-id namespace** carried
in the `$DATA` key:

| `data_sub_id` | Meaning |
|---------------|---------|
| `0x1000` | Current (live) file version |
| `0x1001`, `0x1002`, … | Snapshot versions, allocated oldest-first |
| `0x8` | Metadata: the next-sub-id counter |

Each `$SNAPSHOT` value records the `data_sub_id` of the version it captured at `val[0x44]` (u32), the
stream size at snapshot time at `val[0x20]` (u64), and the snapshot creation FILETIME at the unaligned
offset `val[0x4c]`. That `data_sub_id` is matched against `$DATA key[16:20]` to find the frozen extent
set — the whole recovery depends on this join.

```text
embedded type-0x30 name row (the file)
 ├─ $SNAPSHOT sub-record (0xB0, marker 0x80000002, val[0x10]=2)
 │   val[0x44] = data_sub_id ──────────────┐  (0x1001, 0x1002, …)
 │   val[0x20] = stream size at snapshot   │
 │   val[0x4c] = snapshot FILETIME         │
 └─ $DATA sub-record (0x80, descriptor 0x10028)│
     key[16:20] == data_sub_id  ◄────────────┘
     val[ihdr]      = the extent node (ihdr = u32 at val[0x00], typically 0x88)
     val[ihdr+0x14] = row count of the node (a leaf: one row per extent)
     rows, named by the node's index array = {VLCN@+0x00, file_vcn@+0x0C, run_length@+0x14}
```

## Why the prior bytes survive: copy-on-write

A snapshotted file's shared blocks are never overwritten in place: a block is copied to new clusters when it is
about to be overwritten, and the affected B+-tree pages are rewritten, so the snapshot's `$DATA` extents keep
pointing at the *original*, un-rewritten clusters. This is the same update model the
[Copy-on-Write](copy_on_write.md) page describes in full — a stream snapshot is its directly-recoverable
application.

What keeps those original clusters from being recycled is the snapshot's own extent map: it still names them,
so they are not free space. This is why a snapshot offers a stronger guarantee than recovering a deleted
file: the snapshot's bytes are not merely *not yet overwritten*, they are still referenced.

The [Block Refcount table](../structures/block_refcount.md) (root #6, schema 0xe0b0) does **not** record this
sharing: it counts only the references beyond the first that block clones and deduplication make, and a cluster
shared with a snapshot reads 0 there (as does a hard-linked file's). It is therefore not a test of whether a version
will reconstruct; the snapshot's extent map is that test.

### The consequence: no single stream is a complete block map

Because only the *changed* blocks are rewritten, the live version's extent list ends up covering **only what
has been written since the last snapshot**. Everything untouched is still described by the snapshot's list,
and the cluster is shared rather than duplicated. Neither list, on its own, describes the whole file.

The stream record says so directly, in two fields that are easy to confuse:

| field | means |
|-------|-------|
| **allocated size for this stream** | what *this* version owns — the bytes its own extent list covers |
| **total allocated size** | the **file's** whole allocation, including the blocks it shares |

A file that was modified after a snapshot usually shows the second larger than the first.

One lab file reports a 22,688-byte stream with a 24,576-byte total allocation but only 8,192 bytes of its own —
its own extent list covers file blocks (VCNs) 4 and 5. Blocks 0–2 are held by the first snapshot and block 3 by
the second.

So **reading any version means resolving each block position across the versions**, which is what the driver
does on an ordinary read:

- for the **live** version, a block it does not own comes from the **most recent** snapshot that holds it — a
  block only drops out of the live list while it has not changed since;
- for a **prior** version, only snapshots **older** than it may be used; a newer one can hold bytes written
  after the version you are recovering;
- a position no version holds is a genuine **sparse hole**, and reads as zeros.

Nothing here is reconstructed or inferred: every block comes from a real cluster that a version's extent map
names. Reading only one version's own extents produces a file of the right *length* whose shared regions
are zeros — bytes that are not on the volume at all.

## The recovery chain

From the file's embedded name row, recovery proceeds in four steps:

1. Read each `$SNAPSHOT` sub-record: the `data_sub_id` (`val[0x44]`), the stream size at snapshot time
   (`val[0x20]`), and the snapshot FILETIME (`val[0x4c]`).
2. Find the `$DATA` sub-record whose `key+0x10 == data_sub_id`. It is the extent form (inner-header offset at
   `val[0x00]`, typically 0x88), which never holds inline bytes. Its allocation at `val[0x48]` is what this version
   owns. At `val[ihdr]` sits the extent node: its row count at `+0x14`, its rows named by its index array (see
   [Extent Records](../structures/extent_descriptors.md)).
3. Place each run at its `file_vcn` × the cluster size, translating each VLCN → PLCN through the
   [Container Table](../structures/container_table.md) (mandatory — the VLCN in an extent is a virtual address,
   see [Virtual Addressing](virtual_addressing.md)). Leave flagged holes as zeros, fill every block this version
   does not own from the newest snapshot strictly older than it, and trim to the recorded stream size.
4. The **current** version is `data_sub_id = 0x1000`. If its record is the extent form with allocation `0`, its
   bytes are the newest snapshot's (`snapshot-shared`): read them through the snapshots as in step 3. The inline
   form is a different record (summary size 0x30, bytes at +0x3C).

The snapshot extents use the **same row format as a live file's extent map**: VLCN at `+0x00`, flags (u16) at
`+0x08`, row size (u16) at `+0x0A`, `file_vcn` at `+0x0C`, `run_length` at `+0x14` — 24 bytes, or 24 + 4 × run with
per-cluster CRCs. The format is the same because the driver routes snapshot/CoW `$DATA` reads through the same
allocation lookup as ordinary file reads, so standard Container-Table resolution recovers the content unchanged. The
full byte-level walk of the embedded headers is on the [$SNAPSHOT attribute](../attributes/SNAPSHOT.md) page.

## Forensic implications

- **Exact prior-content recovery from a single image.** This is deletion-recovery **Method 4** (see
  [Deletion Recovery](deletion_recovery.md)) — the most deterministic single-image path. Unlike the
  orphan-page scan or the checkpoint differential, it does not depend on superseded pages surviving: the
  snapshot extents are explicitly referenced by the snapshot's record. Recovery is verified byte-for-byte against
  independent ground truth: every prior version of a lab file family against the generator's specification, the
  lab files against the operator's hashes, and a multi-megabyte, multi-extent version.

- **A timestamped history of every snapshotted version.** Multiple snapshots on one file reconstruct an ordered
  version history, each version stamped by its own `val[0x4c]` FILETIME — distinct from the file's `$SI`
  timestamps. A short worked example: a file with four versions might recover as v1 = 42 bytes of `a`,
  v2 = 65 bytes (`a`+`b`), v3 = 92 bytes (`a`+`b`+`c`), and the live version = `abc\r\n`, all from one
  image with each version's creation time read straight from its snapshot record. Unlike the change journal,
  which records when a file was written but not what it held, a snapshot keeps the content of each snapshotted
  version.

- **Do not confuse snapshots with Alternate Data Streams.** Type 0xB0 serves *both* stream snapshots and
  ADS. The discriminator is `val[0x10]`, the StreamSummary flag: **`2` = snapshot, `0` = ADS**.
  `data_sub_id` is **not** one: an ADS's sub-id also falls in `0x1000–0xFFFF`, so a range test on it admits
  alternate streams as snapshots — measured over five volumes, every row it admits beyond the flag test
  is an ADS, none a snapshot. The flag is corroborated by the `val[0x02]` attribute flags (a snapshot sets
  `0x1C00`, with bit `0x0400` = HasSnapshot). The u32 at `val[0x38]` is **not** a discriminator: it is the stream's
  integrity/checksum-type selector — `0x02` on None/CRC64 volumes and `0x04` on SHA-256 volumes — so it
  follows the volume's checksum configuration rather than the snapshot/ADS distinction and is useless for
  this purpose. Mislabeling an ADS row as a snapshot, or the reverse, corrupts both the version count and
  the recovery target.

- **No snapshot-count limit was found** in the snapshot-creation code read (26100.9444). A file with N snapshots carries
  at least 2N+2 embedded sub-records (the live `$DATA` row, one `$SNAPSHOT` row and one `$DATA` row per version, and the
  0x8 counter row); the embedded-row count at `value+0x20` is an unbounded count, not a fixed enum. A row count of 4–6
  is a common "has snapshots" signal but never a ceiling — treat it as a hint to inspect, not a count.

## Version and state differences

The stream-snapshot code is in the 26100 and Insider drivers read and not in the 3.4 driver (17134); no 3.7 to 3.10
driver is held, so the first driver with it is not known; snapshot entries are seen only on 3.14 volumes of the corpus. v3.4 volumes have no
stream snapshots at all (their type-0xB0 rows are alternate data streams).

The `$SNAPSHOT` *value* format is the same on every snapshot entry measured; only the embedded sub-record **key**
layout differs by version — v3.4-era keys carry no instance markers, while v3.7+ keys place markers at `key[8:12]`.

The Block Refcount table (root #6, schema 0xe0b0) and its empty B+-tree exist since **v3.4**; it gains
rows only where a block clone, the deduplication path or another of the count's few writers raised a count, and two
volumes with snapshots hold none. Stream-snapshot recovery does
not use it — the `$SNAPSHOT` → `$DATA` chain is self-contained and resolves on its own, and a snapshot adds no count
there.

## Tooling

`forefst.py <image> snapshots --show --file '<path>'` previews each recovered version of a file;
`--extract DIR` writes every version to disk. The implementation follows the rule under
[no single stream is a complete block map](#the-consequence-no-single-stream-is-a-complete-block-map): each block at
its own position, unowned blocks from the older snapshots. It is validated byte-for-byte against independent ground
truth (every prior version of a lab file family against the generator's specification, and lab files against the
operator's hashes).

## Cross-references

- [Driver Evolution](driver_evolution.md) — taking a stream snapshot moves an inline stream's bytes into the
  snapshot's extents and leaves the live stream snapshot-shared
- [Copy-on-Write](copy_on_write.md) — the update model that keeps snapshot extents intact, and the other things
  copy-on-write leaves on disk
- [Deletion Recovery](deletion_recovery.md) — stream snapshots are **Method 4**, the strongest
  single-image exact-content path
- [$SNAPSHOT attribute](../attributes/SNAPSHOT.md) — the type-0xB0 value layout and the byte-level
  snapshot-vs-ADS discrimination
- [Block Refcount Table](../structures/block_refcount.md) — the clone and deduplication counts (root #6, schema
  0xe0b0), which a snapshot does not add to
- [Container Table](../structures/container_table.md) — the VLCN → PLCN map required to read snapshot
  extents off disk
- [Virtual Addressing](virtual_addressing.md) — why the VLCN in a snapshot extent is virtual and must be
  translated before any disk read
- [Directory Entries](../structures/directory_entries.md) — the embedded type-0x30 name row that holds the
  snapshot chain

## Evidence

The snapshot is created by `RefsCreateStreamSnapshot`, which builds the StreamSummary, sets the snapshot
flag, and stamps the stream-set id and FILETIME; `GetResidentStreamSummaryFromDisk` and
`SetResidentStreamSummary` read back and persist the on-disk layout the recovery chain walks (E2).

The metadata update path is copy-on-write: `MsUpdateDataWithRoot` — leaf allocate, parent copy, root propagation,
checkpoint (E2). For a snapshotted file's data, a block is copied to new clusters when it is about to be
overwritten, so the snapshot's extents keep the old ones (RD). Snapshot/CoW `$DATA` reads share the ordinary
file-read allocation routine `CmsStream::LookupAllocation`, which is why the extent row format is identical to a
live file's (E2).

Block-refcount maintenance is `IncrementRefcount` / `DecrementRefcount` against the table built by
`CmsBlockRefcount::Initialize`; `DecrementRefcount` is the v3.4 symbol. The v3.14 builds expose only
`IncrementRefcount`; on 26100.8115 a count is lowered by a decrement operation of the refcount cache's update
routine, which raises `MsKmeBlockRefCountUnderflowEventNotification` when it meets a count of 0. The value-layout
offsets, the `data_sub_id` namespace, the snapshot-vs-ADS discriminators, and byte-for-byte content recovery are
raw-disk verified (RD). Each is a registered finding.

The counts behind the text: the two allocation fields differ on 39 of the 54 stream records with snapshots
measured; the ground truth is 8 of 8 current files and 20 of 20 prior versions of one lab file family against the
generator's specification, the lab volumes' snapshot files against the operator's hashes, and a 3,202,036-byte
version in 8 extents.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.

## Deleting a snapshot: refused by the snapshot interface, done by a delete

The snapshot interface does not delete a stream snapshot; deleting the file does.

`RefsStreamSnapshotManagement` (**refs.sys 10.0.26100.8115, `1400c3cfc`**) is the FSCTL entry point, and
it dispatches on the request's operation code:

| op | outcome |
|---:|---|
| 1 | `RefsCreateStreamSnapshot` |
| 2 | `RefsListStreamSnapshots` |
| 3 | `RefsQueryDeltasStreamSnapshot` |
| **4, 5, 6** | **`0xC0000002` — `STATUS_NOT_IMPLEMENTED`** |

All three of the remaining operations take the same branch and return the same status; the function does
not attempt the work and then fail, it declines to start.

The capability itself is not missing. `MsDeleteStreamSnapshot` (**same build, `1400ecec8`**) is a short function:
it prepares the stream set's entry for merging (`CmsTableSetBase::PrepareEntryForMerge`) and queues the merge in
the Trash table (`CmsTrashTable::AddTableSetMergeFinish`). `DeleteAttribute` calls it when the attribute it deletes
is a stream kept in a stream set (attribute flags bit 0x1000), so deleting the file removes its snapshots with it.

**Why this matters for an examiner.** The snapshot FSCTL declines operations 4, 5 and 6, but snapshots do
disappear:

- deleting a snapshotted file removes its snapshots (in the lab, a deleted snapshotted file left metadata only);
- a file snapshotted while inline and then rewritten past 2 KiB (format 3.14) kept no snapshot record (see
  [Record placement and data residency](placement_and_residency.md#a-snapshot-changes-what-residency-reports)).

So the absence of snapshots does not show that none were taken. The FSCTL's refusal was read on *this*
build: another build can accept the operation by changing only its dispatch table.

<!-- findings: AP_LGFL_005, CT_BKRC_001, CT_DRNT_RA_001, FS_CHKP_015, FS_OTBL_RA_008, FS_SCHM_RA_005,
               FS_SCHM_RA_008, FS_SNAP_RA_001, GN_ARCH_002, GN_SNAP_SA_001, MD_ATTR_RA_018, MD_SNAP_RA_001,
               MD_SNAP_RA_002, MD_SNAP_RA_003, MD_SNAP_RA_005, MD_SNAP_RA_006, MD_SNAP_RA_007, MD_SNAP_RA_008 -->
