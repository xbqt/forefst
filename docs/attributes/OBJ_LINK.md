# $OBJ_LINK

`$OBJ_LINK` is the **object → primary-name backpointer** — it stores a file's canonical filename and
parent OID directly in the object's own type-0x10 row, so a path can be reconstructed from the Object
Table alone, without walking directory trees. It is a multi-instance embedded sub-record, **type 0x39 on
v3.7+** and **type 0x38 on v3.4**. (It is the same on-disk row historically called **`$DIR_LINK`** — the
legacy v3.4-era debug/management-API name.) The row is **one-per-object**: creating a hard link adds no
new `$OBJ_LINK` row.

## Value layout

The format differs between v3.7+ (compact: parent OID + name) and v3.4 (a full metadata block with
timestamps).

**v3.7+ — key** (the value overlaps the key from byte 8):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Value length | |
| 0x08 | 4 | Marker | 0x80000002 (multi-instance) |
| 0x0C | 2 | Type code | 0x0039 |
| 0x0E | 2 | Sub-type | 0x000D |
| 0x10 | 4 | Parent OID | the parent directory OID |
| 0x14 | var | Filename | UTF-16LE, in the key/value overlap |

**v3.7+ — value:** `0x00` marker 0x80000002, `0x04` type 0x0039, `0x06` sub-type 0x000D, `0x08` parent
OID, `0x0C` reserved (12 bytes, 0), `0x18` filename (UTF-16LE, null-terminated).

**v3.4 — value** (the common 12-byte sub-record header, then a full metadata block):

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
| 0x3C | 4 | File attributes | Win32 flags |
| 0x4C | 4 | Flags word | 0x10000006 |
| 0x54 | 2 | Name length | filename length (UTF-16 chars) |
| 0x5E | var | Filename | UTF-16LE, null-terminated |

The v3.4 key is `0x00` value length, `0x08` type code 0x00000038 (no instance marker).

**v3.4 stores independent, frozen timestamps.** The v3.4 `$OBJ_LINK` value carries its own four
timestamps: the *creation* time matches the directory entry exactly, but the modify/change/access times
are **frozen at object creation** while the directory entry tracks later updates — so the two diverge by
the time between object creation and the next metadata update. (v3.7+ stores only the parent OID and
name, not timestamps.)

## Forensic significance

`$OBJ_LINK` is critical for **deleted-file and damaged-tree recovery**. If a directory B+-tree page is
corrupted but the Object Table survives, each surviving type-0x10 row's `$OBJ_LINK` still yields the
file's exact name, its parent OID, and — by chaining parent OIDs — the full path. On v3.4 it additionally
yields the file's creation timestamp.

## Driver and versioning

The on-disk form is selected by `VCB+0x2ACC` (the same flag as `RefsHardlinksSupported`): 0x38 = the
legacy v3.4 backpointer, 0x39 = the current form. The v3.7+ row is built by `RefsInitializeObjLinkRow`;
the v3.4 row by `RefsBackpointerValueFromFileName` → `CreateAttribute(0x38)`. Both are driven by
`RefsAttributeManager::CreateLinkAttribute` / `DeleteLinkAttribute` (the "$DIR_LINK" management API).
Upgraded v3.4→v3.14 volumes keep the old 0x38 rows.

## Cross-references

- [Object Table](../structures/object_table.md) — the OID → row mapping `$OBJ_LINK` is reached through
- [Hard Links](../concepts/hard_links.md) — why a hard link adds no new `$OBJ_LINK` row
- [Resident vs Non-Resident Storage](../concepts/resident_storage.md) — the embedded sub-record model

## Evidence

Type 0x38 / 0x39 and the layouts are confirmed in the decompiled driver (E2 — `RefsInitializeObjLinkRow`,
`RefsBackpointerValueFromFileName`) and raw-disk decoded across the corpus (RD); `$OBJ_LINK` is present on
nearly every user object. See [how this was verified](../methodology.md).
