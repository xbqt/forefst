# File IDs — the FileRef that Identifies a File

A ReFS file has **no Object ID of its own** (that identifier belongs to directories and system tables — see
[Object IDs](object_ids.md)). A file is instead identified by a **FileRef**: the pair

```text
 FileRef = (HomeOID, FileID)
           HomeOID = the OID of the directory the file was CREATED in
           FileID  = a per-directory ordinal assigned to the file at birth
```

This 16-byte pair is the file's durable identity. It is exactly the **FileReferenceNumber** the
[USN journal](../structures/usn_journal.md) records for the file, and the value the driver builds with
`RefsPackFileId`; `forefst.py` surfaces it as the `ObjectRef` column (`HomeOID:FileID`) and the `HomeOID` and
`FileID` columns.

This page explains why the *pair* — not either half alone — is the identity, why it is unique, and what
stays fixed when a file is renamed, moved to another directory, hard-linked, or deleted.

## The two halves

**HomeOID — the creation directory's OID.** The upper half of the FileRef is an ordinary directory
[Object ID](object_ids.md): 64-bit, volume-unique, drawn from the monotonic OID counter. It identifies the
directory in whose B+-tree the file's record was first created. In a split file's directory entry (an index
entry) it is the *home back-reference* at value+0x08; an embedded record has no such field, because its home is
its parent.

**FileID — the per-directory child ordinal (`NextFileId`).** The lower half is a separate, much smaller
counter. Each directory owns a `NextFileId`, kept in its object record (and, on format 3.10 and earlier, also in
its own [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) at $SI+0x58).

On child creation the driver increments the *creating* directory's `NextFileId` and stamps the new child with the
assigned ordinal — a small, near-contiguous integer starting from 2 (0 and 1 are reserved). In an index entry it is
the value at value+0x00; an embedded record carries it at value+0x80 (its `$SI+0x58`).

It is **local to one directory**: two children of two different directories routinely carry the same ordinal, so
an ordinal on its own says nothing about which file it belongs to.

Only a creation uses up an ordinal. A rename, a hard link (in the same directory or into another) and a move do not:
on two lab volumes with hard-link support, Windows' own file IDs and the tool's references agree on every name, and
the files created after those operations took the next ordinals without a gap. (Without hard-link support a move
does take one, in the destination: below.)

The FileRef is globally unique only because the directory OID qualifies it: a volume-unique OID identifies a
single directory's B+-tree, and within that directory the ordinal is unique. The two halves together are an
identity; the lower half alone never identifies a file on its own.

## HomeOID is the *creation* directory, not the current parent

This is the single most important thing to get right about the FileRef. `HomeOID` is the OID of the
directory the file was **first created in** — the directory whose `NextFileId` minted the ordinal. It is
**not**, in general, the directory the file's name currently sits in.

For the common case they are the same: a file created in a directory and never moved has `HomeOID` equal to
its current parent. But a file can be moved to another directory, and when it is, `HomeOID` and `FileID`
**do not change** — only the parent changes. That is why the field is called *home*, not *parent*: it
permanently records the directory the file was created in. On disk, a file whose `HomeOID` differs from its current
parent is one that has been relocated since birth (or hard-linked into a second directory — see below).

## The ordinal alone is not unique; the pair is

The per-directory ordinal **collides across directories**: the same ordinal value appears under many
parents. Matching artifacts on the ordinal alone — or treating it as if it were a volume-wide identifier — will
join events from unrelated files. Always qualify the ordinal with its
directory OID, i.e. use the *full* FileRef, never just its lower half.

Qualified with its `HomeOID`, the FileID is a unique object identity, and this is guaranteed by the
B+-tree, not merely observed. A split file's record — its data and metadata — lives in a **type-0x40 backing
record** stored in its home directory's B+-tree, keyed by the ordinal; an embedded record lives in its name row in
that same directory. A B+-tree cannot hold two rows under the same key, so **a home directory owns at most one
backing per ordinal**.

Across the corpus, every `(HomeOID, FileID)` group resolves to exactly one home-owned backing — there is no case
of two distinct files sharing a FileRef.

