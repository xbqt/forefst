# Worked Example: Track One File Across a Rename and a Move

**Goal:** show that a ReFS file's identity — its **FileRef** `(HomeOid, FileId)` — stays fixed while its
*name* and *directory* change, and use that fixed identity to (a) follow the file through the change journal
and (b) recognise and target it on disk after it has been relocated. The payoff is practical: the FileRef is
the correct key for correlating a file's history, and a move cannot break that correlation the way a
path-based join would.

## Setup

A native ReFS 3.14 image with an **active** USN journal and normal file activity (referred to as `$IMG`).
Two facts about ReFS identity make this work, both covered on the [File IDs](../concepts/file_ids.md) page:

- a file has no OID of its own; it is identified by `FileRef = (HomeOid, FileId)` — the OID of the
  directory it was **created in**, plus a per-directory ordinal assigned at birth;
- that pair is **frozen for the life of the object** — a rename or a move to another directory changes the
  *name* and the *parent*, never the FileRef.

```sh
IMG=your_v3.14_image.raw
```

## Part A — follow a move through the change journal

The USN journal is the history, so it shows the move as it happened. Here one real file was created as a
temp file, written, then renamed into a different directory — the "write a temp, rename to final" pattern
that is also a cross-directory move:

```sh
python3 forefst.py "$IMG" usn --csv - | awk -F, '$7=="0x959e:0x30"'
```

```
reason                         file_ref     home_oid  file_id  parent_oid  name
FILE_CREATE                    0x959e:0x30  0x959e    0x30     0x959e      tmpCF1F.tmp
DATA_EXTEND|DATA_TRUNCATION    0x959e:0x30  0x959e    0x30     0x959e      tmpCF1F.tmp
RENAME_OLD_NAME                0x959e:0x30  0x959e    0x30     0x959e      tmpCF1F.tmp
RENAME_NEW_NAME                0x959e:0x30  0x959e    0x30     0x99df      ServerList.xml
```

Read down the columns. The **`file_ref` is `0x959e:0x30` on every record** — creation, writes, and both
halves of the rename. The move is the `RENAME_OLD_NAME` + `RENAME_NEW_NAME` pair, and across that pair
**only two things change**: the `parent_oid` (`0x959e` → `0x99df`) and the `name` (`tmpCF1F.tmp` →
`ServerList.xml`). The file's identity did not move — its location did. A path-keyed timeline would file
these four records under two unrelated names in two directories; keyed on the `file_ref` they are correctly
one file's story.

(The `home_oid` here is `0x959e` because that is where the file was created; the `RENAME_NEW_NAME` record's
`parent_oid` `0x99df` is the *new* directory — the [USN journal](../structures/usn_journal.md)'s File ID at
record 0x08 versus its Parent file ID at record 0x18.)

## Part B — recognise and target a relocated file on disk

The journal is a sliding window, so a move made long ago may have aged out of it — but the relocation is
*still legible in the live directory tree*, because the moved entry keeps its creation-directory home
back-reference. Take a file that was created in one directory and later moved under `\tools`:

```sh
python3 forefst.py "$IMG" files --csv - | awk -F, '$5=="Generate-FSActivity.ps1"'
```

```
FileRef      HomeOid  FileId  FileName                 ParentOID  ParentPath  FileSize  HardLinkCount
0x9586:0x3   0x9586   0x3     Generate-FSActivity.ps1  0x9e25     tools       72305     1
```

`HomeOid` (`0x9586`) is **not** the same as `ParentOID` (`0x9e25`) — the file sits in `\tools` now, but it
was born in directory `0x9586`. With a hard-link count of 1 (a single name), that `HomeOid != ParentOID`
is the signature of a **relocated** file. (Had the count been above 1, the same shape would instead mean a
hard-link name placed in a second directory — see [Hard Links](../concepts/hard_links.md).)

### Prove it by hand

The entry lives in directory `0x9e25`'s B+-tree, but decode its non-resident value and the home
back-reference names a *different* directory:

```
value+0x00..+0x0f: 03 00 00 00 00 00 00 00  86 95 00 00 00 00 00 00
                   └── ordinal = 3 ──────┘  └── home backref = 0x9586 ┘
value+0x38 file size = 72305
```

`value+0x08 = 0x9586` is the creation directory, carried unchanged into `0x9e25` when the file was moved
(the [directory-entry](../structures/directory_entries.md) fields `value+0x00`/`value+0x08`). The file's
object — its type-0x40 backing, holding the real 72,305-byte content — is still stored in directory
`0x9586`'s tree, **not** in `0x9e25`; the name moved, the object did not.

### Target it by identity, not path

Because the FileRef is the identity, you can address the file by it directly — no path needed, and it
resolves through the home directory even though the name now lives elsewhere:

```sh
python3 forefst.py "$IMG" details --id 0x9586:0x3
```

```
File Detail: tools/Generate-FSActivity.ps1
  Parent OID:   0x9e25
  Parent path:  tools
  Name:         Generate-FSActivity.ps1
  File size:    72305 (70.6 KB)
  Hard-link count: 1
```

The `--id 0x9586:0x3` targets the object at its home; the tool reports the current path (`\tools`) and the
correct size, confirming the identity still reaches the file after the move.

## What this tells you

- **The FileRef `(HomeOid, FileId)` is fixed across rename and move.** In the journal it was constant on
  all four records of the file's life; on disk it is carried unchanged into the new directory. Only the
  *name* and the *parent* change. This was measured corpus-wide: across **1,858 real cross-directory moves**
  in nine volumes, the FileRef changed in **zero** cases.
- **Correlate a file's history on the FileRef, not the path.** In Part A a path-keyed join would have split
  one file into `tmpCF1F.tmp` and `ServerList.xml`; the `file_ref` stitches them into one timeline. This is
  the join the [artifact timeline](../concepts/artifact_timeline.md) and
  [timestomp detection](../concepts/timestomp_detection.md) rely on — a stomp cannot be hidden by moving the
  file afterward, because the journal records still match on the File ID.
- **`HomeOid != ParentOID` is a forensic signal** — a file that has been relocated since birth (single name)
  or hard-linked into another directory (multiple names). The home back-reference records the creation
  directory even after the file has left it, which a live `dir` listing never shows.
- **The object stays home.** A moved file's type-0x40 backing remains in its creation directory's tree,
  which is why `--id` resolution and the reported size stay correct across the move.

## See also

- [File IDs](../concepts/file_ids.md) — the FileRef identity, the two stabilities (temporal and spatial), and the move mechanism
- [USN Journal](../structures/usn_journal.md) — the File ID (record 0x08) vs Parent file ID (record 0x18) and the RENAME_OLD/NEW pair
- [Directory Entries](../structures/directory_entries.md) — the `value+0x00` ordinal and `value+0x08` home back-reference decoded by hand above
- [Artifact Timeline](../concepts/artifact_timeline.md) — why the File ID is the correct correlation key across renames and moves
- [Hard Links](../concepts/hard_links.md) — the other reason `HomeOid != ParentOID` arises (a name placed in a second directory)
