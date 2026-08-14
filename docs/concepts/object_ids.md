# Object IDs — the Volume-Wide Identity

Every persistent ReFS **directory or system table** carries a 64-bit **Object ID (OID)**. The
[Object Table](../structures/object_table.md) maps that OID to the object's own B+-tree, so the OID is the
handle by which the whole filesystem refers to a directory: the parent-child edges, the security table, the
change journal, and the reference in every child's directory entry all name a directory by its OID.

**A file, by contrast, has no OID of its own.** A file lives *inside* its parent directory's B+-tree and is
named by a **FileId** — the directory's OID paired with a per-directory ordinal. The companion page,
[File IDs](file_ids.md), covers that identifier in full. This page is about the OID: what it is, why its
ordering is trustworthy evidence, and why it is the one reliable key to join a fragmented object back
together.

Knowing which identifier is which — and which one is safe to trust — is the difference between
reconstructing an object's identity correctly and splicing artifacts onto the wrong object.

## What an Object ID is

The Object Table (schema 0xe030) is the master OID-to-table map: an 8-byte key (the OID at offset 0x00)
whose value points at the object's own B+-tree root through four LCN slots at value+0x20. OIDs come from a
single monotonic counter held at `CmsObjectTable+0x18`, atomically incremented on each allocation; on mount
the counter is re-derived from the largest (rightmost) key already in the Object Table, so it never hands
out a value below one already in use.

OIDs are **64-bit, monotonically increasing, and never reused after deletion** — this no-reuse property is
what makes them forensically valuable. System OIDs occupy 0x00–0x6FF, with **0x700 as the boundary that is
never assigned**; user OIDs begin at **0x701**, a constant hardcoded in `MsSetMinimumNewObjectId`. The
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
change journal: in one journal-rich image, 93 directory moves across parents were recorded, and in every
case the directory's own identifier was unchanged by the move — only its parent reference flipped from the
old directory to the new one.

This is why a join keyed on the OID survives any amount of tree reorganisation, and why the OID is the
dependable anchor for a directory's whole history. Files behave the same way through their FileId, whose
directory half is likewise frozen at creation — see [File IDs](file_ids.md).

## The OID is the reliable join key

Because the OID is stable and unique, a full forensic identity for one object is assembled by joining four
sources on it:

- the **[Object Table](../structures/object_table.md)** — OID to the object's B+-tree root, schema
  reference, and the generation / dirty-generation epochs at value+0x18 and value+0x1C that record when the
  object was created and last modified;
- the **[USN journal](../structures/usn_journal.md)** — the OID, as the directory half of the FileIds of
  events under it as *parent* directory, links to every change event with its reason code and timestamp;
- **directory entries** (the type 0x30 filename records) — the name(s) and parent linkage; and
- the **[Parent-Child Table](../structures/parent_child_table.md)** (root #4, schema 0xe040) — the
  authoritative directory-tree edges, keyed by OID.

Because all four are keyed on the same OID, the join is exact. Trying to assemble the same picture from
names — which change on rename and collide across directories — invites error.

## OID chronology is strong evidence

Because OIDs are never reused, a **lower OID means earlier creation** — a strong chronological indicator
across the whole volume. This is a sharp contrast with the NTFS MFT reference, which is 48-bit and *is*
reused after deletion, so MFT-number order only partially reflects creation order; reuse obscures the
chronology. ReFS OID order does not suffer that erosion, which the [NTFS vs ReFS](ntfs_comparison.md)
comparison treats in full.

Two consequences follow directly:

- **Gaps in the OID sequence are positive evidence of past deletions.** On a freshly formatted volume the
  OID space is essentially fully dense; on a worked volume the density drops as deletions punch holes, and
  each missing OID marks an object that once existed.
- **Orphaned OIDs survive in pages.** An OID found in a B+-tree page but absent from the current Object
  Table is a candidate deleted object whose pages have not yet been overwritten — a recovery lead. This
  connects directly to [deletion recovery](deletion_recovery.md), where the
  [copy-on-write](copy_on_write.md) discipline determines whether the orphan's content is still intact.

## Version and state differences

- **OID allocation is stable** across v3.4 through v3.14 / Insider: the same monotonic counter, the same
  0x700/0x701 boundary, and the same no-reuse rule throughout. The only mechanical difference is the lock
  used to guard the counter — Win10 v3.4 takes a guarded mutex, while Win11 v3.14 and Insider use a
  lock-free atomic increment — but the allocation semantics are identical.
- **Object Table value format changed at v3.10.** Pre-v3.10 volumes use the legacy 200-byte (system) /
  208-byte (file) value; v3.10+ volumes use the compact 80-byte / 88-byte value. **Upgraded volumes are
  mixed** — pre-upgrade objects keep the legacy size while post-upgrade objects use the compact size — so a
  parser must handle both sizes within one table. The byte layouts of both forms are on the
  [Object Table](../structures/object_table.md) page.

## Cross-references

- [File IDs](file_ids.md) — the companion identifier: how a *file* (which has no OID) is uniquely and
  durably identified by its FileId, and why the directory half of that FileId is an OID frozen at creation
- [OID Allocation](oid_allocation.md) — the monotonic counter, the 0x700/0x701 boundary in detail, and how
  gap density becomes a deleted-object estimate
- [System OIDs](../structures/system_oids.md) — the 0x00–0x6FF system range and the fixed table OIDs
- [Object Table](../structures/object_table.md) — the OID-to-table mapping and the compact-vs-legacy value
  formats this page depends on
- [Parent-Child Table](../structures/parent_child_table.md) — the authoritative directory-tree edges,
  keyed by OID, that complete the join
- [NTFS vs ReFS](ntfs_comparison.md) — why the no-reuse 64-bit OID beats the reused 48-bit MFT reference
  for chronology
- [Deletion Recovery](deletion_recovery.md) — using OID gaps and orphaned OIDs as recovery leads
- [Copy-on-Write](copy_on_write.md) — what decides whether an orphaned OID's content survives

## Evidence

The OID boundary and predicate are confirmed in the driver (E2): `MsSetMinimumNewObjectId` hardcodes 0x700
as the boundary so user OIDs start at 0x701 (findings FS_OTBL_RA_006, FS_OTBL_SA_004, FS_OTBL_SA_009), and
`RefsIsSystemObjectId` returns true for `OID <= 0x6FF AND OID != 0x600` (finding FS_OTBL_SA_005). The
monotonic, never-reused allocation is decoded from `CmsObjectTable` — the counter at `CmsObjectTable+0x18`,
atomically incremented, re-derived on mount from the rightmost Object Table key — and confirmed on the
raw-disk corpus (RD) as OID density (~100% on fresh volumes; roughly 55–79% across the worked volumes
measured) and the NTFS-vs-ReFS chronology contrast. The Win10-mutex vs Win11/Insider lock-free allocation
difference is from the decompiled driver (E2). That a directory keeps its OID across a move is confirmed on
disk (RD): in a journal-rich image, 93 recorded cross-parent directory moves left the directory's own
identifier unchanged, with only the parent reference changing. The Object Table value-format split (legacy
200/208 B vs compact 80/88 B) is disk-decoded (RD).
