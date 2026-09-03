# Glossary

Key terms used throughout the ReFS documentation, listed alphabetically.

**ADS** (Alternate Data Stream)
: A named data stream stored as a multi-instance sub-record in a directory-entry value. A small ADS (content below 2 KB) is inline (embedded in the B+-tree row); a larger one is non-resident, its bytes held in on-disk extents. Snapshot streams share the same descriptor but are distinguished by a stream-summary flag.

**Allocator**
: ReFS's free-space manager — a three-tier hierarchy (Container, Medium, Small allocator) sharing one bitmap-row format and differing only in the region they manage. The Small Allocator and the Container Table use real physical LCNs — the bootstrap exception underlying virtual addressing. See [Allocator Tables](structures/allocators.md).

**Block clone**
: A fast, copy-on-write file copy that shares the source's data clusters until one side is written. Like deduplication and snapshots, it relies on shared clusters tracked by the Block Refcount Table.

**Block Refcount Table**
: Tracks shared data blocks for deduplication, snapshots, and clones. Populated only on v3.14 volumes with sharing features enabled.

**Carrier categories**
: Brian Carrier's five file-system data categories — *File System, Content, Metadata, File Name, Application* — from *File System Forensic Analysis* (2005), used as the organising axis for ReFS artifacts. See [Carrier Categories](concepts/carrier_categories.md).

**Change Journal**
: A file entry named "Change Journal" inside the FS Metadata directory (OID 0x520). Holds the $J data stream (USN records), the $Max stream (size limits), and journal metadata. Not active by default; created by `fsutil usn createjournal`. See [USN Journal](structures/usn_journal.md).

**CHKP** (Checkpoint)
: The atomic commit point. Two alternating checkpoints each hold the 13 root-table pointers; the copy with the higher virtual clock is current, the other is the previous state (a rollback point). See [Checkpoint](structures/chkp.md).

**CmsChecksumNone**
: A stub class in the v3.4 driver whose checksum-verification always returns success — which is why v3.4 metadata checksums are written but never verified.

**Container**
: A fixed 64 MiB region of the volume. The volume is divided into containers, each tracked by a row in the Container Table.

**Container Table**
: Maps virtual container IDs to physical disk locations (VLCN → PLCN). Kept as a failover pair, and uses real physical LCNs. See [Container Table](structures/container_table.md).

**CoW** (Copy-on-Write)
: ReFS's fundamental update model. No metadata page is modified in place; a new copy is written and the pointers above it are updated up to the checkpoint. Also called write-to-new or allocate-on-write. See [Copy-on-Write](concepts/copy_on_write.md).

**CPC** (Clusters Per Container)
: Number of clusters in a 64 MiB container — 16,384 for 4 KiB clusters, 1,024 for 64 KiB clusters. Used in address translation.

**CRC32-C**
: The block self-descriptor checksum type used on the SUPB/CHKP self-descriptor. It is *not* the page-reference checksum (that is CRC64) and *not* the SUPB/CHKP block digest (a cluster-size-dependent self-checksum: CRC32-C on 4K-cluster volumes, CRC64 on 64K, SHA-256 on SHA-256 volumes). Also the per-cluster algorithm used by integrity streams.

**CRC64 (CRC-64/NVME)**
: The primary metadata checksum from v3.10+. A reflected CRC64 with polynomial `0xAD93D23594C93659` (reflected `0x9A6C9329AC4BC9B5`), init and xorout all-ones — **not** ECMA-182, but the standard **CRC-64/NVME** (a.k.a. Rocksoft), check value `0xAE8B14860A799888`. Stored in page references and verified at mount on v3.14.

**$DATA**
: A file's default data stream. Can be resident (inline in a B+-tree row) or non-resident (in extent clusters). See [$DATA](attributes/DATA.md).

**Deduplication**
: A ReFS feature that stores identical data once and shares the clusters between files, tracked by the Block Refcount Table. See [Deduplication](concepts/deduplication.md).

**Dev Drive**
: A Windows 11 volume optimised for developer workloads, formatted as ReFS by default — a common place to encounter a modern ReFS volume.

