# Hard Links

A hard link is a second (or third, ...) directory name that points at one physical file. On ReFS the
mechanism is unusual enough that a parser written for NTFS will get the link count wrong every time:
there is **no explicit `HardLinkCount` field anywhere on disk**, and the value at
[`$SI`](../attributes/STANDARD_INFORMATION.md) offset 0x70 — the field whose PDB name *is*
"HardLinkCount" — is an embedded-layout per-FCB scalar that always reads 1, never the number of names.
For an analyst this has two consequences. First, link relationships must be **reconstructed by joining
directory-entry fields**, not read from a counter. Second, the join exposes a fact a live directory
listing never surfaces: the directory a file was *first created in*.

## Why ReFS has no link counter

In NTFS the MFT record for a file carries an explicit hard-link count and every name is a `$FILE_NAME`
attribute hanging off that one record. ReFS has no per-file MFT record to hang a counter on — a file is
a set of B+-tree rows, and each *name* is an independent row
([directory entry](../structures/directory_entries.md), type 0x30) in its own parent directory's tree.
There is nowhere natural to keep a shared count, so ReFS keeps none on disk. The driver synthesizes a
count only when an application asks for `FILE_STANDARD_INFORMATION`, via
`RefsConvertToStandardInfoLinkCount`; that synthesized value is written into the `$SI` 0x70 slot, which
is exactly why the on-disk field is always 1 and is not the source of truth.

## What hard-linking does on disk

Linking a file performs three changes to its on-disk representation:

1. **It splits the object's record out of the name row.** Even a small file that would normally keep its
   record inline (key flags `0x01`) is rewritten as a key-flags `0x02` directory entry — an 84-byte value
   (72 if a pre-v3.10 driver wrote it) that is only a pointer, with the record moved into a separate
   backing record. A file whose record is embedded in one name cannot be given a second name, so the split
   is forced, and it leaves a trace.

   **This moves the record, not necessarily the data.** Placement and residency are independent: the
   file's bytes can stay *inside* that backing record, and for small files they usually do — the three
   names `hl1_a/b/c` in the lab corpus share a single 400-byte stream held inline. So a hard-linked file
   is commonly reported as a **split record holding inline data, with a link count above one** — not a
   contradiction. See [Record placement and data residency](resident_storage.md).

2. **It creates one type-0x30 directory entry per name.** Each name is a fully independent row in its
   own parent directory, carrying its own filename in the key. The names need not share a parent — that
   is the whole point of a hard link.

3. **It stamps every name with the same file identity** in the index-entry value. Two fields in the
   [index-entry value](../structures/directory_entries.md) carry that identity:
   - `value+0x00` is the **per-directory child ordinal** — the same `NextFileId` ordinal the home
     directory assigned from its `$SI+0x58` counter. Every name of the one file shares it. Crucially it
     is **not** a globally-unique FileId: it is reused per directory and *collides across sibling
     directories under a shared home*, which is the trap the link join has to avoid.
   - `value+0x08` is the **home-dir backref** — the OID of the directory the file was *first created in*
     (it is identical for every name of the file, and shared with other files born in that same home,
     e.g. `0x600` for root-created files). This is provenance, recoverable nowhere else.

The identity copy is done by the driver routine `RefsLinkFileToSelf`, which writes the (home backref,
ordinal) pair into the new name's value and emits a redo record under tag `0x80000040`; it notably
allocates **no new stream** for the link, which is why a link must be resolved back to an existing one.

## Reconstructing the link count: a join, not a field read

Because no count exists, the link count is **derived** by resolving each name to its physical content.
A file's extents live in a type-0x40 ("stream") record keyed by **`(owner-directory OID, file_id)`** —
the driver's own physical-object identity. The complication is that `file_id` is the per-directory child
ordinal (`value+0x00`), which is **not unique**: a directory can hold the stream of a *different* file
that was home'd there under the same ordinal. So `(dir, ordinal)` alone over-merges distinct files, and
grouping by it produces a wrong count.

