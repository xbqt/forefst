# Record placement and data residency

Every ReFS file has two storage properties, and each is independent of the other:

- **Record placement**: where the file's *record* is stored. The record holds the file's `$STANDARD_INFORMATION`
  and its attributes. It is either **embedded** in the file's name row in its directory, or **split** out of the
  name row into a separate backing record (row type 0x40) in the file's home directory.
- **Data residency**: where the file's *bytes* are stored. They are either **inline**, inside the record itself, or
  in **extents**: clusters elsewhere on the volume, listed by an extent map in the record.

A statement about one property says nothing about the other. A 149 MiB file can have an embedded record (its bytes in
extents), and a hard-linked file, whose record is split, can keep its bytes inline.

forefst prints the two properties as two columns:

| Property | Column | Values |
|---|---|---|
| Where the record is | `RecordPlacement` | `embedded` · `split` |
| Where the bytes are | `DataResidency` | `inline` · `extents` · `snapshot-shared` · `unallocated` |

- `snapshot-shared`: the stream owns no clusters of its own; its bytes are still those of a stream snapshot.
- `unallocated`: the stream owns no clusters and no snapshot holds them; it reads as zero.
- `DataResidency` reads `unknown` when no `$DATA` record can be read, and is blank for a directory.

The tool and these pages use these two names, not the single word "resident", which would name both.

## The two properties side by side

```
  RECORD PLACEMENT                          DATA RESIDENCY
  ────────────────                          ──────────────

  embedded                                  inline
  ┌─ directory B+-tree ─────────┐           ┌─ the record ────────────┐
  │ name row ─┬─ the record     │           │ $DATA ─┬─ length        │
  │           └─ …              │           │        └─ THE BYTES     │
  └─────────────────────────────┘           └─────────────────────────┘

  split                                     extents
  ┌─ directory B+-tree ─────────┐           ┌─ the record ────────────┐      ┌─ disk ───┐
  │ name row ── points to ──┐   │           │ $DATA ─┬─ length        │  ──▶ │ clusters │
  └─────────────────────────┼───┘           │        └─ an extent list│      └──────────┘
  ┌─ backing record (0x40) ◀┘   │           └─────────────────────────┘
  │ the record lives here       │           snapshot-shared → no allocation of its own;
  └─────────────────────────────┘             the bytes are still the snapshot's
                                            unallocated → no allocation, no snapshot: reads as zero
```

Both combinations happen on ordinary volumes, in quantity: an embedded record with its bytes in extents, and a split
record with its bytes inline. (`snapshot-shared` and `unallocated` have so far been seen only on embedded records.)

## Record placement: embedded or split

The name row's key says which: the `key_flags` u16 at key offset 0x02 takes only two values on disk.

| key_flags | The name row is | Value size |
|-----------|-----------------|------------|
| **0x01** | an **embedded record**: the file's own record follows in this row | more than 84 bytes |
| **0x02** | an **index entry**: a fixed set of cached fields and a pointer to the record, split out into a type-0x40 backing record in the file's home directory | 84 bytes, or 72: the writing driver and the volume's format decide, so take the size from the row |

- `key_flags` says where the record is, **not** where the data is. Reading 0x01 as "resident" and 0x02 as
  "non-resident" is the most common misreading of this field.
- A directory is always stored with key_flags 0x02. It is told apart from a split *file* only by the directory
  attribute bit `0x10000000` in the index entry's attributes (value+0x40).
- There is no third value (no "0x04 = directory" flag).

What splits a record:

- On a volume with hard-link support (boot-sector flag 0x20: on the corpus, every volume formatted at 3.7 or later but one), a cross-directory
  move or a hard link splits the record. A rename within the same directory does not. The 26100 and Insider drivers can
  also split a record on their POSIX-delete and rename-replace paths.
- On a volume without hard-link support (measured on volumes formatted at 3.4 and those upgraded from them), a move carries the
  whole embedded record to the new directory, so the record stays embedded; the 3.4 volumes measured hold no
  type-0x40 rows.
- A split is never undone: a file moved back to its first directory keeps its split record.

So on a file, `split` is a strong indication that the file was moved or hard-linked at some point. It is not a sign
of tampering: both operations are ordinary.

## Data residency: inline or in extents

The rule depends on the volume's format and on the kind of stream:

| Stream | format 3.10 and earlier | format 3.11 and later |
|---|---|---|
| main `$DATA` | **never inline**: even a 5-byte file gets a whole cluster | inline below **2 KiB**; in extents from 2 KiB |
| named stream (ADS) | inline, up to a hard **128 KiB** cap (past it the write fails) | inline below 2 KiB; in extents from 2 KiB |

