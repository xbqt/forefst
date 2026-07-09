# Disk Image Corpus Description

## Summary

The corpus contains 118 raw disk images spanning ReFS versions 3.4 through 3.14 (Insider). Of these, 112 are valid parseable ReFS images. The remaining 6 are non-parseable by design (negative tests and corruption tests).

All tools achieve 100% pass rate on the 112 valid images (2912/2912 tests in the final v9 suite).

## Corpus Summary Table

| ReFS Version | OS | Cluster Size | Checksum (Meta) | Features Tested | Image Count |
|---|---|---|---|---|---|
| 3.4 | Win10 17134 | 4K | None | Baseline, sizes 2G-110G, integrity streams | 9 |
| 3.4 | Win10 17134 | 64K | None | 64K cluster addressing | 1 |
| 3.4 | Win10 17134 | 4K | None | Specials (symlinks, ADS, hardlinks) | 1 |
| 3.4 -> 3.14 | Win10 -> Win11 | 4K | None -> CRC64 | Cross-version upgrade (3 snapshots) | 3 |
| 3.7 | Win11 21H2 | 4K | None | Oldest Win11 format | 1 |
| 3.9 | Win11 22H2 | 4K | None | Intermediate version | 1 |
| 3.9 -> 3.14 | Win11 22H2 -> Insider | 4K | CRC64 | Upgraded by Insider | 1 |
| 3.10 | Win11 23H2 | 4K | CRC64 (declared) | Transition version | 1 |
| 3.14 | Win11 24H2 | 4K | CRC64 | Standard Win11, sizes 2G-110G | 20 |
| 3.14 | Win11 24H2 | 64K | CRC64 | 64K clusters (5G, 15T) | 2 |
| 3.14 | Win11 24H2 | 4K | SHA256 | SHA256 metadata checksums | 2 |
| 3.14 | Win11 24H2 | 64K | SHA256 | 64K + SHA256 combined | 1 |
| 3.14 | Win11 24H2 | 4K | CRC64 | Compression (LZ4, ZSTD, multi-stage) | 6 |
| 3.14 | Win11 24H2 | 4K | CRC64 | Dedup | 1 |
| 3.14 | Win11 24H2 | 4K | CRC64 | Snapshots, integrity, specials | 4 |
| 3.14 | Win11 24H2 | 4K | CRC64 | Massive file count (430K+ files) | 2 |
| 3.14 | Win11 24H2 | 4K | CRC64 | Large volumes (15T 4K) | 1 |
| 3.14 | Win11 24H2 | 4K | CRC64 | Attributes: EFS, WSL, reparse, timestamps | 4 |
| 3.14 | Win11 24H2 | 4K | CRC64 | Salvage before/after | 2 |
| 3.14 | Win11 24H2 | 4K | CRC64 | Corruption/checksum tests | 4 |
| 3.14 | Win11 24H2 | 4K | CRC64 | VBR modification tests | 15 |
| 3.14 | Insider 29574 | 4K | CRC64 | Insider-specific features, boot disk | 3 |
| 3.14 | Insider 29574 | 64K | SHA256 | Insider + 64K + SHA256 | 1 |
| N/A | Win11 24H2 | N/A | N/A | BitLocker (negative test) | 1 |
| NTFS | Win11 24H2 | N/A | N/A | NTFS (negative test) | 1 |
| **Total** | | | | | **~118** |

Note: Some counts overlap due to multi-snapshot images (e.g., the millionsofactions before/after salvage pair, the cross-version 3-snapshot set, and the 5-stage compression set).

## Non-Parseable Images (6)

| Image | Reason | Expected Behavior |
|---|---|---|
| win11refsbitlocked.raw | BitLocker full-volume encryption | VBR detection fails: "-FVE-FS-" signature |
| win11ntfs.raw | NTFS filesystem | VBR detection fails: "NTFS" signature |
| win11refs8gwithoutchecksums.raw | Never formatted (creation error) | Empty/blank image |
| win11refs2tmillionsofactions.raw | Volume became unmountable after dirty disconnect | Parseable by tools but unmountable by Windows |
| win10refsmini_testchecksum_corrupt.raw | Deliberately corrupted SUPB bytes | Parses normally (corruption is cosmetic) |
| win11refsmini_testchecksum_corrupt.raw | Deliberately corrupted SUPB bytes | Parses normally (corruption is cosmetic) |

Note: The corruption test images actually parse correctly (tools read them without error). The truly non-parseable images are the BitLocker, NTFS, and blank images (3 total that fail at VBR validation). The unmountable millionsofactions also parses correctly with tools despite being unmountable by Windows.

Effective non-parseable count for tool testing: 3 (BitLocker + NTFS + blank).

## Testing Phases

### Phase 1: Baseline (Step 1)
- 2 images (1 Win10, 1 Win11), both 2 GB, 4K clusters
- Purpose: Initial structural discovery, manual byte-level verification
- Result: 22/22 PASS

### Phase 2: Validation (Step 2)
- 18 images (6 Win10, 12 Win11)
- Sizes: 2 GB to 110 GB
- Configurations: 4K/64K clusters, None/CRC64/SHA256 checksums, integrity on/off, heat/trim options
- Purpose: Validate position-independent parsing across diverse configurations
- Result: 198/198 PASS (after fixing 4 bugs)

### Phase 3: Stress Testing (Steps 3 + 3b + 3c)
- 26 images total
- Sizes: up to 15 TB (245,759 containers)
- Configurations: compression (LZ4/ZSTD), dedup, snapshots, 1M+ actions, cross-version mounts
- Purpose: Extreme scale, edge cases, negative testing
- Result: All valid tests PASS, no new bugs

### Phase 4: Targeted Analysis (Step 4)
- 18+ images including version analysis (21H2/22H2/23H2/Insider), attribute testing, corruption tests
- Purpose: Deep field-by-field analysis, version evolution, metadata validation behavior
- Result: All valid tests PASS

### Phase 5: VBR Modification and Forensic Testing (Step 4 continued)
- 15 VBR modification test images + 4 timestamp/attribute images
- Purpose: Test Windows driver response to individual field modifications, timestamp behavior
- Result: Complete field validation matrix documented

## Key Corpus Statistics

| Metric | Value |
|---|---|
| Total images | ~118 |
| Valid parseable ReFS images | 112 |
| Unique ReFS versions | 5 (3.4, 3.7, 3.9, 3.10, 3.14) |
| Cluster sizes tested | 2 (4K, 64K) |
| Checksum types tested | 4 (None, CRC32, CRC64, SHA256) |
| Volume sizes | 2 GB to 15 TB |
| Maximum containers in single image | 245,759 (15 TB) |
| Maximum files in single image | ~430,000+ (millionsofactionsv2) |
| Windows versions used | 6 (Win10 1803, Win11 21H2/22H2/23H2/24H2, Insider 29574) |
| Total tool tests (v9 final) | 2912 PASS on 112 valid images |
| Pass rate on valid images | 100% |
