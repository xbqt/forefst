---
title: "ReFS Reference"
description: "The most complete public forensic reference for Microsoft's Resilient File System (ReFS) 3.4–3.14 — the on-disk format decoded byte by byte, with two open-source tools (forefst) to parse a raw volume."
---

A structural and forensic reference for Microsoft's **Resilient File System (ReFS)**, versions
**3.4 through 3.14** — what ReFS actually writes to disk, decoded byte by byte, with two open-source
[tools](https://github.com/xbqt/forefst) that read a raw volume with no dependencies. Public ReFS forensic
documentation largely stopped at version **3.4 (2019)**, and almost everything that opens a *current* volume
is commercial and closed. This is the open alternative: the most complete public account of the on-disk
format through 3.14, and a tool you can download, read line by line, and point at a modern ReFS volume for
the full forensic job.

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
- **Objects and the Object Table.** Directories and larger files are objects with a **64-bit Object ID
  that is monotonic and never reused** (the closest thing ReFS has to an inode); a small *resident* file
  has none — it lives inline in its parent directory's row. The **Object Table** maps each ID to its
  on-disk location — ReFS's `$MFT`-equivalent. See [Object Table](object_table.md).
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

- **Reconstruct the timeline — and catch tampering.** Every file carries a `$SI` **MACB** set, reinforced
  by two independent logs: the **USN V3** change journal and the redo-only **MLog** transaction log, which
  `forefst` decodes into concrete create / write / rename / move / delete actions and merges into one
  super-timeline. And because a hard-linked file keeps **one `$SI` per name** — ReFS has no `$FILE_NAME`
  twin — a back-dated name stands out against its siblings: a timestomp signal NTFS can't offer. See
  [Artifact Timeline](artifact_timeline.md) and [Timestomp Detection](timestomp_detection.md).
- **Recover what survives — and prove what's gone.** Copy-on-write leaves superseded rows at stale
  clusters, and five methods (Trash table, checkpoint differencing, orphan-page scan, stream-snapshot
  reconstruction, B+-tree node-slack carving) recover what the volume hasn't reused — realistically, not a
  guaranteed "undelete everything," though the [`$SNAPSHOT`](snapshots_versioning.md) stream is a
  *deterministic* prior-content path. And because Object IDs are **never reused**, a gap in the sequence is
  durable evidence that an object existed and was deleted — even after every byte it touched is overwritten.
  See [Deletion Recovery](deletion_recovery.md) and [What Survives](what_survives.md).
- **Mine the ReFS-specific artifacts.** Reparse points (symlinks, junctions, mount points), **WSL / Linux
  metadata** and device nodes, alternate data streams, extended attributes, hard links, and `$RECYCLE.BIN`
  entries all decode to real evidence. See [Reparse Points](reparse_points.md),
  [WSL Metadata](wsl_metadata.md), and [Hard Links](hard_links.md).
- **Attribute the volume and its files.** Each file resolves to an owner and group **SID** and its
  DACL/SACL from a single volume-wide security table; and a native v3.14, an upgraded v3.4→v3.14, and an
  original v3.4 volume are told apart from an on-disk marker an upgrade can't fake — which matters for
  dating and provenance. See [Security Descriptors](security_descriptors.md) and
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

Think of it as MFTECmd for ReFS: point it at an image and get analyst-ready output. It can:

- **List every file and directory** with full metadata — MACB timestamps, sizes, attributes, owner/group
  **SID**, hard-link names, reparse targets, alternate data streams — as a **38-column CSV**, a **Sleuthkit
  body file** (for mactime / super-timelines), or **JSON**.
- **Recover deleted files** by five independent methods (Trash table, checkpoint differencing, orphan-page
  scan, stream-snapshot reconstruction, B+-tree node-slack carving), plus **prior versions** of existing
  files through copy-on-write.
- **Build a super-timeline** that merges `$SI` MACB timestamps, the USN change journal, and the MLog
  transaction log — and **flag timestamp anomalies** (timestomping).
- **Read the change history** — decode the USN journal and the durable MLog log into readable
  create / write / rename / move / delete events.
- **Extract content and artifacts** — pull a file's data (resident, CoW-shared, or non-resident extents);
  decode **security descriptors** (with a tamper audit), **reparse points / WSL nodes**, **stream
  snapshots**, and **`$RECYCLE.BIN`** items; and **verify integrity-stream checksums**.

Every capability is a subcommand — `forefst.py <image> --list` shows them all. And every field it prints
traces to a graded-evidence claim register; `--provenance` marks the ones that rest on inference rather
than on facts confirmed in both the decompiled driver and the disk — so the output is auditable, not a
black box.

### [refsanalysis.py](refsanalysis.md) — the structure analyser

Where forefst answers *"what happened on this volume?"*, refsanalysis answers *"what does this structure
look like?"* — it decodes one on-disk structure at a time (boot sector, superblock, checkpoint, the
object / schema / container / parent-child tables, the upcase table, and more), and includes a boot-sector
inspect/repair mode. It's the companion for learning the format and for validating the forensic tool
against new ReFS builds.

### Try it in two minutes

Both tools are pure Python (3.6+, standard library) — nothing to install. Clone the
[repository](https://github.com/xbqt/forefst), grab one of the sample images under `analysis/samples/`
(each ships with a one-line decompress recipe), and run:

```bash
python3 forefst.py disk.raw summary        # volume overview: version, size, counts, upgrade state
python3 forefst.py disk.raw -o files.csv   # full 38-column listing, opens straight in Timeline Explorer
python3 forefst.py disk.raw mlog --parse   # decode the transaction log into user actions
```

Point it at a raw image (`dd` / `.raw`), a disk device, or an E01 exported to raw — forefst finds the ReFS
partition itself.
