# USN Journal

The USN (Update Sequence Number) Journal records every change to files and directories on the
volume. ReFS uses the `USN_RECORD_V3` format with 128-bit file IDs (NTFS uses the older `USN_RECORD_V2`
form with a 64-bit file reference). The journal is **not active by default** — it must be enabled with `fsutil usn createjournal`.

**On-disk ReFS journal records are version 3.** ReFS's 128-bit file IDs require the `USN_RECORD_V3` layout;
`fsutil usn queryjournal` on ReFS reports `Maximum record version supported : 3`. Version 2 (NTFS's 64-bit
form) and version 4 (`USN_RECORD_V4`, the NTFS-only range-tracking / extent record — `fsutil usn
enablerangetracking` refuses a ReFS volume with *"A local NTFS volume is required for this operation"*) do
**not** occur on a ReFS journal (erratum E58). The parser decodes every record with the **V3 field layout**;
it still *accepts* a V2 or V4 record if one is present (a non-ReFS journal, or crafted/corrupt input) but
prints a one-time note that such records are parsed with V3 offsets and their fields are not validated —
it does not silently refuse them.

## USN_RECORD_V3 layout

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Record length (u32) | Total record size = `pad8(0x4C + UTF-16 name byte length)`; name-dominated, driver minimum 80 (0x50), observed 80–312 B across the corpus, no fixed ceiling — all records 8-byte aligned |
| 0x04 | 2 | Major version (u16) | 3 on every ReFS record (the 128-bit File ID requires the V3 layout). The parser decodes with V3 offsets and *tolerates* a stray V2/V4 — a non-ReFS/corrupt input — with a one-time note rather than refusing it (see above) |
| 0x06 | 2 | Minor version (u16) | Always 0 |
| 0x08 | 16 | File ID (u128) | See 128-bit File ID structure below |
| 0x18 | 16 | Parent file ID (u128) | Same format |
| 0x28 | 8 | USN (u64) | The record's own USN = its **virtual byte offset** in the journal (monotonic, never reused; can far exceed the live `$J` stream size because `$J` is a sliding window). A file's `$SI+0x40` LastUsn points at this value for its most recent record. |
| 0x30 | 8 | Timestamp (FILETIME) | 100 ns ticks since 1601-01-01 |
| 0x38 | 4 | Reason (u32) | See Reason codes below |
| 0x3C | 4 | Source info (u32) | — |
| 0x40 | 4 | Security ID (u32) | — |
| 0x44 | 4 | File attributes (u32) | Current WIN32_FILE_ATTRIBUTE flags |
| 0x48 | 2 | File name length (u16) | In bytes |
| 0x4A | 2 | File name offset (u16) | Offset from record start |
| 0x4C | var | File name (UTF-16LE) | — |

## 128-bit File ID structure

