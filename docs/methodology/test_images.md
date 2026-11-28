# Test images

Every release is checked on a fixed list of disk images: the release gate reads each of them with every
command and compares the outputs with recorded ones. This page lists those images and describes each one.
[Driver builds analysed](driver_builds.md) is its counterpart for the `refs.sys` builds read.

The figures are measured, not typed: `forefst summary` on each image (2026-11-27, forefst 1.14.1). The image names are the lab's,
under the lab's step folders; four of the images are published as samples, with every output (marked
**sample**).

A volume does not record the Windows build that formatted it: where that build was recorded when the volume
was made, [Driver builds analysed](driver_builds.md) names the volume.

## In short

| ReFS format | Volumes |
|---|---|
| 3.4 | 9 |
| 3.7 | 1 |
| 3.9 | 2 |
| 3.10 | 2 |
| 3.14 | 110 |

124 ReFS volumes; 5 other images (not ReFS, or not readable as ReFS), listed at the end.

## The volumes

| Image | Format | State | Cluster | Checksum | Volume size | Change journal |
|---|---|---|---|---|---|---|
| `step1/win10refsmini.raw` | 3.4 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step2/win10refs110g.raw` | 3.4 | formatted | 4 KiB | CRC64 | 109.9 GiB | Inactive |
| `step2/win10refs5g64k.raw` | 3.4 | formatted | 64 KiB | CRC64 | 4.9 GiB | Inactive |
| `step2/win11refs2g.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step2/win11refs2g_setintegritystreams0.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step2/win11refs2g_setintegritystreams1.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step2/win11refs2g_sha256checksums.raw` | 3.14 | formatted | 4 KiB | SHA-256 | 1.9 GiB | Inactive |
| `step2/win11refs2g_test.raw` | 3.14 | formatted | 4 KiB | SHA-256 | 1.9 GiB | Inactive |
| `step2/win11refs5g64k.raw` | 3.14 | formatted | 64 KiB | CRC64 | 4.9 GiB | Inactive |
| `step3/win10refs2tspecials.raw` | 3.4 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step3/win10refs8gsetintegristystreams1.raw` | 3.4 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3/win10to11refs4g.raw` | 3.14 | upgraded from before ReFS 3.10 (ReFS 3.4–3.9) | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step3/win10to11refs4g_afterwin11mount.raw` | 3.14 | upgraded from before ReFS 3.10 (ReFS 3.4–3.9) | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step3/win10to11refs4g_beforewin11mount.raw` | 3.4 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step3/win11refs15t.raw` | 3.14 | formatted | 4 KiB | CRC64 | 15.0 TiB | Inactive |
| `step3/win11refs15t64k.raw` | 3.14 | formatted | 64 KiB | CRC64 | 15.0 TiB | Inactive |
| `step3/win11refs2t64ksha256checksums.raw` | 3.14 | formatted | 64 KiB | SHA-256 | 2.0 TiB | Inactive |
| `step3/win11refs2tintegrity.raw` | 3.14 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step3/win11refs2tmillionsofactions.raw` | 3.14 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step3/win11refs2tsnapshots.raw` (**sample**) | 3.14 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step3/win11refs2tspecials.raw` (**sample**) | 3.14 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step3/win11refs8gcompresslz4default.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3/win11refs8gcompresslz4withparam.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3/win11refs8gcompresszstddefault.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3/win11refs8gcompresszstdwithparam.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3/win11refs8gdedup.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3b/win11refs2tmillionsofactions_aftersalvage.raw` | 3.14 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step3b/win11refs2tmillionsofactions_beforesalvage.raw` | 3.14 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step3b/win11refs2tmillionsofactionsv2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step3b/win11refs8gtestcompression.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3b/win11refs8gtestcompression_afterdedup.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3b/win11refs8gtestcompression_beforelz4enabled.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3b/win11refs8gtestcompression_lz4enabled.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3b/win11refs8gtestcompression_lz4enableddifferentparams.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3b/win11refs8gtestcompression_zstdenabled.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step3c/win11refs2tmillionsofactions_aftersalvage_fixboottest.raw` | 3.14 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step4/win10refsmini_testchecksum.raw` | 3.4 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4/win10refsmini_testchecksum_corrupt.raw` | 3.4 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4/win1121h2test.raw` | 3.7 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step4/win1122h2test.raw` | 3.9 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step4/win1122h2test_afteropenedwithinsider.raw` | 3.14 | upgraded from before ReFS 3.10 (ReFS 3.4–3.9) | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step4/win1122h2test_testchecksum.raw` | 3.9 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step4/win1123h2test.raw` | 3.10 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step4/win1123h2test_testchecksum.raw` | 3.10 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step4/win11refs4gattributes.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step4/win11refsmini_testchecksum.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4/win11refsmini_testchecksum_corrupt.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4/wininsiderrefs2t.raw` | 3.14 | formatted | 4 KiB | CRC64 | 2.0 TiB | Inactive |
| `step4/wininsiderrefs8gtest2.raw` (**sample**) | 3.14 | formatted | 64 KiB | SHA-256 | 7.9 GiB | Inactive |
| `step4/winsider.raw` | 3.14 | formatted | 4 KiB | CRC64 | 57.8 GiB | Active |
| `step4continuing/win11refs4gattributestest2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step4continuing/win11refs8gtest4timestamps.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingbootformattimeguid.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingversion.raw` | 3.14 | test fixture: its boot sector was edited to read 6.66 | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingversion_opened.raw` | 3.14 | test fixture: its boot sector was edited to read 6.66 | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingversion_opened_rechangedtopreviousversionandopened.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingversion_opened_rechangedtoversion312.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingversion_opened_rechangedtoversion312test2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingversion_opened_rechangedtoversion315.raw` | 3.14 | test fixture: its boot sector was edited to read 3.15 | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingvolumeflags.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingvolumeflags_opened.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_afterchangingvolumeflagstest2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_aftercorruption.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_aftercorruption_openedwith314.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_aftercorruption_openedwith34.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_beforechangingbootformattimeguid.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step4continuing/win11refsmini_beforecorruption.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_detached.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_detached_remounte.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_detached_remounte_detached.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile_filedeletedwithexplorer.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile_filedeletedwithexplorer_unmount.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Inactive |
| `step5/testchecksums/win11refslasttests.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step5/testchecksums/win11refslasttests_baseline.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step5/testchecksums/win11refslasttests_baseline_corrupted.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step5/testchecksums/win11refslasttests_baseline_corruptedtest2aftermounted.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step5/testchecksums/win11refslasttests_baseline_corruptedtest2beforemounted.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step5/win10refsmini.raw` | 3.4 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step5/win11refslasttests.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step5/win11refstestmftecmd.raw` (**sample**) | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step6/win11refs2gtargeted.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Active |
| `step6/win11refs2gtargeted_reformated.raw` | 3.14 | formatted | 4 KiB | CRC64 | 1.9 GiB | Inactive |
| `step6/win11refs8g.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Active |
| `step6/win11refs8gtestmove.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Active |
| `step6/win11refs8gtestmove_aftermove.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Active |
| `step6/win11refs8gtestmove_beforemove.raw` | 3.14 | formatted | 4 KiB | CRC64 | 7.9 GiB | Active |
| `step6/win11bidule.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step6/lab314_main.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step6/lab314_64k.raw` | 3.14 | formatted | 64 KiB | CRC64 | 3.9 GiB | Active |
| `step6/lab314_4kn.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step6/lab314_main_step2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step6/lab314_64k_step2.raw` | 3.14 | formatted | 64 KiB | CRC64 | 3.9 GiB | Active |
| `step6/lab314_4kn_step2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labA_image1.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labA_image2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labBeforeF.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labC.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labD.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labE.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labEnotdetached.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labFafterreboot.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labFbeforereboot.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labG_0.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labG_1.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/labG_2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/win11afterblindaudit.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/win11afterblindaudit_empty.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step7/winsiderv2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 57.8 GiB | Active |
| `step8/labL_1.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step8/labL_2.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step8/labL_3.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step8/labL_4.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step8/labL_5.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step8/labL_6.raw` | 3.14 | formatted | 4 KiB | CRC64 | 3.9 GiB | Active |
| `step8/labM_after_rebuilt.raw` | 3.14 | upgraded from before ReFS 3.10 (ReFS 3.4–3.9) | 4 KiB | CRC64 | 1.9 GiB | Active |

