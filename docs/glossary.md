# Glossary

Key terms used throughout the ReFS documentation, listed alphabetically.

**ADS** (Alternate Data Stream)
: A named data stream, stored as a type-0xB0 sub-record (`$NAMED_DATA`) of the file's record: in the name row when
  the record is embedded, in the type-0x40 backing when it is split.

  - From format 3.7 its key carries the multi-instance marker `0x80000002`; the 3.4 key carries no marker.
  - On format 3.11 and later a small ADS (content below 2 KiB) is inline, its bytes in the record, unless a
    conversion moved it to extents; one of 2 KiB or more is in on-disk extents.
  - On format 3.10 and earlier a named stream is always inline, up to a 128 KiB cap.
  - Stream snapshots share the type-0xB0 code; the StreamSummary flag tells the two apart.

  See [$NAMED_DATA](attributes/NAMED_DATA.md).

**Allocator**
: ReFS's free-space manager — a three-tier hierarchy (Medium, Container and Small allocator) sharing one row layout
  and differing in the region each manages and in how its own table pages are reached.

  The Small Allocator (root 12) and the Container Table (roots 7 and 8) are the checkpoint roots reached by real
  physical LCNs — the bootstrap exceptions underlying virtual addressing.

  See [Allocator Tables](structures/allocators.md).

**Block clone**
: A fast, copy-on-write file copy that shares the source's data clusters until one side is written.

  Like deduplication, it adds references that the Block Refcount Table counts. A stream snapshot shares clusters
  too, but adds no count there.

  See [Block Refcount Table](structures/block_refcount.md).

**Block Refcount Table**
: The table (root 6) that counts, per data cluster, the references beyond the first that block clones and
  deduplication make; a snapshot or a hard link adds none.

  Rows have been found only on v3.14 volumes, and not on every one; what writes a volume's first rows is not
  established.

  See [Block Refcount Table](structures/block_refcount.md).

**Carrier categories**
: Brian Carrier's five file-system data categories — *File System, Content, Metadata, File Name, Application* — from
  *File System Forensic Analysis* (2005), used as the organising axis for ReFS artifacts.

  See [Carrier Categories](concepts/carrier_categories.md).

**Change Journal**
: A file entry named "Change Journal" inside the FS Metadata directory (OID 0x520). It holds the `$J` data stream
  (USN records), the `$Max` stream (size limits) and journal metadata.

  A freshly formatted data volume has none: a journal is created, for example with `fsutil usn createjournal`
  (installers and management tools create one too).

  See [USN Journal](structures/usn_journal.md).

**CHKP** (Checkpoint)
: The atomic commit point. Two alternating checkpoints each hold the 13 root-table pointers.

  The valid copy with the higher virtual clock is current; the other is the previous consistent state (a rollback
  target until the next flush).

  See [Checkpoint](structures/chkp.md).

**CmsChecksumNone**
: A class in the v3.4 driver whose checksum verification always returns success. It is the type-0 ("no checksum")
  entry of that driver's stream checksum table; metadata pages are checked by the CRC64 or CRC32-C entry their page
  reference names.

**Container**
: A fixed 64 MiB region of the volume. The volume is divided into containers, each tracked by a row in the Container
  Table.

**Container Table**
: Maps virtual container IDs to physical disk locations (VLCN → PLCN). Kept as a failover pair (roots 7 and 8), and
  reached by real physical LCNs.

  See [Container Table](structures/container_table.md).

**CoW** (Copy-on-Write)
: ReFS's fundamental update model. No B+-tree page is modified in place: a new copy is written and the pointers above
  it are updated up to the checkpoint. Also called write-to-new or allocate-on-write.

  A few fixed structures are the exception: the superblock copies and the two checkpoint slots are rewritten at
  their fixed addresses, and the log's data area is reused as a ring.

  See [Copy-on-Write](concepts/copy_on_write.md).

