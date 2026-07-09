# $EA_INFORMATION and $EA

Extended attributes (EAs) on ReFS are a **two-part** structure: **`$EA_INFORMATION`** (embedded type
0xD0, schema 0x1D0; v3.7+) is the size index, and **`$EA`** (embedded type 0xE0, schema 0x1E0; v3.14+) is
the body — a standard NT `FILE_FULL_EA_INFORMATION` chain. Both are single-instance sub-records in the
type-0x10 own-row. EAs are the storage mechanism for **WSL Linux metadata** (`$LXUID`, `$LXGID`,
`$LXMOD`, `$LXDEV`) and kernel-cache state (`$Kernel.Purge.*`).

## $EA_INFORMATION value layout (type 0xD0)

Sub-record: marker 0x80000001 (single-instance), type code 0x00D0. Fixed 20-byte value:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | 8 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | **PackedEaSize** | the NTFS-conventional packed EA size, Σ per-entry `5 + EaNameLength + EaValueLength`. **Mirrored into `$SI+0x50` on v3.10+** (= `FCB+0xA0`), enabling EA-presence detection without reading the body |
| 0x10 | 4 | Serialized footprint | Σ `align4(8 + EaNameLength + 1 + EaValueLength)` — the on-disk byte footprint of the chain (always ≥ `val[0x0C]`) |

The two size fields are distinct: **`val[0x0C]` is the logical PackedEaSize** (the value stored at
`$SI+0x50`); `val[0x10]` is the physical chain length. (`RefsReplaceFileEas` sets `FCB+0xA0 = val[0x0C]`;
`RefsComputeStandardInformationFromFcb` reads it into `$SI+0x50`.)

## $EA value layout (type 0xE0)

Sub-record: marker 0x80000001 (single-instance), type code 0x00E0.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | value length − 12 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | var | EA chain | `FILE_FULL_EA_INFORMATION` entries |

Each `FILE_FULL_EA_INFORMATION` entry (at `value+0x0C`, chained via NextEntryOffset, 8-byte aligned):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | NextEntryOffset | offset to the next entry (0 = last) |
| 0x04 | 1 | Flags | 0 or FILE_NEED_EA |
| 0x05 | 1 | EaNameLength | name length, excluding the null terminator |
| 0x06 | 2 | EaValueLength | value-data length |
| 0x08 | N+1 | EaName | ASCII name + null terminator |
| 0x08+N+1 | M | EaValue | raw value bytes |

The per-entry value starts at `entry + 8 + EaNameLength + 1`.

## Common EA names

| EA name | Value | Purpose |
|---------|-------|---------|
| `$LXUID` | 4 bytes (u32) | WSL Linux UID → `FILE_STAT_LX_INFORMATION+0x4c`, presence-flag bit 0x1 |
| `$LXGID` | 4 bytes (u32) | WSL Linux GID → `+0x50`, bit 0x2 |
| `$LXMOD` | 4 bytes (u32 `mode_t`) | WSL permission + file-type bits → `+0x54`, bit 0x4 |
| `$LXDEV` | 8 bytes (u32 major + u32 minor) | WSL device number (device nodes only) → major `+0x58`, minor `+0x5c`, bit 0x8 |
| `$Kernel.Purge.*` | var | kernel-purgeable cache state (the driver matches the `$Kernel.Purge.` prefix and deletes these in `RefsPurgeKernelEA`) |
| `$CI.CATALOGHINT` | var | Code-Integrity catalog hint |

The WSL presence-flags word is at `FILE_STAT_LX_INFORMATION+0x48` (bits 0x1/0x2/0x4/0x8 for
UID/GID/MOD/DEV); the decode is `RefsQueryLxMetadataEa`, which gates each `$LX*` on its exact value
length. WSL EAs require a `-o metadata` mount.

## Cross-references

- [$STANDARD_INFORMATION](STANDARD_INFORMATION.md) — the PackedEaSize (`val[0x0C]`) is mirrored at `$SI+0x50` (v3.10+)
- [WSL / Linux Metadata](../concepts/wsl_metadata.md) — the full WSL artifact picture
- [$REPARSE_POINT](REPARSE_POINT.md) — WSL special-file *types* are reparse points (the ownership/mode lives here)
- [Directory Entries](../structures/directory_entries.md) — the embedded sub-record location

## Evidence

`$EA_INFORMATION` (0xD0/0x1D0, v3.7+) and `$EA` (0xE0/0x1E0, v3.14+) and their layouts are confirmed in
the decompiled driver (E2 — `RefsLookupEasOnFile`, `RefsReplaceFileEas`, `RefsQueryLxMetadataEa`) and
raw-disk decoded across the corpus (RD). Finding: **FS_REPS_RA_003, FS_REPS_RA_002, MD_ATTR_RA_010, MD_ATTR_RA_011, MD_ATTR_RA_012** (WSL `$LX*`). See
[how this was verified](../methodology.md).
