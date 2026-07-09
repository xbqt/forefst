# OID Allocation — Monotonic Counter and Deletion Estimation

Every persistent ReFS object draws its 64-bit Object ID (OID) from a single per-volume counter that
only ever moves forward. The driver hardcodes a boundary at **0x700**, hands out **0x701** as the first
user OID, and on deletion frees the object's B+-tree row but **never rewinds the counter**. The forensic
payoff is large: OIDs are monotonic, never reused, and the *gaps* they leave behind let an analyst
estimate how many objects were created and later deleted — something NTFS makes impossible because it
recycles MFT-record numbers. An OID is also a reliable creation-order index, so the same property that
exposes deletions also orders the surviving objects in time.

## How allocation works

A volume-wide counter lives in the Object Table's in-memory control structure at `CmsObjectTable+0x18`.
That counter — not anything stored per object — is the single source of new identity for the whole
volume. Three distinct driver paths touch it: initialization, allocation, and deletion. The on-disk side
of what they manage is the [Object Table](../structures/object_table.md), whose 8-byte key *is* the OID.

**Initialization — `MsSetMinimumNewObjectId` (the 0x700 boundary).** At mount the driver clamps the
counter so it can never sit below `0x700`. The constant is hardcoded; the routine writes both copies of
the failover-table counter and marks the structure dirty:

```c
// MsSetMinimumNewObjectId
uStack_40 = 0x700; // minimum value
*(undefined8 *)(lVar1 + 0x10) = 0;
*(undefined8 *)(lVar1 + 0x18) = 0x700; // counter = 0x700
*(undefined1 *)(lVar1 + 0x20) = 1; // mark dirty
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

Because the counter is seeded at `0x700`, the first object generated receives **0x701**. The counter
therefore trails the last-assigned OID by exactly one — a useful invariant when reasoning about the
high-water mark.

**Deletion — `CmsObjectTable::DeleteIdentifier` (no rewind).** Deletion calls `CmsTable::DeleteRow` to
remove the object's row from the B+-tree and *does not touch the counter*:

```c
// CmsObjectTable::DeleteIdentifier
lVar3 = CmsTable::DeleteRow(*(CmsTable **)(this + 0x28), ...);
// counter at this+0x18 is never decremented — OID retired forever
```

The removed row vanishes from the live tree, but the identity it consumed is burned: no future object
will ever be issued that number. This is the mechanical reason deletions leave permanent gaps. See
[deletion and recovery](deletion_recovery.md) for what else survives a delete — OID-gap analysis is the
one deletion signal that needs *no* surviving record at all.

**On-mount derivation — rightmost Object-Table key.** The counter is reconstructed at mount from the
rightmost (largest) key in the Object Table B+-tree, so allocation resumes above every OID ever issued —
including those whose rows have since been deleted, because the high-water mark is persisted in the table
root rather than recomputed from live rows. The driver's rightmost/max-key traversal is
`MsFindRightmostNodeAvlFull` / `PinInIndexRightMost`; there is no `CmsKey::RightMost` symbol in any
build. The net effect is a strictly monotonic, per-volume, never-recycled identifier space.

```
 counter @ CmsObjectTable+0x18
 seed 0x700 ─► 0x701 ─► 0x702 ─► 0x703 ─► 0x704 ─► ...
 issued: f1 f2(del) f3 f4(del)
 live rows: 0x701 ........... 0x703 ........... ← 0x702, 0x704 are GAPS
 = past deletions