## What the volumes hold

The counts of `summary`'s directory walk: files by where their bytes are (inline in the record, or in
extents), files with more than one name, files with named streams, files with stream snapshots, and files
encrypted, with an integrity stream, or compressed.

| Image | Directories | Files | Inline | Extents | Hard-linked | Named streams | Snapshots | Encrypted | Integrity | Compressed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `step1/win10refsmini.raw` | 5 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step2/win10refs110g.raw` | 33 | 263 | 0 | 263 | 0 | 2 | 0 | 0 | 0 | 0 |
| `step2/win10refs5g64k.raw` | 33 | 263 | 0 | 263 | 0 | 2 | 0 | 0 | 0 | 0 |
| `step2/win11refs2g.raw` | 38 | 264 | 9 | 255 | 1 | 2 | 0 | 0 | 0 | 0 |
| `step2/win11refs2g_setintegritystreams0.raw` | 38 | 264 | 9 | 255 | 1 | 2 | 0 | 0 | 0 | 0 |
| `step2/win11refs2g_setintegritystreams1.raw` | 38 | 264 | 0 | 264 | 1 | 2 | 0 | 0 | 263 | 0 |
| `step2/win11refs2g_sha256checksums.raw` | 38 | 264 | 9 | 255 | 1 | 2 | 0 | 0 | 0 | 0 |
| `step2/win11refs2g_test.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step2/win11refs5g64k.raw` | 38 | 264 | 9 | 255 | 1 | 2 | 0 | 0 | 0 | 0 |
| `step3/win10refs2tspecials.raw` | 148 | 1,035 | 0 | 1,035 | 0 | 100 | 0 | 0 | 260 | 0 |
| `step3/win10refs8gsetintegristystreams1.raw` | 33 | 262 | 0 | 262 | 0 | 2 | 0 | 0 | 262 | 0 |
| `step3/win10to11refs4g.raw` | 38 | 265 | 3 | 262 | 0 | 2 | 0 | 0 | 0 | 0 |
| `step3/win10to11refs4g_afterwin11mount.raw` | 38 | 265 | 3 | 262 | 0 | 2 | 0 | 0 | 0 | 0 |
| `step3/win10to11refs4g_beforewin11mount.raw` | 33 | 262 | 0 | 262 | 0 | 2 | 0 | 0 | 0 | 0 |
| `step3/win11refs15t.raw` | 38 | 264 | 9 | 255 | 1 | 2 | 0 | 0 | 0 | 0 |
| `step3/win11refs15t64k.raw` | 38 | 264 | 9 | 255 | 1 | 2 | 0 | 0 | 0 | 0 |
| `step3/win11refs2t64ksha256checksums.raw` | 33 | 261 | 6 | 255 | 1 | 2 | 0 | 0 | 0 | 0 |
| `step3/win11refs2tintegrity.raw` | 97 | 779 | 6 | 773 | 3 | 6 | 0 | 0 | 517 | 0 |
| `step3/win11refs2tmillionsofactions.raw` (incomplete, below) | 187 | 1,935 | 32 | 1,903 | 17 | 19 | 0 | 0 | 0 | 0 |
| `step3/win11refs2tsnapshots.raw` | 34 | 269 | 9 | 257 | 1 | 3 | 5 | 0 | 0 | 0 |
| `step3/win11refs2tspecials.raw` | 217 | 980 | 364 | 616 | 180 | 123 | 0 | 0 | 0 | 0 |
| `step3/win11refs8gcompresslz4default.raw` | 38 | 264 | 8 | 256 | 1 | 2 | 0 | 0 | 0 | 0 |
| `step3/win11refs8gcompresslz4withparam.raw` | 33 | 262 | 6 | 256 | 1 | 2 | 0 | 0 | 0 | 0 |
| `step3/win11refs8gcompresszstddefault.raw` | 67 | 510 | 10 | 500 | 3 | 4 | 0 | 0 | 0 | 0 |
| `step3/win11refs8gcompresszstdwithparam.raw` | 66 | 522 | 11 | 511 | 2 | 4 | 0 | 0 | 0 | 0 |
| `step3/win11refs8gdedup.raw` | 103 | 777 | 17 | 760 | 3 | 5 | 0 | 0 | 0 | 0 |
| `step3b/win11refs2tmillionsofactions_aftersalvage.raw` (incomplete, below) | 187 | 1,935 | 32 | 1,903 | 17 | 19 | 0 | 0 | 0 | 0 |
| `step3b/win11refs2tmillionsofactions_beforesalvage.raw` (incomplete, below) | 187 | 1,935 | 32 | 1,903 | 17 | 19 | 0 | 0 | 0 | 0 |
| `step3b/win11refs2tmillionsofactionsv2.raw` | 496 | 334,025 | 331,207 | 2,818 | 27 | 28 | 0 | 0 | 0 | 0 |
| `step3b/win11refs8gtestcompression.raw` | 102 | 783 | 17 | 766 | 3 | 6 | 0 | 0 | 0 | 0 |
| `step3b/win11refs8gtestcompression_afterdedup.raw` | 102 | 783 | 17 | 766 | 3 | 6 | 0 | 0 | 0 | 0 |
| `step3b/win11refs8gtestcompression_beforelz4enabled.raw` | 97 | 779 | 14 | 765 | 3 | 6 | 0 | 0 | 0 | 0 |
| `step3b/win11refs8gtestcompression_lz4enabled.raw` | 100 | 780 | 15 | 765 | 3 | 6 | 0 | 0 | 0 | 0 |
| `step3b/win11refs8gtestcompression_lz4enableddifferentparams.raw` | 100 | 780 | 15 | 765 | 3 | 6 | 0 | 0 | 0 | 0 |
| `step3b/win11refs8gtestcompression_zstdenabled.raw` | 100 | 780 | 15 | 765 | 3 | 6 | 0 | 0 | 0 | 0 |
| `step3c/win11refs2tmillionsofactions_aftersalvage_fixboottest.raw` (incomplete, below) | 187 | 1,935 | 32 | 1,903 | 17 | 19 | 0 | 0 | 0 | 0 |
| `step4/win10refsmini_testchecksum.raw` | 5 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4/win10refsmini_testchecksum_corrupt.raw` | 5 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4/win1121h2test.raw` | 109 | 573 | 0 | 573 | 74 | 70 | 0 | 0 | 259 | 0 |
| `step4/win1122h2test.raw` | 136 | 903 | 0 | 903 | 84 | 99 | 0 | 0 | 259 | 0 |
| `step4/win1122h2test_afteropenedwithinsider.raw` | 208 | 1,261 | 151 | 1,110 | 169 | 168 | 0 | 0 | 259 | 0 |
| `step4/win1122h2test_testchecksum.raw` | 136 | 903 | 0 | 903 | 84 | 99 | 0 | 0 | 259 | 0 |
| `step4/win1123h2test.raw` | 87 | 356 | 0 | 356 | 96 | 68 | 0 | 0 | 0 | 0 |
| `step4/win1123h2test_testchecksum.raw` | 87 | 356 | 0 | 356 | 96 | 68 | 0 | 0 | 0 | 0 |
| `step4/win11refs4gattributes.raw` | 113 | 646 | 177 | 468 | 87 | 65 | 2 | 2 | 0 | 0 |
| `step4/win11refsmini_testchecksum.raw` | 11 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4/win11refsmini_testchecksum_corrupt.raw` | 14 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4/wininsiderrefs2t.raw` | 110 | 657 | 178 | 478 | 90 | 58 | 1 | 1 | 259 | 0 |
| `step4/wininsiderrefs8gtest2.raw` | 118 | 621 | 177 | 444 | 92 | 69 | 0 | 0 | 0 | 0 |
| `step4/winsider.raw` | 26,559 | 81,701 | 40,379 | 41,322 | 33,106 | 4 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refs4gattributestest2.raw` | 387 | 1,747 | 698 | 1,045 | 356 | 233 | 4 | 4 | 0 | 0 |
| `step4continuing/win11refs8gtest4timestamps.raw` | 231 | 981 | 358 | 623 | 172 | 143 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingbootformattimeguid.raw` | 14 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingversion.raw` | 11 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingversion_opened.raw` | 11 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingversion_opened_rechangedtopreviousversionandopened.raw` | 14 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingversion_opened_rechangedtoversion312.raw` | 14 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingversion_opened_rechangedtoversion312test2.raw` | 14 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingversion_opened_rechangedtoversion315.raw` | 11 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingvolumeflags.raw` | 11 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingvolumeflags_opened.raw` | 14 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_afterchangingvolumeflagstest2.raw` | 14 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_aftercorruption.raw` | 11 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_aftercorruption_openedwith314.raw` | 14 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_aftercorruption_openedwith34.raw` | 11 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_beforechangingbootformattimeguid.raw` | 11 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step4continuing/win11refsmini_beforecorruption.raw` | 11 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_detached.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_detached_remounte.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_detached_remounte_detached.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile_filedeletedwithexplorer.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal_cpgit_unmounted_remounted_encrypted_hotxtmodified_symlinkcreated_dirsymlinkcreated_hardlinkcreated_emptyfilecreated_newfile_filedeletedwithexplorer_unmount.raw` | 6 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/testchecksums/win11refslasttests.raw` | 10 | 12 | 10 | 2 | 1 | 1 | 1 | 1 | 0 | 0 |
| `step5/testchecksums/win11refslasttests_baseline.raw` | 10 | 12 | 10 | 2 | 1 | 1 | 1 | 1 | 0 | 0 |
| `step5/testchecksums/win11refslasttests_baseline_corrupted.raw` | 10 | 12 | 10 | 2 | 1 | 1 | 1 | 1 | 0 | 0 |
| `step5/testchecksums/win11refslasttests_baseline_corruptedtest2aftermounted.raw` | 10 | 12 | 10 | 2 | 1 | 1 | 1 | 1 | 0 | 0 |
| `step5/testchecksums/win11refslasttests_baseline_corruptedtest2beforemounted.raw` | 10 | 12 | 10 | 2 | 1 | 1 | 1 | 1 | 0 | 0 |
| `step5/win10refsmini.raw` | 5 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step5/win11refslasttests.raw` | 10 | 11 | 9 | 2 | 1 | 1 | 1 | 1 | 0 | 0 |
| `step5/win11refstestmftecmd.raw` | 237 | 1,225 | 214 | 1,011 | 168 | 150 | 0 | 0 | 340 | 0 |
| `step6/win11refs2gtargeted.raw` | 10 | 20 | 19 | 1 | 2 | 0 | 0 | 0 | 2 | 0 |
| `step6/win11refs2gtargeted_reformated.raw` | 5 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step6/win11refs8g.raw` | 68 | 531 | 229 | 302 | 6 | 162 | 9 | 5 | 0 | 0 |
| `step6/win11refs8gtestmove.raw` | 72 | 9,618 | 9,313 | 305 | 7 | 162 | 9 | 5 | 0 | 0 |
| `step6/win11refs8gtestmove_aftermove.raw` | 72 | 9,618 | 9,313 | 305 | 7 | 162 | 9 | 5 | 0 | 0 |
| `step6/win11refs8gtestmove_beforemove.raw` | 71 | 10,630 | 10,328 | 302 | 6 | 162 | 9 | 5 | 0 | 0 |
| `step6/win11bidule.raw` | 17 | 636 | 18 | 618 | 0 | 31 | 1 | 0 | 574 | 0 |
| `step6/lab314_main.raw` | 31 | 4,664 | 4,046 | 618 | 3 | 9 | 0 | 0 | 2 | 0 |
| `step6/lab314_64k.raw` | 23 | 636 | 26 | 610 | 1 | 7 | 0 | 0 | 0 | 0 |
| `step6/lab314_4kn.raw` | 23 | 636 | 26 | 610 | 1 | 7 | 0 | 0 | 0 | 0 |
| `step6/lab314_main_step2.raw` | 33 | 4,673 | 4,049 | 623 | 3 | 9 | 2 | 0 | 2 | 0 |
| `step6/lab314_64k_step2.raw` | 24 | 639 | 27 | 612 | 1 | 7 | 0 | 0 | 0 | 0 |
| `step6/lab314_4kn_step2.raw` | 24 | 639 | 27 | 612 | 1 | 7 | 0 | 0 | 0 | 0 |
| `step7/labA_image1.raw` | 11 | 23 | 5 | 18 | 1 | 0 | 0 | 0 | 0 | 0 |
| `step7/labA_image2.raw` | 11 | 24 | 5 | 19 | 1 | 0 | 0 | 0 | 0 | 0 |
| `step7/labBeforeF.raw` | 17 | 34 | 13 | 21 | 1 | 0 | 1 | 0 | 0 | 0 |
| `step7/labC.raw` | 17 | 34 | 13 | 21 | 1 | 0 | 1 | 0 | 0 | 0 |
| `step7/labD.raw` | 13 | 27 | 7 | 20 | 1 | 0 | 1 | 0 | 0 | 0 |
| `step7/labE.raw` | 6 | 12 | 4 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step7/labEnotdetached.raw` | 6 | 12 | 4 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step7/labFafterreboot.raw` | 83 | 12,514 | 12,493 | 21 | 1 | 0 | 1 | 0 | 0 | 0 |
| `step7/labFbeforereboot.raw` | 83 | 7,243 | 7,222 | 21 | 1 | 0 | 1 | 0 | 0 | 0 |
| `step7/labG_0.raw` | 88 | 12,530 | 12,493 | 37 | 1 | 0 | 1 | 0 | 0 | 0 |
| `step7/labG_1.raw` | 88 | 12,530 | 12,493 | 37 | 1 | 0 | 1 | 0 | 0 | 0 |
| `step7/labG_2.raw` | 88 | 12,530 | 12,493 | 37 | 1 | 0 | 1 | 0 | 0 | 0 |
| `step7/win11afterblindaudit.raw` | 96 | 12,557 | 12,502 | 55 | 1 | 10 | 1 | 0 | 4 | 0 |
| `step7/win11afterblindaudit_empty.raw` | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step7/winsiderv2.raw` | 53,192 | 172,205 | 81,766 | 90,439 | 66,653 | 1,508 | 0 | 0 | 0 | 0 |
| `step8/labL_1.raw` | 6 | 15 | 14 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| `step8/labL_2.raw` | 10 | 16 | 15 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| `step8/labL_3.raw` | 10 | 16 | 15 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| `step8/labL_4.raw` | 10 | 17 | 16 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| `step8/labL_5.raw` | 11 | 17 | 16 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| `step8/labL_6.raw` | 11 | 17 | 16 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| `step8/labM_after_rebuilt.raw` | 12 | 34 | 4 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |

