# ReFS Attributes — Forensic Reference

A file's or directory's metadata in ReFS is a set of typed attributes. This page is the analyst's entry point:

- what the real ReFS attributes are, and how they are laid out on disk;
- which NTFS attribute names have no ReFS attribute behind them;
- which attributes matter most forensically.

Most attributes have a detailed byte-level page linked from the catalog below.

## 1. What a ReFS attribute is

In NTFS, a file's metadata is a list of typed attributes inside its `$MFT` record. ReFS keeps the same idea but
stores it differently.

- Every directory and system object has its own B+-tree, reached by a 64-bit Object ID (OID) through the
  [Object Table](../structures/object_table.md). Its metadata lives in the rows of that tree, and its attributes are
  embedded sub-records inside the object's own row, not a separate attribute list.
- A file has no OID or B+-tree of its own. Its metadata and attributes sit in its name row in the parent directory's
  tree or, once a move or a hard link has split its record out, in a type-0x40 backing in its home directory's tree.

So there are two layers:

- Top-level row types — the kinds of row in an object's B+-tree:

  | Row type | Role |
  |----------|------|
  | `0x10` | the object's own row — carries `$STANDARD_INFORMATION` (`$SI`) plus the embedded sub-record chain |
  | `0x20` | the FileId index — Format A repeats a name, Format B holds a home-directory back-reference; both keyed by FileId (see [Reverse Index](../structures/reverse_index.md)) |
  | `0x30` | a child name row — it either embeds the child's record (`key_flags` 0x01) or points at it (`key_flags` 0x02: every subdirectory and every split file) |
  | `0x40` | the backing record of a split file (moved or hard-linked): its own `$SI`, `$DATA` (inline or an extent map), names and other attributes, keyed by its ordinal and its home directory's OID. A directory always has its own OID and B+-tree; a split file has no OID of its own — its record lives here, reached via the home-dir backref + child ordinal, not via the Object Table |

- Embedded sub-records — inside a directory's `0x10` value, a file's embedded name-row value, or a split file's
  `0x40` backing, the actual attributes (`$DATA`, `$OBJ_LINK`, `$I30_INDEX`, `$EA`, `$EFS`, …) are stored as
  embedded sub-records.

See [Record placement and data residency](../concepts/placement_and_residency.md) for the two placements of a file's
record.

## 2. How attributes are organized

Embedded sub-record markers. On 3.7 and later keys a marker at `key+0x08` says whether the attribute may repeat;
3.4 keys (and the 3.4 rows an upgraded volume keeps) carry none:

| Marker | Meaning | Examples |
|--------|---------|----------|
| `0x80000001` | single-instance (at most one per object) | `$DATA` (0x80) when its data is inline, `$REPARSE_POINT` (0xC0), `$EA_INFORMATION` (0xD0), `$EA` (0xE0) |
| `0x80000002` | multi-instance (may repeat) | `$DATA` (0x80) when its data is in extents, `$SNAPSHOT`/ADS (0xB0), `$OBJ_LINK` (0x39), `$I30_INDEX` (0x90) |

`$DATA` appears under both markers: a record carries its main `$DATA` in one form or the other, never both, so read
the marker and the type together.

Type codes and schemas. A type code names an attribute; a schema id names a table. The record that holds a file's
or a directory's attributes is itself a small table, and its schema id (in the record's first 40 bytes) says under
which format the object was created or last converted, not which attributes it holds: see [Schema Table](../structures/schema_table.md). An attribute has
no schema of its own.

`$SI` is the record's root data, not a sub-record. A common trap: `$STANDARD_INFORMATION` is not an embedded
`0x90` sub-record — it is the root data of the record's table, at `value+0x28` of the record: a directory's `0x10`
own-row value, or a file's record (its `0x30` name-row value, or its `0x40` backing once split out). The embedded
type-`0x90` sub-record is `$I30_INDEX` (the directory-index template), a different thing. Read `$SI` from
`value+0x28`, never from a type-`0x90` sub-record.

