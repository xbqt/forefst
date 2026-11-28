---
title: "ReFS Forensics Reference"
description: "A forensic reference for Microsoft's Resilient File System (ReFS) — the on-disk format decoded byte by byte, with two open-source tools (forefst) to parse a raw disk or partition image. Tested on ReFS 3.4–3.14 volumes (3.7, 3.9 and 3.10: one volume each)."
---

This site is **a structural and forensic reference for Microsoft's Resilient File System (ReFS), versions 3.4
through 3.14.** It decodes what ReFS actually writes to disk, byte by byte, and comes with two open-source
[tools](https://github.com/xbqt/forefst) that read a raw disk or partition image with no dependencies. The format is
read from two sources, wherever both can be read: the ReFS driver's own code and real volumes.
The newest driver builds read are {{< latest-driver >}}.

## How this site is organised

- **[Concepts](/concepts/)** — how ReFS works and what that means for an examination: copy-on-write, virtual
  addressing, file identity, deleted files, timelines.
- **[Structures](/structures/)** — the byte layout of each on-disk structure, from the boot sector to the journals.
- **[Attributes](/attributes/)** — what a file's or a directory's record holds: `$STANDARD_INFORMATION`, `$DATA`,
  reparse points, extended attributes and the rest.
- **[Tools](/tools/)** — the two tools:
  - the [forefst.py help](forefst.md), its [internals](internals.md), and the [refsanalysis.py](refsanalysis.md) page;
  - [migrating between releases](migration.md), the [known issues](known_issues.md) of this release, and the list of
    [releases](releases.md);
  - worked examples, from [a first examination](first_examination.md) to [decoding a boot sector by hand](decode_vbr_by_hand.md).
- **[Glossary](/glossary/)** — the terms the pages use.
- **[Methodology](/verification/)** — how the facts were established: their two sources, the driver builds and the
  volumes tested, the confidence grades, and how corrections are tracked.
- **[About](/about/)** — the project: how it began and why it exists.

## How a ReFS volume is organised

ReFS is Microsoft's **resilient, self-healing** file system. It first shipped with **Windows Server 2012**;
Microsoft recommends it on **Storage Spaces Direct**, and every **Dev Drive** is a ReFS volume.

Unlike NTFS there is no `$MFT`: metadata lives in **Minstore B+-trees**, and every table hangs off the **13
checkpoint root tables**, reached by a short bootstrap chain from the boot sector:

{{< bootstrap-roots >}}

Eight ideas explain most of what ReFS writes to disk.

- **A transactional B+-tree engine (Minstore).** Beneath the file-system layer, ReFS is a general-purpose key-value
  store.
  - Every table — directories, the object map, security, containers, the allocators — is a Minstore **B+-tree** of
    sorted rows on 16 KiB pages (64 KiB on a volume with 64 KiB clusters).
  - A reader that parses this tree can walk every table, whatever higher-level feature produced it; each row's content
    still has its own format.

  See: [Architecture](architecture.md) · [B+-tree Node](btree_node.md)

- **Copy-on-write.** A B+-tree page is never overwritten in place.
  - A modified copy is written to a new location, and the pointers above it are rewritten up to the checkpoint.
  - The superblock copies and the two checkpoint slots are the exception: they sit at fixed places and are rewritten
    there.
  - This is what makes the volume crash-consistent and self-healing, and it is why superseded data stays on disk and
    can be recovered.

  See: [Copy-on-Write](copy_on_write.md)

- **Objects and the Object Table.** Directories and system tables are objects; files are not.
  - An object has a **64-bit Object ID that only moves forward** where the 26100 and Insider drivers write the volume (they keep its counter on it): the
    closest thing ReFS has to an inode.
  - A file lives as rows inside its directory's tree and is identified by a **File ID**: its home directory's Object
    ID plus a per-directory birth ordinal, **fixed at creation**, so it stays the same when the file is renamed or
    moved to another directory.
  - The **Object Table** maps each Object ID to its location on disk: the ReFS counterpart of `$MFT`.

  See: [Object Table](object_table.md) · [File IDs](file_ids.md)

- **Two-level virtual addressing.** Almost every address on the volume is virtual.
  - A file's data is described by *extents* (VCN → **VLCN**), and a separate **Container Table** translates those
    virtual clusters to physical ones (VLCN → **PLCN**).
  - This is also what lets ReFS relocate and tier data underneath a file.

  See: [Virtual Addressing](virtual_addressing.md)

- **Where a file's bytes live.** A small stream sits **inline** in its B+-tree row; a larger one lives in on-disk
  **extents**.
  - The inline ceiling is **2 KiB** on modern volumes (format 3.11 and later); below it, a small file usually sits
    whole inside a metadata row, where a cluster carver never looks.
  - On older formats a file's main data is never inline; there, only an *alternate data stream* can sit in a row, up
    to a hard 128 KiB.

  See: [Record placement and data residency](placement_and_residency.md)

- **Checksums, integrity and self-healing.** Every metadata page is checksummed, and the driver checks a page when it
  reads it.
  - A page's checksum is stored in the reference that points to it, from the checkpoint down; optional *integrity
    streams* checksum file data too.
  - Core tables (the Object, Schema and Container tables among them) are kept as **failover pairs**: when one copy
    fails its check the other is read. For the Object Table, the driver read (26100.8115) also repairs the failed copy
    from the good one on a writable mount.

  See: [Checksum Architecture](checksum_architecture.md) · [Redundancy](redundancy.md)

- **A durable change record.** The volume keeps two independent change records to build a timeline from.
  - A **USN V3** change journal, where the volume has one active, records per-file changes.
  - A redo-only **MLog** transaction log makes every metadata update crash-safe.

  See: [USN Journal](usn_journal.md) · [MLog](mlog.md)

- **Shared and tiered blocks.** On top of the core, ReFS shares clusters between files and moves data between tiers.
  - Block cloning and deduplication share clusters between files; the Block Refcount table counts those references.
  - Per-file **stream snapshots** keep earlier versions on clusters their own extent maps still name; they add no
    count.
  - Tiered storage moves data between a fast and a slow tier underneath the file.

  See: [Snapshots & Versioning](snapshots_versioning.md) · [Deduplication](deduplication.md) ·
  [Tiered Storage](tiering.md)

The format grew from **3.4** (Windows 10, 1803) to **3.14** (Windows 11, 24H2).

ReFS can also be the **boot volume**: Windows Server Insider builds install on and boot from a ReFS C: drive, which
Microsoft announced in February 2026 ([Announcing ReFS Boot for Windows Server Insiders](https://techcommunity.microsoft.com/blog/windowsservernewsandbestpractices/announcing-refs-boot-for-windows-server-insiders/4496592)). The test corpus holds
one: the C: drive of a Windows Server Insider 29574 machine. The released versions of Windows do not boot from ReFS (Microsoft's ReFS overview; see [What ReFS Is](/concepts/what_is_refs/)).

See [Version Evolution](version_evolution.md).

## The tools

Two open-source, pure-Python tools (3.7+ standard library, no install, no third-party dependencies) read a raw disk
or partition image. They live in the source repository — **[github.com/xbqt/forefst](https://github.com/xbqt/forefst)**.

Unlike the NTFS workflow, there is no artifact to extract first. ReFS has no single `$MFT` file, so instead of
carving one file out of an image and feeding it to a parser, you point the tool at the raw image and it bootstraps
the whole volume: the metadata tree, the change journal and the transaction log all come from the same image.

The closest thing to an `$MFT` extract is `forefst.py <image> export metadata -o DIR`: it writes the volume's metadata
(the boot structures, every reachable metadata page, the change journal and the MLog) into a hash-sealed directory of a few MB to
over a GB, which `forefst.py` reads as it reads the image itself.

See [Metadata bundle](metadata_bundles.md).

### [forefst.py](forefst.md) — the forensic tool

It is the ReFS counterpart of MFTECmd: it reads an image directly and prints output ready for analysis. It can:

- **List every file and directory** with full metadata.
  - MACB timestamps, sizes, attributes, owner and group **SID**, hard-link names, reparse targets, alternate data
    streams.
  - As a **42-column CSV**, a **Sleuthkit body file** (for mactime and super-timelines) or **JSON**.
- **Recover deleted files**, best effort, from what the metadata pages still hold.
  - `deleted` reads the Trash table, compares the volume's two checkpoints and scans the free space of the metadata
    pages in use; `deleted --full` also reads every old metadata page on the volume.
  - An opt-in, low-confidence tier lists the directory objects the Object Table still holds but the tree no longer
    reaches.
  - **Prior versions** of existing files come from their stream snapshots.
- **Build a super-timeline** that merges the `$SI` MACB timestamps, the USN change journal and the MLog transaction
  log, and **flag timestamp anomalies** (timestomping) — both experimental.
- **Read the change history**: decode the USN journal and the MLog into readable create / write / rename / move /
  delete events.
- **Extract content and artifacts.**
  - A file's data: inline, snapshot-shared or from extents.
  - **Security descriptors** (with a tamper audit), **reparse points / WSL nodes**, **stream snapshots** and
    **`$RECYCLE.BIN`** items.
  - **Integrity-stream checksums**, verified.

Every capability is a subcommand: `forefst.py --list` shows them all.

The fields it prints are documented against a graded-evidence claim register, which separates what rests on
inference from what was confirmed in the decompiled driver, on disk, or both — so that a printed field can be
traced to its evidence.

### [refsanalysis.py](refsanalysis.md) — the structure analyser

forefst reports what happened on the volume; refsanalysis shows what one on-disk structure contains, field by
field.

- It decodes one on-disk structure at a time: the boot sector, superblock and checkpoint, the object / schema /
  container / parent-child tables, the upcase table, and more.
- It includes a boot-sector inspect and repair mode.
- It is the companion for learning the format. It imports its parsing layer from `forefst.py`, so it is not an
  independent check of it.
- 1.14.0 is its last release, and it runs only with forefst 1.14.0 (see [its status](refsanalysis.md)).