**$EA** (Extended Attributes)
: NTFS-style name/value pairs attached to a file; their packed size is written to `$SI+0x50` on v3.10+. WSL stores POSIX metadata in EAs — `$LXUID` / `$LXGID` / `$LXMOD` and `$LXDEV`. See [$EA_INFORMATION and $EA](attributes/EA_INFORMATION.md).

**Embedded sub-record**
: A nested attribute packed **inside** a B+-tree row value rather than given its own row — how `$DATA`, ADS, `$SNAPSHOT`, `$EA`, and `$EFS` ride inside a directory-entry value. A leading marker distinguishes single-instance (`0x80000001`) from multi-instance (`0x80000002`). See [Directory Entries](structures/directory_entries.md).

**Extent**
: A contiguous run of clusters holding a non-resident stream's data, described as (VCN → starting VLCN, length). A file's extent table (type-0x40 records) maps its logical clusters to volume clusters. See [Extent Descriptors](structures/extent_descriptors.md).

**Failover pair**
: Two copies of a critical structure (for example the Object, Schema, and Container tables) kept at independent locations, so a checksum mismatch on one can be healed from the other at mount. See [Redundancy](concepts/redundancy.md).

**FCB** (File Control Block)
: Per-file driver state in kernel memory. Not an on-disk structure.

**FileId / FileRef** (128-bit file reference)
: The identity of a file, which has no OID of its own. `FileRef = (HomeOid, FileId)`: the upper 64 bits are the **HomeOid** — the OID of the directory the file was *created in* — and the lower 64 bits are the **FileId** ordinal (a per-directory counter). It is the 16-byte reference carried in USN V3 records and is **frozen for the life of the object**: a rename or a move to another directory changes the file's name and parent, never its FileRef. `forefst.py` surfaces it as the `FileRef` / `HomeOid` / `FileId` columns. See [File IDs](concepts/file_ids.md).

**Hard link**
: Two or more directory names for one file object. All names share a single FileId and one set of data, but each name carries its **own** `$SI` (its own MACB timestamps) — the basis of the ReFS-specific per-name timestomp cross-check. See [Hard Links](concepts/hard_links.md).

**Indirect root list**
: The v3.14 encoding where the 13 root pointers are reached via an in-page offset to a root-list region within the checkpoint page, rather than stored inline. Selected by a CHKP flag bit.

**Integrity stream**
: A file whose data ReFS checksums per cluster (CRC32-C) and verifies on read, self-healing on a mirrored/parity volume. Marked by file-attribute bit `0x8000`. `forefst.py` can verify these checksums on extract. See [Integrity Streams](concepts/integrity_streams.md).

**IRP** (I/O Request Packet)
: The Windows kernel structure that carries a single I/O operation (create, read, write, …) to the driver. Not an on-disk structure. See [Architecture](concepts/architecture.md).

**LCN** (Logical Cluster Number)
: Generic term for a cluster address. In ReFS it may be virtual (VLCN) or physical (PLCN) depending on the structure; the Container Table and Small Allocator use real physical LCNs, most other structures use virtual LCNs.

**MACB**
: The four `$SI` timestamps used to build forensic timelines — **M**odified (content), **A**ccessed, **C**hanged (metadata change), **B**irth (creation). The basis of the `forefst.py files --body` and `timeline` outputs.

**Merkle Tree**
: The integrity chain formed by page references: each parent stores a checksum of its children, anchored at the checkpoint. A verified checkpoint vouches for everything beneath it.

**Minstore**
: ReFS's lower layer — a general-purpose, transactional B+-tree key-value engine that produces the entire on-disk format. The upper (`Refs*`) layer adds file-system semantics on top; a tool that models Minstore can read any ReFS metadata regardless of which upper-layer features are enabled. See [Architecture](concepts/architecture.md).

**MLog** (Metadata Log)
: The write-ahead transaction log for crash recovery. Contains redo-only records (no undo), located at a fixed physical LCN. `forefst.py` decodes it into create / write / rename / move / delete events. See [MLog](structures/mlog.md).

