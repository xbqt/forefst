# File Systems

Every ReFS forensic decision rests on a small number of general file-system ideas — what a cluster is,
how files point at their data, how the namespace forms a graph, and how a file system stays consistent
across a crash. Getting these wrong is how an NTFS-trained tool mis-reads a ReFS volume: it treats a
cluster number as a disk offset, expects a flat metadata table, or looks for an undo log that does not
exist. This page sets out the vocabulary and the design space so the ReFS-specific pages can name
exactly *which* general choice ReFS makes and *what it costs an analyst*.

## The storage hierarchy

Storage is a stack of abstractions, each one allocating from the layer beneath it:

```
Raw storage device
 └─ Sectors        (smallest addressable hardware unit)
   └─ Partitions   (contiguous regions, managed independently)
     └─ Volumes    (logical storage units presented to the OS)
       └─ Clusters / Blocks   (allocation units, size fixed at format time)
         └─ Files and directories
```

- A **sector** is the minimum atomic unit of physical I/O.
- A **partition** is a contiguous region of a disk managed independently.
- A **volume** is the logical storage unit a file system resides on; it may span multiple partitions via
  LVM or RAID.
- A **cluster** (Windows) or **block** (Unix) is the smallest logical unit the file system allocates —
  one or more consecutive sectors, with the size chosen at format time.

The cluster is the unit that matters most for ReFS analysis, because two of its properties drive
everything downstream. Its **size** is fixed at format and decides how every address is decomposed —
ReFS supports 4 KiB and 64 KiB clusters, and that choice (not the version) sets the page size and the
container arithmetic, as the [Cluster and Page Size](cluster_page_size.md) page explains. And the
cluster number a file's metadata records is, on ReFS, not even a disk position — it is a *virtual*
address that must be translated, which is the subject of [Virtual Addressing](virtual_addressing.md).

**Slack space** is the unused tail of the last cluster allocated to a file. Because allocation is at
cluster granularity, a file that does not fill its last cluster leaves residual bytes that may still hold
data from a previous file — a classic recovery target. ReFS reshapes what slack *looks like*: its
metadata lives in variable-length B+-tree pages rather than fixed records, so the analogous artifact is a
stale row left inside a page rather than a fixed-size record tail. [Copy-on-Write](copy_on_write.md)
covers how those stale rows are produced and propagated.

## Files and directories

A **file** is a logical unit of persistent information, independent of any process that opens it. A
**directory** is a special file whose entries map names to references into the metadata store — inode
numbers on Unix, MFT record numbers on NTFS, or B+-tree keys on ReFS. Directories form a hierarchical
namespace rooted at a single entry point.

### Metadata and attributes

Every file carries attributes beyond its content: name, timestamps, owner, size, permissions. This
metadata is where forensics happens — timestamps, link counts, and allocation state reveal a file's
history independently of, and often after the loss of, its data. On ReFS each of these lives as a typed,
named record inside the file's B+-tree entry; the [Attributes — Forensic Reference](../attributes/README.md)
catalogs how each one is laid out and what it is worth.

Brian Carrier's *File System Forensic Analysis* draws a distinction this catalog inherits:

- **Essential attributes** — name, the metadata reference, and the data-location pointers — are required
  to *access* the file. They cannot be wrong without breaking the file.
- **Optional attributes** — timestamps, ownership — can be modified without affecting access, which is
  precisely why they are the surface a forger (or a backup tool) alters and an analyst scrutinizes.

That essential/optional split is the spine of the broader
[Carrier category model](carrier_categories.md), which maps every ReFS artifact to one of five
analytical layers.

## How file systems allocate data

The central design problem is recording *which clusters hold a file's content*. The chosen scheme shapes
both performance and what an analyst can reconstruct:

| Method | Metadata | Strengths | Weaknesses |
|--------|----------|-----------|------------|
| **Contiguous** | Start + length | Fast sequential and random access | External fragmentation |
| **Linked list** | Per-block next pointer | No fragmentation | Poor random access, pointer overhead |
| **FAT** | Global allocation table | Better random access than linked | Table must fit in memory |
| **Inode-based** | Per-file inode with block pointers | Memory-efficient (load on open) | Fixed pointer count per inode |
| **MFT (NTFS)** | Per-file MFT record with data runs | Compact extent representation | MFT itself can fragment |
| **B+-tree (ReFS, Btrfs)** | Tree-indexed metadata records | Dynamic growth, efficient indexing, snapshots | Complexity |

