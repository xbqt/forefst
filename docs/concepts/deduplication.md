# Deduplication

ReFS deduplication lets several files share the same physical clusters. It is an opt-in, post-process feature: a
volume is enabled with `Enable-ReFSDedup` (for example `-Type DedupAndCompress`), and a dedup job (for example
`Start-ReFSDedupJob`) then does the work.

The dedup path points a file's run at an identical cluster that already exists and raises that cluster's count. The
shared content stays reachable through each file's extents, so a file walk that follows extents reads it; what the
walk does not show is that the clusters are shared.

The driver records that sharing in the [Block Refcount Table](../structures/block_refcount.md): a count per cluster
of the references beyond the first, and two weak-reference bits that the dedup path uses.

## One refcount table, two counting paths

Deduplication keeps no table of its own in the file system's metadata: apart from a volume-level state (the
checkpoint flag `0x010`, below) and the dedup service's own index file (below), it uses the same **per-cluster
reference counts** as block clones.

For each range it tracks, the [Block Refcount Table](../structures/block_refcount.md) holds one `u16` entry per
cluster (in its long form), and a clone or the deduplication path raises a cluster's count of references beyond the
first.

A [snapshot](snapshots_versioning.md) or a hard link adds no count (a hard-linked file's clusters and a snapshot's
shared clusters read 0), so the table is the place to reason about clone and deduplication sharing, not about every
kind of sharing on the volume. The entry's flag bits mark the weak references the deduplication path sets.

The table is **root #6, schema `0xe0b0`**. Both the root and the schema exist from **v3.4** on. Rows appear on some
v3.14 volumes, including a volume with block clones and no dedup, while other v3.14 volumes hold none; what writes the
first rows is not established. A populated table is not by itself a dedup signal.

**Files that share clusters are still separate files.** Deduplication (and block-cloning) make several *distinct*
files — each with its own [FileRef](file_ids.md) `(HomeOID, ordinal)` and its own directory entry — point
at the same physical clusters. A [hard link](hard_links.md) is the opposite: several *names* of **one**
object, all sharing a single FileRef. So two directory entries that share a FileRef are hard-link names of
one file, **never** a dedup pair, and two deduplicated files **never** share a FileRef.

The refcount table sees only the block-level effect: a count does not say which mechanism raised it. The files'
identities are what separate a hard link from files that share content. (This distinction is why a rare pair of files
that appear to share a `(HomeOID, ordinal)` is a hard link, not evidence that dedup ran.)

Each tracked range is keyed by `Start VLCN` (u64 @0x00, a virtual cluster number) and `Cluster count` (u64 @0x08).
The cluster count is **0x400 (1,024 clusters)** on every long-form row measured — one `u16` array entry per cluster —
and a compact row can carry `0x800`.

The row's value comes in two forms:

- **The long form** carries a redundant copy of the start VLCN and cluster count, a byte @0x10 (1 on every row), three
  bytes @0x11 not decoded, a u32 @0x14 (1 in the long form, 0 in the compact one), a **`TotalRefCount` u32 @0x18** (the sum of all live counts in the row, with the high 16 bits zero on
  every row measured), then the **`u16[1024]` per-cluster refcount array @0x1C..0x81B**, and a 4-byte field @0x81C that ends the value
  at **0x820 (2,080 bytes)**.
- **A 32-byte compact form** holds the same header and trailer with the array omitted. The driver then reads one `u16`
  at `+0x1C` for the whole range (one driver reading); what the form means on disk is not established.

The byte-level layout, including how this row differs from the similarly-sized allocator bitmap row, is on the
[Block Refcount Table](../structures/block_refcount.md) page.

## Reading a refcount entry

Every `u16` array entry packs a reference count into the low 13 bits and two flag bits on top (the driver's
`CmsRefcountCacheEntry::Update` reads the count as `entry & 0x1FFF`):

```text
 bit 15      bit 14             bit 13   bits 12..0
+-----------+------------------+--------+------------------------------+
| weak      | weak reference   | (not   | references beyond the first  |
| reference | broken           |  read) | (mask 0x1FFF)                |
+-----------+------------------+--------+------------------------------+
 0x8000      0x4000             0x2000   0x1FFF
```