A hard-link name reaches its stream in one of two on-disk forms, and the correct grouping has to handle
both:

- **No local record** (links created by `fsutil hardlink`): the link's directory entry has no type-0x40
  at all. Its content is the home stream `(home backref, file_id)`.
- **An `alloc=0` stub** (links created by some other tools): the link's own directory holds a
  placeholder type-0x40 with `alloc_size=0` and `file_size=0`; the real extents live only in the
  original/home directory.

The disambiguator that makes the join correct is the **name's own size** (type-0x30 `value+0x38`).
Resolve each name to the candidate stream — local `(parent, file_id)` or home `(home, file_id)` — whose
type-0x40 size **equals the name's size**, then group names that share that stream's `(owner, file_id)`.
A stub (size 0) never matches the name's real size, so resolution correctly follows the home stream; a
colliding ordinal whose stream is a *different* size is correctly rejected; a name whose size matches no
candidate is not merged (counted as 1). This reproduces `fsutil hardlink list` exactly and matches the
driver's own object identity.

```text
file1 "hltest_file1"  dir=0x600  →  value+0x00 = 3  value+0x08 = 0x600  ┐
file1 "link1"         dir=0x600  →  value+0x00 = 3  value+0x08 = 0x600  ├─ 4 links
file1 "link2"         dir=0x600  →  value+0x00 = 3  value+0x08 = 0x600  │  (ordinal 3)
file1 "link3"         dir=0x600  →  value+0x00 = 3  value+0x08 = 0x600  ┘
file2 ...             dir=0x600  →  value+0x00 = 4  value+0x08 = 0x600  ┐─ 2 links
file2 ...             dir=0x600  →  value+0x00 = 4  value+0x08 = 0x600  ┘  (ordinal 4)
```

Why size-match and not the metadata? Because the per-directory ordinal collides: two distinct
different-size files can sit at the same home OID under the same ordinal, and a tuple of
`(home, ordinal, size, ctime, mtime)` either false-merges them or false-splits them. Only resolving each
name to the candidate stream whose 0x40 size equals the name's own size keeps colliding files distinct.

### The authoritative name list lives in the backing

The size match reconstructs the grouping from the *names'* side, but ReFS also stores the answer directly.
A hard-linked file's single type-0x40 backing embeds **one type-0x39 back-pointer per name**, each carrying
that name's parent-directory OID and the name string. These back-pointers are the object's own record of
every path that points at it — the ground truth `RefsConvertToStandardInfoLinkCount` derives its count from.
They matter because a name's cached size (`value+0x38`) is a *per-name* copy that ReFS does **not** keep in
lockstep across the names: one name can carry a stale size — the `alloc=0` stub's 0 is the common case, but
any old value occurs — and that stale size is the one situation where a size-match join under-groups (the
name resolves to no candidate and is counted as a solo file). It is still one object, and its 0x39
back-pointers still list every name. All of a file's names share the single FileRef `(HomeOid, FileId)`
(see [File IDs](file_ids.md)); the back-pointers enumerate the names behind that one shared identity.

### Which size is the file's real size

The name's `value+0x38` is a **cache**. The object's size lives in its **type-0x40 backing record, at
`value+0x58`** — that is the one to trust, and it is the one every forefst command resolves.

The cache can be wrong **in either direction**, and the two failure modes are not equally visible:

| Cache says | Effect if believed |
|---|---|
| **larger** than the object | Reads past the end of the real content and appends whatever fills the last cluster |
| **smaller** than the object | **Silently truncates the file** — you get a short file with no error |

Across the corpus this affects **190 of 83,176** index-entry names (ReFS 3.7 through 3.14), and both
directions occur: one name caches 239,973 bytes for a 97,673-byte object, another caches 293,302 for a
479,429-byte one. In every one of the 190 the backing's size agrees with the file's own `$DATA` stream size
and the cached one does not, so the backing is corroborated rather than merely preferred.

This cannot arise on **ReFS 3.4**, which has no type-0x40 backings and no index-entry file rows at all.

## Forensic implications

