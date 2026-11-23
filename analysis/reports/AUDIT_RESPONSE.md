# Response to the audit — one row per finding, with where the answer can be checked

**Generated** by `analysis/verification/gen_audit_response.py`. Do not hand-edit: a hand-kept
list of 215 findings drifts the moment a fix lands, and the generator is deliberately blind to
prose, because a K-id mentioned in a sentence is not evidence that it was addressed (N75).

## Totals

| state | count | meaning |
|---|---:|---|
| in-reference | 61 | corrected in an erratum or a register row that cites the K-id |
| in-docs | 38 | the documentation corrected to state what the tool does |
| in-tool | 37 | a fix site in the tool cites it; no probe or test names it (not evidence that can fail) |
| test | 29 | a test in the suite names it and passes |
| battery | 21 | a damaged-volume case asserts the corrected behaviour and is GREEN |
| analysed | 15 | measured and recorded in a named document, NOT fixed |
| refsprogs | 8 | not this repository (plan v12 section 2.4) |
| oracle | 4 | a per-K-id probe is GREEN on this build |
| refuted | 2 | the audit's finding refuted by a measurement, recorded in a named document |

## By severity

| severity | battery | oracle | oracle-red | in-tool | in-reference | test | refuted | analysed | in-docs | refsprogs | deferred | UNTRIAGED |
|---|---|---|---|---|---|---|---|---|---|---|---|---||
| wrong_bytes | 6 | 1 | 0 | 3 | 1 | 1 | 1 | 1 | 0 | 4 | 0 | 0 |
| wrong_verdict | 14 | 3 | 0 | 12 | 6 | 13 | 0 | 0 | 0 | 3 | 0 | 0 |
| wrong_claim | 1 | 0 | 0 | 18 | 42 | 8 | 1 | 7 | 17 | 1 | 0 | 0 |
| wording | 0 | 0 | 0 | 4 | 12 | 7 | 0 | 5 | 21 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |

## Every finding, by the audit's own rank

