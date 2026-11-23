# Volume Information

The Volume Information table (OIDs 0x500 and 0x501, a failover pair; schema 0x150) stores:

- the volume label;
- the creation and last-mount timestamps;
- version information;
- volume flags.

It is a small B+-tree whose rows are addressed by key type. It is where the volume label that
`fsutil fsinfo volumeinfo` prints comes from (the serial number comes from the [VBR](vbr.md)).

## Identity

| Property | Value |
|----------|-------|
| OIDs | 0x500 and 0x501 (a failover pair: neither copy is a primary) |
| Schema | 0x150, the volume-information table (the schema at its root) |

## Key types

OID 0x500 is a B+-tree with three key types. The key is 8 bytes: type (u16) at offset 0x00, padding at
0x02–0x07.

### Key type 0x0510 — Volume Label

| Field | Description |
|-------|-------------|
| Value | Variable-length UTF-16LE string, no terminator (the value's length is the label's) |

The label is raw UTF-16LE with no length header and no terminator — the first bytes are the first character, and
refs.sys copies the label by the value's length (a value of 64 KiB or more is refused; at most 32 characters reach
the mounted volume's label); no terminator on the three volumes read.

### Key type 0x0520 — Volume Metadata (448 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x80 | 1 | Volume major version (u8) | e.g., 3 |
| 0x81 | 1 | Volume minor version (u8) | e.g., 14 |
| 0x82 | 1 | Driver major version (u8) | The ReFS version the driver of the last writable mount stamps (its own maximum) |
| 0x83 | 1 | Driver minor version (u8) | |
| 0x90 | 8 | Volume creation time (FILETIME) | Set at format time |
| 0xA0 | 8 | Last mount (rw) (FILETIME) | Written by each mount that can write; later writes do not change it |

This row is the volume's own record of when it was formatted and when it was last mounted writable,
independent of any file's timestamps.

refs.sys also writes `+0x84` (`SetVolumeMounted` and `RefsSetClearVolumeFlag`) and reads `+0x98` with `+0x90`
and `+0xA0` (`SetAndGetVolumeTimes`); their meaning is not decoded here, nor is the rest of 0x00–0x7F and
0xA8–0x1BF.

When a newer driver upgrades the volume (at a writable mount), the volume version at `+0x80`/`+0x81` is rewritten
to the new format: 3.14 on the two upgrades measured (from 3.4 and from 3.9). The driver stamp at `+0x82`/`+0x83`
can differ from it (3.15 after an Insider mount).

This key type 0x0520 within OID 0x500 is **unrelated** to standalone OID 0x520 (FS Metadata).

### Key type 0x0540 — the verify block's location (16 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | First cluster (u64) | The verify block's LCN: 0x23 (35) on every corpus volume |
| 0x08 | 8 | Cluster count (u64) | 1 on every corpus volume; the driver accepts 1 to 2^32 - 1 |

At each writable mount the driver writes a copy of the 448-byte key-0x520 blob at that cluster
(`InitializeVerifyBlock`, called by `RefsMountVolume`; 17134, 26100.9444, Insider 29574). On the 124 corpus volumes
cluster 0x23 begins with the blob: equal to the 0x520 row on 89, different only at +0x82 to +0x84 (the driver-version
bytes) on 35, and the rest of the cluster is zero. What reads the block back was not read.

## Failover pair

OID 0x500 and OID 0x501 form a failover pair: `InitializeVolumeInfoTable`, which the mount runs, passes
{0x500, 0x501} to `MsCreateDurableFailoverTableObject`, which looks up both object records. Neither copy is a
primary: which copy the driver reads first has not been read, and on every corpus volume the two copies hold the
same rows.

This is the same durable-failover pattern used by the Upcase Table (0x07/0x08) and the Logfile Info table
(0x09/0x0A). Related driver functions: `RefsGetVolumeInformation` reads the volume information, and
`AllocateAndGetVolumeLabel` reads the volume label (key type 0x0510).

## Forensic notes

- The volume label is preserved across version upgrades.
- refs.sys copies the label by its length without checking its content; only a value of 64 KiB or more is
  refused.
- The driver version fields at +0x82/+0x83 name the driver of the **last writable mount**: refs.sys stores the
  mounting driver's own version there, with no comparison. It can exceed the volume's own format version (3.15
  after an Insider mount of a 3.14 volume; 3.15 is never a format). A later writable mount by an older driver
  replaces an Insider stamp, and a read-only or write-blocked mount leaves the stamp as it was.
- A v3.4 volume carrying driver version 3.14 was last mounted writable by a 26100-era driver.

## Version presence

Present on every format read, 3.4 to 3.14, volumes written by Insider builds included. All three key types are
present in every version tested.

## Cross-references

- [System OIDs](system_oids.md) — OIDs 0x500 and 0x501
- [Schema Table](schema_table.md) — table schema 0x150
- [VBR](vbr.md) — volume serial number (separate from volume label)
- [Object Table](object_table.md) — OID resolution for 0x500/0x501

## Evidence

Identity (OID 0x500/0x501, schema 0x150) and the failover pair are confirmed in the driver:
`InitializeVolumeInfoTable` builds the pair with `MsInitializeWellKnownObjectId(0x500, 0x501)`,
schema 0x150, and `MsCreateDurableFailoverTableObject`. The `$VOLUME_INFORMATION` / `$VOLUME_NAME`
string literals are present in the binary. The three key-type layouts (0x0510 label, 0x0520
metadata/version/timestamps, 0x0540 the verify block's location) and the raw-UTF-16LE no-length-header label
form are decoded from the disk across the corpus, on v3.4 and v3.14 volumes (Insider-written ones included); the
label's lack of a terminator was checked on three volumes. The general-information row's contents are a
registered finding too.

The `+0xA0` writer was measured on one lab volume: it moved at each of five read-write mounts and not at a
read-only mount nor at any later write. The two copies of the pair hold the same rows on the 117 ReFS volumes of
the corpus.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.

<!-- findings: FS_VINF_002, FS_VINF_RA_001 -->
