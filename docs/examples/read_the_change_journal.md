# Read How Far the Change Journal Reaches

**Goal:** know how far back a volume's change journal reaches, whether it has wrapped or was re-created, and how the
checkpoint records where it stood.

## Setup

Two images of the test corpus, both native ReFS 3.14:
- `winsider.raw`, the Windows Server Insider system drive, whose 32 MiB journal has wrapped;
- `labG_0.raw`, a lab volume whose journal was re-created.

A record's USN is its byte offset in the journal's stream as if the stream never wrapped. The journal itself is a ring:
new records overwrite the oldest ones in place ([USN Journal](../structures/usn_journal.md)). The checkpoint also keeps
where the journal stood when it was written ([Checkpoint](../structures/chkp.md#the-change-journal-cursor-at-0x88)).

## Step 1: the window of a wrapped journal

```text
$ forefst.py winsider.raw usn --info
[...]
    Max journal:    33554432 bytes (32 MiB)
[...]
  Parsed records:
    Count:          217892
    Versions:       3.0
    USN range:      40906752 — 74459840

  The checkpoint's journal cursor (the checkpoint copy in use, its area at +0x88):
    Next USN:       74459968  (0 records at or past it: written after this checkpoint)
    First USN:      40906752  (the journal has wrapped: wrap base 67108864, ring 32 MiB)
```

The oldest record still held is USN 40,906,752. Every record below it was overwritten, so the journal holds no
change older than that record.

The checkpoint's cursor says the same: its first USN is that record, and its next USN, 74,459,968, is where the last
record (74,459,840, 128 bytes long) ends. Nothing was written after this checkpoint.

## Step 2: when the window starts

```text
$ forefst.py winsider.raw usn --csv | head -2 | cut -d, -f1-4
USN,Timestamp,Reason,ReasonHex
40906752,2026-05-11T20:34:50.2578082Z,FILE_CREATE,0x100
```

The oldest record dates the start of the window. On this system drive the journal was created at 2026-05-11T20:33:59
(`usn --info`, the Change Journal entry's `Created`). Within the first minute, Windows wrote more than the ring holds,
so this journal tells nothing of those first 51 seconds.

## Step 3: a re-created journal

```text
$ forefst.py labG_0.raw usn --info
[...]
    USN range:      0 — 4439864
    Journal instances: the journal's numbering restarted at USN 0 at 2026-09-20T06:53:53.1627748Z,
                       its first record, with a new id, 0x01dd48cccc6edb06.
                       USN 0 to 11904 belong to the current journal; USN 12288 to 4439864 belong to
                       an earlier instance: from USN 12288 up every record is older than every
                       record below it.
[...]
  The checkpoint's journal cursor (the checkpoint copy in use, its area at +0x88):
    Next USN:       12016  (0 records of the current journal at or past it: written after this checkpoint)
                    (the records of an earlier journal instance, above, are not compared)
    First USN:      0  (0 with the wrap base and size: the journal has not wrapped)
```

Here the journal was re-created: a new instance numbers its records from USN 0 again. Its records overwrote the start
of the ring, and above them lie the earlier instance's records, older than every record below them.

The checkpoint's cursor belongs to the current journal: its last record (USN 11,904) ends at 12,016, the cursor's next
USN. The earlier instance's records carry higher USNs, but they are not newer, and the cursor says nothing about them.
On every corpus volume whose checkpoint carries the cursor, no record of the current journal lies past it.

## What to take from it

- The oldest record bounds what the journal can tell you; `usn --info` gives it, and the cursor confirms it.
- After a re-creation, a higher USN is not a newer record: compare USNs only within one journal instance, as
  `usn --info` separates them.
- When the checkpoint copy carries no cursor (on the corpus, three volumes captured mounted or rebuilt), `usn --info`
  says so.

## Cross-references

- [USN Journal](../structures/usn_journal.md): the record layout, the ring, how a record reaches the disk.
- [Checkpoint](../structures/chkp.md#the-change-journal-cursor-at-0x88): the cursor's four fields.
- [Follow the history](follow_the_history.md): the journal and the MLog in a first examination.
