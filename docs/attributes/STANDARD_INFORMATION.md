# $STANDARD_INFORMATION ($SI)
<!-- site: description "Every object's times, file attributes, security id and change-journal link: the first record an examiner reads." -->

`$STANDARD_INFORMATION` (`$SI`) holds an object's timestamps, file attributes, SecurityId and change-journal
pointer, which makes it the first record an examiner reads.

- Every file and directory has exactly one.
- It is not an embedded sub-record: it is the fixed region at `value+0x28` of the object's record.
- Its size depends on the format, and the meaning of some offsets on the driver that wrote the row (an upgraded
  volume can hold both meanings of 0x50), so a parser decides per row, not from the volume version alone (see
  [Differences between versions](#differences-between-versions)).

| Property | Value |
|----------|-------|
| Type code | — not a sub-record, so it has no type code of its own |
| Schema id | — none: the `$SI` is the root data of the record's table; the table's schema id (file record or directory own row, by format) is in the record's first 40 bytes ([Schema Table](../structures/schema_table.md)) |
| Instances | — no instance marker (it is not a sub-record); exactly one per record |
| Where it lives | `value+0x28` of the record: a directory's or system object's type-0x10 own row; a file's type-0x30 name row, or its type-0x40 backing once the record is split out of the name row |
| Size | 124 bytes (0x7C) on format 3.7 and later; 116 bytes (0x74) on 3.4 |
| Added in | 3.4 or earlier: present on every format read (3.4, Windows 10 1803, driver 17134, is the oldest held); the 124-byte layout from 3.7 (Windows 11 21H2) |

See [Directory Entries](../structures/directory_entries.md) for the record around it.

## Value layout (format 3.14)

The layout below is that of format 3.14 (124 bytes); formats 3.7 to 3.10 share its offsets, with the differences
listed under [Differences between versions](#differences-between-versions).

<!-- site: hexfig "attr_si_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Creation time | FILETIME (100 ns since 1601-01-01) |
| 0x08 | 8 | Modification time | last content modification |
| 0x10 | 8 | Metadata change time | last metadata change. A directory has a second copy in its index entry, the one Windows reported where the two differed: see [A directory's change time](#a-directorys-change-time) |
| 0x18 | 8 | Last access time | not updated on read unless the machine enables it: see [Last access time](#last-access-time) |
| 0x20 | 4 | File attributes | Win32 `FILE_ATTRIBUTE_*`. A directory's own row carries the ReFS directory flag (bit 28) only on some formats: see [The directory flag (bit 28)](#the-directory-flag-bit-28) |
| 0x24 | 4 | Internal flags | 6-bit field on 3.14; 0 on 3.4 to 3.10 (see [Internal flags](#internal-flags)) |
| 0x28 | 8 | Security ID | resolves directly in the security table (OID 0x530) |
| 0x30 | 8 | File size | in a file's record, a cached copy of the file size (`value+0x58` of the name row or backing; see [Directory Entries](../structures/directory_entries.md)); 0 in a directory's own row. The per-file journal link is LastUsn at 0x40 |
| 0x38 | 8 | Allocated size | in a file's record, a cached copy of the allocated size (`value+0x60`); 0 in a directory's own row |
| 0x40 | 8 | LastUsn | the file's last USN: the virtual byte offset of its most recent record in `$UsnJrnl:$J` (8-byte aligned; upper 32 bits 0 on every volume measured). See [LastUsn / UsnJournalId](#lastusn--usnjournalid) |
| 0x48 | 8 | UsnJournalId | a FILETIME identifying the journal instance the file's LastUsn belongs to: one value per journal instance; a volume whose journal was replaced can hold files still carrying an earlier instance's id |
| 0x50 | 4 | PackedEaSize / ReparseTagLow16 | the packed EA size on a row written by a 3.10 or later driver; the reparse tag's low 16 bits on a row written earlier (see [Differences between versions](#differences-between-versions)) |
| 0x54 | 4 | ReparseTag | `IO_REPARSE_TAG_*` (0 if none) |
| 0x58 | 8 | NextFileId | the child-creation ordinal: a file's record holds its own; a directory's own row holds the directory's counter only below format 3.11, so 0 on a native 3.14 own row. See [NextFileId ordinal](#nextfileid-ordinal) |
| 0x60 | 8 | Reference ordinal | the ordinal of the file's own FileRef when the file sits outside that reference's directory, else 0 (when a move sets it: [Differences between versions](#differences-between-versions)) |
| 0x68 | 8 | Reference directory | the directory of that FileRef (where the file was created), set with 0x60, else 0. The file's identity is (0x68 : 0x60) when set, which is what Windows reports as its file ID |
| 0x70 | 4 | HardLinkCount | the file's link count as the driver last wrote it: 1 in an embedded record, the number of the file's names in a type-0x40 backing. See [HardLinkCount](#hardlinkcount) |
| 0x74 | 8 | NextStreamSetId | per-file next-stream-set-ID allocator, base 0xF000; non-zero only on a file owning an extra stream set |

## Format 3.4 difference

On format 3.4 the `$SI` is shorter: total 116 bytes (0x74), against total 124 bytes (0x7C) from 3.7. Offsets
0x00 to 0x57 are those of the table above, with the per-offset differences of the next section; the tail reads:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x58 | 8 | NextFileId (ExternalFileId_1) | the directory child-creation ordinal (see [NextFileId ordinal](#nextfileid-ordinal)); non-zero on every 3.4 entry, a directory's own row included |
| 0x60 | 8 | Reference ordinal | the ordinal of the file's own FileRef when the file sits outside that reference's directory (a file moved on a volume without hard-link support), else 0 |
| 0x68 | 8 | Reference directory | the directory of that FileRef (where the file was created), set with 0x60, else 0. The file's identity is (0x68 : 0x60) when set |
| 0x70 | 4 | HardLinkCount | 1 on every 3.4 record: the format has no hard links and no type-0x40 backings, and the 3.4 driver (17134) has no link-count writer |

There is no NextStreamSetId: the 3.4 layout ends at 0x73.

## Differences between versions

- **Size.** 116 bytes (0x74) on 3.4, 124 bytes (0x7C) from 3.7. The mapper enforces the size: the Windows 10 driver
  (17134) requires `value > 0x73` (at least 116 bytes), the Windows 11 drivers read (26100 and Insider) require
  `value > 0x7b` (at least 124 bytes), which is why a Windows 11 driver rejects a Windows 10-sized `$SI`.
- **0x20, bit 28.** A directory's own row carries the directory flag only on formats 3.4, 3.7 and 3.9 and on a
  volume upgraded from 3.4; see [The directory flag (bit 28)](#the-directory-flag-bit-28).
- **0x24, internal flags.** 0 on 3.4 to 3.10; active on 3.14.
- **0x40 / 0x48, LastUsn and UsnJournalId.** Written while a change journal is active. Every journaled volume in the
  corpus is format 3.14; the 3.4 driver writes the same pair.
- **0x50.** The low 16 bits of the reparse tag on 3.4 to 3.9; the packed EA size from 3.10. A row keeps what its
  writer stored, so a volume upgraded from an older format can hold both: there, take the EA size from
  [$EA_INFORMATION](EA_INFORMATION.md).
- **0x58.** A directory's own row holds the directory's NextFileId counter only below format 3.11 (0 on a native
  3.14 own row); every file's record holds its own ordinal on every format.
- **0x60 / 0x68.** The driver compares the reference's directory with the current parent and writes the reference
  here when they differ.
  - A move on a volume with hard-link support splits the record and leaves 0 here (the home is carried at
    `value+0x08` of the split name row).
  - On a volume without it (in the corpus, the volumes formatted at 3.4 or upgraded from 3.4) the moved record stays
    embedded and carries its reference here.
- **0x70.** 1 on every 3.4 record; on a format with hard links, the link count (see [HardLinkCount](#hardlinkcount)).
- **0x74, NextStreamSetId.** From 3.7; absent on 3.4.

## A directory's change time

A directory's metadata change time exists twice: at `$SI+0x10` of its own row, and in its index entry in the parent
(the type-0x30 row with `key_flags` 0x02, `value+0x20`).

- The two copies can differ. They differ rarely: on about 1 % of the directories measured.
- Where they differed on a volume with Windows ground truth, Windows reported the index-entry copy, and no volume
  with ground truth shows the reverse.
- `forefst` reports the index-entry value for a directory.

For a file, the copies depend on where the record sits:

- An embedded record is the name row, so there is one copy.
- A split record (a moved or hard-linked file) keeps its own values in its type-0x40 backing. Each name row holds a
  cached copy of the times, refreshed only when the file is opened, read and closed through that name (a directory
  listing does not refresh it), so the two can differ (see [Hard Links](../concepts/hard_links.md)).

## The directory flag (bit 28)

Bit 28 (0x10000000) is the ReFS directory flag in the file attributes.

- The index entry at `value+0x40` carries it on every directory measured, on every format.
- A directory's own row (`$SI+0x20`) carries it on some directories of formats 3.4, 3.7 and 3.9 (formatted in this
  corpus by Windows 10 1803, Windows 11 21H2 and Windows 11 22H2) and on a volume upgraded from 3.4.
- On the 3.10 and natively formatted 3.14 volumes measured, no directory's own row carries it.
- Bit 28 is the only attribute bit seen to differ between the two copies.

## Internal flags

A 6-bit field at `$SI+0x24`, 0 on 3.4 to 3.10 and active on 3.14. Bits 0–3 are computed by
`RefsComputeStandardInformationInternalFromFcb` (from FCB+0x08); bits 4–5 are added by the caller via
`(FCB[0xf4] << 4) & 0x30`.

| Bit | Mask | Name | FCB source | Notes |
|-----|------|------|------------|-------|
| 0 | 0x01 | DeleteDisposition | FCB+0x08 bit 27 | delete-disposition / EFS transient state; not integrity (the integrity marker is file_attrs 0x8000, never reflected here) |
| 1 | 0x02 | CaseSensitive | FCB+0x08 bit 22 | a case-sensitive directory (`fsutil file setCaseSensitiveInfo`): see [below](#case-sensitive-directories-bit-1) |
| 2 | 0x04 | FLAG_0xB | FCB+0x08 bit 11 | rarely observed; also set by the link-count-zero path |
| 3 | 0x08 | DataInRecord | FCB+0x08 bit 31 | the file's default data stream is held in its record (the bytes inline): see [below](#data-held-in-the-record-bit-3) |
| 4 | 0x10 | FCB_F4_BIT0 | FCB[0xf4] bit 0 | |
| 5 | 0x20 | RedirectionTrust | FCB[0xf4] bit 1 | symlink/junction redirection-trust level (`IoComputeRedirectionTrustLevel`), written only in `RefsSetReparsePointInternal` for tags 0xa000000c / 0xa0000003 |

### Case-sensitive directories (bit 1)

`RefsSetCaseSensitiveInfo` sets the bit, `RefsQueryCaseSensitiveInfo` reads it, and `RefsUpdateFcbInfoFromDisk` reads
it back from the disk on open (the 26100 builds read; the 17134 driver of Windows 10 1803 has no case-sensitive
directories).

The flag is rare on the corpus: a few directories on two of the readable volumes carry it (a directory created inside
a flagged one inherits it). Two of them hold two names that differ only by case: the one case in which a lookup that
folds case can return the wrong file.

### Data held in the record (bit 3)

The bit says that the file's default data stream is held in its record: the bytes are inline, with no separate data
stream.

- `RefsCreateNewFile` sets it when it builds the file from the resident-data table template, which exists only on
  volumes above 3.10. A file created encrypted or sparse does not get it, and the driver makes further tests on the
  file and its parent.
- `RefsConvertToNonResident` clears it when the data moves to extents.
- Read in the 26100.8115 and 26100.9711 drivers, and recognised in Insider; not in 17134.
- On the corpus it is set on every file whose data is inline, on no file with extents and on no directory.

### How the tools print the field

`files` (CSV and JSON), `details` and `refsanalysis attributes` print bits 0, 1, 3 and 5 by the names above
(`DataInRecord|RedirectionTrust` for a symbolic link's `0x28`), and bits 2 and 4, which have no established name, as
their hex (`0x4`). The `InternalFlagsHex` column holds the whole word.

## LastUsn / UsnJournalId

`$SI+0x40` and `$SI+0x48` are the USN change-journal fields. They are written atomically (both zero or both
non-zero), and non-zero only on a file changed while a journal was active (every journaled volume in the corpus is
format 3.14):

- `$SI+0x40` = LastUsn: the virtual byte offset of the file's most recent record in `$UsnJrnl:$J`, taken from the
  journal write cursor (VCB+0x3a0) and cached in FCB+0xe0. Always 8-byte aligned.
- `$SI+0x48` = UsnJournalId: a FILETIME identifying the journal instance (VCB+0x388), one value per instance.
  - `fsutil usn createjournal` over an existing journal keeps it: measured on a lab volume, the call restarted USNs
    at 0 under the same id, so there this field cannot show that a stale `LastUsn` points into an earlier numbering.
  - `deletejournal` followed by `createjournal` gives a new id (the new journal's creation time). A file still
    carrying the earlier id then shows that it belongs to an earlier instance (the tools state such a re-creation).
- Both are written by `RefsWriteFcbUsnRecordToJournal`, while the journal is active.
- When it loads the record from disk, the driver sets FCB bit 23 ("the cached LastUsn is valid for the current
  journal") only when the journal is active and the on-disk UsnJournalId matches the current journal: a stale-epoch
  check like NTFS's journal-id validation.

## NextFileId ordinal

`$SI+0x58` (also ExternalFileId_1 on 3.4) is the directory child-creation ordinal.

- A directory's own row holds the directory's counter, `NextFileId`: the highest ordinal it has assigned (equal to
  its largest surviving child's ordinal unless a later child was deleted). Each child's own record (embedded name row
  or type-0x40 backing) carries its assigned ordinal at `$SI+0x58`.
- `RefsMoveFile` (the unified create/rename/link path) increments the parent directory's NextFileId and stamps the
  child.
- It is persisted to the directory's own row only when the volume version is below 0x30b (3.11), so on native 3.14
  the own row reads 0 while the object-record payload carries it.
- A fresh directory starts at 1 (0/1 reserved); child ordinals are near-contiguous from 2.
- The counter is increment-only: a deleted child's ordinal is never re-used (it stays a permanent gap). So a file's
  reference `(creation-directory OID, ordinal)` is stable over time, never reassigned to a later file, which USN
  correlation relies on.
- It is not a per-write counter.

## HardLinkCount

`$SI+0x70` is the file's link count as the driver last wrote it (read from FCB+0xB4; the writer is
`RefsConvertToStandardInfoLinkCount`, run on every name added or removed and on a rename).

- In an embedded record it reads 1 on every row measured: a file with one name.
- In a split record's type-0x40 backing it is the number of the file's names: it reads more than 1 on most backings
  measured and equals the number of size-matched names on almost all of them; on the volume checked against
  `fsutil hardlink list` the backings matched `fsutil`'s counts exactly. See [Hard Links](../concepts/hard_links.md).
- A few backings read 0. The driver accepts a zero count only on a record whose internal flags (`$SI+0x24`) carry
  0x01 (delete pending) or 0x04 (set when the last link is removed), or on a system object; any other zero-count
  record it treats as dead and queues for triage. Check the internal flags of such a backing before interpreting it.

## The two "0x90"s — `$SI` is not `$I30_INDEX`

A common trap: `$SI` is the root data of the record's table (a type-0x10 own row, or a file's name row or backing,
from `value+0x28`); it is not a sub-record. The embedded type-0x90 sub-record is `$I30_INDEX` (the directory-index
template), a different thing.

Read `$SI` from `value+0x28`, never from a type-0x90 entry: the type-0x90 sub-record is `$I30_INDEX`,
and a top-level type-0x90 row of a system table (such as the Upcase table, OID 0x7) is that table's payload.

See [$I30_INDEX](I30_INDEX.md).

## Last access time

ReFS does not update the last access time on read by default, and the machine can enable it.

- The setting is the registry value `RefsDisableLastAccessUpdate` (DWORD) under
  `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem`. It defaults to 1 (updates disabled) when the value is absent;
  set to 0 (any value other than 1), it enables tracking.
  - The 26100.9818 driver reads the value under `HKLM\SYSTEM\CurrentControlSet\Policies` first, and under
    `Control\FileSystem` only when the policy value is absent: check both keys on the machine.
- It is a machine-wide setting held by the driver, not a volume setting: nothing on the volume records it, so an
  image cannot say whether updating was enabled.
- What an image can show is one-directional: a file whose access time is more than a second later than both its
  modification and creation times shows that updating was active; no such file shows nothing (a copy sets Created
  and Accessed a moment apart, so the margin matters).

Per-handle suppression bits at `CCB+4` (bit 6 = 0x40 access / bit 5 = 0x20 change / bit 4 = 0x10 modify) stop the
driver from updating a time on that handle once a caller has set it (or passed -1). `SetFileTime` sets the access and
modify bits; `NtSetInformationFile` can also set the change bit.

## Driver functions

- `RefsMapStandardInfo` — maps `$SI` from a B+-tree row (and enforces the min-size gate)
- `RefsGetStandardInfo` (the 3.4 driver only) / `RefsSetStandardInfo` (every build read) — read / write
  (`RefsSetStandardInfo` writes through `RefsPartialSetStandardInfo`, which calls `MsUpdateDataWithRoot`)
- `RefsComputeStandardInformationFromFcb` — builds `$SI` from the in-memory FCB state (the v3.14-era drivers;
  `RefsUpdateStandardInformation` in the 3.4 driver)

## Forensic value

| Field | Forensic value |
|-------|----------------|
| Timestamps (0x00–0x18) | the MACB timeline |
| LastUsn + UsnJournalId (0x40 / 0x48) | the file's last `$UsnJrnl:$J` offset and the journal instance it belongs to (written while a journal is active) |
| ReparseTag (0x54) | symlinks, junctions (mount points), app-execution aliases and WSL special files |
| PackedEaSize (0x50) | presence of extended attributes, on rows written by a 3.10 or later driver |
| Internal flags (0x24, 3.14) | a case-sensitive directory (bit 1); the data held in the record (bit 3); a symbolic link's or junction's redirection trust (bit 5) |
| NextFileId ordinal (0x58) | a file's creation order within its home directory (every format; the directory's own counter only below 3.11) — corroborating for timeline reasoning |

**Timestomping detection.** A file has one record and one `$SI`. Each name of a split record (every hard-linked
file) also carries a cached copy of the four times in its name row, refreshed only when the file is opened through
that name (a directory listing does not refresh it). So the
names of a hard-linked file can hold different times (NTFS's hard links share one `$SI`; each NTFS link has its own
`$FILE_NAME`, with its own times).

- A divergence of the names' Created times is evidence to follow up (their Changed times diverge routinely: a
  hard link added later carries the time it was added).
- Agreement is not: a `SetFileTime` through one name updates the file's own record at once, and each name's copy
  is updated when the file is opened through that name (the lab measurement that found both name rows byte-identical
  had opened both names). Which name holds the true birth is not established.

For any file, timestomping can also be checked through:

- the metadata-change time (`$SI+0x10`): when Win32 `SetFileTime` or PowerShell sets the other times, the driver
  stamps the change time with the moment of the change; a native `NtSetInformationFile` call can set it as well, so
  this is a check against common tools, not proof;
- the USN journal, when it was active and its records for the period survive (it records the edit and the create:
  the stronger check);
- the volume creation time, a floor for a file created on this volume (a copy or a restore can carry an older time).

See [Timestomping Detection](../concepts/timestomp_detection.md).

## Raw example

A `$STANDARD_INFORMATION` from a directory's own row on a format 3.14 volume (all four times are equal), with
offsets from the start of the `$SI` (`value+0x28` of the row):

```text
+0x00:  92 10 67 69 18 e6 dc 01    <- Created   (FILETIME)  2026-05-17 16:15
+0x08:  92 10 67 69 18 e6 dc 01    <- Modified  (FILETIME)
+0x10:  92 10 67 69 18 e6 dc 01    <- Changed   (FILETIME)
+0x18:  92 10 67 69 18 e6 dc 01    <- Accessed  (FILETIME)
+0x20:  00 00 00 00 00 00 00 00
+0x28:  62 9b 9f 0a 01 00 00 00    <- SecurityId 0x10a9f9b62 (resolves in the security table, OID 0x530)
```

The four 8-byte FILETIMEs sit at `0x00` / `0x08` / `0x10` / `0x18`; `SecurityId` is the u64 at `0x28`.

## Cross-references

- [Directory Entries](../structures/directory_entries.md) — the `$SI` fields inside embedded records and type-0x40 backings
- [$I30_INDEX](I30_INDEX.md) — the other type-0x90 thing `$SI` is confused with
- [$EA_INFORMATION and $EA](EA_INFORMATION.md) — the packed EA size mirrored at 0x50 by 3.10 and later drivers
- [Security Descriptors](../structures/security_descriptors.md) — the SecurityId at 0x28 (OID 0x530)
- [Version Detection](../concepts/version_detection.md) — how to tell the format, and whether the volume was upgraded (rows written before an upgrade keep the older meaning of 0x50)

## Evidence

The `$SI` layout and the USN / NextFileId fields are read from the drivers (the v3.14-era builds:
`RefsComputeStandardInformationFromFcb`, `RefsComputeStandardInformationInternalFromFcb`,
`RefsWriteFcbUsnRecordToJournal`, `RefsMoveFile`; the 3.4 driver: `RefsUpdateStandardInformation`,
`RefsMapStandardInfo`) and decoded on disk across the corpus.

Per-name time divergence is measured on disk over the corpus: the names' Changed times diverge routinely (12,170
files), their Created times on 31 files of the 36 volumes whose change journal was read (20 of them with a
basic-information change in the journal, the other 11 with no record left). A divergence is evidence when present,
disappears when the file is opened through the stale name, and its absence proves nothing (see
[Hard Links](../concepts/hard_links.md)).

The page is documented against the project's claim register, whose rows carry each finding's evidence grade and
witness. Prior work tabulated these fields twice — once as a *File Table* and once as a *Directory Descriptor* — and
both sets describe this one structure, since a file's `$SI` and a directory's `$SI` share the layout; both are kept
in the register because each records a distinct source table. See [how this was verified](../methodology.md).

The measurements behind the text:

- A directory's change time: the own-row and index-entry copies disagree on 994 of 86,955 directory pairs (1.14 %),
  on 106 of 141 image paths (the paths include byte-identical copies of one volume). Against the PowerShell
  inventory of `lab314_main`, 26 directories compared: 25 equal, 1 differed (OID 0x712, a `$RECYCLE.BIN` entry), and
  there Windows matched the index-entry copy; the same on `lab314_main_step2`; `lab314_4kn` and `lab314_64k` 18 of
  18 identical. The lab314 volumes are the only ones with such ground truth.
- File size and allocated size slots: 0 in 87,674 of 87,674 directory own rows (OID 0x600 and above) over 141 image
  paths.
- HardLinkCount: 1 in 329,120 of 329,120 embedded rows over 141 image paths. Over 107,525 type-0x40 backings on 78
  images it reads more than 1 on 101,252 (94.2 %), equals the number of size-matched names on 99.84 % and reads 0
  on 38 (each with `$SI+0x24` bit 0x01 or 0x04, or a system object). On the `fsutil`-ground-truthed volume the three
  backings read 4 / 2 / 1 against `fsutil hardlink list`'s 4 / 2 / 1.
- The directory flag in own rows (bit 28): 3.4 (`win10refsmini`) 1 of 9, 3.7 (`win1121h2test`) 33 of 113, 3.9
  (`win1122h2test`) 27 of 140, 3.10 (`win1123h2test`) 0 of 91, native 3.14 (`win11refsmini`,
  `win11refstestmftecmd`) 0 of 15 and 0 of 241, 3.14 upgraded from 3.4 (`win10to11refs4g`) 2 of 42. The index entry
  carries it on 86,955 of 86,955 directory index entries.
- Internal flags bit 3 (DataInRecord): set on 586,574 of 586,574 files whose data is inline, on none of 263,526
  files with extents, snapshot-shared or unallocated data, on no directory and on no volume below 3.14 (129 corpus
  images). 0x08 is the most common value on `winsider` (33,553 entries), the one volume counted.
- The case-sensitive flag: 12 directories on 2 of 102 readable volumes; 2 of them hold two names that differ only by
  case.
- UsnJournalId: `fsutil usn createjournal` over an existing journal kept the id on `lab314_main`.
- Last access time: no file with the access time more than 1 s past both other times on `win11bidule` (a copy-heavy
  volume); exactly 1 of 1,286 on the volume with a deliberate read test (`ok.txt`, Accessed 10.4 s after Modified);
  a 60 s margin misses that file. The default (1, disabled) is read in the 17134, 26100 and Insider 29574 drivers.
- The raw example is the own row of the directory `System Volume Information\EDP` (OID 0x7a0) on
  `win11refs4gattributestest2` (table page at image offset 0x1808000, row +0x3f8).

<!-- findings: FN_DTBL_001, FN_LINK_002, FN_LINK_003, FS_OTBL_RA_008, FS_SNAP_RA_001, MD_ATTR_RA_015, MD_CS_RA_003, MD_DDIR_001, MD_DDIR_002, MD_DDIR_003, MD_DDIR_004, MD_DDIR_006, MD_FTBL_001, MD_FTBL_002, MD_FTBL_003, MD_FTBL_004, MD_FTBL_006, MD_INTG_RA_001, MD_SI_RA_002, MD_SI_RA_004, MD_SI_RA_005, MD_SI_RA_006, MD_SI_RA_007, MD_SI_RA_008, MD_SI_RA_010, MD_SI_RA_011, MD_SI_RA_012, MD_SI_RA_013, MD_SI_RA_014, MD_SI_SA_001, MD_SI_SA_002, MD_TS_RA_001, MD_TS_RA_002, MD_TS_RA_004, MD_TS_RA_008 -->
