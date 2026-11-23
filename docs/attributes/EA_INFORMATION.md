# $EA_INFORMATION and $EA
<!-- site: description "Extended attributes: a 20-byte size index and the EA list itself, where WSL keeps its Linux metadata." -->

Extended attributes (EAs) on ReFS are a two-part structure:

- `$EA_INFORMATION` (embedded type 0xD0) is the size index.
- `$EA` (embedded type 0xE0) is the body, a standard NT `FILE_FULL_EA_INFORMATION` chain.
- Both are single-instance sub-records in the object's own record: a file's type-0x30 name row or its type-0x40
  backing, a directory's type-0x10 own row.
- EAs are the storage mechanism for WSL Linux metadata (`$LXUID`, `$LXGID`, `$LXMOD`, `$LXDEV`) and for
  kernel-cache state (`$Kernel.Purge.*`).

| Property | $EA_INFORMATION | $EA |
|----------|-----------------|-----|
| Type code | 0xD0 | 0xE0 |
| Instances | single-instance (marker 0x80000001) | single-instance (marker 0x80000001) |
| Where it lives | the object's own record (a file's name row or type-0x40 backing; a directory's type-0x10 own row) | the same record, beside its `$EA_INFORMATION`: the two occur as one pair per file |
| Size | 20 bytes, fixed | variable: a 12-byte header, then the chain |
| Added in | not known: the EA code is in the 26100 and Insider drivers read; the 3.4 driver (17134) has no EA set path (it looks up a file's `$EA_INFORMATION` when the file is opened, and `RefsQueryEaInfo` returns a size), and no 3.7 to 3.10 driver is held. EA-bearing records are seen only on 3.14 volumes | the same |

See [Directory Entries](../structures/directory_entries.md) for the sub-record chain that holds them.

## $EA_INFORMATION value layout (type 0xD0)

Sub-record: marker 0x80000001 (single-instance), type code 0x00D0. Fixed 20-byte value:

<!-- site: hexfig "attr_ea_information_win11refs4gattributes" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | 8 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 2 | PackedEaSize (u16) | the NTFS-conventional packed EA size, Σ per-entry `5 + EaNameLength + EaValueLength`; mirrored at `$SI+0x50` (see [The two size fields](#the-two-size-fields)) |
| 0x0E | 2 | NeedEaCount (u16) | the number of EAs flagged `FILE_NEED_EA`; 0 on every value read |
| 0x10 | 4 | Unpacked size (u32) | Σ `align4(8 + EaNameLength + 1 + EaValueLength)` — the byte length of the `FILE_FULL_EA_INFORMATION` chain (always ≥ PackedEaSize) |

### The two size fields

The two size fields are distinct: the u16 at `val[0x0C]` is the logical PackedEaSize (the value stored at
`$SI+0x50`); `val[0x10]` is the chain's length. `RefsReplaceFileEas` writes the three fields (the u16 PackedEaSize,
the u16 NeedEaCount, the u32 unpacked size; 26100.9444, read twice), the load path reads the u16, and
`RefsComputeStandardInformationFromFcb` copies `FCB+0xA0` into `$SI+0x50`.

- The mirror at `$SI+0x50` is written by 3.10 and later drivers, and lets a reader see that a file has EAs without
  reading the body.
- On a volume upgraded from an older format, rows written before the upgrade hold the reparse tag's low 16 bits at
  `$SI+0x50` instead: there, test for the `$EA_INFORMATION` sub-record itself (or the attribute bit 0x40000 in the
  record).

## $EA value layout (type 0xE0)

Sub-record: marker 0x80000001 (single-instance), type code 0x00E0.

<!-- site: hexfig "attr_ea_win11refs4gattributes" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | the chain's length in bytes, equal to `$EA_INFORMATION`'s unpacked size; the value can be longer than 12 + this size |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | var | EA chain | `FILE_FULL_EA_INFORMATION` entries |

Each `FILE_FULL_EA_INFORMATION` entry (at `value+0x0C`, chained via NextEntryOffset, 4-byte aligned):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | NextEntryOffset | the entry's own 4-aligned size, the last entry included (refs.sys stores the size when it is given 0); the chain ends at the data-area size |
| 0x04 | 1 | Flags | 0 or FILE_NEED_EA |
| 0x05 | 1 | EaNameLength | name length, excluding the null terminator |
| 0x06 | 2 | EaValueLength | value-data length |
| 0x08 | N+1 | EaName | ASCII name + null terminator |
| var | M | EaValue | raw value bytes, at `0x08 + EaNameLength + 1` |

The per-entry value starts at `entry + 8 + EaNameLength + 1`.

## Common EA names

| EA name | Value | What it is |
|---------|-------|------------|
| `$LXUID`, `$LXGID`, `$LXMOD`, `$LXDEV` | 4, 4, 4 and 8 bytes | the Linux owner, group, mode and device number of a file written through WSL: see [WSL Linux metadata](#wsl-linux-metadata) |
| `$KERNEL.PURGE.*` | var | a kernel EA that refs.sys deletes when the file's data changes: see [Kernel purge EAs](#kernel-purge-eas) |
| `$CI.CATALOGHINT` | var | an ordinary EA that refs.sys stores without interpreting: see [$CI.CATALOGHINT](#cicataloghint) |

### WSL Linux metadata

WSL writes these four EAs to carry the Linux identity of a file that the Windows file model has no slot for; they
require a `-o metadata` mount. What they mean for an examiner, and how they combine with the WSL reparse tags, is on
[WSL / Linux Metadata](../concepts/wsl_metadata.md#the-two-artifact-families).

refs.sys decodes them in `RefsQueryLxMetadataEa`, which gates each `$LX*` on its exact value length and fills
`FILE_STAT_LX_INFORMATION`:

| EA name | Value | Destination in `FILE_STAT_LX_INFORMATION` | Presence bit |
|---------|-------|--------------------------------------------|--------------|
| `$LXUID` | 4 bytes (u32) | Linux UID → `+0x4c` | 0x1 |
| `$LXGID` | 4 bytes (u32) | Linux GID → `+0x50` | 0x2 |
| `$LXMOD` | 4 bytes (u32 `mode_t`) | permission + file-type bits → `+0x54` | 0x4 |
| `$LXDEV` | 8 bytes (u32 major + u32 minor) | device number (device nodes only) → major `+0x58`, minor `+0x5c` | 0x8 |

The presence-flags word is at `FILE_STAT_LX_INFORMATION+0x48`.

### Kernel purge EAs

An EA whose name begins with `$Kernel.Purge.` is one that refs.sys deletes when the file's data changes (the
driver calls them kernel EAs: `RefsPurgeKernelEA`; 26100.9444).

- The deletion runs on four kinds of change:
  - `RefsPostUsnChange` calls `RefsPurgeKernelEaUsnUnconditionalCallback` for each change it posts to a file that is
    not a system file, before it tests whether the change journal is active;
  - the callback runs `RefsPurgeKernelEA` when the reasons include 0x1, 0x2, 0x4 (the default data stream
    overwritten, extended or truncated) or 0x100000 (reparse-point change), and not a delete;
  - `RefsPurgeKernelEA` matches each EA name against the `$Kernel.Purge.` prefix (case-insensitively) and deletes
    each match.
- On disk the names are stored upper-case, for example `$KERNEL.PURGE.ESBCACHE` (a 30-byte value) and
  `$KERNEL.PURGE.APPXFICACHE`, on Windows system and app files of a boot volume. What each cache holds is not read
  here.
- So such an EA suggests that the file's data was not overwritten, extended or truncated, and its reparse point not
  changed, through a 26100 or Insider driver since the EA was written (17134 has none of these functions). It does not
  prove it: the callback also tests conditions the reading did not decode (26100.9444 :113218-113222). A change made outside the driver, an image edited by hand for one, leaves it in place.

### $CI.CATALOGHINT

`$CI.CATALOGHINT` is observed on Windows system files of a boot volume.

- Its name does not begin with `$Kernel.Purge.`, so the purge above does not delete it.
- refs.sys does not interpret it: the name occurs in no driver build read, and the value is stored as written.
  What it holds is not read here.

## Cross-references

- [$STANDARD_INFORMATION](STANDARD_INFORMATION.md) — the PackedEaSize (`val[0x0C]`) mirrored at `$SI+0x50` by 3.10 and later drivers
- [WSL / Linux Metadata](../concepts/wsl_metadata.md) — the full WSL artifact picture
- [$REPARSE_POINT](REPARSE_POINT.md) — WSL special-file *types* are reparse points (the ownership/mode lives here)
- [Directory Entries](../structures/directory_entries.md) — the embedded sub-record location

## Evidence

The layouts are read from the v3.14-era drivers (`RefsLookupEasOnFile`, `RefsReplaceFileEas`,
`RefsQueryLxMetadataEa`) and decoded on 3.14 volumes, as are the WSL `$LX*` entries; the 17134 driver has no EA code
beyond `RefsQueryEaInfo`, and no 3.7 to 3.10 driver is held. The page is documented against the project's claim register. See
[how this was verified](../methodology.md).

The measurements and sources behind the text:

- NeedEaCount 0, and the `$EA` value longer than 12 + its data area (60 in a 76-byte value), on the 16 values read.
- `$EA` values of 44 to 209 bytes over 3,854 entries; `$EA_INFORMATION` and `$EA` co-occur one pair per file.
- The EA names on `winsider` (the Insider 29574 boot volume): `$CI.CATALOGHINT` on 2,182 files,
  `$KERNEL.PURGE.ESBCACHE` on 1,624, `$KERNEL.PURGE.APPXFICACHE` on 1,618, `APPLICENSING` on 3. One decoded record:
  a hard-linked Store-app asset (`SplashScreen.scale-100.png`) whose type-0x40 backing holds a 140-byte `$EA` with
  `$KERNEL.PURGE.ESBCACHE` and `$KERNEL.PURGE.APPXFICACHE`, beside its `$EA_INFORMATION`.
- The purge path is read on 26100.9444: `RefsPostUsnChange` → `RefsPurgeKernelEaUsnUnconditionalCallback` (the
  reason test `param_3 & 0x100007`, not 0x200) → `RefsPurgeKernelEA` (the prefix match `RtlPrefixString(..., TRUE)`,
  then `RefsDeleteEa`). The functions are present in every 26100.x and Insider build read, and absent from 17134.
- `$CI.CATALOGHINT`: absent from the string exports and decompilations of every refs.sys build read.

<!-- findings: FS_REPS_RA_002, FS_REPS_RA_003, MD_ATTR_RA_010, MD_ATTR_RA_011, MD_ATTR_RA_012, MD_ATTR_RA_013, MD_ATTR_RA_019, MD_ATTR_010 -->
