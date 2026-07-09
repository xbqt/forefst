# Bootstrap Chain

Before a ReFS parser can read a single file, a directory, or any B+-tree, it has to find the trees in
the first place — and there is exactly one path that gets it there. Every address on the volume is a
*virtual* cluster number (see [Virtual Addressing](virtual_addressing.md)), so the parser cannot
translate any address until it has loaded the [Container Table](../structures/container_table.md), and
it cannot find the Container Table until it has walked a fixed chain of metadata anchors from the
partition table inward. This page describes that chain, why each link points at the next, and the two
places where the chain *must* break the virtual-addressing rule or it would never bootstrap.

## The chain at a glance

```
GPT → VBR → SUPB → CHKP → Container Table → any target table
```

Each link exists only to locate the next, and each is found at a position the previous link hands you:

| Step | Structure | Where it lives | What it hands the next step |
|------|-----------|----------------|-----------------------------|
| 1 | GPT | Sector 1 (header), sector 2+ (entries) | The ReFS partition's starting LBA — the base for all volume addressing |
| 2 | [VBR](../structures/vbr.md) | First sector of the partition | Cluster size, version, checksum mode, and the fixed SUPB location (LCN 0x1E) |
| 3 | [SUPB](../structures/supb.md) | LCN 0x1E (fixed), plus two backups near the volume end | The two checkpoint LCNs (primary and backup) |
| 4 | [CHKP](../structures/chkp.md) | The two LCNs from the SUPB; pick the higher virtual clock | The 13 root page references — including the Container Table at real LCNs |
| 5 | [Container Table](../structures/container_table.md) | Roots #7/#8 (real LCNs — read directly) | The VLCN→PLCN map every other table needs |
| 6 | Target table | Its root is a virtual LCN, now translatable | The Object Table, Schema Table, or any per-object tree |

The deep reason the chain is *ordered* this way is that addressing is two-level. A cluster number stored
in any root, extent, or B+-tree pointer is a VLCN, and a VLCN means nothing until the Container Table
resolves it to a physical LCN. So the parser must reach a structure that *isn't* virtually addressed
before it can translate anything — and the only structures with that property are the volume anchors
(VBR, SUPB) at fixed positions and the three bootstrap roots that store real LCNs by design.

## Step 1 — GPT partition table

The GUID Partition Table identifies the ReFS partition by its type GUID and gives its starting LBA. That
LBA is the origin for every cluster address that follows: all later LCNs are partition-relative, so the
parser adds `partition_start` before touching any sector. Nothing in the GPT is ReFS-specific; it is the
only step shared with any other file system.

## Step 2 — Volume Boot Record (VBR)

The VBR sits at the first sector of the partition and is recognised by the `FSRS` signature at offset
0x10. It is the parser's source of truth for the format parameters that decide how every later structure
is laid out, so reading it first is mandatory:

- **Cluster size** — `sectors_per_cluster` (offset 0x24) × `bytes_per_sector` (0x20). This converts every
  LCN into a byte offset and also fixes *clusters-per-container*, which drives the translation arithmetic
  in step 5 (see [Cluster and Page Size](cluster_page_size.md)).
- **Version** (offset 0x28, packed `major.minor`) — selects which structure layouts apply downstream; a
  parser that skips this will misread version-gated fields (see [Version Detection](version_detection.md)).
- **Checksum algorithm selector** (offset 0x2A) — `None`, CRC64, or SHA-256. This sets the
  [page-reference](../structures/page_references.md) size (104 / 48 / 72 bytes), which is the stride used
  to walk every root list and B+-tree node from step 4 onward.
- **Volume flags** (offset 0x2C) — format-time capability bits.

The SUPB location is *not* read from the VBR — it is a fixed constant (LCN 0x1E). The VBR carries a
ROR1+ADD self-checksum at offset 0x16, computed over bytes 3..511 with the two checksum bytes excluded;
the driver verifies it via `RefsIsBootSectorOurs`, and a mismatch prevents mount. Critically, the VBR is
the one structure whose location does not depend on translation, which is why it can be the first thing
read.

## Step 3 — Superblock (SUPB)

The Superblock always lives at LCN 0x1E — a fixed constant, not a value stored anywhere — and is
recognised by the `SUPB` signature in its page header. Its only job in the bootstrap is to point at the
two checkpoints: it holds a checkpoint-reference count (always 2) and the two checkpoint LCNs at offset
0xC0 / 0xC8.