- The 2 KiB boundary is **fixed**: it does not depend on the cluster size or the sector size (a 1,900-byte stream
  is inline and a 2,100-byte one is in extents on 4 KiB and 64 KiB clusters and on a 4Kn disk alike; on 64 KiB
  clusters that 2,100-byte stream occupies a whole cluster).
- It is the **volume's format** that decides, not the driver's build: a newer driver writes by the older rule as long
  as the volume stays at the older format.
- The change runs **one way**: no driver read can bring a stream back inline. A file grown to 3,000 bytes and
  truncated back to 0 stays in extents; a file that never held data is inline. History decides, not size.

On format 3.11 and later, a stream below 2 KiB is in extents when one of these converted it:

- a **stream snapshot**;
- a block clone (`RefsDuplicateExtents`), or replacing the data attribute;
- **encryption**;
- remote / tiering storage, or strictly-sequential mode;
- an allocation or end of file of **2 KiB or more** set on it (on format 3.11 and later; a smaller one leaves it
  inline);
- a write past 2 KiB.

Two things are **not** conversions:

- **Integrity streams.** Enabling integrity on an existing inline stream leaves it inline. A file *created* in a
  directory that already has integrity on is extent-backed from birth, with a whole cluster even for 512 bytes.
- **A move or a hard link.** They relocate the record (splitting it, on a volume with hard-link support) and move no
  data at all.

An upgrade converts nothing: on a volume upgraded from 3.4 to 3.14, no file that existed before the upgrade changed
residency. Only later writes follow the new format's rule.

## One file, through four states

The same file, as operations happen to it, with the two column values beside each state. No operation changes both.

```
                                              RecordPlacement   DataResidency
  ┌────────────────────────────────────────┐
  │ 1. created, 600 bytes                  │      embedded    ·    inline
  │    record in the name row,             │
  │    bytes inside that record            │
  └───────────────┬────────────────────────┘
                  │  write past the format-3.11+ ceiling ── residency only
  ┌───────────────▼────────────────────────┐
  │ 2. grown to 60 KiB                     │      embedded    ·    extents
  │    record unmoved; the bytes are now   │                       ▲
  │    on disk, described by an extent list│                    changed
  └───────────────┬────────────────────────┘
                  │  moved to another directory          ── placement only
  ┌───────────────▼────────────────────────┐
  │ 3. moved                               │       split      ·    extents
  │    the record is split out into a      │        ▲
  │    backing record; NO data moved       │     changed
  └───────────────┬────────────────────────┘
                  │  snapshot taken, file not written    ── residency only
  ┌───────────────▼────────────────────────┐
  │ 4. snapshotted, untouched since        │       split      · snapshot-shared
  │    owns no allocation of its own;      │                       ▲
  │    the bytes are still the snapshot's  │                    changed
  └────────────────────────────────────────┘
```

- The step-1→2 ceiling is the 2 KiB limit of format 3.11 and later; on format 3.10 and earlier a file's main data
  starts at step 2.
- Truncating back to 0 bytes would not return it to `inline`. Renaming it at any step changes neither value.
- Step 4's combination (a split record whose stream is snapshot-shared) follows from the rules; on the volumes
  measured, every snapshot-shared stream was on an embedded record.

## What changes what

| Operation | `RecordPlacement` | `DataResidency` |
|---|---|---|
| Create a small file | `embedded` | `inline` (format 3.11 and later; exceptions above) |
| Grow it past the inline ceiling | unchanged | `inline` → `extents` |
| Truncate it back to 0 | unchanged | **stays `extents`** |
| **Move it to another directory** | `embedded` → **`split`** | **unchanged** |
| **Add a hard link** | `embedded` → **`split`** | **unchanged** |
| Rename in place | unchanged | unchanged |
| Take a snapshot, then read (not write) | unchanged | `inline` or `extents` → `snapshot-shared` |
| Write to a snapshot-shared file | unchanged | `snapshot-shared` → `extents` |

- The rows in bold: a move or a hard link relocates the record and moves no data.
- They are measured on format 3.14 volumes with hard-link support. Without it, a move keeps the record embedded
  (above).
- The record does not show whether a rename came before or after a move: both orders end in the same state; only the
  change journal can separate them.

## A snapshot changes what residency reports

