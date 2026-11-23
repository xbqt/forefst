# Enumerate Every Name of One Physical File (a Hard-Link Group)

**Goal:** given a ReFS image, recover the *complete* list of names that point at one
physical file — and prove the reconstruction is correct by decoding the on-disk identity
fields by hand: the link count in the file's backing record gives the number of names, not
the names themselves.

## Setup

Image: `win11refs2gtargeted.raw`, a **native ReFS 3.14** volume of the test corpus, built specifically as hard-link
ground truth (`CHKP` flags `0x682`; its boot-sector flags carry bit 0x20, which refs.sys reads as the volume's
hard-link flag).

`fsutil hardlink list` on the live volume reported:

- `hltest_file1.txt` → **4 names** (`hltest_file1.txt`, `hltest_dir1/link1_to_file1.txt`,
 `hltest_dir1/link3_to_file1.txt`, `hltest_dir2/link2_to_file1.txt`)
- `hltest_file2.txt` → **2 names** (`hltest_file2.txt`, `hltest_dir2/link_to_file2.txt`)
- `survivor.txt` → **1 name** (the lone survivor of a deleted original)

The task is to reproduce that list from metadata alone.

## Steps

### Step 1 — Ask the tool: `files --jsonl`, then read `HardLinkCount` / `HardLinkNames`

The output (one JSON object per directory entry, in the order printed; the rows of the two directories are left
out, and each file row is cut, `[...]`, to the fields used here, of its 42):

```text
$ forefst.py win11refs2gtargeted.raw files --jsonl | grep -i hltest
[...]
{"ObjectRef": "0x600:0x3", "FullPath": "hltest_dir1/link1_to_file1.txt", [...], "RecordPlacement": "split", "DataResidency": "inline", [...], "HardLinkCount": 4, "HardLinkNames": ["hltest_dir1/link1_to_file1.txt", "hltest_dir1/link3_to_file1.txt", "hltest_dir2/link2_to_file1.txt", "hltest_file1.txt"], [...]}
{"ObjectRef": "0x600:0x3", "FullPath": "hltest_dir1/link3_to_file1.txt", [...], "RecordPlacement": "split", "DataResidency": "inline", [...], "HardLinkCount": 4, "HardLinkNames": ["hltest_dir1/link1_to_file1.txt", "hltest_dir1/link3_to_file1.txt", "hltest_dir2/link2_to_file1.txt", "hltest_file1.txt"], [...]}
{"ObjectRef": "0x600:0x5", "FullPath": "hltest_dir1/survivor.txt", [...], "RecordPlacement": "split", "DataResidency": "inline", [...], "HardLinkCount": 1, "HardLinkNames": [], [...]}
[...]
{"ObjectRef": "0x600:0x3", "FullPath": "hltest_dir2/link2_to_file1.txt", [...], "RecordPlacement": "split", "DataResidency": "inline", [...], "HardLinkCount": 4, "HardLinkNames": ["hltest_dir1/link1_to_file1.txt", "hltest_dir1/link3_to_file1.txt", "hltest_dir2/link2_to_file1.txt", "hltest_file1.txt"], [...]}
{"ObjectRef": "0x600:0x4", "FullPath": "hltest_dir2/link_to_file2.txt", [...], "RecordPlacement": "split", "DataResidency": "inline", [...], "HardLinkCount": 2, "HardLinkNames": ["hltest_dir2/link_to_file2.txt", "hltest_file2.txt"], [...]}
{"ObjectRef": "0x600:0x3", "FullPath": "hltest_file1.txt", [...], "FileSize": 36, "Created": "2026-06-14T06:03:20.9010724Z", "Modified": "2026-06-14T06:03:20.9031113Z", [...], "RecordPlacement": "split", "DataResidency": "inline", [...], "HardLinkCount": 4, "HardLinkNames": ["hltest_dir1/link1_to_file1.txt", "hltest_dir1/link3_to_file1.txt", "hltest_dir2/link2_to_file1.txt", "hltest_file1.txt"], [...]}
{"ObjectRef": "0x600:0x4", "FullPath": "hltest_file2.txt", [...], "FileSize": 36, "Created": "2026-06-14T06:03:20.9470439Z", "Modified": "2026-06-14T06:03:20.9470439Z", [...], "RecordPlacement": "split", "DataResidency": "inline", [...], "HardLinkCount": 2, "HardLinkNames": ["hltest_dir2/link_to_file2.txt", "hltest_file2.txt"], [...]}
```

Every one of file1's 4 names carries the *same* `HardLinkCount` 4 and the *same* `HardLinkNames` array — the tool
reports the whole group from any member. file2's two names both read `2`; `survivor.txt` reads `1` with an empty
`HardLinkNames`. This reproduces `fsutil hardlink list` exactly (4 / 2 / 1).

All seven rows' `ObjectRef` begins with `0x600`, their `HomeOID` — the directory they were created in. A file has no
OID of its own: it is identified by its `ObjectRef` (`HomeOID:FileID`), `0x600:0x3` for file1's four names and
`0x600:0x4` for file2's two.

