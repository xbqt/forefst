# Integrity State Table

The Integrity State Table (root #11, table ID 0x0F, schema 0xe080) tracks volume-level
integrity-stream coverage. It is present on every volume regardless of whether integrity streams
are enabled, and on a quiescent image it holds a single row spanning the whole volume.

## Key format — 16 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Start LCN (u64) | Always 0 (covers from the beginning of the volume) |
| 0x08 | 8 | Block count (u64) | Total clusters on the volume (container count × clusters-per-container) |

## Value format — 24 bytes

The table uses the same row format as the allocator tables (key: range start/end; value: range
metadata). The field breakdown below is the decoded form of that value.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Start LCN (u64) | Redundant copy of the key |
| 0x08 | 8 | Block count (u64) | Redundant copy of the key |
| 0x10 | 4 | State (u32) | default 0x0002ffff on quiescent single-row images |
| 0x14 | 4 | Config (u32) | default 0x00000100 on quiescent single-row images |

## Observed values

On baseline/quiescent images each volume holds a single row spanning the whole volume LCN range; a small minority (large Win10, 2 of 89 corpus images) instead show 3 rows, one of which covers a container with a modified integrity state. The block
count tracks the volume size (container count × clusters-per-container). The `State` and `Config`
values are stable on quiescent single-row images (one large-Win10 image shows a container with a modified `State` 0x00013f6c and `Config` 0x00000118), including:

- Integrity streams enabled (`SetIntegrityStreams=1`)
- Integrity streams disabled (`SetIntegrityStreams=0`)
- SHA-256 metadata checksums
- Standard CRC64 metadata checksums

## Interpretation

The Integrity State Table is a **volume-level** integrity-state tracker, not a per-file mechanism.
The `State` value 0x0002ffff likely represents the "default/clean" state. Per-file integrity is
tracked separately, through the `INTEGRITY_STREAM` file-attribute flag (bit 0x8000), not through this
table — so a file's integrity-stream status is not derivable from any row here.

The table survives a version upgrade in place: its root LCN is unchanged across a v3.4 → v3.14
upgrade, and the table is present on all versions from v3.4 through Insider.

## Driver handling

The `CmsIntegrityState` class manages this table. Relevant functions include:

- `CmsIntegrityState::Initialize` — reads root #11 during mount
- `CmsIntegrityState::GetIntegrityStateTable` — accessor for the table
- `CmsIntegrityState::GetRangeBitmap` — per-range integrity tracking
- `CmsIntegrityState::SetClearIntegrityState` — mark/clear a stream for integrity checking
- `CmsIntegrityState::TriageIntegrityState` — triage integrity state during corruption handling
- `CmsIntegrityState::ResetIntegrityState` — reset integrity state for a range

The class contracts modestly across versions rather than growing.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — root #11 in the root-pointer list
- [Schema Table](schema_table.md) — schema 0xe080
- [VBR](vbr.md) — integrity streams are orthogonal to the metadata-checksum configuration

## Evidence

Identity (root #11 / table ID 0x0F / schema 0xe080), the key/value row format, and the default
`State` 0x0002ffff / `Config` 0x00000100 values (one large-Win10 image carries a container with modified `State` 0x00013f6c / `Config` 0x00000118) are raw-disk decoded (RD) across the corpus and
corroborated in the driver (E2) via the `CmsIntegrityState` class. The single-row-per-volume result (87/89 images)
and the cross-configuration invariance on quiescent images (integrity on/off, SHA-256, CRC64) were re-confirmed by reading
CHKP root #11 directly on v3.4 and v3.14 images. See [how this was verified](../methodology.md) to
trace these to the exact images and measurements in `analysis/`.
