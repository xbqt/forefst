# Test Baseline Images (25)

These **25 images** are a fixed baseline: together they cover the corpus's format versions, cluster sizes and
checksum types and the feature groups listed below, and a new tool or a regression run is to be checked against all
of them.

The release gate (`analysis/verification/verify.sh`) runs over its own list, `analysis/verification/corpus.lst`,
which holds 22 of these 25: `win10refs5g4k.raw`, `win11refs5g4k.raw` and `win11refsmini.raw` are not in it.

All paths relative to `analysis/rawdisk/disks/`.

**Objects** is the number of entries in the volume's Object Table, system and user objects together (read on all 25).

## Group A — Version Coverage (7 images)

| # | Image | Path | Version | Clusters | Checksum | Objects | Key feature |
|---|-------|------|---------|----------|----------|---------|-------------|
| 1 | win10refs5g4k.raw | step2/ | v3.4 | 4K | CRC64 | 45 | Baseline v3.4, 4K clusters |
| 2 | win10refs5g64k.raw | step2/ | v3.4 | 64K | CRC64 | 45 | Baseline v3.4, 64K clusters |
| 3 | win1121h2test.raw | step4/ | v3.7 | 4K | CRC64 | 121 | Three down-level children of OID 0x520 (the last format held with them) |
| 4 | win1122h2test.raw | step4/ | v3.9 | 4K | CRC64 | 148 | No down-level children of OID 0x520 (the first format held without them) |
| 5 | win1123h2test.raw | step4/ | v3.10 | 4K | CRC64 | 100 | OID 0x30 (heat engine table), format GUID |
| 6 | win11refs5g4k.raw | step2/ | v3.14 | 4K | CRC64 | 51 | Baseline v3.14, 4K clusters |
| 7 | win11refs5g64k.raw | step2/ | v3.14 | 64K | CRC64 | 51 | Baseline v3.14, 64K clusters |

## Group B — Checksum & Upgrade Variants (3 images)

| # | Image | Path | Version | Clusters | Checksum | Objects | Key feature |
|---|-------|------|---------|----------|----------|---------|-------------|
| 8 | win11refs2g_sha256checksums.raw | step2/ | v3.14 | 4K | SHA-256 | 52 | SHA-256 metadata checksums, 4K |
| 9 | win11refs2t64ksha256checksums.raw | step3/ | v3.14 | 64K | SHA-256 | 46 | SHA-256 + 64K (72-byte page refs, 224-byte CT rows) |
| 10 | win10to11refs4g.raw | step3/ | v3.14 | 4K | CRC64 | 51 | Upgraded from v3.4; VBR 0x2A stays 0x0000 (not read) |

## Group C — Feature-Specific (7 images)

| # | Image | Path | Version | Clusters | Checksum | Objects | Key feature |
|---|-------|------|---------|----------|----------|---------|-------------|
| 11 | wininsiderrefs8gtest2.raw | step4/ | v3.14 | 64K | SHA-256 | 132 | Insider build 29574 |
| 12 | win11refs2tintegrity.raw | step3/ | v3.14 | 4K | CRC64 | 113 | Integrity streams enabled |
| 13 | win11refs8gcompresslz4default.raw | step3/ | v3.14 | 4K | CRC64 | 51 | LZ4 compression |
| 14 | win11refs8gcompresszstddefault.raw | step3/ | v3.14 | 4K | CRC64 | 80 | ZSTD compression |
| 15 | win11refs8gdedup.raw | step3/ | v3.14 | 4K | CRC64 | 116 | Data deduplication |
| 16 | win11refs2tsnapshots.raw | step3/ | v3.14 | 4K | CRC64 | 47 | Stream snapshots |
| 17 | win11refs4gattributes.raw | step4/ | v3.14 | 4K | CRC64 | 126 | EFS, EA, attribute variety (no USN) |

## Group D — USN Journal (3 images)

| # | Image | Path | Version | Clusters | Checksum | Objects | Key feature |
|---|-------|------|---------|----------|----------|---------|-------------|
| 18 | win11refs4gattributestest2.raw | step4continuing/ | v3.14 | 4K | CRC64 | 400 | USN active + EFS + EA (richest attribute image) |
| 19 | win11refslasttests.raw | step5/ | v3.14 | 4K | CRC64 | 23 | USN active, small (fast USN testing) |
| 20 | win11refstestmftecmd.raw | step5/ | v3.14 | 4K | CRC64 | 250 | USN active, medium size |

