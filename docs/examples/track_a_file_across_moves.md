# Track One File Across a Rename and a Move

**Goal:** show that a ReFS file's identity — its **FileRef** `(HomeOID, FileID)` — stays fixed while its
*name* and *directory* change, and use that fixed identity to (a) follow the file through the change journal
and (b) recognise and target it on disk after it has been relocated. In practice, the FileRef is
the correct key for correlating a file's history: a move breaks a path-based join, but not a join on the
FileRef.

## Setup

Image: `winsider.raw`, the Windows Server Insider system volume of the test corpus: a native ReFS 3.14 image with an
**active** USN journal and normal file activity.

Two facts about ReFS identity make this work, both covered on the [File IDs](../concepts/file_ids.md) page:

- a file has no OID of its own; it is identified by `FileRef = (HomeOID, FileID)` — the OID of the
  directory it was **created in**, plus a per-directory ordinal assigned at creation;
- that pair is **fixed for the life of the object** — a rename or a move to another directory changes the
  *name* and the *parent*, never the FileRef.

## Part A — follow a move through the change journal

The USN journal is the history, so it shows the move as it happened. Here one real file was created as a
temp file, written, then renamed into a different directory — the "write a temp, rename to final" pattern
that is also a cross-directory move:

```text
$ forefst.py winsider.raw usn --csv | awk -F, 'NR==1 || $7=="0x959e:0x30" {print $3","$5","$7","$8","$9","$10}'
Reason,FileName,ObjectRef,HomeOID,FileID,ParentOID
FILE_CREATE,tmpCF1F.tmp,0x959e:0x30,0x959e,0x30,0x959e
FILE_CREATE|CLOSE,tmpCF1F.tmp,0x959e:0x30,0x959e,0x30,0x959e
DATA_TRUNCATION,tmpCF1F.tmp,0x959e:0x30,0x959e,0x30,0x959e
DATA_EXTEND|DATA_TRUNCATION,tmpCF1F.tmp,0x959e:0x30,0x959e,0x30,0x959e
DATA_EXTEND|DATA_TRUNCATION|CLOSE,tmpCF1F.tmp,0x959e:0x30,0x959e,0x30,0x959e
RENAME_OLD_NAME,tmpCF1F.tmp,0x959e:0x30,0x959e,0x30,0x959e
RENAME_NEW_NAME,ServerList.xml,0x959e:0x30,0x959e,0x30,0x99df
RENAME_NEW_NAME|CLOSE,ServerList.xml,0x959e:0x30,0x959e,0x30,0x99df
FILE_DELETE|CLOSE,ServerList.xml,0x959e:0x30,0x959e,0x30,0x99df
```

Read down the columns. The **`ObjectRef` is `0x959e:0x30` on every record** — creation, writes, both halves of
the rename, and the later deletion. The move is the `RENAME_OLD_NAME` + `RENAME_NEW_NAME` pair, and across that
pair **only two things change**: the `ParentOID` (`0x959e` → `0x99df`) and the `FileName` (`tmpCF1F.tmp` →
`ServerList.xml`). The file's identity did not move — its location did. A path-keyed timeline would file these nine
records under two unrelated names in two directories; keyed on the `ObjectRef` they are correctly grouped as one file's records.

(The `HomeOID` here is `0x959e` because that is where the file was created; the `RENAME_NEW_NAME` record's
`ParentOID` `0x99df` is the *new* directory — the [USN journal](../structures/usn_journal.md) record's File ID at
offset 0x08 versus its Parent file ID at offset 0x18.)

## Part B — recognise and target a relocated file on disk

The journal is a ring of limited size that overwrites its oldest records, so a move made long ago may have aged
out of it — but the relocation *can still be read in the live directory tree*, because the moved entry keeps its
creation-directory home back-reference.

Take a file that was created in one directory and later moved under `tools` (the `files` columns cut out:
ObjectRef 1, FileName 3, FileSize 5, ParentPath 10, ParentOID 11, HardLinkCount 31):

```text
$ forefst.py winsider.raw files --csv | awk -F, 'NR==1 || $3=="Generate-FSActivity.ps1"' | cut -d, -f1,3,10,11,5,31
ObjectRef,FileName,FileSize,ParentPath,ParentOID,HardLinkCount
0x9586:0x3,Generate-FSActivity.ps1,72305,tools,0x9e25,1
```

`HomeOID` (`0x9586`) is **not** the same as `ParentOID` (`0x9e25`) — the file sits in `tools` now, but it
was created in directory `0x9586`.

- With a hard-link count of 1 (a single name), that `HomeOID != ParentOID` shows a **relocated**
  file: a move, or a hard link made there whose original name was then removed. The metadata alone does not tell
  the two apart; here the change journal does (`details` below says `moved (change journal)`).
