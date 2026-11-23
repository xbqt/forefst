# System OIDs

ReFS reserves the OIDs below 0x700 for internal use; user directories start at 0x701. A file draws no OID of its
own: its record lives in its directory's tree.

These low-numbered objects hold the volume's infrastructure: the upcase table, the log metadata, the
security-descriptor store, the reparse index, the volume-information table, and the root directory itself.

In the driver:

- `RefsIsSystemObjectId` classifies an object as "system": it returns true when `OID <= 0x6FF AND OID != 0x600`;
- the 0x700 user boundary is hardcoded in `MsSetMinimumNewObjectId`, which seeds the OID counter with 0x700, so the
  first user OID issued is 0x701.

## Known System OIDs

| OID | Purpose | Schema | Notes |
|-----|---------|--------|-------|
| 0x07 | Upcase Table | 0xe090 | Unicode case-folding for case-insensitive name comparison (one copy of a failover pair) |
| 0x08 | Upcase Table | 0xe090 | The pair's other copy |
| 0x09 | Logfile Information Table | 0xe090 | MLog metadata bookkeeping (one copy of a failover pair) |
| 0x0A | Logfile Information Table | 0xe090 | The pair's other copy |
| 0x0D | Trash Table | 0xe0d0 | Deferred (asynchronous) deletion queue |
| 0x30 | Heat engine table | 0xe130 | v3.10+ only; when the volume had I/O, in 10-minute generations |
| 0x500 | Volume Information | 0x150 | Volume label, timestamps (one copy of a failover pair) |
| 0x501 | Volume Information | 0x150 | The pair's other copy |
| 0x520 | FS Metadata | 0x130 | Directory (NTFS $Extend equivalent); child of root 0x600 |
| 0x530 | Security Descriptors | 0x140 | SID/ACL data |
| 0x540 | Reparse Point Index | 0x160 | Reparse point lookup by tag + file reference (one copy of a failover pair) |
| 0x541 | Reparse Point Index | 0x160 | The pair's other copy |
| 0x600 | Root directory | 0x130 | First user-visible object (volume root "/") |

## OID ranges

| Range | Classification |
|-------|---------------|
| 0x00 – 0x6FF (except 0x600) | System objects (`RefsIsSystemObjectId` returns true) |
| 0x600 | Root directory (system-owned but excluded from `RefsIsSystemObjectId`) |
| 0x700 | Boundary (hardcoded in `MsSetMinimumNewObjectId`) |
| >= 0x701 | User objects: directories (files draw no OID) |

## Failover pairs

Four system tables exist as failover pairs: two independently-checksummed copies of the same table, each with its
own object record.

- refs.sys opens each pair with `MsCreateDurableFailoverTableObject`, which looks up both records, and neither copy
  is a primary.
- For the Logfile Information and Upcase tables the driver reads the first copy of its order and the other only when
  that copy fails; for the other two pairs, which copy it reads first was not read.
- When neither copy passes its check, refs.sys does not open the table; the tools read the first copy that can be
  read, as it is, and say so.

On the 117 ReFS volumes of the corpus measured, the two copies of every pair hold the same rows.

| Copies, in the order refs.sys passes them | Table |
|---------|---------|
| 0x08, 0x07 | Upcase Table |
| 0x0A, 0x09 | Logfile Information Table |
| 0x500, 0x501 | Volume Information |
| 0x540, 0x541 | Reparse Point Index |

## Heat engine table (OID 0x30)

Present from v3.10 onwards. The driver creates it at mount when it is absent, so an upgraded volume gets it at its
first mount by a 3.10 or later driver. It is the table in which the driver's heat engine (`CmsVolumeHeatEngine`) keeps
its I/O metrics, one generation at a time: a generation is opened every 600 seconds by default and kept when the volume
had I/O in it, and a dismount closes one more. At most 720 generations are kept (five days of 10-minute generations);
the oldest are trimmed.

