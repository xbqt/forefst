# File IDs — the FileRef that Identifies a File

A ReFS file has **no Object ID of its own** (that identifier belongs to directories and system tables — see
[Object IDs](object_ids.md)). A file is instead identified by a **FileId**: the pair

```
 FileRef = (HomeOid, FileId)
           HomeOid = the OID of the directory the file was CREATED in
           FileId  = a per-directory ordinal assigned to the file at birth
```

This 16-byte pair is the file's durable identity. It is exactly the **FileReferenceNumber** the
[USN journal](../structures/usn_journal.md) records for the file, and the value the driver builds with
`RefsPackFileId`; `forefst.py` surfaces it as the `FileRef`, `HomeOid`, and `FileId` columns. This page
explains why the *pair* — not either half alone — is the identity, why it is unique, and, crucially, what
stays fixed when a file is renamed, moved to another directory, hard-linked, or deleted.

## The two halves

**HomeOid — the creation directory's OID.** The upper half of the FileId is an ordinary directory
[Object ID](object_ids.md): 64-bit, volume-unique, drawn from the monotonic OID counter. It identifies the
directory in whose B+-tree the file's record was first created. In a file's on-disk directory entry it is
the *home back-reference* at value+0x08.

**FileId — the per-directory child ordinal (`NextFileId`).** The lower half is a separate, much smaller
counter. Each directory owns a `NextFileId`, held in its
[$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) at $SI+0x58. On child creation the driver
increments the *creating* directory's `NextFileId` and stamps the new child with the assigned ordinal — a
small, near-contiguous integer starting from 2 (0 and 1 are reserved). In the directory entry it is the
value at value+0x00. It is **local to one directory**: two children of two different directories routinely
carry the same ordinal, so an ordinal on its own says nothing about which file it belongs to.

The FileId is globally unique only because the directory OID qualifies it: a volume-unique OID pins down a
single directory's B+-tree, and within that directory the ordinal is unique. The two halves together are an
identity; the lower half alone never identifies a file on its own.

## HomeOid is the *creation* directory, not the current parent

This is the single most important thing to get right about the FileId. `HomeOid` is the OID of the
directory the file was **first created in** — the directory whose `NextFileId` minted the ordinal. It is
**not**, in general, the directory the file's name currently sits in.

For the common case they are the same: a file created in a directory and never moved has `HomeOid` equal to
its current parent. But a file can be moved to another directory, and when it is, `HomeOid` and `FileId`
**do not change** — only the parent changes. That is why the field is called *home*, not *parent*: it
records where the file was born, permanently. On disk, a file whose `HomeOid` differs from its current
parent is one that has been relocated since birth (or hard-linked into a second directory — see below).

## Why the pair is unique — and why the bare ordinal is a trap

The per-directory ordinal **collides across directories**: the same ordinal value appears under many
parents. Matching artifacts on the ordinal alone — or treating it as if it were a volume-wide FileId — will
splice events from unrelated files together. The rule is simple: always qualify the ordinal with its
directory OID, i.e. use the *full* FileId, never just its lower half.

Qualified with its `HomeOid`, the FileId is a genuine, unique object identity, and this is guaranteed by the
B+-tree, not merely observed. A file's actual object — its data and metadata — lives in a **type-0x40
backing record** stored in its home directory's B+-tree, keyed by the ordinal. A B+-tree cannot hold two
rows under the same key, so **a home directory owns at most one file per ordinal**. Across the corpus, every
`(HomeOid, FileId)` group resolves to exactly one home-owned backing — there is no case of two distinct
files sharing a FileRef. (The `(HomeOid, FileId)` pair is also far more discriminating than a
`(parent, ordinal)` pair would be: because many hard-linked system files share a common parent and a low
ordinal, keying on the current parent produces vastly more collisions than keying on the home directory.)

## Two kinds of stability

The FileRef is stable in two independent senses, and both matter for forensics.

**Temporal — never reused after deletion.** `NextFileId` is increment-only: a deleted child's ordinal is
never handed out again — it stays a permanent gap, with no free-list. So within a directory the ordinal
permanently belongs to the file that first received it, and a deleted file's FileRef is **never reassigned**
to a later file. A USN record that references a FileRef therefore always points to the same file across the
whole journal.

**Spatial — unchanged by rename or move.** The FileRef is an *identity*, not a *location*. Renaming a file
leaves it untouched. Moving a file to a different directory leaves `HomeOid` and `FileId` unchanged too —
**only the parent changes.** This was measured directly: across 1,858 real cross-directory moves in nine
volumes, the FileRef's home half changed in **0** cases and its ordinal in **0** cases, while the parent
reference changed every time.

