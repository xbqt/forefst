# Glossary

Key terms used throughout the ReFS documentation.

## Addressing and Layout

**VLCN** (Virtual Logical Cluster Number)
: A cluster address in ReFS's virtual address space. Not a direct physical disk address. Must be translated through the Container Table to obtain a PLCN.

**PLCN** (Physical Logical Cluster Number)
: The actual on-disk cluster address after Container Table translation. This is the byte offset into the volume image.

**VCN** (Virtual Cluster Number)
: A logical cluster offset within a single file's data. Analogous to NTFS VCN. Maps to a VLCN through the file's extent table.

**LCN** (Logical Cluster Number)
: Generic term for a cluster address. In ReFS context, may be virtual (VLCN) or physical (PLCN) depending on the structure. The Container Table and Small Allocator use real (physical) LCNs; most other structures use virtual LCNs.

**CPC** (Clusters Per Container)
: Number of clusters in a 64 MiB container. 16,384 for 4 KiB clusters; 1,024 for 64 KiB clusters. Used in address translation: `container_index = vlcn >> CPC.bit_length()` (shift = 15 for 4 KiB, 11 for 64 KiB).

**Container**
: A fixed 64 MiB region of the volume. The volume is divided into containers, each tracked by a row in the Container Table.

**Allocator**
: ReFS's free-space manager — a three-tier hierarchy (**Container**, **Medium**, **Small** allocator) sharing schema `0xe010` and an identical bitmap row format, differing only in the region they manage and how their addresses resolve. The Small Allocator (root 12) and the Container Table (roots 7, 8) use real **physical** LCNs — the bootstrap exception underlying virtual addressing. Driver `CmsAllocator` (v3.14). See [Allocator Tables](structures/allocators.md).

## Structures

**VBR** (Volume Boot Record)
: 512-byte structure at sector 0 providing format parameters: cluster size, version, checksum mode.

**SUPB** (Superblock)
: Fixed-location anchor at cluster 30. Stores the Volume GUID and pointers to the two checkpoints.

**CHKP** (Checkpoint)
: Atomic commit point. Two alternating checkpoints, each holding the 13 root table pointers. The copy with the higher virtual clock is current.

**MSB+** (Minstore B+-tree page)
: A node of any B+-tree. All ReFS metadata tables are stored as MSB+ pages. The ASCII signature `MSB+` identifies these pages.

**MLog** (Metadata Log)
: Write-ahead transaction log for crash recovery. Contains redo-only records (no undo). Located at a fixed physical LCN.

**Redo Opcode**
: The operation type in an `_SmsRedoRecord` entry (offset 0x04, u32). The dispatched ranges are contiguous: v3.4 = 29 values 0x00–0x1C (0 gaps); v3.14 = 44 values 0x00–0x2B, of which only 0x17 returns an explicit error (NTSTATUS `0xC0000427`, the generic unhandled-opcode status -- the same error as out-of-range opcodes). Dispatched by `CmsLogRedoQueue::PerformRedo`. See [MLog](structures/mlog.md).

**OID** (Object Identifier)
: A 64-bit, monotonically increasing, never-reused identifier for every file and directory on the volume. Allocated from a counter; lower OID = earlier creation.

**FileId** (128-bit, USN V3)
: The 16-byte file identifier carried in USN V3 records. Upper 64 bits = the **home directory's OID** (volume-unique); lower 64 bits = the **child ordinal** (`NextFileId`, a per-directory counter that is reused across directories). It identifies a child *relative to its home directory* — the lower half alone is not a volume-wide identity. See [Object IDs and FileIds](concepts/object_ids_fileids.md).

**FCB** (File Control Block)
: Per-file driver state in kernel memory. Not an on-disk structure.

**SCB** (Stream Control Block)
: Per-stream state in kernel memory.

**IRP** (I/O Request Packet)
: The Windows kernel structure that carries a single I/O operation (create, read, write, …) to the driver. The ReFS driver's upper layer dispatches IRPs through a three-tier handler. Not an on-disk structure. See [Architecture](concepts/architecture.md).

**Page reference**
: A pointer from a parent B+-tree page to a child page that also carries the child's checksum — the Merkle link that makes the tree self-verifying. Its size depends on version **and** checksum type: **104 B** (v3.4), **48 B** (CRC64, v3.10+), **72 B** (SHA-256). See [Page References](structures/page_references.md).

