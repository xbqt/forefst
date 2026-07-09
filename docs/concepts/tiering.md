# Tiered Storage and the Heat Engine

A ReFS volume can silently relocate file data between a fast tier (NVMe/SSD) and a slow
tier (HDD), and can compress, decompress, or recompress that data, based on how often it
is accessed — all with no user action and no metadata edit. The subsystem that decides
this is the **Heat Engine** (`CmsVolumeHeatEngine`), which tracks per-block I/O
"temperature." For an analyst the consequence is direct: a file's *physical location* and
*compression state* on a ReFS disk are an access-pattern signal, not a user choice, and
they can differ between two images of the same volume even when nothing was written.

## How the engine decides

The Heat Engine lives in the Minstore layer (the `Cms*` namespace — Tier 3 of the
[three-tier driver dispatch](driver_architecture.md)). It continuously samples I/O against
logical blocks and assigns each a heat value derived from access frequency and recency.
Hot blocks are promoted to the fast tier; cold blocks are demoted to the slow tier. The
same heat signal drives compression policy: cold data becomes a candidate for compression,
freshly-warmed data for decompression. The engine only *classifies and decides* — the
actual movement and (de)compression are carried out downstream.

```
 I/O on a block
 │
 ▼
 CmsRotatingSkipList ── ages out stale samples, keeps a
 (per-block I/O ranked, time-windowed view of heat
 temperature)
 │
 ▼
 CmsVolumeHeatEngine ── classifies each block and decides:
 │ promote (→ fast tier) / demote (→ slow tier)
 │ compress / decompress / recompress
 ▼
 placement + (de)compression carried out by the allocator
 and container subsystem; persisted under schema 0xe130
```

Three named heat classes govern the (de)compression decision, each a distinct query type
the engine enables (`CmsVolumeHeatEngine::EnableHeatQueryType`):

- `SmsCompressionHeatClass` — cold data eligible for compression
- `SmsDecompressionHeatClass` — data warming up, decompress for fast access
- `SmsRecompressionHeatClass` — re-evaluate and re-pack already-compressed data

The temperature ledger itself is a **`CmsRotatingSkipList`** — a skip-list that "rotates"
(ages out) old samples so heat reflects a recent time window rather than lifetime totals.
This rotation is why the heat signal is a *recent-activity* indicator and not a cumulative
counter: an old burst of access decays out of the window. Heat state is persisted to the
volume under **system schema `0xe130`** ("Heat Engine"), which
`CmsVolumeHeatEngine::Initialize` binds by loading that schema ID (see Evidence). The
schema is registered in the [Schema Table](../structures/schema_table.md) and creates a
durable table for container heat metrics.

The relocation that the engine triggers is the same machinery
[virtual addressing](virtual_addressing.md) is built to make cheap: because file extents
point at *virtual* clusters, a whole container can be moved between tiers by rewriting a
single physical-start value in the [Container Table](../structures/container_table.md),
with no edit to any per-file extent table. Physical placement is carried out through the
[allocator](../structures/allocators.md) and container-rotation subsystem — see
[Allocation and Space Management](allocation_space_mgmt.md) — and the (de)compression it
selects is the per-container scheme described under [Compression](compression.md).

Tiering and heat tracking are independent of the
[Session Activity Table](../structures/system_oids.md) (OID 0x30): that table is present
even when heat gathering is disabled, so the two are separate access-pattern artifacts —
do not treat one as a proxy for the other.

## Forensic interpretation

- **A file's physical location or compression state changing "by itself" is expected.**
  Between two images of the same volume a file may move from slow to fast tier (or be
  compressed/decompressed) with no write, no timestamp change, and no user involvement. Do
  not read such a delta as user activity or tampering — it is the Heat Engine acting on
  access frequency.
- **Tier placement and compression are an access-pattern signal, not a timestamp.** A
  block resident on the fast tier, or one that has been promoted/decompressed, indicates
  *recent or frequent* access; a compressed, slow-tier block indicates *cold* data. This
  corroborates "what was being used," but it is a heuristic: heat is time-windowed (the
  rotating skip list ages samples out), so treat it as soft circumstantial evidence.
- **Whole-volume tier fill levels are visible without parsing on-disk heat metadata.**
  `fsutil refsinfo <vol>` reports **Fast/Slow Tier Fill %** and **Fast/Slow Tier Rate** on
  a live mount (see Tooling). These characterize how aggressively a volume uses its fast
  tier and whether it is near capacity.
- **Heat gathering may be turned off.** The `$VOLUME_INFORMATION` flag bit `0x200` means
  heat gathering is disabled (the `disableheatgathering` tunable; see
  [Volume Information](../structures/volume_info.md)). If that bit is set, the *absence* of
  tier/heat changes is explained by configuration, not by lack of activity — check it
  before drawing conclusions from "no movement."
