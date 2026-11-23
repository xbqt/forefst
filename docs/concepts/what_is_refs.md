# What ReFS Is

ReFS, the Resilient File System, is a Microsoft file system for Windows, introduced in 2012 with Windows
Server 2012. It was built beside NTFS, not as its replacement: Windows still uses NTFS for its system
drive.

Microsoft describes its aim as "to maximize data availability, scale efficiently to large data sets
across diverse workloads, and provide data integrity with resiliency to corruption".

This page says what ReFS is for, what it gave up and gained over the years, where it is used and how it
compares with its peers. The other Concepts pages say what it leaves on disk.

## Why Microsoft built a second file system

NTFS updates its metadata in place and keeps a journal beside it, so that a change can be rolled back after
a failure. Microsoft's 2012 design post for ReFS names the cost of that model: writes become scattered and,
worse, "the act of updating the disk can corrupt previously written metadata if power is lost at the time of
the write", a *torn write*. The second cost is availability at scale. Repairing damaged metadata meant an
offline disk check, and on a very large volume that is a long outage. The post sets five goals:

1. keep the NTFS features that are widely used, and drop those that "provide limited value at the cost of
   system complexity and footprint";
2. verify data and correct it automatically, and never write metadata in place;
3. use structures that scale, without assuming that a disk check can scale to the whole volume;
4. never take the file system offline: isolate a fault, keep the rest of the volume available and salvage
   what can be saved, while it runs;
5. give full end-to-end resiliency together with Storage Spaces, which was designed with it.

## How the design answers those goals

**Metadata is never written in place.** A changed metadata page is written to a new location and the tree
above it is re-pointed, atomically. Microsoft calls this *allocate-on-write* and relates it to the old idea
of shadow paging: a power cut during the write cannot tear the metadata already on disk. The mechanism,
and what it leaves behind, is on the [Copy-on-Write](copy_on_write.md) page.

**What is read is checked.** Every metadata (B+-tree) page has a checksum, kept apart from the page in the
reference that points to it, so a lost or misdirected write is caught as well as a flipped bit; the
superblock and the checkpoint carry their own. Every metadata page reference of every volume of the test corpus
carries its checksum (see [Checksum Architecture](checksum_architecture.md) for the types).

File data is checked only when the file has an *integrity stream*, an option set on a file or inherited
from its directory (on a lab volume, files created inside a directory with integrity on had it too).

See [Checksum Architecture](checksum_architecture.md) and [Integrity Streams](integrity_streams.md).

**Everything is a B+-tree.** The on-disk engine stores everything in B+-trees, and a tree can sit
inside a row of another: a directory is a table, a file is a table embedded in a row of its directory, and
the volume's own bookkeeping is a set of global tables. Microsoft gives 35 PB as the largest file and the
largest volume, against 256 TB for NTFS. The layout is traced from the first sector on the
[Bootstrap Chain](bootstrap_chain.md) page.

**Repair online, or isolate the damage.** On a mirror or parity Storage Space, when a checksum fails,
ReFS reads the other copy and has the bad one rewritten, without taking the volume offline; a *scrubber*
reads the volume periodically to find corruption before it is needed. Where no good copy exists,
*salvage* removes the corrupt data from the namespace and, in most cases, keeps the rest of the volume
online. For an examiner, this means that a damaged volume mounted read-write repairs and removes things
by itself, so image it before you mount it ([Redundancy](redundancy.md)).

**The Windows semantics are NTFS's.** ReFS reuses the NTFS code that implements the file-system
interface (open, read, write, change notification, security, caching) and puts a new on-disk engine under
it. The driver read for these pages shows that split: an upper layer of `Refs*` functions over the
`Cms*` storage engine, Minstore ([Driver Architecture](architecture.md)).

## What it left out, and what came back

In 2012 ReFS did not implement ten NTFS features, and it could neither start Windows nor be used on a
removable drive. Microsoft's current comparison table (updated December 2025) shows most of the ten back:

| | Windows Server 2012 | Microsoft's table today |
|---|---|---|
| Named streams | no | yes |
| Sparse files | no | yes |
| Hard links | no | yes |
| Extended attributes | no | yes |
| Compression | no | yes (block system compression) |
| File encryption (EFS) | no | Windows Server 2025 only |
| Object IDs | no | no |
| Short (8.3) names | no | no |
| Transactions on user data | no | no |
| Disk quotas | no | no |
| Starting Windows from it | no | no |
| Removable media | no | no |

