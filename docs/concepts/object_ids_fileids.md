# Object IDs and FileIds — the Cross-Table Join Key

Every persistent ReFS object — file, directory, or system table — carries a 64-bit **Object ID
(OID)** that the [Object Table](../structures/object_table.md) maps to that object's own B+-tree.
A separate, much weaker identifier — the per-directory **child ordinal** (`NextFileId`, surfaced as
the lower half of the 128-bit FileId in USN journal records) — names a child *within one directory*
and is **reused per directory**. Knowing which identifier is which, and which one is safe to trust,
is the difference between correctly reconstructing an object's identity and splicing artifacts onto
the wrong file. The OID is the reliable join key; the ordinal is a trap if used alone.

## Two identity spaces

ReFS keeps two distinct identity spaces, and the analyst must not confuse them.

**Object ID (OID) — the volume-wide identity.** The Object Table (schema 0xe030) is the master
OID-to-table map: an 8-byte key (the OID at offset 0x00) whose value points at the object's own
B+-tree root through four LCN slots at value+0x20. OIDs come from a single monotonic counter held at
`CmsObjectTable+0x18`, atomically incremented on each allocation; on mount the counter is re-derived
from the largest (rightmost) key already in the Object Table, so it never hands out a value below
one already in use. OIDs are **64-bit, monotonically increasing, and never reused after deletion** —
this no-reuse property is what makes them forensically valuable. System OIDs occupy 0x00–0x6FF, with
**0x700 as the boundary that is never assigned**; user OIDs begin at **0x701**, a constant hardcoded
in `MsSetMinimumNewObjectId`. The companion predicate `RefsIsSystemObjectId` returns true when
`OID <= 0x6FF AND OID != 0x600`, so OID 0x600 (the root directory) is treated as a user-visible
object even though it sits below the boundary. The fixed [system OIDs](../structures/system_oids.md)
and that 0x700/0x701 boundary are documented in detail on their own page.

**Child ordinal / NextFileId — the per-directory index.** This is a separate counter, *not* the OID.
Each directory owns a `NextFileId` (held in the directory's
[$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) at $SI+0x58). On child creation the
driver increments the *parent* directory's `NextFileId` and stamps the new child with the assigned
ordinal — this happens in `RefsMoveFile`, the unified create/rename/link path, which reads and bumps
the counter in the parent directory's in-memory SCB (at SCB+0x1b8 on Win11 v3.14, SCB+0x1a8 on
Insider) before persisting it. The ordinal is a
small, near-contiguous integer starting from 2 (0 and 1 are reserved), and it is **local to one
directory**. Two children of two different directories routinely carry the same ordinal value, so an
ordinal on its own says nothing about which file it belongs to.

**Where they meet — the 128-bit USN FileId.** [USN journal](../structures/usn_journal.md) V3 records
carry a 16-byte FileId at record offset 0x08 whose two halves combine both identity spaces:

```
 USN V3 FileId (16 bytes, record offset 0x08)
 +---------------------------+---------------------------+
 |  upper 8 bytes = OID      |  lower 8 bytes = child     |
 |  (the directory's Object  |  ordinal within that       |
 |  Table OID)               |  directory (NextFileId)    |
 +---------------------------+---------------------------+
        volume-wide                  per-directory
```

The upper half is the *directory's* OID, which is volume-unique; the lower half is the child ordinal,
which is directory-local. The FileId therefore identifies a child *relative to its home directory* —
it is globally unique only because the directory OID qualifies it. The lower half alone is never a
volume-wide file identity.

## Reconstructing one identity by joining on the OID

The OID is the reliable join key, so a full forensic identity for one object is assembled by joining
four sources on it:

- the **[Object Table](../structures/object_table.md)** — OID to the object's B+-tree root, schema
  reference, and the generation / dirty-generation epochs at value+0x18 and value+0x1C that record
  when the object was created and last modified;
- the **[USN journal](../structures/usn_journal.md)** — the OID, as the upper half of the FileIds of
  events under it as *parent* directory, links to every change event with its reason code and
  timestamp;
