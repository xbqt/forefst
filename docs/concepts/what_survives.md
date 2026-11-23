# What Survives: Artifact-vs-Event Survival Matrix

For each event that can happen to a ReFS volume, this page says which artifacts an analyst can still recover, and
by which method.

It cross-tabulates eight forensic artifacts against five events — file deletion, quick format, an in-place
v3.4→v3.14 upgrade, a clean unmount, and a crash — and states, per cell, whether the artifact survives and which
recovery method reaches it.

On ReFS, survival depends mostly on the [copy-on-write](copy_on_write.md) update
model for metadata: no metadata page is overwritten in place (a changed page is written to a new location), so the
limiting factor is usually *cluster reallocation*, not the triggering event itself. (The change journal is the
exception: it is an in-place ring.)

## The three mechanisms behind the cells

Most cells in the matrix below follow from three properties of the file system; the exceptions are named in the
cells.

<!-- site: diagram "survival-mechanisms.svg" "The three mechanisms: copy-on-write leaves old pages on disk, the log is redo-only, and some boot-sector fields keep their format-time value." -->

**1. Copy-on-write writes new and frees old.** When an object is modified or deleted, its prior pages are
*dereferenced*, not scrubbed — the bytes stay on disk until the [allocator](../structures/allocators.md) hands
those clusters to a later write.

This is why "survives" and "recoverable" mean different things throughout this page: the bytes are present, but
reaching them depends on whether the clusters were reused.

The strongest case is a cluster that a live map still names — a stream snapshot's extents, a clone's: it is not
free, so it survives while that map lives. The detailed mechanism is on the [Copy-on-Write](copy_on_write.md)
page, and the recovery categories that follow from it are in [Deletion Recovery](deletion_recovery.md).

**2. Logging is redo-only — there is no undo pass.** The [MLog](../structures/mlog.md) is a redo-only journal:
each record holds the values its transaction wrote, and no record holds the value a change replaced (no
pre-images). Crash recovery (`CmsRestarter`) replays redo records *forward* onto pages that CoW already left
intact, so ReFS never performs the undo pass that an NTFS `$LogFile` runs. Two forensic consequences follow:

- no record holds the value a change replaced. An earlier value can still be in an earlier record of the same
  file while the log keeps it: the transaction that created a file holds its first times, and each call that set
  its times holds the `$SI` it wrote;