**CPC** (Clusters Per Container)
: Number of clusters in a 64 MiB container — 16,384 for 4 KiB clusters, 1,024 for 64 KiB clusters. Used in address
  translation.

**CRC32-C**
: The algorithm of the SUPB and CHKP self-checksum on 4 KiB-cluster volumes (64 KiB-cluster volumes use CRC64 there,
  SHA-256 volumes SHA-256). It is *not* the page-reference checksum, which is CRC64 or SHA-256.

  It is also the per-cluster checksum of integrity streams on 4 KiB-cluster CRC64 volumes.

  See [Checksum Architecture](concepts/checksum_architecture.md).

**CRC64 (CRC-64/NVME)**
: The metadata checksum stored in page references, on every format measured — the references of a v3.4 volume
  declare it too; a SHA-256 volume uses SHA-256 instead. The driver checks a page against it when it reads the page.

  A reflected CRC64 with polynomial `0xAD93D23594C93659` (reflected `0x9A6C9329AC4BC9B5`), init and xorout all-ones —
  **not** ECMA-182, but the standard **CRC-64/NVME** (a.k.a. Rocksoft), check value `0xAE8B14860A799888`.

  See [Checksum Architecture](concepts/checksum_architecture.md).

**$DATA**
: A file's default data stream. Its bytes are either **inline** in the file's record or in on-disk **extents**: the
  volume's format, the stream's size and any conversion that moved the stream to extents decide which.

  - Format 3.10 and earlier: always in extents.
  - Format 3.11 and later: inline below 2 KiB unless a conversion moved it, in extents from 2 KiB.
  - The inline form is single-instance (marker `0x80000001`), the extent form multi-instance (`0x80000002`); a
    record carries its main `$DATA` in one form, never both.

  See [$DATA](attributes/DATA.md).

**Data residency**
: Where a file's *bytes* live, read from the `$DATA` descriptor's own form. Reported as `DataResidency`:

  - **inline** — in the record;
  - **extents** — in on-disk clusters;
  - **snapshot-shared** — the live stream owns no allocation and its bytes are still a snapshot's (recoverable);
  - **unallocated** — the stream owns no clusters and no snapshot holds its bytes, so it reads as zeros.

  Independent of record placement. Not to be confused with the `FILE_ATTRIBUTE_SPARSE_FILE` bit, which `IsSparse`
  and `--filter sparse` report and which is a different fact.

  See [Record placement and data residency](concepts/placement_and_residency.md).

**Deduplication**
: A ReFS feature that stores identical data once and shares the clusters between files, tracked by the Block
  Refcount Table.

  See [Deduplication](concepts/deduplication.md).

**Dev Drive**
: A Windows 11 volume type for developer workloads; every Dev Drive is a ReFS volume — one place an examiner meets
  a modern ReFS volume.

**$EA** (Extended Attributes)
: NTFS-style name/value pairs attached to a file; their packed size is written to `$SI+0x50` by a 3.10 or later
  driver. WSL stores POSIX metadata in EAs — `$LXUID` / `$LXGID` / `$LXMOD` and `$LXDEV`.

  See [$EA_INFORMATION and $EA](attributes/EA_INFORMATION.md).

**Embedded / split**
: The two values of record placement. An embedded record sits in the name row (`key_flags` 0x01); a split one is
  reached through it (`key_flags` 0x02) and lives in a type-0x40 backing record.

  Neither value tells you where the bytes are — a 149 MiB file can be embedded, and a hard-linked file can keep its
  bytes inline.

  See [Directory Entries](structures/directory_entries.md).

**Embedded sub-record**
: A nested attribute packed **inside** the file's record rather than given its own row — how `$DATA`, ADS,
  `$SNAPSHOT`, `$EA` and `$EFS` are stored in the name row when the record is embedded, in the type-0x40 backing when it
  is split (and, for a large attribute set, in a child page of that embedded tree).

  From format 3.7 the sub-record's key carries a marker that distinguishes single-instance (`0x80000001`) from
  multi-instance (`0x80000002`); format 3.4 keys carry none.

  See [Directory Entries](structures/directory_entries.md).