| Component | Size | Meaning |
|-----------|------|---------|
| Upper 8 bytes | u64 | B+-tree table OID (directory's Object Table OID) |
| Lower 8 bytes | u64 | Sequential entry index within directory (monotonically increasing, never reused) |

The upper 8 bytes identify which directory's B+-tree contains this entry; the lower 8 bytes identify
the specific entry within that tree. This makes a USN record directly resolvable to a
[B+-tree node](btree_node.md) location without a separate lookup table (see
[Object IDs & File IDs](../concepts/object_ids_fileids.md)).

## Reason codes

Reason codes are bitmask flags. A single record can combine multiple flags (e.g.
`0x80000100` = FILE_CREATE + CLOSE).

| Code (hex) | Name | Description |
|------------|------|-------------|
| 0x00000001 | DATA_OVERWRITE | Default data stream content overwritten |
| 0x00000002 | DATA_EXTEND | Default data stream extended |
| 0x00000004 | DATA_TRUNCATION | Default data stream truncated |
| 0x00000010 | NAMED_DATA_OVERWRITE | Named data stream (ADS) overwritten |
| 0x00000020 | NAMED_DATA_EXTEND | Named data stream extended |
| 0x00000040 | NAMED_DATA_TRUNCATION | Named data stream truncated |
| 0x00000100 | FILE_CREATE | File or directory creation |
| 0x00000200 | FILE_DELETE | File deleted |
| 0x00000400 | EA_CHANGE | Extended attributes changed |
| 0x00000800 | SECURITY_CHANGE | Security descriptor (ACL) changed |
| 0x00001000 | RENAME_OLD_NAME | Source name in rename operation |
| 0x00002000 | RENAME_NEW_NAME | Target name in rename operation |
| 0x00004000 | INDEXABLE_CHANGE | Content indexing attribute changed |
| 0x00008000 | BASIC_INFO_CHANGE | Timestamps or file attributes changed |
| 0x00010000 | HARD_LINK_CHANGE | Hard link count changed |
| 0x00020000 | COMPRESSION_CHANGE | Compression state changed |
| 0x00040000 | ENCRYPTION_CHANGE | EFS encryption state changed |
| 0x00080000 | OBJECT_ID_CHANGE | Object ID changed |
| 0x00100000 | REPARSE_POINT_CHANGE | Reparse point set or removed |
| 0x00200000 | STREAM_CHANGE | Named data stream added or removed |
| 0x00400000 | TRANSACTED_CHANGE | Change within a TxF transaction |
| 0x00800000 | INTEGRITY_CHANGE | Data integrity attribute changed |
| 0x80000000 | CLOSE | Handle closed (OR-ed with the final reason) |

## Forensic patterns

The reason-code combination, not just the individual flag, is the forensic signature of an operation:

| Operation | USN signature |
|-----------|---------------|
| Sparse flag set | Basic info change (0x8000); file attributes change from 0x20 to 0x220 |
| EFS encrypt/decrypt | Transient `EFS0.LOG` in system directory (OID 0x701); reason 0x40000 |
| $RECYCLE.BIN creation | Created on demand at first Explorer deletion |
| Junction creation | Reparse point change (0x100000) as a separate event |
| Symlink creation | Reparse change combined with create (0x100100) |
| ADS on symlink | Not possible — ADS cannot be written to symlink files on ReFS |

## Storage location

The Change Journal is stored as a file entry inside OID 0x520, the **FS Metadata directory** — the
ReFS equivalent of NTFS `$Extend` (see [System OIDs](system_oids.md)). When journaling is active a
type 0x30 B+-tree row appears with key `"Change Journal"` (UTF-16LE). Fresh volumes have no such
entry — it is created by `RefsCreateUsnJournal` and removed by `RefsDeleteUsnJournal`.

### Change Journal file entry structure

The "Change Journal" filename entry in OID 0x520 carries a `stream_count` field (3 on v3.14) and a
value of ~720 bytes on v3.14. The value holds three sub-records after the standard directory-entry
header (the embedded sub-record markers are described in [Directory Entries](directory_entries.md)):

| Sub-record | Type | Offset | Content |
|------------|------|--------|---------|
| 1 | Multi-instance (0x80000002) | varies (scan from 0xA8) | Data stream extents (likely `$J` stream) |
| 2 | Multi-instance (0x80000002) | 0x148 | Data stream extents (likely `$Max` stream) |
| 3 | Single-instance (0x80000001) | 0x288 | Journal metadata, 240 bytes (likely `$USN_INFO`) |

The `$J` data stream contains the actual `USN_RECORD_V3` entries as non-resident extent data. The
`$Max` stream holds the journal size parameters, and is also surfaced as the type-0xF0
`$LOGGED_UTILITY_STREAM` attribute (single-instance marker 0x80000001) on the Change Journal file —
not to be confused with the type-0x100 `$EFS` attribute. The single-instance sub-record at 0x288
contains organizational metadata including a creation timestamp and journal configuration.

### Activation detection

| Image state | OID 0x520 row count | Change Journal entry |
|-------------|---------------------|----------------------|
| Fresh (never activated) | 1 (descriptor only) | Absent |
| Active journaling | 3+ | Present (type 0x30, "Change Journal") |
| Deactivated | Varies | May persist with zeroed extents |

## Tooling

USN Journal parsing is integrated into `forefst.py` (parsing + display).
Available via `forefst.py <image> usn`:

| Mode | Description |
|------|-------------|
| Default | Record listing with reason codes and file names |
| `--csv [FILE]` | Export as CSV |
| `--json` | Machine-readable JSON output |
| `--stats` | Reason code frequency distribution |
| `--info` | Journal metadata, extent layout, format reference |

## Cross-references

- [Directory Entries](directory_entries.md) — per-file LastUsn at resident value offset **0x68**; value+0x58 holds FileSize; UsnJournalId at 0x70
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — per-file LastUsn at **$SI+0x40**, UsnJournalId at $SI+0x48 ($SI+0x30 is an unpopulated slot)
- [System OIDs](system_oids.md) — OID 0x520 hosts the Change Journal file entry
- [Object IDs & File IDs](../concepts/object_ids_fileids.md) — how the 128-bit File ID maps to a B+-tree location

## Evidence

The `USN_RECORD_V3` layout, the 128-bit File ID split (upper = table OID, lower = entry index), and
the reason-code catalog are raw-disk decoded across the corpus (RD). The record length range and the
`pad8` rule are measured corpus-wide (driver minimum 80 (0x50), observed 80–312 B, 8-byte aligned). The
USN ↔ `$SI+0x40` LastUsn link is both decompiled (E2) and disk-proven — every sampled file's LastUsn
resolved to a `$J` record naming that file. Journal activation, the OID 0x520 Change Journal entry,
and the type-0xF0 `$Max` attribute are corroborated in the driver
(`RefsSetupUsnJournal`, `RefsWriteFcbUsnRecordToJournal`) and verified on disk. Findings:
**MD_USN_RA_001**, **MD_USN_RA_002**, **MD_USN_RA_003**, **MD_USN_RA_004**, **AP_CHJN_001/002/004**,
**MD_SI_RA_013**, **MD_SI_RA_015**, **FS_OTBL_005**. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
