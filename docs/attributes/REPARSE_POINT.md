# $REPARSE_POINT
<!-- site: description "A reparse point's data (symlink, junction, mount point, WSL special file), inline in the object's record." -->

`$REPARSE_POINT` stores the inline `REPARSE_DATA_BUFFER` for a reparse point — a symlink, junction, mount point, or
WSL special file (embedded type 0xC0).

- It is a single-instance sub-record of the object's own record: a file's type-0x30 name row (an embedded record)
  or its type-0x40 backing (a split record), a directory's type-0x10 own row.
- On 3.7 to 3.10 a split file's backing carries only the tag mirror (at backing `+0x7C`), not the buffer, on the
  volumes read; on 3.14 the backing holds the buffer.
- The reparse tag is also mirrored into `$STANDARD_INFORMATION` at `$SI+0x54`.

| Property | Value |
|----------|-------|
| Type code | 0xC0 (the 3.4 driver reads reparse data as type 0xC0 too; no type-0x70 row is observed in user objects) |
| Instances | single-instance (marker 0x80000001) |
| Where it lives | the object's own record: a file's name row or type-0x40 backing; a directory's type-0x10 own row (see [Where to find it on a directory](#where-to-find-it-on-a-directory)) |
| Size | variable: from 20 bytes (a WSL special file) to 972 bytes (a symlink) on the corpus; a symlink's or junction's grows with its path strings |
| Added in | 3.4 or earlier: the 3.4 driver (17134) already reads type 0xC0 |

## Value layout

Sub-record: marker 0x80000001 (single-instance), type code 0x00C0, subtype 0x0000.

<!-- site: hexfig "attr_reparse_point_win11refs2tspecials" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | value length − 12 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | Reparse tag | `IO_REPARSE_TAG_*` constant |
| 0x10 | 2 | Reparse data length | length of the type-specific data |
| 0x12 | 2 | Reserved | 0 |
| 0x14 | var | Reparse data | the type-specific `REPARSE_DATA_BUFFER` content |

Symlink (tag 0xA000000C):

<!-- site: hexfig-rows "attr_reparse_point_win11refs2tspecials" "symlink" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x14 | 2 | Substitute name offset | |
| 0x16 | 2 | Substitute name length | |
| 0x18 | 2 | Print name offset | |
| 0x1A | 2 | Print name length | |
| 0x1C | 4 | Flags | 1 = relative |
| 0x20 | var | Path strings | UTF-16LE |

Mount point / junction (tag 0xA0000003): the same layout *without* the 4-byte Flags field — the path strings begin
at 0x1C.

On the corpus a symlink's value is 68 to 972 bytes and a junction's 68 to 380, growing with the two path strings; a
WSL socket's, FIFO's or device's is 20 bytes, and a WSL symlink's 36 to 44.

### Where to find it on a directory

On a file, the buffer is the type-0xC0 sub-record of the file's record (its name row, or on 3.14 its backing). On a
directory reparse point — a junction or a directory symlink — the directory's own table has no top-level `0xC0` row:

- the directory's own table holds a single row keyed 0x10, and the buffer sits in the attribute tree embedded in that
  row's value, alongside the `0x90` and `0x39` attributes;
- the name row in the parent directory is an 84-byte index entry with no room for it.

A reader that looks only at top-level rows therefore finds nothing and reports the target as absent, though it is
fully present. Across the image corpus more than a quarter of the reparse-bearing objects keep their buffer only there;
on a real Windows volume nearly all of them do — the familiar compatibility junctions (`\??\C:\ProgramData`,
`\??\C:\Users\Default`, `Program Files`, …).

Two decode consequences follow:

- A junction commonly carries print name length 0, so the substitute name is the authoritative target — never fall
  back to the tag's *name*.
- If the object's attribute set is large enough that its embedded tree becomes an index node, the attributes live one
  level further down again (see [Attributes](../concepts/attributes.md)), so the descent has to be followed there too.

## Reparse tags

`refs.sys` structurally recognizes only two tags: `0xA0000003` (junction — gated to directory targets) and
`0xA000000C` (symlink — gated on privilege / redirection-trust level). Every other tag is stored verbatim with no
interpretation — WSL, WCI, WOF, and dedup tag handling lives entirely in minifilters, not in `refs.sys`.