**MSB+** (Minstore B+-tree page)
: A node of any B+-tree. All ReFS metadata tables are stored as MSB+ pages; the ASCII signature `MSB+` identifies these pages. See [B+-tree Node](structures/btree_node.md).

**Native format**
: A volume freshly formatted under the target OS version. Carries a distinguishing CHKP flag that an in-place upgrade cannot set. See [Version Detection](concepts/version_detection.md).

**Node slack**
: The bytes of a B+-tree page **not** referenced by its live offset array — including the bodies of deleted rows, which ReFS unlinks but does not scrub until a later rewrite. The strongest deleted-entry recovery source. See [Deletion Recovery](concepts/deletion_recovery.md).

**Object Table**
: The master OID-to-location mapping. Every persistent directory or system object has one entry (files have none) — ReFS's closest equivalent to NTFS's `$MFT`. Kept as a failover pair. See [Object Table](structures/object_table.md).

**OID** (Object Identifier)
: A 64-bit, monotonically increasing, never-reused identifier for every directory and system object on the volume (files have none — a file is named by a FileId instead). A gap in the sequence is durable evidence that an object was deleted. See [Object IDs](concepts/object_ids.md).

**Orphan page / orphan OID**
: Two deletion signals. An **orphan page** is an `MSB+` metadata page still on disk that the live tree no longer references. An **orphan OID** is an OID absent from the current Object Table between present ones — permanent-deletion evidence that survives even full page reuse. See [Deletion Recovery](concepts/deletion_recovery.md).

**Page reference**
: A pointer from a parent B+-tree page to a child that also carries the child's checksum — the Merkle link that makes the tree self-verifying. Its size depends on version **and** checksum type: 104 B (v3.4), 48 B (CRC64, v3.10+), 72 B (SHA-256). See [Page References](structures/page_references.md).

**Parent-Child Table**
: Encodes directory-to-directory relationships. A pure set/index with 48-byte rows. See [Parent-Child Table](structures/parent_child_table.md).

**PLCN** (Physical Logical Cluster Number)
: The actual on-disk cluster address after Container Table translation — the byte offset into the volume image.

**Redo opcode**
: The operation type in an MLog redo record (offset 0x04, u32). The dispatched ranges are contiguous: v3.4 dispatches 29 values (0x00–0x1C); v3.14 dispatches 44 values (0x00–0x2B), of which only 0x17 returns an explicit unhandled-opcode error. See [MLog](structures/mlog.md).

**Reparse index**
: The volume-wide system table (OID 0x540, with a mirror) that lists every object carrying a reparse tag — distinct from the per-file reparse data. See [$REPARSE](attributes/REPARSE.md).

**Reparse point** / **reparse tag**
: A file carrying an `IO_REPARSE_TAG_*` that redirects or annotates it — symlink, junction, mount point, WSL `LX_SYMLINK`, or a WOF-compressed file. The tag sits at `$SI+0x54`; the target/data follows in the `$REPARSE_POINT` attribute. See [Reparse Points](structures/reparse_points.md).

**Resident / Non-resident**
: Whether a stream's bytes live **inline** in the B+-tree row value (*resident* — small streams) or in separate **on-disk extent clusters** (*non-resident* — larger streams; an ADS promotes at ≥ 2 KB, and a cross-directory move forces a file non-resident). Recovering a non-resident stream means translating its extents VLCN→PLCN. See [Resident Storage](concepts/resident_storage.md).

