# Stream Snapshots and File Versioning

A ReFS stream snapshot freezes a file's current content under a new stream identity, so that later
writes leave the snapshotted bytes intact and exactly recoverable from a single disk image. For a
forensic analyst this is the strongest recovery path on a ReFS volume: unlike carving free space or
diffing checkpoints, the prior version of a versioned file is reconstructed *deterministically*, from
explicitly-referenced extents that the file system has committed to keep alive. This page explains how a
snapshot is wired into the on-disk structures, why copy-on-write makes the old bytes survive, and the
exact chain an analyst follows to recover them.

## A snapshot is not a separate file

The first thing to understand is where a snapshot lives. It is **not** a second file object with its own
OID, and it is **not** stored elsewhere on the volume. A stream snapshot is an embedded sub-record
(`$SNAPSHOT`, type 0xB0 / schema 0x1B0) inside the file's **resident** type-0x30
[directory-entry row](../structures/directory_entries.md), and it points at a sibling `$DATA` sub-record
in that same row which holds the frozen extents. Everything — the live version, every snapshot, and the
metadata linking them — sits inside the one parent directory row.

That has a direct consequence for how you reach a snapshotted file: because the whole chain is resident
inside the parent directory's type-0x30 value, the file is addressed by `(parent_oid, filename)` — a
path — and **not** by an Object-Table OID, since resident files have no own OID. A tooling lookup keyed
on `--oid` will miss them; use a path-based lookup.

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
set — this is the join that drives the whole recovery.

```
resident type-0x30 row (the file)
 ├─ $SNAPSHOT sub-record (0xB0, marker 0x80000002, val[0x10]=2)
 │   val[0x44] = data_sub_id ──────────────┐  (0x1001, 0x1002, …)
 │   val[0x20] = stream size at snapshot   │
 │   val[0x4c] = snapshot FILETIME         │
 └─ $DATA sub-record (0x80, descriptor 0x10028)│
     key[16:20] == data_sub_id  ◄────────────┘
     val[ihdr+0x14] = extent_count
     val[ihdr+0x28] = 24-byte extents {VLCN@+0x00, file_vcn@+0x0C, run_length@+0x14}
```

## Why the prior bytes survive: copy-on-write and refcount sharing

ReFS never overwrites data in place. A write to a snapshotted file allocates new clusters and rewrites
the affected B+-tree pages, so the snapshot's `$DATA` extents keep pointing at the *original*,
un-rewritten clusters. This is the same update model the [Copy-on-Write](copy_on_write.md) page describes
in full — a stream snapshot is its directly-recoverable application.