**Extent**
: A contiguous run of clusters holding an extent-backed stream's data, described as (VCN → starting VLCN, length).

  A file's extent map — a small B+-tree node inside its `$DATA` value at +0x88, whose leaf rows are the 24-byte
  extent entries — maps its logical clusters to volume clusters. A type-0x40 row is a backing record, not an extent.

  See [Extent Records](structures/extent_descriptors.md).

**Failover pair**
: Two copies of one table, each checked against its own reference in the checkpoint; neither is a primary. The
  Object ID (roots 0 and 5), Schema (3 and 9) and Container (7 and 8) tables are kept so.

  When one copy fails its check the other is read. For the Object Table, the driver read (26100.8115) also repairs
  the failed copy from the good one on a writable mount.

  See [Checkpoint](structures/chkp.md) for the pairs, and [Redundancy](concepts/redundancy.md) for the boot-sector,
  superblock and checkpoint copies.

**FCB** (File Control Block)
: Per-file driver state in kernel memory. Not an on-disk structure.

**FileId / FileRef** (128-bit file reference)
: The identity of a file, which has no OID of its own. `FileRef = (HomeOID, FileID)`:

  - the upper 64 bits are the **HomeOID** — the OID of the directory the file was *created in*;
  - the lower 64 bits are the **FileID** ordinal (a per-directory counter).

  It is the 16-byte reference carried in USN V3 records and is **fixed for the life of the object**: a rename or a
  move to another directory changes the file's name and parent, never its FileRef (on a volume without hard-link
  support the moved record carries it at `$SI+0x68` / `+0x60`).

  `forefst.py` surfaces it as the `ObjectRef` column (`HomeOID:FileID`) and the `HomeOID` / `FileID` columns.

  See [File IDs](concepts/file_ids.md).

**Format version vs driver build**
: The **format version** is a property of the volume (3.4, 3.7, 3.9, 3.10, 3.14 …), recorded in its boot sector,
  which the driver reads at mount; the **driver build** is the `refs.sys` that happens to be mounting it.

  Behaviour is gated on the *volume's* format, so a newer driver writes by the older rule only while the volume stays
  at the older format. In the corpus a read-write mount by a newer Windows upgraded the volume in place: the upgrade
  rewrites its version fields and checkpoint flags but converts no record already written, which keeps its old form.

  See [Driver Evolution](concepts/driver_evolution.md).

