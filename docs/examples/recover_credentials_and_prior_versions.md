# Recover Credentials, Alternate Streams and Earlier File Versions

**Goal:** on one volume, find the credentials (including those someone tried to hide), read the alternate data
streams, and read what a file said **before** it was edited. Then show what this volume could **not** give: the
content of a file emptied from the Recycle Bin.

Every command below is real, and every output is what the tool printed (`[...]` marks lines left out). Where an
answer can be checked against something the volume itself recorded, it is checked.

## Setup

A 3.9 GiB native **ReFS 3.14** volume (4 KiB clusters, CRC64 metadata checksums) imaged from a Windows 11 test
machine (`win11bidule.raw` in the test corpus). It was used normally for a day: files downloaded, edited, renamed,
deleted (directly, to the Recycle Bin, and from it) and snapshotted.

```text
$ forefst.py win11bidule.raw summary
[...]
  ReFS version:       3.14
[...]
  Volume label:       data
[...]
  Cluster size:       4 KiB
[...]
  Checksum:           CRC64
[...]
  Volume created:     2026-09-01T09:32:39.5748217Z
[...]
  Volume state:       NATIVE ReFS 3.14
[...]
  Space used:         2.4 GiB of 3.9 GiB (61.6%) — 1.5 GiB not allocated
[...]
  USN Journal:        Active
[...]
```

Native ReFS 3.14, never upgraded, and its USN journal is active — so the volume's own record of its changes is there
to check what follows against.

---

## Part 1 — Find the credentials

### 1a. The deleted file — its bytes are in its own record, not carved

Start with the deletion scan, which reads the free space inside metadata pages. Plain `deleted` prints one line
per entry (`bytes in row   2026-09-01T10:36:44.6740305Z  username.txt           tests`: what can be recovered, the creation
time, the name, the folder whose page held the row); `-v` prints each entry's details:

```text
$ forefst.py win11bidule.raw deleted -v
[...]
    FILE username.txt  (embedded record, slack of a live page @ cluster 0xe0c off 0xa10, image offset 0x1e0ca10)
      Found in a page of: tests  (table 0x703; where it was found, not necessarily where it was deleted from)
      Identity: ObjectRef 0x703:0x2d, read from the change journal, live nowhere
      Created:  2026-09-01T10:36:44.6740305Z
      Modified: 2026-09-01T10:36:44.6765532Z
      Recoverable: content inline: the 40 B this remnant holds (`export deleted` writes them as they are)
[...]
```

**`content inline` means the row itself holds the file's bytes.** On ReFS 3.11 and later a file under 2 KiB
normally keeps its bytes *inside* its own record rather than in separate clusters (on 3.10 and earlier it never
does).

Deleting the file removes the row's entry from the page's index, but the row body — including those bytes — stays
in the page until something overwrites it. So the content is read back, not reconstructed: `export deleted` writes
the 40 bytes as the remnant holds them (it does not check that they are the whole file as it was):

```text
$ forefst.py win11bidule.raw export deleted ./out
[...]
  176 entries indexed → ./out/deleted_files.csv  (+ .json; every entry the report lists, its Status
  column says what it is)
    Content recovered: 2 inline (as found) + 0 extent-backed carved = 2 files → ./out/content/
    Recovery log → ./out/recovery_log.txt
    1 extent-backed file(s) have a recoverable extent map — re-run with --full to carve their content (best-effort).
[...]
$ cat ./out/content/username.txt
username:bat
password:in the other file
```

We have the **username: `bat`** — and a pointer to a second file.

(The index lists every entry the report shows, the live files' old copies too; content is written for an entry
whose row holds its bytes, unless its file is still live.)

### 1b. "The other file" — the name was changed to hide it

Nothing on the volume is called `password`. Search for the obvious alternative:

```text
$ forefst.py win11bidule.raw search passphrase
ObjectRef      Type          Size  Data             Modified                      Path
─────────────  ────  ────────────  ───────────────  ────────────────────────────  ────────────────────────────────────────
0x703:0x2b     File           104  inline           2026-09-01T10:39:30.4201261Z  tests/passphrase.txt

1 match. Use `details <path>`, `details --id FileRef` (HomeOID:FileID) or `details --id OID` for full detail.
```