ReFS sits in the last row: there is **no flat metadata table** to scan the way NTFS scanners walk the
MFT array. File state lives in per-object B+-trees managed by the Minstore storage engine, so locating a
file means walking a tree from a root recorded in the checkpoint, not indexing into an array. The
[Architecture](architecture.md) and [NTFS vs ReFS](ntfs_comparison.md) pages develop this contrast and
its tooling consequences.

### Extents

NTFS, ReFS, and Btrfs describe a file's data with **extents** — a contiguous cluster range given as
start + length — rather than one pointer per block. This collapses the metadata cost of large files. In
NTFS these are *data runs*; on ReFS they are rows in B+-tree leaf nodes, and there is a forensic twist:
the cluster numbers in those rows are virtual, not physical. The byte layout of a ReFS extent is on the
[Extent Descriptors](../structures/extent_descriptors.md) page, and the translation those virtual numbers
demand is on [Virtual Addressing](virtual_addressing.md).

### Directory indexing

| Strategy | Lookup | Used By |
|----------|--------|---------|
| Linear list | O(n) | Early FAT |
| B-tree | O(log n) | NTFS, ReFS |
| Hash tree (HTree) | O(log n) | ext4 |

ReFS indexes every directory as its own B+-tree, keyed so that name lookups stay logarithmic even in very
large directories. The [Directory Entries](../structures/directory_entries.md) page details the key and
value rows that index walk produces.

## Shared files: when the namespace becomes a graph

Most file systems let one file be reachable under more than one name, turning the namespace from a tree
into a directed graph. Two mechanisms do this, and they differ in a way that matters for recovery:

- **Hard links** — multiple directory entries reference the *same* metadata object. A reference count
  tracks the live links, and the data is freed only when the count reaches zero. Because every name is
  equal, deleting one name does not delete the file.
- **Symbolic links** — store a target *path* rather than a direct metadata reference. They can cross file
  system boundaries, but become dangling references if the target moves or is deleted.

On NTFS, hard links use file-record references (MFT record number + sequence number) and symbolic links
ride on reparse points. ReFS supports reparse points — and therefore symlinks and junctions — from its
earliest version, but **hard links arrived later and require a natively-formatted v3.14 volume**; a v3.4
volume upgraded to v3.14 does *not* gain them. ReFS also takes an unusual implementation route: it stores
**no explicit hard-link count on disk**, so the link relationship has to be *reconstructed* by matching
directory-entry identity fields rather than read from a counter. The
[Hard Links](hard_links.md) page works through that reconstruction (and why the field that looks like a
count is a decoy), and [Reparse Points](../structures/reparse_points.md) covers the symlink/junction
side.

## How file systems stay consistent

A file system must survive a power loss mid-update and a hardware fault that silently flips bits. The
three mechanisms below are complementary, and ReFS's *choice among them* is the single biggest
architectural difference from NTFS.

### Journaling

Metadata changes are written to a dedicated log *before* being applied. After a crash the journal is
replayed to finish or reverse incomplete operations, avoiding a full integrity scan (`fsck` / `chkdsk`).
A classic journal stores both **redo** (re-apply) and **undo** (roll back) records, because in-place
updates have to be reversible. NTFS (`$LogFile`) and ext4 work this way.

### Copy-on-write (CoW)

Instead of overwriting a block, the file system writes the modified data to a *new* location and then
atomically swings a root pointer to the new state. The old blocks stay intact on disk until reclaimed, so
the volume is *always* in a consistent state and a half-finished update simply leaves the old version in
force. ReFS and Btrfs use this model.