- **directory entries** (the type 0x30 filename records) — the name(s) and parent linkage; and
- the **[Parent-Child Table](../structures/parent_child_table.md)** (root #4, schema 0xe040) — the
  authoritative directory-tree edges, keyed by OID.

Because all four are keyed on the same OID, the join is exact. Trying to assemble the same picture
from names or ordinals invites the collision described below.

## OID chronology is strong evidence

Because OIDs are never reused, a **lower OID means earlier creation** — a strong chronological
indicator across the whole volume. This is a sharp contrast with the NTFS MFT reference, which is
48-bit and *is* reused after deletion, so MFT-number order only partially reflects creation order;
reuse obscures the chronology. ReFS OID order does not suffer that erosion, which the
[NTFS vs ReFS](ntfs_comparison.md) comparison treats in full.

Two consequences follow directly:

- **Gaps in the OID sequence are positive evidence of past deletions.** On a freshly formatted volume
  the OID space is essentially fully dense; on a worked volume the density drops as deletions punch
  holes, and each missing OID marks an object that once existed.
- **Orphaned OIDs survive in pages.** An OID found in a B+-tree page but absent from the current
  Object Table is a candidate deleted object whose pages have not yet been overwritten — a recovery
  lead. This connects directly to [deletion recovery](deletion_recovery.md), where the
  [copy-on-write](copy_on_write.md) discipline determines whether the orphan's content is still
  intact.

## The ordinal-reuse trap

The per-directory child ordinal **collides across directories**: the same ordinal value appears under
different parents. Treating the ordinal as if it were a volume-wide FileId — or matching artifacts on
the ordinal alone — will splice events from unrelated files together. The rule is simple: always
qualify the ordinal with its directory OID, i.e. use the *full* 128-bit FileId, never just its lower
half.

This same collision is why **hard-link identity cannot be decided on `(home backref + ordinal)`
alone**. Those two fields collide across sibling directories under a shared home, so the analyst must
resolve each name to the type-0x40 stream record whose 0x40 size **matches that name's own size**
(read from the name entry's value+0x38), then group names on that stream's `(owner, file_id)` pair.
The size match is what rejects a colliding same-ordinal stream that actually belongs to a different
file — a metadata tuple or a merely content-bearing record over-merges in exactly this case. The
[hard links](hard_links.md) page works through the mechanism and its failure modes.

Finally, **do not read the ordinal as a version or write counter.** `NextFileId` is a child-creation
ordinal, and its persistence is version-gated (see below). A *zero* value in a directory's own row on
a native v3.14 volume is therefore normal, and is **not** evidence of tampering.

## Version and state differences

- **OID allocation is stable** across v3.4 through v3.14 / Insider: the same monotonic counter, the
  same 0x700/0x701 boundary, and the same no-reuse rule throughout. The only mechanical difference is
  the lock used to guard the counter — Win10 v3.4 takes a guarded mutex, while Win11 v3.14 and Insider
  use a lock-free atomic increment — but the allocation semantics are identical.
- **Object Table value format changed at v3.10.** Pre-v3.10 volumes use the legacy 200-byte (system)
  / 208-byte (file) value; v3.10+ volumes use the compact 80-byte / 88-byte value. **Upgraded volumes
  are mixed** — pre-upgrade objects keep the legacy size while post-upgrade objects use the compact
  size — so a parser must handle both sizes within one table. The byte layouts of both forms are on
  the [Object Table](../structures/object_table.md) page.
- **NextFileId persistence is version-gated.** The directory own-row and the non-resident file own-row
  carry the ordinal on v3.4 through v3.10 but are **0 on native v3.14/v3.15**: a persist gate (the
  volume version `< 0x30b` test) stops writing the ordinal to the own-row, and on v3.11+ the value
  lives in the object-record payload instead. A resident file's inline $SI always carries its ordinal,
  on every version. An upgraded v3.4-to-v3.14 volume retains the old own-row values.

## Tooling

`forefst.py` surfaces the Object Table and OID chronology. Its hard-link grouping (`hard_link_count`,
and the equivalent `refsanalysis summary` enrichment) resolves each name to the type-0x40 stream
whose 0x40 size **matches the name's own size** (value+0x38) — choosing between the local
`(parent, file_id)` and home `(home, file_id)` candidate — rather than trusting a metadata tuple or
a merely content-bearing record, both of which over-merge files that collide on the per-directory
ordinal.

## Cross-references

- [Object Table](../structures/object_table.md) — OID-to-table mapping, the key/value layout, and
  the compact-vs-legacy value formats this page depends on
- [System OIDs](../structures/system_oids.md) — the 0x00–0x6FF system range, the 0x700 boundary,
  the 0x701 first user OID, and the OID allocation properties
- [USN Journal](../structures/usn_journal.md) — V3 records and the 128-bit FileId whose upper half is
  the directory OID and lower half the child ordinal
- [Parent-Child Table](../structures/parent_child_table.md) — the authoritative directory-tree edges,
  keyed by OID, that complete the join
- [Hard Links](hard_links.md) — why a name must resolve to the size-matched type-0x40 stream
  `(owner, file_id)`, not a metadata fingerprint or a colliding content-bearing record
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the `$SI+0x58` NextFileId field and
  its version-gated persistence
- [NTFS vs ReFS](ntfs_comparison.md) — why the no-reuse OID beats the reused MFT reference for
  chronology
- [Deletion Recovery](deletion_recovery.md) — using OID gaps and orphaned OIDs as recovery leads
- [Copy-on-Write](copy_on_write.md) — what decides whether an orphaned OID's content survives

## Evidence

The OID boundary and predicate are confirmed in the driver (E2): `MsSetMinimumNewObjectId` hardcodes
0x700 as the boundary so user OIDs start at 0x701 (finding FS_OTBL_RA_006, FS_OTBL_SA_004, FS_OTBL_SA_009), and `RefsIsSystemObjectId`
returns true for `OID <= 0x6FF AND OID != 0x600` (finding FS_OTBL_SA_005). The monotonic, never-reused
allocation is decoded from `CmsObjectTable` — the counter at `CmsObjectTable+0x18`, atomically
incremented, re-derived on mount from the rightmost Object Table key — and confirmed on the raw-disk
corpus (RD) as OID density (~100% on fresh volumes; roughly 55–79% across the worked volumes measured) and the NTFS-vs-ReFS
chronology contrast. The Win10-mutex vs
Win11/Insider lock-free allocation difference is from the decompiled driver (E2).

The child-ordinal mechanism is confirmed in the driver (E2): `RefsMoveFile` increments the parent
directory's `NextFileId` and stamps the new child's ordinal (finding MD_SI_RA_008; the field lives at $SI+0x58,
finding MD_SI_RA_010, MD_SI_RA_008). The `version < 0x30b` persist gate that zeroes the own-row on native v3.14 is
decompiled (E2) and disk-confirmed (finding MD_SI_RA_010, MD_SI_RA_008). The 128-bit USN FileId split (upper = table
OID, lower = directory-local ordinal) is from the USN record layout (RD). The
hard-link size-match resolution is grounded in the driver and re-measured across the corpus
(finding FN_LINK_002). The Object Table value-format split (legacy 200/208 B vs
compact 80/88 B) is disk-decoded (RD).
