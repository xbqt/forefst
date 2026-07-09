# System OIDs

ReFS reserves the OIDs below 0x700 for internal use; user files and directories start at 0x701. These low-numbered objects hold the volume's infrastructure — the upcase table, the log metadata, the security-descriptor store, the reparse index, the volume-information table, and the root directory itself. The driver classifies an object as "system" through `RefsIsSystemObjectId`, which returns true when `OID <= 0x6FF AND OID != 0x600`; the 0x700 user boundary is hardcoded in `MsSetMinimumNewObjectId`.

## Known System OIDs

| OID | Purpose | Schema | Notes |
|-----|---------|--------|-------|
| 0x07 | Upcase Table (primary) | 0xe090 | Unicode case-folding for case-insensitive name comparison |
| 0x08 | Upcase Table (duplicate) | 0xe090 | Failover copy |
| 0x09 | Logfile Info (primary) | 0xe090 | MLog metadata bookkeeping |
| 0x0A | Logfile Info (duplicate) | 0xe090 | Failover copy |
| 0x0D | Trash Table | 0xe0d0 | Deferred (asynchronous) deletion queue |
| 0x30 | Session Activity Table | — | v3.10+ only; mount session forensics |
| 0x500 | Volume Info (primary) | 0x150 | Volume label, timestamps |
| 0x501 | Volume Info (duplicate) | 0x150 | Failover copy |
| 0x520 | FS Metadata | 0x200 | Directory (NTFS $Extend equivalent); child of root 0x600 |
| 0x530 | Security Descriptors | — | SID/ACL data (stream-type, no schema) |
| 0x540 | Reparse Index (primary) | 0x160 | Reparse point lookup by tag + file reference |
| 0x541 | Reparse Index (duplicate) | 0x160 | Failover copy |
| 0x600 | Root directory | — | First user-visible object (volume root "/") |

## OID ranges

| Range | Classification |
|-------|---------------|
| 0x00 – 0x6FF (except 0x600) | System objects (`RefsIsSystemObjectId` returns true) |
| 0x600 | Root directory (system-owned but excluded from `RefsIsSystemObjectId`) |
| 0x700 | Boundary (hardcoded in `MsSetMinimumNewObjectId`) |
| >= 0x701 | User objects (files and directories) |

## Failover pairs

Several system OIDs exist as primary/duplicate pairs for resilience. Each pair holds two independently-checksummed copies of the same table, so a corrupted primary can fail over to the backup.

| Primary | Duplicate | Purpose |
|---------|-----------|---------|
| 0x07 | 0x08 | Upcase Table |
| 0x09 | 0x0A | Logfile Info |
| 0x500 | 0x501 | Volume Info |
| 0x540 | 0x541 | Reparse Index |

## Session Activity Table (OID 0x30)

Present from v3.10 onwards. It is a B+-tree of per-mount-session activity records, present even when heat gathering is disabled.

| Property | Details |
|----------|---------|
| Two value formats | 80-byte (extended summary), 44-byte (per-category) |
| Independent of heat gathering | Present even with heat disabled |
| Static analysis correlation | `RefsTelemetryPerfCountersWorker` |

## Security Descriptor Table (OID 0x530)

OID 0x530 is the single, centralized store for security descriptors, indexed by Security ID. Each file or directory carries a compound Security ID in its `$SI`; that value resolves directly into this table.

### Key format — 16 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Value size (u32) | — |
| 0x04 | 4 | Padding (u32) | — |
| 0x08 | 4 | Security ID high (u32) | — |
| 0x0C | 4 | Security ID low (u32) | — |

Security descriptors themselves are standard Windows self-relative `SECURITY_DESCRIPTOR` structures containing Owner SID, Group SID, DACL with ACEs, and SACL. See [Security Descriptors](security_descriptors.md) for the value layout and the Security ID lookup mechanism.

## FS Metadata Directory (OID 0x520)

OID 0x520 is a directory named "FS Metadata" in the parent-child table, analogous to NTFS's `$Extend` directory. It uses schema 0x200 (same as the root directory 0x600) and its parent is always OID 0x600. It is a directory, **not** a security-mapping table.

Security functions (`RefsSecurityInitialize`, `RefsLoadSecurityDescriptor`, `RefsCacheSharedSecurityBySecurityId`) access OID 0x530 directly; `MsInitializeWellKnownObjectId` is never invoked with 0x520. `RefsHasSystemName` treats 0x520 as a directory with hidden system entries (index <= 0x4ff) and user-visible entries (index > 0x4ff).

### Contents by version

| Version | Rows | Children | Value size |
|---------|------|----------|-----------|
| v3.4 (4K and 64K clusters) | 7 | Reparse Index, Security Descriptor Stream, Volume Direct IO File | 640B |
| v3.7 | 7 | Same three children | 800B |
| v3.9 | 1 | Empty (descriptor only) | — |
| v3.10 | 1 | Empty (descriptor only) | — |
| v3.14 (fresh) | 1 | Empty (descriptor only) | — |
| v3.14 (USN active) | 3 | Change Journal | 720B |
| Insider | 1 | Empty (descriptor only) | — |
| Upgraded (v3.4→v3.14) | 7 | Retains v3.4 children | 640B (original) |