```text
$ forefst.py win11bidule.raw extract /tests/passphrase.txt
password:Des scorpions culpabiliseront dans mon salon.


** Generated with https://xbpt.gitlab.io/pp/
```

**The password is recovered — but the file name is not the one it was written under.** The change journal
records renames as a pair of entries, and both carry the same file reference, which is what proves they are
one object rather than two files that happen to look alike:

```text
$ forefst.py win11bidule.raw usn --csv | grep RENAME | grep 0x703:0x2b
66904,2026-09-01T10:40:11.2247867Z,RENAME_OLD_NAME,0x1000,generatepasswordfromxbptgitlabiopp.txt,false,0x703:0x2b,[...]
67056,2026-09-01T10:40:11.2247867Z,RENAME_NEW_NAME,0x2000,passphrase.txt,false,0x703:0x2b,[...]
67160,2026-09-01T10:40:11.2273346Z,RENAME_NEW_NAME|CLOSE,0x80002000,passphrase.txt,false,0x703:0x2b,[...]
```

The original name — `generatepasswordfromxbptgitlabiopp.txt` — states the file's purpose *and* names the
generator it came from, and it survives in the journal. The full journal entry sequence for that same
reference `0x703:0x2b` also dates the activity precisely:

| time (UTC) | journal reason | what it means |
|------------|----------------|---------------|
| 10:36:02 | `FILE_CREATE` | file created under the original name |
| 10:37:24 → 10:39:24 | `DATA_OVERWRITE\|DATA_EXTEND` ×3 | candidate passphrases generated and replaced |
| 10:39:30 | `DATA_OVERWRITE\|DATA_TRUNCATION` | the final 104-byte content settled |
| **10:40:11** | **`RENAME_OLD_NAME` → `RENAME_NEW_NAME`** | **renamed to `passphrase.txt`** |

Renaming a file changes nothing about its identity on ReFS: the reference `0x703:0x2b` is fixed at creation
and survives renames and moves. That is why the two halves of the rename can be tied together at all.

### 1c. Whose account?

The Recycle Bin says which account sent files to it:

```text
$ forefst.py win11bidule.raw recyclebin
[...]
  $IY0YDJS.txt   (SID S-1-5-21-1473886876-2352682097-2257922272-1001)
    Original path:  R:\tests\bigtextfiledeleted.txt
    Deleted:        2026-09-01T10:50:39.0020000Z
    Size:           41943040 bytes
    Payload ($RY0YDJS.txt): present
[...]
```

The Recycle Bin is organised into one folder per user security identifier, and `-1001` is the relative id of an
ordinary account (1001 is usually the first account created on a machine); the identifier gives no name. A
PowerShell transcript saved on this volume names the user:

```text
$ forefst.py win11bidule.raw extract /logs/transcript2.txt | head -7
**********************
Windows PowerShell transcript start
Start time: 20260901132501
Username: malw\bat
RunAs User: malw\bat
Configuration Name: 
Machine: MALW (Microsoft Windows NT 10.0.26200.0)
```

**`malw\bat`** — matching the `username:bat` recovered from the deleted file, and matching the profile path
`C:\Users\bat` in another transcript on the volume (`logs/transcript.txt`). Two independent sources, the deleted
note and the transcripts, give the same account.

---

## Part 2 — Find the alternate data streams, in one command

Alternate data streams are a classic hiding place, and on ReFS they need no scan — they are rows in each
file's own attribute set, so listing them is a single tree walk:

```text
$ forefst.py win11bidule.raw ads
── ads  (31 objects, 31 names) — named data streams ──
  OBJECTREF = the host file's reference (HomeOID:FileID); RESIDENCY = where the stream's bytes are
  OBJECTREF        STREAM                     RESIDENCY      HOST FILE
  0x703:0x20       Zone.Identifier            inline         $RECYCLE.BIN/S-1-5-21-1473886876-2352682097-2257922272-1001/$RRJOQB1.xml
  0x703:0x22       Zone.Identifier            inline         $RECYCLE.BIN/S-1-5-21-1473886876-2352682097-2257922272-1001/$RWQ96ME.jpg
  0x703:0x14       Zone.Identifier            inline         $RECYCLE.BIN/S-1-5-21-1473886876-2352682097-2257922272-1001/$RY0YDJS.txt
  0x703:0x15       Zone.Identifier            inline         tests/100pagesword.docx
[...]
  0x703:0x25       Zone.Identifier            inline         tests/zip1mb.zip
[...]
```

