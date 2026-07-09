# $I30_INDEX

> **Naming note (findings MD_ATTR_010/MD_ATTR_RA_015/FS_SNAP_RA_001):** this page documents the **embedded type-0x90 `$I30_INDEX`**
> directory-index config template. The legacy/alias name **`$I30`** (the directory-index *stream name*,
> checked in `RefsFillStandardInfo` / `RefsCheckValidAttributeAccess`) refers to this same template. The
> NTFS-convention name **`$INDEX_ROOT` proper maps to type `0xA0` / schema `0x1A0`** — a *separate,
> non-embedded* attribute. The two are distinct despite the shared NTFS lineage.

`$I30_INDEX` (embedded type 0x90, schema 0x190) is the **B+-tree index configuration template** for a
directory's "$I30" entry index. Every directory-bearing object — the root directory (OID 0x600) and every
user OID ≥ 0x701 — has exactly **one** type-0x90 sub-record in its type-0x10 value; non-directory system
pseudo-OIDs have none. It is a write-once template, not a per-file record.

## Value layout

The key and value differ between v3.14+ and v3.4; the **9 config words at `value[0x00:0x24]` are
byte-for-byte constant** across all versions and images.

**Key — v3.14+ (24 bytes):**

| Offset | Size | Field | Value |
|--------|------|-------|-------|
| 0x00 | 8 | Value length | 0x8C (140) |
| 0x08 | 4 | Marker | 0x80000002 |
| 0x0C | 2 | Type code | 0x0090 |
| 0x0E | 2 | Subtype | 0x0005 |
| 0x10 | 8 | Stream name | "$I30" (UTF-16LE) + null |

**Key — v3.4 (20 bytes):** `0x00` value length 0x94 (148), `0x08` type code 0x00000090 (no marker),
`0x0C` reserved 0x0024, `0x0E` stream name "I30" (no `$`).

**Value:**

| Offset | Size | Field | Constant | Description |
|--------|------|-------|----------|-------------|
| 0x00 | 4 | Padding | 0 | common sub-record prefix |
| 0x04 | 4 | Data-area size | 0x80 (128) | = value length − 12 on v3.14+ |
| 0x08 | 4 | Content offset | 0x0C | common sub-record prefix |
| 0x0C | 4 | Index header size | 0x30 (48) | |
| 0x10 | 4 | Index flags | 0x00010240 | collation / type parameters |
| 0x14 | 4 | Key descriptor | 0x16 (22) | index key-format descriptor |
| 0x18 | 4 | Entry header size | 0x10 (16) | |
| 0x1C | 4 | Entry size | 0x70 (112) | minimum index entry size |
| 0x20 | 4 | Entry size (repeat) | 0x70 (112) | |
| 0x24 | 104 / 112 | Reserved | 0 | unused template space (104 bytes on v3.14+, 112 on v3.4) |

The value is **140 bytes on v3.14+** and **148 bytes on v3.4** (the extra 8 bytes are trailing zero pad).

## Version differences

The config region (`value[0x00:0x24]`) is identical everywhere; only the wrapper changes: v3.14+ uses a
140-byte value and a 24-byte key with the multi-instance marker (0x80000002) and the stream name
**"$I30"**; v3.4 uses a 148-byte value and a 20-byte key with **no marker** and the stream name **"I30"**
(no `$`). So there are two distinct full records but one invariant config payload.

## Cross-references

- [Attributes — Forensic Reference](README.md) — the two-level attribute model
- [Directory Entries](../structures/directory_entries.md) — the directory B+-tree this template configures

## Evidence

Type 0x90 / schema 0x190 and the template layout are confirmed by the `$I30` string literal (E1) and
raw-disk decoded across the corpus (RD), where the config payload is byte-identical on every
directory-bearing object. Findings: **MD_ATTR_010, MD_ATTR_RA_015, FS_SNAP_RA_001** (the `$I30_INDEX` vs `$SI` / `$INDEX_ROOT`
distinction), **MD_ATTR_RA_017**. See [how this was verified](../methodology.md).
