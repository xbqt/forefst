# Hard Links

> A hard link splits the file's **record** out of the name row and moves **no data**: its bytes stay wherever they were, inline or in extents. The two properties are explained on [Record placement and data residency](placement_and_residency.md).

A hard link is a second (or third, ...) directory name that points at one physical file. On ReFS
**the link count of a file with several names is only in its type-0x40 backing record**: its name rows are
[index entries](../structures/directory_entries.md#index-entry-value-key_flags--0x02), which hold times, sizes and
attributes but no link count.

The field at [`$SI`](../attributes/STANDARD_INFORMATION.md) offset 0x70, which these pages call
"HardLinkCount", behaves differently in the two record forms:

* In an **embedded** record (`key_flags` 0x01) it always reads **1**, on every embedded row measured. A file with
  several names does not keep its count here.
* In a **type-0x40 backing** — the split-out record that carries the file's own `$SI` — it **is** the
  count. Over the backings measured it reads greater than 1 on **most of them (about 94 %)**, and it equals
  the number of size-matched names for that `(home, file_id, size)` on **nearly every one (more than 99.8 %)**.
  On a lab volume where this project holds `fsutil hardlink` ground truth of **4 / 2 / 1**, the three backings
  read **4 / 2 / 1**.

So the counter exists on disk, and it is trustworthy on backings. It gives the number of names, not the names:

* in an embedded record it reads 1, whatever the file;
* on the few residual backings (under 0.2 %) it reads 2 while only one name matches the backing's size: a name's
  cached size can be stale, so check the backing's back-pointers before calling the second name lost;
* which names share the file is read from the backing's type-0x39 back-pointers, or reconstructed by joining
  directory entries ([below](#the-authoritative-name-list-lives-in-the-backing)). The join also shows what a
  live directory listing does not: the directory a file was *first created in*.

## Per-name timestamps: why they differ, and what erases the difference

A file's names can disagree on their timestamps; a disagreement on Created is the
[`HARDLINK_MACB_MISMATCH`](timestomp_detection.md) signal. Two layers explain it, and they refresh at
different times:

* The **file's own record** takes a new timestamp **immediately** — a `SetFileTime` through one name
  updates every name at once, because the file has one set of times.
* Each **name's index entry** is a **lazily refreshed cache** of those times. refs.sys refreshes only the
  entry of the name a handle was **opened** through: when that handle sets the basic information, the
  allocation or the end of file (`RefsUpdateFileDupInfo`), and on its close path (`RefsCommonCleanup` →
  `RefsUpdateDuplicateInfo`); the other names stay stale until each of them is opened.

Three consequences for an examiner:

1. **A divergence of the names' Created times is evidence.** On the volumes measured, every file whose names
   disagree on Created and whose change journal still holds records of it carries a recorded basic-information
   change. **Their Changed times diverge routinely**, with no stomp: a name added as a hard link carries the time it
   was added, and a name refreshed later carries a later one, so a difference in Changed alone is not a sign
   of a stomp.
2. **Agreement proves nothing**: either the names never diverged, or they diverged and something has
   since opened the file through the other name.
3. **A read erases the difference.** An open of the file through that name refreshes the name's entry: an antivirus scan,
   a search indexer, an inventory pass, a `Get-FileHash` sweep. A directory listing alone does not: on a lab
   volume (Windows 11 24H2), two `dir` listings of the stale name left its times stale on disk, and the listing
   itself printed the name's stale size; an open, a 1-byte read and a close through that name then refreshed it.

Measured on a controlled pair differing by exactly one recorded action (`read-sibling-name-ONLY`): before, the names
are flagged HIGH with the mismatch and the unread sibling still shows the **pre-stomp** birth; after **merely
reading** the sibling, the mismatch is gone and the sibling is not flagged at all.

Which name holds the authentic birth is still **not** established — the mechanism says which entry was
refreshed last, not which timestamp is true.

**Image before anything touches the volume.**

## Where ReFS keeps the link count

In NTFS the MFT record for a file carries an explicit hard-link count and every name is a `$FILE_NAME`
attribute hanging off that one record.

ReFS has no MFT: a file is a set of B+-tree rows, and each *name* is an independent row
([directory entry](../structures/directory_entries.md), type 0x30) in its own parent directory's tree. There is
no name row to hang a shared count on, so ReFS keeps it in the file's own record.

The driver holds the count in the file's FCB and writes it at `$SI+0x70` on every change of the file's names
(`RefsConvertToStandardInfoLinkCount`, called when a name is added or removed and on a rename). A file with one
name keeps its record in its name row and reads 1 there; once it has a second name its record is split out into a
type-0x40 backing, and that backing carries the count.

## What hard-linking does on disk

Linking a file performs three changes to its name rows (it also adds a type-0x39 back-pointer to the file's
record and raises the count at `$SI+0x70`, both described on this page):

1. **It splits the object's record out of the name row.** Even a file whose record is embedded in its name row
   (key flags `0x01`) is rewritten as a key-flags `0x02` directory entry — an 84-byte value (72 if a pre-v3.10
   driver wrote it) that is only a pointer, with the record moved into a separate backing record. The driver's link
   path splits a file that is not yet split before it adds the new name, so the split is forced, and it leaves a
   trace.

   **This moves the record, not necessarily the data.** Placement and residency are independent: on format 3.11
   and later the file's bytes can stay *inside* that backing record, and for small files they usually do — the
   three names `hl1_a/b/c` in the lab corpus share a single 400-byte stream held inline. (On format 3.10 and
   earlier a split record's data is always in extents.) So on format 3.11+ a hard-linked file is commonly reported
   as a **split record holding inline data, with a link count above one** — not a contradiction.

   See [Record placement and data residency](placement_and_residency.md).

2. **It creates one type-0x30 directory entry per name.** Each name is a fully independent row in its
   own parent directory, carrying its own filename in the key. The names need not share a parent — that
   is what a hard link allows.

3. **It stamps every name with the same file identity** in the index-entry value. Two fields in the
   [index-entry value](../structures/directory_entries.md) carry that identity:
   - `value+0x00` is the **per-directory child ordinal** — the `NextFileId` ordinal the home directory
     assigned (the directory keeps that counter in its object record, and on format 3.10 and earlier also in its
     own `$SI+0x58`). Every name of the one file shares it. It is **not** unique on its own: each directory
     numbers its own children, so the same ordinal recurs in other directories (it is never reused within one).
     Qualified by the home OID it is: `(home OID, ordinal)` — the FileRef — names exactly one object.
   - `value+0x08` is the **home-dir backref** — the OID of the directory the file was *first created in*
     (it is identical for every name of the file, and shared with other files created in that same home directory,
     e.g. `0x600` for root-created files). This is provenance: the same OID is also the upper half of the
     file's 128-bit File ID in the change journal, and the key of its backing record, which stays in the home
     directory.

The driver routine `RefsLinkFileToSelf` prepares a file for a second name, once per file. It moves the file's
record out of the name row that embeds it into a row of its own in the same directory, keyed `0x80000040` (the
type-0x40 key prefix) + the file reference, and writes the file's existing name back as an index entry carrying
the (home backref, ordinal) pair; the file id, the directory and the name do not change, and no change-journal
record is written for it. Each further name is added by `RefsAddLink`.

It allocates **no new stream** — the record is moved, not copied — which is why a link must be resolved back to an
existing record. This is the placement change (embedded to split) that a hard link or a move to another directory
causes on a volume with hard-link support; without it a move keeps the record embedded and moves it whole.

## Reconstructing which names share a file: the join

The count can be read from the backing (`$SI+0x70`); the names that make it up are found by resolving each name to
its object, or from the backing's back-pointers.

A split file's record — its `$SI`, its name back-pointers and its `$DATA` (inline bytes or an extent map) — is a
type-0x40 row in its home directory, keyed by **`(owner-directory OID, file_id)`**: the driver's own object
identity. The complication is that `file_id` is the per-directory child ordinal (`value+0x00`), which is **not
unique** on its own: a directory can hold the backing of a *different* file that was home'd there under the same
ordinal. So a lookup by `(current parent, ordinal)` can land on a different file, and grouping by it produces a
wrong count; a lookup by `(home OID, ordinal)` — the FileRef — cannot.

A hard-link name reaches its record in one of two on-disk forms, and the correct grouping has to handle
both:

- **No local record** (the `fsutil hardlink` links of the ground-truth volume): the link's directory entry has
  no type-0x40 at all. Its record is the home backing `(home backref, file_id)`.
- **An `alloc=0` stub** (seen on the synthetic generator volumes): the link's own directory holds a placeholder
  type-0x40 at the same ordinal with `alloc_size=0` and `file_size=0`; the file's data is only in its home
  backing.

Which tool or API produces which form is not established.

The join resolves each name to the candidate backing — local `(parent, file_id)` or home `(home, file_id)` — whose
size **equals the name's own size** (type-0x30 `value+0x38`), then groups the names that share that backing's
`(owner, file_id)`:

- a stub's size is 0, so for a file with content it never matches and resolution follows the home backing;
- a name whose size matches no candidate is checked against the home backing's type-0x39 back-pointers, and joins
  the group if they name it;
- only a name the back-pointers do not list counts as 1.

This reproduces `fsutil hardlink list` exactly and matches the driver's own object identity.

```text
file1, name 1  →  value+0x00 = 3  value+0x08 = 0x600  ┐
file1, name 2  →  value+0x00 = 3  value+0x08 = 0x600  ├─ 4 links
file1, name 3  →  value+0x00 = 3  value+0x08 = 0x600  │  (ordinal 3)
file1, name 4  →  value+0x00 = 3  value+0x08 = 0x600  ┘
file2, name 1  →  value+0x00 = 4  value+0x08 = 0x600  ┐─ 2 links
file2, name 2  →  value+0x00 = 4  value+0x08 = 0x600  ┘  (ordinal 4)
```

The names sit in the root (OID 0x600) and in two subdirectories (0x705 and 0x706): what they share is the ordinal
and the home backref, not the parent.

The metadata cannot be used for the join: a name's cached size and times are per-name copies that go stale: two names of one
object can carry different sizes, so a `(home, ordinal, size, ctime, mtime)` tuple splits one file in two. And
`(home, ordinal)` itself never joins two distinct files; the size and the back-pointers confirm which names belong
to that one object.

### The authoritative name list lives in the backing

The size match reconstructs the grouping from the *names'* side, but ReFS also stores the list of names directly.
A hard-linked file's single type-0x40 backing embeds **a type-0x39 back-pointer for each name**, carrying that
name's parent-directory OID and the name string (count distinct `(parent, name)` pairs: some backings repeat one
byte-for-byte). These back-pointers are the object's own record of every path that points at it. (The count
itself the driver keeps in the file's FCB and writes to `$SI+0x70` when a name is added or removed.)

They matter because a name's cached size (`value+0x38`) is a *per-name* copy that ReFS does **not** keep in
lockstep across the names: one name can carry a stale size — 0, or an older size in either direction. A stale
size is the one situation where a size match alone under-groups; the name is still one of the object's, and its
0x39 back-pointers still list every name. All of a file's names share the single FileRef `(HomeOID, FileID)`
(see [File IDs](file_ids.md)); the back-pointers enumerate the names behind that one shared identity.

### Which size is the file's real size

The name's `value+0x38` is a **cache**. The object's size is in its **type-0x40 backing record, at `value+0x58`**
— itself a cached copy of the file's `$DATA` stream size, which is authoritative where the two differ (on one
corpus backing). forefst resolves the size through the backing.

The cache can be wrong **in either direction**, and the two failure modes are not equally visible:

| Cache says | Effect if believed |
|---|---|
| **larger** than the object | Reads past the end of the real content and appends whatever fills the last cluster |
| **smaller** than the object | **Silently truncates the file** — you get a short file with no error |

Across the corpus this affects **about 0.2 % of the index-entry names** (ReFS 3.7 through 3.14), and both
directions occur: one name caches more than twice its object's size, another about 60 % of it. In every one of
them the backing's size agrees with the file's own `$DATA` stream size
and the cached one does not, so the backing's size is confirmed, not only chosen.

This cannot arise on **ReFS 3.4**, which has no type-0x40 backings and no index-entry file rows at all.

## Forensic implications

- **Read `$SI+0x70` from the right record.** In a name row (an embedded record, key flags `0x01`) it is always
  1, even on a volume full of hard links, because a file with several names does not keep its record there. The
  count is in the split-out type-0x40 backing, where it equals the number of size-matched names on nearly every
  backing. A parser that reads the name row's copy reports "no hard links" on a volume that has them.

  See [Standard Information](../attributes/STANDARD_INFORMATION.md).

- **Links can be read or joined.** The backing gives the count (`$SI+0x70`) and the names (type-0x39
  back-pointers); the directory join reproduces both from the names' side. To join, scan every type-0x30 entry,
  resolve each to its backing through `(home OID, ordinal)`, confirm it by the name's own size (`value+0x38`) or by
  the back-pointers, and group the names of each backing.

  Grouping by the home backref alone merges every file created in that directory; `(parent, ordinal)` collides across
  directories, while `(home, ordinal)` — the FileRef — never joins two distinct files. The backing holds the file's
  `$DATA`: inline bytes, or an extent map (see [Extent Records](../structures/extent_descriptors.md)).

- **The home-dir backref shows where the file was created.** `value+0x08` records the directory a file was *originally
  created in*, and it survives even after the file has been hard-linked into other directories —
  invisible to a live `dir` listing. Because it is an OID, it resolves through the
  [Object Table](../structures/object_table.md) to a concrete directory, so it can place a file's origin
  even when all of its current names live elsewhere.

- **The record split is itself an artifact.** A file whose record was split out of its name row (key flags
  `0x02`, a 72- or 84-byte value) is the trace of a split: a cross-directory move or a hard link makes one (every such row on the volume audited is
  explained so), and so do the driver's POSIX-delete and rename-replace paths, so read it as a strong hint of a move or
  a link, not proof. Read it
  as a statement about the *record*, not the data: on format 3.11 and later such a file often still holds its
  bytes **inline** in the backing record — about one split-record row in five across the corpus does — so the
  split changes no byte of the data and is not a change of data residency.

  See [Record placement and data residency](placement_and_residency.md).

- **Each name carries a cached copy of the MACB — and they can disagree, but agreement proves nothing.** The file
  keeps one timestamp set in its own record (the backing), and each name's type-0x30 value holds a cached copy of
  its Created/Modified/Changed/Accessed (see
  [above](#per-name-timestamps-why-they-differ-and-what-erases-the-difference)).
  For a single-named file whose record is embedded there is only one set; a single-named split file (a moved file)
  also has the backing's own set beside its name's cached copy.

  A hard-linked file has one copy per name, and unlike NTFS — where every link shares a single `$SI` — those
  copies **can** hold different times. Two names of one file have been seen on disk carrying different Created
  values.

  **Setting a time through one name is not confined to that name.** A lab measurement built a two-name file and
  called `SetFileTime` on one path: afterwards both name rows were **byte-identical across their whole 84-byte
  value**, timestamp block included, and the backing record carried the same times. `SetFileTime` changes the
  file's own record at once, and each name's entry when that name is next opened; the lab's inventory pass had
  opened both names before the image was taken.

  What this shows, and what it does not:

  - **Divergence in Created between names is evidence.** It has been observed on disk, and nothing routine
    changes Created; the other three times can differ after ordinary use through one name.
  - **Agreement between names proves nothing.** It is what a stomp leaves behind once every name has been
    opened, and it is also what an untouched file looks like. The two are indistinguishable here.
  - **Which name holds the true birth is not established.** The driver refreshes only the opened name's entry,
    so the stale entry is the one nobody opened, not the one nobody forged: "the latest Created among the names
    is the authentic one" is an inference this project cannot support.

  Treat a divergence as a lead to follow with the [USN journal](../structures/usn_journal.md) or the
  [log](../structures/mlog.md), not as a conclusion on its own. Never read equal times on the other names as proof that
  the file is untouched.

- **Hard links need the volume's hard-link flag.** A split multi-name group on a volume whose boot-sector flags
  lack bit 0x20 (a v3.4 volume, or one upgraded from 3.4) is anomalous (see below).

- **Do not confuse hard links with block-clones.** A block-clone is a copy-on-write share: two
  *distinct* file objects, with different `(owner, file_id)` records, that happen to point at the same
  physical clusters. The join keeps them separate, which is correct — they are not the same object. They are
  also distinct from [reparse points](../structures/reparse_points.md) (symlinks and junctions), which are
  separate objects that point at another path rather than sharing an object.

  See [Copy-on-Write](copy_on_write.md).

## Version and state differences

| Aspect | v3.4, and v3.4 upgraded to 3.14 | formatted at 3.7 or later (corpus: 3.7, 3.9, 3.10, 3.14) |
|--------|------|----------------|
| Hard links supported | No (boot-sector bit 0x20 clear) | Yes (bit 0x20 set) |
| Index-entry type-0x30 value size | 72 bytes (directories only; entries written after an upgrade to 3.14 are 84) | 84 bytes, or 72 when a pre-v3.10 driver wrote it |
| Driver support routines | absent from the 17134 driver | present in the 26100 and Insider drivers (`RefsLinkFileToSelf`, etc.) |

refs.sys supports hard links on a volume exactly when its boot-sector flags (`+0x2C`) carry **bit 0x20**
(`InitializeVcbFromBootSector` / `RefsHardlinksSupported`, read on 26100.9444 and .8115; 17134 has no such
switch). The bit is set at format time on every volume formatted at 3.7 or later and is clear on 3.4 volumes; an
upgrade does not set it, so a volume upgraded from 3.4 has no hard-link support while one upgraded from 3.7 or 3.9
keeps it. On a volume without the bit a multi-name split group should not appear; finding one is an inconsistency
worth flagging — unless `refsutil fixboot` rewrote the boot sector, which clears the bit (its flags read 0x04)
and leaves the hard links made before it in the metadata.

## Tooling

`forefst.py` emits a computed `HardLinkCount` column (alongside `HardLinkNames`) in its file
listing — a CSV/JSON field, not a subcommand. The grouping runs automatically during the standard
directory walk (`walk_directory_tree`):

- it resolves each split name through its home key `(home, file_id)` and takes that type-0x40 backing when its
  size matches the name's own size (`value+0x38`);
- when the name's cached size is stale, it accepts the home backing if that backing's type-0x39 back-pointers list
  the name;
- it groups the names that share that backing's `(owner, file_id)`.

It reproduces `fsutil hardlink list` (a 4-link group, a 2-link group, and a 1-name survivor), keeps block-clones
separate, and `refsanalysis summary++` (`HardLinkExtraNames` in its JSON) uses the same resolver. Use the computed
field for the names; the backing's `$SI+0x70` is an independent check of the count.

## Cross-references

- [File IDs](file_ids.md) — the FileRef `(HomeOID, FileID)` every name of a hard-linked file shares, and
  why `HomeOID != current parent` marks a relocated *or* hard-linked-elsewhere name
- [Directory Entries](../structures/directory_entries.md) — the type-0x30 key/value layout; the
  index-entry value carries the child ordinal (`+0x00`) and home backref (`+0x08`) the join depends on
- [Standard Information](../attributes/STANDARD_INFORMATION.md) — `$SI+0x70` HardLinkCount (1 in a name row, the
  count in the backing) and the `$SI+0x58` NextFileId ordinal that seeds the child ordinal
- [Record placement and data residency](placement_and_residency.md) — why hard-linking splits the record out of the
  name row, and why that leaves the data where it was
- [Extent Records](../structures/extent_descriptors.md) — the extent map inside a backing's `$DATA`, for files
  whose data is not inline
- [Object Table](../structures/object_table.md) — resolves the home-dir backref OID (`+0x08`) to a
  concrete directory
- [Reparse Points](../structures/reparse_points.md) — symlinks and junctions, separate objects that point at
  another path, distinct from hard links
- [Copy-on-Write](copy_on_write.md) — block-clones share clusters but are distinct objects, correctly
  not merged as links

## Evidence

The hard-link mechanism is confirmed in the v3.14 driver and on the raw-disk corpus. Static:
the v3.14 driver carries hard-link routines that are absent in the v3.4 driver —
`RefsHardlinksSupported` (gating), `RefsLinkFileToSelf` (moves the record to its own row keyed `0x80000040`
and rewrites the existing name as an index entry carrying the identity pair, allocating no new stream),
`RefsOpenHardlinkDirectoryTarget` (target resolution) and `RefsPosixDeleteLink` (POSIX unlink); `RefsAddLink`, which
writes each further name, is in both drivers.
`RefsConvertToStandardInfoLinkCount` writes the count to the 4-byte `$SI+0x70` slot on every change of the file's
names (called by `RefsSetLinkInfo` after `RefsAddLink`, by `RefsPosixDeleteLink`, `RefsCommonCleanup` and
`RefsRemoveOrphanedHardlinkBackPointer`, and by `RefsSetRenameInfo`; read on 26100.9818, the writer present on
26100.8115, .9444 and Insider 29574, 29683, absent from 17134). `RefsComputeStandardInformationFromFcb` builds a
record's `$SI` from its FCB: `$SI+0x70 <- FCB+0xB4`, and `$SI+0x58` is the file's own ordinal (for a directory on
format 3.10 and earlier, its NextFileId counter `SCB+0x1B8`): the count is the file's own, kept in its FCB. Raw-disk: the mechanism was decoded on the image with `fsutil hardlink list`
ground truth (hard links occur on many corpus volumes), where one file's four names all share ordinal 3 / home
`0x600` and another's two names share ordinal 4 / home `0x600`, and their backings read 4 and 2 at `$SI+0x70`, as
`fsutil` counts them. In name rows `$SI+0x70` is never above 1 (329,120 of 329,120 rows); in backings it is above 1
on 101,252 of 107,525. The size-matched resolution was validated by an independent oracle reading each name's
own `value+0x38`: zero over-merge across the image corpus, the `fsutil` control reproduced, and genuine
multi-name groups preserved. The mechanism, the home-directory back-reference, `$SI+0x70` reading 1 in a name row
and the count in a backing, the type-0x40 backing key and the `alloc=0` stub form are registered findings.

Per-name MACB divergence was observed on disk against a two-name file whose names carried different Created times.
The driver explains it (`RefsUpdateFileDupInfo`, read on 26100.8115 and .9444): the file's own record takes a new
time at once, and each name's entry is refreshed only through a handle opened on that name. A lab measurement found
a `SetFileTime` through one name left **both** rows byte-identical across all 84 bytes, because both names had
been opened before the image. So equal times on a file's names do **not** show that its times were not changed.

The counts behind the text:

- `$SI+0x70` reads 1 on 329,120 of 329,120 embedded rows over 141 image files (some are copies of one volume);
- over 107,525 backings on 78 image files it reads greater than 1 on 101,252 (94.2 %; `{2: 91,337, 3: 6,489,
  4: 2,793, …}`) and equals the number of size-matched names on 107,355 of 107,525 (99.84 %); the 170 residual
  backings (0.16 %) read 2 with one surviving name;
- the `fsutil hardlink` ground truth (4 / 2 / 1) is on `win11refs2gtargeted`;
- the cached size differs from the backing's on 190 of 83,176 index-entry names; the two examples cache 239,973
  bytes for a 97,673-byte object and 293,302 for a 479,429-byte one;
- 16,191 split-record rows (over all 117 image paths; 16,164 of 81,760 over 79 distinct volumes) keep their data
  inline in the backing, all on format 3.11 or later.

See [how this was verified](../methodology.md) to trace these statements to the exact images and measurements in
`analysis/`.

<!-- findings: FN_LINK_001, FN_LINK_002, FN_LINK_003, FN_LINK_004, FS_OTBL_RA_008, MD_DATA_RA_004,
               MD_DATA_RA_006, MD_SI_RA_001, MD_SI_RA_009, MD_TS_RA_008 -->