**No stream other than `Zone.Identifier` exists on this volume; that absence is a finding too.** All
31 are `Zone.Identifier`, the stream Windows attaches to a downloaded file (three of the files are now in the
Recycle Bin, under their `$R` names).

A stream of that name can hold any bytes, so read them; the one shown below holds ordinary download metadata. They also
show where these files came from.

`export ads` writes the stream to a file named after the file and the stream (beside it, a `.holes.json` record of
whether any of its bytes came from a range the image stores as a hole), and says so on stderr. `cat` shows its
content (Windows line ends; the stream's last byte, after the `HostUrl` value, is a NUL, `0x00`, not shown):

```text
$ forefst.py win11bidule.raw export ads "tests/Get-ZimmermanTools.zip:Zone.Identifier"
[...]
Extracting 'Get-ZimmermanTools.zip:Zone.Identifier' (144 bytes):
[forefst] wrote 144 bytes to ./Get-ZimmermanTools.zip__Zone.Identifier
$ cat ./Get-ZimmermanTools.zip__Zone.Identifier
[ZoneTransfer]
ZoneId=3
ReferrerUrl=https://ericzimmerman.github.io/
HostUrl=https://download.ericzimmermanstools.com/Get-ZimmermanTools.zip
```

`ZoneId=3` means the file came from the internet, and the two URLs give the page the user was on and the
address the bytes actually came from. Repeating that for every `Zone.Identifier` stream gives the origin of the
downloads still on the volume (those a tool saved without the stream, and those deleted since, are not covered).

To pull the stream names into a spreadsheet alongside everything else, `files --csv` carries them in its `HasADS`
and `ADSNames` columns.

---

## Part 3 — Read what a file said before it was edited

One file on this volume reports snapshots:

```text
$ forefst.py win11bidule.raw snapshots --show
[...]
  Files with snapshots: 1
  Total snapshots:      2

------------------------------------------------------------------------------

  FILE tests/secret.txt
    Created:      2026-09-01T10:40:23.1096170Z
    Modified:     2026-09-01T10:44:32.3652989Z
    Record value: 1608 bytes (the name row's value, which holds the versions)
    Snapshots:    2

    [1] "backup 2"
        Created:           2026-09-01T10:44:10.0908010Z
        Stream size:       79 bytes
    [2] "too important to lose"
        Created:           2026-09-01T10:43:04.1814251Z
        Stream size:       58 bytes

    Recovered content (2 version(s)):
      [too important to lose] sub_id=0x1001 size=58 -> 58 bytes, 1 extent(s)
          "i don't understand anything to refs, it's too complicated!"
      [backup 2] sub_id=0x1002 size=79 -> 79 bytes, 1 extent(s)
          "i don't understand anything to refs, it's too complicated!\r\ni can't say that..."
```

Now compare that with the file as it stands today:

```text
$ forefst.py win11bidule.raw extract /tests/secret.txt
no, i can't say that...
```

**25 bytes live; 79 bytes in the most recent snapshot.** The current file was overwritten with shorter text, and
the text it replaced is still on the volume. The journal dates every write, and the snapshot times
`snapshots --show` prints fall exactly between the writes:

| time (UTC) | event | resulting size |
|------------|-------|----------------|
| 10:40:23 | `FILE_CREATE` | 0 |
| 10:41:39 | `DATA_EXTEND` | 58 |
| **10:43:04** | **snapshot `"too important to lose"` taken** | **58 captured** |
| 10:43:57 | `DATA_OVERWRITE\|DATA_EXTEND` | 79 |
| **10:44:10** | **snapshot `"backup 2"` taken** | **79 captured** |
| 10:44:32 | `DATA_OVERWRITE\|DATA_TRUNCATION` | 25 |

The last write replaced the 79-byte text with 25 new bytes. Both earlier versions survive because taking a
snapshot switches the file to **copy-on-write**: from that moment, writing a block does not overwrite it but
allocates a new one, leaving the snapshot pointing at the original. The current stream owns only the blocks written
since the last snapshot; everything else is shared with the versions before it.

**This is reading, not reconstruction.** Here each earlier version is read from its snapshot's own extent (one each,
`1 extent(s)` above); nothing is rebuilt or guessed. For a file changed after several snapshots, the tool also takes
the unchanged blocks from older snapshots, never from newer ones.

