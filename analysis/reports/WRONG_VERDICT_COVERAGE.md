# Wrong-verdict K-ids: coverage, one row each (plan v12 section 8, item 2)

**Generated** by `analysis/verification/gen_wrong_verdict_coverage.py` - do not hand-edit; a
hand-kept list of 51 ids drifts the moment a fix lands.

51 of the audit's 215 findings are `wrong_verdict`. Item 2 requires every one with a **buildable**
case GREEN in the damaged battery, and the rest **named**.

| K-id | where it is verified | title |
|---|---|---|
| K010 | **battery** (B2_integrity_data_hole) | A hole in an integrity-stream cluster is described as possibly the file's own zeros / undeterminab |
| K011 | **battery** (B2_integrity_data_hole) | integrity reads only metadata pages yet prints unscoped 'no tampering/corruption', PASS, clean=tru |
| K014 | a test names it: test_1132_red_a_coverage.py | summary/dataruns/refsanalysis containers report a damaged or relocated Container Table as normal c |
| K017 | **battery** (E1_K017_metadata_refuse_holes) | export metadata writes usn_J.bin without holes_mark: stderr reports hole-sourced $J bytes but hole |
| K018 | a test names it: test_1132_e1_kids.py | Undeterminable hole coverage is treated as 'no holes' on every content path except extract's main  |
| K019 | **battery** (A4_oid_root_punch) | The export metadata bundle does not reflect metadata damage (zero-filled vbr_backup.bin with no ho |
| K020 | a test names it: test_1132_e1_kids.py | export metadata MLog branch swallows exceptions: bundle lacks MLog artifacts with no manifest warn |
| K024 | a test names it: test_1132_red_b2_carve.py | deleted/export deleted grade rows 'metadata + carve' BEST-EFFORT whose carve produces no file: ver |
| K028 | a test names it: test_1132_red_a_coverage.py | deleted --full claims it scanned 100% of the volume after silently skipping a 16 MiB block on a re |
| K029 | **battery** (A1_chkp_flip_newest) | integrity warns on a checkpoint only when role=='secondary' and never on SUPB copies (self_lcn_ok  |
| K030 | **battery** (A1_chkp_flip_newest, A6_supb_backup_zero, A7_object_page_flip) | integrity rc/clean are computed from FAIL + page-checksum mismatches only: page-reference mismatch |
| K031 | **oracle** probe GREEN on this build | integrity PASS/clean=true/rc 0 with incomplete checksum coverage (page cap reached or unreadable p |
| K032 | **battery** (A6_supb_backup_zero) | SUPB backups are located by signature scan of the last 64 clusters and warned only when fewer than |
| K034 | **battery** (E13_A4K_supb_flip) | summary takes Volume GUID from the unverified primary SUPB and prints the constant 'payload is ide |
| K035 | **battery** (A1_chkp_flip_newest) | refsanalysis boot/supb/chkp --verify tables have no self-checksum or clock rows ('valid' = signatu |
| K036 | **battery** (A1_chkp_flip_newest, A2_chkp_zero_newest) | Checkpoint selection is signature-only and +0x10-ordered with no self-checksum check and no fallba |
| K037 | corrected in the reference layer: errata.md | The active checkpoint is picked by header +0x10 at 10 sites with 4 tie rules, while the driver and |
| K038 | corrected in the reference layer: errata.md | Tied checkpoint clocks: forefst marks both copies PRIMARY (secondary warning cannot fire) and prin |
| K042 | a test names it: test_1132_e1_kids.py | Checkpoint clock-consistency damage (allocator clock above virtual clock; inverted across the pair |
| K043 | **battery** (A3_oid_root_zero, A4_oid_root_punch) | _walk returns [] silently for a referenced page that is not a B+ node and the bootstrap never chec |
| K044 | **battery** (A3_oid_root_zero) | summary Global Root Tables: exception handlers turn an unreadable root page into '0 rows' with no  |
| K045 | **battery** (E13_A4K_dirpage_flip, E13_B64K_dirpage_flip, E13_C4KN_dirpage_flip, E13_D34_dirpage_flip) | Directory-page damage silently removes names from files/summary/timeline, gives surviving split ha |
| K046 | **battery** (E13_I34_extidx_flip, E13_I34_64K_extidx_flip) | integrity (including --fullchecksums) follows only inner-node child refs, never page references in |
| K047 | **battery** (E1_K047_fsmeta_page_flip) | USN presence is computed in three places and a read error of the FS-metadata directory becomes 'jo |
| K048 | **battery** (E1_K048_security_page_flip) | security --audit prints 'VERDICT: CLEAN - 0/0' rc 0 when the SD table root page is damaged; files  |
| K050 | **battery** (E1_K050_vbr_version_6666) | bootedit repair --dry-run diagnoses only primary-VBR fixboot fields (no backup VBR/SUPB/CHKP read, |
| K051 | corrected in the reference layer: reference_table.csv | volume_state is 'NATIVE v' + VBR version and is never compared with CHKP or $VOLUME_INFORMATION; a |
| K055 | corrected in the reference layer: errata.md | MLog redo iteration (duplicated in two functions) uses remaining = total_size - first_off and drop |
| K056 | corrected in the reference layer: errata.md | MLog parser reads only the first redo block of each log record (no merged-block iteration), so 86% |
| K058 | **battery** (B5_mlog_newest_zero) | Zeroing the newest 1024 MLog records reads as a healthy shorter log ('Failed: 0'); checkpoint/cont |
| K059 | a test names it: test_1132_e1_kids.py | mlog --parse/--csv and timeline date volume-information updates at the volume format time instead  |
| K062 | **oracle** probe GREEN on this build | Undamaged 4Kn volume: integrity WARNs 'backup boot sector missing' / 'fewer than 2 SUPB copies', s |
| K064 | a test names it: test_1132_red_b_items.py | Image length used as volume length: summary capacity counts the image tail (48 MB 'beyond the last |
| K067 | **battery** (B3_journal_tail_zero) | parse_usn_records counts zero words inside the live range as slack and accepts any aligned record  |
| K068 | **battery** (B3_journal_tail_zero) | Head/tail-truncated or fully zeroed $J is reported as a normal shorter journal by usn --info ('jou |
| K069 | **battery** (E1_K069_journal_zeroed) | On an active journal whose records are all zeroed, timeline states 'USN journal inactive' while su |
| K070 | a test names it: test_1132_e1_kids.py | $J real stream size/VDL at MI value +0x38/+0x40 are never read; code and docs wrongly say $J has n |
| K075 | a test names it: test_1132_e1_kids.py | Timestomp USN corroboration is keyed by file NAME with a live-name uniqueness gate (private walker |
| K076 | **battery** (E1_K076_journal_coverage) | Journal coverage is never checked: a truncated journal or one created after the files were written |
| K077 | a test names it: test_1132_e1_kids.py | timestomp loses corroboration silently on read errors (journal=False; _ts_vol_times -> (0,0)): tie |
| K080 | a test names it: test_1132_red_b_items.py | FUTURE compares Created with $VOLUME_INFORMATION+0xA0, which is not the last metadata write, so re |
| K081 | **oracle** probe GREEN on this build | --margin-days is unvalidated: negative values accepted silently (98% HIGH), 0 turns jitter into HI |
| K092 | out of scope (refsprogs, plan 2.4) | refsls/librefs never terminates on a junction whose PrintNameLength is 0; listings lose later entr |
| K093 | out of scope (refsprogs, plan 2.4) | refsprogs aborts on every 64K-cluster volume (metadata read overflow) |
| K094 | out of scope (refsprogs, plan 2.4) | refsprogs rejects the 4Kn volume (sectors_per_cluster < 8) and prints the wrong variable |
| K106 | corrected in the reference layer: errata.md, reference_table.csv | 'Both CHKP copies always decode to the same 13-root list' (what_survives.md, carrier_categories.md |
| K129 | corrected in the reference layer: errata.md | CT_ALLC_RA_001 is CONFIRMED but three structure statements are contradicted by the bytes (fixed 20 |
| K131 | corrected in the reference layer: errata.md | CT_CTBL_010 is CONTRADICTED only under a value-relative reading; row+0xA0 is the container start o |
| K145 | corrected in the reference layer: errata.md | FS_SUPB_RA_002 is CONFIRMED, but its headline 'SUPB page has NO self-checksum' is contradicted by  |
| K187 | **battery** (A3_oid_root_zero) | integrity --fullchecksums prints 'all 511 checksummed pages VERIFIED - no tampering/corruption' wh |
| K189 | a test names it: test_1132_e1_kids.py | verify-bundle 'rehydrates and bootstraps' check runs only when no other problem exists and passes  |

## Totals

- battery: **23**
- test: **13**
- in-reference: **9**
- oracle-green: **3**
- refsprogs: **3**

