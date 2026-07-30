# Volume Boot Record (VBR)

The VBR is a 512-byte structure at sector 0 of the ReFS partition. It provides the format
parameters -- cluster size, version, checksum mode -- that every later structure depends on. A
backup copy resides in the last sector of the volume.

## Field layout

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 3 | Jump instruction | `00 00 00` -- no x86 jump; ReFS is not legacy-BIOS bootable (the Insider build adds boot support) |
| 0x03 | 8 | File system name | ASCII `"ReFS\0\0\0\0"` |
| 0x0B | 5 | Reserved | All zeros |
| 0x10 | 4 | FSRS identifier | ASCII `"FSRS"` signature (`0x46535253`) |
| 0x14 | 2 | VBR size (u16) | Always `0x0200` (512) |
| 0x16 | 2 | VBR checksum (u16) | ROR-1 + ADD over bytes 3..511, excluding offsets 0x16-0x17 |
| 0x18 | 8 | Total sector count (u64) | Volume size in 512-byte sectors |
| 0x20 | 4 | Bytes per sector (u32) | Always 512 |
| 0x24 | 4 | Sectors per cluster (u32) | 8 (4 KiB clusters) or 128 (64 KiB clusters) |
| 0x28 | 1 | Major version (u8) | 3 on all covered volumes |
| 0x29 | 1 | Minor version (u8) | 4–14 -- see Version values below |
| 0x2A | 2 | Checksum algorithm selector (u16) | See Checksum algorithm selector below |
| 0x2C | 4 | Volume flags (u32) | See Volume flags below |
| 0x30 | 8 | Reserved | All zeros |
| 0x38 | 8 | Volume serial number (u64) | Unique per volume |
| 0x40 | 8 | Bytes per container (u64) | `0x04000000` (64 MiB, invariant) |
| 0x48 | 16 | Extended GUID | All-zero (pre-v3.10 or upgraded) or populated (native v3.10+ format) |
| 0x58 | 424 | Unused | All zeros |

## Derived values

- **Cluster size** = `bytes_per_sector * sectors_per_cluster`
- **Clusters per container (CPC)** = `bytes_per_container / cluster_size`
  - 4 KiB clusters: CPC = 16,384
  - 64 KiB clusters: CPC = 1,024

The bytes-per-container value at 0x40 is the constant that drives virtual-to-physical address
translation; without it the mount code cannot resolve virtual LCNs through the
[Container Table](container_table.md).

## Version values (offset 0x28)

| Bytes 0x28 / 0x29 | Major | Minor | Windows release |
|-------------|-------|-------|-----------------|
| 03 04 | 3 | 4 | Win10 1803 |
| 03 07 | 3 | 7 | Win11 21H2 |
| 03 09 | 3 | 9 | Win11 22H2 |
| 03 0A | 3 | 10 | Win11 23H2 |
| 03 0E | 3 | 14 | Win11 24H2 / Insider 29574 |

**Warning:** The version field records mount history, not the original format version. A
v3.4-formatted volume mounted on Win11 will have its version updated to 3.14.

## Checksum algorithm selector (offset 0x2A)

| Value | Algorithm | Metadata verification | Page reference size |
|-------|-----------|----------------------|---------------------|
| 0x0000 | None | Disabled (`CmsChecksumNone` stub) | 0x68 (104 bytes) |
| 0x0002 | CRC64 (custom poly 0x9A6C9329AC4BC9B5, **not** ECMA-182) | Enabled from v3.10+ | 0x30 (48 bytes) |
| 0x0004 | SHA-256 | Enabled | 0x48 (72 bytes) |

This field is set at format time and **never modified** during version upgrades. On upgraded
volumes (v3.4 to v3.14), VBR 0x2A remains 0x0000 even though the driver activates CRC64 via CHKP
flags. The selector also determines the on-disk
[page reference](page_references.md) format, so it must be read before any tree page can be parsed.

## Volume flags (offset 0x2C)

| Bit | Mask | Meaning | First version |
|-----|------|---------|---------------|
| 1 | 0x02 | Mount marker | v3.4 |
| 2 | 0x04 | Always set | v3.4 |
| 5 | 0x20 | Win11 format | v3.7 |
| 6 | 0x40 | Native v3.10+ format (gates checksum) | v3.10 |