Both recovered sizes — 58 and 79 — are exactly the sizes Windows itself reports for those snapshots.

> **`extract` and `snapshots --extract` are not the same command.**
> `extract` gives you the file's **current** stream — the 25 bytes above.
> `snapshots --extract DIR` writes the **earlier versions** — the 58- and 79-byte ones (`--snapshot SEL` selects
> by index `[N]` or by part of a version name).
> A file can have both, and on this volume the interesting content is only in the second.

---

## Part 4 — A file whose content did not survive

The same volume holds a file that was deleted from the Recycle Bin — emptied, not merely sent there. Its
metadata came back; **its content did not.** This section reports that
result.

`jpgharddeleted.jpg` is a clean experiment, because the operator made **two copies of the same 7 MB image**:
one was sent to the Recycle Bin and left there, the other was recycled and then emptied. The first is
recovered byte-for-byte (`export recyclebin`) and serves as ground truth for judging the second.

The deletion scan recovers the emptied file's name, the directory whose page holds its row, its timestamps, and
its 7 MB extent map. `export deleted --full` carves those extents: 7,340,032 bytes — the right length. Compared
against the twin:

- **0 of 1,792 clusters match**
- 28,845 of 7,340,032 bytes coincide — 0.4 %, which is chance
- the JPEG signature is gone from the very first cluster

The clusters no longer hold the image: they were reused after the deletion (whether by files still on the volume
was not checked). **The carve returns 7 MB of unrelated data at the correct length**: output that looks plausible
and is wrong. The tool says so:
the export is written with a `.carved` suffix and its manifest states that the data clusters
may have been reused since deletion and must be verified.

**The general rule:**

| the deleted file's data was… | what you get |
|------------------------------|--------------|
| **inline** (small — content inside its own record) | the bytes the row holds, as found, as in Part 1a |
| **extent-backed** (content in its own clusters) | usually the name, the directory and the timestamps; the content only if nothing has reused those clusters since |

Carving a hard-deleted extent-backed file works only while its clusters have not been reused. On a volume
that stayed in service (this one ran for another day), the clusters were reused and the carve failed. Treat the recovered length and file name
as evidence; treat the recovered *bytes* as unverified until you can check them against something
independent, as was done here.

---

## What each answer rests on

| Answer | Where it came from | Independently corroborated by |
|--------|--------------------|-------------------------------|
| Username `bat` | a deleted file whose bytes are inline in its row, read from page free space | on-volume transcripts (user name and profile path); the Recycle Bin shows one ordinary account (`...-1001`) |
| The password | the live file `passphrase.txt` (bytes inline) | — |
| The file was renamed (to conceal it, on our reading) | change journal rename pair, same file reference | file's creation and edit history in the same journal |
| Download provenance of 31 files | `Zone.Identifier` alternate data streams | — |
| Two earlier versions of `secret.txt` | snapshot extent lists, read directly | recovered sizes match the sizes Windows reports; journal write times bracket both snapshots |
| Emptied file's content is unrecoverable | carve compared against a known-good twin | 0 / 1,792 clusters match |

## See also

[Find a deleted file](find_a_deleted_file.md) · [Track a file across moves](track_a_file_across_moves.md) ·
[Detect timestomping](detect_timestomping.md) ·
[Stream snapshots and versioning](../concepts/snapshots_versioning.md) ·
[Record placement and data residency](../concepts/placement_and_residency.md) ·
[Change journal](../structures/usn_journal.md) ·
[forefst command reference](../tools/forefst.md)