Residency does not follow from size alone. Take a stream snapshot of a small file and leave the file untouched: its
live stream stops reporting `inline` and reports `snapshot-shared`, because it now owns no allocation of its own; the
bytes are the snapshot's. This was measured on format 3.14 with a 600-byte file, far below the 2 KiB ceiling.

- So `snapshot-shared` is not reserved for large files, and a file can change its reported state without any write.
- A file snapshotted while inline and then rewritten whole at a size past the ceiling (the lab used `WriteAllBytes`,
  which truncates and rewrites the file) kept **no snapshot record**. Whether growing a file alone loses its snapshot
  was not tested.

## Seven files, measured

The size, placement and residency cells are generated from the shipped sample volumes with `files --csv` and
re-checked on every release, so they cannot drift away from the tool; the captions are written by hand.


<!-- BEGIN generated: worked examples -->
| File | Size | `RecordPlacement` | `DataResidency` | What it shows |
|---|---:|---|---|---|
| `WPSettings.dat` | 12 | `embedded` | `inline` | small, never moved — record in the name row, bytes in the record |
| `xbpt_large_149mb_alpha_610845.dat` | 156,237,824 | `embedded` | `extents` | **149 MiB, never moved** — the record is still in the name row, whatever the file's size |
| `xbpt_log_november_496320.csv` | 552,331 | `split` | `extents` | moved — the record was split out; the bytes are in extents |
| `index_data_269514.bin` | 1,108 | `split` | `inline` | **hard-linked, and its bytes are inline** — a split record still carries its own `$DATA` |
| `hardlink_sync_683343.lnk` | 0 | `split` | `inline` | 0 bytes, hard-linked — residency is the form of its `$DATA` record, even when it stores no byte |
| `test.txt` | 5 | `embedded` | `snapshot-shared` | unmodified since a snapshot — the bytes are the snapshot's, not this stream's |
| `lasttest.txt` | 201 | `embedded` | `snapshot-shared` | the same state at 201 bytes — size does not decide this one either |
<!-- END generated: worked examples -->


## Alternate data streams

An ADS is a type-0xB0 `$NAMED_DATA` row of the file's record; it follows the named-stream row of the table above.

- On format 3.11 and later it is inline below 2 KiB (typical ADS are tens of bytes) and in extents from 2 KiB. The
  conversion applies to it as to `$DATA`, whatever the file's main stream does.
- A large ADS has a fixed 116-byte descriptor (`val[0x04] = 0x68`, no inline content); its bytes are in extents
  listed by a separate extent record of the same file record (its key: 0x50 bytes, type 0x0003 at `key+0x08`), linked
  to the ADS by its stream size. forefst rebuilds such an ADS from its extents.
- The attribute-flags bit **0x1000** at `val+0x02` tells the two forms apart: across the named streams and stream
  snapshots measured it is set on every row that is not inline and clear on every inline row.
- Type 0xB0 also carries stream snapshots; the StreamSummary field at `val+0x10` reads 0 for an ADS and 2 for a
  snapshot.

