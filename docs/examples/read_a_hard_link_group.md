# Worked Example: Enumerate Every Name of One Physical File (a Hard-Link Group)

**Goal:** given a ReFS image, recover the *complete* list of names that point at one
physical file — and prove the reconstruction is correct by decoding the on-disk identity
fields by hand, because ReFS stores **no explicit hard-link count anywhere**.

## Setup

Image: a native ReFS 3.14 image (referred to below as `$IMG`).
A **native ReFS 3.14** volume (`CHKP` flags `0x682`, the only state that supports hard
links) built specifically as hard-link ground truth. `fsutil hardlink list` on the live
volume reported:

- `hltest_file1.txt` → **4 names** (`hltest_file1.txt`, `hltest_dir1/link1_to_file1.txt`,
 `hltest_dir1/link3_to_file1.txt`, `hltest_dir2/link2_to_file1.txt`)
- `hltest_file2.txt` → **2 names** (`hltest_file2.txt`, `hltest_dir2/link_to_file2.txt`)
- `survivor.txt` → **1 name** (the lone survivor of a deleted original)

The whole job is to reproduce that list from metadata alone.

```sh
IMG=your_v3.14_image.raw
```

## Steps

### Step 1 — Ask the tool: `forefst --jsonl`, then read `hard_link_count` / `hard_link_names`

```sh
python3 forefst.py "$IMG" --jsonl -q | grep -i hltest
```

Relevant fields from the real output (one JSON object per directory entry; trimmed to the
hard-link fields):

```
file_name "hltest_file1.txt" hard_link_count 4 hard_link_names [
 "hltest_dir1/link1_to_file1.txt", "hltest_dir1/link3_to_file1.txt",
 "hltest_dir2/link2_to_file1.txt", "hltest_file1.txt" ]
file_name "hltest_dir1/link1_to_file1.txt" hard_link_count 4 (same 4 names)
file_name "hltest_dir1/link3_to_file1.txt" hard_link_count 4 (same 4 names)
file_name "hltest_dir2/link2_to_file1.txt" hard_link_count 4 (same 4 names)

file_name "hltest_file2.txt" hard_link_count 2 hard_link_names [
 "hltest_dir2/link_to_file2.txt", "hltest_file2.txt" ]
file_name "hltest_dir2/link_to_file2.txt" hard_link_count 2 (same 2 names)

file_name "survivor.txt" hard_link_count 1 hard_link_names null
```

Every one of file1's 4 names carries the *same* `hard_link_count: 4` and the *same*
`hard_link_names` array — the tool reports the whole group from any member. file2's two
names both read `2`; `survivor.txt` reads `1` with `hard_link_names: null`. This reproduces
`fsutil hardlink list` exactly (4 / 2 / 1). Note all seven rows share `"home_oid": "0x600"` (their `"oid"` is `null`) and
`"is_resident": false` — hard-linking promotes a file out of resident storage, so they have
no own OID and live as non-resident type-0x30 entries (per
[Hard Links](../concepts/hard_links.md) and [Resident Storage](../concepts/resident_storage.md)).

### Step 2 — Prove it by hand: decode the value, then resolve the content record

The tool's count is a **join**, not a field read. To see what it joined on, locate one
name's type-0x30 row on disk and decode its 84-byte non-resident value. The key for
`hltest_file1.txt` sits at file offset `0x1209d28` (`30 00 02 00` = type 0x30,
key_flags **0x02** non-resident, followed by the UTF-16LE name); its 16-byte row header at
`0x1209d18` gives `voff=56`, so the value is at `0x1209d50`:

```
+0x00: 03 00 00 00 00 00 00 00 00 06 00 00 00 00 00 00
+0x10: 24 82 99 80 c3 fb dc 01 c9 d1 99 80 c3 fb dc 01
+0x20: 66 75 7e a9 c3 fb dc 01 c9 d1 99 80 c3 fb dc 01
+0x30: 28 00 00 00 00 00 00 00 24 00 00 00 00 00 00 00
+0x40: 20 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
+0x50: 00 00 00 00
```

Decoded against the non-resident value layout
([Directory Entries](../structures/directory_entries.md), C.3):

```
+0x00 child ordinal = 3
+0x08 home-dir backref = 0x600
+0x10 created = 0x01dcfbc380998224 (2026-06-14 06:03:20.901072)
+0x18 modified = 0x01dcfbc38099d1c9 (2026-06-14 06:03:20.903111)
+0x38 file size = 36
+0x40 attributes = 0x00000020 (Archive — directory bit 0x10000000 clear)
```

These fields match the `hltest_file1.txt` JSONL row from Step 1 (`...20.9010724` /
`...20.9031113`) to the tick, and size = 36 = the JSONL `file_size`. All four of file1's names
carry the *same* `(ordinal 3, home 0x600)`. **But the real identity is the file's type-0x40
stream, not these metadata fields:** the tool resolves each name to the candidate stream —
local `(parent, file_id)` or home `(home, file_id)` — whose 0x40 size **equals the name's own
size** (`value+0x38` = 36). Here all four reach the one stream at `(0x600, 3)` (size 36, via the
home backref since these fsutil links have no local record). *That* is "same physical object."
On these fsutil links the metadata happens to coincide, but it is **not** the general rule: on
other images a hard link carries an `alloc=0` stub in its own dir, and the
per-directory ordinal collides between distinct files, so the **size match** is what reliably
identifies the shared physical stream (see [Hard Links](../concepts/hard_links.md)).

