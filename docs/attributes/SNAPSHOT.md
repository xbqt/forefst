# $SNAPSHOT
<!-- site: description "Stream snapshots: a file's earlier content, frozen under a new stream id so that later writes leave it recoverable." -->

`$SNAPSHOT` is the per-stream snapshot metadata for file versioning (embedded type 0xB0; in the 26100 and later drivers).

- A snapshot keeps a stream's current content under a new sub-stream id (0x1001, 0x1002, …), so the prior bytes
  survive later writes to the file.
- Measured exceptions: a snapshot taken while the stream was inline, followed by a rewrite of the whole file past
  2 KiB, was not found afterwards (whether growth alone loses it was not tested); a deleted file's snapshots yield
  metadata only.
- It is stored as a multi-instance sub-record inside the file's record (in the corpus, always the embedded name
  row's value), and shares the type-0xB0 code with `$NAMED_DATA` (ADS): the two are distinguished by the
  StreamSummary flag.

| Property | Value |
|----------|-------|
| Type code | 0xB0 (subtype 0x0005), shared with [$NAMED_DATA](NAMED_DATA.md) |
| Instances | multi-instance (marker 0x80000002) |
| Where it lives | the file's record; on every snapshot entry measured, the embedded name row's value |
| Size | 116 bytes, fixed |
| Added in | not known: the code is in the 26100 and Insider drivers read and not in the 3.4 driver (17134); no 3.7 to 3.10 driver is held. Snapshot entries are seen only on 3.14 volumes in the corpus |

## Value layout

Sub-record: marker 0x80000002 (multi-instance), type code 0x00B0, subtype 0x0005, key suffix = the UTF-16LE stream
name.

The value (the type-0xB0 value header, shared with ADS; a snapshot value is always 116 bytes):

