# Object Table

The Object Table (roots #0 and #5, schema 0xe030) is the master OID-to-table mapping. Every persistent object -- file, directory, or system table -- has exactly one entry, so it is the pivot of the entire namespace: a file is reachable only through it.

## Key Format -- 16 bytes

The on-disk B+-tree leaf-row key is **16 bytes** (the key type is `SmsBigIdentifier`, the 128-bit identifier):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | (zero padding / high half) | Always `00 00 00 00 00 00 00 00` on the Object Table |
| 0x08 | 8 | Object ID (OID) (u64) | Monotonically increasing, never reused — the low half carries the OID (e.g. key `0000000000000000 0700000000000000` = OID 0x7) |

## Value Format -- Compact (v3.10+)

80 bytes (system objects) / 88 bytes (file objects):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Schema reference (u64) | Value 0x2 for standard objects |
| 0x08 | 16 | Record header | format=2, key_offset=0x18, value_offset=0x30 |
| 0x18 | 4 | Generation counter (u32) | Checkpoint virtual clock at creation/last modification |
| 0x1C | 4 | Dirty generation (u32) | Modification epoch (small integer 1-6) |
| 0x20 | 32 | 4 x u64 LCN slots | Page references for object's own B+-tree root (see [Container Table](container_table.md) for the virtual-to-physical LCN translation) |
| 0x40 | 8 | (unconfirmed) | u64 — the on-disk values are large and structured rather than a small bitfield; the exact role is not established. |
| 0x48 | 8 | (per-object identifier — unconfirmed) | u64 — values are mostly distinct across rows, consistent with a per-object id; the exact role is not established. |

## Value Format -- Legacy (pre-v3.10)

A legacy Object-Table row value has three distinct sizes:

1. **B+-tree `value_length`** — the full value-buffer size: **240 bytes** for objects with no 8-byte trailing field (upcase `0x7/0x8`, logfile `0x9/0xa`, trash `0xd`, volume-info `0x500/0x501`, security `0x530`, reparse `0x540/0x541`) and **248 bytes** for the root directory `0x600`, `0x520`, and every file / directory (which carry an 8-byte trailing field).
2. **`value+0x10`** — a payload **offset**, constant for every legacy object: **200 (0xC8)**. **`value+0x14`** — the trailing-payload length, **0 or 8**. Their sum (**200 / 208**) is the driver's copyable payload extent.
3. The driver reads exactly those two fields: `CmsObjectTable::GetObjectRecordPayload` (win11 `@140118c14`) computes `src = value + u32@0x10` and copies `u32@0x14` bytes.

On **compact (v3.10+)** volumes the value shrinks and `value_length` tracks the **checksum** size (independent of cluster size): **80 / 88 bytes** by default, **104 / 112 bytes** under SHA-256. Here `value+0x10` = 80 / 104 flat, so it equals `value_length` only for the no-trailer (system) objects, not for files.

A forensic parser keyed on the B+-tree `value_length` should expect **240 / 248** (legacy), **80 / 88** (compact), or **104 / 112** (compact SHA-256).

**Important**: Upgraded volumes show mixed format. Pre-existing objects retain legacy size; objects created after upgrade use compact size. A forensic parser must handle both sizes within the same Object Table.

## OID Allocation

- 64-bit, monotonically increasing, never reused after deletion
- Counter maintained at `CmsObjectTable+0x18`; atomically incremented (`LOCK` prefix)
- On mount, derived from the rightmost (largest) Object-Table B+-tree key. Win11/Insider use the `_CmsKey::RightMost` sentinel with `CmsTable::FindRow` (present in the decompiled win11 driver, 12 occurrences; Insider 11); the Win10 (v3.4) driver has no such symbol and uses `PinInIndexRightMost` / `MsFindRightmostNodeAvlFull` instead
- **System OIDs**: below 0x700 (except 0x600 which is the root directory)
- **User OIDs**: start at 0x701 (hardcoded via `MsSetMinimumNewObjectId`)
- `RefsIsSystemObjectId` returns true when `OID <= 0x6FF AND OID != 0x600`

See [System OIDs](system_oids.md) for the 13 known system OIDs and their roles.

## Forensic Properties

- **Lower OID = earlier creation** -- reliable chronological indicator
- **Gaps in sequence** = evidence of past deletions
- **Volume activity estimation**: `max_OID - 0x700` = upper bound on total files ever created
- **OID density**: `present_OIDs / (max_OID - min_OID + 1)` -- fresh volumes are 100%; worked volumes show 55-79%

### NTFS vs ReFS Chronology Comparison

| Property | NTFS MFT Record | ReFS OID |
|----------|----------------|----------|
| Size | 48-bit | 64-bit |
| Sequential | Yes | Yes |
| Reused after deletion | Yes | **No** |
| Chronology reliability | Partial (reuse obscures) | **Strong** (no reuse) |
| Scope | Per-MFT | Per-volume |

## Failover

The Object Table has a failover pair: root #0 (table ID 0x02) and root #5 (table ID 0x04). If one copy is corrupted, the driver falls back to the duplicate.

## Driver functions

| Function | Purpose |
|----------|---------|
| `RefsIsSystemObjectId` | Returns true for `OID <= 0x6FF && OID != 0x600`. Guards system object access. |
| `MsSetMinimumNewObjectId` | Sets the floor at 0x701 for user object allocation. |
| `RefsAllocateObjectId` | Atomically increments the OID counter at `CmsObjectTable+0x18`. |
| `RefsGetNextFileIdFromObjectTable` | Reads the current max OID from the rightmost B+-tree key. |
| `UpdateObjectTableWorker` | Persists Object Table modifications during transaction commit. |

## Cross-references

- [Checkpoint (CHKP)](chkp.md) -- roots #0 and #5 point to the Object Table
- [Schema Table](schema_table.md) -- schema 0xe030 defines key comparison for this table
- [Parent-Child Table](parent_child_table.md) -- encodes directory hierarchy relationships
- [System OIDs](system_oids.md) -- the 13 known system OIDs and their roles
- [Container Table](container_table.md) -- needed to translate virtual LCNs in the LCN slots

## Evidence

The key/value layout, the compact-versus-legacy formats, and the failover pair are decompiled from the driver (E2) and decoded on raw disk across the corpus (RD). The record-header decode (`format=2`, key/value offsets, generation and dirty-generation counters) and the four-slot LCN tuple are read by `CmsObjectTable::GetObjectRecordOfIdentifier` / `MsGetObjectRecordPayload`. The OID-allocation behaviour (monotonic, never-reused, 0x701 user floor, 0x600 root exception) is proven both statically — `CmsObjectTable::GenerateIdentifier` (atomic increment), `DeleteIdentifier` (never decrements), `MsSetMinimumNewObjectId`, `RefsIsSystemObjectId` — and on disk via the observed no-reuse / gaps-equal-deletions behaviour. The 0x40 and 0x48 value fields are inferred only (no E2): 0x40 is an unconfirmed structured u64 and 0x48 is a probable per-object identifier; neither role is established. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
