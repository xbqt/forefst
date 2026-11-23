# Knowledge Map — where every ReFS fact lives

**This page is an index, never a source.** Every fact it points at is stated on the page or in the
claim register; nothing is documented only here.

It is **repo-only**: it is not published to the website, is not in the site menu, and no finding id it
contains ever reaches a reader — the site's leak gate stays absolute and has no exemption. Its audience
is someone auditing the documentation against the evidence. A reader wanting the narrative starts from
the [documentation index](README.md).

Its purpose is **drift detection**, in the two directions prose cannot read:

1. **I am about to change a fact — which pages depend on it?** Section 2. A claim corrected in one
   place and left standing in three others is this project's most repeated documentation failure.
   A finding cited on several pages needs one *owner* page that states it and others that link.
2. **Which register rows does no page document?** Section 3 — the triage list.

**Every column is derived, none is typed.** Findings are the ids the page itself cites, scanned from
the page; tiers come from the claim register. There is no hand-maintained companion file: one used to
supply these columns and it drifted, holding an id that did not exist until the citation gate caught
it. A page's audit date is its git history. Regenerate with `build_docs_index.py`; `--check` verifies
only, and the sync step regenerates.

## 1. Pages in attributes/

| Page | Topic | Findings cited on the page |
|------|-------|----------------------------|
| [DATA.md](attributes/DATA.md) | $DATA is a file's default data stream (embedded type 0x80). | MD_ATTR_RA_009, MD_DATA_RA_008, MD_DATA_RA_009, MD_DATA_RA_010, MD_DATA_RA_011, MD_DATA_RA_022, MD_DATA_RA_024, MD_DATA_RA_025, MD_DATA_RA_029, MD_SI_RA_002, MD_SI_RA_016 |
| [EA_INFORMATION.md](attributes/EA_INFORMATION.md) | Extended attributes (EAs) on ReFS are a two-part structure … | FS_REPS_RA_002, FS_REPS_RA_003, MD_ATTR_010, MD_ATTR_RA_010, MD_ATTR_RA_011, MD_ATTR_RA_012, MD_ATTR_RA_013, MD_ATTR_RA_019 |
| [EFS.md](attributes/EFS.md) | $EFS is the Windows Encrypting File System metadata for an encrypted file. | GN_EFS_SA_001, MD_ATTR_RA_009, MD_DISK_RA_006, MD_EFS_RA_003, MD_EFS_RA_004, MD_EFS_RA_005, MD_EFS_RA_006 |
| [I30_INDEX.md](attributes/I30_INDEX.md) | $I30_INDEX (embedded type 0x90) is the B+-tree index configuration template for a directory's "$I30" entry index. | FS_SNAP_RA_001, MD_ATTR_010, MD_ATTR_RA_015, MD_ATTR_RA_017 |
| [NAMED_DATA.md](attributes/NAMED_DATA.md) | $NAMED_DATA is ReFS's named (alternate) data stream — ADS. | FS_SNAP_RA_001, MD_ADS_RA_001, MD_ADS_RA_002, MD_ADS_RA_003, MD_ADS_RA_004, MD_ADS_RA_005, MD_ATTR_007, MD_ATTR_RA_018, MD_DATA_RA_010, MD_DATA_RA_027, MD_FTBL_007, MD_INTG_RA_005, MD_SNAP_RA_005 |
| [OBJ_LINK.md](attributes/OBJ_LINK.md) | $OBJ_LINK is the object → name backpointer. | GN_AMGR_SA_001, MD_ATTR_003, MD_ATTR_RA_006, MD_LK_RA_005, MD_LK_RA_006, MD_LK_RA_007, MD_LK_RA_008, MD_LK_RA_009 |
| [REPARSE.md](attributes/REPARSE.md) | The reparse index is a system table (table schema 0x160): it is not an attribute and never an embedded sub-record … | FS_OTBL_RA_005, FS_REPS_RA_001 |
| [REPARSE_POINT.md](attributes/REPARSE_POINT.md) | $REPARSE_POINT stores the inline REPARSE_DATA_BUFFER for a reparse point — a symlink, junction, mount point, or … | FS_REPS_RA_002, FS_REPS_RA_003, FS_REPS_RA_005, MD_ATTR_RA_010, MD_ATTR_RA_012, MD_ATTR_RA_016 |
| [SNAPSHOT.md](attributes/SNAPSHOT.md) | $SNAPSHOT is the per-stream snapshot metadata for file versioning (embedded type 0xB0; in the 26100 and later drivers). | CT_DRNT_RA_001, FS_SNAP_RA_001, GN_SNAP_SA_001, MD_ADS_RA_004, MD_ATTR_RA_018, MD_DEL_RA_004, MD_SNAP_RA_002, MD_SNAP_RA_003, MD_SNAP_RA_004, MD_SNAP_RA_005, MD_SNAP_RA_008, MD_SNAP_RA_009, MD_SNAP_RA_010 |
| [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) | $STANDARD_INFORMATION ($SI) holds an object's timestamps, file attributes, SecurityId and change-journal … | FN_DTBL_001, FN_LINK_002, FN_LINK_003, FS_OTBL_RA_008, FS_SNAP_RA_001, MD_ATTR_RA_015, MD_CS_RA_003, MD_DDIR_001, MD_DDIR_002, MD_DDIR_003, MD_DDIR_004, MD_DDIR_006, MD_FTBL_001, MD_FTBL_002, MD_FTBL_003, MD_FTBL_004, MD_FTBL_006, MD_INTG_RA_001, MD_SI_RA_002, MD_SI_RA_004, MD_SI_RA_005, MD_SI_RA_006, MD_SI_RA_007, MD_SI_RA_008, MD_SI_RA_010, MD_SI_RA_011, MD_SI_RA_012, MD_SI_RA_013, MD_SI_RA_014, MD_SI_SA_001, MD_SI_SA_002, MD_TS_RA_001, MD_TS_RA_002, MD_TS_RA_004, MD_TS_RA_008 |
| [VOLUME_INFORMATION.md](attributes/VOLUME_INFORMATION.md) | $VOLUME_INFORMATION is the volume-level metadata — version, flags, label, and timestamps. | FS_OTBL_RA_004, FS_VINF_001, FS_VOLI_RA_001, FS_VOLI_RA_002 |

## 1. Pages in structures/