The `(HomeOID, FileID)` pair is also far more discriminating than a `(parent, ordinal)` pair would be: because many
hard-linked system files share a common parent and a low ordinal, keying on the current parent produces vastly
more collisions than keying on the home directory.

## Two kinds of stability

The FileRef is stable in two independent senses, and both matter for forensics.

**Temporal — never reused after deletion.** `NextFileId` is increment-only: a deleted child's ordinal is
never handed out again — it stays a permanent gap, with no free-list. So within a directory the ordinal
permanently belongs to the file that first received it, and a deleted file's FileRef is **never reassigned**
to a later file. A USN record that references a FileRef therefore always points to the same file across the
whole journal.

**Spatial — unchanged by rename or move.** The FileRef is an *identity*, not a *location*. Renaming a file
leaves it untouched. Moving a file to a different directory leaves `HomeOID` and `FileID` unchanged too —
**only the parent changes.** This was measured directly: across every real cross-directory move measured, the
FileRef's home half and its ordinal **never** changed, while the parent reference changed every time.

The mechanism explains why. On a volume with hard-link support, a move relocates the file's **name** — its type-0x30
directory entry — into the new parent's B+-tree, but the file's **object** — its type-0x40 backing — **stays in the
creation directory's B+-tree**. The FileRef points at the object, and the object stays in the creation directory. (You can confirm
this on disk: a moved file's backing is found in its `HomeOID` directory, not in its current parent, which is exactly
why a tool can still read the file's true size and content after the move.) This makes `HomeOID` the durable owner and
the reason a relocated file is recognisable at all: its `HomeOID` still names the directory it was created in.

## Move, copy, rename, hard link — and what each does to the record

Four everyday operations are easy to confuse, but each changes the identity, the parent and the record placement
differently. This was measured directly
on a controlled before/after pair (a small file created, then moved, renamed, copied, and hard-linked, with the
disk captured on each side):

| Operation | FileRef (HomeOID : ordinal) | Current parent | Record placement |
|---|---|---|---|
| **Same-directory rename** | unchanged | unchanged | **stays embedded** (only the name changes) |
| **Cross-directory move** | unchanged (home stays the creation dir) | changes | **split out** of the name row |
| **Hard link** (new name elsewhere) | unchanged — the new name shares it | the new name's parent | **split out** (one object, several names) |
| **Copy** | **new** FileRef, homed in the destination | destination | a brand-new object (independent) |

The surprising row is the move. On a volume with hard-link support, a **cross-directory move splits a file's
record out of its name row** into a backing record, and the record stays split.

The likely reason is structural (a reading of the two layouts, not of the driver): a file that lives in more than
one place — a moved file (name here, object still in its creation directory) or a hard-linked file (several names) —
needs a slot that records its creation directory, which does not change. Only the index-entry layout has that slot; the
embedded layout does not. No operation converts a split record back.

On a volume **without** hard-link support (the boot sector's flags lack 0x20 — measured on volumes formatted at
ReFS 3.4 and those upgraded from them) the move is different:

- the whole embedded record moves into the new directory and takes that directory's next ordinal;
- it keeps the file's original FileRef at `$SI+0x68` (directory) / `$SI+0x60` (ordinal) — the identity Windows
  still reports for it;
- the old directory keeps a forwarding entry.

