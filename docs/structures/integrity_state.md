# Integrity State Table

The Integrity State Table (root #11, table ID 0x0F, schema 0xe080) keeps an integrity state per range of the
volume's clusters; what the state means is not decoded.

It is present on every volume measured, whether integrity streams are enabled or not, and on a quiescent image it
holds a single row spanning the whole volume.

## Key format — 16 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Range start (u64) | The first cluster of the row's range; 0 for the first row |
| 0x08 | 8 | Range length (u64) | Clusters in the range; the rows together cover the whole volume |

## Value format — an allocator row

The table is an allocator: the 26100 and Insider drivers build it as one (`CmsIntegrityState::Initialize` creates a
`CmsAllocator`; 26100.9444, Insider 29574), so
its rows are the [allocator tables](allocators.md)' rows, a bit per cluster. A uniform range is a 24-byte compact row;
a mixed range is a bitmap row, the 24-byte header followed by one bit per cluster.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Range start (u64) | A copy of the key |
| 0x08 | 8 | Range length (u64) | A copy of the key |
| 0x10 | 2 | Free count (u16) | Clusters whose bit is clear; saturates at 0xFFFF |
| 0x12 | 2 | Flags (u16) | Bit 0 set: a bitmap row; 0x2 on the compact rows measured |
| 0x14 | 1 | Bitmap offset (u8) | 0x18 on a bitmap row, 0 on a compact row |
| 0x15 | 1 | Format byte (u8) | 1 on every row measured |
| 0x16 | 2 | Hint (u16) | 0 on every row measured |
| 0x18 | var | Bitmap | Bitmap rows only: one bit per cluster of the range |

## Observed values

On 122 of the 124 corpus volumes the table holds one compact row covering the whole volume, with every bit clear. Read
as two u32 at +0x10 and +0x14 that row gives `0x0002ffff` and `0x00000100`: the free count saturated at 0xFFFF, the
flags 0x2, the format byte 1. On a volume of fewer than 65,535 clusters the free count is the volume's own (the
64 KiB-cluster lab volume of 64,512 clusters reads `0x0002fc00`).

The two large Win10 (ReFS 3.4) volumes hold three rows: a compact row, then a bitmap row of 16,384 clusters (2,072
bytes) with 148 bits set (it reads `0x00013f6c` / `0x00000118`: free 0x3f6c, flags 0x1, bitmap offset 0x18), then a
compact row to the end of the volume.

The values do not change with the volume's integrity setting: the single clear row is the same with integrity streams
enabled or disabled, and with SHA-256 or CRC64 metadata checksums.

## Interpretation

The Integrity State Table is a **volume-level** bit per cluster, kept as an allocator; what a set bit means is not
decoded.

Per-file integrity is tracked separately, through the `INTEGRITY_STREAM` file-attribute flag (bit 0x8000) and the
`$DATA` stream's integrity algorithm (value+0x3A, 0 without integrity), not through this table — so a file's integrity-stream status is not
derivable from any row here ([Integrity Streams](../concepts/integrity_streams.md)).

The table survives a version upgrade in place: its root LCN is unchanged across the v3.4 → v3.14 upgrade measured,
and the table is present on every format from v3.4 to v3.14.

## Driver handling

The `CmsIntegrityState` class manages this table. Relevant functions include:

- `CmsIntegrityState::Initialize` — opens root #11 at mount, as a `CmsAllocator` (schema 0xe080, table ID 0x0F;
  26100.9444, Insider 29574)
- `CmsIntegrityState::GetIntegrityStateTable` — accessor for the table
- `CmsIntegrityState::GetRangeBitmap` — reads a range's bits, by walking the allocator
- `CmsIntegrityState::SetClearIntegrityState` — mark/clear a stream for integrity checking
- `CmsIntegrityState::TriageIntegrityState` — triage integrity state during corruption handling
- `CmsIntegrityState::ResetIntegrityState` — reset integrity state for a range

The class contracts modestly across versions rather than growing: 17 functions on 17134, 12 on 26100.8115, 13 on
Insider 29574.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — carries this table's root pointer, at index #11 in the root-pointer list
- [Schema Table](schema_table.md) — schema 0xe080
- [VBR](vbr.md) — integrity streams are independent of the metadata-checksum configuration

## Evidence

Identity (root #11 / table ID 0x0F / schema 0xe080) and the allocator row format are read in the driver (26100.9444:
`CmsIntegrityState::Initialize` builds a `CmsAllocator`; `Extend` and `GetRangeBitmap` are the allocator's) and measured
on every row of the 124 corpus volumes: 126 compact rows of 24 bytes, 2 bitmap rows of 2,072 bytes whose free count
equals the range minus its set bits, and on every volume rows that cover the boot sector's cluster count without a
gap.

The single-row-per-volume result (one whole-volume row on every scanned image but those two) and the
cross-configuration invariance on quiescent images (integrity on/off, SHA-256, CRC64) were re-confirmed by reading
CHKP root #11 directly on v3.4 and v3.14 images.

See [how this was verified](../methodology.md) for the method.

<!-- findings: FS_CHKP_020 -->