Note what the rows' `"DataResidency": "inline"` beside `"RecordPlacement": "split"` means here.

- Creating a hard link moves the file's *record* out of the name row into a shared backing — that is what lets
  several names resolve to one object.
- It does **not** move the file's *bytes*. On format 3.11 and later a small file's bytes stay inline, in the
  backing, which is exactly what these rows report; on 3.10 and earlier a file's data is always in extents.

Placement and residency are separate properties, so a hard-linked file showing **inline** data *and* a link count
above one is not a contradiction (see [Hard Links](../concepts/hard_links.md) and
[Record placement and data residency](../concepts/placement_and_residency.md)).

### Step 2 — Prove it by hand: decode the value, then resolve the content record

The tool's count is a **join**, not a field read. To see what it joined on, locate one
name's type-0x30 row on disk and decode its 84-byte split-record value. The key for
`hltest_file1.txt` sits at file offset `0x1209d28` (`30 00 02 00` = type 0x30,
key_flags **0x02**, the index-entry layout, followed by the UTF-16LE name); its 16-byte row header at
`0x1209d18` gives `voff=56`, so the value is at `0x1209d50`:

```text
+0x00: 03 00 00 00 00 00 00 00 00 06 00 00 00 00 00 00
+0x10: 24 82 99 80 c3 fb dc 01 c9 d1 99 80 c3 fb dc 01
+0x20: 66 75 7e a9 c3 fb dc 01 c9 d1 99 80 c3 fb dc 01
+0x30: 28 00 00 00 00 00 00 00 24 00 00 00 00 00 00 00
+0x40: 20 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
+0x50: 00 00 00 00
```

Decoded against the index-entry value table in [Directory Entries](../structures/directory_entries.md):

```text
+0x00 child ordinal = 3
+0x08 home-dir backref = 0x600
+0x10 created = 0x01dcfbc380998224 (2026-06-14 06:03:20.901072)
+0x18 modified = 0x01dcfbc38099d1c9 (2026-06-14 06:03:20.903111)
+0x38 file size = 36
+0x40 attributes = 0x00000020 (Archive — directory bit 0x10000000 clear)
```

These fields match the `hltest_file1.txt` JSONL row from Step 1 (its `Created` / `Modified`, `...20.9010724Z` /
`...20.9031113Z`) to the tick, and size = 36 = the JSONL `FileSize`. All four of file1's names carry the *same*
`(ordinal 3, home 0x600)`.

**These two fields are the file's identity.** The file's type-0x40 backing record is keyed by them, and a home
directory holds at most one backing per ordinal, so `(home 0x600, ordinal 3)` names exactly one object.

- The tool resolves each name through that home key `(home, file_id)` and checks that the backing's size equals the
  name's own cached size (`value+0x38` = 36).
- Where a name's cached size is stale, it accepts the backing when the backing's type-0x39 back-pointers list that
  name.
- Here all four names reach the one backing at `(0x600, 3)`. That is what "same physical object" means here.

What the pair does not allow is a lookup in the name's *own* directory: the ordinal is per directory, so a link's
directory can hold a different file under the same ordinal (on the synthetic generator volumes a link's own
directory even holds a type-0x40 row at that ordinal with alloc 0). That is why the tool goes through the home key
(see [Hard Links](../concepts/hard_links.md)).

One caveat about those `+0x10..+0x28` FILETIMEs. On NTFS every hard link shares one `$STANDARD_INFORMATION` (each
link's `$FILE_NAME` has its own times). ReFS keeps one set of times in the file's own record, the backing, and each
name's type-0x30 row holds a cached copy of them — Created / Modified / Changed / Accessed — refreshed for the name
that was opened.

Here the four names of file1 agree on Created, Modified and Accessed but **not on Changed** (`+0x20`; this row's
`0x01dcfbc3a97e7566` is 06:04:29.5103846): each link's Changed is the moment it was added — the change journal's own
HARD_LINK_CHANGE time for it — and `hltest_file1.txt`'s equals the last link's. A Changed-only difference is
routine, not a stomp; a difference in **Created** is what to follow. See Step 2b.

### Step 2b — Compare the names' Created to catch a per-name timestomp

Because each name caches its own copy of Created, the group's names *can* disagree (NTFS's hard links share one
`$SI`; each NTFS link has its own `$FILE_NAME`, with its own times).

When their `value+0x10` FILETIMEs differ, that is evidence to follow up:

- no routine cause of a Created difference has been observed (on the volumes whose journal was read, every file
  whose names disagree on Created and that the journal holds carries a basic-information change);
- it is **journal-independent**: it holds even when `$UsnJrnl:$J` has wrapped or is absent.

`forefst`'s `timestomp` check emits a `HARDLINK_MACB_MISMATCH` signal on such a group.

**A difference is a lead, and an agreement proves nothing.** A lab measurement built a two-name file and called `SetFileTime`
on one path: afterwards both name rows were byte-identical across their whole 84-byte value, because the lab's
inventory pass had then opened both names.

