# Reverse Index (Type 0x20)

Type 0x20 is the per-**object** FileId-resolution index: rows keyed by a FileId (object reference / child index)
that let the driver, given a file reference, recover one of two things:

- the object's **name** (Format A);
- where its record is (Format B): the record itself, for a type-0x40 backing, or the directory a move carried it
  to.

It is not strictly a directory reverse index — the rows live in each index object's own B+-tree, created during
normal file/dir creation and move.

The home-directory back-pointer it stores is the same **creation-directory** reference that forms the upper half of a
file's [FileRef](../concepts/file_ids.md); a cross-directory move inserts a Format B row rather than re-homing the
identity.

## Key format — 24 bytes

All user-OID type 0x20 keys are 24 bytes:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Type marker (u32) | 0x80000020 (type 0x20 with instance flag) |
| 0x04 | 4 | Reserved (u32) | Always 0 |
| 0x08 | 8 | Child index (u64) | Monotonically-increasing per-directory ordinal |
| 0x10 | 8 | Reserved (u64) | Always 0 |

The child index is NOT the child's OID — it is a sequential number assigned within the directory.

## Value Format A — Filename Entry (type_flag = 0)

Variable length. Maps a child index to a UTF-16LE filename.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Type flag (u32) | 0x00000000 |
| 0x04 | 4 | Padding (u32) | Always 0 |
| 0x08 | 2 | Name offset (u16) | Always 0x000C (12) |
| 0x0A | 2 | Name byte length (u16) | The name's UTF-16LE length in bytes, without a terminator |
| 0x0C | var | Filename | UTF-16LE, not NUL-terminated |

Value sizes range 24--104 bytes depending on filename length.

## Value Format B — Linked Entry (24 bytes)

Fixed 24 bytes, in two kinds told apart by the type flag:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Type flag (u32) | 2: a backing's self-reference; 1: a moved record's forward pointer |
| 0x04 | 4 | Padding (u32) | Always 0 |
| 0x08 | 8 | FileID / child index (u64) | Type 2: the same value as key[0x08:0x10]. Type 1: the record's ordinal in the directory that now holds it |
| 0x10 | 8 | Directory OID (u64) | Type 2: the table's own OID. Type 1: the directory that now holds the record |

- **Type 2, a backing's self-reference.** Every file record stored as a type-0x40 backing has one, keyed by its
  ordinal and pointing at itself (`RefsLinkFileToSelf`).
- **Type 1, a forward pointer.** On a volume without hard-link support, a cross-directory move carries the whole
  record into the destination directory. The file keeps its reference (home directory : ordinal), and its home
  directory keeps a type-1 row under that ordinal, naming the directory and the ordinal where the record now is. From a
  moved file's reference, this row tells where to find it.

The type is not a format version: the 17134 driver (Windows 10 1803) writes only type 1, and the 26100 driver
writes either, by the caller.

## Coverage

One type 0x20 row per **file record**, in the directory whose table holds it, keyed by its ordinal:

- an **embedded** record (in its name row) has a Format A row with its name;
- a **backing** (type 0x40) has a type-2 Format B row;
- a record **moved** out of its home directory (no hard-link support) leaves a type-1 Format B row in the home
  directory.

Subdirectories have none, and a multi-name file's extra names have none of their own. (No file has its own
Object-Table OID: an embedded record carries its table descriptor's flags (1) and schema id at val+0x08 (read together as one u64), while a
split record's name row carries its home-dir backref there — a real *directory* OID, not an OID of its own.)

A home directory whose files were moved out keeps their type-1 rows after their names have gone, so it can hold
more type 0x20 rows than names (on the corpus volumes with moved records: 15 of 34 directories on one, 32 of 149 on
another); elsewhere each row has a record beside it, except 65 Format A rows on two volumes (the
`win11refs2tmillionsofactions` images, whose checkpoint roots fail their digests, and `labM_after_rebuilt`).

Case-sensitive files that differ only in case get distinct FileIds and distinct type 0x20 child indices, so they coexist as separate B+-tree entries.

## System OID Type 0x20

System OIDs 0x7 and 0x8 have a different type 0x20 format: 4-byte keys (`0x20000000`) with 341-byte values. OIDs
0x7 and 0x8 are the [Upcase Table](upcase_table.md), whose data rows are fragments of up to 341 bytes of the case
map; whether these rows are such fragments has not been checked.

OID 0x520 (FS Metadata directory) uses the standard 24-byte key format for its named children ("Volume Direct IO
File", "Security Descriptor Stream", "Reparse Index"; on 3.4 and 3.7 volumes and those upgraded from them).

## Open questions

1. **What determines the child index assignment?** The value comes from the directory's increment-only counter
   (the u64 at +0x50 of its Object-Table record) and is never reused; values are not always contiguous — gaps
   suggest deleted entries.
2. **System OID type 0x20 format**: whether the 341-byte values at OIDs 0x7 and 0x8 are Upcase Table fragments
   has not been checked.

## Cross-references

- [Directory Entries](directory_entries.md) — the type 0x30 filename rows this index resolves back from a FileId
- [File IDs](../concepts/file_ids.md) — the FileRef identity this index resolves, and why its home back-reference is the creation directory
- [Object Table](object_table.md) — the back-ref parent OID in Format B resolves via the Object Table

## Evidence

The type 0x20 semantics — the per-object FileId-resolution role, the Format A / Format B split, and the type (1 or 2) each caller passes — are read in the decompiled driver, in the creation/move routines `RefsCreateFileId2` / `RefsLinkFileToSelf` (`RefsFindFileId`); `RefsQueueTriageForDeadFileId` is only the read-time triage path, not the creator. The 24-byte key layout, the two value formats, the coverage rule, and the system-OID variant are decoded from the disk across the corpus. The page's other field-level statements are registered findings, each with its own evidence tier and witness in the claim register.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

<!-- findings: FN_DTBL_003, MD_CS_RA_002, MD_DISK_RA_009 -->