CoW is why ReFS needs only a **redo** log and never an undo log: there is no in-place change to reverse,
so the recovery log records only operations to re-apply. That is the structural opposite of the NTFS
journal, and it has a direct forensic payoff — the old pages an update leaves behind are recoverable from
a single image until the allocator reuses their clusters. [Copy-on-Write](copy_on_write.md) is the
canonical treatment of the mechanism and its artifacts;
[Transactions and Crash Consistency](transactions_crash_consistency.md) formalizes the redo-only
recovery, and [Deletion Recovery](deletion_recovery.md) turns the surviving pages into recovered files.

### Checksumming

A checksum computed over a block is stored separately; on each read the file system recomputes and
compares, catching silent corruption regardless of cause — including faults that journaling and CoW,
which protect only against *crash* inconsistency, cannot see. The two file systems differ in *scope*:

- **Btrfs** checksums both metadata and user data by default.
- **ReFS** checksums **metadata** (CRC64 by default on v3.14; *off* on original v3.4 volumes, which
  format with no metadata checksums), but checksums **user data only when integrity streams are
  enabled** — and that is a *per-file* opt-in, not a volume-wide setting.

For an analyst that scope difference is load-bearing: on a default ReFS volume a recomputable checksum
proves a *metadata* page is genuine, but it says nothing about whether a *data* cluster is original,
because no data checksum was ever written. [Checksum Architecture](checksum_architecture.md) details the
Merkle-tree layout and the algorithms per level, and [Integrity Streams](integrity_streams.md) covers the
per-file data-checksum opt-in and how to tell whether a given file carries one.

## The evolution this leads to

| Generation | Examples | Key properties |
|------------|----------|----------------|
| Simple allocation table | FAT | Hierarchical namespace, no integrity guarantees |
| Structured metadata | ext2 | Per-file inodes, permissions |
| Journaling | NTFS, ext4 | Crash consistency via redo/undo logs |
| Copy-on-write + checksums | Btrfs, ReFS | Atomic updates, integrity verification, snapshots |

ReFS belongs to the last generation, and the move it embodies — from a static, in-place allocation table
to a dynamic, copy-on-write, tree-indexed architecture — is the conceptual pivot the rest of these pages
build on. Every ReFS-specific behavior an analyst meets (virtual addressing, redo-only logging,
per-container relocation, snapshot recovery) is a consequence of that one architectural shift.

## Cross-references

- [Windows File Systems](windows_file_systems.md) — how a file system plugs into the Windows I/O stack and
  how `refs.sys` receives requests
- [Architecture](architecture.md) — how the general ideas here are assembled into the ReFS on-disk design
- [NTFS vs ReFS](ntfs_comparison.md) — the same choices made differently, mapped structure by structure
- [Carrier's Five Data Categories](carrier_categories.md) — the essential/optional split extended into a
  full forensic model
- [Virtual Addressing](virtual_addressing.md) — why a ReFS cluster number is not a disk offset
- [Cluster and Page Size](cluster_page_size.md) — how the format-time cluster size fixes the page size and
  address arithmetic
- [Copy-on-Write](copy_on_write.md) — the consistency model ReFS chooses, and the artifacts it leaves
- [Checksum Architecture](checksum_architecture.md) — the metadata Merkle tree
- [Integrity Streams](integrity_streams.md) — the per-file user-data checksum opt-in
- [Hard Links](hard_links.md) — the multi-name graph, reconstructed without a count field
- [Bootstrap Chain](bootstrap_chain.md) — how a ReFS volume is traversed from raw disk to metadata
- [Attributes — Forensic Reference](../attributes/README.md) — the per-file metadata catalog

## Evidence

This page is a conceptual orientation; it asserts no ReFS structure offsets, values, or driver internals
of its own. The ReFS-specific claims it makes in passing — copy-on-write and redo-only logging, metadata
checksummed by default on current versions (but never on original v3.4) with user-data checksummed only
under integrity streams, reparse points from the earliest
version with hard links gated to native v3.14, and the absence of a flat metadata table or an on-disk
hard-link count — are each established, with their evidence levels and finding IDs, on the linked page
that owns them (`copy_on_write.md`, `checksum_architecture.md`, `integrity_streams.md`, `hard_links.md`,
`ntfs_comparison.md`). See [how this was verified](../methodology.md) for the corpus and method behind
those pages.