- **bits 12:0 (`0x1FFF`)** — the count of references beyond the first, observed up to 758 in dedup scenarios; a
  count of 1 or more is the driver's sharing test (`IsRangeSharedOrCompacted`). Block-clone pairs read 1 and
  triples 2.
- **bit 14 (`0x4000`)** — the weak reference of bit 15 broken by a later write or checksum rewrite
  (`BreakWeakReferences`, redo opcode `0x28`); on the corpus only ever set on entries whose count is zero.
- **bit 15 (`0x8000`)** — an LCN weak reference the deduplication path sets on clusters the stream itself maps
  (`CreateRangeWeakReferences`).

The two flag meanings are one reading of the driver. Where they appear is measured: over the 2,752 Block Refcount rows
of the 47 corpus volumes that have any, bit 15 is set on 62,233 entries and bit 14 on 181, all on the three volumes
whose checkpoint carries the dedup flag (0x010), never both on one entry; every bit-14 entry has a count of 0, and the
largest count is 758.

| Pattern | Meaning |
|---------|---------|
| count ≥ 1, bit 15 clear | the cluster has that many references beyond the first — block clones or deduplicated files |
| bit 15 set, count 0 | a weak reference the deduplication path set on a cluster a stream maps |
| bit 14 set, count 0 | that weak reference, broken |

As a worked example, the entry value `0x81F9` decodes to a count of 505 with bit 15 set — one cluster with 505
references beyond the first.

`IncrementRefcount`'s callers are the block clone, the deduplication redirect, two flagged-extent paths and the
stream-run updates (26100.8115), and neither `RefsLinkFileToSelf` (hard links) nor the snapshot path calls it. The
v3.4 driver also carries a paired `DecrementRefcount`; 26100.8115 has none: `IncrementRefcount` and the undo path both
call the private `AdjustRefcount`, which takes an unsigned count and a direction byte.

The table is built by `CmsBlockRefcount::Initialize`; a weak reference is broken by
`CmsBlockRefcount::BreakWeakReferences`, which the v3.14 redo log records as opcode `0x28`.

## Why this matters for recovery

What the table tells an analyst about recoverable content:

- **Bit 15 is a weak reference, not by itself content no file points at.** An entry with bit 15 (`0x8000`) set
  and a count of 0 is, by the driver reading, a cluster the deduplication path marked on a stream that maps it —
  so a file-walk does reach it through that stream.
- **One physical block can belong to several files.** A cluster with a count of N has N references beyond the first
  (block clones or deduplicated files). When you carve or recover from such a block, expect the same bytes to
  belong to several files.
- **A count shows sharing; it does not guarantee that the content survives.** A count of 1 or more says other clones or
  deduplicated files reference the cluster; a snapshot's or a hard link's sharing does not show here at all.

  See [what survives](what_survives.md) for the survival reasoning.
- **The dedup index looks like metadata pages.** `System Volume Information/NativeDedup/DedupIndex.db` stores its own
  data as 16 KiB pages that start with `MSB+` and carry, at `+0x0C`, a 32-bit value that is not the volume's signature
  (dozens of such pages on one corpus volume, hundreds on another): they are that file's content — its `extract` output
  equals those clusters, every one — and the address they name at `+0x20` is not where they lie. A scan that reads every
  cluster for pages meets them; `deleted --full` reads as pages only those that lie at the address they name, so it
  counts these and leaves them out, and does not take them for an earlier volume's pages.
- **The checkpoint says whether dedup was enabled.** Checkpoint flag `0x010` (dedup enabled) indicates that ReFS
  dedup was enabled on the volume (`Enable-ReFSDedup`) when the checkpoint was written; a populated root #6 alone does
  not.

## Version and volume-state differences

- **v3.4–v3.10:** schema `0xe0b0` and root #6 exist, and the tree was empty on every such volume measured.
  The schema is listed as present from v3.4 through Insider.
- **v3.14 with dedup enabled:** the table is populated, and the [checkpoint](../structures/chkp.md) flags read
  `0x07b2` on the dedup volumes measured: the native-v3.14 base `0x682` plus three features the dedup volumes carry,
  each set by its own driver function:
  - `0x010` dedup enabled — the dedup bit, and how a parser can detect "dedup was enabled" without walking the table;
  - `0x020` weak references enabled;
  - `0x100` dirty-state tracking enabled.