The `$EA` chain (WSL / Linux metadata). Extended attributes are a two-part structure: `$EA_INFORMATION` (type 0xD0)
is the size index; `$EA` (type 0xE0) is the body — a standard NT `FILE_FULL_EA_INFORMATION` chain. WSL stores Linux
ownership inside that chain as named EAs — `$LXUID`, `$LXGID`, `$LXMOD`, `$LXDEV` (and kernel-cache state as
`$Kernel.Purge.*`). These are EA entries, not standalone attribute types; see
[$EA_INFORMATION and $EA](EA_INFORMATION.md).

## 3. The attribute catalog

The ReFS attributes, by type code (the driver's attribute-definition table pairs each name with its type code).

| Type | Attribute | What it is | Versions | Detail |
|------|-----------|------------|----------|--------|
| — | `$STANDARD_INFORMATION` (`$SI`) | timestamps, file attributes, SecurityId, sizes, USN link — the root data of the record's table (a directory's own row, a file's name row or backing) | v3.4+ | [STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) |
| 0x38 / 0x39 | `$OBJ_LINK` | object→name backpointer (parent OID + name), one per name, in a directory's own row or a split file's backing | 0x38 on v3.4 and on volumes upgraded from it; 0x39 from v3.7 | [OBJ_LINK](OBJ_LINK.md) |
| 0x80 | `$DATA` | the file's main data stream — inline (format 3.11+, below 2 KiB) or an extent map | v3.4+ | [DATA](DATA.md) |
| 0x90 | `$I30_INDEX` | the embedded directory-index configuration template (the "$I30" template; *not* `$SI`; the driver's attribute-definition name for type 0x90 is `$INDEX_ROOT`) | v3.4+ | [I30_INDEX](I30_INDEX.md) |
| 0xB0 | `$SNAPSHOT` / `$NAMED_DATA` | stream snapshots and named data streams (ADS) share type 0xB0, distinguished by the StreamSummary flag | named streams v3.4+; snapshots seen on v3.14 only (the first driver to write them is not known) | [SNAPSHOT](SNAPSHOT.md), [NAMED_DATA](NAMED_DATA.md) |
| 0xC0 | `$REPARSE_POINT` | per-file reparse data (symlink / junction / mount / WSL node); no type-0x70 row is observed in user objects | v3.4+ (the 3.4 driver reads type 0xC0) | [REPARSE_POINT](REPARSE_POINT.md) |
| 0xD0 | `$EA_INFORMATION` | extended-attribute size index | seen on v3.14 only (the first driver to write it is not known) | [EA_INFORMATION](EA_INFORMATION.md) |
| 0xE0 | `$EA` | extended-attribute body (carries the WSL `$LX*` names) | as `$EA_INFORMATION` | [EA_INFORMATION](EA_INFORMATION.md) |
| 0xF0 | USN `$Max` (unnamed) | journal-size metadata on the Change Journal file (OID 0x520) | v3.4+, when the journal is active | [structures/usn_journal](../structures/usn_journal.md) |
| 0x100 | `$EFS` (`$LOGGED_UTILITY_STREAM`) | EFS encryption metadata (DDF + wrapped FEK) | v3.11+ (the driver's gate; seen on v3.14) | [EFS](EFS.md) |

Two pages of this section describe system tables rather than attributes of an object:

| Page | What it is | Where it lives | Detail |
|------|------------|----------------|--------|
| `$VOLUME_INFORMATION` | volume label, version, flags and times | rows of the volume-information table, OIDs 0x500 / 0x501 | [VOLUME_INFORMATION](VOLUME_INFORMATION.md) |
| Reparse Index | the global reparse-point index | rows of the system table at OIDs 0x540 / 0x541 | [REPARSE](REPARSE.md) |

## 4. NTFS attribute names with no ReFS equivalent

Several NTFS attribute names have no ReFS attribute of that name behind them. They appear in tools or literature
out of NTFS habit; the table says where the equivalent information lives on a ReFS volume:

| NTFS name | ReFS reality |
|-----------|--------------|
| `$FILE_NAME` | There is no standalone `$FILE_NAME` attribute. Names live in the directory-entry rows themselves (row type 0x30 of the directory's table; the driver's attribute table lists `$FILE_NAME` with that type code), keyed by the full long name. ReFS has no 8.3 short-name variant. See [Directory Entries](../structures/directory_entries.md). |
| `$ATTRIBUTE_LIST` | No attribute of that name. When a file's attribute set outgrows its record's embedded node it continues in child pages, the job `$ATTRIBUTE_LIST` does in NTFS (see [Attributes](../concepts/attributes.md)). On disk, type 0x20 is the FileId index: Format A repeats a name, Format B holds a home-directory back-reference. |
| `$INDEX_ALLOCATION` | The driver's attribute-definition table names type 0xA0 `$INDEX_ALLOCATION` and type 0x90 `$INDEX_ROOT`, as NTFS does; on disk the type-0x90 sub-record is the `$I30_INDEX` template, and type 0xA0 is not an embedded sub-record. |
| `$EXTEND` | A *directory*, not an attribute: OID 0x520 "FS Metadata" (the ReFS analogue of NTFS's `$Extend`, holding the Change Journal etc.). See [System OIDs](../structures/system_oids.md). |
| `$VOLUME_NAME` | No standalone attribute; the volume label is its own row (key 0x510) of the OID 0x500 table, beside the `$VOLUME_INFORMATION` blob. |
| `$OBJECT_ID` | The driver's attribute table lists the name with type 0x40, the type of a directory's backing-record rows; what that entry is used for is not read, and no NTFS-style object-id attribute is observed. A directory's identity is its OID, mapped by the [Object Table](../structures/object_table.md); a file's is its 128-bit reference (home-directory OID + ordinal). |
| `$OBSOLETE` | The driver's attribute table lists it with type 0x50; no on-disk structure of that type is known. |

The broader NTFS↔ReFS architectural mapping is in [NTFS vs ReFS](../concepts/ntfs_comparison.md).

## 5. How attributes look on disk

A directory's or system object's metadata is its own B+-tree, reached by OID through the Object Table (a file has
none — its attributes live in its name row in the parent directory, or in a type-0x40 backing in its home directory
once a move or a hard link has split it). A directory's tree decodes to rows of up to four kinds — for example a real
user directory:

```text
OID 0x701  (a user directory)
  Type 0x10  $STANDARD_INFORMATION — the own row (always exactly one)
  Type 0x20  FileId index          — keyed by FileId (see Reverse Index)
  Type 0x30  child name rows       — the directory's contents
  Type 0x40  backing records       — of the split files homed here
```

The type-0x10 own-row value is where the attributes live, laid out as `$SI` followed by the embedded sub-record
chain:

```text
type-0x10 value
  +0x00   record-node offset (0xA8: where the record's embedded node begins)
  +0x04   node descriptor (0x00010028)
  +0x28   $STANDARD_INFORMATION region:
            creation / modification / change / access FILETIMEs,
            file attributes, internal flags,
            SecurityId  ($SI+0x28)  -> resolves in the security table (OID 0x530),
            LastUsn     ($SI+0x40)  -> the USN: a virtual byte offset in $UsnJrnl:$J,
            UsnJournalId($SI+0x48)
  +0xA8   the embedded node (at the offset in +0x00); its rows are addressed through the node's key index,
          and on 3.7+ keys each begins [ value_length | marker | type code ]:
            marker 0x80000002 · type 0x39 $OBJ_LINK    -> parent OID + filename (one row per name)
            marker 0x80000002 · type 0x90 $I30_INDEX   -> directory-index template
            (a file's record — its embedded name-row value or its type-0x40 backing — carries instead:
             type 0x80 $DATA, optional 0xB0 ADS/$SNAPSHOT, 0xD0/0xE0 $EA, 0xC0 $REPARSE_POINT, 0x100 $EFS …)
```

A file has no own row: its record is the value of its type-0x30 row in its directory (or, once split, of its type-0x40
backing), with the `$SI` fields at `+0x28` and its attributes in the embedded node from `+0xA8`.

A real one, byte by byte (a 128-byte file of one of the published sample images, whose data is inline in its `$DATA`
sub-record), is drawn on the website's
[Directory entries](../structures/directory_entries.md#embedded-record-value-key_flags--0x01) page.

Tools decode this directly:

- `forefst.py <image> details 0x701` dumps the row types and `$SI` fields;
- `refsanalysis.py <image> details <path>` decodes the sub-records of an embedded record (a split record's backing is
  not decoded).

The exact offsets are on each attribute's detail page.

## 6. Differences from NTFS that matter forensically

- Attributes are embedded sub-records inside the object's row — a directory/system object's own B+-tree row, or a
  file's name row (or, for a split record, its type-0x40 backing in the home directory) — not entries in a central
  `$MFT`. Recovering an object's metadata means reaching its row through the Object Table, not scanning one table.
- Names are not a `$FILE_NAME` attribute — they live in directory-entry rows, and additionally in the type-0x20
  index (its Format A rows) and in the `$OBJ_LINK` backpointers of directories and split files. Those rebuild a
  directory's path from the Object Table alone, and list every name of a split file.
- No 8.3 short names — there is no short-name attribute or generation code.
- Security is by reference, as in NTFS 3.x: `$SI` stores a SecurityId, not an inline descriptor; the descriptor lives
  once in the security table (OID 0x530).
- On format 3.11 and later a file below 2 KiB keeps its `$DATA` inline unless a conversion moved it to extents — a
  higher ceiling than NTFS's; on 3.10 and earlier main `$DATA` is never inline. See
  [Record placement and data residency](../concepts/placement_and_residency.md).

## 7. The forensically important attributes

| Attribute | Why the analyst cares |
|-----------|------------------------|
| `$SI` | the MACB timestamps, file attributes, the SecurityId, and the per-file USN link (`LastUsn`) — the core of any timeline |
| `$OBJ_LINK` | every name + parent OID of a directory or a split file — rebuilds their paths even when directory trees are damaged; embedded files have none |
| `$DATA` | file content or its extent map — inline content can survive in node slack; extents drive carving |
| `$EA` / `$LX*` | WSL Linux UID/GID/mode/device — ownership and special-file identity for Linux-side artifacts |
| `$SNAPSHOT` / `$NAMED_DATA` | prior-version content (deterministic single-image recovery) and alternate data streams |
| `$EFS` | which key, certificate, and user are needed to decrypt — the pointers, though not the plaintext |

## 8. Attribute detail pages

[$DATA](DATA.md) · [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) · [$OBJ_LINK](OBJ_LINK.md) · [$I30_INDEX](I30_INDEX.md) · [$EA_INFORMATION / $EA](EA_INFORMATION.md) · [$EFS](EFS.md) · [$SNAPSHOT](SNAPSHOT.md) · [$NAMED_DATA](NAMED_DATA.md) · [$REPARSE_POINT](REPARSE_POINT.md) · [Reparse Index](REPARSE.md) · [$VOLUME_INFORMATION](VOLUME_INFORMATION.md)

## Evidence and verification

The attribute type codes are read from the decompiled driver (among others `RefsCheckValidAttributeAccess`,
`RefsLookupEasOnFile`, and the driver's attribute-definition table) and measured on the corpus; the schema ids from
the driver code that mounts a volume and creates each table. The key findings behind this page are the type-0x90/`$I30_INDEX` vs `$SI` distinction, the `$EFS`
metadata decoding, the WSL `$EA` chain and the per-file USN link; the page is documented against the project's claim
register. See [how this was verified](../methodology.md) for the evidence levels.

The sources behind the text:

- The record drawn byte by byte on Directory entries is a 128-byte file of the sample image `win11refstestmftecmd`.
- Type 0x70: zero sub-records in user objects across 111 images; the 3.4 driver reads reparse data as attribute
  type 0xC0.
- Snapshots and EAs: the 17134 (3.4) driver has no stream-snapshot code and no EA set path (it looks up a file's
  `$EA_INFORMATION` when the file is opened, and `RefsQueryEaInfo` returns a size from the in-memory file record); the 26100 and Insider drivers have both; no 3.7 to 3.10
  driver is held, and snapshot and EA records are seen only on 3.14 volumes of the corpus.
- An attribute set continued in child pages: 1,329 files over 19 of 99 images (4,094 records).

<!-- findings: FS_REPS_RA_002, FS_REPS_RA_003, FS_SNAP_RA_001, MD_ATTR_004, MD_ATTR_006, MD_ATTR_RA_010,
               MD_ATTR_RA_012, MD_ATTR_RA_015, MD_ATTR_RA_016, MD_SI_RA_013 -->