What keeps those original clusters from being recycled is **block reference-count sharing**. A cluster
range referenced by both the live version and a snapshot carries a refcount `>= 2` in the
[Block Refcount table](../structures/block_refcount.md) (root #6, schema 0xe0b0), and a refcount above 1
tells the allocator the range is still in use, so it is never reclaimed. In the deletion-recovery model
a refcount `>= 2` is the **guaranteed-survival** category: the cluster is alive precisely because more
than one object — here, a version — points at it. This is why a snapshot offers a stronger guarantee
than recovering a deleted file: the snapshot's bytes are not merely *not yet overwritten*, they are
*pinned*.

The refcount also doubles as a triage signal before extraction. A cluster range with refcount `>= 2`
(bit 15 clear) is a normal multi-reference — a snapshot, a hard link, or a block clone — and is
guaranteed intact; clusters with refcount `0` survive only until the allocator reuses them. So a refcount
check distinguishes "this version will reconstruct byte-for-byte" from "this is opportunistic salvage."

## The recovery chain

From the resident type-0x30 row, recovery proceeds in four steps:

1. Read each `$SNAPSHOT` sub-record: the `data_sub_id` (`val[0x44]`), the stream size at snapshot time
   (`val[0x20]`), and the snapshot FILETIME (`val[0x4c]`).
2. Find the `$DATA` sub-record whose `key+0x10 == data_sub_id`. Its inner-header offset is at `val[0x00]`
   (typically 0x88); the on-disk allocation at `val[0x48]` decides residency — `0` means the content is
   **inline** in the 0x30 body (typical of the current version), `> 0` means the content is non-resident
   and follows extents. The extent count is at `val[ihdr+0x14]` and the 24-byte extents begin at
   `val[ihdr+0x28]`.
3. Sort the extents by `file_vcn`, translate each VLCN → PLCN through the
   [Container Table](../structures/container_table.md) (mandatory — the VLCN in an extent is a virtual
   address, see [Virtual Addressing](virtual_addressing.md)), read `run_length` clusters per extent,
   concatenate, and trim to the recorded stream size.
4. The **current** version is `data_sub_id = 0x1000`; if its allocation is `0` the live content is inline,
   otherwise it follows the same extent chain.

The snapshot extents use the **identical 24-byte format as ordinary non-resident type-0x40 data runs**:
VLCN at `+0x00`, flags at `+0x08`, `file_vcn` at `+0x0C`, `run_length` at `+0x14`. That is not a
coincidence — the driver routes snapshot/CoW `$DATA` reads through the same allocation lookup as ordinary
file reads, so standard Container-Table resolution recovers the content unchanged. The full byte-level
walk of the embedded headers is on the [$SNAPSHOT attribute](../attributes/SNAPSHOT.md) page.

## Forensic implications

- **Exact prior-content recovery from a single image.** This is deletion-recovery **Method 4** (see
  [Deletion Recovery](deletion_recovery.md)) — the most deterministic single-image path. Unlike the
  orphan-page scan or the checkpoint differential, it does not depend on superseded pages surviving: the
  snapshot extents are explicitly referenced and refcount-pinned. Recovery has been verified
  byte-for-byte (MD5-identical to an independent export) on multi-extent, multi-megabyte chains across
  several volumes.

- **A complete, timestamped edit history.** Multiple snapshots on one file reconstruct an ordered
  version history, each version stamped by its own `val[0x4c]` FILETIME — distinct from the file's `$SI`
  timestamps. A short worked example: a file with four versions might recover as v1 = 42 bytes of `a`,
  v2 = 65 bytes (`a`+`b`), v3 = 92 bytes (`a`+`b`+`c`), and the live version = `abc\r\n`, all from one
  image with each version's creation time read straight from its snapshot record. This is the closest
  ReFS comes to handing the analyst a file's editing timeline.

- **Do not confuse snapshots with Alternate Data Streams.** Type 0xB0 serves *both* stream snapshots and
  ADS. The reliable discriminator is `data_sub_id`: a value in `0x1000–0xFFFF` is a true snapshot, an
  ASCII/named stream is an ADS. This is corroborated by `val[0x10]` (the StreamSummary flag: `2` =
  snapshot, `0` = ADS) and by the `val[0x02]` attribute flags (a snapshot sets `0x1C00`, with bit
  `0x0400` = HasSnapshot). The u32 at `val[0x38]` is **not** a discriminator: it is the stream's
  integrity/checksum-type selector — `0x02` on None/CRC64 volumes and `0x04` on SHA-256 volumes — so it
  follows the volume's checksum configuration rather than the snapshot/ADS distinction and is useless for
  this purpose. Mislabeling an ADS row as a snapshot, or the reverse, corrupts both the version count and
  the recovery target.

- **Snapshot count is bounded only by the file.** A file with N snapshots carries at least N+2 embedded
  sub-records (1 live `$DATA`, one `$SNAPSHOT` per version, plus a metadata row); the embedded-row count
  at `value+0x20` is an unbounded count, not a fixed enum. A row count of 4–6 is a common "has snapshots"
  signal but never a ceiling — treat it as a hint to inspect, not a count.

## Version and state differences

`$SNAPSHOT` / schema 0x1B0 is gated **v3.7+** (the version-gating matrix lists 0x1B0 as present from v3.7
through Insider). v3.4 volumes have no `$SNAPSHOT` attribute at all. The `$SNAPSHOT` *value* formats are
otherwise identical across v3.7 to Insider; only the embedded sub-record **key** layout differs by
version — v3.4-era keys carry no instance markers, while v3.7+ keys place markers at `key[8:12]`.

The Block Refcount table (root #6, schema 0xe0b0) and its empty B+-tree exist since **v3.4**, but the
table is only *populated* on v3.14 volumes with sharing activity. Stream-snapshot recovery does not
require a populated refcount table — the `$SNAPSHOT` → `$DATA` chain is self-contained and resolves on
its own — but where refcount data is present, a refcount `>= 2` confirms the "guaranteed survival"
classification.

## Tooling

`forefst.py <image> snapshots --show --file '<path>'` previews each recovered version of a file;
`--extract DIR` writes every version to disk. The implementation re-derives the chain above and was
validated MD5-identical to an independent export.

## Cross-references

- [Copy-on-Write](copy_on_write.md) — the update model that keeps snapshot extents intact; the canonical
  recovery-chain walk-through and the refcount-survival categories
- [Deletion Recovery](deletion_recovery.md) — stream snapshots are **Method 4**, the strongest
  single-image exact-content path
- [$SNAPSHOT attribute](../attributes/SNAPSHOT.md) — the 0xB0 / schema 0x1B0 value layout and the byte-level
  snapshot-vs-ADS discrimination
- [Block Refcount Table](../structures/block_refcount.md) — the refcount `>= 2` sharing that pins snapshot
  clusters against reuse (root #6, schema 0xe0b0)
- [Container Table](../structures/container_table.md) — the VLCN → PLCN map required to read snapshot
  extents off disk
- [Virtual Addressing](virtual_addressing.md) — why the VLCN in a snapshot extent is virtual and must be
  translated before any disk read
- [Directory Entries](../structures/directory_entries.md) — the resident type-0x30 row that holds the whole
  snapshot chain

## Evidence

The snapshot is created by `RefsCreateStreamSnapshot`, which builds the StreamSummary, sets the snapshot
flag, and stamps the stream-set id and FILETIME; `GetResidentStreamSummaryFromDisk` and
`SetResidentStreamSummary` read back and persist the on-disk layout the recovery chain walks (E2;
finding MD_SNAP_RA_002, MD_SNAP_RA_003, CT_DRNT_RA_001, GN_SNAP_SA_001). The CoW write path that frees the newly-allocated clusters while leaving the snapshot
extents in place is `MsUpdateDataWithRoot` — leaf allocate, parent copy, root propagation, checkpoint
(E2; findings GN_ARCH_002, AP_LGFL_005). Snapshot/CoW `$DATA` reads share the ordinary file-read allocation routine
`CmsStream::LookupAllocation`, which is why the 24-byte extent format is identical to type-0x40 runs (E2).
Block-refcount maintenance is `IncrementRefcount` / `DecrementRefcount` against the table built by
`CmsBlockRefcount::Initialize`; `DecrementRefcount` is the v3.4 symbol, while v3.14 builds expose only
`IncrementRefcount` and handle refcount-down via a signed delta (with
`MsKmeBlockRefCountUnderflowEventNotification`). The value-layout offsets, the `data_sub_id` namespace,
the snapshot-vs-ADS discriminators, and byte-for-byte content recovery are raw-disk verified (RD).
Findings: MD_SNAP_RA_002, MD_SNAP_RA_003, CT_DRNT_RA_001, GN_SNAP_SA_001, MD_SNAP_RA_006, MD_SNAP_RA_005, FS_SNAP_RA_001, MD_SNAP_RA_007, MD_ATTR_RA_018, FS_OTBL_RA_008, FS_CHKP_015, CT_BKRC_001, FS_SCHM_RA_008, FS_SCHM_RA_005. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
