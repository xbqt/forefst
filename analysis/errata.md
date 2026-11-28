<!-- Generated from the project's working errata, which are not in this repository. Do not edit this copy by hand: every change is made in the working errata. -->
# Post-Thesis Errata

These are the corrections made to this project's ReFS reference, numbered E1 to E182. The first ones
correct the master's thesis the project started from; the later ones correct the reference pages, the
claim register (`reference_table.csv`, next to this file) and the tools. An erratum wins over the text it
corrects, and a later erratum over an earlier one it supersedes.

Many entries cite the project's working files, such as the reports under `analysis/reports/`. Not all of
those files are in this repository: a path you cannot find here names a working file that is not
published.

Corrections discovered during post-thesis review sessions against the submitted PDF (`memoire.pdf`). Each entry references the thesis section, table, or listing where the error appears, the correct value established by post-thesis analysis, and the evidence source.

Batches: E1-E8 verified 2026-06-02, E9-E12 verified 2026-06-03, E13-E17 verified 2026-06-03, E18 verified 2026-06-09, E19 verified 2026-06-09. E9-E11 resolved 2026-06-09 (mlog.md corrected, refs_mlog.py replaces broken tool). E22-E25 verified 2026-06-11 ($SI deep analysis). E26 verified 2026-06-11 ($SI+0x38 is DataSize, not timestamp). E27-E41 verified 2026-06-12 (field-verdict consolidation + verification pass; see analysis/tools/analysis_scripts/field_verdicts/CONSOLIDATED.md and VERIFICATION.md). E27 supersedes E24; E32 corrects E15/E17; E20 reaffirmed (E41). E42-E44 verified 2026-06-14/16. **E45 + E30 RETRACTION verified 2026-06-17** (resident type-0x30 = index entry, not $SI; value+0x58 = FileSize not USN; per-file USN = LastUsn $SI+0x40 / value+0x68, proven 14/14 then 480/480 $J-record matches; see analysis/reports/deep_si_usn_findings_2026-06-17.md). E27/E28 reaffirmed; E26 clarified. **E46-E48 verified 2026-06-18** (static-decompilation + all-disk resolution of the 2 held claims + the snapshot re-verify error: E46 page+0x40 = TableIdHigh not Schema; E47 [**LATER SUPERSEDED by E49** — Prade's 0x20-0x28 was actually correct] index-header row count = u32 at header+0x14; E48 non-resident snapshots exist and use type-0x40 extents, overturning the UNCONFIRMABLE verdict; see analysis/reports/held_claims_and_snapshots_2026-06-18.md). **E49 verified 2026-06-19 — SUPERSEDES E47 (frame error):** Prade's "Index Root" is the `_SmsIndexRoot` descriptor at page+0x50 (not the per-node `_SmsIndexHeader` at thoff); in that frame GN_IDXR_002 (schema@0x0C), GN_IDXR_003 (extents@0x18) and GN_IDXR_004 (total-rows@0x20) are ALL CONFIRMED (static + all-disk). E47's "GN_IDXR_004 CONTRADICTED" is retracted. See analysis/reports/idxroot_descriptor_2026-06-19.md. **E50 verified 2026-06-19:** Parent-Child schema u32[7] is the key-comparison-rules selector (8->CmsRulesPARENT_CHILD_LINK), NOT a 'bit 3 = value-overlaps-key' flag; the overlap is a caller-side same-buffer construction (AddParentChildLink/InitializeIndexEntry). Refuted on disk (schema 0x130 has bit 3 set, no overlap). The registry's last E3 is eliminated. See analysis/reports/pct_schema_u32_7_2026-06-19.md. **E117-E123 filed 2026-10-24** (1.13.2, wave C's close: the MLog open count, the checkpoint record size, the superblock choice, the Container Table's allocated count, the failover-pair labels, the boot-sector validity, the redo opcodes without a handler). **E124 filed 2026-10-27** (1.13.2, wave D's close: a page with another signature is an earlier volume's only at the address it names, in its own units). **E125-E128 filed 2026-11-04** (1.13.2, wave E's close: `$SI+0x24` bit 0x02 = case-sensitive directory; checkpoint flags 0x010 / 0x020 / 0x040 / 0x100; what `refsutil fixboot` writes; boot-sector flags bit 0x20 = hard-link support). **E129-E133 filed 2026-11-05** (1.14.0, the conformance batch: OID 0x500 / 0x501 and 0x540 / 0x541 are failover pairs, no primary; the OID 0x520 children's value+0x80 is their file id; `RefsLinkFileToSelf` adds no name; a superblock copy's header clocks are those of its write; a hard-linked file's names diverge on Changed routinely). **E134-E143 filed 2026-11-06, E144-E146 2026-11-07** (1.14.0, the labs-and-driver batch: `VersionCheck`'s operand is the boot sector's version, at +0x894 / +0x895 on Insider; the Container Table copies differ in bits 0x2000 and 0x4000; the boot sector's +0x2A is read only with flag 0x40; Container Table row +0x28 is not decoded; +0x2A = 0 is not a volume without checksums; Container Table rows +0x50 / +0x98 as the driver lays them out; the 104-byte page reference is the checkpoint's root reference on 3.4-3.9; 17134 checks a metadata page against its reference's checksum type; `$VOLUME_INFORMATION`+0xA0 is the time of the last mount that writes; a directory listing does not refresh a hard link's stale name; without hard-link support a move moves the whole record and leaves its reference). The number between E115 and E117 is reserved for the drafted MLog control `+0x18`/`+0x20` erratum (`analysis/reports/v1.13.2/DEEP_CHECK_VERDICT.md` §8), not filed until its lab separation (N342) is read.

---

<a id="e1"></a>
## E1 — Page size is cluster-size-dependent, not version-dependent

| | |
|---|---|
| **Thesis claim** | Page size is 4 KiB on v3.4, 16 KiB on v3.14 |
| **Correct** | **16 KiB on both** (4 clusters x 4 KiB). Page size depends on cluster size, not version. 64K clusters → 64 KiB pages. |
| **Thesis locations** | Implied in multiple sections discussing page layout |
| **Evidence** | CHKP run outputs: LCN quadruples show 4 consecutive clusters on all images regardless of version |
| **Docs affected** | structure_reference.md, forefst docs |

<a id="e2"></a>
## E2 — MLog control page field count

| | |
|---|---|
| **Thesis claim** | MLog control page has "19 decoded fields" |
| **Correct** | **18 field positions** (16 with known meaning + 2 unknown purpose). ~124 bytes undecoded in 5 gap regions. |
| **Thesis locations** | MLog section |
| **Evidence** | ra_step4_2_logfile_report.md: 18 rows in control page table |
| **Docs affected** | Thesis text |
| **Update (2026-11-21, RC3a W1; RUNNING_LOG N663, the follow-up N182 placed)** | The count "18 field positions" is superseded. It is the number of rows in `ra_step4_2_logfile_report.md`'s control-page table, not a reading of the driver. The control record's payload is a byte copy of the first 0xE48 bytes of the log handle (`DEEP_MLOG_CONTROL_STATIC.md` §1; master §E.1a; **E116**, **E117**, **E148**; register AP_LGFL_RA_011): +0x00 the control-area write sequence, +0x08 / +0x10 the data area's start / end, +0x18 the log start, +0x20 the log end, +0x28 the log instance's UUID, +0x38 the u32 log open count, +0x3C flags, +0x40 the u32 log version, +0x44 the u64 host info, +0x4C to +0xE47 zero. |

<a id="e3"></a>
## E3 — Insider Extended GUID / UEFI NVRAM binding

| | |
|---|---|
| **Thesis claim** | Insider uses Extended GUID (VBR+0x48) for UEFI NVRAM binding |
| **Correct** | **Separate GUIDs**: `SetRollbackGUID` and `SetBootVolumeGuidFwVariable` are distinct functions. `FreezeRollbackParameters` passes checkpoint record field, not VBR+0x48. Relationship unresolved. |
| **Thesis locations** | Boot / VBR analysis section |
| **Evidence** | Ghidra decompilation of FreezeRollbackParameters, boot_decompiled.json |
| **Docs affected** | Thesis text, main_findings |

<a id="e4"></a>
## E4 — Insider function count

| | |
|---|---|
| **Thesis claim** | Insider function count = 6,023 |
| **Correct** | **6,430** non-external functions (6,981 total − 551 externals) |
| **Thesis locations** | Driver analysis section (§4.2) |
| **Evidence** | winsider_refs_quick.json: total_functions=6430 |
| **Docs affected** | Thesis text |

<a id="e5"></a>
## E5 — VBR format-time fields never modified during upgrade

| | |
|---|---|
| **Thesis claim** | VBR 0x2A updated to 0x0002 on 3.9→3.14 upgrade |
| **Correct** | **Stays 0x0000 for ALL upgrade paths.** VBR format-time fields (0x2A, 0x2C, 0x48) are never modified during upgrade. |
| **Thesis locations** | Version evolution / upgrade analysis |
| **Evidence** | boot_win10to11refs4g.txt: version=3.14, 0x2A=0x0000; boot_newimages.txt confirms |
| **Docs affected** | disks.md, thesis text |
| **Amendment (2026-11-12; RC1-docs G7 I035)** | "Format-time" holds for 0x2A and 0x48 only, and "ALL upgrade paths" for the two upgrades measured (3.4 -> 3.14 `win10to11refs4g`, 3.9 -> 3.14 `win1122h2test`). 0x2C (volume flags) is written at run time: a writable mount sets 0x02, `RefsSetBreakOnCorrupt` sets or clears 0x01, `MsKmeUpdateBootSector` sets 0x10, `RefsMarkVolumeForUpgrade` sets 0x80 and `RefsUpgradeVersionInBootSector` clears it at the next writable mount; its format bits 0x20 (E128) and 0x40 kept their values on the two upgrades measured. |

<a id="e6"></a>
## E6 — Hard links finding classification

| | |
|---|---|
| **Thesis claim** | Hard links finding = CONTRADICTED (vs Prade) |
| **Correct** | **NEW** — Prade was correct for v3.4 (hard links abolished). v3.14 native hard link support is a NEW finding, not a contradiction of Prade. |
| **Thesis locations** | Findings register, evaluation section |
| **Evidence** | findings_register.md #187 |
| **Docs affected** | findings_register |

<a id="e7"></a>
## E7 — ADS ceiling depends on cluster size, not version

| | |
|---|---|
| **Thesis claim** | ADS ceiling version-dependent (~3.8 KiB on v3.4) |
| **Correct** | **Cluster-size-dependent**: 4K clusters → 16 KiB page capacity, 64K clusters → 64 KiB page capacity. Both v3.4 and v3.14 with 4K clusters have the same ceiling. |
| **Thesis locations** | Content category, ADS/resident storage discussion |
| **Evidence** | structure_reference ADS Size Limit table |
| **Docs affected** | structure_reference, thesis text |
| **Update (2026-11-21, RC3a W1; RUNNING_LOG N663)** | The ceiling is not the page capacity, and it depends on the format, not the cluster size. On formats 3.11 and later a stream, main or named, is inline below the 2 KiB conversion threshold and in extents from it (**E61**); **E91** measured that identically on 4 KiB, 64 KiB and 4Kn volumes (1,900 B inline, 2,100 B in extents). Below 3.11 an inline stream never converts: a named stream stays inline and `RefsAddAllocationForResidentWrite` refuses an inline write past 128 KiB (a driver reading; every named stream of the corpus on those formats is 47 B or less, so none exercises the cap), and no main `$DATA` is inline (0 of 7,006 rows on the 3.4 to 3.10 volumes; **E87**). Master "ADS Size Limit" and `docs/concepts/cluster_page_size.md` ("Inline stream ceiling") state this. |

<a id="e8"></a>
## E8 — Attribute type count

| | |
|---|---|
| **Thesis claim** | 26 attribute types |
| **Correct** | **27**: 26 identified by E1 (string literal) + $EA (type 0xE0) identified by E2 (`RefsLookupEasOnFile` function analysis) |
| **Thesis locations** | §4.5.2 Attribute architecture, Table 4.27 |
| **Evidence** | subreport_attributes_v2.md |
| **Docs affected** | Analysis docs (some say 26, thesis says 27) |

<a id="e9"></a>
## E9 — Redo opcode count and evidence level

> **SUPERSEDED 2026-06-13 (finding #328), re-confirmed 2026-07-05.** The "32/37" and "25/27" figures below were themselves an undercount. The driver `PerformRedo` dispatches a CONTIGUOUS range: **v3.14 = 44 opcode values (0x00–0x2B) = 43 handlers + 1 explicit-error branch (0x17 → NTSTATUS 0xC0000427); v3.4 = 29 values (0x00–0x1C), all handled** (~26 distinct handler functions). 0 true gaps. Verified by re-reading `PerformRedo_win11.c` (max case `!= 0x2b`) / `PerformRedo_win10.c` (max `== 0x1c`) and the tool's live "Dispatch table: v3.14 (44 opcodes)". Canonical table: `forclaude/intelligence/redo_opcode_complete.md`. Use 44/29, NOT 32/37 or 25/27.

| | |
|---|---|
| **Thesis claim** | "19 redo opcodes catalogued from raw disk analysis" (some E3) |
| **Correct (superseded — see banner above; use 44/29)** | ~~**32 redo operations / 37 opcode values** (v3.14), **all E2**. v3.4 has 25 handlers / 27 values.~~ Cross-version relationships (15 unchanged, 3 renamed, 3 repurposed, 1 rejected, 3 removed, 11 new) predate #328 and need per-opcode re-derivation against the driver. |
| **Thesis locations** | §4.7 Application category, Appendix E.3 (redo opcode table) |
| **Evidence** | Decompilation of `CmsLogRedoQueue::PerformRedo` in Win10 and Win11 with PDB |
| **Docs affected** | annexe_structures.tex E.3, findings_register #210, mlog.md, refs_logfile_v2.py |
| **Resolution** | mlog.md dispatch table corrected (v3.0.2). refs_mlog.py (1240 lines) replaces refs_logfile_v2.py with correct E2 dispatch tables for both versions. |

<a id="e10"></a>
## E10 — MLog tool opcode numbering is wrong

| | |
|---|---|
| **Thesis claim** | Tool REDO_OPS numbering correct |
| **Correct** | **Wrong**: only 2/19 tool entries match actual dispatch values. Tool scans all 4-byte positions for small integers — NOT a reliable opcode detector. |
| **Thesis locations** | Tool output referenced in §4.7 |
| **Evidence** | Comparison of tool dict vs PerformRedo dispatch table |
| **Docs affected** | refs_logfile_v2.py REDO_OPS dict + detection logic |
| **Resolution** | refs_logfile_v2.py replaced by refs_mlog.py. Reads opcode from `_SmsRedoRecord+0x04` via two-layer parsing. 25/25 images, 0 unknown opcodes. |

<a id="e11"></a>
## E11 — MLog record header layout (inner vs outer)

| | |
|---|---|
| **Thesis claim** | Log Record Header: +0x00 = "Record type/signature", +0x04 = "Record length" |
| **Correct** | **Likely wrong for inner redo record.** Decompilation shows `_SmsRedoRecord` has record_size at +0x00 and opcode at +0x04. The thesis header may describe the OUTER log block (from Lee), while the inner redo record has a different layout. Two-layer structure not previously documented. |
| **Thesis locations** | Appendix E.2 (MLog record structure) |
| **Evidence** | ForEachRedoInBlock + PerformRedo decompilation |
| **Docs affected** | annexe_structures.tex E.2 |
| **Resolution** | mlog.md now documents both layers: outer `_SmsRedoHeader` (total_size at +0x00, first_record_offset at +0x04) and inner `_SmsRedoRecord` (record_size at +0x00, opcode at +0x04, object_id at +0x20, flags at +0x2C, min 0x38 bytes). ForEachRedoInBlock iteration logic included. |

<a id="e12"></a>
## E12 — Evidence level tags in findings register

| | |
|---|---|
| **Thesis claim** | Finding #99 (schema 0xe0f0) tagged RD only |
| **Correct** | Should be **E3+RD** — same structural inference method as #112-114 (other legacy schemas). Also #210 should note all E2 (not E2+E3). |
| **Thesis locations** | Appendix: Findings Register |
| **Evidence** | findings_register.md |
| **Docs affected** | findings_register |

<a id="e13"></a>
## E13 — Container Table root index

| | |
|---|---|
| **Thesis claim** | §4.4.4: Container Table called "global root 2" |
| **Correct** | **Roots 7/8**. Root 2 is the Container Allocator. The parenthetical "global root 2 in the analysis of Section 4.3" uses the wrong root index. |
| **Thesis locations** | §4.4.4 p.97 (one parenthetical reference) |
| **Evidence** | Table 4.18, §4.3.6, Subtable A.4b all confirm Container Table = roots 7/8 |
| **Docs affected** | §4.4.4 one parenthetical |

<a id="e14"></a>
## E14 — Schema count (system + attribute)

| | |
|---|---|
| **Thesis claim** | Listing 5.2 p.135: "30 (14 system + 16 attribute)" |
| **Correct** | **29 (13 system + 16 attribute)**. Production v3.14 has 13 system schemas; 14 is the Insider count (adds 0xe140 Volume Attestation). |
| **Thesis locations** | Listing 5.2 p.135 |
| **Evidence** | schema_win11refs8g.txt: "Total entries: 29, System table schemas (13 entries)" |
| **Docs affected** | Listing 5.2 |

<a id="e15"></a>
## E15 — key_flags location and values

> **CORRECTED 2026-06-12 by E32.** The "0x04=directory" value below is WRONG. key_flags is only ever {0x01 resident, 0x02 non-resident}; directories use 0x02 + the directory attribute bit (0x10000000) at value+0x40. See E32.

| | |
|---|---|
| **Thesis claim** | §4.4.1 p.94: key_flags described as "first 4 bytes of row header" with values 0x68/0x2a8 |
| **Correct** | **key_flags is at key offset 0x02 (u16), NOT in the row header.** Values 0x68 and 0x2a8 are total row sizes, not key_flags. Correct key_flags: 0x01=resident, 0x02=non-resident (no 0x04 — directories use 0x02 + dir attribute bit 0x10000000 (E32)). |
| **Thesis locations** | §4.4.1 p.94 |
| **Evidence** | structure_reference C.1, forefst.py line 831 (kd[0:2] = key type, kd[4:] = filename), row size arithmetic (16+16+72=104=0x68) |
| **Docs affected** | §4.4.1 paragraph |

<a id="e16"></a>
## E16 — Directory entry key layout (no Reserved field)

| | |
|---|---|
| **Thesis claim** | Table 4.33: key has Reserved(4) at 0x04 before Filename at 0x08 |
| **Correct** | **No Reserved field.** Correct key: Type(2, 0x00) + key_flags(2, 0x02) + Filename(var, **0x04**). Proof: "coucou"=6 chars→key=4+12=16B; with Reserved(4) it would be 20B, giving wrong row size 108 instead of 104=0x68. |
| **Thesis locations** | Table 4.33 |
| **Evidence** | structure_reference C.1, forefst.py kd[4:].decode("utf-16-le"), row size arithmetic |
| **Docs affected** | Table 4.33 |

<a id="e17"></a>
## E17 — Directory listing type annotation

> **CORRECTED 2026-06-12 by E32.** The "type 4 = directory" claim below is WRONG. Directories carry key_flags 0x02 (same non-resident layout as a non-resident file) and are distinguished by the directory attribute bit (0x10000000) at value+0x40, not by a distinct key_flags value. See E32.

| | |
|---|---|
| **Thesis claim** | Listing C.3 p.169: directory annotated "type 2" |
| **Correct** | ~~Should be "type 4".~~ **WRONG (see E32).** key_flags values are 0x01 = resident, 0x02 = non-resident (no 0x04 — directories use 0x02 + dir attribute bit 0x10000000 (E32)). The thesis "type 2" annotation is actually CORRECT for the on-disk key_flags: a directory IS key_flags 0x02 (non-resident layout); it is identified as a directory by the dir attribute bit at value+0x40, not by key_flags 0x04. Listing C.4's "type 1" = 0x01 resident is correct. |
| **Thesis locations** | Listing C.3 p.169 |
| **Evidence** | structure_reference Subtable C.1a; E32 (key_flags census {0x01,0x02} only across 111 images) |
| **Docs affected** | Listing C.3 annotation |

<a id="e18"></a>
## E18 — Address translation shift value

| | |
|---|---|
| **Thesis claim** | Address translation shift = log2(CPC) = 14 for 4K clusters |
| **Correct** | **shift = CPC.bit_length() = 15 for 4K, 11 for 64K.** Driver stores log2(CPC) at +0x50 and adds 1 before shifting (`GetContainerIdFromRealRange` at 0x1400b3e64). `(CPC-1).bit_length()` in annexe_lab.tex equals log2(CPC) for powers of 2 — same wrong value. methodology_tools.tex line 109 correctly says "bit_length() not log2()" but main text still uses log2 value. |
| **Thesis locations** | analysis_filesystem.tex line 373 (§4.3), annexe_lab.tex line 389 |
| **Evidence** | Win11 refs.sys decompilation + disk verification: VLCN 81408 with shift=15→CID 2→MSB+ valid; shift=14→CID 4→wrong page |
| **Docs affected** | analysis_filesystem.tex, annexe_lab.tex, structure_reference.md |

<a id="e19"></a>
## E19 — OID 0x520 is FS Metadata directory, not Security ID Mapping

| | |
|---|---|
| **Thesis claim** | OID 0x520 = "Security ID Mapping" table. SecurityId at $SI+0x28 resolves through OID 0x520 (mapping) then OID 0x530 (descriptors). Two-table security model. |
| **Correct** | **OID 0x520 = FS Metadata directory** (schema 0x200, child of root 0x600). Analogous to NTFS `$Extend`. SecurityId resolves **directly** in OID 0x530 — single-table model. OID 0x520 is not involved in security resolution at all. |
| **Thesis locations** | §4.5 Table 4.26 line "0x520 — Security ID mapping — Maps SecurityId → descriptor index"; §4.5.5 p.~110 "resolved through the Security ID mapping object (OID 0x520) to a shared descriptor blob in the Security Descriptors object (OID 0x530)"; §5.3 NTFS correspondence "OID 0x520 (mapping table) and OID 0x530 (descriptors)" and "rerouted through OID 0x520/0x530"; Appendix C.12 table row "0x520 — Security ID Mapping"; Appendix F.4a table row "0x520 — Security ID Mapping — SecurityId-to-descriptor index". |
| **Note** | The thesis was internally contradictory: reference table entry FS_OTBL_005 (Appendix D) **correctly** says "File System Metadata ID = 0x520 (like NTFS $Extend)" — the error is in the main text and structure appendix, not the reference table. |
| **Evidence** | **Raw disk** (25 images, v3.4 through Insider): OID 0x520 B+-tree contains directory-style entries (type 0x10 descriptor, type 0x30 filenames), uses schema 0x200 (same as root directory 0x600), and is a child of root 0x600 named "FS Metadata" in the parent-child table. No security mapping rows found on any image. **Static analysis** (3 builds: v3.4/v3.14/Insider): `MsInitializeWellKnownObjectId` is never called with 0x520; all security functions (`RefsSecurityInitialize`, `RefsLoadSecurityDescriptor`, `RefsCacheSharedSecurityBySecurityId`, `RefsSecurityGetDescriptorById`) resolve SecurityId directly in OID 0x530 via VCB+0xb0. `RefsHasSystemName` treats 0x520 as a directory. |
| **Version-dependent contents** | v3.4: 3 children ("Reparse Index", "Security Descriptor Stream", "Volume Direct IO File"). v3.9+: empty (descriptor only). USN activation adds "Change Journal" child. |
| **Docs affected** | structure_reference.md (C.12, F.4a), findings_register #156, system_oids.md, security_descriptors.md, ntfs_comparison.md, standard_information.md, usn_journal.md, README.md, refsanalysis.py (_KNOWN_OIDS) |
| **Investigation artifacts** | `forefst/docs/reports/investigate_oid_0x520.py`, `forefst/docs/reports/report_oid_0x520_investigation.txt` |

<a id="e20"></a>
## E20 — RETRACTED: ADS are always inline (original thesis claim correct)

> **REAFFIRMED 2026-06-12 (E41).** A 2026-06 snapshot agent claimed to have found a genuine non-resident ADS, which would refute E20. The verification pass REFUTED that claim: all 159 ADS scanned have stream_flags=0x02 (inline resident), including the single attr_flags=0x1000 ADS. E20 stands. attr-flag 0x1000 means "ADS on a file that also has snapshots/a stream-set", NOT non-residency. See E41.

| | |
|---|---|
| **Thesis claim** | ADS on ReFS are always resident (inline in B+-tree row, never promoted to non-resident) |
| **E20 original (wrong)** | Claimed ADS could be extent-based based on 7 entries with storage_type=2. |
| **Retraction** | The 7 "extent-based ADS" were **snapshot streams**, not ADS. Both ADS and snapshots use descriptor 0x000500B0 under marker 0x80000002. The discriminator is storage_type at hdr+0x0C: 0=ADS (always inline), 2=snapshot (extent-based). Cross-verified: 678 ADS across 41 images — ALL have storage_type=0. 28 entries originally counted as "extent ADS" are all snapshots (confirmed via `_classify_b0_entry` with data_sub_id in 0x1000-0xFFFF range at B+-tree value offset 0x44). The thesis claim is correct. |
| **Evidence** | **Raw disk** (111 images): 678 ADS entries across 41 images, all inline. Zero extent-based ADS observed. **Static analysis**: `RefsConvertToNonResident` accepts type 0xB0 (shared by ADS and snapshots), so non-resident ADS is theoretically possible but has never been empirically confirmed. |
| **Code fix** | `_parse_ads_from_value()` now filters out entries with storage_type != 0 (snapshots). |

<a id="e21"></a>
## E21 — $SI HardLinkCount and ReparseTag at wrong offsets

| | |
|---|---|
| **Thesis claim** | $SI+0x48 = HardLinkCount (u32), $SI+0x4C = ReparseTag (u32). Win11 extension $SI+0x50 = SnapshotId (u64), $SI+0x70 = ClassId (u32). |
| **Correct** | **ReparseTag is at $SI+0x54** (not 0x4C). **HardLinkCount is at $SI+0x70** (not 0x48). $SI+0x48 is a conditional u64 (usually 0). $SI+0x50 is a u16-derived u32 (not lower half of SnapshotId). $SI+0x50 and $SI+0x54 are separate u32 fields, NOT one u64 "SnapshotId". |
| **Thesis locations** | Table 4.28 ($SI layout), Appendix C.7 |
| **Evidence** | **Decompilation** (E2): RefsComputeStandardInformationFromFcb writes `*(u32*)(SI+0x54) = *(u32*)(FCB+0x9c)` (ReparseTag) and `*(u32*)(SI+0x70) = *(u32*)(FCB+0xb4)` (used by RefsConvertToStandardInfoLinkCount). **Raw disk** (RD): $SI+0x54 = 0xa000000c for all 367+ symlinks across 3 images; $SI+0x48 = 0; $SI+0x4C = high 32 bits of the u64 UsnJournalId@0x48 (see UPDATE). |
| **UPDATE (2026-06-16, disk re-verification)** | Two claims above were imprecise. **(1) $SI+0x4C is NOT "0 for all entries"** — it is the high dword of the u64 UsnJournalId@0x48: 0 when the journal is inactive, but **non-zero when active** (`== hi32(UsnJournalId)` on 4674/4674 objects; **602 non-zero** on journal-active volumes, e.g. win11refs2gtargeted). It is still not a separate ReparseTag. **(2) the "$SI+0x70 = 1/2/3 (link counts)" reading was the pre-E33 artifact** — $SI+0x70 is **≤ 1** (0 or 1, never > 1: 0/4674 objects with HLC>1); the "1/2/3" multi-name values were the retracted parser artifact. See **E33 / #292 / #340**. **E161 (2026-11-17):** the 4,674 objects were embedded records; in a type-0x40 backing $SI+0x70 is the link count. |
| **Docs affected** | structure_reference.md C.7 (common + Win11 extension), standard_information.md, findings_register |

<a id="e22"></a>
## E22 — $SI+0x50 has version-dependent semantics (not "unknown counter")

| | |
|---|---|
| **E21 description** | $SI+0x50 described as "u16-derived u32 counter" of unknown purpose. |
| **Correct** | **v3.4 through v3.9**: field = `ReparseTag & 0xFFFF` (low 16 bits of the reparse tag from the same FCB source). **v3.10+**: field = `PackedEaSize` (u16 from FCB+0xa0, Extended Attribute packed size). Transition occurs at the Win11 23H2 driver (v3.10). |
| **Evidence** | **Decompilation** (E2): Win10 `RefsUpdateStandardInformation` writes `local_38 = *(uint*)(FCB+0xa4) & 0xffff` (reparse low bits). Win11 24H2 `RefsComputeStandardInformationFromFcb` writes `*(uint*)(SI+0x50) = (uint)*(ushort*)(FCB+0xa0)` (PackedEaSize). `RefsReplaceFileEas` and `RefsUpdateFcbInfoFromDisk` (attribute 0xD0) confirm FCB+0xa0 is PackedEaSize. **Raw disk** (RD): v3.4-v3.9: counter=12 on all 284 SYMLINK entries (12 = 0x0C = low16 of 0xa000000C). v3.10: counter=0 on 115 SYMLINK entries (PackedEaSize=0, no EAs). Winsider v3.14: 3,852 entries with EA sizes 19-209 bytes. |
| **Docs affected** | structure_reference.md C.7, standard_information.md, open_questions.md |

<a id="e23"></a>
## E23 — $SI+0x58 is u64 VersionRefCount, not two u32

| | |
|---|---|
| **Previous** | Documented as two separate u32 fields: VersionRefCount ($SI+0x58) + VersionInfo ($SI+0x5C). |
| **Correct** | Single u64 write at $SI+0x58 in all code paths (Branch A and Branch B). "VersionInfo" at $SI+0x5C is just the upper 32 bits, always 0. Max observed value: 110,001 (fits in 32 bits). |
| **Evidence** | **Decompilation** (E2): `*(longlong*)(param_1 + 0x58) = lVar1` (Branch B), `*(undefined8*)(param_1 + 0x58) = ...` (Branch A) — both 8-byte stores. **Raw disk** (RD): 0 non-zero values at $SI+0x5C across 403,943 v3.7+ entries on 98 images. |
| **Docs affected** | structure_reference.md C.7, standard_information.md |

<a id="e24"></a>
## E24 — $SI+0x48 is SessionTimestamp (not "Unknown_48") — SUPERSEDED by E27

> **SUPERSEDED 2026-06-12 by E27.** The structural facts below (FILETIME from VCB+0x388, gated by VCB bit 19, one constant value per mount session, bit 23 semantics) are all correct. E27 identifies the *meaning*: $SI+0x48 is the **USN journal ID** (not a generic "session timestamp"), $SI+0x40 is the file's **last USN** (not a "ClassTag"/classification tag), and bit 23 is the journal-epoch validity bit. The "session-bound file classification" framing is replaced by the USN change-journal mechanism. See E27.

| | |
|---|---|
| **E21 description** | $SI+0x48 described as "conditional u64, usually 0" of unknown purpose. |
| **Correct** | **SessionTimestamp**: a FILETIME from VCB+0x388, gated by VCB flag bit 19 (0x80000) AND matching session token. Constant per mount session — all entries in one image share the same value. Invalidated on remount. Together with ClassTag ($SI+0x40), tracks session-bound file classification. |
| **Evidence** | **Decompilation** (E2): `RefsUpdateFcbInfoFromDisk` checks `VCB+0x18 & 0x80000` and compares `$SI+0x48` against `VCB+0x388`. If match: sets FCB+0xe0 from $SI+0x40, sets bit 23. If mismatch: clears both. **Raw disk** (RD): Non-zero on 9 of 111 images (all v3.14). Confirmed FILETIME values: winsider=2026-05-11T20:33:59, step5=2026-05-23T09:04:41. 100% correlation with ClassTag non-zero counts. |
| **Docs affected** | structure_reference.md C.7, standard_information.md |

<a id="e25"></a>
## E25 — InternalFlags: Win11 RTM already has all 4 FCB flag bits

| | |
|---|---|
| **Previous analysis** | Stated Insider has 4 FCB flag bits (0x1b, 0x16, 0x0b, 0x1f) vs Win11 RTM's 2 bits (0x1b, 0x16). |
| **Correct** | Win11 RTM `RefsComputeStandardInformationInternalFromFcb` (line 157912) already extracts all 4 bits identically to Insider. The function was not examined in the prior session; only the calling code in `RefsComputeStandardInformationFromFcb` was analyzed, which obscured the 4-bit extraction behind a function call. |
| **Evidence** | **Decompilation** (E2): Win11 RTM function at address 0x1400b7454: checks FCB+0x08 bits 27→flag0, 22→flag1, 11→flag2, 31→flag3. Identical to Insider inline code at line 174100-174110. |
| **Docs affected** | standard_information.md, RefsComputeStandardInformationFromFcb.md analysis file |

<a id="e26"></a>
## E26 — $SI+0x38 is DataSize, not LastMftChangeTime

| | |
|---|---|
| **Previous analysis** | $SI+0x38 described as "LastMftChangeTime (FILETIME)". Noted "often small FILETIME tick values rather than real dates". |
| **Correct** | **DataSize**: $DATA stream size in bytes. FCB+0x88 is populated from the attribute 0x80 ($DATA) stream summary during `RefsUpdateFcbInfoFromDisk`, NOT from a timestamp source. The PDB name "LastMftChangeTime" is a misnomer — likely a legacy field name from NTFS compatibility stubs. |
| **Evidence** | **Decompilation** (E2): `RefsUpdateFcbInfoFromDisk` line 465168-465192 — FCB+0x88 is set from `LookupAttribute(0x80)` → `GetStreamSummary()` → stream_summary+0x08 (or +0x20 for non-resident). **Raw disk** (RD): 110 images, 525,145 entries. **Resident entries**: 32,573 exact matches vs embedded $DATA content on winsider (97.9%); 689 mismatches are exactly 8-byte alignment padding; 1 outlier (GUID file, DataSize=1024 vs content=876). File `xbpt_large_149mb` = 156,237,824 = 149×1,048,576 bytes. `pagefile.sys` = 1,476,395,008 ≈ 1.37 GB. **Child OID type 0x10 $SI**: DataSize=0 for ALL non-resident files across ALL 110 images (not populated). **Directories**: DataSize=0 for 32,490/32,490 (100%). Refinement: DataSize is only populated in resident directory entry $SI; child OID's own $SI has DataSize=0. |
| **Docs affected** | structure_reference.md C.7, standard_information.md, RefsComputeStandardInformationFromFcb.md |
| **Clarified 2026-06-17** | The "resident: 32,573 exact matches (97.9%)" figure was the type-0x30 **index-entry FileSize at value+0x58**, NOT the type-0x10 $SI+0x38 field — those are different structures (see E30 retraction, §C.2). The core claim stands for the $SI itself: $SI+0x38 (DataSize) is **0 on 0 of 32,629 own-rows** (re-confirmed); the type-0x30 index entry carries FileSize@0x58 + AllocatedSize@0x60 (not DataSize@0x60). |

<a id="e27"></a>
## E27 — $SI+0x40 / $SI+0x48 are USN change-journal fields (LastUsn / UsnJournalId), not a tiering tag — SUPERSEDES E24

| | |
|---|---|
| **Previous (E24 / E3 tiering theory)** | $SI+0x40 = "ClassTag", $SI+0x48 = "SessionTimestamp", interpreted as a storage-tiering / session-bound file-classification tag. |
| **Correct** | **$SI+0x40 = LastUsn** — the file's last USN, i.e. the byte offset of its most recent record in `$UsnJrnl:$J`, 8-byte aligned (USN records are 8-aligned). Held in FCB+0xe0, written from the journal write cursor VCB+0x3a0 by `RefsWriteFcbUsnRecordToJournal`. **$SI+0x48 = UsnJournalId** — a FILETIME identifying the journal instance (VCB+0x388), exactly ONE distinct value per volume. **FCB+0x08 bit23** = "cached last-USN in FCB+0xe0 is valid for the CURRENT journal epoch": set only when the journal is active (VCB+0x18 & 0x80000) AND on-disk $SI+0x48 == VCB+0x388 (stale-epoch check, like NTFS USN journal-ID validation). The "storage tiering tag" interpretation is **DISPROVEN**. |
| **Evidence** | **Decompilation** (E2): write path `RefsWriteFcbUsnRecordToJournal` → `RefsPartialSetStandardInfo(...,0x40,0x10,...)` gated VCB+0x18 & 0x80000 (win11 L446230-446240), values from VCB+0x3a0 (L445790/445727) and VCB+0x388 (L159523, journal init L445682); epoch/bit23 check at L465089; v3.4 equivalent VCB+0x360, FCB+4 bit (L241626). **Raw disk** (RD): all 1443 $SI+0x40 values on win11refstestmftecmd.raw are 8-byte aligned; exactly ONE distinct $SI+0x48 per volume; upper 32 bits always 0; nonzero only on 9 v3.14+ images captured with an active USN journal. Verification pass: 717/717 LastUsn 8-aligned, 1 distinct UsnJournalId (0x1dcea86b624a787, valid FILETIME). |
| **Note** | Read code present since v3.4 (VCB+0x360); on-disk values written only v3.14+. Recommend renaming census/forefst field keys `class_tag`→`last_usn`, `session_timestamp`→`usn_journal_id`. Open MS-PDB member names and whether VCB+0x388 is journal-creation vs last-reset time remain unknown. |
| **Supersedes** | E24 (structural facts in E24 stand; the meaning is corrected here). |
| **Docs affected** | structure_reference.md C.7, standard_information.md, open_questions.md (A2), errata E24 |
| **Amendment (2026-11-12; RC1-docs G7; RUNNING_LOG N183, E157)** | "Exactly ONE distinct value per volume" holds per journal instance, not per volume: `deletejournal` + `createjournal` gives a new id (its creation FILETIME; LAB-J, KNOWLEDGE_INTAKE A10), and files written under the earlier journal keep its id at $SI+0x48 (the LAB-F files carry the old one). `createjournal` over an existing journal keeps the id. |

<a id="e28"></a>
## E28 — $SI+0x58 is a directory child-creation ordinal (NextFileId), not a version/CoW/write counter

| | |
|---|---|
| **Previous (E23)** | $SI+0x58 = u64 "VersionRefCount" — implied a version / copy-on-write / write counter. (E23's structural fact "single u64, upper 32 always 0" stands.) |
| **Correct** | **$SI+0x58 = NextFileId** — a per-directory CHILD-CREATION ORDINAL. The write path `RefsMoveFile` (unified create/rename/link) increments the PARENT directory SCB's NextFileId (SCB+0x1b8 win11 / SCB+0x1a8 insider) and stamps the new child's FCB+0x158 with the assigned ordinal. Each resident child's $SI+0x58 = its assigned ordinal; a directory's own-row $SI+0x58 = NextFileId = max(child ordinal). NOT a per-write/version/CoW counter. |
| **Evidence** | **Decompilation** (E2): `RefsMoveFile` L192932 `*(+0x1b8)+=1`, `RefsCreateFileId2`, `RefsPersistNextFileId` (win11 192932-192961). Read path `RefsComputeStandardInformationFromFcb` reads dir SCB+0x1b8 via FCB+0x148 when version<0x30b/3.11 (L159529; insider L174127). Persist gate: `RefsPersistNextFileId` writes the 8 bytes to dir own-row $SI+0x58 ONLY when version<0x30b (`MsUpdateDataWithRoot ...,0x58`); on ALL versions it persists to the object-record payload (insider 263119/263135/263138). Fresh dir init=1 (win11 140176); self-heal `RefsGetNextFileIdFromObjectTable` reads max child. **Raw disk** (RD): file_resident 100% nonzero ALL versions (max 110001 native v3.14); dir_own/file_own 100% on v3.4-3.10 but 0% on native v3.14/3.15 (tracks the <0x30b persist gate). **Ground truth**: on v3.7/3.9/3.10, dir own-row value ≥ max(resident child ordinal), equal unless a higher child was deleted — 0 violations across 232 dirs; child ordinals near-contiguous from 2 (0/1 reserved). |
| **Note** | Resolves the "VersionRefCount is always 1 on directories" confusion. Reads dir SCB+0x1b8/0x1a8 (NOT VCB+0xf8). On native v3.14 the dir own-row value is 0 because the persist target is the object-record payload, not $SI. |
| **Docs affected** | standard_information.md, structure_reference.md C.7 (line ~841), errata E23 |

<a id="e29"></a>
## E29 — InternalFlags bit5 (0x20) = symlink/junction redirection-trust level, not "HardLinkCount drops to 0"

| | |
|---|---|
| **Previous** | $SI+0x24 InternalFlags bit5 (0x20) interpreted as "HardLinkCount drops to 0". |
| **Correct** | **bit5 (0x20) = the symlink/junction redirection-trust bit** = FCB[0xf4] bit1, derived from `IoComputeRedirectionTrustLevel`. It is NOT the hardlink-zero bit. (The genuine link-count-zero path ORs bit2 (0x04), not 0x20, into $SI+0x24, gated FCB[0xb4]==1 + POSIX-delete; most callers pass 0.) |
| **Evidence** | **Decompilation** (E2): InternalFlags bits0-3 from `RefsComputeStandardInformationInternalFromFcb` (FCB+0x08 bits 27/22/11/31); bits4-5 added by caller via `(FCB[0xf4]<<4)&0x30` (win11 L159547, L157918-157929). FCB[0xf4] written ONLY in `RefsSetReparsePointInternal` for tags 0xa000000c/0xa0000003 (L174306-174404). Link-count-zero path `RefsConvertToStandardInfoLinkCount` ORs constant 0x04 (insider L511461). **Raw disk** (RD): winsider.raw file_own internal_flags=0x20 count = 78 = EXACTLY the 78 reparse points (46 junctions + 32 symlinks). Across 98 v3.14+ images, bit5 present in 47, ALL 47 have a symlink/junction; 0 counterexamples. |
| **Note** | 0x28 = resident symlink, 0x20 = reparse own-row. InternalFlags is 0 on all v3.4-3.10; activates v3.14. |
| **Docs affected** | standard_information.md, structure_reference.md C.7 |

<a id="e30"></a>
## E30 — RETRACTED 2026-06-17: "$SI+0x30 USN, populated resident-only" was the type-0x30 index-entry FileSize

| | |
|---|---|
| **The E30 claim (WRONG)** | "$SI+0x30 = a change-journal byte offset, populated only on resident-file $SI (file_resident 53-99.5% nonzero), 0% on file_own/dir_own." |
| **Why it is wrong** | E30 conflated **two different structures** that `study_all_fields.py` both parsed as "$SI at base 0x28": (a) the type-0x10 **own-row $SI**, whose +0x30 field is **0 on 0 of 32,629 own-rows across the whole corpus** (2026-06-17) — never a populated USN; and (b) the type-0x30 **resident index entry** (FILE_NAME-like), whose value+0x58 is **FileSize**, not a USN. The "resident-only USN, 53-99.5% nonzero" = FileSize present in index entries (nonzero ∝ files with nonzero size), absent in own $SI. **Decisive disk proof:** value+0x58 = the independently-parsed embedded-$DATA size on **409,514/409,514** v3.14 files, **= file size even on USN-inactive images** (win10 v3.4 `arg/bat/bye/fsutil.txt` = 5/5/11/1060 — a USN is 0 with no journal). The decompilation E30 cited (`FCB+0x90 ← StreamSummary+0x10`, win11 L465174) sources a **size/valid-data field**, not a USN — alongside `FCB+0x88 ← +0x08/+0x20` (DataSize, E26); `RefsFileOffsetFromUsn`/`RefsUsnAppendData` are the *real* USN mechanism, tied to **$SI+0x40 (LastUsn)** + the OID-0x520 `$J` journal, not $SI+0x30. |
| **Correct** | The type-0x30 resident index entry carries **FileSize @ value+0x58** and **AllocatedSize @ value+0x60** (§C.2). The type-0x10 $SI's +0x30 ("USN") and +0x38 ("DataSize") fields are **0 across the corpus**. The per-file → journal link is **LastUsn ($SI+0x40) + UsnJournalId ($SI+0x48)** (E27, independently re-confirmed: 14/14 then 480/480 LastUsn→$J-record name matches). |
| **Evidence** | `analysis/tools/analysis_scripts/measure_resident_si.py` + `usn_linkage_proof.py` over 119 images (409,514 resident files / 32,629 own-rows / 10 USN-active); `analysis/reports/deep_si_usn_findings_2026-06-17.md`. R1/S3-class error — a master byte-claim trusted without disk re-measurement. |
| **Docs affected** | structure_reference.md §C.7 (0x30/0x38 rows) + §C.2 (resident value 0x58/0x60/0x68/0x70), standard_information.md, forefst.py + refsanalysis.py (resident-dirent usn), study_all_fields.py (file_resident bucket labels) |
| **Cross-ref** | Same failure mode as R1 (block refcount 2080) and S3 (resident +0x58) — see THESIS_ERRATA.md "Excluded". E26 clarified; E27/E28 unaffected (their offsets 0x40/0x48/0x58 mirror correctly between the two structures). |

<a id="e31"></a>
## E31 — InternalFlags bits 0-3 already present in Win11 RTM (no change; cross-reference E25)

> Subsumed by E25 (Win11 RTM `RefsComputeStandardInformationInternalFromFcb` at 0x1400b7454 already extracts all four FCB flag bits 27/22/11/31). Listed here only so the InternalFlags discussion (E29) has its companion. No new correction. See E25.

<a id="e32"></a>
## E32 — key_flags 0x04 does NOT exist on disk; directories use key_flags 0x02 + dir attribute bit — CORRECTS E15/E17

| | |
|---|---|
| **Previous (E15/E17)** | key_flags value 0x04 = directory. |
| **Correct** | **There is no key_flags 0x04 on disk.** Type-0x30 key_flags is only ever {0x01 = resident, 0x02 = non-resident}. A directory uses key_flags **0x02** (the ordinary non-resident layout) and is identified as a directory by the **directory attribute bit 0x10000000** at value+0x40 — NOT by a distinct key_flags value. |
| **Evidence** | **Raw disk** (RD): full type-0x30 key scan across 3 images → key_flags distribution {1:1235, 2:1240}; ZERO 0x04. Verified {0x01,0x02} only across 111 images. (Directory attribute bit 0x10000000 = the long-standing ReFS dir flag, value+0x40.) |
| **Corrects** | E15 (drop "0x04=directory" from the value list), E17 (thesis "type 2" annotation for a directory is in fact CORRECT). |
| **Docs affected** | errata E15/E17, structure_reference.md C.1, standard_information.md, filename/index docs |

<a id="e33"></a>
## E33 — HardLinkCount ($SI+0x70) is always 1; the "confirmed cross-directory hard links" were a parser artifact — corrects finding #292

| | |
|---|---|
| **Previous (finding #292)** | $SI+0x70 HardLinkCount=1 "despite confirmed cross-directory hard links". |
| **Correct** | **HardLinkCount is always 1; there are NO genuine hard links in the corpus.** The apparent "multi-parent OIDs" were a parser artifact: for a non-resident type-0x30 entry, value+0x08 is the HOME-directory OID back-reference, NOT a child OID. Treating value+0x08 as a child OID makes one directory appear referenced ~40× (every sibling shares the same home-dir OID). The driver DOES support and increment HLC (`RefsMarkHandle`), but no test case exercised it detectably. |
| **Evidence** | **Decompilation/semantics**: for a subdirectory entry value+0x08 = child's own OID (distinct); for a non-resident FILE entry value+0x08 = home/parent-dir OID (shared by all siblings). **Raw disk** (RD): HardLinkCount=1 across the corpus; no reliable hard-link evidence on any image. |
| **Corrects** | findings_register #292 (premise wrong — no confirmed hard links). |
| **Docs affected** | findings_register #292, hardlink/extobjid docs, refsanalysis.py (do not treat non-resident value+0x08 as a child OID) |

> **UPDATE 2026-06-14 (#340 / FN_LINK_002):** Genuine hard links HAVE since been observed (step6/win11refs2gtargeted, `fsutil hardlink list` ground truth). The value+0x08 = home-dir-backref diagnosis above is **CONFIRMED** and is the basis of the decoded link-count mechanism (link count = entries sharing home backref + per-directory child ordinal value+0x00 + content fingerprint). Only the clause "there are NO genuine hard links in the corpus" is superseded. **$SI+0x70 remains the resident-only field (always 1), NOT the multi-name counter.**

> **UPDATE 2026-11-17 (E161):** the last sentence holds for an embedded record only: in a split record's type-0x40 backing $SI+0x70 is the file's link count.

<a id="e34"></a>
## E34 — Attribute type 0xF0 = USN journal $Max metadata, present since v3.4 — corrects findings #173 and #282, resolves open question C3

| | |
|---|---|
| **Previous** | #173: type 0xF0 first appears v3.14. #282: type 0xF0 "never observed". C3: 0xF0 = "$EFS_LOGGED?", never observed. |
| **Correct** | **type 0xF0 = USN journal `$Max` metadata** — a 32-byte NTFS `$UsnJrnl:$Max` structure, carried on OID 0x520's Change Journal file. Created by `RefsSetupUsnJournal`, present **since v3.4** (NOT v3.14-only, NOT EFS). |
| **Evidence** | **Decompilation** (E2): `RefsSetupUsnJournal` builds the journal and writes the $Max metadata. **Raw disk** (RD): 0xF0 sits on OID 0x520 with vlen=44; decoded MaxSize=128 MB (win11refstestmftecmd) / 32 MB (winsider) — both standard USN journal sizes. |
| **Corrects** | findings #173 (not v3.14), #282 (not "never observed"). |
| **Resolves** | open question C3. |
| **Docs affected** | findings_register #173/#282, open_questions.md (C3), usn_journal.md, structure_reference.md |

> **Note (E44):** this erratum is about the type-0xF0 **attribute** (v3.4-era code path). The registered **schema-table entry 0x1F0** is a *separate* object, gated **v3.14+** (disk-confirmed) — do not conflate the two.

<a id="e35"></a>
## E35 — "$CBW4" EFS stream name is a fabrication; the only EFS stream name is "$EFS"

| | |
|---|---|
| **Previous** | A "$CBW4" stream name was attributed to EFS, with "EfsEncryptStream". |
| **Correct** | **"$CBW4" does not exist** — 0 occurrences as a stream name both on disk and in the binary. The 140 "CBW4" hits in the decompilation are mangled C++ template names (`span<$$CBW4byte@utl>` = a checksum `span<4 byte>`), unrelated to EFS. The only EFS stream name is **"$EFS"** (E1 string literal, present in win11/insider). The function is **`RefsEncryptStream`** (not "EfsEncryptStream"). |
| **Evidence** | **E1** string literal "$EFS". **Verification** (grep binaries + UTF-16LE disk scan): $CBW4 utf16le on disk = 0, $EFS = 50; the 140 "CBW4" decomp hits are all `span<$$CBW4byte@utl>` template manglings. |
| **Docs affected** | EFS docs, structure_reference.md, any reference to $CBW4/EfsEncryptStream |

<a id="e36"></a>
## E36 — $SI+0x50 (PackedEaSize, v3.10+) maps to $EA_INFORMATION val[0x0C], not val[0x10]

| | |
|---|---|
| **Previous (E22)** | $SI+0x50 (v3.10+) = PackedEaSize (correct), but documented as sourced from $EA_INFORMATION val[0x10]. |
| **Correct** | The PackedEaSize value equals **$EA_INFORMATION val[0x0C]** — the unpacked / NTFS-packed EA size (= FCB+0xa0). NOT val[0x10]. (E22's v3.4↔v3.10 transition and "PackedEaSize from FCB+0xa0" remain correct; only the on-disk source offset is fixed.) |
| **Evidence** | **Raw disk** (RD, win11refs4gattributes): $SI+0x50 = 45 = $EA_INFORMATION val[0x0C]; val[0x10] = 60 (no match). Verified 3852/3852 on disk. |
| **Docs affected** | standard_information.md (0x50 row), ea / $EA_INFORMATION docs, errata E22 |

<a id="e37"></a>
## E37 — $DATA stream_flags (val+0x38) = checksum-type / integrity selector

| | |
|---|---|
| **Previous** | $DATA stream_flags (val+0x38) variously read as residency or as an Insider-specific field. |
| **Correct** | **val+0x38 = checksum-type / integrity selector.** Low byte: 0x02 = CRC, 0x04 = SHA-256 (mutually exclusive). Bit 0x10000 = integrity-stream flag. Hence 0x10002 = CRC + integrity. It is NOT a residency indicator and NOT Insider-specific. |
| **Evidence** | **Raw disk** (RD) + decompilation: observed combinations match the selector model (0x02 CRC, 0x04 SHA-256, +0x10000 integrity). |
| **Note** | Distinct from the ADS storage_type at hdr+0x0C (0=ADS inline, 2=snapshot extent-based, E20). |
| **Docs affected** | $DATA / data_runs docs, structure_reference.md |
| **Update (2026-11-21, the static readings S4; RUNNING_LOG N654)** | val+0x38 is not one u32 selector but two u16 fields: **+0x38 the table's checksum type** (2 = CRC64, 4 = SHA-256; from SCB+0x102, the table's index root +0x14) and **+0x3A the stream's integrity checksum algorithm**, 0 without integrity (from SCB+0x104, set by `RefsSetIntegrity`; `GetChecksumTypeForStreams` gives 1 = CRC32-C on 4 KiB clusters and 2 = CRC64 otherwise on a CRC64 volume): `RefsCreateDataAttribute` 26100.9444 `refs.decomp.c` :390859-390860, `RefsSetIntegrity` :421951, :69772; 17134 the same layout (:244322-244326). The "bit 0x10000" above is +0x3A = 1 seen through a u32, so 0x10002 = CRC64 table, CRC32-C integrity. Not measured: a 64 KiB CRC64 volume with integrity, where +0x3A would read 2. |
| **Update (2026-11-21, the disk; RUNNING_LOG N657)** | The two fields are the INLINE `$DATA` value's (RefsCreateDataAttribute builds its 0x30-byte summary with SCB+0x102 at +0x2C and SCB+0x104 at +0x2E, which the 12-byte header puts at value+0x38 / +0x3A; the extent form's +0x38 is the stream size). Census over every file the directory walk reaches on the 124 corpus.lst volumes (`analysis/reports/v1.13.2/RC1D/rc3a/disk/data_integrity_census.py`, 735,656 file records): +0x38 = 2 on all inline values of CRC64 and checksum-none volumes, 4 on all 196 of SHA-256 volumes (563,606 of 563,606); +0x3A = 1 on the 3 inline files with attribute 0x8000 (4 KiB, CRC64) and 0 on all 563,603 without. An extent-form file records its integrity in its table's descriptor +0x16 instead (1 on 4,034 of the 4,037 attribute files, the other 3 being the inline ones; 1 without the attribute on 2). No file on a 64 KiB volume of the corpus carries the attribute, so +0x3A = 2 stays unmeasured. |

<a id="e38"></a>
## E38 — $OBJ_LINK v3.4 timestamp divergence is VARIABLE; $DIR_LINK is the same on-disk structure

| | |
|---|---|
| **Previous** | $OBJ_LINK v3.4 timestamps diverge from the directory entry by "~1.5s"; $DIR_LINK treated as a distinct attribute. |
| **Correct** | **Divergence is VARIABLE (0.8 s to >135 s, median ~10 s)**, not ~1.5 s. The CREATION time matches the directory entry EXACTLY (148/148); modify/change/access diverge because the objlink m/ch/a are frozen at OBJECT CREATION while the dir entry tracks later updates (only 11/97 fall in the old 1-2 s band). **$DIR_LINK is the SAME on-disk structure as $OBJ_LINK**, not a separate attribute (type 0x38 v3.4 single-instance / type 0x39 v3.7+ multi-instance marker 0x80000002 sub-type 0x0D). |
| **Evidence** | **Raw disk** (RD): 148-object image — creation exact, m/ch/a gap = time-to-next-metadata-update. **Decompilation** (E2): writer `RefsInitializeObjLinkRow` @14003dd70 (0x39, L54116-54169); v3.4 via `RefsBackpointerValueFromFileName` @140098490 → CreateAttribute(0x38) (L188932-188937); format gated by VCB+0x2ACC (== 0x39 also = hardlinks supported, `RefsHardlinksSupported` L124753). |
| **Docs affected** | OBJ_LINK.md (replace "~1.5s"; note $DIR_LINK == $OBJ_LINK), structure_reference.md |

<a id="e39"></a>
## E39 — $SI+0x74 (v3.7+) = NextStreamSetId allocator (base 0xF000), not "ExternalFileObjectId"

| | |
|---|---|
| **Previous** | $SI+0x74 (v3.7+) labelled "ExternalFileObjectId". |
| **Correct** | **$SI+0x74 = NextStreamSetId** — a per-object stream-set id allocator with base 0xF000. Not an external file/object id. |
| **Evidence** | **Decompilation** (E2) / raw disk: allocator semantics with base 0xF000. |
| **Docs affected** | standard_information.md, structure_reference.md C.7 |

<a id="e40"></a>
## E40 — $I30/$INDEX_ROOT wrapper is version-dependent (payload is constant)

| | |
|---|---|
| **Previous** | $I30/$INDEX_ROOT treated as a single fixed layout across versions. |
| **Correct** | The **config PAYLOAD is byte-constant across versions**, but the **WRAPPER is version-dependent**: v3.4 = 148-byte value / 20-byte key / name "I30" / no marker; v3.7+ = 140-byte value / 24-byte key / marker 0x80000002 / name "$I30". |
| **Evidence** | **Raw disk** (RD): cross-version comparison of the index-root attribute wrapper vs constant payload. |
| **Docs affected** | $I30 / index docs, structure_reference.md |
| **Amendment (2026-11-12; RC1-docs G7 I026; RUNNING_LOG N186)** | The v3.4 name is **"$I30"** too, not "I30": the 20-byte v3.4 key is the u64 value length, the u32 type 0x90 and 8 bytes of UTF-16LE "$I30" at +0x0C (a 3-character "I30" would make the key 18 bytes; the u16 0x0024 the docs called "reserved" at +0x0C is the `$`; the si_group critic's byte read), and 17134's `RefsCreatePrerestartScb` matches an 8-byte name against L"$I30" (17134 decompilation :262041-262043, re-read by the lead). The wrapper's other differences stand (148-byte value, 20-byte key, no marker on v3.4). Corrects `docs/attributes/I30_INDEX.md`. |

<a id="e41"></a>
## E41 — REAFFIRM E20 (ADS always inline); 0x8000001B = APPEXECLINK and the prior _REPARSE_TAGS table was off-by-one/mislabeled

> **CORRECTED 2026-06-12.** The earlier E41 reparse labels were themselves wrong (a mislabeled/off-by-one tag table). Per authoritative Microsoft ntifs.h: **0x8000001B = IO_REPARSE_TAG_APPEXECLINK** (app execution alias — Store app package+target exe), NOT WCI/WOF. **0x80000024 = IO_REPARSE_TAG_LX_FIFO** (WSL named pipe), NOT AF_UNIX (which is 0x80000023). **0x80000017 = WOF** (not NFS), **0x80000018 = WCI**.

| | |
|---|---|
| **Reparse correction** | The container/app reparse tag observed in the corpus is **IO_REPARSE_TAG_APPEXECLINK = 0x8000001B** (app execution alias), NOT WOF/WCI. The whole prior `_REPARSE_TAGS` table was off-by-one / mislabeled — e.g. **0x80000024 = LX_FIFO not AF_UNIX**, **0x80000017 = WOF not NFS**. Corrected to authoritative ntifs.h values. **WOF (0x80000017), WCI (0x80000018), AF_UNIX (0x80000023), and DEDUP (0x80000013) are NOT observed** in the corpus. (refsanalysis.py `_REPARSE_TAGS`/`_decode_reparse_data` were rebuilt to the full authoritative table — flag for maintainer; stdlib-only file.) refs.sys structurally recognizes only symlink 0xA000000C and junction 0xA0000003; all other tags are stored verbatim and handled by minifilters. |
| **ADS reaffirmation** | E20 (ADS always inline) is REAFFIRMED. The verification pass scanned all 159 ADS (storage descriptor 0xB0, SS=0): ALL have stream_flags=0x02 (inline resident). A claimed "non-resident ADS" was REFUTED — the single attr_flags=0x1000 ADS is STILL inline. **attr-flag 0x1000 = "ADS on a file that also has snapshots / a stream-set", NOT non-residency.** |
| **Evidence** | **Raw disk** (RD): APPEXECLINK 0x8000001B = 28 instances on winsider (payload = package+exe path strings); LX_FIFO 0x80000024 = 2 (empty payload, the `lxfifo` file, mode S_IFIFO); MOUNT_POINT 47; SYMLINK 2007. NOT present: WOF 0x80000017, WCI 0x80000018, AF_UNIX 0x80000023, DEDUP 0x80000013, 0x80000025/26, 0xA000001D. All 159 ADS stream_flags=0x02. |
| **Docs affected** | REPARSE_POINT.md, refsanalysis.py `_REPARSE_TAGS`/`_decode_reparse_data` (full table rebuild), structure_reference.md C.8a, findings_register #304, reference_table.csv, errata E20, TOOL_ISSUES.md #2 |

> **UPDATE 2026-06-14 (#341 / FS_REPS_RA_003):** The tag *values* in E41 are correct, but the "NOT observed" status is now outdated: **AF_UNIX (0x80000023), LX_CHR (0x80000025), and LX_BLK (0x80000026) are now OBSERVED** on win11refs2gtargeted (testsocket/testchr/testblk). Only **WOF (0x80000017), WCI (0x80000018), DEDUP (0x80000013), and LX_SYMLINK (0xA000001D)** remain unobserved. Also: **$LXDEV = 8 bytes (u32 major + u32 minor)** — RD-confirmed (testchr 1:3, testblk 7:0) AND static-confirmed (`RefsQueryLxMetadataEa` checks `EaValueLength==8`). The forefst.py `REPARSE_TAGS` table (separate from refsanalysis's) was ALSO corrected on 2026-06-14 (it still mislabeled 0x80000024 as ONEDRIVE and lacked the WSL tags).

<a id="e42"></a>
## E42 — MLog page/record offset 0x04 is a per-volume constant magic, NOT a CRC32

| | |
|---|---|
| **Previous** | MLog page+0x04 documented as **"CRC32 — control page checksum"** (mlog.md control-page table; forefst.py `parse_mlog_control_page` field `"crc32"`; thesis `analysis_application.tex:74` `0x04 & 4 & CRC32 & Control page checksum`; thesis register AP_LGFL_RA_004 lists "CRC" as a record-header field). |
| **Correct** | **page+0x04 is a constant-per-volume format / log-instance magic word** — copied verbatim from the log handle (`handle+0x2fe8`) at record assembly and validated on read by **equality** (never recomputed). It is **identical for every control page AND every data record within a volume** and differs only between volumes (a content-derived CRC32 would differ per record). The **genuine per-record integrity value is an 8-byte XOR-fold (also not a CRC) stored at entry-header+0x08 = page+0x80**, which DOES vary per record. |
| **Evidence** | **E2**: `LogCoreWriteDataRecord` writes `*(param_3+4) = *(handle+0x2fe8)` (no checksum applied); `LogValidateEntryHeader` checks `param_4[1] == *(handle+0x2fe8)` by equality; the real checksum is the XOR-fold loop stored at `record + [record+0x54] + 8`. Confirmed in v3.4/v3.14/Insider (`LogInitializeEntryHeader`: `param_1[1] = handle+0x2fe8`). **RD**: page+0x04 constant within each volume (win11 0x84c1ffcf ×all records, win10 0x998da6fd, win11refs2g 0xc86639e7 ×1328 records) while the entry+0x08 checksums vary per record. |
| **Docs affected** | mlog.md (control-page + record-header tables), forefst.py `parse_mlog_control_page` (`crc32`→`format_magic`), structure_reference.md E.2, findings_register #320, THESIS_ERRATA.md, reference_table.csv AP_LGFL_RA_004 |

> **CORROBORATION 2026-06-14 (#343 / AP_LGFL_RA_008):** A genuine ReFS **reformat** of the same partition gave page+0x04 = **0x6d790647** (original) → **0x5e524606** (reformatted copy), while ~90% of the control-page bytes were identical and the volume serial/GUID also changed — independently confirming a stored per-volume constant, not a content CRC. (The per-volume value differs from the 0x84c1ffcf/0x998da6fd/0xc86639e7 examples above and from the 0x6d6c6f07 quoted in an earlier step6 draft, because it is per-volume; the *mechanism* is invariant.)

<a id="e43"></a>
## E43 — $SI+0x24 internal_flags bit0 is a delete-disposition/EFS state flag, NOT "INTEGRITY" — corrects the bit-mapping label (#261/#305/MD_SI_RA_006)

| | |
|---|---|
| **Previous** | The $SI+0x24 internal_flags bit mapping documented **bit0 (0x01) = "INTEGRITY (FCB bit 27)"** (structure_reference.md C.7 table, findings #261/#305, reference_table.csv MD_SI_RA_006, several SI reports). This invited reading bit0 as the on-disk integrity-stream marker. |
| **Correct** | The decode is right that bit0 ← **FCB+0x08 bit 27**, but the **semantic label "INTEGRITY" is wrong.** FCB bit 27 is a **delete-disposition / EFS transient-state** flag (set in `DeleteDirectoryOnDisk`/`DeleteDirectoryOnDiskLeakingADS`, consulted in `EfsDecryptFile`), which is why it is essentially never set on live files. The **integrity-stream marker is file_attrs bit 0x8000** (FILE_ATTRIBUTE_INTEGRITY_STREAM), set by `RefsSetIntegrity` at **SCB+0x98 bit 15**, reflected to `$SI+0x20` — it is **never** reflected into `$SI+0x24`. |
| **Evidence** | **E2** (win11_4b0558f6 + insider): `RefsSetIntegrity` @1402840a8 `*(SCB+0x98) \|= 0x8000` / `&= 0xffff7fff`; `RefsComputeStandardInformationInternalFromFcb` @1400b7454 builds $SI+0x24 from FCB+0x08 bits only (bit0 ← bit 27), never SCB+0x98; FCB bit 27 set in `DeleteDirectoryOnDisk`. **RD**: across 4 v3.14 integrity images, file_attrs 0x8000 = 100% of integrity files; win11refs2g_setintegritystreams1 has **5953 integrity files, 0** with $SI+0x24 bit0 set; integritytest.txt = attrs 0x8020 (0x8000 set), internal_flags 0x08 (bit0 clear). |
| **Corrects** | findings_register #261 (and the #305 decode label), reference_table.csv MD_SI_RA_006, structure_reference.md C.7 ($SI+0x24 bit0 label). Affirms #342 / MD_INTG_RA_001. |
| **Docs affected** | structure_reference.md C.7 ($SI+0x24), findings_register #261/#305/#342, reference_table.csv MD_SI_RA_006/MD_INTG_RA_001, concepts/standard_information.md, attributes/STANDARD_INFORMATION.md, SI reports, verify_si_fields.py |
| **Update (2026-11-21, RUNNING_LOG N657)** | The count above is not that volume's: `win11refs2g_setintegritystreams1` holds 303 entries (`forefst files`, dev tool): 264 files carry 0x8000, 38 directories carry it, 1 file does not; $SI+0x24 bit 0 is clear on all 264 (261 read 0x0, 3 read 0x20). The conclusion stands; the 5,953 is withdrawn. |

<a id="e44"></a>
## E44 — Schema-table entry 0x1F0 is v3.14+, but the type-0xF0 $Max ATTRIBUTE is v3.4-era — corrects the schema/attribute conflation (resolves)

| | |
|---|---|
| **Previous** | The schema-name table (structure_reference.md F.2, 0x1F0 row) and reference_table.csv `FS_SCHM_RA_007` stated **schema 0x1F0 "present since v3.4 (NOT v3.14+)"**, treating the registered schema entry and the type-0xF0 $Max attribute as one object — and applied E34's "v3.14 floor is a sampling artifact" reasoning to the schema as well as the attribute. |
| **Correct** | They are **two version-decoupled objects.** The registered **schema-table entry 0x1F0** (key-type 0xF0, in `RefsSchemaSet` / Roots #3) is **v3.14+**. The **type-0xF0 $Max attribute** (USN $Max, 0x20-byte body on OID 0x520) is **v3.4-era**, materializing only where the USN journal is active. E34 (attribute = v3.4+) **stands**; only the *schema*-gating "v3.4+" was wrong. |
| **Evidence** | **Raw disk** (decisive): schema-table scan (Roots #3, schema 0xe060) on 11 images — the 0x1F0 key is physically **absent** on all three v3.4 images + v3.7/v3.9/v3.10, and **present** on all v3.14/Insider (appearing as a fixed set with 0x1E0/0x200, independent of USN activity → structural, not sampling). **Static** (E2): v3.4 `InitializeRefsSchemas` (refs_win10 L125720) registers only 0x110–0x1A0 (no 0x1F0); v3.14 RTM (refs_win11 L168943) + Insider (L242111) iterate the 16-record `RefsSchemaSet` array where 0x1F0 is record [11]. The type-0xF0 attribute is created in all three builds by `RefsSetupUsnJournal` (`RefsCreateAttributeWithValue(…,0xf0,…,0x20)` win10 L325273; `CreateAttribute(…,0xf0,…)` win11 L445618). |
| **Corrects** | structure_reference.md F.2 (0x1F0 schema-name row) + B.4 attribute-count footnote; reference_table.csv `FS_SCHM_RA_007`. F.3 matrix (0x1F0 = v3.14+) was already correct. Affirms E34 (attribute v3.4+). |
| **Docs affected** | structure_reference.md (F.2 0x1F0 row, B.4 footnote), reference_table.csv `FS_SCHM_RA_007`, errata E34 (cross-ref) |

<a id="e45"></a>
## E45 — The type-0x30 resident value is an INDEX ENTRY, not a verbatim $SI; per-file USN link = LastUsn/$J (proven) — completes E30 retraction

| | |
|---|---|
| **Context** | Resolves the structural confusion behind E30, S3 and the resident-dirent USN tool bug. The type-0x30 resident directory-entry value and the type-0x10 own-row $SI were both parsed "as $SI at base 0x28", but the type-0x30 value is a **FILE_NAME-like index entry**, distinct from the $SI. |
| **Correct** | The two structures **mirror at every offset except value 0x58/0x60**: the type-0x10 own-row $SI has **USN ($SI+0x30)** and **DataSize ($SI+0x38)** there (both **0 on 0/32,629 own-rows**), while the type-0x30 index entry has **FileSize (value+0x58)** and **AllocatedSize (value+0x60)** (FileSize == embedded-$DATA size on **409,514/409,514** v3.14 files; nonzero even on USN-inactive images). Both structures share LastUsn@0x68, UsnJournalId@0x70, NextFileId@0x80. **There is NO embedded type-0x10 $SI sub-record** in resident files (0/all images; only type-0x80 $DATA + multi-instance attrs). |
| **USN linkage (Part 3, proven)** | The per-file → change-journal link is **LastUsn ($SI+0x40 / value+0x68) = the virtual byte offset of the file's most recent record in `$UsnJrnl:$J`** (OID 0x520), plus **UsnJournalId ($SI+0x48 / value+0x70) = the journal epoch (one per volume)**. End-to-end disk proof (`usn_linkage_proof.py`): win11refs2gtargeted **14/14** files' LastUsn hit an exact $J record offset whose record names that file; win11refstestmftecmd **480/480** of the live ones (the rest wrapped out of the ~900 KB $J sliding window over a ~67 MB virtual USN space). UsnJournalId distinct=1 on every USN-active image; both fields 0 when the journal is inactive (the dissociation that disproves E30). $SI+0x30 is **not** the USN. |
| **Evidence** | `measure_resident_si.py` + `usn_linkage_proof.py` over all 119 images; decompilation `RefsUpdateFcbInfoFromDisk` (FCB+0x90 ← StreamSummary+0x10 = a size field) + `RefsWriteFcbUsnRecordToJournal` (E27). `analysis/reports/deep_si_usn_findings_2026-06-17.md`. |
| **Docs affected** | structure_reference.md §C.2 + §C.7, errata E30 (retracted) / E26 (clarified), forefst.py + refsanalysis.py (resident usn → file_size/LastUsn), study_all_fields.py (file_resident bucket labels), forefst docs (directory_entries.md, standard_information.md). E27/E28 reaffirmed. |

<a id="e46"></a>
## E46 — MSB+ page header 0x40 = Table OID high (always 0), not a "Schema" field; 0x48 = numeric table OID

| | |
|---|---|
| **Context** | structure_reference.md §A.2 labelled page+0x40 "Table OID (high) + Schema (low)" and page+0x48 "Table identifier (low)". The audit-2 re-verify then proposed the opposite ("page+0x40 reserved/zero, OID at 0x48"), and the claim was HELD NEEDS-STATIC. Static analysis resolves it. |
| **Correct** | The MSB+ page identity is a **16-byte `_SmsBigIdentifier`** at page+0x40..0x4F: **page+0x40 = TableIdHigh** (written from identity-object +0x178), **page+0x48 = TableIdLow** (identity +0x180) = the numeric table OID the driver actually uses. `MsInitializeWellKnownObjectId` builds it as **{high=0, low=numericOID}**, so 0x40 is **always 0** in practice but is the OID's high half, **NOT** "reserved" and **NOT** a schema field. The original Prade "0x40-0x50 = table identifier (high+low)" framing (GN_PAGE_007) is **correct**; only the structure_reference "Schema" sub-label was wrong. |
| **Evidence** | **Static (E2)**: `FormatPageHeaderInternal` (win11 @94308-94311) writes page+0x40←id+0x178, page+0x48←id+0x180; `MsInitializeWellKnownObjectId` (win10 @1c00019b8) `{0, OID}`; driver compares **only the low half** (id+0x180 / page+0x48) against table OIDs ==5/==6/1-4 (`OptimizeTablePages` @27563, dispatch @82379); 16-byte OID key (len 0x10). v3.4 + v3.14 identical. **Raw disk**: page+0x40 == 0 on **137,444/137,444** MSB+ pages (113 images, all versions/cluster sizes + SUPB/CHKP); numeric OID at 0x48. (`measure_pagehdr_tablehdr.py`) |
| **Corrects** | structure_reference.md §A.2 (0x40/0x48 rows relabelled), reference_table.csv `GN_PAGE_007` (notes), proof_index_reverified.csv (NEEDS-STATIC → CONFIRMED-STATIC). |
| **Docs affected** | structure_reference.md §A.2 |

<a id="e47"></a>
## E47 — [SUPERSEDED BY E49 — FRAME ERROR] thoff+0x14 is the per-NODE count; Prade's GN_IDXR_004 (Index Root descriptor +0x20) is CORRECT

> **⚠ This erratum was itself wrong (a frame error) and is SUPERSEDED by E49.** It analysed the
> `_SmsIndexHeader` **node** header (thoff = page+0x50+u32@0x50) and concluded Prade's "0x20-0x28 = number of
> rows" was refuted. But Prade's "Index Root" is the `_SmsIndexRoot` **descriptor at page+0x50** (§A.2b), where
> +0x20 = the whole-table row count — **Prade was right.** What this erratum found (thoff+0x14 = a count) is real
> but is the *per-node* count, a different field. The factual sub-statements below about the node header remain
> true; only the conclusion "Prade is wrong / GN_IDXR_004 CONTRADICTED" is retracted. See E49.

| | |
|---|---|
| **Context** | GN_IDXR_004 (Prade p.57) put the "Index Root" row count at **0x20-0x28 (u64)**; the audit-2 re-verify "corrected" it to **root+0x1C (u32)** and was HELD NEEDS-STATIC. This erratum then wrongly refuted **both** by reading the wrong structure (the per-node header at thoff). |
| **Correct (about the node header, still true)** | In the on-disk B+-tree **node** header `_SmsIndexHeader` (start = `page + 0x50 + u32@(page+0x50)`), the **per-node** row/key count is the u32 at header+0x14; header+0x20 is the row-pointer-array END offset; header+0x1C is the high half of the u64 at header+0x18 (the audit-2 "0x1C" misread). **But this is NOT the structure Prade's GN_IDXR_004 describes** — see E49. |
| **Evidence** | **Static (E2)**: `CheckIndexHeaderRecurse` (win11 @111103) requires `(u32@0x20 − u32@0x10) ≥ u32@0x14 * 4`; `InitializeIndexHeader` (@114299) stores 0x14 and 0x24 as **separate u32** and 0x18 as a **u64**; `BinarySearchIndex` (@113007, @79910) bound the search by `u32@0x14`. **Raw disk**: header+0x14 == (array_end − array_start)/4 on **136,425/136,425** pages across 113 images; header+0x1C and header+0x20 never equal the count except by coincidence. (`measure_pagehdr_tablehdr.py`) |
| **Corrects** | structure_reference.md (new §A.2a `_SmsIndexHeader` subtable), reference_table.csv `GN_IDXR_004` (CONTRADICTED, correct offset documented), proof_index_reverified.csv (NEEDS-STATIC → CONTRADICTED). The audit-2 0x1C note is retracted. |
| **Docs affected** | structure_reference.md §A.2a |

<a id="e48"></a>
## E48 — Non-resident snapshots DO exist and use the type-0x40 24-byte extent format — overturns the "UNCONFIRMABLE" re-verify

| | |
|---|---|
| **Context** | MD_SNAP_RA_003 ("non-resident snapshot extents use the same VLCN format as type-0x40 data runs") was marked **UNCONFIRMABLE** by the audit-proofs re-verify, which reported "all ~29 snapshot 0xB0 sub-records are resident/inline (116-byte values), no non-resident snapshot exists." |
| **Correct** | The 0xB0 snapshot **record** is indeed a 116-byte resident sub-record, but the snapshot **content** lives in the linked type-0x80 `$DATA` sub-record (`key+0x10 == data_sub_id`, descriptor 0x10028), and that DATA is **non-resident** whenever its **disk-allocated-size (DATA value+0x48) > 0**. Across the corpus **29 of 30 true snapshots are non-resident**, their content stored via the **identical 24-byte type-0x40 extent format** (VLCN@0x00, flags@0x08=0x180050, file_vcn@0x0C, run@0x14). The re-verify error was reading the *record* residency and never following `data_sub_id` to the DATA record. |
| **Evidence** | **Raw disk (decisive)**: `scan_nonresident_snapshots.py` over 113 images → 29 non-resident true snapshots on 8 images; content byte-exactly recovered — `arg.txt/test2` = `'arg ument 1'` (1 extent), `xbpt_beta_sierra_570651.json/versionmodified` = **3,202,036 B across 8 extents** (header `GFSAREPLAY`, byte-exact), via manual VLCN→PLCN and via `refsanalysis snapshots --show`. **Static (E2)**: snapshot/CoW DATA routes through the **same** extent routine as ordinary file reads, `CmsStream::LookupAllocation` (win11 + insider). |
| **Corrects** | structure_reference.md §C.6 (new "Non-Resident Snapshot DATA" subsection), reference_table.csv `MD_SNAP_RA_003` (NEW → CONFIRMED), proof_index_reverified.csv (UNCONFIRMABLE → CONFIRMED-ALLDISK). |
| **Docs affected** | structure_reference.md §C.6 |

<a id="e49"></a>
## E49 — Prade's Index Root = the `_SmsIndexRoot` descriptor at page+0x50; GN_IDXR_002/003/004 all CONFIRMED (corrects E47's frame error)

| | |
|---|---|
| **Context** | Resolving the held GN_IDXR_002 ("0x0C = schema") and GN_IDXR_003 ("0x18-0x20 = number of extents") revealed that Prade's "Index Root" is a structure the prior passes never analysed: the **`_SmsIndexRoot` descriptor at page+0x50** (Ghidra-typed), present on table-**root** pages, SEPARATE from the per-page `_SmsIndexHeader` node header at `thoff = page+0x50+u32@(page+0x50)`. E47 (and the audit-2 re-verify, and the original task-1 GN_IDXR_004 resolution) all analysed the node header — the wrong frame. |
| **Correct** | In the `_SmsIndexRoot` descriptor (base = page+0x50), all four Prade Index-Root fields are correct: **+0x04 = 0x28 descriptor size (GN_IDXR_001); +0x0C = table SCHEMA id (GN_IDXR_002); +0x18 (u64) = table EXTENT/leaf-page count (GN_IDXR_003); +0x20 (u64) = TOTAL row count of the whole table (GN_IDXR_004).** The per-node `_SmsIndexHeader+0x14` count (the field E47 documented) is a *different* field — equal to the table total only for single-page tables, and equal to the root's child-count on a multi-level tree. |
| **Evidence** | **Static (E2)**: `PrepareWriteRoot` (win10 @1411) casts `(_SmsIndexRoot *)(page+0x50)`; `CreateIndex` (@72940) writes +0x04=0x28 (@73080), +0x0C=schema-id (@73106, from `RegisterSchema` @17820) and validates it (@73234), and on open reads +0x20→`this+0x38` (total rows) and +0x18→`this+0x40` (extents) (@73243-44); `EnqueueTreeUpdate` increments `this+0x38` per row insert; write-back at `CopyStateToTreeUpdateGen…` @82620-82621; `FindIndexHeaderInPage` (@3496) follows +0x00 to the node. `MsGetTableRowAndPageCount`/`MsGetTableInfoFromTable` (win11 @196550/@196519) read rows/pages/schema. **Raw disk (113 images, 34,207 tables, `compare_idxroot_frames.py`/`measure_idxhdr_0c_18.py`)**: desc+0x0C is a valid schema id on **34,203/34,207**; desc+0x20 == an independent full leaf-walk total on **34,177/34,207** (diverging from the per-node count on multi-level trees — e.g. 387 vs 10 children, 245,759 vs 2); desc+0x18 == leaf-page census on every clean multi-level table. |
| **Corrects** | Retracts E47's "GN_IDXR_004 CONTRADICTED / Prade refuted". structure_reference.md: §A.2a reframed as the node header (per-node count), **new §A.2b** documents the `_SmsIndexRoot` descriptor. reference_table.csv: `GN_IDXR_004` CONTRADICTED→**CONFIRMED**, `GN_IDXR_002`/`GN_IDXR_003` →**CONFIRMED**. proof_index_reverified.csv: all three →CONFIRMED-ALLDISK. verify_claim.py: node-count assertion relabelled + new `_SmsIndexRoot+0x20 == total rows` assertion. |
| **Docs affected** | structure_reference.md §A.2a/§A.2b, errata E47 (superseded) |

<a id="e50"></a>
## E50 — Parent-Child schema `u32[7]` is a key-rules selector (not a "bit 3 = value-overlaps-key" flag); the overlap is caller-side

| | |
|---|---|
| **Context** | The registry's only `E3` (inference) claim, `FS_PCTB_RA_001`, hypothesised that Parent-Child Table schema 0xe040's `u32[7]==0x08` meant "bit 3 = value overlaps key." Attempting to upgrade it (E3→E2) refuted it. |
| **Correct** | (1) **`u32[7]` (schema-def byte +0x1C) = the key-comparison-rules selector** — a small enum (disk: 1..0x11), indexing the driver's key-rules dispatch table; `0xe040 → 8 → CmsRulesPARENT_CHILD_LINK`. Not a bitfield; `8 == bit-3` is coincidence. (2) **value-overlaps-key is caller-side**, not schema-gated: `CmsObjectTable::AddParentChildLink` passes the same 32-byte buffer as key and value, and `CmsHashTable::InitializeIndexEntry` sets `value_offset=key_offset` on detecting the pointer overlap. |
| **Evidence** | **Static (E2, win11)**: `RegisterSchema` @83852 (loads `u32[7]`, bounds-checks `<0x15`, indexes `DAT_1401cb370`); `GetKeyRulesInternal` @102170 (21-slot table); `.rdata` system-schema table reproduces disk `u32[7]` exactly (0xe040=8, 0xe0c0=10, 0xe130=17); slot 8 = `CmsRulesPARENT_CHILD_LINK::CompareKeys`; `AddParentChildLink` @232562 (key_ptr==value_ptr); `InitializeIndexEntry` @8710 (sets value_offset=key_offset on overlap). **Raw disk**: `u32[7]` ∈ {1,2,3,6,8,9,10,11,15,16,17} (varied int, not a bit pattern); value-overlaps-key on 238/238 PCT rows and **0** elsewhere; **schema 0x130 has `u32[7]=0x9` (bit 3 set) but its tables do NOT overlap** — decisively refuting "bit 3 = overlap". |
| **Corrects** | reference_table.csv `FS_PCTB_RA_001` (`E3` → `E2+RD`; description's bit-3 hypothesis replaced). structure_reference.md §B.4 (new "schema definition / `u32[7]` = key-rules selector") + §B.5 (value-overlaps-key mechanism). **The registry now has no `E3` row.** |
| **Docs affected** | structure_reference.md §B.4, §B.5 |

<a id="e51"></a>
## E51 — Hard-link grouping must be size-matched (the "content-bearing record" key still over-merged)

| | |
|---|---|
| **Context** | `hard_link_count` (forefst.py / `refsanalysis summary++`) groups a file's names by their physical stream `(owner-dir, file_id)`. `file_id` is the per-directory child ordinal (type-0x30 `value+0x00`), which **collides** — a directory can hold the stream of a *different* file home'd there under the same ordinal. The 2026-06-19 "content-bearing type-0x40 record" key (local `(parent,file_id)` if `alloc>0`, else home) **still over-merged**, because the local content-bearing record at a colliding ordinal is the *other* file's. |
| **Correct** | Resolve by **size match**: a name's content is the candidate stream — local `(parent,file_id)` or home `(home,file_id)` — whose 0x40 size **equals the name's own size** (type-0x30 `value+0x38`). Group names sharing that stream's `(owner, file_id)`. A stub (`size 0`) never matches the name's real size (so resolution follows the home stream), and a same-ordinal different-size stream is excluded. Names matching no candidate are not merged (count 1). |
| **Evidence** | **Disk (independent oracle, each name's own `value+0x38`)**: the prior key fused `xbpt_output_lima` (403,765 B) with `xbpt_record_index` (415,474 B) — distinct files, different home streams — into one group; 5 such groups on `win11refs2g`, 30 on `wininsiderrefs8gtest2`. After size-match: **0 over-merge across 112 images**, fsutil control `{4,2}`, genuine groups preserved (`winsider` 33,104). Independent ground truth (streams with ≥2 size-matched names) = exactly the control's 2 groups and 0 on `win11refs2g`. |
| **Self-deception note** | The "0 mixed across 113 images" validation that blessed the 2026-06-19 key was self-deceiving: `verify_hl_integrity.py` / `verify_claim.py` #12 resolved each member's content through the **same colliding key** the tool grouped by, so over-merged members fetched the identical record and looked consistent. Both gates were re-based on the independent per-name size signal (they now FAIL on the buggy tool, PASS on the fixed one). |
| **Corrects** | forefst.py + refsanalysis.py grouping (size-matched); structure_reference.md §J + §C.3 row 0x00; hard_links.md; verify_claim.py assertion #12 (renamed `assert_hardlink_no_overmerge`); verify_hl_integrity.py. `MD_DATA_RA_006` (alloc=0 stub) STAYS CONFIRMED — both link representations still occur. |
| **Docs affected** | structure_reference.md §J, §C.3; concepts/hard_links.md; examples/read_a_hard_link_group.md |

<a id="e52"></a>
## E52 — §111 page+0x48 parenthetical mislabelled the well-known TableIds (==5 is Block Refcount, not Object Table)

| | |
|---|---|
| **Context** | The §A.2 page-header row for `page+0x48` (TableIdLow, GN_PAGE_007/E46) carried a parenthetical "the numeric table OID the driver compares (==5 Object Table, ==6 Block Refcount, 1–4 system tables)". This was sourced from the 2026-06-18 GN_PAGE_007 analysis and propagated into the audit evidence (`batch1_claims.csv` GN_PAGE_007). |
| **Correct** | The TableIdLow values are the **§A.4 CONFIRMED** TableIds: **Object ID Table = 0x02** (root 0), **Block Refcount = 0x05** (root 6), Schema=0x01, Parent-Child=0x03, ObjID-dup=0x04, Schema-dup=0x06, Container=0x0B/0x0C, …, Small Allocator=0x22; user objects ≥0x500. So `==5` selects **Block Refcount**, not "Object Table"; `==6` is the Schema-Table duplicate, not Block Refcount. The Object Table is `==2`. |
| **Evidence** | **§A.4 (CONFIRMED, all-disk)** root→TableId table: 0=ObjID/0x02, 6=BlockRefcount/0x05. **RD**: the Object-ID-Table root's `page+0x48`=0x02 and Block-RefCount root=0x05 on the 137,444 MSB+ pages re-measured 2026-06-18 (and re-confirmed 2026-06-20 reading every CHKP root's `page+0x48` across the corpus). **Static**: win11 @27563 `if (*(*(p+0x48)+0x180) == 5) goto LAB_14001e5ce` is a Block-Refcount (TableId 5) special-case in `CmsBPlusTable` tree-collapse — consistent with 5=Block Refcount. The driver selects table roots by INDEX (`GetGlobalTableRoot(idx)`), not by this comparison. |
| **Corrects** | structure_reference.md §A.2 (`page+0x48` row parenthetical); audit `batch1_claims.csv` / `proof_index` / `specs.jsonl` GN_PAGE_007 evidence text where it repeats "==5 Object Table/==6 Block Refcount". The MAIN claim (`page+0x48` = numeric TableIdLow, the value forefst reads, 16-byte OID with `page+0x40`) is unchanged and CONFIRMED. |
| **Docs affected** | structure_reference.md §A.2; forefst/docs/audit GN_PAGE_007 machine-data |

<a id="e53"></a>
## E53 — Pre-3.14 schema-table totals omitted the 0x04/0x06 legacy attribute schemas ( was wrong)

| | |
|---|---|
| **Context** | §B.4 "Entry Counts by Version" (and registry `FS_SCHM_RA_011`) gave pre-3.14 schema-table totals **v3.4=25, v3.7=28, v3.9=29, v3.10=28** — "" claimed these "exact and disk-confirmed" with the attribute base **0x110–0x1A0 = 10** and that the v3.4–v3.10 attribute counts "do not rise". Phase-1/D20 (2026-06-18) had separately found 27/30/31/30 and marked the row CONTRADICTED; the two records conflicted. |
| **Correct** | The schema-table leaf-row totals are **v3.4=27, v3.7=30, v3.9=31, v3.10=30, v3.14=29, Insider=30**. The pre-3.14 attribute count includes **two legacy schemas `0x04` and `0x06`** that omitted: they are genuine 80-byte schema definitions (valid `u32[7]` key-rules selector — 0x04→1, 0x06→3 — identical structure to 0x110), present on **every v3.4–v3.10 volume** and **retired at v3.14**. So attribute = 0x04,0x06 + base: v3.4 (10→12), v3.7/v3.9/v3.10 (13→15); v3.14/Insider stay 16 (no 0x04/0x06). The "0x1F0 is v3.14-gated" half of is unaffected and stands. |
| **Evidence** | **All-disk (2026-06-20, 112 ReFS images):** v3.4=27 on **13/13** images (15 sys + 12 attr, 0x04&0x06 on 13/13); v3.7=30 (1/1), v3.9=31 (2/2), v3.10=30 (2/2); 0x04&0x06 present on all v3.4–v3.10, absent on 88/91 fresh v3.14 (the 3 non-29 = insider 30 / upgraded-union 35–36 which retain 0x04/0x06). `refsanalysis schema` itself counts attribute entries as `k < 0xe000`, i.e. includes 0x04/0x06. **Static:** `CmsSchemaTable::InitializePhase2 → InitializeIdSchemaTable` registers the per-version ID-schema set (win10 416 B vs win11 520 B — different sets, consistent with 0x04/0x06 being v3.4-era). |
| **Corrects** | structure_reference.md §B.4 (table + rationale); reference_table.csv `FS_SCHM_RA_011` (×3 copies); forefst docs schema_table.md, version_evolution.md, version_detection.md, volume_info.md. |
| **Docs affected** | §B.4; concepts/version_evolution.md, version_detection.md; structures/schema_table.md, volume_info.md |

<a id="e54"></a>
## E54 — `val[0x38]` in 0xB0 sub-records is NOT a constant 0x02; it is the integrity/checksum-type selector

| | |
|---|---|
| **Context** | §C.6 "Snapshot vs ADS Discrimination" (and concepts/snapshots_versioning.md, resident_storage.md) stated the u32 at `val[0x38]` of every 0xB0 (snapshot/ADS) sub-record "is **always 0x02**" (used to argue it is not a snapshot discriminator). resident_storage.md additionally labeled `val[0x38]=0x02` as an "(inline)" residency marker. |
| **Correct** | `val[0x38]` is **NOT** always 0x02 — it is the stream's **integrity/checksum-type selector**, tracking the volume's checksum configuration: **0x02 on None and CRC64 volumes, 0x04 on SHA-256 volumes** (some CRC64 entries read 0x10002 = bit 16 set). It is volume-wide, so the *conclusion* (not a snapshot-vs-ADS discriminator) stands — but the "always 0x02" premise is refuted, and `val[0x38]` is not a residency marker (residency is set by key_flags 0x01/0x02). |
| **Evidence** | **All-disk (2026-06-20, 112 ReFS images, 985 0xB0 sub-records — all on v3.14 volumes; v3.4–v3.10 have no 0xB0 sub-records in the corpus):** v3.14-None → `2` (73), v3.14-CRC64 → `2` (795) + `0x10002` (59), **v3.14-SHA-256 → `4` (58/58)**. Targeted decode on win11refs2g_sha256checksums + win11refs2t64ksha256: `val[0x38]` bytes = `04 00 00 00` on every 0xB0 entry. The project's own **attributes/SNAPSHOT.md already carried the correct decode** (0x02=CRC, 0x04=SHA-256, bit 0x10000=integrity → 0x10002, `0x00000 on v3.4`) — §C.6 was internally inconsistent with it. |
| **Corrects** | structure_reference.md §C.6 (the "always 0x02" sentence); concepts/snapshots_versioning.md, concepts/resident_storage.md. |
| **Docs affected** | §C.6; concepts/snapshots_versioning.md, resident_storage.md |

<a id="e55"></a>
## E55 — $EFS per-file metadata GUID is at val[0x1c], not val[0x18] (master §789 / MD_EFS_RA_005 were stale)

| | |
|---|---|
| **Context** | §789 (the "$EFS (0x100)" value table) and registry `MD_EFS_RA_005` placed the per-file GUID at **val[0x18]**, labelled "Certificate GUID". The 2026-06-12 EFS precision report (`report_efs_ddf_precision_and_decryptability_2026-06-12.md`) had already corrected this to **0x1c** in `docs/attributes/EFS.md` ("not 0x18, was off by 4") — but the correction was never propagated to the master table or the registry row, so the stale 0x18 sat in the central reference until the 2026-06-25 docs conversion audit compared EFS.md (0x1c) against the master (0x18). |
| **Correct** | The per-file metadata GUID is the **16 bytes at val[0x1c] (0x1c–0x2b)**. val[0x18–0x1b] is a **reserved-zero** u32. The field is **per-file** (unique per encrypted file), not the per-user certificate GUID; it is one of only two per-file-varying regions (the other is the RSA-wrapped FEK at val[0x1a2]). |
| **Evidence** | **Raw-disk byte-diff (2026-06-25):** on `win11refs4gattributes.raw`, the two encrypted files' $EFS values are byte-identical except exactly val[0x1c–0x2b] (16 B, the GUID) and the FEK region. val[0x14]=02000000 (EFS version 2), val[0x18–0x1b]=00000000 (constant), val[0x1c–0x2b] differs per file, val[0x2c–0x4f]=zero. Confirmed on `win11refs4gattributestest2.raw`. A "16-byte GUID at 0x18" is refuted because val[0x28–0x2b] also varies (it is the tail of the 0x1c GUID), and val[0x18–0x1b] is constant zero. **Static:** not applicable — the $EFS metadata blob is built by the EFS subsystem (DDF/FEK) and stored opaquely by ReFS, so refs.sys does not reveal the GUID offset; disk is authoritative. |
| **Corrects** | structure_reference.md §789 ($EFS value table — split 0x18/16 row into 0x18/4 Reserved + 0x1c/16 Per-file metadata GUID + 0x2c/36 Reserved); reference_table.csv `MD_EFS_RA_005` (×2 copies). docs/attributes/EFS.md was already correct (0x1c). |
| **Docs affected** | §789; reference_table.csv MD_EFS_RA_005 (canonical + shipped) |

<a id="e56"></a>
## E56 — Non-resident file_attrs: the type-0x30 POINTER (+0x40) under-reports the EA bit; the authoritative attrs are in the type-0x40 BACKING (+0x48)

| | |
|---|---|
| **Context** | §C.3 ("Non-Resident File Value (Type 0x30, key flags = 0x02)") documents the directory-entry file_attrs at **value+0x40** as a plain `CONFIRMED` "Win32 flags + ReFS extensions", with no caveat. A non-resident file's directory entry is only a **pointer**: its real metadata lives in a separate **type-0x40 backing record** keyed `(owner-dir OID, file_id)` — the file's own `$SI`/stream-summary. Any tool that reads non-resident attributes from the type-0x30 `+0x40` pointer therefore **under-reports** them: forefst's `files`/`summary` did (showed `HasEA=False` on EA-bearing non-resident files), and refsanalysis's `files`/`attributes`/`details` did until 2026-06-30. |
| **Correct** | The type-0x30 `+0x40` file_attrs for a **non-resident** file is an **incomplete copy**. The authoritative file_attrs are at **type-0x40 backing +0x48** (same `$SI` layout as the resident type-0x30 value). The pointer copy **under-reports the EA bit (0x40000)**: it carries EA correctly for many non-resident files but **drops it for a substantial subset** — on winsider the pointer shows EA on 14,207 files while the backing shows it on 22,347, so the pointer **omits EA on 8,140 files and over-reports on 0** (strict unique size-match; ±1 depending on how hard-link ordinal collisions resolve — it never falsely sets EA; the backing is a strict superset). Across all sampled images the **only** attribute bits that ever differ between the pointer (`+0x40`) and the size-matched backing (`+0x48`) are **0x40000 (EA)** and the transient **0x20 (Archive)**. To report HasEA / FileAttributes correctly for non-resident files, read `+0x48` from the backing — or OR its EA bit into the pointer value. (Resident files are unaffected: their `+0x48` $SI attrs are already authoritative.) |
| **Evidence** | **All-disk re-measure (2026-06-30, broad set: win11refs2g/4g-attributes, winsider, 5g-64k, v3.4 64k/specials, 2t-specials, mini, insider-8g):** `XOR(pointer+0x40, size-matched-backing+0x48)` over every non-resident file yields a bit-set of **exactly {0x40000, 0x20}** — 0x40000 on **8,140** files (winsider system files carrying `$CI.CATALOGHINT`/`$KERNEL.PURGE.*` EAs; strict unique size-match, ±1 by collision resolution), 0x20 on **42** files (sporadic, both directions; the Archive count is resolution-sensitive — 42 with a strict UNIQUE size-match, ~50 if the resolver falls back to the first candidate on an ordinal collision, in which case a stray 0x400 reparse bit can also appear on the ~8 collided hard-link names — see E51/§J; the EA finding is unaffected). **E2:** the type-0x40 backing record IS the file's own `$SI`/stream-summary (#327 / `FN_LINK_002`; same layout as the resident type-0x30 value per `MD_SI_SA_001`) — confirmed on disk: `+0x48` attrs, `+0x50` SecurityId, `+0x58` size, `+0x60` allocated, `+0x68` LastUsn, `+0x70` UsnJournalId (volume-constant), `+0x7C` ReparseTag. The 0x20 Archive divergence is a transient "modified-since-backup" flag with **no** systematically-authoritative copy (investigated 2026-06-29; benign, tools display the `+0x40` value). |
| **Corrects** | structure_reference.md §C.3 (annotate the `+0x40` File-attributes row; cross-reference the new type-0x40 backing field map) + §C.8 (non-resident reparse storage); reference_table.csv `MD_ATTR_RA_019` (pointer-omits-EA), `MD_DATA_RA_012` (type-0x40 backing field map), `FS_REPS_RA_004` (non-resident reparse). Tools: forefst fixed 2026-06-29, refsanalysis fixed 2026-06-30. |
| **Docs affected** | §C.3, §C.8; docs/tools/{forefst.md,refsanalysis.md} (HasEA correctness for non-resident files) |

<a id="e57"></a>
## E57 — LX_SYMLINK (0xA000001D) IS produced on ReFS (was recorded DEFINED-NOT-OBSERVED)

| | |
|---|---|
| **Context** | `structure_reference` §C.8 (Subtable C.8a + prose) and `reference_table` `FS_REPS_RA_003` / `MD_ATTR_RA_010` recorded `IO_REPARSE_TAG_LX_SYMLINK` (0xA000001D) as **DEFINED-NOT-OBSERVED**, because on `win11refs2gtargeted` (2026-06-14) WSL `ln -s` on a DrvFs `-o metadata` mount produced a **Windows** SYMLINK (0xA000000C) instead. The tag was believed unproducible on ReFS. |
| **Correct** | LX_SYMLINK **is** producible on ReFS. WSL writes a **Windows** symlink (0xA000000C) when the target is representable as a Windows path (a relative name that resolves), and a **Linux** LX_SYMLINK (0xA000001D) when it is not — an **absolute Linux path** (`ln -s /etc/passwd`) or an **ext4 symlink copied with `cp -a`**. LXSS payload layout: after the 8-byte `REPARSE_DATA_BUFFER` header, `u32 version (=2)` then the **UTF-8 target with no NUL**; the target starts at **buffer+0x0C**, and `ReparseDataLength = 4 + len(target)`. |
| **Evidence** | **RD 2026-07-03, `win11refs8g.raw` (step6, "somenewtests"):** `m2_lxsym_abs` (`ln -s /etc/passwd`) raw buffer `1d0000a0 0f000000 02000000 /etc/passwd`; `m3_lxsym_cp` (`cp -a` of an ext4 symlink) `1d0000a0 11000000 02000000 /etc/hostname` — both tag 0xA000001D, `version`=2, target at +0x0C, `datalen = 4 + len(target)` exactly (15, 17). `m1_lxsym` (`ln -s targetfile.txt`, relative) = Windows SYMLINK 0xA000000C. Independently raw-byte decoded and adversarially re-verified (report `analysis/reports/step6_validation_2026-07-03.md`). forefst decodes both targets correctly (confirms review E5's `+8→+12` tool fix on disk — the first on-disk LX_SYMLINK in the corpus). |
| **Corrects** | structure_reference.md §C.8 (Subtable C.8a LX_SYMLINK row → OBSERVED; the "remains unobserved" prose); reference_table.csv `FS_REPS_RA_003`, `MD_ATTR_RA_010`; docs/concepts/wsl_metadata.md ("The symlink exception"). |
| **Docs affected** | §C.8; concepts/wsl_metadata.md |

<a id="e58"></a>
## E58 — ReFS USN journal is record-version 2/3 only; V4 (range tracking) is NTFS-only

| | |
|---|---|
| **Context** | forefst's USN parser accepted record major versions **2–4** and decoded every record with the V3 field layout (review E6's concern: a V4 `USN_RECORD_V4` / range-tracking record has no timestamp at 0x30, so decoding it as V3 would fabricate fields). It was unknown whether ReFS ever emits V4. |
| **Correct** | **ReFS does not support USN range tracking.** `fsutil usn enablerangetracking R:` on a ReFS volume returns **"A local NTFS volume is required for this operation."** ReFS USN journals therefore contain **only V2/V3** records; `USN_RECORD_V4` (range-tracking `USN_RECORD_EXTENT`) **cannot occur** on ReFS, so review E6's misparse scenario is **moot on ReFS**. A ReFS-scoped tool should accept only V2/V3 and treat a V4 record as anomalous (non-ReFS journal / corruption), not silently decode it as V3. |
| **Evidence** | **RD 2026-07-03, `win11refs8g.raw`:** `fsutil usn queryjournal` reports `Maximum record version supported : 3` even after `enablerangetracking` was attempted; an exhaustive independent scan of the on-disk journal (3644 records across both physical extents, aligned + dword- + byte-unaligned brute force) gives major-version histogram `{3: 3644}` — 0 V4. **User-confirmed:** `fsutil.exe usn enablerangetracking R:` → "A local NTFS volume is required for this operation." |
| **Corrects** | Resolves review E6 as **moot-on-ReFS**. Tool: forefst `parse_usn_records` now accepts V2/V3 and skips/notes a V4 record (forefstdev). |
| **Docs affected** | docs/structures/usn_journal.md; forefst USN-parser comment |
| **Amendment (2026-11-12; RC1-docs G7; RUNNING_LOG N183, E157)** | "Only V2/V3 records": no V2 record was ever observed on ReFS (every record read is major version 3), and the driver rejects a major version below 3, so a ReFS journal holds V3 records. The Tool line describes the behaviour before 1.13.0: the parser decodes with the V3 offsets and tolerates a stray V2 or V4 record with a one-time note (`docs/structures/usn_journal.md`, the record layout). |

<a id="e59"></a>
## E59 — Hard-link names carry PER-NAME, independently-settable MACB (a ReFS-only timestomp cross-check); corrects the "one timestamp set, no $SI-vs-$FN analogue" framing

| | |
|---|---|
| **Context** | Multiple docs + `findings_register.md #335` state that ReFS "keeps only one timestamp set per file" and therefore "the NTFS $SI-vs-$FILE_NAME timestomp cross-check does not exist on ReFS." That is correct for a single-named file, but **wrong/incomplete for hard-linked files**. |
| **Correct** | On ReFS, `$SI` MACB is stored **per name entry (per hard link)**, not per inode as on NTFS (where all hard links share one `$STANDARD_INFORMATION`). Each of a file's names is an independent **type-0x30** row carrying its own four FILETIMEs at value **+0x10 (Created) / +0x18 (Modified) / +0x20 (Changed) / +0x28 (Accessed)**. A **name-scoped `SetFileTime`** (e.g. `Get-Item <one path>` then set `CreationTimeUtc`) rewrites **only the opened name's** row **and the shared type-0x40 backing** — sibling hard-link names keep the **true birth**. Comparing MACB **across a file's names** therefore localises a per-name timestomp, and the **latest** Created among the siblings is the authentic birth. This is a **journal-independent** cross-check (works when `$UsnJrnl:$J` is wrapped/absent) and is **stronger** than NTFS's `$SI`-vs-`$FN` (NTFS hard links cannot diverge — they share one `$SI`). The shared **type-0x40 backing** MACB (resident layout, value +0x28/+0x30/+0x38/+0x40) tracks the **stomped** value, so backing-vs-clean-sibling also diverges. |
| **Evidence** | **RD 2026-07-03, `win11refs8g.raw` (step6), File ID 0x1e (home dir 0x746):** two hard-link names of one file — `f6.bin` and `f6_link.bin` (HardLinkCount 2, shared type-0x40 backing). After `Get-Item R:\blabla\f6.bin; $i.CreationTimeUtc='2011-01-01Z'; $i.LastWriteTimeUtc='2011-01-02Z'`, the on-disk type-0x30 rows read: `f6.bin` Created **0x01cba946d534c000 = 2011-01-01**, Modified 2011-01-02; `f6_link.bin` Created **0x01dd0b1d102d451c = 2026-07-03 18:52:14** (the true birth). The shared type-0x40 backing (value+0x28) = **2011-01-01** (matches the stomped name, not the clean sibling). USN journal corroborates (FILE_CREATE @ 2026-07-03 20:52:14 local); the divergence is decodable **without** the journal. Byte-level probe + adversarial re-verify, report `analysis/reports/f5f6_validation_2026-07-03.md`. forefst `timestomp` now emits a `HARDLINK_MACB_MISMATCH` signal (flags only the backdated name, never the clean sibling). |
| **Corrects** | `findings_register.md #335` (scope: true for single-name files; a multi-name file has N independent name-entry MACB copies that can diverge); the "one timestamp set / no cross-check" prose in `concepts/timestomp_detection.md`, `concepts/ntfs_comparison.md`, `concepts/artifact_timeline.md`, `concepts/forensic_analysis_workflow.md`, `concepts/README.md`, `attributes/STANDARD_INFORMATION.md`; adds the per-name-MACB fact to `concepts/hard_links.md` and `examples/read_a_hard_link_group.md`. New reference finding `FN_LINK_003`. |
| **Docs affected** | structure_reference.md §C.3 / §J; the 6 concept/attribute pages above; hard_links.md; read_a_hard_link_group.md |

<a id="e60"></a>
## E60 — Suppress false inline content from a DEGENERATE ADS (`storage_type==0` but `alloc_size != stream_size`); this does NOT overturn E20/E41 (there are 0 genuinely extent-backed ADS)

> **SCOPE CORRECTED 2026-07-05 (do not repeat the E20-retraction mistake).** An initial draft called `adstest` an "extent-backed named stream, recoverable via the extent path." **That is wrong** — re-verified on disk: `adstest` has NO committed data extent, and E20/E41 ("ADS are always inline") still HOLDS. The *code fix* (don't emit descriptor tail as content) is correct and unchanged; only the characterisation is corrected here.

| | |
|---|---|
| **Context** | `_parse_ads_from_value` treated `storage_type (hdr+0x0C) == 0` as sufficient proof that an ADS is inline, reading content from the inline window at `hdr+0x38`. That is correct for every genuine ADS (E20/E41), but on one image a **degenerate** named-stream entry with `storage_type==0` caused 30 bytes of **descriptor tail** to be returned as if they were the stream. |
| **Correct** | Only claim inline content when **`alloc_size (hdr+0x14) == stream_size (hdr+0x1C)`** — a genuinely-inline ADS stores its bytes packed exactly. **This does NOT mean the `alloc!=size` case is "extent-backed":** re-verification shows the offending entry has **no data extent at all**. The guard simply refuses to emit non-content bytes. **ADS (0xB0)-specific:** a `$DATA` (0x80) MAIN stream legitimately rounds `alloc_size` up (e.g. size 174 / alloc 176), so the check must **NOT** be applied to `get_resident_data_content` — doing so rejects **221,442 of 255,475** genuine inline resident files (221,272 with real content). |
| **Evidence** | **RD 2026-07-04/05, `win11refs2tsnapshots.raw` (step3), `testsnapshots/testads.txt:adstest`:** the 0xB0 row is a real ADS (`_is_snapshot_value=False`, `storage_type=0`), `stream_size=30`, `alloc_size=4096`, **`data_sub_id (val+0x44) = 0x1000`** — which is the file's **MAIN `$DATA` stream** (12 B `datastream`, `disk_alloc=0`, **no extents**). So adstest has no data holder of its own and no committed extent. The real 30-byte payload `adsteststreamnotsupervisible\r\n` was found at raw `0x98c7560` — but that cluster **starts with `MLog`** (it is a durable-log page): the payload is a **journaled copy of the write**, NOT a data extent. **Corpus scan (85 images, 878 non-snapshot ADS): 0 have an extent-backed data holder** (every ADS's `data_sub_id` holder has `disk_alloc==0` / no extents) — E20/E41 reaffirmed. The ONLY `alloc!=size` ADS is `adstest` (1-for-1 with the only wrong-content row). Fix scope surgical: prod→dev diff = exactly 1 ADS (adstest inline→non-inline), 877 byte-identical; genuine ADS `hidden_7357`/`hidden_1514` still decode `"Replayed ADS at …Z"`. Anti-regression assertion added (`verify_claim.py --regress`, 15/15). |
| **Corrects** | `forefst.py` `_parse_ads_from_value` (added the `alloc==size` inline guard + honest label "non-inline (alloc!=size — content not in the record)"); does NOT change `get_resident_data_content`. ADS remain fully DETECTED (name/count unaffected). **Does NOT modify E20/E41/MD_SNAP_RA_007** — "ADS always inline" holds; `adstest` is a degenerate entry whose content is journaled-only (MLog), not a genuine extent-backed ADS. |
| **Docs affected** | none of the "ADS always inline" prose changes; `tools/forefst.md` export-ads note only |

> **SUPERSEDED IN PART by E61 (2026-07-05).** This banner's claim that `adstest` is "degenerate / journaled-only (MLog), NOT a genuine extent-backed ADS" is **WRONG** — the round-6 investigation missed the **type-0x0** extent sub-record (it only searched type-0x80 holders). `adstest` IS extent-backed: its 30 bytes live in 1 committed extent (`vlcn 108101828`), read byte-exact as `adsteststreamnotsupervisible\r\n`. The MLog page at 0x98c7560 was an *additional* journaled copy, not the only copy. The E60 CODE guard (`alloc==size` for inline) is still correct and retained, but the extent path (E61) now recovers `adstest` and every large ADS. See E61.

<a id="e61"></a>
## E61 — LARGE ADS (>= 2 KB) ARE EXTENT-BACKED via a type-0x0 sub-record; scopes E20/E41 "ADS always inline" to below the ~2 KB RefsConvertToNonResident threshold

| | |
|---|---|
| **Context** | E20/E41/MD_SNAP_RA_005-007 state "ADS are ALWAYS inline/resident," noting `RefsConvertToNonResident` accepts type 0xB0 but that "the ~2 KB threshold is never reached by an ADS." That was an EMPIRICAL corpus finding — every ADS ever measured was < 2 KB (7-47 B). A deliberately-large ADS reaches the threshold and IS promoted to non-resident. |
| **Correct** | An ADS whose content is **>= 2048 bytes** is stored NON-RESIDENT (extent-backed). It stays an ADS (`value+0x10 == 0`, not a snapshot), gains `value+0x02` bit 0x1000 (stream-set member), and its descriptor collapses to a fixed 116-byte record with **no inline content** (`value+0x04 == 0x68`). Its **extent list lives in a separate type-0x0 sub-record** (key type 0x00, key_len 80) of the SAME resident type-0x30 value — NOT in the 0xB0 descriptor, NOT in a type-0x80 holder, NOT via `data_sub_id` (which aliases the inline main stream 0x1000). That type-0x0 record uses the STANDARD extent-holder layout (`ihdr=le32(v,0)`; `extent_count=le32(v,ihdr+0x14)`; 24-byte type-0x40 extents at `v[ihdr+0x28]`: `vlcn u64@+0x00`, `file_vcn u32@+0x0C`, `run_length u32@+0x14`; `stream_size=le64(v,0x38)`). The link ADS->extent-record is by **stream_size** (0xB0 `value+0x20` == type-0x0 `value+0x38`); both appear in the same order (positional tie-break). Reconstruct: sort by file_vcn, VLCN->PLCN (Container Table), read, trim to stream_size. **This is the same mechanism a `refsutil streamsnapshot` stream uses** — `adstest` (30 B) is exactly this (a snapshot-created stream with `value+0x10==0`, 1 extent). |
| **Evidence** | **RD 2026-07-05, `win11refs8g.raw` (v2 corpus, `generate_validation_corpus_v2.ps1`): 161/161 extent-backed ADS reconstructed BYTE-EXACT** vs their deterministic markers (128-file size sweep 2 KB..2 MB + 33 multi-ADS). Threshold pinned: `host_014` (1920 B) inline (value_len 1980 = content+60); `host_015` (2048 B) extent-backed (value_len 116). Multi-ADS file: 5 ADS of distinct sizes each linked by stream_size, 5/5 byte-exact. `adstest` on win11refs2tsnapshots: 30-B extent (`vlcn 108101828`) -> `adsteststreamnotsupervisible\r\n`. Report `analysis/reports/ads_snapshot_knowledge_and_impact_2026-07-05.md`. |
| **Corrects** | **E20/E41/MD_SNAP_RA_005/006/007**: add SCOPE — "ADS always inline" holds only **below ~2 KB**; a larger ADS is extent-backed. Do NOT retract their LOCAL findings (the 7/28 extent entries really were snapshots; `attr-flag 0x1000` really is stream-set membership). **FS_SNAP_RA_001** (`val[0x04]=0x68 = snapshot`): 0x68 means "non-inline 0xB0 record" (snapshot OR large ADS), not "snapshot" — demote to a proxy behind `value+0x10` (0=ADS/2=snapshot) + `value+0x02` bit 0x0400 (HasSnapshot). **`structure_reference.md` §2079 "ADS Size Limit"** (ceiling = single-page row capacity): wrong — the ceiling is the ~2 KB conversion threshold, above which content spills to extents. `forefst.py`: `_parse_ads_from_value` now returns `storage="extent-backed"` + `extents`; `cmd_extract` reads them via `_read_vlcn_extents`; NEW `_stream_extent_records`. New regress assertion `assert_extent_backed_ads` (16/16). |
| **Docs affected** | `attributes/NAMED_DATA.md` (§Residency "always inline"), `concepts/resident_storage.md`, `concepts/ntfs_comparison.md` ("always resident regardless of size"), `concepts/cluster_page_size.md`, `glossary.md`; `findings_register.md` #119/#192/#305 are FROZEN -> annotate via this erratum. website/content is GENERATED -> fix docs upstream. |

<a id="e62"></a>
## E62 — CoW-shared stream snapshots recover only PARTIAL content (own extents), not the full version

| | |
|---|---|
| **Context** | MD_SNAP_RA_003/E48 established non-resident snapshots recover byte-exact via type-0x40 extents (29/30 on the old corpus, all COMPLETE snapshots). New v2 snapshots created on a file MODIFIED after snapshotting expose the CoW-shared case. |
| **Correct** | A snapshot of a stream that was later modified is **CoW-shared**: its own type-0x80 holder carries extents ONLY for the region that diverged from the base; the unchanged region is shared with the base/current version. `recover_snapshot_streams` reads a snapshot's OWN extents, so for a CoW-shared snapshot it returns `len(content) < stream_size` (correct, but partial). Recovering the FULL version requires MERGING the shared base extents for the unchanged regions — a separate, unimplemented feature. |
| **Evidence** | RD 2026-07-05 `win11refs8g.raw` v2: `snapfile_02.txt` v1 (8192 B, 2 extents) recovers complete; v2 (10792 B) recovers 4096 B (1 own extent); v3 (13392 B) recovers 8192 B — the shares grow with the file. 9/21 non-resident snapshots recover complete, 12/21 partial (all CoW-shared). |
| **Corrects** | `verify_claim.py assert_nonresident_snapshot_type40` scoped: verify extents READ cleanly (0 < len <= stream_size), not completeness (== stream_size) which CoW-shared partials legitimately fail. Adds the CoW-shared caveat to MD_SNAP_RA_003. |
| **Docs affected** | `attributes/DATA.md`/snapshot pages: note CoW-shared snapshots recover the changed region only. |

<a id="e63"></a>
## E63 — "$PAGE" is NOT a ReFS attribute; it is a misread PE linker section name (a second $CBW4, cf. E35)

| | |
|---|---|
| **Previous** | `$PAGE` was catalogued as a "new Win11/Insider attribute" (boot-volume / paging metadata) — listed in `MD_ATTR_SA_001` ("8 new Win11 attributes … $PAGE"), `refs_essentials.md`, `new_knowledge.md` (AT-001), `refs_analysis_notes.md` (A-005), `refs_manual.md`, `how_refs_works.md`, and given its own doc `attributes/PAGE.md`. |
| **Correct** | **`$PAGE` does not exist as a ReFS attribute.** Its ONLY occurrence in any refs.sys binary is inside the string **`.rdata$PAGE$lp00SPGO`** — an **MSVC PE linker COMDAT section name** (`.rdata$PAGE` = the pageable read-only-data section). The string catalog scraped that section name and misfiled it under `attribute_names`, exactly as `$CBW4` was misfiled from the C++ template mangling `span<$$CBW4byte@utl>` (E35). |
| **Evidence** | **Binary scan (2026-07-05, all four builds refs_win10/refs_win11/win11_latest/insider):** bare `$PAGE` as a UTF-16LE attribute string = **0** in every binary (a real attribute IS a UTF-16LE literal: `$SNAPSHOT`=1, `$OBJ_LINK`=1, `$REPARSE_POINT`=2, … ; 16 genuine string-literal attributes present). The only `$PAGE` byte-sequence is the ASCII section name `.rdata$PAGE` (present in win11/insider, absent in win10 — a build/section artifact, not an on-disk attribute). The whole MSVC section-grouping family is present (`.rdata$voltmd`, `.rdata$zETW1/2`, `.text$lp00SPGO`, `PAGE$x/$zy/$zz`). **No schema ID, no type code, no Schema-Table entry, no on-disk layout** (already admitted by `PAGE.md`; `$PAGE` is NOT among the v3.14 schema slots 0x1E0/0x1F0/0x200). **No driver attribute registration.** Contrast $LXUID/$LXGID/$LXMOD/$LXDEV: also 0 UTF-16LE strings, but GENUINE — present **on disk as WSL EA names** (4/8-byte EA values on WSL volumes). $PAGE has NO such on-disk presence (data-gated / never observed). |
| **Corrects** | `MD_ATTR_SA_001` (×3 reference_table copies): "8 new Win11 … $PAGE. Total 17->25" -> **7 new**, drop $PAGE, **Total 17->24**. Intelligence files `refs_essentials.md` / `new_knowledge.md` (AT-001, "25 in Win11 / 24 E1-confirmed" -> **24 / 23**, drop $PAGE) / `refs_analysis_notes.md` (A-005) / `refs_manual.md` / `how_refs_works.md`: remove $PAGE from the attribute list. `attributes/PAGE.md`: mark $PAGE a **non-attribute** (misread section name), keep only as a cautionary note. `concepts/architecture.md`: drop $PAGE from the v3.14 attribute list. Like $CBW4/E35, $PAGE was never a genuine E1 string, so E8's union total (26 E1-string types + $EA = 27) is **unchanged** — $PAGE was never among the 26. (Note kept separate: the "new Win11" list mis-dates $OBJ_LINK (v3.4) and $SNAPSHOT (v3.7); that is a distinct issue, not corrected here.) |
| **Docs affected** | `attributes/PAGE.md`, `attributes/README.md` (attribute list), `concepts/architecture.md`; intelligence files above; `MD_ATTR_SA_001` ×3. `findings_register` GN_INS_SA_001/MD_ATTR_SA_001 references to $PAGE are FROZEN -> annotate via this erratum. website/content is GENERATED -> rebuild after fixing docs. |


<a id="e64"></a>
## E64 — Deleted-file recovery is IDENTITY-BASED with TWO MODES and MORE than three methods (corrects §I "Three recovery methods", FS_DEL_RA_001/004/005)

| | |
|---|---|
| **Previous** | `structure_reference.md §I` opened "**Three recovery methods**" (Trash / checkpoint-diff / orphan-object) and omitted the B+-tree node-slack method (FS_DEL_RA_005) and the two-mode command surface. `FS_DEL_RA_001` listed "Recovery: (1) Trash Table scan (2) checkpoint comparison (3) orphaned MSB+ page scan" (same three-method omission). `FS_DEL_RA_004` gave an efficiency gradient "Trash (1 read) < checkpoint diff (2 traversals) < orphan scan (full volume)" that omitted live-page slack. `FS_DEL_RA_005` said deleted-vs-prior was a **global name** test and "no current tool method gets them" (the orphan-page slack path). §I.1 said "Files may remain in this table" without the resident-bypass caveat. |
| **Correct** | The `deleted` command has **two modes** — *recovery* (default: Trash + checkpoint-diff + LIVE-page B+-tree node slack) and *`--full`* (adds a bounded ORPHAN-page slack scan + carve). Deleted-vs-still-present is decided by **file IDENTITY (name + creation-time)**, not by name alone or by owning directory: a remnant is DELETED iff no live file with that identity exists anywhere; else it is a still-present CoW prior version or a neutral *former location* of a moved/renamed file (creation-time is immutable across move/rename). Identical files deleted from several dirs are recovered once, all locations logged. **Resident files bypass the Trash** (`RefsDeleteResidentDataScbAndCommit`); only non-resident files + directories are reparented (FS_DEL_RA_001). A `deleted --orphans` opt-in low-confidence tier surfaces identity-filtered Object-Table orphans. |
| **Evidence** | RD 2026-08-01, whole corpus (`analysis/reports/improved_recovery_validation_2026-08-01.md`, `orphan_tier_build_2026-08-01.md`): identity classifier = **0 live-matching slack rows** on 4 USN images (162/380/23386/441), a strict improvement over the shipped owner-aware test (7 live files shown deleted on win11refs8g → 0); all-image sweep **113 OK / 0 issues / 119** both modes (recovery ⊆ full everywhere); `--orphans` sweep 113 OK / 0 crash. USN/MLog corroborate deletions (27/44/215/47) and moves-as-RENAME (3/24/9/9). E2: `CmsBPlusTable::DeleteFromIndex` (slot-only delete), `RefsDeleteFile→MsReparentFileToTrash→CmsTrashTable::AddFileTable`, `RefsDeleteResidentDataScbAndCommit` (resident bypass). |
| **Corrects** | `structure_reference.md §I` heading → "Deleted-File Recovery (identity-based)"; three→two-mode/five-subsection layout (I.1 Trash + resident-bypass, I.2 checkpoint-diff + FS_CHKP_RA_014, I.3 B+-tree node slack = primary/FS_DEL_RA_005, I.4 orphan-object opt-in tier, I.5 prior-state CoW). `reference_table.csv`: `FS_DEL_RA_001` recovery clause (+ slack, + resident-bypass, + two modes), `FS_DEL_RA_004` gradient (+ live-page slack below orphan-page slack), `FS_DEL_RA_005` (drop "no current tool method gets them"; identity-based, two modes, recover-once/log-all, `export deleted DIR`). |
| **Docs affected** | `concepts/deletion_recovery.md`, `tools/forefst.md`, `examples/find_a_deleted_file.md`, `concepts/forensic_analysis_workflow.md`, `concepts/what_survives.md`, `structures/trash_table.md` (intro self-contradiction), website mirror. `findings_register` #334 is FROZEN → annotated by this erratum. Additional identity techniques (journal-identity, Parent-Child ancestry) are analysed + document-only (`deleted_journal_parentchild_analysis_2026-08-01.md`). |


<a id="e65"></a>
## E65 — Inline extent record with VLCN==0 is a SPARSE HOLE (zero-fill), not a readable extent (refines §C.6 / adds MD_DATA_RA_014)

| | |
|---|---|
| **Previous** | `§C.6` described the inline / snapshot extent records as "the **identical 24-byte format** as ordinary type-0x40 file data runs … Standard Container-Table **VLCN→PLCN resolution recovers the content**", with no exception for `VLCN==0`. Accordingly `forefst` reassembly (`_recover_inline_extent_content`) and carve (`_carve_extent_backed`) read **every** extent via `VLCN→PLCN`, so a `VLCN==0` record resolved to **PLCN 0** and the ReFS **boot sector** was read into the recovered/carved file at that cluster. |
| **Correct** | An inline extent record with **`VLCN==0` is a SPARSE HOLE**: its `run_length` clusters are **zero-filled and never read** — `VLCN 0 → PLCN 0` is the ReFS boot region on **every** volume, so cluster 0 is never file data (the ReFS analog of NTFS's LCN-0 sparse runs). The sentinel carries flags **bit 0x20** (observed `0x180060` at a file's first cluster, `0x180064` at interior clusters); `file_vcn` = hole start, `run_length` = hole length. |
| **Evidence** | RD 2026-08-05 (`analysis/tools/analysis_scripts/sparse_extent_sweep.py`; `analysis/reports/_runlogs/snapshot_sparse_fix_HANDOFF_2026-08-05.md`): **213** `VLCN==0` records corpus-wide, **0 in snapshot holders** (all current-stream `sub_id 0x1000`). `zero.bin` ext0 `(fvcn=0, vlcn=0, run=1, flags=0x180060)` — reading VLCN 0 yields `…ReFS…FSRS…` **boot bytes** while the file is zeros; fixed reassembly zero-fills cluster 0 (no boot leak, verified: `ReFS` magic absent). The old carve leaked the boot sector into **29** deleted-file recoveries on an integrity image (`win11refstestmftecmd`); now zero-filled. Regression-safe: decoder-level **0 DANGER / 0 snapshot divergence over 37,898 holders**; `export snapshots` byte-identical dev vs pub (10 files incl. an 8-extent snapshot). |
| **Corrects** | `structure_reference.md §C.6` (adds the sparse-hole exception + refines the "VLCN→PLCN recovers content" clause) and `§C.4a` subtable (new `0x180060`/`0x180064` sparse-hole row); `reference_table.csv` **MD_DATA_RA_014** (new). Tool: `forefst.py` `_decode_inline_extents` keeps `VLCN==0` as a hole and `_recover_inline_extent_content`/`_carve_extent_backed` zero-fill it (never read PLCN 0); `refsanalysis.py` delegates all extent/snapshot/extract work to `forefst` (no separate decoder — it skips 0x10028 holders). |
| **Docs affected** | concepts covering data extents / `extract` / deletion-recovery (extract now handles inline-extent non-resident files incl. sparse); `changelog` v1.3.0. Website mirror rebuilt after `docs` sync. |


<a id="e66"></a>
## E66 — FileId `(dir-OID, ordinal)` is monotonic and NEVER reused after deletion (confirms §C.13a; disambiguates §C.3a "reused per directory")

| | |
|---|---|
| **Previous** | §C.13a and the NTFS-vs-ReFS table asserted the FileId lower-8-bytes ordinal is "monotonically increasing, never reused" as **NEW** (stated, not yet proven). §C.3a described the child ordinal as "**reused per directory** and collides across sibling dirs", which — read literally — could be taken to mean the ordinal is recycled **within** a directory after a deletion (it is not; the phrase meant per-directory *scoping* / cross-directory value collision). |
| **Correct** | The per-directory FileId ordinal (`$SI+0x58` NextFileId; = lower 8 bytes of the 128-bit USN File ID) is **monotonically allocated and NEVER re-used after a deletion** — a deleted child's ordinal stays a permanent hole and is never re-issued. This is a **TEMPORAL** stability: a file's USN reference `(containing-dir OID, FileId)` is never later handed to a *different* file, so USN correlation on it is unambiguous across the journal's history. It is **distinct from SPATIAL object identity**: the ordinal is per-directory *scoped* (the same value recurs in different directories, so it needs the OID), and for **hard-linked** files the object is resolved by `(owner-dir, file_id)` **size-match** (frozen finding #340 / FN_LINK_002 / E51), **not** by the ordinal alone — this erratum does **not** overturn that. On the real-volume corpus (incl. winsider's 33k hard-link groups) the reference was also spatially unique (0 shared by two independently-created files); the `(home, ordinal)` cross-*file* collision recorded in §J is a **synthetic-corpus** artifact, for which size-match remains the robust disambiguator. (Hard-links share one FileId across their names; unique per-volume only.) |
| **Evidence** | **Static (E2):** increment-only counter — `RefsMoveFile` increments the parent NextFileId; `RefsGetNextFileIdFromObjectTable` @1400d17ac reads the persisted object-record counter (no free-list); `RefsDeleteFileId2` / `RefsQueueTriageForDeadFileId` only remove the type-0x20 FileId-index entry on delete; `RefsPackFileId` @140079440 packs (ordinal, dir-OID). **Disk (RD, 2026-08-07):** `usn_fileid_reuse.py` — across **3,661 distinct file references** on win11refs8g / win11refstestmftecmd / winsider, **0** references show a `FILE_CREATE` after a `FILE_DELETE` and **0** carry ≥2 distinct create-names; **6 positive demonstrations** on win11refs8g of a same-directory delete-then-later-create receiving a **fresh** ordinal (deleted ordinal never reappears); on-disk ordinal gaps corroborate on v3.14/insider and v3.9. (USN behavioural proof scoped to v3.14/insider — the only rich journals in the corpus; the mechanism is version-independent.) Report `analysis/reports/fileid_reuse_investigation_2026-08-07.md`. |
| **Corrects** | `structure_reference.md` §C.13a (lower-8-bytes row NEW→CONFIRMED with the temporal no-reuse / stable-reference wording + the hard-link size-match caveat), §C.3a (disambiguate "reused per directory" → per-directory *scoped* but monotonic/no-re-use *after deletion* within a directory, kept consistent with the size-match resolution), §C.7 NextFileId rows (increment-only/temporal no-reuse, distinct from spatial identity). `reference_table.csv` **MD_USN_RA_005** (new). |
| **Docs affected** | `concepts/file_ids.md` (state within-directory monotonic no-re-use-after-deletion as a *temporal* stability, distinct from spatial identity; fix the "reused per directory" line), `attributes/STANDARD_INFORMATION.md` ($SI+0x58), `structures/usn_journal.md` (the 128-bit File ID). Website mirror rebuilt after the doc sync. |

> **Refined by E69 (2026-08-13):** the "`(home, ordinal)` cross-file collision … is a **synthetic-corpus** artifact" phrase above is superseded — the collision is a **hard-link name set of one object** (proven organically on winsider `0x9d84:0x2`, not only synthetically). E66's spatial-uniqueness conclusion (no two distinct objects share a FileRef) stands.


<a id="e67"></a>
## E67 — Reparse-index key word1 (@0x10) is the CREATION/home directory OID (frozen), not merely the current parent

| | |
|---|---|
| **Previous** | The Reparse Index (OID 0x540/0x541) key row at 0x10 was labelled "**containing-directory OID** = the reparse file's **PARENT** directory OID" (disk-verified "242/242 across win11refstestmftecmd / insider / specials"). Those 242 samples are all **never-moved** reparse files (home == parent), so the sample could not distinguish the creation directory from the current parent. |
| **Correct** | The 0x10 field is the reparse file's **home (creation) directory OID** — the upper (`word1`) half of its `(HomeOid, FileId)` reference, sourced from the frozen FCB field `[fcb+0x58]+0x100` (the same field the USN `FileReferenceNumber` word1 reads). It **equals the current parent only for a file that has never been moved**; for a **relocated** reparse file it stays at the creation directory. The row is create/delete-only (an in-place tag change is rejected), so it is written once when the reparse attribute is created and is **not** re-homed by a later move. |
| **Evidence** | **Disk (RD, 2026-08-12):** across the corpus **1,439** reparse files have home ≠ current parent (19 images); a collision-free test (an ordinal is unique within its home dir, so `(ordinal, home)` in the 0x540 index unambiguously identifies that object's row) shows **881/881 relocated reparse objects indexed at their creation directory — 0 at the current parent, 0 missing** (`reparse_index_anchoring.py`). The prior 242/262 "parent" match stands: those were never-moved files where home == parent. **Static (E2):** `[fcb+0x58]+0x100` is the frozen creation-directory reference word, stamped once at creation. Report `analysis/reports/fileref_move_2026-08-12/`. |
| **Corrects** | `structure_reference.md` reparse-index key table (the 0x10 row: "containing/PARENT directory OID" → "**home (creation) directory OID**, frozen; == current parent only for never-moved files"). |
| **Docs affected** | `structures/reparse_points.md` (0x10 field wording), `concepts/file_ids.md` (the six-structure coherence). Applied in the dev docs 2026-08-13. |


<a id="e68"></a>
## E68 — The 128-bit File ID / FileRef home half is the CREATION directory OID, frozen across rename and cross-directory move

| | |
|---|---|
| **Previous** | `MD_USN_RA_002` and the §C.13a / `usn_journal` "128-bit File ID" wording described the upper 8 bytes as the "**table OID**" / "directory OID" without distinguishing the *creation* directory from the *current* parent, and without stating what happens on a move. |
| **Correct** | The upper 8 bytes are the **creation (home) directory's OID** — the directory the file was first created in, where its `NextFileId` minted the ordinal. Together with the lower-8-byte ordinal it is **frozen for the life of the object**: a rename or a **cross-directory move** changes the file's name and its `ParentFileReferenceNumber` (the record-0x18 Parent file ID), but **not** its File ID (record 0x08). The file's type-0x40 backing likewise **stays in the creation directory**; only the type-0x30 name entry moves. This is the **SPATIAL** counterpart to the temporal no-reuse stability of E66. |
| **Evidence** | **Disk (RD, 2026-08-12):** **1,858** real cross-directory moves across nine v3.14 volumes (`RENAME_OLD_NAME`/`RENAME_NEW_NAME` pairs) — the File ID (home half + ordinal) was **unchanged in every case**, while the Parent file ID changed old→new (`usn_move_invariance.py`, `move_invariance_breadth.py`); a moved file's type-0x40 backing is found in its **home** directory, not its current parent (`backing_stays_in_home.py`); on disk the moved entry carries `value+0x08` = creation dir (e.g. `Generate-FSActivity.ps1`, home `0x9586`, now in parent `0x9e25`). **Static (E2):** `RefsMoveFile` migrates only the type-0x20 FileId-resolution row and never rewrites the FCB reference word `[fcb+0x58]+0x100`. Report `analysis/reports/fileref_move_2026-08-12/`. |
| **Corrects** | `reference_table.csv` **MD_USN_RA_002** (description: "table OID" → "**creation/home directory OID**, frozen across rename and move"); the new **MD_USN_RA_006** records the move-invariance in full. `structure_reference.md` §C.13a (the 128-bit File ID split → creation-dir + frozen-across-move). |
| **Docs affected** | `concepts/file_ids.md`, `structures/usn_journal.md`, `structures/directory_entries.md`, `examples/track_a_file_across_moves.md`. Applied in the dev docs 2026-08-13. |


<a id="e69"></a>
## E69 — The rare (home, ordinal) cross-file "collision" is a HARD-LINK name set of ONE object, not two distinct files (refines E66 / §J)

| | |
|---|---|
| **Previous** | §J described the per-directory ordinal collision with the example "**two distinct different-size files** both at home 0x708 / ordinal 8 in the synthetic xbpt_* corpora", and E66 called the `(home, ordinal)` cross-file collision recorded in §J a "**synthetic-corpus** artifact". |
| **Correct** | That case is **one object with two hard-link names**, not two distinct files. The object has a **single home-owned type-0x40 backing**, and that backing embeds **one type-0x39 back-pointer per name** — the object's own authoritative list of its names. The differing per-name sizes are **stale `value+0x38` copies** (ReFS does not keep the per-name cached size in lockstep), not evidence of distinct files. The collision is therefore a **hard link**, and it occurs both synthetically **and organically** (winsider `0x9d84:0x2`, the Microsoft.DesktopAppInstaller MSIX split-package pair). The B+-tree still guarantees uniqueness (a home owns at most one backing per ordinal), so **no two distinct file objects share a FileRef** — E66's spatial-uniqueness conclusion stands; only its "synthetic-corpus artifact" **characterization** of the collision is refined. It is **not** deduplication or block-cloning (new finding **FN_LINK_004**, 10-axis exclusion). |
| **Evidence** | **Disk (RD, 2026-08-09/12):** the winsider `0x9d84:0x2` pair (SplashScreen size 0 / Wide310 size 1397) resolves to **one** backing (size 1397) carrying **two** type-0x39 back-pointers naming both; the §J-cited `(home 0x708, ordinal 8)` xbpt pair (`xbpt_romeo_output` 97673 / `xbpt_hardlink_audit` 239973) likewise has **one** home-owned backing (size 97673) with two 0x39 back-pointers naming both, **reproduced on 3 images** (`verify_single_object.py`; byte dump `f1_investigation_2026-08-09/evidence/bytes_collision_pair.md`); across the corpus every different-size `(home, ordinal)` group re-resolves to exactly one home-owned backing (0 multi-backing; 44 groups / ReFS 3.7–3.14). **Static (E2):** `RefsLinkFileToSelf` copies the identity into each name and adds a type-0x39 back-pointer, allocating no new stream. Report `analysis/reports/f1_investigation_2026-08-09/F1_FINDING.md`. |
| **Update (2026-11-20, E164)** | The Evidence row's static sentence does not hold: `RefsLinkFileToSelf` copies no identity into each name. It runs once per file, re-parents the file's own table under the type-0x40 key {0x80000040, 0, file reference} and writes back only the name the record sat under; each further name is written by `RefsAddLink`. The disk evidence stands. |
| **Corrects** | `structure_reference.md` §J (the "two distinct different-size files" example → **one object with two hard-link names** + stale per-name size; the type-0x39 back-pointers as authoritative membership). `errata.md` **E66** (refines its "synthetic-corpus artifact" phrase → hard-link name set of one object, organic + synthetic). `reference_table.csv` **FN_LINK_004** (new). |
| **Docs affected** | `concepts/hard_links.md`, `concepts/file_ids.md`, `concepts/deduplication.md`. Applied in the dev docs 2026-08-13. |

<a id="e70"></a>
## E70 — A cross-directory MOVE forces the record to be SPLIT out of its name row (one-way ratchet); the ExternalFileId same-volume write path is not persisted on native

> **CORRECTED by E87 (2026-09-04) — read this first.** "NON-RESIDENT" throughout this entry means the
> record is **SPLIT out of the name row** (`key_flags` 0x02 + type-0x40 backing), which is what a move and a
> hard link actually force. **They do not move the file's data**: on the very images below, a whole-volume
> before/after shows 5 files changing placement and **0** changing data residency, and `move.txt`'s `$DATA`
> sub-record is byte-identical across the move. Everything this entry says about **identity** (frozen
> `(home, ordinal)` FileRef, monotonic ordinals, ExternalFileId, rename/copy corollaries) is unaffected.

| | |
|---|---|
| **Previous** | The reference documented FileRef move-invariance (E66/E68, MD_USN_RA_002/006) and the resident (§C.2) vs non-resident (§C.3) type-0x30 layouts **separately**, but never stated that a cross-directory move **changes a file's residency**. A transient 2026-08-15 static reading also suggested `RefsConvertToStandardInfoExternalId` stamps the moved file's home into `$SI+0x58` (ExternalFileId) when home≠parent. |
| **Correct** | **A cross-directory MOVE converts a resident file to NON-RESIDENT — a one-way ratchet.** `RefsMoveFile` re-homes only the **name** (type-0x30) and the **type-0x20 FileId-resolution index**, and freezes the `(home, ordinal)` FileRef (home = creation dir; E66/E68). Because **only the non-resident §C.3 type-0x30 layout carries the per-name home-backref at `value+0x08`** that holds the frozen creation-dir home — the **resident §C.2 layout has no such field** — and `RefsMoveFile` calls **neither** `RefsConvertToNonResident` **nor** any `ConvertToResident` (no residency-reversion helper exists in any driver), a relocated file **must** take the non-resident form and can never revert. Corollaries (all RD-proven): a **same-directory RENAME keeps residency** (name-only change, home==parent); a **COPY is a new object** with a new File ID homed at the destination; a **cross-directory HARD LINK** likewise forces the object non-resident (shared home-owned backing, one type-0x39 back-pointer per name); a **move-back** stays non-resident (home==parent again, yet non-resident). Consequences for identity: **resident files always have home == parent** (they can never be relocated while resident); a resident file's FileRef is `(parent_oid, ordinal@value+0x80)`. The per-directory **ordinal (`NextFileId`) is monotonic and never reused after deletion**. On **ExternalFileId_2/_3** (`$SI+0x60`/`+0x68`): `RefsConvertToStandardInfoExternalId` **keys on an origin-VOLUME identity word, not a directory OID**, and zeroes the field when origin-volume == current-volume — so a **same-volume move leaves it 0**. The existing wording "zero on native v3.7+; non-zero only on upgraded carryover" is therefore **CORRECT and unchanged**; the relocated home is carried by the non-resident `value+0x08` (§C.3), **not** ExternalFileId. |
| **Evidence** | **Controlled before/after (RD, 2026-08-16, `win11refs8gtestmove_{before,after}move.raw` + USN + transcript):** `move.txt` (16 B `"hello"`) was **resident** before a cross-dir move (testmove1→testmove2) and **non-resident** after, FileRef `0x761:0x2` (home 0x761 frozen, parent→0x762); `hl.txt` resident→non-resident (hlc 2, shared `0x761:0x3`); `movesamedir`→`movedsamedir` stayed **resident**; `copied.txt` = new File ID (`0x762:0x2` / `0x761:0x7`); `haha2_10021` moved out+back stayed non-resident. Corpus: **134/134** cross-dir-moved files non-resident (win11refs8g 42/42, testmftecmd 92/92); moved files far below the resident-size ceiling (winsider 10–36 B vs 2047 B) still non-resident while equal-size non-moved size-0 files are resident. **Static (E2, all versions):** `RefsMoveFile` (win11 @1400e9500 / insider @14010f2d4 / win10 @1c00b4800) = `RefsRemoveLink` + `MsReparentChildTable` + `RefsCreateFileId2` + `RefsConvertToStandardInfoExternalId` + `RefsAddLink`; **0** `RefsConvertToNonResident` calls; no `ConvertToResident` symbol in any of the 4 drivers. **ExternalFileId (RD):** `ExtFid2/3` = 0 on **0/905** native-v3.14 moved backings and 0 across the census; the only non-zero (49) are resident carryover on the upgraded image (0 moves). **Ordinal (RD):** the `testdeletion2` controlled 10,001-file create + 1,112-delete sequence → 10,190 distinct ordinals, strictly monotonic, **0 reuse**; files created after the deletions all take ordinals above the max deleted. Reports: `move_residency_controlled_2026-08-16.md`, `fileref_moved_investigation_handoff_2026-08-15.md`, `externalfileid_disk_2026-08-16/`. |
| **Corrects** | `structure_reference.md` §C.2 (a resident file is never relocated: home == parent) and §C.3 (a cross-directory move forces this non-resident form; `value+0x08` carries the frozen creation-dir home). **Enriches** (does NOT correct) the ExternalFileId_2/_3 rows (`$SI+0x60`/`+0x68`): the static same-volume write path exists but is **not persisted** on native — the "zero on native" wording stands. `reference_table.csv` **FS_MOVE_RA_001** (new). |
| **Docs affected** | `concepts/file_ids.md`, `concepts/object_ids.md`, `structures/directory_entries.md`, `examples/track_a_file_across_moves.md`, `concepts/resident_storage.md`, `attributes/STANDARD_INFORMATION.md`, `structures/usn_journal.md`, `structures/reverse_index.md`. |

<a id="e71"></a>
## E71 — The USN `$J` change journal was read only to ~896 KB (a $DATA descriptor misread as the stream size); the whole allocation is now read

| | |
|---|---|
| **Previous** | forefst's `usn` command read the `$J` stream capped at a "stream size" of **917632** bytes — actually the `$DATA` sub-record **descriptor `0x000E0080`** (= 917632), which `_usn_find_subrecord_markers` took as a length (`read_usn_j_stream` then sized its buffer at `min(alloc, stream_size)`). Any journal allocated larger than ~896 KB was truncated to its first ~896 KB. The §C.3 LastUsn note reported "480/480 on a heavier image, rest wrapped out of the `$J` sliding window", attributing the unmatched files to journal wrapping. |
| **Correct** | `$J` is a **non-resident, extent-backed rolling log that fills its allocation**, so the read length is the **extent allocation** (Σ run clusters = the configured journal size, e.g. 32 MiB / 128 MiB), **not** `0x000E0080` — which is the `$DATA` sub-record **type descriptor**, not a length (already documented at §C.3/§C.6). Reading the full allocation recovers every record (each self-validates: length @0x00, USN @0x28; a partially-filled journal's zero tail is skipped). Most files previously deemed "wrapped out" were in the journal but **unread**: with the full read, **13,550/13,550** in-window winsider LastUsns hit an exact record offset (was 706/706 within the truncated window). Only USNs older than the live window's floor are genuinely purged. |
| **Evidence** | RD 2026-08-21, all **11** corpus images with an active `$J`: every one had `stream_size`==`0x000E0080` while `alloc` = 32–128 MiB. Before→after record counts: winsider **6,481 → 217,892**, testmove 8,703 → 33,379, testmftecmd 6,805 → 9,371, attributes2 6,874 → 8,111; barely-used journals (win11refs2gtargeted 100; lasttests 46/53) **byte-identical** (records fit in the first ~896 KB). Full read: **0 duplicate USNs**, ~100 % named, contiguous USN range. The trigger `passwords.txt` (FileRef 0x9c9f:0x7, LastUsn 66051560) now appears with 4 records incl. exactly USN 66051560 (reason 0x80008102). regress 18/18. Reports: `usn_journal_fix_plan_2026-08-21.md`, `usn_details_analysis_2026-08-21.md`. |
| **Corrects** | `structure_reference.md` §C.13 (NEW `$J` storage & reading subsection) + §C.3 row 0x68 LastUsn note (the "480/480 … wrapped out" undercount). `reference_table.csv` **MD_USN_RA_007** (new). The `LastUsn`/`UsnJournalID` **field definitions were already correct** — this is a **reader** fix + a sliding-window undercount correction, not a field-layout error. |
| **Docs affected** | `structures/usn_journal.md`, the `usn` command help, any reader USN page. |


<a id="e72"></a>
## E72 — The non-resident MI `$DATA` header layout was documented from v3.14-only images; v3.4 shifts the size fields +4, and `summary_size` is 0x1A0 before v3.14

| | |
|---|---|
| **Previous** | `MD_DATA_RA_011` and `structure_reference.md` §C.6 "MI $DATA Sub-Record Header" gave the non-resident (multi-instance, key descriptor 0x000E0080 / value+0x04 0x00010028) `$DATA` holder value layout as `summary_size@0x0C=0x200`, `total_alloc@0x30`, `stream_size@0x38`, `vdl@0x40`, `disk_alloc@0x48` for version scope **"3.4;3.14"**. The 2026-06-18 re-measurement was *"anchored on `val[0x38]==file_size`"* over a census of **v3.14/Insider-only images** (win11refs2g, win11refs2tspecials, winsider — `deep_data_mi_format.md`), so no v3.4–v3.10 record was ever in the sample; the anchor itself also self-excludes v3.4 (where file_size is at 0x3C, not 0x38). |
| **Correct** | The documented offsets are **v3.7+ only**, and there are **two independent version boundaries**. **(1) Size fields shift +4 on v3.4:** `total_alloc@0x34`, `stream_size@0x3C`, `vdl@0x44`; `disk_alloc@0x4C` is 0 / unpopulated (v3.4 carries the allocation in `total_alloc@0x34` alone, whereas v3.7+ also mirror it at `disk_alloc@0x48`). `inner_hdr_size@0x00 = 0x88` and the extent sub-record at +0x88 are **unchanged** across all versions. Boundary = v3.4 ↔ v3.7 (the instance-marker era, MD_LK_RA_006; refsprogs' `/* v1.0-3.4: 0x3C  v3.5+: 0x38 */`). **(2) `summary_size@0x0C` = 0x1A0 (416) on v3.4–v3.10** and **0x200 (512) on v3.14+** (the v3.14 non-backward-compatible $SI/attribute-layout change). Boundary = v3.10 ↔ v3.14. |
| **Evidence** | RD 2026-08-29, per-version holder census (`analysis/reports/refsprogs_audit_2026-08-29/harnesses/{census34,full34,hdr34}.py`): **v3.4** stream_size@0x3C on **257/257** (win10refs8g) + **257/257** (win10refs110g), total_alloc@0x34, vdl@0x44, disk_alloc@0x4C=0; e.g. `xbpt_archive_romeo` FileSize 186635=0x2d90b@+0x3C, AllocSize 188416=0x2e000@+0x34. **v3.7** (win1121h2test 291), **v3.9** (win1122h2test 519), **v3.10** (win1123h2test 98): stream_size@0x38, `summary_size@0x0C`=0x1A0. **v3.14** (win11refs2tspecials 475) / **Insider** (winsider 14,299): stream_size@0x38, `summary_size@0x0C`=0x200. Independently corroborated by `unsound/refsprogs @1c17be1` `node.c:7702/7752` (`static_size = version>=3.5 ? 0x84 : 0x88`). The 0x000E0080 (key+0x0C) / 0x00010028 (value+0x04) descriptor pair is one record (settled 2026-08-20, `snap_data_descriptor_0x10028_vs_0x000E0080_2026-08-20.md`) — unaffected. **Static:** the on-disk field offset is emitted by the minstore/Sms row builder and is **not** isolated to a single decompiled citation (the same limitation recorded in the original 2026-06-18 analysis); the version-dependence rests on the all-version disk census + refsprogs' explicit `version>=3.5` branch. |
| **forefst impact** | **None.** `parse_snapshot_data_entry` reads stream_size@0x38 / disk_alloc@0x48 (the v3.7+ offsets), which read 0 on v3.4 — but forefst does **not** use them for v3.4 output: FileSize comes from the type-0x30 value+0x58, residency from value+0x60, and the extent list decodes independently (v3.4 extraction is byte-exact, verified). Reference-accuracy correction, not a tool bug. (Same phenomenon as the refsprogs differential audit's "finding #2": offset real, no output impact; the audit's proposed `le32(v,0)` discriminator is itself wrong — value+0x00 = 0x88 on every version.) |
| **Corrects** | `reference_table.csv` **MD_DATA_RA_011** (version-scope the header offsets to v3.7+ and add the v3.4 +4 layout + the `summary_size` v3.14 boundary). `structure_reference.md` §C.6 "MI $DATA Sub-Record Header" table (add the v3.4 column and the `summary_size` boundary; note the "31,678 anchored on `val[0x38]==file_size`" census was v3.14/Insider-only). |
| **Docs affected** | `attributes/DATA.md` and `structures/extent_descriptors.md` both tabulate the MI $DATA header as `stream_size@0x38` / `summary_size@0x0C=0x200` with **no** v3.4/summary-size version note — add the v3.4 +4 shift and the `summary_size` 0x1A0(≤3.10)/0x200(3.14+) boundary (2026-08-29 doc review). Check `attributes/SNAPSHOT.md` / `NAMED_DATA.md` for the same. |


<a id="e73"></a>
## E73 — A file's attributes can live in a CHILD node of the embedded tree; an outer-level-only parse reports a confident, wrong "none"

| | |
|---|---|
| **Previous** | The embedded attribute B+-tree inside a resident type-0x30 value was parsed at the **outer level only** (`parse_resident_btree_rows`: take the node at `le32(vd,0)`, walk its offsets array, decode rows). `MD_DATA_RA_015` already recorded that such a value "is a (multi-level) B+-tree so an outer-level parse finds no inline `$DATA` row", but it compensated **only for the missing `$DATA` size** (the `value+0x58` / alloc heuristic in `_multilevel_extent_backed_size`). The consequence for **every other attribute** was never recognised. |
| **Correct** | When a file's attribute set outgrows one embedded node, the node inside the type-0x30 value becomes an **INDEX node** — descriptor **+0x0C level != 0** and **+0x0D bit 0 set** (§A.2b node flags) — holding one row per child with an **empty separator key** (`key_offset 0x10`, `key_size 0x00`) whose value is a 48-byte node reference (4 × `le64` LCNs; 0 and 0xFFFFFFFFFFFFFFFF are sentinels). The file's real attributes — `$DATA` 0x80, ADS/`$SNAPSHOT` 0xB0, `$REPARSE` 0xC0, and the type-0x0 `key_len 0x50` ADS extent records of **E61** — live in the **child page**, not in the value. The child must be descended with the ordinary page walk. Because the outer level carries **no** attributes at all, the old parse returned an empty list and every consumer reported a confident **"none"** rather than an error. |
| **Evidence** | **Static (E2):** `CmsEmbeddedComposite::FindIndexHeaderInPage` (win10 @`1c0004b00`) — the *embedded*-composite class — either takes the node directly at `page+0x50 + le32(page+0x50)` (the same `thoff` the reader uses) **or** pushes a lookup stack and calls **`CmsBPlusTable::BinarySearchIndex`**: a real B+-tree index descent. **Ground truth (RD):** `generate_validation_corpus_v2.ps1` writes `3+(n%3)` ADS on each of 12 `multibig_NN.bin`; the reader listed only **9** — `multibig_05/08/11` (the three 5-ADS files) reported **zero**. Descending their index row reaches an `MSB+` page of 16 rows holding exactly `big_1..big_5`; after the fix **12/12** files match the generator formula (48 streams) and the five recovered streams **extract byte-exactly** (`8192·k·5` bytes of the marker `MB05s{k}_`, k=1..5). **Corpus:** 1,329 files across **19 of 99** images, **4,094 records** recovered — 2,050 × 0x80, 709 × 0xC0, **548 × 0xB0 (ADS)**, plus 298/188/181 in the v3.4 marker-less form (E72) and 120 type-0x0 ADS-extent records — on v3.4, v3.7, v3.9, v3.10 and v3.14. `win1122h2test` goes from **0 → 60** ADS-bearing files. |
| **Safety** | Strictly **additive**: across all 1,329 index-node values the pre-fix parse returned **0** rows, so nothing is replaced — measured **4,094 gained, 0 lost**. 3,070 of 3,168 regression fingerprints unchanged; every changed one is an image that gained attributes. |
| **Corrects** | `MD_DATA_RA_015` — the multi-level tree is now **descended**, not merely worked around (its size heuristic remains a fallback for the extent case). **`FS_SNAP_RA_001`'s census (532,503 entries / 409,185 files / 112 images) is a LOWER BOUND** — it was taken with the outer-level parse. `MD_ATTR_RA_016`'s "types 0x50/0x60/0x70 = ZERO sub-records" **survives**: re-checked against all 4,094 recovered rows, none is 0x50/0x60/0x70. New row **MD_ATTR_RA_017**. Independently predicted by the `unsound/refsprogs` differential audit as `MD_ATTR_RP_001` / action `A-L7-6` ("identified by `key_offset == 0x10 && key_size == 0x00` … if any exist, forefst drops data"), which the 2026-08-29 analysis had filed as *"Low, NOT_TESTED, unknown whether it occurs"* — **it occurs**. |
| **Docs affected** | `attributes/NAMED_DATA.md`, `attributes/DATA.md`, `concepts/resident_storage.md`, `structures/directory_entries.md`, `structures/btree_node.md`. Tool: `forefst.py` v1.8.0 (`_descend_embedded_index`). |


<a id="e74"></a>
## E74 (audit K129) — The allocator row is not a fixed 2,072-byte record: the bitmap is variable-length, `+0x14` is two bytes not a u16 "header size", and `+0x16` is not a usable "used count"

| | |
|---|---|
| **Previous** | `structure_reference.md` §B.2 documented the allocator (schema 0xe010) bitmap row as a fixed **"Bitmap Row — 2,072 bytes"** with `Free count u16@0x10`, `Flags u16@0x12`, **`Header size u16@0x14`** ("Small/Container: 0x0118 all versions; Medium: 0x0118 on v3.4, 0x0218 on v3.7+ — version-dependent"), **`Used count u16@0x16`**, and a fixed **`bitmap 2,048 B @0x18`**; plus a "Compact Row — 24 bytes … same first 24 bytes" and Subtable B.2a enumerating flags 0x01 partial / 0x02 compact / 0x05 fully free / 0x09 fully free. Tier selection was implicitly by **root index** (Medium=1, Container=2, Small=12). |
| **Correct** | Five corrections, all read straight off the driver's own row codec and confirmed on disk. **(1) The bitmap is variable-length.** Its size is `ceil(range_length / 8)` rounded up to 8 bytes, so the row is `bitmap_offset + roundup8(ceil(range_length/8))` — 2,072 B is only the common `range_length = 16,384` case. Observed row sizes: **2,072** (16,384 clusters), **152** (1,024), **32** (12 and 3). **(2) `+0x14` is two `u8` fields, not a `u16`:** `bitmap_offset u8 @0x14` (**0x18** when a bitmap is present, **0x00** when not) and a **format byte `u8 @0x15`** (1 or 2). The "version-dependent header size 0x0118 → 0x0218" was this format byte, and it is **tier-dependent, not merely version-dependent**: Container and Small are format **1 on every version**; Medium is **1 on v3.4** and **2 on v3.7+**. **(3) Flags **bit 0** means "this row carries a bitmap"** — that is the discriminator the driver uses; the enumerated values 0x01/0x05/0x09 (bitmap) and 0x02/0x06 (compact) are consequences of it. **(4) `+0x16` is NOT a usable "used count".** It is a driver-maintained allocated-cluster *hint* with **0xFFFF meaning "the entire range"** (expanded to `range_length` on read); it disagrees with the row's own bitmap on **742 of 4,634** bitmap rows and the driver itself carries `RebuildAllocatorSummary` / `MarkAllocatorSummaryOutOfSync`. **Never use `+0x16` for capacity arithmetic.** **(5) `+0x10` (free) is the authoritative count but saturates at 0xFFFF** — it does *not* truncate (a 262,144-cluster range whose low 16 bits are 0 stores 0xFFFF). Saturation is structurally impossible on a bitmap row (max range 16,384 clusters), so it only affects compact rows. **Authoritative per-row free count:** bitmap row → `range_length − popcount(bitmap)`; compact row → `0` if `free_u16 == 0`, else `range_length`. |
| **Compact-row discriminator** | `free_u16` — **`0` = fully allocated, non-zero = fully free** (and then `free_u16 == min(range_length, 0xFFFF)`). Resolved on **1,061/1,061** compact rows with **0 unexplained**. This **refutes** the earlier working guess that the discriminator was `used(+0x16)` (2026-09-01 probe note "the discriminator is probably `used` … but that is unproven"): `+0x16` takes the values 0, 1, 4, 116 and 0xFFFF on rows that are unambiguously free, and is not a discriminator. |
| **Persisted allocator summary (NEW structure)** | Each allocator table's **root page** carries a **416-byte summary** (corrected from 384 by E110) that ReFS maintains itself, at `_SmsIndexRoot + u16@(_SmsIndexRoot+0x04)` — i.e. `page + 0x50 + u16@page+0x54`, observed at **page+0x78** on every image. Read as `u64[48]`: **slot 1 = clusters covered**, **slot 2 = free clusters** (slot 0 = 2 on v3.7+ Medium, 1 on v3.4 Medium, 0 on Container/Small; slots 3–8 undecoded). This is the volume's *own* accounting and an independent check on any recomputation. |
| **Row addresses are PHYSICAL cluster numbers (new — not a correction of §B.2, which never stated it)** | A row's `range_start` / `range_length` are **physical** LCNs, at least for the **Medium** tier. Structural proof: the Medium tier's span is exactly `[0, last-mapped-physical-cluster)` on every image measured — `win11refs2g` 0..507,904, `win11refs8g` 0..2,080,768, `winsider` 0..15,138,816, `win10refs110g` 0..28,819,456 — each identical to that volume's physical container extent, while the *virtual* space starts at `first_container_id << shift` (65,536 on all four, container ids beginning at 2) and is roughly twice as wide. Behavioural proof: live file-data extents are marked allocated **99–100 %** of the time when queried by their translated **PLCN** and only **0–27 %** by their VLCN (13,917 extents, 28 images); the sole outlier at 62 % is a v3.4 volume where the uncovered remainder belongs to another tier under strict separation, not to a "free" verdict (`win10refs2tspecials`: 844 allocated, 506 uncovered, **1** free). **This is a different question from §B.2's "Addressing" column**, which describes how each tier's *table pages* are reached (roots 1 and 2 through the container translator, root 12 by real LCN) and remains correct. The Container and Small tiers' row ranges are proper subsets of the physical space and their address basis is **not established here** — do not assume it. |
| **Tier interaction (§B.2 "Three-Tier Interaction" confirmed by measurement)** | **v3.4: the tiers partition** — Medium ∩ Container = **0** on all 9 v3.4 volumes, and the live metadata clusters Medium does not span are covered by Container (e.g. `win10refs2tspecials`: 976 Medium + 244 Container, 0 unaccounted). **v3.7+: Medium contains Container** — Medium ∩ Container = the *entire* Container span on **86/86** v3.7+ volumes. So the tiers must never be summed on v3.7+; Medium alone is the authority there, and on v3.4 the tiers are unioned. |
| **Coverage gap** | The allocator's virtual space covers only what the **Container Table maps**; the physical tail beyond the last container belongs to no tier. Measured as **exactly 48 MiB on 90/95 images** — every version (3.4→6.66), both cluster sizes (12,288 × 4 KiB = 768 × 64 KiB), every volume size (2 GB → 16 TB) — and it is a **tail**, `[last mapped cluster … volume end)`, not a prefix. It is the partial trailing container ReFS never creates. A real Windows volume can leave much more (`winsider`: 924 containers of a possible 956, 2,087 MiB unmapped). Report it as *outside the allocator*, never as free. |
| **Update (2026-11-18, E162)** | The coverage-gap row does not hold: the allocator covers the whole volume (its summary equals the volume's length on 117 of 117 corpus volumes), and the 48 MiB is the image's bytes after the volume. |
| **Root index is not the tier** | Same defect class as **#337** / `_select_ct_root` / `_select_ot_root`: on the four `win11refs2tmillionsofactions*` volumes **root 12 carries table 0x0B (the Container Table), not the Small allocator 0x22**, and roots 4 and 6 are empty. Worse, an ID-correct root is not sufficient — on those same volumes root 1's page *does* claim 0x21 yet its subtree descends into pages belonging to tables **0x05** and **0x20** (stale/crossed pointers on a damaged volume): **1,368 of 7,063 rows** reached from the tier roots came from a foreign page. Every row must be accepted only if the page it sits on claims the tier's own table id. On the 91 undamaged images this rejects nothing. |
| **Evidence** | **Static (E2), two independent driver generations.** v3.14 `CmsAllocator::BPlusRowToRegionEx` (win11 @`140092a60`): reads `u64@0x00`/`u64@0x08` as start/length, `(u32)u16@0x10` as free (no sentinel handling), `u16@0x12` as flags, and `u16@0x16` into `region+0x18` **expanding 0xFFFF to `range_length`**; sets the bitmap pointer to `value + (u8)value[0x14]` **only when `flags & 1`**; and tests `(u8)value[0x15] > 1` to set an internal flag. v3.14 write side `CmsAllocator::PersistRegion` (@`140018…`): writes `value+0x16 = 0xFFFF` **iff** `region+0x18 == range_length`, else the low 16 bits. v3.4 `CmsGlobalAllocator::CopyBPlusRowToFv` (win10 @`1c0054f50`) independently confirms all three: `flags & 1` gates the bitmap, `(u8)value[0x14]` is the bitmap offset, and the copy length is `range_length >> 3` — the variable bitmap size. Summary: `CmsAllocator::LoadAllocatorSummary` (win11 @`14003ef8c`) copies 3 × 0x80 bytes from `_SmsIndexRoot + u16@+0x04`. **Raw disk (RD), all 95 ReFS images of the 99-image corpus, 7,063 rows (5,695 from pages claiming the tier's own id):** row size matches the driver's formula on **4,634/4,634** bitmap rows; `bitmap_offset` is 24 exactly when `flags&1` and 0 otherwise, **5,695/5,695**; `free == range_length − popcount` on **4,634/4,634**; compact discriminator resolves **1,061/1,061**; persisted summary agrees with the recomputed rows on **268 of 281** tier-instances, and **all 13 disagreements are explained** — 9 are v3.4 Medium (the summary spans the whole mapped volume while Medium's rows do not, and the **free counts still match exactly**) and 4 are the damaged `millionsofactions` family. **Adversarial:** every live metadata cluster on every image is marked **allocated** — **0** live-but-free clusters across 95 images / 281,289 live clusters (the clusters fed to that test are the physical ones the page walk returns, which is why it passed and is what first indicated the physical addressing above). Extended to live **file data**: 100 % allocated on every healthy image tested (`winsider` 131,385 / 131,385). Probes: `analysis/tools/analysis_scripts/allocator_probe.py`, `allocator_validate.py`, `allocator_summary_check.py`. |
| **forefst impact** | **None yet — no tool currently decodes the allocator.** `summary` computes a container-level `containers_free` / `free_space_est` (forefst.py ~:4065) that it deliberately does **not** display, calling a container-level figure misleading (:4228). This erratum is what a real capacity figure must be built on. |
| **Corrects** | `structure_reference.md` **§B.2** (row size, `+0x14`, `+0x16`, flags bit 0, Subtable B.2a, tier interaction, and a new persisted-summary subtable). New register rows **FS_ALLOC_RA_001** (row format) and **FS_ALLOC_RA_002** (persisted summary + tier resolution). |
| **Docs affected** | `structures/allocators.md` was written to this erratum. `concepts/allocation_space_mgmt.md` **already documented the allocator** and was missed at the time — this cell previously read "no reader page currently documents the allocator", which was wrong, and the two pages consequently contradicted each other in the published site (one calling the bitmap row variable-length, the other a fixed 2,072 bytes). Reconciled 2026-09-02: the concept page now carries the variable-length row, the `+0x14`/`+0x15` byte pair, the flags-bit-0 discriminator, the compact-row free-count rule and the bitmap-row scoping of the popcount invariant. Any future allocator page must also carry the "never sum the tiers on v3.7+" rule and the unmapped tail. |


<a id="e75"></a>
## E75 — ReFS 3.4 alternate data streams were invisible: the 0xB0 key gate only matched the marker form

| | |
|---|---|
| **Previous** | Every reader of an embedded 0xB0 (ADS / `$SNAPSHOT`) attribute row required an instance marker: `_is_b0_snapshot_key` returned true only for `key[0x08:0x0C] == 0x80000002` with the type at `key[0x0C]`, and the stream name was always read from `key+0x10`. The differential audit of 2026-08-29 flagged this gate (finding #1) but concluded it was a **latent** fragility with no live impact, having measured "**zero** live object-tree rows" carrying the `hidden_*` ADS names on the v3.4 image and recorded *"forefst's '0 ADS' on 3.4 is the correct answer"*. |
| **Correct** | The 0xB0 key has **two on-disk forms** — the marker form above, and the **v3.4 marker-less form already documented by E72**: no marker, the attribute type at **`key+0x08`**, and the stream name from **`key+0x0C`**. Matching only the marker form makes **every v3.4 ADS invisible**. Both forms must be accepted, and the name read at the offset the matched form implies. |
| **Why the audit's measurement said otherwise** | Its sweep walked only the **outer level** of the embedded tree. On these volumes the 0xB0 rows live in a **child page**, reachable only after **E73**'s index-node descent, which did not exist when the audit ran. The audit's conclusion was therefore correct *for what it could see* and wrong about the volume. This is the second finding to change verdict once E73 opened the child pages, and is a standing lesson: **a census taken with a reader that cannot reach a region is evidence about the reader, not about the disk.** |
| **Evidence (RD)** | `win10refs2tspecials` (v3.4, 2 TB): **176** live embedded 0xB0 rows, **0** carrying a marker, type `0xB0` at `key+0x08`, all with StreamSummary `val+0x10 == 0` (= ADS, not snapshot, per E61). The reader reported `ads (0) — (none)`; after the fix it reports **100 ADS-bearing files**. Names are exactly the generator's `hidden_NNNN` (`Generate-FSActivity.ps1:1024`, `$stream = 'hidden_{0}' -f $Rng.Next(1000,9999)`). **Content is byte-exact against the generator**: `test/xbpt_tango_archive_828215.dat:hidden_1514` → `"Replayed ADS at 2026-05-16T11:51:08.7086168Z"` and `…/xbpt_data_quebec_921347.tmp:hidden_2136` → `"Generated ADS at 2026-05-16T11:55:12.4451440Z"` — the two literals the generator writes (`:733`, `:1024`). Corpus census of marker-less embedded 0xB0 rows: **184 on v3.4** (176 + 2 + 2 + 2 + 2 across five volumes) and **4 on v3.14** upgraded-from-3.4 volumes (`win10to11refs4g`, `…_afterwin11mount`), i.e. the retained pre-marker entries the audit predicted would exist on upgraded volumes. |
| **Scope note** | Strictly additive for 0xB0: the v3.4 form was previously matched by nothing, so no row changes meaning. `_is_b0_snapshot_key` also gates snapshot counting/parsing, where the same two-form rule now applies. |
| **Corrects** | The audit's finding-#1 verdict *"IMPACT OVERSTATED / forefst's 0 ADS on 3.4 is the correct answer"* (`analysis/reports/refsprogs_audit_2026-08-29/ANALYSIS.md` §1 and §4 item 1, which ranked the per-record marker probe as optional hardening). It is a **live data-loss bug**, now fixed. `MD_LK_RA_006` / **E72** already held the underlying two-form fact — the gap was that the ADS reader never applied it. New register row **MD_ADS_RA_001**. |
| **Docs affected** | `attributes/NAMED_DATA.md`, `structures/directory_entries.md` (the key forms), `concepts/resident_storage.md`. Tool: `forefst.py` v1.8.0 (`_b0_name_offset` / `_b0_stream_name`). |


<a id="e76"></a>
## E76 — A name's cached file size (`value+0x38`) can be stale in BOTH directions; the object's size lives in the type-0x40 backing at `+0x58`

| | |
|---|---|
| **Previous** | `hard_links.md` recorded that a name's cached size *"can carry a stale size"*, and `walk_directory_tree` already corrected for it (the F-1 hardening) — but only for `files`. The reference never stated **which field is authoritative**, and the extraction paths (`_analyze_dir_extents` → `get_file_content` → `extract` / `dataruns` / `export`) kept reading the name's own copy. The stale case was understood as the cached size being **too large** (the "size-0 SplashScreen" example). |
| **Correct** | The object's size is the **type-0x40 backing's `value+0x58`**; a type-0x30 index-entry name (`key_flags 0x02`) carries a *cache* at `value+0x38` that the driver does not refresh on every update. It can be stale **in either direction**, and the small-cache case is the dangerous one: it silently **truncates** an extraction. Every size that gates a read or a write must resolve through the backing when one exists, and fall back to the name's field only when it does not. |
| **Evidence (RD, 2026-09-02, whole corpus)** | **83,176** `key_flags 0x02` FILE rows across 99 images, every one with a resolvable backing. **190 stale** — v3.7 (3), v3.9 (4), v3.10 (18), v3.14 (165). In **190/190** the backing's `+0x58` equals the independently-decoded `$DATA` stream size and the name's `+0x38` does not, so the backing is corroborated by a second field. The divergence runs **both ways**: `hardlink_audit_219848.cfg` caches 239,973 for a 97,673-byte object (over-read), while `hardlink_mike_576693.csv` caches 293,302 for a **479,429**-byte object (under-read). Extracting the three largest under-read cases recovered **186,127 / 274,284 / 49,480 bytes** that the previous code discarded, each **99.6 % non-zero** — real content, not padding. |
| **Version scope** | Structurally impossible on **v3.4**: those volumes have **0 type-0x40 rows** and **0 `key_flags 0x02` file rows** (only kf=2 *directories*, 72-byte values), so no cache can diverge from a backing. The rule keys on "a backing resolves", which makes it version-safe rather than version-gated. |
| **Symptom it produced** | Extracting an object by its hard-link or moved name returned different bytes from extracting it by its primary name — 98,304 vs 97,673 in the reported case (the whole cluster allocation, with 631 bytes of slack), or a silently short file in the under-read case. `files` was already right, so the tool contradicted itself. |
| **Corrects** | `MD_DATA_RA_015` / `FN_LINK_002` context and `hard_links.md`: name the authoritative field and state that the cache can be **smaller** as well as larger. New register row **MD_DATA_RA_021**. |
| **Found by** | The external v1.8 audit (C1), independently reproduced and then extended here — the audit reported only the over-read direction; the corpus census found the truncating direction, which is the more serious of the two. |


<a id="e77"></a>
## E77 — `key_flags` encodes record placement, not data residency; `$OBJ_LINK` is one row per NAME; CHKP `+0x58` is the self-descriptor offset

Three reference pages had drifted behind the register and the disk. An external review of v1.8.0 identified
all three; each was re-measured **corpus-wide** here before being written, and one of the review's proposed
corrections was **rejected** on that evidence (below).

| | |
|---|---|
| **1. `key_flags` ≠ residency** | `resident_storage.md` and `directory_entries.md` mapped `key_flags` 0x01 → "resident file / inline data" and 0x02 → "non-resident file / extent references", and instructed readers to *"read content from the row when key_flags is 0x01 and follow extents only when it is 0x02"*. **Falsified.** 0x01 means the name row **embeds the file's record**; 0x02 means it is an **index entry** whose record was split into a type-0x40 backing in the home directory. Neither says where the data is. **Measured:** every kf=0x01 *file* row is extent-backed on ReFS **3.4 / 3.7 / 3.9 / 3.10** — 1,120 / 250 / 386 / 236 rows, **zero inline**; on **3.14** 219,960 of 236,769 (93 %) are inline and 16,809 are not. Residency must be read from the `$DATA` attribute's storage. **CORRECTION 2026-09-02:** this cell originally added "which is what the tools already do — so no tool output was wrong, only the pages". That was **too strong** — it was inferred, not measured, and the measurement above covered only the `kf=0x01` direction. For `kf=0x02` the reader sets `is_resident=False` **unconditionally** (`forefst.py:3551`) without consulting the backing's `$DATA`, so a split-record file whose `$DATA` is the **resident** form (`summary@0x0C=0x30`, `storage_type=0`, size@`+0x20`, content@`+0x3C`) is reported non-resident and its content is never read — `extract` fails with "no extents decoded" although the bytes are in the record already held. Measured: **16,191 files over 26 images** (winsider 14,580 of 72,709); content validated (400/400 lengths, 56/57 XML well-formed) and **byte-exact on 7/7 hard-link files against the lab generator's own recorded content**. Static: the driver validates with `RefsCheckValidResidentDataAttribute` and reads the attribute **in place** (content at header+0x38), never consulting a name-row placement flag. The STRUCTURAL claim of this row stands; only its tool-impact parenthetical was wrong. |
| **2. A kf=0x02 file row is a move/hard-link fingerprint** | Not a residency statement. On the audited 2 TB volume **51/51** such rows are moved (49) or hard-linked (2). Version-scoped: the form does not exist on **v3.4**, which has **0** type-0x40 rows and **0** kf=0x02 *file* rows (only kf=0x02 directories, 72-byte values). |
| **3. `$OBJ_LINK` is per-NAME** | `OBJ_LINK.md` stated twice that the row is *"one-per-object: creating a hard link adds no new `$OBJ_LINK` row"*. **Falsified.** The number of **distinct `(parent OID, name)`** 0x39 pairs in an object's backing equals the number of directory entries pointing at that object on **40,966 of 40,966** backings — v3.7, v3.9, v3.10, v3.14 — for objects carrying **1 to 19** names, **0 mismatches**. Two caveats the count must handle: some backings carry the *same* pair **twice**, byte-for-byte (deduplicate; not an artefact of the E73 descent — the duplicate is present with the descent disabled), and the rows exist only on objects with their own record — **0 of 219** embedded (kf=0x01) file rows carry one, and on **v3.4 no directory carries one** (0/309). |
| **4. CHKP `+0x58`** | `chkp.md` called it *"Table descriptor end"*. It is the in-page offset of the checkpoint's **own page reference**: the reference there has slot 0 equal to the checkpoint's own LCN on **95/95 corpus images, every version** (0xD0 on v3.4–v3.10, 0xE0 on v3.14+, 0xE8 on some v3.14). Where the `0x88`/`0x8C` pair is populated, `0x88 == 0x58 + 14 × 0x5C` (**76/95**) — the self-descriptor plus 13 roots; on 19 v3.14 images **both fields are zero**, which the page already documented and the review's proposed relation did not allow for. The `0x94` field-table entry also said *"pointer to root list page"*, contradicted two sections later on the same page: in indirect mode it is an in-page **offset to an array of 13 offsets**, not a pointer to another page. |
| **5. Object Table `+0x40`/`+0x48`** | Documented as *"unconfirmed structured u64"* and *"probable per-object identifier"*. They are the checksum descriptor and the **digest of the object's root page**: recomputing the checksum over the referenced page reproduces `+0x48` on **34,108 of 34,108** rows corpus-wide (CRC64 and SHA-256, v3.4 → Insider). The only **20** mismatches are all on one known-damaged volume family — the check working as intended. So `0x20–0x50` is a complete page reference, and the 80-byte / 104-byte row sizes are header + one reference. |
| **6. Node-header invariant** | `btree_node.md` documented only `+0x0C`/`+0x0D`/`+0x14`. Added `+0x10` (key-index start) and `+0x20` (end), the 4-byte entry stride, and the invariant `(+0x20 − +0x10)/4 == +0x14` — **118,351 pages, 0 violations**, all seven versions. Also recorded that a page is **four clusters** at 4 KiB, so reading one cluster puts the key-index array out of range and silently yields a zero row count. |
| **REJECTED recommendation** | The review proposed replacing `MD_DATA_RA_015`'s *"rarely [on] native v3.14"* (for the inline-holder extent-backed form) with *"the measured majority (206/258)"*. That figure comes from **one image**, `win11refs2tsnapshots`, which is atypical. Corpus-wide on v3.14 the form is **16,809 of 236,769 kf=0x01 file rows — 7.1 %**, so the existing wording is **correct** and the proposed change would have introduced an error. `MD_DATA_RA_015` is left as it stands. |
| **Also corrected** | The metadata CRC64 is not a "custom polynomial": it is **CRC-64/NVME** (Rocksoft) — poly `0xAD93D23594C93659`, reflected `0x9A6C9329AC4BC9B5`, init/xorout all-ones, check value `0xAE8B14860A799888`, which the reader's own implementation reproduces exactly. Named in `checksum_architecture.md`, `page_references.md`, `vbr.md`, `glossary.md`, `driver_architecture.md`. The `CmsChecksumNone` "written but never verified before v3.14" claim is now marked as **read from the driver, never tested behaviourally**; the `$J` in-place-ring window model as **inferred, no wrapped journal observed**; and the MLog per-record XOR-fold as **not reproduced** (byte range, stride and init unpinned, so nothing verifies it). `vbr.md`'s "Always 512" is now scoped to the corpus, with 4Kn untested. |
| **Process** | `methodology.md` now states that the audit gate covers the **claim register, not page prose**, so a page can drift behind a corrected row without the gate noticing — which is exactly what happened to all three pages above — and that where a page and a finding row disagree, the register plus its errata wins. |
| **Tool impact** | **None.** Every item is a reference correction; the code already behaved correctly in each case. |
| **Update (2026-11-21, the later census K114; RUNNING_LOG N639)** | Item 3's last clause does not hold: on ReFS 3.4 every directory carries an `$OBJ_LINK`, the marker-less type-0x38 row (its type at key+0x08): **445 of 445** directories over the 13 v3.4 image paths (439 of 439 over the 12 distinct images), and the rows decode as back-pointers equal to the tree on 148 of 148 non-root directories of `win10refs2tspecials` and 5 of 5 of `win10refsmini` (`analysis/reports/RC3_1.13.0/CORRECTIONS.md` K114; MD_LK_RA_005's own census counts 509 type-0x38 entries on the v3.4 images). The "0/309" was most likely a scan that matched only the v3.7+ marker form (0x80000002 + type 0x39; K114's reading). Item 3's per-name rule (40,966 of 40,966, v3.7-v3.14) stands. |


<a id="e78"></a>
## E78 — The MLog per-record integrity value is reproducible: a four-way interleaved u64 XOR fold

E77 recorded the MLog per-record XOR-fold as **not reproduced** — byte range, stride and initial value
unpinned, so nothing could verify a log record. The algorithm has now been pinned and implemented, and it
reproduces **every** record in the corpus.

| | |
|---|---|
| **Where** | 8 bytes at `entry_header + 0x08`, i.e. `page + le32(page, 0x54) + 8` (= page+0x80, the entry-header offset being 0x78 on every corpus volume). |
| **Algorithm** | Zero the 8-byte field itself. Then, for each log block of `le32(page, 0x0C)` bytes (`0x1000` on every volume, independent of cluster size): `acc[i mod 4] ^= ` each little-endian u64 of the block; `v = acc0^acc1^acc2^acc3`; `result = (v >> 32) ^ (v & 0xFFFFFFFF)`. Blocks chain — the next block's `acc[0]` is seeded with **rotate-left-1** of the previous block's result. A record is exactly one block, so in practice the seed is 0. |
| **Scope** | Present on **both** LogCore record types (`entry_header + 0x30`): **type 1** = control page, **type 2** = data record. No other type exists on disk. |
| **Evidence (RD)** | Whole 99-image corpus: **599,039 of 599,039** data records and **95 of 95** control pages recompute exactly — ReFS 3.4 → 3.15 + Insider, 4 K and 64 K clusters, **0 mismatches**. Every MLog-signature page in every data area is type 2 (599,039/599,039). |
| **Evidence (adversarial)** | 2,000/2,000 random single-bit flips detected; a `0x01` flip at **every one of the 4,096 byte offsets** is detected (0 blind offsets); corrupting the stored field itself is detected; 500 records carry 500 distinct values, so the check is not vacuous. End-to-end on a tampered copy, `mlog --stats` reports the two flipped data records and the flipped control copy while leaving the intact copy verified. |
| **Honest limit** | It is an XOR fold, so it is an **integrity check, not a signature**: it catches any altered byte, but it is blind to a **reordering of 8-byte words that keeps each word in its own lane** (`i mod 4`). Stated in the tool output, the help and the reference. |
| **Static** | `LogCoreWriteDataRecord` writes it; `LogVerifyChecksumEntryHeader` → `LogChecksumBlock` verifies it on recovery; the 0x1000 block size is hard-set by `MlLogOpenLog`. |
| **Corrects** | The E77 line "the MLog per-record XOR-fold as **not reproduced**", and `checksum_architecture.md`'s "Algorithm not yet reproduced" note. New register row **AP_LGFL_RA_010**. |
| **Amendment (2026-11-12; RC1-docs G7; RUNNING_LOG N182)** | The "Honest limit" understates the blind spot. The four lanes are XORed together and then the two 32-bit halves, so with a seed of 0 (a one-block record) the result is the XOR of all the block's 32-bit words: it is blind to **any reordering** of those words, whatever their lane, and to any set of changes whose XOR cancels (win10refsmini's two differing control copies both store 0xfee0f4b8, the mlog critic's read). "Catches any altered byte" holds for a single altered bit or byte, not for several. Derived from the algorithm row above, which reproduces every record. Corrects master §E.2a, `docs/structures/mlog.md` and `concepts/checksum_architecture.md`; the tool's docstring and its Record Integrity preamble wording go with the code half. |
| **Tool impact** | New — `forefst.mlog_verify_record()` / `mlog_verify_pages()`, surfaced in `mlog --stats` (a Record Integrity section, plus a per-copy verdict for the two control pages) and in `mlog --json` (an `integrity` object). MLog records are no longer parsed without an integrity check. |
| **Update (2026-11-21, RC3a W1; RUNNING_LOG N663, N144, N651)** | Two parts of the Evidence row do not hold as written. (1) "3.4 → 3.15": no volume has format 3.15; the one image that reads 3.15 is a hand-edited 3.14 (**E96**), so the set was 3.4 to 3.14 and Insider. (2) "95 of 95 control pages ... 4 K and 64 K clusters": on a 64 KiB volume the tool of that date folded the whole 64 KiB cluster and seeded each block with a 64-bit shift instead of the driver's 32-bit rotate, and printed both intact control copies FAILED (N144; fixed in 1.14.0), so that count cannot have come from the tool's path on the 64 KiB volumes. Re-measured with the fixed fold on 2026-11-09: 886,932 of 886,932 data records and 248 of 248 control copies of the 124 ReFS volumes of `corpus.lst`, 64 KiB volumes included (`analysis/reports/v1.13.2/RC1D/evidence/measures/h08.jsonl`, `ctlok.jsonl`; N651; register AP_LGFL_RA_010, master §E.2a). |


<a id="e79"></a>
## E79 — The `$J` change journal is an in-place ring: observed, no longer inferred

E77 recorded the `$J` window model as **inferred, no wrapped journal observed**, and set out the exact
experiment that would settle it: *a journal whose highest USN exceeds its own allocation — then check whether
its extents start at VCN 0 and whether a record with USN X sits at offset X modulo the window.* That journal
was found in the corpus and the experiment was run.

| | |
|---|---|
| **Result** | **In-place ring.** A record whose USN is *X* sits at byte offset *X* **modulo the stream's allocation**; the extents begin at file **VCN 0**; old records are overwritten where they lie. NTFS-style front-trimming is refuted. |
| **The decisive volume** | `winsider.raw` — the only corpus journal that has **wrapped**. Allocation **33,554,432 B** (32 MiB; extents `(VCN 0, 6021 cl)` + `(VCN 6021, 2171 cl)` = 8,192 clusters exactly), highest USN **74,459,840** = **2.22 windows**. **All 217,892 records have USN ≥ the allocation**, so the modulo is never the trivial identity. |
| **The ring signature** | The buffer holds **two generations at once**, cleanly partitioned by position: generation 1 at offsets **7,352,320 … 33,554,168**, generation 2 at **0 … 7,350,976** — the write head sitting at ≈7.35 MB. Under front-trimming the live data would be one monotonic run starting past VCN 0. **0 violations.** |
| **Breadth** | 14 corpus journals, **338,439 of 338,439** records satisfy `USN mod allocation == offset`. |
| **Not circular** | `parse_usn_records` derives `offset` from its linear scan position and reads `usn` from the record body — the two quantities are independent measurements. |
| **Consequence for a reader** | The whole allocation must be read; **byte order is not time order**; and a highest USN larger than the stream size is normal, not corruption. |
| **Corrects** | The E77 line marking this "inferred", and the `usn_journal.md` caveat "This window model is inferred, not observed." New register row **MD_USN_RA_008**. |
| **Tool impact** | **None.** `read_usn_j_stream` already reads the full allocation, which is what the ring model requires. |


> **UPDATE 2026-11-18 (KNOWLEDGE_INTAKE A7, the D18 sweep):** the driver side, read twice: `RefsFileOffsetFromUsn` maps a USN
> to its file offset as the USN less the ring's base (VCB+0x3c8), wrapping at the ring's size (VCB+0x3d8) (26100.9549
> `refs.decomp.c` :182390-182398, Insider 29574 :178361-178369, 17134 :171219-171227). The master's LastUsn and USN rows
> now say "a virtual byte offset" (the file offset until the journal wraps).

<a id="e80"></a>
## E80 — Index-entry value size is fixed at WRITE time, so an upgraded volume carries both layouts

The 72-byte / 84-byte size of a type-0x30 index-entry value (`key_flags 0x02`) was documented as a
**version** property — 72 B on v3.4–v3.9, 84 B on v3.10+. The driver gate is real, but it applies when an
entry is **added**, not to the volume: existing entries are never rewritten, so a volume upgraded across the
v3.10 boundary carries **both layouts side by side**.

| | |
|---|---|
| **Rule** | Take the entry size from the **row's own length**, never from the volume version. Keying on the version misparses every retained entry on an upgraded volume. |
| **Evidence (RD)** | Whole 99-image corpus: **2,172** × 72-byte and **113,356** × 84-byte values. Exactly **3** images carry **both**, and all 3 are the corpus's **upgraded** volumes: `win10to11refs4g` and `win10to11refs4g_afterwin11mount` (32 × 72 B + 6 × 84 B), `win1122h2test_afteropenedwithinsider` (482 × 72 B + 333 × 84 B). Every **native** volume carries **one** size, matching its format-time version. |
| **Controlled before/after** | Two independent upgrade paths, same volume imaged either side: `win10to11refs4g_beforewin11mount` (v3.4 — 33 × 72 B, 0 × 84 B) → `win10to11refs4g` (v3.14 — 32 × 72 B **retained** + 6 × 84 B new); `win1122h2test` (v3.9 — 482 × 72 B, 0 × 84 B) → `win1122h2test_afteropenedwithinsider` (v3.14 — the **same 482** × 72 B retained + 333 × 84 B new). |
| **Static** | `RefsAddFileNameIndexEntry`: value length `0x48` when version < `0x309`, else `0x54`. A gate on **add**, which is why retained entries survive an upgrade unchanged. |
| **Why it is safe** | Every field the tools read lives at or below `value+0x44`, identical in both layouts, so the length **range** test `0x48 <= len <= 84` is correct and version-independent. |
| **Corrects** | The version-keyed phrasing of the rule. New register row **FN_DTBL_007**. |
| **Tool impact** | **None.** `forefst` already tests the length range rather than the version, so no output was ever wrong — this pins *why* the range test is the correct form. |
| **Update (2026-11-21, the static readings S9; RUNNING_LOG N654)** | The 26100 and Insider drivers' gate is `< 0x309` (26100.9444 :127294-127297; the same on 26100.8115 / .9818 and Insider 29574 / 29683): they add 84-byte entries on a volume of format **3.9** or later and 72-byte ones below. The 72-byte entries of the corpus's native 3.9 volumes were written by the driver that formatted them (22621, not read). So the "v3.10 boundary" above is the boundary between the corpus's writers, not the 26100 gate; the rule (take the size from the row) is unchanged. |


<a id="e81"></a>
## E81 — A directory reparse point keeps its buffer in the object record's embedded attribute tree, not in a top-level `0xC0` row

Found by the Phase 4 self-audit (the second pass over the areas the external v1.8 review never covered).

| | |
|---|---|
| **Previous** | The reparse target was read only from a **top-level** type-`0xC0` row in the object's own B+-tree. |
| **Correct** | For a **directory** reparse point — a junction or a directory symlink — there is no such row. The object's table holds a **single row keyed `0x10`** whose value carries an embedded attribute tree (typically `0xC0` reparse, `0x90`, `0x39`), and the name row in the parent is an 84-byte index entry with no room for a buffer. The embedded `0xC0` value has a **12-byte header whose `u32` at `+0x08` is the offset** of the standard `REPARSE_DATA_BUFFER` (tag `u32@0x00`, `ReparseDataLength u16@0x04`, `Reserved u16@0x06`, then the SubstituteName and PrintName offset+length `u16` pairs; path buffer at `+0x14` for SYMLINK, which carries a 4-byte Flags field, and `+0x10` for MOUNT_POINT). |
| **Scale** | Of **341** reparse-bearing objects corpus-wide, **243** carry `0xC0` at the top level and **98 carry it only embedded** — including **78 of 81** on the one real Windows volume. Those 98 targets were reported as absent although they are fully present on disk. |
| **What was there** | Decoding them yields the expected Windows compatibility junctions: `\??\C:\ProgramData`, `\??\C:\Users\Default`, `Program Files`, `Common Files`, `Internet Explorer`, `Windows Defender`, `Microsoft Shared`, … |
| **Ground truth (non-circular)** | The lab generator writes its own CSV log **onto the volume**. Extracting `forefst_test2_log_20260705_085450.csv` from `win11refs8g` gives the 8 reparse points it created with their intended targets. Before the fix the tool found all 8 and resolved the **6 file** symlink targets byte-for-byte, but reported **no target** for the **2 directory** ones; after it, both resolve to the generator's recorded `R:\forefst_test2\reparse\rp_target_dir` — the junction via its NT-namespace SubstituteName `\??\R:\…`. |
| **Two decode rules this pins** | A junction commonly carries `PrintNameLength == 0`, so the **SubstituteName is the authoritative fallback** and the target must never degrade to the tag *name*. And the embedded parse must be given the descent context, or an object whose attribute set is large enough to become an **index node** is missed a second way — the same blind spot as **E73**. |
| **Same class as** | E73 (attributes in a child node) and E75 (the two embedded-key forms): the reader was looking at the wrong level, and a confident "none" came back. |
| **Corrects** | `get_reparse_target()`. New register row **FS_REPS_RA_005**. |
| **Tool impact** | **98 targets gained across 11 images, 0 changed, 0 lost** — strictly additive; no previously reported target moved. |


<a id="e82"></a>
## E82 — A split-out record can still hold the file's data: the backing's own `$DATA` is the *resident* form

Record **placement** and data **residency** are two independent axes (E77). A move or a hard link forces the
object's record out of the name row into a type-0x40 backing (`key_flags 0x02`) — it does **not** move the
file's bytes out of that record.

| | |
|---|---|
| **Already known** | §C.3a records that the backing's `+0x60` allocation is `== size` for *"small files stored resident inside the backing"* — **6,794 of 6,823** sub-cluster backings on `winsider`. The phenomenon was on record; what was missing was **how to read the content**, and every tool path treated a `key_flags 0x02` name as non-resident regardless. |
| **The decode** | The backing's **main** `$DATA` sub-record — single-instance marker `0x80000001` + type `0x80` — is the **resident** form: `summary_size@0x0C = 0x30`, `storage_type@0x10 = 0`, byte count at **`+0x20`**, content at **`+0x3C`**. The alternative is the extent-bearing stream record (`inner_hdr@0x00 = 0x88`, `summary_size` `0x200` on v3.14+ / `0x1A0` on v3.4–v3.10, extents at `+0x88`). The two are **mutually exclusive**: over 72,709 index-entry files on `winsider`, **no record carries both**. |
| **The marker matters** | An ADS is a **multi-instance** (`0x80000002`) `0x80` row. Matching *any* `0x80` row returns a stream that is not the file's data — it reported `hassrv.dll` as a 291-byte PNG. |
| **The join** | The backing is found by the **pair** `(stream_idx = name value+0x00, home = name value+0x08)` → backing key `(+0x08, +0x10)`. Stream indices are unique **per home**, not globally; joining on the index alone silently mixes files up (it reported a `.json` file as containing PNG bytes). |
| **Scale** | **16,191 of 83,176** index-entry files across **26 images** keep their data this way; `winsider` alone 14,580 of 72,709. |
| **Content validated** | Over 400 sampled files: **400/400** inline length == the stated size == the name's cached size; **56 of 57** `.xml` parse as well-formed XML; **13/13** `.png` carry the PNG magic; **5/5** `.json` parse. |
| **Byte-exact ground truth** | The lab generator wrote `hl1_/hl2_/hl3_` hard links as exactly 400 bytes of a repeated marker (`New-Marked "HL1BODY_" 400`). Recovered content is **byte-exact on 7 of 7**, and those files now extract byte-exact through the tool. |
| **Static (E2)** | The driver's read path validates the attribute with `RefsCheckValidResidentDataAttribute` and reads the bytes **in place**, content at header `+0x38` (= value `+0x3C`). It never consults a name-row placement flag — residency is a property of the **attribute**. |
| **Corrects (tools)** | `extract` / `dataruns` / `export` failed with *"no extents decoded"* on these files while their bytes sat in the record already held; they now read them. The reported `IsResident` — documented as *"the current `$DATA` stream is inline"* — was `False` for all of them and is now correct. **Internally** the flag keeps a second, narrower meaning ("the record is embedded in this name row"), which is the right gate for the ADS / snapshot / inline-reparse readers and for hard-link grouping; reporting ORs the two, so a hard-linked file with inline data is reported resident **and** keeps its link count. |
| **Corrects (pages)** | `hard_links.md` said a hard link *"promotes the file to non-resident"*. It promotes the **record** out of the name row; the data can stay inline — `hl1_a/b/c` are three names over one 400-byte inline stream. |
| **Residual** | On `winsider`, **548 of 14,580** keep `IsResident=False`: their name did not size-match the backing during hard-link grouping, so the flag is not propagated. **Extraction is unaffected** — 15/15 sampled extract with the correct size. Reported rather than forced, because the record those names *do* resolve to is the one exposed to `file_id` collisions. |
| **New register row** | **MD_DATA_RA_022**. |
| **Update (2026-11-21, E165; RUNNING_LOG N638)** | The "marker matters" row's first sentence does not hold: a multi-instance (`0x80000002`) `0x80` row is the **extent form of the main `$DATA`** (its sub-stream records 0x8, 0x1000 and the snapshot versions 0x1001 and up, E165), not an ADS; an alternate data stream is a type-0xB0 row (`$NAMED_DATA`; E87's census: 8,238 named streams, all 0xB0). The row's rule stands: the main stream's inline form is the single-instance 0x80 row, and matching any 0x80 row picks the wrong one. |


<a id="e83"></a>
## E83 — A snapshotted file's blocks are SHARED across streams: the current stream owns only what changed since the last snapshot

ReFS stream snapshots are copy-on-write. A block is duplicated only when it is about to be **overwritten**;
every block not yet modified since a snapshot stays **shared** — present once on disk, listed in the
snapshot's extent table and **absent from the current stream's**. Reading any version therefore means
resolving each file VCN across the streams, exactly as the driver does.

| | |
|---|---|
| **The two allocation fields, now distinguished** | `total_alloc@0x30` and `disk_alloc@0x48` were both listed in the `$DATA` stream record with no note on how they differ. **`disk_alloc` is what THIS stream owns** (what its own extent list covers); **`total_alloc` is the file's whole allocation**, including blocks the stream does not own. Measured over **38,378** stream records: with no snapshots they are equal on 38,286 and differ on 38 (sparse holes); with snapshots present they differ on **39 of 54**. |
| **Worked example** | `snapfile_03.txt` (`win11refs8g`): current stream `0x1000` reports `stream_size` 22,688, `total_alloc` **24,576** (6 clusters) but `disk_alloc` **8,192** — its own extent list holds exactly 2 extents, for file VCNs **4 and 5**. VCNs 0–2 live in snapshot `0x1001`, VCN 3 in `0x1002`. The extent-count field in the record confirms 2, so this is the on-disk truth, not a parse gap. |
| **Resolution rule** | For the **current** stream, a missing VCN comes from the **newest** snapshot that holds it — a block only leaves the current stream's table while it has not changed. For a **prior version**, only snapshots **strictly older** than it may be used: a newer snapshot can hold content written *after* the version being recovered. A VCN no stream holds is a genuine **sparse hole** and stays zero. |
| **What was wrong** | The reader assembled a stream from its own extents alone and treated every other block as a sparse hole. `extract` returned the **full size with the shared blocks zero-filled** — bytes that exist nowhere on the volume — and said nothing. `snapshots --extract` concatenated a version's own extents, producing a short, offset-shifted file (it did at least print `size=14888 -> 4096 bytes`). |
| **Scope** | **8 distinct files** (32 rows across 4 images of one lab family), **655,360 bytes** silently zero-filled. **Zero on the real Windows volume** — it needs `refsutil streamsnapshot` followed by a modification. Where the current stream owns **no** clusters at all (snapshotted, never modified) the pre-existing CoW fallback already handled it correctly, which is why a first structural count of 39 files / 14.1 MB **overstated** the defect. |
| **Ground truth** | The lab generator wrote each `snapfile_NN.txt` as `4096×N` bytes of a marker, then snapshotted and appended in a recorded sequence. After the fix: **8/8** current files and **20/20** prior versions are **byte-exact** against that specification (the versions were **8/20** before). Sparse files are byte-identical and their holes remain zero. |
| **Corrects** | `_recover_inline_extent_content` and `recover_snapshot_streams` (new helper `_snapshot_shared_blocks`). §C.6's `total_alloc` / `disk_alloc` rows. New register row **MD_SNAP_RA_008**. |


<a id="e84"></a>
## E84 — The two refsprogs-sourced claims resolved: one refuted and decoded, one confirmed and sharpened

Both had defeated two earlier attempts (A3c) because the *probe* was at fault, not the claim. Measured here
over the whole corpus with the population selected structurally rather than by a byte test.

### GN_TREE_RP_002 — **REFUTED**, and replaced with a verified decode

Claimed: the row-index slot's second `u16` is a cumulative cluster count in extent nodes, saturating at
0xFFFF.

| | |
|---|---|
| **Refutation** | Across **843,408** page-level slots the field takes exactly **two** values — `0xFFFF` on 842,529 and `0` on 879 — and **nothing else**. It cannot be a count. |
| **What it is** | A marker on the row-index slot. `0` appears **only on inner nodes, exactly once per page, always the LAST slot**, and always on a row with an **empty key** (`key_offset 0x10`, `key_size 0`) whose value is a 48- or 72-byte page reference — the B+-tree's **rightmost child pointer**, the child covering keys above every separator. `tag == 0 ⟹ empty key` holds **879/879** with no exception. |
| **Not a biconditional** | The converse fails: **269** keyless rows carry `0xFFFF`. |
| **Version boundary** | The `0` marker is written from **v3.10** onward (879 pages across v3.10/3.14/3.15 and the version-tampered 6.66); on **v3.4–v3.9** the same keyless slot carries `0xFFFF` — **216 pages, 0 exceptions**. |
| **The 53 v3.14 exceptions** | **48** are the three **upgraded** volumes (`win10to11refs4g`, `…_afterwin11mount`, `win1122h2test_afteropenedwithinsider`) retaining pre-upgrade pages — the same write-time retention as **E80**. The other **5** are one page each on the five 2 TB volumes, all the same structure: table **0x0B** (Container Table), an inner page with 189 slots. |
| **Leaves** | **0** leaf slots carry the marker — 15,642 leaf pages, all `0xFFFF`. |
| **Update (2026-11-21, the later census K101; RUNNING_LOG N639)** | This census does not hold beyond its own population. Over every MSB+ page of the 25 baseline images whose index array satisfies `(u32 +0x20 - u32 +0x10) / 4 == u32 +0x14` (15,169 pages, 689,639 key-index entries) the marker takes **38 values**: `0xFFFF` on 685,755, `0` on 963 and 2,921 at 36 others (`0x1` x1,085, `0x4001` x515, `0x8001` x285, ...); `0` sits on 67 leaf (level-0) entries and on 44 that are not a page's last, and 467 of the 1,363 index pages of 3.10+ volumes carry no `0` (`analysis/reports/RC3_1.13.0/CORRECTIONS.md` K101, with a reproducible read of three `win11refsmini` pages, e.g. leaf page 0x1024000, table 0x22: markers `0x1` / `0x3fdd`). So `0` is a tendency of the rightmost-child row, not a test for it, and the refutation's argument (two values, so not a count) no longer stands: what the other values are is not read. |

### MD_ADS_RP_001 — **CONFIRMED**, and sharpened into an exact test

Claimed: a named-stream extent key is identified by `key_offset == 0x10 && key_size == 0x50`.

| | |
|---|---|
| **`key_offset == 0x10`** (the untested half) | **CONFIRMED** — holds on **2,908/2,908** records the shipped reader resolves, and on 2,994/2,994 in a wider structural population. |
| **`key_size == 0x50`** | **CONFIRMED as the identifier**, but only together with the attribute type: the real record is a 0x50-byte key carrying **`0x0003` at `key+0x08`** — **657/657**, every one with a plausible stream size at `value+0x38`. |
| **What the old test also matched** | A **different** record: a 14-byte key whose type at `key+0x08` is `0x0080`. There are **2,382** of them, and `value+0x38` is **not** a stream size there — implausible (larger than the volume) on **2,330 of 2,350**. |
| **The key carries no name** | Neither form holds a decodable UTF-16 stream name; the name lives in the `0xB0` descriptor, which links to the extent record by **stream size** (E61). "Named-stream extent key" describes what the record *is for*, not what its key contains. |
| **Tool impact** | `_stream_extent_records` filtered on `len(k) > 12 and k[12] == 0x00` — for a 14-byte key `k[12]` is padding, so the wrong record type was admitted. **Measured impact: 0** — no loose row shares a real record's stream size on any corpus image, so nothing was ever mis-resolved. Tightened to the exact test (`key_size 0x50` + type `0x0003`); `ads --json`, `files --csv` and `specials --json` are **byte-identical on 297/297** runs across the corpus. |
| **New register rows** | **GN_TREE_RP_003** (slot marker) and **MD_ADS_RA_002** (stream-extent key shape). |


<a id="e85"></a>
## E85 — The inline extent decoder validated a VIRTUAL cluster number against the PHYSICAL cluster count

A file whose `$DATA` extent map is held inline in a `0x10028` holder is decoded by `_decode_inline_extents`,
which screened each entry with a plausibility test `0 < vlcn < ncl`, where `ncl` is the volume's **physical**
cluster count.

| | |
|---|---|
| **Why that is wrong** | A `vlcn` is **virtual**. The container table maps it to a physical cluster, and the virtual address space is wider than the physical one — it begins at `first_container_id << shift` and runs roughly twice as far (**E74**). Bounding a virtual address by the physical count therefore rejects every extent living in the upper half of the virtual space. The decoder stops at the first rejected entry, so the whole map decodes as empty and `extract` reports *"inline-holder-overflow"*. |
| **Worked case** | `win11bidule` `logs/allfiles.csv` (60,490 B): the holder carries exactly 2 extents — `vlcn 0x17a799, fvcn 0, run 1` and `vlcn 0x17a79a, fvcn 1, run 14` — a contiguous 15-cluster cover matching `alloc` 61,440. `vlcn 1,550,233` exceeds the physical count 1,044,480 and was rejected, yet it translates cleanly to **PLCN 731,033**. Reading those 15 clusters by hand reproduces the volume's own recorded SHA-256 exactly. |
| **Scale** | On that volume, **583 of 629** files with a recorded hash could not be extracted. |
| **The fix** | When a translator is available, the authoritative test is whether the **container table can map the VLCN**; the physical bound is kept as the fallback for callers that have no translator. Strictly additive — it can only accept extents that were previously rejected, and the existing coverage gate (extents must cover exactly `disk_alloc`, contiguously, within the file) still rejects a wrong parse. |
| **Effect, measured** | `win11bidule`: files matching their recorded SHA-256 go from **41 to 608 of 629** — every remaining one is a large file (1 MB–791 MB) hitting the documented multi-page overflow-holder residual, and each still fails **cleanly**. Existing corpus: `extract` on all **95** golden targets is **byte-identical**, and every image's `dataruns` summary is unchanged (the fix touches content recovery, not residency classification). |
| **Why it was never seen** | It needs a volume whose live file extents sit above the physical cluster count in virtual space. No image in the 99-image corpus does; `win11bidule` — a 4 GB volume added 2026-09-02 with its own on-volume SHA-256 inventory — does, for 93 % of its files. |
| **New register row** | **MD_DATA_RA_023**. |


<a id="e86"></a>
## E86 — A file's extent map is a B+-tree NODE inside its `$DATA` record, not a flat run array

§C.3b closed with a documented residual: *"a file whose extent B+-tree spans child pages on separate LCNs
(not inline in the value) is not walked; it fails the cover check and `extract` stops with 0 bytes."* That
residual is now decoded, and the structure turns out to be more general than "sometimes there is a child
page" — **the extent map is always a B+-tree node**, and the flat run array previously assumed is only what
that node looks like when it holds one row.

| | |
|---|---|
| **The node** | The current stream's `$DATA` value carries, at **`value+0x88`**, a node with the standard `0x28`-byte header: **level** at `+0x0C` (**0 = leaf**, non-zero = index), **row count** at `+0x14`, **node size** at `+0x20`, and a **trailing index array** of 4-byte slots (`u16` row offset, `u16` key hint = the row's file VCN, truncated). |
| **Leaf rows** | Standard **24-byte §C.4 extent entries** — VLCN `+0x00`, file VCN `+0x0C`, run `+0x14` — i.e. exactly the offsets already read for type-0x40 records. |
| **Index rows** | The row **value** is the standard **48-byte, four-LCN node reference**. Those LCNs are **virtual** (translated they land on a valid `MSB+` page). The child page carries the same node at **`0x50 + u32@page+0x50`**, so the walk is uniform and recursive. |
| **New field: `record_size` at `+0x0A`** | `24` for a plain run, and **`24 + run*4`** when the stream carries **per-cluster CRC32-C** — the trailing `u32`s being those checksums, **4 bytes each**. Flag bit **`0x80`** at `+0x08` says which. Measured over **48,474 records across 40 images: 0 violations** of `record_size == 24 + (flags & 0x80 ? run*4 : 0)`. The field takes **136 distinct values** (24 … 1048), and for checksummed records it tracks the run across the full observed range — run 11 → 68, run 66 → 288, run 100 → 424, run 122 → 512, run 223 → 916. A field with 136 values is not the high half of a flags constant. |
| **Records are 8-byte aligned** | The step to the next record is **`roundup8(record_size)`**, not `record_size`. Measured on **30,524 consecutive row pairs: 30,405 (99.6 %) match**, of which 428 are genuinely padded (an odd run makes `24 + run*4 ≡ 4 mod 8`); the remaining 119 are larger gaps — unused space in the node, which is harmless because rows are addressed by the index array, not by stride. |
| **Why the integrity files were the ones that failed** | The previous walk advanced `32 if the u32 at +0x08 == 0x1c00d0 else 24`. That constant is `(record_size 28) | (flags 0xd0)` — the **run == 1** case. A checksummed record with run 122 has `record_size 512`, so the u32 is `0x020000d0`, the test fails, the walk advances 24 and lands **mid-record**. The coverage check then rejected the whole map. That is precisely why **19 of the 21** unreadable files on the reference volume were integrity streams. |
| **Correction to §C.4 / §C.4a** | The entry's `+0x08` is **not** a `u32` flags field. It is **`u16` flags at `+0x08` + `u16` row_size at `+0x0A`**. Reading the pair as one `u32` yields `(row_size << 16) \| flags` — which is precisely why *every* documented flag constant begins `0x18`: that is **24, the plain row size**, not part of the flags. Observed flag lows are `0x40`, `0x50`, `0x60` (plain, row_size 24) and `0xD0` (`0x50\|0x80`, checksummed). The old reading is harmless on plain rows and wrong on checksummed ones, where the "flags" would appear to change with the file's length. |
| **Selecting the right row** | The `$DATA` row **must** be selected on the **sub-stream id at `key+0x10` == `0x1000`**. A file with snapshots carries one `$DATA` row per version under the same key prefix (`0x1001`, `0x1002`, …). Choosing by value size or first match returns a **snapshot's** extents, and therefore that older version's bytes presented as the live file — observed concretely on `win11bidule` `tests/secret.txt`, where it produced the 79-byte pre-truncation text instead of the live 25 bytes. |
| **Effect, measured** | `win11bidule` against the operator's own SHA-256 inventory: **608 → 629 of 629 files match, 0 mismatch**. The 21 that previously failed were all > 1 MB (19 of them integrity streams, plus a 782 MB archive and a 791 MB ISO) and each had failed **cleanly** with 0 bytes. Verified end to end through `extract`, including the 791 MB file. The structure is not rare: **54 of 100 corpus images** contain files whose map is such a node. |
| **Why it stayed hidden** | The single-row case *is* a flat array at `value+0x88`, so the old contiguous-array scan read it correctly and every small file worked. Only a file needing a second row — in practice past about a megabyte — exposes the node framing, and the cover guard then correctly refused rather than emitting a partial map. |
| **Implementation** | `_extent_node_rows` / `_extent_node_map` / `_embedded_data_extents`, wired as a **fallback only** — it runs where the existing cascade yielded nothing, so no file that resolved before can change. The `_contiguous_cover` guard is still applied to the result, so an incomplete walk still yields no extents rather than wrong bytes. |
| **Two defects the change exposed** | `tr.tr()` does **not** raise on a container-table miss — it falls back to **identity** (VLCN read as PLCN) and counts the miss. A decode that calls it directly would therefore accept an unmappable row and **read the wrong clusters**; mappability is now tested as `(vlcn >> tr.shift) in tr.map`, without the counter. And because that counter is surfaced as *"N VLCN(s) had no container mapping — output may be incomplete"*, probing rows that never become extents moved a number the analyst reads as evidence of damage (541 → 550 on one image, nothing actually incomplete). Translation is now deferred until a cover is accepted. With both fixed, `dataruns` is byte-identical to the previous release on every corpus image. |
| **New register row** | **MD_DATA_RA_024**. |

<a id="e87"></a>
## E87 — E70's "a move forces the file NON-RESIDENT" is a PLACEMENT statement, not a residency one; and the residency decision itself is a volume-format gate at 2 KiB

| | |
|---|---|
| **Previous** | **E70 / `FS_MOVE_RA_001`** is titled *"A cross-directory MOVE forces the file NON-RESIDENT (one-way ratchet)"* and states that a move *"converts a resident file to NON-RESIDENT"*, that *"a cross-directory HARD LINK likewise forces the object non-resident"*, and that *"a move-back stays non-resident"*. **E77** (item 1) and **E82** later established the opposite reading — `key_flags` encodes **record placement**, not data residency — but **E70 itself was never corrected**, so the reference carried two contradictory statements about the same operation, with E70's title the more visible. The residency *decision rule* was documented only as a size "threshold table", never read from the driver. |
| **Correct** | **Two independent properties were both being called "resident".** **A = record placement:** the file's record is either EMBEDDED in its type-0x30 name row (`key_flags 0x01`, §C.2 layout) or SPLIT into a type-0x40 backing record (`key_flags 0x02`, §C.3 layout, carrying the frozen home backref at `value+0x08`). **B = data residency:** the `$DATA` bytes are either INLINE in the record or in on-disk extents. **E70's observation is correct and stands in full for A — a cross-directory move and a hard link both force the SPLIT, one-way. E70 is wrong only where it names that outcome "non-resident": neither operation moves a single byte of file data.** Every consequence E70 draws for identity (frozen `(home, ordinal)` FileRef, monotonic non-reused ordinal, ExternalFileId untouched, rename/copy corollaries) depends solely on A and is **unaffected**. **The residency decision (B) is a volume-format gate, not a property of moving:** `RefsAddAllocationForResidentWrite` branches on the **volume format version** read from the VCB (`CONCAT11(vcb[0x318], vcb[0x319])`, compared against `0x30b` = 3.11 and `0x309` = 3.9) — *(a)* on format **< 3.11** a resident write larger than **`0x20000` (128 KiB)** raises **`0xC0000427` STATUS_FILE_SYSTEM_LIMITATION**, and the v3.4 driver reaches that branch through a function named **`RefsTelemetryUnsupportedADS`**, which identifies the 128 KiB limit as the **named-stream (ADS)** limit; *(b)* the residency branch proper is `if (format < 0x30b || size < 0x800) stay resident; else RefsConvertToNonResident()` — so **`0x800` = 2048 bytes is the inline ceiling on format ≥ 3.11**, and on format **< 3.11 an already-resident stream never converts at all** (consistent with `RefsConvertToNonResident` being **absent from the v3.4 driver**). Because main `$DATA` is never *created* resident before format 3.11, the net effect on ≤ 3.10 volumes is that **main `$DATA` is always extent-backed** while named streams are always resident up to a hard 128 KiB cap. **Three further triggers convert an already-inline stream to extents, independent of size:** taking a **stream snapshot**, enabling **integrity streams**, and the other callers of `RefsConvertToNonResident` (duplicate-extents/block-clone, encryption, remote/tiering, strictly-sequential, explicit set-allocation / set-EOF). **The gate reads the volume's format, so an upgrade changes future writes only — it converts nothing retroactively.** |
| **Evidence (disk, controlled)** | **Whole-volume before/after a move+hard-link session** (`win11refs8gtestmove_{before,after}move`, the very images E70 was written from): of **9,521 files present in both**, **2 changed A** (`hl.txt`, `haha2_10021.txt`: EMBEDDED→SPLIT) plus **3 relocated** to a new parent (`move.txt`, `haha2_10011.txt`, `haha2_10070.txt`, all EMBEDDED→SPLIT) — and **0 files changed B**. `move.txt`'s `$DATA` sub-record is **byte-identical** before and after (76 B, sha1 `ccb1c73861f55f14`), its inline payload `ff fe` + `hello\r\n` sitting at `value+0x3C` in both; before it is read out of the name row, after out of the type-0x40 backing `0x761:0x2`. **Hard link, independent image and file:** `forefst_test/hardlink_{target,alias}.txt` (300 B) on `win11refs8g` — both names A=SPLIT, both resolving to backing `0x74c:0x4`, both **B=INLINE**, payload sha1 `5958f030…` identical to the 300 bytes `extract` writes (`HARDLINKBODY_…`); size at `+0x20`, 8-byte-aligned allocation 304 at `+0x18`/`+0x30`. Ground truth for which files were hard-linked comes from the generator's own `fsactivity_baseline.json` (`CREATE_HARDLINK` actions), not from the tool. |
| **Evidence (disk, corpus)** | Two-axis census over **corpus manifest r2** (`analysis/corpus_manifest.csv` + `corpus_manifest_notes.md`: 128 paths, each identified by SHA-256 over its **non-zero 64 KiB blocks with their offsets** — a value independent of how sparsely the host stores the image, verified identical on a dense copy). **Definition — one unit, stated once:** a row is one type-0x30 **file name row**, so a hard-linked object contributes one row per name; no row is excluded; the **eight** observed A×B states — EMBEDDED×{INLINE, EXTENT, EMPTY, SHARED, UNALLOCATED} and SPLIT×{INLINE, EXTENT, EMPTY} — partition the total exactly. Two denominators, both reported; the **deduplicated one is the citation target** because paths are not volumes: **79 distinct volumes / 507,433 rows** (primary) and **117 openable paths / 523,756 rows** (as measured) (deduplicated by content hash — 38 paths are byte-identical copies of another, including a 23-path chain that is a single volume, and `win11refs8gtestmove.raw` which is byte-identical to its own `_aftermove`). **Per path:** EMBEDDED×INLINE 394,004 · EMBEDDED×EXTENT 43,888 · EMBEDDED×EMPTY 2,370 · SPLIT×INLINE 14,666 · SPLIT×EXTENT 67,294 · SPLIT×EMPTY 1,525 · SHARED 7 · UNALLOCATED 2 = **523,756, sum closes**. **Deduplicated:** 384,578 / 38,818 / 2,268 / 14,647 / 65,596 / 1,517 / 7 / 2 = **507,433, sum closes**. All four quadrants are populated either way, so placement cannot determine residency. **Format ≤ 3.10: INLINE = 0 and EMPTY = 0** on 7,006 rows / 18 paths (5,419 rows / 14 distinct volumes; v3.4, 3.7, 3.9, 3.10), smallest extent-backed **5 B** in a whole 4 KiB cluster. **Format ≥ 3.11: largest inline 2,047 B, 0 of 408,670 inline rows reach 2,048** — the driver's `0x800`; measured on **4 KiB-cluster** volumes, while 64 KiB volumes contribute only **14** inline rows (max 1,685), too few to establish a ceiling there. **Upgrade is not retroactive** (win10to11refs4g: 0 of 262 pre-existing files changed; the one inline file is one of 3 created after the upgrade). **Integrity streams force extents** (setintegritystreams 0 vs 1, same base volume: the same 4 small files flip INLINE → EXTENT). **E82 re-measured, with the deciding definition stated next to the number.** Under the rule adopted here — *the `$DATA` descriptor's own form decides, for empty records too* — the split rows holding their data in the record are 14,666 INLINE + 1,525 **inline-form** empties = **16,191** of 83,485, on 26 paths: E82's own figure. The alternative reading, *count every 0-byte split record as inline* (the pre-E88 reader behaviour), gives 14,666 + all 2,253 split empties = **16,919**, which does **not** match. So E82's count already keyed on the descriptor form; its **conclusion stands and its arithmetic agrees with the adopted definition**, and the agreement is only meaningful with that definition attached. The **728** split empties whose descriptor is the *extent* form are counted in SPLIT×EXTENT, not here. E77's v3.14 counts came from a smaller corpus and are cited as history only. *(Provenance: the figures first written here — 436,078 rows / 112 images — came from a defective aggregation and a basename-keyed image set; superseded.)* |
| **SHARED needs a positive witness** | "Extent form + `disk_alloc == 0` + `size > 0`" also describes a fully **sparse** file that owns no allocation because nothing was written. SHARED is therefore claimed only when a **snapshot sub-record for the same stream exists** (an MI `$DATA` row with sub-id > 0x1000). Of the 9 candidates, **7 have that witness** (`test.txt` carries sub-ids 0x1001–0x1004 alongside its live 0x1000) and **2 do not** — `bigsparse.dat` (1,234,567,891 B) and `sparse.dat` (423,456,789 B), which are now labelled **UNALLOCATED**. An earlier form of the test, without the witness and without the `size > 0` requirement, mislabelled **1,626** rows, 1,123 of them on pre-3.11 volumes that have no snapshots at all. |
| **E82 reconciliation (verbatim)** | The count depends entirely on how a **0-byte split record** is classified, so the rule is stated with the number:<br><br>&nbsp;&nbsp;`rule` — `count` — `matches E82's 16,191?`<br>&nbsp;&nbsp;**pre-E88** (every 0-byte split record treated as inline): 14,666 + **2,253** = **16,919** — **no**<br>&nbsp;&nbsp;**adopted** (the `$DATA` descriptor's own form decides, empty records included): 14,666 + **1,525** inline-form empties = **16,191** — **yes**<br><br>Split rows with `size == 0` are **1,525 inline-form + 728 extent-form**; the 728 are counted in SPLIT×EXTENT. So **E82 already keyed on the descriptor form**: its conclusion stands and its arithmetic agrees with the adopted definition. The agreement is only meaningful with the definition attached. |
| **Evidence (named streams, disk)** | Census of **every 0xB0 row: 8,353 rows over 57 images, 0 unrecognised**. After excluding the 115 snapshot-name rows (below), **8,238 are true named streams**: **7,505 INLINE, 4 EMPTY, 729 extent-backed**. Classification follows the reader's own **E60** rule — an inline named stream stores its bytes *packed*, so `alloc == size`; when `alloc != size` the window at `+0x3C` holds descriptor tail, not content. **The 2 KiB rule is one-directional and exact in that direction:** **0** inline rows reach 2,048 B, and the 716 extent-backed rows of 2,048 B or more start at **exactly 2,048** — the driver's `0x800`, the same constant it applies to main `$DATA`, so one threshold governs both stream kinds on ≥ 3.11. Below 2 KiB a named stream is inline *unless the writer pre-allocated*: **13** sub-2 KiB rows are extent-backed, every one with `alloc != size` — `adstest` (30 B, alloc 4,096; the refsutil-streamsnapshot case already named in the reader's E61 comment) and 12 `SmartScreen` streams (7 B, alloc 4,096) on downloaded executables. `step6/win11refs8g` carries a deliberate `sweep` series across the boundary, and an `s_big` stream of exactly **131,072 B = 0x20000** which stores normally *because* the volume is v3.14 — that error branch fires only below format 3.11. **On format ≤ 3.10 every named stream in the corpus is INLINE** (3.7: 285, 3.9: 658, 3.10: 928) but all are ≤ **47 B**, so nothing on disk exercises the 128 KiB cap; it stays a static-only claim pending the lab test. **The documented attribute-flags word at `value+0x02` is the discriminator:** bit **0x1000** is set on **exactly** the 844 non-inline rows (729 extent-backed + 115 snapshot-name) and clear on **exactly** the 7,509 inline/empty ones — **0 violations**. (An earlier reading of this as a u32 "flags word at +0x00" was wrong: `+0x00` is the documented 2-byte padding and the flags are the u16 at `+0x02`, exactly as `NAMED_DATA.md` already had it.) |
| **Evidence (static, E2)** | The **complete** caller set of `RefsConvertToNonResident` in v3.14 (`refs.sys` win11 26100, @`1400e6080`) is `RefsCreateStreamSnapshot`, `RefsDuplicateExtents`, `RefsAddAllocationForResidentWrite`, `RefsReplaceDataAttribute`, `RefsSetEncryption`, `RefsCascadesSetFileRemote`, `RefsSetFileStrictlySequential`, `RefsSetAllocationInfo`, `RefsSetEndOfFileInfo` — **no rename, move or link function appears in it**. Scanned directly: **0 of 17** (v3.14) and **0 of 18** (v3.4) `Refs*(Rename|AddLink|RemoveLink|SetLinkInfo|MoveFile|StreamRename|ReplaceLinkInDir|UpdateLink)*` function bodies contain a call to it. The symbol is **absent entirely from the v3.4 driver** (present in win11 26100, win11 26100.8521 and Insider 29574, 15 references each; 0 in win10 17134), whose over-limit path instead calls `RefsTelemetryUnsupportedADS` and raises `-0x3ffffbd9` = `0xC0000427`, the same status its WPP trace logs literally. `RefsCheckValidResidentDataAttribute` — the *data*-specific validity check — likewise exists **only** in the v3.14-era drivers; v3.4 carries only the generic `RefsCheckValidResidentAttribute`. |
| **Sub-2 KiB extent-backed main streams (86 over 24 volumes) — trigger census** | Every identified trigger is a function in the `RefsConvertToNonResident` caller list: **13 encrypted** (EFS → `RefsSetEncryption`), **12 snapshot** (witnessed by a `$DATA` sub-id > 0x1000 → `RefsCreateStreamSnapshot`), **11 written under ≤ 3.10** before their volume was upgraded (the format gate), **6** on integrity-streams volumes. **44 have no identified trigger**, and their composition supports a specific hypothesis rather than randomness: 20 are a uniform 128-byte generator series on one image, and the rest are dominated by ETW `.etl` loggers, `Diagnostic.log` and browser-cache entries — writers that set allocation or end-of-file *before* writing. `RefsSetAllocationInfo` and `RefsSetEndOfFileInfo` are both in the caller list, so a tiny extent-backed stream is a plausible **fingerprint of a write through an allocation-setting path**. **Hypothesis, not a finding** — the lab test that would settle it is to create a 7-byte stream normally and a second after `SetLength` / `SetFileInformationByHandle(FileAllocationInfo)` and compare. Until then the 2 KiB rule is stated one-directionally: **≥ 2,048 ⇒ extents; < 2,048 ⇒ inline unless a conversion trigger fired.** |
| **Corrects** | **E70 / `FS_MOVE_RA_001`**: its residency wording only. Read "forces the file NON-RESIDENT" as "forces the record to be SPLIT out of the name row (`key_flags` 0x02 + type-0x40 backing)", "a move-back stays non-resident" as "stays split", and "resident files always have home == parent" as "files whose record is EMBEDDED always have home == parent". Its identity findings are untouched. Confirms and completes **E77** item 1 and **E82** by supplying the driver rule behind them. `structure_reference.md` §C.2/§C.3 — the layouts are placement forms; residency must be read from the `$DATA` attribute. Supersedes any size-only "resident threshold" table: the rule is two-axis (**stream kind** × **volume format**). New rows **`MD_DATA_RA_025`** (the format-gated residency rule), **`FS_MOVE_RA_002`** (a move/hard link changes placement only), **`MD_ADS_RA_003`** / **`MD_ADS_RA_004`** (named-stream threshold and the attribute-flags discriminator), **`MD_DATA_RA_026`** (the E89 reader defect), **`FS_RESD_SA_001`** (the conversion-trigger caller set), **`FS_RESD_SA_002`** (`RefsCheckValidResidentDataAttribute` per driver) and **`GN_VCB_SA_001`** (the VCB format field at +0x318). Rewritten: **`MD_ATTR_005`** (its circular value-length RD cell withdrawn, Prade's statement restored and scoped to ≤ 3.10 main data), **`MD_DATA_RA_015`** (“rarely native v3.14” and “resident-layout” withdrawn; the embedded/split ratio among extent-backed files reported per format), **`FS_MOVE_RA_001`** (placement wording), **`MD_LK_RA_005`** (one `$OBJ_LINK` row per NAME, with the duplicate-pair caveat) and **`MD_SNAP_RA_007`** (whose “all ADS are inline; non-resident ADS refuted” headline rested on 159 rows and already contradicted E61). Vocabulary: the bare word “resident” is retired from the live register except for driver symbol names and quoted prior wording — see `REGISTER_CONVENTIONS.md`. |
| **Tool impact** | `_reported_resident` (= `is_resident or data_inline`) already reports axis B, and the two-axis model itself needed no code change. Measured against this independent byte-level classifier over the whole corpus (**117 images, 523,756 comparisons**, every image completeness-asserted): **1,646 disagreements, 99.686 % agreement**, and **0** of them are cases where the two-axis reading is wrong. They split cleanly in two: **1,098 zero-byte rows** (22 images) whose record is EMBEDDED with an **extent-form** `$DATA` descriptor, reported resident from the legacy placement flag — these become `extents` once axis B is read from the descriptor; and **548 data-bearing rows** (446 names, 53–2,047 B, `winsider` only) which are a real reporting defect (**E89**). The zero-byte rows whose descriptor is the **inline** form already report correctly after **E88**. |
| **Docs affected** | `concepts/resident_storage.md` (replace the size-threshold table with the two-axis rule; delete "never converts back" as a residency statement), `structures/directory_entries.md`, `concepts/hard_links.md`, `attributes/DATA.md`, `attributes/NAMED_DATA.md` (the 128 KiB cap is the ADS cap on ≤ 3.10), `tools/forefst.md` (`IsResident` = axis B; `IsMoved` = axis A; both can be True together), and the home page / README sentence about whole files hiding in a metadata row. |
| **Amendment (2026-11-12; RC1-docs G7 I031)** | The 8,353-row census counts the 0xB0 rows of the marker form only (the named-stream rows the census script reads); it is not a census of every 0xB0 row on every format. |
| **Update (2026-11-21, RC3a W1; RUNNING_LOG N663)** | The master's "Observed Ratios" table (thesis-era, ENRICHED: "Win10 (all) 100% resident" ... "Win10 is 100% resident because the threshold (128 KB) exceeds all test file sizes") survived this erratum's docs step. It names neither property, and its reason is wrong for main `$DATA` on 3.4 to 3.10, where no main `$DATA` is inline (the census above). The table is withdrawn from the master; the two-axis census above replaces it. |

<a id="e88"></a>
## E88 — An empty file whose record was split out of its name row was omitted from the record list entirely, so `extract` reported "file not found"

| | |
|---|---|
| **Previous** | `_analyze_dir_extents` admitted a `key_flags 0x02` name row into its file list only `if not is_dir and file_size > 0`, so a **0-byte** split-record file produced **no record at all**; `extract` then failed with `file '<name>' not found` for a name that `files` and `details` both list. Independently, `_backing_inline_data` returned `None` when the inline form carried `stream size == 0`, which is indistinguishable from "extent-backed", so the same files were also reported `IsResident=False`. |
| **Correct** | A 0-byte file is still a file: it is admitted to the record list, and an inline `$DATA` form with `size == 0` is an **empty resident stream** (`return b""`), not an absent one. Extraction of a 0-byte file with no extents succeeds and writes nothing, whatever its placement. |
| **Evidence** | Measured by comparing forefst's `IsResident` against an independent byte-level classifier: **772** rows on **11 images** were split-record files whose `$DATA` was the inline form with size 0 — reported non-resident, and unextractable. Reproduced end-to-end on `win11refs2tspecials`: `files` lists `testspecials/hardlink_alpha_915629.lnk` (0 B, 3 hard-link names, `IO_REPARSE_TAG_SYMLINK`) while `extract` answered `file 'hardlink_alpha_915629.lnk' not found`. After the fix that name and its siblings extract as `0 bytes — empty file, inline form`, the second class (split, extent-form, `disk_alloc == 0`) as `0 bytes — empty file` (verified on the **v3.7** volume `win1121h2test`), and a non-empty file on the same image is byte-identical. On the corpus-wide re-measurement (117 images, 523,756 comparisons) **no zero-byte inline-form row disagrees any more**: the whole remaining zero-byte class is the *extent*-form one (1,098 rows), addressed by reading axis B from the descriptor rather than the placement flag. |
| **Corrects** | No reference row — this is a reader defect, not a structure error. Related: **E82** (a split record can hold its data inline) covered only the non-empty case. |
| **Docs affected** | None (behaviour matches what the pages already describe). |

<a id="e89"></a>
## E89 — A multi-name file whose HOME object is never walked as a directory loses its resolved backing, so `files` reports it non-resident while `extract` reads it as resident

**Status: FIXED in v1.10** (`forefst.py`, `_home_t40`). Characterised first as reporting-only — no content was ever lost or wrong — then fixed once the blast radius had its own measurement.

| | |
|---|---|
| **Previous** | In `walk_directory_tree`, a split (`key_flags 0x02`) name is resolved to its type-0x40 backing through `t40_content`, keyed `(owner_oid, stream_idx)` and populated **only from directories the walk actually visits**. When neither `(parent, fid)` nor `(home, fid)` is present the entry falls through to the `solo` branch with `rec = None`, and every field carried by that record — including `data_inline` (E82), and equally the per-file LastUsn, SecurityId, internal flags and backing `file_attrs` — is silently left unset. |
| **Correct** | The backing exists and is reachable: it lives in the home object's own tree and can be walked on demand from `obj_map[home]`, which is exactly what `_analyze_dir_extents` already does via `_home_streams(oid)` (cached). Resolution must not depend on whether the home object happened to be traversed as a directory. |
| **Evidence** | RD 2026-09-04, whole-corpus comparison against an independent byte-level classifier (one process per image, 122 images, 523,176 comparisons): **548 name rows on `winsider.raw`** (v3.14, real Windows volume; 446 distinct names, 53–2,047 B, every one `key_flags 0x02`) report `IsResident=False` with `data_inline` unset, while their backing's `$DATA` **is** the inline form. Traced end to end on `Windows/System32/spool/drivers/x64/3/MSXPSINC.GPD` (parent `0x1a2e`, home `0x94aa`, backing `(0x94aa, 3)`, own size 73, `_backing_inline_data` → 73 bytes): four *other* directory entries of the same object, whose home **is** walked, all report `data_inline=True`. The affected entries are exactly those whose home object is not itself traversed. No other image in the corpus is affected — `winsider` is the only volume with this depth of multi-path driver duplication (`DriverStore/FileRepository` + `spool/drivers`). |
| **Not affected** | **Extraction, content and size are correct.** `extract` on the traced file writes the right 73 bytes and correctly announces `resident/inline`, because it resolves through `_home_streams`. The defect is the disagreement between `files` (`IsResident=False`) and `extract` (`resident/inline`) for the same file. |
| **Fix (applied)** | `walk_directory_tree` gained the same on-demand, cached home-tree lookup `_analyze_dir_extents` uses: when both `t40_content` lookups miss, `_home_t40(home)` walks `obj_map[home]` for the `(stream_idx)` type-0x40 row and uses it. The blast radius was measured rather than assumed — the same `rec` feeds hard-link grouping, USN, SecurityId and attributes — and the pre-fix join is retained behind `--legacy-link-join` for one release so the old behaviour stays reproducible. |
| **Verified** | The whole-corpus comparison against the independent byte-level classifier goes from **99.686 %** (1,646 disagreements) to **100.0000 %** — 523,756 comparisons over 117 volumes, **0** disagreements. The 548 `winsider` names now carry `data_inline`, LastUsn, SecurityId and backing attributes; `files` and `extract` agree on every one. |
| **Docs affected** | None (behaviour now matches what the pages already describe). |

<a id="e90"></a>
## E90 — The container-table compression header's field at `0xA0` is **not** a constant `0x0F`: it is `0x07` on a v3.4-format volume

| | |
|---|---|
| **Previous** | Master §C.11 (*Compression Parameters*) recorded the first field of the block at container-table-root `+0xA0` as `Prefix (constant 0x0F)`, and `structures/container_table.md` repeated it. Nothing scoped the value to a format version. |
| **Correct** | The value is **version-keyed**, not constant: `0x07` on a **v3.4**-format volume and `0x0F` on **v3.7 and later**. The change is at the v3.4→v3.7 boundary and is independent of cluster size and checksum type. The three fields that follow it are unchanged and confirmed: `0xA4` u16 format, `0xA6` i16 level, `0xA8` u32 chunk size. |
| **Evidence** | RD 2026-09-05, whole corpus. 89 volumes carry a container-table root page; **85** of them parse as an index root (descriptor `thoff == 0x228`, 31 total rows) and are the scope of the claim. Across those 85: `0x07` on **13/13** v3.4 pages (12 at 4 KiB clusters, 1 at 64 KiB) and `0x0F` on **72/72** v3.7+ pages (v3.7 ×1, v3.9 ×2, v3.10 ×2, v3.14 ×64, v3.15 ×1, plus 2 version-field-edited images whose volume is v3.14). No page of either version group shows the other value. The following fields decode consistently on the **10** images that have compression configured (`0xA4 != 0`): format 1 (LZ4) ×7 and 2 (ZSTD) ×3, levels 1/3/7/9/11/13/15, chunk sizes 0x1000 / 0x8000 / 0x20000 / 0x40000 (4 / 32 / 128 / 256 KiB). |
| **Scope limit (not a counter-example)** | The remaining **4** volumes — the four 2 TB `win11refs2tmillionsofactions` images — read `0x4004` at `+0xA0`. Their container-table root page is a **multi-level (inner) node whose index header sits at page+0x58 instead of page+0x278**, so `+0xA0` lands in a different frame there and says nothing about this field. The table itself parses correctly: `_select_ct_root` picks it by table id, `_parse_ct_page` descends the inner node, and the result is 184 container rows, **16,192 mappings and 0 translator misses** on each of the four. The claim is therefore scoped to the 85 volumes whose container-table root is a **leaf**, not excluded for any defect in these four. *(An earlier draft of this row said the page was "not an index root at all", reading `thoff` as an absolute offset; the reader computes it as `0x50 + le32(page, 0x50)`, so the measured `0x8` is a **relative** header offset, not an absent descriptor.)* |
| **Also unverified** | Format value **3 = LZ4QAT** is documented from the driver's enum and has **no** on-disk instance in the corpus. The neighbouring u32 at `+0x98` is `0x00` on all 13 v3.4 pages and the single v3.7 page and `0x04` on v3.9+, **except** 2 v3.14 pages that read `0x00` — too weak to state as a rule, so it is left in `open_questions.md`. |
| **Corrects** | Master §C.11 (the word *constant*). New register row **CT_COMP_RA_003**. |
| **Docs affected** | `structures/container_table.md`. |
| **Amendment (2026-11-12; RC1-docs G7 I039)** | The word at `+0xA0` is a flags word, the root data's `+0x28` (`CmsVolumeContainer+0x78` on 26100.x and Insider 29574, `+0x70` on 17134), and the word at `+0x98` (the "neighbouring u32" above) is the root data's `+0x20`, the number of containers reserved for compaction; the page offsets hold when the u16 at page+0x54 is 0x28 (`analysis/reports/v1.13.2/fixes/WAVEC_READING_tables.md` C1-C4, MR-2; RUNNING_LOG N234). The values and the scope above stand. Corrects: master §C.11 (the word "marker"). |

<a id="e91"></a>
## E91 — E81 (reparse) and E83 (snapshot CoW sharing) were static-only; both are now raw-disk, and a pre-allocation hypothesis is refuted

**Status:** three corrections of *evidence level*, one refutation. No decoder changed.

**E81 → RD.** The junction / directory-symlink / file-symlink decode had no instance on any public image, so
it stood on the driver alone. `lab314_main` carries all three: `IO_REPARSE_TAG_MOUNT_POINT` (junction) and
two `IO_REPARSE_TAG_SYMLINK` (directory and file), with `reparse --index` reporting 1 + 2 and each target
decoded. `FS_REPS_RA_003` is upgraded with the witness.

**E83 → RD.** Snapshot-shared CoW blocks had no instance either. The step2 re-run produced snapshot `before`
on a 12,288-byte file whose middle cluster was then rewritten, and `keep` on a snapshotted 600-byte inline
file; both are found, and all three T12 files are byte-exact against the operator's `witness/hashes_t12r.csv`.
`MD_SNAP_RA_008` is upgraded. Note the first attempt **failed** — refsutil rejected the snapshot syntax with
`rc=87`, which is why the step1 volumes carry none; the failure is recorded in `groundtruth.txt`.

**The 2 KiB ceiling is FIXED, not cluster-relative (T4).** Measured identically on 4 KiB, 64 KiB and 4Kn
volumes: 1,900 B inline, 2,100 B extents, for the main stream *and* for a named stream. On 64 KiB clusters a
2,100-byte stream occupies a whole 64 KiB cluster. A 131,073-byte ADS exists and reads back byte-exact, so
the 128 KiB ADS cap does **not** apply on 3.14 — it remains a ≤3.10 rule, still E2 + vendor documentation
there. `MD_ATTR_005` is upgraded.

**REFUTED — pre-allocation does not force extent-backing (T14).** `fsutil file createnew` (SetEndOfFile
before any write) on a 7-byte ADS and a 500-byte main stream leaves **both inline**, alongside an ordinary
7-byte ADS that is also inline. The hypothesis that pre-allocation explains the twelve extent-backed
SmartScreen streams is therefore wrong, and that observation needs another explanation. Recorded as
`MD_DATA_RA_027` with status REFUTED rather than deleted, so the dead end stays visible.

**Witness for all of the above:** the lab314 volumes (Win11 24H2, ReFS 3.14, 4 KiB / 64 KiB / 4Kn) and the
ground truth written **on** them by the operator — `inventory.csv` (4,657 + 626 + 626 files, 100 % SHA-256),
`streams.csv` (per-ADS), `hashes.csv`, `witness/hashes_t12r.csv`, and `fsutil queryfileid` for 57 objects.
Content proof: **5,908 of 5,909 byte-exact**, the one difference being a witness that hashed a symlink's
target while recording the link's own size.


<a id="e92"></a>
## E92 — `MD_ATTR_RA_019`'s "the type-0x30 pointer OMITS the EA bit" reads as a universal rule; it is a *possible* omission, on one corpus volume

The row records that the attribute copy cached in a type-0x30 index entry (value+0x40) is an INCOMPLETE
copy of the authoritative attributes in the type-0x40 backing record (value+0x48), and that the only bits
that ever differ are `0x40000` (EA) and the transient `0x20` (Archive). Its wording — "the POINTER … OMITS
the EA bit" — was written as though the pointer never carries it. Re-measured 2026-09-07 against the
tool's own backing resolution, on `winsider` (the volume the original measurement used):

| pointer `0x40000` | backing `0x40000` | split-record names |
|---|---|---|
| clear | set | **8,141** — the cached copy drops the bit |
| set | set | **14,207** — the cached copy carries it |
| set | clear | **0** — the pointer never sets a bit the backing lacks |
| clear | clear | 50,361 |

So the usable rule is an implication, not an equality: the index-entry copy is a **lower bound** on the
EA bit, and the authoritative value is always the backing. The correction does not change any tool
behaviour — `forefst` already ORs the bit in from the resolved backing — and it does not change the
finding's status; it changes what a reader concludes from it, which is why it is recorded here.

**Breadth, stated as measured.** A raw scan of the whole corpus for backing records carrying `0x40000`
finds them on **exactly one** of the 102 ReFS images: `winsider` (Windows system files with
`$CI.CATALOGHINT` / `$KERNEL.PURGE` EAs). Every other image has zero extended attributes on split
records, so the phenomenon is not observable there and the rule is single-volume evidence. The WSL images
carry EAs only on embedded records, where the question does not arise.

`concepts/attributes.md` stated the bit as living *in* the type-0x30 value, which is the reading this
erratum forbids; it is corrected in the same change, citing `MD_ATTR_RA_019` in its Evidence section.

<a id="e93"></a>
## E93 — Three statements the 2026-09-07 lab reads (T9, T15, T17) contradict, all in the tool rather than the reference

The seven remaining lab tests were read against `lab314_main` and `lab314_main_step2`. Four confirm what
was already documented (T10, T12c, T16, T18 — recorded as `FS_MOVE_RA_003`, `MD_SNAP_RA_009`,
`MD_USN_RA_009`, `MD_SF_RA_005`). Three contradict a standing statement; none of the three is in the
reference or on a page, so this erratum records them against the tool.

**1. "A file that HAS an ADS is always resident here — this resident path is complete."** That comment
sits above the ADS branch in `walk_directory_tree`, and cites a 2026-06-28 corpus recount (678 == 678, 0
divergent images) as proof. The recount was sound and the conclusion did not follow: no corpus image
carried a named stream on a *split* record, so the case the branch cannot handle was absent from the
evidence. T9 creates it in one line — write a file with an ADS, then move it. The stream becomes
invisible: `HasADS=False`, no row in `specials ads`, while the tool's own `detect_ads_in_resident()`
returns it when handed the type-0x40 backing value. Corpus-wide, **655 backing records on 28 of 102
images** carry streams no command inspects. (A per-name count first quoted alongside that figure was
withdrawn: it joined on `(parent_oid, file_id)`, and `file_id` is a per-directory ordinal -- one value is
shared by 32 distinct backings on one image -- so it attributed other files' streams. The backing-record
count does not depend on any join.) See `MD_ADS_RA_005`. This is a second, independent reason the
ADS censuses (`FS_SNAP_RA_001`, `MD_ATTR_RA_017`) are lower bounds — the first was E73's embedded subtree.

**2. The timestomp legend describes a tier scheme the tool does not implement.** `cmd_timestomp` prints
"HIGH = >=2 independent signals or 1 authoritative; MEDIUM = 1 strong intrinsic; LOW = a weak/single
hint". `timestomp_verdict()` — the single source since v1.10.1 — awards HIGH *only* for an authoritative
corroboration (USN or hard-link) and never for a signal count. On the T15 controlled set a file with all
three timestamps backdated carries three signals and is INFO, correctly, because that signal set is a
subset of the copy signature. The verdict function is right; the legend above it is stale. See
`MD_TS_RA_008`.

**3. "FULL FILE recoverable … EXACT" is decided by the remnant's value LENGTH, not by whether the value
holds the bytes.** T17 deleted one file per residency class; the classification is right in every case,
including the E87 point that a moved-then-deleted file whose data stayed inline is still fully
recoverable. But `del_split`'s slack row is 1,336 bytes long with 108 non-zero and no data pattern, and
`export deleted` wrote **500 zero bytes** for it, manifest `confidence: high`, `recoverable_inline`,
`EXACT`. The fix names both readings of those zeros -- `content zero or absent (indistinguishable in the
remnant)` -- because the file may genuinely have held zeros and the remnant cannot say which. The generator proves these zeros are fabricated rather than real content: every T16 `f_*.bin`
was written with the same 300 non-zero bytes, and of 849 recovered, 635 carry the pattern while **214 are
300 zero bytes**. Breadth of zero-filled "recovered content": winsider 6,110/8,459, lab314_main 228/877,
win11refs8g 57/72, win11refstestmftecmd 11/15. See `MD_DEL_RA_004`.

All three are tool defects scheduled for 1.11.0. Nothing on a published page is wrong as a result, so no
page changes with this erratum; the three register rows carry the measurements and their witnesses.

---

<a id="e94"></a>
## E94 — A path resolved to the FIRST case-folded match, so on a case-sensitive directory `extract` served one file's bytes under another file's name

**Status:** tool defect, present in every release up to and including v1.11.1; fixed in v1.11.2.
**Affects:** `resolve_path()` in `forefst.py`, and therefore `extract` (bare name, `/path`, `--path`,
`--id`), `details`, and `export file`. Listing (`files`, `search`) was never affected.

ReFS folds case by default, so path resolution folds too. But a directory carrying the per-directory
case-sensitivity flag (`fsutil file setCaseSensitiveInfo`) compares filename keys **binary rather than
case-folded** — this is already recorded in `MD_CS_RA_001`, `MD_CS_RA_002` and `MD_DISK_RA_009` — and two
names differing only by case then coexist as separate type-0x30 rows with distinct FileIds.

`resolve_path` compared `nm.lower() == part.lower()` and returned the **first** row that matched, so every
spelling resolved to whichever name came first in B+-tree order. The bytes served were a different file's,
under the requested name, with **exit 0 and no warning**.

Measured on the two corpus volumes that have such a directory, against ground truth the project did not
produce (the operator's own SHA-256 inventory on `win11bidule`, and a size difference on the other):

| volume | pair | published v1.11.1 | v1.11.2 |
|---|---|---|---|
| `win11bidule` | `HI.txt` / `hi.txt` (10 B each, different content) | both spellings and both `--id`s return `HI.txt` | each returns its own |
| `win11refs4gattributestest2` | `WindowsCaseSensitive.txt` (14 B) / `windowsCaseSensitive.txt` (8 B) | both return the 14-byte file | each returns its own |

**Corpus census.** 102 readable images: **12 directories carry the flag, on 2 images** — 11 of them are
`tests/testdir` and its whole subtree on `win11bidule`, one operator action inherited by subdirectories.
Only **2 directories actually hold a colliding pair**, and those two are the only places the defect is
reachable: with a single spelling present the case-folded fallback returns the right row anyway.

**The rule now implemented:** an exact spelling wins outright; the first case-folded hit is kept only as a
fallback, so wrong-case paths keep resolving on ordinary directories (ReFS's own default, and the release
golden depends on it — one extract target is spelled `$RRJOQB1.xml` against an on-disk `$Rrjoqb1.xml`).
The fallback is deliberately lenient: on a case-sensitive directory a spelling that exists only in another
case still resolves, where Windows reports not-found. Finding the file and naming it exactly serves an
examiner better than refusing it; the exact match governs which bytes are served.

**Why it survived to release.** No page was wrong — `upcase_table.md` and `reverse_index.md` describe the
binary-comparison rule correctly, and the register recorded it. The tool simply did not implement what the
reference said, and no test addressed a file by a spelling that differed from another file's. The pair on
`win11bidule` was being merged by the verification harness itself, which keyed its ground-truth inventory
by `path.lower()`; that merge is what hid the defect behind a clean 629/629. Both are fixed: the harness
keys exactly (630/630 byte-exact), and `verify_claim.py --regress` assertion 29 checks resolution
exactness corpus-wide plus every colliding pair — verified to FAIL on the pre-fix code (3 counter-examples
across both volumes) and PASS after.

No page changes with this erratum: the pages were right. `MD_CS_RA_003` records the census and the fix.

<a id="e95"></a>
## E95 — The extent-map decoder consulted a heuristic marker scan before its two structural readings, so a small number of files decoded to the wrong clusters — nine of them to the volume boot record

**Status:** tool defect, present in every release up to and including v1.11.3; fixed in v1.12.0.
**Affects:** extent-map decoding in `forefst.py`, and therefore every command that returns or describes
non-resident content — `extract`, `dataruns`, `export file`, `export deleted`. Resident (inline) files were
never affected, and listing was never affected.

A non-resident file's extent map is held in one of **two holder forms**, and the tool has a **structural
reading** for each: the nested B+-tree node, whose rows are addressed through the node's own index array
(**E86**), and the plain holder, whose entries are read at a fixed stride from a descriptor whose start,
end, count and capacity must agree before an entry is read. Behind both sits a **heuristic marker scan**
that searches the value for a 4-byte constant and takes the first entry that covers the file.

Through v1.11.3 the dispatcher consulted the marker scan **first**. The guard that accepts a decoded map
cannot catch this: a wrong single run of the right length covers the file's allocation exactly as well as
the right one does, so a wrong answer is accepted silently and `extract` exits 0.

| Measured | Value |
|---|---|
| Corpus scope | **102 readable ReFS volumes** of the 106 entries in `corpus.lst` (2 NTFS, 1 NTFS variant, 1 BitLocker cannot be opened) |
| Universe, in the unit measured here | **109,567 files** for which v1.11.3 produces an extent map (v1.12.0 produces 110,160). The M2.1 census counts **109,588 extent-backed *streams*** over the same corpus — a different unit, quoted here only so the two are not confused |
| **Files whose clusters changed** | **11 distinct files, 23 occurrences** (several exist on more than one image) — re-derived 2026-09-11 by running the **published v1.11.3** and **v1.12.0** side by side and diffing their maps, order-independently |
| Files mapped to **cluster 0, the volume boot record** | **9** — `extract` returned 43 non-zero bytes of the `ReFS` signature as file content |
| Files mapped through the `$DATA` sub-record descriptor constant `0x000E0080` | **1** — extracted as 505,381 zero bytes; the real content was recoverable all along |
| Files mapped from an **unindexed row** inside their own extent node | **1** |

**Scope:** ReFS 3.7, 3.9, 3.10 and 3.14; both 4 KiB and 64 KiB clusters. Rare — 23 of the 109,567 files v1.11.3 maps —
and silent.

**Evidence.** The A/B was run against the **published** v1.11.3, not against a reasoned model of it, and
every changed map is named in `analysis/reports/M2_2_decoder_order.md`. For the nine boot-sector files the
witness is the content itself: the old map reads `\x00\x00\x00ReFS` with 43 non-zero bytes of 16,384, the
new map reads real content with ~16,318. For the `0x000E0080` file the new map begins `GFSAREPLAY`, the
generator's own marker.

For the `millionsofactions` record the correction was first recorded as *mechanism-explained rather than
content-proven*. It is now **content-proven** (M3.4, 2026-09-11): the cluster the old map returned,
VLCN `0x6732e74` / PLCN `0x338ae74`, is **byte-identical to cluster 91 of a different live file**
(`…/xbpt_sierra_victor_918254.bin`, 470,384 bytes, 4 extents), and each of the two candidate clusters is
referenced exactly once on the volume. The pre-fix decoder served one file's bytes as another's. This does
not by itself prove the new map's bytes are that file's true content — no witness on that volume carries a
hash for it; that rests on E86's index-array rule together with the new cluster being referenced by nothing
else on the volume.

**Correction:** the structural readings are consulted first and the marker scan is demoted to a logged
fallback. All three decoders remain, and the index array is still the only one that answers on ReFS 3.4.
A secondary effect: **593 more files gain a decoded extent map**, because the structural reading resolves
maps the scan could not. **Of those 593, 152 are byte-proven** (the generator's content marker) and **441
are unproven** — they decode and return real content, none of it zeros, but no independent record confirms
the bytes; `refscat` corroborates 3 of the 49 tested on one 4 KiB volume, disagreeing on none. Decoding is
not correctness, and the release text says so. Re-derived at RC by running both shipped tools over every readable volume and
comparing `dataruns -v`; the unit is a **file**, not a stream — `dataruns` lists one entry per file and no
sub-streams, so this figure is not comparable with an earlier stream-level count of 641 taken from an
artefact that was not kept. Run boundaries are also now reported as the node records them, so a file's
extent *count* can change while its clusters do not.

**Docs affected:** `changelog.md` (v1.12.0), `structures/extent_descriptors.md` (the census fact that the
scan was primary through v1.11.3). Register row: **MD_DATA_RA_030**.

<a id="e96"></a>
## E96 — 3.15 was carried as a ReFS volume format version; no volume has ever been formatted 3.15, and nothing was verified on one

**Status:** documentation and register defect, present through v1.12.2; corrected 2026-09-13.
**Reported by:** the maintainer — *"the last official version is v3.14. I saw from windows insider that it
supports v3.15 but the disk was never detected as a 3.15."*
**Affects:** `refs_version` and `format_verified` on 11 register rows, the format-version enumeration in
`REGISTER_CONVENTIONS.md`, the generated `docs/format_support.md` matrix (which showed a **3.15 column with
counts**), and four public pages describing the image corpus as spanning "3.4 → 3.15".

### What was claimed

That ReFS 3.15 is a volume format this project has images of and has verified statements against. Five
register rows named `3.15` in **`format_verified`**, which means *a measurement was made on an image of that
format*. The support matrix is generated from that column, so it published a 3.15 column, and prose on four
pages described the corpus as reaching 3.15.

### What is true

**No volume in the corpus is formatted 3.15.** Exactly one image reports that version:

```
analysis/rawdisk/disks/step4continuing/win11refsmini_afterchangingversion_opened_rechangedtoversion315.raw
```

Its name records what it is — a **hand-edited version field**. It is the third member of a series built
from one v3.14 volume to test version handling:

| image | reported version | objects |
|---|---|---|
| `win11refsmini` | 3.14 | 24 |
| `win11refsmini_afterchangingversion` | **6.66** | 24 |
| `…_rechangedtoversion315` | **3.15** | 24 |

Identical object counts across all three: one volume, one edited byte. `6.66` is already understood as an
impossible version used as a negative test; `3.15` is the same construction with a plausible-looking number,
and that plausibility is what let it propagate into the register as a real format.

The image manifest records the **whole series** — six images from one `win11refsmini` base: `6.66`, the same
reopened, one changed back, two changed to `3.12` (both of which read back as **3.14**), and the one changed
to `3.15`. It is a version-editing experiment, not a set of formats.

### What is true, and must not be removed

Two genuine findings mention 3.15, and both are about the **driver**, not about any volume:

- `fsutil fsinfo refsinfo` on Insider build 29574 reports **`REFS Driver Maximum Supported Version: 3.15`** —
  the highest format that driver could *write*, not a format any volume here uses.
- `$VOLUME_INFORMATION` at `+0x82/+0x83` stamps the highest driver build that ever mounted the volume;
  `0x0f03` (3.15) appears there only after an Insider mount (finding #306). This is a forensically useful
  signal of Insider exposure, and it says nothing about the volume's own format, which is at `+0x80/+0x81`.

The conflation is precisely between those two fields: a **driver** version of 3.15 was read as a **volume
format** of 3.15.

The register already knew. `FS_VBR_RA_013` states, of these same images, that *"the primary carries the
altered version (6.66, 3.15) while the backup holds the authentic 3.14"* — so one row correctly called 3.15
a hand-edited value while eleven others carried it as a format. The follow-up investigation
(`FS_VBR_RA_014`) settles it on disk: the 3.15 image has a checkpoint clock of 64, unchanged from its base,
so **no ReFS driver has ever mounted it**. That version byte has never been validated by anything.

### Correction

- `format_verified`: `3.15` removed from all five rows that carried it. Nothing is lost — **every one of
  them already lists `3.14`**, which is what that volume actually is. Counting it separately was
  double-counting v3.14 under a label no volume bears.
- `refs_version`: `3.4-3.15` becomes `3.4-3.14`; `;3.15` dropped from explicit lists.
- `REGISTER_CONVENTIONS.md`: `3.15` removed from the format-version enumeration, with the reason recorded so
  it is not re-added.
- `docs/format_support.md`: regenerated; the 3.15 column is gone.
- Public prose: "3.4 through 3.15" / "3.4 → 3.15" becomes 3.14; "native v3.14/v3.15" becomes "native v3.14".

**Scope of the claims themselves is unchanged.** Not one statement becomes less true: each was verified on
the volume it was always verified on. What changes is the *name* under which that verification was counted,
and the removal of a published implication that this project has evidence about a format that does not
exist outside a deliberately edited byte.

---

<a id="e97"></a>
## E97 — the MLog record budget and the merged-block chain were both wrong, so the parser read 13.7 % of the log and the tool explained the shortfall as a property of ReFS

**Status:** tool and register defect, present through v1.12.3; corrected 2026-09-19 (A2).
**Reported by:** the 2026-09 blind audit (K055, K056), confirmed against the driver and re-measured here.
**Affects:** `mlog`, `mlog --parse`, `mlog --stats`, `timeline`; register rows `AP_REDO_040`,
`AP_EVNT_002`, `AP_EVNT_005`, `MD_TS_RA_009`, `AP_LGFL_RA_007`.

### What was claimed

That a log payload holds one `_SmsRedoHeader`, and that its records occupy `total_size - first_off`
bytes. The tool also printed, beside its own count of zero commits:

> "commit is marked at the checkpoint/LogCore layer, not by a per-redo-record flag — this is 0 on every
> volume, healthy or not; do NOT read starts>commits as 'uncommitted work'"

### What is true

Two functions in `refs.sys` define the framing, and neither matches:

```
CmsRestarter::ForEachBlockInMergedBlock:  remaining -= blk[1] + blk[0];  blk += blk[1] + blk[0]
CmsRestarter::ForEachRedoInBlock:         budget = hdr[0]        # total_size, not total_size - first_off
                                          p = hdr + hdr[1]       # first_off only locates the first record
```

A payload holds a **chain of up to 15 merged blocks**, and each block's record budget is its own
`total_size`. Measured before changing anything:

| volume | payloads | blocks | max chain | close under `total_size` | under `total − first` | records |
|---|---|---|---|---|---|---|
| `win11refsmini` | 147 | 364 | 9 | **364/364** | 2/147 | 746 (was 137) |
| `lab314_main_step3_dirty` | 11,868 | **75,695** | **15** | **75,695/75,695** | 2/11,868 | 128,214 (was 17,538) |

**The commit flag was never absent.** The last record of a block carries bit 1 at `+0x2C` on
**75,695 of 75,695** blocks, and on 115/115, 4,887/4,887 and 4,885/4,885 transactions of three v3.4
volumes. The wrong budget truncated every block *before its final record* — the one that carries the
flag — and the note above was written to explain a zero the tool produced itself. Every clause of it is
false; it is deleted.

### How it was missed

The framing was implemented **twice** — `try_parse_redo_block` and an inline copy inside
`extract_mlog_transactions` — with the same two defects. The two MLog surfaces therefore agreed with
each other, and with neither the driver nor the disk. Both now call one pair of iterators
(`iter_redo_blocks` / `iter_redo_records`).

### What it cost

Beyond the missing 86 %: the timeline **invented** events. On `win11refsmini` the shipped tool places
`2026-05-14 06:29:26 … /plusrienneva DELETE` on the super-timeline, while that object's own CREATE and
its `$SI` Created stamp are both `06:30:45` — a deletion 79 seconds before the object existed. Under the
corrected framing it is absent. Corpus-wide, the old parse also over-reported file creation about
six-fold (`lab314_main`: 2,846 CREATE → 460, with 5,173 WRITE appearing in their place), because a
truncated transaction shows only its opening `INSERT`s.

### Register consequences

See `analysis/reports/plan_v11_2026-09-18/A2_REGISTER_REMEASURED.md`. In brief: `AP_REDO_040` loses two
clauses and must be rewritten; `AP_EVNT_002` and `AP_EVNT_005` HOLD and gain support (23 → 67 and
35 → 68 witnesses); `MD_TS_RA_009` keeps its mechanism and all four T15 witnesses reproduce to the
millisecond, but its counts are restated and "the file's CREATE" becomes "the file's creating
transaction"; `AP_LGFL_RA_007` gains the merged-block chain. The other 20 `CONFIRMED` MLog rows are
structural and untouched — `AP_LGFL_RA_010`'s per-record integrity fold still verifies 145/145,
byte-identical to the shipped build.

**Amendment (2026-11-12; RC1-docs G7 I014; RUNNING_LOG N173, N182).** The harness behind the table counted the volume's
two control pages as log payloads: it has no record-type test, and each control payload parses as one bogus block
(its write sequence read as `total_size`; the mlog critic's read). The data records are 2 fewer and the blocks 2 fewer:
on `lab314_main_step3_dirty` the dev tool (1.14.0, `mlog --stats`, 2026-11-12) reads 11,866 log records, 128,214 redo
records, 75,693 transaction starts and 75,693 commits (the table's 11,868 and 75,695); on `win11refsmini` 746 records,
362 transaction starts and 362 commits (the dev tool, 2026-09-26; the table's 364). The "2 of 11,868" (and "2 of 147")
payloads that close under the retired budget are those two control pages (the critic's read, not re-measured). The
rule E97 states, the per-block budget and the merged-block chain, is unchanged.

---

<a id="e98"></a>
## E98 — the sparse-hole rule named the weaker of two co-observed discriminators, and `extract` put the volume's own superblocks inside user files

**Status:** tool defect, present through v1.12.3; corrected 2026-09-18 (A1). **Re-scopes E65.**
**Reported by:** the 2026-09 blind audit (K001, K002).
**Affects:** every extent decoder, `extract`, `export`, `dataruns`, the carve paths.

### What E65 claimed

That a sparse hole is an extent row with `VLCN == 0`.

### What is true

A hole row sets **bit 0x20 in flags@+0x08**, and its VLCN *mirrors its FVCN* — so on the extent-node
form the VLCN is non-zero and `VLCN == 0` fires on nothing. E65 is not a fabrication: both
discriminators were observed together. It named the weaker one, and the census that confirmed it counted
`vlcn0-exts` per image, so a flag-0x20 row with `VLCN = 1` could never appear in it.

Re-measured over all six decoders on four volumes (8,864 accepted rows on the shipped build): the flag
is a strict **superset** of `VLCN == 0`, with **0 counterexamples**. Two volumes carry holes with both
discriminators, two carry holes with only the flag — which is exactly how a corpus weighted to the first
kind makes `VLCN == 0` look like a rule.

### What it cost

On `win11refs2tsnapshots`, three files whose hole rows read `fvcn=1 vlcn=0x1 run=25343 flags=0x180060`
were extracted with the hole read as real data. The 99 MB witness came back at its exact length, with
its correct marker at offset 0, and **6,973,680 bytes of the volume's own bootstrap metadata inside it**
— `SUPB` at file offset 0x1e000, `MSB+` at 0x24000, 0x28000, 0x2c000. The retired content predicate
(length + not-all-zero + marker@0) passed it on all three counts, which is why it was reported correct.

### The correction, and one thing it is careful NOT to do

`_extent_is_hole(flags)` decides **membership**: the flag, and only the flag. An unflagged `VLCN == 0`
row is *malformed*, not a hole, and is rejected so the cover guard fails cleanly — admitting it would let
a bogus map pass the cover check and serve clusters of zeros as content. A separate
`_extent_never_read(flags, vlcn)` is the **read-time floor**: no cluster is read for a hole, nor for
VLCN 0, which translates to the boot region and is never file content.

### K002 — and a second cause that was not the flag at all

A sparse file's rows tile only its **allocated** clusters, at their logical positions, with no row for
the range between (`lab314_main/t18_sparse.bin`: one row at file_vcn 0, one at 15, allocation 2 clusters,
size 16). The gapless cover guard rejected that healthy map, and the file vanished from `dataruns` with
rc 0 and no message — while the tool's own summary printed `Data in extents: 619` beside
`With decoded extents: 617` and compared neither. Accepted now under `FILE_ATTRIBUTE_SPARSE_FILE` when
the rows are ascending, non-overlapping and sum to the declared allocation; the gaps become explicit hole
rows, and `dataruns` prints a hole as a hole rather than as `VLCN=0x0 PLCN=0x0` — which read literally is
a run at the boot sector, the same confusion that caused K001.

Recovered on `win11refs8g`: `blabla/bigsparse.bin`, previously shown with no extents at all, now decodes
to `hole: fvcn=0 clusters=2048` plus 14 runs — 3,328 clusters, exactly its 13,631,488 bytes.

---

<a id="e99"></a>
## E99 — `INTEGRITY_EXTENT_FLAG = 0x1C00D0` was never a flag value, so every integrity extent of two or more clusters went unverified

**Status:** tool defect, present through v1.12.3; corrected 2026-09-18 (A3).
**Reported by:** the 2026-09 blind audit (K009, K010, K011).
**Affects:** `extract`, `export`, `integrity`; the per-cluster CRC-32C verification path.

### What was claimed

That a checksummed cluster is a `run == 1` extent carrying flag `0x1C00D0`, followed by an 8-byte element
at a 32-byte stride.

### What is true

The u32 at row+0x08 is `flags(u16) | row_size(u16) << 16`. `0x1C00D0` therefore means *flags `0x00D0`
**and** row_size 28* — and 28 is `24 + 4·1`, i.e. `run == 1`. The shipped condition
`flag == 0x1C00D0 and run == 1` states `run == 1` twice. A row carries **one CRC-32C per cluster** and
declares it by its own size field at +0x0A: 24 for a plain run, `24 + 4·run` otherwise.

On `lab314_main/LAB_0906/t19_integrity/`:

| file | run | u32 @+0x08 | flags | row_size | stored CRCs | shipped test |
|---|---|---|---|---|---|---|
| `small500.bin` | 1 | `0x1c00d0` | `0x00d0` | 28 = 24+4·1 | 1 | match |
| `big10k.bin` | 3 | `0x2400d0` | `0x00d0` | 36 = 24+4·3 | **3** | **no match — silent** |

All four stored values verify on recomputation. The stride compounded it: a 36-byte row was advanced by
24, landing inside the checksum array and losing every later row in that record.

### A second, independent cause

`_verify_inline_integrity` was called from two places, both inside `cmd_extract`'s *inline-holder*
branch. Both corpus integrity files leave by the **non-resident extent** branch, which never called it —
so even `small500.bin`, the one shape the old constant would have matched, was extracted with no
integrity statement at all. Either defect alone produces total silence.

### The correction

The row's declared size is the rule; flags bit `0x80` (`0x00d0 = 0x0050 | 0x80`) is carried as a
**cross-check**, and a row whose size and flag disagree is reported, never silently resolved. Every
content path routes through one reporter, and a mismatch reaches the exit code at the single content exit.

**A/B on a damaged copy** (one byte flipped in the middle cluster of the run-3 extent):

| build | rc | output |
|---|---|---|
| v1.12.3 | **0** | nothing |
| fixed | **2** | `INTEGRITY MISMATCH — 1 of 3 … stored=0x21fbf5bf actual=0x2bab73b9` |

Both deliver the same bytes: the verdict changed, not the content.

---

<a id="e100"></a>
## E100 — `total_sectors` counts the VBR's own sectors, not 512-byte LBAs; six sites assumed 512 and a healthy 4Kn volume was reported damaged

**Status:** tool defect, present through v1.12.3; corrected 2026-09-19 (A4).
**Reported by:** the 2026-09 blind audit (K061, K062).
**Affects:** `summary`, `fastsummary`, `integrity`, `export metadata`.

### What is true

`total_sectors` at VBR+0x18 counts sectors of the size the VBR itself declares at **+0x20**. Six sites
multiplied it by a hard-coded 512. On 512e volumes `bps == 512`, so the error is invisible — and exactly
**two** images in a 125-image corpus have `bps != 512`, which is why it was never caught.

On the **undamaged** `lab314_4kn` (bps 4096, total_sectors 1,032,192):

| surface | v1.12.3 | fixed |
|---|---|---|
| backup boot sector | `LBA 1032191 — MISSING/unreadable` | `present, identical to primary, checksum OK` |
| superblock copies | **1**, plus `[WARN] fewer than 2 SUPB copies located` | **3** (LCN 0x1e, 0xfbffd, 0xfbffe) |
| verdict | `WARN — 2 warning(s)` | `PASS` |
| volume size | **504.0 MB** beside a 4.0 GB image | **3.9 GB** |

The backup VBR is at `ps + 1032191*4096 = 0xfcfff000`, byte-identical to the primary; the tool read
`ps + 1032191*512 = 0x207ffe00`, half a gigabyte into a 4 GB image. The same constant bounded the SUPB
search at `end_lcn = 129,024` while the backup superblocks sit at LCN 1,032,189 and 1,032,190.

### The evidence bundle shipped wrong bytes under a hash

`export metadata --what vbr,supb` on that healthy volume wrote 512 bytes from the middle of the volume
as `vbr_backup.bin`, labelled "backup boot sector @ last LBA" and listed in `sha256sums.txt`:

```
v1.12.3 : sig=b'\x01\x00\x00A'   00ba0001000041ff542428488b45f033
fixed   : sig=b'ReFS'            00000052654653000000000000000000
```

The fixed bundle also gains two artefacts it never contained — `supb_backup_lcnfbffd.bin` and
`supb_backup_lcnfbffe.bin` — the backup superblocks were outside the search window and so were absent
from the evidence bundle entirely.

**Controls:** `integrity` output is byte-identical on `win11refsmini`, `win10refsmini` and `lab314_64k`.

<a id="e101"></a>
## E101 — Prade's checkpoint clock at CHKP+0x60 was refuted in favour of +0x10; the driver's selection comparator reads +0x60

**What the register said.** `FS_CHKP_005` (raw notes): *"Virtual clock at CHKP+0x10 (not 0x60 as in
Prade); increases monotonically; higher value selects"*. Prade's +0x60 was treated as an error.

**What is true.** Both offsets carry the clock and they agree on every corpus volume measured, so the
earlier reading of +0x10 was not a misread — but the **selection** the statement is about is performed
on **+0x60**. `ChooseCheckpointRecord<0>` (win11 refs.sys 10.0.26100.8115, `1401051b0`) compares
`*(unsigned long long *)(param_1 + 0x60)` against `*(unsigned long long *)(param_2 + 0x60)` and reads no
other field. It also returns a **distinct third value when the two are equal**, i.e. a tie is signalled
rather than resolved by picking a side. Prade named the right field for the right purpose.

> **UPDATE 2026-11-20 (RUNNING_LOG N140; F1, `analysis/reports/v1.13.2/F1_CHECKPOINT_TIE_READING.md`):** the
> distinct value is real, but no caller leaves a tie undecided. `ReadLatestCheckpoint` reads the copies in superblock
> slot order, skips a copy that fails its validation and switches only on a strictly greater unsigned +0x60, so a tie
> between two valid copies keeps slot 0 (17134, 26100.8115 / .8521 / .8972 / .9444 / .9549, Insider 29574). On 26100.x
> and Insider the slot comparison is written inline and the comparator is used only among the data copies of one slot
> (`ReadAndRepairSelfChecksumBlock`). Read "a tie is signalled rather than resolved by picking a side" as "the
> comparator signals a tie; its caller keeps the copy it already holds".

**Why it matters.** Refuting +0x60 removed the only field the driver actually compares. Anything keyed
on +0x10 agrees with the driver *only for as long as the two clocks agree* — which is a property of the
volumes measured, not a guarantee — so a record whose +0x10 and +0x60 diverge would be selected by a
field the driver ignores. Measured: the two match on every corpus volume, so a divergence is itself
worth reporting.

**This is the E49 frame error again** — a literature offset was refuted without first asking whether it
named a different field for a different purpose. The rule stands: let the bytes pick the frame, and check
what the driver reads before calling a published offset wrong.

**Corrected:** `FS_CHKP_005` note rewritten; `docs/structures/chkp.md` states the comparator, its build
and address, and the tie behaviour. The tool's selection sites were reading +0x10 and are corrected in
1.13.0 (K037/K038).

<a id="e102"></a>
## E102 — a metadata page is 16 KiB or 64 KiB; `4 x cluster_size` is the page only on 4K volumes

**What was assumed.** `4 * cluster_size` was hardcoded as "one page" at four sites across both tools,
and the two CHKP SHA-256 rows in `summary` used different scopes: the PRIMARY hashed one CLUSTER, the
SECONDARY hashed `4 * cs`.

**What is true.** A metadata page is a fixed **byte size** — 16 KiB on 4K-cluster volumes (4 clusters)
and 64 KiB on 64K-cluster volumes (**1** cluster). The cluster COUNT varies, not the size. Confirmed on
disk by the page header's own LCN tuple at page+0x20, which lists the clusters a page occupies:
4K gives `[self, self+1, self+2, self+3]`, 64K gives `[self, 0, 0, 0]`.

So each CHKP row was wrong on the geometry the other was right on:

| cluster size | primary hashed `cs` | secondary hashed `4*cs` | true page |
|---|---|---|---|
| 4,096 | 4,096 — a QUARTER page | 16,384 — correct | 16,384 |
| 65,536 | 65,536 — correct | 262,144 — FOUR pages | 65,536 |

**Note on the CHKP header:** a checkpoint page's +0x20 is a single **self-LCN** field, not the 4-entry
tuple an MSB+ page carries there, so it reads `[self, 0, 0, 0]` on every geometry and cannot be used to
infer the page span.

**Corrected in 1.13.0:** one helper (`_page_bytes` = `max(16 KiB, cs)`) used at all four sites and
shared by both tools, pinned in `single_source.tsv`. The CHKP primary now hashes the page. Recorded
CHKP SHA-256 values from earlier releases will not match: the volume has not changed, the byte range
being hashed has. On 4K volumes the primary value moves; on 64K the secondary.

<a id="e103"></a>
## E103 — the USN `$J` declares its own lengths and `$Max` is resident; both were present and unread

**What was assumed.** That `$J` has no usable length field, and that `$Max` is extent-backed.

**What is true.**

1. **`$J` declares its lengths.** They are in the Change Journal value's embedded `$DATA` row whose
   inline-header offset (value+0x00) is **0x88**: allocated size, stream size, valid data length and
   disk allocation at **+0x30, +0x38, +0x40, +0x48**. On all 21 corpus volumes with a journal exactly
   one row matches and all four fields equal the sum of the `$J` extents' clusters — across 32, 64 and
   128 MiB allocations, both cluster sizes and a 4Kn volume. The row's KEY TYPE varies (0xf8, 0x108,
   0x190, 0xa00, 0xc30) and is **not** a discriminator; `ihdr == 0x88` is.

   The earlier conclusion came from reading the multi-instance MARKER's declared size, which is the
   `$DATA` descriptor constant `0x000E0080` (917,632) — capping the read at it truncated every journal
   larger than ~896 KiB. That the constant is not a length is true; concluding that no length exists was
   a frame error of the E49 kind, and it put the real fields out of reach.

2. **`$Max` is RESIDENT.** It is ~40 bytes and has no extents, so a parse gated on `$Max` extents never
   ran. Its parameters sit in the single-instance sub-record behind a small header: a u32 at **+0x08**
   gives the offset at which they start — **12 (0x0C) on all 21 volumes** — and the u64 there is
   MaximumSize, equal to the `$J` allocation on all 21. Because the data begins at +0x0C, reads taken
   on 8-byte boundaries from the sub-record start miss every field by four bytes.

**Corrected in 1.13.0:** `usn --info` prints the declared lengths and the `$Max` parameters, and a
declared length that disagrees with the extents' allocation is reported as a finding (exit 2) — a
shrunken declaration was previously accepted with no change to any output.

<a id="e104"></a>
## E104 — Object-Table `value+0x18` is a per-object LSN, not a "generation counter = checkpoint virtual clock"

**What the register said.** `FS_OTBL_002` (prior work) describes the Object-Table row value as
"page ref + **durable LSN** + variable buffer" and then adds "generation counter at **u32[6]** = checkpoint
virtual clock"; `FS_OTBL_RA_002` carries the same 8×u32 header with `u32[6]` named `generation` and
`u32[7]` named `dirty_gen`.

**What is true.** `u32[6]` (value+0x18) and `u32[7]` (value+0x1C) are not two counters. They are the two
halves of one **64-bit log sequence number** — `u32[6]` the offset within a log segment, `u32[7]` the
segment number — in the same address space as the checkpoint LSN at `CHKP+0x70`. This is the
"durable LSN" the prior-work description already named; the error is in where it was placed and what
`u32[6]` was then taken to mean.

**Why the old reading cannot be right.** A checkpoint virtual clock is one value per volume. This field
takes **8 to 50 distinct values on a single volume**, one per object, and its magnitude is unrelated to
the clock: on `labG_0` the virtual clock is 4020 while the field ranges 0..19907.

**Evidence — a controlled experiment with a null control (LAB-G).** Three images of one volume:
`labG_0` creates `dirA`, `dirB`, `dirC` (f0..f4 each); `labG_1` modifies **one** file in `dirA` only;
`labG_2` modifies **one** file in `dirB` only. `dirC` is never touched after creation.

| dir | OID | labG_0 | labG_1 | labG_2 | predicted | observed |
|---|---|---|---|---|---|---|
| dirA | 0x762 | `0xa000008dd` | `0xb000008f1` | `0xb000008f1` | advance at G1 only | UP, SAME |
| dirB | 0x763 | `0xa000008de` | `0xa000008de` | `0xc00000906` | advance at G2 only | SAME, UP |
| dirC | 0x764 | `0xa000008df` | `0xa000008df` | `0xa000008df` | never move | SAME, SAME |

6 of 6 transitions as predicted, control frozen across all three. The segment half advances 0xa → 0xb →
0xc across the series, the offset half 0x8dd → 0x8f1 → 0x906.

**Corroboration, 15/15 volumes.** The **maximum** `u64` at value+0x18 equals the active checkpoint's own
LSN at `CHKP+0x70` **exactly** on all three LAB-G images and on 12 randomly sampled corpus volumes
(4K and 64K clusters, v3.4 through v3.14, 2 GB to 2 TB, one 4Kn). That is what you expect when the object
table is the last structure written at checkpoint time, so its highest row carries the checkpoint's LSN.

**Forensic consequence.** This is a per-object last-write clock in **log time**, written by the driver and
reachable by no user-facing API: it orders object modifications independently of `$SI` timestamps, which
an attacker can set, and identifies every object modified after a given checkpoint.

**Scope.** Measured on v3.4–v3.14. No tool currently surfaces it.

<a id="e105"></a>
## E105 (audit K145) — The SUPB page DOES have a self-checksum; `0x08` is simply not where it lives

**What the register said.** `FS_SUPB_RA_002`, status CONFIRMED: *"SUPB page has NO self-checksum (offset
0x08 always 0x00000000). SUPB is outside the Merkle-tree checksum chain — it is the root and has no
parent to store its checksum."*

**What is true.** The observation is correct and the conclusion does not follow. `SUPB+0x08` is indeed
`0x00000000` on every volume — and the SUPB's self-checksum is not stored there. It is in the page's
**self-descriptor (`LcnWithChecksum`)**, which on a SUPB sits at **`SUPB+0xD0`**:

| field | offset | value on `win11refsmini` |
|---|---|---|
| self-LCN | `+0xD0` | `0x1e` — the page's own LCN, `SUPB_LCN` |
| marker byte (`== 0x08`) | `+0xF3` | `0x08` |
| **cktype** | `+0xF2` | `1` = CRC32-C (4 KiB clusters; `2` = CRC64 on 64 KiB, `4` = SHA-256) |
| digest length | `+0xF4` | `4` |
| **stored digest** | `+0xF8` | `6bba010c` |

Recomputing it — descriptor region zeroed, checksum over exactly one cluster, the algorithm of
`CmsVolume::ComputeOrVerifySelfChecksumBlock` — **matches the stored digest**. The tool has verified this
all along and prints it: `SUPB primary LCN 0x1e — checksum OK`, on the primary and both backups. The
register and the tool contradicted each other, and the tool was right.

**Why the wrong conclusion was reachable.** This is the **E49 frame error** again, and the third instance
recorded: a field was read at an assumed offset, found to be zero, and the *structure* was declared
absent. "Not at `0x08`" is a fact about `0x08`; it is not a fact about the page. The second clause —
"outside the Merkle-tree checksum chain ... no parent to store its checksum" — remains true and is
exactly *why* the page carries its own: a root with no parent needs a self-checksum, it does not lack one.

**Consequence, which is not cosmetic.** `A5/K033` now recovers a volume whose primary superblock is
destroyed by falling back to a backup copy, and it accepts that copy **only if the copy passes this very
checksum**. Under the retracted reading there would have been nothing to validate a backup with, and the
fallback could not be made safe.

**Scope.** All 26 volumes measured, 4 KiB and 64 KiB clusters; the descriptor is located by its marker
byte rather than a fixed offset, so the same rule holds for CHKP pages, which carry it too.

**The rest of the project already had this right.** `docs/concepts/checksum_architecture.md` documents
"self-checksum (`LcnWithChecksum` @SUPB+0xD0, digest @+0x28)", and the tool verifies and prints it. Only
the register row disagreed — which is the useful lesson: a CONFIRMED row is a claim, and when the
register and the bytes disagree, the bytes win. (CLAUDE.md states this; here it was load-bearing.)

<a id="e106"></a>
## E106 (audit K131) — `CT_CTBL_010` was refuted in the wrong frame: row-relative `+0xA0` IS the container start on 160-byte rows

**What the register said.** `CT_CTBL_010` ("0xA0-0xA7: CSC starting position"), status **CONTRADICTED**,
on the grounds that *"value+0xA0 is OUT OF BOUNDS for 160B (4K) rows (last offset 0x9F)"* and that on
224-byte rows `value[0xA0:0xA8]` is zero.

**What is true.** Both observations are correct **and they were made in the wrong frame.** Read
**row-relative** — from the start of the B+-tree row, not the start of its value — `+0xA0` is exactly the
container's physical start on every 160-byte row measured:

| volume | version | cluster | value length | `row+0xA0` == physical start | `value+0xA0` |
|---|---|---|---|---|---|
| `win10refsmini` | 3.4 | 4 KiB | 160 | **31 / 31** | out of bounds 31/31 |
| `win11refsmini` | 3.14 | 4 KiB | 160 | **31 / 31** | out of bounds 31/31 |
| `win11refs2g_sha256checksums` | 3.14 | 4 KiB | 224 | 1 / 31 | in bounds |
| `win11refs5g64k` | 3.14 | 64 KiB | 224 | 1 / 79 | in bounds |

So the claim **holds, row-relative, on 160-byte rows**, and does **not** hold on 224-byte rows in either
frame. "Out of bounds of the value" is a fact about the value, not about the row.

**The register was internally inconsistent about the frame.** `CT_CTBL_009` ("Container ID at 0x10"),
from the *same source*, is **row-relative and CONFIRMED**. Two adjacent offsets from one author were
measured against two different origins, and only the one that came out wrong was recorded as the
author's error. This is the **E49** failure a fourth time, and the clearest instance of it: the
discriminator was not the bytes but which origin the measurer happened to choose.

**Corrected status:** `CT_CTBL_010` is **CONFIRMED for 160-byte rows, row-relative**, and **not
applicable** to 224-byte rows. The frame is now stated in the row, because a field offset without an
origin is not a claim that can be checked.

**Rule this generalises.** Every offset in the register needs its frame named — row, value, page or
record. Where one is missing, a re-measurement can "refute" a correct claim simply by choosing the other
origin, which is what happened here and in GN_IDXR_004 (E49).

<a id="e107"></a>
## E107 (§3.5, LAB-C2) — integrity does not CONVERT a resident stream; it makes a file extent-backed AT BIRTH

**What was open.** E87's trigger census of sub-2 KiB extent-backed main streams lists **"6 on
integrity-streams volumes"** — an association with no mechanism behind it — and the project and the audit
disagreed about what it meant. Two different questions had been merged: does enabling integrity on an
existing resident stream CONVERT it, and is a file created under integrity extent-backed from the start?
LAB-C2 keeps them apart, which is what makes the answer clean.

**What is true.** Measured on `labC2.raw`, all six files 512 or 1500 bytes — below the 2 KiB inline
ceiling — and every arm verified on the volume before the image was taken:

| arm | how it was made | DataResidency | HasIntegrity | AllocatedSize |
|---|---|---|---|---|
| **C1** | written first, `Set-FileIntegrity` enabled **afterwards** | **inline** | **True** | 512 / 1500 |
| **C2** | created **inside a directory that already had integrity on** | **extents** | True | **4096** (a full cluster) |
| **C3** | control, integrity never touched | inline | False | 512 / 1500 |

1. **Enabling integrity on an existing resident stream does NOT convert it.** C1 carries
   `HasIntegrity = True` while its bytes stay in the record. This agrees with the static reading —
   `RefsChangeResidentStreamIntegrity` is not among `RefsConvertToNonResident`'s callers in any of the
   six builds — and the two lines of evidence now meet.
2. **A file BORN under integrity is extent-backed from the start**, and allocates a **full cluster** for
   512 bytes. So integrity-at-creation belongs on E87's trigger list; it is a creation-time path, not a
   conversion path.
3. **Enabling integrity does not rewrite the content.** The lab recorded each file's SHA-256 before and
   after the enable and they are identical (`21F928B7…` == `21F928B7…`), so the C1 result is not an
   artefact of the bytes having been left untouched by accident.

**This resolves E87's six rather than contradicting them:** they are C2-shaped, not C1-shaped. E87's
one-directional rule stands unchanged — **≥ 2,048 ⇒ extents; < 2,048 ⇒ inline unless a conversion
trigger fired** — with integrity-at-creation now a named member of that trigger set.

**Acceptance.** All six files extract **byte-exact** against the hashes Windows computed at creation, and
`integrity --checksums` verifies the per-cluster CRC-32C on the two streams that have one — the C2 pair.
The C1 pair has `HasIntegrity = True` but no per-cluster CRC extent, which follows from its bytes being
inline: there is no cluster to checksum.

**Method note.** The first LAB-C produced an image on which every integrity call had silently failed, and
its log said `OK` on every row. LAB-C2 proves the mechanism on a throwaway file before creating any test
state, verifies every set, and refuses to tell the operator to image unless the arms are measurably
distinguishable. Its `C4` row — `c2=ON c3=OFF — the arms are distinguishable` — is what makes this image
evidence rather than an assumption.

<a id="e108"></a>
## E108 (audit K135, K137, K138, K139, K140) — four static register claims corrected by a symbol census

All four rows asserted something about the driver that a census of the decompiled builds contradicts.
They are grouped because they share one cause: a static claim was recorded from one build, or from a name
someone expected to find, without checking the other builds for it.

**Census basis.** The `.decomp.index.tsv` sidecars (name, address, line, size) for win10 17134 (v3.4),
win11 26100.8115, .8521, .8972, .9444 and Insider 29574.

| row | said | the census says |
|---|---|---|
| **FS_SCHM_RA_002** | `CmsReadCache::ResetReadCacheMetadataFile`, `static_scope = win11+` | present in **win10 17134 only**, and the `0xe110` constant appears **only** in the win10 decompilation. The scope is exactly inverted: this is a **v3.4** symbol, absent from every v3.14-era build |
| **FS_OTBL_SA_009** | `DeleteIdentifier` is "**30 bytes** (Insider, thin wrapper around DeleteRow)" | **110 bytes** in Insider, **119** in win11 26100.8115. Not a thin wrapper |
| **FS_OTBL_SA_009** | "DOES NOT decrement counter — **guarantees** OIDs are never reused after deletion" | the absence of a decrement in ONE function does not guarantee a global property. What the code supports is narrower: *this* function does not decrement and only calls `DeleteRow`. The no-reuse behaviour is established **on disk** (gaps equal deletions), not by this function |
| **GN_SNAP_SA_001** | "`CStreamSnapshot` class; 6 -> 24 functions" | **no build contains a `CStreamSnapshot` symbol.** The snapshot functions are `Refs*StreamSnapshot*` — `RefsCreateStreamSnapshot`, `RefsListStreamSnapshots`, `RefsQueryDeltasStreamSnapshot`, `RefsCheckStreamSnapshotManagementBuffers`, `RefsStreamSnapshotManagement`. The "6 -> 24" count has no witness |
| **FS_RESD_SA_002** | "exists only in the v3.14-era drivers" | correct, and its `static_scope` already excludes Insider — but the prose reads as though Insider is included. Measured: present at `1400b9384` (win11 26100.8115) and `1400b93dc` (.8521), **81 bytes**, and **ABSENT from Insider 29574** |

**The pattern worth keeping.** Three of the five are *scope* errors — a symbol attributed to the wrong
build family — and one names a symbol that exists in no build at all. A static claim without a build is
not checkable, which is why `static_scope` exists and why its generator's self-test is now a gate step.
A hand-set scope, as these were, bypasses that generator entirely.

<a id="e109"></a>
## E109 (audit K133, K134) — the block-refcount value is not "exactly 0x820": a 32-byte compact form exists

**What the register said.** `CT_BKRC_RA_003`: *"Block-refcount value length is **exactly** 0x820
(2,080 B) … 1,441/1,441"*, and `CT_BKRC_RA_001` gives a value-length formula that follows from it.

**What is true.** Censused over the Block Refcount Table (root 6) on three volumes:

| volume | rows | value lengths |
|---|---:|---|
| `winsider` | 108 | **2,080 B x 106, 32 B x 2** |
| `win11refs5g64k` | 2 | 2,080 B x 2 |
| `lab314_main` | 0 | (table empty) |

So "exactly" fails on the row's own witness, and the count `1,441/1,441` was taken over a population that
excluded the two exceptions.

**The compact form is the full form with the array omitted**, and the arithmetic says so exactly:

```
2,080 = 28-byte header + u16[1024] per-cluster array (2,048) + 4-byte trailer
   32 = 28-byte header +                               (none) + 4-byte trailer
```

Both 32-byte rows on `winsider` carry a well-formed header — the key's `StartLCN` and `BlockCount`
mirrored into the value at `+0x00` and `+0x08` exactly as the long form does
(`0x741800/0x400` and `0x74b800/0x800`) — so these are valid rows in a second encoding, not damage.

**Corrected statement.** A block-refcount value is **either** the long form (28-byte header +
`u16[BlockCount]` + 4-byte trailer) **or** a 32-byte compact form (header + trailer, array omitted). What
the compact form means — whether it encodes a uniform refcount across the range — is **not established
here** and is not claimed: the two observed rows are consistent with that reading and with others, and
two rows on one volume cannot separate them.

**Withdrawn with it:** `CT_BKRC_RA_001`'s "populated only on 3.14+" and its dedup semantics, which the
audit also flags as untested. Neither is supported by anything measured, and `lab314_main` — a 3.14
volume — has an **empty** table, which is by itself a counterexample to "populated".

<a id="e110"></a>
## E110 (audit K128) — the persisted allocator summary is 416 bytes (u64[52]), not 384 (u64[48])

**What was said.** `FS_ALLOC_RA_002` and **E74** both describe the summary as **384 bytes**, read as
`u64[48]`, and the static note attributes that to `CmsAllocator::LoadAllocatorSummary` copying
`3 x 0x80 = 384`.

**What is true.** `LoadAllocatorSummary` (**refs.sys 10.0.26100.8115, `14003ef8c`**) gates on the
descriptor's own length before reading anything:

```c
if (*(int *)local_res8 - (uint)*(ushort *)(local_res8 + 4) < 0x1a0) { ... }
```

`0x1A0` is **416**, so the function requires 416 bytes available — `u64[52]`, four slots more than the
384 the register and E74 claim. A reader that stops at 384 loses the last four slots and, worse, would
treat a 416-byte summary as if slots 48..51 did not exist.

**Corrected in both places.** The number came from an inferred `3 x 0x80` rather than from the length
the function actually demands, which is why it went unnoticed on both write-ups: 384 is a plausible
figure, and nothing compared it with the code.

**Not corrected, because it is not established here:** what slots 48..51 hold. The audit reads slot 1 as
the allocator's volume cluster count that the driver reconciles with the boot sector; that is consistent
with the register's existing note and is not re-derived here.

---

<a id="e111"></a>
## E111 (audit K118) — the directory bit 28 IS carried in a directory's own row, on Win10-era formats

**What was said.** `STANDARD_INFORMATION.md` described `$SI+0x20` bit 28 as *"masked on Win10,
preserved on Win11"*, and this workspace's own session guidance went further: *"bit 28 lives **only in
the index entry** (`value+0x40`). It is absent from every directory's own-row `$SI+0x20` (0 of 27,531),
so do not look for it there."*

**What is true — and it is the opposite way round.** A directory's own row (`$SI+0x20`, i.e. own-row
`value+0x48`, the word `get_object_si` returns as `file_attrs`) carries bit 28 **only on volumes
written by Win10-era ReFS**, and a volume upgraded from one inherits it:

| format | own rows carrying bit 28 |
|---|---|
| 3.4 (`win10refsmini`) | **1 of 9** — OID `0x705`, `value+0x48 = 0x10000000` |
| 3.7 (`win1121h2test`) | **33 of 113** |
| 3.9 (`win1122h2test`) | **27 of 140** |
| 3.10 (`win1123h2test`) | 0 of 91 |
| 3.14 native (`win11refsmini`, `win11refstestmftecmd`) | 0 of 15, 0 of 241 |
| 3.14 upgraded from Win10 (`win10to11refs4g`) | **2 of 42** |

So "masked on Win10" is false — Win10-written volumes are the only ones that carry it — and "preserved
on Win11" is false: a natively-formatted 3.14 volume never does. The **index entry** at `value+0x40`
carries it on every directory of every format, and bit 28 is the only attribute bit that ever differs
between the two copies.

**How the earlier figure arose.** "0 of 27,531" is a true measurement of **Win11-native volumes**, stated
as if it were corpus-wide. The rule it produced — *do not look for it there* — is right for a 3.14 volume
and wrong for a 3.4/3.7/3.9 one, which is exactly the population a forensic reader is most likely to meet
on an older system. Corrected in `STANDARD_INFORMATION.md` and in the workspace guidance; the audit's own
absolute phrasing ("absent from every directory own-row") is corrected here too, while its conclusion —
that the doc line was wrong — stands.


**Amendment (2026-11-12; RC1-docs G7 I043).** "Win10-era formats" is wrong for 3.7 and 3.9: in this corpus they were formatted fresh by Windows 11 (3.7 by 22000, 3.9 by 22621; the lab's `Format-Volume` transcripts). The per-format bit-28 counts stand: carried on 3.4, 3.7 and 3.9 (and a volume upgraded from 3.4), not on 3.10 or a natively formatted 3.14.

<a id="e112"></a>
## E112 (RC1 auditor B6 / audit K083) — the hard-link timestamp divergence has a mechanism: two layers refreshing at different times

**What was said.** `FN_LINK_003` (2026-07-03) read the `win11refs8g` pair as *"sibling names keep the
true birth, so the LATEST Created among siblings is authentic and a backdated name is the stomp"*, and
recorded the tool as *"flagging only the backdated name (f6_link.bin correctly NOT flagged)"*.
`MD_TS_RA_008` (2026-09-07) then measured the opposite on `lab314_main`: a `SetFileTime` through one name
of the T15 pair left **both** type-0x30 rows byte-identical across their whole 84-byte value. The
reconciliation stopped there — the register said the mechanism *"was never decompiled"* and ten live
pages repeated it.

**What is true.** Both measurements are correct; they observe **different layers**, and the driver
(`RefsUpdateFileDupInfo`, S4) separates them:

* The file's **own record** takes the new timestamp **immediately**. In that sense a name-scoped
  `SetFileTime` updates every name at once — the file has one truth, which is what `MD_TS_RA_008`
  measured and what makes "the latest Created is authentic" unsupportable.
* Each **name's index entry** is a **lazily refreshed cache** of it. The driver refreshes only the entry
  of the name that was **opened**; siblings stay stale until each is opened in turn. That is what
  `FN_LINK_003` measured: the stomp opened one name, the other still held its pre-stomp Created.

**What follows, and it is what the pages must say.** Divergence between a file's names is evidence.
**Agreement clears nothing** — it has two causes, and one of them is that somebody read the file. The
signal is **perishable**: any read of a stale sibling (an antivirus scan, a live triage, the examiner's
own `dir`) refreshes its entry and destroys the difference. And the stale entry is the one nobody
**opened**, which is not the one nobody **forged**, so *which* name holds the authentic birth remains
unestablished — the conclusion `MD_TS_RA_008` reached stands, for a better reason.

**Scope.** `FN_LINK_003` is re-scoped to the index-entry layer and its authenticity inference withdrawn;
its tool-behaviour sentence is corrected (every name of a diverging group is flagged, not the backdated
one — flagging one would assert the others are clean). `MD_TS_RA_008` is kept **as measured**, with the
explanation added: the lab's inventory pass opened both names, which is why both rows agreed.
Corrected in `hard_links.md`, `timestomp_detection.md`, `ntfs_comparison.md`, `artifact_timeline.md`,
`forensic_analysis_workflow.md`, `schema_table.md`, `tool_artifact_map.md`, `concepts/README.md`,
`examples/read_a_hard_link_group.md`, `tools/forefst.md`, in `forefst.py`'s signal comments, and in the
`retired_claims.tsv` correction text (its **pattern is unchanged** — the retired claim stays retired).
LAB-A phase 2 is the on-disk confirmation: stomp through one name, read only the stomped name, image;
then read the sibling and image again — the divergence must be present in the first and gone in the second.

**Amendment (2026-11-12; RC1-docs G7 I019; RUNNING_LOG N179).** (a) `RefsUpdateFileDupInfo` is not the whole refresh:
its only direct callers are `RefsSetBasicInfo`, `RefsSetAllocationInfo` and `RefsSetEndOfFileInfo`, and the close path
refreshes the entry through `RefsCommonCleanup` -> `RefsUpdateDuplicateInfo` (call sites read by two critics on
26100.8115 and 26100.9444, and by the lead on 26100.9444: :404361, :494896, :495238, :472569). (b) "the examiner's own
`dir`" was not measured: E112's witness is an open of the sibling (LAB-A A5b), a listing opens no handle on the child,
and on the lab volume measured a directory listing alone did not refresh the entry. (c) The per-name copies are not
something NTFS lacks: NTFS hard links share one `$STANDARD_INFORMATION`, but each NTFS link has its own `$FILE_NAME`
with its own times. Corrects master §C.3 and §J, register FN_LINK_003, and the NTFS contrast on `hard_links.md`,
`timestomp_detection.md`, `ntfs_comparison.md`, `artifact_timeline.md`, `forensic_analysis_workflow.md`,
`attributes/STANDARD_INFORMATION.md`, `examples/read_a_hard_link_group.md`.

<a id="e113"></a>
## E113 (v1.13.0 post-publication check) — the N94 carve classification is withdrawn: the refused carves were genuine, and the stride "fix" was the misalignment

**What was said.** In the RC3 response, `RC3_evidence/N94_carve_classification.md`, N98, the v1.13.0
changelog and the v1.13.0 migration notes: 1.13.0's 111 refused carves on `win11refstestmftecmd` were
fabrications 1.12.3 had produced — 95 "read under sparse holes", 14 from "a misaligned walk whose cluster
counts summed to exactly the file's allocation **by coincidence**"; `GFSAREPLAY` at the start of those
carves was "a filesystem-internal signature"; the 19 changed carves were "the K001 marker shape — a content
correction"; **"nothing genuine was lost"**; and a reader holding 1.12.3 carve output should not rely on
the files 1.13.0 refuses.

**What is true.** Every clause above is wrong, and the last one told readers to discard real evidence.

* **The refused carves are genuine.** Most remnants are prior versions (`[CoW prior-version, same
  directory]`) of files that are still live. Extracting the live twin — same name, same size — **with 1.13.0
  itself**: of the 111 dropped carves, 93 have a live twin and **86 are byte-identical to it** under
  1.12.3; of the 14 changed, 12 have a twin and 8 match 1.12.3 (only 3 match 1.13.0). The journal shipped
  with the sample confirms one independently: `0x869:0x2` was created, extended, overwritten, closed and
  renamed — written once, never changed.
* **`GFSAREPLAY` / `GFSAPPEND` are the test generator's own content markers**, not filesystem metadata.
  No dropped carve contains a metadata signature (`MSB+`, `CHKP`, `SUPB`, `FVE-`): 0 of 111.
* **The 95 are not holes.** The written bit (`0x10`) is per **row version**. For VLCN 701203 the live row
  carries `0x1C00D0` (written) and the slack remnant `0x180040` (not written): that version was committed
  between allocation and the write. Zero-filling its runs is version-accurate and the safe default (N63:
  reading unwritten clusters can deliver another file's bytes); what was wrong was presenting the zeros
  silently, with `confidence: high`, and calling them a correction of fabricated content.
* **The 14 were not a coincidence.** Extent rows are **8-byte aligned** — as `extent_descriptors.md`
  already said. A3 (E99) stepped by a row's declared **size** instead of its aligned **step**: after a
  28-byte checksummed row it landed 4 bytes short of the next real row. The pre-A3 code stepped 32 there
  (`align8(28)`), right by accident; for a three-cluster row the size is 36 and the step 40, and both old
  and new code were wrong. On the public sample **29 of 29** stops after a 28-byte row have a valid row at
  +32. The old decoder's runs summed to exactly `needed` on 10 of 10 files **because the rows are real**.
* **The same misstep made a verdict false.** `_verify_inline_integrity` walks the same rows:
  `integrity --checksums` verified **127 of 142** CRC-bearing clusters and printed "every checksummed file
  cluster matches its stored CRC-32C".

**What changed, in 1.13.1.** One `_extent_row_step()` (declared size rounded up to 8) at all eight stride
sites — the four the check named plus four that index rows as `base + i * 24` — with a lint that fails on
any other. Integrity: **142/142**. Carves: **+14, 0 lost, 0 changed**. The verdict prints "every" only when
the clusters checked equal the clusters carrying a CRC; a gap is a counted finding reaching `rc`. Every
prior-version zero-fill is disclosed per file (manifest `unwritten_zero_filled_bytes`,
`unwritten_nonzero_on_disk_bytes`, `refused_all_unwritten`), and confidence drops from `high` when the
zeros cover data that is on disk now.

**How it was missed.** The classification was issued with no ground-truth control, although one — the
live twin — was on the same public volume; a discriminator ("does the carve contain its own name?") was
tried, found to measure the corpus's style, and then no real third source was sought; and a 10-of-10
exact match was written down as a coincidence. Two rules follow and are adopted: **a classification of
lost evidence needs a ground-truth control before a verdict**, and **an unexplained exact match is a
finding, not a coincidence**.

<a id="e114"></a>
## E114 (audit K095 / K066 / K006, v1.13.1) — three figures the reference trusted as the file's or the volume's own were copies or sums

**What was said.** `structure_reference.md` (index entry, value+0x58): FileSize "== independently-parsed
embedded-$DATA size on **409,514 / 409,514**"; value+0x60: "Allocation **≥ file size**". §B.2b and
`FS_ALLOC_RA_002`: allocator summary "slot 2 = **free clusters**" (and "384 bytes / u64[48]", which E110
had already corrected). The tool took a split file's attributes from its name row, adding only the EA bit.

**What is true.**

* **value+0x58/+0x60 are a cached copy** of the `$DATA` stream's size and the file's allocation — the index
  entry is the lazily refreshed cache E112 describes. Over 117 images the size agrees on **623,322 of 623,326**
  embedded rows; the 4 exceptions are all stale-low on actively appended files, all on the two images of one
  real Windows installation (`winsider` `StorGroupPolicy.log`, a System32 file, `wpndatabase.db-wal`;
  `winsiderv2` `wpndatabase.db-wal`), plus one split record's backing (`winsiderv2`, 1,460 vs 1,606). Where they
  disagree the `$DATA` record is authoritative; on `wpndatabase.db-wal` the stale allocation (3,211,264) is below
  the stream's size (3,271,312) and its extent map covers 3,276,800, the stream's own figure.
* **+0x60 can be below the size while current**: on a sparse file it counts only allocated clusters — 53
  embedded rows, every one carrying the sparse attribute. Where the stream's two allocation fields differ the
  current copy follows `disk_alloc` on sparse files and `total_alloc` where blocks are shared; neither
  reproduces it alone.
* **A split file's attributes are its backing's (+0x48).** The name row's +0x40 is the same kind of cache: on
  `win11refstestmftecmd` the two differ on 47 of 577 split names, and the file's latest change-journal record —
  the driver's own view — carries the backing's attributes on 47/47 (16 as 0x80 NORMAL for a backing of 0),
  the name row's on 0.
* **Allocator slot 2 counts clusters NOT ALLOCATED, which is more than Windows calls free.** Windows'
  `fsutil fsinfo refsinfo` splits it into *Free Clusters* and *Total Reserved*: on `win10refsmini`, captured
  unchanged, slot 2 = **327,420 = 244,188 free + 83,232 reserved** exactly, and slot 1 − slot 2 = **180,484 =**
  Windows' total − free − reserved. So *covered − not-allocated* is Windows' own "used", and the audit's
  decomposition of it on the CTF volume (other tiers' spans, a range no Medium row covers) describes what
  Windows counts as used too. The reserved count is in none of the summary's 52 slots on the three witnesses.

**Witnesses** (transcripts with fsutil output): `win10testchecksum.txt` ↔ `win10refsmini(_testchecksum)` (v3.4,
0 difference); `win1124h2testchecksum.txt` ↔ `win11refsmini_testchecksum` (v3.14, 12 clusters: captured after);
the lab314_64k inventory ↔ `lab314_64k` (45; the lab ran after it). Excluded, with the reason: 
`transcript_win1122h2.txt` ↔ `win1122h2test` — the image holds 1.3 GB of files, which cannot fit in the 449 MB
Windows reported used when the transcript was taken; it predates the content.

**Scope.** Master: the value+0x58/+0x60 rows and §B.2b (slot 2, and E110's size). Register: `MD_DISK_RA_003`
(note), `FS_ALLOC_RA_002` (slot 2). Tool (1.13.1): K095 (AllocatedSize; and FileSize where a split record's backing header is stale),
K006 (split attributes), K066 (`summary` prints "not allocated", not "free"). Docs: `directory_entries.md`, `tools/forefst.md`.

<a id="e115"></a>
## E115 (1.13.1 corpus-golden accounting) — the public sample holds 55,586 checksummed clusters, not 142

**What was said.** E113, the post-publication check, the 1.13.1 plan, response and changelog draft, and
`extent_descriptors.md`: `integrity --checksums` on `win11refstestmftecmd` verified "127 of **142**" CRC-bearing
clusters in 1.13.0, and the aligned row step made it "**142/142**" — "every checksummed cluster on that volume".

**What is true.** The volume holds **55,586** checksummed clusters in **189** files; 142 was the subset in the 23
files the verifier reached. Four more defects kept the rest out, each silent — no count, no finding:
* it walked an extent node's **slots in order** instead of through its key index, so a superseded slot in front
  of the live row used up the walk (win1122h2test: 189 of 3,820 checked, "every ... matches", PASS);
* a file whose extent map spans **more than one node** was read as carrying no stream (its index rows failed the
  plausibility test on the first read and the file returned "nothing inline");
* a **split** file (hard-linked or moved) was checked through its 84-byte name row, which holds no `$DATA`;
* a record whose **virtual** cluster number exceeds the **physical** cluster count was treated as impossible.
**Control:** per CRC-flagged extent, the fixed verifier's set is IDENTICAL to the extraction decoder's (as it was
before the change, with its own descent) on four volumes — 300 / 298 / 272 / 537 extents, 0 missing, 0 extra — and
every one of the 55,586 checked clusters matches its stored CRC-32C, which a misread row could not do (55,398
distinct stored values there). On the 21h2/22h2 volumes the same argument is weaker — 3,504 of their 3,820 CRCs are
the CRC of an all-zero cluster, which a read of the wrong zeroed cluster would also match — so there the extent-set
identity with the extraction decoder is the evidence, not the CRC matches.

**Scope.** E113's statements about the stride stand; its figure "142" is a subset, not the volume's total. The
changelog, `extent_descriptors.md`, the 1.13.1 plan and response state 55,586. Tool: `_extent_leaf_rows` (the one
key-index walk, shared with extraction), `_verify_inline_integrity`, `_verify_volume_integrity_streams`.

<a id="e116"></a>
## E116 (1.13.2 F5, filed 2026-11-07 in 1.14.0's labs-and-driver batch after open question Q39; N11, N136, N342; audit K058, K060) — MLog control `+0x18` is the log start and `+0x20` the log end, each as of the last control-area write; `+0x18` is neither the log's tail nor where replay begins, and the "Generation" 1.13.1 printed is `+0x20`'s block offset

**What was said.** docs `structures/mlog.md`, the control payload: "+0x18 | LSN oldest | Oldest active LSN" and "+0x20
| LSN (duplicate of +0x18)", with "the LSN/generation pair"; `docs/tools/forefst.md` Known issues (published 1.13.1):
"+0x18 ... on the volumes measured it is the log's tail"; the 1.13.1 tool's labels "LSN oldest" / "Generation" and its
`--json` keys `lsn_oldest` / `generation`; NEW_FINDINGS N11; the K058 disposition text (`gen_wrong_verdict_coverage.py`,
`gen_audit_response.py`); register `FS_CHKP_007` (the "byte offset" and "both CHKPs always identical" wording).

**What is true.** Control `+0x18` is the **log start** and `+0x20` the **log end**, each as of the last control-area
write (on Insider 29574: the last write that refreshed the staged copy; its two HMAC writers write without refreshing
it). `+0x18` is neither the log's tail (the end of the newest record) nor where replay begins: replay starts at the
chosen checkpoint's `+0x70`, and the open refuses a log whose start is past it (`MlLogOpenLog`; 17134 does not test it).
The "Generation" 1.13.1 printed is `+0x20`'s block offset (its low u32). On the images measured, start = end = tail
except on two v3.14 4K log instances (the four millionsofactions images, one log, and labFbeforereboot). **LAB-F**:
the dirty mount of 2026-09-20 06:53:53 (ReFS/Operational record 203) reports `LogRestartStartLsn` 8:109e;
labFbeforereboot's checkpoint in use (slot 1, clock 3986) holds `+0x70` = 8:109e, the other copy (clock 3985) 8:89c,
and both control copies `+0x18` = 8:89c -- the replay started at the newest checkpoint's `+0x70`, not at `+0x18`. The
next clean mount (record 208) reports 9:8a2 = labFafterreboot's `+0x70`, `+0x18` and `+0x20`. Not explained by the
image: record 203's checkpoint clock 3994 (the image's newest copy: 3986) and its `LogRestartLastLsn` 8:4dc3 (the
image's log end: 8:4b41) -- the log grew after the image was taken, or those fields mean something else; the event
fields' mapping is inferred.

**Scope.** Static (`analysis/reports/v1.13.2/DEEP_CHECK_VERDICT.md` §8): 26100.8115 carries the full writer census; the
writers are instruction-verified on 17134, 26100.8115, .9444 and Insider 29574, .8521 and .8972 by text identity; the
replay-start chain is instruction-verified on 26100.9444 (full) and .8115 (both ends), on 17134 and Insider only the scan
end. Disk: 147 images / 56 log instances; the start / tail separation on 2 log instances; `+0x18` != `+0x20` on 3
copies; on v3.4, 3.7, 3.9, 3.10 and every 64K volume start = end = tail, so the disk cannot separate the readings there
(v3.4 rests on 17134; no 3.7-3.10 driver read). Replay start != `+0x18`: the static chain, 5 dirty mounts of the May
lab VM's log (ERID 119, 320, 374, 858, 1460) and LAB-F's record 203 against its two images. Not in E116: the relation
"control `+0x18` = the older checkpoint copy's `+0x70`" (seen on labFbeforereboot too; a register row, RD, with that
scope). Evidence: `LAB_J_EVENTLOG_CHECK_2026-10-02.md` §6.3; `analysis/reports/v1.13.2/LD/evidence/q39_labf.py` /
`.txt`. Corrects: the docs (`structures/mlog.md`'s control payload rows, the Known issues item: RC1-docs), register
`FS_CHKP_007`, the tool (fixed in 1.14.0: "Log start" / "Log end", `LogStart` / `LogEnd`).

<a id="e117"></a>
## E117 (1.13.2; N143; filed 2026-10-24 at wave C's close) — MLog control `+0x38` is a u32 log open count, not a write counter; each record's header `+0x20` carries it

**What was said.** The master's LogCore record header row `0x20` "Per-record counter" (§E.2, CONFIRMED); the docs'
MLog control table ("Write counter", 8 bytes) and control-page header ("sequence number, increments each write");
the tool's label "Write counter".

**What is true.** Control area `+0x38` is a **u32** that is 1 when the log is created and +1 at each read-write open
of the log (`MlLogOpenLog`); every store and load is a dword. `LogCoreWriteDataRecord` copies it into each data
record's header `+0x20`, and the control record's header `+0x20` carries the same value, so a record names the mount
session that wrote it. `+0x24` is 0 in every build.

**Scope.** Static: the increment and the copy read at instruction level on 17134, 26100.8115, .9444 and Insider 29574
(8521 and 8972 by text identity), plus three builds without a PDB located by pattern
(`analysis/reports/v1.13.2/DEEP_MLOG_CONTROL_STATIC.md`). Disk: 147 images, 56 log instances, 1,340,053 records,
0 counterexamples, two independent readers (`DEEP_MLOG_REFUTE.md`). Lab: `labJjournal` (26100.8875) holds `+0x38` = 5
after four opens following the format, sessions 2-5 in the record headers without a gap (`LAB_J_RESULTS.md` §5).
Not measured: a read-only mount, a failure after the open, a log re-created by the driver. Verdict and drafts:
`DEEP_CHECK_VERDICT.md` §8.

<a id="e118"></a>
## E118 (1.13.2 F11; N141; filed 2026-10-24 at wave C's close; amends E102) — a checkpoint RECORD is one cluster on every geometry; only its ALLOCATION is a metadata page

**What was said.** E102 extended the page rule (`_page_bytes` = 16 KiB on 4K volumes) to the checkpoint: "the CHKP
primary now hashes the page". The master's §A.4 opening ("each occupying one page — 4 consecutive clusters on
4K-cluster volumes") and E1's evidence line ("LCN quadruples show 4 consecutive clusters") sized the checkpoint as a
page. E102's "at all four sites" missed a fifth checkpoint read with a literal 4 (262,144 bytes per copy on 64K).

**What is true.** The checkpoint record is **one cluster** (4 KiB on 4K volumes, 64 KiB on 64K volumes): it is read,
self-checksummed, bounded, written and initialised at format as one cluster. On 4K volumes the allocator reserves
four clusters `[c, c+4)` for it (the metadata-page allocation); the record uses the first. The checkpoint's own LCN
tuple is `[c, 0, 0, 0]` on every geometry; E1's quadruples are the root references inside the checkpoint, which
point to MSB+ pages.

**What stays true.** E102 for MSB+ pages, and its note that the checkpoint header cannot show a page span.

**Scope.** Static: the record length and writer on 17134, 26100.8115/.8521/.8972/.9444 and Insider 29574 (with a
PDB), plus three builds by pattern; the format reservation and the one-cluster write in refsutil 26100.8115. Disk:
the digest covers one cluster only on 296 of 296 copies (234 corpus + 62 other; 14 of them 64K); the allocator
reserves `[c, c+4)` on 199/199 + 59/59 4K bitmap cases and only `c` on 10/10 64K cases
(`analysis/reports/v1.13.2/DEEP_CHKP_SIZE_STATIC.md`, `DEEP_CHKP_SIZE_DISK.md`, `DEEP_CHECK_VERDICT.md` §4 and §8).
Tool (1.13.2): `checkpoint_select` and `parse_chkp` read one cluster per copy, and every checkpoint SHA-256 hashes that
cluster and says so. Recorded checkpoint SHA-256 values of 1.13.0/1.13.1 on 4K volumes covered 16 KiB.

<a id="e119"></a>
## E119 (1.13.2 wave C, B15 / N449 / N450; filed 2026-10-24) — the superblock primary IS privileged: `+0x68` orders only the two backups, and only an extend bumps it

**What was said.** The master's §A.3: the authoritative copy is the one with the highest `+0x68` among the copies
that pass validation — "primary 0x1E is **not** privileged"; `+0x68` is "bumped on each SUPB rewrite
(`MoveSuperBlock`)"; the copies are healed "when the 3 copies disagree".

**What is true.** `CmsVolume::ReadSuperBlock` reads the copies in the order LCN 0x1E, N-2, N-3 (N = the volume's
cluster count) through `ValidateSuperBlock` and takes the **first valid** copy; a later valid copy replaces it only
when `ChooseSuperBlock` finds its unsigned `+0x68` strictly higher **and** the chosen copy is not slot 0x1E. So a
primary that passes `ValidateSuperBlock` is read whatever the backups hold, and `+0x68` decides only between the two
backups (end-2 on a tie). No valid copy: 0xC0000032. `ValidateSuperBlock` tests, in order: size >= 0xC0, the
self-checksum (descriptor `+0x78`/`+0x7C`), the 32 bytes `+0x20..+0x3F` = {LCN, 0, 0, 0}, byte `+0x04` != 0, u32
`+0x74` = 2, u32 `+0x70` >= 0xC0 and `+0x70` + 0x10 <= the cluster, both checkpoint references (signed) in
[0x1F, N - 3]; there is **no `SUPB` signature test**. After the choice every other slot is rewritten from the chosen
copy unless both other copies are valid with the same `+0x68` as it ("equal" compares `+0x68` only, never the
bytes) or a
volume flag bit is set. `+0x68` is incremented only by `MoveSuperBlock` (at a volume extend), which reads **only**
slot 0x1E and writes the two backups at the new N-2, N-3 with `+0x68` + 1; the primary is not written, and the next
writable mount rewrites the backups from the (privileged) primary, back to its `+0x68`.

**Scope.** `ReadSuperBlock` / `ChooseSuperBlock` read twice or more on 17134, 26100.8115, .9444, .9549 and Insider
29574 (the slot-0 test confirmed in the disassembly of all five); `ValidateSuperBlock` three times on 17134, .8115,
.9549, Insider, once on .8521, .8972, .9444; `MoveSuperBlock` twice on .8115, once on 17134, .9549, Insider. What the
flag bit that skips the rewrite means was read once (.8115: the device is write-protected). Corpus: 349 of 351 signed
superblock copies pass every test, 2 fail their self-checksum only, every `+0x68` = 1; on the two volumes whose
primary fails (`win11refsmini_aftercorruption`, `_openedwith34`) refs.sys reads end-2 (`0x7bffe`). Evidence:
`analysis/reports/v1.13.2/fixes/WAVEC_READING_bootstrap.md` (S1-S11, M1-M6), `WAVEC_PREP.md` §1,
`DRIVER_BUILD_MATRIX.md`; per-build table: `driver_register.md` "Behaviour by build". Tool (1.13.2): `supb_validate`,
`_supb_choose`.

<a id="e120"></a>
## E120 (1.13.2 wave C, N264; filed 2026-10-24) — Container Table row `+0x20` counts ALLOCATED clusters, not free ones

**What was said.** The master's §B.1 160-byte row: `0x20` "Free clusters" (u64, CONFIRMED).

**What is true.** Row `+0x20` is the container's **allocated** cluster count: on each of the 9 v3.4 volumes of the
golden list the sum of `+0x20` over the table equals the allocator's used clusters exactly (win10refsmini 180,484;
win10refs110g 341,122; win10refs5g64k 13,364; win10refs2tspecials 3,164,421; ...), and the driver's
`GetNumAllocatedForContainerEntry` reads it as the allocated count. The two volumes upgraded from 3.4 to 3.14 keep
their v3.4 counts, 28 clusters short of the allocator (210,058 / 210,086); on volumes formatted at 3.7 or later the
field holds all-ones on every row.

**Scope.** Disk: the 9 v3.4 volumes, once (the C3 probe, `analysis/reports/v1.13.2/fixes/C3_NOTES.md`, group ct).
Driver: one reading (`fixes/WAVEC_READING_tables_evidence/reading_facts.md` C5, C10: u32 on 26100.x / Insider, read as
u64 by 17134, kept only for compacted rows or while the root's flag 0x8 is clear). Not settled here: the width
(one reading), `+0x24` (one reading: a compacted length) and `+0x28` (one reading: a second allocation count).

**Also corrected (§B.1a, the row's flags at `+0x14`).** Flag 0x4000 means **every cluster of the container is
allocated**, not "managed by allocator subsystem" (an inference from co-occurrence); and the driver gives 0x0002
(compressed: read through the compressed range), 0x0008 (compacted: found through the Container Index) and
0x0080 | 0x0800 (set together when a needed Container Index row is missing; 0x0800 refuses the container). Read
twice (the N216/N234 reading on 26100.8115 and `WAVEC_READING_tables.md` on 26100.9444 with 17134 cross-checks);
no corpus row carries 0x0002, 0x0008, 0x0080 or 0x0800 (1,591,826 rows).

<a id="e121"></a>
## E121 (1.13.2 wave C, N422 / A50; filed 2026-10-24) — OID 0x7/0x8 and 0x9/0xA are failover pairs: no copy is the "primary" or the "duplicate", and the driver reads 0x8 and 0xA first

**What was said.** The master's §F.4: "0x7 Upcase Table (primary)", "0x8 Upcase Table (duplicate)", "0x9 Logfile Info
(primary)", "0xA Logfile Info (duplicate)".

**What is true.** The Logfile Information table is opened as a failover pair through
`InitializeFailoverMetadataTable(…, {10, 9})` and the Upcase table as the pair {8, 7}: both object records are looked
up (a missing one fails the open), the first identifier is slot 0, two good copies -> slot 0 (OID 0xA, OID 0x8) is
read, one good copy -> that one (on a writable mount the other is revived from it), none -> 0xC0000808 and
`NotifyUnrecoverableMetadata`. Reads go to the current copy; only status 0xC00001A8 fails over. On 117 of 117 corpus
ReFS volumes both copies of each pair verify and hold equal rows.

**Scope.** The pairs and the slot rule read twice on 17134, 26100.8115, .9444, .9549 and Insider 29574
(`analysis/reports/v1.13.2/fixes/WAVEC_READING_tables.md` §2 with FIX_GB_part3c S1); the bad-flag source (root
descriptor `+0x08` bit 0x8) and the Container Table as the same kind of pair (roots 7/8): one reading. Tool
(1.13.2): no copy of OID 0x7-0xA is labelled "dup" or "pri".

**Update (2026-11-21, KNOWLEDGE_INTAKE A127; RUNNING_LOG N639).** The Container Table pair's slot rule (root 7 =
slot 0, root 8 = slot 1, `CmsFailoverBPlusTable::InitializeTables`, slot 0 unless it fails) was read a second time
on 26100.9711 (`InitializeVolumeAllocator` :207565-207587 -> `CmsVolumeContainer::Initialize`; KNOWLEDGE_INTAKE
A127, 2026-11-05), so it is read twice, as master §A.4b states; the bad-flag source stays one reading.

<a id="e122"></a>
## E122 (1.13.2 wave C, B3 / N344; filed 2026-10-24) — `RefsIsBootSectorOurs` makes no version test, and its checksum runs to the boot sector's own length

**What was said.** The master's §G.6: `RefsIsBootSectorOurs` = "Signature + version check"; §A.1's checksum loop
"for i = 3 to 511".

**What is true.** `RefsIsBootSectorOurs` tests, in order: two global flags 0; the device's sector size > 0xFF; bytes
3..10 = `ReFS` and four zero bytes; 0x57 < u16 `+0x14` <= the sector size; the ROR1+ADD checksum over bytes
3..(`+0x14`)-1, skipping `+0x16`/`+0x17`, = u16 `+0x16`; 0x200 <= u32 `+0x20` <= 0x1000; u32 `+0x24` in
{1, 4, 8, 16, 32, 64, 128, 256, 512}; 0 < u64 `+0x18` <= the device's sector count; the device's physical sector size
<= `+0x24` x the sector size. No version test: the version is tested in `RefsMountVolume` (one reading: major 3 and
minor <= 0xE on 26100.9444, minor <= 4 on 17134). On the corpus `+0x14` = 0x200, so the checksum covers 3..511 there.
Also read twice: `RefsReadBootSector` reads the backup copy only when the sector-0 read fails with an I/O error, and
`RefsWriteBootSector` writes the backup before sector 0.

**Scope.** The test list read twice on 17134, 26100.9444 and Insider 29574 (register FS_VBR_SA_013 and the "bounds"
reading `analysis/reports/v1.13.2/fixes/WAVEC_READING_bounds.md` V4), once on 26100.8115 (C2 review 1; the other
26100.x bodies identical to .9444 by the bounds reading); the backup read and the write order twice
(FS_VBR_RA_013 / FS_VBR_RA_014 and the bounds reading K1, K4). Corpus: 117 of 117 primaries pass the image-checkable
tests. Tool (1.13.2): `boot_sector_failures`. Per-build table: `driver_register.md` "Behaviour by build".

<a id="e123"></a>
## E123 (1.13.2 wave C's close, N461; filed 2026-10-24) — redo opcodes 0x12 and 0x15 call no handler in `PerformRedo`; 0x12 is a tree-update record

**What was said.** The master's §E.3 and `forclaude/intelligence/redo_opcode_complete.md`: 0x12, 0x14 and 0x15 all
dispatch to `RedoMoveContainer` ("shared 0x12/0x14/0x15", citing `LAB_14012eebf` / `LAB_1c00e86c4`); "every value in
range dispatches to a handler except v3.14 0x17"; v3.4 "29 values, all handled". The tool names 0x12 and 0x15
`RedoMoveContainer` and `mlog --parse` classes 0x12-0x15 as container-table changes (fixed at wave C's close, N461).

**What is true.** In `CmsLogRedoQueue::PerformRedo` the branches of 0x12 and 0x15 jump to the function's common
epilogue (the table recorded, the key copied, return) without calling any handler; the labels the old reading cited ARE
that epilogue. Only 0x14 calls `RedoMoveContainer` (0x13 `RedoAddContainer`). `CmsRestarter::PreAnalyzeOneRecord`, the
analysis pass, acts on 0x12 only: a counter, the ETW event `TreeUpdateRecordFound`, a 16-byte value and
`StoreObjectTableLSN` -- 0x12 is a tree-update record carrying the object table's LSN, not a container move. On 26100.x
0x17 and any value above 0x2B return 0xC0000427; on 17134 0x17 calls `RedoGenerateChecksum` and a value above 0x1C, like
0x12 and 0x15, reaches the epilogue (17134 has no unknown-opcode error). Insider 29574 accepts 0x2C the same way (to the
epilogue, no handler) where 26100.x returns the error, and replays 0x22 inline (`UpdateSetSummary`) where 26100.x calls
`RedoTableSetSummaryUpdate`. The five 26100.x `PerformRedo` bodies are identical apart from generated names.

**Scope.** Read twice on 17134, 26100.8115 and Insider 29574: the lead (RUNNING_LOG N461) and an independent second
reading (`analysis/reports/v1.13.2/fixes/N461_SECOND_READING.md`), each from the decompilations (17134 :216426-216457,
:216482; 26100.8115 :252413-252422, :252571, :252589, :252614; Insider :318934, :319087-319110, :319135); the 26100.x
identity twice (normalised body comparisons). On disk (2026-10-24, dev tool ed5c4082 `mlog --csv`, 17 volumes of
3.4, 3.7, 3.9, 3.10 and 3.14; `analysis/reports/v1.13.2/fixes/WAVEC_CLOSE.md` section 7): 547 of 210,085 transactions
carry 0x12, on every format (3.4: 10, 3.7: 9, 3.9: 3, 3.10: 17, 3.14: 508), 540 of them nothing else; none carries
0x15, and no record carries an opcode outside the tables (0x2C included). Every CONTAINER transaction the tool printed
there (544) was one of them; after the fix (dacec9f8) none is CONTAINER and the 540 that hold only 0x12 are TREE_UPDATE.


<a id="e124"></a>
## E124 (1.13.2 wave D's close, C3-1 / N475-N477; filed 2026-10-27) — a page with another signature at +0x0C is an earlier volume's only at the address it names, in its own units; the LCN slots list one cluster on a 64 KiB page

**What was said.** The master's §A.2 row 0x0C: a page that carries another signature "was written for another volume
and left on the disk (`labJjournal` 17 pages, `step5/testatomic` 28): its rows are not this volume's". Rows 0x28, 0x30,
0x38: "MSB+ only: second (third, fourth) cluster (self+1, +2, +3)".

**What is true.** (1) Every page a volume writes carries the signature of that volume's GUID at +0x0C: refs.sys computes
it from the superblock's GUID (+0x50) when it reads the superblock and never creates or changes a GUID (read twice, four
builds). (2) A cluster that begins with `MSB+` and carries another value there is an earlier volume's page left in
place when its LCN tuple (+0x20..+0x3F), read in the page's OWN units, names the place where it lies: directly for the
Container Table, its copy and the Small Allocator (tables 0xB, 0xC, 0x22: roots 7, 8 and 12, addressed by physical
LCN), through the current volume's container table for every other table. That is the rule the tool applies; it does
not show the converse: an earlier volume whose containers lay where the current volume's table does not map them would
not be found by it. On the corpus every other such cluster (933) was one of these: the Data Deduplication index's own
content, stored as `MSB+` pages with a value of its own at +0x0C (`DedupIndex.db`: 0x7a535754 on
win11refs8gtestcompression, 0xb32a0746 on win11refs8gdedup; 908), bytes in never-written runs of live files on
win11refs8gdedup (24), and a text file that begins with `MSB+` (1). (3) The tuple lists the clusters the page fills, consecutive: four LCNs for a 16 KiB page
of four 4 KiB clusters; ONE LCN for a 64 KiB page (one 64 KiB cluster), the other three slots zero. An earlier volume's
units can differ from the current one's: on win11refs15t64k (64 KiB clusters) an earlier volume of 4 KiB clusters left
16 KiB pages that begin 16, 32 or 48 KiB into a 64 KiB cluster (450 of its 634).

**Scope.** Disk, through the tool's own code (`analysis/reports/v1.13.2/fixes/D3_evidence/`): every page with the
volume's own signature lies at its address so read, 9,693 of 9,693 on nine volumes (3.4 and 3.14, 4 and 64 KiB
clusters; `c3_ownpages.txt`), and so does every orphan page with it that the deleted-file scans read on 141 volumes
(`WAVED_CLOSE_evidence/n474_census.jsonl`); the other-signature census over the same 141 volumes (`c3_census3_*`):
3,547 pages of 9 signatures at their own address on 36 images of 7 disks (one disk formatted again with a new GUID:
win11refs2gtargeted_reformated's pages carry the signature of its before image's GUID, labJjournal's that of labJefs),
933 others, all a file's content; the tables addressed physically (`c3_tables.txt`). Static (the GUID): the lead and an
independent second reading on 17134, 26100.8115, 26100.9549 and Insider 29574 (`fixes/D3_DEEP_ANALYSIS.md` section 1,
`fixes/WAVED_CLOSE_evidence/second_reading/`).

<a id="e125"></a>
## E125 (1.13.2 wave E, E1a / N156; filed 2026-11-04 at wave E's close) — `$SI+0x24` bit 0x02 marks a case-sensitive directory, not dedup / CoW

**What was said.** Register MD_SI_RA_006: "bit1=DEDUP/COW(FCB bit22)". The master §C.7 row 0x24: "1=DEDUP/COW(FCB bit
22)", and the type-0x10 row 0x4C: "0x02 Dedup/CoW".

**What is true.** `RefsComputeStandardInformationInternalFromFcb` stores FCB+0x08 bit 22 (0x400000) as `$SI+0x24` bit
0x02. `RefsSetCaseSensitiveInfo` sets that FCB bit, `RefsQueryCaseSensitiveInfo` reads it, and `RefsUpdateFcbInfoFromDisk`
reads it back from `$SI+0x24` on open: the bit is the directory's case sensitivity (`fsutil file setcasesensitiveinfo`),
as MD_CS_RA_001 and §L already state from the disk. No build read uses the bit for dedup or block cloning. 17134 has
no case-sensitive directories and reads only bit 0x01 of the field.

**Scope.** Static, read twice: 26100.9444 (`RefsComputeStandardInformationInternalFromFcb` :157017-157019,
`RefsSetCaseSensitiveInfo` :404549, `RefsQueryCaseSensitiveInfo` :403134-403138, `RefsUpdateFcbInfoFromDisk`
:470855-470860) and 26100.8115 (:157907, the same functions); 17134 read. Disk: MD_CS_RA_001 / MD_CS_RA_003 (0x02 on
the 12 flagged directories of the corpus, 0 on every other directory). Evidence: `analysis/reports/v1.13.2/fixes/
E1a_NOTES.md` section 1; RUNNING_LOG N156.

<a id="e126"></a>
## E126 (1.13.2 wave E, E1a / N221, N234; filed 2026-11-04 at wave E's close) — checkpoint flags 0x010, 0x020, 0x040 and 0x100 are four separate features; only 0x010 is dedup

**What was said.** Register FS_CHKP_RA_001: "bits 0x010+0x020+0x100=dedup-specific". The master §A.4a: "4,5,8 | 0x0130
| Deduplication-related flags"; 0x040 not listed.

**What is true.** Each bit is set or tested on the `SmsCheckpointRecord`'s +0x78 by its own function: **0x010** dedup
enabled (`MsEnableDedup` sets it, `MsIsDedupEnabled` tests it); **0x020** weak references enabled
(`MsIsWeakReferenceEnabled`); **0x040** developer volume (`MsSetDeveloperVolume`); **0x100** dirty-state tracking
enabled (`MsEnableDirtyStateTracking` sets it, `MsIsDirtyStateTrackingEnabled` tests it). The composite 0x7b2 seen on
the dedup volumes is 0x682 with 0x010, 0x020 and 0x100 set: dedup with weak references and dirty-state tracking, three
features the dedup volumes carry, not three dedup bits.

**Scope.** Static, read twice: 26100.8115 (N221: `MsEnableDedup` :196098, `MsEnableDirtyStateTracking` :196116,
`MsIsDedupEnabled` :196752, `MsIsDirtyStateTrackingEnabled` :196788, `MsIsWeakReferenceEnabled` :197052,
`MsSetDeveloperVolume` :198051) and 26100.9444 (:195441, :195459, :196095, :196131, :196395, :197394; `this+0x6C8` is
the checkpoint record, page signature CHKP). Disk: the composites as measured before (FS_CHKP_RA_001); 0x040 was not
measured across the corpus. Evidence: `analysis/reports/v1.13.2/fixes/E1a_NOTES.md` section 5.

<a id="e127"></a>
## E127 (1.13.2 wave E, E1c / B14, N154 (a), N187; filed 2026-11-04 at wave E's close) — `refsutil fixboot` rewrites the volume flags (0x66 -> 0x04) and writes a valid boot-sector checksum; a container size of 0 is replaced by the driver

**What was said.** The master §A.1 ("Warning"): `refsutil fixboot` "zeroes the container size, volume serial, checksum
algorithm selector, Extended GUID, and volume flags fields". Register FS_VBR_RA_005: fixboot "zeroes VBR fields
0x2A-0x57 ... preserves only geometry"; FS_VBR_RA_006: container size 0 "preventing virtual-to-physical address
translation".

**What is true.** (1) On the one witness pair (step3b `win11refs2tmillionsofactions_aftersalvage` -> step3c
`..._aftersalvage_fixboottest`) fixboot sets the checksum selector 2 -> 0, the serial, the container size and the
Extended GUID to 0, and the volume flags **0x66 -> 0x04** (not 0); the boot-sector checksum it writes is valid. (2) The
driver does not leave a container size of 0 in use: when +0x40 is 0, `RefsMountVolume` stores the 64 MiB default, and a
writable mount writes the boot sector back with it (17134, 26100.8115, 26100.9444, 26100.9549; read twice; master §A.1
row 0x40).
(3) The flags fixboot leaves lack 0x20, the driver's hard-link switch (E128), and 0x40.

**Scope.** Disk: the witness pair, read by the D14 critic (N187, N154 (a)) and again in E1c (B14). Static (2): A15 /
N365, `driver_register.md` "Behaviour by build" (Boot sector +0x40 = 0). What the driver does with the selector when
0x40 is clear was read once (E1a N154 (b)) and is not stated here. Evidence: `analysis/reports/v1.13.2/fixes/E1c_NOTES.md`
(B14).

<a id="e128"></a>
## E128 (1.13.2 wave E, the first cycle's review RE1-11; filed 2026-11-04 at wave E's close) — boot-sector flags bit 0x20 is the hard-link support switch, not a "Win11 format" marker

**What was said.** The master §A.1c: "5 | 0x20 | Win11 format | v3.7".

**What is true.** `InitializeVcbFromBootSector` sets VCB+0x2ACC = 0x38 | ((+0x2C >> 5) & 1), and
`RefsHardlinksSupported` returns VCB+0x2ACC == 0x39 (VCB+0x2ACC has no other writer): the volume supports hard links
exactly when +0x2C bit 0x20 is set. 17134 has no VCB+0x2ACC (no such switch). On the corpus the bit is set on every
volume natively formatted at 3.7 or later but one, and clear on 3.4 volumes and on the volumes upgraded from 3.4. The
one is `win11refs2tmillionsofactions_aftersalvage_fixboottest`: `refsutil fixboot` rewrote its boot sector to flags 0x04 (E127), so it lacks the bit (scope
corrected 2026-11-07: the census lists it; the first wording left it out).

**Scope.** Static: 26100.9444 read twice (the review of wave E's first cycle and the lead: :486271, :123693), 26100.8115 once (:487472,
:124753); 17134 read. Disk: 115 volumes (`analysis/reports/v1.13.2/fixes/REVIEW_WAVEE1.md` section 6,
`vbr_fields_census.txt`). Evidence: KNOWLEDGE_INTAKE A115.

<a id="e129"></a>
## E129 (1.14.0, the conformance batch CB-9; filed 2026-11-05) — OID 0x500 / 0x501 and 0x540 / 0x541 are failover pairs: neither copy is a "primary" or a "duplicate"

**What was said.** The master F.4: "0x500 | Volume Info (primary)", "0x501 | Volume Info (duplicate)", "0x540 | Reparse
Index (primary)", "0x541 | Reparse Index (duplicate)"; the register `FS_OTBL_RA_004` ("OID 0x501 = Volume Information Table
(failover/duplicate)") and `FS_OTBL_RA_005` ("0x540/0x541 = Reparse Point Index (primary/failover)"); the tools'
labels `VolumeInfo(pri)` / `VolumeInfo(dup)`, `ReparseIdx(pri)` / `ReparseIdx(dup)`.

**What is true.** Each is one table held as a failover pair, as the Upcase {0x8, 0x7} and Logfile Information {0xA, 0x9}
tables are (E121): `InitializeVolumeInfoTable` passes {0x500, 0x501} and `InitializeReparseIndexTable` {0x540, 0x541}
to `MsCreateDurableFailoverTableObject`, which looks up both object records. Which copy the driver reads first was not
read for these two pairs; nothing makes 0x500 or 0x540 a primary. On the 117 ReFS volumes of the corpus the two copies
of each of the four pairs hold the same rows.

**Scope.** Static: 26100.8115 :484750-484755, :488256-488275 (the lead, 2026-11-05) and the registers' own readings of
the same creation (`FS_OTBL_RA_004`, `_005`): read twice. Disk: 117/117
(`analysis/reports/v1.13.2/fixes/CB_evidence/pairs_census.jsonl`). Evidence: KNOWLEDGE_INTAKE A123.

<a id="e130"></a>
## E130 (1.14.0, the conformance batch, open question Q33; filed 2026-11-05) — the word at value+0x80 of the OID 0x520 children is the object's file id, not a "degenerate flag"

**What was said.** The master F.4c: "Degenerate flag (val+0x80)" with the values 0x0400 / 0x0200 / 0x0100 for the
Reparse Index, the Security Descriptor Stream and the Volume Direct IO File; the tools named those three whole-word
values DASD / Security / Reparse and the `summary` JSON called the word `Flags`.

**What is true.** value+0x80 of these rows is `$SI+0x58`, the object's file id within OID 0x520 (8 bytes). 17134 opens
the three objects by the file references {0x100, 0x520}, {0x200, 0x520}, {0x400, 0x520} (`OpenFileSystemFile`);
26100.8115's `CreateDownlevelDegenerateMetadataObjects` passes the same value to `RefsCreateFileId2` as the file id
and stores it at +0x58 of the `$SI` it writes. The Change Journal's 0x501 is the same field. On the 48 corpus volumes
with children of OID 0x520 (72 rows; v3.4, 3.7, 3.14), each word equals the file id of the directory's type-0x20 row.

**Scope.** Static: 17134 (refs_win10 :240389-240391, :240689-240692, :268548-268551) and 26100.8115 (:426831-426916):
read on two builds. Disk: 48/48 (`analysis/reports/v1.13.2/fixes/CB_evidence/q33_census.jsonl`). Evidence:
KNOWLEDGE_INTAKE A122.

<a id="e131"></a>
## E131 (1.14.0, the conformance batch, open question Q3; filed 2026-11-05) — `RefsLinkFileToSelf` adds no name: the IsMoved rule has no "keep-alive link" exception

**What was said.** The master §C.13 ("How a name came where it is"): "One exception is open, read once: the driver's
internal keep-alive link of a POSIX delete is added with no record"; KNOWLEDGE_INTAKE A99: `RefsLinkFileToSelf` "adds the
driver's internal keep-alive link (`RefsKeepAliveLinkName`, POSIX-delete bookkeeping)".

**What is true.** `RefsLinkFileToSelf` changes how a file's record is held, not its names. Read (both readings): it
deletes and re-inserts the file's type-0x20 row (key 0x80000020, 0, file id) with a 24-byte value of type 2 -- that the
row thereby changes from a name mapping to a self-reference is inferred from the same function writing type 0 when called
with a name key; it re-parents the file's own table to the unnamed key {0x80000040, 0, file reference} -- that it stays in
the same directory table is inferred; and it writes the name the record sat under (`RefsBuildFileNameFromNonLinkedFile`:
that key's name, the parent's reference) as a 0x30 index entry of key type 2 in the directory, plus a 0x80000039
back-pointer in the file's table. The file id, the directory and the name's characters do not change (read). No
change-journal reason is posted on its direct-call paths (a script to depth 14 on both builds; minstore vtable calls
not followed); the closing commit can still write reasons a caller posted earlier. `RefsKeepAliveLinkName` ("KA", read from the data section)
names only in-memory link control blocks (`RefsCreateLcb` writes no table; that "KA" never reaches a persistent table is inferred -- not every later reader of
the link block was traced). Its callers are `RefsPosixDeleteLink`,
`RefsRemoveSupersededTarget`, `RefsSetLinkInfo` (a hard link) and `RefsSetRenameInfo` (a rename to another directory):
it is the record-placement flip (embedded to split, E87) that a hard link or a move causes. Removing a file's last name
posts FILE_DELETE | CLOSE (0x80000200), as the master states.

**Scope.** Static: 26100.8115 and 26100.9711, read twice (the lead on 9711; an unprimed second reading on both builds,
`analysis/reports/v1.13.2/fixes/CB_evidence/Q3_SECOND_READING.md`; the bodies are identical); 17134 has no
`RefsLinkFileToSelf` and no `RefsKeepAliveLinkName`. Evidence: KNOWLEDGE_INTAKE A126.

<a id="e132"></a>
## E132 (1.14.0, the conformance batch CB-2; filed 2026-11-05) — a superblock copy's header clocks +0x10 / +0x18 are those of the moment the driver wrote that copy, not "0 (immutable)"

**What was said.** The master §A.2: "0x10 | Virtual allocator clock | 0 for SUPB (immutable); increments for CHKP/MSB+".

**What is true.** `CmsVolume::FormatSuperPageHeader`, which builds the header of every superblock copy the driver
writes, stores `GetCurrentCheckpointVirtualClock` at +0x10 and `GetCurrentTreeUpdateVirtualClock` at +0x18 (and the LCN
at +0x20); the driver rewrites superblock copies (the rewrite of the other slots from the chosen copy after the choice;
`Extend` -> `MoveSuperBlock` writes the backups), so two copies can carry different clocks while they agree on the
volume, and a copy written at format and never since carries 0. The tool's comparison of the copies now leaves the two
clocks out with the copy's own LCN and self-descriptor.

**Scope.** Static: 26100.8115 :152303-152330 (WAVEC_READING_bootstrap S10) and 26100.9711 :151245-151281 (the lead,
2026-11-05): read twice. Evidence: KNOWLEDGE_INTAKE A127; `analysis/reports/v1.13.2/fixes/CB_NOTES.md` G1 (CB-2).

<a id="e133"></a>
## E133 (1.14.0, the conformance batch, Q2; filed 2026-11-05) — a hard-linked file's names diverge on Changed routinely: the per-name cross-check is a Created test

**What was said.** E59 and the master (§C.3, the per-name MACB note; §J): comparing MACB across a file's names "localises
a per-name timestomp". E112 and the pages that took its wording: "Divergence between a file's names is evidence.
Nothing routine produces it."

**What is true.** Of a split record's names, the **Changed** time (value+0x20) diverges routinely -- between the names,
and from the backing's (type-0x40 value+0x38) -- with no `SetFileTime`: what E112's two layers predict, a name's entry
refreshed at its own moments (a new link's entry when the link is made: the example below). Measured over the corpus (121 images, 117 ReFS volumes; 109,688 split files, 226,624 names): 210,304
names carry the backing's Changed, 14,660 an earlier one, 1,660 a later one (all but 4 on `winsider` / `winsiderv2`);
12,170 files have a name whose Changed differs from the backing's or another name's. On the 36 volumes whose change
journal was read, **156 of those files are held by the journal from their FILE_CREATE record and carry no
BASIC_INFO_CHANGE record** (bit 0x8000 in no record of the file) -- the divergence happened with no basic-information
change (e.g. `win11refs2gtargeted` 0x600:0x3, held from its FILE_CREATE: three hard links added 65 and 76 ms apart, each new
name's Changed equal to its own HARD_LINK_CHANGE record's timestamp, the original name's and the backing's equal to the
last one's; `usn --csv` of the image). The **Created** time does not show a routine case: of the 31 files on those 36
volumes whose names disagree on Created, 20 carry a BASIC_INFO_CHANGE record and the other 11 have no record left; none
is held from its creation without one. So the per-name cross-check (`timestomp`'s `HARDLINK_MACB_MISMATCH`, which tests
Created only) stands; a Changed-only divergence is not a sign of a stomp. Modified and Accessed were not classified
against the journal (names earlier than the backing's: 387 / 357; later: 50 / 53).

**Scope.** Disk, measured once (`analysis/reports/v1.13.2/fixes/CB_evidence/q2_census.py`, its three passes'
`.jsonl`); the journal test is the surviving journal's (a record lost before the lowest surviving USN is not seen, which
is why only the files held from FILE_CREATE carry the claim). Not a driver reading. Evidence: KNOWLEDGE_INTAKE A129.
Corrects the wording of E59 and E112 (the divergence rule), master §C.3 and §J.

<a id="e134"></a>
## E134 (1.14.0, the labs-and-driver batch, open question Q40; filed 2026-11-06) — `VersionCheck` compares with the volume's version from the boot sector, and its field is at +0x894 / +0x895 on Insider

**What was said.** Master §A.4: V3's version clause and the after-choice test compare with `CmsVolume+0x844 / +0x845`
"(26100.x, Insider)", "whose source was not read: the volume's version or the driver's own"; the after-choice sentence
called it "the driver-held version".

**What is true.** `CmsVolume::VersionCheck(v)` returns whether (major << 8 | minor) of two bytes of the CmsVolume is at
least `v`: +0x844 / +0x845 on 26100.8115 and 26100.9711, **+0x894 / +0x895 on Insider 29574**. The CmsVolume
constructor stores its 8th and 9th arguments there; MsInitializeVolume passes them on from its own stack arguments, and
RefsMountVolume pushes **bytes +0x28 and +0x29 of the boot sector it read for the mount** (26100.x: the pool buffer
`RefsReadWriteBootSector` fills and `RefsIsBootSectorOurs` tests; Insider: `_VCB::ReadBootSectorForMount`'s buffer,
VCB+0x3400). So the operand is the volume's version as its boot sector records it: V3's clause (`VersionCheck(0x30b)`)
rejects a record with the indirect offset table on a volume whose boot sector records a version below 3.11, and after
the choice a record whose (+0x50, +0x52) is above the boot sector's version fails the mount (0xC000014F).

**Scope.** Static: read at instruction level in the three builds (26100.9711 RefsMountVolume 14028d8d6-14028d939 and
MsInitializeVolume 1400ed81e-1400ed867; 26100.8115 14028dd5d-14028ddc8 and 1400edbc2-1400edc0b, the constructor's stores
at 1400f3ff4 / 1400f4136 / 1400f4160; Insider 1403230aa-1403234c3, the constructor's at 140119b84 / 140119d44 /
140119d7a); `VersionCheck` decompiled in the three. 17134's field (`this+0x6bc`) was not traced. Which boot-sector copy
RefsMountVolume reads when the primary is damaged was not read (the tool makes the version tests only with the primary,
`_chkp_volume_version`). Evidence: KNOWLEDGE_INTAKE A131, `analysis/reports/v1.13.2/LD/LD_NOTES.md`. Corrects master §A.4.

<a id="e135"></a>
## E135 (1.14.0, the labs-and-driver batch; filed 2026-11-06) — the Container Table's two copies differ in bits 0x2000 and 0x4000 of the row flags, not in bit 0x4000 alone

**What was said.** Master §A.3 (written 2026-11-06 after the conformance batch's review): on the 6 volumes whose two
copies differ, they differ in the row's u32 +0x14, "bit 0x4000", win10to11refs4g and `_afterwin11mount` "55 of 63 rows
(0x4001 in root 7, 0x1 in root 8)".

**What is true.** Recounted row by row: on win10to11refs4g and `_afterwin11mount`, 46 of the 55 rows differ in bit
0x2000 (0x2000 / 0 on 45, 0x2040 / 0x40 on 1) and 9 in bit 0x4000 (0x4001 / 0x1 on 8, 0x4200 / 0x200 on 1); on the
four millionsofactions volumes, 1 row in bit 0x4000 (container 0xce3). Every differing bit is set in root 7 and clear in
root 8; nothing else differs. The earlier figure generalised the census's three example rows.

**Scope.** Disk, the 6 volumes (`analysis/reports/v1.13.2/LD/evidence/ct_copy_flag_bits.txt`; the other 111 ReFS
volumes hold equal copies, `fixes/CB_evidence/ct_rows_census_v2.jsonl`). The meaning of 0x2000 is read once (§B.1a,
INFERRED). Evidence: KNOWLEDGE_INTAKE A132. Corrects master §A.3.

<a id="e136"></a>
## E136 (1.14.0, the labs-and-driver batch, open question Q38; filed 2026-11-06) — the boot sector's checksum selector +0x2A is read only when its flags +0x2C carry 0x40

**What was said.** Master §A.1d: the checksum algorithm at +0x2A is "Critical: invalid value prevents mount"; §A.1's
validation list: "checksum algorithm selector (0x2A): validated (invalid value prevents mount)".

**What is true.** `InitializeVcbFromBootSector` sets the volume's checksum selector, VCB+0x31C, to the byte at +0x2A
only when the flags +0x2C carry 0x40, and to 2 (CRC64) otherwise; 17134 does not read +0x2A. On a volume whose flags
lack 0x40 (3.4, 3.7, 3.9, a volume upgraded from them, a boot sector rewritten by `refsutil fixboot`), +0x2A is not
read, whatever it holds. The selector becomes CmsVolume+0x58 (RefsMountVolume -> MsInitializeVolume -> the CmsVolume
constructor; E134's reading), the type `CmsVolume::Start` builds the volume's checksum objects from: 1 is refused as the metadata type
(0xC00000F1) and fails `Start` there -- that the mount then fails is inferred (Start's error path, not the mount's
handling of it, was read) --, and 3 or a value above 5 is given the record of type 0, so the volume gets the
no-checksum objects (`BasicChecksumInfoForType`, KNOWLEDGE_INTAKE A130).

**Scope.** Static: 26100.8115 (:487474-487476), 26100.9444 (:486273-486275) and Insider 29574 (:531290) decompiled
(the first reading, KNOWLEDGE_INTAKE A105); 26100.9711 decompiled (:487211-487214) and at instruction level
(1402e8b19 `mov $0x2,%cl`; 1402e8b65-1402e8b6d `test $0x40,%al` on +0x2c, `mov 0x2a(%r8),%cl`; 1402e8b83 `mov
%ax,0x31c(%r9)`). The disk half -- the checksum type the pages carry on volumes whose flags lack 0x40 -- is a census not
yet run (open question Q38; run since: E138). Evidence: KNOWLEDGE_INTAKE A133, `analysis/reports/v1.13.2/LD/LD_NOTES.md`. Corrects master
§A.1d and §A.1's validation list.

<a id="e137"></a>
## E137 (1.14.0, the labs-and-driver batch, the claims audit's survivor probe; filed 2026-11-06) — Container Table row `+0x28` is not decoded: it is not "free clusters"

**What was said.** Master §B.1, row `+0x28`: "Free clusters (count)".

**What is true.** No driver reading names `+0x28`. E120 corrected `+0x20` from "free" to **allocated** clusters; `+0x28`
kept the "free" label, which no evidence supports. Measured (the docs page `structures/container_table.md`, row
`+0x28`, from the walk of all 797,837 rows of 113 volumes, `analysis/reports/RC3_1.13.0/CORRECTIONS.md`): on the 12
v3.4 volumes it agrees with `+0x20` on 35,391 rows and differs on 68, and summed over them `+0x20` = 5,515,590 and
`+0x28` = 5,227,204. Its width is not decided either: the high dword `+0x2C` is 0 on 797,774 rows and 0xFFFFFFFF on the
63 rows of `win1121h2test` (v3.7), where `+0x28` holds an all-ones u64 -- so the master's "the high dword is 0 on
759,605 / 759,605 rows, a u32" (2026-06-18) and the docs' "always 0, so this is a u32" do not hold.

**Scope.** Found by the claims audit's survivor probe (`analysis/reports/v1.13.2/LD/claims_audit/c3_survivors.tsv`:
the master and the docs page disagreed), then re-read from the evidence. Corrects master §B.1 and the docs page's row.

<a id="e138"></a>
## E138 (1.14.0, the labs-and-driver batch, open question Q38's disk half; filed 2026-11-06) — a boot-sector checksum selector of 0 is not a volume without metadata checksums

**What was said.** Master §A.1b: selector 0x0000 = "None", metadata verification "Disabled (CmsChecksumNone stub)";
0x0002 = CRC64 "Enabled from v3.10+". The docs (`structures/vbr.md`, `concepts/version_detection.md`) and the tool
(`summary`, `fastsummary`, `integrity`: "Checksum: none") named the volume's checksum from +0x2A alone.

**What is true.** On every corpus volume whose +0x2A is 0 -- the 12 formatted at 3.4, 3.7 or 3.9, the 3 upgraded from them to 3.14 (two from 3.4, one from
3.9) and the one 3.14 volume whose boot sector `refsutil fixboot` rewrote -- the flags +0x2C lack 0x40, so refs.sys does not read +0x2A (E136) and uses CRC64, and all 13 root
references of the checkpoint copy in use declare checksum type 2 (CRC64). No corpus volume has a root reference of type
0. The page-reference size follows the format era, not the selector: 0x68 on the 12 volumes formatted at 3.4, 3.7 or
3.9, 0x30 on those 4 3.14 volumes and on the CRC64 volumes formatted at 3.10 or later, 0x48 on the 4 SHA-256 volumes.
+0x2A = 2 or 4 occurs only with 0x40 set (the volumes formatted at 3.10 or later).

**Scope.** Disk, measured once over the 117 ReFS corpus volumes (`analysis/reports/v1.13.2/LD/evidence/q38_census.py`,
`q38_census.jsonl`, `q38_census_summary.txt`); the driver half is E136. Whether any build writes metadata without a
checksum on some volume is not shown (no such volume is held). Evidence: KNOWLEDGE_INTAKE A135. Corrects master §A.1b,
the docs pages named, and the tool's checksum-type line (fixed in 1.14.0: the type refs.sys uses, and a note when +0x2A
is not read).

<a id="e139"></a>
## E139 (1.14.0, the labs-and-driver batch, the claims audit's table comparison; filed 2026-11-06) — Container Table row +0x50 is k units of 16 bytes before the ranges, and +0x98 is the first range's u64 length

**What was said.** Master §B.1: `+0x50` "Integrity checksum buffer, 64 bytes, 4 x 16-byte slots, CONFIRMED"; `+0x98`
"CPC trailing copy, u32, Redundant, CONFIRMED".

**What is true.** The value is laid out as the driver reads it (`CreateContainerForCache`, `PinContainerRange`;
N216, read twice: 17134 and 26100.9444): after +0x4C (the range count), k units of 16 bytes (k fixed per volume: 4 on
160-byte rows, 8 on 224-byte rows), then the ranges, each {u64 start, u64 length}. So with k = 4, +0x50..+0x8F are the
four units -- their content is not decoded; no evidence named them an integrity checksum buffer -- and +0x90 / +0x98
are range 0's start and **u64** length. The master's own +0x4C row already stated that layout.

**Scope.** Found by the claims audit's table comparison (`analysis/reports/v1.13.2/LD/claims_audit/c3_tables.tsv`:
master and docs disagreed); the driver reading is N216's (KNOWLEDGE_INTAKE A66 and the wave C reading). The docs page
holds the corpus measurement of the length (to be re-derived). Corrects master §B.1.

<a id="e140"></a>
## E140 (1.14.0, the labs-and-driver batch, open question Q6; filed 2026-11-06) — the 104-byte page reference is the checkpoint's root reference on 3.4-3.9, written at a fixed size; the root list decodes at that stride

**What was said.** Master §D.1's size table, v3.4 row: what the 104-byte form describes "is an open question; the CHKP
root list at +0x94 was tested at this stride and did not decode". Master §A.4's +0x94 row and "Direct vs indirect root
access": without flag 0x0200, "13 page references stored inline at CHKP+0x94".

**What is true.** On the 12 corpus volumes formatted at 3.4 (9), 3.7 (1) and 3.9 (2), the checkpoint copy in use
declares +0x5C = 0x68, holds its 13 root offsets at +0x94 (flag 0x200 clear on all 12), and every one of the 156 root
references read there at that size is checksum type 2 with an 8-byte digest at +0x28 that verifies over its root page,
the bytes +0x30..+0x67 zero. 17134's `CmsVolume::FormatCheckpointRecord` writes +0x5C = 0x68 as a constant, spaces the
13 root offsets by it, and copies each root reference as 0x68 bytes of its in-memory `_LcnWithChecksumAndBuffer`;
roots past the 13th are copied at 0x28 + the digest length, rounded up to 8. So 104 is the size of the checkpoint's root
references as 17134 writes them, whatever the digest length; the inner B+-tree rows on those volumes are 48-byte
references (unchanged). Without flag 0x200, +0x94 holds the 13 root offsets (u32, stride 4), not the references:
17134 writes them so, the tool and the census read them so. The public PDB names no field of the structure past +0x28.

**Scope.** Disk: measured once over the 123 ReFS volumes of corpus.lst
(`analysis/reports/v1.13.2/LD/evidence/q6_census.py`, `q6_census.jsonl`). Static: 17134 only, read twice (decompiled
:58259; instructions 1c0034390 `movl $0x68,0x5c(%rdi)`, 1c00343b5, the 0x68-byte copy 1c00344c2-1c0034504); no 3.7 or
3.9 driver is held. The earlier failed test's script was not kept, so the frame it read is not known. Evidence:
KNOWLEDGE_INTAKE A138. Corrects master §D.1 and §A.4.

<a id="e141"></a>
## E141 (1.14.0, the labs-and-driver batch, found while scoping Q6; filed 2026-11-06) — 17134 checks a metadata page against its reference's checksum type: `CmsChecksumNone` is the stream table's type-0 object, and checkpoint flag 0x400 is not a verification switch

**What was said.** Master §D.3: v3.4 "CRC64 in page references written but never verified", verification class
"CmsChecksumNone (stub)", "the driver uses CHKP flags (not VBR 0x2A) as the runtime indicator"; §D.4: a "CRC64 test
(Container Table root corruption)" with the v3.4 result "CmsChecksumNone::VerifyChecksum returns TRUE -- modification
undetected"; §D.5: `CmsChecksumNone::VerifyChecksum` "explains v3.4 non-verification"; §A.4a and the flag tables:
0x0400 = "CRC64 metadata verification active". The docs (`page_references.md`, `checksum_architecture.md`,
`glossary.md`, `container_table.md`, `driver_architecture.md`, `version_detection.md`, `chkp.md`): v3.4 metadata
checksums "apparently not verified" / "never verified", "checksums are verified only when [CHKP flag 0x400] is set". The
tool's checkpoint-flag name for 0x400: "metadata-checksum (CRC64/SHA-256)".

**What is true.** On 17134, `CmsChecksum::InitializeLibrary` builds two tables. `MetadataChecksumTable` holds a CRC32C
object at [1] and a CRC64 object at [2] ([0] and [3] are null); `StreamChecksumTable` holds `CmsChecksumNone` at [0],
CRC32C at [1], CRC64 at [2]. `CmsVolume::MakePageResident` checks a page read from disk (the paging context's bit 0x2,
set by `MsConvertVboToLboPagingRead`) against its page reference: it takes `MetadataChecksumTable[reference +0x22]` and
calls its `VerifyChecksum` with the length at +0x24 and the digest at +0x28; the CRC64 object's `VerifyChecksum`
computes CRC64 over the page and compares, 0xC0000470 on a mismatch. The `CmsVolume` constructor sets the volume's
metadata type, CmsVolume+0x54, to the constant 2 (CRC64), which `CmsVolume::Start` generates the root checksums with.
`CmsChecksumNone` -- whose `VerifyChecksum` does return success -- is the stream table's type-0 object, not a metadata
verifier. The v3.4 references declare type 2 (156 of 156 root references, E140). The thesis "test" flipped byte 0x55
of the primary superblock, which no page reference covers, and its "Win10 does NOT validate metadata checksums" was the
script's expectation printed before the mount; the image held after the 17134 mount has that superblock copy back to
its original bytes, which is what 17134's superblock choice does with a copy that fails its self-checksum (skipped,
then rewritten from the chosen copy: E119). Checkpoint flag 0x400: no build was read testing or setting it; it is set on every 3.14 volume of
the corpus (106, upgraded ones included) and on none formatted at 3.4-3.10 (14).

**Scope.** Static: 17134, read twice (decompiled and instructions: `InitializeLibrary` 1c0063ae0, the table stores
1c0063b84 / 1c0063c41 and vtable slots 0x80 = 0x1c0001c20 / 0x1c0069950; `MakePageResident` 1c002afbc-1c002b024;
`VerifyChecksum` 1c0001c20, compare 1c0001c93, 0xC0000470 1c0001cda; constructor 1c003124d `movb $0x2,0x54(%rdi)`;
`Start` 1c00317c6); the paging-read flag read once (`MsConvertVboToLboPagingRead` :116568). Not read: every 17134 read
path, what 17134 does after a page's mismatch, what fsutil's "CHECKSUM_TYPE_NONE" on 17134 is taken from, and 0x400's meaning
(open question Q41). No behavioural test of a corrupted page-referenced page on 17134 is held. Disk: the checkpoint
flags over the 123 ReFS volumes of corpus.lst (`analysis/reports/v1.13.2/LD/evidence/chkp_flags_census.jsonl`).
Behaviour: `analysis/rawdisk/transcripts/testchecksum-modifdisks.txt`, `win10testchecksum.txt`. Evidence:
KNOWLEDGE_INTAKE A139, A140. Corrects master §A.4a, §D.3, §D.4, §D.5, the docs pages named and the tool's flag name
(fixed in 1.14.0).

<a id="e142"></a>
## E142 (1.14.0, the labs-and-driver batch, open question Q15; filed 2026-11-06) — `$VOLUME_INFORMATION`+0xA0 is the time of the last mount that writes, not a modification time

**What was said.** Master §F.4b, row 0x0520: "modify timestamp at +0xA0 (FILETIME)". The tools printed it as "Volume
modified" (`summary`, `fastsummary`, refsanalysis `summary`, `timestomp`).

**What is true.** `RefsMountVolume` -> `InitializeVolumeInfoTable` -> `SetAndGetVolumeTimes` reads the row, takes the
system time (+1 when it equals the stored +0xA0), keeps the old +0x90 / +0x98 / +0xA0 in the VCB, and -- unless VCB+0x18
bit 0x2000000 is set (VCB+0x04 on 17134) -- writes the new time to +0xA0 and persists the row (`RefsSetVolumeInfo`). Of the four callers of
`RefsSetVolumeInfo` in 26100.9711, only this one changes +0xA0: `SetVolumeMounted` (+0x82, +0x84),
`RefsSetClearVolumeFlag` (+0x84) and `InitializeVolumeInfoTable` (the version bytes, skipped with the same flag) read
the row and write it back (decompiled once); other writers of the row were not searched for. On LAB-L (one 3.14 volume, 26100.9711) +0xA0 moved at each of 5 read-write mounts, each followed 26-37 ms
later by that mount's first journal record (at 20:02:27 the creation of BitLocker's folders in System Volume
Information; at the four later mounts a security change of `System Volume Information\AadRecoveryPasswordDelete`),
and not at a read-only mount nor at any later write (a marker file, creates, deletes); on labL_5 and labL_6 it falls
0.16 s and 0.13 s after the logged "bringing the disk online". VCB+0x18 bit 0x2000000 is set by `InitializeDevice` when the device answers IOCTL_DISK_IS_WRITABLE (0x70024) with STATUS_MEDIA_WRITE_PROTECTED (0xC00000A2): a write-protected device (26100.8115, KNOWLEDGE_INTAKE A61; 26100.9711 :478961+118; Insider 29574 by form; on 17134 the word is VCB+0x04, set when `RefsGetDiskGeometry` returns true, which it does exactly when IOCTL 0x70024 answers 0xC00000A2, 17134 :262654) -- and, on 26100.9711 and .9818 only, a second setter: `RefsMountVolume` sets it (with VCB+0x189C = 1) when `RefsEvaluateExternalMediaPolicy` applies the external-media mount policy (9711 :427265-427267, 9818 :428899; absent from 26100.8115, .8521, .8972, .9444, .9549). So the bit says the mount writes nothing; +0xA0 is not written then, as the read-only attach of LAB-L left it unchanged (scope corrected 2026-11-07: claims audit C2, then the C4 review, two readers).

**Scope.** Static: 26100.9711 read twice (decompiled :484660; instructions 1402e4807 the clock, 1402e481e the compare,
1402e4867 `testl $0x2000000,0x18(%rsi)`, 1402e4874 `mov %rcx,0xa0(%rdi)`, 1402e488e the call to `RefsSetVolumeInfo`;
the caller chain decompiled, :484567 and :427511); the same body decompiled in 17134 (:265442), 26100.8115 (:484922),
.9444 (:483721) and Insider 29574 (:495789). Lab: LAB-L's six images, log and journal
(`analysis/reports/v1.13.2/LD/LD_NOTES.md`, "Q15"). The register's FS_VOLI_RA_001 already named the writer. Evidence:
KNOWLEDGE_INTAKE A141. Corrects master §F.4b and the tools' label and keys (fixed in 1.14.0: text "Last mount (rw)"; JSON
`VolumeLastWritableMountTime` in `summary` / `fastsummary` / refsanalysis `summary`, `VolumeLastWritableMount` in
`timestomp`, which were `VolumeModifyTime` / `VolumeModified`).

<a id="e143"></a>
## E143 (1.14.0, the labs-and-driver batch, open question Q35; filed 2026-11-06; amends E112) — a directory listing does not refresh a hard link's stale name; an open, a read and a close through that name do

**What was said.** E112: the per-name signal is perishable because "any read of a stale sibling (an antivirus scan, a
live triage, the examiner's own `dir`) refreshes its entry", and "the driver refreshes only the entry of the name that
was opened" (`RefsUpdateFileDupInfo`); FN_LINK_003 repeats the mechanism.

**What is true.** On LAB-L (one 3.14 volume, 26100.9711): after a 1-byte append through H1\h.bin, the name H2\h_link.bin
kept its earlier Modified / Changed / Accessed on disk (labL_1); two `cmd /c dir` listings of H2 alone changed nothing
(labL_2), and Windows' own listing printed the name's stale size (8,192 for an 8,193-byte file); an open of
H2\h_link.bin, a 1-byte read and a close made its times equal to H1's (labL_3). So a listing alone does not refresh a
stale name; one of the open, the read or the close does -- which one, and through which function, is not shown
(`RefsUpdateFileDupInfo`'s only direct callers are `RefsSetBasicInfo`, `RefsSetAllocationInfo` and
`RefsSetEndOfFileInfo`; the close path is `RefsCommonCleanup` -> `RefsUpdateDuplicateInfo`; open question Q35's state).
The rest of E112 stands: divergence is evidence, agreement clears nothing, and a read of the file through the stale
name (an antivirus scan, a live triage that opens files) can still destroy it.

**Scope.** Lab: LAB-L Part B, measured once, two readers for the listing case (the disk and Windows' listing output);
`analysis/reports/v1.13.2/LD/LD_NOTES.md` "The step8 readings". Evidence: KNOWLEDGE_INTAKE A143. Amends E112 and
FN_LINK_003's description; docs `concepts/hard_links.md`.

<a id="e144"></a>
## E144 (1.14.0, the labs-and-driver batch, open question Q36; filed 2026-11-07; corrects E70's explanation and scopes E70) — on a volume without hard-link support a cross-directory move moves the whole record and leaves its reference at $SI+0x60 / +0x68

**What was said.** Master §C.2 / §C.3: a resident (embedded) file is never relocated (home == parent); a
cross-directory move "forces" the split form. Master's $SI rows: +0x60 / +0x68 "ExternalFileId" = a "cross-volume file
origin ID ... populated only for cross-volume copy/move. 49/296 non-zero on typical v3.4 images" (v3.4 table); "non-zero
only on upgraded volumes (carryover) ... A same-volume cross-directory MOVE does NOT populate this --
`RefsConvertToStandardInfoExternalId` keys on an origin-VOLUME identity word, not a directory OID" (v3.14 table; E70).
The tool composed an embedded record's FileRef as (its directory : $SI+0x58), printed HomeOID "(the directory this
file was CREATED in; unchanged by move/rename)" from it, and IsMoved false.

**What is true.** `RefsConvertToStandardInfoExternalId` compares the DIRECTORY of the file's own reference (+0x100 of
the 16-byte reference at +0xF8) with the current parent's; when they differ it persists the reference at $SI+0x60 (id)
/ +0x68 (directory), else 0. On LAB-M (a 3.4 volume upgraded by 26100.9711, boot-sector flags 0x6: no hard-link
support) the two files moved X -> Y stayed EMBEDDED in Y's table with $SI+0x58 = their old id, $SI+0x60 / +0x68 = their
original FileRef (0x70b:2, 0x70b:3) -- Windows' File IDs after the move, 2 of 2; X kept a forwarding row per moved file
(type 0x20, value {u64 1, u64 new id, u64 new directory}) and the moves took Y's next ordinals (3, 4; the next file got
5). On the corpus, 409 embedded records carry $SI+0x68 on 8 volumes, all with flags lacking 0x20 (five formatted at 3.4,
`win10to11refs4g_beforewin11mount` among them; two upgraded from 3.4, the same volume after its upgrade; LAB-M), with
exactly one forwarding row each; none on a volume formatted at 3.7 or later, the fixboot volume (flags 0x04) included
(counts corrected 2026-11-07). So with
hard-link support a move splits the record (E70, measured there); without it the record moves whole and carries its
reference. The 49 per v3.4 image are moved files, not cross-volume origins. A file's identity is ($SI+0x68 : $SI+0x60)
when +0x68 is set, else (its directory : $SI+0x58).

**Scope.** Static: 26100.9711 read twice (decompiled :190252; instructions 1400e61a4-1400e61ab, 1400e61b7,
1400e61c0-1400e61c8, the call to `RefsPartialSetStandardInfo` with 0x58 / 0x18); the same body in 26100.8115 (:190640),
Insider 29574 at FCB+0x158 / +0x160 (:261660); 17134 persists the same 0x18 bytes (:173320). `RefsUpdateFcbInfoFromDisk`
loads the three into FCB+0x158 / +0x160 / +0x168 (read once). Not read: the move path's call to it on each kind of
volume. Lab: LAB-M (the image rebuilt from the BitLocker volume, every metadata page verified, the five files'
SHA-256 equal to the lab's). Disk: `analysis/reports/v1.13.2/LD/evidence/moved_records_census.jsonl`. Evidence:
KNOWLEDGE_INTAKE A145. Corrects master §C.2, §C.3 and the $SI rows (+0x60 / +0x68) of §C (v3.4 and v3.14), E70's
explanation, and the tool (fixed in 1.14.0: `embedded_record_ref` -- ObjectRef, HomeOID, FileID, IsMoved, the timeline
and remnant identities).

<a id="e145"></a>
## E145 (1.14.0, the labs-and-driver batch, open question Q34; filed 2026-11-07; corrects E64's Trash sentence; RUNNING_LOG N176) — a delete goes through the Trash only when the object's data stream set holds two or more tables, not for every non-resident file or directory

**What was said.** E64 and master §I.1: "Resident files bypass the Trash (`RefsDeleteResidentDataScbAndCommit`); only
non-resident files + directories are reparented"; `FS_DEL_RA_001`: "RefsDeleteFile -> MsDeleteRow -> MsReparentFileToTrash
-> CmsTrashTable::AddFileTable (OID 0xD queues for cleanup)" as the deletion flow of every file.

**What is true.** `DeleteFileOnDisk` and both directory delete paths -- the only three `MsReparentFileToTrash` call
sites -- reparent the object to the Trash table (OID 0x0D) only when `RefsCheckDataSetsForDeletion` finds a data stream
set with two or more tables, or a set's +0x100 set; `DeleteFileOnDisk` alone also reparents when the single-table sets'
rows sum to more than 5,000, under feature bit 0x200000 and with IrpContext+4 bit 0x1000000 clear (the directory paths
have no row condition; scope corrected 2026-11-07 after the claims audit's C4 review, which read 26100.9711 :191584-191588
and 26100.9444 :191247-191251); otherwise `RefsDeleteAllMinstoreStreams` and `RefsDeleteObject` delete it in the same transaction.
`RefsDeleteResidentDataScbAndCommit` is not on the file-delete path. LAB-L (26100.9711) deleted six objects together:
only `t_snap.bin` -- the one given a stream snapshot (`refsutil streamsnapshot /c`, whose output in LAB-L's `D_snapshot.txt` (step8/lablm.zip; sha256 78f95403...) lists "labLsnap" with stream size = snapshot size = 1,048,576 bytes) --
entered the Trash (labL_5's log record 1068, RedoReparentTable: the new parent OID 0x0D, the key {u64 2, u64 0x70b} =
its Windows File ID 0x...070b...0002, LAB-L's steps.txt D0); a 1 MiB file and a 100 B file, a file with three small named streams, one with a 256 KiB named stream and a
directory holding a file were deleted in place (RedoDeleteTable) -- the directory contradicts E64 whichever axis its "non-resident" meant (E87: the record's placement or the data's residency). The Trash held 0 rows at labL_5's imaging (after the
dismount, 1 min 46 s later): what emptied it (the cleaner or the dismount) is not read.

**Scope.** Static: 26100.9444 read twice (D14 step 2's deletion checker and its critic, N176: DC:191247-191251,
:191656-191684; the call sites :140164, :191058, :191317); 26100.8115 (refs_win11.decomp.c:191949-192019) and Insider
29574 (:167701-167767) once each; 26100.9549 byte-identical (`F12_DRIVER_9549.md`); 26100.9711 the same body (Q34). 17134
has none of these functions and reparents through `MsReparentChildTableToTrash` (DC10:175428-175437; its condition not
read). Lab: once (LAB-L Part D). Evidence: `analysis/reports/v1.13.2/LD/evidence/q34_record1068.py` / `.txt`;
KNOWLEDGE_INTAKE A146; open_questions Q34. Corrects E64's Trash sentence, master §I.1, `FS_DEL_RA_001`, and the docs
(`structures/trash_table.md`, the deletion pages D14 listed). The frozen findings register (#213) is not edited.

<a id="e146"></a>
## E146 (1.14.0, the labs-and-driver batch, open question Q8; filed 2026-11-07, corrected the same day after the claims audit's C4 review; scopes E98) — a sparse hole's VLCN mirrors its file VCN on every hole row measured, so `VLCN == 0` fires on the holes at file VCN 0

**What was said.** E98: "on the extent-node form the VLCN is non-zero and `VLCN == 0` fires on nothing"; master §C.6
(the hole paragraph: "so it is generally **non-zero** and a `VLCN == 0` test fires on nothing in the extent-node form";
the 0x180060 row: "usually **non-zero**"); the CLAUDE.md pitfall bullet. This erratum's first wording (the same day)
said the VLCN mirrors the file VCN "on most rows, not all" (165 mirror, 24 VLCN 0): wrong, below. The blind audit's
K108 (2026-09) measured the same on its own images (40 flag-0x20 records: VLCN 0 on 20, VLCN = file VCN on 20) and
asked for this rule: the flag marks the hole, and the VLCN is not 0 in general.

**What is true.** The hole is decided by flags bit 0x20 alone (E98's rule, unchanged). Its VLCN mirrors its file VCN on
every hole row measured: over the corpus (129 images; the rows the dev tool's decoders reach through `files --csv`,
`dataruns -v --json` and `snapshots --show`), 189 distinct hole-row byte patterns on 63 volumes, all extent-node rows; 24
of them are holes at file VCN 0, whose VLCN 0 IS their file VCN (`{VLCN 0, flags 0x180060, file VCN 0, run 1}`, on
winsiderv2 also run 792), the other 165 hold VLCN = file VCN != 0. So a `VLCN == 0` test catches exactly the holes that
start a file and misses every other hole -- it does not "fire on nothing" (E98), and E98's own next paragraph (holes
with both discriminators on two of its four volumes) is these. The first wording's error: its classifier tested
`VLCN == 0` before `VLCN == file VCN`, so a hole at file VCN 0 was counted as not mirroring.

**Scope.** Disk: `analysis/reports/v1.13.2/LD/evidence/q8_hole_vlcn.py` -> `q8_hole_vlcn_corpus.json` (a hook on
`_extent_is_hole` reading each hole row's raw VLCN and 24 bytes from the decoder's frame -- the decoders normalise a
hole's VLCN to 0 in what they return; one process per (image, command), every rc equal to the golden's); the unit is a
distinct 24-byte pattern per volume (identical rows of several files count once); rows are taken before the caller's
cover check. The C4 review read 23 of the 24 zero-VLCN patterns in the raw bytes (all at file VCN 0; the 24th, on
win11refs2tmillionsofactionsv2, not re-read). Not reached: remnant rows (`deleted` / the carve paths). The 1.13.0 P0.6
census could not measure this (it counted decoder output). Corrects E98's sentence, master §C.6 (both places), the
CLAUDE.md pitfall (the maintainer's file); the docs page's "mirrors its file VCN, so it is usually non-zero" holds.

<a id="e147"></a>
## E147 (1.14.0, RC1-docs; filed 2026-11-11; RUNNING_LOG N533, which corrects N218's fix) — a redo record's +0x18 and +0x20 are the volume's virtual and allocator clocks when the record was added: +0x20 is not an object id and not a table handle

**What was said.** Master §E.4 (the `_SmsRedoRecord` table): "| 0x20 | 8 | object_id (target OID) | CONFIRMED |", and no
+0x18 row; `docs/structures/mlog.md` (Layer 4: "object_id (u64) | Target OID (from `ObjectIdFromRedoHelper`)") and
`docs/concepts/transactions_crash_consistency.md` ("target OID at +0x20"). The 1.14.0 dev tool (N218's fix of 2026-10)
reads it as "the record's TABLE HANDLE" (`mlog -v` column "Handle", `--json` "TableHandle") and gives a record whose key
names no table the table of another record carrying the same value (`_mlog_handle_oid_map`).

**What is true.** `CmsTxMemLog::AddRedoRecord` (which `CmsTransactionContext::AddRedoRecord` wraps) writes +0x18 = the volume's current checkpoint virtual clock
and +0x20 = the volume's allocator clock: the two volume fields `FormatCheckpointRecord` writes as the checkpoint's +0x60
(virtual clock) and +0x68 (allocator clock). `ReadLatestCheckpoint` loads the chosen checkpoint's +0x60 / +0x68 back into
those fields; the restarter copies the allocator clock (`CmsRestarter::CmsRestarter`), and `ShouldPerformRedo`, called
by `RedoOneRecordBlock` on the first record of a redo block when that record starts a transaction (flags bit 0; a block
whose first record is 0x12 is skipped before it), queues the block for redo when that record's table key path names
OID 0x1, 0xB or 0xE only if its +0x20 is at or above the restarter's allocator clock (a signed comparison). The object
id is not at +0x20: `ObjectIdFromRedoHelper` reads it from the record's table key path (count at +0x08, offset at
+0x0C): component 0's 16-byte identifier at the component's +0x0C.
On disk the two fields behave as these clocks: over the current logs of the 124 corpus volumes read (8,515,322 redo
records in 886,813 log payloads; corpus.lst without blindaudit2.raw and labJjournal.raw; 5 images not ReFS-readable),
+0x20 <= +0x18 on every record; +0x20 is at or below the chosen checkpoint's +0x68, and +0x18 at or below its +0x60, on every
record but 33 for each field, on the same 5 volumes in the same counts (the four win11refs2tmillionsofactions images, 2
each, whose clocks there reach 980 / 985 against the checkpoint's 657 / 662; labM_after_rebuilt, 25; the two sets were
not joined record by record); +0x20 is never 0. As a table key it fails: in 550,720 of the 886,813 payloads one
+0x20 value is carried by records whose keys name different tables.

**Scope.** Static, read once (2026-11-11, the lead): the writer on 17134 (refs_win10.decomp.c:3307-3308, the volume's
+0x670 / +0x678; `FormatCheckpointRecord` :58299 / :58301 writes the same two as CHKP +0x60 / +0x68), 26100.9444
(refs.decomp.c:8055-8056 in `CmsTxMemLog::AddRedoRecord` (:7806), `GetCurrentCheckpointVirtualClock` = the volume's
+0x7f0 (:151382) and +0x7f8;
`FormatCheckpointRecord` :216644-216645; `ReadLatestCheckpoint` :216975-216976; `CmsRestarter` :249435;
`ShouldPerformRedo` :255410-255411, its one caller `RedoOneRecordBlock` :253517-253519; `ObjectIdFromRedoHelper`
:251619), 26100.9818 (the writer, :8055-8056) and Insider 29574 (winsider-refs.decomp.c:138597-138598, +0x840 / +0x848;
`FormatCheckpointRecord` :193771-193772; `ReadLatestCheckpoint` :285963-285964; `CmsRestarter` :316679;
`ShouldPerformRedo` :322208-322209); 17134's reader side too (`CmsRestarter` refs_win10.decomp.c:106958 copies +0x678;
`ShouldPerformRedo` :219209, the OID mask 0x4802 = {0x1, 0xB, 0xE}). The comparison and `PerformRedo`'s current-table
update are in every 26100 decompilation held (.8115, .8521, .8972, .9444, .9549, .9711, .9818). Read by the lead, then
checked by an adversarial review the same day (it corrected the writer's class, the per-block test and three line
numbers; no other writer of +0x18 / +0x20 in the four builds: the split fragments of `AddRedoRecord` write the same pair). Disk: the dev
tool's own MLog walk (the records `mlog --parse` reads; earlier logs left out), `analysis/reports/v1.13.2/RC1D/evidence/
measures/n533_h20.py` and `n533_h18.py` with their `.jsonl`. Corrects master §E.4, the two docs pages and the tool
(N533: the labels and the table fill); N218's reading ("a table handle") is withdrawn with it.

<a id="e148"></a>
## E148 (1.14.0, RC1-docs; filed 2026-11-12; KNOWLEDGE_INTAKE A28 / A31, RUNNING_LOG N411) — the MLog control payload has no "Total entries" at +0x48 and no "Control UUID" at +0x50: +0x44 is the host info, the log instance's UUID is at +0x28

**What was said.** The tool (`mlog`'s "Total entries" and "Control UUID" lines, JSON `TotalEntries` / `PayloadUUID`
from +0x48 / +0x50) and `docs/structures/mlog.md`'s control-payload table, until wave B part 1b. The master never
carried the two labels.

**What is true.** The control payload's +0x44 (a u64, unaligned) is the MLog library's host info:
`MlLogAdvanceLogStart` stores its fourth argument there, and only there, when it advances the log start;
`MlLogGetHostInfo` reads it back, and `CmsDurableLog::Start` hands the value to `CmsRestarter::Restart` at mount.
refs.sys passes the checkpoint virtual clock minus 1. The log start advance zeroes +0x4C .. +0xE43. The log instance's
UUID is at +0x28 (copied to the record header's +0x10). So +0x48 reads 0 and +0x50 an all-zero UUID.

**Scope.** Static: read twice (`analysis/reports/v1.13.2/DEEP_MLOG_CONTROL_STATIC.md` §1 and `DEEP_CHECK_VERDICT.md`
§7), on 17134, 26100.8115, 26100.9444 and Insider 29574 for the host info (A31). Disk: +0x48 = 0 and +0x50 all zero on
win11refsmini and win11refstestmftecmd (wave B part 1, `fixes/FIX_GB_part1.md` S1); the newest copy's +0x44 = the
highest checkpoint clock - 1 on 120 of 120 corpus control areas, the older copy's = the newest's - 1 on 120 of 120
(A31). Corrects the tool (fixed in wave B part 1b, N411) and the docs page (RC1-docs G4).

<a id="e149"></a>
## E149 (1.14.0, RC1-docs; filed 2026-11-12; the blind audit's K106 and K196; register FS_CHKP_RA_014) — the two checkpoint copies usually, not always, decode to the same 13-root list, and their bytes differ in more than the clock and checksums

**What was said.** Register FS_CHKP_RA_014 (CONFIRMED): "the two CHKP copies ALWAYS decode to identical 13-root
pointer lists"; four concept pages ("both CHKP copies always decode to the same 13-root pointer list") and "only the
virtual clock and per-page checksums differ".

**What is true.** On the images the row names (clean, corrupted, busy, pre-salvage) and on 25 of the 26 volumes of the
first blind audit the two copies' root lists are identical; on the audit's foreign ReFS 3.4 volume they differ on
roots 1, 2, 7, 8 and 12 (root 7 is 0x781c in the clock-68 copy and 0x7720 in the clock-67 copy; both lists inside
checksummed clusters). Where the trees are identical the records still differ in 11 to 15 bytes, and on 18 of 18
volumes byte-compared those include fields that are neither a clock nor a checksum: the allocator clock at +0x68 (by
exactly 1), the page's own LCN at +0x20 and the self-descriptor's LCN. A checkpoint comparison therefore usually
yields nothing on a cleanly unmounted volume, and needs a capture between two checkpoint writes that changed a root
table.

**Scope.** Disk: the blind audit's measurement (`analysis/reports/blind_audit_response_2026-09-17/instruments/
compact.md` K106, K196), reproduced (`PLAN_1.13.2` K106: MEASUREMENTS M11, 5 of 13 roots differ on the CTF volume); the
18-volume byte comparison is the register row's own. Not measured: the root lists over every corpus volume. Corrects
FS_CHKP_RA_014 (scope and wording) and the docs (RC1-docs G6: deletion_recovery, redundancy, forensic_analysis_workflow,
what_survives, carrier_categories, copy_on_write).

<a id="e150"></a>
## E150 (1.14.0, RC1-docs; filed 2026-11-12; RUNNING_LOG N233; amends E109) — a Block Refcount entry is a 13-bit count of the references beyond the first: hard links and snapshots add none, and a range is shared at a count of 1

**What was said.** Master §B.6 / §B.6a: bits 0-13 a reference count, bit 15 "shared / dedup-managed", bit 14 a "dedup
metadata" flag, "hard-link sharing: rc >= 2", the table "tracks snapshots, deduplication, clones"; register
CT_BKRC_RA_002 (the bit meanings); the docs' "refcount >= 2 = shared /
guaranteed survival"; AP_REDO_038's note that 0x28 "prepares data for" 0x29.

**What is true.** The driver: an entry is a 13-bit count (`CmsRefcountCacheEntry::Update` reads `e & 0x1FFF`); bit 15
is an LCN weak reference the dedup path sets on clusters the stream itself maps (`CreateRangeWeakReferences`), and bit
14 marks that weak reference broken by a later write or checksum rewrite (`BreakWeakReferences`, redo 0x28; 0x29 is
`DuplicateCluster`, a separate opcode); a range is shared at a count of 1 or more (`IsRangeSharedOrCompacted`);
`IncrementRefcount` has five callers (block clone, the dedup redirect, two flagged-extent paths, stream-run updates),
and neither `RefsLinkFileToSelf` nor the snapshot path calls it; when
+0x14 bit 0 is clear one u16 at +0x1C applies to the whole range (E109's 32-byte compact form). On the bytes the keys
are VLCNs and a cluster's count is the number of references beyond the first: block-clone pairs read 1 and triples 2
(2,239 of 2,257 clusters), the hard-linked file reads 0 on 24 of 24 clusters, and clusters shared with a snapshot read
0. So neither a hard link nor a snapshot shows in this table, and "refcount >= 2" is neither the sharing test nor a
survival guarantee.

**Scope.** Static: 26100.8115 (the W4 critics' reading, the functions present in six builds; the `IncrementRefcount`
call sites re-read 2026-10-01, N227); the 13-bit mask read again on 26100.9444 (refs.decomp.c:70178, :70208, the lead,
2026-11-12). The bit 14 / 15 meanings: one reading. Not settled, and not corrected here: the value's +0x10 (the 26100.8115
reading has the driver reject a row whose +0x10 low byte is not 1, while master §B.6 measured low bytes 0xE4 and 0xF0
on populated rows: one of the two reads another frame) and CT_BKRC_RA_001's name for it. Disk: one populated volume (win11refs2tsnapshots, 21 rows joined to
its runs); lab314_main_step2 and win11bidule hold empty tables. Corrects master §B.6 / §B.6a, CT_BKRC_RA_002,
AP_REDO_038's note, `docs/structures/block_refcount.md` and every page that states "refcount >= 2" as
sharing or survival (RC1-docs G7).

**Update (2026-11-21, RC3a U32; RUNNING_LOG N665).** The value's +0x10 and the compact form, measured over the 124
ReFS volumes of corpus.lst (`analysis/reports/v1.13.2/RC1D/rc3a/u/`: `u_census.py`, `u_followup.py`, `u_followup2.py`):
2,752 rows on the 47 volumes that have any, all 3.14.
- Byte +0x10 is 1 on all 2,752 rows, as the 26100.8115 reading requires; bytes +0x11 to +0x13 vary (not decoded). Master
  §B.6's "low byte varies (0xE4 / 0xF0)" read another frame.
- The u32 at +0x14 is 1 on the 2,724 long rows (2,080 bytes) and 0 on the 28 compact rows (32 bytes): the long / compact
  switch the driver tests.
- On a long row +0x18 equals the sum of the counts (`e & 0x1FFF`) on all 2,724, the largest 1,408; bit 13 is clear on
  every entry; 16 distinct non-zero entry values, the largest 0x82F6 (758). The u32 at +0x81C is 0 on 2,500 long rows
  and one of 20 values with high half 0xFFFF on 224 (9 volumes).
- The 28 compact rows (winsider 2, winsiderv2 25, win11refs4gattributestest2 1) cover 1,024 to 4,096 clusters and
  carry a u16 count of 1 or 2 at +0x1C, the count the driver applies to the whole range; the u16 at +0x1E equals it on
  26 (0xFFFF and 0 on the other two; not decoded); +0x18 is 0 on all 28.
- Bits 15 and 14: 62,233 and 181 entries, all on the three volumes whose checkpoint carries the dedup flag 0x010
  (win11refs8gdedup, win11refs8gtestcompression, win11refs8gtestcompression_afterdedup), never both on one entry;
  every bit-14 entry has a count of 0.
Corrects master §B.6 (+0x10, +0x14, +0x18, +0x81C and the counts), register CT_BKRC_RA_001 / 002 / 003, the pages
`docs/structures/block_refcount.md` and `docs/concepts/deduplication.md`.

<a id="e151"></a>
## E151 (1.14.0, RC1-docs; filed 2026-11-12; RUNNING_LOG N232, KNOWLEDGE_INTAKE A101; amends E86) — an extent node's bit-0x04 row is a slot its key index does not list, the index word is not reliably the file VCN, and +0x04 is the end of the rows

**What was said.** Master §C.4a (CONFIRMED, RD) and §C.3b: a row with flag bit 0x04 is an "aggregate/fence" or
"index/summary" row, "a coarse duplicate of the leaves it spans"; register MD_DATA_RA_015 the same. Master §C.3c (E86):
the index slot's second u16 is a "key hint, the row's file VCN truncated to 16 bits"; the node header lists +0x20 as an
8-byte "node size" with the index array at `N + node_size - 4*row_count`, and has no +0x04 field.

**What is true.** On the rows read, bit 0x04 marks a slot the node's key index does not list: 23 of 23 unindexed slots
carry it and 0 of 345 indexed rows, all 23 in slack copies (E115 calls such slots superseded); what the driver means by the bit is not read.
The index word is not reliably the VCN: 0xFFFF on 1,364 rows of three images whose own file VCN is lower (K168; the
v3.7 and v3.9 images among them), the VCN's low 16 bits on 345 of 345 rows of the four public v3.14 samples (a split
by format is not established); the row's own file VCN (+0x0C) is the one to read.
The node header's +0x10 / +0x20 are the key-index array's start and end (u32 each, `(+0x20 - +0x10) / 4 == +0x14`),
+0x24 a separate word, and +0x04 the end of the rows: every row the index array of a valid extent node names lies in
[+0x28, +0x04) on 1,169,631 node readings over 141 volumes (1,006,261 of live files, 163,370 of remnants), 0 outside.
A deleted remnant's index array can be zeros while the header and rows survive (118 node readings on 21 volumes).

**Scope.** Disk: the bit-0x04 and 345-row counts are the W4 extents critic's byte reads of the four public samples
(`analysis/reports/v1.13.2/D14/critic/extents.md` §5, a stdlib reader); the 1,364 rows are K168's; the +0x04 census once
(`analysis/reports/v1.13.2/fixes/WAVED_CLOSE_evidence/n486_census.jsonl`); +0x08 (the free bytes) seen on 30 headers,
not measured corpus-wide. Static: none for bit 0x04 (E2 pending). The exclusion of bit-0x04 rows when a file's extents
are listed is unchanged; the tool walks the key index (`_extent_leaf_rows`). Corrects master §C.3b, §C.3c and §C.4a,
register MD_DATA_RA_015, `docs/structures/extent_descriptors.md` (the index word).

<a id="e152"></a>
## E152 (1.14.0, RC1-docs; filed 2026-11-12; KNOWLEDGE_INTAKE A85 / A86, RUNNING_LOG N462 / N463) — v3.4 integrity streams carry inline CRC-32C, and most integrity files also hold runs without one

**What was said.** Master §C.6: "**v3.4** (Win10) carry **no** inline element; their `run_length==1` extents lack the
`0x1C` marker", listed with the SHA-256 and 64 KiB-cluster volumes as "non-vacuously confirmed".

**What is true.** On win10refs8gsetintegristystreams1 (ReFS 3.4) the integrity files' checksummed rows are flagged 0xD0
with row size 24 + 4 x run, and 3,929 of 3,929 CRC-carrying clusters match their CRC-32C; on win10refs2tspecials 257
files verify the same way. The 1.13.1 verifier selected the `$DATA` row by the v3.14 key only and read no v3.4
integrity file (N462), which is how a v3.4 volume looked as if it carried none. Beside the checksummed rows, most
integrity files hold runs whose rows (flags 0x40, row size 24) carry no CRC slot: 204 of 209 integrity files on
win11refs2g_setintegritystreams1 (69,960 clusters), 214 of 259 on win10refs8gsetintegristystreams1 (25,338); typically
the first cluster is checksummed and the rest of the file is one run without CRCs.

**Scope.** Disk, once, two volumes each (`analysis/reports/v1.13.2/fixes/WAVEC_CLOSE_evidence/probe_outputs.txt`,
p_v34_crc and p_crc_cover). Why the driver leaves the 0x40 runs unchecksummed is not read (open_questions Q43). The
SHA-256 and 64 KiB-cluster statements stand. Corrects master §C.6; the tool was fixed at wave C's close (N462, N463).

<a id="e153"></a>
## E153 (1.14.0, RC1-docs; filed 2026-11-12; RUNNING_LOG N186) — the EA chain: the data-area size is the chain's length, the last entry's NextEntryOffset is its own size, and PackedEaSize is a u16

**What was said.** Master §C.2c: every sub-record value's +0x04 is "value length minus 12"; §C.2d's `$EA` table:
NextEntryOffset "0 = last entry"; §C.2d's `$EA_INFO` table: PackedEaSize a u32 at +0x0C; `docs/attributes/
EA_INFORMATION.md` the same, with the chain "8-byte aligned".

**What is true.** On the 16 `$EA` values read (win11refs2gtargeted 11, win11refs4gattributes 5) the value is 76 bytes
and +0x04 is 60, the chain's length, equal to `$EA_INFORMATION` val[0x10]: a value can be longer than 12 + its data
area. `RefsAppendEa` stores each entry's own 4-aligned size as its NextEntryOffset when its caller passes 0, which the
last entry always does (26100.9444 :397669-397671, :397694); the last entry holds 20 on 16 of 16 values and 0 on none,
and the chain ends at the data-area size. `$EA_INFORMATION` +0x0C is a u16 PackedEaSize followed by a u16 NeedEaCount
(`RefsReplaceFileEas`, as §C.9 already states).

**Scope.** Disk: the W2 critic's reads of the 16 values (`analysis/reports/v1.13.2/D14/critic/si_group.md`, EA claims 18
and 21), once; static: 26100.9444, once. Whether +0x04 is the content's size on the other sub-record types is not
measured here. Not in E153: E40's v3.4 `$I30` name (a second reading pending). The tool is unaffected (`parse_ea_chain`
stops at the end of the value). Corrects master §C.2c and §C.2d, `docs/attributes/EA_INFORMATION.md`.

<a id="e154"></a>
## E154 (1.14.0, RC1-docs; filed 2026-11-12; RUNNING_LOG N228) — the checkpoint virtual clock counts checkpoints, not file operations or transactions

**What was said.** Master §A.4, "Virtual Clock Typical Values" (status NEW, no witness): "Freshly formatted volume
~20-30", "After ~1,000 file operations ~50-100", "After v3.4 to v3.14 upgrade +41 transactions"; master §H.5 "~68 (+41
transactions)"; `docs/concepts/what_survives.md` ("adds roughly 41 transactions to the virtual clock") and the 1.13.1
`structures/chkp.md` table.

**What is true.** The clock (+0x60) increments per committed checkpoint (master §A.4's own +0x60 row); the number of
checkpoints a workload produces depends on what ran and for how long. Read: 29-63 on the nine volumes formatted by
Windows 10 (`analysis/rawdisk/runs/chkp/chkp_win10refs*.txt`, the latest copy); 27, then 68 on win10to11refs4g before
and after its first Windows 11 mount (the upgrade: +41 checkpoints); +35 checkpoints on the other measured upgrade
(FS_CHKP_RA_003); 57-534 on the lab volumes, 662 and 293 after the "millions of actions" workloads and 617 on the
published sample after four 1,000-action replays (N228's list).

**Scope.** The Windows 10 range and the win10to11refs4g pair re-read 2026-11-12 from the run outputs named; the rest as
N228 lists them. Corrects master §A.4 and §H.5, `docs/concepts/what_survives.md` (the published `chkp.md` table is
not in the 1.14.0 page).

<a id="e155"></a>
## E155 (1.14.0, RC1-docs; filed 2026-11-12; RUNNING_LOG N177) — the first user OID is 0x701, and a gap in the OID sequence is a deletion or a failed creation

**What was said.** Register FS_OTBL_RA_006: "user OIDs start at 0x700 (hardcoded in MsSetMinimumNewObjectId)" and
"Gaps = deleted objects"; FS_OTBL_SA_004: "user OIDs (0x700+)"; master §F.5: "Gaps in sequence = evidence of past
deletions".

**What is true.** `MsSetMinimumNewObjectId` seeds the counter with 0x700 and `GenerateIdentifier` returns counter + 1
(26100.9444 :150897, :232562-232607), so the first user OID is 0x701; the four published samples' outputs hold 0
occurrences of 0x700 against 40-2,316 of 0x701. `GenerateIdentifier` commits the counter in its own top-level action,
and `OpenFileSystemFile`, `RefsAllocateObjectId`'s only caller (:464711), draws a directory OID before the directory
exists, so a creation that fails leaves a gap as a deletion does; only directories draw user OIDs.

**Scope.** Static: 26100.9444 (the deletion critic; `GenerateIdentifier` and the one caller re-read by the lead,
2026-11-12). Disk: the four samples' outputs. Not measured: a gap from a failed creation. Not settled here: whether the
counter is reloaded from the Object Table root or derived from its rightmost key at mount (master §F.5 and
`oid_allocation_mechanism.md` disagree; open_questions Q44). Corrects FS_OTBL_RA_006, FS_OTBL_SA_004, master §F.5,
`docs/concepts/object_ids.md` and `docs/concepts/oid_allocation.md` (the gaps, the bound of the deletion estimate, the
mount-time restore stated as not traced).

**Update (2026-11-21, RUNNING_LOG N639).** The point left open above is answered by `CmsObjectTable::InitializeTable`
(26100.9444 :232893-233090; the same lines on 26100.8115 :233315 and Insider 29574 :300199): both. When the Object
Table root's data is set (its first u32 not 0), the 128-bit counter (this+0x10 / +0x18) is reloaded from it (root data
+0x08 / +0x10; :233021-233027); then `CmsTable::FindRow` with `_CmsKey::RightMost` (:233052) reads the table's largest
key, and when that key is above the counter the counter is raised to it, unless bit 0x2 of the volume's +0xD34 is set
(+0xD84 on Insider 29574; :233054-233070). One reading per build; 17134 has no `_CmsKey::RightMost` and was not read.
Answers open_questions Q44 for these builds; master §F.5 and register FS_OTBL_SA_002 follow.

**Update (2026-11-21, the static readings S2, S3, S16; RUNNING_LOG N655).** 17134 read: its
`CmsObjectTable::InitializeTable` (17134 :2431, reached from `RefsMountVolume` through `MsInitializeVolume` and
`CmsVolume::Start`, :265910, :115352, :55582) loads nothing from the root's data; it reads the table's last key
(`CmsFailoverBPlusTable::FindLastInIndex`, :2550) and sets the counter (+0x38 / +0x40) to it when its low half is above
0x4FF, else, or when the table is empty, to 0x500 (:2552-2576). On every build read, the same mount later calls
`MsSetMinimumNewObjectId` (17134 :266138; 26100.8115 :427746; 26100.9444 :427071; Insider 29574 :591147), which raises a
counter below 0x700 to 0x700. "Returns counter + 1" above means the counter's value after the increment: the counter
holds the last OID given out (26100.9444 :232601-232607; 17134 :176017-176027). Q44 is resolved.

<a id="e156"></a>
## E156 (1.14.0, RC1-docs; filed 2026-11-12; RUNNING_LOG N185) — the volume-information driver stamp names the last writable mount's driver, not the highest; the label has no terminator

**What was said.** Register FS_VOLI_RA_001: the stamp at +0x82/+0x83 is "the HIGHEST ReFS driver build that ever
mounted the volume", and "drv=3.15 appears ONLY after an Insider mount (forensic: detects Insider exposure)";
FS_VINF_RA_001 and master §F.4: the volume label is "null-terminated".

**What is true.** `SetVolumeMounted` stores the mounting driver's own constant with no comparison (17134 :265530,
26100.8115 / .8521 :385763, .8972 :385207, .9444 :385407, Insider 29574 :532295), and only on a writable mount
(26100.9444 :427075-427076, :476905-476906): the stamp names the driver of the last writable mount. A later writable
mount by an older driver replaces an Insider stamp, and a read-only or write-blocked mount leaves it. The label is
copied by length (`AllocateAndGetVolumeLabel`, 26100.9444 :133995; a value of 0x10000 bytes or more is refused,
:133970 / :133999) and has no terminator on the three volumes read.

**Scope.** Static: six builds for `SetVolumeMounted`, 26100.9444 for the write-protect gate and the label (the si_group
critic's reading). Disk: three volumes for the label. Corrects FS_VOLI_RA_001, FS_VINF_RA_001, master §F.4 where it
says null-terminated, `docs/attributes/VOLUME_INFORMATION.md`, `docs/structures/volume_info.md` and
`docs/concepts/driver_builds.md`.

<a id="e157"></a>
## E157 (1.14.0, RC1-docs; filed 2026-11-12; RUNNING_LOG N183; the RC3 correction K120) — the USN truth layer: createjournal grows but never shrinks, a range from 0 is not proof of a re-creation, and the Change Journal's sub-records are two $J data records and the $Max

**What was said.** Register MD_USN_RA_009: `createjournal` "does not resize", "the same 32 MiB allocation as every
other corpus volume", "DISCARDS the existing history", and a USN range starting at 0 on a used volume "indicates the
journal was recreated"; MD_USN_RA_007, MD_ATTR_009 and master §C.13 / §O: two multi-instance sub-records "$J" and
"$Max" (and "$USN_INFO" for the third); AP_CHJN_002: NTFS's V2 file reference "32-bit"; MD_USN_RA_001's description:
records of 96-168 B; master §C.13: 80-312 B observed; E27: one journal id per volume; E58: "only V2/V3".

**What is true.** `RefsSetupUsnJournal` grows a journal but never shrinks it: a 32 MiB floor, at most half the volume
and 4 GiB, 256 KiB rounding, AllocationDelta 0 (26100.9444 :444931-444988; also read on 26100.8115, Insider and
17134 by the usn checker and critic); no clearing path was found. `createjournal` over an existing journal keeps the id
and restarts at USN 0 (LAB-J); the earlier sequence's bytes can survive above the new numbering (win11refs8g). A range
from 0 on a used volume says the journal was created after that activity, the first time or again: the published
win11refstestmftecmd's journal is a first creation after a 1,000-action replay (journal id 0x01dcea86b624a787 =
2026-05-23 07:35:21 UTC; LastUsn 0 on 292 of 292 objects under /test). The Change Journal value holds three
sub-records: two multi-instance $DATA records of the $J stream (type 0x000E0080; sub_id 0x8, a 40-byte stream-metadata
value with no extents, and sub_id 0x1000, the extent node with the $J extents) and the single-instance type-0xF0
record, the $Max (44 B) (K120: 34 Change Journal rows on 113 images). USN_RECORD_V2 carries 64-bit file references.
Records are 80-408 B (408 on winsider and winsiderv2, read whole after E71). A journal id is per journal instance (E27
as amended); every record read is V3 and the driver rejects a major version below 3 (E58 as amended).

**Scope.** Static: the readings named. Lab: LAB-J (A10), T16 on lab314_main. Disk: K120's walk; the published sample's
transcript order and `files.csv`. Corrects MD_USN_RA_009, MD_USN_RA_007, MD_ATTR_009, AP_CHJN_002, MD_USN_RA_001,
master §C.13, E27, E58, `docs/structures/usn_journal.md` (the recreation table, the record length). The lab procedure
`analysis/rawdisk/lab/T21_timestomp_lab_procedure.md:76` ("does not resize") is a dated lab document, left as written.


<a id="e158"></a>
## E158 (1.14.0, PLAN §10.1; filed 2026-11-12; KNOWLEDGE_INTAKE A152; amends E141) — checkpoint flag 0x400 marks a record that carries the rollback-protection fields: +0x9C and +0xA0 locate the blob, and are zero when there is none

**What was said.** E141: "Checkpoint flag 0x400: no build was read testing or setting it; it is set on every 3.14 volume
of the corpus ... and on none formatted at 3.4-3.10", and 0x400's meaning was listed as not read. The tool prints the
flag as "set on ReFS 3.14 volumes (its meaning is not read)".

**What is true.** `FormatCheckpointRecord` sets 0x400 in the record's flags (+0x78) when `VersionCheck(0x30d)` holds,
i.e. the volume version is 3.13 or later, and asks `CmsRollbackProtection::GetInfoAsBinaryBlobToPersist` for the
volume's rollback-protection information: when there is none, the 8 bytes at +0x9C are zeroed; otherwise +0x9C holds the
blob's offset in the record and +0xA0 its length, and the blob is copied there (26100.9818 :217038-217055).
`ValidateAndAttestMountMeasurementsImpl` reads the blob only when 0x400 is set and +0xA0 is not 0, and refuses the mount
(0xC00004E3) for a blob under 0x50 bytes or one whose offset + length exceeds the size it is given; with no blob it
refuses only when the volume asks for rollback protection (flag 0x200000 at +0xD34 of its first argument) and the
firmware variable `BootVolumeRollbackProtectionGUID` is not reported absent (26100.9818 :277919-277932). 17134 has no
such code. On the disk, every checkpoint record of a 3.14 volume carries 0x400 with +0x9C = +0xA0 = 0, and no record of a
3.4-3.10 volume carries it (there +0x9C / +0xA0 hold other values).

**Scope.** Static: the setter on 26100.8115 :217453, .9818 :217039, Insider 29574 :193818, 29659 :39532, 29683 :156493 (each
under `VersionCheck(0x30d)`); the reader on .8115 and .9818 :277919, Insider 29683 :220085-220100. Disk:
`analysis/reports/v1.13.2/DRIVERS_10_1/chkp_0x400_census.jsonl` (124 ReFS volumes of corpus.lst, both copies: 0x400 on
all 220 records formatted at 3.14, version-edited fixtures included, +0x9C = +0xA0 = 0 on every one; on none of the 28
records of 3.4-3.10 volumes). No corpus record holds a blob: that branch is read in the driver only, and no 3.11-3.13
volume is in the corpus. Amends E141 (0x400's meaning); the tool's label and `docs/structures/chkp.md` follow with the
maintainer's answer (PLAN §10).

**Amendment to E158 (2026-11-12 13:34Z, the consolidation the maintainer asked for).** The setter is read twice on
26100.9818 and Insider 29683: the decompilation and the instructions (`MOV EDX,0x30d; CALL VersionCheck; TEST AL,AL;
JZ ...; BTS dword ptr [RDI+0x78],0xa`, .9818 0x140105377-0x140105388, 29683 0x1400b06fe-0x1400b070f). The +0x9C / +0xA0
pair is one of the record's optional areas: E159.

<a id="e159"></a>
## E159 (1.14.0, PLAN §10.1; filed 2026-11-12; KNOWLEDGE_INTAKE A158 / A159; amends FS_CHKP_RA_005, FS_CHKP_RA_012, FS_CHKP_RA_009) — the checkpoint record's header locates its optional areas by (offset, length) pairs: +0x88 / +0x8C is a 32-byte area, not a "data area end" and a "max root capacity", and flag 0x2000 marks Insider's attestation HMAC at +0xA4 / +0xA8

**What was said.** Master §A.4: +0x88 "Data area end offset", +0x8C "Max root capacity" (the
`MS_CHECKPOINT_MAX_ROOTS = 0x20` label "where the region is populated"); FS_CHKP_RA_005: "data area end offset. Value =
first_root_offset + root_count * ref_size"; FS_CHKP_RA_012: +0x8C 0x20 or 0, "a field-pair"; FS_CHKP_RA_009: flag
0x2000 Insider only, "related to CmsVolumeAttestation/CmsRollbackProtection". refsanalysis `chkp -vv` prints the two
fields as "Data area end" and "Max root capacity"; `docs/structures/chkp.md` names them so.

**What is true.** `FormatCheckpointRecord` lays out the 13 root references and then up to three optional areas, each
located by an (offset, length) pair of u32 in the record header, the next area starting at the previous one's end
rounded up to 8: **+0x88 / +0x8C** a byte span its caller passes (`CmsVolume::Checkpoint`, which compares it with the
previous record's area), both zero when there is none (26100.9818 :217024-217036; Insider 29683 :156476-156490);
**+0x9C / +0xA0** the rollback-protection blob, with flag 0x400 (E158); and on Insider, **+0xA4 / +0xA8** the
attestation HMAC structure: `CmsVolumeAttestation::CreateEmptyHmacStructure` sets flag 0x2000, +0xA4 = its offset and
+0xA8 = its length, 0x48 or 0x48 + 2^n (29574 :342842, 29659 :374577, 29683 :336833-336843; called from 29683's
`FormatCheckpointRecord` under `VersionCheck(0x30d)`, :156512-156516; 26100.9818 has no such function). The root-offset
table pair +0x94 / +0x98 (flag 0x200, E140) has the same form. +0x88 equals the end of the root references because the
area is placed right after them. On the disk (`analysis/reports/v1.13.2/DRIVERS_10_1/chkp_0x400_census.jsonl`, 2026-11-12
13:27Z; 124 ReFS volumes, both copies): +0x88 / +0x8C are both 0 on 44 records formatted at 3.14 and an in-record offset
with **length 0x20 on every other record** (204: 0x680 on 3.4-3.9, 0x370 on 3.10, 0x380 / 0x388 / 0x4D0 / 0x4D8 on 3.14; 0x4D8, on the 2 records of `wininsiderrefs8gtest2`, added 2026-11-17: the census holds it, this list had left it out); the 32
bytes are zero on 126 records and hold data on 78 (not decoded: open question Q46). Flag 0x2000 is set on 10 records,
the 5 volumes an Insider build mounted, each with +0xA4 / +0xA8 = an in-record offset (0x3A8 or 0x4F8) and length 0x48.

**Scope.** Static: 26100.9818 and Insider 29683 for the layout, the three Insider builds for 0x2000; 17134's writer not
read (the disk shows the same 32-byte area on 3.4). Insider's larger minimum root offset (0xB0 against 26100's 0xA8,
E140) is consistent with the extra pair; that link is not read. Corrects master §A.4 (+0x88, +0x8C, the flags table's
0x2000), FS_CHKP_RA_005, FS_CHKP_RA_012, FS_CHKP_RA_009, `docs/structures/chkp.md`, and refsanalysis `chkp -vv`'s two
labels (the code half).

<a id="e160"></a>
## E160 (1.14.0, PLAN §10.1; filed 2026-11-12; KNOWLEDGE_INTAKE A153 / A160) — the redo records' writers name opcodes 0x1A, 0x25 and 0x2B on 26100 too, and Insider 29683 logs a table deletion as 0x2D, not 0x0F

**What was said.** `forclaude/intelligence/redo_opcode_complete.md` and the tool (`_REDO_V314_UNCONFIRMED` =
{0x16, 0x1A, 0x25, 0x2B}): 0x1A replayed inline with "no `RedoAddCompressionUnitOffsets` in any 26100 build or Insider
29574", 0x25 and 0x2B an indirect table-set callback (vtable +0x08 / +0x18) "concrete handler not static"; the tool's
comment "Opcodes 0x00-0x2B are a CONTIGUOUS dispatched range" (v3.14); a table deletion is opcode 0x0F, the one record
the tool's classifier reads as DELETE.

**What is true.** The function that WRITES each record names it, on 26100.9818 and Insider 29683 alike: 0x1A
`InsertContainerCompressionHeaders` (.9818 :228163, 29683 :296160), 0x25 `LogRedoForWeakRefPurge` (.9818 :259173, 29683
:322720), 0x2B `LogRedoForStrongRefMergeSingle` (.9818 :259089, Insider 29574 :325436, 29659 :361007, 29683 :322687); Insider
29659 and 29683 replay them through functions of those names (`RedoAddCompressionUnitOffsets`,
`RedoTableSetWeakRefPurge`, `RedoTableSetStrongRefMergeSingle`). `DeleteTable` logs opcode 0x0F on 26100.9818 (:128716),
Insider 29574 (:64266) and 29659 (:110900), and **0x2D on Insider 29683** (:213182, with a 16-byte value; no 0x0F writer
is left there). `PerformRedo` replays 0x2D with `RedoDeleteTable` on 29683 (as 0x0F) and refuses it (0xC0000427) on 29574
and 29659 -- read twice on each (the decompilation and the instructions). So a log record with opcode 0x2D is a table
deletion written by a build that logs it so: of the builds read, Insider 29683 only. 0x16 has no writer by the same
search on .9818 or 29683.

**Scope.** Static only (no corpus log carries 0x2D; no corpus volume was written by 29683). Writer search: every
`AddRedoRecord` call whose opcode argument is a constant. Corrects `redo_opcode_complete.md` (0x1A, 0x25, 0x2B, the
Insider ranges), the register's "Redo dispatch" row, `docs/structures/mlog.md`, and the tool's labels for 0x1A / 0x25 /
0x2B / 0x2D and its DELETE rule (the code half).

<a id="e161"></a>
## E161 (1.14.0, the article review's ART-01; filed 2026-11-17; KNOWLEDGE_INTAKE A172; corrects the updates of E21 and E33, scopes MD_SI_RA_009) — `$SI+0x70` is the file's link count as the driver last wrote it: 1 in an embedded record, the number of names in a split record's type-0x40 backing

**What was said.** E33's update (2026-06-14): "$SI+0x70 remains the resident-only field (always 1), NOT the multi-name
counter." E21's update (2026-06-16): "$SI+0x70 is ≤ 1 (0 or 1, never > 1: 0/4674 objects with HLC>1)". Register
`MD_SI_RA_009`: "HardLinkCount ($SI+0x70) >1: ZERO across 525165 entries / 111 images because $SI+0x70 is a
EMBEDDED-LAYOUT field always 0/1 — it is NOT the multi-name counter."

**What is true.** The driver keeps the link count in the FCB (+0xb4) and writes it at $SI+0x70 on every change of the
file's names: `RefsConvertToStandardInfoLinkCount` (`RefsPartialSetStandardInfo(..., 0x70, 4)`) is called by
`RefsSetLinkInfo` after `RefsAddLink` (the count + 1; a new link is refused at 0x2000), and by `RefsPosixDeleteLink`,
`RefsCommonCleanup` and `RefsRemoveOrphanedHardlinkBackPointer` (the count - 1), and by `RefsSetRenameInfo` (26100.9818
`refs.decomp.c` :190268, :407247, :407317-:407324, :392359-:392360, :474607, :420844, :408614; the writer is present in 26100.8115,
.9444 and Insider 29574, 29683, absent from 17134, which has no hard links). A file with one name keeps its record in its
name row (embedded) and reads 1 there; a hard-linked file's record is split into a type-0x40 backing, which carries the
count. Disk: over 107,525 backings $SI+0x70 reads more than 1 on 101,252 (94.2 %), 1 on 6,235 (split records with one
name: moved files), 0 on 38 (each with $SI+0x24 bit 0x01 or 0x04, or a system object), and equals the number of
size-matched names on 99.84 %; on the `fsutil`-ground-truthed volume the three backings read 4 / 2 / 1 against `fsutil`'s
4 / 2 / 1 (the D14 measurement, `analysis/reports/v1.13.2/D14/measure/attributes__STANDARD_INFORMATION.tsv`); the first
blind audit measured the same independently (K109: equal to the names on 74,297 of 74,297, and to the lab314 Windows
inventory's `Links` column). The three statements above measured embedded records only.

**Scope.** Static: 26100.9818 read at the call sites; the other builds by the writer's presence. Disk: the corpus
backings (D14) and the blind audit's 10 volumes. **Corrects** E33's and E21's updates (read "always 1 / ≤ 1" as "1 in an
embedded record"); `MD_SI_RA_009` is scoped to embedded records. The docs (`attributes/STANDARD_INFORMATION.md`) already
say it.

<a id="e162"></a>
## E162 (1.14.0, the D18 sweep; filed 2026-11-18; KNOWLEDGE_INTAKE A73, the C2 fixer's bounds_a, 2026-10-23; corrects E74's "Coverage gap" row) — the allocator covers the whole volume: the "48 MiB past the last container" is the image's bytes after the volume

**What was said.** E74's "Coverage gap" row: "The allocator's virtual space covers only what the Container Table maps;
the physical tail beyond the last container belongs to no tier. Measured as exactly 48 MiB on 90/95 images". Master
§B.2 ("Coverage limit"): the tail `[last mapped cluster … volume end)` "belongs to no tier: exactly 48 MiB on 90/95
images ... Report it as *outside the allocator*, never as free." `refsanalysis help allocators`: "The tail of the volume
past the last container belongs to no tier and is reported separately".

**What is true.** The Medium allocator's persisted summary (its root page, u64[1]) equals N = total sectors × bytes per
sector ÷ cluster size, the volume's own length from the boot sector, on 117 of 117 corpus ReFS volumes: the allocator
covers the whole volume. The 48 MiB was measured to the end of the image, not of the volume. The volume's length is its
partition rounded down to a whole number of 64 MiB, so on 115 GPT images 47.9 MiB of the partition follow the volume,
and 64 KiB follow the partition; on lab314_4kn 47 MiB and 1 MiB; on winsider and winsiderv2 38 MiB inside partition #3,
and another partition after it. Those bytes are the image's, outside the volume; the tools report them as the image
tail. `FS_ALLOC_RA_002` already states it from the Container Table side (the mapped end equals the boot sector's cluster
count on 11 of 11 volumes).

**Scope.** Disk: measured once over the 117 volumes (MR-V, `analysis/reports/v1.13.2/fixes/WAVEC_measurements/
bounds_census.jsonl`: `alloc.s1_vs_N`, `volume.gap_in_partition`, `tail_after_partition`), and a second time on 5 of
them by the fixer's A/B probe (`fixes/C2_fix_bounds_a_evidence/ab_diffs.txt`: win11refsmini, win10refsmini,
lab314_64k, lab314_4kn, winsider). No driver reading of the allocator's span. **Corrects** E74's "Coverage gap" row
(read "the physical tail beyond the last container belongs to no tier" as "there is no such tail inside the volume").

<a id="e163"></a>
## E163 (1.14.0, the D18 sweep; filed 2026-11-18; KNOWLEDGE_INTAKE A165's amendment, the group-1 review F2 / F3) — `PerformRedo`'s current table is not emptied at a redo block's start: it belongs to the redo queue and carries into a block that continues a transaction

**What was said.** Master §E.4, the `_SmsRedoRecord` +0x08 row: a record with table path length 0 applies to
`PerformRedo`'s current table, which is empty "after a record whose branch uses no table ..., after `RedoDeleteTable`
(0x0F; 0x2D on Insider 29683) and after `RedoTableSetCommitMerge` (0x24), and at a redo block's start".

**What is true.** The current table is the redo queue's (`CmsLogRedoQueue`+0xf0): the queue's constructor zeroes it
(26100.9818 `refs.decomp.c` :249782) and `PerformRedo` writes it after each record (:252525). `RedoOneRecordBlock`
picks a new one only for a block whose first record starts a transaction (by object id, :253942-253965), so a block
that continues a transaction keeps the table the previous block left. The other points where it is emptied stand.

**Scope.** Static: 26100.9818, read by the group-1 review and re-read by the lead (2026-11-12); the other builds are not
read for this point. `structures/mlog.md` and the tool (`mlog`) already follow it.

<a id="e164"></a>
## E164 (1.14.0, RC3; filed 2026-11-20; RUNNING_LOG N180; amends E69's static sentence; corrects FN_LINK_002 and FN_LINK_004) — `RefsLinkFileToSelf` copies no identity into each name: it runs once per file and re-parents the file's own table under the type-0x40 key, and 0x80000040 is that key's prefix, not a tag

**What was said.** E69's Evidence row: "Static (E2): `RefsLinkFileToSelf` copies the identity into each name and adds a
type-0x39 back-pointer, allocating no new stream." Register `FN_LINK_002` (static note): "RefsLinkFileToSelf/RefsAddLink
copy the home pair under tag 0x80000040". `FN_LINK_004` (static note): "RefsLinkFileToSelf copies the (home,ordinal)
identity into each name and adds a type-0x39 back-pointer, allocating no new stream."

**What is true.** `RefsLinkFileToSelf` runs at most once per file: each of its four callers (`RefsSetLinkInfo`,
`RefsSetRenameInfo`, `RefsPosixDeleteLink`, `RefsRemoveSupersededTarget`) calls it only while FCB+8 bit 28 (0x10000000)
is clear, and it sets that bit. It re-parents the file's own table (the FCB's table handle at +0x108) with
`MsReparentChildTable` under the key {0x80000040, 0, file reference} -- 0x80000040 is the type-0x40 key prefix, the key of
the split record's backing row, not a tag -- and then writes back, with `RefsAddLink`, the name the record sat under
(`RefsBuildFileNameFromNonLinkedFile`), as an index entry, plus a 0x80000039 back-pointer in the file's table (E131). The
table is moved, not copied: no new stream is allocated. The names a hard link adds are written by `RefsAddLink` called
from `RefsSetLinkInfo`, not by `RefsLinkFileToSelf`. E69's disk evidence (one home-owned backing per object, one type-0x39
back-pointer per name) stands, and so does the (home, ordinal) pair each name's index entry carries (`FN_LINK_002`,
measured); which lines of `RefsAddLink` write that pair was not read.

**Scope.** Static, read on three builds: 26100.8115 (RUNNING_LOG N180: `refs_win11.decomp.c` :192719 the name, :192730-192743
the key and `MsReparentChildTable`, :192746 bit 28, :192747 `RefsAddLink`; `RefsSetLinkInfo` -> `RefsAddLink` :405612),
26100.9549 and Insider 29574 (`analysis/reports/v1.13.2/RC1D/rc3/N166_DRIVER_READING.md` section 2.2: W9549 :192033-192044,
I29574 :262769-262780; `RefsSetLinkInfo`'s bit-28 test W9549 :404920-404922, I29574 :512710-512712). Re-read for this
filing on the three builds: the four callers' bit-28 tests (8115 :390668, :404476, :405292, :406314; 9549 :390312, :404104,
:404920, :405938; Insider :511596, :512710, :570658, :587176) and `RefsSetLinkInfo`'s `RefsAddLink` (9549 :405240, Insider
:513062). The index entry's key type 2, the back-pointer and the type-0x20 row are E131's reading (26100.8115 and .9711,
twice). 17134 has no `RefsLinkFileToSelf`. **Amends** E69's static sentence (read "copies the identity into each name and
adds a type-0x39 back-pointer" as "re-parents the file's own table once and writes back the name the record sat under,
with its back-pointer; each further name is `RefsAddLink`'s"); **corrects** the static notes of `FN_LINK_002` and
`FN_LINK_004`. The docs (`concepts/hard_links.md`) already describe the move; no page or tool carries the old reading.

<a id="e165"></a>
## E165 (1.14.0, RC3; filed 2026-11-20; the byte-figure pilot's disagreements, `analysis/reports/v1.13.2/RC1D/rc3/site_reports/D.md` §6 items 1-2, re-measured in `D13.md`; corrects master §C.0b and §C.2b) — a file's main `$DATA` is single-instance when its data is inline (key marker 0x80000001, a 16-byte key, subtype 0x0000) and multi-instance when it is in extents (0x80000002, a 40-byte key, subtype 0x000E); a record carries one form, never both

**What was said.** Master §C.2b: "0x80000001 | Single-instance attribute (reparse 0xC0, EA info 0xD0, EA 0xE0)",
"0x80000002 | Multi-instance attribute ($DATA 0x80, $SNAPSHOT 0xB0)"; §C.0b's embedded sub-record table: "0x80 |
$DATA | MI | (resident files)". The docs: `attributes/README.md` §2 listed `$DATA` (0x80) under 0x80000002 only;
`attributes/DATA.md` gave the single-instance key's subtype at +0x0E as 0x000E and said every file has a
single-instance entry "plus one or more multi-instance entries".

**What is true.** A file's main `$DATA` sub-record, in its record (its type-0x30 name row, or its type-0x40 backing
once the record is split out), takes one of two forms. Data inline: one row whose 16-byte key is {u64 value length,
u32 0x80000001, u16 type 0x0080, u16 subtype 0x0000}, its value the stream summary (summary size 0x30) followed by the
bytes at +0x3C (§C.2d). Data in extents: rows whose 40-byte key carries 0x80000002 at +0x08, type 0x0080 and subtype
0x000E at +0x0C (read as one u32, the descriptor 0x000E0080) and the sub-stream id at +0x10 (0x8 the stream-set
record, 0x1000 the live data, 0x1001 and above the snapshot versions; §C.6). Measured on the user directories (OID 0x600 and above) of the 124 corpus ReFS volumes (2026-11-20): 563,606
single-instance `$DATA` keys (542,867 in name rows, 20,739 in backings), every one 16 bytes with subtype 0x0000 and the
inline value; 334,044 multi-instance `$DATA` keys (156,014 / 178,030), every one 40 bytes with subtype 0x000E. Of the
730,556 records holding a marked `$DATA` key, 563,606 carry the single-instance row and no multi-instance one, 166,950
carry multi-instance rows (always both sub-stream ids 0x8 and 0x1000; 66 also snapshot versions) and no single-instance
one, and none carries both. The 0x000E the docs gave the
single-instance key is the multi-instance key's subtype. E82 established the single-instance marker and the
exclusivity for the type-0x40 backing; they hold for the name row too. The master's own §C.2d ("SI $DATA") and §C.3a,
the register (`FS_SNAP_RA_001`: "Marker 0x80000001: single-instance (0x80 DATA header ..."; `MD_DATA_RA_022`) and the
tool (`_backing_inline_data`, `_resident_data_sizes`, which match 0x80000001 + type 0x0080) already say it.

**Scope.** Disk only, the user directories (OID 0x600 and above) of the 124 corpus ReFS volumes of `analysis/verification/corpus.lst` (the five NTFS or BitLocker images excluded); the
single-instance keys are on 109 of them, all v3.14 (three with a hand-edited version field, E96). The single-instance form is measured on
v3.14 volumes only: formats up to 3.10 hold no inline `$DATA`, and v3.4 keys carry no marker (E72). No driver reading
of the key's writer. **Corrects** master §C.0b and §C.2b; the docs pages `attributes/DATA.md` and
`attributes/README.md` are corrected with it (`structures/directory_entries.md` already listed 0x80 under both
markers); the register and the tool need no change.

<a id="e166"></a>
## E166 (1.14.0, RC3; filed 2026-11-21; the RC3 site review C2, `analysis/reports/v1.13.2/RC1D/rc3/site_reports/C2.md`; RUNNING_LOG N637) — the root-offset table's place at +0x94 depends on the build that wrote the record, not on the cluster size

**What was said.** Master §A.4 "Direct vs indirect root access": with flag 0x0200, "`CHKP+0x94` is an in-page offset
(0xA8 on 4K, 0xB0 on 64K — always << page size) ... (disk-verified 2026-07-05: flags 0x682→0xA8, 0x2682/64K→0xB0)".

**What is true.** The writer decides the value. 26100.9818's `FormatCheckpointRecord` sets +0x94 = 0xA8 and +0x58 =
0xA8 + the table's length (`refs.decomp.c` :217009-:217013; the same value in 26100.8115 and .9444); Insider 29683's
sets +0x94 = 0xB0 and +0x58 = the table's length + 0xB0 (:156459-:156462; the same in 29574 and 29659), its header
also carrying the attestation pair +0xA4 / +0xA8 (E159). On the disk (`analysis/reports/v1.13.2/DRIVERS_10_1/
chkp_0x400_census.jsonl`, 124 ReFS volumes, both copies), every flag-0x200 record reads +0x98 = 0x38 and +0x94 = 0xA8
on the 210 records no Insider build wrote (200 on 4 KiB volumes, 10 on 64 KiB) and 0xB0 on the 10 an Insider build
wrote (flag 0x2000: 8 on 4 KiB volumes, 2 on 64 KiB). The 2026-07-05 pair compared a 26100 record on a 4 KiB volume with
an Insider record on a 64 KiB one, so the cluster size and the build changed together.

**Scope.** Static: 26100.8115, .9444, .9818 and Insider 29574, 29659, 29683; 17134 writes no flag-0x200 record (E140).
Disk: the census above. **Corrects** master §A.4 (the sentence above). The pages (`docs/structures/chkp.md`) and the
tools already state it by build; a retired-claim canary (`check_retired_claims.py`, id `chkp-0x94-by-cluster`) keeps the
old reading out.

<a id="e167"></a>
## E167 (1.14.0, RC3a; filed 2026-11-21; N158, decided with the maintainer 2026-11-21; `analysis/reports/v1.13.2/RC1D/rc3/embedded_record/NOTES.md` S5-S15, D1, D2; `RC1D/rc3a/disk/system_table_schemas.jsonl`) — the schema ids 0x110-0x200 are the schemas of whole tables, named by the table's role and chosen by the format era, not "type code + 0x100"; and the attribute types 0x50 / 0x60 / 0x70 are $OBSOLETE / $VOLUME_NAME / $VOLUME_INFORMATION

**What was said.** Master §F.2 "Attribute Schemas": "Schema ID = type code + 0x100 (for per-object attributes)", each
id named after the attribute of its type code: 0x130 "$FILE_NAME / dir entry", 0x140 "Backing record", 0x150
"$VOLUME_INFORMATION" (type 0x50), 0x160 "Reparse Index" (type 0x60), 0x170 "$REPARSE_POINT", 0x180 "$DATA", 0x190
"$STANDARD_INFORMATION / $I30_INDEX", 0x1A0 "type 0xA0", 0x1B0 "$SNAPSHOT", 0x1C0 "$REPARSE_POINT (v2)", 0x1D0
"$EA_INFORMATION", 0x1E0 "$EA", 0x1F0 "$UsnJrnl:$Max", 0x200 "$LOGGED_UTILITY_STREAM"; §F.4 / §D: OID 0x530 "stream-type,
no schema"; `docs/structures/schema_table.md` (its "Naming rule"), the attribute pages' "Schema id" rows, the register
(FS_SCHM_RA_005, FS_SCHM_RA_007, FS_SCHM_RA_008, MD_ATTR_006, MD_ATTR_010), refsanalysis `schema`'s Name column
(`_TABLE_TYPE_NAMES`) and forefst's `MLOG_SCHEMA_NAMES`.

**What is true.** A schema describes a whole table (its key type, root-data size and flags: the driver's
`RefsSchemaSet` entries, whose values the on-disk Schema Table rows carry, NOTES S10, S15). The ids are used as follows
(26100.x and Insider; 17134 where stated):
- the table embedded in a FILE's record (its type-0x30 row or type-0x40 backing): 0x180 below format 3.6, 0x1C0 from
  3.6 to 3.10, 0x1E0 from 3.11 (`RefsMountVolume` picks the set by the volume's version, S5, S8, S14; read on all 12
  builds held);
- the table embedded in a DIRECTORY's own row (type 0x10): 0x190 / 0x1D0 / 0x1F0 by the same eras;
- a DATA STREAM's table: 0x1A0 below 3.11, 0x200 from 3.11 -- the table embedded in each extent-form `$DATA` record
  (sub-stream id 0x1000 and up): its `_SmsIndexRoot` at +0x00 (+0x00 = 0x88, +0x04 = 0x28, +0x0C = +0x10 = 0x1A0 on 3.7
  and 3.10, 0x200 on 3.14, +0x20 = the node's rows: 3,197 records of 5 volumes, 0 counterexamples,
  `RC1D/rc3a/disk/census_data.jsonl`), the stream's sizes as its 0x60-byte root data (+0x28 to +0x87), the extent node
  at +0x88 (E86); the driver's readers of this slot are the data-stream-set functions (`RefsCreateOrOpenDataStreamSet`,
  `RefsCreateDataStream`, S9); no 3.4 record of this form is held;
- the older set 0x110 (file) / 0x170 (directory) / 0x120 (data stream): 17134 uses it on a volume whose boot sector
  lacks flag 0x04 (E169); no corpus object carries it;
- 0x130: the table of every directory (the B+-tree of its names): OID 0x520 and every user directory (0x600, 0x701 ...)
  on 3.4, 3.7 and 3.14 (`system_table_schemas.jsonl`); the driver sets it before `MsCreateVirtualBTableObject` (S10);
- 0x140: the security-descriptor table, OID 0x530 (`RefsSecurityInitialize`, 26100.9444 :458580-:458634, creates it
  with schema 0x140; on disk 0x140 on 3.4, 3.7 and 3.14);
- 0x150: the volume-information tables, OIDs 0x500 / 0x501 (`InitializeVolumeInfoTable`; on disk 0x150);
- 0x160: the reparse index, OIDs 0x540 / 0x541 (`InitializeReparseIndexTable`; on disk 0x160);
- 0x1B0: registered by 26100 / Insider and present in the on-disk Schema Table from 3.7, with a file-table shape (key
  type 9, root data 0x80, flags 1); no code read uses it and no corpus object carries it: role not read.
An object keeps its table's id until it is opened on a 3.6+ volume, which moves it to its era's id (S14: the id
rewritten for key type 0xF, the table re-keyed otherwise); on the volumes upgraded to 3.14, 1,221 file records and 199
directory own rows still carry an older id (census D2). An attribute has no schema of its own: a type code names an
attribute, a schema names a table. The driver's attribute-definition table (ATTRDEF) names the types 0x50 `$OBSOLETE`,
0x60 `$VOLUME_NAME`, 0x70 `$VOLUME_INFORMATION` (the .rdata table, stride 0x9C, UTF-16 name at +0, u16 type at +0x80,
ended by a zero entry: 14 named entries on 17134 and 15 on 26100.8115 / .9444, which add `$OBJ_LINK` 0x39; file offsets
refs_win10.sys 0x105190, refs_win11.sys 0x1ce390, 26100.9444 0x1ce3a0, re-read 2026-11-21 (X, MD_ATTR_SA_001); walked by
`RefsGetAttributeTypeCode`; read in D14, `analysis/reports/v1.13.2/D14/pages/concepts__attributes.md`); the "0x50 = $VOLUME_INFORMATION",
"0x60 = reparse index" names were worked back from the schema ids 0x150 / 0x160 with the +0x100 rule.

**Why it went unnoticed.** New formats added a new attribute and new table schemas in the same release (3.7, 3.14), so
the +0x100 pairing matched by coincidence; the schema set is a data block (`RefsSchemaSet`), not code, so decompilation
searches never showed it (N158 was opened 2026-09-27 as a question about labels).

**Scope.** Static: the mount slots on all 12 builds held; the schema set on 26100.8115/.9444/.9818/.9974 and Insider
29574/29659/29683, 17134's 10 entries in code (S10); the security / volume-information / reparse-index creators on
26100.9444. Disk: the census D2 (124 volumes, 820,293 records) and the system-table roots of 3 volumes (3.4, 3.7, 3.14).
**Corrects** master §F.2 (names, the +0x100 sentence), §F.3 (the role column), the OID 0x530 rows (§D, §F.4), the
register rows above, `docs/structures/schema_table.md`, the attribute pages' "Schema id" rows, concepts/attributes.md, and
the two tools' label tables (1.14.0, with their own changelog and output-change entries). A retired-claim canary keeps
"schema = type + 0x100" out. Register: FS_SCHM_RA_005, FS_SCHM_RA_007, FS_SCHM_RA_008, MD_ATTR_010 restated; new
FS_SCHM_RA_012 (the eras, the upgrade on open) and FS_SCHM_RA_013 (the system tables' schemas).
**Sweep, 2026-11-27 (1.14.1 D1; RUNNING_LOG N676, N679):** the attribute reading survived in places this erratum's
sweep did not reach, corrected now: the "Schema version-gating matrix" of `docs/concepts/version_evolution.md` (names
0x1B0-0x200 after attributes) and four more sentences there, `docs/concepts/architecture.md` (the "attribute schemas"
paragraph), `docs/README.md`; master §B.4 (the entry counts: header, totals sentence), §F.2 ("18 attribute") and the `$EA`
storage line; register FS_SCHM_RA_006 (description, notes), MD_ATTR_008 (description, notes), MD_ATTR_006 (notes), FS_SCHM_RA_010 (notes: 0x160 is on v3.4 too, 9 of 9 v3.4 corpus entries).
A retired-claim row keeps the table form out.

<a id="e168"></a>
## E168 (1.14.0, RC3a; filed 2026-11-21; N158; NOTES.md S1-S4, S11, S12, D2; `RC1D/rc3a/D6_D7_ANALYSIS.md` d6.1; supersedes E45's framing, corrects E26's name for $SI+0x38) — an object's record is an embedded B+-tree table: a 40-byte `_SmsIndexRoot` descriptor, the `$SI` as the table's root data, then the node of its attributes; on a file, `$SI+0x30` is the data size and `$SI+0x38` the allocated size

**What was said.** E45: "the type-0x30 resident value is an INDEX ENTRY, not a verbatim $SI": the own-row $SI and the
type-0x30 value are two structures that "mirror at every offset except value 0x58/0x60", the own row having "USN
($SI+0x30)" and "DataSize ($SI+0x38)" (both 0), the type-0x30 value FileSize / AllocatedSize there. E26: "$SI+0x38 is
DataSize", "the PDB name LastMftChangeTime is a misnomer". Master §C.0b: the first 40 bytes "B+-tree metadata" (+0x00
"Base offset", +0x04 "Flags, typically 0x00010028", +0x20 "Row count"); §C.2: "0x00 | 40 | Structural metadata";
§C.7: +0x30 "(USN slot — unpopulated)", +0x38 "(DataSize slot — unpopulated in $SI)", "PDB names it LastMftChangeTime";
register FS_OTBL_RA_008: the file record's value+0x08 u64 a per-format "sentinel" (0x18000000001 / 0x1c000000001 /
0x1e000000001).

**What is true.** One structure, written by the same driver code for files and directories:
- the value's first 0x28 bytes are the `_SmsIndexRoot` descriptor of the object's table (the one master §A.2b documents
  at a table-root page's +0x50; `MsParseEmbeddedTableInfoFromRow`, `CheckEmbeddedRoot`, `CmsBPlusTable::CreateIndex`'s
  embedded branch, 26100.9444): +0x00 the offset of the node (0x28 + the root data's size: 0xA8 on every record);
  +0x04 u16 the descriptor's size 0x28; +0x06 u16 (1 on every record; carried with the schema id, not decoded); +0x08
  flags (1 on every record; `CreateIndex` maps bits 0x2 / 0x4 / 0x8 into the table's state, never set on the corpus);
  +0x0C and +0x10 the table's schema id (E167; FS_OTBL_RA_008's "sentinel" is +0x08 = 1 and this id read as one u64);
  +0x14 u16 the table's checksum type, which `CreateIndex` requires to equal the volume's (CmsVolume+0x58, else
  0xC00000BB): 4 on every record of the four SHA-256 volumes, 2 elsewhere; +0x16 u16 1 when a FILE's table carries
  integrity (2,213 of the 2,215 file records with it carry the `$SI` attribute bit 0x8000, every record with the bit
  has it; 0 on every directory own row); +0x18 the leaf-page count (0 when the node is in the value, 1 with a child
  page); +0x20 the table's row count (on all but 5 of 820,293 records);
- +0x28 to +0xA7 the root data (0x80 bytes): the 124-byte `$SI` (116 on 3.4) and 4 bytes; `RefsComputeStandardInformation-
  FromFcb` builds it from the FCB and `MsUpdateDataWithRoot` writes it into the table's root data, for a file and for a
  directory alike (S1, S2; 17134 S12);
- +0xA8 the node of the table's rows (the attributes).
So a file's `$SI` and a directory's are the same structure at the same offsets. On a FILE's record `$SI+0x30` = FCB+0x90
is the file's data size and `$SI+0x38` = FCB+0x88 its allocated size (the size equals the `$DATA` record's on 623,436 of
623,440 file records, the allocated size on 623,437; the exceptions, all on `winsider`, are stale copies); on a
DIRECTORY's own row both are 0 (87,099 of 87,099). E45's "USN slot" / "DataSize slot both 0" was a measurement of
directory own rows only; E26's "DataSize" for +0x38 named the allocated size; no binary or PDB held contains the string
"LastMftChangeTime" (0 hits in the 12 refs.sys / refsutil binaries and PDBs under `analysis/static/binaries/`), so the
"PDB name" was not a symbol. E45's other findings stand (LastUsn / UsnJournalId, the per-file journal link).

The same descriptor heads a data stream's extent-form `$DATA` record (E167): master §C.6's "inner header size 0x88" is
its node offset and its "summary size 0x1A0 / 0x200" its schema id; the extent node at +0x88 (E86) is that table's node.

**Scope.** Static: 26100.9444 (the descriptor parse, the root-data write, CreateIndex), 26100.x / Insider 29574 / 29683
for the $SI writer, 17134 for the root-data layout (S12). Disk: the census D2 (all 124 ReFS volumes of corpus.lst) and
the +0x16 cross-tab on 7 volumes (3.4, 3.7, 3.14). **Corrects** master §C.0b (the header table), §C.2 (the 0x00 row,
the "index entry ... except 0x58/0x60" note), §C.7 (+0x30, +0x38), register FS_OTBL_RA_008, MD_SI_RA_002 (restated),
new GN_IDXR_RA_005 (the descriptor) and MD_SI_RA_017 (the $SI as root data, +0x30 / +0x38), the docs
(`directory_entries.md`, `btree_node.md`, `STANDARD_INFORMATION.md`'s "PDB label").

**Amended the same day, before any release (RUNNING_LOG N669, the Y trace).** The +0x16 figures above are the
7-volume cross-tab. The 124-volume census of E36's update (`RC1D/rc3a/disk/data_integrity_census.py`) gives +0x16 = 1 on
4,034 of the 4,037 files with the attribute 0x8000 and on 2 without it; the 3 others keep their data inline, where the
integrity is the `$DATA` value's +0x3A (E36). So "every record with the bit has it" holds for the files whose data is
in extents, not for every file. Register GN_IDXR_RA_005, `docs/structures/directory_entries.md`.

<a id="e169"></a>
## E169 (1.14.0, RC3a; filed 2026-11-21; N158 S13; `analysis/reports/v1.13.2/RC1D/rc3/vbr_hl_census.jsonl`) — boot-sector flag 0x04 selects the schema set of the volume's objects

**What was said.** Master §A.1c bit 2 (0x04): "Not decoded (no driver reading names it)"; `docs/structures/vbr.md`:
"Meaning not decoded".

**What is true.** 17134's `InitializeVcbFromBootSector` sets VCB+0x18 bit 0x80 when VBR+0x2C has 0x04
(`refs_win10.decomp.c` :276606-:276607); `RefsMountVolume` then uses the schema set (file, data stream, directory) =
(0x180, 0x1A0, 0x190), and without it the older set (0x110, 0x120, 0x170) (:265897-:265904). 26100.9444 refuses a
volume below 3.6 whose flags lack 0x04, status 0xC000029C (`refs.decomp.c` :426759-:426773). No refs.sys write of the
flag was found on 17134, 26100.9444 or Insider 29683, so it is set when the volume is formatted. On the disk the flag
is set on all 122 volumes whose flags were not edited by hand (the two hand-edited images read 0x63); no volume
without it is held, so the older set is read in the driver only.

**Scope.** Static: 17134, 26100.9444; Insider 29683 for the absence of a writer. **Corrects** master §A.1c (bit 2),
`docs/structures/vbr.md`; register: new FS_VBR_RA_015.

<a id="e170"></a>
## E170 (1.14.0, RC3a; filed 2026-11-21; open question Q46; register MD_USN_SA_002 (the driver reading, N387 b / KNOWLEDGE_INTAKE A8); `RC1D/rc3a/D6_D7_ANALYSIS.md` d6.2, `RC1D/rc3a/disk/chkp_payload_usn.jsonl`; amends E159) — the checkpoint record's 32-byte area (+0x88 / +0x8C) is the change journal's cursor that MD_USN_SA_002 reads in the driver

**What was said.** E159: "+0x88 / +0x8C a byte span its caller passes ... the 32 bytes are zero on 126 records and hold
data on 78 (not decoded: open question Q46)". MD_USN_SA_002 (2026-11-20): `RefsCheckpointVolume` hands `MsFlushVolume`
a 0x20-byte payload {FirstUsn, NextUsn, wrap base, wrap size} and `MsGetCheckpointPayload` returns it at mount, but
"where the payload is stored in the checkpoint record is not read (open question Q46)"; disk NOT_TESTED.

**What is true.** The payload is the area: on 26100.9818 `CmsVolume::Flush` passes the span to `CmsVolume::Checkpoint`,
which hands it to `FormatCheckpointRecord` (the +0x88 / +0x8C pair, E159) and compares it with the previous record's
area (`refs.decomp.c` :6436-:6473); `RefsCheckpointVolume`'s span is VCB+0x398 / +0x3A0 / +0x3C8 / +0x3D0
(:445370-:445414). On the disk (124 ReFS volumes, both copies): +0x08 (NextUsn) equals the journal's next USN (its last
record's USN + the record's length) on 66 copies of 33 volumes; on the two wrapped journals (`winsider`, `winsiderv2`)
+0x00 (FirstUsn) equals the first record's USN, +0x10 (wrap base) is a multiple of the ring's length and +0x18 (wrap
size) the ring's length (0x2000000), the driver's `RefsFileOffsetFromUsn` mapping placing the oldest record just past the
write head; +0x00, +0x10 and +0x18 are 0 on every journal that has not wrapped. On 6 volumes the journal holds 2,353
to 43,734 records at or past +0x08 (written after the last checkpoint the image holds). The area is zero on all 126
copies of volumes without a journal. 44 copies carry no area (+0x8C = 0): 38 of journal-less 3.14 volumes, and 6 of
three volumes captured mounted or rebuilt (`labEnotdetached`, `labFbeforereboot`, `labM_after_rebuilt`), consistent with
MD_USN_SA_002's condition (the payload is passed only by some calls); there the checkpoint does not say where the
journal stood.

**Scope.** Static: 26100.9818 for the storage link; the payload's fields and condition as MD_USN_SA_002 reads them
(seven builds). Disk: the census above (3.4 to 3.14 volumes). **Amends** E159; closes Q46; register MD_USN_SA_002 disk
CONFIRMED, FS_CHKP_RA_005 and FS_CHKP_RA_012 (their content); master §A.4 (+0x88 / +0x8C).

**Amended the same day (RUNNING_LOG N669, the Y trace).** The 38 above are copies: both copies of 19 journal-less 3.14
volumes (`chkp_payload_usn.jsonl`); the 6 are both copies of the three volumes named.

**Amended again before release (2026-11-22, RUNNING_LOG N670, RC3b D2).** The 6 volumes whose journal holds records at
or past +0x08 hold no record written after the last checkpoint. All six (`win11refs8g`, `labFafterreboot`, `labG_0`,
`labG_1`, `labG_2`, `win11afterblindaudit`) carry a re-created journal: the records past +0x08 belong to the earlier
instance, numbered from USN 0 again, which the dev tool's journal-instance split names (`_usn_journal_state`; on
`labG_0` USN 0 to 11,904 are the current journal, whose last record ends at 12,016 = +0x08, and USN 12,288 to 4,439,864
the earlier one). Counted against the current journal's records only, no record lies at or past +0x08 on any of the
40 corpus volumes whose checkpoint copy in use carries the area (`RC1D/rc3a/rc3b/d2_cursor_census.py` / `.tsv`). On the
corpus, +0x08 is the current journal's next USN as of the checkpoint. Corrects: register MD_USN_SA_002 (disk note),
master §C.13 (the change journal's cursor), `structures/chkp.md`.

<a id="e171"></a>
## E171 (1.14.0, RC3a; filed 2026-11-21, amended the same day before any release (the second round: six builds, three answer keys, the copy case); RUNNING_LOG N645, N648; closes N178 and the D14 timestomp bundle's M4; `analysis/reports/v1.13.2/D14/critic/timeline.md` 7.1; `RC1D/rc3a/disk/{stomp_si_records,si_records,stomp_vs_key,stomp_vs_usn,si_transitions}.py` and their outputs under `RC1D/rc3a/disk/si/`; KNOWLEDGE_INTAKE A185, A186) — a call that sets a file's times is in the MLog as its own record, with the whole `$SI` it wrote

**What was said.** Register MD_TS_RA_009: "A backdated $SI write leaves NO MLog transaction of its own -- the log
records the file's creating transaction, not the SetFileTime"; the timestomp pages: "The log does not record the stomp;
the evidence is the file's creation"; `what_survives.md` and the survival diagram: prior state comes "never from log",
"do not look in the log for prior values".

**What is true, the driver.** On every symbolled build held (17134, 26100.8115, .9444, .9818, Insider 29574, 29683)
`RefsSetBasicInfo` stores the times the caller gives in the FCB, then `RefsUpdateStandardInformation` builds the whole
`$SI` from it (`RefsComputeStandardInformationFromFcb`) and `RefsSetStandardInfo` writes it as the file table's root data
(`RefsPartialSetStandardInfo(.., 0, 0x7c)`, 0x74 bytes on 17134; Insider inlines it) through `MsUpdateDataWithRoot`;
`CmsBPlusTable::UpdateDataWithRoot` logs `AddRedoRecord(.., 4, ..)` (26100.9444 `refs.decomp.c` :404335, :389154,
:157096, :140020, :118236; the same chain on the five others, read by script). The change time: when the caller sets
Created, Modified or Accessed and leaves the change time 0, `RefsSetBasicInfo` sets it to the system time
(`KUSER_SHARED_DATA` +0x14, read once at the call's start, :404223); a change time the caller gives is stored as given;
-1 leaves it (the same rule on 17134 and Insider 29574). So each call is one redo 0x04 on the file's table -- keyed on its
name row in its directory's table, or on its backing row (0x80000040 / FileID) for a split file -- carrying the whole
`$SI` after the call.

**What is true, the disk (three answer keys).**
- `lab314_main` (test T15, `xlab.ps1`): all seven calls are records of their own, after the file's creating record: the
  five stomps (Created, Modified, and Created, Modified, Accessed of `stomp_both.bin`), the Created set through a hard
  link's name (on the shared backing row), and the Modified set to 2024-01-01 of `rounded.bin`; each record's change time
  equals, to the 100 ns, the Changed time the lab's own inventory (`Inventory_RefsVolume.ps1`, run on Windows after the
  session) reports for the file: stomp_created.bin 17:02:14.7783590, stomp_modified.bin 17:02:14.9363254,
  stomp_both.bin 17:02:15.1134902, linked.bin / linked_alias.bin 17:02:15.2574271, rounded.bin 17:02:15.4402930.
- `win11refstestmftecmd` (the generator's four replay logs on the ReFS volume): 186 SET_TIMESTAMPS, three .NET calls
  each; all 186 have their three records, each carrying the forged values to the 100 ns; each record's change time is 0
  to 28 ms before the generator's own log time (median 0.0 ms), never after; and on the three replays the USN journal
  covers, 336 of 336 records have a BASIC_INFO_CHANGE record of the same file whose time equals the record's change time
  to the 100 ns.
- `win10refs2tspecials` (format 3.4, a 116-byte `$SI`): the same 74 forged values replayed, all present, and 23 more
  Created sets of an original run of the generator (its forged value keeps the call's time of day).

**The copy case.** A plain copy ends with the source's Modified and change time and a new Created: on `lab314_main`
`copied.bin` (`Copy-Item` of `control.bin`) holds the source's Modified and change time, both older than its own
creation; on `win11refstestmftecmd` every copy of the generator (.NET `File.Copy`) moves Modified and the change time
back together (202 updates); the inventory of `lab314_main` shows the same for a copied drivers folder
(`copydrivers\drivers\1394ohci.sys`: Created 17:07:50, Modified 2024-09-06 and Changed 2026-06-09, the source's).
`robocopy /MOV` (T20) sets all four of the source's times on the destination, the change time included. So a record's
change time is the moment of the call when the program leaves it to the driver, as SetFileTime and the .NET setters do;
after a plain copy or a robocopy copy it is the source's, older than the destination's own creation. A program that sets
Created, Modified or Accessed and leaves the change time to the driver -- an installer extracting files, a script --
leaves the same record as a stomp, whatever its purpose.

**What it does not say.** The record shows that a call set the times, to what, and (as above) when; not why. On
`winsider` (the C: drive of a Windows Server Insider machine, no planted stomps) the log's window holds 957 updates that
set a file's Created and 2,275 that set Modified or Accessed back while the change time moved forward: Windows servicing
and application updates extracting files with their package dates. The creating record keeps a file's first times, so
the comparison MD_TS_RA_009 describes still holds, and more generally a file's earlier records, while the log keeps
them, hold the values they wrote: the log has no undo records, not no earlier values.

**Scope.** Static: the six symbolled builds above. Disk: three volumes with answer keys (3.14 and 3.4) and one real
Windows volume for the base rate. A caller that sets the change time itself through the native API was not tested on the disk;
the driver stores the value given (above). The log is a ring: a record exists only until it is overwritten. **Corrects** register
MD_TS_RA_009 and the pages that repeat it; new rows MD_TS_RA_010 (the copy case) and MD_TS_RA_011 (the base rate). The
tool's MLog row time takes the first FILETIME of each record, Created for a `$SI` value, so a stomp record's row is dated
by the forged value (N646, a tool change).

<a id="e172"></a>
## E172 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N655; X13; `RC1D/rc3a/disk/ot_key_census.py` and `ot_key_census.json`) — the Object Table's key is 16 bytes, the OID its low half at +0x08

**What was said.** Master §B.3: "Key — 8 bytes | 0x00 | 8 | Object ID (OID) | u64"; `docs/concepts/object_ids.md`: "an
8-byte key (the OID at offset 0x00)"; `docs/concepts/oid_allocation.md`: "whose 8-byte key *is* the OID" (twice).

**What is true.** The key is the 128-bit identifier, 16 bytes: +0x00 its high half, +0x08 its low half, the OID.
`CmsObjectTable::ConstructObjectRecord` sizes the row's key 0x10 and copies both halves into it (26100.9444 :134488-134496;
17134 :2062-2090), and `DeleteIdentifier` deletes by a 0x10-byte key (26100.9444 :232393-232397; 17134 :197457-197460).
On the disk, every row of both copies (checkpoint roots 0 and 5) on the 124 ReFS volumes of corpus.lst has a 16-byte key
whose high half is 0: 176,788 rows in 244 copies, formats 3.4 to 3.14 and the hand-edited version images. One copy reads
otherwise: the second copy of `win11refs2tmillionsofactions` (its four images) holds 240 rows with 4- to 66-byte keys beside
107 of 16 bytes, rows of another shape on the pages it reaches (that image's checkpoint roots 7, 8 and 0xC fail their
digests); its first copy is clean (307 rows). Register FS_OTBL_001 ("16 bytes: 8-byte padding + 8-byte OID") and
`docs/structures/object_table.md` already said so. **Corrects** master §B.3 and the two concept pages.

<a id="e173"></a>
## E173 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N655; open question Q44 (resolved); amends E155; `RC1D/rc3a/disk/{oid_counter,oid_reuse_usn,oid_above_max_usn}.py` and their outputs) — the OID counter is stored in the Object Table's root by the 26100 and Insider drivers; the 17134 driver re-derives it at each mount, so "never reused" holds by the stored counter, not on every driver

**What was said.** Register FS_OTBL_RA_006: "OIDs are NEVER reused after deletion (DeleteIdentifier never decrements
counter)"; FS_OTBL_SA_009: the no-reuse behaviour "is established on disk (gaps equal deletions) and by
GenerateIdentifier's atomic increment"; master §F.5 and the pages (object IDs, OID allocation, Object Table, deletion
recovery, the workflow, the home page): OIDs are "never reused after deletion", without a driver scope;
`docs/concepts/README.md`: "not reused below the highest one issued".

**What is true, the driver.** `GenerateIdentifier` sets the Object Table's dirty flag (+0x20) each time it draws an id
(26100.9444 :232607), and at each checkpoint `CmsVolume::PersistCheckpointCaches` writes the table's 24 bytes at +0x08 (a
u64, then the 128-bit counter: high half, low half) as the Object Table's root data when that flag is set, then clears it
(:55479-55490; the same write on every other symbolled build held: 26100.8115 and .8521 :82355-82359, .8972, .9549,
.9711 and .9818 :55479-55483, Insider 29574 :106990 (the table at volume +0xD50), 29659 :144642-144652 (+0xD10), 29683
:112182; 26100.9974 has no symbols and was not read). At mount `InitializeTable` reloads them when the root data's first u32 is not 0, then raises the counter
to the table's largest key (E155's update). 17134 neither writes nor reads that root data (no Object Table root-data
writer among its `UpdateDataWithRoot` callers): at each mount its counter is the table's last key, 0x500 when lower,
then 0x700 (E155, update of 2026-11-21). After a crash the log replay keeps the counter above every directory it recreates: `InstantiateTableForRedo` keeps
the largest object id it creates, plus one, in the restarter (+0xD0 / +0xD8; 26100.9444 :251041-251067), and `RedoPass`
and `Restart` pass it to `SetMinimumNewObjectId` (:253799, :255290); one reading, 26100.9444. So on 17134, after a remount, the next directory gets the largest live OID + 1:
a deleted directory whose OID was above every live one has its OID issued again. That is read in the driver and not
measured: no 3.4 volume of the corpus has a change journal.

**What is true, the disk.** The Object Table root's data (the root page's +0x50 + the descriptor's 0x28, 512 bytes) on
the 124 ReFS volumes of corpus.lst: on all 112 volumes of 3.10 and later, both copies hold {1, 0, the counter}; the
counter equals the largest OID in the table on 99 and is above it on 13. On the 6 of those 13 with a change journal, each
OID between the two is a directory the journal shows created and deleted (7 of 7: `_selftest`, `_probe`, `t_dir`, the
lab scripts' own probes); on `win11refs2tmillionsofactions` the counter is 1,509 above. On the 12 volumes of 3.4, 3.7 and
3.9 the 512 bytes are zero (the 3.7 and 3.9 drivers were not read). `win10to11refs4g` holds zero before its first 26100
mount and {1, 0, 0x740} after it. Over the change journals of the 42 corpus images that have one (all 3.14), no directory
OID is created again after a delete of the same OID: 0 of 13,907 deleted directory OIDs, counted per image (winsider
alone 6,919 of 9,833).

**Scope.** Static: 17134 and every symbolled 26100 and Insider build held (26100.8115 to .9818, Insider 29574, 29659, 29683). Disk: corpus.lst as above. Not measured: a
re-issued OID on a 17134-written volume (it needs a 3.4 lab: a top directory deleted, a remount, a new directory); a gap
from a failed creation (E155). One case follows from the two readings: on a volume upgraded from 3.4, the first mount by
a 26100 driver finds no stored counter and starts from the largest live key, so the OIDs of directories deleted above it
under 17134 can be issued once more; the counter is stored from then on (win10to11refs4g: zero root data before that
mount, {1, 0, 0x740} after). **Corrects** FS_OTBL_RA_006, FS_OTBL_SA_009 and the pages listed above; the
deletion-evidence reading of a gap below the largest live OID is unchanged on every driver.

<a id="e174"></a>
## E174 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N656; W2a; the static readings S7; `RC1D/rc3a/disk/heat_table.py` and `heat_table.json`, `heat_table_disableheat.json`) — OID 0x30 is the heat engine's table of I/O metrics by 10-minute generation (schema 0xe130), not a "Session Activity Table" of mount sessions

**What was said.** Register FS_OTBL_RA_001: "OID 0x30 = Session Activity Table ... Stores per-mount-session IO/allocation
statistics. Key: FILETIME + sub-ID", its static note "RefsTelemetryPerfCountersWorker references OID 0x30 session
table"; FS_SCHM_RA_004: schema 0xe130 "Always 0 rows on test volumes"; master §F.1 (0xe130 "Block tier classification
(hot/warm/cold)"), §F.4, §H.2 and §N ("Session Activity Table", "Static analysis correlation
`RefsTelemetryPerfCountersWorker`"); the pages (system OIDs, version evolution, tiering, the tool-artifact map, the
baseline images): "mount-session history", "per-mount-session activity records"; `docs/concepts/tiering.md`: the table is
independent of heat tracking, "do not treat one as a proxy for the other", and 0xe130 has "0 rows on every test
volume"; refsanalysis `oid30`: "Sessions", sub-IDs "Session summary", "IO counters", "Category A-H".

**What is true, the driver (26100.9444; the same functions on every symbolled 26100 and Insider build, none in
17134).** `CmsVolumeHeatEngine::Initialize` creates object 0x30 with schema 0xe130 (:246577-246591; the one creator,
S7), from `CmsVolume::Start` (:214325). `MspVolumeHeatSnapshotWorker`, a periodic work item, loads the persisted entries
on its first run, then snapshots a generation every period (:247023-247039); `Shutdown` snapshots one more.
`SnapshotAndProcessUpdateGeneration` reads the system time (`KUSER_SHARED_DATA`+0x14) as it opens a generation and
persists the closed one only when I/O was tracked in it (:247780-247796). `Persist` (:247083-247240) writes, per
generation, a 44-byte row per tracked container and direction (`SmsPersistedContainerMetrics`: +0x00 the generation,
+0x08 the container x 2 + the `RWType` bit, +0x10 / +0x18 two counters, +0x20 the offset 0x28 and +0x21 the size of a
32-bit map at +0x28) and two 80-byte rows (+0x00 the generation, +0x08 0 or 1, seven u64 of the generation's totals,
+0x48 0), then adds 1 to the root data's u32 +0x04; `TrimPersistedEntries` deletes the oldest generations while that
count is above the maximum (:247894-247990). The defaults, when the volume's parameters are 0 (`CmsVolume::Start`
:214312-214324): a 600-second period and a 432,000-second window, so at most 720 generations. The key is the value's
first 16 bytes. `RefsTelemetryPerfCountersWorker` does not touch object 0x30 (S7). Which `RWType` value is read and
which write was not read.

**What is true, the disk (124 corpus.lst volumes).** Object 0x30 is on all 112 of 3.10 and later and none of the 12 of
3.4, 3.7 and 3.9; its root's schema is 0xe130 on all 112. On all 112, the root data's u32 +0x04 equals the number of
distinct generations (0 on 16, whose table is empty; N664), each generation has exactly two 80-byte rows (second u64 0 and 1), and every key is its value's
first 16 bytes; the 44-byte rows' low bit is 0 on 17,120 and 1 on 12,846. On a volume mounted for hours the gaps
between generations are 600 s (winsiderv2: 149 of 172; the others are the remount and dismount generations); on the lab
volumes, mounted for minutes, each mount leaves about one generation, which is why they read as sessions: winsider's
"27 sessions" are 27 generations, 16 of whose 26 gaps are exactly 600 s. The volume formatted with
`-DisableHeatGathering` (`win11refs2g_disableheatgathering`, not in corpus.lst, read by name) holds 3 generations.
Not measured: the trim (the largest table held has 173 generations); the meaning of the counters and the 32-bit map.

**Corrects** FS_OTBL_RA_001, FS_SCHM_RA_004, master §F.1 / §F.4 / §H.2 / §N, the pages above, and (RC3b, tool output)
refsanalysis `oid30`'s labels and forefst's object name "SessionActivity".

<a id="e175"></a>
## E175 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N658; X39, X40; `RC1D/rc3a/disk/reverse_index_census.py` and `reverse_index_census.json`) — the type-0x20 rows: Format A for every embedded record, Format B type 2 for every backing, type 1 a forward pointer to a moved record; none for subdirectories; the names carry no terminator

**What was said.** Register FN_DTBL_003 and master §C.5: Format A "for split-record files" / "created for non-resident
child names"; Format B "for subdirectories + cross-dir links", "type_flag = 1 on v3.4 / = 2 on v3.7+", "home-directory
back-reference"; master §C.5: "One row per child"; `docs/structures/reverse_index.md`: Format A's name "null-terminated",
its length "including null terminator"; "v3.4: the back-pointer points at the REAL parent directory OID"; "Files whose
record is embedded in its name row ... typically lack type 0x20 entries" (beside "Format A for an embedded record").

**What is true, the disk** (every object table of OID 0x600 and above on the 124 corpus.lst volumes: 87,099 tables,
733,667 type-0x20 rows, joined by ordinal within the table):
- Format A (type 0): one per embedded record, keyed by its ordinal (the record's value+0x80): 623,439 of 623,439
  embedded records have one; the other 65 Format A rows are on two odd volumes (the `win11refs2tmillionsofactions`
  capture, 16 per image, whose checkpoint roots fail their digests; `labM_after_rebuilt`, 1).
- Format B type 2: one per type-0x40 backing, self-referencing (value+0x08 = the key's ordinal, value+0x10 = the table's
  own OID): 109,754 rows for 109,754 backings, 260 of 260 self-references checked on three volumes.
- Format B type 1: a forward pointer, on a volume without hard-link support, for a record that a cross-directory move
  carried out of its home directory: it sits in the home directory, keyed by the file's home ordinal; value+0x10 is the
  directory now holding the record (409 of 409 rows, on the 8 images that hold the corpus's 409 moved records,
  KNOWLEDGE_INTAKE A145), value+0x08 the record's ordinal there (407 of 409; on `labM_after_rebuilt` the 2 rows read one
  more than the record's value+0x80, not explained).
- Subdirectories have none: 0 of 12,623 subdirectory entries.
- A home directory whose files were moved out keeps their type-1 rows, so it can hold more type-0x20 rows than names
  (15 of 34 directories on `win10refs110g`, 32 of 149 on `win10refs2tspecials`): the page's "on every directory
  measured, the type 0x20 count is <= the type 0x30 child count" does not hold there.
- Format A's name length (value+0x0A) counts the name only: 0 of 623,504 names end in a NUL inside it (name offset 12 on
  all); the two zero bytes after the name on 300,916 rows are the value's padding.

**What is true, the driver.** `RefsCreateFileId2` writes Format A from the name key when it is given one and Format B
(24 bytes: the type, then the file reference) when not; 26100.9444 sets the type to 1 + (its fifth argument != 0)
(:486069-486141): `RefsLinkFileToSelf` passes 1 with the object's own reference (type 2, :191999), `RefsCreateFile`
writes Format A for a new file after creating its table (:69127), `RefsMoveFile` writes Format A rows and one Format B
(:192175-192318). 17134 hard-codes type 1 (:246643-246700); its callers are `AllocateForNewFile`, `RefsMoveFile` and
`RefsReconcileFileIds`. So the type is not a format version: 1 is the moved-record pointer, 2 a backing's
self-reference.

**Corrects** FN_DTBL_003, master §C.5 and `docs/structures/reverse_index.md` (the Format A table, the Format B and
Coverage sections, and the count rule).

<a id="e176"></a>
## E176 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N660; X35, the review R5's item (6); `RC1D/rc3a/disk/integrity_state_rows.py` and `integrity_state_rows.json`) — the Integrity State Table is an allocator: its rows are allocator rows, and "State 0x0002ffff" is a saturated free count with the flags

**What was said.** Register CT_INTS_001: "Value=24B [u64 start_lcn(dup), u64 block_count(dup), u32 state_field, u32
config_field] ... default [0x0002ffff, 0x00000100] ... 3 rows — 1 container has modified state [0x00013f6c,
0x00000118]", "Row format invariant: Key=16B, Value=24B"; `docs/structures/integrity_state.md`: "Value format — 24
bytes", "State (u32)", "Config (u32)", "0x0002ffff likely represents the default/clean state", the block count
"container count x clusters-per-container".

**What is true, the driver (26100.9444).** `CmsIntegrityState::Initialize` builds the table as a `CmsAllocator`
(`CmsAllocator::MakeAllocator`, `InitializeAllocator` with schema 0xe080, table id 0xF, the root at checkpoint root 11;
:283449-283520); `Extend` is `CmsAllocator::Extend` (:283395-283400) and `GetRangeBitmap` walks it with
`CmsAllocator::WalkAllocator` (:283430-283445). Its rows are therefore the allocator rows of master §B.2 (E74).

**What is true, the disk (124 corpus.lst volumes, every row of root 11).** Read in the allocator frame: +0x10 u16 free
count, +0x12 u16 flags (bit 0 = a bitmap row), +0x14 u8 bitmap offset, +0x15 u8 format byte, +0x16 u16 hint. 126 rows
are compact (24 bytes, flags 0x2, bitmap offset 0, format 1, the whole range free): 124 read 0x0002ffff / 0x100 as two
u32, i.e. a free count saturated at 0xFFFF; the two of `lab314_64k` (64,512 clusters, below the saturation) read
0x0002fc00, the volume's own count. 2 rows are bitmap rows of 2,072 bytes (0x18 + 2,048 bitmap bytes; flags 0x1, offset
0x18): 16,384 clusters each, 148 bits set, free = length - popcount on both, on the two large 3.4 volumes
(`win10refs110g`, `win10refs2tspecials`), between two compact rows. On all 124 volumes the rows cover [0, the boot
sector's cluster count) without a gap; 122 hold one row. What a set bit means is not decoded.

**Corrects** CT_INTS_001, master §B.7 (its value description) and `docs/structures/integrity_state.md`.

<a id="e177"></a>
## E177 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N665; the U round's static readings, `analysis/reports/v1.13.2/RC1D/rc3a/u/U_STATIC_READINGS.md` (U29, U31, U45), spot-checked by the lead against the decompilations) — the driver's imports serve EFS and the soft restart, SymCrypt serves Insider's volume attestation, and redo-record flag bit 16 has no writer

**What was said.** Master §G.8 (the Win11 import table): `ext-ms-win-ntos-ksr` "memory persistence across soft
reboots", `msrpc.sys` "Kernel-mode RPC (clustered storage communication)", `ext-ms-win-crypto-xbox` "Hardware-
accelerated crypto", `ext-ms-win-ntos-clipsp` "Client License System Policy", the counts as the v3.14 driver's; register
GN_IMP_SA_001 "v3.14=566 (7 libraries)"; GN_INS_SA_003 "Embedded SymCrypt (153 funcs) for early boot + MinCrypt (57
funcs) for certificate chain validation before CNG.sys available"; master §E (the `_SmsRedoRecord` table): +0x2C "flags
(bit0 txn-start, bit1 commit, bit16 special)" CONFIRMED.

**What is true.**
- The counts are per build (PE import directories): 17134 415 from 2 libraries; 26100.8115 566 from 7; 26100.9444 and
  .9818 567 from 7; Insider 29574 564 and 29683 572, each from 6 (no xbox-crypto library).
- What each 26100 addition is called for (26100.9444, every caller read): ksr keeps each mounted volume's container-
  table state (not on an SMR disk) in memory across a kernel soft restart, for the next mount to reuse
  (`RefsKsrSaveContext`, `CmsVolume::Start` → `MsKsrRestoreVolumeContext`); msrpc carries EFS's calls to its user-mode
  service (`EfsKRpcDecryptFek`, `EfsKRpcGenerateKey`, `EfsKRpcGenerateDirEfs`, the enterprise-file notifications); the
  xbox-crypto library is an alternative EFS XTS-AES key and decryption provider used when `XboxCryptoSupported()`
  (`EfsXtsAesEnc` refuses its key type, so it never encrypts); clipsp loads the license callbacks EFS uses for
  file-license headers and keys (`EfspCreateFileLicenseHeaderAndKey`, `EfspClipSpDecryptFek`). No clustered-storage,
  checksum or edition code calls them.
- SymCrypt (153 functions) is in Insider 29574, 29659 and 29683 and in no 17134 or 26100 build read. On 29574 its
  callers are the volume attestation's HMAC-SHA256 of checkpoint and log records (`ComputeCheckpointRecordHmac`,
  `Compute/VerifyLogRecordHmac`) and MinCrypt's PKCS#7 / RSA checks of attestation certificates and PCR measurements,
  reached at mount (`ReadLatestCheckpoint` → `AttestVolume`), at checkpoint, at log write and from an FSCTL. "Early
  boot" and "before CNG.sys is available" are not shown by the code.
- Redo-record +0x2C: bit 0 transaction start and bit 1 commit (`CmsMemLog::MergeTxLog`); bit 2 on the first record of a
  block merged into the previous one; bit 12 or 13 on a transaction's first record (the argument that chooses is not
  traced); bit 16 has a reader in 17134, 26100.9444, .9818, Insider 29574 and 29683 (`CmsLogRedoQueue::RedoOneRecord`
  drops the record's last value and clears the bit) and no writer was found in those builds.

**Scope.** Static only: the builds named. Re-checked by the lead: the import counts by an own PE parse of the four
binaries (17134, 26100.8115, .9444, Insider 29574), the msrpc binding (`EfsRpcInit`, 26100.9444 :454939), the SymCrypt
function counts (0 on 17134 and 26100.9444, 153 on Insider 29574 and 29683) and the bit-16 reader (26100.9444
:253454-253457). **Corrects** master §G.8 and the §E `_SmsRedoRecord` +0x2C row, register GN_IMP_SA_001
and GN_INS_SA_003, `docs/concepts/driver_architecture.md`, `docs/structures/mlog.md`.

<a id="e178"></a>
## E178 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N665; the U round, U57: `analysis/reports/v1.13.2/RC1D/rc3a/u/U_STATIC_READINGS.md` U57, re-read by the lead at 26100.9444 :483918-483958 and :427024-427032; `u/u_disk2.py` and `u_disk2.json`) — the volume-information row keyed 0x540 locates the verify block, a cluster that holds a copy of the 448-byte volume-information blob: the prior work's "backup block", not a schema count and flags

**What was said.** Master §F.4b: key 0x0540, "16 bytes | Schema count (u32 at +0x00, typically 35) + flags (u32 at
+0x04) | CONFIRMED", and §F.4 (OID 0x500) "Volume label, timestamps, schema count"; register FS_VINF_003 ("Backup block
row (key 0x540)", prior work) disk_status CONTRADICTED, its note: "disk shows key 0x540 in OID 0x500 = schema count (35)
+ flags ... There is no 'backup block' here"; `docs/attributes/VOLUME_INFORMATION.md`: "schema count (u32) at +0x00,
flags (u32) at +0x04, a u32 (=1, purpose unknown) at +0x08".

**What is true, the driver.** `InitializeVerifyBlock`, called by `RefsMountVolume` (26100.9444 :427030), reads the row
with the 8-byte key 0x540 of the volume-information table (VCB+0x68; :483920-483924). The value must hold at least 0x10
bytes (else 0xC0000012). +0x00 is a u64, kept as the block's first cluster (VCB+0x1D0); +0x08 is a u64 cluster count,
1 to 2^32 - 1 (else 0xC0000032). On a writable mount the driver fills that many clusters with the 0x1C0-byte volume-
information blob (`RefsGetVolumeInfo`) and writes them at +0x00 << the cluster shift ("Verify block at sec 0x%llx
write failed" on a failure). 17134 (:268372-268420) and Insider 29574 (:496017-496049) do the same. No driver writer of
the 0x540 row was found.

**What is true, the disk (the 124 ReFS volumes of corpus.lst).** +0x00 = 0x23 (35, the "typically 35") and +0x08 = 1
on all 124, with 4 KiB clusters (117) and 64 KiB (7). The cluster at LCN 0x23 begins with the key-0x520 row's 448
bytes: equal on 89 volumes, and on the other 35 different only at +0x82 to +0x84 (the driver-version bytes a writable
mount writes; which write comes last in a mount was not read); the rest of the cluster is zero on all 124.

**Scope.** Static: 17134, 26100.9444, Insider 29574. Disk: 3.4 to 3.14 volumes. Not read: what reads the block back
(`RefsScrubVerifyBlock`). **Corrects** master §F.4b (the 0x0540 row) and §F.4 (OID 0x500's "schema count"), register
FS_VINF_003 (CONTRADICTED withdrawn: the prior work's "backup block" holds), `docs/attributes/VOLUME_INFORMATION.md`.

<a id="e179"></a>
## E179 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N665; the U round, U56: `analysis/reports/v1.13.2/RC1D/rc3a/u/U_STATIC_READINGS.md` U56, re-read by the lead at 26100.9444 :132063-132086; `u/u_disk2.py`, `u/u56_probe.py`, `u_disk2.json`) — an `$OBJ_LINK` name has no terminator, and the 3.4 row's +0x3C / +0x44 / +0x4C are two sizes and the object's attribute word

**What was said.** Master §C (the `$OBJ_LINK` value format, v3.7+): +0x18 "Null-terminated primary filename";
`docs/attributes/OBJ_LINK.md` (the 3.4 value): +0x3C "File attributes (4)", +0x4C "Flags word 0x10000006", the name
"UTF-16LE, null-terminated".

**What is true.**
- 3.7 and later (type 0x39): on all 312,797 rows of the 124 corpus.lst volumes the name runs to the end of the row and
  ends with a character, not 00 00; `key[0x20:] == value[0x18:]` and value +0x0C..+0x17 is zero on all of them.
- 3.4 (type 0x38): the 17134 writer (`RefsAddLink` / `RefsAddNameToParent`, :242794-242854) fills the 0x52-byte block
  from the FCB: +0x1C..+0x3B the four times, +0x3C (u64) and +0x44 (u64) the values it also writes to `$SI+0x38` and
  `$SI+0x30`, +0x4C (u64) the attribute word with the directory bit, then +0x54 the name length, +0x5A 0x30, +0x5C 2
  for a directory; the row's length ends at the name. On the corpus's 373 type-0x38 rows +0x3C and +0x44 are 0 (all
  on directories), +0x5A is 0x30 and +0x5C 2 on all, and +0x4C equals the record's `$SI` attributes with the directory
  bit on 363; the others are the root directory's `.` row on nine images of 17134-formatted volumes, whose +0x10..+0x51
  hold other bytes, and one directory whose `$SI` carries bit 0x8000 that +0x4C lacks. The value ends at the name on 100
  rows and 2 to 6 zero bytes follow it on 273: the "null-terminated" reading was that padding. 0x10000006 is one
  object's attributes (a hidden, system directory), not a constant.
- The 26100.9444 writer of a 0x38 row (`RefsBackpointerValueFromFileName`) zeroes the block between the parent
  reference and the name and writes no terminator either; no row it wrote was identified on the corpus.

**Scope.** Static: 17134, 26100.9444. Disk: the 124 corpus.lst volumes (0x38 rows on the 3.4 volumes and the one volume
upgraded from 3.4). **Corrects** master §C (`$OBJ_LINK` +0x18), register MD_LK_RA_008 ("file_attrs at
val[0x3C]"), `docs/attributes/OBJ_LINK.md`.

**Amended the same day, before any release (RUNNING_LOG N669, the Y trace).** "On the corpus's 373 type-0x38
rows +0x3C and +0x44 are 0" holds on 364 of them (register MD_LK_RA_008, `u_disk2.json`): the nine root `.` rows named
above hold other bytes in +0x10..+0x51, these fields included. On the volume upgraded from 3.4, its 32 type-0x38 rows
are byte-identical before and after the first Windows 11 mount (`RC1D/rc3a/y/ym2_objlink_upgrade.py`, .json; two
directories of the earlier image are not in the later one).

<a id="e180"></a>
## E180 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N666; the V round, P1: `analysis/reports/v1.13.2/RC1D/rc3a/v/V_NOTES.md`, `v/p1_census.py`, `p1_census.json`, `v/v2_followup.py` (d), `v2_followup.json`) — a page header's +0x10 is the checkpoint virtual clock and +0x18 the volume's count of tree updates since the last checkpoint

**What was said.** Master §A.2: +0x10 "Virtual allocator clock"; +0x18 "Tree update clock: Last modification clock for
this page's table". Register GN_PAGE_004 ("virtual allocator clock") and GN_PAGE_005 (a "per-tree modification counter");
`docs/structures/page_header.md`.

**What is true.**
- `CmsVolume::FormatPageHeaderInternal`, which builds every MSB+ page header, writes +0x10 from the volume's checkpoint
  virtual clock (26100.9444 :94211, `GetCurrentCheckpointVirtualClock` = CmsVolume+0x7f0; 17134 `FormatPageHeader`
  +0x670; Insider 29574 +0x840): the field `FormatCheckpointRecord` stores at CHKP +0x60 (26100.9444 :216644, 17134
  :58299, Insider :193771) and `ReadLatestCheckpoint` reloads from it. The allocator clock is another field (CHKP +0x68:
  +0x7f8 / +0x678 / +0x848).
- It writes +0x18 from `GetCurrentTreeUpdateVirtualClock` (+0x800 / +0x680 / +0x850). `CmsBPlusTable::UpdateBoundTrees`
  raises that field by 1 on a tree update without the checkpoint bit and, on a checkpoint, raises the allocator clock and
  the checkpoint clock and sets it to 0 (26100.9444 :98611-98676; 17134 :85952-85971; Insider :305291-305348). It is the
  volume's counter, not the table's, and no checkpoint field stores it.
- Disk, 166,973 distinct pages walked on the 124 corpus.lst volumes: +0x10 is at most the chosen checkpoint's +0x60 on
  all (equal on 5, all on labFbeforereboot, captured mounted); +0x18 is above the checkpoint's +0x68 on 42,566. On
  win11refs2g, win10refsmini and labL_6 +0x18 is 0 on 19, 28 and 15 pages, and of the page pairs with a larger +0x10,
  1,319 of 4,260, 180 of 851 and 589 of 1,397 carry a smaller +0x18, as a counter reset at each checkpoint gives.

**Scope.** Static: 17134, 26100.9444, Insider 29574 (one reading each). Disk: the 124 corpus.lst volumes.
**Corrects** master §A.2 (+0x10, +0x18), register GN_PAGE_004 / GN_PAGE_005, `docs/structures/page_header.md`. The
superblock copies (E132) are written by `FormatSuperPageHeader` from the same two clocks.

<a id="e181"></a>
## E181 (1.14.0, RC3a; filed 2026-11-21; RUNNING_LOG N668; the Z round: `analysis/reports/v1.13.2/RC1D/rc3a/z/Z_NOTES.md`, `z/Z_STATIC_READINGS.md` (one agent, re-read by the lead at the lines cited), `z/z1_census.py`, `z1_census.json`, `z/z3_followup.py`, `z3_followup.json`) — seven "reserved / padding / always 0" fields of the master are written with data, and two layouts were mis-sized

**What was said.** Master §A.2 page header +0x08 "Reserved u32, always 0"; §A.2a node header +0x18 "0 on every on-disk
page"; §B.4 the Schema Table key "8 bytes: schema id + 4 bytes zero padding"; §C.0 the row header +0x08 "Reserved"
(NOT_TESTED); §C.0b the `$OBJ_LINK` value +0x08 "Parent OID u32" and +0x0C "12 bytes reserved"; §C.2c "All embedded
sub-record VALUES share a 12-byte header prefix: +0x00 padding, always 0"; §C.3 the directory entry +0x44 "8 bytes
padding"; §C.7 the 3.4 `$SI` +0x56 "2 bytes padding after the ReparseTag"; §C.12 the security table key +0x00 "value
size u32" and +0x04 "padding u32".

**What is true.**
- Page header byte +0x08: the volume's count of bound-tree cycles with a failed tree update since the last checkpoint,
  capped at 0xFF (`FormatPageHeaderInternal` / `FormatSuperPageHeader` write CmsVolume+0xd54; `UpdateBoundTrees` raises
  it on its abort path, `Checkpoint` sets it to 0; 26100.9444 :94225, :98939, :6182; the same pattern on 17134 +0xb80
  and Insider 29574 +0xda4). 0 on every page of the corpus (169,316 MSB+ pages, 372 SUPB, 124 CHKP copies).
- Node header +0x18: the u64 `InitializeIndexHeader`'s caller passes (:112486); non-zero on 1,770 of 169,316 pages, all
  leaves of the Block Refcount table (0x5) and the allocators 0x20, 0x21, 0x22. +0x24 is written 0 and is 0 on all.
- The Schema Table key is the 4-byte schema id: 3,614 of 3,614 rows of roots 3 and 9.
- Row header +0x08 is a u16 of flags: 0x4 = deleted (`MarkIndexEntryDeleted` / `MarkIndexEntriesDeleted`, :88911,
  :88358). Of the rows in the data areas, the 393,750 that the row-pointer arrays do not list all carry 0x4; none of the
  3,963,248 listed rows does. 0x1 is read by `CheckEmbeddedRoot` (819,898 listed rows), 0x2 is set by `AbortUndoRecords`
  (3,981). +0x0E is 0 on all listed rows.
- `$OBJ_LINK` +0x08 is a u64 (`RefsInitializeObjLinkRow` stores 8 bytes, :53579) and +0x10 a u64 written 0 (:53580);
  on disk +0x0C..+0x17 is 0 on 312,797 of 312,797 rows.
- The 12-byte prefix with +0x00 = 0 holds for the single-instance rows (563,606 inline `$DATA` rows included) and the
  $I30_INDEX / $EFS rows; an `$OBJ_LINK` row begins with its marker, the multi-instance `$DATA` rows with the
  stream-set row (sub-stream 0x8) or the extent record's embedded table (§C.6), an extent-backed `$SNAPSHOT` / ADS
  descriptor with its flags (u16 +0x02).
- Directory entry +0x44 is the object's reparse tag (`ComposeDirIndexEntry` copies `$SI+0x54`, :68287): set on the
  2,140 84-byte and 260 72-byte corpus entries whose attributes carry 0x400, and only there. In the 84-byte form +0x48 is
  a u16, the object's `$SI+0x50` capped at 0xFFFF (:68289-68293); +0x4A, written 0 in that branch, reads 4-13 on most
  3.14 entries with an EA size (their writer not traced).
- 3.4 `$SI` +0x56 is the high half of the u32 ReparseTag at +0x54 (0xA000 on the 175 tagged records), not padding.
- Security table key +0x00 is a u64, the row's value length (4,405 of 4,405); the insert call passes only the 8 bytes
  {generation, hash} at +0x08 (`RefsSecurityAddDescriptorToTable`, :458263-458268).
The other fields swept are what the master says (0 on every instance read; writer read where named): boot sector
+0x0B, +0x30, +0x58..+0x1FF (no refs.sys writer: the driver never builds a boot sector), SUPB +0x60, CHKP +0x7C..+0x87,
Container Table +0x1C / +0x9C, Object Table +0x04, the Parent-Child Table's +0x00 / +0x10, inline `$DATA` +0x10,
`$REPARSE` +0x12, the MLog control payload +0x4C..+0xE47.

**Scope.** Static: 26100.9444 (the agent's readings; the lead re-read the row flags, `RefsInitializeObjLinkRow`,
`ComposeDirIndexEntry` and the page-byte counter); 17134 and Insider 29574 for the page byte. Disk: the 124 corpus.lst
volumes. **Corrects** master §A.2, §A.2a, §B.4, §C.0, §C.0b, §C.2c, §C.3, §C.7, §C.12; register GN_IENT_004 (confirmed);
`docs/structures/page_header.md`, `btree_node.md`, `directory_entries.md`, `parent_child_table.md`,
`security_descriptors.md`, `docs/attributes/OBJ_LINK.md`.

**Amended the same day, before any release (RUNNING_LOG N669; RC3b item 14: `RC1D/rc3a/rc3b/r14_slack_flags.py`,
`r14b_slack_twins.py` and their outputs).** The deletion sets the flag. On 26100.9444 `CmsBPlusTable::DeleteFromIndex`
(:20256) calls `_SmsIndexHeader::MarkIndexEntryDeleted` (:20490), which sets row +0x08 bit 0x4, adds the row's size to
the node header's +0x08 (the free-space size), lowers the +0x04 high-water when the row was the last of the data area,
and removes the row's slot from the key index (`RemoveOffsetEntries`; :88899-88926). The mark function does the same on
17134 (`CmsBPlusTable::MmsMarkIndexEntryDeleted`, :154354) and Insider 29574 (:164985), which add the slot's 4 bytes to
+0x08 and shift the key index in place. So register FS_DEL_RA_005's and master §I's "`DeleteFromIndex` removes only the
slot" was wrong in one point: the row's bytes are not scrubbed, but the row is marked. The bit marks a row removed from
the index, by a delete or an update, not a deleted file: of the type-0x30 name rows the dev tool's slack scan recovers
from the pages the table walks read (the 124 corpus.lst volumes), the 158,043 in the data areas all carry it, and 88,634
of them have a live row with the same name and creation time; of the 106,577 in the free space past the high-water,
94,006 do not carry it (their origin not read), 68,335 of those with a live twin. **Corrects** also register
FS_DEL_RA_005, master §I, `docs/examples/find_a_deleted_file.md`; the tool's printed Method 5 header and
`_scan_page_slack`'s docstring change in RC3b, with a 7j row.

**Amended again the same day (RUNNING_LOG N669, the Y trace).** The directory entry's +0x44 was read on the 84-byte
form only (`z3_followup.py` reads values of 0x4C bytes or more): the 2,140 tagged entries are all 84-byte entries, 260
of them on 3.10 volumes, not "2,140 84-byte and 260 72-byte"; the 72-byte form was not read. Master §C.3.

<a id="e182"></a>
## E182 (1.14.1; filed 2026-11-27; RUNNING_LOG N682; `analysis/reports/v1.14.1/DATA50/FINDINGS.md`, `census_payload.py`, `census_payload.jsonl`, `census_summary.txt`, `witness_offsets.py`) — `$DATA` +0x50 is the stream's flags word: bit 31 sparse, bit 30 encrypted; its low bits are not a version count, and on 3.4 the word is at +0x28

**What was said.** Master §C.6 (MI `$DATA` sub-record header): "+0x50 (v3.4: 0x54) | 8 | Version count (low 31) +
sparse flag (bit 31) | u64", low 31 bits the stream's version count ("1 for non-snapshotted files, N for N-version
snapshotted files"), bit 31 a sparse flag "per finding #307", never observed set; register MD_DATA_RA_011 the same;
`docs/attributes/DATA.md` and `docs/structures/extent_descriptors.md` the same, the 3.4 field at +0x54. In 1.14.1 item W
(dev only, never published) the register, the master and DATA.md added that the two sparse files of
`win11refs4gattributestest2` carry bit 31 and are "the corpus's only sparse files" -- false: E114 counts 53 sparse
files, the master names `lab314_main/t18_sparse.bin`.

**What is true.**
- The value is an embedded table root: `D = value + u16(+0x04)` (0x28), and the stream's 4-byte user payload is at
  `D + u16(D+4)` in the layout 26100.x and Insider 29574 write for 3.7+ records, or at D in the other
  (`CmsStream::InitializeStreamTablePayload`, `PersistStreamTablePayloadToDataWithRoot`, 26100.9818 :109117 / :107379;
  `PersistStreamTablePayloadToDataWithRoot` is the same code on 26100.8115; on Insider 29574, :212054, it allows a
  summary up to 0x38 bytes). +0x2C reads 0x28 on every 3.7+
  record, so the word is +0x50 there; it is 4 bytes, not 8.
- Its high 16 bits are the stream's attribute flags: bit 31 is set when the stream is made sparse and cleared when it is
  made not sparse (`RefsChangeStreamSparsenessAndBlob`, :189766 / :189769, which also sets the file's 0x200 attribute);
  bit 30 when it is encrypted (`RefsEncryptStream` :401287) and cleared on decryption (`RefsSetEncryption` :403041); bit 29
  when the sparseness function's fourth argument is nonzero (:189773), which the driver passes only on a volume on SMR
  storage (`RefsSetFileStrictlySequential` :423292, `RefsReplaceDataAttribute` :395935; amended 2026-11-28 after an
  independent second reading, `DATA50/FINDINGS.md` section 2.4). The same writes on 26100.8115 and Insider 29574.
- On the corpus (124 ReFS volumes, every `$DATA` row of every file record): 166,950 current streams of 3.7-3.14 and 144
  snapshot versions; bit 31 set on exactly the 130 records (25 images) whose file carries the sparse attribute; bit 30
  on exactly the 33 (12 images) whose file carries the encrypted attribute; bit 29 and every other high bit on none. The low 16 bits are 1 on every record, snapshot versions included. The writers read set byte 0 to 1 at creation
  and none changes it: the low bits are not decoded, and "version count" is withdrawn (the June 2026 census's 16 values
  other than 1 are not found again; its script was not kept).
- 3.4: the 17134 driver keeps the word first (`RefsChangeStreamSparsenessAndBlob` rewrites 0x2C bytes from D, the flags at
  D+2, :172946; `MsFindEmbeddedDataWithRoot` :17386): +0x28 reads 0x00000001 on all 2,638 records of the 3.4 form (8
  volumes 3.4, 3 upgraded volumes keeping the 3.4 key), and +0x50 / +0x54 read 0 on all. No 3.4 volume holds a sparse
  or encrypted file: on 3.4 the bits rest on the driver alone.
- Witnesses (read back at their file offsets): `win11refs4gattributestest2.raw` sparse.dat +0x50 at 0x10306c8 =
  `01000080`, encrypted.txt +0x50 at 0x3c04d98 = `01000040`; `win10refs110g.raw` IndexerVolumeGuid (3.4 form) +0x28
  at 0x1030820 = `01000000`, +0x54 at 0x103084c = 0 (re-read 2026-11-28; the register cites the same).

**Scope.** Static: 26100.9818 (the lead), the same functions on 26100.8115 and Insider 29574, 17134 for 3.4. Disk: the 124
corpus.lst ReFS volumes; on the four `win11refs2tmillionsofactions` images 6 metadata pages are holes in the image file
and their records are not counted. No tool reads the field. **Corrects** master §C.6; register MD_DATA_RA_011;
`docs/attributes/DATA.md`, `docs/structures/extent_descriptors.md`; the retired readings are 7j rows.
