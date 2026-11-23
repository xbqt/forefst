# $VOLUME_INFORMATION
<!-- site: description "The volume's version, flags, label and times, kept in a system table (OID 0x500 / 0x501), not on user objects." -->

`$VOLUME_INFORMATION` is the volume-level metadata — version, flags, label, and timestamps.

- It is not an attribute of user objects: no file's or directory's record on the corpus volumes carries it as an
  embedded sub-record.
- The volume metadata lives in the system table at OID 0x500, held as a failover pair with OID 0x501 (neither copy is
  a primary; the two hold the same rows on every volume measured), as a multi-row B+-tree keyed by system-specific key
  types.

| Property | Value |
|----------|-------|
| Table schema | 0x150, the volume-information table ([Schema Table](../structures/schema_table.md)) |
| Instances | — not a per-object sub-record: three rows of a system table |
| Where it lives | the system table at OID 0x500, a failover pair with OID 0x501 |
| Size | the key-0x520 value is 448 bytes (0x1C0); the label row is variable; the key-0x540 row is 16 bytes |
| Added in | 3.4 or earlier: present on every format read (3.4, Windows 10 1803, driver 17134, is the oldest held) |

## Value layout

OID 0x500 holds three rows:

| Key | Content |
|-----|---------|
| 0x510 | the volume label (UTF-16LE, variable length) |
| 0x520 | a 448-byte (0x1C0) `_REFS_VOLUME_INFO` metadata blob (below) |
| 0x540 | 16 bytes — the location of the verify block: u64 +0x00 its first cluster, u64 +0x08 its cluster count; at each writable mount the driver writes a copy of the 0x520 blob there |

The key-0x520 blob's populated regions are +0x80 (versions and flags), +0x90 (creation) and +0xA0 (last writable
mount), plus, on a volume whose version was rewritten by an upgrade, a u16 at +0xB0; the rest is zero on the volumes
read. No volume GUID is stored here — the volume serial lives in the VBR (VBR+0x38).

The verify block is a second copy of the 448-byte blob outside the table. On every corpus volume the 0x540 row
points at cluster 0x23 (35) with a count of 1, and that cluster begins with the blob: equal to the 0x520 row on 89
volumes, and on the other 35 different only at +0x82 to +0x84, the driver-version bytes (`InitializeVerifyBlock`;
17134, 26100.9444, Insider 29574).

<!-- site: hexfig "volinfo_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x80 | 1 | Volume major version | echoes VBR+0x28; changes only on a real format upgrade |
| 0x81 | 1 | Volume minor version | echoes VBR+0x29 |
| 0x82 | 1 | Driver major version | written by `SetVolumeMounted` at each writable mount (a read-only mount leaves it) |
| 0x83 | 1 | Driver minor version | the mounting driver's own constant, written at each writable mount: the driver of the last writable mount (see [Version stamping](#version-stamping--a-forensic-discriminator)) |
| 0x84 | 4 | Volume flags | `_REFS_VOLUME_FLAGS` (read by `RefsGetVolumeInformation`): the format bits 0x180 mark a pre-3.10 format (see [Volume flags](#volume-flags)) |
| 0x90 | 8 | Volume creation time | FILETIME; set at format; the mount path copies it to the VCB and does not rewrite it |
| 0x98 | 8 | Secondary FILETIME slot | propagated to VCB+0x208/0x210; 0 on sampled volumes |
| 0xA0 | 8 | Last mount (rw) | FILETIME: the time of the last mount that can write (see [The last-mount time](#the-last-mount-time)) |
| 0xB0 | 2 | Upgrade word (u16) | written when a mount rewrites the volume version (an upgrade), copied from the driver's VCB+0x31c; its meaning is not read. 0 on the native volumes read |

### Volume flags

The u32 at +0x84:

- 0x180 (bits 0x080 | 0x100) on formats 3.4, 3.7 and 3.9: a pre-3.10 format marker that persists across an upgrade
  (an upgraded v3.4→v3.14 volume still shows 0x180);
- neither bit on a native-formatted 3.10 or later volume;
- 0x200 = heat-gathering disabled (the `disableheatgathering` tunable);
- the driver sets further state bits that can appear on any volume (0x008, 0x020, 0x200, 0x400, 0x800), and
  `SetVolumeMounted` clears 0x004 at every writable mount.

### The last-mount time

+0xA0 is the time of the last mount that can write.

- The driver's mount path (`SetAndGetVolumeTimes`) writes the current system time here unless the volume is mounted
  without writes; the row's other writers read in 26100.9711 leave it.
- Measured on a lab volume over five read-write mounts and one read-only mount (Windows 11 24H2, 26100.9711): it
  moved at each read-write mount, and not at the read-only mount nor at any later write.

## Version stamping — a forensic discriminator

The volume version (+0x80/+0x81) and the driver version (+0x82/+0x83) are independent:

- the volume version advances only on a real format upgrade;
- the driver stamp records the driver of the last writable mount, overwritten at every writable mount with the
  mounting driver's own constant and no comparison (0x403 = 17134, 0xe03 = 26100.x, 0xf03 = Insider 29574); a later
  writable mount by an older driver replaces it, and a read-only or write-blocked mount leaves it.

The volume flags are one more native-versus-upgraded marker, alongside the checkpoint flag 0x080 and the VBR flags
(0x2C) and GUID (0x48): a native-formatted 3.10 or later volume has neither 0x080 nor 0x100 set in these flags, while
a volume upgraded from v3.4 keeps 0x180.

A `0xf03` (Insider) driver stamp shows that the last writable mount was by an Insider build; its absence does not show
that no Insider build ever mounted the volume.

## Cross-references

- [System OIDs](../structures/system_oids.md) — OID 0x500 / 0x501 volume metadata
- [Volume Information](../structures/volume_info.md) — the system-table layout
- [Version Detection](../concepts/version_detection.md) — the VBR and checkpoint fields that classify a volume (this blob's 0x180 flag is a further marker)

## Evidence

Schema 0x150, the OID 0x500/0x501 storage, and the blob layout are read in the decompiled driver
(`RefsGetVolumeInformation`, `SetVolumeMounted`, `InitializeVolumeInfoTable`) and measured on the corpus. The
version stamp: `SetVolumeMounted` stores the mounting driver's own constant with no comparison, and only on a
writable mount (read in six builds, 17134 to Insider 29574). The page is documented against the project's claim
register. See [how this was verified](../methodology.md).

The measurements and readings behind the text:

- The two copies of the 0x500 / 0x501 pair hold the same rows on 117 of 117 corpus volumes.
- +0xB0: 0x0002 in both copies on the upgraded volume `win10to11refs4g`; 0 on the two native volumes read.
  `InitializeVolumeInfoTable` (26100.9444) writes it with the new version when the stored version differs from the
  mounted format.
- The volume flags 0x180 / no format bits: measured over 110 images.

<!-- findings: FS_OTBL_RA_004, FS_VINF_001, FS_VOLI_RA_001, FS_VOLI_RA_002 -->
