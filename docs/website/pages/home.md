---
title: "ReFS Reference"
---

A structural and forensic reference for Microsoft's **Resilient File System (ReFS)**, versions
**3.4 through 3.14** — what ReFS actually writes to disk, decoded byte by byte, with two open-source
[tools](https://github.com/xbqt/forefst) to parse a volume. Public ReFS forensic documentation largely stopped at version 3.4 (2019),
and there is still no real ReFS equivalent of the NTFS toolchain; this reference closes that gap.

## How a ReFS volume is organised

Everything on the volume hangs off **13 checkpoint root tables**, reached by a short bootstrap chain from
the boot sector. This is the map to keep in mind — each box links to its byte-level reference:

{{< bootstrap-roots >}}

## For a forensic analyst

- **No `$MFT`.** Metadata lives in **B+-trees**; every file and directory is an object in an
  **Object Table**, keyed by a 64-bit **Object ID that is monotonic and never reused** — a reliable
  timeline anchor.
- **Copy-on-write keeps history.** ReFS never overwrites a metadata page in place, so earlier
  versions of files and metadata frequently survive at stale clusters and stay **recoverable** until
  the space is reused.
- **Three distinct volume states** — original, upgraded, and native v3.14 — are distinguishable on
  disk, which matters for dating and attributing a volume.
- **Plenty to mine:** per-file MACB timestamps, a **USN change journal**, **stream snapshots**,
  integrity-stream checksums, reparse points (symlinks / junctions / WSL), and alternate data
  streams (always stored inline).
- **Deleted files** are recoverable through several independent paths — the trash table, checkpoint
  differencing, and orphan-page / node-slack scanning.

## Know the limits

- Coverage is **ReFS 3.4 – 3.14 (+ Insider 29574)**; other versions may differ.
- The tools read a **raw image or volume** — a **BitLocker**-encrypted volume must be decrypted first.
- ReFS has **no 8.3 short names** and does not duplicate timestamps in a filename attribute, so the
  classic NTFS `$SI`-vs-`$FN` timestomp cross-check does not exist; other anchors apply (see
  [Timestomping Detection](/concepts/timestomp_detection/)).
