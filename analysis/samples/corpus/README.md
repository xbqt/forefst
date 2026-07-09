# Evidence Corpus

Curated tool outputs from the analysis of 118 disk images (v3.4 through v3.14 + Insider build 29574) — 112 parseable ReFS volumes plus 6 non-parseable negative tests (BitLocker / NTFS / blank). Each file is a raw, unedited output from `refsanalysis.py` or `forefst.py` run against a real disk image. Together they provide reproducible evidence for the structural claims documented in [`docs/`](../../docs/).

The full corpus of 118 images produced 562 individual tool outputs across 9 categories. This directory contains 16 selected structural outputs that demonstrate the most significant findings, each captured at default verbosity and — where the subcommand supports it — with a fullest-verbosity companion (`.vv.txt` for `-vv` subcommands, `.v.txt` for `-v`-only ones), for 28 files in all.

For the full corpus description (all 118 images, testing phases, pass rates), see [corpus_description.md](corpus_description.md).

## Directory Structure

```
corpus/
├── README.md ← this file
├── corpus_description.md ← full 118-image corpus description
├── bootstrap/ ← complete VBR→SUPB→CHKP→roots chain
├── version_evolution/ ← how structures change across ReFS versions
├── cross_version_upgrade/ ← before/after a Win10→Win11 upgrade
├── checksum_variants/ ← CRC64 vs SHA256 structural differences
└── file_attributes/ ← per-file metadata parsing
```

## Evidence Files

### bootstrap/ — Complete Bootstrap Chain

These outputs show the full traversal from raw disk to file metadata: GPT → VBR → SUPB → CHKP → 13 global root tables → object table → schema table → parent-child table. This is the core structural claim of the research.

| File | Image | What it proves |
|------|-------|---------------|
| `fs_win10_v34_2g.txt` | win10refs2g.raw (v3.4, 2 GB, 4K clusters) | Complete bootstrap chain on v3.4: VBR checksum=None, CHKP flags=0x2, 104-byte page references, 45 objects, 13 root tables all using virtual LCNs with container table translation |
| `fs_win11_v314_2g.txt` | win11refsmini.raw (v3.14, 2 GB, 4K clusters) | Complete bootstrap chain on v3.14: VBR checksum=CRC64, CHKP flags=0x682, 48-byte page references with indirect root list, 24 objects, schema table with 29 entries (13 system + 16 attribute types) |

**Key observations visible in these outputs:**
- SUPB always at LCN 0x1E (offset 0x101E000 after partition start)
- Two checkpoint references in SUPB (dual-checkpoint CoW)
- Container Table (root 7) and Container Table dup (root 8) use real/physical LCNs (bootstrap roots)
- Small Allocator (root 12) also uses real LCNs
- All other roots use virtual LCNs requiring container table translation
- System OIDs: 0x7–0xD, 0x500–0x541, 0x600 (root directory)
- User OIDs start at 0x701

### version_evolution/ — Version-Dependent Structure Changes

| File | Images | What it proves |
|------|--------|---------------|
| `chkp_five_versions.txt` | 5 images: Win11 21H2 (v3.7), 22H2 (v3.9), 23H2 (v3.10), 22H2 upgraded by Insider (v3.14), Insider native (v3.14) | CHKP flag evolution across all observed versions. Shows the exact transition points for each flag bit |
| `boot_five_versions.txt` | Same 5 images | VBR version field changes: 3.7, 3.9, 3.10, 3.14. Format-time fields (0x2A checksum type, 0x2C volume flags) preserved even after upgrade |
| `schema_win10_v34.txt` | win10refs2g.raw (v3.4) | Schema table in v3.4: 27 entries (15 system + 12 attribute types) |
| `schema_win11_v314.txt` | win11refsmini.raw (v3.14) | Schema table in v3.14: 29 entries (13 system + 16 attribute types). Net change from v3.4 (27 = 15+12): legacy system schemas retired, new attribute schemas added (see version_evolution.md) |

**CHKP flag evolution visible in `chkp_five_versions.txt`:**

| Version | Flags | Ref size | Key changes |
|---------|-------|----------|-------------|
| 3.7 | 0x002 | 104 bytes | Baseline |
| 3.9 | 0x002 | 104 bytes | No structural change |
| 3.10 | 0x082 | 48 bytes | +0x080 (native Win11 format), page ref shrinks to 48 bytes |
| 3.14 (upgraded) | 0x2602 | 48 bytes | +0x200 (indirect root list), +0x400 (CRC64 metadata checksums) |
| 3.14 (native Insider) | 0x2682 | 72 bytes | +0x080 (native), ref size grows to 72 bytes (SHA256-capable) |

### cross_version_upgrade/ — Before/After Win10→Win11 Upgrade

A single ReFS volume formatted on Windows 10 (v3.4) then mounted on Windows 11 (v3.14). The before/after pair proves the upgrade behavior.

