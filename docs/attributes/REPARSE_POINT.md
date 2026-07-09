# $REPARSE_POINT

`$REPARSE_POINT` stores the inline `REPARSE_DATA_BUFFER` for a reparse point — a symlink, junction,
mount point, or WSL special file (embedded type 0xC0, schema 0x1C0; the v3.7+ "v2" format). It appears
as a single-instance sub-record inside a file's type-0x10 own-row and inside resident type-0x30
directory entries. The reparse tag is also mirrored into `$STANDARD_INFORMATION` at `$SI+0x54`.

## Value layout

**Sub-record:** marker 0x80000001 (single-instance), type code 0x00C0, subtype 0x0000.

**Value:**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | value length − 12 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | Reparse tag | `IO_REPARSE_TAG_*` constant |
| 0x10 | 2 | Reparse data length | length of the type-specific data |
| 0x12 | 2 | Reserved | 0 |
| 0x14 | var | Reparse data | the type-specific `REPARSE_DATA_BUFFER` content |

**Symlink (tag 0xA000000C):**

| Offset | Size | Field |
|--------|------|-------|
| 0x14 | 2 | Substitute name offset |
| 0x16 | 2 | Substitute name length |
| 0x18 | 2 | Print name offset |
| 0x1A | 2 | Print name length |
| 0x1C | 4 | Flags (1 = relative) |
| 0x20 | var | Path strings (UTF-16LE) |

**Mount point / junction (tag 0xA0000003):** the same layout *without* the 4-byte Flags field — the path strings begin at 0x1C.

Value sizes range roughly 188–548 bytes, depending on the path-string length.

## Reparse tags

`refs.sys` structurally recognizes **only two** tags: `0xA0000003` (junction — gated to directory
targets) and `0xA000000C` (symlink — gated on privilege / redirection-trust level). **Every other tag is
stored verbatim with no interpretation** — WSL, WCI, WOF, and dedup tag handling lives entirely in
minifilters, not in `refs.sys`.

| Tag | Constant | Notes |
|-----|----------|-------|
| 0xA000000C | `IO_REPARSE_TAG_SYMLINK` | file and directory symlinks (the most common) |
| 0xA0000003 | `IO_REPARSE_TAG_MOUNT_POINT` | junctions / mount points |
| 0x8000001B | `IO_REPARSE_TAG_APPEXECLINK` | Store-app execution alias (payload = package + target-exe path strings) |
| 0x80000023 | `IO_REPARSE_TAG_AF_UNIX` | WSL Unix-domain socket |
| 0x80000024 | `IO_REPARSE_TAG_LX_FIFO` | WSL named pipe (FIFO) — empty payload; the tag is the type marker |
| 0x80000025 | `IO_REPARSE_TAG_LX_CHR` | WSL character device |
| 0x80000026 | `IO_REPARSE_TAG_LX_BLK` | WSL block device |
| 0xA000001D | `IO_REPARSE_TAG_LX_SYMLINK` | WSL Linux symlink — produced when the target is **not** representable as a Windows path: an **absolute** Linux target (`ln -s /etc/passwd`) or an ext4 symlink copied with `cp -a`. (A **relative** name that resolves yields a Windows symlink `0xA000000C` instead.) Confirmed on disk (E57). |
| 0x80000017 / 0x80000018 / 0x80000013 | WOF / WCI / DEDUP | defined Windows tags, handled by minifilters |

## WSL special files

WSL records a special file in **two separate** mechanisms — only one of which is a reparse point:

- **The special-file *type*** (FIFO, socket, character/block device, Linux symlink) is a **reparse
  point**, using the `LX_*` / `AF_UNIX` tags above. The payload format is defined by the WslFs
  minifilter; for a FIFO the payload is empty (the tag alone marks the type).
- **The Linux *ownership and mode*** (`$LXUID` / `$LXGID` / `$LXMOD` / `$LXDEV`) are **extended
  attributes**, not reparse data — see [$EA_INFORMATION and $EA](EA_INFORMATION.md). They require a WSL
  `-o metadata` mount.

So a WSL device node carries both: a reparse point (the `LX_CHR` / `LX_BLK` tag) *and* an `$EA` chain
(`$LXMOD` carrying the `S_IFMT` type bits, `$LXDEV` carrying the major:minor numbers).

## Cross-references

- [$STANDARD_INFORMATION](STANDARD_INFORMATION.md) — the reparse tag is mirrored at `$SI+0x54`
- [$EA_INFORMATION and $EA](EA_INFORMATION.md) — the WSL `$LX*` ownership/mode EAs
- [Directory Entries](../structures/directory_entries.md) — the embedded sub-record location
- [WSL / Linux Metadata](../concepts/wsl_metadata.md) — the full WSL artifact picture

## Evidence

Type 0xC0 / schema 0x1C0 and the value layout are confirmed in the decompiled driver (E2) and raw-disk
decoded across the corpus (RD); the recognize-vs-store-verbatim behavior is from the driver's reparse
handling (only 0xA0000003 / 0xA000000C are interpreted). Findings: **FS_REPS_RA_003, FS_REPS_RA_002, MD_ATTR_RA_010, MD_ATTR_RA_012** (WSL) and the corrected
reparse-tag table. See [how this was verified](../methodology.md).
