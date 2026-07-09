# Allocator Tables

ReFS tracks free and allocated clusters with a three-tier allocator hierarchy. All three tiers share schema 0xe010 and an identical on-disk row format; they differ only in which region of the volume they manage and how their addresses are resolved.

## Bitmap Row — 2,072 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Range start (LCN) (u64) | First cluster of the managed range |
| 0x08 | 8 | Range length (clusters) (u64) | Number of clusters in the range |
| 0x10 | 2 | Free count (u16) | Number of free clusters |
| 0x12 | 2 | Flags (u16) | See Row Flags below |
| 0x14 | 2 | Header size (u16) | 0x0118 for Small/Container (all versions); Medium tier is version-dependent: **0x0118 on v3.4, 0x0218 on v3.7+** |
| 0x16 | 2 | Used count (u16) | Number of allocated clusters |
| 0x18 | 2,048 | Allocation bitmap (bits) | 1 bit per cluster; 1 = allocated |

The row **size** (2,072 bytes) and the bitmap **offset** (+0x18) are version-invariant. Only the +0x14 header-size *value* changes, and only for the Medium tier.

**Invariant**: `free_count = range_length - popcount(bitmap)` (100% match across the corpus).

### Compact Row — 24 bytes

Used for fully-allocated or fully-free ranges, where a bitmap would be redundant. It is the same first 24 bytes as the bitmap row, without the bitmap payload. (The Medium tier's compact-row header value follows the same version split: 0x0100 on v3.4, 0x0200 on v3.7+.)

### Row Flags (offset +0x12)

| Value | Meaning |
|-------|---------|
| 0x01 | Partial allocation |
| 0x02 | Compact row |
| 0x05 | Fully free |
| 0x09 | Fully free (alternative) |

## The three tiers

| Tier | Root index | Table ID | Addressing | Role |
|------|-----------|----------|------------|------|
| Medium | 1 | 0x21 | Virtual | General metadata + file data |
| Container | 2 | 0x20 | Virtual | Container Table pages |
| Small | 12 | 0x22 | **Real (physical)** | Bootstrap structures |

Most ReFS addresses are virtual and must be translated VLCN → PLCN through the [Container Table](container_table.md). The Small Allocator (root 12) is one of the three bootstrap exceptions that use real physical LCNs directly: it cannot use virtual addressing because it underlies the very translation that other structures depend on. Roots 7 and 8 (the Container Table itself) are the other two real-LCN roots.

## Three-tier interaction

The way the tiers divide up the volume changed between versions, while the row format did not.

### v3.4 — strict separation

Each tier manages separate containers with zero overlap:

- CID 0: Medium only
- CID 1: Small only
- CID 2: Container only
- CID 3+: Medium

### v3.14 — overlapping management

The Medium tier covers all containers (the entire virtual address space). The Container and Small tiers track their pages within specific containers. Where a specialised tier owns a container, Medium marks that container "fully allocated" with a compact row, and the specialised tier's bitmap tracks the individual 4-cluster page groups inside it.

## Driver behaviour

The on-disk row format is unchanged across versions despite a driver refactoring. The v3.4 driver split allocator logic across the `CmsAllocatorBase` and `CmsGlobalAllocator` classes; v3.14 merged these into a single `CmsAllocator` class and expanded the number of allocation zones from 9 to 13.

Relevant driver routines: `Allocate` (the general allocation routine that finds free page groups in the bitmap) and `MsAllocateObjectId` (allocates a new OID via the allocator subsystem).

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — roots 1 (Medium), 2 (Container), 12 (Small) in the root-pointer list
- [Container Table](container_table.md) — the Container Allocator manages this table's pages, and supplies the VLCN→PLCN translation the Medium/Container tiers depend on
- [Container Index](container_index.md) — the by-state index the allocator subsystem consumes
- [Schema Table](schema_table.md) — all three tiers use schema 0xe010

## Evidence

The three-tier hierarchy, the bitmap/compact row layouts, and the `free_count` invariant are raw-disk decoded across the corpus and corroborated in the driver (`CmsAllocator` / the v3.4 `CmsAllocatorBase` + `CmsGlobalAllocator` split). The Small Allocator's real-LCN bootstrap exception (roots 7, 8, 12) is raw-disk-confirmed and driver-backed. The 9→13 allocation-zone expansion is from static analysis of the v3.14 driver. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

Findings: **CT_ALLC_RA_001** (deep row structure), **CT_ALLC_001/002/003** (the three tiers), **GN_ARCH_RA_001** (real-LCN bootstrap exception), **GN_ALLC_SA_001** (Win11 allocator unification, 9→13 zones), **FS_CHKP_010/011/021** (global tables 0x21/0x20/0x22).