- **The `$SI+0x70` field is a decoy.** It is present only in embedded (key flags `0x01`) values and is
  always 1 across the entire corpus — even on the volume that actually contains hard links. Treating it
  as a link count will silently report "no hard links" on a volume that has them, because hard-linked
  files are split out and carry no `$SI+0x70` at all. See
  [Standard Information](../attributes/STANDARD_INFORMATION.md) for the field's true (embedded-layout)
  meaning.

- **Link reconstruction is a join.** To count links you must scan every type-0x30 entry, resolve each to
  the type-0x40 stream whose 0x40 size matches the name's own size (`value+0x38`), and group names that
  share that stream's `(owner, file_id)`. Grouping by the home backref alone reports the *directory's
  child count*, `(home, ordinal)` collides across sibling directories, and a metadata tuple over-merges;
  the size match is what makes the join sound. The streams themselves are
  [extent descriptors](../structures/extent_descriptors.md) under a type-0x40 record.

- **The home-dir backref is provenance.** `value+0x08` records the directory a file was *originally
  created in*, and it survives even after the file has been hard-linked into other directories —
  invisible to a live `dir` listing. Because it is an OID, it resolves through the
  [Object Table](../structures/object_table.md) to a concrete directory, so it can place a file's origin
  even when all of its current names live elsewhere.

- **The record split is itself an artifact.** A file whose record was split out of its name row (key flags
  `0x02`, 84-byte value) is a fingerprint of having been moved or hard-linked at some point. Read it as a
  statement about the *record*, not the data: such a file very often still holds its bytes **inline** in
  the backing record — 16,191 rows across the corpus do — so the split changes no byte of the data and is
  not a change of data residency. See [Record placement and data residency](resident_storage.md).

- **Each name carries its own MACB — a hard-link-specific tamper check.** ReFS keeps one
  [`$SI`](../attributes/STANDARD_INFORMATION.md) timestamp set *per name*, not per file: every name's
  type-0x30 value holds its own Created/Modified/Changed/Accessed. For a single-named file there is no
  timestamp twin to compare against. But a hard-linked file has one independent timestamp copy per name,
  and a name-scoped timestomp (opening one path and setting its times) rewrites only that name's row —
  the sibling names keep the true birth. Comparing the names' Created/Modified therefore localises the
  backdated name, and the latest Created among the siblings is the authentic birth. This cross-check is
  journal-independent, and it is stronger than NTFS's `$SI`-vs-`$FILE_NAME` check, where all hard links
  share one `$SI` and cannot diverge.

- **Hard links are a v3.14-native-only signal.** A split multi-name group on a volume that should
  be v3.4, or on a volume that was *upgraded* rather than natively formatted, is anomalous (see below).

- **Do not confuse hard links with block-clones.** A block-clone is a copy-on-write share: two
  *distinct* file objects, with different `(owner, file_id)` records, that happen to point at the same
  physical clusters. The size-matched join keeps them separate, which is correct — they are not the same
  object. See [Copy-on-Write](copy_on_write.md). They are also distinct from
  [reparse points](../structures/reparse_points.md) (symlinks and junctions), the *other* multi-name
  mechanism, which redirect by path rather than sharing an object.

## Version and state differences

| Aspect | v3.4 | v3.14 (native) |
|--------|------|----------------|
| Hard links supported | No | Yes |
| Index-entry type-0x30 value size | 72 bytes | 84 bytes |
| Driver support routines | absent | present (`RefsLinkFileToSelf`, etc.) |

Hard links require the **CHKP native-format flag `0x080`** (the native-format marker). They are **not**
available on a v3.4 volume that was *upgraded* to v3.14 — only on a volume natively formatted as v3.14.
On an upgraded volume the directory still reports the legacy behavior, so a multi-name split group
should not appear; finding one is an inconsistency worth flagging.

## Tooling