| Page | Topic | Findings cited on the page |
|------|-------|----------------------------|
| [allocators.md](structures/allocators.md) | ReFS tracks free and allocated clusters with a three-tier allocator hierarchy. | CT_ALLC_001, CT_ALLC_004, CT_ALLC_RA_001, FS_ALLOC_RA_001, FS_ALLOC_RA_002, FS_CHKP_010, GN_ALLC_SA_001, GN_ARCH_RA_001 |
| [block_refcount.md](structures/block_refcount.md) | The Block Refcount Table (root #6, table ID 0x05, schema 0xe0b0) counts, per data cluster, the references beyond … | CT_BKRC_001, CT_BKRC_RA_001, CT_BKRC_RA_002, CT_BKRC_RA_003, GN_DEDUP_SA_001 |
| [btree_node.md](structures/btree_node.md) | The ReFS tables — the system tables and every directory's own tree — are B+-trees whose pages carry the signature … | GN_ARCH_001, GN_ARCH_005, GN_BPT_RA_001, GN_IDXH_001, GN_IDXH_002, GN_IDXH_003, GN_IDXR_001, GN_IDXR_002, GN_IDXR_003, GN_IDXR_004, GN_IENT_001, GN_IENT_002, GN_IENT_003, GN_IENT_005, GN_IENT_006, GN_PAGE_007, GN_TREE_RP_003, GN_UTIL_SA_001 |
| [chkp.md](structures/chkp.md) | The Checkpoint is the atomic commit point of a ReFS volume. A volume keeps two alternating checkpoints. | CT_ALLC_002, FS_CHKP_001, FS_CHKP_002, FS_CHKP_003, FS_CHKP_004, FS_CHKP_006, FS_CHKP_007, FS_CHKP_008, FS_CHKP_011, FS_CHKP_013, FS_CHKP_021, FS_CHKP_RA_001, FS_CHKP_RA_002, FS_CHKP_RA_005, FS_CHKP_RA_008, FS_CHKP_RA_009, FS_CHKP_RA_011, FS_CHKP_RA_012, FS_CHKP_RA_013, FS_CHKP_RA_015, FS_CHKP_RA_016, FS_VBR_RA_009, MD_USN_SA_002 |
| [container_index.md](structures/container_index.md) | The Container Index (root #10, table ID 0x0E, schema 0xe100) holds, per container, what its … | CT_CNTX_001, FS_CHKP_019, GN_CROT_SA_001 |
| [container_table.md](structures/container_table.md) | The Container Table (roots #7/#8, schema 0xe0c0) maps virtual container IDs to physical disk … | AP_REDO_037, CT_CTBL_001, CT_CTBL_002, CT_CTBL_003, CT_CTBL_004, CT_CTBL_005, CT_CTBL_006, CT_CTBL_007, CT_CTBL_008, CT_CTBL_009, CT_CTBL_010, CT_CTBL_011, CT_CTBL_RA_003, CT_CTBL_RA_004, FS_CHKP_016, FS_CHKP_017, FS_CHKP_019, GN_ARCH_003, GN_ARCH_RA_001 |
| [directory_entries.md](structures/directory_entries.md) | Directory entries (type 0x30) are B+-tree rows within a per-directory B+-tree. | FN_DTBL_002, FN_DTBL_006, FN_DTBL_007, FS_SCHM_RA_012, GN_IDXR_RA_005, GN_IENT_004, MD_ATTR_RA_008, MD_ATTR_RA_014, MD_DATA_RA_012, MD_DATA_RA_021, MD_FTBL_005, MD_SI_RA_017 |
| [extent_descriptors.md](structures/extent_descriptors.md) | An extent record maps a run of a file's logical clusters (VCNs) to virtual cluster numbers (VLCNs). | CT_DRNT_001, CT_DRNT_002, CT_DRNT_003, CT_DRNT_RA_001, MD_ADS_RA_002, MD_DATA_RA_001, MD_DATA_RA_002, MD_DATA_RA_007, MD_DATA_RA_009, MD_DATA_RA_011, MD_DATA_RA_013, MD_DATA_RA_014, MD_DATA_RA_023, MD_DATA_RA_024, MD_DATA_RA_028, MD_DATA_RA_030, MD_SF_RA_004, MD_SF_RA_005, MD_SNAP_RA_003 |
| [integrity_state.md](structures/integrity_state.md) | The Integrity State Table (root #11, table ID 0x0F, schema 0xe080) keeps an integrity state per range of the … | FS_CHKP_020 |
| [mlog.md](structures/mlog.md) | The MLog implements write-ahead logging for atomic metadata updates. | AP_EVNT_001, AP_EVNT_002, AP_EVNT_003, AP_EVNT_004, AP_EVNT_005, AP_EVNT_006, AP_EVNT_007, AP_LGFL_003, AP_LGFL_004, AP_LGFL_RA_005, AP_LGFL_RA_006, AP_LGFL_RA_008, AP_LGFL_RA_010, AP_LGFL_RA_011, AP_LGFL_RA_012, AP_LGTB_001, AP_LGTB_002, AP_LGTB_003, AP_LGTB_005, AP_REDO_001, AP_REDO_002, AP_REDO_003, AP_REDO_004, AP_REDO_005, AP_REDO_006, AP_REDO_007, AP_REDO_008, AP_REDO_009, AP_REDO_010, AP_REDO_011, AP_REDO_012, AP_REDO_013, AP_REDO_014, AP_REDO_015, AP_REDO_016, AP_REDO_017, AP_REDO_018, AP_REDO_019, AP_REDO_020, AP_REDO_021, AP_REDO_022, AP_REDO_023, AP_REDO_024, AP_REDO_025, AP_REDO_026, AP_REDO_027, AP_REDO_028, AP_REDO_029, AP_REDO_030, AP_REDO_031, AP_REDO_032, AP_REDO_033, AP_REDO_034, AP_REDO_035, AP_REDO_036, AP_REDO_037, AP_REDO_038, AP_REDO_039, AP_REDO_040 |
| [object_table.md](structures/object_table.md) | The Object Table (roots #0 and #5, schema 0xe030) is the master OID-to-table mapping. | FS_OTBL_001, FS_OTBL_002, FS_OTBL_RA_002, FS_OTBL_RA_007, FS_OTBL_RA_009, FS_OTBL_RA_010, FS_OTBL_SA_001, FS_OTBL_SA_003, FS_OTBL_SA_007, MD_ATTR_RA_005 |
| [page_header.md](structures/page_header.md) | Every ReFS metadata page -- SUPB, CHKP, and MSB+ (B+-tree) -- begins with a common 80-byte header. | FS_SUPB_RA_001, FS_SUPB_RA_004, GN_PAGE_001, GN_PAGE_002, GN_PAGE_003, GN_PAGE_004, GN_PAGE_005, GN_PAGE_006, GN_PAGE_007, GN_PAGE_RA_001, GN_PAGE_RA_002 |
| [page_references.md](structures/page_references.md) | A page reference binds a child page's address to a checksum of that child's contents. | FS_CHKP_004, FS_SUPB_006, FS_SUPB_RA_003, GN_PREF_002, GN_PREF_003, GN_PREF_RA_004 |
| [parent_child_table.md](structures/parent_child_table.md) | The Parent-Child Table (root #4, schema 0xe040) encodes the directory hierarchy. | FN_DTBL_004, FS_OTBL_004, FS_OTBL_SA_010, FS_PCHL_001, FS_PCTB_RA_001, GN_IENT_005 |
| [reparse_points.md](structures/reparse_points.md) | A reparse point is a per-file tag plus payload that redirects path resolution — a symlink, junction … | FS_OTBL_RA_004, FS_REPS_RA_004, MD_LK_RA_002 |
| [reverse_index.md](structures/reverse_index.md) | Type 0x20 is the per-object FileId-resolution index: rows keyed by a FileId (object reference / child index) … | FN_DTBL_003, MD_CS_RA_002, MD_DISK_RA_009 |
| [schema_table.md](structures/schema_table.md) | The Schema Table (roots #3/#9, schema 0xe060) is self-describing: it contains one entry per table type used by the volume. | FN_LINK_003, FS_PCTB_RA_001, FS_SCHM_001, FS_SCHM_RA_002, FS_SCHM_RA_003, FS_SCHM_RA_005, FS_SCHM_RA_008, FS_SCHM_RA_009, FS_SCHM_RA_010, FS_SCHM_RA_011, FS_SCHM_RA_012, FS_SCHM_RA_013, FS_SECD_RA_003, FS_VBR_RA_015, GN_IDXR_RA_005, MD_TS_RA_005, MD_UNSUP_RA_001 |
| [security_descriptors.md](structures/security_descriptors.md) | ReFS uses a centralised, content-addressed security model … | FS_OTBL_SA_006, MD_DDIR_006 |
| [supb.md](structures/supb.md) | The Superblock is the fixed-location volume anchor that points to the two alternating checkpoints. | FS_CHKP_005, FS_SUPB_001, FS_SUPB_002, FS_SUPB_003, FS_SUPB_004, FS_SUPB_005, FS_SUPB_007, FS_SUPB_RA_003, FS_UPGD_RA_001 |
| [system_oids.md](structures/system_oids.md) | ReFS reserves the OIDs below 0x700 for internal use; user directories start at 0x701. | FS_OTBL_003, FS_OTBL_005, FS_OTBL_RA_001, FS_OTBL_RA_003, FS_OTBL_RA_005, FS_OTBL_SA_004, FS_OTBL_SA_005, FS_REPS_RA_001, FS_SCHM_RA_001, FS_SECD_RA_001, MD_SECT_001 |
| [trash_table.md](structures/trash_table.md) | The Trash Table (OID 0x0D, schema 0xe0d0) is an asynchronous deletion queue. | CT_MISC_002, FS_OTBL_RA_008 |
| [upcase_table.md](structures/upcase_table.md) | The Upcase Table (a failover pair, OID 0x08 and OID 0x07, schema 0xe090) stores the Unicode … | FS_UPCS_001, MD_CS_RA_001 |
| [usn_journal.md](structures/usn_journal.md) | The USN (Update Sequence Number) Journal records changes to files and directories on the volume, for as long as … | AP_CHJN_001, AP_CHJN_002, AP_CHJN_004, FS_OTBL_005, GN_ARCH_RA_002, MD_EFS_RA_001, MD_EFS_RA_002, MD_LK_RA_003, MD_LK_RA_004, MD_SF_RA_002, MD_SI_RA_013, MD_SI_RA_015, MD_USN_RA_001, MD_USN_RA_002, MD_USN_RA_003, MD_USN_RA_004, MD_USN_RA_007, MD_USN_RA_008, MD_USN_RA_009, MD_USN_RA_010, MD_USN_SA_001 |
| [vbr.md](structures/vbr.md) | The VBR is a 512-byte structure at sector 0 of the ReFS partition. | FS_VBR_001, FS_VBR_002, FS_VBR_003, FS_VBR_004, FS_VBR_005, FS_VBR_006, FS_VBR_007, FS_VBR_009, FS_VBR_010, FS_VBR_012, FS_VBR_013, FS_VBR_RA_002, FS_VBR_RA_004, FS_VBR_RA_005, FS_VBR_RA_006, FS_VBR_RA_007, FS_VBR_RA_010, FS_VBR_RA_012, FS_VBR_SA_013, GN_INS_SA_001, GN_PREF_002 |
| [volume_info.md](structures/volume_info.md) | The Volume Information table (OIDs 0x500 and 0x501, a failover pair; | FS_VINF_002, FS_VINF_RA_001 |

## 1. Pages in concepts/

| Page | Topic | Findings cited on the page |
|------|-------|----------------------------|
| [allocation_space_mgmt.md](concepts/allocation_space_mgmt.md) | ReFS decides which clusters are free and which are in use with a three-tier bitmap allocator (Medium … | — |
| [architecture.md](concepts/architecture.md) | The ReFS driver is built in two layers, and only the lower one reads and writes the disk. | FN_OPEN_SA_001, GN_ARCH_001, GN_ARCH_002, GN_ARCH_SA_001, GN_FOPS_SA_001, GN_INS_SA_003, GN_IRP_SA_001, GN_OOP_SA_001, GN_WSL_SA_001, MD_ATTR_SA_001 |
| [artifact_timeline.md](concepts/artifact_timeline.md) | Most filesystem investigations are built on times. | FN_LINK_003, MD_ATTR_001, MD_TS_RA_004, MD_TS_RA_008 |
| [attributes.md](concepts/attributes.md) | In NTFS a file's metadata is a list of typed attributes inside its MFT record, and a parser that walks that list … | FS_REPS_RA_004, FS_SCHM_RA_005, FS_SNAP_RA_001, MD_ATTR_002, MD_ATTR_004, MD_ATTR_005, MD_ATTR_006, MD_ATTR_008, MD_ATTR_009, MD_ATTR_RA_003, MD_ATTR_RA_004, MD_ATTR_RA_007, MD_ATTR_RA_016, MD_ATTR_RA_019, MD_ATTR_RA_020, MD_DDIR_005, MD_UNSUP_RA_001, MD_USN_RA_004 |
| [bootstrap_chain.md](concepts/bootstrap_chain.md) | Before a ReFS parser can read a file, a directory, or any B+-tree, it has to find the trees. | FS_CHKP_005, FS_SUPB_001, FS_SUPB_005, FS_SUPB_007, FS_SUPB_RA_003 |
| [carrier_categories.md](concepts/carrier_categories.md) | Brian Carrier's File System Forensic Analysis (Addison-Wesley, 2005) organises every file-system artifact into five … | AP_CHJN_003, AP_LGFL_005, AP_REDO_001, AP_REDO_002, AP_REDO_003, AP_REDO_004, AP_REDO_005, AP_REDO_006, AP_REDO_007, AP_REDO_008, AP_REDO_009, AP_REDO_010, AP_REDO_011, AP_REDO_012, AP_REDO_013, AP_REDO_014, AP_REDO_015, AP_REDO_016, AP_REDO_017, AP_REDO_018, AP_REDO_019, AP_REDO_020, AP_REDO_021, AP_REDO_022, AP_REDO_023, AP_REDO_024, AP_REDO_025, AP_REDO_026, AP_REDO_027, AP_REDO_028, AP_REDO_029, AP_REDO_030, AP_REDO_031, AP_REDO_032, AP_REDO_033, AP_REDO_034, AP_REDO_035, AP_REDO_036, AP_REDO_037, AP_REDO_038, AP_REDO_039, FN_LINK_002, FS_CHKP_RA_014, FS_DEL_RA_002, FS_DEL_RA_005, MD_SI_RA_008, MD_SI_RA_009, MD_SI_RA_010 |
| [checksum_architecture.md](concepts/checksum_architecture.md) | ReFS protects its metadata with a Merkle-tree variant: every B+-tree parent stores a checksum of each … | FS_CHKP_005, FS_SUPB_001, FS_SUPB_005, FS_SUPB_007, FS_SUPB_RA_002, FS_SUPB_RA_003, GN_PREF_002 |
| [cluster_page_size.md](concepts/cluster_page_size.md) | The cluster size is a single number chosen when a ReFS volume is formatted, and it sets the … | CT_CTBL_002, CT_CTBL_003, CT_CTBL_RA_003, CT_CTBL_RA_006, CT_CTBL_RA_007, FS_VBR_008, FS_VBR_011 |
| [compression.md](concepts/compression.md) | ReFS compression makes a file's bytes on disk unreadable to a parser that does not decompress them. | AP_REDO_026, AP_REDO_037, CT_COMP_RA_001, CT_COMP_RA_002, CT_COMP_RA_003, GN_COMP_SA_001 |
| [copy_on_write.md](concepts/copy_on_write.md) | Copy-on-write is the rule that makes ReFS recoverable: no B+-tree page is ever overwritten in place. | AP_LGFL_005, GN_ARCH_002, GN_FOPS_SA_002 |
| [deduplication.md](concepts/deduplication.md) | ReFS deduplication lets several files share the same physical clusters. | CT_BKRC_001, CT_BKRC_RA_001, CT_BKRC_RA_002, CT_BKRC_RA_003, FS_CHKP_015, FS_CHKP_RA_001 |
| [deletion_recovery.md](concepts/deletion_recovery.md) | Deletion on ReFS zeroes nothing. When a file is deleted, the analyst has to find where the prior bytes still are … | AP_LGFL_RA_012, FN_PATH_001, FS_CHKP_RA_014, FS_DEL_RA_005, MD_DEL_RA_001, MD_DEL_RA_003, MD_DEL_RA_004, MD_DISK_RA_008 |
| [driver_architecture.md](concepts/driver_architecture.md) | The on-disk structures are one source of evidence; the code that writes them is the other. | FS_VBR_RA_011, GN_ARCH_006, GN_ARCH_SA_002, GN_BIN_SA_001, GN_HEAT_SA_001, GN_IMP_SA_001, GN_INS_SA_002, GN_KSR_SA_001 |
| [driver_evolution.md](concepts/driver_evolution.md) | The ReFS driver, refs.sys, changes between most of the builds read even where the on-disk format does not. | FS_MOVE_RA_002, FS_RESD_SA_001, FS_RESD_SA_002, GN_VCB_SA_001, MD_ADS_RA_003, MD_DATA_RA_025, MD_EFS_RA_003, MD_SI_RA_007 |
| [file_ids.md](concepts/file_ids.md) | A ReFS file has no Object ID of its own (that identifier belongs to directories and system tables — see … | FN_ADDR_001, FN_LINK_002, GN_IDENT_RA_001, MD_DISK_RA_010, MD_SI_RA_008, MD_SI_RA_010, MD_USN_RA_001, MD_USN_RA_002, MD_USN_RA_005, MD_USN_RA_006 |
| [file_systems.md](concepts/file_systems.md) | Every ReFS forensic decision depends on a few general file-system ideas: what a cluster is, how files point at … | MD_LK_RA_001 |
| [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md) | This is the end-to-end runbook for examining a ReFS volume: a fixed order of steps that takes an analyst from … | FN_LINK_003, FS_CHKP_005, FS_CHKP_RA_001, FS_CHKP_RA_012, FS_CHKP_RA_013, FS_CHKP_RA_014, FS_DEL_RA_005, FS_SUPB_001, FS_SUPB_005, FS_SUPB_007, FS_SUPB_RA_003, FS_SUPB_RA_005, MD_TS_RA_008 |
| [hard_links.md](concepts/hard_links.md) | A hard link is a second (or third, ...) directory name that points at one physical file. | FN_LINK_001, FN_LINK_002, FN_LINK_003, FN_LINK_004, FS_OTBL_RA_008, MD_DATA_RA_004, MD_DATA_RA_006, MD_SI_RA_001, MD_SI_RA_009, MD_TS_RA_008 |
| [integrity_streams.md](concepts/integrity_streams.md) | An integrity stream is a per-file, opt-in feature that protects a file's data with per-block … | CT_DRNT_004, CT_INTS_001, CT_INTS_002, GN_PREF_002, MD_DATA_RA_010, MD_DATA_RA_013, MD_INTG_RA_001, MD_SI_RA_006 |
| [ntfs_comparison.md](concepts/ntfs_comparison.md) | Almost every ReFS forensic mistake comes from applying an NTFS habit to ReFS. | AP_REDO_037, MD_SI_RA_008 |
| [object_ids.md](concepts/object_ids.md) | Every persistent ReFS directory or system table carries a 64-bit Object ID (OID). | FS_OTBL_RA_006, FS_OTBL_RA_010, FS_OTBL_SA_002, FS_OTBL_SA_004, FS_OTBL_SA_005, FS_OTBL_SA_009 |
| [oid_allocation.md](concepts/oid_allocation.md) | Every persistent ReFS directory and system object draws its 64-bit Object ID (OID) from a single per-volume … | — |
| [placement_and_residency.md](concepts/placement_and_residency.md) | Every ReFS file has two storage properties, and each is independent of the other … | FN_DTBL_005, FS_MOVE_RA_001, FS_MOVE_RA_003, MD_DATA_RA_015, MD_DATA_RA_022, MD_DATA_RA_027, MD_PLAC_RA_001, MD_SNAP_RA_009 |
| [redundancy.md](concepts/redundancy.md) | Every ReFS volume keeps redundant copies of the three structures it needs to mount — the … | CT_MISC_001, FS_CHKP_005, FS_CHKP_RA_014, FS_SUPB_001, FS_SUPB_005, FS_SUPB_007, FS_SUPB_RA_003, FS_VBR_RA_013, FS_VBR_RA_014 |
| [snapshots_versioning.md](concepts/snapshots_versioning.md) | A ReFS stream snapshot freezes a file's current content under a new stream identity, so that later … | AP_LGFL_005, CT_BKRC_001, CT_DRNT_RA_001, FS_CHKP_015, FS_OTBL_RA_008, FS_SCHM_RA_005, FS_SCHM_RA_008, FS_SNAP_RA_001, GN_ARCH_002, GN_SNAP_SA_001, MD_ATTR_RA_018, MD_SNAP_RA_001, MD_SNAP_RA_002, MD_SNAP_RA_003, MD_SNAP_RA_005, MD_SNAP_RA_006, MD_SNAP_RA_007, MD_SNAP_RA_008 |
| [tiering.md](concepts/tiering.md) | A ReFS volume can move its data between a fast tier (NVMe/SSD) and a slow tier (HDD), and can compress, decompress or … | FS_SCHM_RA_004, FS_VOLI_RA_002 |
| [timestomp_detection.md](concepts/timestomp_detection.md) | Timestomping — back-dating a file's timestamps to hide when it was really created or written — is a standard … | MD_MISC_001, MD_SNAP_RA_010, MD_TS_RA_003, MD_TS_RA_007, MD_TS_RA_008, MD_TS_RA_009, MD_TS_RA_010, MD_TS_RA_011 |
| [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md) | ReFS keeps its metadata consistent across power loss with two cooperating mechanisms … | AP_LGFL_001, AP_LGFL_002, AP_LGFL_005, AP_LGFL_RA_004, AP_LGFL_RA_007, AP_LGFL_RA_008, AP_LGFL_RA_009, AP_LGFL_RA_012, AP_REDO_001, AP_REDO_002, AP_REDO_003, AP_REDO_004, AP_REDO_005, AP_REDO_006, AP_REDO_007, AP_REDO_008, AP_REDO_009, AP_REDO_010, AP_REDO_011, AP_REDO_012, AP_REDO_013, AP_REDO_014, AP_REDO_015, AP_REDO_016, AP_REDO_017, AP_REDO_018, AP_REDO_019, AP_REDO_020, AP_REDO_021, AP_REDO_022, AP_REDO_023, AP_REDO_024, AP_REDO_025, AP_REDO_026, AP_REDO_027, AP_REDO_028, AP_REDO_029, AP_REDO_030, AP_REDO_031, AP_REDO_032, AP_REDO_033, AP_REDO_034, AP_REDO_035, AP_REDO_036, AP_REDO_037, AP_REDO_038, AP_REDO_039, FS_CHKP_RA_017, FS_DEL_RA_001, FS_SUPB_RA_006 |
| [version_detection.md](concepts/version_detection.md) | A parser needs a ReFS volume's version before it reads any other structure. | FS_CHKP_RA_001, FS_CHKP_RA_007, FS_CHKP_RA_013, MD_ATTR_RA_002 |
| [version_evolution.md](concepts/version_evolution.md) | ReFS has several closely related formats. A parser that ignores the differences between them silently misreads … | — |
| [virtual_addressing.md](concepts/virtual_addressing.md) | Virtual addressing is the rule that decides where ReFS data is stored on disk. | CT_ALLC_003 |
| [what_is_refs.md](concepts/what_is_refs.md) | ReFS, the Resilient File System, is a Microsoft file system for Windows, introduced in 2012 with Windows … | FN_LINK_001, GN_ARCH_001, GN_ARCH_002, GN_ARCH_003, GN_ARCH_004, GN_INS_SA_001, GN_INS_SA_002 |
| [what_survives.md](concepts/what_survives.md) | For each event that can happen to a ReFS volume, this page says which artifacts an analyst can still recover, and … | AP_LGFL_005, AP_LGFL_RA_004, AP_LGFL_RA_008, AP_LGFL_RA_012, CT_DRNT_RA_001, FS_CHKP_RA_014, FS_DEL_RA_005, FS_OTBL_RA_008, FS_SECD_RA_001, FS_VBR_RA_013, GN_IMG_RA_001, GN_SNAP_SA_001, MD_SNAP_RA_002, MD_SNAP_RA_003 |
| [windows_file_systems.md](concepts/windows_file_systems.md) | A file operation on a ReFS volume passes through several Windows kernel layers before refs.sys reads anything … | GN_HIER_SA_001 |
| [wsl_metadata.md](concepts/wsl_metadata.md) | When the Windows Subsystem for Linux (WSL) accesses a ReFS volume through a DrvFs mount with … | FS_SCHM_RA_006 |

## 1. Pages in tools/

| Page | Topic | Findings cited on the page |
|------|-------|----------------------------|
| [forefst.md](tools/forefst.md) | ReFS forensic analysis tool. forefst.py lists per-file metadata (CSV, JSON, JSON Lines or a body file) from a raw … | — |
| [internals.md](tools/internals.md) | How forefst.py and refsanalysis.py are built: the order in which a volume is read, the functions that do each … | — |
| [known_issues.md](tools/known_issues.md) | These are the known limits of this release that can change what an examiner reports: what the tools do not read or … | — |
| [metadata_bundles.md](tools/metadata_bundles.md) | A bundle is what export metadata writes: a hash-sealed directory holding the structures of one ReFS … | — |
| [migration.md](tools/migration.md) | What a script that reads the output of forefst.py or refsanalysis.py must change from one release to the next … | — |
| [refsanalysis.md](tools/refsanalysis.md) | ReFS structure and lab analysis tool. It decodes … | — |
| [tool_artifact_map.md](tools/tool_artifact_map.md) | This page maps each forensic goal to the command that finds its artifact and to the page that documents the … | AP_LGFL_001, AP_LGFL_RA_002, AP_LGTB_004, CT_CNTX_001, CT_DRNT_RA_001, CT_DRNT_RA_002, CT_INTS_001, FN_LINK_002, FN_LINK_003, FS_CHKP_009, FS_CHKP_012, FS_CHKP_014, FS_CHKP_016, FS_CHKP_017, FS_CHKP_018, FS_CHKP_RA_001, FS_CHKP_RA_003, FS_CHKP_RA_009, FS_DEL_RA_001, FS_DEL_RA_003, FS_DEL_RA_004, FS_DEL_RA_005, FS_OTBL_RA_001, FS_OTBL_RA_003, FS_PCHL_001, FS_PCTB_RA_001, FS_SCHM_RA_001, FS_SCHM_RA_005, FS_SCHM_RA_007, FS_SCHM_RA_008, FS_SCHM_RA_010, FS_SECD_RA_001, FS_SECD_RA_002, FS_SECD_RA_003, FS_SNAP_RA_001, FS_UPCS_001, FS_VBR_RA_013, GN_ARCH_002, GN_ARCH_004, GN_ARCH_005, GN_PAGE_001, GN_PAGE_007, GN_PAGE_RA_002, GN_PREF_001, GN_SNAP_SA_001, MD_ATTR_011, MD_DATA_RA_001, MD_DATA_RA_005, MD_DISK_RA_003, MD_DISK_RA_004, MD_SECT_001, MD_SI_RA_002, MD_SI_RA_003, MD_SI_RA_015, MD_SNAP_RA_002, MD_SNAP_RA_003, MD_SNAP_RA_005, MD_SNAP_RA_006, MD_SNAP_RA_007, MD_TS_RA_005, MD_UNSUP_RA_001, MD_USN_RA_004 |

## 1. Pages in examples/

| Page | Topic | Findings cited on the page |
|------|-------|----------------------------|
| [check_integrity.md](examples/check_integrity.md) | A first examination, 6 of 6 · previous: Look for what was deleted … | — |
| [decode_vbr_by_hand.md](examples/decode_vbr_by_hand.md) | cluster size, container size, version, and checksum mode, then confirm the by-hand values against the tool. | — |
| [detect_timestomping.md](examples/detect_timestomping.md) | lead with a record outside the file's own timestamps (the change journal, a second hard-link name) rather than with … | — |
| [find_a_deleted_file.md](examples/find_a_deleted_file.md) | and why the others find nothing. | FS_CHKP_RA_014 |
| [first_examination.md](examples/first_examination.md) | You have an image of a ReFS volume and a case to work. | — |
| [follow_the_history.md](examples/follow_the_history.md) | A first examination, 4 of 6 · previous: Read the times with care · next: Look for what was deleted … | — |
| [identify_each_file.md](examples/identify_each_file.md) | A first examination, 2 of 6 · previous: Know the volume · next: Read the times with care … | — |
| [identify_native_vs_upgraded.md](examples/identify_native_vs_upgraded.md) | upgraded from an older v3.4 volume. Both report version 3.14, so the answer comes from the checkpoint flags and the … | — |
| [know_the_volume.md](examples/know_the_volume.md) | A first examination, 1 of 6 · next: Identify each file properly … | — |
| [look_for_deleted_files.md](examples/look_for_deleted_files.md) | A first examination, 5 of 6 · previous: Follow the history · next: Check that it is intact … | — |
| [read_a_hard_link_group.md](examples/read_a_hard_link_group.md) | physical file — and prove the reconstruction is correct by decoding the on-disk identity … | — |
| [read_the_change_journal.md](examples/read_the_change_journal.md) | checkpoint records where it stood. | — |
| [read_the_times.md](examples/read_the_times.md) | A first examination, 3 of 6 · previous: Identify each file properly · next: Follow the history … | — |
| [read_wsl_files.md](examples/read_wsl_files.md) | Linux facts they carry (file type, mode, owner, device number), which no Windows tool shows. | — |
| [recover_credentials_and_prior_versions.md](examples/recover_credentials_and_prior_versions.md) | streams, and read what a file said before it was edited. | — |
| [track_a_file_across_moves.md](examples/track_a_file_across_moves.md) | name and directory change, and use that fixed identity to (a) follow the file through the change journal … | — |

## 1. Pages in methodology/

| Page | Topic | Findings cited on the page |
|------|-------|----------------------------|
| [driver_builds.md](methodology/driver_builds.md) | Every structural claim on this site is checked against the refs.sys driver as well as against disks. | — |

## 2. Findings → the pages that cite them

Before changing a finding, correct every page listed on its row in the same commit. The
The **163 rows citing more than one page** are not duplication to be consolidated:
a finding is cited where a page declares what backs its statements, and one finding legitimately
backs statements on several pages. Measured 2026-09-11: 540 of the 557 citations in the tree sit
in a `## Evidence` section, and no concept is explained redundantly. What must not happen is two
pages stating one fact with *different numbers* — gates 7h and 7i check exactly that.

| Finding | Static | Disk | Pages | Cited on |
|---------|--------|------|-------|----------|
| `AP_CHJN_001` | — | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `AP_CHJN_002` | — | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `AP_CHJN_003` | — | NOT_TESTED |  | [carrier_categories.md](concepts/carrier_categories.md) |
| `AP_CHJN_004` | — | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `AP_EVNT_001` | E2 | ENRICHED |  | [mlog.md](structures/mlog.md) |
| `AP_EVNT_002` | E2 | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_EVNT_003` | — | NOT_TESTED |  | [mlog.md](structures/mlog.md) |
| `AP_EVNT_004` | E2 | ENRICHED |  | [mlog.md](structures/mlog.md) |
| `AP_EVNT_005` | E2 | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_EVNT_006` | E2 | ENRICHED |  | [mlog.md](structures/mlog.md) |
| `AP_EVNT_007` | E2 | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGFL_001` | E1 | ENRICHED | 2 | [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `AP_LGFL_002` | E2 | CONFIRMED |  | [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md) |
| `AP_LGFL_003` | E2 | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGFL_004` | — | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGFL_005` | E2 | CONFIRMED | 5 | [carrier_categories.md](concepts/carrier_categories.md), [copy_on_write.md](concepts/copy_on_write.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [what_survives.md](concepts/what_survives.md) |
| `AP_LGFL_RA_002` | E2 | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `AP_LGFL_RA_004` | E2 | CONFIRMED | 2 | [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [what_survives.md](concepts/what_survives.md) |
| `AP_LGFL_RA_005` | E2 | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGFL_RA_006` | E2 | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGFL_RA_007` | E2+RD | CONFIRMED |  | [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md) |
| `AP_LGFL_RA_008` | E2+RD | CONFIRMED | 3 | [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [what_survives.md](concepts/what_survives.md), [mlog.md](structures/mlog.md) |
| `AP_LGFL_RA_009` | E2 | CONFIRMED |  | [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md) |
| `AP_LGFL_RA_010` | E2+RD | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGFL_RA_011` | E2+RD | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGFL_RA_012` | E2 | CONFIRMED | 4 | [deletion_recovery.md](concepts/deletion_recovery.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [what_survives.md](concepts/what_survives.md), [mlog.md](structures/mlog.md) |
| `AP_LGTB_001` | — | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGTB_002` | — | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGTB_003` | — | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_LGTB_004` | — | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `AP_LGTB_005` | — | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `AP_REDO_001` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_002` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_003` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_004` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_005` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_006` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_007` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_008` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_009` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_010` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_011` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_012` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_013` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_014` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_015` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_016` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_017` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_018` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_019` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_020` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_021` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_022` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_023` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_024` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_025` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_026` | E2 | NOT_TESTED | 4 | [carrier_categories.md](concepts/carrier_categories.md), [compression.md](concepts/compression.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_027` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_028` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_029` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_030` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_031` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_032` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_033` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_034` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_035` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_036` | E2 | NOT_TESTED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_037` | E2 | INFERRED | 6 | [carrier_categories.md](concepts/carrier_categories.md), [compression.md](concepts/compression.md), [ntfs_comparison.md](concepts/ntfs_comparison.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [container_table.md](structures/container_table.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_038` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_039` | E2 | INFERRED | 3 | [carrier_categories.md](concepts/carrier_categories.md), [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [mlog.md](structures/mlog.md) |
| `AP_REDO_040` | RD | CONFIRMED |  | [mlog.md](structures/mlog.md) |
| `CT_ALLC_001` | E2 | INFERRED |  | [allocators.md](structures/allocators.md) |
| `CT_ALLC_002` | E2 … | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `CT_ALLC_003` | E2 | ENRICHED |  | [virtual_addressing.md](concepts/virtual_addressing.md) |
| `CT_ALLC_004` | E2 | CONFIRMED |  | [allocators.md](structures/allocators.md) |
| `CT_ALLC_RA_001` | — | NEW |  | [allocators.md](structures/allocators.md) |
| `CT_BKRC_001` | E2 | INFERRED | 3 | [deduplication.md](concepts/deduplication.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [block_refcount.md](structures/block_refcount.md) |
| `CT_BKRC_RA_001` | — | NEW | 2 | [deduplication.md](concepts/deduplication.md), [block_refcount.md](structures/block_refcount.md) |
| `CT_BKRC_RA_002` | E2+RD | CONFIRMED | 2 | [deduplication.md](concepts/deduplication.md), [block_refcount.md](structures/block_refcount.md) |
| `CT_BKRC_RA_003` | RD | CONFIRMED | 2 | [deduplication.md](concepts/deduplication.md), [block_refcount.md](structures/block_refcount.md) |
| `CT_CNTX_001` | E2 | CONFIRMED | 2 | [container_index.md](structures/container_index.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `CT_COMP_RA_001` | — | CONFIRMED |  | [compression.md](concepts/compression.md) |
| `CT_COMP_RA_002` | — | CONFIRMED |  | [compression.md](concepts/compression.md) |
| `CT_COMP_RA_003` | E2+RD | CONFIRMED |  | [compression.md](concepts/compression.md) |
| `CT_CTBL_001` | — | CONFIRMED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_002` | — | CONFIRMED | 2 | [cluster_page_size.md](concepts/cluster_page_size.md), [container_table.md](structures/container_table.md) |
| `CT_CTBL_003` | — | CONFIRMED | 2 | [cluster_page_size.md](concepts/cluster_page_size.md), [container_table.md](structures/container_table.md) |
| `CT_CTBL_004` | — | CONFIRMED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_005` | — | CONFIRMED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_006` | — | CONTRADICTED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_007` | — | CONFIRMED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_008` | — | INFERRED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_009` | — | CONFIRMED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_010` | — | CONTRADICTED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_011` | — | CONTRADICTED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_RA_003` | — | CONFIRMED | 2 | [cluster_page_size.md](concepts/cluster_page_size.md), [container_table.md](structures/container_table.md) |
| `CT_CTBL_RA_004` | E2 | CONFIRMED |  | [container_table.md](structures/container_table.md) |
| `CT_CTBL_RA_006` | E2 … | CONFIRMED |  | [cluster_page_size.md](concepts/cluster_page_size.md) |
| `CT_CTBL_RA_007` | E2+RD | CONFIRMED |  | [cluster_page_size.md](concepts/cluster_page_size.md) |
| `CT_DRNT_001` | E2 | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `CT_DRNT_002` | — | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `CT_DRNT_003` | — | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `CT_DRNT_004` | E2 | CONFIRMED |  | [integrity_streams.md](concepts/integrity_streams.md) |
| `CT_DRNT_RA_001` | E2 | CONFIRMED | 5 | [SNAPSHOT.md](attributes/SNAPSHOT.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [what_survives.md](concepts/what_survives.md), [extent_descriptors.md](structures/extent_descriptors.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `CT_DRNT_RA_002` | E3 | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `CT_INTS_001` | E2 … | CONFIRMED | 2 | [integrity_streams.md](concepts/integrity_streams.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `CT_INTS_002` | E3 | CONFIRMED |  | [integrity_streams.md](concepts/integrity_streams.md) |
| `CT_MISC_001` | E2 | CONFIRMED |  | [redundancy.md](concepts/redundancy.md) |
| `CT_MISC_002` | E2 | NOT_TESTED |  | [trash_table.md](structures/trash_table.md) |
| `FN_ADDR_001` | — | CONFIRMED |  | [file_ids.md](concepts/file_ids.md) |
| `FN_DTBL_001` | — | INFERRED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `FN_DTBL_002` | — | ENRICHED |  | [directory_entries.md](structures/directory_entries.md) |
| `FN_DTBL_003` | E2+RD | INFERRED |  | [reverse_index.md](structures/reverse_index.md) |
| `FN_DTBL_004` | E1 | CONFIRMED |  | [parent_child_table.md](structures/parent_child_table.md) |
| `FN_DTBL_005` | E2+RD | CONFIRMED |  | [placement_and_residency.md](concepts/placement_and_residency.md) |
| `FN_DTBL_006` | E2+RD | CONFIRMED |  | [directory_entries.md](structures/directory_entries.md) |
| `FN_DTBL_007` | E2+RD | CONFIRMED |  | [directory_entries.md](structures/directory_entries.md) |
| `FN_LINK_001` | E2 | INFERRED | 2 | [hard_links.md](concepts/hard_links.md), [what_is_refs.md](concepts/what_is_refs.md) |
| `FN_LINK_002` | E2+RD | CONFIRMED | 5 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [carrier_categories.md](concepts/carrier_categories.md), [file_ids.md](concepts/file_ids.md), [hard_links.md](concepts/hard_links.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FN_LINK_003` | E2+RD | CONFIRMED | 6 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [artifact_timeline.md](concepts/artifact_timeline.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [hard_links.md](concepts/hard_links.md), [schema_table.md](structures/schema_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FN_LINK_004` | E2 | NEW |  | [hard_links.md](concepts/hard_links.md) |
| `FN_OPEN_SA_001` | E2 | NOT_TESTED |  | [architecture.md](concepts/architecture.md) |
| `FN_PATH_001` | E2 | CONFIRMED |  | [deletion_recovery.md](concepts/deletion_recovery.md) |
| `FS_ALLOC_RA_001` | E2+RD | CONFIRMED |  | [allocators.md](structures/allocators.md) |
| `FS_ALLOC_RA_002` | E2+RD | CONFIRMED |  | [allocators.md](structures/allocators.md) |
| `FS_CHKP_001` | E1 | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_002` | — | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_003` | — | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_004` | — | CONFIRMED | 2 | [chkp.md](structures/chkp.md), [page_references.md](structures/page_references.md) |
| `FS_CHKP_005` | E2 … | CONFIRMED | 5 | [bootstrap_chain.md](concepts/bootstrap_chain.md), [checksum_architecture.md](concepts/checksum_architecture.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [redundancy.md](concepts/redundancy.md), [supb.md](structures/supb.md) |
| `FS_CHKP_006` | — | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_007` | E2 | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_008` | — | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_009` | E2 | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_CHKP_010` | E2 | CONFIRMED |  | [allocators.md](structures/allocators.md) |
| `FS_CHKP_011` | — | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_012` | E2 … | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_CHKP_013` | E2 | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_014` | — | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_CHKP_015` | E2 | CONFIRMED | 2 | [deduplication.md](concepts/deduplication.md), [snapshots_versioning.md](concepts/snapshots_versioning.md) |
| `FS_CHKP_016` | E2 | CONFIRMED | 2 | [container_table.md](structures/container_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_CHKP_017` | — | CONFIRMED | 2 | [container_table.md](structures/container_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_CHKP_018` | — | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_CHKP_019` | E2 | CONFIRMED | 2 | [container_index.md](structures/container_index.md), [container_table.md](structures/container_table.md) |
| `FS_CHKP_020` | E2 | CONFIRMED |  | [integrity_state.md](structures/integrity_state.md) |
| `FS_CHKP_021` | — | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_RA_001` | E2 | CONFIRMED | 5 | [deduplication.md](concepts/deduplication.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [version_detection.md](concepts/version_detection.md), [chkp.md](structures/chkp.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_CHKP_RA_002` | E2 | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_RA_003` | — | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_CHKP_RA_005` | E2 | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_RA_007` | E2 | CONFIRMED |  | [version_detection.md](concepts/version_detection.md) |
| `FS_CHKP_RA_008` | E1 | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_RA_009` | E2 … | CONFIRMED | 2 | [chkp.md](structures/chkp.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_CHKP_RA_011` | E2 | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_RA_012` | E2 | CONFIRMED | 2 | [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [chkp.md](structures/chkp.md) |
| `FS_CHKP_RA_013` | RD | CONFIRMED | 3 | [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [version_detection.md](concepts/version_detection.md), [chkp.md](structures/chkp.md) |
| `FS_CHKP_RA_014` | E3 | CONFIRMED | 6 | [carrier_categories.md](concepts/carrier_categories.md), [deletion_recovery.md](concepts/deletion_recovery.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [redundancy.md](concepts/redundancy.md), [what_survives.md](concepts/what_survives.md), [find_a_deleted_file.md](examples/find_a_deleted_file.md) |
| `FS_CHKP_RA_015` | E3 | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_RA_016` | E2+RD | CONFIRMED |  | [chkp.md](structures/chkp.md) |
| `FS_CHKP_RA_017` | RD | NEW |  | [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md) |
| `FS_DEL_RA_001` | E2 … | CONFIRMED | 2 | [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_DEL_RA_002` | E2 | CONFIRMED |  | [carrier_categories.md](concepts/carrier_categories.md) |
| `FS_DEL_RA_003` | E2 | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_DEL_RA_004` | E2 | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_DEL_RA_005` | E2+RD | CONFIRMED | 5 | [carrier_categories.md](concepts/carrier_categories.md), [deletion_recovery.md](concepts/deletion_recovery.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [what_survives.md](concepts/what_survives.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_MOVE_RA_001` | E2+RD | NEW |  | [placement_and_residency.md](concepts/placement_and_residency.md) |
| `FS_MOVE_RA_002` | E2+RD … | CONFIRMED |  | [driver_evolution.md](concepts/driver_evolution.md) |
| `FS_MOVE_RA_003` | RD | CONFIRMED |  | [placement_and_residency.md](concepts/placement_and_residency.md) |
| `FS_OTBL_001` | E2 | CONFIRMED |  | [object_table.md](structures/object_table.md) |
| `FS_OTBL_002` | — | ENRICHED |  | [object_table.md](structures/object_table.md) |
| `FS_OTBL_003` | — | CONFIRMED |  | [system_oids.md](structures/system_oids.md) |
| `FS_OTBL_004` | — | CONFIRMED |  | [parent_child_table.md](structures/parent_child_table.md) |
| `FS_OTBL_005` | — | CONFIRMED | 2 | [system_oids.md](structures/system_oids.md), [usn_journal.md](structures/usn_journal.md) |
| `FS_OTBL_RA_001` | E2 | ENRICHED | 2 | [system_oids.md](structures/system_oids.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_OTBL_RA_002` | E2 | NEW |  | [object_table.md](structures/object_table.md) |
| `FS_OTBL_RA_003` | E2 | CONFIRMED | 2 | [system_oids.md](structures/system_oids.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_OTBL_RA_004` | E2 | CONFIRMED | 2 | [VOLUME_INFORMATION.md](attributes/VOLUME_INFORMATION.md), [reparse_points.md](structures/reparse_points.md) |
| `FS_OTBL_RA_005` | E2 | CONFIRMED | 2 | [REPARSE.md](attributes/REPARSE.md), [system_oids.md](structures/system_oids.md) |
| `FS_OTBL_RA_006` | E2 | ENRICHED |  | [object_ids.md](concepts/object_ids.md) |
| `FS_OTBL_RA_007` | — | NEW |  | [object_table.md](structures/object_table.md) |
| `FS_OTBL_RA_008` | E2 | CONFIRMED | 5 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [hard_links.md](concepts/hard_links.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [what_survives.md](concepts/what_survives.md), [trash_table.md](structures/trash_table.md) |
| `FS_OTBL_RA_009` | RD | NEW |  | [object_table.md](structures/object_table.md) |
| `FS_OTBL_RA_010` | E2 | CONFIRMED | 2 | [object_ids.md](concepts/object_ids.md), [object_table.md](structures/object_table.md) |
| `FS_OTBL_SA_001` | E2 … | CONFIRMED |  | [object_table.md](structures/object_table.md) |
| `FS_OTBL_SA_002` | E2 | CONFIRMED |  | [object_ids.md](concepts/object_ids.md) |
| `FS_OTBL_SA_003` | E2 … | CONFIRMED |  | [object_table.md](structures/object_table.md) |
| `FS_OTBL_SA_004` | E2 … | CONFIRMED | 2 | [object_ids.md](concepts/object_ids.md), [system_oids.md](structures/system_oids.md) |
| `FS_OTBL_SA_005` | E2 | CONFIRMED | 2 | [object_ids.md](concepts/object_ids.md), [system_oids.md](structures/system_oids.md) |
| `FS_OTBL_SA_006` | E2 | CONFIRMED |  | [security_descriptors.md](structures/security_descriptors.md) |
| `FS_OTBL_SA_007` | E2 | CONFIRMED |  | [object_table.md](structures/object_table.md) |
| `FS_OTBL_SA_009` | E2 … | INFERRED |  | [object_ids.md](concepts/object_ids.md) |
| `FS_OTBL_SA_010` | E2 … | CONFIRMED |  | [parent_child_table.md](structures/parent_child_table.md) |
| `FS_PCHL_001` | — | CONFIRMED | 2 | [parent_child_table.md](structures/parent_child_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_PCTB_RA_001` | E2+RD | CONFIRMED | 3 | [parent_child_table.md](structures/parent_child_table.md), [schema_table.md](structures/schema_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_REPS_RA_001` | E2+RD | CONFIRMED | 2 | [REPARSE.md](attributes/REPARSE.md), [system_oids.md](structures/system_oids.md) |
| `FS_REPS_RA_002` | — | CONFIRMED | 2 | [EA_INFORMATION.md](attributes/EA_INFORMATION.md), [REPARSE_POINT.md](attributes/REPARSE_POINT.md) |
| `FS_REPS_RA_003` | E2+RD | CONFIRMED | 2 | [EA_INFORMATION.md](attributes/EA_INFORMATION.md), [REPARSE_POINT.md](attributes/REPARSE_POINT.md) |
| `FS_REPS_RA_004` | E2+RD | CONFIRMED | 2 | [attributes.md](concepts/attributes.md), [reparse_points.md](structures/reparse_points.md) |
| `FS_REPS_RA_005` | RD | CONFIRMED |  | [REPARSE_POINT.md](attributes/REPARSE_POINT.md) |
| `FS_RESD_SA_001` | E2+RD | CONFIRMED |  | [driver_evolution.md](concepts/driver_evolution.md) |
| `FS_RESD_SA_002` | E2 | CONFIRMED |  | [driver_evolution.md](concepts/driver_evolution.md) |
| `FS_SCHM_001` | E2 | CONFIRMED |  | [schema_table.md](structures/schema_table.md) |
| `FS_SCHM_RA_001` | E2 | CONFIRMED | 2 | [system_oids.md](structures/system_oids.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_SCHM_RA_002` | E2 … | CONFIRMED |  | [schema_table.md](structures/schema_table.md) |
| `FS_SCHM_RA_003` | E2 … | CONFIRMED |  | [schema_table.md](structures/schema_table.md) |
| `FS_SCHM_RA_004` | E2 … | CONFIRMED |  | [tiering.md](concepts/tiering.md) |
| `FS_SCHM_RA_005` | E1 | CONFIRMED | 4 | [attributes.md](concepts/attributes.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [schema_table.md](structures/schema_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_SCHM_RA_006` | E2 | CONFIRMED |  | [wsl_metadata.md](concepts/wsl_metadata.md) |
| `FS_SCHM_RA_007` | E2+RD | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_SCHM_RA_008` | E2 … | ENRICHED | 3 | [snapshots_versioning.md](concepts/snapshots_versioning.md), [schema_table.md](structures/schema_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_SCHM_RA_009` | RD | CONFIRMED |  | [schema_table.md](structures/schema_table.md) |
| `FS_SCHM_RA_010` | E1+RD | CONFIRMED | 2 | [schema_table.md](structures/schema_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_SCHM_RA_011` | RD | CONFIRMED |  | [schema_table.md](structures/schema_table.md) |
| `FS_SCHM_RA_012` | E2 … | CONFIRMED | 2 | [directory_entries.md](structures/directory_entries.md), [schema_table.md](structures/schema_table.md) |
| `FS_SCHM_RA_013` | E2 | CONFIRMED |  | [schema_table.md](structures/schema_table.md) |
| `FS_SECD_RA_001` | E2 | CONFIRMED | 3 | [what_survives.md](concepts/what_survives.md), [system_oids.md](structures/system_oids.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_SECD_RA_002` | E2 | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_SECD_RA_003` | — | CONFIRMED | 2 | [schema_table.md](structures/schema_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_SNAP_RA_001` | E2+RD | CONFIRMED | 7 | [I30_INDEX.md](attributes/I30_INDEX.md), [NAMED_DATA.md](attributes/NAMED_DATA.md), [SNAPSHOT.md](attributes/SNAPSHOT.md), [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [attributes.md](concepts/attributes.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_SUPB_001` | E2 | CONFIRMED | 5 | [bootstrap_chain.md](concepts/bootstrap_chain.md), [checksum_architecture.md](concepts/checksum_architecture.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [redundancy.md](concepts/redundancy.md), [supb.md](structures/supb.md) |
| `FS_SUPB_002` | — | CONFIRMED |  | [supb.md](structures/supb.md) |
| `FS_SUPB_003` | — | CONFIRMED |  | [supb.md](structures/supb.md) |
| `FS_SUPB_004` | — | CONFIRMED |  | [supb.md](structures/supb.md) |
| `FS_SUPB_005` | E2 | CONFIRMED | 5 | [bootstrap_chain.md](concepts/bootstrap_chain.md), [checksum_architecture.md](concepts/checksum_architecture.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [redundancy.md](concepts/redundancy.md), [supb.md](structures/supb.md) |
| `FS_SUPB_006` | — | CONFIRMED |  | [page_references.md](structures/page_references.md) |
| `FS_SUPB_007` | — | CONFIRMED | 5 | [bootstrap_chain.md](concepts/bootstrap_chain.md), [checksum_architecture.md](concepts/checksum_architecture.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [redundancy.md](concepts/redundancy.md), [supb.md](structures/supb.md) |
| `FS_SUPB_RA_001` | E2 | CONFIRMED |  | [page_header.md](structures/page_header.md) |
| `FS_SUPB_RA_002` | E2+RD | CONFIRMED |  | [checksum_architecture.md](concepts/checksum_architecture.md) |
| `FS_SUPB_RA_003` | — | CONFIRMED | 6 | [bootstrap_chain.md](concepts/bootstrap_chain.md), [checksum_architecture.md](concepts/checksum_architecture.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [redundancy.md](concepts/redundancy.md), [page_references.md](structures/page_references.md), [supb.md](structures/supb.md) |
| `FS_SUPB_RA_004` | — | CONFIRMED |  | [page_header.md](structures/page_header.md) |
| `FS_SUPB_RA_005` | — | CONFIRMED |  | [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md) |
| `FS_SUPB_RA_006` | — | CONFIRMED |  | [transactions_crash_consistency.md](concepts/transactions_crash_consistency.md) |
| `FS_UPCS_001` | — | CONFIRMED | 2 | [upcase_table.md](structures/upcase_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_UPGD_RA_001` | — | CONFIRMED |  | [supb.md](structures/supb.md) |
| `FS_VBR_001` | E2 … | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_002` | E2 | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_003` | E2 … | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_004` | — | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_005` | — | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_006` | E2 … | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_007` | E2 … | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_008` | E2 … | CONFIRMED |  | [cluster_page_size.md](concepts/cluster_page_size.md) |
| `FS_VBR_009` | E2 … | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_010` | E2 … | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_011` | — | CONFIRMED |  | [cluster_page_size.md](concepts/cluster_page_size.md) |
| `FS_VBR_012` | E2 … | CONTRADICTED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_013` | E2 … | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_RA_002` | E2 … | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_RA_004` | E2 | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_RA_005` | — | INFERRED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_RA_006` | — | INFERRED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_RA_007` | — | INFERRED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_RA_009` | — | INFERRED |  | [chkp.md](structures/chkp.md) |
| `FS_VBR_RA_010` | E2 … | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_RA_011` | RD | CONFIRMED |  | [driver_architecture.md](concepts/driver_architecture.md) |
| `FS_VBR_RA_012` | RD | CONFIRMED |  | [vbr.md](structures/vbr.md) |
| `FS_VBR_RA_013` | E2 | CONFIRMED | 3 | [redundancy.md](concepts/redundancy.md), [what_survives.md](concepts/what_survives.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `FS_VBR_RA_014` | — | CONFIRMED |  | [redundancy.md](concepts/redundancy.md) |
| `FS_VBR_RA_015` | E2 | CONFIRMED |  | [schema_table.md](structures/schema_table.md) |
| `FS_VBR_SA_013` | E2 … | INFERRED |  | [vbr.md](structures/vbr.md) |
| `FS_VINF_001` | E1 | CONFIRMED |  | [VOLUME_INFORMATION.md](attributes/VOLUME_INFORMATION.md) |
| `FS_VINF_002` | — | CONFIRMED |  | [volume_info.md](structures/volume_info.md) |
| `FS_VINF_RA_001` | — | CONFIRMED |  | [volume_info.md](structures/volume_info.md) |
| `FS_VOLI_RA_001` | E2 | CONFIRMED |  | [VOLUME_INFORMATION.md](attributes/VOLUME_INFORMATION.md) |
| `FS_VOLI_RA_002` | E2 | CONFIRMED | 2 | [VOLUME_INFORMATION.md](attributes/VOLUME_INFORMATION.md), [tiering.md](concepts/tiering.md) |
| `GN_ALLC_SA_001` | E2 … | NOT_TESTED |  | [allocators.md](structures/allocators.md) |
| `GN_AMGR_SA_001` | E2 | NOT_TESTED |  | [OBJ_LINK.md](attributes/OBJ_LINK.md) |
| `GN_ARCH_001` | E2 | CONFIRMED | 3 | [architecture.md](concepts/architecture.md), [what_is_refs.md](concepts/what_is_refs.md), [btree_node.md](structures/btree_node.md) |
| `GN_ARCH_002` | E2 | CONFIRMED | 5 | [architecture.md](concepts/architecture.md), [copy_on_write.md](concepts/copy_on_write.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [what_is_refs.md](concepts/what_is_refs.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `GN_ARCH_003` | E2 | CONFIRMED | 2 | [what_is_refs.md](concepts/what_is_refs.md), [container_table.md](structures/container_table.md) |
| `GN_ARCH_004` | E2 | ENRICHED | 2 | [what_is_refs.md](concepts/what_is_refs.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `GN_ARCH_005` | E1 … | CONFIRMED | 2 | [btree_node.md](structures/btree_node.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `GN_ARCH_006` | E2 | — |  | [driver_architecture.md](concepts/driver_architecture.md) |
| `GN_ARCH_RA_001` | E2 | CONFIRMED | 2 | [allocators.md](structures/allocators.md), [container_table.md](structures/container_table.md) |
| `GN_ARCH_RA_002` | — | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `GN_ARCH_SA_001` | E2 | NOT_TESTED |  | [architecture.md](concepts/architecture.md) |
| `GN_ARCH_SA_002` | E2 … | NOT_TESTED |  | [driver_architecture.md](concepts/driver_architecture.md) |
| `GN_BIN_SA_001` | E2 | NOT_TESTED |  | [driver_architecture.md](concepts/driver_architecture.md) |
| `GN_BPT_RA_001` | E2 | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_COMP_SA_001` | E2 | CONFIRMED |  | [compression.md](concepts/compression.md) |
| `GN_CROT_SA_001` | E2 … | NOT_TESTED |  | [container_index.md](structures/container_index.md) |
| `GN_DEDUP_SA_001` | E2 … | INFERRED |  | [block_refcount.md](structures/block_refcount.md) |
| `GN_EFS_SA_001` | E2 … | INFERRED |  | [EFS.md](attributes/EFS.md) |
| `GN_FOPS_SA_001` | E2 | NOT_TESTED |  | [architecture.md](concepts/architecture.md) |
| `GN_FOPS_SA_002` | E2 | NOT_TESTED |  | [copy_on_write.md](concepts/copy_on_write.md) |
| `GN_HEAT_SA_001` | E2 … | NOT_TESTED |  | [driver_architecture.md](concepts/driver_architecture.md) |
| `GN_HIER_SA_001` | E2 | NOT_TESTED |  | [windows_file_systems.md](concepts/windows_file_systems.md) |
| `GN_IDENT_RA_001` | RD | CONFIRMED |  | [file_ids.md](concepts/file_ids.md) |
| `GN_IDXH_001` | — | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IDXH_002` | — | ENRICHED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IDXH_003` | — | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IDXR_001` | E2 | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IDXR_002` | E2 | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IDXR_003` | E2 | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IDXR_004` | E2 | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IDXR_RA_005` | E2 | CONFIRMED | 2 | [directory_entries.md](structures/directory_entries.md), [schema_table.md](structures/schema_table.md) |
| `GN_IENT_001` | — | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IENT_002` | — | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IENT_003` | — | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IENT_004` | — | CONFIRMED |  | [directory_entries.md](structures/directory_entries.md) |
| `GN_IENT_005` | — | CONFIRMED | 2 | [btree_node.md](structures/btree_node.md), [parent_child_table.md](structures/parent_child_table.md) |
| `GN_IENT_006` | — | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_IMG_RA_001` | RD | CONFIRMED |  | [what_survives.md](concepts/what_survives.md) |
| `GN_IMP_SA_001` | E2 | NOT_TESTED |  | [driver_architecture.md](concepts/driver_architecture.md) |
| `GN_INS_SA_001` | E2 … | NOT_TESTED | 2 | [what_is_refs.md](concepts/what_is_refs.md), [vbr.md](structures/vbr.md) |
| `GN_INS_SA_002` | E2 | INFERRED | 2 | [driver_architecture.md](concepts/driver_architecture.md), [what_is_refs.md](concepts/what_is_refs.md) |
| `GN_INS_SA_003` | E2 | NOT_TESTED |  | [architecture.md](concepts/architecture.md) |
| `GN_IRP_SA_001` | E2 | NOT_TESTED |  | [architecture.md](concepts/architecture.md) |
| `GN_KSR_SA_001` | — | NOT_TESTED |  | [driver_architecture.md](concepts/driver_architecture.md) |
| `GN_OOP_SA_001` | — | NOT_TESTED |  | [architecture.md](concepts/architecture.md) |
| `GN_PAGE_001` | E1 | CONFIRMED | 2 | [page_header.md](structures/page_header.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `GN_PAGE_002` | — | CONFIRMED |  | [page_header.md](structures/page_header.md) |
| `GN_PAGE_003` | — | CONFIRMED |  | [page_header.md](structures/page_header.md) |
| `GN_PAGE_004` | E2 | CONFIRMED |  | [page_header.md](structures/page_header.md) |
| `GN_PAGE_005` | E2 | CONFIRMED |  | [page_header.md](structures/page_header.md) |
| `GN_PAGE_006` | — | CONFIRMED |  | [page_header.md](structures/page_header.md) |
| `GN_PAGE_007` | E2 | CONFIRMED | 3 | [btree_node.md](structures/btree_node.md), [page_header.md](structures/page_header.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `GN_PAGE_RA_001` | — | CONFIRMED |  | [page_header.md](structures/page_header.md) |
| `GN_PAGE_RA_002` | E2 | CONFIRMED | 2 | [page_header.md](structures/page_header.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `GN_PREF_001` | — | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `GN_PREF_002` | E2 | ENRICHED | 4 | [checksum_architecture.md](concepts/checksum_architecture.md), [integrity_streams.md](concepts/integrity_streams.md), [page_references.md](structures/page_references.md), [vbr.md](structures/vbr.md) |
| `GN_PREF_003` | — | CONFIRMED |  | [page_references.md](structures/page_references.md) |
| `GN_PREF_RA_004` | RD | CONFIRMED |  | [page_references.md](structures/page_references.md) |
| `GN_SNAP_SA_001` | E2 … | INFERRED | 4 | [SNAPSHOT.md](attributes/SNAPSHOT.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [what_survives.md](concepts/what_survives.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `GN_TREE_RP_003` | RD | CONFIRMED |  | [btree_node.md](structures/btree_node.md) |
| `GN_UTIL_SA_001` | E2 … | NOT_TESTED |  | [btree_node.md](structures/btree_node.md) |
| `GN_VCB_SA_001` | E2+RD | CONFIRMED |  | [driver_evolution.md](concepts/driver_evolution.md) |
| `GN_WSL_SA_001` | — | NOT_TESTED |  | [architecture.md](concepts/architecture.md) |
| `MD_ADS_RA_001` | RD | CONFIRMED |  | [NAMED_DATA.md](attributes/NAMED_DATA.md) |
| `MD_ADS_RA_002` | RD | CONFIRMED | 2 | [NAMED_DATA.md](attributes/NAMED_DATA.md), [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_ADS_RA_003` | E2+RD | CONFIRMED | 2 | [NAMED_DATA.md](attributes/NAMED_DATA.md), [driver_evolution.md](concepts/driver_evolution.md) |
| `MD_ADS_RA_004` | RD … | CONFIRMED | 2 | [NAMED_DATA.md](attributes/NAMED_DATA.md), [SNAPSHOT.md](attributes/SNAPSHOT.md) |
| `MD_ADS_RA_005` | RD | CONFIRMED |  | [NAMED_DATA.md](attributes/NAMED_DATA.md) |
| `MD_ATTR_001` | E2 … | CONFIRMED |  | [artifact_timeline.md](concepts/artifact_timeline.md) |
| `MD_ATTR_002` | E1 … | CONFIRMED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_003` | E1 … | CONFIRMED |  | [OBJ_LINK.md](attributes/OBJ_LINK.md) |
| `MD_ATTR_004` | E1 | NOT_TESTED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_005` | E2+RD | CONFIRMED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_006` | E1 | CONFIRMED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_007` | E1 … | INFERRED |  | [NAMED_DATA.md](attributes/NAMED_DATA.md) |
| `MD_ATTR_008` | E1 | CONFIRMED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_009` | — | INFERRED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_010` | E2 … | CONFIRMED | 2 | [EA_INFORMATION.md](attributes/EA_INFORMATION.md), [I30_INDEX.md](attributes/I30_INDEX.md) |
| `MD_ATTR_011` | E1 | — |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_ATTR_RA_002` | — | NEW |  | [version_detection.md](concepts/version_detection.md) |
| `MD_ATTR_RA_003` | — | CONFIRMED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_RA_004` | — | CONFIRMED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_RA_005` | E2+RD | CONFIRMED |  | [object_table.md](structures/object_table.md) |
| `MD_ATTR_RA_006` | E2+RD | CONFIRMED |  | [OBJ_LINK.md](attributes/OBJ_LINK.md) |
| `MD_ATTR_RA_007` | RD | CONFIRMED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_RA_008` | RD | CONFIRMED |  | [directory_entries.md](structures/directory_entries.md) |
| `MD_ATTR_RA_009` | E2+RD | CONFIRMED | 2 | [DATA.md](attributes/DATA.md), [EFS.md](attributes/EFS.md) |
| `MD_ATTR_RA_010` | E2+RD | CONFIRMED | 2 | [EA_INFORMATION.md](attributes/EA_INFORMATION.md), [REPARSE_POINT.md](attributes/REPARSE_POINT.md) |
| `MD_ATTR_RA_011` | E2+RD | CONFIRMED |  | [EA_INFORMATION.md](attributes/EA_INFORMATION.md) |
| `MD_ATTR_RA_012` | E2+RD | CONFIRMED | 2 | [EA_INFORMATION.md](attributes/EA_INFORMATION.md), [REPARSE_POINT.md](attributes/REPARSE_POINT.md) |
| `MD_ATTR_RA_013` | RD | CONFIRMED |  | [EA_INFORMATION.md](attributes/EA_INFORMATION.md) |
| `MD_ATTR_RA_014` | E2+RD | CONFIRMED |  | [directory_entries.md](structures/directory_entries.md) |
| `MD_ATTR_RA_015` | E1+RD | CONFIRMED | 2 | [I30_INDEX.md](attributes/I30_INDEX.md), [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_ATTR_RA_016` | RD | CONFIRMED | 2 | [REPARSE_POINT.md](attributes/REPARSE_POINT.md), [attributes.md](concepts/attributes.md) |
| `MD_ATTR_RA_017` | RD | CONFIRMED |  | [I30_INDEX.md](attributes/I30_INDEX.md) |
| `MD_ATTR_RA_018` | E2 | CONFIRMED | 3 | [NAMED_DATA.md](attributes/NAMED_DATA.md), [SNAPSHOT.md](attributes/SNAPSHOT.md), [snapshots_versioning.md](concepts/snapshots_versioning.md) |
| `MD_ATTR_RA_019` | E2+RD | CONFIRMED | 2 | [EA_INFORMATION.md](attributes/EA_INFORMATION.md), [attributes.md](concepts/attributes.md) |
| `MD_ATTR_RA_020` | E2+RD | CONFIRMED |  | [attributes.md](concepts/attributes.md) |
| `MD_ATTR_SA_001` | — | ENRICHED |  | [architecture.md](concepts/architecture.md) |
| `MD_CS_RA_001` | E2+RD | CONFIRMED |  | [upcase_table.md](structures/upcase_table.md) |
| `MD_CS_RA_002` | — | CONFIRMED |  | [reverse_index.md](structures/reverse_index.md) |
| `MD_CS_RA_003` | E2+RD | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_DATA_RA_001` | — | CONFIRMED | 2 | [extent_descriptors.md](structures/extent_descriptors.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_DATA_RA_002` | — | CONTRADICTED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DATA_RA_004` | — | CONFIRMED |  | [hard_links.md](concepts/hard_links.md) |
| `MD_DATA_RA_005` | — | CONFIRMED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_DATA_RA_006` | — | CONFIRMED |  | [hard_links.md](concepts/hard_links.md) |
| `MD_DATA_RA_007` | — | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DATA_RA_008` | E2+RD | CONTRADICTED |  | [DATA.md](attributes/DATA.md) |
| `MD_DATA_RA_009` | E2+RD | CONFIRMED | 2 | [DATA.md](attributes/DATA.md), [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DATA_RA_010` | E2+RD | CONFIRMED | 3 | [DATA.md](attributes/DATA.md), [NAMED_DATA.md](attributes/NAMED_DATA.md), [integrity_streams.md](concepts/integrity_streams.md) |
| `MD_DATA_RA_011` | E2 | CONFIRMED | 2 | [DATA.md](attributes/DATA.md), [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DATA_RA_012` | E2+RD | CONFIRMED |  | [directory_entries.md](structures/directory_entries.md) |
| `MD_DATA_RA_013` | E2+RD | CONFIRMED | 2 | [integrity_streams.md](concepts/integrity_streams.md), [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DATA_RA_014` | RD | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DATA_RA_015` | RD | CONFIRMED |  | [placement_and_residency.md](concepts/placement_and_residency.md) |
| `MD_DATA_RA_021` | RD | CONFIRMED |  | [directory_entries.md](structures/directory_entries.md) |
| `MD_DATA_RA_022` | E2+RD | CONFIRMED | 2 | [DATA.md](attributes/DATA.md), [placement_and_residency.md](concepts/placement_and_residency.md) |
| `MD_DATA_RA_023` | RD | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DATA_RA_024` | RD | CONFIRMED | 2 | [DATA.md](attributes/DATA.md), [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DATA_RA_025` | E2+RD | CONFIRMED | 2 | [DATA.md](attributes/DATA.md), [driver_evolution.md](concepts/driver_evolution.md) |
| `MD_DATA_RA_027` | RD | REFUTED | 2 | [NAMED_DATA.md](attributes/NAMED_DATA.md), [placement_and_residency.md](concepts/placement_and_residency.md) |
| `MD_DATA_RA_028` | RD | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DATA_RA_029` | RD | CONFIRMED |  | [DATA.md](attributes/DATA.md) |
| `MD_DATA_RA_030` | RD | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_DDIR_001` | E2 | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_DDIR_002` | — | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_DDIR_003` | — | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_DDIR_004` | — | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_DDIR_005` | — | CONFIRMED |  | [attributes.md](concepts/attributes.md) |
| `MD_DDIR_006` | — | CONFIRMED | 2 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [security_descriptors.md](structures/security_descriptors.md) |
| `MD_DEL_RA_001` | — | INFERRED |  | [deletion_recovery.md](concepts/deletion_recovery.md) |
| `MD_DEL_RA_003` | — | INFERRED |  | [deletion_recovery.md](concepts/deletion_recovery.md) |
| `MD_DEL_RA_004` | RD | CONFIRMED | 2 | [SNAPSHOT.md](attributes/SNAPSHOT.md), [deletion_recovery.md](concepts/deletion_recovery.md) |
| `MD_DISK_RA_003` | — | NEW |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_DISK_RA_004` | — | CONTRADICTED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_DISK_RA_006` | — | NEW |  | [EFS.md](attributes/EFS.md) |
| `MD_DISK_RA_008` | — | CONFIRMED |  | [deletion_recovery.md](concepts/deletion_recovery.md) |
| `MD_DISK_RA_009` | — | NEW |  | [reverse_index.md](structures/reverse_index.md) |
| `MD_DISK_RA_010` | — | CORRECTED |  | [file_ids.md](concepts/file_ids.md) |
| `MD_EFS_RA_001` | — | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_EFS_RA_002` | — | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_EFS_RA_003` | — | NEW | 2 | [EFS.md](attributes/EFS.md), [driver_evolution.md](concepts/driver_evolution.md) |
| `MD_EFS_RA_004` | E1+RD | CONFIRMED |  | [EFS.md](attributes/EFS.md) |
| `MD_EFS_RA_005` | E2+RD | CONFIRMED |  | [EFS.md](attributes/EFS.md) |
| `MD_EFS_RA_006` | RD | CONFIRMED |  | [EFS.md](attributes/EFS.md) |
| `MD_FTBL_001` | — | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_FTBL_002` | — | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_FTBL_003` | — | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_FTBL_004` | — | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_FTBL_005` | — | CONFIRMED |  | [directory_entries.md](structures/directory_entries.md) |
| `MD_FTBL_006` | — | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_FTBL_007` | E2 | CONFIRMED |  | [NAMED_DATA.md](attributes/NAMED_DATA.md) |
| `MD_INTG_RA_001` | E2+RD | CONFIRMED | 2 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [integrity_streams.md](concepts/integrity_streams.md) |
| `MD_INTG_RA_005` | RD | CONFIRMED |  | [NAMED_DATA.md](attributes/NAMED_DATA.md) |
| `MD_LK_RA_001` | — | INFERRED |  | [file_systems.md](concepts/file_systems.md) |
| `MD_LK_RA_002` | — | CONFIRMED |  | [reparse_points.md](structures/reparse_points.md) |
| `MD_LK_RA_003` | — | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_LK_RA_004` | — | INFERRED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_LK_RA_005` | E2+RD | CONFIRMED |  | [OBJ_LINK.md](attributes/OBJ_LINK.md) |
| `MD_LK_RA_006` | E2+RD | CONFIRMED |  | [OBJ_LINK.md](attributes/OBJ_LINK.md) |
| `MD_LK_RA_007` | E2+RD | CONFIRMED |  | [OBJ_LINK.md](attributes/OBJ_LINK.md) |
| `MD_LK_RA_008` | E2+RD | CONFIRMED |  | [OBJ_LINK.md](attributes/OBJ_LINK.md) |
| `MD_LK_RA_009` | E2+RD | CONFIRMED |  | [OBJ_LINK.md](attributes/OBJ_LINK.md) |
| `MD_MISC_001` | — | NOT_TESTED |  | [timestomp_detection.md](concepts/timestomp_detection.md) |
| `MD_PLAC_RA_001` | E2 | CONFIRMED |  | [placement_and_residency.md](concepts/placement_and_residency.md) |
| `MD_SECT_001` | E2 | CONFIRMED | 2 | [system_oids.md](structures/system_oids.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_SF_RA_002` | — | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_SF_RA_004` | — | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_SF_RA_005` | RD | CONFIRMED |  | [extent_descriptors.md](structures/extent_descriptors.md) |
| `MD_SI_RA_001` | E2+RD | CONFIRMED |  | [hard_links.md](concepts/hard_links.md) |
| `MD_SI_RA_002` | E2+RD | CONFIRMED | 3 | [DATA.md](attributes/DATA.md), [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_SI_RA_003` | RD | CONTRADICTED |  | [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_SI_RA_004` | RD | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_SI_RA_005` | E2+RD | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_SI_RA_006` | E2+RD | CONFIRMED | 2 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [integrity_streams.md](concepts/integrity_streams.md) |
| `MD_SI_RA_007` | E2+RD | CONFIRMED | 2 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [driver_evolution.md](concepts/driver_evolution.md) |
| `MD_SI_RA_008` | E2+RD | CONFIRMED | 4 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [carrier_categories.md](concepts/carrier_categories.md), [file_ids.md](concepts/file_ids.md), [ntfs_comparison.md](concepts/ntfs_comparison.md) |
| `MD_SI_RA_009` | RD | CONFIRMED | 2 | [carrier_categories.md](concepts/carrier_categories.md), [hard_links.md](concepts/hard_links.md) |
| `MD_SI_RA_010` | E2+RD | CONFIRMED | 3 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [carrier_categories.md](concepts/carrier_categories.md), [file_ids.md](concepts/file_ids.md) |
| `MD_SI_RA_011` | E2+RD | INFERRED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_SI_RA_012` | RD | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_SI_RA_013` | E2+RD | CONFIRMED | 2 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [usn_journal.md](structures/usn_journal.md) |
| `MD_SI_RA_014` | E2+RD | INFERRED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_SI_RA_015` | E2+RD | CONTRADICTED | 2 | [usn_journal.md](structures/usn_journal.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_SI_RA_016` | E2 | CONFIRMED |  | [DATA.md](attributes/DATA.md) |
| `MD_SI_RA_017` | E2 | CONFIRMED |  | [directory_entries.md](structures/directory_entries.md) |
| `MD_SI_SA_001` | E2 | NOT_TESTED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_SI_SA_002` | E2 | NOT_TESTED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_SNAP_RA_001` | — | NEW |  | [snapshots_versioning.md](concepts/snapshots_versioning.md) |
| `MD_SNAP_RA_002` | — | INFERRED | 4 | [SNAPSHOT.md](attributes/SNAPSHOT.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [what_survives.md](concepts/what_survives.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_SNAP_RA_003` | E2 | CONFIRMED | 5 | [SNAPSHOT.md](attributes/SNAPSHOT.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [what_survives.md](concepts/what_survives.md), [extent_descriptors.md](structures/extent_descriptors.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_SNAP_RA_004` | — | NEW |  | [SNAPSHOT.md](attributes/SNAPSHOT.md) |
| `MD_SNAP_RA_005` | E2+RD | CONFIRMED | 4 | [NAMED_DATA.md](attributes/NAMED_DATA.md), [SNAPSHOT.md](attributes/SNAPSHOT.md), [snapshots_versioning.md](concepts/snapshots_versioning.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_SNAP_RA_006` | E2+RD | CONFIRMED | 2 | [snapshots_versioning.md](concepts/snapshots_versioning.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_SNAP_RA_007` | RD … | CONFIRMED | 2 | [snapshots_versioning.md](concepts/snapshots_versioning.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_SNAP_RA_008` | RD | CONFIRMED | 2 | [SNAPSHOT.md](attributes/SNAPSHOT.md), [snapshots_versioning.md](concepts/snapshots_versioning.md) |
| `MD_SNAP_RA_009` | RD | CONFIRMED | 2 | [SNAPSHOT.md](attributes/SNAPSHOT.md), [placement_and_residency.md](concepts/placement_and_residency.md) |
| `MD_SNAP_RA_010` | RD | CONFIRMED | 2 | [SNAPSHOT.md](attributes/SNAPSHOT.md), [timestomp_detection.md](concepts/timestomp_detection.md) |
| `MD_TS_RA_001` | — | CONFIRMED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_TS_RA_002` | — | INFERRED |  | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md) |
| `MD_TS_RA_003` | — | CONFIRMED |  | [timestomp_detection.md](concepts/timestomp_detection.md) |
| `MD_TS_RA_004` | — | CONFIRMED | 2 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [artifact_timeline.md](concepts/artifact_timeline.md) |
| `MD_TS_RA_005` | E2 | CONFIRMED | 2 | [schema_table.md](structures/schema_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_TS_RA_007` | E2+RD | CONFIRMED |  | [timestomp_detection.md](concepts/timestomp_detection.md) |
| `MD_TS_RA_008` | E2+RD | CONFIRMED | 5 | [STANDARD_INFORMATION.md](attributes/STANDARD_INFORMATION.md), [artifact_timeline.md](concepts/artifact_timeline.md), [forensic_analysis_workflow.md](concepts/forensic_analysis_workflow.md), [hard_links.md](concepts/hard_links.md), [timestomp_detection.md](concepts/timestomp_detection.md) |
| `MD_TS_RA_009` | RD | CONFIRMED |  | [timestomp_detection.md](concepts/timestomp_detection.md) |
| `MD_TS_RA_010` | E2 | CONFIRMED |  | [timestomp_detection.md](concepts/timestomp_detection.md) |
| `MD_TS_RA_011` | RD | CONFIRMED |  | [timestomp_detection.md](concepts/timestomp_detection.md) |
| `MD_UNSUP_RA_001` | — | NEW | 3 | [attributes.md](concepts/attributes.md), [schema_table.md](structures/schema_table.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_USN_RA_001` | — | CONTRADICTED | 2 | [file_ids.md](concepts/file_ids.md), [usn_journal.md](structures/usn_journal.md) |
| `MD_USN_RA_002` | — | NEW | 2 | [file_ids.md](concepts/file_ids.md), [usn_journal.md](structures/usn_journal.md) |
| `MD_USN_RA_003` | — | NEW |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_USN_RA_004` | E2+RD | CONFIRMED | 3 | [attributes.md](concepts/attributes.md), [usn_journal.md](structures/usn_journal.md), [tool_artifact_map.md](tools/tool_artifact_map.md) |
| `MD_USN_RA_005` | E2+RD | CONFIRMED |  | [file_ids.md](concepts/file_ids.md) |
| `MD_USN_RA_006` | E2 | NEW |  | [file_ids.md](concepts/file_ids.md) |
| `MD_USN_RA_007` | RD | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_USN_RA_008` | RD | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_USN_RA_009` | RD | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_USN_RA_010` | E2+RD | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_USN_SA_001` | E2 … | CONFIRMED |  | [usn_journal.md](structures/usn_journal.md) |
| `MD_USN_SA_002` | E2 … | CONFIRMED |  | [chkp.md](structures/chkp.md) |

## 3. Register rows no page cites

The triage list: **16 of 503** register rows are cited by no page in
`attributes/, structures/, concepts/, tools/, examples/, methodology/` — the denominator is the content directories, because those are the
pages a reader reaches. A row here is one of three things, and the triage decides which:

- **internal-only** — a tool/verification fact with no reader-facing statement to make;
- **undocumented** — reader-facing knowledge with no page, so a page (or a paragraph) is owed;
- **duplicate** — the same fact as a cited row, to be merged into it.

Rows read in register order. A mention in `changelog.md` does not count as documentation.

| Finding | Static | Disk | Class (`register_triage.tsv`) |
|---------|--------|------|-------|
| `FS_VINF_003` | E2 | CONFIRMED | internal-only: contradicted prior-work claim (a backup block row at key 0x540): nothing to state |
| `MD_MISC_002` | — | NOT_TESTED | internal-only: a placeholder ("unknown metadata file, future work"), not a fact |
| `AP_WIPE_001` | — | NOT_TESTED | internal-only: a prior-work claim (wiping tools told apart by log opcode patterns) not tested here; no page states it until it is |
| `GN_XVER_SA_001` | — | NOT_TESTED | internal-only: function counts of the driver comparison: analysis statistics |
| `AP_LGFL_RA_003` | E2 | CONTRADICTED | internal-only: retracted (the log data area does not hold page images) |
| `MD_DATA_RA_003` | — | INFERRED | duplicate: superseded by FN_LINK_002 (the type-0x30 value fields of a hard-linked file) |
| `GN_DTCT_RA_001` | E2 | CONFIRMED | internal-only: a test result of the tools: a BitLocker or NTFS volume is refused as not ReFS |
| `MD_TS_RA_006` | — | CONFIRMED | internal-only: the object layout of one lab image |
| `MD_SF_RA_001` | — | NEW | internal-only: a lab procedure (how the sparse test files were made) |
| `MD_DEL_RA_002` | — | CONTRADICTED | internal-only: contradicted (an Explorer deletion's $R / $I records as first described) |
| `MD_ATTR_RA_001` | — | CONTRADICTED | internal-only: contradicted (a "complete" catalog of attribute values) |
| `FN_MISC_001` | — | NOT_TESTED | internal-only: prior work on format 1.2, outside the corpus |
| `GN_MISC_001` | — | NOT_TESTED | internal-only: a prior-work remark on format 3.2, outside the corpus |
| `GN_MISC_002` | — | NOT_TESTED | internal-only: a prior-work reference (format 1.2 read with EnCase) |
| `FS_OTBL_SA_008` | E2 … | CONFIRMED | internal-only: a driver call chain (RefsOpenFcbById) behind rows the pages cite |
| `MD_DATA_RA_026` | RD | CONFIRMED | internal-only: a defect of this project's reader, fixed in 1.10 |

---
*Generated by `build_docs_index.py` — 95 pages indexed, 487 of 503 register rows cited, 163 cited on more than one page. The claim register is `analysis/reference_table.csv`.*