- Had the count been above 1, the same shape could also be a hard-link name placed in a second directory — see
  [Hard Links](../concepts/hard_links.md).

### Prove it by hand

The entry lives in directory `0x9e25`'s B+-tree, but decode its name row's value (the index-entry layout of a
split record, key_flags 0x02) and the home back-reference names a *different* directory:

```text
value+0x00..+0x0f: 03 00 00 00 00 00 00 00  86 95 00 00 00 00 00 00
                   └── ordinal = 3 ──────┘  └── home backref = 0x9586 ┘
value+0x38 file size = 72305
```

`value+0x08 = 0x9586` is the creation directory, carried unchanged into `0x9e25` when the file was moved
(the [directory-entry](../structures/directory_entries.md) fields `value+0x00`/`value+0x08`).

The file's object — its type-0x40 backing, which holds the file's own record (its times, its size of 72,305 bytes
and the map of the extents that hold its data) — is still stored in directory `0x9586`'s tree, **not** in
`0x9e25`; the name moved, the object did not.

### Target it by identity, not path

Because the FileRef is the identity, you can address the file by it directly — no path needed, and it
resolves through the home directory even though the name now lives elsewhere:

The output (excerpt):

```text
$ forefst.py winsider.raw details --id 0x9586:0x3
==============================================================================
File Detail: tools/Generate-FSActivity.ps1
==============================================================================
  ObjectRef:          0x9586:0x3   (FileRef = HomeOID:FileID, the directory the file was CREATED in)
  Home directory:     0x9586   created here; this name is under parent 0x9e25: moved (change journal)
  Name:               Generate-FSActivity.ps1
  Extension:          .ps1
  File size:          72305 bytes (70.6 KiB)
[...]
  Parent path:        tools
  Parent OID:         0x9e25
  Creation dir:       Users/Administrator/Downloads
  HomeOID:            0x9586   (the directory this file was CREATED in; unchanged by move/rename)
  FileID:             0x3
[...]
  Is moved:           moved (change journal)
[...]
  Hard-link count:    1
[...]
```

The `--id 0x9586:0x3` targets the object at its home; the tool reports the current path (`tools`), the directory
the file was created in (`Users/Administrator/Downloads`) and the correct size, and the change journal says how the
name came there (`moved`), confirming the identity still reaches the file after the move.

## What this tells you

- **The FileRef `(HomeOID, FileID)` is fixed across rename and move.** In the journal it was constant on all nine
  records of the file's life, from its creation to its deletion; on disk it is carried unchanged into the new
  directory. Only the *name* and the *parent* change. Measured on nine v3.14 volumes of the corpus: across
  **1,858 real cross-directory moves**, the FileRef changed in **zero** cases.
- **Correlate a file's history on the FileRef, not the path.** In Part A a path-keyed join would have split
  one file into `tmpCF1F.tmp` and `ServerList.xml`; the `ObjectRef` joins them into one timeline.
  - It is the key the [artifact timeline](../concepts/artifact_timeline.md) page tells you to correlate on (the
    `timeline` command lists its sources side by side and does not join them).
  - [Timestomp detection](../concepts/timestomp_detection.md) matches journal records on it, so moving a file
    afterwards does not hide a stomp from it, as long as the journal still holds the records.
- **`HomeOID != ParentOID` is a forensic signal** — a file that has been relocated since its creation (single name: a
  move, or a hard link whose original name was removed) or hard-linked into another directory (multiple names).
  The home back-reference records the creation directory even after the file has left it, which a live `dir`
  listing never shows.
- **The object stays in its creation directory.** On a volume with hard-link support (boot-sector flags bit 0x20), a moved file's
  type-0x40 backing remains in its creation directory's tree, which is why `--id` resolution and the reported size
  stay correct across the move. Without that support the record moves whole with its name and carries its original
  reference with it.

## See also

- [File IDs](../concepts/file_ids.md) — the FileRef identity, the two stabilities (temporal and spatial), and the move mechanism
- [USN Journal](../structures/usn_journal.md) — the File ID (record offset 0x08) vs Parent file ID (record offset 0x18) and the RENAME_OLD/NEW pair
- [Directory Entries](../structures/directory_entries.md) — the `value+0x00` ordinal and `value+0x08` home back-reference decoded by hand above
- [Artifact Timeline](../concepts/artifact_timeline.md) — why the File ID is the correct correlation key across renames and moves
- [Hard Links](../concepts/hard_links.md) — the other reason `HomeOID != ParentOID` arises (a name placed in a second directory)