## Group E — Interesting (2 images)

| # | Image | Path | Version | Clusters | Checksum | Objects | Key feature |
|---|-------|------|---------|----------|----------|---------|-------------|
| 21 | win11refs2tmillionsofactions.raw | step3/ | v3.14 | 4K | CRC64 | 200 | Long workload, its script not kept: 187 directories, 1,935 files; both checkpoint copies at clock 662 (a natural tie) |
| 22 | win11refs2tspecials.raw | step3/ | v3.14 | 4K | CRC64 | 230 | 344 reparse points (symlinks, junctions) |

## Group F — Minimal Baselines (3 images)

| # | Image | Path | Version | Clusters | Checksum | Objects | Key feature |
|---|-------|------|---------|----------|----------|---------|-------------|
| 23 | win10refsmini.raw | step1/ | v3.4 | 4K | CRC64 | 17 | Minimal v3.4 (fast sanity check) |
| 24 | win11refsmini.raw | step5/ | v3.14 | 4K | CRC64 | 24 | Minimal v3.14 (fast sanity check) |
| 25 | win11refs8gtest4timestamps.raw | step4continuing/ | v3.14 | 4K | CRC64 | 244 | Timestamp behavior testing |

## Coverage Matrix

| Dimension | Images covering it |
|-----------|-------------------|
| v3.4 | 1, 2, 23 |
| v3.7 | 3 |
| v3.9 | 4 |
| v3.10 | 5 |
| v3.14 | 6-22, 24-25 |
| 4K clusters | 1, 3-6, 8, 10, 12-25 |
| 64K clusters | 2, 7, 9, 11 |
| CRC64 checksum | 1-7, 10, 12-25 |
| SHA-256 checksum | 8, 9, 11 |
| VBR 0x2A = 0 (not read; the volume uses CRC64) | 1-4, 10, 23 |
| Upgraded | 10 |
| Insider build | 11 |
| USN Journal | 18, 19, 20 |
| Integrity streams | 12 |
| LZ4 compression | 13 |
| ZSTD compression | 14 |
| Deduplication | 15 |
| Snapshots | 16 |
| EFS encryption | 17, 18 |
| Extended attributes | 17, 18 |
| Reparse-heavy | 22 |
| Stress (high activity) | 21 |

## Usage

Regression test script template:
```bash
DISK_BASE="analysis/rawdisk/disks"
IMAGES=(
 "$DISK_BASE/step2/win10refs5g4k.raw"
 "$DISK_BASE/step2/win10refs5g64k.raw"
 "$DISK_BASE/step4/win1121h2test.raw"
 "$DISK_BASE/step4/win1122h2test.raw"
 "$DISK_BASE/step4/win1123h2test.raw"
 "$DISK_BASE/step2/win11refs5g4k.raw"
 "$DISK_BASE/step2/win11refs5g64k.raw"
 "$DISK_BASE/step2/win11refs2g_sha256checksums.raw"
 "$DISK_BASE/step3/win11refs2t64ksha256checksums.raw"
 "$DISK_BASE/step3/win10to11refs4g.raw"
 "$DISK_BASE/step4/wininsiderrefs8gtest2.raw"
 "$DISK_BASE/step3/win11refs2tintegrity.raw"
 "$DISK_BASE/step3/win11refs8gcompresslz4default.raw"
 "$DISK_BASE/step3/win11refs8gcompresszstddefault.raw"
 "$DISK_BASE/step3/win11refs8gdedup.raw"
 "$DISK_BASE/step3/win11refs2tsnapshots.raw"
 "$DISK_BASE/step4/win11refs4gattributes.raw"
 "$DISK_BASE/step4continuing/win11refs4gattributestest2.raw"
 "$DISK_BASE/step5/win11refslasttests.raw"
 "$DISK_BASE/step5/win11refstestmftecmd.raw"
 "$DISK_BASE/step3/win11refs2tmillionsofactions.raw"
 "$DISK_BASE/step3/win11refs2tspecials.raw"
 "$DISK_BASE/step1/win10refsmini.raw"
 "$DISK_BASE/step5/win11refsmini.raw"
 "$DISK_BASE/step4continuing/win11refs8gtest4timestamps.raw"
)
```
