# Reverse Index (Type 0x20)

Type 0x20 is the per-**object** FileId-resolution index: rows keyed by a FileId (object reference / child index) that let the driver, given a file reference, recover either the object's **name** (Format A) or its **home-directory back-pointer** (Format B). It is not strictly a directory reverse index — the rows live in each index object's own B+-tree, created during normal file/dir creation and move.

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
| 0x0A | 2 | Name byte length (u16) | UTF-16LE length including null terminator |
| 0x0C | var | Filename | UTF-16LE, null-terminated |

Value sizes range 24--104 bytes depending on filename length.

## Value Format B — Linked Entry (home-directory back-reference)

Fixed 24 bytes. This is the object's **home-directory back-reference**, created for subdirectories (and cross-directory moves / re-link) when a `_REFS_FILE_REFERENCE` is passed instead of a name. It is present on **all versions** (v3.4 onward).

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Type flag (u32) | 1 on v3.4, 2 on v3.7+ |
| 0x04 | 4 | Padding (u32) | Always 0 |
| 0x08 | 8 | FileId / child index (u64) | Same value as key[0x08:0x10] |
| 0x10 | 8 | Back-ref parent OID (u64) | v3.4: real parent directory OID; v3.7+: containing OID (self-referencing) |

The encoding differs by version:

- **v3.4**: `type_flag = 1`, and the back-pointer points at the **REAL parent directory OID** (a genuine, non-self-referencing home reference). `RefsCreateFileId2` hard-codes `1` and copies the home-directory reference.
- **v3.7+**: `type_flag = 2`, **self-referencing** — `RefsLinkFileToSelf` passes the object's own reference.

A scan that only counts `type_flag = 2` will report zero Format B on v3.4 — that is a classifier blind spot, not an absence. On v3.4, Format B is present but appears as `type_flag = 1` (non-self-referencing, pointing at the real parent directory OID).

## Coverage

Not every type 0x30 child has a corresponding type 0x20 entry. Resident files — identified by the sentinel at child_oid (val+0x08) >= 0x10000000000 — typically lack type 0x20 entries. (No file has its own Object-Table OID: a resident file carries that sentinel at val+0x08, while a non-resident file carries its home-dir backref there — a real *directory* OID, not an OID of its own.) The total type 0x20 count per directory is always <= the type 0x30 child count.

Case-sensitive files that differ only in case get distinct FileIds and distinct type 0x20 child indices, so they coexist as separate B+-tree entries.

## System OID Type 0x20

System OIDs 0x7 and 0x8 have a different type 0x20 format: 4-byte keys (`0x20000000`) with 341-byte values that appear to be bitmap/allocation data. OID 0x520 (FS Metadata directory) uses the standard 24-byte key format for its named children ("Volume Direct IO File", "Security Descriptor Stream", "Reparse Indexs").

## Open questions

1. **What determines the child index assignment?** Values are monotonically increasing but not always contiguous — gaps suggest deleted entries.
2. **System OID type 0x20 format**: The 341-byte values at OIDs 0x7 and 0x8 have not been decoded.

## Cross-references

- [Directory Entries](directory_entries.md) — the type 0x30 filename rows this index resolves back from a FileId
- [Object Table](object_table.md) — the back-ref parent OID in Format B resolves via the Object Table

## Evidence

The type 0x20 semantics — the per-object FileId-resolution role, the Format A / Format B split, and the `type_flag` 1→2 transition at v3.7 — are decompilation-grounded (E2) in the creation/move routines `RefsCreateFileId2` / `RefsLinkFileToSelf` (`RefsFindFileId`); `RefsQueueTriageForDeadFileId` is only the read-time triage path, not the creator. The 24-byte key layout, the two value formats, the coverage rule, and the system-OID variant are raw-disk decoded (RD) across the corpus. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