- The v3.14 redo log has a refcount opcode the 17134 (v3.4) driver lacks: `0x28` =
  `CmsBlockRefcount::BreakWeakReferences`, which marks the weak references on a range broken (bit 15 → bit 14) when
  the range is written or its checksums are rewritten.

## Finding the table with forefst

There is no dedicated `dedup` subcommand. `forefst summary` (and `fastsummary`) print the table's row count under
Global Root Tables (`Block RefCount`) and the checkpoint flags with their names; `refsanalysis chkp` prints the flags
too.

Decoding the entries needs a reader of your own:

- Enumerate the root-pointer list and locate **root #6 / schema `0xe0b0`** (`refsanalysis.py` labels root 6 — table
  ID 0x05 — as the Block RefCount Table).
- In each row's value, parse the `u16[BlockCount]` array at `0x1C` when the value is the long form (2,080 bytes for
  `0x400` clusters; the `TotalRefCount` u32 precedes it at 0x18). A 32-byte value is the compact form and has no array.
- Decode every entry with the masks above: `& 0x1FFF` is the count, `& 0x4000` the broken weak reference, `& 0x8000`
  the weak reference.

Whether dedup was *enabled* is readable directly from the checkpoint flags (bit `0x010`; composite `0x07b2` on the
dedup volumes measured), without parsing the table at all.

## Cross-references

- [Block Refcount Table](../structures/block_refcount.md) — the byte-level layout this page reads from:
  the key, the two value forms (2,080-byte and 32-byte) and the entry bit fields
- [Stream Snapshots and File Versioning](snapshots_versioning.md) — sharing this table does not count, and the
  strongest single-image content-recovery path
- [Copy-on-Write](copy_on_write.md) — the update model; the versions it keeps are not counted here
- [File IDs](file_ids.md) — why deduplicated files keep distinct FileRefs while hard-link names share one,
  so a shared `(HomeOID, ordinal)` is never a dedup signal
- [Hard Links](hard_links.md) — the identity-sharing mechanism that dedup (content-sharing) is often
  confused with
- [Compression](compression.md) — the feature enabled alongside dedup (`DedupAndCompress`), done by container
  compaction rather than per cluster
- [What survives](what_survives.md) — the survival categories of deleted content
- [Checkpoint](../structures/chkp.md) — where the dedup flag (`0x010`) and the flags the dedup volumes carry with it
  (`0x020`, `0x100`; composite `0x07b2`) live

## Evidence

- **The table's functions** are confirmed in the driver: it is built by `CmsBlockRefcount::Initialize` (the PDB symbol
  for schema `0xe0b0`); the counts are changed by `IncrementRefcount` / `DecrementRefcount` on 17134 and by
  `IncrementRefcount` / `AdjustRefcount` on 26100.8115; the v3.14 redo path adds
  `CmsBlockRefcount::BreakWeakReferences` (redo opcode `0x28`).
- **The layout** is decoded on disk: the 16-byte key, the two value forms (the 2,080-byte (`0x820`) long form, 2,724
  rows, and the 32-byte compact form, 28 rows on three volumes), the `TotalRefCount = Σ(entry & 0x1FFF)` invariant at
  value+0x18 (2,724 of 2,724 long rows), the `u16[1024]` array at 0x1C..0x81B, and the positions of the bit fields,
  over the 47 corpus volumes whose table has rows.
- **The count** — its width (`0x1FFF`) and meaning (references beyond the first; none for a hard link or a snapshot)
  — is read in the driver (26100.8115; the mask again on 26100.9444) and measured on one populated volume: block-clone
  pairs read 1 and triples 2 on 2,239 of 2,257 clusters, the hard-linked file 0 on 24 of 24. The two flag meanings
  are one driver reading.
- **The checkpoint flags** `0x010`, `0x020` and `0x100` are each set or tested by their own function (read twice,
  26100.8115 and 26100.9444); the composite `0x07b2` is measured on the dedup-enabled volumes only.
- **The dedup index's** `MSB+`-like pages are 70 on one corpus volume and 768 on another; `extract` equals those
  clusters on 838 of 838.

See [how this was verified](../methodology.md) to
trace these statements to the exact images and measurements in `analysis/`.

<!-- findings: CT_BKRC_001, CT_BKRC_RA_001, CT_BKRC_RA_002, CT_BKRC_RA_003, FS_CHKP_015, FS_CHKP_RA_001 -->