- The file's own record takes the new time for every name at once; each name's row is a cache of it that the driver
  refreshes when the file is opened, read and closed through *that* name (a directory listing alone does not refresh
  it).
- So **names that agree tell you nothing** — agreement is what a stomp leaves behind once every name has been read,
  and also what an untouched file looks like.
- And the stale name is the one nobody opened, which is not the same as the one nobody forged: *which* name holds
  the true birth is not established.

Treat a mismatch as a lead to follow up, not as a conclusion. The next read through the stale name erases it.

### Step 3 — Confirm the two files resolve to different content records

Decode `hltest_file2.txt`'s index-entry value the same way (key at `0x1209f80`, value via
its row header):

```text
+0x00 child ordinal = 4
+0x08 home-dir backref = 0x600
+0x10 created = 2026-06-14 06:03:20.947043
+0x18 modified = 2026-06-14 06:03:20.947043
+0x38 file size = 36
```

file2 shares `home = 0x600` with file1 — both were created in the volume root — but its **ordinal is 4, not 3**,
and its create/modify times differ.

This is exactly why the home backref *alone* is insufficient: grouping by `home=0x600` would wrongly merge file1,
file2 and survivor into one group of 7 names. Resolving each name through its home key keeps file1's backing
`(0x600, 3)` and file2's `(0x600, 4)` apart. The two files have the same size (36 bytes), so here it is the
ordinal, under the shared home, that separates them; the size only confirms each match. See
[Hard Links](../concepts/hard_links.md).

### Step 4 — Why the name row's `$SI+0x70` ("HardLinkCount") is not the count

A shortcut that fails: reading the field the layout names *HardLinkCount* at `$SI+0x70` in a name row.

- In a name row that holds the file's record (an embedded record, key_flags 0x01) it reads **1** on every such row
  measured — 329,120 of 329,120 rows over 141 image paths — because a file with several names does not keep its
  record there.
- These hard-linked names use the index-entry layout (key_flags 0x02): their 84-byte value has no `$SI+0x70` field.

The count is in the file's own record, its split-out type-0x40 backing: the driver keeps it in the file's FCB and
writes it at `$SI+0x70` on every change of the file's names (`RefsConvertToStandardInfoLinkCount`). On this volume
the three backings read **4 / 2 / 1**, as `fsutil` counts them; over 107,525 backings on 78 images it equals the
number of size-matched names on 99.84 %.

It gives the number of names, not the names: those come from the join of Step 1. A parser that reads the name row's
copy reports "no hard links" on a volume that has them.

## What this tells you

- **`files --jsonl` gives the whole group from any member.** `HardLinkCount` and the
 `HardLinkNames` array on any one of file1's four entries list all four names; the count
 reproduces `fsutil hardlink list` (4 / 2 / 1); checked against each name's own size over the corpus, the
 grouping shows **0 over-merge across 110+ images**.
- **The tool's count is a join on the file's backing record**, not a read of the backing's own counter
 (`$SI+0x70`) and not a metadata tuple: the tool resolves each name through its home key `(home, file_id)`,
 accepts the backing when its size equals the name's (`value+0x38`), or when its back-pointers list a name whose
 cached size is stale, and groups the names of each backing.
- **The decoded bytes match the tool output exactly** — ordinal 3 / home 0x600 / size 36 /
 the two FILETIMEs for file1 — so every step of the reconstruction can be
 checked.
- **`value+0x08` (home-dir backref = 0x600) records where the file was created:** it records the directory the
 file was *first created in* (here the volume root), and survives even after the file is
 hard-linked into `hltest_dir1` / `hltest_dir2` — a fact a live `dir` listing never shows.
- **Read `$SI+0x70` from the backing, not the name row.** In an embedded record it reads 1; a
 hard-linked file's record is split out into its backing, and the backing's `$SI+0x70` is
 the number of its names.
- Hard links need the volume's **hard-link flag**, boot-sector flags bit 0x20 (refs.sys reads it at mount). On the
 corpus it is set on every volume formatted at 3.7 or later but one (whose boot sector `refsutil fixboot`
 rewrote), and clear on 3.4 volumes and on those upgraded from 3.4. A multi-name split group on a volume without the
 bit would be anomalous ([Hard Links](../concepts/hard_links.md)).

## See also

- [Hard Links](../concepts/hard_links.md) — how a file's names are joined to one object, where `$SI+0x70` holds the
  count, and the hard-link flag
- [Directory Entries](../structures/directory_entries.md) — the type-0x30 key and the index-entry value layout decoded in Step 2
- [Standard Information](../attributes/STANDARD_INFORMATION.md) — the `$SI+0x70` "HardLinkCount" field and the `$SI+0x58` NextFileId ordinal source
- [Record placement and data residency](../concepts/placement_and_residency.md) — why hard-linking splits the record out of the name row, and why the data does not move
- [Object Table](../structures/object_table.md) — resolving the `value+0x08` home backref OID
- Master reference: `structure_reference.md` §J (Hard Links), §C.3 (index-entry value), §C.7 (`$SI+0x70`)