**Row type**
: The type marker on a B+-tree key/row: **0x10** = an object's own-row (carries `$SI`); **0x30** = a filename / directory entry (and a resident file's value); **0x40** = an extent record (a non-resident file's data runs); **0x20** = the reverse index (FileId → name / home directory). See [Directory Entries](structures/directory_entries.md).

**SCB** (Stream Control Block)
: Per-stream driver state in kernel memory. Not an on-disk structure.

**Schema Table**
: A self-describing table of key-comparison rules — one entry per table type. Kept as a failover pair. See [Schema Table](structures/schema_table.md).

**SecurityId** / **SID**
: `$SI+0x28` holds a 64-bit **SecurityId** (an index, not a Windows SID directly) into the Security Descriptors table (OID 0x530), which resolves to the owner/group **SID** and the DACL/SACL. See [Security Descriptors](structures/security_descriptors.md).

**$SI** ($STANDARD_INFORMATION)
: The primary metadata attribute — timestamps, file attributes, security reference, and USN. Its layout differs between v3.4 (116 bytes) and v3.14 (124 bytes). See [$STANDARD_INFORMATION](attributes/STANDARD_INFORMATION.md).

**$SNAPSHOT**
: Per-file stream snapshot metadata, available from v3.7+. Uses the same descriptor as ADS but with a stream-summary flag of 2 and a per-version stream index. A snapshot of a stream modified after snapshotting is copy-on-write-shared, storing only the changed region — a deterministic prior-content source. See [$SNAPSHOT](attributes/SNAPSHOT.md).

**Storage Spaces**
: Microsoft's software-defined storage (pooling, mirror/parity, tiering) for which ReFS is the default file system; its redundancy is what the self-healing integrity streams draw on.

**Super-timeline / body file**
: forefst's timeline outputs. A **body file** (`files --body`) is the mactime-compatible per-file MACB dump; the **super-timeline** (`timeline`) merges `$SI` timestamps, the USN journal, and the MLog into one time-ordered event stream. See [Artifact Timeline](concepts/artifact_timeline.md).

**SUPB** (Superblock)
: The fixed-location volume anchor at cluster 30 (LCN 0x1E). Stores the Volume GUID and pointers to the two alternating checkpoints, protected by its own cluster-size-dependent self-checksum. See [Superblock](structures/supb.md).

**Timestomping**
: Falsifying a file's `$SI` timestamps to hide activity. ReFS-specific detection compares a hard-linked file's per-name MACB sets, the metadata-change time (`$SI+0x10`, left untouched by high-level APIs), the USN journal, and the volume creation time (a hard lower bound). See [Timestomping Detection](concepts/timestomp_detection.md).

**Trash Table**
: The deferred-deletion queue (OID 0x0D). Holds files whose names have been removed but whose storage has not yet been reclaimed — a recovery source. See [Trash Table](structures/trash_table.md).

**Upgraded volume**
: A volume originally formatted under an older version and later mounted on a newer OS. Does **not** carry the native-format CHKP flag — which is how an upgrade is told apart from a native volume. See [Version Detection](concepts/version_detection.md).

**USN** (Update Sequence Number)
: A monotonically increasing 64-bit offset into the $J data stream. Each journal record is written at the current USN, which then advances by the record size. The value serves as both a byte offset and a global ordering identifier for change events.

**USN_RECORD_V3**
: The record format ReFS uses for journal entries. Differs from NTFS's V2 by using 128-bit file IDs (directory OID + entry index). Minimum record size is 80 bytes, 8-byte aligned within the $J stream.

**VBR** (Volume Boot Record)
: The 512-byte structure at sector 0 providing format parameters: cluster size, version, and checksum mode. See [VBR](structures/vbr.md).

**VCN** (Virtual Cluster Number)
: A logical cluster offset within a single file's data (analogous to NTFS's VCN). Maps to a VLCN through the file's extent table.

**Version echo**
: A CHKP field (offset 0x50) populated on native v3.10+ volumes (e.g. `0x000E0003`) and zero on upgraded or legacy volumes — a corroborating version marker.

**Virtual Clock**
: A monotonically increasing counter in the checkpoint header, incremented on each transaction commit. The checkpoint with the higher clock is current.

**VLCN** (Virtual Logical Cluster Number)
: A cluster address in ReFS's virtual address space — not a direct physical disk address. Must be translated through the Container Table to obtain a PLCN. See [Virtual Addressing](concepts/virtual_addressing.md).

**WOF** (Windows Overlay Filter)
: A transparent file-compression scheme exposed as a reparse tag; WOF-compressed files appear as reparse points. See [Reparse Points](structures/reparse_points.md).