So an inline ADS lives in the metadata tree, and a large ADS in clusters: a tool that assumes all ADS are inline
misses the large ones. See [Named data streams](../attributes/NAMED_DATA.md#residency).

A record can also move *within* its tree: when a file collects enough attributes, its attribute table moves to a
child page and the name row's value holds only an index node. A reader that stops at the value then reports "no
alternate data streams" for a file that has many. See [Directory Entries](../structures/directory_entries.md).

## Why it matters for recovery

On a format 3.11+ volume, small files keep their bytes inside the directory's metadata tree, not in any cluster.

- A tool that only follows extents, as on NTFS, never sees those files: it reports success and leaves them out. On a
  volume of small files they can be many of the files, though few of the bytes.
- So read each file's `$DATA` record and follow the storage it names, inline bytes or extents, and never decide it
  from `key_flags`.
- A deleted inline file's bytes survive or disappear with its metadata row, except that the MLog can keep a copy
  until the log reuses its space; a deleted extent-backed file's bytes can stay in unreferenced clusters long after
  the row is gone. See [Deletion Recovery](deletion_recovery.md).

## How to check on your own image

```sh
forefst.py disk.raw files --csv -q            # RecordPlacement and DataResidency columns
forefst.py disk.raw details /path/to/file     # both properties for one file, with the record's own numbers
forefst.py disk.raw dataruns -v               # INLINE / EXTENT / SHARED / UNALLOC, with the record's placement
forefst.py disk.raw extract /path/to/file     # the bytes, whichever of the four states they are in
```

`extract` handles all four states; you do not need to know the state to recover the content.

### Reading it by hand

A parser reads record placement from the name row, then residency from the `$DATA` record.

- **Placement.** An 84-byte or 72-byte value is an index entry: a split file, or a directory
  (attribute bit `0x10000000` at value+0x40). The length is fixed when the entry is written, so an upgraded volume
  holds both sizes: read it from the row, not from the volume version. A longer value is an embedded record.
- **Residency.** The form of the current `$DATA` record ([$DATA](../attributes/DATA.md#residency)):
  - the **inline** form (`+0x0C` = 0x30, StreamSummary flags 0 at `+0x10`): the bytes are in the record, at `+0x3C`;
    there may be none;
  - the **extent** form (node offset 0x88): the bytes are on disk, listed by the extent map at `+0x88`. Within it
    (v3.7 and later), a disk allocation of 0 at `+0x48` marks a stream that owns no clusters: `snapshot-shared` when a
    snapshot row of the same stream exists, otherwise `unallocated`. A 0-byte extent-form stream stays `extents`; a
    zero allocation never means inline.

An embedded record whose data is in extents keeps its extent map in its own `$DATA` sub-record. Two fields of the
record cache the stream's size (value+0x58) and allocation (value+0x60); where they disagree with the `$DATA` record,
the `$DATA` record is authoritative. The extent map is a small B+-tree node, so a fragmented file decodes too, and
when the node outgrows the value it continues in a child page. A split file's extent map sits in its type-0x40
backing record, decoded the same way.

Every extent-based recovery is checked first: the extents must cover the file's allocated clusters exactly once, with
no overlap and no gap except a sparse file's holes, which are zero-filled. If they do not, `extract` stops and
recovers no bytes rather than part of them. This catches a misread that shifts a run or changes its length; it cannot
catch a wrong address with the right length.

### A raw example

`forattributes/encrypteddir/bla.txt` on a v3.14 4 KiB-cluster image holds the 7 bytes `hello\r\n`, stored
**inline** in its embedded directory record: it has no data clusters at all. Its `$DATA` sub-record, at offsets
relative to the file record's value (`vd`):

```text
vd+0x0e8:  01 00 00 80                <- embedded marker 0x80000001 (single-instance)
vd+0x0ec:  80 00 00 00                <- sub-record type 0x80 = $DATA
vd+0x118:  07 00 00 00                <- valid data length = 7 (value+0x28; the stream size is at value+0x20)
vd+0x12c:  68 65 6c 6c 6f 0d 0a       <- "hello\r\n"  (the file content, inline, at value+0x3C)
```

The file's whole content is in the parent directory's B+-tree leaf row.

## Questions

**Is `split` a sign of tampering?** No. It shows the record was split out of its name row, which a cross-directory
move or a hard link causes; both are ordinary. If the file is later moved back, its record stays split.

**Does a big file always have `extents`?** On format 3.11 and later a stream of 2 KiB or more is never inline: it is
`extents`, or `snapshot-shared` / `unallocated` when it owns no clusters. Below 2 KiB it is usually inline. On format
3.10 and earlier main data is never inline, whatever the size.

**Can a hard-linked file have its bytes inline?** Yes: see `index_data_269514.bin` above. On the corpus's 3.14
volumes (no format from 3.11 to 3.13 is held) about one split file row in five does, a share that varies by volume;
on format 3.10 and earlier, none.

**`snapshot-shared`: where are the bytes?** In the snapshot's clusters. The live stream owns no allocation until
something writes to it.

## Cross-references

- [Directory Entries](../structures/directory_entries.md): the embedded-record and index-entry layouts, and the key
  that holds `key_flags`
- [`$DATA`](../attributes/DATA.md) · [Named data streams](../attributes/NAMED_DATA.md#residency) ·
  [Extent records](../structures/extent_descriptors.md)
- [Hard links](hard_links.md) · [Snapshots and versioning](snapshots_versioning.md) ·
  [Deletion Recovery](deletion_recovery.md) · [NTFS comparison](ntfs_comparison.md)
- [Driver Evolution](driver_evolution.md): the functions behind the format gate and the conversions
- [Version Detection](version_detection.md): telling a format 3.10 or earlier volume from a 3.11+ one before choosing a
  carving strategy
- [Cluster and Page Size](cluster_page_size.md): the 2 KiB ceiling is not a page or cluster size

## Evidence

Measured on disk across the corpus, and read in the driver.

- The format gate and the size limits: `RefsAddAllocationForResidentWrite` compares the volume's format (VCB+0x318 /
  +0x319) with 0x30b (3.11), raises STATUS_FILE_SYSTEM_LIMITATION above 128 KiB below that format, keeps the stream
  inline below 0x800 bytes or below 3.11, and converts otherwise; a stream extended repeatedly by the same caller has
  its growth scaled up (up to 16 times, capped at 128 KiB), so it can move to extents before its content reaches
  2,048 bytes (read in 26100.8115; not tested on disk). `RefsSetAllocationInfo` and `RefsSetEndOfFileInfo` convert
  only on format 3.11 and later and from 0x800 bytes (26100.8115). The 128 KiB branch is the named-stream limit; the 17134 driver
  reaches it through `RefsTelemetryUnsupportedADS` and has no `RefsConvertToNonResident` (no 3.7 to 3.10 driver is
  held). `RefsConvertToNonResident` accepts types 0x80 and 0xB0; its callers in the 26100 and Insider builds are the
  list above; no rename, move or link function calls it, and no driver read has a `ConvertToResident`.
- The two key_flags values (`{0x01, 0x02}` only, across the corpus), the directory bit, and the value sizes are read
  on disk.
- Embedded (key_flags 0x01) file rows, over 79 distinct volumes: in extents on all 3,153 (3.4), 442 (3.7), 701 (3.9)
  and 250 (3.10), none inline; on 3.14, 34,272 of 421,109 in extents, by volume from 0 % (`win11refsmini`, 0 of 9)
  and 30 % (`winsider`, 14,353 of 47,909) to 96 % (`lab314_64k` and `lab314_4kn`, 611 of 635).
- Split rows keeping their data inline: 16,164 of 81,760 over 79 distinct volumes (16,191 of 83,485 over all 117 image
  paths), 14,580 of them on one real Windows volume (`winsider`); the count includes 0-byte records whose `$DATA` is
  the inline form.
- The audited 2 TB volume: 51 of 51 key_flags-0x02 file rows explained by a move or a hard link (49 moved, 2
  hard-linked). The split's driver paths: `RefsLinkFileToSelf`'s callers `RefsSetLinkInfo`, `RefsSetRenameInfo`,
  `RefsPosixDeleteLink` and `RefsRemoveSupersededTarget` (26100.8115, .9549 and Insider 29574).
- A controlled move session over a whole volume: of 9,521 files present before and after, 5 changed placement (2 in
  the same directory, 3 relocated to a new parent) and 0 changed residency; the moved file's `$DATA` record was
  byte-identical either side.
- The upgraded volume: 0 of 262 pre-existing files changed residency; its one inline file is one of three names that
  appear only after the upgrade.
- Integrity: two small files written first and then given integrity stayed inline; two created inside an integrity
  directory were in extents, each with a full 4,096-byte cluster (512 and 1,500 bytes).
- The lab volumes (format 3.14; 4 KiB clusters, 64 KiB clusters, 4 KiB clusters on a 4Kn disk; 2026-09-07): the fixed
  2 KiB boundary on all three; a 131,073-byte ADS on 3.14 (so the 128 KiB cap is a rule of format 3.10 and earlier,
  read in the driver and not yet witnessed on a volume of that format); the one-way change (the 0-byte pair). On `win11refs8g`
  (2026-07-05): 161 of 161 extent-backed ADS rebuilt byte-exact, over a 2 KB to 2 MB size sweep and multi-ADS files.
- A snapshot alone moves an unmodified 600-byte inline stream to `snapshot-shared`; the order of a rename and a
  cross-directory move leaves no trace in the record (two 500-byte files, renamed then moved and moved then renamed);
  an end of file of 7 or 500 bytes set before any write leaves a stream inline, a 1 MiB allocation leaves a 16-byte
  file in extents.
- Bit 0x1000 at `val+0x02`, over the 8,353 marker-form `0xB0` rows of 57 images (8,238 named streams and 115
  stream-snapshot rows): set on the 844 that are not inline (729 extent-backed streams and the 115 snapshot rows),
  clear on the 7,509 that are (7,505 inline, 4 empty). The field at `val+0x38` is the checksum-type selector, not a
  residency field.
- The placement and residency census behind the observed combinations covers 79 distinct volumes (507,433 file name
  rows): embedded with inline, extents, empty, snapshot-shared or unallocated data, and split with inline, extents or
  empty data.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements.

<!-- findings: FN_DTBL_005, FS_MOVE_RA_001, FS_MOVE_RA_003, MD_DATA_RA_015, MD_DATA_RA_022, MD_DATA_RA_027,
               MD_PLAC_RA_001, MD_SNAP_RA_009 -->