| File | Snapshot | What it proves |
|------|----------|---------------|
| `boot_before_upgrade.txt` | Before Win11 mount | VBR version=3.4, checksum type=None, volume flags=0x6, GUID field empty |
| `boot_after_upgrade.txt` | After Win11 mount | VBR version changes to 3.14, but **checksum type (0x2A) and volume flags (0x2C) are NOT modified** — format-time fields are frozen |
| `chkp_before_upgrade.txt` | Before Win11 mount | CHKP flags=0x2, ref size=104 bytes, indirect roots=false, 63 container entries |
| `chkp_after_upgrade.txt` | After Win11 mount | CHKP flags=0x602, ref size=48 bytes, indirect roots=true. Virtual clock jumps from 27 to 68 (41 transactions for the upgrade process) |

**Key finding:** The VBR version field at 0x28 is updated to 3.14, but the format-time fields at offsets 0x2A (checksum algorithm) and 0x2C (volume flags) are never modified during upgrade. This distinguishes upgraded volumes from natively formatted v3.14 volumes.

### checksum_variants/ — CRC64 vs SHA256 Structural Differences

| File | Image | What it proves |
|------|-------|---------------|
| `boot_crc64.txt` | win11refsmini.raw (CRC64, 4K) | VBR checksum type=CRC64 (0x0002) at offset 0x2A |
| `boot_sha256.txt` | win11refs2g_sha256checksums.raw (SHA256, 4K) | VBR checksum type=SHA256 (0x0004) at offset 0x2A |
| `chkp_crc64_4k.txt` | win11refsmini.raw | CHKP flags=0x682, page ref size=0x30 (48 bytes) |
| `chkp_sha256_4k.txt` | win11refs2g_sha256checksums.raw | CHKP flags=0x682, page ref size=0x48 (72 bytes). The 24-byte increase accommodates the 32-byte SHA-256 hash replacing the 8-byte CRC64 |

**Key finding:** The page reference format depends on both version AND checksum type: v3.4 uses 104 bytes (no checksum), v3.14+CRC64 uses 48 bytes, v3.14+SHA256 uses 72 bytes.

### file_attributes/ — Per-File Metadata Parsing

| File | Image | What it proves |
|------|-------|---------------|
| `attributes_win11_v314_baseline.txt` | win11refsmini.raw (v3.14, 20 files) | Baseline file attribute extraction: timestamps, attribute flags (DIRECTORY_INTERNAL=0x10000000), security IDs, USN values, resident file storage with byte counts |
| `attributes_win11_specials.txt` | win11refs2tspecials.raw (v3.14, 1550 entries) | Advanced features: hundreds of reparse points (symbolic links), alternate data streams, deep directory hierarchies. Demonstrates tool capability on volumes with symbolic links, ADS, and reparse metadata. (This volume carries **0 stream snapshots** — an earlier note of "13 snapshots" was alternate data streams misclassified; for genuine stream snapshots see the `win11refs2tsnapshots` sample image.) |

**Key finding visible in baseline:** The directory attribute flag in ReFS is bit 28 (0x10000000), not bit 4 (0x10) as in the Win32 `FILE_ATTRIBUTE_DIRECTORY` constant. This is an internal representation that differs from the user-visible flag.

## Disk Image Corpus

These outputs were produced from a corpus of 118 raw disk images spanning:
- **6 Windows versions**: Win10 1803, Win11 21H2/22H2/23H2/24H2, Insider 29574
- **5 ReFS versions**: 3.4, 3.7, 3.9, 3.10, 3.14
- **Volume sizes**: 2 GB to 15 TB
- **Cluster sizes**: 4K and 64K
- **Checksum algorithms**: None, CRC32, CRC64, SHA256
- **Features tested**: compression (LZ4/ZSTD), dedup, snapshots, integrity streams, EFS, reparse points, hard links, cross-version upgrades

All tools achieve **100% pass rate** on the 112 valid images (2912/2912 tests). See [corpus_description.md](corpus_description.md) for the complete corpus breakdown.

## Reproducibility

Each output can be reproduced by running the corresponding tool against the named disk image. The
subcommand follows the image path; add `-vv` (or `-v`) for the fullest-verbosity companion files.

```bash
# Full analysis (bootstrap chain)  -> the fs_*.txt files
python3 refsanalysis.py <image.raw> all

# Individual structures
python3 refsanalysis.py <image.raw> boot         # add -vv for boot_*.vv.txt
python3 refsanalysis.py <image.raw> supb
python3 refsanalysis.py <image.raw> chkp         # add -vv for chkp_*.vv.txt
python3 refsanalysis.py <image.raw> schema       # add -vv for schema_*.vv.txt
python3 refsanalysis.py <image.raw> objects
python3 refsanalysis.py <image.raw> attributes
```

The `*_five_versions.txt` files concatenate the `boot` / `chkp` output of the five version-evolution
images, one section per image under an `=== <image> ===` delimiter.

The disk images used here were generated using `Generate-FSActivity.ps1` on Windows 10/11 virtual machines with controlled configurations. See [`lab/`](../lab/) for methodology.
