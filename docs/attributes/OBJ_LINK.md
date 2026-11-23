# $OBJ_LINK
<!-- site: description "The object-to-name backpointer: one row per name, holding the name and its parent directory's object ID." -->

`$OBJ_LINK` is the object → name backpointer.

- It stores a filename and its parent OID directly in the object's own record. A directory's path can therefore be
  rebuilt from the Object Table alone, by chaining parent OIDs, without walking the directory trees; a split file's
  backing lists every name of the file the same way.
- It is an embedded sub-record: type 0x39 (multi-instance) on a volume with hard-link support, type 0x38 on 3.4 and
  on a volume upgraded from it (see [Driver and versioning](#driver-and-versioning)).
- It is the same on-disk row called `$DIR_LINK` elsewhere: the 17134 driver carries that name, and the driver type
  that builds the 0x38 row is `_DIR_LINK_BACKPOINTER`.

| Property | Value |
|----------|-------|
| Type code | 0x39 on a volume with hard-link support (in the corpus, every volume formatted at 3.7 or later but one); 0x38 on 3.4 and on a volume upgraded from 3.4 |
| Instances | multi-instance (marker 0x80000002), one row per name; the 3.4 key carries no marker |
| Where it lives | the record of an object that has its own: a directory's type-0x10 own row, or a split file's type-0x40 backing. A file whose name row embeds its record has none (on the volume measured) |
| Size | variable with the name: 0x18 bytes + the name on 3.7 and later; a metadata block + the name on 3.4 |
| Added in | 3.4 or earlier: present on every format read (type 0x38 on 3.4, Windows 10 1803, driver 17134; type 0x39 from 3.7, Windows 11 21H2) |

## One row per name

There is one row per *name*, not one per object: a hard link adds a row.

- Measured across the corpus (ReFS 3.7, 3.9, 3.10 and 3.14), the number of *distinct* `(parent OID, name)` pairs
  in an object's backing equals the number of directory entries pointing at that object on every backing measured,
  for objects carrying from one to many names, with no exceptions.
- That makes these rows the object's own enumeration of every path that reaches it, and the most direct way to count
  and list a file's hard links.

Two things to handle when counting:

- Deduplicate. Some backings carry the *same* `(parent, name)` row twice, byte-for-byte. Count distinct pairs, not
  rows. (Observed on moved files; the operation that produces the second copy is not yet pinned.)
- Scope "always present". These rows live on objects that have their own record: directories (in their type-0x10
  row) and files whose record was split out into a type-0x40 backing. A file whose name row still *embeds* its
  record (`key_flags` 0x01) has none (none on the volume measured).
- On ReFS 3.4 every directory carries one, a type-0x38 row (and none a 0x39 row), with no exception on the 3.4
  volumes measured. The 3.4 row is a different *shape* from the 3.7+ one — see the layouts below — but it is
  present, so absence must not be used to tell the formats apart.

## Value layout (3.7 and later)

The format differs between 3.7 and later (compact: parent OID + name) and 3.4 (a full metadata block with
timestamps).

Key (the value overlaps the key from byte 8):

<!-- site: hexfig "attr_obj_link_win11refs2tspecials" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Value length | |
| 0x08 | 4 | Marker | 0x80000002 (multi-instance) |
| 0x0C | 2 | Type code | 0x0039 |
| 0x0E | 2 | Subtype | 0x000D |
| 0x10 | 4 | Parent OID | the parent directory OID |
| 0x14 | 12 | Reserved | zero on every row measured |
| 0x20 | var | Filename | UTF-16LE, in the key/value overlap — not NUL-terminated |

Value:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Marker | 0x80000002 |
| 0x04 | 2 | Type code | 0x0039 |
| 0x06 | 2 | Subtype | 0x000D |
| 0x08 | 8 | Parent OID (u64) | |
| 0x10 | 8 | Reserved | 0 |
| 0x18 | var | Filename | UTF-16LE, not NUL-terminated |

The name sits at value+0x18, which is key+0x20 — the key is 8 length bytes followed by the whole value, so the two
addresses are the same bytes.

- On every type-0x39 row measured, `key[0x20:] == value[0x18:]`.
- Reading the name at `key+0x14` succeeds on none, because `key[0x14:0x20]` is the 12 reserved zero bytes on every
  row.
- The name runs to the end of the row and carries no NUL terminator — take its length from the row, not from a scan
  for `00 00`.

## Format 3.4 difference

The 3.4 key is `0x00` value length, `0x08` type code 0x00000038 (no instance marker).

The 3.4 value (the common 12-byte sub-record header, then a full metadata block):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | value length − 12 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 8 | Reserved | 0 |
| 0x14 | 4 | Parent OID | |
| 0x18 | 4 | Reserved | 0 |
| 0x1C | 8 | Creation time | FILETIME |
| 0x24 | 8 | Modification time | FILETIME |
| 0x2C | 8 | Change time | FILETIME |
| 0x34 | 8 | Access time | FILETIME |
| 0x3C | 8 | Size | the value 17134 also writes to `$SI+0x38`; 0 on 364 of the 373 rows measured (all on directories; the nine root rows hold other bytes, below) |
| 0x44 | 8 | Size | the value 17134 also writes to `$SI+0x30`; 0 on the same 364 of 373 rows |
| 0x4C | 8 | File attributes | the object's attribute word, directory bit 0x10000000 included (0x10000000 on most rows) |
| 0x54 | 2 | Name length | filename length (UTF-16 chars) |
| 0x5A | 2 | — | 0x30 on every row measured |
| 0x5C | 2 | — | 2 on every row measured (the 17134 writer sets 2 for a directory) |
| 0x5E | var | Filename | UTF-16LE, not NUL-terminated: its length is at +0x54, and 0 to 6 zero bytes may follow it |

Measured on the 373 type-0x38 rows of the corpus (the 3.4 volumes and the volumes upgraded from 3.4): +0x4C equals the
record's `$SI` attributes with the directory bit on 363. The others are the root directory's `.` row on nine images
of volumes formatted by 17134, whose +0x10 to +0x51 hold other bytes (not times or attributes), and one directory
whose `$SI` carries the integrity bit 0x8000 that its row's +0x4C lacks. On the volume upgraded from 3.4, the 32
user directories' rows keep their times, attributes and length across the first Windows 11 mount. The 26100.9444 writer of a 0x38 row
(`RefsBackpointerValueFromFileName`) zeroes everything between the parent reference and the name, so a row it writes
would carry no times and no attributes; no row it wrote was identified on the corpus.

The 3.4 value stores independent, frozen timestamps. Its own four timestamps, as measured on one 3.4 volume, are:

- the *creation* time, which matches the directory entry exactly;
- the modify / change / access times, frozen at object creation while the directory entry tracks later updates — so
  the two diverge by the time between object creation and the next metadata update.

(3.7 and later store only the parent OID and name, not timestamps.)

## Forensic significance

`$OBJ_LINK` is critical for deleted-file and damaged-tree recovery. If a directory B+-tree page is corrupted but the
Object Table survives:

- each surviving directory's own row still yields the directory's exact name and its parent OID, and — by chaining
  parent OIDs — its full path;
- each surviving type-0x40 backing yields every name of its file and the directory of each;
- on 3.4 the row additionally yields the object's creation timestamp.

## Driver and versioning

The on-disk form is selected by `VCB+0x2ACC` (the same field `RefsHardlinksSupported` tests): 0x38 = the legacy v3.4
backpointer, 0x39 = the current form.

- The driver sets the field at mount from the boot sector's hard-link bit (0x20 of the flags at `+0x2C`): 0x39 when
  it is set, else 0x38. So on 26100.9444 `CreateLinkAttribute` writes a 0x38 row on a volume without hard-link
  support, an upgraded one included.

- The 3.7+ row is built by `RefsInitializeObjLinkRow`; the 3.4 row by `RefsBackpointerValueFromFileName` →
  `CreateAttribute(0x38)`.
- On the 26100 drivers both are driven by `RefsAttributeManager::CreateLinkAttribute` / `DeleteLinkAttribute`.
- Upgraded v3.4→v3.14 volumes keep the old 0x38 rows.

## Cross-references

- [Object Table](../structures/object_table.md) — the OID → row mapping `$OBJ_LINK` is reached through
- [Hard Links](../concepts/hard_links.md) — how the per-name rows enumerate an object's links
- [Record placement and data residency](../concepts/placement_and_residency.md) — the embedded sub-record model

## Evidence

Type 0x38 / 0x39 and the layouts are read in the decompiled driver (`RefsInitializeObjLinkRow`,
`RefsBackpointerValueFromFileName`, `CreateLinkAttribute` on 26100.9444) and decoded on disk across the corpus;
`$OBJ_LINK` is present on 99.6 % of the user OIDs measured. The page is documented against the project's claim
register. See [how this was verified](../methodology.md).

The measurements behind the text:

- One row per name: distinct `(parent OID, name)` pairs = directory entries pointing at the object on 40,966 of
  40,966 backings (formats 3.7, 3.9, 3.10 and 3.14), for objects carrying 1 to 19 names.
- An embedded-record file carries none: 0 of 219 on the volume measured.
- 3.4 directories: 445 of 445 over the 13 v3.4 image paths carry a 0x38 row (439 of 439 over 12 distinct volumes),
  among them `win10refsmini` 6/6, `win10refs2g` / `5g4k` / `5g64k` / `8g` / `8gsetintegritystreams1` / `19g` / `110g`
  34/34 each, `win10refs2tspecials` 149/149 and `win10to11refs4g_beforewin11mount` 34/34.
- The 3.4 timestamps: on one 148-object volume the creation time matches the directory entry on 148 of 148; the
  three others diverge by 0.8 s to more than 135 s (median about 10 s).
- Upgraded volume: on `win10to11refs4g` (3.4 upgraded to 3.14) 39 of 39 objects keep type 0x38.
- The 3.7+ key: the 12 reserved bytes are zero on 314,249 of 314,249 rows; over those 314,249 type-0x39 rows on 126
  volumes `key[0x20:] == value[0x18:]` on all, the name read at `key+0x14` succeeds on 0, and 0 carry a NUL
  terminator. Values of 26 to 82 bytes are observed.

<!-- findings: GN_AMGR_SA_001, MD_ATTR_003, MD_ATTR_RA_006, MD_LK_RA_005, MD_LK_RA_006, MD_LK_RA_007,
               MD_LK_RA_008, MD_LK_RA_009 -->
