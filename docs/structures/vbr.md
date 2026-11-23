# Volume Boot Record (VBR)

The VBR is a 512-byte structure at sector 0 of the ReFS partition.

It provides the format parameters every later structure depends on: the cluster size, the version and, on volumes
formatted at 3.10 or later, the checksum selector.

A backup copy is kept at the end of the volume:

- refs.sys writes it at the volume's last sector (before it writes sector 0);
- at mount, it reads it at sector floor(P / 64 MiB) x (64 MiB / sector size) - 1 of the partition (P its length;
  the same sector when the partition is a whole number of 64 MiB), and only when the read of sector 0 fails with an
  I/O error.

A sector 0 that reads is used whatever it holds, and one that fails the boot-sector tests fails the mount; no driver
code compares the two copies (read on 17134, 26100.9444 and Insider 29574).

## Field layout

<!-- site: hexfig "vbr_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 3 | Jump instruction | `00 00 00` -- no x86 jump, also on the corpus's Insider 29574 boot volume |
| 0x03 | 8 | File system name | ASCII `"ReFS\0\0\0\0"` |
| 0x0B | 5 | Reserved | All zeros |
| 0x10 | 4 | FSRS identifier | ASCII `"FSRS"` signature (`0x46535253`) |
| 0x14 | 2 | VBR size (u16) | `0x0200` (512) on every volume measured. It is the length the checksum at 0x16 covers; the driver accepts a value above `0x57` and at most the sector size |
| 0x16 | 2 | VBR checksum (u16) | ROR-1 + ADD over bytes 3 to (0x14) - 1, excluding offsets 0x16-0x17: bytes 3..511 when 0x14 is `0x0200` (see Checksum algorithm below) |
| 0x18 | 8 | Total sector count (u64) | Volume size in units of the sector size in the field above — **512 on a 512e volume, 4096 on a 4Kn one**. Multiply by `0x20`, never by a constant |
| 0x20 | 4 | Bytes per sector (u32) | **512** on a 512e volume and **4096** on a 4Kn one; both occur on the volumes measured ([4Kn volumes](#4kn-volumes)) |
| 0x24 | 4 | Sectors per cluster (u32) | **1, 8 or 128** on the volumes measured; the cluster size is the **product** of `0x20` and `0x24` ([4Kn volumes](#4kn-volumes)) |
| 0x28 | 1 | Major version (u8) | 3 on all covered volumes |
| 0x29 | 1 | Minor version (u8) | 4–14 -- see Version values below |
| 0x2A | 2 | Checksum algorithm selector (u16) | See Checksum algorithm selector below |
| 0x2C | 4 | Volume flags (u32) | See Volume flags below |
| 0x30 | 8 | Reserved | All zeros |
| 0x38 | 8 | Volume serial number (u64) | Unique per volume, set at format (`refsutil fixboot` zeroes it: [Cautions](#cautions)) |
| 0x40 | 8 | Bytes per container (u64) | `0x04000000` (64 MiB) on every volume measured but the one `refsutil fixboot` rewrote (0: [Cautions](#cautions)) |
| 0x48 | 16 | Extended GUID | All-zero (pre-v3.10 or upgraded) or populated (native v3.10+ format) |
| 0x58 | 424 | Unused | All zeros |

### 4Kn volumes

Two lab volumes of the measured set are real 4Kn volumes: their VBR declares 4096 bytes per sector, and every file
on them was verified against the operator's own SHA-256 inventory. The other volumes, across every format, are 512e.

The cluster size is the product of `0x20` and `0x24`, so the same 4 KiB cluster is reached by two different sector
counts. The three geometries measured:

- 4096 x 1 = 4 KiB (4Kn);
- 512 x 8 = 4 KiB;
- 512 x 128 = 64 KiB.

The tools look for the GPT at byte 512 **and**, failing that, at 4096.

## Derived values

- **Cluster size** = `bytes_per_sector * sectors_per_cluster`
- **Clusters per container (CPC)** = `bytes_per_container / cluster_size`
  - 4 KiB clusters: CPC = 16,384
  - 64 KiB clusters: CPC = 1,024

The bytes-per-container value at 0x40 sets the container size that virtual-to-physical address translation through
the [Container Table](container_table.md) uses. When the field is 0 (what `refsutil fixboot` writes), refs.sys uses
the 64 MiB default ([Cautions](#cautions)).

## Version values (offset 0x28)

| Bytes 0x28 / 0x29 | Major | Minor | Windows release |
|-------------|-------|-------|-----------------|
| 03 04 | 3 | 4 | Win10 1803 |
| 03 07 | 3 | 7 | Win11 21H2 |
| 03 09 | 3 | 9 | Win11 22H2 |
| 03 0A | 3 | 10 | Win11 23H2 |
| 03 0E | 3 | 14 | Win11 24H2 / Insider 29574 |

**Warning:** The version field records the volume's upgrades, not the original format version. On the two upgrades
measured (from 3.4 and from 3.9), a Windows 11 mount rewrote the version to 3.14.

## Checksum algorithm selector (offset 0x2A)

| Value | Algorithm | Where it is found | Page reference size |
|-------|-----------|-------------------|---------------------|
| 0x0000 | not read: the volume uses CRC64 | the volumes formatted at 3.4, 3.7 or 3.9, those upgraded from them, and a boot sector `refsutil fixboot` rewrote; their flags at 0x2C lack 0x40, so the driver does not read 0x2A, and their page references carry CRC64 | 0x68 (104 bytes) on 3.4 to 3.9; 0x30 once upgraded to 3.14 |
| 0x0002 | CRC-64/NVME (reflected poly 0x9A6C9329AC4BC9B5, **not** ECMA-182) | the volumes formatted at 3.10 or later (flags 0x40 set) | 0x30 (48 bytes) |
| 0x0004 | SHA-256 | volumes formatted with SHA-256 (flags 0x40 set) | 0x48 (72 bytes) |
| 0x0005 | XXH64 (the driver's list; seen on no volume measured, not computed by the tools) | — | — |

This field is set at format time, and an upgrade does not change it (the two upgrades measured). No 26100.9444
boot-sector write path assigns it; `refsutil fixboot` rewrites it.

refs.sys 26100 and Insider read it only when the flags at 0x2C carry 0x40, and use CRC64 otherwise; 17134 never reads
it. An upgraded volume (v3.4 to v3.14) keeps `0x0000` here, and the driver uses CRC64 because its flags lack 0x40.

A value of 0x0000 therefore does not mean a volume without checksums: the page references of every such volume
measured carry CRC64.

The authority for the on-disk [page reference](page_references.md) format is the **checkpoint's** page-reference size
at CHKP+0x5C: an upgraded volume still reads `0x0000` here while its checkpoint has moved to the 48-byte CRC64
reference.

## Volume flags (offset 0x2C)

| Bit | Mask | Meaning | First version |
|-----|------|---------|---------------|
| 0 | 0x01 | Break on corruption: set or cleared at run time by `RefsSetBreakOnCorrupt` | — |
| 1 | 0x02 | Mount marker: set by a writable mount | v3.4 |
| 2 | 0x04 | Schema set: with it the 17134 driver mounts the volume with the schema set 0x180 / 0x1A0 / 0x190 (file, data stream, directory), without it with an older set (0x110 / 0x120 / 0x170); 26100.9444 refuses a volume below 3.6 without it. Set at format time; on every volume measured whose flags were not edited by hand | v3.4 |
| 4 | 0x10 | Salvage: set at run time by `MsKmeUpdateBootSector` | — |
| 5 | 0x20 | **Hard-link support**: the driver allows hard links on the volume exactly when this bit is set (see below) | v3.7 |
| 6 | 0x40 | Native v3.10+ format: refs.sys 26100 and Insider read the checksum selector 0x2A only when it is set | v3.10 |
| 7 | 0x80 | Upgrade requested: set by `RefsMarkVolumeForUpgrade`, cleared when the next writable mount upgrades the version (`RefsUpgradeVersionInBootSector`); not on any volume measured | — |

The run-time writers of 0x01 and 0x10 are read on 17134 and 26100.9444, those of 0x80 on 26100.9444 (17134 has
none). The format bits 0x20 and 0x40 kept their values across the two upgrades measured (3.4 to 3.14 and 3.9 to
3.14).

Observed composite values:
- `0x06` -- v3.4
- `0x26` -- v3.7 / v3.9
- `0x66` -- v3.10+

### Bit 0x20 is what the driver tests for hard-link support

`RefsHardlinksSupported` (win11 refs.sys 10.0.26100.8115, `14008f034`) is a single comparison:

```c
return *(short *)(VCB + 0x2acc) == 0x39;
```

and that VCB field is built from this flag, at `487472` of the same build:

```c
*(ushort *)(VCB + 0x2acc) = (ushort)(*(uint *)(VBR + 0x2c) >> 5) & 1 | 0x38;
```

`0x38` with bit 5 of the volume flags shifted in, so the field is `0x39` exactly when **bit 0x20 is
set** and `0x38` when it is clear. The equality test *is* the bit test, one indirection away — other
call sites compare against `0x38` for the bit-clear behaviour.

**On disk:** across the corpus, the flag and the presence of hard links agree on **every volume whose VBR is intact**:

- a volume with the bit set has hard links or none (the bit says *supported*, not *used*);
- a volume with the bit clear has none.

The single volume with hard links and the bit clear is one whose VBR `refsutil fixboot` rewrote, and its fields show the
cause: `refsutil fixboot` left `volume_flags = 0x04` with **serial = 0 and container size = 0** (the values
fixboot writes), while the hard links created before it remain in the metadata. Its pre-fixboot sibling carries `0x66` with
the bit set.

## VBR field classification

| Field | Classification |
|-------|---------------|
| Version (0x28) | **Critical** -- a version above the driver's maximum fails the mount (tested in `RefsMountVolume`, not in the boot-sector check) |
| Checksum algorithm (0x2A) | Read only when the flags at 0x2C carry 0x40 (otherwise the volume uses CRC64, whatever 0x2A holds). With 0x40 set, a value of 1 (CRC32-C) is refused as the metadata checksum type when the volume starts, and 3 or a value above 5 gives the volume no metadata checksums |
| VBR checksum (0x16) | **Critical** -- mismatch prevents mount |
| Volume flags (0x2C) | Semi-critical -- determines available capabilities |
| Volume serial (0x38) | Informational -- arbitrary values preserved on mount |
| Extended GUID (0x48) | Informational -- arbitrary values preserved on mount |

## Checksum algorithm

The VBR checksum (offset 0x16) is computed by `RefsIsBootSectorOurs`:

```text
checksum = 0 (u16)
for i = 3 to u16(VBR[0x14]) - 1:      // the boot sector's own length, 0x57 < it <= the sector size
    if i == 0x16 or i == 0x17: skip
    checksum = (checksum >> 1) | (checksum << 15)  // rotate right 1
    checksum = (checksum + VBR[i]) & 0xFFFF
compare checksum with stored value at VBR[0x16]
```

## Version-specific notes

- **v3.10+**: Extended GUID at 0x48 is populated. On earlier versions this field is all-zero.
- **Upgraded volumes**: VBR 0x2A stays 0x0000, the flags keep their format value (0x06 on the volume upgraded
  from 3.4, 0x26 on the one upgraded from 3.9), and the Extended GUID stays all-zero. Their flags lack 0x40, so
  `InitializeVcbFromBootSector` (26100 and Insider) does not read 0x2A and gives the volume CRC64; it also extracts
  the geometry from the boot sector.
- **Insider boot volume**: the test corpus's Insider 29574 boot volume (the C: drive that machine booted from) also
  holds `00 00 00` at 0x00: the boot does not go through a jump in the VBR.

## Cautions

- `refsutil fixboot` rewrites the boot sector. On the one image measured it zeroes the container size (+0x40), the
  volume serial (+0x38), the checksum selector (+0x2A) and the Extended GUID (+0x48), sets the volume flags (+0x2C) to
  0x04 (they were 0x66), and recomputes the checksum, so the copy it writes passes. When it mounts the volume refs.sys
  puts 64 MiB in its copy of the container size, and a writable mount writes that back to the boot sector (read on
  26100.8115/.9549, 26100.9444 and 17134).
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
| `0x03` | `52 65 46 53` | File system name | `ReFS` |
| `0x10` | `46 53 52 53` | FSRS identifier | `FSRS` |
| `0x28` | `03 0e` | Major / minor version | **3.14** |
| `0x2A` | `02 00` | Checksum algorithm selector | `0x0002` (CRC64) |
| `0x2C` | `66 00 00 00` | Volume flags | `0x66` |
| `0x40` | `00 00 00 04` | Bytes per container | `0x04000000` (64 MiB) |
| `0x48` | `00 b2 8e 59 …` | Extended GUID | populated (native v3.10+ format) |

## Cross-references

- [Superblock (SUPB)](supb.md) -- at the fixed cluster 30 (LCN 0x1E): the VBR's cluster size locates it
- [Checkpoint (CHKP)](chkp.md) -- SUPB stores pointers to two alternating checkpoints
- [Page References](page_references.md) -- their size is the checkpoint's CHKP+0x5C, not this checksum selector
- [Container Table](container_table.md) -- the bytes-per-container constant feeds VLCN to PLCN translation

## An encrypted volume shows a different signature

When BitLocker encrypts the volume, the ReFS signature at `+0x03` is replaced by the FVE marker
`-FVE-FS-`. A reader that keys on the ReFS signature alone will call such a volume unrecognised rather
than encrypted; the distinction matters: an unrecognised volume is not ReFS, while an encrypted one is a
ReFS volume that must be decrypted before it can be read. Measured on format 3.14.

## Evidence

The field layout, signatures, and checksum loop are confirmed by the string literals and the decompiled driver:
`RefsIsBootSectorOurs` validates the boot sector and computes the 0x16 checksum, and `InitializeVcbFromBootSector`
extracts the geometry.

The field values, the format-time fields kept across the upgrades measured, and the `refsutil fixboot` effects are
measured on the disk across the corpus. So are the custom CRC64 polynomial (not ECMA-182; the checksums recomputed
from the bytes) and the BitLocker `-FVE-FS-` marker replacing the signature at `+0x03`.

The counts behind the text:

- VBR size `0x0200` on 124 of 124 volumes;
- the 4Kn volumes are `lab314_4kn` and `lab314_4kn_step2` (626 of 626 files verified against the operator's SHA-256
  inventory); the three cluster geometries were measured on `lab314_4kn` (4096 x 1), `lab314_main` (512 x 8) and
  `lab314_64k` (512 x 128);
- flag 0x04 on 122 of 122 volumes of the regression corpus whose flags were not edited by hand (2026-11-21; the two
  without it are the two images whose flags were edited by hand);
- the hard-link flag against the presence of hard links (a type-0x40 backing whose link count, `$SI+0x70`, is 2 or more),
  over the 124 ReFS volumes of the regression corpus (2026-11-21): on the 123 with an intact VBR, 74 with the bit set
  and hard links, 37 with the bit set and none, 12 with the bit clear and none; the one volume with hard links and
  the bit clear (17 linked files) is `win11refs2tmillionsofactions_aftersalvage_fixboottest.raw`.

See [how this was verified](../methodology.md) for the method.

<!-- findings: FS_VBR_001, FS_VBR_002, FS_VBR_003, FS_VBR_004, FS_VBR_005, FS_VBR_006, FS_VBR_007,
               FS_VBR_009, FS_VBR_010, FS_VBR_012, FS_VBR_013, FS_VBR_RA_002, FS_VBR_RA_004, FS_VBR_RA_005,
               FS_VBR_RA_006, FS_VBR_RA_007, FS_VBR_RA_010, FS_VBR_RA_012, FS_VBR_SA_013, GN_INS_SA_001,
               GN_PREF_002 -->