Observed composite values:
- `0x06` -- v3.4
- `0x26` -- v3.7 / v3.9
- `0x66` -- v3.10+

## VBR field classification

| Field | Classification |
|-------|---------------|
| Version (0x28) | **Critical** -- invalid value prevents mount |
| Checksum algorithm (0x2A) | **Critical** -- invalid value prevents mount |
| VBR checksum (0x16) | **Critical** -- mismatch prevents mount |
| Volume flags (0x2C) | Semi-critical -- determines available capabilities |
| Volume serial (0x38) | Informational -- arbitrary values preserved on mount |
| Extended GUID (0x48) | Informational -- arbitrary values preserved on mount |

## Checksum algorithm

The VBR checksum (offset 0x16) is computed by `RefsIsBootSectorOurs`:

```
checksum = 0 (u16)
for i = 3 to 511:
    if i == 0x16 or i == 0x17: skip
    checksum = (checksum >> 1) | (checksum << 15)  // rotate right 1
    checksum = (checksum + VBR[i]) & 0xFFFF
compare checksum with stored value at VBR[0x16]
```

## Version-specific notes

- **v3.10+**: Extended GUID at 0x48 is populated. On earlier versions this field is all-zero.
- **Upgraded volumes**: VBR 0x2A stays 0x0000, VBR flags stay 0x06, Extended GUID stays all-zero.
  The driver uses CHKP flags (not VBR 0x2A) as the runtime checksum indicator. Geometry extraction
  from the boot sector is handled by `InitializeVcbFromBootSector`.
- **Insider build**: Jump instruction at 0x00 may contain a real x86 jump (first bootable ReFS
  version).

## Cautions

- `refsutil fixboot` is **destructive**: it zeroes the container size, volume serial, checksum
  algorithm selector, Extended GUID, and volume flags fields.
- The VBR version field reflects mount history, not original format version. Cross-check with the
  superblock or checkpoint for provenance.

## Raw example

From a v3.14 image, the VBR at the partition start (byte offset `0x1000000`):

```text
0x00:  00 00 00 52 65 46 53 00  00 00 00 00 00 00 00 00   |...ReFS.........|
0x10:  46 53 52 53 00 02 b2 7a  00 00 7e 00 00 00 00 00   |FSRS......~.....|
0x20:  00 02 00 00 08 00 00 00  03 0e 02 00 66 00 00 00   |............f...|
0x30:  00 00 00 00 00 00 00 00  44 99 a9 5a a6 a9 5a 00   |........D..Z..Z.|
0x40:  00 00 00 04 00 00 00 00  00 b2 8e 59 d7 ab 80 45   |...........Y...E|
```

| Offset | Bytes | Field | Value |
|--------|-------|-------|-------|
| `0x03` | `52 65 46 53` | FS name | `ReFS` |
| `0x10` | `46 53 52 53` | FSRS signature | `FSRS` |
| `0x28` | `03 0e` | Version | **3.14** |
| `0x2A` | `02 00` | Checksum selector | `0x0002` (CRC64) |
| `0x2C` | `66 00 00 00` | Volume flags | `0x66` |
| `0x40` | `00 00 00 04` | Bytes per container | `0x04000000` (64 MiB) |
| `0x48` | `00 b2 8e 59 …` | Extended GUID | populated (native v3.10+ format) |

## Cross-references

- [Superblock (SUPB)](supb.md) -- located at cluster 30; VBR points to it via fixed offset
- [Checkpoint (CHKP)](chkp.md) -- SUPB stores pointers to two alternating checkpoints
- [Page References](page_references.md) -- format depends on VBR checksum algorithm selector
- [Container Table](container_table.md) -- the bytes-per-container constant feeds VLCN to PLCN translation

## Evidence

The field layout, signatures, and checksum loop are confirmed by the string literals (E1) and the
decompiled driver (E2) -- `RefsIsBootSectorOurs` validates the boot sector and computes the 0x16
checksum, and `InitializeVcbFromBootSector` extracts the geometry; the field values, the immutable
format-time fields on upgrade, and the `refsutil fixboot` effects are raw-disk verified across the
corpus (RD). The custom CRC64 polynomial (not ECMA-182) is finding GN_PREF_002. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
