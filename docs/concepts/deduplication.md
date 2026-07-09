# Deduplication

Deduplication is the one ReFS feature that deliberately stores file content with **no live file pointing
at it**. It is an opt-in, post-process feature (`Enable-DedupVolume`) that lets a single physical block
back many logical files: identical chunks are written once into a chunk store and every file that needed
those bytes is left holding a reference instead of a copy. For an analyst, the consequence is direct — a
file-walk-only tool will never see the deduplicated payload, because the bytes live behind a reference
count rather than a directory entry. The authoritative map of that sharing is the
[Block Refcount Table](../structures/block_refcount.md): it records which clusters are shared, by how
many references, and which are dedup-managed store blocks with zero live references.

## One refcount table, three sharing mechanisms

Deduplication does not have its own bookkeeping. It reuses the same **per-cluster reference-counting**
machinery that already backs [snapshots](snapshots_versioning.md) and clones — the
[Block Refcount Table](../structures/block_refcount.md) holds one `u16` refcount entry per cluster, and
deduplication simply drives those counts up the same way a hard link or a clone would. This is why the
table is the single place to reason about *all* block sharing on the volume: a high refcount could be a
snapshot, a clone, a hard link, or dedup, and the entry's flag bits are what tell them apart.

The table is **root #6, schema `0xe0b0`**. Both the root and the schema have existed since **v3.4** as an
empty B+-tree, but the table is only *populated* on a v3.14 volume that has had sharing activity. On a
volume that never enabled dedup, snapshots, or hard links, root #6 is present but empty — its presence is
not by itself a dedup signal.

Each tracked range is keyed by `Start LCN` (u64 @0x00) and `Cluster count` (u64 @0x08), and the cluster
count is **0x400 (1,024 clusters)** — one `u16` array entry per cluster. The row's value carries a
redundant copy of the start LCN and cluster count, an 8-byte modification stamp @0x10, a **`TotalRefCount`
u32 @0x18** (the sum of all live counts in the row, with the high 16 bits always zero), then the
**`u16[1024]` per-cluster refcount array @0x1C..0x81B**, and four trailing bytes that round the value to
**0x820 (2,080 bytes)**. The byte-level layout, including how this row differs from the similarly-sized
allocator bitmap row, is on the [Block Refcount Table](../structures/block_refcount.md) page.

## Reading a refcount entry

Every `u16` array entry packs a reference count into the low 14 bits and two flag bits on top:

```
 bit 15   bit 14            bits 13..0
+--------+----------------+-------------------------+
| dedup- | dedup-metadata | reference count         |
| managed| (rc=0 only)    | (mask 0x3FFF)           |
+--------+----------------+-------------------------+
 0x8000   0x4000            0x3FFF
```

- **bits 13:0 (`0x3FFF`)** — the reference count, observed up to 758 in dedup scenarios.
- **bit 14 (`0x4000`)** — dedup *metadata* flag; marks dedup management clusters, and is only ever set on
  entries whose count is zero.
- **bit 15 (`0x8000`)** — dedup-*managed* / shared; marks clusters managed by the Data Deduplication
  engine.

The same entry therefore reads three different ways depending on the bits, and distinguishing them is the
whole forensic point of the table:

| Pattern | Meaning |
|---------|---------|
| `rc >= 2`, bit 15 clear | Normal multi-reference (hard links, clones) |
| `rc >= 2`, prior checkpoint still references | [Copy-on-write](copy_on_write.md) orphan |
| bit 15 set, `rc = 0` | **Dedup store block** — data present, no live file reference |

As a worked example, the entry value `0x81F9` decodes to a reference count of 505 with the shared bit set
— a single cluster referenced by 505 files. The driver maintains these counts through
`CmsBlockRefcount::IncrementRefcount` and `CmsBlockRefcount::DecrementRefcount` (the v3.4 symbol;
v3.14 reaches the same logic through `IncrementRefcount` with a signed delta), and the tracking table is
built by `CmsBlockRefcount::Initialize`. When a block's last live reference is removed, the v3.14 redo
path runs `CmsBlockRefcount::BreakWeakReferences` (redo opcode `0x28`), confirming that the refcount table
participates in transactional weak-reference teardown rather than being touched out-of-band.

## Why this matters for recovery

The table changes what "recoverable content" means on a ReFS volume:

- **Dedup store blocks are content no file points at.** Any array entry with **bit 15 (`0x8000`) set and
  `rc = 0`** is a dedup-store block: the chunk store holds the data, but no directory entry currently
  references it. These blocks are the deduplicated payload — recoverable bytes that a file-walk-only tool
  will miss entirely, because there is no live extent to follow to them.
