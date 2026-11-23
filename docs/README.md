# ReFS Documentation

Reverse engineering documentation for the Resilient File System (ReFS), covering versions 3.4 through 3.14 and the
Insider builds 29574 to 29683.

It began as a master thesis, and combines:

- static analysis of `refs.sys`: twelve builds, eleven with Microsoft's published symbols (the list is in
  [Driver builds](methodology/driver_builds.md));
- raw disk analysis of 124 readable ReFS disk images (97 distinct once byte-identical copies are set aside) of five
  format versions.

> **[Knowledge Map](KNOWLEDGE_MAP.md)** — the single index from any topic to its authoritative sources
> (master-reference section, findings, evidence).
>
> - **Directory indexes:** [structures](structures/README.md) · [concepts](concepts/README.md) ·
>   [attributes](attributes/README.md) · [examples](examples/README.md).
> - **[How this was verified](methodology.md)** — the dual-evidence methodology, evidence levels, and how to trace
>   any claim to its provenance.

**Known issues in 1.14.0:** the known limits that can change what an examiner reports (what the tools do not read or do not check), each with what to do — see [Known issues in 1.14.0](tools/known_issues.md).

**New to ReFS forensics?** Start with:

- [A first examination](examples/first_examination.md) (six steps on a sample image);
- the [Forensic Analysis Workflow](concepts/forensic_analysis_workflow.md) (end-to-end runbook);
- the [Carrier categories](concepts/carrier_categories.md) (how the artifacts are organised);
- [What Survives](concepts/what_survives.md) (delete / format / upgrade).

## Quick Start

1. [Architecture](concepts/architecture.md) -- two-layer driver model and three-tier IRP dispatch
2. [Bootstrap Chain](concepts/bootstrap_chain.md) -- how to traverse from VBR to any table
3. [Version Evolution](concepts/version_evolution.md) -- what changed across v3.4 through Insider
4. [How this was verified](methodology.md) -- the dual-evidence method and how to trace any claim

## Core Concepts