The SUPB is the volume's redundancy anchor, and the parser should treat it as such. There are **three
copies** — the primary at LCN 0x1E and two backups computed from the volume size (at `VolSize−2` and
`VolSize−3`). Each copy carries its own self-checksum (a self-descriptor at SUPB+0xD0), and the driver
*does* verify it at mount through `ValidateSuperBlock`. The checksum is cluster-size-dependent: read the
checksum-type byte at descriptor+0x22 to know whether it is CRC32-C (4-byte, on 4K-cluster volumes),
CRC64 (8-byte, on 64K-cluster volumes), or SHA-256 (32-byte). The authoritative copy is **not**
necessarily the primary: `ChooseSuperBlock` selects the validating copy with the highest generation
value at SUPB+0x68, so a corrupt primary silently falls back to a backup. On a writable volume the
winner is copied over the stale copies and re-checksummed — the self-heal behaviour described on
[Volume Redundancy](redundancy.md). For a forensic parser the practical rule is: try all three SUPB
copies, validate each, and trust the highest valid generation.

## Step 4 — Checkpoint (CHKP)

The Checkpoint is the volume's atomic commit point and the chain's branch into the trees. Read both
checkpoint LCNs from the SUPB, then select the copy with the higher **virtual clock** (offset 0x60) —
that is the current consistent state. Each flush writes the *other* slot with `clock + 1`, so the
lower-clock slot is the previous consistent state and a rollback target until the next flush; this is
the mechanism behind [transactional crash-consistency](transactions_crash_consistency.md). Like the
SUPB, each CHKP copy carries a self-checksum verified at mount (same cluster-size-dependent rule), and
`ChooseCheckpointRecord` falls back to the lower-clock copy if the higher one fails to validate; if both
fail, mount fails.

The page-reference size field at CHKP+0x5C is load-bearing for everything after this point — it is the
stride for reading the 13 root references that follow. The CHKP then holds **13 root page references**,
each the root of a system B+-tree:

| Root | Table | Addressing |
|------|-------|-----------|
| 0 | Object ID Table (primary) | Virtual LCN |
| 1 | Medium Allocator | Virtual LCN |
| 2 | Container Allocator | Virtual LCN |
| 3 | Schema Table (primary) | Virtual LCN |
| 4 | Parent-Child Table | Virtual LCN |
| 5 | Object ID Table (duplicate) | Virtual LCN |
| 6 | Block Refcount | Virtual LCN |
| **7** | **Container Table (primary)** | **Real (physical) LCN** |
| **8** | **Container Table (duplicate)** | **Real (physical) LCN** |
| 9 | Schema Table (duplicate) | Virtual LCN |
| 10 | Container Index | Virtual LCN |
| 11 | Integrity State | Virtual LCN |
| **12** | **Small Allocator** | **Real (physical) LCN** |