- after a crash, a page the interrupted session wrote after its last checkpoint is referenced by no checkpoint (the
  next mount rebuilds those changes by replaying the log from that checkpoint's log position), so such a page can
  stay on disk, unreferenced, until its space is reused; this follows from the replay and was not measured on a
  crashed image.

Prior state therefore comes from [snapshots](../attributes/SNAPSHOT.md), superseded CoW pages and the earlier log
records still held, never from an undo record.

**3. Some VBR fields keep their format-time value.** Two [Volume Boot Record](../structures/vbr.md) fields are
format-time: the checksum-algorithm selector (0x2A) and the Extended GUID (0x48). No boot-sector write path of the
26100.9444 driver assigns them (`refsutil fixboot` rewrites both), and they kept their values across the two
upgrades measured. The volume flags (0x2C)
are written at run time, but their format bits (0x20, 0x40) kept their values across those upgrades.

Because they keep their format-time values, they show how the volume was formatted and, with the checkpoint
flags, decide the [upgrade-vs-native](version_detection.md) question discussed below.

What each event does to the on-disk image, in one line apiece:

```text
event ──► what it does to the on-disk image
─────────────────────────────────────────────────────────────────
delete         remove the live B+-tree offset-array slot (row body NOT scrubbed), dereference
               pages; reparent to the Trash Table (OID 0x0D) only what passes the Trash gate
               (a data stream set of 2+ tables, or two rarer conditions)
quick format   write a fresh metadata skeleton; old clusters left as slack
upgrade        rewrite VBR version (0x28) + checksum (0x16), bump CHKP flags
               (0x002→0x602), advance the checkpoint clock (35 and 41 checkpoints on the
               two upgrades measured); leave 0x2A/0x48 and the format bits of 0x2C
clean unmount  both CHKP copies usually point to the same 13 root pages; the clock stops
crash          last transaction may be torn; redo log replayed forward, no undo
```

## The survival matrix

The matrix is the main content of this page. Read **survives** as *the bytes are present
somewhere on the image*, and **recoverable** as *a documented method reaches them*. Read
**image-dependent** as *survives only if the clusters or pages have not yet been reallocated*
(the reuse of freed clusters, mechanism 1). This is the most common reason a
recovery succeeds on one image and fails on another.

The recovery methods are numbered as on the [Deletion Recovery](deletion_recovery.md) page,
where each is described in full: **M1** Trash Table · **M2** Checkpoint differential ·
**M3** Orphan-object scan (the opt-in `--orphans` tier) · **M4** Stream-snapshot reconstruction ·
**M5** B+-tree node-slack carve. M5 runs by **default** over live pages and, with `deleted --full`,
also over **orphan pages** (freed metadata pages), whose directory rows it recovers too. Every slack-scan remnant is classified by the **identity** its row records (see
[Deletion Recovery](deletion_recovery.md)).

| Artifact | Delete | Quick format | Upgrade v3.4→v3.14 | Clean unmount | Crash |
|----------|--------|--------------|--------------------|---------------|-------|
| **File content (extent-backed)** | Image-dependent — dereferenced clusters survive until reused; **M5** recovers the extent map from the deleted name row (embedded record) or its type-0x40 backing (split record) in slack, then reads those clusters best-effort; snapshots go with the file | Image-dependent — old data clusters become free slack; carve until reallocated | **Survives** — every file's content byte-identical across the two upgrades measured | **Survives** (live); prior versions via **M4** (snapshots) and **M5** remnants, best-effort | **Survives** if already on disk — CoW left old pages intact; writes not yet on disk at the crash can be lost |
| **`$SI` (timestamps, attributes)** | **M5** — the deleted name row's timestamps and attributes persist in node slack until a CoW rewrite; else gone from live tree | Image-dependent slack carve (**M5**) on un-rewritten directory pages | **Survives** — `$SI` carried forward; note the Win10 (116-byte) and Win11 (124-byte) layouts differ | **Survives** (live) | **Survives** (live + dereferenced) |
| **Filename (dir entry)** | **M5** — type-0x30 row name survives in slack; only the offset-array slot is removed, body not scrubbed | **M5** image-dependent | **Survives** — directory tree carried forward intact | **Survives** | **Survives** |
| **Object-Table entry** | Removed from live table; **M1** lists its row if it was queued in the Trash; **M3** lists a directory OID still in the Object Table but unreachable from the tree; an OID *gap* is a permanent trace | New Object Table written; old Object-Table pages stay on disk, unreferenced, until reused (no method decodes them) | **Survives** — OIDs preserved; mixed legacy/compact entry sizes coexist | **Survives** (live); **M2** usually yields nothing (both CHKP copies usually reference the same roots) | Live table survives; **M2** finds a difference only when a root table changed between the last two checkpoint writes |
| **USN record (`$UsnJrnl:$J`, OID 0x520)** | Journal append survives until the journal wraps; the per-file journal link is `$SI+0x40` LastUsn (virtual byte offset of the file's most recent `$J` record); `$SI+0x30` is not a USN (in a file's record it holds a cached copy of the file size; 0 in a directory's own row) | Journal reset by format; old `$J` records stay in free clusters until reused (no method recovers them) | **Not measured** — neither upgrade measured held a journal | **Survives** | Records already on disk survive; the newest can be missing (still in a cache page at the crash), so a file's LastUsn can point past the journal's last record |
| **MLog entry** | The deletion is logged as redo records, which survive until the log area is reused (`mlog` reads them); a small inline file's earlier records can also hold its bytes | Log re-initialized; control-page magic (page+0x04) is **per-volume** and changes on reformat. The earlier volume's records can stay in the data area: their format magic is not the volume's, and `mlog --earlier-logs` lists them (as it lists an earlier log of *this* volume, which carries the volume's signature with another UUID) | **Survives the upgrade** — log-instance magic is stable across a v3.4→v3.14 upgrade; no pre-images regardless | Bounded live log; redo-only, no historical undo trail | **Replayed forward** at mount; the un-replayed tail is the crash evidence |
| **Snapshot / CoW chain** | **M4** recovers the snapshots of files that still exist; deleting a snapshotted file removes its snapshots (its remnant yields metadata only) | Lost with the format; old snapshot extents stay in free clusters until reused (no method recovers them) | **Not measured** — neither upgrade measured held a snapshot | **Survives** — strongest single-image prior-content path on a clean volume (use this, not M2) | **Survives** |
| **Security descriptor (OID 0x530)** | Shared SDs (refcounted) survive while any object references them; orphaned SDs follow CoW slack rules | Old security-table pages stay on disk until reused (no method decodes them) | **Survives** — every entry keeps its SecurityId across the two upgrades measured | **Survives** | **Survives** |

## Why the upgrade column matters most

Of the five events, the in-place v3.4→v3.14 upgrade is the one analysts most often misread, because it *looks*
destructive (the version stamp changes) while in fact preserving almost everything. It is a *non-destructive metadata
migration*: it rewrites the VBR version field (0x28: 0x0304→0x030E) and its checksum (0x16), bumps the checkpoint
flags from 0x002 to 0x602, advances the version echoes, and advances the checkpoint clock (by 41 and 35 checkpoints on
the two upgrades measured). **Everything else is carried forward**: on those two upgrades (3.4 → 3.14 and 3.9 →
3.14), every file and directory present before is present after with the same name, path, object reference, sizes,
times, attributes and security id, and every file's content is byte-identical (295 and 1,183 entries, 1.8 GB of
data); the one difference is the Modified, Changed and Accessed times of `System Volume Information` on the first, which
gained new entries after the mount. Neither volume held a [USN journal](../structures/usn_journal.md) or [snapshots](../attributes/SNAPSHOT.md), so
those two are not measured across an upgrade. That is why the upgrade column of the matrix is almost solid
"Survives".