| Row | Size | Content |
|-----|------|---------|
| Key | 16 bytes | The value's first 16 bytes: the generation's time (FILETIME), then the u64 below |
| Generation totals | 80 bytes | Two per generation: +0x08 is 0 or 1 (the driver's read/write type), then seven 64-bit totals |
| Container metrics | 44 bytes | One per container and direction with I/O: +0x08 is the container number × 2 plus the read/write bit, then two counters and a 32-bit map |

The table's root data holds the number of generations (u32 at +0x04).

**What it tells.** The generation times record when the volume had I/O: on a volume mounted for hours they step by
600 seconds, and a mount of a few minutes leaves about one generation. Each container row says which
part of the volume had I/O in that generation. The one volume measured that was formatted with heat gathering
disabled holds generations too (3). The table can be empty: it holds no generation on 16 of the 112 corpus volumes of 3.10 and later. Not
decoded: what the counters and the map count, and which read/write value is which.

## Security Descriptor Table (OID 0x530)

OID 0x530 is the single, centralized store for security descriptors, indexed by Security ID. Each file or directory
carries a compound Security ID in its `$SI`; that value resolves directly into this table.

### Key format — 16 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Value length (u64) | — |
| 0x08 | 4 | Security ID high (u32) | — |
| 0x0C | 4 | Security ID low (u32) | — |

Security descriptors themselves are standard Windows self-relative `SECURITY_DESCRIPTOR` structures containing Owner
SID, Group SID, DACL with ACEs, and SACL (when present).

See [Security Descriptors](security_descriptors.md) for the value layout and the Security ID lookup mechanism.

## FS Metadata Directory (OID 0x520)

OID 0x520 is a directory named "FS Metadata" in the parent-child table, analogous to NTFS's `$Extend` directory. It
is a directory table, schema 0x130 like the root directory 0x600 and every other directory, and its parent is
always OID 0x600. It is a directory, **not** a
security-mapping table.

Security functions (`RefsSecurityInitialize`, `RefsLoadSecurityDescriptor`, `RefsCacheSharedSecurityBySecurityId`)
access OID 0x530 directly; `MsInitializeWellKnownObjectId` is never invoked with 0x520. `RefsHasSystemName` treats
0x520 as a directory with hidden system entries (index <= 0x4ff) and user-visible entries (index > 0x4ff).

### Contents by version

| Version | Rows | Children | Value size |
|---------|------|----------|-----------|
| v3.4 (4K and 64K clusters) | 7 | Reparse Index, Security Descriptor Stream, Volume Direct IO File | 640B |
| v3.7 | 7 | Same three children | 800B |
| v3.9 | 1 | Empty (descriptor only) | — |
| v3.10 | 1 | Empty (descriptor only) | — |
| v3.14 (fresh) | 1 | Empty (descriptor only) | — |
| v3.14 (USN active) | 3 | Change Journal | 720B |
| v3.14, a volume an Insider build wrote | 1 | Empty (descriptor only) | — |
| Upgraded (v3.4→v3.14) | 7 | Retains v3.4 children | 640B (original) |

The transition point is exactly v3.7 to v3.9. The three original children are "degenerate" objects created by
`CreateDownlevelDegenerateMetadataObjects` on volumes formatted at v3.4 through v3.7 (a version below 0x307 in the
driver's test).

v3.9+ no longer creates them; the standalone OIDs (0x530, 0x540/0x541) continue to function independently. Upgraded
volumes retain the v3.4 children: the upgrade does not delete them.

### Row structure

Each OID 0x520 B+-tree follows standard directory structure:

| Row type | key_type | Purpose | Count (v3.4) | Count (v3.9+, empty) | Count (USN active) |
|----------|----------|---------|-------------|---------------------|-------------------|
| Descriptor | 0x0010 | Directory metadata ($SI) | 1 | 1 | 1 |
| Reverse lookup | 0x0020 | Back-references to children | 3 | 0 | 1 |
| Filename | 0x0030 | Child file entries | 3 | 0 | 1 |

### Degenerate children (v3.4 through v3.7)

These three file entries are created at format time by `CreateDownlevelDegenerateMetadataObjects`. Each has
key_flags=0x01 (record embedded in the name row) and file_attributes=0x20 (ARCHIVE). They are lightweight file-entry
wrappers for standalone system OIDs, not independent data stores.

#### Reparse Index

| Field | Value |
|-------|-------|
| Key | type 0x0030, key_flags 0x0001, "Reparse Index" (UTF-16LE) |
| File id (val+0x80 = $SI+0x58) | 0x400 |
| Relationship | File entry wrapper for standalone OID 0x540/0x541 (schema 0x160) |
| Driver function | `InitializeReparseIndexTable` creates OID 0x540/0x541 first, then creates this entry via `OpenFileSystemFile` |
| Sub-records | None on v3.4; 1 multi-instance on v3.7 |

#### Security Descriptor Stream

| Field | Value |
|-------|-------|
| Key | type 0x0030, key_flags 0x0001, "Security Descriptor Stream" (UTF-16LE) |
| File id (val+0x80 = $SI+0x58) | 0x200 |
| Relationship | File entry wrapper for standalone OID 0x530 |
| Driver function | `OpenSecurityFile` |
| SecurityId | Always 0 (this file entry itself has no security descriptor) |
| Sub-records | None on v3.4; 2 multi-instance on v3.7 |

#### Volume Direct IO File

| Field | Value |
|-------|-------|
| Key | type 0x0030, key_flags 0x0001, "Volume Direct IO File" (UTF-16LE) |
| File id (val+0x80 = $SI+0x58) | 0x100 |
| Purpose | DASD (Direct Access Storage Device) file representing the raw volume for direct I/O |
| Driver function | `InitializeDasdFile` |
| Sub-records | None on any version |
| Data | No data extents. Metadata-only placeholder. |

### Change Journal (dynamic, version-independent)

Created at runtime when USN journaling is activated via `fsutil usn createjournal`. Not a degenerate object. Created
by `ConditionallyCreateOrOpenFileSystemFile` wrapping `OpenFileSystemFile`. Removed by `RefsDeleteUsnJournal`.

| Field | Value |
|-------|-------|
| Key | type 0x0030, key_flags 0x0001, "Change Journal" (UTF-16LE) |
| File id (val+0x80 = $SI+0x58) | 0x501 on every volume measured with a journal |
| Stream count (val+0x20) | 3 |
| Sub-records | 2 multi-instance (data stream extents for $J and $Max) + 1 single-instance (journal metadata) |

See [USN Journal](usn_journal.md) for the Change Journal sub-record layout and $J stream format.

### OID 0x521 (Degenerate Metadata Directory)

The driver contains `OpenDegenerateMetadataDirectory`, which references OID 0x521. This object is not found in the
Object Table on disk; it appears to be an in-memory-only construct used during mount, not persisted.

## Forensic value

- System OIDs define the infrastructure: any forensic tool must recognize these objects and their roles.
- The Trash Table (0x0D) receives a deleted object only in some cases (on the lab volume measured, only the file
  that had a stream snapshot); most deletions happen in place, and it is empty on every image held
  ([Trash Table](trash_table.md)).
- The heat engine table (0x30) records when the volume had I/O, in 10-minute generations.
- Volume Info (0x500/0x501) carries the volume label and timestamps.

## Cross-references

- [Object Table](object_table.md) — all system OIDs are entries in the Object Table
- [Schema Table](schema_table.md) — each system table has a schema defining its key comparison
- [Security Descriptors](security_descriptors.md) — the OID 0x530 store and Security ID resolution
- [Checkpoint (CHKP)](chkp.md) — the root table pointers include several system table pairs

## Evidence

The OID classification (`RefsIsSystemObjectId` true for `OID <= 0x6FF AND OID != 0x600`; 0x700 user boundary in
`MsSetMinimumNewObjectId`) is read in the decompiled driver; the first user OID 0x701 and "only directories draw user
OIDs" are read on 26100.9444.

The OID-to-purpose map, the failover pairs, the OID 0x520 FS-Metadata-directory identity (it is a directory, not a
security map), the per-version child contents, and the degenerate-child layouts are measured on the disk across the
corpus and corroborated by the named driver functions: `CreateDownlevelDegenerateMetadataObjects`,
`OpenFileSystemFile`, `InitializeReparseIndexTable`, `OpenSecurityFile`, `InitializeDasdFile`.

The heat engine table (OID 0x30) is read in the driver's heat engine (`CmsVolumeHeatEngine::Initialize`, `Persist`,
`TrimPersistedEntries`, on every symbolled 26100 and Insider build held) and measured on all 112 corpus volumes of 3.10 and
later: schema 0xe130 at its root, two total rows per generation, the generation count in its root data, and 600-second
steps on the volumes mounted for hours.

The counts behind the text: OID 0x30 is present on all 112 corpus volumes of 3.10 and later and absent on all 12 of 3.4 / 3.7 / 3.9; the Change Journal's file id is 0x501 on the 36 corpus volumes with a journal; the two copies of
every failover pair hold the same rows on 117 of 117 ReFS volumes.

See [how this was verified](../methodology.md) for the method.

<!-- findings: FS_OTBL_003, FS_OTBL_005, FS_OTBL_RA_001, FS_OTBL_RA_003, FS_OTBL_RA_005, FS_OTBL_SA_004,
               FS_OTBL_SA_005, FS_REPS_RA_001, FS_SCHM_RA_001, FS_SECD_RA_001, MD_SECT_001 -->
