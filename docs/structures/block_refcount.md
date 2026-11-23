# Block Refcount Table

The Block Refcount Table (root #6, table ID 0x05, schema 0xe0b0) counts, per data cluster, the references beyond
the first:

- block clones and deduplication add them;
- a hard link or a snapshot adds none.

The schema and root #6 exist from v3.4. Rows have been found only on v3.14 volumes, and not on every one: some v3.14
volumes hold an empty table, and what writes a volume's first rows is not established.

The v3.4 driver can write the table too (its block-clone path raises the counts), so an empty table on an older
volume is an observation, not a rule.

## Key — 16 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Start VLCN (u64) | First cluster of the tracked range, a virtual cluster number |
| 0x08 | 8 | Cluster count (u64) | Range length in clusters: **0x400 = 1,024** on every long-form row (one array entry per cluster); a compact row covers 1,024 to 4,096 on the corpus |

## Value — 2,080 bytes (0x820, normal)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Start LCN (u64) | Redundant copy of key |
| 0x08 | 8 | Cluster count (u64) | Redundant copy of key (**0x400 = 1,024**) |
| 0x10 | 4 | Not decoded (u32) | Its first byte is **1** on every row, as the driver requires; the other three bytes vary |
| 0x14 | 4 | Form (u32) | **1** = the long form; **0** = the compact form (both below) |
| 0x18 | 4 | **TotalRefCount (u32)** | The sum of the per-cluster counts; upper 16 bits 0 on every row measured |
| 0x1C | 2,048 | Per-cluster refcount array (u16[1024]) | Spans **0x1C..0x81B**; one entry per cluster ([bit fields](#per-cluster-refcount-entry-bit-fields-u16-one-entry-per-cluster)) |
| 0x81C | 4 | Unknown (4 bytes) | Not padding: zero on most rows, structured content on the rest (below) |

One array entry covers one cluster of the volume's cluster size (4 KiB or 64 KiB): populated tables were measured on
both.

The 4 bytes at `+0x81C` are zero on most long rows and non-zero on 224 of the corpus's 2,724, on nine format 3.14
volumes, in 20 distinct values whose high half is `0xFFFF` on every one. Their meaning is undetermined.

**TotalRefCount.** The header's `TotalRefCount@0x18` equals the sum of the counts (`entry & 0x1FFF`) across the whole
array on every long row of the corpus; bit 13 is clear on every entry measured.

**Two value forms.** The table above is the **long** form: a 28-byte header (0x00..0x1B, including
`TotalRefCount@0x18`), the **u16[1024] array @ 0x1C..0x81B** and a 4-byte trailing field @ 0x81C, 2,080 bytes when
`BlockCount` is `0x400`.

A **32-byte compact** form also exists: the same 28-byte header followed by 4 bytes, with no per-cluster array
(28 + 4 = 32).

- The driver reads it as one count for the whole range: when bit 0 of the u32 at `+0x14` is clear, it applies the u16
  at `+0x1C` to every cluster of the range (one reading of the driver).
- On the corpus 28 rows are compact, on three volumes, against 2,724 long ones; the u32 at `+0x14` is 0 on every
  compact row and 1 on every long one.
- The two compact rows read on `winsider` carry a well-formed header (the key's `StartLCN`/`BlockCount` mirrored
  into the value at `+0x00`/`+0x08`); each of the 28 carries a count of 1 or 2 at `+0x1C`; its `TotalRefCount` is 0, and the u16 at `+0x1E` equals the count
  on 26 of the 28 (not decoded). So the form is a second encoding, not damage.

Do not confuse this table with the [allocator bitmap row](allocators.md), which is a *different* structure with a
different value length.

## Per-cluster refcount entry bit fields (u16; one entry per cluster)

| Bits | Mask | Field | Notes |
|------|------|-------|-------|
| 12:0 | 0x1FFF | Reference count | The references to this cluster beyond the first (`CmsRefcountCacheEntry::Update` reads `entry & 0x1FFF`) |
| 13 | 0x2000 | — | not read |
| 14 | 0x4000 | Weak reference broken | the weak reference of bit 15 broken by a later write or checksum rewrite (`BreakWeakReferences`, redo opcode 0x28; one reading) |
| 15 | 0x8000 | Weak reference | an LCN weak reference the deduplication path sets on clusters the stream itself maps (`CreateRangeWeakReferences`; one reading) |

### Interpreting an entry

- **Shared**: a count of 1 or more — the driver's sharing test (`IsRangeSharedOrCompacted`). On the populated sample
  volume measured, block-clone pairs read 1 and triples 2 (almost every cluster measured).
- **Not counted**: a hard link adds nothing (the hard-linked file reads 0 on every one of its clusters), and a cluster
  shared with a snapshot reads 0 — neither shows in this table.
  - `IncrementRefcount`'s five callers are the block clone, the deduplication redirect, two flagged-extent paths and
    the stream-run updates.
  - Neither `RefsLinkFileToSelf` nor the snapshot path calls it.
- **Weak reference, count 0**: bit 15 set, count 0 — a cluster the deduplication path marked on a stream that maps it.
- **Example**: entry value 0x81F9 = count 505 with bit 15 set — one 4 KiB cluster with 505 references beyond the first.

Bits 15 and 14 appear only on dedup-enabled volumes, and never together: over the corpus's 2,752 rows, bit 15 is set
on 62,233 entries and bit 14 on 181, all on the three volumes whose checkpoint carries the dedup flag (0x010). Their
names above come from one reading of the driver.

There the flagged entries were `0x4000` (a broken weak reference, count 0), `0x8000` (a weak reference, count 0) and
`0x8000 | count`.

## Population by version

| Version | State | Notes |
|---------|-------|-------|
| v3.4–v3.10 | No rows found | Root #6 exists; the v3.4 driver's block-clone path can write rows, so the empty table is an observation |
| v3.14 (no dedup) | Populated on some volumes, empty on others | Block clones raise the counts; hard links and snapshots add none |
| v3.14 (dedup) | Populated with flag bits | The deduplication path uses bits 14 and 15 |

## Implementation notes

- The Win11 driver uses a cache-based model (`LookupCacheEntry` / `PersistCacheEntry` /
  `PopulateCacheEntry`), replacing the Win10 driver's direct B+-tree manipulation (`InsertEntry` / `DeleteEntry` /
  `UpdateEntry`).
- The counts change through `AdjustRefcount`, which takes a direction:
  - on 26100.8115 `IncrementRefcount` calls it to raise a count, and there is no `DecrementRefcount`; the delete
    queue (`ProcessDeleteQueueEntry`) updates the cached entries, and the undo path calls `AdjustRefcount` with the
    opposite direction;
  - the Win10 v3.4 driver (17134) also carries a `DecrementRefcount`. 26100.9444 and Insider 29574 have
    `AdjustRefcount` and no `DecrementRefcount`, as 26100.8115.
- The root page's index-root descriptor carries schema 0xe0b0, like every table root.
- Root #6 has no failover pair — it is the sole copy.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — carries this table's root pointer, at index #6 in the root-pointer list
- [Schema Table](schema_table.md) — schema 0xe0b0
- [Container Table](container_table.md) — the Start VLCN values are virtual: translate them through it before reading
  the disk
- [Copy-on-Write](../concepts/copy_on_write.md) — sharing between versions, which this table does not count

## Evidence

Identity (root #6 / table ID 0x05 / schema 0xe0b0 / virtual addressing / no failover pair) is confirmed in the
driver: the `CmsBlockRefcount` class implements the table, and root #6 carries table ID 0x05 on valid MSB+ pages.

The long-form key/value layout and the `TotalRefCount@0x18 == Σ(entry & 0x1FFF)` invariant are decoded from the disk
over the populated v3.14 volumes. The compact form's meaning and the meanings of bits 13-15 come from the driver.

The driver's `CmsBlockRefcount::PopulateCacheEntry` (26100.8115) reads the range, the total at `+0x18` and the array
at `+0x1C`. It also requires the value's `+0x10` byte to be 1 and takes bit 0 of the u32 at `+0x14` as the long /
compact switch; on the corpus the byte is 1 on every row, and the u32 at `+0x14` is 1 or 0 with the form. What the
other three bytes at `+0x10` hold is not decoded.

The count's meaning (references beyond the first; none for a hard link or a snapshot) is measured on one populated
volume and read in the driver (26100.8115, and the `0x1FFF` mask again on 26100.9444); the bits 14 / 15 meanings are
one reading.

The counts behind the text:

- over the 124 ReFS volumes of the corpus, the table has rows on 47 (all format 3.14): 2,752 rows, 2,724 long and 28
  compact (`winsider` 2, `winsiderv2` 25, `win11refs4gattributestest2` 1); the byte at `+0x10` is 1 on all 2,752;
- on the long rows the sum check holds on 2,724 of 2,724, the largest total 1,408, with 16 distinct non-zero entry
  values (the largest 0x82F6, count 758); the trailer at `+0x81C` is non-zero on 224 rows on 9 volumes, in 20 values;
- the compact rows cover 1,024 to 4,096 clusters and carry a count of 1 or 2;
- on the populated sample volume, block-clone pairs read 1 and triples 2 on 2,239 of 2,257 clusters, and the
  hard-linked file reads 0 on 24 of 24 clusters;
- populated tables were read on 4 KiB volumes and on a 64 KiB volume (two long-form rows).

See [how this was verified](../methodology.md) for the method.

<!-- findings: CT_BKRC_001, CT_BKRC_RA_001, CT_BKRC_RA_002, CT_BKRC_RA_003, GN_DEDUP_SA_001 -->
