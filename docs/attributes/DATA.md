# $DATA

`$DATA` is a file's **default data stream** (embedded type 0x80, schema 0x180). It is stored either
**resident** (content inline in the B+-tree row) or **non-resident** (extent references to data
clusters). On disk it appears as embedded sub-records inside the type-0x10 / type-0x30 rows: one
**single-instance (SI)** entry carrying the stream summary and any inline content, plus one or more
**multi-instance (MI)** entries carrying the extent / allocation metadata.

## Resident content — the SI sub-record

The single-instance entry stores the stream-summary header and the inline file content.

**Key (16 bytes):**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Value length (u64) | total value byte count |
| 0x08 | 4 | Marker (u32) | 0x80000001 (single-instance) |
| 0x0C | 2 | Type code (u16) | 0x0080 |
| 0x0E | 2 | Subtype (u16) | 0x000E |

**Value:**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | value length − 12 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | Summary size | 0x30 (48) |
| 0x10 | 8 | Reserved | 0 |
| 0x18 | 8 | Allocated size | stream allocated size (≈ file size, but **not** a fixed 8-byte round-up — e.g. a 129-byte file reads 129, not 136) |
| 0x20 | 8 | File size | exact stream length in bytes |
| 0x28 | 8 | Valid data length | usually equals file size |
| 0x30 | 8 | Total allocated | usually equals allocated size |
| 0x38 | 4 | Stream flags | checksum-type / integrity selector (not a residency flag). Low byte = checksum type: **0x02 = CRC** (CRC32-C / CRC64), **0x04 = SHA-256** (mutually exclusive). Bit **0x10000 = integrity stream enabled** (per-block checksums + CoW), so **0x10002 = CRC + integrity**. 0 on v3.4. Proven by `GetChecksumTypeForStreams` / `SetResidentStreamSummary` |
| 0x3C | var | Inline content | the raw file bytes (file_size long) |

Size relationships: `value_length = 0x3C + allocated_size` (or 0x3C for an empty file); `key[0:8] = value_length`. The minimum value is 60 bytes (0x3C) for an empty file.

## Extent metadata — the MI sub-records

Each file also has one or more multi-instance entries holding the **stream allocation metadata** (not
inline content). The MI key is 40 bytes and carries the extent/allocation identifiers; the MI value does
**not** use the common 12-byte sub-record header.

**Value (extent record, summary size = 0x200):**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Inner header size | 0x88 (136) |
| 0x0C | 4 | Summary size | 0x200 |
| 0x30 | 8 | Total allocated | |
| 0x38 | 8 | Stream size | the stream size in MI records (**not** the stream-flags field) |
| 0x40 | 8 | Valid data length | |
| 0x48 | 8 | Disk allocated | |
| 0x50 | 4 | Version count + sparse flag | low 31 bits = version count (1 for a single-version stream); bit 31 = sparse flag |

The extent sub-record header sits at offset = inner_header_size (0x88): `+0x00` sub_rec_size (0x28),
`+0x0C` flags (0xe00 = non-resident extents), `+0x14` extent_count, then 24-byte extents.

**CoW version namespace** (in the key, not the value): the `sub_id` at key[16:20] selects the version —
**0x8** = stream-set metadata / next-sub-id counter, **0x1000** = the live data version,
**0x1001+** = CoW / snapshot versions.

## Extracting resident content

1. Find the SI `$DATA` sub-record (marker 0x80000001, type 0x80).
2. Read the file size: `le64(value, 0x20)`.
3. Content starts at `value[0x3C]`, length = file_size bytes.

Note: the **`$SI+0x38` DataSize slot in the type-0x10 own-row is unpopulated** — the size lives on the
resident type-0x30 *index entry*, at `value+0x58` (FileSize) and `value+0x60` (AllocatedSize); see the
cross-references.

## Cross-references

- [Directory Entries](../structures/directory_entries.md) — the sub-record chain inside type-0x30 values
- [$NAMED_DATA](NAMED_DATA.md) and [$SNAPSHOT](SNAPSHOT.md) — ADS and snapshots use the same stream-summary format
- [$STANDARD_INFORMATION](STANDARD_INFORMATION.md) — why the own-row `$SI` DataSize slot is unpopulated

## Evidence

Type 0x80 / schema 0x180 and the SI/MI layouts are confirmed in the decompiled driver (E2 —
`RefsCheckValidAttributeAccess`, `GetChecksumTypeForStreams`, `SetResidentStreamSummary`) and raw-disk
decoded across the corpus (RD). Findings: **MD_DATA_RA_008, MD_DATA_RA_009, MD_DATA_RA_010, MD_ATTR_RA_009, MD_SI_RA_016, MD_SI_RA_002** (allocated_size is not a fixed round-up)
(`$SI+0x38` is DataSize). See [how this was verified](../methodology.md).