```

## Forensic implications

**OID gaps are direct evidence of deletion.** If live objects exist at OID 0x710 and 0x712 but none at
0x711, an object was created at 0x711 and later deleted; the slot can never be refilled. Every absent OID
inside the observed `[min_OID, max_OID]` interval corresponds to exactly one object that once existed and
is now gone — there is no aliasing, no reuse, no ambiguity.

**Estimate the deleted-object count from OID density.** Define

```
present_OIDs = number of live Object Table rows with OID >= 0x701
density = present_OIDs / (max_OID - min_OID + 1)
deleted_est = (max_OID - min_OID + 1) - present_OIDs
```

`deleted_est` is a *lower bound* on objects deleted from the volume. Density is **100% on fresh volumes**
(near-definitional) and, on the worked volumes measured, fell into roughly a **55–79%** band (an observed
range over the — largely v3.14 — corpus, not a fixed constant) — so a volume showing density well under
100% has a deletion history even when no deleted records survive in any directory. The metric is independent of CoW or slack
recovery: it works from the live Object Table alone.

**Chronology is reliable.** A lower OID means an earlier *first* creation of that object. Because the
counter is never rewound, OID order is a trustworthy creation-order index across the whole volume —
unlike NTFS, where MFT-record reuse can place a newer file in an older record number (see the
[NTFS comparison](ntfs_comparison.md)).

**Pitfalls.** (1) The OID is a *volume-wide* identity; do not confuse it with the per-directory child
ordinal (`NextFileId`, the lower half of the 128-bit FileId), which *is* reused per directory — see
[object IDs and FileIds](object_ids_fileids.md). (2) `deleted_est` counts deleted *objects*, not deleted
*names*: a hard-linked file with multiple names is one OID, and a rename consumes no new OID. (3) OID
0x600 (root) and all OIDs `<= 0x6FF` are system objects — exclude them from the density math by starting
at 0x701. (4) Density gives a floor, not an exact count: a long run of sequential deletions at the high
end can be masked, because the recoverable high-water mark is only the largest *surviving or logged* key.

## Comparison with NTFS

| Property | NTFS MFT record | ReFS OID |
|----------|-----------------|----------|
| Width | 48-bit | 64-bit |
| Sequential | Yes | Yes |
| Reused after deletion | **Yes** (sequence number bumps) | **No** (counter never rewinds) |
| Chronology reliability | Partial (reuse obscures) | Strong (no reuse) |
| Scope | Per-MFT | Per-volume |
| Deletion estimate from gaps | Unreliable (slots refill) | Reliable lower bound |

The per-volume scope and never-reuse rule are why ReFS OID gaps carry deletion evidence that NTFS
record numbers cannot — see [NTFS comparison](ntfs_comparison.md) for the broader contrast.

## Cross-references

- [Object IDs and FileIds](object_ids_fileids.md) — the volume-wide OID versus the per-directory
  `NextFileId` ordinal; the distinction that pitfall (1) turns on
- [Deletion and recovery](deletion_recovery.md) — what survives a delete; OID-density estimation is the
  one deletion signal that needs no surviving record
- [System OIDs](../structures/system_oids.md) — the reserved `0x00–0x6FF` range the density math excludes
- [Object Table](../structures/object_table.md) — the B+-tree whose 8-byte key is the OID and whose
  rightmost key seeds the counter at mount
- [NTFS comparison](ntfs_comparison.md) — MFT-record reuse versus ReFS never-reuse

## Evidence

Verified across all three driver builds (Win10 v3.4, Win11 v3.14 RTM, Insider) and on the raw-disk
corpus. The driver gives the same `0x700` boundary in `MsSetMinimumNewObjectId`, the same pre-increment
in `CmsObjectTable::GenerateIdentifier`, and a `CmsObjectTable::DeleteIdentifier` that calls
`CmsTable::DeleteRow` and never decrements — in every build (E2). The 0x700/0x600 split is the
`RefsIsSystemObjectId` predicate (E2). The counter location is build-specific (`CmsObjectTable+0x40` on
Win10 v3.4, `+0x18` on Win11 v3.14), but the mechanism is not. OID monotonicity, the never-reuse rule,
gap-as-deletion, and the **100%** fresh / **55–79%** worked density figures are raw-disk decoded across
the corpus (RD). The mount-time high-water-mark recovery uses `MsFindRightmostNodeAvlFull` /
`PinInIndexRightMost`. See [how this was verified](../methodology.md) to trace these to the exact images
and measurements in `analysis/`.
