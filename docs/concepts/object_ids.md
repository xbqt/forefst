# Object IDs — the Volume-Wide Identity

Every persistent ReFS **directory or system table** carries a 64-bit **Object ID (OID)**. The
[Object Table](../structures/object_table.md) maps that OID to the object's own B+-tree, so the OID is the
handle by which the whole filesystem refers to a directory: the parent-child edges, the change journal, and the
reference in every child's directory entry all name a directory by its OID.

**A file, by contrast, has no OID of its own.** A file lives *inside* its parent directory's B+-tree and is
named by a **FileId** — the directory's OID paired with a per-directory ordinal. The companion page,
[File IDs](file_ids.md), covers that identifier in full. This page is about the OID: what it is, why its
ordering is trustworthy evidence, and why it is the one reliable key for joining the records of one
object.

An analyst who confuses the two identifiers, or trusts the wrong one, attaches artifacts to the
wrong object.

## What an Object ID is

The Object Table (schema 0xe030) is the master OID-to-table map: a 16-byte key (a 128-bit identifier whose low
half, at offset 0x08, is the OID; the high half is 0) whose value points at the object's own B+-tree root through four
LCN slots at value+0x20.

OIDs come from a single monotonic counter (at `CmsObjectTable+0x18` on the 26100 builds), atomically incremented on
each allocation. It never hands out a value below one already in use. The Windows 11 (26100) and Insider drivers store
it in the Object Table's root at each checkpoint and reload it at mount; the Windows 10 1803 driver re-derives it at
each mount from the largest OID still in use ([OID allocation](oid_allocation.md#at-mount)).

OIDs are **64-bit, issued above every live one, and not reused after deletion** on the volumes the Windows 11 (26100)
and Insider drivers write — this no-reuse property is what makes them forensically valuable. The exception is a volume the
Windows 10 1803 driver writes: after a remount, a deleted directory whose OID was above every live one can have its OID
issued again (read in the driver, not observed), and once more at the first mount after such a volume is upgraded.

System OIDs occupy 0x00–0x6FF, with **0x700 as the boundary that is never assigned**; user OIDs begin at **0x701**:
`MsSetMinimumNewObjectId` raises the counter to 0x700 and each draw increments it and returns the new value. The
companion predicate `RefsIsSystemObjectId` returns true when `OID <= 0x6FF AND OID != 0x600`, so OID 0x600
(the root directory) is treated as a user-visible object even though it sits below the boundary. The fixed
[system OIDs](../structures/system_oids.md) and that 0x700/0x701 boundary are documented on their own page,
and the counter mechanics — including how `deleted_est` is derived from gaps — are covered in
[OID Allocation](oid_allocation.md).

## A directory is identified by its OID — and keeps it when moved

An OID names the *object*, not its place in the tree. A directory's name and its parent edge can change —
it can be renamed, or moved under a different parent — but its **OID does not change**. Reorganising the
directory tree rewrites the parent-child edges and the moved directory's own name entry; the OID that every
other structure uses to refer to that directory stays fixed. On the raw-disk corpus this is visible in the
change journal: in one journal-rich image, every directory move across parents recorded left the directory's own
identifier unchanged — only its parent reference flipped from the old directory to the new one.

So a join keyed on the OID still holds after any reorganisation of the tree, and the OID identifies a
directory across its whole history. Files behave the same way through their FileId, whose
directory half is likewise fixed at creation — see [File IDs](file_ids.md).

## The OID is the reliable join key

Because the OID is stable and unique, a full forensic identity for one object is assembled by joining four
sources on it:

- the **[Object Table](../structures/object_table.md)** — OID to the object's B+-tree root, schema
  reference, and the log position (LSN) of the object's last write at value+0x18 (offset) / value+0x1C (segment),
  a last-write order in log time that no user-facing API sets;
- the **[USN journal](../structures/usn_journal.md)** — the OID is the parent reference of the change events in
  the directory and the home half of the file reference of every file created in it, which links it to those
  events with their reason codes and timestamps;
- **directory entries** (the type 0x30 filename records) — the name(s) and parent linkage; and
- the **[Parent-Child Table](../structures/parent_child_table.md)** (root #4, schema 0xe040) — the
  authoritative directory-tree edges, keyed by OID.

Because all four are keyed on the same OID, the join is exact. A join on names is
error-prone, because names change on rename and collide across directories.

## OID chronology is strong evidence

Because a new OID is always above every live one, a **lower OID means earlier creation** — a strong chronological
indicator across the whole volume. NTFS differs: its MFT reference is 48-bit and *is* reused after deletion (on the
corpus's two NTFS volumes 225 and 132 in-use records carry a sequence number above 1, the system files among them,
whose sequence equals their record number), so MFT-number order only
partially reflects creation order; reuse obscures the chronology. ReFS OID order is not affected by reuse, which the
[NTFS vs ReFS](ntfs_comparison.md) comparison treats in full.

Two consequences follow directly:

- **Gaps in the OID sequence are evidence of past deletions — or of failed creations.** refs.sys commits the
  counter before the directory exists, so a creation that fails leaves a gap too (not measured on the corpus). On a
  freshly formatted volume the OID space is essentially fully dense; on a worked volume the density drops as
  deletions leave gaps, and each missing OID marks an identifier that was issued.
- **Orphaned OIDs are a recovery lead.** An OID still present in the Object Table but no longer reachable from the
  directory tree is a deleted directory whose entry has not yet been reclaimed: `deleted --orphans` lists these, a
  low-confidence tier ([deletion recovery, Method 3](deletion_recovery.md#method-3--orphan-object-scan-opt-in-low-confidence)).
  Whether the directory's content is still intact depends on the [copy-on-write](copy_on_write.md) discipline.

## Version and state differences

- **OID allocation is stable** across v3.4 through v3.14 / Insider: the same monotonic counter, the same
  0x700/0x701 boundary, and the same rule that no OID below a live one is issued again. The mechanical differences are where the counter
  sits and how it is guarded — the 17134 driver (v3.4) increments it under a guarded mutex in `MsAllocateObjectId`,
  while the 26100 and Insider builds use a lock-free atomic increment in `CmsObjectTable::GenerateIdentifier` — but
  the allocation semantics are identical.
- **Object Table value format changed at v3.10.** Volumes formatted before v3.10 use the legacy 240- / 248-byte
  value (its payload 200 / 208 bytes); v3.10+ volumes use the compact 80- / 88-byte value (104 / 112 bytes with
  SHA-256). **Upgraded volumes are mixed** — pre-upgrade objects keep the legacy size while post-upgrade objects
  use the compact size — so a parser must handle both sizes within one table. The byte layouts of both forms are on
  the [Object Table](../structures/object_table.md) page.

## Cross-references

- [File IDs](file_ids.md) — the companion identifier: how a *file* (which has no OID) is uniquely and
  durably identified by its FileId, and why the directory half of that FileId is an OID fixed at creation
- [OID Allocation](oid_allocation.md) — the monotonic counter, the 0x700/0x701 boundary in detail, and how
  gap density becomes a deleted-object estimate
- [System OIDs](../structures/system_oids.md) — the 0x00–0x6FF system range and the fixed table OIDs
- [Object Table](../structures/object_table.md) — the OID-to-table mapping and the compact-vs-legacy value
  formats this page depends on
- [Parent-Child Table](../structures/parent_child_table.md) — the authoritative directory-tree edges,
  keyed by OID, that complete the join
- [NTFS vs ReFS](ntfs_comparison.md) — why the no-reuse 64-bit OID is more reliable than the reused 48-bit MFT reference
  for chronology
- [Deletion Recovery](deletion_recovery.md) — using OID gaps and orphaned OIDs as recovery leads
- [Copy-on-Write](copy_on_write.md) — what decides whether an orphaned OID's content survives

## Evidence

The OID boundary and predicate are confirmed in the driver: `MsSetMinimumNewObjectId` raises the counter to 0x700
so user OIDs start at 0x701 (26100.9444), and `RefsIsSystemObjectId` returns true for
`OID <= 0x6FF AND OID != 0x600`. The monotonic allocation is decoded from `CmsObjectTable` — the counter at
`CmsObjectTable+0x18`, atomically incremented, stored in the Object Table's root and reloaded at mount on the 26100 and
Insider builds and re-derived at each mount on 17134 — and confirmed on the raw-disk corpus as OID density (~100% on fresh volumes; roughly 55–79% across the worked volumes measured)
and the NTFS-vs-ReFS chronology contrast. The four published samples' outputs hold no OID 0x700 and 40 to 2,316
occurrences of 0x701.

The 17134-mutex vs 26100/Insider lock-free allocation difference is from the decompiled driver. That a directory
keeps its OID across a move is observed on disk: in a journal-rich image, 93 recorded cross-parent directory moves
left the directory's own identifier unchanged, with only the parent reference changing. The Object Table value
sizes (legacy 240/248 B with a 200/208-byte payload, compact 80/88 B, 104/112 B with SHA-256) are disk-decoded.
The value+0x18 LSN reading rests on a controlled lab series (one directory changed per step, a control left
untouched) and on 15 volumes where the highest value equals the checkpoint's own log position.

See [how this was verified](../methodology.md) for the method.

<!-- findings: FS_OTBL_RA_010, FS_OTBL_RA_006, FS_OTBL_SA_002, FS_OTBL_SA_004, FS_OTBL_SA_005, FS_OTBL_SA_009 -->