`forefst.py` emits a computed `hard_link_count` column (alongside `hard_link_names`) in its file
listing — a CSV/JSON field, not a subcommand. The grouping runs automatically during the standard
directory walk (`walk_directory_tree`): it resolves each split name to the type-0x40 stream —
local `(parent, file_id)` or home `(home, file_id)` — whose 0x40 size matches the name's own size
(`value+0x38`), and groups names that share that stream's `(owner, file_id)`. It reproduces
`fsutil hardlink list` (a 4-link group, a 2-link group, and a 1-name survivor), keeps block-clones
separate, and `refsanalysis summary++` (`hardlink_extra`) uses the same resolver. Rely on this computed
field rather than reading any `$SI` field directly.

## Cross-references

- [File IDs](file_ids.md) — the FileRef `(HomeOid, FileId)` every name of a hard-linked file shares, and
  why `HomeOid != current parent` marks a relocated *or* hard-linked-elsewhere name
- [Directory Entries](../structures/directory_entries.md) — the type-0x30 key/value layout; the
  index-entry value carries the child ordinal (`+0x00`) and home backref (`+0x08`) the join depends on
- [Standard Information](../attributes/STANDARD_INFORMATION.md) — the `$SI+0x70` "HardLinkCount" decoy
  and the `$SI+0x58` NextFileId ordinal that seeds the child ordinal
- [Record placement and data residency](resident_storage.md) — why hard-linking splits the record out of the
  name row, and why that leaves the data where it was
- [Extent Descriptors](../structures/extent_descriptors.md) — the type-0x40 stream record each name is
  resolved to
- [Object Table](../structures/object_table.md) — resolves the home-dir backref OID (`+0x08`) to a
  concrete directory
- [Reparse Points](../structures/reparse_points.md) — symlinks and junctions, the *other* multi-name
  mechanism, distinct from hard links
- [Copy-on-Write](copy_on_write.md) — block-clones share clusters but are distinct objects, correctly
  not merged as links

## Evidence

The hard-link mechanism is confirmed in the v3.14 driver (E2) and on the raw-disk corpus (RD). Static:
the v3.14 driver carries a family of hard-link routines that are entirely absent in the v3.4 driver —
`RefsHardlinksSupported` (gating), `RefsLinkFileToSelf` (copies the home-backref/ordinal identity pair
into the new name and emits the redo under tag `0x80000040`, allocating no new stream), `RefsAddLink`,
`RefsOpenHardlinkDirectoryTarget` (target resolution), and `RefsPosixDeleteLink` (POSIX unlink).
`RefsConvertToStandardInfoLinkCount` synthesizes the count for the `FILE_STANDARD_INFORMATION` query API
and writes the 4-byte `$SI+0x70` slot — the reason that field always reads 1.
`RefsComputeStandardInformationFromFcb` fills the embedded `$SI`, copying `$SI+0x70 <- FCB+0xB4` and
`$SI+0x58 <- SCB+0x1B8` (the NextFileId ordinal), confirming 0x70 is a per-FCB scalar, not a
cross-directory aggregate. Raw-disk: the mechanism was decoded against the one corpus image with genuine
hard links (ground-truth `fsutil hardlink list`), where one file's four names all share ordinal 3 / home
`0x600` and another's two names share ordinal 4 / home `0x600`; `$SI+0x70 > 1` occurs in zero entries
across the corpus. The size-matched resolution was validated by an independent oracle reading each name's
own `value+0x38`: zero over-merge across the image corpus, the `fsutil` control reproduced, and genuine
multi-name groups preserved. Findings: **FN_LINK_002** (mechanism), **FS_OTBL_RA_008** (home-dir backref),
**FN_LINK_002, MD_SI_RA_009 / MD_SI_RA_001** (`$SI+0x70` is embedded-only, never > 1),
**MD_DATA_RA_004** (type-0x40 stream key), **MD_DATA_RA_006** (`alloc=0` stub form); the size match
defeats the colliding-ordinal over-merge. The per-name MACB divergence was proven on disk against a
two-name file whose one name was name-scoped timestomped while its sibling kept the true birth
(**FN_LINK_003 / E59**). See [how this was verified](../methodology.md) to trace these to the exact images
and measurements in `analysis/`.
