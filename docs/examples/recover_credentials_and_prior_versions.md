# Worked Example: Recover Credentials, Alternate Streams and Earlier File Versions

**Goal:** one volume, three questions an investigator actually asks — *where are the credentials, including
the ones someone tried to hide?*, *what is in the alternate data streams?*, and *what did this file say
**before** it was edited?* — followed, honestly, by the question this volume would **not** answer.

Every command below is real, and every output is what the tool printed. Where an answer can be checked
against something the volume itself recorded, it is checked.

## Setup

A 3.9 GB native **ReFS 3.14** volume (4 KB clusters, CRC64 metadata checksums) imaged from a Windows 11 test
machine. It was used normally for a day: files downloaded, edited, renamed, deleted three different ways, and
snapshotted.

```sh
IMG=disk.raw
python3 forefst.py "$IMG" summary
```

```
  ReFS version:       3.14
  Volume label:       data
  Cluster size:       0x1000 (4.0 KB)
  Checksum:           CRC64
  Volume state:       NATIVE v3.14
  Volume created:     2026-09-01 09:32:39.5748217
  Space used:         2.4 GB of 3.9 GB (61.6%) — 1.5 GB free
```

Native v3.14, never upgraded, and the journal is intact — so the volume's own record of what happened is
available to corroborate everything that follows.

---

## Part 1 — Find the credentials

### 1a. The deleted file — recovered exactly, not carved

Start with the deletion scan, which reads the free space inside metadata pages:

```sh
python3 forefst.py "$IMG" deleted
```

```
    FILE username.txt  (resident, live-slack @ cluster 3596 off 0xa10)
      Deleted from: /tests  (table 0x703)
      Created:  2026-09-01 10:36:44 UTC
      Modified: 2026-09-01 10:36:44 UTC
      Recoverable: FULL FILE recoverable (resident — 40 B stored inline in the record)
```

**`FULL FILE recoverable` is a strong claim, and here it is literal.** A small file's bytes are stored
*inside* its own directory record rather than in separate clusters. Deleting the file removes the row's entry
from the page's index, but the row body — including those bytes — stays in the page until something
overwrites it. So the content is read back, not reconstructed:

```sh
python3 forefst.py "$IMG" export deleted ./out
cat ./out/content/username.txt
```

```
username:bat
password:in the other file
```

```
  20 deleted entries indexed → ./out/deleted_files.csv  (+ .json)
    Content recovered: 14 resident (exact) + 0 non-resident carved = 14 files → ./out/content/
```

We have the **username: `bat`** — and a pointer to a second file.

### 1b. "The other file" — the name was changed to hide it

Nothing on the volume is called `password`. Search for the obvious alternative:

```sh
python3 forefst.py "$IMG" search passphrase
```

```
OID          Parent       Type          Size  Res  Modified             Path
───────────  ───────────  ────  ──────────── ────  ───────────────────  ──────────────────────
(resident)   0x703        File         104 B  Yes  2026-09-01 10:39:30  tests/passphrase.txt
```

```sh
python3 forefst.py "$IMG" extract /tests/passphrase.txt
```

```
password:Des scorpions culpabiliseront dans mon salon.

** Generated with https://xbpt.gitlab.io/pp/
```

**The password is recovered — but the file name is not the one it was written under.** The change journal
records renames as a pair of entries, and both carry the same file reference, which is what proves they are
one object rather than two files that happen to look alike:

```sh
python3 forefst.py "$IMG" usn --csv | grep RENAME
```

```
66904,2026-09-01T10:40:11.224Z,0x00001000,RENAME_OLD_NAME,generatepasswordfromxbptgitlabiopp.txt,file,0x703:0x2b,…
67056,2026-09-01T10:40:11.224Z,0x00002000,RENAME_NEW_NAME,passphrase.txt,                        file,0x703:0x2b,…
```

The original name — `generatepasswordfromxbptgitlabiopp.txt` — states the file's purpose *and* names the
generator it came from, and it survived only in the journal. The full journal entry sequence for that same
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

