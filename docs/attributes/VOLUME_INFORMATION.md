# $VOLUME_INFORMATION

`$VOLUME_INFORMATION` (schema 0x150, embedded type 0x50) is the **volume-level metadata** — version,
flags, label, and timestamps. Despite being registered as an attribute schema, it does **not** appear as
an embedded sub-record in user objects: the volume metadata lives in the system table at **OID 0x500**
(with a byte-identical durable failover mirror at **OID 0x501**), as a multi-row B+-tree keyed by
system-specific key types.

## Value layout

OID 0x500 holds three rows:

| Key | Content |
|-----|---------|
| 0x510 | the volume **label** (UTF-16LE, variable length) |
| 0x520 | a 448-byte (0x1C0) `_REFS_VOLUME_INFO` metadata blob (below) |
| 0x540 | 16 bytes — schema count (u32) at +0x00, flags (u32) at +0x04, a u32 (=1, purpose unknown) at +0x08 |

The key-0x520 blob's only populated regions are +0x80 (versions + flags), +0x90 (creation) and +0xA0
(mount); everything else is zero. **No volume GUID is stored here** — the volume serial lives in the VBR
(VBR+0x38).

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x80 | 1 | Volume major version | echoes VBR+0x28; changes only on a real format upgrade |
| 0x81 | 1 | Volume minor version | echoes VBR+0x28 |
| 0x82 | 1 | Driver major version | stamped per-mount by `SetVolumeMounted` |
| 0x83 | 1 | Driver minor version | stamped per-mount with the driver's constant (0x403 = v3.4, 0xe03 = v3.14, 0xf03 = Insider) — the *highest driver version that ever mounted the volume* |
| 0x84 | 4 | Volume flags | `_REFS_VOLUME_FLAGS` (read by `RefsGetVolumeInformation`): **0x180** on pre-v3.10 formats (a marker that **persists across an upgrade** — an upgraded v3.4→v3.14 volume still shows 0x180); **0x000** on native v3.10+; **0x200** = heat-gathering disabled |
| 0x90 | 8 | Creation timestamp | FILETIME; set at format, never rewritten |
| 0x98 | 8 | Secondary FILETIME slot | propagated to VCB+0x208/0x210; 0 on sampled volumes |
| 0xA0 | 8 | Mount / modify timestamp | FILETIME; rewritten on each writable mount |

## Version stamping — a forensic discriminator

The **volume** version (+0x80/+0x81) and the **driver** version (+0x82/+0x83) are independent: the
volume version advances only on a real format upgrade, while the driver stamp records the *highest
driver build that ever mounted the volume*. This gives a third independent upgrade discriminator
(alongside the CHKP 0x080 flag): a **native-formatted v3.10+ volume shows volume-flags 0x000, while a
volume upgraded from v3.4 still shows 0x180**. A `0xf03` (Insider) driver stamp appears only when an
Insider build has mounted the volume, not on a generic upgrade.

## Cross-references

- [System OIDs](../structures/system_oids.md) — OID 0x500 / 0x501 volume metadata
- [Volume Information](../structures/volume_info.md) — the system-table layout
- [Version Detection](../concepts/version_detection.md) — using these fields to classify a volume

## Evidence

Schema 0x150 / type 0x50, the OID 0x500/0x501 storage, and the blob layout are confirmed in the
decompiled driver (E2 — `RefsGetVolumeInformation`, `SetVolumeMounted`) and on the raw-disk corpus (RD).
Finding: **FS_VOLI_RA_001** (the version-stamp semantics). See [how this was verified](../methodology.md).