The mechanism explains why. A move relocates the file's **name** — its type-0x30 directory entry — into the
new parent's B+-tree, but the file's **object** — its type-0x40 backing — **stays in the creation
directory's B+-tree**. The FileRef points at the object, and the object never left home. (You can confirm
this on disk: a moved file's backing is found in its `HomeOid` directory, not in its current parent, which
is exactly why a tool can still read the file's true size and content after the move.) This makes `HomeOid`
the durable owner and the reason a relocated file is recognisable at all: its `HomeOid` still names the
directory it was born in.

## Move, copy, rename, hard link — and what each does to storage

Four everyday operations are easy to confuse, but they leave very different marks. This was measured directly
on a controlled before/after pair (a small file created, then moved, renamed, copied, and hard-linked, with the
disk captured on each side):

| Operation | FileRef (HomeOid : ordinal) | Current parent | Storage |
|---|---|---|---|
| **Same-directory rename** | unchanged | unchanged | **stays resident** (only the name changes) |
| **Cross-directory move** | unchanged (home stays the creation dir) | changes | **becomes non-resident** |
| **Hard link** (new name elsewhere) | unchanged — the new name shares it | the new name's parent | **becomes non-resident** (one object, several names) |
| **Copy** | **new** FileRef, homed in the destination | destination | a brand-new object (independent) |

The surprising row is the move. A **cross-directory move converts a small resident file into a non-resident
one**, and it never turns back. The reason is structural: a file that lives in more than one place — a moved
file (name here, object still in its birth directory) or a hard-linked file (several names) — needs a slot that
records its frozen creation-directory home. Only the **non-resident** directory-entry layout has that slot; the
resident layout does not. So the moment a file is moved or hard-linked, ReFS must store it in the non-resident
form, and there is no operation that converts it back to resident.

Two practical consequences:

- **A resident file has always lived in one place.** Its `HomeOid` equals its current parent, because any move
  would have made it non-resident. So `HomeOid != parent` only ever appears on **non-resident** files.
- **Copy is not move.** A copied file is a new object with its own FileRef; only a move (or rename, or hard
  link) preserves the original identity. Correlating history by FileRef therefore follows the *same* file through
  moves and renames, while treating a copy as the separate object it represents.

The per-directory ordinal is handed out by a simple counter (`NextFileId`) that only ever counts up: a deleted
file's ordinal is never given to a later file, even after thousands of deletions — so ordinals are a permanent,
gap-leaving record of creation order within a directory.

## Where the FileRef appears

The same `(HomeOid, FileId)` identity threads through every structure that has to name a file, and all of
them anchor on the *home* directory:

- the **type-0x30 directory entry** — ordinal at value+0x00, home back-reference at value+0x08 (the name;
  this is the part that moves with the file);
- the **type-0x40 backing record** — the file object, keyed by `(home dir, ordinal)`, kept in the home
  directory's tree even after the name is moved;
- the **[type-0x20 FileId-resolution index](../structures/reverse_index.md)** — a per-object row whose
  value is the home-directory back-reference;
- the **reparse index** (OID 0x540) — for a reparse-bearing file, a row whose directory half is likewise
  the home (creation) directory, frozen when the reparse attribute is created;
- the **[USN journal](../structures/usn_journal.md)** — the `FileReferenceNumber` is the FileRef; the
  separate `ParentFileReferenceNumber` is the *current* directory and is what changes on a move;
- the embedded **type-0x39 back-pointers** inside the backing — one per name, used to enumerate a
  [hard-linked](hard_links.md) file's names.

Because they all key on the home directory, they stay consistent through renames and moves.

## Hard links — one FileRef, several names

A hard-linked file has one object but several names, and **all of its names carry the identical
`(HomeOid, FileId)`** — that is correct: the FileRef identifies the *object*, which the names share. The
names live in different directories, so for the extra names `HomeOid` differs from the current parent, just
as for a moved file. To decide *which object* a name belongs to when ordinals collide, each name is resolved
to the type-0x40 backing whose recorded size matches that name's own cached size, and the backing's embedded
type-0x39 back-pointers list every name authoritatively. The [Hard Links](hard_links.md) page works through
the mechanism and its one failure mode (a name whose cached size is stale).

## Using the FileRef in an investigation

- **It is the correct correlation key across a file's whole history.** Because the FileRef survives renames
  and moves while the path does not, correlating [USN journal](../structures/usn_journal.md), log, and
  `$STANDARD_INFORMATION` records on the FileRef tracks one file through every relocation — where a path- or
  name-based correlation would fragment it. This is the join the [artifact timeline](artifact_timeline.md)
  relies on.