The transition point is exactly v3.7 to v3.9. The three original children are "degenerate" objects created by `CreateDownlevelDegenerateMetadataObjects` on volumes formatted at v3.4 through v3.7. v3.9+ no longer creates them; the standalone OIDs (0x530, 0x540/0x541) continue to function independently. Upgraded volumes retain the v3.4 children because the upgrade process does not delete legacy entries.

### Row structure

Each OID 0x520 B+-tree follows standard directory structure:

| Row type | key_type | Purpose | Count (v3.4) | Count (v3.9+, empty) | Count (USN active) |
|----------|----------|---------|-------------|---------------------|-------------------|
| Descriptor | 0x0010 | Directory metadata ($SI) | 1 | 1 | 1 |
| Reverse lookup | 0x0020 | Back-references to children | 3 | 0 | 1 |
| Filename | 0x0030 | Child file entries | 3 | 0 | 1 |

### Degenerate children (v3.4 through v3.7)

These three file entries are created at format time by `CreateDownlevelDegenerateMetadataObjects`. Each has key_flags=0x01 (resident) and file_attributes=0x20 (ARCHIVE). They are lightweight file-entry wrappers for standalone system OIDs, not independent data stores.

#### Reparse Index

| Field | Value |
|-------|-------|
| Key | type 0x0030, key_flags 0x0001, "Reparse Index" (UTF-16LE) |
| Degenerate flag (val+0x80) | 0x0400 |
| Relationship | File entry wrapper for standalone OID 0x540/0x541 (schema 0x160) |
| Driver function | `InitializeReparseIndexTable` creates OID 0x540/0x541 first, then creates this entry via `OpenFileSystemFile` |
| Sub-records | None on v3.4; 1 multi-instance on v3.7 |

#### Security Descriptor Stream

| Field | Value |
|-------|-------|
| Key | type 0x0030, key_flags 0x0001, "Security Descriptor Stream" (UTF-16LE) |
| Degenerate flag (val+0x80) | 0x0200 |
| Relationship | File entry wrapper for standalone OID 0x530 |
| Driver function | `OpenSecurityFile` |
| SecurityId | Always 0 (this file entry itself has no security descriptor) |
| Sub-records | None on v3.4; 2 multi-instance on v3.7 |

#### Volume Direct IO File

| Field | Value |
|-------|-------|
| Key | type 0x0030, key_flags 0x0001, "Volume Direct IO File" (UTF-16LE) |
| Degenerate flag (val+0x80) | 0x0100 |
| Purpose | DASD (Direct Access Storage Device) file representing the raw volume for direct I/O |
| Driver function | `InitializeDasdFile` |
| Sub-records | None on any version |
| Data | No data extents. Metadata-only placeholder. |

### Change Journal (dynamic, version-independent)

Created at runtime when USN journaling is activated via `fsutil usn createjournal`. Not a degenerate object. Created by `ConditionallyCreateOrOpenFileSystemFile` wrapping `OpenFileSystemFile`. Removed by `RefsDeleteUsnJournal`.

| Field | Value |
|-------|-------|
| Key | type 0x0030, key_flags 0x0001, "Change Journal" (UTF-16LE) |
| Stream count (val+0x20) | 3 |
| Sub-records | 2 multi-instance (data stream extents for $J and $Max) + 1 single-instance (journal metadata) |

See [USN Journal](usn_journal.md) for the Change Journal sub-record layout and $J stream format.

### OID 0x521 (Degenerate Metadata Directory)

The driver contains `OpenDegenerateMetadataDirectory`, which references OID 0x521. This object is not found in the Object Table on disk; it appears to be an in-memory-only construct used during mount, not persisted.

## Forensic value

- System OIDs define the infrastructure: any forensic tool must recognize these objects and their roles.
- The Trash Table (0x0D) may contain recently deleted files not yet reclaimed.
- The Session Activity Table (0x30) provides mount session history.
- Volume Info (0x500/0x501) carries the volume label and timestamps.

## Cross-references

- [Object Table](object_table.md) — all system OIDs are entries in the Object Table
- [Schema Table](schema_table.md) — each system table has a schema defining its key comparison
- [Security Descriptors](security_descriptors.md) — the OID 0x530 store and Security ID resolution
- [Checkpoint (CHKP)](chkp.md) — the root table pointers include several system table pairs

## Evidence

The OID classification (`RefsIsSystemObjectId` true for `OID <= 0x6FF AND OID != 0x600`; 0x700 user boundary in `MsSetMinimumNewObjectId`) is decompiled across all driver builds (E2). The OID-to-purpose map, the failover pairs, the OID 0x520 FS-Metadata-directory identity (it is a directory, not a security map), the per-version child contents, and the degenerate-child layouts are raw-disk verified across the corpus (RD) and corroborated by the named driver functions (E2): `CreateDownlevelDegenerateMetadataObjects`, `OpenFileSystemFile`, `InitializeReparseIndexTable`, `OpenSecurityFile`, `InitializeDasdFile`. The Session Activity Table decode (OID 0x30, two value formats) is raw-disk verified and correlates with `RefsTelemetryPerfCountersWorker`. Findings: **FS_OTBL_SA_004**, **FS_OTBL_SA_005** (classification/boundary), **FS_OTBL_005** (OID 0x520), **FS_OTBL_RA_001** (Session Activity Table), **FS_OTBL_RA_003**, **FS_SCHM_RA_001** (Trash Table), **FS_OTBL_RA_005**, **FS_REPS_RA_001** (Reparse Index), **MD_SECT_001**, **FS_SECD_RA_001** (Security Descriptors). See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
