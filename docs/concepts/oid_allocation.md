# OID Allocation — Monotonic Counter and Deletion Estimation

Every persistent ReFS **directory and system object** draws its 64-bit Object ID (OID) from a single per-volume
counter: the 26100 and Insider drivers keep it on the volume, the Windows 10 1803 driver re-derives it at
each mount ([At mount](#at-mount)). **Files are not allocated an OID** — a new file instead takes the next
per-directory child ordinal (NextFileId) from its parent directory.

The driver hardcodes a boundary at **0x700**, hands out **0x701** as the first user OID, and on deletion frees the
object's B+-tree row but **never rewinds the counter**.

This matters forensically in two ways:

- OIDs are monotonic and are not issued twice (the exceptions: volumes the Windows 10 1803 driver writes,
  and once a volume upgraded from 3.4: [at mount](#at-mount)), and the *gaps* they leave behind let an analyst estimate how many
  directories were created and later deleted (file deletions leave no OID gap) — something NTFS record numbers do
  not allow, because NTFS recycles them;
- an OID is also a reliable creation-order index, so the same property that exposes deletions also orders the
  surviving directories in time.

## How allocation works

A volume-wide counter lives in the Object Table's in-memory control structure at `CmsObjectTable+0x18`.
Every new OID on the volume comes from that counter, not from anything stored per
object. Three distinct driver paths touch it: initialization, allocation, and deletion. The on-disk side
of what they manage is the [Object Table](../structures/object_table.md), whose 16-byte key holds the OID (its low
half).

**Initialization — `MsSetMinimumNewObjectId` (the 0x700 boundary).** At mount (`RefsMountVolume` calls it on
26100.9444) the driver clamps the counter so it can never sit below `0x700`. The constant is hardcoded; the routine
compares the 128-bit counter (`+0x10` high half, `+0x18` low half) with 0x700 and, only when the counter is below it,
sets it to 0x700 and marks the structure dirty:

```c
// MsSetMinimumNewObjectId (refs.sys 26100.9444, excerpt)
uStack_40 = 0x700; // minimum value
...                                        // only when the counter is below 0x700:
*(undefined8 *)(lVar1 + 0x10) = 0;         // high half of the 128-bit counter
*(undefined8 *)(lVar1 + 0x18) = 0x700;     // low half: counter = 0x700
*(undefined1 *)(lVar1 + 0x20) = 1;         // mark dirty
```

`0x700` is a *boundary*, never an assigned OID. Everything below it is reserved: OIDs `0x00–0x6FF` name
system objects, and the predicate `RefsIsSystemObjectId` returns true exactly when `OID <= 0x6FF AND
OID != 0x600` — so the root directory at 0x600 is the one sub-0x700 object treated as user-visible. The
fixed assignments in that reserved range (Upcase, Logfile Info, Trash Table, Volume Info, Security
Descriptors, Reparse Index, FS Metadata, root) are catalogued on the
[system OIDs](../structures/system_oids.md) page.

**Allocation — `CmsObjectTable::GenerateIdentifier` (pre-increment).** Each new object reads the
counter, atomically increments it under an `x86 LOCK` prefix, and returns `old_value + 1`:

```c
// CmsObjectTable::GenerateIdentifier
LOCK();
lVar2 = *(longlong *)(this + 0x18); // read counter
*(longlong *)(this + 0x18) = lVar2 + 1; // atomic increment
UNLOCK();
*(longlong *)(param_2 + 8) = lVar2 + 1; // returned OID = old + 1
```

Because the counter is seeded at `0x700`, the first object generated receives **0x701**. After each draw the
counter holds the OID it just issued (0x700 before the first draw) — a useful invariant when reasoning about the
high-water mark.

**Deletion — `CmsObjectTable::DeleteIdentifier` (no rewind).** Deletion calls `CmsTable::DeleteRow` to
remove the object's row from the B+-tree and *does not touch the counter*:

```c
// CmsObjectTable::DeleteIdentifier
lVar3 = CmsTable::DeleteRow(*(CmsTable **)(this + 0x28), ...);
// counter at this+0x18 is never decremented — OID retired forever
```

The removed row is gone from the live tree, and the Windows 11 (26100) and Insider drivers do not issue its OID
again: they keep the counter across mounts. The Windows 10 1803 driver keeps it only within a mount; after a remount
it resumes above the highest OID still in use, so an OID deleted above that one can be issued again (see
[at mount](#at-mount)). This is the mechanical reason deletions leave
permanent gaps (a creation that fails after drawing its OID leaves one too: the counter is committed before the
directory exists).

```text
 counter @ CmsObjectTable+0x18
 seed 0x700 ─► 0x701 ─► 0x702 ─► 0x703 ─► 0x704 ─► ...
 issued: f1 f2(del) f3 f4(del)
 live rows: 0x701 ........... 0x703 ........... ← 0x702, 0x704 are GAPS
 = past deletions (or failed creations)
```

See [deletion and recovery](deletion_recovery.md) for what else survives a delete — OID-gap analysis is the
one deletion signal that needs *no* surviving record at all.

### At mount

**The Windows 11 (26100) and Insider drivers store the counter.** `GenerateIdentifier` marks the Object Table dirty
each time it draws an OID, and the next checkpoint writes the counter into the table's root
(`CmsVolume::PersistCheckpointCaches`). At mount `CmsObjectTable::InitializeTable` reloads it (when the root data holds
one) and raises it to the table's largest key if that is higher, unless a volume state bit is set (bit 0x2 of the
volume's +0xD34 on 26100.9444). The counter therefore survives a remount even when the directories holding the
highest OIDs were deleted, and an OID is never issued twice. After a crash, the replay of the log raises the counter
above every directory it re-creates (read on 26100.9444). One exception: a volume upgraded from ReFS 3.4 holds no stored counter until its
first mount by one of these drivers, which starts from the largest OID in use, so the OIDs of directories deleted above it
while the volume was 3.4 can be issued once more (derived from the two readings, not measured). From then on the counter is stored.

**The Windows 10 1803 driver (17134) does not.** It writes no counter to the table's root data. At each mount its counter
restarts from the table's largest key (`FindLastInIndex`), then the 0x700 floor. So after a remount, a deleted
directory whose OID was above every live one can have its OID issued again (the first one above the largest live
OID to the next new directory). This is read in the
driver and has not been observed: no ReFS 3.4 volume of the corpus has a change journal that could show it. The 3.7
and 3.9 volumes of the corpus hold no stored counter either; those drivers were not read.

**Reading the stored counter.** On a volume of 3.10 or later, the Object Table's root page holds the counter after its
40-byte descriptor: at page +0x78, a u64 `1`, then the counter's high half (`0`) and its low half, the last OID issued
as of the last checkpoint. Both copies of the table hold the same value. When it is above the largest OID in the table,
OIDs were drawn after the largest live one for directories that are gone (deleted, or a failed creation). On the corpus, wherever a change journal covered
that range, every OID in it was a directory the journal shows created and then deleted.

## Forensic implications

**OID gaps are evidence of a directory deletion or a failed creation.** If live objects exist at OID 0x710 and
0x712 but none at 0x711, the counter issued 0x711 and no live object holds it: an object was created there and later deleted, or
its creation failed after the identifier was drawn — refs.sys commits the counter in its own action, before the
directory exists (the failed-creation case is not measured on the corpus). A slot below the largest live OID is never
refilled, by any driver read.

**Estimate the deleted-object count from OID density.** Define

```text
present_OIDs = number of live Object Table rows with OID >= 0x701
density = present_OIDs / (max_OID - min_OID + 1)
deleted_est = (max_OID - min_OID + 1) - present_OIDs
```

`deleted_est` estimates the directories deleted from the volume: failed creations would raise it, and deletions
above the highest surviving OID are not counted (pitfall 4), so it is neither a strict lower nor a strict upper
bound. On a volume of 3.10 or later, take `max_OID` from the [stored counter](#at-mount) instead: the deletions above
the highest surviving directory are then counted too (on one corpus volume, 1,509 OIDs above its largest live one).

Density is **100% on fresh volumes** (near-definitional) and, on the worked volumes measured, fell into roughly a
**55–79%** band (an observed range over the — largely v3.14 — corpus, not a fixed constant) — so a volume showing
density well under 100% has a deletion (or failed-creation) history even when no deleted records survive in any
directory. The metric is independent of CoW or slack recovery: it works from the live Object Table alone.

**Chronology is reliable.** A lower OID means an earlier *first* creation of that object. Because a new OID is
always above every live one, the OID order of the live directories is a trustworthy creation-order index across the
whole volume —
unlike NTFS, where MFT-record reuse can place a newer file in an older record number (see the
[NTFS comparison](ntfs_comparison.md)).

**Pitfalls.**

1. The OID is a *volume-wide* identity; do not confuse it with the per-directory child ordinal (`NextFileId`, the
   lower half of the 128-bit FileId), which is counted per directory: never reused within its directory, but the
   same value occurs in every directory — see [File IDs](file_ids.md).
2. `deleted_est` counts deleted *directories*, not deleted files or names: only directories (and system objects)
   draw OIDs, so a deleted file leaves no gap, and a rename consumes no new OID.
3. OID 0x600 (root) and all OIDs `<= 0x6FF` are system objects — exclude them from the density math by starting
   at 0x701.
4. Density gives an estimate, not an exact count. On the corpus's 3.4, 3.7 and 3.9 volumes a long run of sequential
   deletions at the high end is masked, because the high-water mark is only the largest *surviving or logged* key; on 3.10 and later the stored
   counter gives it, as of the last checkpoint.

## Comparison with NTFS

| Property | NTFS MFT record | ReFS OID |
|----------|-----------------|----------|
| Width | 48-bit | 64-bit |
| Sequential | Yes | Yes |
| Reused after deletion | **Yes** (sequence number bumps) | **No** on volumes the 26100 / Insider drivers write (stored counter), except once on a volume upgraded from 3.4; the Windows 10 1803 driver can re-issue the OIDs above the largest live one after a remount |
| Chronology reliability | Partial (reuse obscures) | Strong (a new OID is above every live one) |
| Scope | Per-MFT | Per-volume |
| Deletion estimate from gaps | Unreliable (slots refill) | An estimate of deleted directories (neither a strict lower nor upper bound) |

The per-volume scope and the counter (no OID below a live one is issued again) are why ReFS OID gaps carry deletion evidence that NTFS
record numbers cannot — see [NTFS comparison](ntfs_comparison.md) for the broader contrast.

## Cross-references

- [Object IDs](object_ids.md) — the volume-wide OID, and [File IDs](file_ids.md) — the per-directory
  `NextFileId` ordinal; the distinction that pitfall (1) turns on
- [Deletion and recovery](deletion_recovery.md) — what survives a delete; OID-density estimation is the
  one deletion signal that needs no surviving record
- [System OIDs](../structures/system_oids.md) — the reserved `0x00–0x6FF` range the density math excludes
- [Object Table](../structures/object_table.md) — the B+-tree whose 16-byte key holds the OID
- [NTFS comparison](ntfs_comparison.md) — MFT-record reuse versus the ReFS OID counter

## Evidence

Verified in the driver builds where it was read (17134, 26100.8115, 26100.9444, Insider 29574) and on the raw-disk
corpus. The driver gives the same `0x700` boundary in `MsSetMinimumNewObjectId`, the same increment-and-return
(`CmsObjectTable::GenerateIdentifier` on the 26100 and Insider builds, `MsAllocateObjectId` under a guarded mutex on
17134), and a `DeleteIdentifier` that removes the row and never decrements the counter. The 0x700/0x600 split is the
`RefsIsSystemObjectId` predicate. The counter location is build-specific (`+0x40` of the 17134 structure, `+0x18` of
`CmsObjectTable` on the 26100 builds), but the mechanism is not.

OID monotonicity, the gaps, and the **100%** fresh / **55–79%** worked density figures are raw-disk decoded across
the corpus; the four published samples' outputs hold no OID 0x700 and 40 to 2,316 occurrences of 0x701. That a failed
creation leaves a gap is read in the driver (26100.9444), not measured.

How the counter is kept across mounts is read in the driver on every build with symbols (stored and reloaded by the
26100 and Insider builds, re-derived at each mount by 17134) and measured on the 124 ReFS volumes of the corpus: the
stored counter is in both copies of the Object Table root on every volume of 3.10 and later, equal to the largest OID
on 99 and above it on 13, and zero on the 12 volumes of 3.4, 3.7 and 3.9; in the change journals of the 42 corpus
images that have one, no directory OID is created again after its deletion (13,907 deleted directories, counted per image). A re-issued
OID on a volume the Windows 10 1803 driver wrote is not measured.

See [how this was verified](../methodology.md) for the method.
