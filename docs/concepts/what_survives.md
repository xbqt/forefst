# What Survives: Artifact-vs-Event Survival Matrix

On a ReFS volume the analyst's first question is rarely *how is this structure laid
out* — it is *given what happened to this disk, which artifacts can I still recover, and
by what method?* This page answers that directly. It cross-tabulates eight forensic
artifacts against five events — file deletion, quick format, an in-place v3.4→v3.14
upgrade, a clean unmount, and a crash — and states, per cell, whether the artifact
survives and which recovery method reaches it. The unifying insight is that survival in
ReFS is governed almost entirely by its [copy-on-write](copy_on_write.md) update model:
old content is never overwritten in place, so the limiting factor is usually *cluster
reallocation*, not the triggering event itself.

## The three mechanisms behind every cell

Every cell in the matrix below reduces to three properties of the file system. Understanding
these three is enough to predict survival for an artifact this page does not list.

**1. Copy-on-write writes new and frees old.** When an object is modified or deleted, its
prior pages are *dereferenced*, not scrubbed — the bytes stay on disk until the
[allocator](../structures/allocators.md) hands those clusters to a later write. This is why
"survives" and "recoverable" are different questions throughout this page: the bytes are
present, but reaching them depends on whether the clusters were reused. The strongest case
is a cluster whose reference count is ≥ 2 (CoW-protected): both checkpoints still point at
it, so it survives *guaranteed* until the older checkpoint is released. The detailed
mechanism is on the [Copy-on-Write](copy_on_write.md) page, and the recovery categories that
follow from it are in [Deletion Recovery](deletion_recovery.md).

**2. Logging is redo-only — there is no undo pass.** The [MLog](../structures/mlog.md) is a
redo-only journal with no pre-images. Crash recovery (`CmsRestarter`) replays redo records
*forward* onto pages that CoW already left intact, so ReFS never performs the undo pass that
an NTFS `$LogFile` runs. Two forensic consequences follow. First, a crash does not generate
the rich "previous value" trail that an NTFS undo record does — do not go looking for one.
Second, because the torn last transaction is recovered by replaying forward rather than
rolling back, a crash actually leaves *more* dereferenced-but-unreused pages on disk than a
clean unmount does. Prior state therefore comes from [snapshots](../attributes/SNAPSHOT.md)
and superseded CoW pages, never from log undo.

**3. Certain VBR fields are format-time immutables.** A handful of
[Volume Boot Record](../structures/vbr.md) fields are written once at format and *never*
rewritten — not on upgrade, not on remount. Because they freeze the volume's birth state,
they are the most durable provenance markers ReFS offers, and they drive the entire
[upgrade-vs-native](version_detection.md) determination discussed below.

What each event does to the on-disk image, in one line apiece:

```
event ──► what it does to the on-disk image
─────────────────────────────────────────────────────────────────
delete         reparent to Trash Table (OID 0x0D), dereference pages,
               remove the live B+-tree offset-array slot (row body NOT scrubbed)
quick format   write a fresh metadata skeleton; old clusters left as slack
upgrade        rewrite VBR version (0x28) + checksum (0x16), bump CHKP flags
               (0x002→0x602), bump virtual clock (+41 txns); leave 0x2A/0x2C/0x48
clean unmount  both CHKP copies point to the same 13 root pointers; vclock settled
crash          last transaction may be torn; redo log replayed forward, no undo
```

## The survival matrix

The matrix is the operational core of this page. Read **survives** as *the bytes are present
somewhere on the image*, and **recoverable** as *a documented method reaches them*. Read
**image-dependent** as *survives only if the clusters or pages have not yet been reallocated*
— this is the CoW-vs-reuse race from mechanism 1, and it is the single most common reason a
recovery succeeds on one image and fails on another.

The recovery methods are numbered as on the [Deletion Recovery](deletion_recovery.md) page,
where each is described in full: **M1** Trash Table · **M2** Checkpoint differential ·
**M3** Orphan MSB+ page scan · **M4** Stream-snapshot reconstruction · **M5** B+-tree
node-slack carve.