- **One physical block can satisfy many paths.** A high reference count means one block underlies many
  logical files. When you carve or recover from such a block, expect the same bytes to legitimately
  satisfy multiple paths; the count tells you how many references the allocator believes exist before it
  will free the block.
- **Reference counts protect deleted content.** A block with `rc >= 2` will not be reclaimed until the
  count reaches zero, regardless of any single file being deleted. This is central to judging whether a
  deleted file's content still exists — see [what survives](what_survives.md) for how this folds into the
  broader survival reasoning.
- **A populated table is an investigative fact in itself.** A populated root #6 together with the dedup
  [checkpoint](../structures/chkp.md) flag bits indicates the volume had dedup enabled — that is, the user
  ran `Enable-DedupVolume`.

## Version and volume-state differences

- **v3.4–v3.10:** schema `0xe0b0` and root #6 exist but the tree is empty — no deduplication activity.
  The schema is listed as present from v3.4 through Insider.
- **v3.14 (native, dedup):** the table is populated, and the volume state advances to `0x07b2` — the
  native-v3.14 base `0x682` plus the `0x130` dedup/compression flag bits. The same dedup state is visible
  in the [checkpoint](../structures/chkp.md) volume-state flags (`0x010 / 0x020 / 0x100` co-set), which is
  how a parser can detect "dedup was enabled" without walking the table.
- The redo log gains a refcount-management opcode at v3.14: `0x28` = `CmsBlockRefcount::BreakWeakReferences`,
  the transactional teardown of a block's last weak reference.

## Finding the table with forefst

There is no dedicated `dedup` subcommand; the table is reached structurally. Enumerate the root-pointer
list and locate **root #6 / schema `0xe0b0`** (`refsanalysis.py` labels root 6 — table ID 0x05 — as the
Block RefCount Table). Within each row's 2,080-byte value, parse the `u16[1024]` array at `0x1C..0x81B`
(the `TotalRefCount` u32 precedes it at 0x18) and decode every entry with the masks above: `& 0x3FFF` is
the count, `& 0x4000` is the metadata flag, `& 0x8000` is the managed flag. Whether dedup was *enabled*
is also readable directly from the checkpoint volume-state flags surfaced by the `integrity` / `version`
output (composite `0x07b2`, flag bits `0x010 / 0x020 / 0x100`), without parsing the table at all.

## Cross-references

- [Block Refcount Table](../structures/block_refcount.md) — the byte-level layout this page reads from:
  the key, the 2,080-byte value, and the Subtable B.6a entry bit fields
- [Stream Snapshots and File Versioning](snapshots_versioning.md) — the `rc >= 2` sharing this same table
  also tracks, and the strongest single-image content-recovery path
- [Copy-on-Write](copy_on_write.md) — CoW orphans (`rc >= 2`, with a prior checkpoint still referencing
  the clusters) share this refcount machinery
- [Compression](compression.md) — the paired 24H2 feature enabled alongside dedup (`DedupAndCompress`),
  tracked separately and per-container rather than per-cluster
- [What survives](what_survives.md) — how refcount-protected blocks feed deleted-content survival
  reasoning
- [Checkpoint](../structures/chkp.md) — where the dedup volume-state flag bits (`0x010 / 0x020 / 0x100`,
  composite `0x07b2`) live

## Evidence

The tracking table and its management functions are confirmed in the driver (E2): it is built by
`CmsBlockRefcount::Initialize` (the PDB symbol for schema `0xe0b0`), the counts are mutated by
`CmsBlockRefcount::IncrementRefcount` / `CmsBlockRefcount::DecrementRefcount`, and the v3.14 redo path
adds `CmsBlockRefcount::BreakWeakReferences` (redo opcode `0x28`). The 16-byte key, the 2,080-byte
(`0x820`) value, the `TotalRefCount = Σ(entry & 0x3FFF)` invariant at value+0x18, the `u16[1024]` array at
0x1C..0x81B, and the Subtable B.6a bit fields (count `0x3FFF`, metadata `0x4000`, managed `0x8000`) are
raw-disk decoded (RD). The dedup-enabled checkpoint flag bits (`0x010 / 0x020 / 0x100`, composite
`0x07b2`) are likewise raw-disk confirmed. See [how this was verified](../methodology.md) to trace these
to the exact images and measurements in `analysis/`. Findings: **FS_CHKP_015, CT_BKRC_001** (schema `0xe0b0` = Block Refcount
Table), **CT_BKRC_001, FS_CHKP_015** (block-level dedup sharing in root #6), **FS_CHKP_RA_001** (dedup checkpoint flags),
**FS_CHKP_RA_001** (volume-state flags including `0x07b2`).