On these volumes the walk could not read every metadata page, so their counts are lower bounds:

- `step3/win11refs2tmillionsofactions.raw`: 14 metadata pages not read (stored as holes in the image file).
- `step3b/win11refs2tmillionsofactions_aftersalvage.raw`: 14 metadata pages not read (stored as holes in the image file).
- `step3b/win11refs2tmillionsofactions_beforesalvage.raw`: 14 metadata pages not read (stored as holes in the image file).
- `step3c/win11refs2tmillionsofactions_aftersalvage_fixboottest.raw`: 14 metadata pages not read (stored as holes in the image file).

## The other images

Images on the list that hold no ReFS volume the tool reads: NTFS volumes kept for comparison, and
volumes it cannot read as they are (for example an encrypted one).

| Image | Why |
|---|---|
| `step3b/win11ntfs.raw` | not read as ReFS: no GPT partition table found (use --partition-start for raw partitions) |
| `step3c/win11ntfs.raw` | not read as ReFS: partition contains NTFS, not ReFS (signature: 'NTFS    ') |
| `step3c/win11refs4gbitlocked.raw` | not read as ReFS: partition is BitLocker-encrypted (signature: -FVE-FS-) |
| `step5/win11ntfstestmftecmd.raw` | not read as ReFS: partition contains NTFS, not ReFS (signature: 'NTFS    ') |
| `step8/labM_after.raw` | not read as ReFS: partition is BitLocker-encrypted (signature: -FVE-FS-) |
