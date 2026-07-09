# $SNAPSHOT

`$SNAPSHOT` is the per-stream **snapshot metadata** for file versioning (embedded type 0xB0, schema
0x1B0; v3.7+). A snapshot freezes a stream's current content under a new stream-set id, so the prior
bytes survive later writes. It is stored as a multi-instance sub-record inside resident directory-entry
values, and **shares the type-0xB0 code with `$NAMED_DATA` (ADS)** — the two are distinguished by the
StreamSummary flag. (Prior forensic literature mislabeled schema 0x1B0 as "Index Root"; it is
`$SNAPSHOT`, added with snapshot support at v3.7.)

## Value layout

**Sub-record:** marker 0x80000002 (multi-instance), type code 0x00B0, subtype 0x0005, key suffix = the
UTF-16LE stream name.

**Value** (the type-0xB0 value header, shared with ADS; a snapshot value is always 116 bytes):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 2 | Padding | 0 |
| 0x02 | 2 | Attribute flags | **0x1C00** for a snapshot (= 0x0400 \| 0x0800 \| 0x1000 — see below); 0x0000 / 0x1000 for ADS |
| 0x04 | 4 | Data-area size | value length − 12 (0x68 for a snapshot) |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | Summary size | 0x30 (48) |
| 0x10 | 2 | **StreamSummary flags** | **2 = snapshot**, 0 = ADS — the discriminator |
| 0x12 | 6 | Reserved | 0 |
| 0x18 | 8 | Allocated size | cluster-aligned |
| 0x20 | 8 | Stream size | logical content length |
| 0x28 | 8 | Valid data length | usually equals stream size |
| 0x30 | 8 | Total allocated | usually equals allocated size |
| 0x38 | 4 | Stream flags | checksum-type / integrity selector (not a residency flag) |

**Snapshot-specific region** (beyond 0x3C, where an ADS would instead hold inline content):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x44 | 4 | Stream index (`data_sub_id`) | links to the `$DATA` sub-record holding this version's extents — 0x1001, 0x1002, … per version (the live version is 0x1000) |
| 0x4C | 8 | Snapshot timestamp | FILETIME of snapshot creation — distinct from the file's `$SI` timestamps |

## Content recovery — the extent chain

The prior (snapshotted) content is fully recoverable from a single image. Follow the snapshot's
`data_sub_id` (`val[0x44]`) to the `$DATA` sub-record (type 0x80, marker 0x80000002) whose
`key+0x10 == data_sub_id`; that DATA value carries the extent table — the **same 24-byte extent format
as non-resident type-0x40 entries**:

| Offset | Field | Description |
|--------|-------|-------------|
| 0x00 | inner-header offset | = 0x88 |
| 0x38 | stream size (u64) | logical content length |
| 0x48 | on-disk allocation (u64) | 0 ⇒ content is inline (current version); >0 ⇒ extents |
| ihdr+0x14 | extent count (u32) | number of 24-byte entries |
| ihdr+0x28 | extent table | array of 24-byte extents |

Each 24-byte extent: `0x00` VLCN (needs Container-Table translation), `0x08` flags (0x180040 = standard
data-run; 0x1c00d0 = integrity checksum-page entry, run_length 1; other variants),
`0x0C` file_vcn, `0x14` run_length.

**Procedure:** read `data_sub_id` → find the `$DATA` sub-record → parse its extents → **sort by
`file_vcn`** → **translate each VLCN → PLCN via the Container Table** → read `run_length` clusters per
extent → concatenate → **trim to the stream size**. Tools: `forefst.py <image> snapshots --show`
(preview) or `--extract DIR` (write files). See
[Copy-on-Write](../concepts/copy_on_write.md#stream-snapshot-content-recovery) for the forensic framing.

## ADS vs snapshot, and the attribute-flag bits

ADS and snapshots share descriptor 0x000500B0 / marker 0x80000002. The discriminator is the
**StreamSummary flag `val[0x10]`** (2 = snapshot, 0 = ADS) — equivalently the **HasSnapshot** bit 0x0400
in `val[0x02]`; the two methods always agree. A snapshot's `val[0x02] = 0x1C00`:

| Bit | Meaning |
|-----|---------|
| 0x0400 | HasSnapshot — a base stream that owns child snapshots |
| 0x0800 | sets `SCB+0x98` bit 0x80 (sparse / CoW-related; gates CoW / valid-data-length / encryption) |
| 0x1000 | stream-set member — the stream belongs to a file that also has snapshots / a stream set |

A plain ADS sets `val[0x02] = 0x0000`; an ADS on a snapshot-bearing file sets 0x1000; a snapshot sets all
three (0x1C00). See [$NAMED_DATA](NAMED_DATA.md) for the ADS-specific parsing.

## Cross-references

- [$DATA](DATA.md) — the `$DATA` sub-record that holds the snapshot's extents
- [$NAMED_DATA](NAMED_DATA.md) — ADS detection and parsing (shares the type-0xB0 value header)
- [Copy-on-Write](../concepts/copy_on_write.md) · [Snapshots and Versioning](../concepts/snapshots_versioning.md) — the recovery model
- [Directory Entries](../structures/directory_entries.md) — the embedded sub-record location

## Evidence

Type 0xB0 / schema 0x1B0 and the value layout are confirmed in the decompiled driver (E2 —
`RefsCreateStreamSnapshot`, `GetResidentStreamSummaryFromDisk`, `RefsUpdateScbFromAttribute`); the
extent table and the byte-for-byte content recovery are raw-disk verified (RD). Findings: **MD_SNAP_RA_005, FS_SNAP_RA_001**,
**MD_SNAP_RA_002, MD_SNAP_RA_003, CT_DRNT_RA_001, GN_SNAP_SA_001** (snapshot content recovery). See
[how this was verified](../methodology.md).
