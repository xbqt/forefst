# Disk Image Corpus Description

## Summary

The validation corpus is a list of 129 raw disk images: 124 ReFS volumes and 5 images that are not ReFS volumes
(negative controls). Once byte-identical copies are set aside, the 124 ReFS volumes are 97 distinct images. They
span the formats 3.4, 3.7, 3.9, 3.10 and 3.14, both cluster sizes (4 KiB and 64 KiB), both metadata checksums
(CRC64 and SHA-256) and image sizes from 2 GiB to 15 TiB. The figures below are measured from the images (the
project's image manifest, regenerated 2026-11-16).

The lab collection holds 35 further images that the list leaves out. Two of them are sample images in this
directory: `win11refsmini` (its content is byte-identical to `win11refsmini_testchecksum`,
`win11refsmini_beforecorruption` and `win11refsmini_beforechangingbootformattimeguid`, which are in the list) and
`win10refs2g`.

The tools are regression-tested against every image of the list.

## Corpus Summary Table

| ReFS Version | Written by | Cluster Size | Metadata Checksum | Image Count |
|---|---|---|---|---|
| 3.4 | Win10 1803 | 4K | CRC64 | 8 |
| 3.4 | Win10 1803 | 64K | CRC64 | 1 |
| 3.7 | Win11 21H2 | 4K | CRC64 | 1 |
| 3.9 | Win11 22H2 | 4K | CRC64 | 2 |
| 3.10 | Win11 23H2 | 4K | CRC64 | 2 |
| 3.14 | Win11 24H2 / Insider 29574 | 4K | CRC64 | 99 |
| 3.14 | Win11 24H2 | 4K | SHA-256 | 2 |
| 3.14 | Win11 24H2 | 64K | CRC64 | 4 |
| 3.14 | Win11 24H2 / Insider 29574 | 64K | SHA-256 | 2 |
| 3.14, version field edited (reads 6.66 or 3.15) | Win11 24H2, then a hand edit | 4K | CRC64 | 3 |
| not ReFS | — | — | — | 5 |
| **Total** | | | | **129** |

The 3.14 rows include the 3 upgraded volumes: `win10to11refs4g` and `win10to11refs4g_afterwin11mount` (formatted at
3.4 by Windows 10, upgraded by a Windows 11 mount) and `win1122h2test_afteropenedwithinsider` (formatted at 3.9,
upgraded by an Insider mount). The metadata checksum is CRC64 on every format, including the volumes whose boot-sector
checksum field (0x2A) reads 0x0 (formatted at 3.4, 3.7 or 3.9, upgraded from them, or rewritten by `refsutil fixboot`):
refs.sys does not read that field when the volume flags lack 0x40.

Several images are the same volume imaged at successive stages (before and after an upgrade, a salvage, a compression
setting, a corruption or a boot-sector edit, or after each action of a scripted sequence).

## Images That Are Not ReFS Volumes (5)

| Image | Content | Tool behaviour |
|---|---|---|
| `step3b/win11ntfs.raw` | Blank: every byte is zero | Refused (exit 1): no GPT partition table |
| `step3c/win11ntfs.raw` | NTFS | Refused (exit 1): the partition holds NTFS |
| `step3c/win11refs4gbitlocked.raw` | BitLocker-encrypted | Refused (exit 1): the partition is BitLocker-encrypted (`-FVE-FS-`) |
| `step5/win11ntfstestmftecmd.raw` | NTFS | Refused (exit 1): the partition holds NTFS |
| `step8/labM_after.raw` | BitLocker-encrypted | Refused (exit 1): the partition is BitLocker-encrypted (`-FVE-FS-`) |

Deliberately damaged ReFS volumes (corruption tests, boot-sector edits) are not in this table: they are ReFS volumes,
and the tools read them and report what they find.

## Acquisition Steps

The images are grouped by the lab step that produced them; each is named for its scenario.

| Step | Images | What they hold |
|---|---|---|
| step1 | 1 | Baseline v3.4 volume (`win10refsmini`) |
| step2 | 8 | Sizes 2 GiB to 110 GiB; 4K and 64K clusters; SHA-256 checksums; integrity streams on and off |
| step3 | 17 | 2 TiB and 15 TiB volumes; 64K + SHA-256; integrity streams; special files (`win10refs2tspecials`, `win11refs2tspecials`); stream snapshots; compression (LZ4, ZSTD); dedup; the 3.4 → 3.14 upgrade, before and after; a large workload (`win11refs2tmillionsofactions`) |
| step3b | 10 | The large-workload volume before and after salvage, and a second one; a compression sequence (before LZ4, LZ4, LZ4 with other parameters, ZSTD, after dedup); the blank image |
| step3c | 3 | NTFS and BitLocker controls; the salvaged volume after `refsutil fixboot` |
| step4 | 14 | The 3.7, 3.9 and 3.10 volumes; the 3.9 volume after an Insider mount; checksum tests (damaged copies and their controls); an attributes test; volumes made on Insider 29574 |
| step4continuing | 17 | Boot-sector edits on a 3.14 volume (version, volume flags, Extended GUID), before and after a mount; a corruption test opened by 3.14 and 3.4 drivers; attribute and timestamp tests |
| step5 | 23 | One volume imaged at successive stages of a scripted sequence of actions (encryption, a modification, symbolic links, a hard link, an empty file, a new file, an Explorer deletion, an unmount), and the same baseline across detach and remount; corruption tests; a 3.4 volume; an NTFS control; `win11refstestmftecmd` (active change journal) |
| step6 | 13 | Targeted tests, a reformatted volume, move tests, `win11bidule`; the lab volumes `lab314_main`, `lab314_64k` (64K clusters) and `lab314_4kn` (4 KiB sectors), two stages each |
| step7 | 15 | Lab volumes A–G (labF before and after a reboot), `winsiderv2`, and two post-audit volumes |
| step8 | 8 | LAB-L (six images of one volume across mounts) and LAB-M (a BitLocker-encrypted image and a rebuilt one) |

## Key Corpus Statistics

| Metric | Value |
|---|---|
| Images in the validation list | 129 |
| ReFS volumes | 124 (97 distinct) |
| Images that are not ReFS volumes | 5 (blank, NTFS, BitLocker) |
| ReFS versions | 5 (3.4, 3.7, 3.9, 3.10, 3.14), plus 3 volumes whose version field was edited |
| Upgraded volumes | 3 (to 3.14, from 3.4 and from 3.9) |
| Cluster sizes | 2 (4K: 117 volumes, 64K: 7) |
| Metadata checksums | CRC64 (120 volumes), SHA-256 (4) |
| Image sizes | 2 GiB to 15 TiB |
| Volumes with an active change journal | 42 |
| Volumes with EFS-encrypted files | 13 |
| Volumes with stream snapshots | 25 |
| Windows versions used | Win10 1803, Win11 21H2 / 22H2 / 23H2 / 24H2, Insider 29574 |