<!-- site: hexfig "attr_snapshot_win11refs2tsnapshots" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 2 | Padding | 0 |
| 0x02 | 2 | Attribute flags | 0x1C00 for a snapshot (= 0x0400 \| 0x0800 \| 0x1000; see [the attribute-flag bits](#ads-vs-snapshot-and-the-attribute-flag-bits)); for ADS, 0x0000 (inline) or 0x1000 / 0x5000 (extent-backed) |
| 0x04 | 4 | Data-area size | value length − 12 (0x68 for a snapshot) |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | Summary size | 0x30 (48) |
| 0x10 | 2 | StreamSummary flags | 2 = snapshot, 0 = ADS — the discriminator |
| 0x12 | 6 | Reserved | 0 |
| 0x18 | 8 | Allocated size | cluster-aligned |
| 0x20 | 8 | Stream size | logical content length |
| 0x28 | 8 | Valid data length | equal to the stream size on every snapshot entry read |
| 0x30 | 8 | Total allocated | usually equals allocated size |
| 0x38 | 2 | Checksum type | the table's checksum type, as for [$DATA](DATA.md#checksum-fields) (not a residency flag) |
| 0x3A | 2 | Integrity algorithm | as for [$DATA](DATA.md#checksum-fields) |

The region beyond 0x3C in the 116-byte form (snapshot entries, and also extent-backed ADS, where `+0x44` reads
0x1000); an inline ADS holds its content there instead:

<!-- site: hexfig-rows "attr_snapshot_win11refs2tsnapshots" "more" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x44 | 4 | Stream index (`data_sub_id`) | links to the `$DATA` sub-record holding the extents this version owns (blocks unchanged since an older snapshot are in that snapshot's record) — 0x1001, 0x1002, … per version (the live version is 0x1000) |
| 0x4C | 8 | Snapshot timestamp | FILETIME of snapshot creation — distinct from the file's `$SI` timestamps |

## Content recovery — the extent chain

A live file's snapshots are recoverable from a single image, provided each version is rebuilt across the snapshots
as below.

Follow the snapshot's `data_sub_id` (`val[0x44]`) to the `$DATA` sub-record (type 0x80, marker 0x80000002) whose
`key+0x10 == data_sub_id`. That record is the extent form of `$DATA`
([Extent metadata](DATA.md#extent-metadata--the-multi-instance-record)); its value carries the extent map — the same
extent node as a live file's `$DATA` record:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Inner header size | 0x88: where the extent map begins |
| 0x38 | 8 | Stream size | logical content length of this version |
| 0x48 | 8 | Disk allocated | what this stream owns: on a snapshot's record, the clusters that version owns; on the live stream (sub-id 0x1000), 0 means the bytes are shared with a snapshot (`snapshot-shared`) or, with no snapshot row, that nothing was written (`unallocated`) — never inline |
| 0x88 | var | Extent map | the extent node: level at `+0x0C` (0 = leaf), row count at `+0x14`, rows reached through the node's index array (see [Extent records](../structures/extent_descriptors.md#where-the-extent-records-live--a-b-tree-node)) |

> One record, two views: this `$DATA` sub-record carries descriptor `0x000E0080` in its key (tabulated on
> [Directory Entries](../structures/directory_entries.md)) and `0x00010028` at value+0x04 — not two different
> sub-records.

Each extent entry: `0x00` VLCN (needs Container-Table translation), `0x08` flags, `0x0A` record size, `0x0C`
file_vcn, `0x14` run_length. The u32 read at `0x08` therefore carries `flags | record_size << 16`, which is why the
values look like `0x180040` rather than `0x40`. Record size is `24` for a plain data run and `24 + run*4` when the
entry carries one CRC-32C per cluster (flags bit 0x80) — see
[Extent records](../structures/extent_descriptors.md). Flags bit 0x20 marks a sparse hole.

A version's record lists only the blocks that version owns. Snapshots are copy-on-write: a block is duplicated
only when it is about to be overwritten, so every block unchanged since a snapshot stays shared, listed in that
snapshot's record and absent from the newer streams'.

Procedure:

1. Read `data_sub_id` and find the `$DATA` record.
2. Walk its extent node.
3. Place each run at `file_vcn × cluster size`, translating each VLCN → PLCN through the Container Table and leaving
   flagged holes zero.
4. Fill every cluster this version does not own from the newest snapshot strictly older than it (a newer snapshot
   can hold content written after the version being recovered). For the live stream, a missing cluster comes from
   the newest snapshot that holds it. A cluster no stream holds is a sparse hole and stays zero.
5. Trim to the stream size.

Tools: `forefst.py <image> snapshots --show` (preview) or `--extract DIR` (write files). See
[Copy-on-Write](../concepts/copy_on_write.md#stream-snapshots-explicit-history) for the forensic framing.

## ADS vs snapshot, and the attribute-flag bits

ADS and snapshots share descriptor 0x000500B0 (under marker 0x80000002 in the 3.7 and later key form). The
discriminator is the StreamSummary flag `val[0x10]` (2 = snapshot, 0 = ADS) — equivalently the HasSnapshot bit
0x0400 in `val[0x02]`; the two methods agree on every 0xB0 row measured. A snapshot's `val[0x02] = 0x1C00`:

| Bit | Meaning |
|-----|---------|
| 0x0400 | HasSnapshot — set on every snapshot entry; the driver (`_FCB::HasSnapshot`) decides that a file has a snapshot by finding this bit on one of its 0xB0 attributes |
| 0x0800 | sets `SCB+0x98` bit 0x80 (sparse / CoW-related; gates CoW / valid-data-length / encryption) |
| 0x1000 | set on exactly the 0xB0 rows whose content is not inline — extent-backed named streams and snapshot entries (every marker-form row measured) |

An inline ADS sets `val[0x02] = 0x0000`; an extent-backed ADS sets 0x1000 (0x5000 on two SmartScreen streams); a
snapshot sets all three (0x1C00). See [$NAMED_DATA](NAMED_DATA.md) for the ADS-specific parsing.

## Cross-references

- [$DATA](DATA.md) — the `$DATA` sub-record that holds the snapshot's extents
- [$NAMED_DATA](NAMED_DATA.md) — ADS detection and parsing (shares the type-0xB0 value header)
- [Copy-on-Write](../concepts/copy_on_write.md) · [Snapshots and Versioning](../concepts/snapshots_versioning.md) — the recovery model
- [Directory Entries](../structures/directory_entries.md) — the embedded sub-record location

## Evidence

Type 0xB0 and the attribute-flag handling are read from the driver (`RefsCreateStreamSnapshot`,
`GetResidentStreamSummaryFromDisk`, `RefsUpdateScbFromAttribute`, `_FCB::HasSnapshot`); the `data_sub_id` link at
`+0x44`, the timestamp at `+0x4C`, the extent table and the byte-for-byte content recovery are measured on disk.

That the `0x4C` FILETIME is the snapshot moment and not a frozen copy of the file's `$SI` was measured on a file
snapshotted between its own creation and modification.

The page is documented against the project's claim register. See [how this was verified](../methodology.md).

The measurements behind the text:

- 115 snapshot entries in the corpus, all in embedded records' name-row values, all with `val[0x02] = 0x1C00`; no
  other 0xB0 row carries bit 0x0400. Bit 0x1000 is also on 729 extent-backed ADS rows, 728 of them on files with no
  snapshot entry.
- The rebuild rule: after it, 8 of 8 current files and 20 of 20 prior versions of a lab family (`win11refs8g`,
  `snapfile_NN.txt`) are byte-exact against the generator's specification. Worked case: `snapfile_03.txt`'s current
  stream owns file VCNs 4 and 5 only; VCNs 0–2 are in snapshot 0x1001 and VCN 3 in 0x1002.
- The exceptions: `t12_small.bin` on `lab314_main_step2` (snapshotted while inline, then rewritten whole at 3,000
  bytes) carries no snapshot sub-record; `del_snap` on `lab314_main` (a deleted snapshotted file) yields metadata
  only.
- A snapshot of an unmodified 600-byte inline stream moves its live stream to `snapshot-shared`
  (`t12_inline_kept.bin`, `lab314_main_step2`).

<!-- findings: CT_DRNT_RA_001, FS_SNAP_RA_001, GN_SNAP_SA_001, MD_ADS_RA_004, MD_ATTR_RA_018, MD_DEL_RA_004,
               MD_SNAP_RA_002, MD_SNAP_RA_003, MD_SNAP_RA_004, MD_SNAP_RA_005, MD_SNAP_RA_008, MD_SNAP_RA_009,
               MD_SNAP_RA_010 -->