| Artifact | Delete | Quick format | Upgrade v3.4→v3.14 | Clean unmount | Crash |
|----------|--------|--------------|--------------------|---------------|-------|
| **File content (non-resident)** | Image-dependent — dereferenced clusters survive until reused; **M4** if snapshotted (exact bytes, deterministic); else **M3** of orphan extents | Image-dependent — old data clusters become free slack; carve until reallocated | **Survives** — upgrade does not touch file data; both live and prior-version content intact | **Survives** (live); prior versions only via **M4** / CoW-protected clusters | **Survives** — CoW left old pages intact; no undo needed |
| **`$SI` (resident metadata)** | **M5** — inline `$SI` (MACB, attrs) persists in node slack until CoW rewrite; else gone from live tree | Image-dependent slack carve (**M5**) on un-rewritten directory pages | **Survives** — `$SI` carried forward; note layout changes non-backward-compatibly at v3.14 | **Survives** (live) | **Survives** (live + dereferenced) |
| **Filename (dir entry)** | **M5** — type-0x30 row name survives in slack; only the offset-array slot is removed, body not scrubbed | **M5** image-dependent | **Survives** — directory tree carried forward intact | **Survives** | **Survives** |
| **Object-Table entry** | Removed from live table; **M1** if still in Trash Table; **M3** orphan OID in un-reused MSB+ page; the OID *gap* is permanent evidence | New Object Table written; old OT pages are orphan slack (**M3**) until reused | **Survives** — OIDs preserved; mixed legacy/compact entry sizes coexist | **Survives** (live); **M2** yields nothing (both CHKP = same roots) | Live table survives; **M2** *could* fire only on a true mid-txn crash capture |
| **USN record (`$UsnJrnl:$J`, OID 0x520)** | Journal append survives until the journal wraps; the per-file journal link is `$SI+0x40` LastUsn (virtual byte offset of the file's most recent `$J` record); `$SI+0x30` is an unpopulated slot | Journal reset by format; old `$J` data = orphan slack (**M3**) until reused | **Survives** — journal carried forward; `$Max` (type-0xF0 attr) preserved | **Survives** | **Survives** — redo replay does not truncate the journal |
| **MLog entry** | n/a (delete is journaled as a redo record, then superseded) | Log re-initialized; control-page magic (page+0x04) is **per-volume** and changes on reformat | **Survives the upgrade** — log-instance magic is stable across a v3.4→v3.14 upgrade; no pre-images regardless | Bounded live log; redo-only, no historical undo trail | **Replayed forward** at mount; the un-replayed tail is the crash evidence |
| **Snapshot / CoW chain** | **M4** — `$SNAPSHOT` prior versions reconstruct exactly from one image; independent of deletion | Lost if the host file is reformatted away; surviving extents only via **M3** | **Survives** — snapshots work on upgraded volumes | **Survives** — strongest single-image prior-content path on a clean volume (use this, not M2) | **Survives** |
| **Security descriptor (OID 0x530)** | Shared SDs (refcounted) survive while any object references them; orphaned SDs follow CoW slack rules | Old `$Secure` pages = orphan slack (**M3**) until reused | **Survives** — SD table carried forward; self-relative SDs decode unchanged | **Survives** | **Survives** |

## Why the upgrade column matters most

Of the five events, the in-place v3.4→v3.14 upgrade is the one analysts most often misread,
because it *looks* destructive (the version stamp changes) while in fact preserving almost
everything. It is a *non-destructive metadata migration*: it rewrites the VBR version field
(0x28: 0x0304→0x030E) and its checksum (0x16), bumps the checkpoint flags from 0x002 to
0x602, advances the version echoes, and adds roughly 41 transactions to the virtual clock.
**Everything else is carried forward** — file data, `$SI`, names, OIDs, the
[USN journal](../structures/usn_journal.md), [snapshots](../attributes/SNAPSHOT.md), and
[security descriptors](../structures/security_descriptors.md) all survive intact. That is why
the upgrade column of the matrix is almost solid "Survives".

The reason this is forensically useful is that three VBR fields are *never* rewritten on
upgrade, so they remain frozen at their original native/upgraded value and let you tell a
genuinely native v3.14 volume from one that was upgraded into v3.14:

| Marker | Upgraded v3.4→v3.14 | Native v3.14 |
|--------|---------------------|--------------|
| VBR checksum algorithm (0x2A) | `0x0000` (immutable format field) | `0x0002` |
| VBR volume flags (0x2C) | `0x06` (not updated to `0x66`) | `0x66` |
| VBR Extended GUID (0x48) | all-zero | populated |
| CHKP native-format flag 0x080 | not set | set |
| CHKP version echo (0x50) | `0x00000000` | `0x000E0003` |

A second, fully independent provenance signal comes from the **backup boot sector**. ReFS
dual-writes the primary VBR (sector 0) and a backup copy at the last LBA, and the driver
validates each copy in isolation with a self-checksum — there is no cross-copy CRC and no
virtual clock, so the two copies' relative currency is undecidable to the driver. On every
observed real upgrade the **backup retains the original pre-upgrade minor version**, which
recovers the *exact* original version (for example a volume reading v3.14 in the primary but
v3.4 in the backup). The same divergence also exposes VBR tampering: a hand-edited primary
carries the altered version while the authentic value survives in the backup. The
[Version Detection](version_detection.md) page treats this signal in depth.

Finally, the upgrade leaves a *capability* fingerprint. POSIX unlink/rename and hard links
require the native-format flag (CHKP 0x080) and are therefore **unavailable** on upgraded
volumes — their absence on an otherwise v3.14 volume is itself a marker that the volume was
upgraded rather than freshly formatted.

## Two traps

**Checkpoint differential (M2) yields nothing on a clean or remountable volume.** It is
tempting to diff the two checkpoint copies hoping the alternate one holds an earlier tree
state — but both CHKP copies always decode to the *same* 13-root pointer list, confirmed
across the whole corpus including corrupted and busy images. Only the virtual clock and the
per-page checksums differ between them. Do not mistake those raw-byte differences for
recoverable prior state; decode the root page references before comparing, or you will report
a phantom delta. M2 only does real work on a genuine mid-transaction crash capture, which the
corpus does not contain. For prior whole-tree content on a clean volume, go to snapshots (M4)
and superseded pages (M3/M5) instead.

**There is no undo trail.** Because logging is redo-only (mechanism 2), do not expect an
NTFS-style "previous value" record from the [MLog](../structures/mlog.md). This is a frequent
analyst reflex carried over from NTFS and it produces nothing here. Prior states come from
**snapshots (M4)** and **superseded CoW/slack pages (M3/M5)** — never from log undo.

## Version and state differences

Three differences change *how* a carve must be coded, not whether the artifact survives:

- **`$SI` resident layout changes non-backward-compatibly at v3.14.** A carved `$SI` from an
  upgraded-but-legacy object and one from a native v3.14 object are parsed differently — the
  fields above offset 0x50 shift — so a slack carve (M5) must branch on version before
  decoding. See the [version-specific `$SI` layout](version_detection.md).
- **Object-Table entries are mixed-size on upgraded volumes.** Pre-upgrade objects keep the
  legacy 200/208-byte entry size while post-upgrade objects use the compact 80/88-byte size,
  and both coexist in one table on an upgraded volume — a parser of the
  [Object Table](../structures/object_table.md) must handle both within a single tree.
- **USN `$Max` has two version axes.** The registered schema entry (key-type 0xF0) is
  v3.14+, while the type-0xF0 `$Max` *attribute* code path is v3.4-era and only materializes
  where the journal is active. Do not conflate the schema entry with the attribute when
  reasoning about whether `$Max` should be present.

## Tooling

- **Native-vs-upgraded determination.** `forefst.py <image> summary` reports
  "APPEARS UPGRADED" from the CHKP native-bit (0x080) plus the `$VolInfo` stamp.
- **Snapshot prior-content (M4).** `forefst.py <image> snapshots --show` (and
  `--extract DIR`) reconstructs `$SNAPSHOT` prior versions byte-for-byte from a single image.
- **Node-slack deleted-name / `$SI` carve (M5).** `forefst.py <image> deleted --slack`
  (and `--extract DIR`) brute-walks free-region row headers in directory pages, decoding
  name + MACB + attributes for deleted entries the live tree no longer indexes.
- **Trash Table (M1) and orphan scan (M3).** Read OID 0x0D from the
  [Object Table](../structures/object_table.md); the full procedure is on the
  [Deletion Recovery](deletion_recovery.md) page.

## Cross-references

- [Deletion Recovery](deletion_recovery.md) — defines the five recovery methods (M1–M5) and the CoW recovery categories referenced throughout this matrix
- [Copy-on-Write](copy_on_write.md) — the write-new/free-old update model that makes most survival possible and sets the reallocation race
- [Stream Snapshots ($SNAPSHOT)](../attributes/SNAPSHOT.md) — Method 4 prior-version reconstruction, the strongest single-image path
- [Version Detection](version_detection.md) — how to read the VBR/CHKP markers and the backup-boot-sector divergence that establish upgrade-vs-native
- [VBR](../structures/vbr.md) — the format-time immutable fields (0x2A/0x2C/0x48) and the primary/backup boot-sector pair
- [MLog](../structures/mlog.md) — the redo-only journal with no undo pass; the per-volume control-page magic
- [USN Journal](../structures/usn_journal.md) — the OID 0x520 change journal whose survival this page tracks
- [Security Descriptors](../structures/security_descriptors.md) — the OID 0x530 shared/refcounted SDs
- [Object Table](../structures/object_table.md) — where OID gaps and orphan entries become deletion evidence
- [Allocators](../structures/allocators.md) — the allocator whose reuse decisions set the survival deadline for every dereferenced cluster

## Evidence

The three governing mechanisms are static-analysis confirmed (E2) and raw-disk corroborated
(RD). CoW's no-undo guarantee — the redo-only replay forward by `CmsRestarter` with no
pre-image pass — is finding AP_LGFL_005 (E2). The CoW recovery categories and the refcount-≥2
guaranteed-survival case are RD-validated. Per-cell survival facts are raw-disk decoded
across the corpus: the checkpoint-differential limitation (both CHKP copies decode to the
identical 13-root pointer list on clean, corrupted, and busy images) is finding FS_CHKP_RA_014; exact
`$SNAPSHOT` prior-content reconstruction from one image is finding MD_SNAP_RA_002, MD_SNAP_RA_003, CT_DRNT_RA_001, GN_SNAP_SA_001 (E2+RD); the
node-slack deleted-name/`$SI` carve, driven by `CmsBPlusTable::DeleteFromIndex` removing only
the offset-array slot and leaving row bytes unscrubbed, is finding FS_DEL_RA_005 (E2+RD);
self-relative security-descriptor decode is finding FS_SECD_RA_001 (E2+RD). The upgrade column rests on
the upgrade-behaviour fields-changed/fields-unchanged tables and the native-vs-upgraded marker
table; the backup-boot-sector retaining the original version is finding
FS_VBR_RA_013 (E2+RD); native-vs-upgraded tooling determination from the CHKP 0x080 bit plus `$VolInfo`
is finding FS_OTBL_RA_008. The MLog control-page per-volume magic, and its stability across upgrade, are
findings AP_LGFL_RA_008 and AP_LGFL_RA_004 (E2+RD). Version splits involve the $SI non-backward-compatible change at
v3.14, the legacy-vs-compact Object-Table entry sizes, and the attribute schema gating — with the
type-0xF0 $Max attribute being v3.4-era and the schema
entry 0x1F0 being v3.14+. See [how this was verified](../methodology.md) to trace these to the
exact images and measurements in `analysis/`.