| Page | Topic |
|------|-------|
| [Architecture](concepts/architecture.md) | Refs\*/Cms\* two-layer model, three-tier IRP dispatch |
| [Bootstrap Chain](concepts/bootstrap_chain.md) | GPT → VBR → SUPB → CHKP → Container Table → target |
| [Virtual Addressing](concepts/virtual_addressing.md) | VLCN-to-PLCN translation via Container Table |
| [Cluster and Page Size](concepts/cluster_page_size.md) | 4 KiB vs 64 KiB clusters, page size derivation |
| [Copy-on-Write](concepts/copy_on_write.md) | Fundamental update model and forensic implications |
| [Checksum Architecture](concepts/checksum_architecture.md) | CRC64/SHA-256 Merkle tree, page reference sizes |
| [Record placement and data residency](concepts/placement_and_residency.md) | Where a file's record is stored (embedded or split) and where its bytes are (inline or in extents), with the byte-level detail |
| [$STANDARD_INFORMATION](attributes/STANDARD_INFORMATION.md) | Timestamp fields and version-dependent layout |
| [Timestomping Detection](concepts/timestomp_detection.md) | Multi-source timestamp-tamper detection (hard-link names' Created times + $SI change-time + USN journal + volume bound) |
| [Attributes](concepts/attributes.md) | Where a file's and a directory's attributes sit: the two levels of B+-tree, the sub-record set, and how to tell a genuine attribute from noise |
| [Version Evolution](concepts/version_evolution.md) | v3.4 through Insider structural changes |
| [Version Detection](concepts/version_detection.md) | Classifying upgrade state from CHKP flags |
| [Deletion Recovery](concepts/deletion_recovery.md) | Five recovery methods: Trash Table, checkpoint differential, orphan scan, stream-snapshot reconstruction, B+-tree node-slack carve |
| [What Survives](concepts/what_survives.md) | Artifact-vs-event survival matrix (delete / format / upgrade / unmount / crash) |
| [Carrier Categories](concepts/carrier_categories.md) | Carrier's five data categories applied to ReFS |
| [Tool-to-Artifact Map](tools/tool_artifact_map.md) | For each forensic goal, which `forefst.py` / `refsanalysis.py` invocation surfaces it |
| [Hard Links](concepts/hard_links.md) | Multi-name files: shared FileRef identity, where the backing record's `$SI+0x70` holds the count |
| [Snapshots and Versioning](concepts/snapshots_versioning.md) | `$SNAPSHOT` stream snapshots and prior-content recovery |
| [Integrity Streams](concepts/integrity_streams.md) | Per-file opt-in block checksums (file attribute `0x8000`, `IntegrityStream`) |
| [WSL / Linux Metadata](concepts/wsl_metadata.md) | `$LXUID/$LXGID/$LXMOD/$LXDEV` EAs and WSL device nodes |
| [Artifact Timeline](concepts/artifact_timeline.md) | Timestamp sources and super-timeline construction |
| [Transactions / Crash Consistency](concepts/transactions_crash_consistency.md) | Redo-only MLog + checkpoint atomicity |
| [Redundancy](concepts/redundancy.md) | Boot-sector, superblock, checkpoint copies |
| [Object IDs](concepts/object_ids.md) | The volume-wide 64-bit directory identity — the reliable cross-table join key |
| [File IDs](concepts/file_ids.md) | How a file (which has no OID) is identified: the FileRef = creation directory + ordinal |
| [OID Allocation](concepts/oid_allocation.md) | Monotonic counter, gaps as evidence of a deletion or a failed creation |
| [Space Allocation](concepts/allocation_space_mgmt.md) | Three-tier bitmap allocator (Medium / Container / Small) |
| [Compression](concepts/compression.md) | Per-container 24H2 volume compression |
| [Deduplication](concepts/deduplication.md) | Opt-in post-process block sharing |
| [Tiered Storage](concepts/tiering.md) | Fast/slow tier relocation and the heat engine |
| [What ReFS Is](concepts/what_is_refs.md) | What ReFS is, why it exists, and where it is used |
| [Driver builds analysed](methodology/driver_builds.md) | The `refs.sys` builds read, and how each one was read |
| [Driver Evolution](concepts/driver_evolution.md) | What changed from one build to the next, and the functions that change a file's storage |
| [Metadata bundle](tools/metadata_bundles.md) | What an `export metadata` bundle contains, and what it does not |
| [File Systems](concepts/file_systems.md) | General file system background |
| [Windows File Systems](concepts/windows_file_systems.md) | Windows I/O stack and driver model |

## On-Disk Structures

### Bootstrap Chain

| Page | Structure |
|------|-----------|
| [VBR](structures/vbr.md) | Volume Boot Record (sector 0) |
| [SUPB](structures/supb.md) | Superblock (LCN 0x1E) |
| [CHKP](structures/chkp.md) | Checkpoint (13 root pointers) |

### B+-Tree Engine

| Page | Structure |
|------|-----------|
| [Page Header](structures/page_header.md) | 80-byte common metadata header |
| [Page References](structures/page_references.md) | Three formats: 104B, 48B, 72B |
| [B+-Tree Node](structures/btree_node.md) | MSB+ page format, inner/leaf nodes |

### System Tables (13 Roots)

| Page | Structure |
|------|-----------|
| [Object Table](structures/object_table.md) | OID-to-LCN mapping (roots 0/5) |
| [Schema Table](structures/schema_table.md) | Key-comparison rules (roots 3/9); attribute schemas: 12 on v3.4, 16 on v3.14 (18 distinct across all versions) |
| [Container Table](structures/container_table.md) | VLCN-to-PLCN translation (roots 7/8) |
| [Parent-Child Table](structures/parent_child_table.md) | Directory hierarchy (root 4) |
| [Allocators](structures/allocators.md) | Three-tier allocation: Medium (1), Container (2), Small (12) |
| [Block Refcount](structures/block_refcount.md) | Shared block counts (root 6) |
| [Container Index](structures/container_index.md) | What a container's Container Table row does not hold: a compacted container's bitmap, a compressed container's headers (root 10) |
| [Integrity State](structures/integrity_state.md) | Per-range integrity tracking (root 11) |
| [System OIDs](structures/system_oids.md) | All system object identifiers |

### Metadata Structures

| Page | Structure |
|------|-----------|
| [Directory Entries](structures/directory_entries.md) | Type 0x30 rows, embedded and split (index-entry) layouts |
| [Reverse Index (Type 0x20)](structures/reverse_index.md) | Per-object FileId-resolution index (name ↔ FileId ↔ home dir) |
| [Extent Records](structures/extent_descriptors.md) | Extent records (the rows of the extent map inside `$DATA`), VCN-to-VLCN mapping |
| [Reparse Points](structures/reparse_points.md) | Global reparse-point index table (24-byte key, OID 0x540/0x541) |
| [Security Descriptors](structures/security_descriptors.md) | OID 0x530 single-table model (SecurityId → descriptor) |
| [Upcase Table](structures/upcase_table.md) | Unicode case-folding |
| [Volume Info](structures/volume_info.md) | OIDs 0x500 / 0x501 (label, creation and last-mount times, version, flags) |
| [Trash Table](structures/trash_table.md) | Async deletion queue (OID 0x0D) |

### Recovery Structures

| Page | Structure |
|------|-----------|
| [MLog](structures/mlog.md) | Metadata log (redo-only journaling) |
| [USN Journal](structures/usn_journal.md) | V3 format with 128-bit file IDs |

## Attributes

The **[Attributes — Forensic Reference](attributes/README.md)** is the entry point: the catalog of the real ReFS attributes, the NTFS attribute names that have no ReFS equivalent, the on-disk layout, and the forensically important elements.

Byte-level detail pages: [$DATA](attributes/DATA.md) · [$STANDARD_INFORMATION](attributes/STANDARD_INFORMATION.md) · [$OBJ_LINK](attributes/OBJ_LINK.md) · [$I30_INDEX](attributes/I30_INDEX.md) · [$EA_INFORMATION / $EA](attributes/EA_INFORMATION.md) · [$EFS](attributes/EFS.md) · [$SNAPSHOT](attributes/SNAPSHOT.md) · [$NAMED_DATA](attributes/NAMED_DATA.md) · [$REPARSE_POINT](attributes/REPARSE_POINT.md) · [Reparse Index](attributes/REPARSE.md) · [$VOLUME_INFORMATION](attributes/VOLUME_INFORMATION.md)

## Driver Internals

| Page | Topic |
|------|-------|
| [Driver Interface](concepts/driver_architecture.md) | Import tables, embedded libraries, subsystem growth, IRP handlers |

(The two-layer driver model is in [Architecture](concepts/architecture.md), listed under Core Concepts.)

## Research

| Page | Topic |
|------|-------|
| [NTFS Comparison](concepts/ntfs_comparison.md) | Structural mapping for NTFS practitioners |

## Tools

| Page | Tool |
|------|------|
| [forefst.py](tools/forefst.md) | Unified forensic tool — timeline-ready listings, deleted/CoW recovery, and the forensic suite (USN, MLog, timeline, timestomp, extract, security, reparse, deleted, recyclebin, snapshots, dataruns, integrity, export, specials) |
| [refsanalysis.py](tools/refsanalysis.md) | Structure / lab tool — decode one on-disk structure at a time (VBR, SUPB, CHKP, object/schema/container tables, …) |

## Examples

### Worked walkthroughs (step-by-step investigations)

| Walkthrough | Goal |
|-------------|------|
| [Decode the VBR by hand](examples/decode_vbr_by_hand.md) | Read every VBR field from a hexdump → version, cluster size, checksum algorithm, container size (no tool) |
| [A first examination](examples/first_examination.md) | Six steps of a first examination, with what `forefst` shows at each and what not to conclude from it |
| [Find a deleted file](examples/find_a_deleted_file.md) | Run the `deleted` command's recovery methods on one image, and read which method finds what |
| [Track a file across a rename and a move](examples/track_a_file_across_moves.md) | Follow one file by its FileRef through the change journal, and find it on disk after the move |
| [Detect timestomping](examples/detect_timestomping.md) | Cross `$SI` change-time vs USN journal vs volume-creation bound to flag a tampered timestamp |
| [Read a hard-link group](examples/read_a_hard_link_group.md) | Resolve every name of one physical object via home-backref + child-ordinal, confirmed by size (or the backing's back-pointers) |
| [Recover credentials and prior versions](examples/recover_credentials_and_prior_versions.md) | Credentials, alternate data streams and earlier versions of a file, on one volume |
| [Identify native vs upgraded](examples/identify_native_vs_upgraded.md) | Classify volume state from CHKP flags (0x002 / 0x602 / 0x682) and the VBR fields an upgrade leaves unchanged |

### Raw tool dumps

| File | Content |
|------|---------|
| [VBR Win10](examples/vbr_win10.txt) | VBR output from a v3.4 volume |
| [VBR Win11](examples/vbr_win11.txt) | VBR output from a v3.14 volume |
| [Summary Win10](examples/summary_win10.txt) | Full volume summary (v3.4, 2 TB) |
| [Summary Win11](examples/summary_win11.txt) | Full volume summary (v3.14, 2 TB) |
| [Schema Win11](examples/schema_win11.txt) | Schema Table dump (v3.14) |

## Reference

| Page | Content |
|------|---------|
| [Methodology](methodology.md) | How every claim was verified; evidence levels; tracing provenance |
| [Glossary](glossary.md) | Key terms and definitions |
| [Format support](format_support.md) | Which ReFS formats each area was **confirmed on** by a measurement on an image — a floor, with the statements confirmed without a recorded format, and those not confirmed on an image, in columns of their own |
| [Changelog](changelog.md) | Release history |