This was measured on a lab volume (two moves, Windows' file IDs equal to that reference) and on the corpus volumes
without hard-link support, each moved record with one forwarding entry.

The split is a statement about the **record**, not about the file's data: the record moves out of the name row,
and the bytes can stay inline inside it. On format 3.11 and later a small moved or hard-linked file
is commonly still stored inline — see [Record placement and data residency](placement_and_residency.md).

Two practical consequences:

- **On a volume with hard-link support, an embedded record has always lived in one place.** Its `HomeOID` equals
  its current parent, because any move would have split it. So there `HomeOID != parent` only ever appears on
  **split** records. (On a volume without hard-link support a moved record stays embedded; its original FileRef
  is at `$SI+0x68` / `$SI+0x60`.)
- **Copy is not move.** A copied file is a new object with its own FileRef; only a move (or rename, or hard
  link) preserves the original identity. Correlating history by FileRef therefore follows the *same* file through
  moves and renames, while treating a copy as the separate object it represents.

The per-directory ordinal is handed out by a simple counter (`NextFileId`) that only ever counts up: a deleted
file's ordinal is never given to a later file, even after thousands of deletions — so ordinals are a permanent,
gap-leaving record of creation order within a directory.

## Where the FileRef appears

Every structure that has to name a file uses the same `(HomeOID, FileID)` identity, and all of them refer to
the *home* directory:

- the **type-0x30 directory entry** — in an index entry, ordinal at value+0x00 and home back-reference at
  value+0x08; in an embedded record, the ordinal at value+0x80, the parent being the home (the name; this is the
  part that moves with the file);
- the **type-0x40 backing record** — the file object, keyed by `(home dir, ordinal)`, kept in the home
  directory's tree even after the name is moved;
- the **[type-0x20 FileId-resolution index](../structures/reverse_index.md)** — a per-object row whose
  value is the home-directory back-reference;
- the **reparse index** (OID 0x540) — for a reparse-bearing file, a row whose directory half is likewise
  the home (creation) directory, fixed when the reparse attribute is created;
- the **[USN journal](../structures/usn_journal.md)** — the `FileReferenceNumber` is the FileRef; the
  separate `ParentFileReferenceNumber` is the *current* directory and is what changes on a move;
- the embedded **type-0x39 back-pointers** inside the backing — one per name, used to enumerate a
  [hard-linked](hard_links.md) file's names.

Because they all key on the home directory, they stay consistent through renames and moves.

## Hard links — one FileRef, several names

A hard-linked file has one object but several names, and **all of its names carry the identical
`(HomeOID, FileID)`** — that is correct: the FileRef identifies the *object*, which the names share. The
names live in different directories, so for the extra names `HomeOID` differs from the current parent, just
as for a moved file. To decide *which object* a name belongs to when ordinals collide, each name is resolved
to the type-0x40 backing whose recorded size matches that name's own cached size, and the backing's embedded
type-0x39 back-pointers list every name authoritatively. The [Hard Links](hard_links.md) page works through
the mechanism, including a name whose cached size is stale (the back-pointers then decide).

## Using the FileRef in an investigation

- **It is the correct correlation key across a file's whole history.** Because the FileRef survives renames
  and moves while the path does not, correlating [USN journal](../structures/usn_journal.md) and
  `$STANDARD_INFORMATION` records on the FileRef tracks one file through every relocation — where a path- or
  name-based correlation would fragment it. This is how to read the [artifact timeline](artifact_timeline.md)'s
  rows for one file (an MLog row names the directory its records change, not the FileRef).
- **`HomeOID != parent` is a signal.** A file whose home differs from its current parent has either been
  moved out of its creation directory (a single name — hard-link count 1) or hard-linked into a second
  directory (more than one name — hard-link count above 1). The hard-link count tells the two apart, except that a
  single name can also be a hard link whose first name was removed: the metadata does not tell that from a move,
  the change journal does (below).
- **A move leaves a two-record trace in the journal.** A cross-directory move is recorded as a
  `RENAME_OLD_NAME` + `RENAME_NEW_NAME` pair carrying the *same* `FileReferenceNumber`; only the
  `ParentFileReferenceNumber` differs between them (old directory → new directory).
- **A hard link leaves its own record.** refs.sys writes `HARD_LINK_CHANGE | CLOSE` (0x80010000) both when a link
  is made and when one is removed, each with that link's parent and name (read on 26100.8115). Read in USN order,
  the most recent record that puts a name at (parent, name) says how it came there — a link made, a rename or a
  move. `files` and `details` use that rule for `IsMoved` where the journal's history is whole: on the public sample
  every decided row agrees with the workload logs (moves, hard links made, and directories in or outside their
  creation directory). On a journal that was created again (some of the corpus journals are) the rule is not used.
- **Targeting by identity.** `forefst.py`'s `--id HomeOID:FileID` addresses a file by its FileRef directly,
  independent of its current path — which resolves correctly even for a moved file, because the object is
  found through its home directory.

## Version differences

`NextFileId` persistence is version-gated:

- a directory's own row carries its counter, and a split file's backing its ordinal, on formats up to 3.10; both
  read **0 on native v3.14**: a persist gate (the volume version `< 0x30b` test) stops writing them, and the
  directory's counter is kept in its object-record payload, as on every version;
- an embedded file record's `$SI` always carries its ordinal, on every version;
- an upgraded v3.4-to-v3.14 volume retains the old own-row values.

A *zero* own-row value on a native v3.14 volume is therefore normal, and is **not** evidence of tampering. Do not
read the ordinal as a version or write counter — it is a child-creation ordinal, nothing more.

## Cross-references

- [Object IDs](object_ids.md) — the companion identifier: the volume-wide OID that a directory owns and that
  forms the upper (home) half of every FileRef
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

## The 128-bit id Windows reports is this pair

`fsutil file queryfileid` prints a 128-bit value, and it decomposes **exactly** into the two halves this
page describes: the high 64 bits are the home directory's OID, the low 64 bits the per-home ordinal.
The root directory is OID `0x600`. So the identifier an examiner reads from a live Windows system and
the identifier recovered from the image are the same number, expressed the same way.

## Evidence

The two halves are grounded in the driver (E2) and on disk (RD). `RefsPackFileId` builds the 16-byte file reference
from the ordinal and the directory OID; the ordinal is the `$SI+0x58` `NextFileId`, incremented by `RefsMoveFile` on
the creating directory and stamped onto the child. The **increment-only, never-reused-after-deletion** property is
decoded in the driver (`RefsMoveFile` advances the counter with a literal `+ 1`; `RefsPersistNextFileId` writes it;
`RefsGetNextFileIdFromObjectTable` reads it back; deletion via `RefsDeleteFileId2` removes only the type-0x20
resolution entry, with no decrement and no free-list) and confirmed on disk across 3,661 file references in three
journal-rich images, with no reference ever created after being deleted.

That `HomeOID` is the **creation** directory and is **frozen across rename and move** rests on both axes.
Statically, `RefsMoveFile` migrates only the type-0x20 FileId-resolution row and never rewrites the FCB's
stored file-reference word, and it is the unified create/move/link path that stamps the home reference once
at creation. On disk, 1,858 real cross-directory moves across nine v3.14 volumes left the FileRef's home and
ordinal halves unchanged in every case, while the `ParentFileReferenceNumber` changed each time; a moved
file's type-0x40 backing is found in its home directory, not its current parent; and the resolution and
reparse indexes place a relocated object's row at its home directory (881 relocated reparse objects, all
indexed at the creation directory, none at the current parent). The unique-object guarantee — one home-owned
type-0x40 backing per ordinal — is the B+-tree key-uniqueness property, re-verified across the corpus with
no counterexample. The `version < 0x30b` persist gate that zeroes the own-row on
native v3.14 is decompiled (E2) and disk-confirmed.

The 128-bit split into home OID and ordinal, with the root at `0x600`, and Windows' own `queryfileid` value
decomposing into exactly that pair are registered findings too, as is each statement above.

The counts behind the text: 1,858 real cross-directory moves on nine volumes, the home half and the ordinal changed in
0; without hard-link support, 409 moved records on 8 volumes (the lab volume among them), each with one forwarding
entry; on the public sample, 539 decided `IsMoved` rows agree with the workload logs (91 moves, 252 hard links made,
144 / 52 directories in / outside their creation directory); 8 of the 38 corpus journals were created again.

<!-- findings: FN_ADDR_001, FN_LINK_002, GN_IDENT_RA_001, MD_DISK_RA_010, MD_SI_RA_008, MD_SI_RA_010,
               MD_USN_RA_001, MD_USN_RA_002, MD_USN_RA_005, MD_USN_RA_006 -->
