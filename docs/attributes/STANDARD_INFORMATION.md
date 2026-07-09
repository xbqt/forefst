# $STANDARD_INFORMATION ($SI)

`$STANDARD_INFORMATION` (`$SI`) is the **most forensically important attribute** — every file and
directory has exactly one, carrying all timestamps, the file attributes, the SecurityId, and the
per-file USN link. Structurally it is **not an embedded sub-record**: it occupies the **fixed region of
the object's type-0x10 own-row value** (read `$SI` only from a type-0x10 row). Its layout differs between
v3.4 and v3.7+ in a **non-backward-compatible** way — the same byte offsets mean different things by
version, so a parser must know the version first.

## Value layout

### Common fields (all versions, 0x00–0x57)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Creation time | FILETIME (100 ns since 1601-01-01) |
| 0x08 | 8 | Modification time | last content modification |
| 0x10 | 8 | MFT change time | last metadata modification |
| 0x18 | 8 | Last access time | not updated on read by default |
| 0x20 | 4 | File attributes | Win32 `FILE_ATTRIBUTE_*`. Bit 28 (the ReFS directory flag) is masked on Win10, preserved on Win11 |
| 0x24 | 4 | Internal flags | 6-bit field on v3.14+; 0 on v3.4–v3.10 (see [Internal flags](#internal-flags)) |
| 0x28 | 8 | Security ID | resolves directly in the security table (OID 0x530) |
| 0x30 | 8 | USN slot — **unpopulated** | Always 0 in the type-0x10 `$SI` (0 non-zero across 32,629 own-rows). The live per-file→journal link is **LastUsn** at 0x40 |
| 0x38 | 8 | DataSize slot — **unpopulated** | Always 0 in the type-0x10 `$SI` (0 non-zero across 32,629 own-rows). The PDB label (`LastMftChangeTime`) notwithstanding, it carries neither a timestamp nor a size |
| 0x40 | 8 | **LastUsn** | the file's last USN = byte offset of its most recent record in `$UsnJrnl:$J` (8-byte aligned; upper 32 bits always 0). See [LastUsn / UsnJournalId](#lastusn--usnjournalid) |
| 0x48 | 8 | **UsnJournalId** | a FILETIME identifying the journal instance — one distinct value per volume |
| 0x50 | 4 | PackedEaSize / ReparseTagLow16 | **version-dependent**: v3.10+ = PackedEaSize (EA size); v3.4–v3.9 = low 16 bits of the ReparseTag |
| 0x54 | 4 | ReparseTag | `IO_REPARSE_TAG_*` (0 if none) |

### v3.4 extension (Win10) — total 116 bytes (0x74)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x58 | 8 | NextFileId ordinal (ExternalFileId_1) | the directory child-creation ordinal (see [NextFileId ordinal](#nextfileid-ordinal)); non-zero on every v3.4 entry |
| 0x60 | 8 | ExternalFileId_2 | cross-volume file-identity word; normally 0 same-volume, carries the source-volume id only for cross-volume-copied content. Co-occurs with ExternalFileId_3 |
| 0x68 | 8 | ExternalFileId_3 | the source parent-directory OID; 0 if same-volume |
| 0x70 | 4 | HardLinkCount | **always 1 on disk** — a resident-layout field; genuine hard links are non-resident and counted by the shared FileId (§J). The increment path exists but is unexercised |

### v3.7+ extension (Win11) — total 124 bytes (0x7C)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x58 | 8 | NextFileId ordinal | the directory child-creation ordinal; persisted to the own-row only when version < 0x30b (v3.11), so **0 on native v3.14 own-rows** while resident files stay populated. See [NextFileId ordinal](#nextfileid-ordinal) |
| 0x60 | 8 | ExternalFileId_2 | cross-volume file-identity word; 0 on native v3.7+, non-zero only as upgrade carryover |
| 0x68 | 8 | ExternalFileId_3 | source parent-directory OID; 0 on native v3.7+, non-zero only as upgrade carryover |
| 0x70 | 4 | HardLinkCount | read from FCB+0xb4; **always 1 on disk** (hard links promote to non-resident, counted by the shared FileId — §J). On a **non-resident** own-row it reads 0 and is re-sourced from the resident FCB — do not treat 0 as corruption |
| 0x74 | 8 | NextStreamSetId | per-file next-stream-set-ID allocator, base 0xF000; non-zero only on a file owning an extra stream set |

The mapper enforces the size: a Win10 driver requires `value > 0x73` (≥116 B), a Win11 driver requires
`value > 0x7b` (≥124 B) — which is why a Win11 driver rejects a Win10-sized `$SI`.

## Internal flags

A 6-bit field at `$SI+0x24`, **0 on v3.4–v3.10, active on v3.14+**. Bits 0–3 are computed by
`RefsComputeStandardInformationInternalFromFcb` (from FCB+0x08); bits 4–5 are added by the caller via
`(FCB[0xf4] << 4) & 0x30`.

| Bit | Mask | Name | FCB source | Notes |
|-----|------|------|------------|-------|
| 0 | 0x01 | DELETE / DISPOSITION | FCB+0x08 bit 27 | delete-disposition / EFS transient state — **not** integrity (the integrity marker is file_attrs 0x8000, never reflected here) |
| 1 | 0x02 | DEDUP_OR_COW | FCB+0x08 bit 22 | dedup / CoW related |
| 2 | 0x04 | FLAG_0xB | FCB+0x08 bit 11 | rarely observed; also set by the link-count-zero path |
| 3 | 0x08 | FLAG_0x1F | FCB+0x08 bit 31 | most common on v3.14 regular files |
| 4 | 0x10 | FCB_F4_BIT0 | FCB[0xf4] bit 0 | |
| 5 | 0x20 | SYMLINK_TRUST | FCB[0xf4] bit 1 | symlink/junction redirection-trust level (`IoComputeRedirectionTrustLevel`), written only in `RefsSetReparsePointInternal` for tags 0xa000000c / 0xa0000003 |

## LastUsn / UsnJournalId

`$SI+0x40` and `$SI+0x48` are the USN change-journal fields — written atomically (both zero or both
non-zero), and non-zero only on a volume with an active USN journal (v3.14+):

- **`$SI+0x40` = LastUsn** — the byte offset of the file's most recent record in `$UsnJrnl:$J`, taken from
  the journal write cursor (VCB+0x3a0) and cached in FCB+0xe0. Always 8-byte aligned.
- **`$SI+0x48` = UsnJournalId** — a FILETIME identifying the journal instance (VCB+0x388), one distinct
  value per volume.
- The pair is gated by **FCB bit 23** ("the cached LastUsn is valid for the current journal epoch": set
  only when the journal is active *and* the on-disk UsnJournalId matches the current journal — a
  stale-epoch check, like NTFS journal-ID validation). Both are written by
  `RefsWriteFcbUsnRecordToJournal`.

## NextFileId ordinal

`$SI+0x58` (also ExternalFileId_1 on v3.4) is the **directory child-creation ordinal**: a directory's
own-row holds `NextFileId = max(child ordinal)`, and each resident child's `$SI+0x58` is its assigned
ordinal. `RefsMoveFile` (the unified create/rename/link path) increments the parent directory's
NextFileId and stamps the child. It is persisted to the own-row only when version < 0x30b (v3.11) — so on
native v3.14 the own-row reads 0 while the object-record payload carries it. A fresh directory starts at
1 (0/1 reserved); child ordinals are near-contiguous from 2. It is **not** a per-write counter.

## The two "0x90"s — `$SI` is not `$I30_INDEX`

A common trap (findings MD_ATTR_RA_015/FS_SNAP_RA_001): `$SI` is the **type-0x10 own-row's fixed region**, and its schema
slot is historically labeled 0x190 / embedded code 0x90. But the embedded **type-0x90 sub-record** is
`$I30_INDEX` (the directory-index template), a different thing. **Read `$SI` only from a type-0x10 row** —
a top-level type-0x90 row is `$I30_INDEX`, not `$SI`. See [$I30_INDEX](I30_INDEX.md).

## Driver functions

- `RefsMapStandardInfo` — maps `$SI` from a B+-tree row (and enforces the min-size gate)
- `RefsGetStandardInfo` / `RefsSetStandardInfo` — read / write (`RefsSetStandardInfo` via `MsUpdateDataWithRoot`)
- `RefsComputeStandardInformationFromFcb` — builds `$SI` from the in-memory FCB state

## Forensic value

| Field | Forensic value |
|-------|----------------|
| Timestamps (0x00–0x18) | the MACB timeline |
| LastUsn + UsnJournalId (0x40 / 0x48) | the file's last `$UsnJrnl:$J` offset and the journal instance (v3.14+) |
| ReparseTag (0x54) | symlinks, mount points, WSL / WOF special files |
| PackedEaSize (0x50, v3.10+) | presence of extended attributes |
| Internal flags (0x24, v3.14+) | feature state (dedup / CoW); bit 5 = reparse own-row |
| NextFileId ordinal (0x58) | directory child-creation order (versions < v3.11) — corroborating for timeline reasoning |

**Timestomping detection.** ReFS carries one `$SI` timestamp set **per name**. For a single-named file
there is no NTFS-style `$SI`-vs-`$FN` twin to compare — but a **hard-linked** file has one independent
timestamp copy per name, and a name-scoped timestomp leaves the sibling names at the true birth (the
latest Created among the siblings is the authentic one). Comparing a file's names' MACB is thus a
ReFS-specific tamper check — **journal-independent**, and **stronger** than NTFS's `$SI`-vs-`$FN`, where
all hard links share one `$SI` and cannot diverge. For any file, timestomping is also detectable via the
**metadata-change time (`$SI+0x10`)** (left at the real write moment by the high-level APIs that timestomp
tools use), the **USN journal** (records the edit and the true create time — the stronger anchor), and the
**volume creation time** (a hard lower bound). See [Timestomping Detection](../concepts/timestomp_detection.md).

**Last access time.** ReFS does not update last-access on read by default (`RefsDisableLastAccessUpdate`
defaults to 1). Per-handle suppression bits at `CCB+4` (bit 6 access / bit 5 modify / bit 4 change) are
the in-driver timestomp-suppression bits, set when a caller supplies an explicit time via `SetFileTime`.

## Raw example

A `$STANDARD_INFORMATION` value on a v3.14 image (a file created and untouched, so all four stamps match), value-relative offsets:

```text
+0x00:  92 10 67 69 18 e6 dc 01    <- Created   (FILETIME)  2026-05-17 16:15
+0x08:  92 10 67 69 18 e6 dc 01    <- Modified  (FILETIME)
+0x10:  92 10 67 69 18 e6 dc 01    <- Changed   (FILETIME)
+0x18:  92 10 67 69 18 e6 dc 01    <- Accessed  (FILETIME)
+0x20:  00 00 00 00 00 00 00 00
+0x28:  62 9b 9f 0a 01 00 00 00    <- SecurityId 0x10a9f9b62 (resolves in the security table, OID 0x530)
```

The four 8-byte FILETIMEs sit at `0x00` / `0x08` / `0x10` / `0x18`; `SecurityId` is the u32 at `0x28`. (ReFS carries one timestamp set per name — there is no NTFS-style `$FILE_NAME` duplicate, but a hard-linked file has one such set per name, and those can diverge under a name-scoped timestomp.)

## Cross-references

- [Directory Entries](../structures/directory_entries.md) — `$SI` fields are embedded in resident values
- [$I30_INDEX](I30_INDEX.md) — the other type-0x90 thing `$SI` is confused with
- [$EA_INFORMATION and $EA](EA_INFORMATION.md) — the PackedEaSize at 0x50 (v3.10+)
- [Security Descriptors](../structures/security_descriptors.md) — the SecurityId at 0x28 (OID 0x530)
- [Version Detection](../concepts/version_detection.md) — detect the version before parsing `$SI`

## Evidence

The `$SI` layout, the version split, the internal-flag bits, and the USN / NextFileId resolutions are
confirmed in the decompiled driver (E2 — `RefsComputeStandardInformationFromFcb`,
`RefsComputeStandardInformationInternalFromFcb`, `RefsWriteFcbUsnRecordToJournal`, `RefsMoveFile`) and
raw-disk decoded across the corpus (RD). The per-name MACB timestomp cross-check is RD-proven on a
hard-link pair (**FN_LINK_003 / E59**). Findings: **MD_SI_RA_012, MD_SI_SA_001, MD_SI_SA_002, FN_LINK_002, FN_LINK_003, MD_INTG_RA_001**. See [how this was verified](../methodology.md).