Three of the failover pairs let a parser survive a corrupt root: Object Table 0/5, Schema Table 3/9,
Container Table 7/8. Block Refcount (#6) has no failover pair. One subtlety worth knowing: the
Container-Table pair is defined by the *set* of two table IDs at roots {7,8}, not by a fixed
index-to-table-ID order — large volumes have been observed with the two swapped, so a robust parser
treats either of {7,8} as a valid Container-Table root.

Roots **7, 8, and 12** are the bootstrap exception: they store **real, physical LCNs** that are read
directly, with no translation. Every other root stores a virtual LCN and is unreadable until the
Container Table from roots 7/8 is loaded. (Whether the 13 references are stored inline at CHKP+0x94 or
behind a pointer to a separate root-list page depends on a CHKP flag — the indirect mode appears from
v3.14.)

## Step 5 — Container Table: the VLCN→PLCN map

The [Container Table](../structures/container_table.md) is the structure that holds the per-container
physical-start map this whole chain exists to reach. It is the *only* table that can be read without
translation, precisely because its roots (#7/#8) carry real LCNs — that is what makes it the foothold
for translating everything else.

The volume is carved into fixed **64 MiB containers**, and a VLCN is just a container index in its high
bits and an in-container offset in its low bits. Translation is therefore a shift, a mask, and one table
lookup:

```
shift = CPC.bit_length()          # 15 for 4 KiB clusters, 11 for 64 KiB
mask  = CPC - 1

container_index     = vlcn >> shift
offset_in_container = vlcn & mask
physical_LCN        = container_map[container_index] + offset_in_container
```

`CPC` (clusters per container) lives at value+0x18 of each Container Table row — 16,384 on 4 KiB
clusters, 1,024 on 64 KiB — and the physical start cluster is always at value[len−16]. The driver
performs this in `GetContainerIdFromRealRange` (calling `RealRangeToContainerRange`): it stores
`log2(CPC)` in the volume structure and shifts by that value **plus one**, so the effective shift is 15
for 4 KiB clusters, not 14. The extra bit is safe because `IsValidContainerLcn` guarantees bit
`log2(CPC)` is zero in any valid container LCN, so the `CPC − 1` mask still captures the whole offset.
The [Virtual Addressing](virtual_addressing.md) page derives this arithmetic in full.

The row size depends on checksum type and cluster size: **160 bytes** on 4 KiB clusters with CRC64 or
None, and **224 bytes** on 64 KiB clusters or SHA-256 (the larger integrity buffer, with the physical
start at value+0xD0). A parser must read the VBR's cluster-size and checksum fields (step 2) to pick the
right row stride here.

## Step 6 — any target table

With the Container Table loaded, every other root becomes reachable:

1. Read the target root's page reference from the checkpoint (e.g. root 0 for the
   [Object Table](../structures/object_table.md)).
2. Translate its VLCN through the Container Table.
3. Read and parse the root page.
4. Walk the B+-tree, translating each child VLCN through the Container Table as you descend.

From here the parser has full read access to the [Schema Table](../structures/schema_table.md),
[Parent-Child Table](../structures/parent_child_table.md), [Allocators](../structures/allocators.md),
and every per-object tree.

## Implementation pattern

```python
# The bootstrap chain, in parse order.
partition_start = read_gpt(disk)
vbr             = read_vbr(disk, partition_start)
cluster_size    = vbr.cluster_size

supb  = read_page(disk, partition_start + 0x1E * cluster_size)   # fixed LCN 0x1E
chkp_a = read_page(disk, partition_start + supb.chkp_lcn_a * cluster_size)
chkp_b = read_page(disk, partition_start + supb.chkp_lcn_b * cluster_size)
chkp   = chkp_a if chkp_a.vclock > chkp_b.vclock else chkp_b     # higher virtual clock wins

container_root  = chkp.roots[7]                                  # real LCN — read directly
container_table = load_btree(disk, container_root, translate=False)

object_root  = chkp.roots[0]                                     # virtual LCN — needs translation
object_table = load_btree(disk, object_root, translate=container_table)
```

## Forensic notes

The chain is also a redundancy ladder, and each rung is a recovery option. A corrupt VBR can be checked
against its backup near the volume end; a corrupt SUPB primary falls back to one of two end-of-volume
copies by generation; a corrupt or higher-clock-invalid CHKP falls back to the lower-clock copy, which
*is* the previous consistent state. A tool that hard-codes "primary only" at any rung will miss volumes
that mount fine in Windows because the driver itself fell back — so a forensic parser should mirror the
driver's selection logic, not assume the primary is authoritative. Finally, because step 4's lower-clock
checkpoint preserves the prior on-disk state, a dirty (crashed) volume can expose a recoverable previous
snapshot of the metadata that a clean volume would have overwritten — see
[Transactional Crash-Consistency](transactions_crash_consistency.md).

## Cross-references

- [VBR](../structures/vbr.md) — format parameters and the ROR1+ADD self-checksum that gate every later step
- [Superblock (SUPB)](../structures/supb.md) — the fixed anchor and its three self-validated copies
- [Checkpoint (CHKP)](../structures/chkp.md) — the 13 root references, virtual clock, and rollback slot
- [Container Table](../structures/container_table.md) — the structure that holds the VLCN→PLCN map step 5 loads
- [Page References](../structures/page_references.md) — the three size formats that set the root-list stride
- [Virtual Addressing](virtual_addressing.md) — why translation is mandatory and the shift/mask arithmetic
- [Volume Redundancy](redundancy.md) — how VBR, SUPB, and CHKP copies are maintained and self-healed
- [Transactional Crash-Consistency](transactions_crash_consistency.md) — the checkpoint as atomic commit and rollback target
- [Cluster and Page Size](cluster_page_size.md) — how the cluster size fixes CPC and page stride
- [Version Detection](version_detection.md) — establishing the version before interpreting any structure

## Evidence

The chain order and link positions are confirmed on the raw-disk corpus (RD): SUPB at LCN 0x1E with two
end-of-volume backups, the CHKP virtual-clock selection at +0x60, and the 13 roots with roots 7/8/12 at
real LCNs. The self-checksum and selection logic are confirmed in the driver (E2): `RefsIsBootSectorOurs`
(VBR), `ValidateSuperBlock` and `ChooseSuperBlock` (SUPB generation selection at +0x68),
`ChooseCheckpointRecord` (CHKP virtual-clock selection at +0x60), and `GetContainerIdFromRealRange`
calling `RealRangeToContainerRange` with `IsValidContainerLcn` for the translation. The SUPB/CHKP
self-checksum being cluster-size-dependent and verified-at-mount (CRC32-C 4B on 4K-cluster, CRC64 8B on
64K, SHA-256 32B), with clock-based selection and self-heal of stale copies, is finding FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