- **`HomeOid != parent` is a signal.** A file whose home differs from its current parent has either been
  moved out of its creation directory (a single name — hard-link count 1) or hard-linked into a second
  directory (more than one name — hard-link count above 1). The two are told apart by the hard-link count.
- **A move leaves a two-record trace in the journal.** A cross-directory move is recorded as a
  `RENAME_OLD_NAME` + `RENAME_NEW_NAME` pair carrying the *same* `FileReferenceNumber`; only the
  `ParentFileReferenceNumber` differs between them (old directory → new directory).
- **Targeting by identity.** `forefst.py`'s `--id HomeOid:FileId` addresses a file by its FileRef directly,
  independent of its current path — which resolves correctly even for a moved file, because the object is
  found through its home directory.

## Version differences

`NextFileId` persistence is version-gated. The directory own-row and the non-resident file own-row carry the
ordinal on v3.4 through v3.10, but are **0 on native v3.14/v3.15**: a persist gate (the volume version
`< 0x30b` test) stops writing the ordinal to the own-row, and on v3.11+ the value lives in the object-record
payload instead. A resident file's inline $SI always carries its ordinal, on every version. An upgraded
v3.4-to-v3.14 volume retains the old own-row values. A *zero* own-row value on a native v3.14 volume is
therefore normal, and is **not** evidence of tampering. Do not read the ordinal as a version or write
counter — it is a child-creation ordinal, nothing more.

## Cross-references

- [Object IDs](object_ids.md) — the companion identifier: the volume-wide OID that a directory owns and that
  forms the upper (home) half of every FileId
- [USN Journal](../structures/usn_journal.md) — the `FileReferenceNumber` (the FileRef) and the separate
  `ParentFileReferenceNumber` that changes on a move
- [Directory Entries](../structures/directory_entries.md) — the type-0x30 record where the ordinal
  (value+0x00) and home back-reference (value+0x08) live
- [FileId-Resolution Index](../structures/reverse_index.md) — the type-0x20 per-object index keyed by the
  ordinal, with a home-directory back-reference
- [Hard Links](hard_links.md) — why several names share one FileRef, and how a name resolves to its object
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the `$SI+0x58` NextFileId field and its
  version-gated persistence
- [Artifact Timeline](artifact_timeline.md) — correlating a file's events on the FileRef, which survives
  moves and renames
- [Timestomp Detection](timestomp_detection.md) — pulling a file's full timestamp history by FileRef

## Evidence

The two halves are grounded in the driver (E2) and on disk (RD). `RefsPackFileId` builds the 16-byte file
reference from the ordinal and the directory OID (findings MD_USN_RA_001, MD_USN_RA_002); the ordinal is the
`$SI+0x58` `NextFileId`, incremented by `RefsMoveFile` on the creating directory and stamped onto the child
(findings MD_SI_RA_008, MD_SI_RA_010). The **increment-only, never-reused-after-deletion** property is
decoded in the driver (`RefsMoveFile` advances the counter with a literal `+ 1`; `RefsPersistNextFileId`
writes it; `RefsGetNextFileIdFromObjectTable` reads it back; deletion via `RefsDeleteFileId2` removes only
the type-0x20 resolution entry, with no decrement and no free-list) and confirmed on disk across 3,661 file
references in three journal-rich images, with no reference ever created after being deleted (finding
MD_USN_RA_005).

That `HomeOid` is the **creation** directory and is **frozen across rename and move** rests on both axes.
Statically, `RefsMoveFile` migrates only the type-0x20 FileId-resolution row and never rewrites the FCB's
stored file-reference word, and it is the unified create/move/link path that stamps the home reference once
at creation. On disk, 1,858 real cross-directory moves across nine v3.14 volumes left the FileRef's home and
ordinal halves unchanged in every case, while the `ParentFileReferenceNumber` changed each time; a moved
file's type-0x40 backing is found in its home directory, not its current parent; and the resolution and
reparse indexes place a relocated object's row at its home directory (881 relocated reparse objects, all
indexed at the creation directory, none at the current parent). The unique-object guarantee — one home-owned
type-0x40 backing per ordinal — is the B+-tree key-uniqueness property, re-verified across the corpus with
no counterexample (finding FN_LINK_002). The `version < 0x30b` persist gate that zeroes the own-row on
native v3.14 is decompiled (E2) and disk-confirmed (findings MD_SI_RA_010, MD_SI_RA_008).
