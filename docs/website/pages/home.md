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
- **Two-level ("double") virtual addressing.** A file's data is described by *extents* (VCN → **VLCN**),
  and a separate **Container Table** translates those virtual clusters to physical ones (VLCN → **PLCN**).
  Almost every address on the volume is virtual and resolved through it. See
  [Virtual Addressing](virtual_addressing.md).
- **Resident vs non-resident storage.** A small stream sits *inline* in its B+-tree row (resident); a
  larger one lives in on-disk **extents** (non-resident). See [Resident Storage](resident_storage.md).
- **Object IDs.** Every file and directory is an object identified by a **64-bit Object ID that is
  monotonic and never reused** — the closest thing ReFS has to an inode. See
  [Object IDs](object_ids_fileids.md).
- **Checksums and integrity.** Every metadata page carries a checksum, and optional *integrity streams*
  checksum file data too; a mismatch is caught at mount and, on a redundant volume, self-healed. See
  [Checksum Architecture](checksum_architecture.md).

On top of this ReFS layers block cloning, deduplication, tiered storage, and per-file **stream snapshots**.
The format grew from **3.4** (Windows 10, 1803) to **3.14** (Windows 11, 24H2); the shipping releases are
**not bootable**, and the Insider preview (build 29574) is the **first ReFS that can host a boot volume**,
adding TPM attestation. See [Version Evolution](version_evolution.md).

## For a forensic analyst

What matters when you sit down in front of a ReFS volume — each point links to the detail:

- **No `$MFT`, but a stronger timeline anchor.** File identity is the **Object ID**, monotonic and never
  reused — so a *gap* in the OID sequence is direct evidence that an object was created and later deleted,
  and OIDs order objects by creation even when no other trace survives. See
  [OID Allocation](oid_allocation.md).
- **No 8.3 short names, no `$FILE_NAME` timestamp twin.** ReFS keeps one `$SI` timestamp set **per name**,
  so NTFS's classic `$SI`-vs-`$FN` timestomp cross-check simply does not exist. The ReFS equivalent is
  comparing the per-name timestamps of a **hard-linked** file against each other. See
  [Timestomping Detection](timestomp_detection.md).
- **A rich change history.** A **USN V3** change journal (128-bit file IDs) plus the redo-only **MLog**
  transaction log let you reconstruct create / write / rename / delete activity with real timestamps. See
  [Artifact Timeline](artifact_timeline.md).
- **Copy-on-write leaves prior versions behind — opportunistically.** Because pages are written to new
  locations, superseded file and metadata rows often linger at stale clusters. This is *not* a reliable
  "undelete everything" — on an active volume that space is reused quickly — but several independent paths
  (trash table, checkpoint differencing, orphan-page and node-slack scanning) recover what does survive.
  See [Deletion Recovery](deletion_recovery.md) and [What Survives](what_survives.md).
- **Three distinguishable volume states.** A native v3.14 volume, an upgraded v3.4→v3.14 volume, and an
  original v3.4 volume are told apart on disk — which matters for dating and attributing a volume. See
  [Version Detection](version_detection.md).
- **The full picture.** For a side-by-side with NTFS — bootstrap, addressing, journaling, slack, and
  resident thresholds — see [NTFS vs ReFS](ntfs_comparison.md).

## The tools

Two open-source, pure-Python tools (3.6+ standard library, no install) read a raw image or volume:

- **[forefst.py](forefst.md)** — the ReFS answer to MFTECmd: a forensic file lister with 38-column CSV /
  body-file / JSON output, deleted-file and copy-on-write recovery, the USN journal and MLog transaction
  log, super-timelines, timestomp detection, file extraction, security descriptors, reparse points, and
  stream snapshots.
- **[refsanalysis.py](refsanalysis.md)** — an interactive structural analyser that decodes one on-disk
  structure at a time (boot sector, checkpoint, superblock, the B+-tree tables, and more) — for learning
  the format and validating the forensic tool.

Both live in the source repository: **[github.com/xbqt/forefst](https://github.com/xbqt/forefst)**.
