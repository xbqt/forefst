# ReFS Attributes — Forensic Reference

A file's or directory's metadata in ReFS is a set of **typed attributes**. This page is the analyst's
entry point: what the real ReFS attributes are, how they are laid out on disk, which NTFS attribute
names have **no** ReFS equivalent, and which attributes carry the forensic weight. Each attribute has a
detailed byte-level page linked from the catalog below.

## 1. What a ReFS attribute is

In NTFS, a file's metadata is a list of typed attributes inside its `$MFT` record. ReFS keeps the same
idea but stores it differently. Every object — file, directory, or system table — has its **own
B+-tree**, reached by a 64-bit **Object ID (OID)** through the
[Object Table](../structures/object_table.md). The object's metadata lives in the rows of that tree,
and its attributes are **embedded sub-records inside the object's own row**, not a separate attribute
list.

So there are two layers:

- **Top-level row types** — the kinds of row in an object's B+-tree:

  | Row type | Role |
  |----------|------|
  | `0x10` | the object's **own row** — carries `$STANDARD_INFORMATION` (`$SI`) plus the embedded sub-record chain |
  | `0x20` | the **FileId reverse index** — a second copy of the name, keyed for FileId→name resolution |
  | `0x30` | a **resident** child directory entry (the child's metadata inlined in the parent) |
  | `0x40` | a **non-resident** child's out-of-line backing record (extents). A non-resident *directory* has its own OID and B+-tree; a non-resident *file* has **no** own OID — its data lives here, reached via the home-dir backref + child ordinal, not via the Object Table |

- **Embedded sub-records** — inside a `0x10` value (or a resident `0x30` value), the actual attributes
  (`$DATA`, `$OBJ_LINK`, `$I30_INDEX`, `$EA`, `$EFS`, …) are stored as embedded sub-records.

## 2. How attributes are organized

**Embedded sub-record markers.** Each embedded sub-record begins with a marker that says whether the
attribute may repeat:

| Marker | Meaning | Examples |
|--------|---------|----------|
| `0x80000001` | **single-instance** (at most one per object) | `$REPARSE_POINT` (0xC0), `$EA_INFORMATION` (0xD0), `$EA` (0xE0) |
| `0x80000002` | **multi-instance** (may repeat) | `$DATA` (0x80), `$SNAPSHOT`/ADS (0xB0), `$OBJ_LINK` (0x39), `$I30_INDEX` (0x90) |

**Schema numbering.** Attributes registered in the [Schema Table](../structures/schema_table.md) follow
the rule **schema = embedded type code + 0x100** (e.g. `$DATA` = type `0x80` → schema `0x180`). A few
embedded row types (`$OBJ_LINK` 0x38/0x39) have *no* `0x1xx` schema slot of their own. (`$I30_INDEX` 0x90 *does* follow the rule — schema `0x190`.)

**`$SI` is the own-row itself, not a sub-record.** A common trap: `$STANDARD_INFORMATION` is **not** an
embedded `0x90` sub-record — it occupies the fixed region of the `0x10` own-row value. The embedded
type-`0x90` sub-record is `$I30_INDEX` (the directory-index template), a different thing that happens to
share the schema slot 0x190. Read `$SI` only from a type-`0x10` row.

**The `$EA` chain (WSL / Linux metadata).** Extended attributes are a two-part structure:
`$EA_INFORMATION` (type 0xD0) is the size index; `$EA` (type 0xE0) is the body — a standard NT
`FILE_FULL_EA_INFORMATION` chain. WSL stores Linux ownership inside that chain as named EAs —
`$LXUID`, `$LXGID`, `$LXMOD`, `$LXDEV` (and kernel-cache state as `$Kernel.Purge.*`). These are **EA
entries, not standalone attribute types**; see [$EA_INFORMATION and $EA](EA_INFORMATION.md).

## 3. The attribute catalog

The real ReFS attributes, by schema (cross-checked against the master schema roster). Type code =
schema − 0x100.

| Schema | Type | Attribute | What it is | Versions | Detail |
|--------|------|-----------|------------|----------|--------|
| — | `0x10`-row | **`$STANDARD_INFORMATION`** (`$SI`) | timestamps, file attributes, SecurityId, USN link — the object's own-row metadata | v3.4+ | [structures/standard_information](../attributes/STANDARD_INFORMATION.md) |
| 0x150 | 0x50 | **`$VOLUME_INFORMATION`** | volume label, version, flags (system OIDs 0x500/0x501) | v3.4+ | [VOLUME_INFORMATION](VOLUME_INFORMATION.md) |
| 0x160 | 0x60 | **Reparse Index** | the global reparse-point index attribute (OID 0x540/0x541) | v3.4+ | [REPARSE](REPARSE.md) |
| 0x170 / 0x1C0 | 0x70 / 0xC0 | **`$REPARSE_POINT`** | per-file reparse data (symlink / junction / mount / WSL node) | v3.4 (0x70) → v3.7+ (0xC0) | [REPARSE_POINT](REPARSE_POINT.md) |
| 0x180 | 0x80 | **`$DATA`** | the default data stream — inline (resident) or extent references (non-resident) | v3.4+ | [DATA](DATA.md) |
| 0x190 | 0x90 | **`$I30_INDEX`** | the embedded directory-index configuration template (the "$I30" template; *not* `$SI`) | v3.4+ | [I30_INDEX](I30_INDEX.md) |
| 0x1A0 | 0xA0 | **`$INDEX_ROOT`** | the directory-index attribute ("extended attributes index"); *not* an embedded sub-record | v3.4+ | (naming note in [I30_INDEX](I30_INDEX.md)) |
| 0x1B0 | 0xB0 | **`$SNAPSHOT`** / **`$NAMED_DATA`** | stream snapshots and named data streams (ADS) share type 0xB0, distinguished by the StreamSummary flag | v3.7+ | [SNAPSHOT](SNAPSHOT.md), [NAMED_DATA](NAMED_DATA.md) |
| 0x1D0 | 0xD0 | **`$EA_INFORMATION`** | extended-attribute size index | v3.7+ | [EA_INFORMATION](EA_INFORMATION.md) |
| 0x1E0 | 0xE0 | **`$EA`** | extended-attribute body (carries the WSL `$LX*` names) | v3.14+ | [EA_INFORMATION](EA_INFORMATION.md) |
| 0x1F0 | 0xF0 | **USN `$Max`** (`$LOGGED_UTILITY_STREAM`) | journal-size metadata on the Change Journal file (OID 0x520) | v3.14+ schema; attr v3.4-era when the journal is active | [structures/usn_journal](../structures/usn_journal.md) |
| 0x200 | 0x100 | **`$EFS`** (`$LOGGED_UTILITY_STREAM`) | EFS encryption metadata (DDF + wrapped FEK) | v3.11+ | [EFS](EFS.md) |
| — | 0x38 / 0x39 | **`$OBJ_LINK`** | object→primary-name backpointer (parent OID + name) embedded in the own-row | v3.4 (0x38) → v3.7+ (0x39) | [OBJ_LINK](OBJ_LINK.md) |

The remaining attribute-schema slots are **structural**, not per-file attributes: `0x110` / `0x120` /
`0x130` / `0x140` are the directory-entry, file-stream, and filename schemas — the rows of a directory's
B+-tree (see [Directory Entries](../structures/directory_entries.md); `$FILE_NAME` is covered in §4) —
and `0x04` / `0x06` are legacy allocator schemas retired at v3.14.

## 4. NTFS attribute names with no ReFS equivalent

Several NTFS attribute names have no ReFS attribute behind them. They appear in tools or literature out
of NTFS habit, but on a ReFS volume there is nothing to read under these names:

| NTFS name | ReFS reality |
|-----------|--------------|
| **`$FILE_NAME`** | There is **no standalone `$FILE_NAME` attribute**. Names live in the **directory-entry rows** themselves (type 0x30 / schema 0x130 and type 0x40 / schema 0x140), keyed by the full long name. ReFS has **no 8.3 short-name** variant. See [Directory Entries](../structures/directory_entries.md). |
| **`$ATTRIBUTE_LIST`** | No equivalent (ReFS attributes do not span multiple records). On disk, **type 0x20 is the per-object FileId reverse index** — a second copy of the filename keyed for FileId→name resolution. |
| **`$INDEX_ALLOCATION`** | NTFS name only. The directory-index attribute is **`$INDEX_ROOT`** (type 0xA0 / schema 0x1A0); the embedded directory-index template is **`$I30_INDEX`** (type 0x90). Neither is a separate `$INDEX_ALLOCATION`. |
| **`$EXTEND`** | A *directory*, not an attribute: **OID 0x520 "FS Metadata"** (the ReFS analogue of NTFS's `$Extend`, holding the Change Journal etc.). See [System OIDs](../structures/system_oids.md). |
| **`$VOLUME_NAME`** | No standalone attribute; the volume label lives inside **`$VOLUME_INFORMATION`** (schema 0x150). |
| **`$OBJECT_ID`** | No schema slot. Object identity is the **OID** itself, mapped by the [Object Table](../structures/object_table.md). |
| **`$OBSOLETE`** | A binary string literal only — no schema slot and no observed on-disk structure. |

The broader NTFS↔ReFS architectural mapping is in [NTFS vs ReFS](../concepts/ntfs_comparison.md).

## 5. How attributes look on disk

An object's metadata is its own B+-tree, reached by OID through the Object Table. A directory's tree
decodes to rows of three kinds — for example a real user directory:

```
OID 0x701  (a user directory)
  Type 0x10  $STANDARD_INFORMATION — the own row (always exactly one)
  Type 0x20  FileId reverse index  — one row per child name
  Type 0x30  resident child entries — the directory's contents
```

The **type-0x10 own-row value** is where the attributes live, laid out as `$SI` followed by the
embedded sub-record chain:

```
type-0x10 value
  +0x00   sub-record header (content begins at the offset stored in +0x04, = 0x28)
  +0x28   $STANDARD_INFORMATION region:
            creation / modification / change / access FILETIMEs,
            file attributes, internal flags,
            SecurityId  ($SI+0x28)  -> resolves in the security table (OID 0x530),
            LastUsn     ($SI+0x40)  -> byte offset in $UsnJrnl:$J,
            UsnJournalId($SI+0x48)
  +0xA8+  embedded sub-record chain — each entry = [ value_length | marker | type code | value ]:
            marker 0x80000002 · type 0x39 $OBJ_LINK    -> parent OID + primary filename
            marker 0x80000002 · type 0x90 $I30_INDEX   -> directory-index template
            (a file would instead carry: type 0x80 $DATA, optional 0xB0 ADS/$SNAPSHOT,
             0xD0/0xE0 $EA, 0xC0 $REPARSE_POINT, 0x100 $EFS …)
```

Tools decode this directly — `forefst.py <image> details 0x701` dumps the row types and `$SI` fields, and
`refsanalysis.py <image> details <path>` decodes the embedded sub-records. The exact offsets are on each
attribute's detail page and in `structure_reference.md`.

## 6. Differences from NTFS that matter forensically

- **Attributes are embedded sub-records in the object's own B+-tree row**, not entries in a central
  `$MFT`. Recovering an object's metadata means reaching its row through the Object Table, not scanning
  one table.
- **Names are not a `$FILE_NAME` attribute** — they live in directory-entry rows, and additionally in
  the type-0x20 reverse index and the `$OBJ_LINK` backpointer (which enables path reconstruction from
  the Object Table alone).
- **No 8.3 short names** — there is no short-name attribute or generation code.
- **Security is by reference** — `$SI` stores a **SecurityId**, not an inline descriptor; the descriptor
  lives once in the security table (OID 0x530).
- **The resident-storage threshold is much higher** than NTFS's, so far more files keep their `$DATA`
  inline. See [Resident vs Non-Resident Storage](../concepts/resident_storage.md).

## 7. The forensically important attributes

| Attribute | Why the analyst cares |
|-----------|------------------------|
| **`$SI`** | the MACB timestamps, file attributes, the SecurityId, and the per-file USN link (`LastUsn`) — the core of any timeline |
| **`$OBJ_LINK`** | the primary name + parent OID embedded in every object — reconstructs paths even when directory trees are damaged |
| **`$DATA`** | file content and its extent map — resident content survives inline in node slack; non-resident extents drive carving |
| **`$EA` / `$LX*`** | WSL Linux UID/GID/mode/device — ownership and special-file identity for Linux-side artifacts |
| **`$SNAPSHOT` / `$NAMED_DATA`** | prior-version content (deterministic single-image recovery) and alternate data streams |
| **`$EFS`** | which key, certificate, and user are needed to decrypt — the pointers, though not the plaintext |

## 8. Attribute detail pages

[$DATA](DATA.md) · [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) · [$OBJ_LINK](OBJ_LINK.md) · [$I30_INDEX](I30_INDEX.md) · [$EA_INFORMATION / $EA](EA_INFORMATION.md) · [$EFS](EFS.md) · [$SNAPSHOT](SNAPSHOT.md) · [$NAMED_DATA](NAMED_DATA.md) · [$REPARSE_POINT](REPARSE_POINT.md) · [Reparse Index](REPARSE.md) · [$VOLUME_INFORMATION](VOLUME_INFORMATION.md)

## Evidence and verification

The attribute type codes and schemas are confirmed in both the decompiled driver (`E2` — e.g.
`RefsCheckValidAttributeAccess`, `RefsLookupEasOnFile`) and on the raw-disk corpus (`RD`), and are
recorded in `structure_reference.md` §F.2. Key findings behind this page: the type-0x90/`$I30_INDEX`
vs `$SI` distinction (MD_ATTR_RA_015/FS_SNAP_RA_001), the `$EFS` metadata decoding, the WSL `$EA` chain
(FS_REPS_RA_003, FS_REPS_RA_002, MD_ATTR_RA_010, MD_ATTR_RA_012), and the per-file USN link (MD_SI_RA_013). See [how this was verified](../methodology.md) for the
methodology, the evidence levels, and how to trace any of these to the exact images and measurements in
the project's `analysis/` tree.