**Hard link**
: Two or more directory names for one file object. All names share one FileRef, one record (its type-0x40 backing,
  which holds the file's `$SI`) and one set of data.

  Each name's directory entry keeps a cached copy of the timestamps, refreshed only when the file is opened through
  that name, so the names can disagree: a disagreement on Created is the ReFS-specific per-name timestomp signal.

  See [Hard Links](concepts/hard_links.md).

**HomeOID / CreationDir** (one field, as an id and as a path)
: The OID of the directory a file was **created in**, fixed at creation and not changed by a move or a rename. It is
  the upper half of the file's [FileRef](concepts/file_ids.md), which is why moving a file does not change its
  identity.

  - The `files` listing reports it as the **`HomeOID`** column, with its resolved path in **`CreationDir`**.
  - On a volume without hard-link support a moved record stays embedded and carries its reference at `$SI+0x68` /
    `$SI+0x60`; `HomeOID` is then that reference's directory.
  - Contrast **`ParentOID`**, where the name lives *now*. The two differ for a file that sits outside its creation
    directory — after a move, or for a hard-link name in another directory (`IsMoved` tells the two apart where it
    can); a file moved back home shows them equal.

**Image tail**
: The part of an image file after the volume's last cluster: the rest of the volume's partition and anything after
  the partition. The tool reads none of it; `summary` and `fastsummary` give its size on one line.

**Index entry / backing record**
: An **index entry** is a directory name row whose object record was split out; the **backing record** is the
  type-0x40 row in the object's home directory that actually holds it. Several index entries — the names of a
  hard-linked file — can point at one backing record.

  See [Directory Entries](structures/directory_entries.md).

**Indirect root list**
: The v3.14 encoding, selected by checkpoint flag 0x0200, in which `CHKP+0x94` holds the in-record offset of the
  root-offset table (0xA8, or 0xB0 on records an Insider build wrote) instead of the 13 root offsets themselves.

  See [Checkpoint](structures/chkp.md).

**Inline / extent-backed**
: The two ordinary values of data residency. **Inline** bytes are stored in the `$DATA` descriptor itself;
  **extent-backed** bytes are on disk, described by an extent map.

  Which one the driver chooses depends on the *volume's format version*, the stream kind and its size, and on
  operations that convert a stream (a snapshot, encryption, a block clone, creation with integrity on) — never on the
  record's placement.

**Integrity stream**
: A file whose data ReFS checksums per cluster and verifies on read, self-healing on a mirrored/parity volume. Marked
  by file-attribute bit `0x8000`.

  - The checksum follows the volume: CRC32-C on 4 KiB-cluster CRC64 volumes.
  - Not every run carries one: an integrity file often has its first cluster checksummed and the rest in a run
    without checksums.
  - Only data in extents is checksummed: a file created with integrity on is extent-backed from its creation, while one
    given integrity after an inline write keeps its bytes inline.

  `forefst.py` can verify these checksums on extract.

  See [Integrity Streams](concepts/integrity_streams.md).

**IRP** (I/O Request Packet)
: The Windows kernel structure that carries a single I/O operation (create, read, write, …) to the driver. Not an
  on-disk structure.

  See [Architecture](concepts/architecture.md).

**LCN** (Logical Cluster Number)
: Generic term for a cluster address. In ReFS it may be virtual (VLCN) or physical (PLCN) depending on the structure:
  the Container Table, the Small Allocator and the MLog's data area use real physical LCNs, most other structures
  virtual LCNs.

**MACB**
: The four `$SI` timestamps used to build forensic timelines — **M**odified (content), **A**ccessed, **C**hanged
  (metadata change), **B**irth (creation). The basis of the `forefst.py files --body` and `timeline` outputs.

**Merkle Tree**
: The integrity chain formed by page references: each parent stores a checksum of its children, anchored at the
  checkpoint. Once the checkpoint is verified, every metadata page beneath it can be verified through the chain; file contents are covered only where
  integrity streams are on.

**Minstore**
: ReFS's lower layer — a general-purpose, transactional B+-tree key-value engine that stores every table: its pages,
  rows and B+-trees. The upper (`Refs*`) layer adds file-system semantics on top and decides what the rows contain.

  A tool that models Minstore can walk every ReFS table whatever upper-layer features are enabled; reading the rows
  still needs each attribute's own (sometimes version-dependent) format.

  See [Architecture](concepts/architecture.md).

**MLog** (Metadata Log)
: The write-ahead transaction log for crash recovery. It contains redo-only records (no undo).

  The driver reads its place from the Logfile Information Table (OID 0x9 / 0xA), never from a fixed address; its
  data area is in physical clusters (no container translation).

  `forefst.py` decodes it into create / write / rename / move / delete events.

  See [MLog](structures/mlog.md).

**MSB+** (Minstore B+-tree page)
: A node of any B+-tree. All ReFS metadata tables are stored as MSB+ pages; the ASCII signature `MSB+` identifies
  these pages.

  See [B+-tree Node](structures/btree_node.md).

**Native format**
: A volume freshly formatted under the target OS version.

  Formatted at 3.10 or later, it carries checkpoint flag 0x0080, which no upgraded volume measured carries (an
  upgraded v3.14 volume reads 0x0602, a native one 0x0682). A volume formatted at 3.4–3.9 carries no such flag.

  See [Version Detection](concepts/version_detection.md).

**Node slack**
: The bytes of a B+-tree page **not** referenced by its live offset array — including the bodies of deleted rows,
  which ReFS unlinks but does not scrub until a later rewrite. The primary deleted-entry recovery source.

  See [Deletion Recovery](concepts/deletion_recovery.md).

**Object Table**
: The master OID-to-location mapping. Every persistent directory or system object has one entry (files have none) —
  ReFS's closest equivalent to NTFS's `$MFT`. Kept as a failover pair.

  See [Object Table](structures/object_table.md).

**ObjectRef** (the identity column)
: One column carrying whichever identity the object has:

  - a **directory** has an [OID](concepts/object_ids.md) of its own and shows it as `OID:0x0` (its OID in the home
    half, FileID 0), which is how the change journal names a directory;
  - a **file** has none and shows its [FileRef](concepts/file_ids.md) as `HomeOID:FileID`.

  Both address the same object through `details --id`.

**OID** (Object Identifier)
: A 64-bit, monotonically increasing, never-reused identifier for every directory and system object on the volume
  (files have none — a file is identified by its FileRef instead). User OIDs start at 0x701.

  A gap in the sequence marks an OID that was issued: a deleted directory, or a creation that failed after the
  counter was committed — a lead, not proof.

  See [Object IDs](concepts/object_ids.md).

**Orphan page / orphan OID**
: Two deletion signals.

  - An **orphan page** is an `MSB+` metadata page still on disk that the live tree no longer references.
  - An **orphan OID** is an OID still present in the Object Table but no longer reachable from the directory tree —
    a deleted directory whose table entry has not yet been cleaned up (`deleted --orphans`, a low-confidence lead).

  A missing OID between present ones is an OID gap (see OID).

  See [Deletion Recovery](concepts/deletion_recovery.md).

**Page reference**
: A pointer from a parent B+-tree page to a child that also carries the child's checksum — the Merkle link that makes
  the tree self-verifying.

  - A B+-tree node's inner rows hold 48-byte (CRC64) or 72-byte (SHA-256) references.
  - A checkpoint stores its root references at the size it declares at `CHKP+0x5C`: 48 or 72 bytes from format
    3.10, 104 bytes on a volume formatted at 3.4 to 3.9.

  See [Page References](structures/page_references.md).

**Parent-Child Table**
: Encodes directory-to-directory relationships (and directory-to-security-mapping ones); regular files are not
  tracked. A pure set/index with 48-byte rows.

  See [Parent-Child Table](structures/parent_child_table.md).

**PLCN** (Physical Logical Cluster Number)
: The physical cluster number after Container Table translation. Its byte offset in the volume is PLCN × cluster
  size (plus the partition's start in a whole-disk image).

**Record placement**
: Where a file's *record* lives, reported as `RecordPlacement`:

  - **embedded** in its directory name row (`key_flags` 0x01);
  - **split** out into its own type-0x40 backing record in the object's home directory (`key_flags` 0x02).

  On a volume with hard-link support a move to another directory or a hard link forces the split — one-way, and it
  moves no data. On a volume without hard-link support (the boot sector's flags lack 0x20 — measured on volumes
  formatted at ReFS 3.4 and those upgraded from them) the whole record moves instead, carrying its FileRef at
  `$SI+0x68` / `+0x60`.

  Placement does **not** determine where the file's bytes are: a split record commonly still holds its data inline.
  Independent of data residency.

  See [Record placement and data residency](concepts/placement_and_residency.md).

**Redo opcode**
: The operation type in an MLog redo record (offset 0x04, u32). The dispatched ranges are contiguous:

  - v3.4 (17134) dispatches 29 values (0x00–0x1C);
  - v3.14 (26100) dispatches 44 values (0x00–0x2B), and the Insider builds read dispatch 45 or 46.

  0x12 and 0x15 call no handler; on 26100 and the Insider builds 0x17 returns the explicit unhandled-opcode error.

  See [MLog](structures/mlog.md).

**Reparse index**
: The volume-wide system table (OID 0x540 / 0x541, a failover pair) that lists every object carrying a reparse tag —
  distinct from the per-file reparse data.

  See [$REPARSE](attributes/REPARSE.md).

**Reparse point** / **reparse tag**
: A file carrying an `IO_REPARSE_TAG_*` that redirects or annotates it — symlink, junction, mount point, WSL
  `LX_SYMLINK` (a WOF-compressed file would be one too; none has been observed). The tag sits at `$SI+0x54`; the
  target/data follows in the `$REPARSE_POINT` attribute.

  See [$REPARSE_POINT](attributes/REPARSE_POINT.md).

**Resident / Non-resident**
: Retired wording for two *different* properties that a single word cannot express — use **record placement** and
  **data residency**. Where the word still appears it can name either property: read it from the context.

  See [Record placement and data residency](concepts/placement_and_residency.md).

**Row type**
: The type marker on a B+-tree key/row:

  - **0x10** — an object's own row (carries `$SI`);
  - **0x20** — the reverse index (FileId → name, or where the record is);
  - **0x30** — a name row (a directory entry), which also holds the whole record of a file whose record is embedded;
  - **0x40** — a backing record: the record of a file split out of its name row, kept in its home directory.

  See [Directory Entries](structures/directory_entries.md).

**SCB** (Stream Control Block)
: Per-stream driver state in kernel memory. Not an on-disk structure.

**Schema Table**
: A self-describing table of key-comparison rules — one entry per table type. Kept as a failover pair (roots 3 and
  9).

  See [Schema Table](structures/schema_table.md).

**SecurityId** / **SID**
: `$SI+0x28` holds a 64-bit **SecurityId** (an index, not a Windows SID directly) into the Security Descriptors table
  (OID 0x530), which resolves to the owner/group **SID** and the DACL/SACL.

  See [Security Descriptors](structures/security_descriptors.md).

**$SI** ($STANDARD_INFORMATION)
: The primary metadata attribute — timestamps, file attributes, security reference, and USN.

  Its layout differs between v3.4 (116 bytes) and v3.14 (124 bytes); the 124-byte layout starts at format 3.7, and
  the meaning of `+0x50` depends on the driver that wrote the row (3.10 and later: the packed EA size).

  See [$STANDARD_INFORMATION](attributes/STANDARD_INFORMATION.md).

**$SNAPSHOT**
: Per-file stream snapshot metadata, from format 3.7. It uses the same type-0xB0 descriptor as an ADS, with a
  StreamSummary flag of 2, and keeps the stream's content under a new sub-stream id (0x1001, 0x1002, …).

  Snapshots are copy-on-write: a block is copied only when it is about to be overwritten. After a change the current
  stream owns just the changed blocks, and the unchanged ones stay listed in the snapshot's extent map; a version is
  rebuilt from its own extents plus older snapshots' — a deterministic prior-content source.

  See [$SNAPSHOT](attributes/SNAPSHOT.md).

**Snapshot-shared**
: A stream that owns no allocation because its bytes are still those of the snapshot it has not diverged from.
  Writing to it gives it clusters of its own.

  See [Snapshots and Versioning](concepts/snapshots_versioning.md).

**Storage Spaces**
: Microsoft's software-defined storage (pooling, mirror/parity, tiering); Microsoft recommends ReFS on Storage Spaces
  Direct. The self-healing of integrity streams uses its redundant copies.

**SUPB** (Superblock)
: The volume anchor: it stores the Volume GUID and pointers to the two alternating checkpoints, protected by its own
  cluster-size-dependent self-checksum.

  It has three copies: the primary at cluster 30 (LCN 0x1E) and two backups at the end of the volume. The driver
  reads the primary when it passes its tests.

  See [Superblock](structures/supb.md).

**Super-timeline / body file**
: forefst's timeline outputs. A **body file** (`files --body`) is the mactime-compatible per-file MACB dump; the
  **super-timeline** (`timeline`) merges `$SI` timestamps, the USN journal, and the MLog into one time-ordered event
  stream.

  See [Artifact Timeline](concepts/artifact_timeline.md).

**Timestomping**
: Falsifying a file's `$SI` timestamps to hide activity. ReFS-specific detection compares:

  - a hard-linked file's names, on their Created times;
  - the metadata-change time (`$SI+0x10`), which the common APIs cannot set — the call moves it to the moment of the
    call — though a native-API call can;
  - the USN journal;
  - the volume creation time (a floor for a file created on the volume, not for a copied or restored one).

  See [Timestomping Detection](concepts/timestomp_detection.md).

**Trash Table**
: The deferred-deletion queue (OID 0x0D). A deleted object goes there only when one of its data stream sets holds
  two or more tables (or, for a file, a large number of rows); every other delete is done in place, in the same
  transaction.

  While a row is there, the object's data and metadata are still in place — a recovery source.

  See [Trash Table](structures/trash_table.md).

**Upgraded volume**
: A volume originally formatted under an older version and upgraded in place when a newer Windows mounted it
  read-write.

  Every upgraded volume in the corpus is at 3.14 and none carries checkpoint flag 0x0080, which every volume
  formatted natively at 3.10 or later carries — which is how an upgrade is told apart from a native volume.

  See [Version Detection](concepts/version_detection.md).

**USN** (Update Sequence Number)
: A 64-bit virtual byte offset in the `$J` data stream (the journal is an in-place ring, so a USN can exceed the
  stream's size), monotonically increasing **within one journal instance**. Each journal record is written at the
  current USN, which then advances by the record size.

  It is **not** unique for the life of the volume:

  - `fsutil usn createjournal` over an existing journal restarts numbering at 0 while the UsnJournalId stays the
    same, so a USN from before the restart can name a different record afterwards;
  - `deletejournal` followed by `createjournal` also restarts at 0, under a new UsnJournalId (the new journal's
    creation time).

**USN_RECORD_V3**
: The record format ReFS uses for journal entries. It differs from NTFS's V2 by using 128-bit file IDs: the OID of the
  directory the file was created in plus its per-directory ordinal (the FileRef). Minimum record size is 80 bytes,
  8-byte aligned within the `$J` stream.

**VBR** (Volume Boot Record)
: The 512-byte structure at sector 0 providing format parameters: cluster size, version and, on volumes formatted at
  3.10 or later, the checksum selector.

  See [VBR](structures/vbr.md).

**VCN** (Virtual Cluster Number)
: A logical cluster offset within a single file's data (analogous to NTFS's VCN). Maps to a VLCN through the file's
  extent map.

**Version echo**
: A CHKP field (offset 0x50) populated on native v3.10+ volumes (e.g. `0x000E0003`) and zero on upgraded or legacy
  volumes — a corroborating version marker.

**Virtual Clock**
: A monotonically increasing counter in each checkpoint, at `CHKP+0x60` (the page header repeats it at `+0x10`),
  incremented each time a checkpoint is written — one checkpoint commits many transactions. The valid copy with the
  higher clock is current.

**VLCN** (Virtual Logical Cluster Number)
: A cluster address in ReFS's virtual address space — not a direct physical disk address. Must be translated through
  the Container Table to obtain a PLCN.

  See [Virtual Addressing](concepts/virtual_addressing.md).

**WOF** (Windows Overlay Filter)
: A transparent file-compression scheme exposed as a reparse tag (0x80000017); a WOF-compressed file would appear as
  a reparse point. The tag is defined, but it has not been observed on any volume of the corpus.

  See [Reparse Points](structures/reparse_points.md).