The reason this is forensically useful is that the format-time VBR fields (0x2A, 0x48) and the format bits of the
volume flags (0x2C) kept their values on the two upgrades measured, so they let you tell a genuinely native v3.14
volume from one that was upgraded into v3.14:

| Marker | Upgraded v3.4→v3.14 | Native v3.14 |
|--------|---------------------|--------------|
| VBR checksum algorithm (0x2A) | `0x0000` (immutable format field) | `0x0002` |
| VBR volume flags (0x2C) | `0x06` (not updated to `0x66`) | `0x66` |
| VBR Extended GUID (0x48) | all-zero | populated |
| CHKP native-format flag 0x080 | not set | set |
| CHKP version echo (0x50) | `0x00000000` | `0x000E0003` |

The **backup boot sector** gives a second, independent indication of the volume's original format. refs.sys
writes the backup copy at the volume's last sector, then the primary at sector 0 — except an upgrade, which writes
sector 0 only — and the driver validates each copy in isolation with a self-checksum — there is no cross-copy CRC and no
virtual clock, so the driver cannot tell which copy is newer. On every
observed real upgrade the **backup retains the original pre-upgrade minor version**, which
recovers the *exact* original version (for example a volume reading v3.14 in the primary but
v3.4 in the backup).

The same divergence exposes an upward or impossible edit of the primary's version, while the authentic value
survives in the backup. An edit to a lower version is corrected in both copies at the next mount, so matching
copies do not prove the field was never altered. The [Version Detection](version_detection.md) and
[Redundancy](redundancy.md) pages treat this signal.

