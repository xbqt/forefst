# Block Refcount Table

The Block Refcount Table (root #6, table ID 0x05, schema 0xe0b0) tracks shared data clusters used by
snapshots, deduplication, and clones. The schema and root #6 have existed since v3.4 as an empty
B+-tree; the table is only populated on v3.14 volumes with snapshot, dedup, or hard-link sharing
activity.

## Key — 16 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Start LCN (u64) | First cluster of the tracked range |
| 0x08 | 8 | Cluster count (u64) | Range length in clusters = **0x400 = 1,024** (one u16 array entry per cluster) |

## Value — 2,080 bytes (0x820, normal)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Start LCN (u64) | Redundant copy of key |
| 0x08 | 8 | Cluster count (u64) | Redundant copy of key (**0x400 = 1,024**) |
| 0x10 | 8 | Modification stamp (u64) | Low byte varies (e.g. 0xE4 / 0xF0) — NOT always 0x01 |
| 0x18 | 4 | **TotalRefCount (u32)** | **= Σ(array entry & 0x3FFF)**; upper 16 bits always 0 |
| 0x1C | 2,048 | Per-cluster refcount array (u16[1024]) | Spans **0x1C..0x81B**; one entry per cluster (4 KiB); bits 0–13 = refcount, bits 14–15 = flags |
| 0x81C | 4 | Trailing | Rounds the value to 0x820 |

The normal value is **2,080 bytes (0x820)**: a 28-byte header (0x00..0x1B, including
**TotalRefCount@0x18**) + the **u16[1024] array @ 0x1C..0x81B** (one entry per cluster) + a 4-byte
trailing field @ 0x81C. The header's `TotalRefCount@0x18` equals the sum of the refcount fields across
the whole array (Σ of `entry & 0x3FFF`), with the upper 16 bits always 0. Do not confuse this with the
[allocator bitmap row](allocators.md), which is a *different* structure with a different value length.

A compact/stale variant of 32 bytes also exists.

## Per-cluster refcount entry bit fields (u16; one entry per cluster / 4 KiB)

| Bits | Mask | Field | Notes |
|------|------|-------|-------|
| 13:0 | 0x3FFF | Reference count | How many references hold this cluster |
| 14 | 0x4000 | Dedup metadata flag | Marks dedup management clusters (only on entries with rc=0) |
| 15 | 0x8000 | Shared / dedup-managed | Marks clusters managed by the Data Deduplication engine |

### Interpreting an entry

- **Hard link sharing**: rc ≥ 2, bit 15 clear (normal multi-reference).
- **CoW orphans**: rc ≥ 2, a previous checkpoint still references the clusters.
- **Dedup store**: bit 15 set, rc = 0 (data present but no live file reference).
- **Example**: entry value 0x81F9 = rc=505, shared=1 — a single 4 KiB cluster referenced by 505 files.

Bit 15 (Shared) and bit 14 (Flag14) appear only on dedup-enabled volumes, and bit 14 is never combined
with bit 15 — the bit positions and this dedup-only appearance are what the corpus establishes; the field
*names* are interpreted from that correlation. Common entry shapes are `0x4000` (dedup metadata, rc=0), `0x8000` (dedup-shared, rc=0), and
`0x8000 | rc` (dedup-shared with a live reference count).

## Population by version

| Version | State | Notes |
|---------|-------|-------|
| v3.4–v3.10 | Not populated | Root #6 exists but the table holds no rows |
| v3.14 (no dedup) | Populated | Tracks CoW references and snapshot sharing |
| v3.14 (dedup) | Populated with flag bits | Dedup engine uses bits 14 and 15 |

## Implementation notes

- The Win11 driver uses a cache-based model (`LookupCacheEntry` / `PersistCacheEntry` /
  `PopulateCacheEntry`), replacing the Win10 driver's direct B+-tree manipulation (`InsertEntry` / `DeleteEntry` /
  `UpdateEntry`). The `CmsBlockRefcount` table's refcount is adjusted through `IncrementRefcount` (the Win10 v3.4 driver also carries a paired `DecrementRefcount`; v3.14/Insider retain only `IncrementRefcount`).
- The root page meta_type is always 0x0 (not 0xe0b0).
- Root #6 has no failover pair — it is the sole copy.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — root #6 in the root-pointer list
- [Schema Table](schema_table.md) — schema 0xe0b0
- [Container Table](container_table.md) — Start LCN values align with container boundaries
- [Copy-on-Write](../concepts/copy_on_write.md) — why refcounts ≥ 2 protect CoW clusters

## Evidence

Identity (root #6 / table ID 0x05 / schema 0xe0b0 / virtual addressing / no failover pair) is confirmed
in the driver (E2): the `CmsBlockRefcount` class implements the table, and root #6 carries table ID 0x05
on valid MSB+ pages. The key/value layout, the per-cluster bitfields, and the
`TotalRefCount@0x18 == Σ(entry & 0x3FFF)` invariant are raw-disk decoded (RD) across the populated v3.14
corpus and corroborated by the decompiled access functions named above. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
