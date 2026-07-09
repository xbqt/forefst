# Volume Information

The Volume Information table (OID 0x500 primary, OID 0x501 duplicate, schema 0x150) stores the volume
label, creation and modify timestamps, version information, and volume flags. It is a small B+-tree
whose rows are addressed by key type, and it is the canonical on-disk source for the data that
`fsutil fsinfo volumeinfo` surfaces through the Windows API.

## Identity

| Property | Value |
|----------|-------|
| Primary OID | 0x500 |
| Duplicate OID | 0x501 |
| Schema | 0x150 (attribute schema for $VOLUME_INFORMATION) |
| Embedded type code | 0x50 |

Schema ID 0x150 maps to embedded type code 0x50 via the standard naming rule (schema = type + 0x100).

## Key types

OID 0x500 is a B+-tree with three key types. The key is 8 bytes: type (u16) at offset 0x00, padding at
0x02–0x07.

### Key type 0x0510 — Volume Label

| Field | Description |
|-------|-------------|
| Value | Variable-length UTF-16LE string, null-terminated |

The label is raw UTF-16LE with no length header — the first bytes are the first character, and the
string is null-terminated.

### Key type 0x0520 — Volume Metadata (448 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x80 | 1 | Volume major version (u8) | e.g., 3 |
| 0x81 | 1 | Volume minor version (u8) | e.g., 14 |
| 0x82 | 1 | Driver major version (u8) | ReFS major version of the driver that last wrote the volume metadata (its max-supported version) |
| 0x83 | 1 | Driver minor version (u8) | |
| 0x90 | 8 | Volume creation time (FILETIME) | Set at format time |
| 0xA0 | 8 | Volume modify time (FILETIME) | Updated on mount |

Bytes 0x00–0x7F and 0xA8–0x1BF are not yet decoded. The version fields at +0x80 are updated during
upgrade: a v3.4 volume mounted under a newer driver has its volume minor version rewritten to match.

This key type 0x0520 within OID 0x500 is **unrelated** to standalone OID 0x520 (FS Metadata).

### Key type 0x0540 — Schema Count and Flags (16 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Schema count (u32) | Typically 35 |
| 0x04 | 4 | Volume flags (u32) | Purpose not fully decoded |

The schema count is constant across versions and does not track the number of schemas the
[Schema Table](schema_table.md) actually contains.

## Failover pair

OID 0x500 (primary) and OID 0x501 (duplicate) form a failover pair, created together at format time by
`InitializeVolumeInfoTable` via `MsCreateDurableFailoverTableObject`. This is the same durable-failover
pattern used by the Upcase Table (0x07/0x08) and the Logfile Info table (0x09/0x0A). Related driver
functions: `RefsGetVolumeInformation` reads the volume information, and `AllocateAndGetVolumeLabel`
reads the volume label (key type 0x0510).

## Forensic notes

- The volume label is preserved across version upgrades.
- The volume label is not validated during mount — arbitrary values are accepted.
- The driver version fields at +0x82/+0x83 record the ReFS version of the driver that last wrote the
  volume metadata — its maximum supported version, which can exceed the volume's own format version
  (e.g. 3.15 after an Insider mount of a 3.14 volume; never observed below the volume version across the
  corpus). A v3.4 volume carrying driver version 3.14 was opened under a newer Windows build at some
  point.

## Version presence

Present on all versions from v3.4 through Insider. All three key types are present in every version
tested.

## Cross-references

- [System OIDs](system_oids.md) — OIDs 0x500 and 0x501
- [Schema Table](schema_table.md) — attribute schema 0x150
- [VBR](vbr.md) — volume serial number (separate from volume label)
- [Object Table](object_table.md) — OID resolution for 0x500/0x501

## Evidence

Identity (OID 0x500/0x501, schema 0x150) and the failover-pair creation are confirmed in the driver
(E2): `InitializeVolumeInfoTable` builds the pair with `MsInitializeWellKnownObjectId(0x500, 0x501)`,
schema 0x150, and `MsCreateDurableFailoverTableObject`. The `$VOLUME_INFORMATION` / `$VOLUME_NAME`
string literals are present in the binary (E1). The three key-type layouts (0x0510 label, 0x0520
metadata/version/timestamps, 0x0540 schema count + flags) and the raw-UTF-16LE no-length-header label
form are raw-disk decoded across the corpus (RD), present on v3.4, v3.14, and Insider. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
