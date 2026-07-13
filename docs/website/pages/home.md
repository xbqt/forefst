---
title: "ReFS Reference"
---

A structural and forensic reference for Microsoft's **Resilient File System (ReFS)**, versions
**3.4 through 3.14** — what ReFS actually writes to disk, decoded byte by byte, with two open-source
[tools](https://github.com/xbqt/forefst) to parse a volume. Public ReFS forensic documentation largely stopped at version 3.4 (2019),
and there is still no real ReFS equivalent of the NTFS toolchain; this reference closes that gap.

## How a ReFS volume is organised

ReFS is Microsoft's **resilient, self-healing** file system — it first shipped with **Windows Server 2012**
and is today the default for **Storage Spaces** and **Dev Drives**. Unlike NTFS there is no `$MFT`:
metadata lives in **Minstore B+-trees**, and every table hangs off the **13 checkpoint root tables**
reached by a short bootstrap chain from the boot sector:

{{< bootstrap-roots >}}

A handful of ideas explain most of what ReFS writes to disk:

- **Copy-on-write.** A metadata page is never overwritten in place — a modified copy is written to a new
  location and the pointers above it are rewritten up to the checkpoint. This is what makes the volume
  crash-consistent and self-healing. See [Copy-on-Write](copy_on_write.md).
- **Objects and the Object Table.** Every file and directory is an object with a **64-bit Object ID that
  is monotonic and never reused** (the closest thing ReFS has to an inode), and the **Object Table** maps
  each ID to its on-disk location — ReFS's `$MFT`-equivalent. See [Object Table](object_table.md).
- **Two-level virtual addressing.** A file's data is described by *extents* (VCN → **VLCN**), and a
  separate **Container Table** translates those virtual clusters to physical ones (VLCN → **PLCN**).
  Almost every address on the volume is virtual and resolved through it. See
  [Virtual Addressing](virtual_addressing.md).
- **Resident vs non-resident storage.** A small stream sits *inline* in its B+-tree row (resident); a
  larger one lives in on-disk **extents** (non-resident). See [Resident Storage](resident_storage.md).
- **Checksums, integrity, and self-healing.** Every metadata page carries a checksum, and optional
  *integrity streams* checksum file data too. Core metadata is kept in **failover pairs**, so a mismatch
  is caught at mount and the good copy heals the bad one. See
  [Checksum Architecture](checksum_architecture.md) and [Redundancy](redundancy.md).
- **A durable change record.** A **USN V3** change journal records per-file changes, and a redo-only
  **MLog** transaction log makes every metadata update crash-safe. See [USN Journal](usn_journal.md) and
  [MLog](mlog.md).

On top of this ReFS layers block cloning, deduplication, tiered storage, and per-file **stream snapshots**.
The format grew from **3.4** (Windows 10, 1803) to **3.14** (Windows 11, 24H2); the shipping releases are
**not bootable**, and the Insider preview (build 29574) is the **first ReFS that can host a boot volume**,
adding TPM attestation. See [Version Evolution](version_evolution.md).

## For a forensic analyst

What matters when you sit down in front of a ReFS volume — each point links to the detail:

- **Reconstruct the timeline.** Every file carries a `$SI` **MACB** timestamp set, and two independent
  activity logs reinforce it — the **USN V3** change journal (create / write / rename / delete, with real
  times) and the redo-only **MLog** transaction log — which `forefst` merges into a single super-timeline.
  See [Artifact Timeline](artifact_timeline.md).
- **Recover deleted and prior data — realistically.** Because pages are written to new locations,
  superseded rows linger at stale clusters, and five independent methods (Trash table, checkpoint
  differencing, orphan-OID scan, stream-snapshot reconstruction, and B+-tree node-slack carving) recover
  what survives. It is not a guaranteed "undelete everything" — an active volume reuses that space quickly —
  but the [`$SNAPSHOT`](snapshots_versioning.md) stream is a *deterministic* prior-content path. See
  [Deletion Recovery](deletion_recovery.md) and [What Survives](what_survives.md).
- **Mine the ReFS-specific artifacts.** Reparse points (symlinks, junctions, mount points), **WSL / Linux
  metadata** and device nodes, alternate data streams, extended attributes, hard links (one shared FileId
  with one `$SI` **per name**), and `$RECYCLE.BIN` entries all decode to real evidence. See
  [Reparse Points](reparse_points.md), [WSL Metadata](wsl_metadata.md), and [Hard Links](hard_links.md).
- **Attribution and ownership.** Each file resolves to an owner and group **SID** and its DACL/SACL from a
  single volume-wide security-descriptor table. See [Security Descriptors](security_descriptors.md).
- **Date and attribute the volume itself.** A native v3.14 volume, an upgraded v3.4→v3.14 volume, and an
  original v3.4 volume are told apart on disk — which matters for dating and provenance. See
  [Version Detection](version_detection.md).
- **Know what breaks your NTFS tools.** No `$MFT`, no 8.3 short names, no `$FILE_NAME` twin, two-level
  addressing, and huge resident thresholds mean an NTFS reflex misses ReFS content entirely. See
  [NTFS vs ReFS](ntfs_comparison.md).

## The tools

Two open-source, pure-Python tools (3.6+ standard library, no install, no third-party dependencies) read a
raw image or volume. They live in the source repository — **[github.com/xbqt/forefst](https://github.com/xbqt/forefst)**.

Unlike the NTFS workflow, there is no artifact to extract first: ReFS has no single `$MFT` file, so instead of
carving one file out of an image and feeding it to a parser, you point the tool at the raw image and it
bootstraps the whole volume — the metadata tree, the change journal, and the transaction log all come from the
same image.

### [forefst.py](forefst.md) — the forensic tool

The ReFS answer to MFTECmd: point it at an image and get analyst-ready output. It can:

- **List every file and directory** with full metadata — MACB timestamps, sizes, attributes, owner/group
  **SID**, hard-link names, reparse targets, alternate data streams — as a **38-column CSV**, a **Sleuthkit
  body file** (for mactime / super-timelines), or **JSON**.
- **Recover deleted files** by five independent methods (Trash table, checkpoint differencing, orphan-OID
  scan, stream-snapshot reconstruction, B+-tree node-slack carving), plus **prior versions** of existing
  files through copy-on-write.
- **Build a super-timeline** that merges `$SI` MACB timestamps, the USN change journal, and the MLog
  transaction log — and **flag timestamp anomalies** (timestomping).
- **Read the change history** — decode the USN journal and the durable MLog log into readable
  create / write / rename / delete events.
- **Extract content and artifacts** — pull a file's data (resident, CoW-shared, or non-resident extents);
  decode **security descriptors** (with a tamper audit), **reparse points / WSL nodes**, **stream
  snapshots**, and **`$RECYCLE.BIN`** items; and **verify integrity-stream checksums**.

Every capability is a subcommand — `forefst.py <image> --list` shows them all.

### [refsanalysis.py](refsanalysis.md) — the structure analyser

Where forefst answers *"what happened on this volume?"*, refsanalysis answers *"what does this structure
look like?"* — it decodes one on-disk structure at a time (boot sector, superblock, checkpoint, the
object / schema / container / parent-child tables, the upcase table, and more), and includes a boot-sector
inspect/repair mode. It's the companion for learning the format and for validating the forensic tool
against new ReFS builds.
