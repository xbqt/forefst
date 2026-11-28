# Evidence Corpus

Curated structure-analysis outputs from eleven of the project's lab disk images (ReFS 3.4, 3.7, 3.9, 3.10 and 3.14,
including a volume formatted by Insider build 29574). Each file is the output of one `refsanalysis.py` command run
against a real disk image, regenerated with refsanalysis 1.14.0 (forefst 1.14.0) on 2026-11-20 by
[`gen_corpus_samples.sh`](#reproducibility). The generator adds one header line naming the command and the tool
version, and shows the image by its basename; the rest is the tool's output as printed. Every command exited 0.
Together they let you see the structures documented in [`docs/`](../../../docs/) as the tool reads them.

This directory holds 16 structural outputs in 28 files: `boot`, `chkp` and `schema` at default verbosity, each with
its `-vv` companion (`.vv.txt`), and `all` and `attributes` at default verbosity.

For the image corpus itself (what it holds, how it was built), see [corpus_description.md](corpus_description.md).

## Directory Structure

```
corpus/
├── README.md ← this file
├── corpus_description.md ← the lab image corpus
├── bootstrap/ ← complete VBR→SUPB→CHKP→roots chain
├── version_evolution/ ← how structures change across ReFS versions
├── cross_version_upgrade/ ← before/after a Win10→Win11 upgrade
├── checksum_variants/ ← CRC64 vs SHA-256 structural differences
└── file_attributes/ ← per-file metadata parsing
```

## Evidence Files

### bootstrap/ — Complete Bootstrap Chain

These outputs show the traversal from the partition to the namespace: VBR → SUPB → CHKP → 13 global root tables →
schema table → object table → parent-child table → directory tree. `all` runs nine structure tools in sequence
(summary, boot, supb, chkp, schema, objects, parentchild, containers, files).

| File | Command | What it shows |
|------|---------|---------------|
| `fs_win10_v34_2g.txt` | `refsanalysis win10refs2g.raw all` (v3.4, 2 GB, 4K clusters) | The chain on v3.4: checkpoint flags 0x2, 104-byte root references read directly (no offset list), 45 objects, 27 schema entries (15 system + 12 attribute types). The boot sector's checksum field (0x2A) is 0x0, which refs.sys does not read on this volume (its flags at 0x2C lack 0x40): the metadata checksum is CRC64 |
| `fs_win11_v314_2g.txt` | `refsanalysis win11refsmini.raw all` (v3.14, 2 GB, 4K clusters) | The chain on v3.14: boot-sector checksum CRC64 (0x2A = 0x2), checkpoint flags 0x682, 48-byte root references through an indirect offset list, 24 objects, 29 schema entries (13 system + 16 attribute types) |

**Key observations visible in these outputs:**
- The primary superblock (SUPB) is at LCN 0x1E — byte 0x101E000 of these images, whose partition starts at 0x1000000
- The superblock holds two checkpoint references; `supb` marks the copy in use (here the one with the higher
  virtual clock)
- Container Table (root 7), Container Table dup (root 8) and Small Allocator (root 12) use real (physical) LCNs: they
  are the bootstrap roots
- The other ten roots use virtual LCNs, translated through the Container Table
- System objects in the Object ID Table: 0x7–0xA and 0xD (upcase, logfile information, trash), 0x500, 0x501, 0x520,
  0x530, 0x540, 0x541, 0x600 (root directory), and on the v3.14 volume also 0x30 (the heat engine's table)
- User objects start at 0x701

### version_evolution/ — Version-Dependent Structure Changes

| File | Command | What it shows |
|------|---------|---------------|
| `chkp_five_versions.txt` | `refsanalysis <image> chkp` on 5 images: Win11 21H2 (v3.7), 22H2 (v3.9), 23H2 (v3.10), the 22H2 volume after an Insider mount (upgraded to v3.14), a volume formatted by the Insider build (v3.14) | Checkpoint flags and root-reference size per version (table below) |
| `boot_five_versions.txt` | `refsanalysis <image> boot` on the same 5 images | VBR version field: 3.7, 3.9, 3.10, 3.14, 3.14. The upgraded volume keeps its format-time fields: checksum field 0x2A = 0x0 and an all-zero Extended GUID (0x48), as on the 3.9 volume before the upgrade. The volume flags (0x2C) read 0x26 before and after the upgrade; they are not a format-time field — refs.sys writes them at run time (a writable mount sets 0x02) |
| `schema_win10_v34.txt` | `refsanalysis win10refs2g.raw schema` (v3.4) | Schema table in v3.4: 27 entries (15 system + 12 attribute types) |
| `schema_win11_v314.txt` | `refsanalysis win11refsmini.raw schema` (v3.14) | Schema table in v3.14: 29 entries (13 system + 16 object-table schemas). Net change from v3.4: four legacy system schemas (0xE050, 0xE070, 0xE0E0, 0xE0F0) and the two legacy object-table schemas (0x4, 0x6) are gone; two system schemas (0xE120, 0xE130) and six object-table schemas (0x1B0–0x200) are new (see [version_evolution.md](../../../docs/concepts/version_evolution.md)) |

**CHKP flag evolution visible in `chkp_five_versions.txt`:**

| Version | Flags | Ref size | Key changes |
|---------|-------|----------|-------------|
| 3.7 | 0x0002 | 104 bytes | Baseline |
| 3.9 | 0x0002 | 104 bytes | No change |
| 3.10 | 0x0082 | 48 bytes | +0x0080 (native-format marker); root references shrink to 48 bytes |
| 3.14 (upgraded from 3.9 by an Insider mount) | 0x2602 | 48 bytes | +0x0200 (indirect root list), +0x0400 (the record carries the rollback-protection fields, set on volumes of format 3.13 or later), +0x2000 (attestation HMAC, written by the Insider driver); no 0x0080, as on every upgraded volume |
| 3.14 (formatted by Insider) | 0x2682 | 72 bytes | 0x0080 + 0x0200 + 0x0400 + 0x2000. The 72-byte references come from this volume's SHA-256 metadata checksum (0x2A = 0x4), not from the Insider build |

### cross_version_upgrade/ — Before/After Win10→Win11 Upgrade

A single ReFS volume formatted on Windows 10 (v3.4) then mounted on Windows 11 (v3.14). The before/after pair shows
what the upgrade changes.

| File | Command (snapshot) | What it shows |
|------|--------------------|---------------|
| `boot_before_upgrade.txt` | `refsanalysis win10to11refs4g_beforewin11mount.raw boot` (before the Win11 mount) | VBR version 3.4, checksum field 0x2A = 0x0 (not read by refs.sys: the flags lack 0x40), volume flags 0x6, Extended GUID all zero |
| `boot_after_upgrade.txt` | `refsanalysis win10to11refs4g_afterwin11mount.raw boot` (after the Win11 mount) | VBR version 3.14; 0x2A still 0x0, the Extended GUID still all zero, the volume flags still 0x6 |
| `chkp_before_upgrade.txt` | `refsanalysis win10to11refs4g_beforewin11mount.raw chkp` | CHKP flags 0x2, root references 104 bytes read directly (no offset list), 63 container entries |
| `chkp_after_upgrade.txt` | `refsanalysis win10to11refs4g_afterwin11mount.raw chkp` | CHKP flags 0x602, root references 48 bytes through an indirect offset list, version 3.14 at 0x54 and none at 0x50 (the version echo). The virtual clock goes from 27 to 68: 41 checkpoints were committed between the two images (the clock counts checkpoints, not file operations or transactions) |

**Key finding:** The VBR version field at 0x28 is updated to 3.14, while the format-time fields are not: the
checksum field 0x2A keeps 0x0 and the Extended GUID at 0x48 stays all zero. The volume flags at 0x2C kept their value
(0x6) across this upgrade, but refs.sys writes them at run time, so their value is an observation, not a freeze. What
distinguishes this upgraded volume from a natively formatted v3.14 one: 0x2A = 0x0 and a zero Extended GUID in the
boot sector, flags 0x2C without 0x40 (0x6 here, 0x66 on a native 3.14 volume), and a checkpoint without the native
marker 0x0080 and without a version echo at 0x50.

### checksum_variants/ — CRC64 vs SHA-256 Structural Differences

| File | Command | What it shows |
|------|---------|---------------|
| `boot_crc64.txt` | `refsanalysis win11refsmini.raw boot` (CRC64, 4K) | VBR checksum field 0x2A = 0x2 (CRC64) |
| `boot_sha256.txt` | `refsanalysis win11refs2g_sha256checksums.raw boot` (SHA-256, 4K) | VBR checksum field 0x2A = 0x4 (SHA-256) |
| `chkp_crc64_4k.txt` | `refsanalysis win11refsmini.raw chkp` | CHKP flags 0x682, root reference size 0x30 (48 bytes) |
| `chkp_sha256_4k.txt` | `refsanalysis win11refs2g_sha256checksums.raw chkp` | CHKP flags 0x682, root reference size 0x48 (72 bytes). The 24-byte increase is the 32-byte SHA-256 digest in place of the 8-byte CRC64 one |

**Key finding:** The checkpoint's root-reference size depends on both the format and the checksum type: 104 bytes on
volumes formatted at 3.4, 3.7 or 3.9 (an 8-byte CRC64 digest followed by zero padding), 48 bytes on 3.10 and 3.14 with
CRC64 (an upgraded volume included), 72 bytes on 3.14 with SHA-256.

### file_attributes/ — Per-File Metadata Parsing

| File | Command | What it shows |
|------|---------|---------------|
| `attributes_win11_v314_baseline.txt` | `refsanalysis win11refsmini.raw attributes` (v3.14; 20 names: 11 directories, 9 files) | Baseline file attribute extraction: the four timestamps, attribute flags (`Directory_Internal` = 0x10000000), internal flags, security IDs, and storage — every file here holds its data inline, in its embedded record |
| `attributes_win11_specials.txt` | `refsanalysis win11refs2tspecials.raw attributes` (v3.14; 1,550 names: 217 directories, 1,333 file names for 980 files) | Special files: 344 files carrying the reparse-point attribute (symbolic links on this volume, 508 names), alternate data streams (an `ADS:` line per stream under each name), hard links (more names than files), paths up to nine levels deep, and storage both inline and in extents, in embedded or split records. The volume carries no stream snapshots; for those see the `win11refs2tsnapshots` image under [`../disks/`](../disks/) |

**Key finding visible in baseline:** Directories show the attribute bit 28 (0x10000000), not bit 4 (0x10, the Win32
`FILE_ATTRIBUTE_DIRECTORY` that Windows reports to programs). The tool prints the attribute word of the directory's
entry in its parent, which carries bit 28 on every directory of every format; the copy in the directory's own record
carries it only on volumes formatted at 3.4, 3.7 or 3.9 (and on some upgraded from 3.4), not on natively formatted
3.14 volumes such as this one.

## Disk Image Corpus

The images come from the project's lab corpus, whose validation list holds 129 images: 124 ReFS volumes (97
distinct once byte-identical copies are set aside) and 5 non-ReFS negative controls. Two of the eleven images used
here, `win11refsmini` and `win10refs2g`, are lab images outside that list (see
[corpus_description.md](corpus_description.md)). The list spans:
- **Windows versions**: Win10 1803, Win11 21H2 / 22H2 / 23H2 / 24H2, Insider build 29574
- **ReFS versions**: 3.4, 3.7, 3.9, 3.10, 3.14 (plus three copies of a 3.14 volume whose version field was edited)
- **Image sizes**: 2 GiB to 15 TiB
- **Cluster sizes**: 4K and 64K
- **Metadata checksums**: CRC64 on every format; SHA-256 on four 3.14 volumes formatted with it. File data is
  checksummed only with integrity streams on (CRC32-C on 4K-cluster volumes)
- **Scenarios**: compression (LZ4/ZSTD), dedup, snapshots, integrity streams, EFS, WSL metadata, reparse points,
  hard links, alternate data streams, the change journal, cross-version upgrades, corruption and boot-sector edits

The tools are regression-tested against the whole validation list. See [corpus_description.md](corpus_description.md)
for the breakdown.

## Reproducibility

Each output can be reproduced by running the command in its header line (and in the tables above) against the named
disk image; the subcommand follows the image path.

```bash
python3 refsanalysis.py <image.raw> all            # the fs_*.txt files
python3 refsanalysis.py <image.raw> boot           # add -vv for boot_*.vv.txt
python3 refsanalysis.py <image.raw> chkp           # add -vv for chkp_*.vv.txt
python3 refsanalysis.py <image.raw> schema         # add -vv for schema_*.vv.txt
python3 refsanalysis.py <image.raw> attributes     # the attributes_*.txt files
```

The `*_five_versions.txt` files concatenate the `boot` / `chkp` output of the five version-evolution images, one
section per image under an `=== <image> ===` delimiter followed by that section's command.

In this project's workspace, `analysis/tools/analysis_scripts/gen_corpus_samples.sh` regenerates all 28 files with
the development tools, one command per file; it fails on a usage error, an error line, an empty output or a
workspace path left in an output, and `--check` compares a fresh run with these files.

The disk images were formatted inside Windows 10, Windows 11 and Insider virtual machines and populated by hand or
with the scripted workload `Generate-FSActivity.ps1`. See [`lab/`](../../lab/) for the methodology.