It also gained what NTFS has not: block cloning, sparse VDL (valid data length, which lets a large file
be zeroed rapidly), mirror-accelerated parity on Storage Spaces Direct and, from Windows Server 2022,
file-level snapshots. Deduplication came with Windows Server version 1709 and Windows Server 2019.

Some of these depend on the volume's format, not only on the Windows that mounts it. Hard-link support is
a boot-sector flag set when a volume is formatted at version 3.7 or later, so a volume upgraded from 3.4
has none; the driver refuses encryption on a volume below format 3.11, and the encryption stream is
observed only on 3.14 volumes ([Version Evolution](version_evolution.md#capability-differences)).

## Where ReFS is used

- **Windows Server.** Microsoft supports ReFS on Storage Spaces Direct, where it recommends it for virtual
  machines and network-attached storage; on Storage Spaces with shared SAS enclosures, for archives and
  user documents; on basic disks, for applications that bring their own resiliency; and as a backup target.
  Block cloning and sparse VDL make creating, merging and expanding virtual disks (`.vhdx`) much faster.
- **Windows 10 and 11.** Since Windows 10 version 1709, only the Enterprise and Pro for Workstations editions
  can create a ReFS volume; the other editions read and write existing ones.
- **Dev Drive.** From Windows 11 build 22621.2338, on every edition, a *Dev Drive* is a ReFS volume formatted
  for source trees, package caches and build output: at least 50 GB, never the C: drive, never on a
  removable disk, with block cloning from Windows 11 24H2 and Windows Server 2025. Microsoft documents the
  Dev Drive designation, its *trusted* state and its filter policy as kept by the machine (the trust flag in
  its registry) and not carried with the volume. Whether formatting a Dev Drive leaves a mark on the volume
  was not examined here.
- **The system drive, on Windows Server Insider builds.** The released versions of Windows do not boot from ReFS
  (Microsoft's feature table lists it as not bootable). Windows Server Insider builds do:
  - Microsoft announced ReFS boot for Windows Server Insiders in February 2026
    ([Announcing ReFS Boot for Windows Server Insiders](https://techcommunity.microsoft.com/blog/windowsservernewsandbestpractices/announcing-refs-boot-for-windows-server-insiders/4496592));
  - the test corpus holds one such boot volume, the C: drive of a Windows Server Insider 29574 machine (its own
    registry names the edition: Windows Server, build 29574);
  - the Insider drivers read (29574, 29659 and 29683) carry the boot-volume code, with a volume attestation by TPM
    or certificate that the 26100 drivers do not have.

## Versions

Every ReFS volume carries a format version, and the format has changed more than once. The forensic
literature describes ReFS 1.2, whose clusters were 64 KiB by default, and ReFS 3.2, with 4 KiB by
default, and notes that Windows upgrades a volume to its own latest version when it mounts it, unless a
registry value prevents it (Nordvik et al., 2019); ReFS 3.4 is analysed by Prade et al. (2020), and its
two journals by Lee et al. (2021). These pages cover the formats 3.4 to 3.14, written by Windows 10 1803
through Windows 11 24H2: [Version Evolution](version_evolution.md) records what changed at each step, and
[Version Detection](version_detection.md) tells a natively formatted volume from an upgraded one.

## ReFS among its peers

ReFS belongs to the generation of file systems that never overwrite metadata in place, with ZFS, Btrfs and
Apple's APFS ([File Systems](file_systems.md) explains the design space). They differ most in what they
check and in what they leave to other layers:

| | ReFS | ZFS | Btrfs |
|---|---|---|---|
| Updates | allocate-on-write | copy-on-write | copy-on-write |
| Metadata checksums | always | yes | yes, by default |
| File-data checksums | only for files with an integrity stream | yes, by default | yes, by default |
| Redundancy across disks | a separate layer, Storage Spaces | its own storage pools | its own multi-device support |
| Point-in-time copies | volume snapshots, file-level snapshots, block clones | snapshots and clones of a dataset | snapshots of a subvolume, writable or read-only |

APFS also uses copy-on-write, checksums its metadata with Fletcher's algorithm and clones files instead of
deduplicating them.

The row that matters most to an examiner is the third. On ZFS and Btrfs a file's bytes carry a checksum
by default; on ReFS only a file with an integrity stream does, and for a file without one nothing on disk
says what its bytes should be.

## Sources

- Microsoft, [Resilient File System (ReFS) overview](https://learn.microsoft.com/en-us/windows-server/storage/refs/refs-overview)
  (updated 9 December 2025): the aim quoted above, the resiliency and performance features, the supported
  deployments, the limits and the feature comparison with NTFS.
- Microsoft, [Building the next generation file system for Windows: ReFS](https://learn.microsoft.com/en-us/archive/blogs/b8/building-the-next-generation-file-system-for-windows-refs)
  (Surendra Verma, 16 January 2012): the goals, allocate-on-write, the checksums, salvage, the reuse of the
  NTFS upper layer, and the features left out in 2012.
- Microsoft, [Features and functionality removed in Windows client](https://learn.microsoft.com/en-us/windows/whats-new/removed-features):
  the Windows 10 1709 row on creating ReFS volumes.
- Microsoft, [Set up a Dev Drive on Windows 11](https://learn.microsoft.com/en-us/windows/dev-drive/)
  (updated 13 November 2026): the requirements, limits, trust and block cloning of a Dev Drive, and NTFS as
  the system drive.
- OpenZFS, [Checksums and Their Use in ZFS](https://openzfs.github.io/openzfs-docs/Basic%20Concepts/Data%20Storage/Checksums.html)
  and [zfsconcepts(7)](https://openzfs.github.io/openzfs-docs/man/master/7/zfsconcepts.7.html); the FreeBSD
  Handbook, [ZFS](https://docs.freebsd.org/en/books/handbook/zfs/) (copy-on-write).
- Btrfs documentation, [Introduction](https://btrfs.readthedocs.io/en/latest/Introduction.html) and
  [Checksumming](https://btrfs.readthedocs.io/en/latest/Checksumming.html).
- Apple, [Apple File System Guide: FAQ](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/APFS_Guide/FAQ/FAQ.html).
- R. Nordvik, H. Georges, F. Toolan, S. Axelsson, "Reverse engineering of ReFS", *Digital Investigation* 30
  (2019) 127-147, [doi:10.1016/j.diin.2019.07.004](https://doi.org/10.1016/j.diin.2019.07.004).
- P. Prade, T. Groß, A. Dewald, "Forensic Analysis of the Resilient File System (ReFS) Version 3.4",
  *Forensic Science International: Digital Investigation* 32 (2020) 300915,
  [doi:10.1016/j.fsidi.2020.300915](https://doi.org/10.1016/j.fsidi.2020.300915).
- S. Lee, J. Park, H. Hwang, S. Lee, S. Lee, D. Jeong, "Forensic analysis of ReFS journaling", *Forensic
  Science International: Digital Investigation* 38 (2021) 301136,
  [doi:10.1016/j.fsidi.2021.301136](https://doi.org/10.1016/j.fsidi.2021.301136).

## Cross-references

- [File Systems](file_systems.md) — the general ideas (allocation, extents, journaling, copy-on-write,
  checksums) this page assumes
- [Windows File Systems](windows_file_systems.md) — how `refs.sys` sits in the Windows I/O stack beside
  `ntfs.sys`
- [NTFS vs ReFS](ntfs_comparison.md) — the two on-disk designs compared structure by structure
- [Version Evolution](version_evolution.md) — the formats 3.4 to 3.14 and what changed between them
- [A first examination](../examples/first_examination.md) — the examiner's route through a ReFS
  volume, as a worked example

## Evidence

This page is a background orientation. Its statements about Microsoft's aims, features, editions, limits
and supported deployments, and about ZFS, Btrfs and APFS, come from the sources above, which this project
did not test; where a statement depends on a source's date, the date is given. Its statements about the
on-disk format (allocate-on-write, the metadata checksums, integrity streams, the B+-tree tables, the
two-layer driver, hard-link support by format, the encryption stream at 3.14, the Insider driver's
attestation code) are established on the linked pages, each with its evidence.

See [how this was verified](../methodology.md).

<!-- findings: GN_ARCH_001, GN_ARCH_002, GN_ARCH_003, GN_ARCH_004, FN_LINK_001, GN_INS_SA_001, GN_INS_SA_002 -->