| rank | K-id | severity | where the answer is | title |
|---:|---|---|---|---|
| 1 | K001 | wrong_bytes | cited at a fix site in the tool: forefst.py (no probe or test names it) | Extent decoders ignore the sparse flag (0x20): hole records with VLCN==FVCN (or below  |
| 2 | K003 | wrong_bytes | damaged battery: B4_image_truncated_in_file | _read_vlcn_extents (extract/export of extent-backed ADS) silently caps streams at 512  |
| 3 | K007 | wrong_bytes | damaged battery: B4_image_truncated_in_file | On a truncated image extract writes fewer bytes than FileSize (non-length-safe slice)  |
| 4 | K008 | wrong_bytes | audit oracle probe, GREEN on this build | export resident-all silently overwrites a file when two names sanitize to the same des |
| 5 | K009 | wrong_bytes | damaged battery: B2_integrity_data_hole | extract never verifies the stored per-cluster CRC32-C of integrity-stream files (verif |
| 6 | K012 | wrong_bytes | damaged battery: A7_object_page_flip | Content and listing paths never check a page's CRC64 against its parent reference (ext |
| 7 | K013 | wrong_bytes | damaged battery: A8_ct_resigned_move | No Container-Table consistency check (injectivity, target signature, data CRC): a re-s |
| 8 | K022 | wrong_bytes | analysed, not fixed: A6_CARVE_STATUS - carve zero-fill measured | export deleted --carve zero-fills checksummed data clusters of slack type-0x40 backing |
| 9 | K023 | wrong_bytes | a test names it: test_1132_red_b2_carve.py | export deleted --carve writes truncated or all-zero carves from inconsistent holders ( |
| 10 | K025 | wrong_bytes | refuted: Q1_verification_status - REFUTED: ordering is higher sub_id = newer | snapshots --extract completes a prior version's missing blocks from the LIVE stream al |
| 11 | K026 | wrong_bytes | cited at a fix site in the tool: forefst.py (no probe or test names it) | snapshots --extract writes an unresolvable version as a 0-byte file with no warning |
| 12 | K057 | wrong_bytes | cited at a fix site in the tool: forefst.py (no probe or test names it) | MLog 4 KiB block unit replaced by cluster size on 64K volumes: bundle rehydrates log b |
| 13 | K061 | wrong_bytes | corrected in the reference layer: errata.md | 512-byte-sector assumption: export metadata on the 4Kn volume writes 512 non-VBR bytes |
| 14 | K074 | wrong_bytes | damaged battery: B4_image_truncated_in_file | read_usn_j_stream would drop/clip $J extents beyond the sum of clusters and usn_J_inde |
| 15 | K087 | wrong_bytes | out of scope (refsprogs, plan v12 section 2.4) | refscat returns wrong clusters for non-resident named streams |
| 16 | K088 | wrong_bytes | out of scope (refsprogs, plan v12 section 2.4) | refscat outputs the oldest snapshot stream's bytes for snapshot-bearing files (no stre |
| 17 | K089 | wrong_bytes | out of scope (refsprogs, plan v12 section 2.4) | refscat scrambles a sparse file whose extents are stored out of logical order |
| 18 | K090 | wrong_bytes | out of scope (refsprogs, plan v12 section 2.4) | refscat truncates a file to the stale size cached in its directory entry |
| 19 | K010 | wrong_verdict | damaged battery: B2_integrity_data_hole | A hole in an integrity-stream cluster is described as possibly the file's own zeros /  |
| 20 | K011 | wrong_verdict | damaged battery: B2_integrity_data_hole | integrity reads only metadata pages yet prints unscoped 'no tampering/corruption', PAS |
| 21 | K014 | wrong_verdict | a test names it: test_1132_red_a_coverage.py | summary/dataruns/refsanalysis containers report a damaged or relocated Container Table |
| 22 | K017 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | export metadata writes usn_J.bin without holes_mark: stderr reports hole-sourced $J by |
| 23 | K018 | wrong_verdict | a test names it: test_1132_e1_kids.py | Undeterminable hole coverage is treated as 'no holes' on every content path except ext |
| 24 | K019 | wrong_verdict | damaged battery: A4_oid_root_punch | The export metadata bundle does not reflect metadata damage (zero-filled vbr_backup.bi |
| 25 | K020 | wrong_verdict | a test names it: test_1132_e1_kids.py | export metadata MLog branch swallows exceptions: bundle lacks MLog artifacts with no m |
| 26 | K024 | wrong_verdict | a test names it: test_1132_red_b2_carve.py | deleted/export deleted grade rows 'metadata + carve' BEST-EFFORT whose carve produces  |
| 27 | K028 | wrong_verdict | a test names it: test_1132_red_a_coverage.py | deleted --full claims it scanned 100% of the volume after silently skipping a 16 MiB b |
| 28 | K029 | wrong_verdict | damaged battery: A1_chkp_flip_newest | integrity warns on a checkpoint only when role=='secondary' and never on SUPB copies ( |
| 29 | K030 | wrong_verdict | damaged battery: A1_chkp_flip_newest, A6_supb_backup_zero, A7_object_page_flip | integrity rc/clean are computed from FAIL + page-checksum mismatches only: page-refere |
| 30 | K031 | wrong_verdict | audit oracle probe, GREEN on this build | integrity PASS/clean=true/rc 0 with incomplete checksum coverage (page cap reached or  |
| 31 | K032 | wrong_verdict | damaged battery: A6_supb_backup_zero | SUPB backups are located by signature scan of the last 64 clusters and warned only whe |
| 32 | K034 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | summary takes Volume GUID from the unverified primary SUPB and prints the constant 'pa |
| 33 | K035 | wrong_verdict | damaged battery: A1_chkp_flip_newest | refsanalysis boot/supb/chkp --verify tables have no self-checksum or clock rows ('vali |
| 34 | K036 | wrong_verdict | damaged battery: A1_chkp_flip_newest, A2_chkp_zero_newest | Checkpoint selection is signature-only and +0x10-ordered with no self-checksum check a |
| 35 | K037 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | The active checkpoint is picked by header +0x10 at 10 sites with 4 tie rules, while th |
| 36 | K038 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | Tied checkpoint clocks: forefst marks both copies PRIMARY (secondary warning cannot fi |
| 37 | K042 | wrong_verdict | a test names it: test_1132_e1_kids.py | Checkpoint clock-consistency damage (allocator clock above virtual clock; inverted acr |
| 38 | K043 | wrong_verdict | damaged battery: A3_oid_root_zero, A4_oid_root_punch | _walk returns [] silently for a referenced page that is not a B+ node and the bootstra |
| 39 | K044 | wrong_verdict | damaged battery: A3_oid_root_zero | summary Global Root Tables: exception handlers turn an unreadable root page into '0 ro |
| 40 | K045 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | Directory-page damage silently removes names from files/summary/timeline, gives surviv |
| 41 | K046 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | integrity (including --fullchecksums) follows only inner-node child refs, never page r |
| 42 | K047 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | USN presence is computed in three places and a read error of the FS-metadata directory |
| 43 | K048 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | security --audit prints 'VERDICT: CLEAN - 0/0' rc 0 when the SD table root page is dam |
| 44 | K050 | wrong_verdict | cited at a fix site in the tool: refsanalysis.py (no probe or test names it) | bootedit repair --dry-run diagnoses only primary-VBR fixboot fields (no backup VBR/SUP |
| 45 | K051 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | volume_state is 'NATIVE v' + VBR version and is never compared with CHKP or $VOLUME_IN |
| 46 | K055 | wrong_verdict | corrected in the reference layer: errata.md | MLog redo iteration (duplicated in two functions) uses remaining = total_size - first_ |
| 47 | K056 | wrong_verdict | corrected in the reference layer: errata.md | MLog parser reads only the first redo block of each log record (no merged-block iterat |
| 48 | K058 | wrong_verdict | damaged battery: B5_mlog_newest_zero | Zeroing the newest 1024 MLog records reads as a healthy shorter log ('Failed: 0'); che |
| 49 | K059 | wrong_verdict | a test names it: test_1132_e1_kids.py | mlog --parse/--csv and timeline date volume-information updates at the volume format t |
| 50 | K062 | wrong_verdict | audit oracle probe, GREEN on this build | Undamaged 4Kn volume: integrity WARNs 'backup boot sector missing' / 'fewer than 2 SUP |
| 51 | K064 | wrong_verdict | a test names it: test_1132_red_b_items.py | Image length used as volume length: summary capacity counts the image tail (48 MB 'bey |
| 52 | K067 | wrong_verdict | damaged battery: B3_journal_tail_zero | parse_usn_records counts zero words inside the live range as slack and accepts any ali |
| 53 | K068 | wrong_verdict | damaged battery: B3_journal_tail_zero | Head/tail-truncated or fully zeroed $J is reported as a normal shorter journal by usn  |
| 54 | K069 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | On an active journal whose records are all zeroed, timeline states 'USN journal inacti |
| 55 | K070 | wrong_verdict | a test names it: test_1132_e1_kids.py | $J real stream size/VDL at MI value +0x38/+0x40 are never read; code and docs wrongly  |
| 56 | K075 | wrong_verdict | a test names it: test_1132_e1_kids.py | Timestomp USN corroboration is keyed by file NAME with a live-name uniqueness gate (pr |
| 57 | K076 | wrong_verdict | cited at a fix site in the tool: forefst.py (no probe or test names it) | Journal coverage is never checked: a truncated journal or one created after the files  |
| 58 | K077 | wrong_verdict | a test names it: test_1132_e1_kids.py | timestomp loses corroboration silently on read errors (journal=False; _ts_vol_times -> |
| 59 | K080 | wrong_verdict | a test names it: test_1132_red_b_items.py | FUTURE compares Created with $VOLUME_INFORMATION+0xA0, which is not the last metadata  |
| 60 | K081 | wrong_verdict | audit oracle probe, GREEN on this build | --margin-days is unvalidated: negative values accepted silently (98% HIGH), 0 turns ji |
| 61 | K092 | wrong_verdict | out of scope (refsprogs, plan v12 section 2.4) | refsls/librefs never terminates on a junction whose PrintNameLength is 0; listings los |
| 62 | K093 | wrong_verdict | out of scope (refsprogs, plan v12 section 2.4) | refsprogs aborts on every 64K-cluster volume (metadata read overflow) |
| 63 | K094 | wrong_verdict | out of scope (refsprogs, plan v12 section 2.4) | refsprogs rejects the 4Kn volume (sectors_per_cluster < 8) and prints the wrong variab |
| 64 | K106 | wrong_verdict | corrected in the reference layer: errata.md, reference_table.csv | 'Both CHKP copies always decode to the same 13-root list' (what_survives.md, carrier_c |
| 65 | K129 | wrong_verdict | corrected in the reference layer: errata.md | CT_ALLC_RA_001 is CONFIRMED but three structure statements are contradicted by the byt |
| 66 | K131 | wrong_verdict | corrected in the reference layer: errata.md | CT_CTBL_010 is CONTRADICTED only under a value-relative reading; row+0xA0 is the conta |
| 67 | K145 | wrong_verdict | corrected in the reference layer: errata.md | FS_SUPB_RA_002 is CONFIRMED, but its headline 'SUPB page has NO self-checksum' is cont |
| 68 | K187 | wrong_verdict | damaged battery: A3_oid_root_zero | integrity --fullchecksums prints 'all 511 checksummed pages VERIFIED - no tampering/co |
| 69 | K189 | wrong_verdict | a test names it: test_1132_e1_kids.py | verify-bundle 'rehydrates and bootstraps' check runs only when no other problem exists |
| 70 | K002 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | dataruns reports 0 runs for every extent map with a gap/VLCN-0 hole (all-or-nothing co |
| 71 | K004 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | DataResidency is never 'unallocated': a 'size > 0' gate makes the value unreachable, s |
| 72 | K005 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | files ADSNames / details list duplicate, non-existent alternate streams (28 files, 44  |
| 73 | K006 | wrong_claim | a test names it: test_1131_held_items.py, test_1132_e2d_b9.py | FileAttributes for split files is the union of index-entry and backing bits (or the in |
| 74 | K015 | wrong_claim | refuted: NEW_FINDINGS N90 - REFUTED as a frame error: the 'written even when nothing drew from holes' sentence is in the BULK-export subsection (docs/tools/forefst.md:323), where the code does write it unconditionally; `extract`'s own section conditions its sidecar on holes being involved | extract -o writes no holes.json when nothing came from holes and none under --refuse-h |
| 75 | K016 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | Extent-backed ADS hole reporting passes no hole ranges, names the host file, and justi |
| 76 | K021 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | Bundle source_content_pin (sha256 of size + first 64 KiB) does not identify source con |
| 77 | K027 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | snapshots lists an ADS (sub_id 0x1000) as a recovered 'current version' (Snapshots: 1  |
| 78 | K033 | wrong_claim | damaged battery: A5_supb_primary_zero | No superblock fallback: parse_supb reads only LCN 0x1e, so a destroyed primary SUPB wi |
| 79 | K039 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | Checkpoint SHA-256 is computed over different lengths (1 cluster in summary, 4 cluster |
| 80 | K040 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | export metadata labels the older checkpoint 'CHKP (current)' because it assigns role b |
| 81 | K041 | wrong_claim | a test names it: test_1131_held_items.py, test_1132_red_group2b.py | Foreign 3.4: a checkpoint that no longer verifies even with its self-LCN restored leav |
| 82 | K049 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | Recorded skips never change exit status or verdicts; code claims 'skipped work is repo |
| 83 | K052 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | No code reads CHKP +0x70 or pending log records, so no surface reports clean/dirty vol |
| 84 | K053 | wrong_claim | documented: docs/concepts/transactions_crash_consistency.md (two sites) — the two checkpoint copies do NOT distinguish a crashed volume from a clean one | Documented dirty-volume signals (diverging checkpoint slots, large clock gap) classify |
| 85 | K054 | wrong_claim | analysed, not fixed: CORRECTIONS.md — measured on the CTF image (analysis/reports/v1.13.2/LD/LD_NOTES.md, Q10, 2026-11-07): the superblock and checkpoint copies hold zeros at +0x20..+0x38 and fail their self-checksum -- this image's damage, not a 3.4 trait (two corpus 3.4 volumes hold their own LCN there); the tool reads past it with two warnings, and bootedit repair --dry-run lists the five failures, restores nothing and exits 2 | The foreign 3.4 volume's bootstrap self-LCNs are zeroed on all 5 SUPB/CHKP copies: ref |
| 86 | K060 | wrong_claim | corrected in the reference layer: errata.md | MLog control header '+0x20 Generation' is an LSN (tool prints its low half as Generati |
| 87 | K063 | wrong_claim | cited at a fix site in the tool: refsanalysis.py (no probe or test names it) | 4Kn volume size reported as 504.0 MB (528482304) instead of 4227858432 by summary and  |
| 88 | K065 | wrong_claim | documented: docs/structures/vbr.md, docs/concepts/cluster_page_size.md — the corpus DOES contain real 4Kn volumes: bytes/sector is 512 or 4096, sectors/cluster 1, 8 or 128 | vbr.md ('sectors/cluster 8 or 128') and cluster_page_size.md ('all volumes 512 bytes/s |
| 89 | K066 | wrong_claim | a test names it: test_1131_held_items.py | v3.4 summary 'Space used 722.4 MB (18.2%)' counts other tiers' spans and a 131,072-clu |
| 90 | K071 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | usn --info shows '$Max stream: Extents: 0' and never the $Max parameters: $Max is assu |
| 91 | K072 | wrong_claim | a test names it: test_1131_held_items.py, test_1132_red_c1_objtable.py | usn path column is not a FileRef resolution (parent OID current path + record-time nam |
| 92 | K073 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | forefst is documented to accept V2/V4 USN records with a one-time note; planted V2/V4  |
| 93 | K078 | wrong_claim | documented: docs/concepts/timestomp_detection.md — a standalone USN BASIC_INFO_CHANGE is not specific to tampering - 34 records, only 12 deliberate stomps; robocopy /COPY:DAT and archive extraction produce it too | USN evidence treated as a deliberate edit (standalone BASIC_INFO_CHANGE lifts to HIGH) |
| 94 | K079 | wrong_claim | documented: docs/concepts/timestomp_detection.md — the LOW tier is UNREACHABLE (0 of 256 enumerated inputs) and ROUND_TIMESTAMPS alone returns INFO, not LOW | LOW tier is unreachable, ROUND_TIMESTAMPS alone yields INFO (docs: LOW), and '--min LO |
| 95 | K083 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | Docs: 'SetFileTime through one name updates every name at once' is contradicted on dis |
| 96 | K084 | wrong_claim | documented: docs/examples/detect_timestomping.md — the worked example mixed two images; it now reproduces on the image its Setup describes | docs/examples/detect_timestomping.md does not reproduce on the image it describes (tie |
| 97 | K085 | wrong_claim | analysed, not fixed: CORRECTIONS.md — measured against the volume's own T21 action log extracted from the image; recorded rather than changing a lab artefact | T21 oracle: true_created/true_modified of every positive row in t21_actions.csv hold p |
| 98 | K086 | wrong_claim | a test names it: test_1131_held_items.py, test_single_source.py, test_timestomp_single_source.py | Single-source tests assert object identity, not behaviour (_filetime_to_str 'differs'  |
| 99 | K091 | wrong_claim | out of scope (refsprogs, plan v12 section 2.4) | refsls listing sizes differ from FileSize for 47 names (cached per-name size) |
| 100 | K095 | wrong_claim | a test names it: test_1131_held_items.py | forefst files row mixes sources: AllocatedSize from the stale index-entry header (+0x6 |
| 101 | K096 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | files progress line counts inline/extent-backed with the walk flag is_resident while C |
| 102 | K097 | wrong_claim | a test names it: test_1131_held_items.py, test_1132_red_b2_refsanalysis.py | refsanalysis files -v prints the stale cached per-name size for split hard-link names  |
| 103 | K098 | wrong_claim | a test names it: test_1131_held_items.py, test_image_holes_and_page_refs.py | v3.4: get_resident_file_size returns the default 0 (refsanalysis details 'File size: 0 |
| 104 | K099 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | export metadata manifest inline_content omits split-record inline streams, contrary to |
| 105 | K100 | wrong_claim | documented: docs/tools/forefst.md — FileAttributes is the ReFS decoding, not Windows': Directory_Internal vs Directory and a tool-only EA bit differ on 490 of 4,684 rows | FileAttributes shows raw on-disk bits (0x10000000, 0x40000), not the documented Window |
| 106 | K101 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | btree_node.md key-index 'marker' is not two-valued, 0 is not confined to index pages,  |
| 107 | K102 | wrong_claim | documented: docs/structures/schema_table.md — the Schema Table key is 4 bytes, not 8 | schema_table.md says the Schema Table key is 8 bytes; it is 4 on every row |
| 108 | K103 | wrong_claim | documented: docs/structures/container_table.md — the raw example's value offset is 0x10, not 0x20 | container_table.md:153 raw example gives value offset 0x20; every row uses 0x10 |
| 109 | K104 | wrong_claim | cited at a fix site in the tool: forefst.py (no probe or test names it) | Object Table value+0x18 is not the checkpoint virtual clock (docs object_table.md:22-2 |
| 110 | K105 | wrong_claim | analysed, not fixed: CORRECTIONS.md — CHKP+0x88/+0x8C read 0x680/0x20 on every v3.4 copy measured; the finding does not reproduce | chkp.md:20-21: CHKP+0x88/+0x8C are 0/0 on the 3.4 volume, not 0x680/0x20 |
| 111 | K107 | wrong_claim | documented: docs/concepts/version_evolution.md, docs/concepts/bootstrap_chain.md — CHKP+0x94 holds 13 u32 IN-PAGE OFFSETS in both modes, never 13 inline page references | version_evolution.md / bootstrap_chain.md say direct mode stores '13 inline page refer |
| 112 | K108 | wrong_claim | corrected in the reference layer: errata.md | extent_descriptors.md: sparse hole records do not have VLCN == 0 (half have VLCN == FV |
| 113 | K109 | wrong_claim | corrected in the reference layer: errata.md | Docs '$SI+0x70 always 1 / embedded-only' is contradicted: in backings it equals the nu |
| 114 | K110 | wrong_claim | analysed, not fixed: CORRECTIONS.md — the size-matched hard-link join reproduces the driver exactly: 577 names, 0 over-merge, 0 under-merge | Docs: size-matched hard-link join does not 'reproduce fsutil exactly' nor have 'zero o |
| 115 | K111 | wrong_claim | documented: docs/structures/directory_entries.md — value+0x58 is a CACHED copy of the $DATA size, not 'decisively FileSize' | directory_entries.md: embedded value+0x58 is not 'decisively FileSize' (stale on 3 win |
| 116 | K112 | wrong_claim | documented: docs/concepts/attributes.md (two sites) — the index attribute copy is NOT strictly a lower bound - it can set the Archive bit the backing lacks | Docs: index-entry attribute copy does set bits the backing lacks (81 files, Archive) |
| 117 | K113 | wrong_claim | documented: docs/attributes/STANDARD_INFORMATION.md — for a DIRECTORY the own-row $SI Changed time is not the value Windows reports | Docs: for directories the own type-0x10 $SI Changed time is not the one Windows report |
| 118 | K114 | wrong_claim | documented: docs/attributes/OBJ_LINK.md — on ReFS 3.4 every directory DOES carry a 0x38 $OBJ_LINK row | Docs: on ReFS 3.4 every directory carries a 0x38 $OBJ_LINK (doc: 0 of 309) |
| 119 | K115 | wrong_claim | documented: docs/attributes/OBJ_LINK.md — the v3.7+ name is at key+0x20 (= value+0x18), not key+0x14, and is not NUL-terminated | OBJ_LINK.md v3.7+ key table (name at key+0x14) and 'null-terminated' name are contradi |
| 120 | K116 | wrong_claim | corrected in the reference layer: reference_table.csv | Docs: 'key and value overlap by construction' holds only for 0x39 rows |
| 121 | K117 | wrong_claim | documented: docs/attributes/NAMED_DATA.md — flag 0x1000 marks the EXTENT-BACKED form; the page contradicted itself | Docs: NAMED_DATA 0x1000 flag 'does not mean non-resident - still inline' contradicts t |
| 122 | K118 | wrong_claim | corrected in the reference layer: errata.md | Docs: bit 28 is absent from every directory own-row $SI+0x20, Win11 volumes included |
| 123 | K119 | wrong_claim | documented: docs/structures/usn_journal.md, docs/glossary.md, docs/attributes/STANDARD_INFORMATION.md — USNs ARE reused: re-creating the journal restarts at 0 without changing the UsnJournalId | After journal recreation the Journal ID is unchanged but USNs restart at 0, so USNs ar |
| 124 | K120 | wrong_claim | corrected in the reference layer: errata.md, reference_table.csv | usn_journal.md / system_oids.md Change Journal value size and sub-record table are wro |
| 125 | K121 | wrong_claim | corrected in the reference layer: reference_table.csv: AP_REDO_005 (static_analysis_notes) — the note contradicted the row's own description; checked in all six builds by name and address | AP_REDO_005 static note 'removed in v3.14 (falls to default error)' is contradicted by |
| 126 | K122 | wrong_claim | corrected in the reference layer: reference_table.csv: AP_REDO_005 (description) — the '7x' was an artefact of the pre-A2 MLog framing (published 1.12.3 reports 7); re-measured with the driver-derived parser | AP_REDO_005 'disk: 7x on v3.14 win11refs2tsnapshots' is a parser artifact; its registe |
| 127 | K123 | wrong_claim | analysed, not fixed: A2_REGISTER_REMEASURED - AP_REDO_040 re-measured, two clauses refuted | AP_REDO_040 commit-bit model and opcode statistics are artifacts of the truncated redo |
| 128 | K124 | wrong_claim | corrected in the reference layer: reference_table.csv: AP_LGFL_RA_005 (description, raw_analysis_notes) — 'record_index can exceed physical page count' is not reproduced anywhere; the old note compared the index against WRITTEN blocks, not the area size | AP_LGFL_RA_005 'record_index can exceed physical page count' not reproduced; wrap is a |
| 129 | K125 | wrong_claim | corrected in the reference layer: reference_table.csv: AP_LGTB_005 (description, raw_analysis_notes) — '0x30' names neither framing - value+0x30 is past the end of a 48-byte value, and row+0x30 is the FIRST control LCN | AP_LGTB_005: second control LCN is not '0x31 (3.4) or 0x8001 (3.14)'; '0x30' is not th |
| 130 | K126 | wrong_claim | corrected in the reference layer: reference_table.csv | FS_ALLOC_RA_002 'slot 0 = ... 1 on v3.4 Medium': the only 3.4 volume reads 2 |
| 131 | K127 | wrong_claim | corrected in the reference layer: reference_table.csv: FS_ALLOC_RA_002 (description) — the '48 MiB tail' is IMAGE end minus mapped end; inside the DECLARED volume the tail is 0 clusters on 11/11 | FS_ALLOC_RA_002 'unmapped tail' is measured to the image end (the space lies outside t |
| 132 | K128 | wrong_claim | corrected in the reference layer: errata.md | FS_ALLOC_RA_002 static note '3 x 0x80 = 384 bytes': LoadAllocatorSummary requires and  |
| 133 | K130 | wrong_claim | corrected in the reference layer: reference_table.csv: CT_ALLC_004 (description) — measured physical vs virtual on 11 v3.14 volumes - physical matches on all, virtual on none | CT_ALLC_004: Medium spans the physical cluster space (not virtual); Small tier bootstr |
| 134 | K133 | wrong_claim | corrected in the reference layer: errata.md | CT_BKRC_RA_003 'value length is exactly 0x820 (1,441/1,441)' fails on its own witness  |
| 135 | K134 | wrong_claim | corrected in the reference layer: errata.md | CT_BKRC_RA_001: value-length formula fails on 2 winsider rows (32-byte compact form);  |
| 136 | K135 | wrong_claim | corrected in the reference layer: errata.md | FS_RESD_SA_002: RefsCheckValidResidentDataAttribute absent from insider_29574, whose v |
| 137 | K136 | wrong_claim | corrected in the reference layer: reference_table.csv: FS_CHKP_RA_002 (static_analysis_notes) — no arithmetic in the function derives a reference size from a checksum type or version flag | FS_CHKP_RA_002 static basis 'ValidateCheckpointRecord: ref_size derived from checksum  |
| 138 | K137 | wrong_claim | corrected in the reference layer: errata.md | FS_SCHM_RA_002 cites CmsReadCache::ResetReadCacheMetadataFile with static_scope 'win11 |
| 139 | K138 | wrong_claim | corrected in the reference layer: errata.md | FS_OTBL_SA_009: CmsObjectTable::DeleteIdentifier is 110 bytes in insider, not 30 |
| 140 | K139 | wrong_claim | corrected in the reference layer: errata.md | FS_OTBL_SA_009: 'guarantees OIDs never reused' does not follow from DeleteIdentifier;  |
| 141 | K140 | wrong_claim | corrected in the reference layer: errata.md | GN_SNAP_SA_001: 'CStreamSnapshot class' exists in no available build; '6->24 functions |
| 142 | K141 | wrong_claim | corrected in the reference layer: reference_table.csv: FS_VBR_SA_013 (description) — there is no power-of-two test (a range and a set), and the row omitted the self-checksum comparison entirely | FS_VBR_SA_013: RefsIsBootSectorOurs checks bytes-per-sector range 0x200..0x1000, an SP |
| 143 | K142 | wrong_claim | corrected in the reference layer: reference_table.csv: FS_VBR_RA_014 (static_analysis_notes) — RefsMarkVolumeForUpgrade reaches RefsWriteBootSector via RefsReadWriteBootSector mode 4 | FS_VBR_RA_014: 'format-upgrade path does not call RefsWriteBootSector' is contradicted |
| 144 | K143 | wrong_claim | corrected in the reference layer: reference_table.csv: FS_VBR_RA_014 (raw_analysis_notes) — 0x3110000 is a real ReFS copy but not the driver-maintained backup; the backup is the last sector | FS_VBR_RA_014: 'Backup VBR at 0x3110000' is not the driver's backup LBA |
| 145 | K144 | wrong_claim | corrected in the reference layer: reference_table.csv: FS_VBR_RA_014 (description) — no 3.12 witness exists pre-mount; the claim cannot be distinguished from 'never edited' by these bytes | FS_VBR_RA_014: 3.12 laundering has no pre-mount witness; 6.66/3.15 non-mount is the Re |
| 146 | K146 | wrong_claim | corrected in the reference layer: reference_table.csv: FS_SUPB_RA_006 (description) — the 'clean volume' pair is a corrupted-then-repaired SUPB; one byte differs before the mount | FS_SUPB_RA_006 calls a mount that self-healed a corrupted primary SUPB a 'mount on cle |
| 147 | K147 | wrong_claim | corrected in the reference layer: reference_table.csv | Four rows whose description was rewritten to the corrected statement still carry disk_ |
| 148 | K148 | wrong_claim | corrected in the reference layer: reference_table.csv: MD_DATA_RA_027 (description) — both experiments the row called untested were run on lab314_main_step3; (a) reverses the expectation | MD_DATA_RA_027 is stale: both experiments it calls untested were run, and the FileAllo |
| 149 | K149 | wrong_claim | corrected in the reference layer: reference_table.csv: MD_SNAP_RA_010 (description) — C < snapshot ts is the NORMAL ordering (3 of 3 snapshotted files, stomped and not); the test is an upper bound | MD_SNAP_RA_010: 'a creation time backdated below a snapshot timestamp is a contradicti |
| 150 | K150 | wrong_claim | corrected in the reference layer: reference_table.csv: MD_USN_RA_005 (raw_analysis_notes) — the '0 references' half is contradicted - 111 on winsider, plus 1 on a volume the row itself cites | MD_USN_RA_005 'monotonically allocated': 111 first-FILE_CREATE ordinals on the real in |
| 151 | K151 | wrong_claim | corrected in the reference layer: reference_table.csv: MD_SI_RA_002 (description) — the headline holds, but 'index entry' must be scoped to the EMBEDDED form; split values are too short to have +0x58 | MD_SI_RA_002: $SI+0x38 is the allocated-size slot, not an unpopulated 'DataSize slot', |
| 152 | K152 | wrong_claim | corrected in the reference layer: reference_table.csv: MD_DATA_RA_028 (description) — measured under the SHIPPED dispatcher order the split is 99.1 / 0.9 / 0.0, not 54.4 / 37.1 / 8.5 | MD_DATA_RA_028 decoder census does not describe forefst v1.12.3 on any available volum |
| 153 | K153 | wrong_claim | corrected in the reference layer: reference_table.csv: FN_DTBL_002 (description) — the row named only the embedded form; the split form is a third of all file rows | FN_DTBL_002: file names also live in type-0x00020030 rows; CONFIRMED rests on a key[0: |
| 154 | K154 | wrong_claim | corrected in the reference layer: reference_table.csv: MD_ATTR_RA_008 (description) — the stated counts cannot sum to the stated total; re-censused, and two row classes were missing | MD_ATTR_RA_008 sub-record distribution is arithmetically impossible and its type list  |
| 155 | K155 | wrong_claim | corrected in the reference layer: reference_table.csv: FN_LINK_001 (description) — the gate is the VBR volume flag; v3.7 and v3.9 volumes carry hard links, so 'abolished until 3.14' is false | FN_LINK_001: hard-link gate is boot-sector flag 0x2C bit 0x20 (RefsHardlinksSupported) |
| 156 | K156 | wrong_claim | corrected in the reference layer: reference_table.csv: MD_ATTR_009 (raw_analysis_notes) — both halves were wrong - the PCT holds no names, and the real name is stored in a type-0x39 sub-record | MD_ATTR_009: OID 0x520's name is 'File System Metadata' (its own 0x10 row link), not ' |
| 157 | K157 | wrong_claim | analysed, not fixed: CORRECTIONS.md — every witness the finding calls 'not findable' is present in this workspace; the premise is a property of the audit's sandbox | Register rows rest on named witness reports, scripts, dossiers, corpora and static ref |
| 158 | K158 | wrong_claim | analysed, not fixed: CORRECTIONS.md — the items called UNCHECKABLE are checkable here and check out: all four WSL tags plus SYMLINK present on win11refs2gtargeted | Register rows claim format/volume coverage (3.7/3.10 volumes, WSL-tagged volumes, Win1 |
| 159 | K170 | wrong_claim | documented: docs/tools/forefst.md col 4 - Extension keeps the on-disk case; the 10-char suffix cap stated | Extension column is not lowercase and is blank for suffixes of 12+ characters (undocum |
| 160 | K202 | wrong_claim | corrected in the reference layer: reference_table.csv: FS_VBR_012 (raw_analysis_notes) — a v3.4 volume reads 0x2A = 0 and is nevertheless fully CRC64-checksummed; the field is gated by VBR+0x2C bit 0x40 | FS_VBR_012: '0x2A checksum selector, 0=None (3.4)' does not mean unchecksummed 3.4 met |
| 161 | K204 | wrong_claim | corrected in the reference layer: reference_table.csv: CT_DRNT_002 (description) — '0x0010=data' fails on v3.4 as well as v3.14; the 0x0080 CRC32-C half is confirmed | CT_DRNT_002 lumps a confirmed flag (0x80), a flag contradicted only on 3.14 (0x10) and |
| 162 | K205 | wrong_claim | corrected in the reference layer: reference_table.csv: FS_MOVE_RA_001 (static_analysis_notes) — the link add/remove pair is absent from the move path, and MsReparentChildTable IS present in win10 | FS_MOVE_RA_001: RefsMoveFile does not call RefsRemoveLink/RefsAddLink (RefsSetRenameIn |
| 163 | K207 | wrong_claim | corrected in the reference layer: reference_table.csv: CT_COMP_RA_003 (static_analysis_notes) — win10 carries four named compression algorithms; 'LZX only' understates it | CT_COMP_RA_003: 'win10 17134 has CmsCompressionLZX only' wrong; '3.15' counted as a ve |
| 164 | K208 | wrong_claim | corrected in the reference layer: reference_table.csv: CT_CTBL_RA_007 (description) — the invariant holds but the cited offset is the win10 CPC field, not log2, on a row scoped to both formats | CT_CTBL_RA_007 'log2(CPC) at volume+0x50' is build-specific (+0x4C in the 3.4-era driv |
| 165 | K159 | wording | documented: docs/structures/chkp.md — the root-reference spacing is the page-reference size stored at CHKP+0x5C (104/48/72), not a literal 0x5C - 226/226 copies | chkp.md 'spaced 0x5C apart' / 'stride 0x5C' actually mean the value stored at CHKP+0x5 |
| 166 | K160 | wording | documented: docs/structures/btree_node.md — the descriptor size at +0x04 is a u16, not a u32 - the upper half is a separate table-dependent field, so the u32 reading is wrong on 1,042 of 1,432 root pages | btree_node.md index-root descriptor size field shared/truncated on allocator roots, +0 |
| 167 | K161 | wording | documented: docs/structures/container_table.md — container_map's KEY was never defined: it is the Container ID u64 at row key +0x00, starting at 2 (minimum key == 2 on 113/113 volumes) | container_map[container_index] docs never say the index is the Container-Table key ID |
| 168 | K162 | wording | documented: docs/structures/object_table.md — the compact row has no 16-byte header at +0x08: format is u32@+0x00, key/value offsets at +0x08/+0x0C, payload offset and trailer at +0x10/+0x14 (89,231/89,231 rows) | object_table.md compact-value field labels misplaced; legacy section omits where the r |
| 169 | K163 | wording | documented: docs/structures/container_table.md — all-ones at value+0x20 is a SENTINEL on 762,252 of 797,837 rows, and on v3.4 the +0x20 and +0x28 counts differ enough to move volume totals | container_table.md free-cluster fields have an undocumented all-ones sentinel on 3.14  |
| 170 | K164 | wording | documented: docs/structures/supb.md — SUPB+0x68 reads 1 on 351 of 351 copies over 117 images, so the documented 'highest virtual clock' selection rule discriminates on no volume in the corpus | Assorted core-structure doc gaps: selection tie-break, duplicate-row rule, virtual hea |
| 171 | K165 | wording | documented: docs/attributes/NAMED_DATA.md, docs/structures/directory_entries.md — stream names are NOT NUL-terminated - 0 of 254 type-0xB0 names and 0 of 3,830 reverse-index names carry a terminator; length comes from the key | NUL-terminator statements for ADS names and reverse-index names are wrong (names lengt |
| 172 | K166 | wording | documented: docs/structures/directory_entries.md — value+0x00 is the record-node offset (0xA8 on 2,701/2,701) and +0x04 the node descriptor 0x00010028 - the old '40 B structural metadata' row hid both | File-system doc gaps bridged from bytes: record node offset, 0x40 key layout, dir OID  |
| 173 | K167 | wording | documented: docs/structures/directory_entries.md — sub-stream id 0x8 is the stream-set metadata record, not the default data stream: all 1,448 are 40-byte values with no extents and size 0 | directory_entries.md says the default DATA stream index is 0x0008; bytes and DATA.md s |
| 174 | K168 | wording | cited at a fix site in the tool: forefst.py (no probe or test names it) | Extent-node framing statements inconsistent (hint saturation, 'array at ihdr+0x28', ex |
| 175 | K169 | wording | documented: docs/structures/directory_entries.md — the marker does not partition the type codes - $DATA 0x80 appears under BOTH markers, and $OBJ_LINK/$I30_INDEX/$EFS were missing from the table | Sub-record marker table incomplete |
| 176 | K171 | wording | documented: docs/tools/forefst.md col 1 - a directory's ObjectRef is OID:0x0 (as the change journal does) | ObjectRef for directories prints 'OID:0x0' (doc: own OID); USN blank instead of 0 |
| 177 | K172 | wording | a test names it: test_1131_held_items.py | A bare CLOSE reason (0x80000000) is rendered '0x80000000' in CSV/JSON but 'CLOSE' in - |
| 178 | K173 | wording | a test names it: test_1131_held_items.py | Warning 'skipped N non-zero byte(s)' counts 8x words and blames 'torn record at the wr |
| 179 | K174 | wording | documented: docs/concepts/attributes.md — $Max field layout documented: 12-byte wrapper then four u64 at content +0x0C/+0x14/+0x1C/+0x24 (MaximumSize, AllocationDelta, UsnJournalID, LowestValidUsn), verified on 5 journals | $Max content layout undocumented |
| 180 | K175 | wording | documented: docs/structures/usn_journal.md — $J is 4 KiB page-framed with zero padding; a record never straddles a page (0 of 332,745) and the tail is not simply zeros | No USN framing/padding/resync rules documented; 'zero tail' is not zero on 2/7 journal |
| 181 | K176 | wording | documented: docs/structures/usn_journal.md — a record can carry NO parent and NO name - 234 such records on each lab314_main variant | usn_journal.md: nameless records with ParentFileReferenceNumber 0:0 (895 records) undo |
| 182 | K177 | wording | documented: docs/structures/usn_journal.md — record length reaches 408 B, not 312; 1,779 records on winsider exceed 312 | usn_journal.md: 1,779 winsider records exceed the stated observed length range (max 40 |
| 183 | K178 | wording | documented: docs/structures/usn_journal.md — the 128-bit File ID is ordinal at +0x08 then home OID at +0x10 - the reverse of the documented upper/lower reading | usn_journal.md: 'upper/lower 8 bytes' of the 128-bit File ID do not state on-disk orde |
| 184 | K179 | wording | documented: docs/tools/forefst.md — a file absent from the image exits 1, not 2 | Exit-code table says extract rc 2 = 'refused a file that is not in the image'; a missi |
| 185 | K180 | wording | documented: docs/tools/forefst.md — the exit-code table was byte-identical to published 1.12.3 while the changelog announced rc 2's new meaning; now states both finding and could-not-complete | Exit-code table understates the rc-2 sources (verify-bundle FAIL, hole-sourced extract |
| 186 | K181 | wording | cited at a fix site in the tool: forefst.py (no probe or test names it) | extract of a symlink reports '0 bytes - empty file' without noting the reparse point |
| 187 | K183 | wording | a test names it: test_1131_held_items.py | export resident-all reports '619 skipped' but 622 files were not written (zero-byte in |
| 188 | K184 | wording | a test names it: test_1132_red_b2_wording.py | summary 'Total file size' sums per name, including 11.4 GB of extra hard-link names on |
| 189 | K185 | wording | documented: docs/tools/forefst.md — AllocatedSize < FileSize does NOT corroborate IsSparse - it fails on 79 of 137 sparse rows (57.7%), the majority | IsSparse doc 'corroborated by AllocatedSize < FileSize' fails on 3/9 rows; 'agrees wit |
| 190 | K186 | wording | cited at a fix site in the tool: forefst.py (no probe or test names it) | Most triage/listing verdict surfaces report CLEAN on data-damage copies and their help |
| 191 | K188 | wording | cited at a fix site in the tool: forefst.py (no probe or test names it) | Error messages after metadata-page damage blame the wrong cause and never name the unr |
| 192 | K190 | wording | a test names it: test_1132_e1_k190_k194.py | _volume_times docstring says 'Used by --timestomp' but only timeline calls it; timesto |
| 193 | K191 | wording | analysed, not fixed: measured: 7 FILETIME converters, disagreeing only at 0/1/all-ones/year>=10000, none of which occurs on the corpus (the audit records 0 disagreements there). Consolidating seven output paths is a refactor, not an RC change; recorded rather than rushed | FILETIME converters disagree at edge values (pre-1970, all-ones, year>=10000); 0 disag |
| 194 | K192 | wording | a test names it: test_1131_held_items.py | build_oid_path_map directory test reads value+0x40 on embedded rows (one non-directory |
| 195 | K193 | wording | documented: docs/concepts/timestomp_detection.md — the USN_BASIC_INFO_CHANGE gate is documented | USN_BASIC_INFO_CHANGE counts only when CHANGE_LATE/PRE_FORMAT/CREATE_GT_MODIFY also fi |
| 196 | K194 | wording | a test names it: test_1132_e1_k190_k194.py | timestomp help cites a removed 'files --timestomp' column; --margin-days documented as |
| 197 | K195 | wording | corrected in the reference layer: reference_table.csv: GN_IDENT_RA_001 (raw_analysis_notes) — the NOTE described a rendering the tool stopped producing in 1.11.0; verified against the current build | Register format_claimed/format_verified fields and notes are inconsistent with what wa |
| 198 | K196 | wording | corrected in the reference layer: reference_table.csv: FS_CHKP_RA_014 (description) — the root-pointer finding stands (18/18 equal) but the copies differ in 11-15 bytes, including the allocator clock and self-LCN | FS_CHKP_RA_014 'Only the virtual clock + per-page checksums differ' between the two CH |
| 199 | K197 | wording | corrected in the reference layer: reference_table.csv: FS_VBR_RA_010 (format_verified) — the claim holds on 146/146 ReFS volumes including the 3.7/3.9/3.10 ones the scope omitted | FS_VBR_RA_010 'No hidden data / true reserved space' does not cover 4Kn boot-sector ta |
| 200 | K198 | wording | corrected in the reference layer: reference_table.csv: MD_SNAP_RA_001 (description) — the name is in the key; it appears in the value on 0 of 10 sub-records | MD_SNAP_RA_001 places the snapshot name 'in sub-record body'; the bytes put it in the  |
| 201 | K199 | wording | corrected in the reference layer: reference_table.csv: MD_USN_RA_005 (description) — $SI+0x58 is the object's OWN ordinal, not a next-counter; the counter is the Object-Table payload u64@+0x50 | MD_USN_RA_005 calls $SI+0x58 'NextFileId'; on disk it is the object's own ordinal |
| 202 | K200 | wording | corrected in the reference layer: reference_table.csv: MD_DATA_RA_015 (description, format_claimed) — 8.1%/34.6% are corpus-composition aggregates; the per-volume range is 0-96.2% and 0-100% | MD_DATA_RA_015 percentages depend on corpus composition, not format; format_claimed di |
| 203 | K201 | wording | corrected in the reference layer: reference_table.csv: GN_ARCH_RA_001 (static_analysis_notes) — the cited line numbers were off by one or two and landed on unrelated lines | Stale or unresolvable register citations (decompilation file names/lines, a forefst li |
| 204 | K203 | wording | corrected in the reference layer: reference_table.csv: MD_SI_RA_015 (static_analysis_notes) — the cited lines resolve in one build only and land in unrelated code in the other four | MD_SI_RA_015: 'LastUsn = virtual byte offset of the latest $J record' needs ring-journ |
| 205 | K206 | wording | corrected in the reference layer: reference_table.csv: FS_OTBL_RA_007 (description) — '400 objects in range' was arithmetically impossible and the image was unnamed | FS_OTBL_RA_007: '400 objects in 0x700-0x8F9 (76.6%)' arithmetic inconsistent, image un |
| 206 | K209 | wording | corrected in the reference layer: reference_table.csv: GN_PAGE_003 (static_analysis_notes) — the static verdict rested on a disk measurement; the function exists in every build and includes a 0->1 rule the layer omitted | GN_PAGE_003 static CONFIRMED rests on disk analysis; driver's XOR==0 -> 1 rule omitted |
| 207 | K210 | wording | corrected in the reference layer: reference_table.csv: FS_SCHM_RA_008 (raw_analysis_notes) — 0xe020 is on disk as a schema VALUE on 21 images; only its absence as a KEY holds | FS_SCHM_RA_008 supporting numbers/text do not reproduce as written (61 functions, 28/3 |
| 208 | K211 | wording | corrected in the reference layer: reference_table.csv: CT_MISC_002 (static_analysis_notes) — the count is build-stale; 8972/9444/insider carry 19 after a genuine symbol removal | CT_MISC_002: CmsTrashTable count is 19; 'retained' is flag-gated deferred deletion (>5 |
| 209 | K212 | wording | analysed, not fixed: CORRECTIONS.md — the inventory script's ReparseTag column is empty on every row of every inventory it produced (5,974 rows, 0 non-empty) | Truth inventory.csv ReparseTag column never measured (script uses info class 35), so t |
| 210 | K213 | wording | analysed, not fixed: CORRECTIONS.md — the inventory's MACB values re-read byte-for-byte at every offset the finding names | Truth: directory $R1K8L13 Changed time moved between the 1923 inventory and T21 withou |
| 211 | K214 | wording | analysed, not fixed: CORRECTIONS.md — BOTH premises of the manifest row are wrong: lab314_4kn is fully readable (VBR parses, 4096 B/sector, 1 sector/cluster) | Audit brief/MANIFEST premises wrong: step3/dirty have on-volume Windows inventories, a |
| 212 | K215 | wording | analysed, not fixed: CORRECTIONS.md — the manifest and links table contain no T21 entry (grep -ci t21 = 0 in both) and no lab_t21_* image exists | MANIFEST does not identify the T21 images: no lab_t21_main/dirty image, T21 lives only |
| 213 | K182 | wording | documented: docs/tools/forefst.md col 38 - AllocatedSize blank for directories | AllocatedSize and HardLinkCount blank for all directories (Windows: Allocation 0, Link |
| 214 | K082 | none | analysed, not fixed: CORRECTIONS.md — re-run on the CTF image (LD_NOTES.md Q10): the 8 .tort files are INFO (CREATE_GT_MODIFY), the audit's values reproduced; INFO is kept: Changed earlier than Created on 1,762 benign copied files of three corpus volumes | CTF time_update.exe manipulation found only as INFO 'copy-indistinguishable' although  |
| 215 | K132 | none | analysed, not fixed: CORRECTIONS.md — the finding's load-bearing premise is false: two 4 KiB SHA-256 volumes DO exist in the corpus, and value+0x90 == value[len-16] on 518,838 of 518,838 160-byte rows | CT_CTBL_006 ('0x90-0x98 physical start LCN, 4K clusters') is CONTRADICTED although it  |
