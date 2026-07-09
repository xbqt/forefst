# Attributes

In NTFS every piece of a file — its name, its timestamps, its data, its security — is an *attribute*,
and a parser that knows how to walk the attribute list can read the whole file. ReFS keeps the same
vocabulary (`$STANDARD_INFORMATION`, `$FILE_NAME`, `$DATA`, `$REPARSE_POINT`, `$EA`) but stores
attributes in a fundamentally different shape: not a flat list inside one record, but **two nested
levels of B+-tree**. The outer level is the object's own B+-tree, located through the
[Object Table](../structures/object_table.md); the inner level is a *mini B+-tree* embedded inside a
single value. A tool that does not understand both levels will see a file's name and timestamps and miss
its data streams, its alternate data streams, its reparse target, and its extended attributes entirely.
This page explains the two-level model, how to tell a genuine attribute from a coincidence in the bytes,
and where each attribute physically lives.

## Two levels, and why

ReFS gives every object its own B+-tree. The rows of that tree are keyed, and the **first two bytes of
the key** name what the row is. For user objects (OID ≥ 0x600) there are only **four** outer key types,
and that small set is the whole top-level attribute vocabulary:

| Key type | What it is | Forensic role |
|----------|-----------|---------------|
| 0x10 | `$STANDARD_INFORMATION` + the embedded sub-record tree | timestamps, flags, security ID — and the container for everything in level 2 |
| 0x20 | [Reverse Index](../structures/reverse_index.md) | parent → child back-reference, used for orphan detection |
| 0x30 | `$FILE_NAME` / [directory entries](../structures/directory_entries.md) | the child names a directory holds |
| 0x40 | [Extent Descriptors](../structures/extent_descriptors.md) | the data-run allocation of a non-resident file |

No user object ever has an outer key of 0x80, 0x90, 0xA0, 0xB0, 0xC0, 0xD0, 0xE0, 0xF0, or 0x100 — those
codes only ever appear one level down. This matters because an NTFS-trained eye expects `$DATA` (0x80) or
`$REPARSE_POINT` (0xC0) to be siblings of `$FILE_NAME` in the same record. In ReFS they are not. They are
**sub-records nested inside a value**, and you reach them by descending.

The descent happens in two places. The type-0x10 value carries `$SI` followed by an *embedded mini
B+-tree*, and the resident type-0x30 directory value carries the same embedded tree after its own header.
Both use one shared row format (described under [Resident Storage](resident_storage.md) and on the
[directory entries](../structures/directory_entries.md) page). The rows of that inner tree are the second
level of the attribute system — the level that actually holds the file's content and most of its
metadata.

## The genuine sub-record set, and the trap

A raw scan that just looks for known type codes in the value bytes will lie to you. ASCII fragments of
file content and structural rows of system objects can land a plausible-looking byte (0x00, 0x01, a
two-character string interpreted as `0x322d`) exactly where a type code would sit. The discriminator that
removes this noise is the **instance marker**: from v3.7 onward, every genuine embedded sub-record key
carries a 4-byte marker immediately before its type code.

- **0x80000001 — single-instance (SI):** at most one of this attribute per file.
- **0x80000002 — multi-instance (MI):** zero or more per file (a file can have many `$DATA` streams).

**Always gate on the marker before trusting a type code.** Under strict marker gating the spurious codes
vanish and the genuine set collapses to **exactly ten** type codes — no more, no less:

| Type | Attribute | Instance | What it stores |
|------|-----------|----------|----------------|
| 0x38 (v3.4) / 0x39 (v3.7+) | [`$OBJ_LINK`](../attributes/OBJ_LINK.md) | MI | the file/dir name plus its parent OID |
| 0x80 | [`$DATA`](../attributes/DATA.md) | SI + MI | default and named data streams |
| 0x90 | [`$I30_INDEX`](../attributes/I30_INDEX.md) | MI | the `$I30` directory-index configuration |
| 0xB0 | [`$SNAPSHOT` / `$NAMED_DATA`](../attributes/SNAPSHOT.md) | MI | snapshots and alternate data streams (ADS) |
| 0xC0 | [`$REPARSE_POINT`](../attributes/REPARSE.md) | SI | symlinks, junctions, mount points |
| 0xD0 | [`$EA_INFORMATION`](../attributes/EA_INFORMATION.md) | SI | extended-attribute size header |
| 0xE0 | `$EA` | SI | the extended-attribute body (WSL `$LX*`) |
| 0xF0 | `$LOGGED_UTILITY_STREAM` | SI | USN-journal `$Max` metadata (see below) |
| 0x100 | [`$EFS`](../attributes/EFS.md) | MI | encryption metadata |

On v3.4 there are no markers at all: the type code is stored directly as a 32-bit value in the same
position, and a v3.4 parser must gate on the type-code *enum* instead. The marker scheme is the v3.7
generation's addition.

