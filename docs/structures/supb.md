# Superblock (SUPB)

The Superblock is the fixed-location volume anchor that points to the two alternating checkpoints. It always resides at cluster 30 (LCN 0x1E), occupying a single cluster.

## Field layout

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 80 | Page header | Common metadata page header (see [Page Header](page_header.md)) with signature `"SUPB"` |
| 0x50 | 16 | Volume GUID | Unique per-volume identifier |
| 0x60 | 8 | Reserved | Always zero |
| 0x68 | 8 | Generation / virtual clock (u64) | The recency selector. `CmsVolume::ChooseSuperBlock` picks the copy with the HIGHEST +0x68. It is bumped on each SUPB rewrite (`MoveSuperBlock`) and reads 1 on a volume that has never had divergent copies (single mount state) — it is NOT a constant "version" |
| 0x70 | 4 | Checkpoint refs offset (u32) | Byte offset to checkpoint LCN list; typically 0xC0 |
| 0x74 | 4 | Checkpoint refs count (u32) | Always 2 |
| 0x78 | 4 | Self-descriptor offset (u32) | Offset to the SUPB self-descriptor |
| 0x7C | 4 | Self-descriptor length (u32) | 0x68 (v3.4), 0x30 (v3.14 CRC64), 0x48 (SHA-256) |
| 0xC0 | 8 | Checkpoint LCN 1 (u64) | At offset specified by +0x70 |
| 0xC8 | 8 | Checkpoint LCN 2 (u64) | Second checkpoint location |

## Location and copies

There are three SUPB copies on every volume:

- **Primary**: Cluster 30 (LCN 0x1E)
- **Backup 1**: `VolSize − 2` (i.e. `total_clusters − 2`)
- **Backup 2**: `VolSize − 3` (i.e. `total_clusters − 3`)

The backup locations are computed from the volume size by `CmsVolume::ReadSuperBlock`. The primary at LCN 0x1E is **not** privileged: the authoritative copy is whichever passes self-checksum validation and has the highest virtual clock (+0x68), so a corrupt primary silently falls back to a backup.

## Self-descriptor

The self-descriptor length varies by checksum configuration:

| Configuration | Self-descriptor length |
|---------------|----------------------|
| v3.4 (None) | 0x68 (104 bytes) |
| v3.14 CRC64 | 0x30 (48 bytes) |
| SHA-256 | 0x48 (72 bytes) |

Each SUPB copy carries a **cluster-size-dependent self-checksum** — a `LcnWithChecksum` self-descriptor at SUPB+0xD0, with the cktype byte at descriptor+0x22, the data-offset byte at descriptor+0x23 (= 0x08), the length at descriptor+0x24, and the digest at descriptor+0x28. The checksum is computed over one cluster with the descriptor zeroed. The algorithm is named by the cktype byte: **CRC32-C / 4 bytes on 4K-cluster** volumes (cktype 1), **CRC64 / 8 bytes on 64K-cluster** volumes (cktype 2), and **SHA-256 / 32 bytes on SHA-256** volumes (cktype 4).

The SUPB sits outside the page-reference Merkle tree — no parent structure stores a checksum of it — but it is **not unchecked**: the self-checksum IS verified at mount (`ValidateSuperBlock` → `ComputeOrVerifySelfChecksumBlock`). A copy that fails its self-checksum is dropped and self-healed from a valid copy: the winning copy is copied over the stale ones, re-stamped `SUPB`, re-checksummed, and written back, and the surrounding checkpoint machinery advances the virtual clock. See [Redundancy](../concepts/redundancy.md) for the self-heal mechanism.

## Volume GUID

The Volume GUID at offset 0x50 is used to derive the **volume signature** found in every metadata page header at offset 0x0C. The volume signature is computed as the XOR of the four 32-bit words of the GUID.

## Parsing notes

1. Read the page header (80 bytes) and verify signature is `"SUPB"`
2. Read the Volume GUID at 0x50 — compute volume signature for later validation
3. Read checkpoint refs offset at 0x70 and count at 0x74
4. Navigate to the offset and read the two checkpoint LCNs
5. Follow the LCN with the higher virtual clock value to reach the current checkpoint

## Cross-references

- [VBR](vbr.md) — the VBR is at sector 0; the SUPB is at cluster 30 (fixed offset)
- [Checkpoint (CHKP)](chkp.md) — the two checkpoint LCNs point to alternating CHKP structures
- [Page Header](page_header.md) — the 80-byte common header shared by SUPB, CHKP, and MSB+ pages
- [Redundancy](../concepts/redundancy.md) — the three-copy fallback and self-heal model

## Evidence

The field layout, the three-copy scheme, and the backup positions at `total_clusters − 2` and `total_clusters − 3` are raw-disk verified across the corpus (RD) and corroborated in the driver (E2): `CmsVolume::ReadSuperBlock` computes the backup locations and `CmsVolume::ChooseSuperBlock` selects the authoritative copy by highest virtual clock. The +0x68 field is a recency selector (generation / virtual clock), not a constant version value. The self-checksum at SUPB+0xD0 was proven by recomputation to be cluster-size-dependent (CRC32-C/4B on 4K, CRC64/8B on 64K, SHA-256/32B on SHA-256), verified at mount via `ValidateSuperBlock` → `ComputeOrVerifySelfChecksumBlock`, with fallback-to-backup and self-heal on mismatch. Findings: **FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003**. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
