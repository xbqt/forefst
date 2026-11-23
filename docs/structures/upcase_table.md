# Upcase Table

The Upcase Table (a failover pair, OID 0x08 and OID 0x07, schema 0xe090) stores the Unicode
uppercase mapping that ReFS uses for case-insensitive filename comparison in directory B+-trees.

Its content is the same on every volume measured: the 124 corpus volumes, formats 3.4 to 3.14, both cluster sizes.

## Logical table

Once loaded into memory, the comparison code sees a flat array:

| Property | Value |
|----------|-------|
| Entry count | 65,536 (one per UTF-16 code unit, U+0000 through U+FFFF) |
| Entry size | 2 bytes (u16) |
| Total size | 131,072 bytes (128 KiB) |
| Non-identity mappings | 973 characters whose uppercase differs from the character itself |
| Content | Identical on every format read, 3.4 to 3.14 |

In the reconstructed logical array, the entry at index N is the uppercase equivalent of code
point U+N: for the 973 non-identity entries the stored value differs from the index; for every
other entry it equals the index (identity mapping).

## On-disk B+-tree

On disk the table is **not** a flat 128 KiB blob — it is a B+-tree (schema 0xe090) whose row count depends on the
cluster size: **387 rows** on a 4 KiB-cluster volume, **27** on a 64 KiB one.

| Row | Key | Contents |
|-----|-----|----------|
| Name row | 0 | the table name `"Upcase Table"` (12 bytes), as other system tables carry their name |
| Count row | 1 | the number of entries, a u32: 65,536 |
| Data rows | 2 onwards | 385 rows on 4 KiB clusters (384 of 341 bytes, then one of 128); 25 on 64 KiB clusters (24 of 5,461 bytes, then one of 8) |

The data-row values **concatenate, in key order**, to exactly the 131,072-byte array, with nothing before it. Both
copies hold the same rows, and the concatenated content is byte-for-byte the same on every corpus volume.

## How it is used

ReFS performs case-insensitive filename comparison by mapping each UTF-16 character through this
table before comparison. The `CmsKeyRules` class consults the Upcase Table for B+-tree key
comparisons in directory tables. At mount time, `CmsVolume::InitializeUpcaseTable` loads the table
into memory from the failover pair (below): OID 0x08 when both copies are good.

## Dual pair and shared schema

OID 0x08 and OID 0x07 form a failover pair; both carry schema 0xe090, and neither is a primary: refs.sys opens
OID 0x08 first and OID 0x07 only when 0x08's copy fails (`InitializeUpcaseTable`; the tools read the pair the
same way).

Schema 0xe090 is **shared** between the Upcase Table (OIDs 0x07/0x08) and the Logfile Info table
(OIDs 0x09/0x0A), which stores MLog metadata.

## Case-sensitive directories

ReFS v3.14 adds a per-directory, opt-in case-sensitive mode (`fsutil file setcasesensitiveinfo <dir> enable`).
A directory is **marked case-sensitive by bit `0x02` in its own `$SI` internal_flags** — the type-0x10 value
at offset `0x4C` (`0x02` when case-sensitive, `0x00` otherwise). When that bit is set, the Upcase Table is
**bypassed** for that directory's filename comparisons, which then use **binary (byte-exact)** key comparison
instead of the default case-folded comparison. Files that differ only in case (`File.txt` / `file.txt`)
therefore no longer collide on insertion — they coexist as separate directory entries.

Each case variant is its own type-0x30 entry with a **distinct FileId** and its own
[FileId-index](reverse_index.md) entry; they are **not** given distinct object IDs — a ReFS file has no
Object-Table OID of its own. The mode cannot be enabled on a directory that already holds names differing
only by case (the driver rejects it).

## Version presence

Present and identical on every format read, 3.4 to 3.14 (volumes written by Insider builds included). The
table content is a fixed Windows Unicode constant, not version-specific.

## Cross-references

- [System OIDs](system_oids.md) — OIDs 0x07 and 0x08
- [Schema Table](schema_table.md) — schema 0xe090
- [Directory Entries](directory_entries.md) — filename keys are compared using this table
- [Object Table](object_table.md) — OID resolution for 0x07/0x08

## Evidence

Identity (OIDs 0x07/0x08, schema 0xe090) is confirmed in the schema and OID registries and in the driver:
`CmsVolume::InitializeUpcaseTable` loads the table at mount and `CmsKeyRules` consults it for directory key comparison.
The logical-array shape (65,536 × 2-byte entries, 131,072 bytes, 973 non-identity mappings), the B+-tree encoding (387
rows on 4 KiB clusters, 27 on 64 KiB) and the byte-for-byte identical content are decoded from the disk across the
corpus: on all 124 ReFS volumes (117 with 4 KiB clusters, 7 with 64 KiB) and both copies, the data rows concatenate to
65,536 entries, 973 of them non-identity, with one SHA-256; the count row reads 65,536 on the 56 volumes whose key-1 row
was read. The pair's read order (OID 0x08 when both copies are good) was read on 17134, 26100.8115, .9444, .9549 and
Insider 29574; on every corpus volume both copies verify and hold equal rows.

See [how this was verified](../methodology.md) to trace these statements to the exact images and measurements in
`analysis/`; the case-sensitive directory statements are registered findings too.

<!-- findings: FS_UPCS_001, MD_CS_RA_001 -->
