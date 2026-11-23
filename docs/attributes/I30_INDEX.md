# $I30_INDEX
<!-- site: description "A directory's index template: exactly one per directory, in its own row, written once." -->

> Naming note: this page documents the embedded type-0x90 `$I30_INDEX` directory-index config template.
> The name `$I30` (the directory-index *stream name*, checked in `RefsFillStandardInfo` /
> `RefsCheckValidAttributeAccess`) refers to this same template. The driver's attribute-definition table names type
> 0x90 `$INDEX_ROOT` and type 0xA0 `$INDEX_ALLOCATION` (the same from 17134 to Insider 29574).

`$I30_INDEX` (embedded type 0x90) is the B+-tree index configuration template for a directory's "$I30" entry index.

- Every directory-bearing object measured — the root directory (OID 0x600) and every user OID ≥ 0x701 — has
  exactly one type-0x90 sub-record in its type-0x10 value; non-directory system pseudo-OIDs have none.
- It is one constant 128-byte template per directory, created with the directory's index; no driver path read
  rewrites it, and repair (`RefsSalvageIndexTable`) can create it again (17134, 26100.9444).

| Property | Value |
|----------|-------|
| Type code | 0x90 (subtype 0x0005) |
| Instances | multi-instance (marker 0x80000002) in the 3.7 and later key; the 3.4 key carries no marker. Exactly one per directory |
| Where it lives | the type-0x10 own row of every directory-bearing object |
| Size | 140 bytes when written by a 3.7 or later driver; 148 bytes when written by the 3.4 driver |
| Added in | 3.4 or earlier: present on every format read (3.4, Windows 10 1803, driver 17134, is the oldest held) |

## Value layout (format 3.7 and later)

The key and value depend on the driver that wrote them: the 3.4 form, and the 3.7+ form. An upgraded volume keeps the
3.4 form in directories created before the upgrade. The 9 config words at `value[0x00:0x24]` were identical on every
directory compared.

Key — format 3.7 and later (24 bytes):

<!-- site: hexfig "attr_i30_win11refs2tspecials" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Value length | 0x8C (140) |
| 0x08 | 4 | Marker | 0x80000002 |
| 0x0C | 2 | Type code | 0x0090 |
| 0x0E | 2 | Subtype | 0x0005 |
| 0x10 | 8 | Stream name | "$I30" (UTF-16LE, no terminator) |

Value:

<!-- site: hexfig-rows "attr_i30_win11refs2tspecials" "value" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 — common sub-record prefix |
| 0x04 | 4 | Data-area size | 0x80 (128) = value length − 12 |
| 0x08 | 4 | Content offset | 0x0C — common sub-record prefix |
| 0x0C | 4 | Index header size | 0x30 (48) |
| 0x10 | 4 | Index flags | 0x00010240: collation / type parameters |
| 0x14 | 4 | Key descriptor | 0x16 (22): index key-format descriptor |
| 0x18 | 4 | Entry header size | 0x10 (16) |
| 0x1C | 4 | Entry size | 0x70 (112): minimum index entry size |
| 0x20 | 4 | Entry size (repeat) | 0x70 (112) |
| 0x24 | 104 | Reserved | 0: unused template space |

## Format 3.4 difference

Key — format 3.4 (20 bytes): `0x00` value length 0x94 (148), `0x08` type code 0x00000090 (no marker), `0x0C`
stream name "$I30" (UTF-16LE, 8 bytes, no terminator: the u16 0x0024 at `0x0C` is the `$`).

The value carries the same config words at `0x00` to `0x23`; its reserved tail at `0x24` is 112 bytes, so the value
is 148 bytes (the extra 8 bytes are trailing zero pad).

## Version differences

The config region (`value[0x00:0x24]`) was identical on every directory compared; only the wrapper changes:

- from 3.7, a 140-byte value and a 24-byte key with the multi-instance marker (0x80000002) and the stream name
  "$I30";
- on 3.4, a 148-byte value and a 20-byte key with no marker, and the same stream name "$I30" at key `0x0C`.

So there are two distinct full records but one invariant config payload.

## Cross-references

- [Attributes — Forensic Reference](../attributes/README.md) — the two-level attribute model
- [Directory Entries](../structures/directory_entries.md) — the directory B+-tree this template configures

## Evidence

The stream name and the template are read in the driver (`RefsCreateDirectoryIndex` creates attribute 0x90 named
`$I30` with these constants; the `$I30` string literal) and decoded on disk, where the config payload was identical
on every directory compared. The page is documented against the project's claim register. See
[how this was verified](../methodology.md).

The measurements behind the text:

- The config payload: identical on 418 directories on four images (v3.4, v3.14 and Insider).
- The 3.7+ form: 140-byte values on 3.7 (111), 3.9 (276) and 3.10 (178); 70 values of 148 bytes on 3.14 volumes
  (directories created before an upgrade).
- One per directory: the type-0x90 row is on 100 % of the 32,721 user OIDs of a 110-image census, and on 26,668 of
  26,668 OIDs of the Insider boot volume.

<!-- findings: FS_SNAP_RA_001, MD_ATTR_010, MD_ATTR_RA_015, MD_ATTR_RA_017 -->
