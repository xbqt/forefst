# $NAMED_DATA

`$NAMED_DATA` is ReFS's **named (alternate) data stream** — ADS. Unlike NTFS, which uses named `$DATA`
attributes, ReFS stores ADS as **multi-instance sub-records** (embedded type 0xB0) inside resident
directory-entry values. A **small ADS (content below 2 KB) is inline** — its bytes sit in the record.
An ADS whose content **reaches 2 KB is promoted to non-resident** and stored in on-disk **extents**, the
same as any large stream (see [Residency](#residency)). The type-0xB0 code is shared with `$SNAPSHOT`;
the two are told apart by the StreamSummary flag (below).

## Value layout

**Sub-record:** marker 0x80000002 (multi-instance), descriptor 0x000500B0, located within a type-0x30
directory-entry value (offset ≥ 0xA8).

**Sub-record header:**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Marker | 0x80000002 |
| 0x04 | 4 | Descriptor | 0x000500B0 |
| 0x08 | var | Stream name | UTF-16LE, null-terminated |
| — | 0–6 | Alignment padding | to `(offset − marker_start) % 8 == 4` |

**Value** (the type-0xB0 value header, shared with `$SNAPSHOT`):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 2 | Padding | 0 |
| 0x02 | 2 | Attribute flags | 0x0000 for a plain ADS; 0x1000 marks an ADS that belongs to a file's stream set (it does **not** mean non-resident — such ADS are still inline). Bit 0x0400 (HasSnapshot) is set only on snapshot entries |
| 0x04 | 4 | Data-area size | value length − 12 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | Summary size | 0x30 (48) |
| 0x10 | 2 | **StreamSummary flags** | **0 = ADS**, 2 = snapshot — the discriminator (see below) |
| 0x12 | 6 | Reserved | 0 |
| 0x18 | 8 | Allocated size | 8-byte-aligned |
| 0x20 | 8 | Stream size | logical content length |
| 0x28 | 8 | Valid data length | usually equals stream size |
| 0x30 | 8 | Total allocated | usually equals allocated size |
| 0x38 | 4 | Stream flags | checksum-type / integrity selector (0x02 = CRC, 0x04 = SHA-256; bit 0x10000 = integrity), **not** a residency flag. 0 on v3.4 |
| 0x3C | var | Inline content | the ADS content bytes (stream_size long) — **present only for a small (< 2 KB) inline ADS** |

Most ADS are small (tens of bytes) and inline. A **large ADS (>= 2 KB)** has **no inline content**: its
value collapses to a fixed 116-byte descriptor (`val[0x04] = 0x68`, `val[0x02]` bit 0x1000 set) and its
data lives in extents — see [Residency](#residency). An ADS on a snapshot-bearing file may carry extra
space matching the snapshot value size.

## ADS vs snapshot

ADS and snapshot streams share descriptor 0x000500B0 under marker 0x80000002. Two reliable
discriminators, which agree on every type-0xB0 entry:

| Method | ADS | Snapshot |
|--------|-----|----------|
| StreamSummary flags at `val[0x10]` | 0x0000 | 0x0002 |
| Attribute flags at `val[0x02]` | 0x0000 or 0x1000 | 0x1C00 (bit 0x0400 = HasSnapshot) |

The StreamSummary-flags method (`val[0x10]`) is preferred: the stream index at `val[0x44]` is **not** a
reliable discriminator — an ADS on a snapshot-bearing file also reads `val[0x44]=0x1000`, and on short
ADS entries offset 0x44 falls inside the inline content. `forefst.py` uses `val[0x10]`.

## Residency

An ADS is **inline while its content is below ~2 KB** — the `RefsConvertToNonResident` threshold. Reaching
2 KB promotes it to **non-resident**, exactly like a large `$DATA` stream:

- The 0xB0 descriptor stays an ADS (`val[0x10] = 0`), sets `val[0x02]` bit 0x1000 (stream-set member), and
  becomes a fixed 116-byte record with `val[0x04] = 0x68` and **no inline content**.
- The **extent list is stored in a separate type-0x0 sub-record** of the same directory value (not in the
  0xB0 descriptor and not via a stream index), using the standard 24-byte type-0x40 extent format. The ADS
  is linked to its extent record by matching **stream size** (`val[0x20]`).
- `forefst` reconstructs the content by translating those extents (VLCN → PLCN) and reading the clusters —
  proven byte-exact on a 256 B → 2 MB size sweep (the boundary sits exactly at 2 KB: 1920-byte content is
  inline, 2048-byte content is extent-backed).

The `val[0x38]` field is the checksum-type selector, **not** a residency flag.

## Cross-references

- [Directory Entries](../structures/directory_entries.md) — the sub-record chain layout
- [$DATA](DATA.md) — the default data stream uses the same stream-summary format
- [$SNAPSHOT](SNAPSHOT.md) — snapshot entries share the type-0xB0 code; the corrected value format and discriminators

## Evidence

Type 0xB0 / descriptor 0x000500B0 and the value layout are confirmed in the decompiled driver (E2 —
`RefsCreateStreamSnapshot`, `RefsUpdateScbFromAttribute`, `RefsConvertToNonResident`) and raw-disk
decoded across the corpus (RD). Findings: **MD_SNAP_RA_005, FS_SNAP_RA_001** (ADS census), **MD_SNAP_RA_005**
(`val[0x38]` is the checksum selector, not residency). The **extent-backed (>= 2 KB) ADS** layout — the
2 KB threshold and the type-0x0 extent record — was decoded and reconstructed **byte-exact on 161 large
ADS** (256 B → 2 MB size sweep). See [how this was verified](../methodology.md).