One caveat about those `+0x10..+0x28` FILETIMEs: unlike NTFS — where every hard link shares
one `$STANDARD_INFORMATION` and the four MACB timestamps cannot diverge — ReFS carries **one
`$SI` timestamp set per name**. Each name's type-0x30 row holds its own Created / Modified /
Changed / Accessed, so the four names of file1 read identically here only because they were
created together and never touched individually. A name-scoped `SetFileTime` (open **one**
path, set `CreationTimeUtc`) rewrites only that name's row (and the shared type-0x40 backing);
the sibling names keep their original values. See Step 2b.

### Step 2b — Compare the names' Created to catch a per-name timestomp

Because each name carries its own Created, comparing the group's names is a ReFS-specific
tamper check. If one name's Created were backdated while its siblings kept the true birth,
their `value+0x10` FILETIMEs would no longer agree — and the **latest** Created across the
siblings is the authentic birth (a name can be pushed back, not forward past creation). For a
**single-named** file there is no sibling to compare against, so this cross-check simply does
not apply; but a **hard-linked** file exposes the discrepancy directly on disk. This is
**journal-independent** (it holds even when `$UsnJrnl:$J` has wrapped or is absent) and is
**stronger** than NTFS's `$SI`-vs-`$FN`, where all hard links share one `$SI` and cannot
diverge at all. `forefst`'s `timestomp` check emits a `HARDLINK_MACB_MISMATCH` signal on the
backdated name and never on the clean sibling.

### Step 3 — Confirm the two files resolve to different content records

Decode `hltest_file2.txt`'s non-resident value the same way (key at `0x1209f80`, value via
its row header):

```
+0x00 child ordinal = 4
+0x08 home-dir backref = 0x600
+0x10 created = 2026-06-14 06:03:20.947043
+0x18 modified = 2026-06-14 06:03:20.947043
+0x38 file size = 36
```

file2 shares `home = 0x600` with file1 — both were created in the volume root — but its
**ordinal is 4, not 3**, and its create/modify times differ. This is exactly why the home
backref *alone* is insufficient: grouping by `home=0x600` would wrongly fuse file1, file2
and survivor into one 7-member blob. Resolving each name to the
**size-matched type-0x40 stream** `(owner-dir, file_id)` (here via the home backref, since
these fsutil links have no local record) keeps file1's stream and file2's stream apart — the
size-matched stream `(owner, file_id)` is the identity here, not the coinciding ordinal/fingerprint. See
[Hard Links](../concepts/hard_links.md) (size-matched resolution; on other images a colliding
ordinal can point at a different file, which the size match correctly separates).

### Step 4 — Why you must NOT read `$SI+0x70` ("HardLinkCount")

Tempting shortcut: read the field literally named *HardLinkCount* at `$SI+0x70`. It is a
trap. `$SI+0x70` is a **resident-layout** field (offset within the key_flags 0x01 value),
and these hard-linked files are **non-resident** (key_flags 0x02) — they have no `$SI+0x70`
at all. Where it *does* exist, the driver writes it from a per-FCB scalar
(`RefsComputeStandardInformationFromFcb` copies `$SI+0x70 <- FCB+0xB4`), so it reads **1**
for every object — even on this very image, the one corpus volume that actually contains
hard links. Across 525,165 dir entries / 111 images it was `> 1` in **zero** cases. Reading
it would report "no hard links" on a volume that demonstrably has them.

## What this tells you

- **`forefst --jsonl` gives the whole group from any member.** `hard_link_count` and the
 `hard_link_names` array on any one of file1's four entries list all four names; the count
 reproduces `fsutil hardlink list` (4 / 2 / 1); independent all-disk validation is **0 over-merge
 across 110+ images**.
- **The count is a derived join on the physical stream record**, not an on-disk counter and
 not a metadata tuple: the tool resolves each name to the type-0x40 stream — local
 `(parent, file_id)` or home `(home, file_id)` — whose 0x40 size **equals the name's own size**
 (`value+0x38`), and groups names sharing that stream's `(owner, file_id)`. The tool resolves each name to the type-0x40 stream whose 0x40 size **equals the name's own
 size**, because on other images distinct files collide on the per-directory ordinal and only the
 **size match** separates them.
- **The decoded bytes match the tool output exactly** — ordinal 3 / home 0x600 / size 36 /
 the two FILETIMEs for file1 — so the reconstruction is verifiable end-to-end, not a
 black box.
- **`value+0x08` (home-dir backref = 0x600) is provenance:** it records the directory the
 file was *first created in* (here the volume root), and survives even after the file is
 hard-linked into `hltest_dir1` / `hltest_dir2` — a fact a live `dir` listing never shows.
- **Never trust `$SI+0x70`.** It is a resident-only decoy that is always 1; hard-linked
 files are non-resident and do not even carry it.
- Hard links are a **native v3.14 signal** (this volume's `CHKP` flags = `0x682`). A
 multi-name non-resident group on a v3.4 or *upgraded* volume would be anomalous.

## See also

- [Hard Links](../concepts/hard_links.md) — the identity-tuple join, the `$SI+0x70` decoy, and the v3.14 gating
- [Directory Entries](../structures/directory_entries.md) — the type-0x30 key + the C.3 non-resident value layout decoded in Step 2
- [Standard Information](../attributes/STANDARD_INFORMATION.md) — the `$SI+0x70` "HardLinkCount" field and the `$SI+0x58` NextFileId ordinal source
- [Resident Storage](../concepts/resident_storage.md) — why hard-linking forces promotion to non-resident
- [Object Table](../structures/object_table.md) — resolving the `value+0x08` home backref OID
- Master reference: `structure_reference.md` §J (Hard Links), §C.3 (non-resident value), §C.7 (`$SI+0x70`)