Three independent places on the volume agree:

```sh
python3 forefst.py "$IMG" recyclebin
```

```
  $IY0YDJS.txt   (SID S-1-5-21-1473886876-2352682097-2257922272-1001)
    Original path:  R:\tests\bigtextfiledeleted.txt
    Deleted:        2026-09-01 10:50:39.0020000
```

The Recycle Bin is organised into one folder per user security identifier, and `-1001` is the first ordinary
(non-built-in) account created on the machine. A PowerShell transcript that was saved onto this volume names
it outright:

```sh
python3 forefst.py "$IMG" extract /logs/transcript2.txt | head -6
```

```
Windows PowerShell transcript start
Start time: 20260901132501
Username: malw\bat
RunAs User: malw\bat
Machine: MALW (Microsoft Windows NT 10.0.26200.0)
```

**`malw\bat`** — matching the `username:bat` recovered from the deleted file, and matching the profile path
`C:\Users\bat` that appears elsewhere on the volume. Three sources, one answer.

---

## Part 2 — Find the alternate data streams, in one command

Alternate data streams are a classic hiding place, and on ReFS they need no scan — they are rows in each
file's own attribute set, so listing them is a single tree walk:

```sh
python3 forefst.py "$IMG" ads
```

```
── ads  (28) — named data streams ──
  STREAMS                      HOST FILE
    Zone.Identifier            tests/100pagesword.docx
    Zone.Identifier            tests/15MB-Corrupt-Testfile.Org.zip
    Zone.Identifier            tests/alpha-shapes.png
    …
    Zone.Identifier            tests/zip1mb.zip
```

**Nothing was hidden in a stream on this volume — and that is itself a result worth stating.** All 28 are
`Zone.Identifier`, the stream Windows attaches to a downloaded file. They are not a hiding place here; they
are provenance, and they answer a different question: *where did these files come from?*

```sh
python3 forefst.py "$IMG" export ads "tests/Get-ZimmermanTools.zip:Zone.Identifier"
```

```
[ZoneTransfer]
ZoneId=3
ReferrerUrl=https://ericzimmerman.github.io/
HostUrl=https://download.ericzimmermanstools.com/Get-ZimmermanTools.zip
```

`ZoneId=3` means the file came from the internet, and the two URLs give the page the user was on and the
address the bytes actually came from. Repeating that for all 28 reconstructs the download history of the
volume. To pull the stream names into a spreadsheet alongside everything else, `files --csv` carries them in
its `HasADS` and `ADSNames` columns.

---

## Part 3 — Read what a file said before it was edited

One file on this volume reports snapshots:

```sh
python3 forefst.py "$IMG" snapshots --show
```

```
  Files with snapshots: 1
  Total snapshots:      2

  FILE tests/secret.txt
    Created:      2026-09-01 10:40:23 UTC
    Modified:     2026-09-01 10:44:32 UTC
    Snapshots:    2

    [1] "too important to lose"
        Stream size:   58 bytes
    [2] "backup 2"
        Stream size:   79 bytes

    Recovered content (2 version(s)):
      [too important to lose] sub_id=0x1001 size=58 -> 58 bytes, 1 extent(s)
          "i don't understand anything to refs, it's too complicated!"
      [backup 2] sub_id=0x1002 size=79 -> 79 bytes, 1 extent(s)
          "i don't understand anything to refs, it's too complicated!\r\ni can't say that..."
```

Now compare that with the file as it stands today:

```sh
python3 forefst.py "$IMG" extract /tests/secret.txt
```

```
no, i can't say that...
```

**25 bytes live; 79 bytes in the most recent snapshot.** The current file is a truncated version of itself,
and the text that was removed is still on the volume. The journal dates every step of it, and the snapshot
sizes fall exactly between the writes:

| time (UTC) | event | resulting size |
|------------|-------|----------------|
| 10:40:23 | `FILE_CREATE` | 0 |
| 10:41:39 | `DATA_EXTEND` | 58 |
| **10:43:04** | **snapshot `"too important to lose"` taken** | **58 captured** |
| 10:43:57 | `DATA_OVERWRITE\|DATA_EXTEND` | 79 |
| **10:44:10** | **snapshot `"backup 2"` taken** | **79 captured** |
| 10:44:32 | `DATA_OVERWRITE\|DATA_TRUNCATION` | 25 |

