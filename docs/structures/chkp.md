# Checkpoint (CHKP)

The Checkpoint is the atomic commit point of a ReFS volume. A volume keeps two alternating checkpoints; each is one metadata page — 4 consecutive clusters on 4K-cluster volumes (16 KiB page) or 1 cluster on 64K-cluster volumes (64 KiB page). The copy with the higher virtual clock is the current one, and the lower-clock copy is the previous consistent state (a rollback target until the next flush).

## Field Layout

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 80 | Page header | Common metadata page header (see [Page Header](page_header.md)) with signature `"CHKP"` |
| 0x50 | 4 | Version echo (u32) | Packed `minor<<16 | major` on native v3.10+; 0 on upgraded/legacy |
| 0x54 | 2 | Major version (u16) | Always 3 |
| 0x56 | 2 | Minor version (u16) | 4, 7, 9, 10, or 14 |
| 0x58 | 4 | Table descriptor end (u32) | 0xD0 (v3.4-v3.10), 0xE0 (v3.14), 0xE8 (Insider) |
| 0x5C | 4 | Page reference size (u32) | 0x68 (v3.4), 0x30 (CRC64), 0x48 (SHA-256) |
| 0x60 | 8 | Virtual clock (u64) | Matches header at 0x10; the checkpoint sequence counter — increments on every committed checkpoint. Bootstrap selects the active checkpoint by the higher value. |
| 0x68 | 8 | Allocator clock (u64) | Always **≤ virtual clock**. A *separate* counter advanced when the allocator's persisted state changes; the **gap = virtual − allocator** is the count of checkpoints since the last allocation-table change. **Forensic interpretation:** a non-zero gap indicates recent checkpoints were metadata-only / in-place (no cluster allocation since the last allocator commit). The per-operation semantic is inferred from the offset relationship rather than verified at the operation level. |
| 0x70 | 8 | Oldest log record ref (u64) | Low 32 bits = log offset, high 32 bits = segment |
| 0x78 | 4 | CHKP flags (u32) | See CHKP Flags below |
| 0x7C | 12 | Reserved | Always zero |
| 0x88 | 4 | Data area end offset (u32) | 0x680 (v3.4), 0x380 (v3.14) on most checkpoints, but **0x0 on some v3.14-native images** — the 0x88–0x8F region co-varies populated-vs-zeroed per checkpoint, so do not treat it as a fixed constant |
| 0x8C | 4 | Max root capacity (u32) | 0x20 (32) on most images but **0x0 on the same v3.14-native images** as 0x88; the "MS_CHECKPOINT_MAX_ROOTS = 0x20" label holds only where the region is populated |
| 0x90 | 4 | Root count (u32) | Always 13 |
| 0x94 | var | Root pointer list | 13 page references (direct) or pointer to root list page (indirect) |

## Checkpoint selection and fallback

Each CHKP carries a **self-checksum verified at mount** — the algorithm is cluster-size-dependent (4-byte CRC32-C on 4K-cluster, 8-byte CRC64 on 64K-cluster, 32-byte SHA-256 on SHA-256 volumes), the same mechanism the [Superblock](supb.md) uses. At mount, `ChooseCheckpointRecord` picks the copy with the highest virtual clock among the copies that pass their checksum. An invalid higher-clock copy is skipped, falling back automatically to the lower-clock valid copy; if both fail, the mount fails. Because each flush writes the *other* slot with clock+1, the lower-clock slot always holds the previous consistent state.

## CHKP Flags (offset 0x78)

| Bit | Mask | Meaning | First Version |
|-----|------|---------|---------------|
| 1 | 0x0002 | Base flag (always set) | v3.4 |
| 7 | 0x0080 | Native format marker (not set on upgraded volumes) | v3.10 |
| 9 | 0x0200 | Indirect root list mode | v3.14 |
| 10 | 0x0400 | CRC64 metadata verification active | v3.14 |
| 4,5,8 | 0x0130 | Deduplication-related flags | v3.14 (dedup) |
| 13 | 0x2000 | Insider-only flag | Insider |

### Composite Flag Values by Version

| Version | Flags (hex) | Flags (binary) | Key Bits |
|---------|-------------|---------------|----------|
| v3.4 | 0x0002 | `0000 0000 0010` | Base |
| v3.7 | 0x0002 | `0000 0000 0010` | Same |
| v3.9 | 0x0002 | `0000 0000 0010` | Same |
| v3.10 | 0x0082 | `0000 1000 0010` | +native format |
| v3.14 native | 0x0682 | `0110 1000 0010` | +indirect roots +CRC64 |
| v3.14 upgraded | 0x0602 | `0110 0000 0010` | +indirect +CRC64, missing native |
| v3.14 dedup/compress | 0x07b2 | `0111 1011 0010` | +dedup/compression feature bits (0x130) |
| Insider (native) | 0x2682 | `0010 0110 1000 0010` | native v3.14 + Insider flag |
| Insider (upgraded) | 0x2602 | `0010 0110 0000 0010` | upgraded (no 0x080) + Insider flag |

