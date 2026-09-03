# Page References

A page reference binds a child page's address to a checksum of that child's contents. Every B+-tree parent stores a page reference for each child, chaining the whole metadata tree into a Merkle tree anchored at the [checkpoint](chkp.md).

The page reference exists in three version- and checksum-dependent formats. Assuming the wrong format misaligns every field that follows, because the page reference size is the stride used to walk a checkpoint root list or B+-tree node.

## Format 1: 104 bytes (0x68) -- ReFS v3.4 through v3.9

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | LCN slot 0 (u64) | First cluster of referenced page |
| 0x08 | 8 | LCN slot 1 (u64) | Second cluster |
| 0x10 | 8 | LCN slot 2 (u64) | Third cluster |
| 0x18 | 8 | LCN slot 3 (u64) | Fourth cluster |
| 0x20 | 2 | Flags (u16) | 0x0000 |
| 0x22 | 1 | Checksum type (u8) | See Checksum Type Codes below |
| 0x23 | 1 | Checksum data offset (u8) | 0x08 |
| 0x24 | 4 | Checksum data length (u32) | 8 (CRC64) |
| 0x28 | 8 | CRC64 checksum | Written; **apparently not verified** before v3.14 (driver-code reading, untested — see below) |
| 0x30 | 56 | Padding | Zero-filled |

**Total**: 104 bytes (0x68)

CRC64 values are written at format time but the mount path instantiates `CmsChecksumNone` (a stub whose `VerifyChecksum` always returns success without comparison), so metadata-page checksums appear not to be verified on these versions.

> **This rests on decompilation alone.** No behavioural test backs it here, and it sits against Microsoft's long-standing statement that ReFS validates metadata checksums. The decisive experiment is cheap and has not been run: flip one byte in a child page of a ReFS 3.4 volume and mount it on the matching Windows build — if the volume mounts and reads the page without complaint, the stub behaves as the code reads. Until then treat this as **something read out of the driver code, not an observed behaviour**.

## Format 2: 48 bytes (0x30) -- ReFS v3.10+ with CRC64

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | LCN slot 0 (u64) | First cluster |
| 0x08 | 8 | LCN slot 1 (u64) | Second cluster |
| 0x10 | 8 | LCN slot 2 (u64) | Third cluster |
| 0x18 | 8 | LCN slot 3 (u64) | Fourth cluster |
| 0x20 | 2 | Flags (u16) | 0x0000 |
| 0x22 | 1 | Checksum type (u8) | 0x02 (CRC-64/NVME — not ECMA-182) |
| 0x23 | 1 | Checksum data offset (u8) | 0x08 |
| 0x24 | 4 | Checksum data length (u32) | 8 |
| 0x28 | 8 | CRC64 checksum | Verified at mount from v3.14 |

**Total**: 48 bytes (0x30). Same as Format 1 with the padding removed.

## Format 3: 72 bytes (0x48) -- ReFS v3.14 with SHA-256

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | LCN slot 0 (u64) | First cluster |
| 0x08 | 8 | LCN slot 1 (u64) | Second cluster |
| 0x10 | 8 | LCN slot 2 (u64) | Third cluster |
| 0x18 | 8 | LCN slot 3 (u64) | Fourth cluster |
| 0x20 | 2 | Flags (u16) | 0x0000 |
| 0x22 | 1 | Checksum type (u8) | SHA-256 selector |
| 0x23 | 1 | Checksum data offset (u8) | 0x08 |
| 0x24 | 4 | Checksum data length (u32) | 32 |
| 0x28 | 32 | SHA-256 digest | Computed over child page |

**Total**: 72 bytes (0x48)

## Checksum Type Codes (offset +0x22)

| Value | Algorithm | Notes |
|-------|-----------|-------|
| 0x00 | None | No verification |
| 0x01 | CRC32-C | CHKP self-descriptor only |
| 0x02 | CRC-64/NVME (reflected poly 0x9A6C9329AC4BC9B5, not ECMA-182) | Standard metadata verification |

## Format Selection Rule

The format is determined by the [VBR](vbr.md) checksum algorithm selector (offset 0x2A) and the [CHKP](chkp.md) page reference size field (offset 0x5C):

| VBR 0x2A | CHKP 0x5C | Format |
|----------|-----------|--------|
| 0x0000 | 0x68 | 104-byte (v3.4) |
| 0x0002 | 0x30 | 48-byte (CRC64) |
| 0x0004 | 0x48 | 72-byte (SHA-256) |

## Verification Behavior by Version

| Property | Win10 (v3.4) | Win11 (v3.14) |
|----------|-------------|---------------|
| VBR 0x2A | 0x0000 (None) | 0x0002 (CRC64) |
| CHKP flags bit 0x400 | Not set | Set |
| Verification class | CmsChecksumNone (stub) | CmsChecksum (real CRC64) |
| CRC64 in page refs | Written; verification stubbed out *(read from the driver, untested)* | Written and verified |

On upgraded volumes (v3.4 to v3.14): VBR 0x2A remains 0x0000 but CHKP flag 0x0400 is set. The driver uses CHKP flags (not VBR 0x2A) as the runtime indicator.

## Checkpoint Self-Checksum

The CHKP self-descriptor **page reference** carries checksum **type 0x01 (CRC32-C)**. Separately, the SUPB/CHKP **block** itself carries a **cluster-size-dependent self-checksum** (a `LcnWithChecksum` self-descriptor at SUPB+0xD0, computed over one cluster with the descriptor zeroed; the algorithm is named by the cktype byte at descriptor+0x22): **CRC32-C / 4 B on 4K-cluster** volumes, **CRC64 / 8 B on 64K**, **SHA-256 / 32 B on SHA-256** volumes. It **is verified at mount** and self-healed on mismatch.

## Cross-references

- [VBR](vbr.md) -- checksum algorithm selector at offset 0x2A determines format
- [Checkpoint (CHKP)](chkp.md) -- page reference size at CHKP+0x5C; checkpoint is Merkle root
- [Page Header](page_header.md) -- the 80-byte header precedes page reference areas in B+-tree nodes

## Evidence

The three formats, the field layout, the checksum-type codes, and the format-selection rule are confirmed in the decompiled driver (E2). The CRC64 is **CRC-64/NVME** (reflected poly 0x9A6C9329AC4BC9B5, check value 0xAE8B14860A799888) — not ECMA-182; finding GN_PREF_002. The non-verification on v3.4 follows from `CmsChecksumNone::VerifyChecksum` always returning TRUE — a driver-code inference with no behavioural test — replaced in v3.14 by the unified `CmsChecksum` class that performs real CRC64 computation. The cluster-size-dependent SUPB/CHKP self-checksum, verified and self-healed at mount, is finding FS_SUPB_006, FS_CHKP_004, FS_SUPB_RA_003. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