The last write destroyed 54 bytes of the live stream. Both earlier versions survive because taking a snapshot
switches the file to **copy-on-write**: from that moment, writing a block does not overwrite it but allocates
a new one, leaving the snapshot pointing at the original. The current stream owns only the blocks written
since the last snapshot; everything else is shared with the versions before it.

**This is reading, not reconstruction.** The earlier bytes are on the volume, at the addresses the snapshot's
own extent list gives; nothing is rebuilt, guessed, or assembled from fragments. Both recovered sizes — 58
and 79 — are exactly the sizes Windows itself reports for those snapshots.

> **`extract` and `snapshots --extract` are not the same command.**
> `extract` gives you the file's **current** stream — the 25 bytes above.
> `snapshots --extract` gives you a **named earlier version** — the 58- or 79-byte one.
> A file can have both, and on this volume the interesting content is only in the second.

---

## Part 4 — What this volume did *not* give up

The same volume holds a file that was deleted from the Recycle Bin — emptied, not merely sent there. Its
metadata came back; **its content did not.** This section is here because that is the result we got, and it
is the honest one.

`jpgharddeleted.jpg` is a clean experiment, because the operator made **two copies of the same 7 MB image**:
one was sent to the Recycle Bin and left there, the other was recycled and then emptied. The first is
recovered byte-for-byte and serves as ground truth for judging the second.

The deletion scan recovers the emptied file's name, its parent directory, its timestamps, and its full 7 MB
extent map. Reading those extents produces 7,340,032 bytes — the right length. Compared against the twin:

- **0 of 1,792 clusters match**
- 28,845 of 7,340,032 bytes coincide — 0.4 %, which is chance
- the JPEG signature is gone from the very first cluster

The clusters were reallocated to other files after the deletion. **The carve returns 7 MB of unrelated data
at the correct length** — plausible-looking output that is entirely wrong. The tool does not claim otherwise:
the export is written with a `.carved` suffix and its manifest states the contract, that the data clusters
may have been reused since deletion and must be verified.

**Take this as the rule, not the exception:**

| the deleted file was… | what you get |
|------------------------|--------------|
| **resident** (small — content inside its own record) | the **exact bytes**, as in Part 1a |
| **non-resident** (content in its own clusters) | the name, parent and timestamps reliably; the content only if nothing has reused those clusters since |

Carving a hard-deleted non-resident file is a bet on the volume not having been used since. On a volume that
stayed in service — this one ran for another day — that bet loses. Treat the recovered length and file name
as evidence; treat the recovered *bytes* as unverified until you can check them against something
independent, as was done here.

---

## What each answer rests on

| Answer | Where it came from | Independently corroborated by |
|--------|--------------------|-------------------------------|
| Username `bat` | deleted resident file, read from page free space | Recycle Bin account identifier; on-volume transcript; profile path |
| The password | live resident file `passphrase.txt` | — |
| The file was renamed to conceal it | change journal rename pair, same file reference | file's creation and edit history in the same journal |
| Download provenance of 28 files | `Zone.Identifier` alternate data streams | — |
| Two earlier versions of `secret.txt` | snapshot extent lists, read directly | recovered sizes match the sizes Windows reports; journal write times bracket both snapshots |
| Emptied file's content is unrecoverable | carve compared against a known-good twin | 0 / 1,792 clusters match |

## See also

[Find a deleted file](find_a_deleted_file.md) · [Track a file across moves](track_a_file_across_moves.md) ·
[Detect timestomping](detect_timestomping.md) ·
[Stream snapshots and versioning](../concepts/snapshots_versioning.md) ·
[Resident storage](../concepts/resident_storage.md) ·
[Change journal](../structures/usn_journal.md) ·
[forefst command reference](../tools/forefst.md)
