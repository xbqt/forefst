# Tiered Storage and the Heat Engine

A ReFS volume can move its data between a fast tier (NVMe/SSD) and a slow tier (HDD), and can compress, decompress or
recompress it, with no user action once the feature is set up and no edit to any file's metadata. Two parts of the
driver decide this (26100.9444):

- the tier moves are decided by `CmsVolumeAnalyzer`, from how full each tier and each container is;
- the compression decisions are made by the **Heat Engine** (`CmsVolumeHeatEngine`), which counts each container's
  I/O in 10-minute generations.

For an analyst the consequence is direct: a file's *physical location* and *compression state* on a ReFS disk are set by
the volume's own maintenance, not by a user, and they can differ between two images of the same volume even when no
file was written.

This page reads the mechanism from the driver: the corpus holds no volume known to sit on tiered storage. The engine's table on the
volume holds I/O metrics on 96 of the 112 corpus volumes of format 3.10 and later and is empty on the other 16.

## What the heat engine counts and decides

The Heat Engine lives in the Minstore layer (the `Cms*` namespace — Tier 3 of the
[three-tier driver dispatch](architecture.md#three-tier-irp-dispatch)). Read on 26100.9444, with the same callers on
26100.9818 and Insider 29574 / 29683:

- When a container range is pinned for I/O, `CmsVolumeContainer::PinContainerRange` calls `TrackIo`, which adds, for
  that container in the current generation, the range's length to a counter, 1 to an I/O count, and bits to a
  32-bit map of the container's touched sub-ranges. The unit is a container, not a block.
- At mount, `CmsVolume::Start` enables three heat lists, one per class: `SmsCompressionHeatClass`,
  `SmsDecompressionHeatClass` and `SmsRecompressionHeatClass` (`EnableHeatQueryType`).
- Only volume compression uses them: `CmsVolume::CompressVolume` calls `BuildHeatLists`, takes containers from the
  three lists and passes them to `CompactAndCompressContainer`. An uncompressed container enters the compression list
  only when its metric is at or above a threshold in every generation and it was seen in more than one generation or
  last more than 30 minutes ago; a compressed one enters the decompression list when its metric is at or below the
  threshold. What the metric fields count, and the threshold table's values, were not read.
- The lists are ordered skip lists (`CmsRotatingSkipList`, a generic list the allocator uses too). A container's
  metrics are dropped when its last generation is older than the current one, and the persisted generations are
  trimmed to a window (below).

```text
 I/O on a container range
 │
 ▼
 TrackIo ── per container, per 10-minute generation:
 │          the length pinned, an I/O count, a 32-bit map of touched sub-ranges
 ▼
 CmsVolumeHeatEngine ── three heat lists (compression / decompression /
 │                      recompression), read only by CompressVolume
 ▼
 CompactAndCompressContainer; the generations are persisted under
 schema 0xe130 (OID 0x30)
```

## Tier moves

Tier moves are not heat decisions. `CmsVolumeAnalyzer::AnalyzeAndProcessContainerMoves` destages containers from the
fast or the slow tier when that tier's fill ratio calls for it, choosing among containers by their own fill level
(eleven fill-percentage buckets); no `CmsVolumeAnalyzer` function reads the heat engine (26100.9444).

The relocation uses the container indirection of
[virtual addressing](virtual_addressing.md): because file extents
point at *virtual* clusters, a whole container can be moved between tiers by rewriting a
single physical-start value in the [Container Table](../structures/container_table.md),
with no edit to any per-file extent table (read in the driver's container-rotation code, not tested on
disk). Physical placement is carried out through the
[allocator](../structures/allocators.md) and container-rotation subsystem — see
[Allocation and Space Management](allocation_space_mgmt.md) — and the (de)compression the heat engine
selects is the per-container scheme described under [Compression](compression.md).

The heat engine's own record on the volume is the
[heat engine table](../structures/system_oids.md#heat-engine-table-oid-0x30) (OID 0x30): its I/O metrics in
10-minute generations, per container. It is written even on a volume formatted with heat gathering disabled, so that
setting does not tell whether the table holds generations.

## Forensic interpretation

- **A file's physical location or compression state changing "by itself" is expected.** Between two images of the
  same volume a container may move between tiers (as the tiers fill) or be compressed or decompressed (by the heat
  engine) with no write, no timestamp change and no user involvement. Do not read such a delta as user activity or
  tampering.
- **Compression state is not a record of use.** The heat engine compresses and decompresses from per-container I/O
  counts, but how its thresholds map to recent use was not read, and the tier moves (`CmsVolumeAnalyzer`) read no heat: treat
  a change as the volume's maintenance acting, not as evidence that a file was or was not read.
- **Whole-volume tier fill levels are visible without parsing on-disk heat metadata.**
  `fsutil refsinfo <vol>` reports **Fast/Slow Tier Fill %** and **Fast/Slow Tier Rate** on
  a live mount (see Tooling). These characterize how aggressively a volume uses its fast
  tier and whether it is near capacity.
- **Heat gathering may be turned off.** The `$VOLUME_INFORMATION` flag bit `0x200` is set when the volume is formatted
  with heat gathering disabled (the `disableheatgathering` tunable; see
  [Volume Information](../structures/volume_info.md)). The volume formatted that way still holds heat generations (3),
  so what the bit switches off is not established; the tier moves read no heat.
- **The heat persistence schema is itself a version/age marker.** Schema `0xe130` first
  appears at v3.10 (see below); finding it on disk shows the volume was formatted or upgraded at v3.10 or later, the
  same way other schema introductions do for [version detection](version_detection.md).

## Version and state differences

Two thresholds matter, and they do not coincide. The whole-volume tier-fill fields that
`fsutil` surfaces appear earlier than the on-disk heat *persistence* schema, so a volume
can report Fast/Slow Tier data while not yet writing any heat schema on disk.

| Element | First present | Source |
|---------|---------------|--------|
| `fsutil refsinfo` Bytes Per Physical Sector | all versions (v3.4+) | `fsutil refsinfo` (behavioral) |
| `fsutil refsinfo` Fast/Slow Tier Fill % | **v3.7** | `fsutil refsinfo` (behavioral) |
| `fsutil refsinfo` Fast/Slow Tier Rate | **v3.7** | `fsutil refsinfo` (behavioral) |
| Heat Engine persistence schema `0xe130` | **v3.10** | schema `0xe130` (driver and disk) |
| `CmsVolumeHeatEngine` class in driver | v3.14 (Win11 26100) and Insider; absent from 17134 | driver class |

The `fsutil` (behavioral) tier rows are single-mount observations; the **v3.7** first-appearance rests on a single
v3.7 image, so treat that boundary as indicative rather than firm. The schema/class rows (`0xe130`,
`CmsVolumeHeatEngine`) are the ones grounded in the driver code and on disk.

In the Win10 v3.4 driver the Heat Engine is effectively absent (2 functions with "heat" in their names and no
`CmsVolumeHeatEngine` class); 26100.8115 has 83 such functions. The
`CmsVolumeHeatEngine` class is present on both v3.14 (Win11) and Insider — it is *not* an Insider-only subsystem.

## Tooling

The whole-volume tier state is exposed by Windows on a live mount. On the disk, the `0xe130` rows are the
[heat engine table](../structures/system_oids.md#heat-engine-table-oid-0x30) (OID 0x30), which holds generations on
96 of the 112 corpus volumes of 3.10 and later; `refsanalysis oid30` lists them,
and forefst does not parse them.

```sh
fsutil refsinfo C:
 ...
 Bytes Per Physical Sector : 4096
 Fast Tier Fill Percentage : ...
 Slow Tier Fill Percentage : ...
 Fast Tier Data Fill Rate : ...
 Slow Tier Data Fill Rate : ...
```

For offline images the parseable signals are the presence of schema `0xe130` in the
[Schema Table](../structures/schema_table.md), the heat engine table's generations (OID 0x30), and the
`$VOLUME_INFORMATION` heat-disabled flag (`0x200`) in [Volume Information](../structures/volume_info.md).

## Cross-references

- [Compression](compression.md) — the per-container (de)compression that the heat classes drive
- [Allocation and Space Management](allocation_space_mgmt.md) — the container-rotation machinery that moves containers between tiers
- [Virtual Addressing](virtual_addressing.md) — why moving a container between tiers needs no per-file extent edit
- [Driver Architecture](architecture.md) — where `CmsVolumeHeatEngine` sits in the three-tier (`Cms*`) engine; its method counts per build are on [Driver Interface](driver_architecture.md)
- [Schema Table](../structures/schema_table.md) — registration of schema `0xe130`
- [Volume Information](../structures/volume_info.md) — `$VOLUME_INFORMATION` flag `0x200` (heat gathering disabled)
- [Heat engine table](../structures/system_oids.md#heat-engine-table-oid-0x30) — OID 0x30, the heat engine's I/O metrics by generation
- [Version Detection](version_detection.md) — using schema and `fsutil`-field presence to bound format age

## Evidence

- **The mechanism** is read in the driver's code (26100.9444; the same callers on 26100.9818 and Insider 29574 /
  29683): `TrackIo` in `PinContainerRange`, the three heat lists enabled by `CmsVolume::Start`, `BuildHeatLists` called
  only from `CompressVolume`, and the tier moves in `CmsVolumeAnalyzer`, which reads no heat. Functions with "heat" in
  their names: 2 on 17134, 83 on 26100.8115 (the function catalogue).
- **The on-disk binding** is confirmed in `CmsVolumeHeatEngine::Initialize` (26100.8115 and Insider), which loads the
  schema ID into a durable-table create call:

```text
mov dword [rsp+0x30], 0xe130   ; schema ID for the Heat Engine persistence table
```

- **Schema `0xe130`** is also checked on the corpus: it is absent on v3.4/v3.7/v3.9 volumes, present on v3.10 and later,
  registered in the Schema Table, and the schema of OID 0x30, which holds 4 to 24,222 rows on 96 of the 112 corpus
  volumes of 3.10 and later and none on the other 16.
- **The heat-disabled control** is the `$VOLUME_INFORMATION` flag bit `0x200` (`disableheatgathering`), decoded on
  disk.
- **The heat engine table** (OID 0x30) is read in the heat engine's code and measured on the corpus; the volume
  formatted with heat gathering disabled holds 3 generations.
- **Not read:** what the metric fields count, and the threshold table's values.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

<!-- findings: FS_SCHM_RA_004, FS_VOLI_RA_002 -->
