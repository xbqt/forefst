# Superblock (SUPB)

The Superblock is the fixed-location volume anchor that points to the two alternating checkpoints.

Its primary copy always resides at cluster 30 (LCN 0x1E), occupying a single cluster; two backups sit at the end of
the volume ([Location and copies](#location-and-copies)).

## Field layout

<!-- site: hexfig "supb_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 80 | Page header | Common metadata page header (see [Page Header](page_header.md)) with signature `"SUPB"` |
| 0x50 | 16 | Volume GUID | Unique per-volume identifier |
| 0x60 | 8 | Reserved | Always zero |
| 0x68 | 8 | Generation (u64) | A generation that orders only the two backups; only an extend of the volume bumps it ([which copy is read](#location-and-copies)) |
| 0x70 | 4 | Checkpoint refs offset (u32) | Byte offset to checkpoint LCN list; typically 0xC0 |
| 0x74 | 4 | Checkpoint refs count (u32) | Always 2 |
| 0x78 | 4 | Self-descriptor offset (u32) | Offset to the SUPB self-descriptor: 0xD0 on every copy measured |
| 0x7C | 4 | Self-descriptor length (u32) | 0x68 (v3.4), 0x30 (v3.14 CRC64), 0x48 (SHA-256) |
| 0xC0 | 8 | Checkpoint LCN 1 (u64) | At offset specified by +0x70 |
| 0xC8 | 8 | Checkpoint LCN 2 (u64) | Second checkpoint location |

## Location and copies

There are three SUPB copies on every volume:

- **Primary**: Cluster 30 (LCN 0x1E)
- **Backup 1**: `VolSize − 2` (i.e. `total_clusters − 2`)
- **Backup 2**: `VolSize − 3` (i.e. `total_clusters − 3`)

The backup locations are computed from the volume size by `CmsVolume::ReadSuperBlock`.

**Which copy is read.** refs.sys reads the copies in the order LCN 0x1E, N−2, N−3 and takes the first that passes its
tests. A later valid copy replaces it only when its +0x68 is strictly higher **and** the chosen copy is not the
primary, so:

- a primary at LCN 0x1E that passes its tests is read whatever the backups hold;
- +0x68 decides only between the two backups (end-2 on a tie).

The +0x68 generation is not a constant "version": only an extend of the volume bumps it. It reads **1 on every copy
measured**, so a "highest value wins" rule discriminates between the copies on no volume in the corpus.

In practice the authoritative copy is the primary when it passes its tests, otherwise the first backup that does.

## Self-descriptor

The self-descriptor length varies by checksum configuration:

| Configuration | Self-descriptor length |
|---------------|----------------------|
| v3.4 | 0x68 (104 bytes) |
| v3.14 CRC64 | 0x30 (48 bytes) |
| SHA-256 | 0x48 (72 bytes) |

Each SUPB copy carries a **cluster-size-dependent self-checksum**: a `LcnWithChecksum` self-descriptor at SUPB+0xD0.

- Its fields: the cktype byte at descriptor+0x22, the data-offset byte at descriptor+0x23 (= 0x08), the length at
  descriptor+0x24, and the digest at descriptor+0x28.
- The checksum is computed over one cluster with the descriptor zeroed.
- The algorithm is named by the cktype byte: **CRC32-C / 4 bytes on 4K-cluster** volumes (cktype 1), **CRC64 /
  8 bytes on 64K-cluster** volumes (cktype 2), and **SHA-256 / 32 bytes on SHA-256** volumes (cktype 4).

The SUPB sits outside the page-reference Merkle tree — no parent structure stores a checksum of it — but it is **not
unchecked**: the self-checksum IS verified at mount (`ValidateSuperBlock` → `ComputeOrVerifySelfChecksumBlock`).

A copy that fails its self-checksum is not chosen. After the choice the mount rewrites every other copy from the
chosen one — copied, re-stamped `SUPB`, re-checksummed and written back — unless both other copies are valid with the
same +0x68, or the device is write-protected (26100.8115, read once). On the volume measured, the checkpoint activity
of that mount also advanced the checkpoint's virtual clock.

See [Redundancy](../concepts/redundancy.md) for the self-heal mechanism.

### Per-copy self-LCN

Each copy also stores its **own LCN** (a self-reference) in two places — in the page header at **SUPB+0x20** and again
at the start of the self-descriptor at **+0xD0** — set to that copy's physical location: `0x1E` on the primary, the
backup's own LCN on each backup. The three copies are therefore **not byte-identical** even though their payload is:
they differ only in the self-LCN (0x20 and 0xD0) and the digest (at descriptor+0x28). A tool rebuilding a corrupt copy
from a healthy sibling copies the payload, rewrites the self-LCN at **both** offsets to the target location, and
recomputes the self-checksum — reproducing the original block exactly.

See [Redundancy → Repairing a corrupt copy](../concepts/redundancy.md).

## Volume GUID

The Volume GUID at offset 0x50 is used to derive the **volume signature** found in every metadata page header at
offset 0x0C. The volume signature is computed as the XOR of the four 32-bit words of the GUID, or 1 when that XOR is
0 (`CalculateVolumeSignature`).

## Parsing notes

1. Read the page header (80 bytes) and verify signature is `"SUPB"`; verify the self-checksum, and fall back to the
   backups in the order above when the primary fails
2. Read the Volume GUID at 0x50 — compute volume signature for later validation
3. Read checkpoint refs offset at 0x70 and count at 0x74
4. Navigate to the offset and read the two checkpoint LCNs
5. Read both checkpoints and use the valid one with the higher clock at CHKP+0x60; on a tie, the first listed
   ([checkpoint selection](chkp.md#checkpoint-selection-and-fallback))

## Cross-references

- [VBR](vbr.md) — the VBR is at sector 0; the SUPB is at cluster 30 (fixed offset)
- [Checkpoint (CHKP)](chkp.md) — the two checkpoint LCNs point to alternating CHKP structures
- [Page Header](page_header.md) — the 80-byte common header shared by SUPB, CHKP, and MSB+ pages
- [Redundancy](../concepts/redundancy.md) — the three-copy fallback and self-heal model

## Evidence

The field layout, the three-copy scheme, and the backup positions at `total_clusters − 2` and `total_clusters − 3`
are measured on the disk across the corpus and corroborated in the driver.

`CmsVolume::ReadSuperBlock` computes the backup locations, reads the copies in the order LCN 0x1E, N−2, N−3 and keeps
the first that passes its tests. A later valid copy replaces it only when `ChooseSuperBlock` ranks it higher by +0x68
and the copy kept is not the primary, so a primary that passes is read whatever the backups hold and +0x68 orders
only the two backups (a tie keeps N−2). Read twice on 17134, 26100.8115, .9444, .9549 and Insider 29574, the primary
test in the disassembly of all five.

The self-checksum at SUPB+0xD0 was proven by recomputation to be cluster-size-dependent (CRC32-C/4B on 4K, CRC64/8B
on 64K, SHA-256/32B on SHA-256), verified at mount via `ValidateSuperBlock` → `ComputeOrVerifySelfChecksumBlock`,
with fallback to a backup and the post-choice rewrite of the other copies.

The counts behind the text: the generation at SUPB+0x68 reads 1, and the self-descriptor offset at +0x78 reads 0xD0,
on 372 of 372 copies of 124 volumes.

See [how this was verified](../methodology.md) for the method.

<!-- findings: FS_CHKP_005, FS_SUPB_001, FS_SUPB_002, FS_SUPB_003, FS_SUPB_004, FS_SUPB_005, FS_SUPB_007,
               FS_SUPB_RA_003, FS_UPGD_RA_001 -->