Finally, the format decides a *capability*. refs.sys supports hard links exactly when the boot-sector
flags carry bit 0x20. On the corpus the bit is set on every volume formatted at 3.7 or later but one whose boot
sector `refsutil fixboot` rewrote, and clear on 3.4 volumes and on those upgraded from 3.4. So a volume upgraded from
3.4 **cannot** hold hard links, while one upgraded from 3.7 or 3.9 keeps the bit. The clear bit is the marker; an
absence of hard links is not, since a volume holds none when none was made.

## Checkpoint copies and the missing undo trail

**Checkpoint differential (M2) usually yields nothing on a clean or remountable volume.** Comparing
the two checkpoint copies in the hope that the alternate one holds an earlier tree state usually fails: the two copies
usually decode to the *same* 13-root pointer list: on the images measured, corrupted and busy ones included, and on
all but one of the volumes of the blind audit (on that ReFS 3.4 volume five roots differ).

Their bytes differ all the same — the clocks, the allocator clock, the copy's own LCN and the checksums. Do not
mistake those raw-byte differences for recoverable prior state; decode the root page references before comparing,
or you will report a difference that is not there.

M2 finds something only on a capture between two checkpoint writes that changed a root table. For prior content on a
clean volume, go to snapshots (M4, per file) and the remnants in superseded pages (M5) instead.

**There is no undo trail.** Because logging is redo-only (mechanism 2), the [MLog](../structures/mlog.md) has no
NTFS-style record of the value a change replaced. What it can still hold are the earlier records of the same file,
each with the values its own transaction wrote, such as the creating transaction's times. Prior states otherwise
come from **snapshots (M4)** and **superseded CoW/slack pages (M5)**.

## Version and state differences

Three differences change *how* a carve must be coded, not whether the artifact survives:

- **The `$SI` layout differs between Win10 (v3.4, 116 bytes) and Win11 (v3.7+, 124 bytes).** The +0x50 field is
  the low half of the reparse tag on v3.4–v3.9 and PackedEaSize from v3.10, and the Win11 form adds +0x74; the
  other offsets are the same. So a slack carve (M5) must decide the form before decoding the fields from +0x50 on.

  See the [`$SI` layout](../attributes/STANDARD_INFORMATION.md).
- **Object-Table entries are mixed-size on upgraded volumes.** Pre-upgrade objects keep the
  legacy 240/248-byte value (its payload 200/208 bytes) while post-upgrade objects use the compact 80/88-byte
  value, and both coexist in one table on an upgraded volume — a parser of the
  [Object Table](../structures/object_table.md) must handle both within a single tree.
- **USN `$Max` has two version axes.** The registered schema entry (key-type 0xF0) is
  v3.14+, while the type-0xF0 `$Max` *attribute* code path is v3.4-era and only materializes
  where the journal is active. Do not conflate the schema entry with the attribute when
  reasoning about whether `$Max` should be present.

## Tooling

- **Native-vs-upgraded determination.** `forefst.py <image> summary` reports "APPEARS UPGRADED" from the CHKP
  native-bit (0x080) plus the `$VolInfo` stamp.
- **Snapshot prior-content (M4).** `forefst.py <image> snapshots --show` (and `--extract DIR`) reconstructs
  `$SNAPSHOT` prior versions byte-for-byte from a single image.
- **Node-slack deleted-name / `$SI` carve (M5).** `forefst.py <image> deleted` (add `--full` to sweep the whole volume
  for orphan pages too; `export deleted DIR` to write out) brute-walks free-region row headers in directory pages,
  decoding name + MACB + attributes for deleted entries the live tree no longer indexes, and classifies each by
  identity (deleted vs still-present).
- **Trash Table (M1), checkpoint diff (M2), orphan-object scan (M3).** `deleted --trash` reads OID 0x0D;
  `deleted --orphans` adds the low-confidence orphan-object tier; the full procedure is on the
  [Deletion Recovery](deletion_recovery.md) page.

## Cross-references

- [Deletion Recovery](deletion_recovery.md) — defines the five recovery methods (M1–M5) and the CoW recovery
  categories referenced throughout this matrix
