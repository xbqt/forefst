---
title: "ReFS Forensics 101"
description: "A one-page orientation to ReFS forensics — how a volume is laid out, what identifies a file, what survives deletion, and what to look for — with links into the detail."
---

# ReFS Forensics 101

The one-page orientation for an analyst sitting down in front of a **ReFS** volume: how the file system is
laid out, what identifies a file, what survives deletion, and where the evidence lives. Every section links
to the detail — read this top to bottom, then jump to what your case needs.

## What ReFS is

ReFS (the **Resilient File System**) is Microsoft's modern, self-healing file system — the default for
**Storage Spaces** and **Dev Drives**, and common on Windows Server and Windows 11. It is **not NTFS with a
new name**: there is no `$MFT`, no `$FILE_NAME` attribute, no 8.3 short names, and addresses are virtual, not
physical. The on-disk format is versioned; public forensic knowledge long stopped at **3.4 (2019)**, while
Windows 11 24H2 now ships **3.14**. The shipping releases are **not bootable** — only the Insider preview
(build 29574) can host a boot volume. See [Version Evolution](version_evolution.md) and
[NTFS vs ReFS](ntfs_comparison.md).

## How a volume is laid out

Everything hangs off a short, fixed **bootstrap chain** that a parser must walk before it can read anything:
the boot sector (**VBR**) names the version and cluster size, points to the **superblock** at a fixed
location, which points to the current **checkpoint**, which holds the **13 root tables**. Below the
file-system layer, ReFS is a transactional key-value engine (**Minstore**): every table — directories, the
object map, security, containers — is a **B+-tree** of sorted rows on 16 KiB or 64 KiB pages. The
**Object Table** maps each object to its location and is the closest thing ReFS has to an `$MFT`.

{{< bootstrap-roots >}}

See [Bootstrap Chain](bootstrap_chain.md), [Architecture](architecture.md), and
[Object Table](object_table.md).

## What identifies a file

ReFS splits identity in a way NTFS does not:

- **Directories and system tables are objects** with a 64-bit **Object ID (OID)** that is **monotonic and
  never reused**. Because IDs are never recycled, a *gap* in the sequence is durable evidence that an object
  once existed and was deleted — even after every byte it touched is overwritten. See
  [Object IDs](object_ids.md).
- **Files have no OID.** A file is identified by a 128-bit **File ID** = its **home directory's OID** plus a
  per-directory **birth ordinal**, and that reference is **frozen at creation** — it survives a rename and
  even a move to another directory. A tell worth knowing: a cross-directory **move forces the file
  non-resident**, a one-way change that leaves a trace of the file's origin. See [File IDs](file_ids.md) and
  [Resident Storage](resident_storage.md).

## Timestamps and the timeline

Every object carries a `$STANDARD_INFORMATION` with the four **MACB** timestamps. Two independent change
records corroborate them: the **USN V3** change journal and the redo-only **MLog** transaction log, which
decode into concrete create / write / rename / move / delete events. Merged with the MACB set they form a
**super-timeline**. And because a hard-linked file keeps **one `$SI` per name** (there is no `$FILE_NAME`
twin to fall back on), a back-dated name stands out against its siblings and against the journals — the basis
of ReFS **timestomp** detection. These are corroborative signals, not an authoritative log. See
[Artifact Timeline](artifact_timeline.md), [Timestomping Detection](timestomp_detection.md),
[USN Journal](usn_journal.md), and [MLog](mlog.md).

## What survives deletion

Copy-on-write means metadata is **never overwritten in place**: a change is written to a new location, so the
superseded rows linger at stale clusters until reused. Recovery draws on several independent sources — the
**Trash table** (deferred deletions), **checkpoint differencing**, **node slack** (deleted rows still in a
live page), **orphan pages** (freed metadata pages the live tree no longer references), and **stream
snapshots**, which are a *deterministic* prior-content path. Remnants are classified by **file identity**
(name + creation time), so a moved or renamed file is never mistaken for a deletion. This is realistic
recovery, not a guaranteed "undelete everything." See [Deletion Recovery](deletion_recovery.md) and
[What Survives](what_survives.md).

## ReFS-specific artifacts

A ReFS volume carries evidence NTFS tools miss entirely:

- **Reparse points** — symlinks, junctions, mount points, and WOF-compressed files. See
  [Reparse Points](reparse_points.md).
- **WSL / Linux metadata** — POSIX owner/mode/device stored in extended attributes (`$LX*`), plus device
  nodes and symlinks. See [WSL Metadata](wsl_metadata.md).
- **Hard links** — many names for one file, each with its **own** timestamps. See [Hard Links](hard_links.md).
- **Alternate data streams, extended attributes, stream snapshots, `$RECYCLE.BIN`, and integrity streams** —
  all decode to real evidence, and integrity streams let you **verify a file's content** cluster by cluster.

## Attribution and provenance

Each object resolves to an owner and group **SID** and its DACL/SACL through a single volume-wide security
table. A volume's history is itself evidence: a **native** 3.14, an **upgraded** 3.4→3.14, and an **original**
3.4 volume are told apart by an on-disk marker an upgrade cannot fake — which matters for dating and
provenance — and the volume creation time is a hard lower bound for every file on it. See
[Security Descriptors](security_descriptors.md) and [Version Detection](version_detection.md).

## The tools

There is no artifact to carve out first: ReFS has no single `$MFT` file, so you point the tool at the raw
image and it bootstraps the whole volume.

- **[forefst.py](forefst.md)** — the forensic tool, the ReFS answer to MFTECmd: a full file listing
  (CSV / body file / JSON) with deleted-file and copy-on-write recovery, the USN and MLog journals,
  super-timelines, timestomp detection, security descriptors, reparse points, and stream snapshots.
- **[refsanalysis.py](refsanalysis.md)** — the structural analyser: decodes one on-disk structure at a time,
  with a boot-sector inspect/repair mode — for learning the format and validating the forensic tool.

Both are pure Python (3.7+ standard library, no dependencies). Start with the [Concepts](/concepts/),
[Structures](/structures/), and [Attributes](/attributes/) references for the full detail behind each point
above.