**Row type**
: The type marker on a B+-tree key/row, identifying what the row holds: **0x10** = an object's *own-row* (carries `$SI`); **0x30** = a filename / directory entry (and a resident file's value); **0x40** = an *extent record* (a non-resident file's data runs); **0x20** = the *reverse index* (FileId → name / home directory). See [Directory Entries](structures/directory_entries.md).

**Embedded sub-record**
: A nested attribute packed **inside** a B+-tree row value rather than given its own row — how `$DATA`, ADS, `$SNAPSHOT`, `$EA` and `$EFS` ride inside a directory-entry value. A leading marker distinguishes **0x80000001** (single-instance) from **0x80000002** (multi-instance). See [Directory Entries](structures/directory_entries.md).

## Update Model

**CoW** (Copy-on-Write)
: ReFS's fundamental update model. No metadata page is modified in place; a new copy is written and pointers are updated up to the root. Also called write-to-new or allocate-on-write.

**Merkle Tree**
: The integrity chain formed by page references. Each parent stores a checksum of its children, anchored at the checkpoint. A verified checkpoint vouches for everything beneath it.

**Virtual Clock**
: A monotonically increasing counter in the checkpoint header. Incremented with each transaction commit. The checkpoint with the higher clock is current.

## Checksums

**CRC64 (custom polynomial)**
: The primary metadata checksum algorithm from v3.10+. Reflected CRC64 with the **custom** polynomial `0x9A6C9329AC4BC9B5` (driver `ClMulCsCrc64`) — **NOT ECMA-182** (GN_PREF_002, RD-verified by `forefst.refs_crc64`, 0 mismatches). Stored in page references and verified at mount on v3.14.

**CRC32-C**
: Block self-descriptor checksum **type 0x01** (CRC32-C), used only on the SUPB/CHKP self-descriptor — **not** page references, which use CRC64. It is *not* the SUPB/CHKP block integrity digest — those carry a **cluster-size-dependent self-checksum** (CRC32-C/4B on 4K-cluster, CRC64/8B on 64K, SHA-256/32B on SHA-256 volumes), verified at mount and self-healed (FS_SUPB_007, FS_SUPB_RA_003).

**CmsChecksumNone**
: A stub class in the v3.4 driver whose VerifyChecksum always returns TRUE. Explains why v3.4 metadata checksums are written but never verified.

## Tables

**Object Table**
: Master OID-to-location mapping. Every persistent object has one entry. Roots #0 and #5 (failover pair).

**Container Table**
: Maps virtual container IDs to physical disk locations. Roots #7 and #8 (failover pair). Uses real (physical) LCNs.

**Schema Table**
: Self-describing table of key-comparison rules. One entry per table type. Roots #3 and #9 (failover pair).

**Parent-Child Table**
: Encodes directory-to-directory relationships. Root #4. A pure set/index with 48-byte rows.

**Trash Table**
: Deferred-deletion queue (OID 0x0D). Holds files whose names have been removed but whose storage has not been reclaimed.

**Block Refcount Table**
: Tracks shared data blocks for deduplication, snapshots, and clones. Root #6. Populated only on v3.14 volumes with sharing features enabled.

## Storage Model

**Resident / Non-resident**
: Whether a stream's bytes live **inline** in the B+-tree row value (*resident* — small streams) or in separate **on-disk extent clusters** referenced by an extent table (*non-resident* — larger streams; e.g. an ADS promotes at ≥ 2 KB). Recovering a non-resident stream means translating its extents VLCN→PLCN. See [Resident Storage](concepts/resident_storage.md).

**Extent**
: A contiguous run of clusters holding a non-resident stream's data, described as (VCN → starting VLCN, length). A file's extent table (type-0x40 records) maps its logical clusters to volume clusters; `forefst.py <image> dataruns` prints them. See [Extent Descriptors](structures/extent_descriptors.md).

## Attributes

**$SI** ($STANDARD_INFORMATION)
: The primary metadata attribute. Contains timestamps, file attributes, security references, and USN. Layout differs between v3.4 (116 bytes) and v3.14 (124 bytes).

**MACB**
: The four `$SI` timestamps used to build forensic timelines — **M**odified (content), **A**ccessed, **C**hanged (metadata/MFT-equivalent change), **B**irth (creation). The basis of the `forefst.py files --body` and `forefst.py <image> timeline` super-timeline.

**$DATA**
: Default data stream. Can be resident (inline in B+-tree row) or non-resident (in extent clusters).

**ADS** (Alternate Data Stream)
: Named data streams stored as multi-instance sub-records (descriptor 0x000500B0) in directory entry values. A small ADS (content below 2 KB) is inline (embedded in the B+-tree row); a large ADS (>= 2 KB) is non-resident, its bytes held in on-disk extents inside a type-0x0 sub-record (reconstructed byte-exact across a 256 B--2 MB size sweep). Snapshot streams share the same descriptor but are distinguished by the StreamSummary flags at val[0x10] (0=ADS, 2=snapshot).

**$SNAPSHOT**
: Per-file stream snapshot metadata. Available from v3.7+. Uses the same descriptor (0x000500B0) as ADS but with StreamSummary flags (val[0x10]) = 2 and a per-version stream index at val[0x44] (0x1001--0x1004). Both snapshots and large ADS can be extent-based (non-resident); a snapshot of a stream modified after snapshotting is CoW-shared, so it stores only the changed region's extents.

**$EA** (Extended Attributes)
: NTFS-style name/value pairs attached to a file. Their packed size is written to `$SI+0x50` (`PackedEaSize`) on v3.10+. WSL stores POSIX metadata in EAs — `$LXUID` / `$LXGID` / `$LXMOD` (4 B each) and `$LXDEV` (8 B). See [$EA_INFORMATION and $EA](attributes/EA_INFORMATION.md).

**Integrity stream**
: A file whose data ReFS checksums per cluster and verifies on read (self-healing on a mirrored/parity volume). Marked by file-attribute bit **0x8000** (set by `RefsSetIntegrity`), reflected into `$SI+0x20`. See [Integrity Streams](concepts/integrity_streams.md).

**Reparse point** / **reparse tag**
: A file carrying an `IO_REPARSE_TAG_*` that redirects or annotates it — symlink, junction, mount point, WSL `LX_SYMLINK`, or a WOF-compressed file. The tag sits at `$SI+0x54`; the target/data follows in the `$REPARSE` attribute. See [Reparse Points](structures/reparse_points.md).

**SecurityId** / **SID**
: `$SI+0x28` holds a 64-bit **SecurityId** (an index, not a Windows SID directly) into the Security Descriptors table (OID 0x530), which resolves to the owner/group **SID** and the DACL/SACL. See [Security Descriptors](structures/security_descriptors.md).

## Journal

**USN** (Update Sequence Number)
: A monotonically increasing 64-bit offset into the $J data stream. Each journal record is written at the current USN, which then advances by the record size (rounded to 8-byte alignment). The USN value serves as both a byte offset and a global ordering identifier for change events.

**Change Journal**
: A file entry named "Change Journal" inside OID 0x520 (FS Metadata directory). Holds three sub-records: the $J data stream (USN records), the $Max stream (journal size limits), and journal metadata. Not active by default; created by `fsutil usn createjournal` or `RefsCreateUsnJournal`. See [USN Journal](structures/usn_journal.md).

**USN_RECORD_V3**
: The record format used by ReFS for journal entries. Differs from NTFS's USN_RECORD_V2 by using 128-bit file IDs (upper 8 bytes = directory OID, lower 8 bytes = entry index). Minimum record size is 80 bytes (0x50). Records are 8-byte aligned within the $J data stream.

## Version Terms

**Native format**
: A volume freshly formatted under the target OS version. Carries CHKP flag 0x080.

**Upgraded volume**
: A volume originally formatted under an older version and later mounted on a newer OS. Does NOT carry CHKP flag 0x080.

**Version echo**
: CHKP field at offset 0x50. Populated (e.g., 0x000E0003) on native v3.10+ volumes; zero on upgraded or legacy volumes.

**Indirect root list**
: The v3.14 encoding where the 13 root pointers are reached via an in-page offset (at CHKP+0x94) to a root-list region within the same checkpoint page, rather than stored inline. Selected by CHKP flag bit 0x0200.

## Forensic Terms

**Hard link**
: Two or more directory names for one file object. All names share a single **FileId** and one set of data, but each name carries its **own** `$SI` (its own MACB timestamps) — the basis of the ReFS-specific per-name timestomp cross-check. Links are counted by the shared FileId, not the (always-1) `$SI` HardLinkCount field. See [Hard Links](concepts/hard_links.md).

**Node slack**
: The bytes of a B+-tree page **not** referenced by its live offset array — including the bodies of deleted rows, which ReFS unlinks from the array but does not scrub until a later CoW rewrite. The strongest deleted-directory-entry recovery source (`deleted --slack`, Method 5). See [Deletion Recovery](concepts/deletion_recovery.md).

**Orphan page / orphan OID**
: Two deletion signals. An **orphan page** is an `MSB+` metadata page still on disk that the live tree no longer references. An **orphan OID** is an OID absent from the current Object Table between present ones — permanent-deletion evidence that survives even full page reuse. See [Deletion Recovery](concepts/deletion_recovery.md).

**Timestomping**
: Falsifying a file's `$SI` timestamps to hide activity. ReFS-specific detection compares a hard-linked file's per-name MACB sets (only a name-scoped stomp diverges), the metadata-change time (`$SI+0x10`, left untouched by high-level APIs), the USN journal, and the volume creation time (a hard lower bound). See [Timestomping Detection](concepts/timestomp_detection.md).

**Super-timeline / body file**
: forefst's timeline outputs. A **body file** (`files --body`) is the mactime-compatible per-file MACB dump; the **super-timeline** (`timeline`) merges `$SI` timestamps, the USN journal, and the MLog into one time-ordered event stream. See [Artifact Timeline](concepts/artifact_timeline.md).

## Evidence and Method

**Evidence levels** (E1 / E2 / E3 / RD)
: How every claim in this documentation is graded — **E1** = string literal, **E2** = decompiled / PDB symbol, **E3** = structural inference, **RD** = raw-disk verified. Load-bearing claims prefer E2/RD. See [contributing conventions](CONTRIBUTING.md).

**Carrier categories**
: Brian Carrier's five file-system data categories — *File System, Content, Metadata, File Name, Application* — from *File System Forensic Analysis* (2005), used as the organising axis for ReFS artifacts (and a hard parse-order dependency chain). See [Carrier Categories](concepts/carrier_categories.md).