- [Copy-on-Write](copy_on_write.md) — the write-new/free-old update model that makes most survival possible and sets
  the reallocation race
- [Stream Snapshots ($SNAPSHOT)](../attributes/SNAPSHOT.md) — Method 4 prior-version reconstruction, the strongest
  single-image path
- [Version Detection](version_detection.md) — how to read the VBR/CHKP markers and the backup-boot-sector divergence
  that establish upgrade-vs-native
- [VBR](../structures/vbr.md) — the format-time fields 0x2A and 0x48, the run-time volume flags at 0x2C, and the
  primary/backup boot-sector pair
- [MLog](../structures/mlog.md) — the redo-only journal with no undo pass; the per-volume control-page magic
- [USN Journal](../structures/usn_journal.md) — the OID 0x520 change journal whose survival this page tracks
- [Security Descriptors](../structures/security_descriptors.md) — the OID 0x530 shared/refcounted SDs
- [Object Table](../structures/object_table.md) — where OID gaps and orphan entries become deletion evidence
- [Allocators](../structures/allocators.md) — the allocator whose reuse decisions set the survival deadline for every
  dereferenced cluster

## A hole in the image is not the same as a hole in the file

A raw image may be stored sparsely, and a sparse image cannot distinguish a file that genuinely held
zeros from a region the acquisition never captured: both read back as zeros. That ambiguity is a property
of **how the image was stored**, not of the evidence, and two byte-identical images stored differently
can disagree about which files are affected.

`forefst extract` reports it rather than hiding it: bytes that came from image holes are written, the
note names the ranges, a `.holes.json` sidecar lists them (written beside the file `-o` names), and the exit code
is 2; `--refuse-holes` writes no bytes instead. The note says what it can and cannot decide — it does not claim
the data is missing.

## Evidence

Mechanisms 1 and 2 are read in the driver and corroborated on disk; mechanism 3 is decoded on disk, with the 0x2C
writers read in the driver. CoW's no-undo guarantee — the redo-only replay forward by
`CmsRestarter` with no pre-image pass — is read in the decompiled driver. The CoW recovery categories are validated on disk. Per-cell
survival facts are raw-disk decoded across the corpus: the checkpoint copies' root lists (the volumes named above);
exact `$SNAPSHOT` prior-content reconstruction from one image (driver and disk); the node-slack deleted-name/`$SI` carve, driven
by `CmsBPlusTable::DeleteFromIndex` removing only the offset-array slot and leaving row bytes unscrubbed (driver and disk);
self-relative security-descriptor decode (driver and disk). The upgrade column rests on the upgrade-behaviour
fields-changed/fields-unchanged tables and the native-vs-upgraded marker table; the backup boot sector retaining the
original version (driver and disk); native-vs-upgraded determination from the CHKP 0x080 bit plus `$VolInfo`. The MLog
control-page per-volume magic, and its stability across upgrade (driver and disk). Version splits involve the `$SI`
layout change between 3.4 (116 bytes) and 3.7 and later (124 bytes, not backward-compatible), the legacy-vs-compact
Object-Table entry sizes, and the table schemas that change with the format (the type-0xF0 $Max attribute exists from
v3.4). That a sparse image
conflates a file's own zeros with an uncaptured region is measured too. Each is a registered finding.

The count behind the text: the checkpoint copies decode to the same root list on 25 of the 26 volumes of the first
blind audit.

See [how this was verified](../methodology.md) to trace these statements to the exact images and measurements in
`analysis/`.

<!-- findings: AP_LGFL_RA_012, AP_LGFL_005, AP_LGFL_RA_004, AP_LGFL_RA_008, CT_DRNT_RA_001, FS_CHKP_RA_014, FS_DEL_RA_005,
               FS_OTBL_RA_008, FS_SECD_RA_001, FS_VBR_RA_013, GN_IMG_RA_001, GN_SNAP_SA_001, MD_SNAP_RA_002,
               MD_SNAP_RA_003 -->