| Tag | Constant | Notes |
|-----|----------|-------|
| 0xA000000C | `IO_REPARSE_TAG_SYMLINK` | file and directory symlinks (the most common) |
| 0xA0000003 | `IO_REPARSE_TAG_MOUNT_POINT` | junctions / mount points |
| 0x8000001B | `IO_REPARSE_TAG_APPEXECLINK` | Store-app execution alias (payload = package + target-exe path strings) |
| 0x80000023 | `IO_REPARSE_TAG_AF_UNIX` | Unix-domain socket; WSL writes it (see [WSL / Linux Metadata](../concepts/wsl_metadata.md#forensic-implications)) |
| 0x80000024 | `IO_REPARSE_TAG_LX_FIFO` | WSL named pipe (FIFO) — empty payload; the tag is the type marker |
| 0x80000025 | `IO_REPARSE_TAG_LX_CHR` | WSL character device |
| 0x80000026 | `IO_REPARSE_TAG_LX_BLK` | WSL block device |
| 0xA000001D | `IO_REPARSE_TAG_LX_SYMLINK` | WSL Linux symlink — produced when the target is not representable as a Windows path: an absolute Linux target (`ln -s /etc/passwd`) or an ext4 symlink copied with `cp -a`. (A relative name that resolves yields a Windows symlink `0xA000000C` instead.) Confirmed on disk. |
| 0x80000017 / 0x80000018 / 0x80000013 | WOF / WCI / DEDUP | defined Windows tags, handled by minifilters; not observed in the corpus |

## WSL special files

WSL records a special file in two separate mechanisms — only one of which is a reparse point:

- The special-file *type* (FIFO, socket, character/block device, Linux symlink) is a reparse point, using the
  `LX_*` / `AF_UNIX` tags above. The payload format is WSL's, not refs.sys's (refs.sys stores it verbatim); for a
  FIFO the payload is empty (the tag alone marks the type).
- The Linux *ownership and mode* (`$LXUID` / `$LXGID` / `$LXMOD` / `$LXDEV`) are extended attributes, not reparse
  data — see [$EA_INFORMATION and $EA](EA_INFORMATION.md). They require a WSL `-o metadata` mount.

So a WSL device node carries both: a reparse point (the `LX_CHR` / `LX_BLK` tag) *and* an `$EA` chain (`$LXMOD`
carrying the `S_IFMT` type bits, `$LXDEV` carrying the major:minor numbers).

## Cross-references

- [$STANDARD_INFORMATION](STANDARD_INFORMATION.md) — the reparse tag is mirrored at `$SI+0x54`
- [$EA_INFORMATION and $EA](EA_INFORMATION.md) — the WSL `$LX*` ownership/mode EAs
- [Directory Entries](../structures/directory_entries.md) — the embedded sub-record location
- [WSL / Linux Metadata](../concepts/wsl_metadata.md) — the full WSL artifact picture
- [Reparse Index](REPARSE.md) — the volume-wide index of reparse-tagged objects (OID 0x540)

## Evidence

Type 0xC0 and the value layout are read in the decompiled driver and decoded on disk across the
corpus; the recognize-vs-store-verbatim behaviour is from the driver's reparse handling (only 0xA0000003 /
0xA000000C are interpreted). The page is documented against the project's claim register. See
[how this was verified](../methodology.md).

The measurements behind the text:

- Buffers kept only in a directory's embedded tree: 98 of 341 reparse-bearing objects across the image corpus; 78
  of 81 on the real Windows volume.
- Split files: the target buffer is recovered from the file's own backing on 3.14; on 3.7 to 3.10 the backing carries
  only the tag mirror, and where the buffer is kept there is not established.
- Type 0x70: zero sub-records in user objects across 111 images; the 17134 driver's reparse lookup asks for
  attribute 0xC0.
- Tags observed over the 124 ReFS volumes of the corpus (4,153 type-0xC0 rows): SYMLINK 3,906, MOUNT_POINT 161,
  APPEXECLINK 72, LX_SYMLINK 8 (the `win11refs8g` volumes), LX_FIFO 3, and AF_UNIX, LX_CHR and LX_BLK one each
  (`win11refs2gtargeted`). WOF, WCI and DEDUP are not observed.
- Value lengths by tag: SYMLINK 188 to 700 bytes on 3.4 to 3.10 and 68 to 972 on 3.14; MOUNT_POINT 68 to 380;
  APPEXECLINK 356 to 516; LX_SYMLINK 36 to 44; the other WSL tags 20.

<!-- findings: FS_REPS_RA_002, FS_REPS_RA_003, FS_REPS_RA_005, MD_ATTR_RA_010, MD_ATTR_RA_012, MD_ATTR_RA_016
     errata: E57 -->