Three codes look like they belong in this set but never do. They are **not** embedded sub-records, and a
marker-gated scan finds zero of them as type-0x10 or type-0x30 rows:

| Type | Name | Where it actually lives |
|------|------|-------------------------|
| 0x50 | [`$VOLUME_INFORMATION`](../attributes/VOLUME_INFORMATION.md) | volume-level metadata, never a per-file row |
| 0x60 | Reparse Index | the table-level reparse-tag index on a system OID |
| 0xA0 | `$INDEX_ROOT` | handled at object-create time by `RefsCheckValidAttributeAccess`, never persisted as a file sub-record |

The genuine ten and the three non-members are confirmed by the driver's attribute-validation path
(`RefsGetAttributeTypeCode`, `RefsGetAttributeDefinition`, `RefsCheckValidAttributeAccess`) and by a
marker-gated scan of the raw-disk corpus.

### The 0xF0 case is not a mystery stream

`$LOGGED_UTILITY_STREAM` (type 0xF0) is sometimes filed as an "unknown logged-utility stream." It is not.
It is the **USN journal `$Max` metadata** — a single-instance sub-record on the Change Journal file under
the system object OID 0x520, holding the journal's maximum size (the familiar `fsutil usn createjournal`
sizes such as 128 MB or 32 MB). It is created by `RefsSetupUsnJournal` and has existed since v3.4, but it
is only present where the [USN journal](../structures/usn_journal.md) has actually been activated, which
is why it is rare on disk. EFS, despite also being a "logged utility stream" in name, uses a *different*
code path (type 0x100) — do not conflate the two.

## Where each attribute physically lives

The same attribute can be stored in three different places depending on the file's
[residency](resident_storage.md), and knowing which place to read is half of parsing ReFS correctly:

| Attribute | In the type-0x10 value | In a resident type-0x30 value | When non-resident |
|-----------|------------------------|-------------------------------|-------------------|
| `$SI` | always (inline, before the embedded tree) | N/A | N/A |
| `$OBJ_LINK` | always (0x38/0x39) | N/A | N/A |
| `$I30_INDEX` | always (0x90) | N/A | N/A |
| `$DATA` | never | SI + MI (0x80) | content via type-0x40 [extents](../structures/extent_descriptors.md) |
| `$SNAPSHOT` | never | MI (0xB0) | content via type-0x40 extents |
| `$REPARSE_POINT` | rare | SI (0xC0) | — |
| `$EA_INFORMATION` | rare | SI (0xD0) | — |
| `$EA` | rare | SI (0xE0) | — |
| `$EFS` | never | MI (0x100) | — |
| Reverse Index | N/A | N/A | type 0x20 at the object level |
| Extent descriptors | N/A | N/A | type 0x40 at the object level |

The recurring pattern: a *directory's* attributes hang off its type-0x10 tree, while a *file's* content
and stream attributes live in the resident type-0x30 directory entry the parent holds for it. A small
file's `$DATA` is inline in that entry; a large file's `$DATA` is replaced by [extent
descriptors](../structures/extent_descriptors.md) that point — through [virtual
addressing](virtual_addressing.md) — at clusters elsewhere on the volume.

## The shared sub-record value header

Every embedded sub-record value (types 0x80 through 0xE0, both SI and MI) opens with the same 12-byte
prefix, which is how a parser can begin decoding any of them before it knows the specific type:

| Offset | Size | Field | Value |
|--------|------|-------|-------|
| 0x00 | 4 | padding | always 0 |
| 0x04 | 4 | data-area size | total value bytes minus 12 |
| 0x08 | 4 | content offset | always 0x0C |

Type-specific content then begins at value+0x0C:

| Type | Content at value+0x0C | Inline data at |
|------|-----------------------|----------------|
| 0x80 SI (`$DATA`) | 48-byte stream summary | value+0x3C (the file's bytes) |
| 0x80 MI (`$DATA`) | does **not** use the common header — extent/allocation metadata instead | — |
| 0xB0 (`$SNAPSHOT` / ADS) | 48-byte stream summary, same shape as SI `$DATA` | value+0x3C (the ADS bytes) |
| 0xC0 (`$REPARSE_POINT`) | a `REPARSE_DATA_BUFFER` (reparse tag + data) | value+0x0C |
| 0xD0 (`$EA_INFORMATION`) | PackedEaSize @0x0C (NTFS packed size, written to `$SI+0x50`) + serialized on-disk footprint @0x10, fixed 20B | — |
| 0xE0 (`$EA`) | a `FILE_FULL_EA_INFORMATION` chain | value+0x0C |

The one exception worth remembering is **MI `$DATA`**: it carries extent/allocation metadata, not the
common header, so a parser must branch on the marker before assuming the 12-byte prefix is present. This
value layout is stable across every version from v3.4 through Insider build 29574; only the *key* format
changed (the v3.7 instance markers).

## Snapshots versus ADS: one type, two meanings

Type 0xB0 does double duty — it is both a [snapshot](snapshots_versioning.md) and an alternate data
stream — so a parser must decide which it is looking at. Two independent discriminators agree, and either
can be used:

1. **Stream-summary flags at value+0x10 (u16):** 0 means ADS, 2 means snapshot. The driver sets the bit
   in `RefsCreateStreamSnapshot` (`StreamSummary |= 2`); `forefst.py` reads this.
2. **Attribute flags at value+0x02 (u16):** bit 0x0400 (`HasSnapshot`) is set only on snapshots, and the
   driver's `HasSnapshot` predicate reads it.

For an ADS, the stream name is in the key starting at offset 16 (UTF-16LE). The corrected value layout is
on the [`$SNAPSHOT`](../attributes/SNAPSHOT.md) page.

## WSL extended attributes

When WSL stores Linux ownership and permissions on a ReFS file (the `-o metadata` mount), it does so
through `$EA_INFORMATION` and `$EA` in the standard Windows `FILE_FULL_EA_INFORMATION` format — *not* in
reparse data. The names a forensic tool should recognise:

| EA name | Size | Meaning |
|---------|------|---------|
| `$LXUID` | 4 | Linux UID |
| `$LXGID` | 4 | Linux GID |
| `$LXMOD` | 4 | mode bits (file-type `S_IFMT` plus permissions) |
| `$LXDEV` | 8 | device number (u32 major + u32 minor) — only on device nodes |

The file attribute flag 0x40000 in the type-0x30 value flags the presence of extended attributes. WSL
special files (FIFOs, sockets, character/block devices) additionally appear as
[reparse points](../structures/reparse_points.md) whose tag encodes the Linux file type, with the type
also reflected in the upper bits of `$LXMOD`. See [WSL metadata](wsl_metadata.md) for the full mapping.

## A note on system objects

System objects (OID < 0x600) reuse the key *position* for table-specific identifiers rather than
attribute type codes: the Security Descriptors table (OID 0x530) keys on the SecurityId, the Reparse
Index (OID 0x540/0x541) keys on a fixed 0x01, and the [Schema Table](../structures/schema_table.md) keys
on a schema ID. These are not attributes — do not feed them through the attribute decoder.

## Cross-references

- [Resident Storage](resident_storage.md) — the embedded-tree row format and the inline-vs-extent decision
- [Directory Entries](../structures/directory_entries.md) — the type-0x30 value that holds a file's resident attributes
- [Object Table](../structures/object_table.md) — locates each object's top-level B+-tree
- [Schema Table](../structures/schema_table.md) — the attribute-schema registry (0x110–0x200)
- [Standard Information](../attributes/STANDARD_INFORMATION.md) — the `$SI` field layout in the type-0x10 value
- [`$OBJ_LINK`](../attributes/OBJ_LINK.md) — name + parent-OID format of the always-present 0x38/0x39 sub-record
- [`$DATA`](../attributes/DATA.md) and [`$SNAPSHOT`](../attributes/SNAPSHOT.md) — the 0x80 / 0xB0 stream sub-records
- [`$EFS`](../attributes/EFS.md) — the 0x100 encryption sub-record
- [Extent Descriptors](../structures/extent_descriptors.md) — where a non-resident file's `$DATA` content lives
- [WSL metadata](wsl_metadata.md) — the `$LX*` extended-attribute mapping

## Evidence

The four outer key types and the ten genuine sub-record codes (with the 0x50/0x60/0xA0 non-members)
are confirmed in the driver's attribute path — `RefsGetAttributeTypeCode`, `RefsGetAttributeDefinition`,
`RefsCheckValidAttributeAccess` (E2) — and by a marker-gated raw-disk scan of the corpus (RD), which
yields exactly this set with zero extras. The instance-marker scheme (0x80000001 / 0x80000002, v3.7+) and
the per-type value formats are E2+RD. The 0xF0 = USN `$Max` identification is E2 (`RefsSetupUsnJournal`)
plus RD on the images where the journal is active. The 0xB0 snapshot/ADS discriminators are E2
(`RefsCreateStreamSnapshot`, `HasSnapshot`) confirmed across the snapshot/ADS corpus (RD). The directory
attribute flag 0x10000000 is finding **MD_DDIR_005**. Findings: **FS_SNAP_RA_001** (the complete
dual-marker taxonomy), **FS_SCHM_RA_005/006/007** (schemas 0x1B0–0x200), **MD_ATTR_005/008/010** (`$DATA`,
`$REPARSE_POINT`, EA), **MD_ATTR_RA_003** (the 0x40000 EA-present flag). See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
