# Upcase Table

The Upcase Table (OID 0x07 primary, OID 0x08 duplicate, schema 0xe090) stores the Unicode
uppercase mapping that ReFS uses for case-insensitive filename comparison in directory B+-trees.
The content is a fixed Windows Unicode constant written at format time, identical on every version.

## Logical table

Once loaded into memory, the comparison code sees a flat array:

| Property | Value |
|----------|-------|
| Entry count | 65,536 (one per UTF-16 code unit, U+0000 through U+FFFF) |
| Entry size | 2 bytes (u16) |
| Total size | 131,072 bytes (128 KiB) |
| Non-identity mappings | 973 characters whose uppercase differs from the character itself |
| Content | Identical across all versions (v3.4 through Insider) |

In the reconstructed logical array, the entry at index N is the uppercase equivalent of code
point U+N: for the 973 non-identity entries the stored value differs from the index; for every
other entry it equals the index (identity mapping).

## On-disk B+-tree

On disk the table is **not** a flat 128 KiB blob — it is a **387-row B+-tree** (schema 0xe090):

| Row | Key | Contents |
|-----|-----|----------|
| Name row | key = 0 | the table name `"Upcase Table"` (as other system tables carry their name) |
| Data rows (~386) | sequential row index | value fragments (variable length, 4–341 bytes) |

The data-row values **concatenate, in key order**, to the ~131 KiB logical map (a short leading
header precedes the 65,536-entry array). The row count is the same on v3.4 and v3.14, and the
concatenated content is byte-for-byte identical across versions — confirming a Windows Unicode
constant written at format time rather than a version-specific structure.

## How it is used

ReFS performs case-insensitive filename comparison by mapping each UTF-16 character through this
table before comparison. The `CmsKeyRules` class consults the Upcase Table for B+-tree key
comparisons in directory tables. At mount time, `CmsVolume::InitializeUpcaseTable` loads OID 0x07
into memory.

## Dual pair and shared schema

OID 0x07 (primary) and OID 0x08 (duplicate) form a failover pair; both carry schema 0xe090.
Schema 0xe090 is **shared** between the Upcase Table (OIDs 0x07/0x08) and the Logfile Info table
(OIDs 0x09/0x0A), which stores MLog metadata.

## Case-sensitive directories

ReFS v3.14 adds per-directory case-sensitive mode (opt-in). When a directory is marked
case-sensitive, the Upcase Table is bypassed for that directory's filename comparisons, which then
use binary (byte-exact) key comparison instead of the default case-folded comparison.

## Version presence

Present and identical on all versions from v3.4 through Insider. The table content is a fixed
Windows Unicode constant, not version-specific.

## Cross-references

- [System OIDs](system_oids.md) — OIDs 0x07 and 0x08
- [Schema Table](schema_table.md) — schema 0xe090
- [Directory Entries](directory_entries.md) — filename keys are compared using this table
- [Object Table](object_table.md) — OID resolution for 0x07/0x08

## Evidence

Identity (OIDs 0x07/0x08, schema 0xe090) is confirmed in the schema and OID registries and in the
driver (E2): `CmsVolume::InitializeUpcaseTable` loads the table at mount and `CmsKeyRules` consults
it for directory key comparison. The logical-array shape (65,536 × 2-byte entries, 131,072 bytes,
973 non-identity mappings), the 387-row B+-tree on-disk encoding, and the byte-for-byte identical
content across versions are raw-disk decoded (RD) across the corpus. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