The **0x0080 bit cleanly separates native-formatted v3.10+ volumes (set) from upgraded-from-v3.4 volumes (clear)** — an independent corroboration of the [volume information](../attributes/VOLUME_INFORMATION.md) driver-version-stamp upgrade signal.

## Direct vs Indirect Root Access

The 13 root table pointers have two encodings, selected by flag bit 0x0200:

- **Without 0x0200 (direct)**: 13 page references stored inline starting at CHKP+0x94
- **With 0x0200 (indirect)**: CHKP+0x94 holds a u32 **offset within the same checkpoint page** to the root-list region (not a pointer to a separate page — the value is far smaller than one page and equals the embedded-data base offset)

**Critical**: A parser must read the flag bit **before** decoding the root list. Reading an indirect-mode checkpoint as direct (or vice versa) yields 13 wrong root addresses.

## 13 Root Table Pointers

| Index | Table | Table ID | Schema | Addressing | Failover Pair |
|-------|-------|----------|--------|------------|---------------|
| 0 | Object ID Table | 0x02 | 0xe030 | Virtual | #5 |
| 1 | Medium Allocator | 0x21 | 0xe010 | Virtual | -- |
| 2 | Container Allocator | 0x20 | 0xe010 | Virtual | -- |
| 3 | Schema Table | 0x01 | 0xe060 | Virtual | #9 |
| 4 | Parent-Child Table | 0x03 | 0xe040 | Virtual | -- |
| 5 | Object ID Table (dup) | 0x04 | 0xe030 | Virtual | -- |
| 6 | Block Refcount | 0x05 | 0xe0b0 | Virtual | -- |
| 7 | Container Table | 0x0B | 0xe0c0 | **Real (physical)** | #8 |
| 8 | Container Table (dup) | 0x0C | 0xe0c0 | **Real (physical)** | -- |
| 9 | Schema Table (dup) | 0x06 | 0xe060 | Virtual | -- |
| 10 | Container Index | 0x0E | 0xe100 | Virtual | -- |
| 11 | Integrity State | 0x0F | 0xe080 | Virtual | -- |
| 12 | Small Allocator | 0x22 | 0xe010 | **Real (physical)** | -- |

Roots 7, 8, and 12 use real (physical) LCNs as a bootstrap exception; every other root uses [virtual addressing](../concepts/virtual_addressing.md) (VLCN → PLCN via the Container Table).

**Failover pairs**: 0/5 (Object ID), 3/9 (Schema), 7/8 (Container). Block Refcount (#6) has no failover pair.

The Container-Table failover pair (roots 7 & 8) is the **set** {0x0B, 0x0C} at roots {7, 8} — the common ordering is root 7 = 0x0B / root 8 = 0x0C, but the two can appear swapped, so the invariant is the set, not a fixed index→Table-ID order.

## Version Echo (offset 0x50)

| Scenario | Value |
|----------|-------|
| Native v3.14 | 0x000E0003 (minor=14, major=3) |
| Upgraded volumes | 0x00000000 |
| v3.4 through v3.9 | 0x00000000 |

The version echo distinguishes natively formatted v3.10+ volumes from upgraded ones.

## Virtual Clock Typical Values

| Scenario | Approximate Value |
|----------|------------------|
| Freshly formatted volume | ~20-30 |
| After ~1,000 file operations | ~50-100 |
| After v3.4 to v3.14 upgrade | +41 transactions |

## Parsing Sequence

1. Read 80-byte page header; verify signature is `"CHKP"`
2. Read version at 0x54/0x56
3. Read page reference size at 0x5C (determines stride for root list traversal)
4. Read CHKP flags at 0x78
5. Check bit 0x0200 to determine direct vs indirect root mode
6. Parse the 13 root pointers accordingly at 0x94
7. For each root, use the appropriate addressing mode (virtual for most, physical for roots 7, 8, 12)

## Cross-references

- [Superblock (SUPB)](supb.md) -- the SUPB stores pointers to the two CHKP locations
- [Page References](page_references.md) -- the page reference size at CHKP+0x5C selects the format
- [Object Table](object_table.md) -- root 0 (and failover root 5)
- [Container Table](container_table.md) -- root 7 (and failover root 8)
- [Container Index](container_index.md) -- root 10
- [Allocators](allocators.md) -- roots 1, 2, 12
- [Schema Table](schema_table.md) -- root 3 (and failover root 9)

## Evidence

The page header signature, the 13 root-table identities, the version fields, and the page-reference sizes are confirmed in the decompiled driver (E2) and the binary string literals (E1); `ValidateCheckpointRecord` checks the flag bits at CHKP+0x78 and `ChooseCheckpointRecord` performs highest-clock selection. The flag composites, the version echo, the real-LCN bootstrap exception for roots 7/8/12, and the field offsets were re-measured directly on disk across the corpus (RD). The 0x88/0x8C populated-vs-zeroed co-variation is the subject of finding FS_CHKP_RA_012, FS_CHKP_RA_005, FS_CHKP_RA_001, FS_CHKP_RA_013. The CHKP flag decomposition is FS_CHKP_RA_001. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