- **The heat persistence schema is itself a version/age marker.** Schema `0xe130` first
  appears at v3.10 (see below); finding it on disk bounds the volume's format age, the same
  way other schema introductions do for [version detection](version_detection.md).

## Version and state differences

Two thresholds matter, and they do not coincide. The whole-volume tier-fill fields that
`fsutil` surfaces appear earlier than the on-disk heat *persistence* schema, so a volume
can report Fast/Slow Tier data while not yet writing any heat schema on disk.

| Element | First present | Source |
|---------|---------------|--------|
| `fsutil refsinfo` Bytes Per Physical Sector | all versions (v3.4+) | `fsutil refsinfo` (behavioral) |
| `fsutil refsinfo` Fast/Slow Tier Fill % | **v3.7** | `fsutil refsinfo` (behavioral) |
| `fsutil refsinfo` Fast/Slow Tier Rate | **v3.7** | `fsutil refsinfo` (behavioral) |
| Heat Engine persistence schema `0xe130` | **v3.10** | schema `0xe130` (E2+RD) |
| `CmsVolumeHeatEngine` class in driver | v3.14 (Win11) and Insider | driver class (E2) |

*The `fsutil` (behavioral) tier rows are single-mount observations; the **v3.7** first-appearance rests on a single v3.7 image, so treat that boundary as indicative rather than firm. The schema/class rows (`0xe130`, `CmsVolumeHeatEngine`) are the ones grounded in the driver code and on disk.*

In the Win10 v3.4 driver the Heat Engine is effectively a stub; the full subsystem is a
Win11 v3.14-era build-out (the heat-related namespace grows substantially across the
transition). The `CmsVolumeHeatEngine` class is present on both v3.14 (Win11) and Insider —
it is *not* an Insider-only subsystem.

## Tooling

The whole-volume tier state is exposed by Windows on a live mount; forefst does not parse
on-disk `0xe130` heat rows (which are typically empty on test volumes — the persistence
table exists but carries no rows unless tiered storage is actively in use).

```
fsutil refsinfo C:
 ...
 Bytes Per Physical Sector : 4096
 Fast Tier Fill Percentage : ...
 Slow Tier Fill Percentage : ...
 Fast Tier Data Fill Rate : ...
 Slow Tier Data Fill Rate : ...
```

For offline images the parseable signals are the presence of schema `0xe130` in the
[Schema Table](../structures/schema_table.md) and the `$VOLUME_INFORMATION` heat-disabled
flag (`0x200`) in [Volume Information](../structures/volume_info.md).

## Cross-references

- [Compression](compression.md) — the per-container (de)compression that the heat classes drive
- [Allocation and Space Management](allocation_space_mgmt.md) — the allocator/container-rotation machinery that physically moves promoted/demoted blocks
- [Virtual Addressing](virtual_addressing.md) — why moving a container between tiers needs no per-file extent edit
- [Driver Architecture](driver_architecture.md) — where `CmsVolumeHeatEngine` sits in the three-tier (`Cms*`) engine
- [Schema Table](../structures/schema_table.md) — registration of schema `0xe130`
- [Volume Information](../structures/volume_info.md) — `$VOLUME_INFORMATION` flag `0x200` (heat gathering disabled)
- [Session Activity Table](../structures/system_oids.md) — OID 0x30; an independent access-pattern artifact
- [Version Detection](version_detection.md) — using schema and `fsutil`-field presence to bound format age

## Evidence

The mechanism is established from the driver's PDB symbols (E2): `CmsVolumeHeatEngine` and
its `CmsRotatingSkipList` temperature ledger, the three heat classes
`SmsCompressionHeatClass` / `SmsDecompressionHeatClass` / `SmsRecompressionHeatClass`, and
the per-class `EnableHeatQueryType` entry points. The on-disk binding is confirmed in
`CmsVolumeHeatEngine::Initialize`, which loads the schema ID into a durable-table create
call:

```
mov dword [rsp+0x30], 0xe130   ; schema ID for the Heat Engine persistence table
```

Schema `0xe130` is also confirmed on the raw-disk corpus (E2+RD): absent on
v3.4/v3.7/v3.9 volumes, present on v3.10 and later, and registered in the Schema Table —
finding **FS_SCHM_RA_004**. The heat-disabled control is the `$VOLUME_INFORMATION` flag bit `0x200`
(`disableheatgathering`), decoded on disk — finding **FS_VOLI_RA_002**. The Session Activity Table's
independence from heat gathering is raw-disk verified (`RefsTelemetryPerfCountersWorker`
correlation). The engine's *runtime policy thresholds* are not recovered from static
analysis. See [how this was verified](../methodology.md) to trace these to the exact
images and measurements in `analysis/`.
