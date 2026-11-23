# Bootstrap Chain

Before a ReFS parser can read a file, a directory, or any B+-tree, it has to find the trees. There is only one
path to them.

Almost every address stored in the trees is a *virtual* cluster number (see
[Virtual Addressing](virtual_addressing.md)), so the parser cannot translate those addresses until it has loaded the
[Container Table](../structures/container_table.md). It cannot find the Container Table until it has walked a fixed
chain of metadata anchors from the partition table inward.

This page describes that chain, why each link points at the next, and the two places where the chain *must* break
the virtual-addressing rule or it would never bootstrap.

## The chain at a glance

```text
GPT → VBR → SUPB → CHKP → Container Table → any target table
```

Each link exists only to locate the next, and each is found at a position the previous link hands you:

| Step | Structure | Where it lives | What it hands the next step |
|------|-----------|----------------|-----------------------------|
| 1 | GPT | LBA 1 (header), the entry array it names | The ReFS partition's starting LBA — the base for all volume addressing |
| 2 | [VBR](../structures/vbr.md) | First sector of the partition | Cluster size, version, checksum selector |
| 3 | [SUPB](../structures/supb.md) | LCN 0x1E (fixed), plus two backups near the volume end | The LCNs of the two alternating checkpoint slots |
| 4 | [CHKP](../structures/chkp.md) | The two LCNs from the SUPB; slot order, a later valid copy only on a strictly higher virtual clock | The 13 root page references — including the Container Table at real LCNs |
| 5 | [Container Table](../structures/container_table.md) | Roots #7/#8 (real LCNs — read directly) | The VLCN→PLCN map every other table needs |
| 6 | Target table | Its root is a virtual LCN, now translatable | The Object Table, Schema Table, or any per-object tree |

The chain has this *order* because addressing is two-level. A cluster number stored in any root, extent,
or B+-tree pointer is a VLCN, and a VLCN cannot be read until the Container Table resolves it to a
physical LCN. So the parser must reach a structure that *isn't* virtually addressed
before it can translate anything. The structures with that property are:

- the volume anchors at fixed positions (VBR, SUPB);
- the two checkpoints, at the real LCNs the SUPB lists;
- the three bootstrap roots that store real LCNs by design (7, 8 and 12).

## Step 1 — GPT partition table

The GUID Partition Table gives each partition's starting LBA. A ReFS partition carries the generic Basic Data type
GUID that NTFS and FAT partitions also carry, so the type does not identify it: the parser reads the boot sector of
each Basic Data partition and takes the one whose name at offset 3 is `ReFS`, which is what `forefst.py` does. An image
of a bare partition has no GPT; give its start with `--partition-start`.

That LBA is the origin for every cluster address that follows: all later LCNs are partition-relative, so the
parser adds `partition_start` before touching any sector. Nothing in the GPT is ReFS-specific; it is the
only step shared with any other file system.

## Step 2 — Volume Boot Record (VBR)

The VBR sits at the first sector of the partition. The driver recognises it by the name `ReFS` and four zero bytes
at offset 3 (`RefsIsBootSectorOurs`); it also carries the `FSRS` identifier at offset 0x10. It is the parser's source
of truth for the format parameters that decide how every later structure is laid out, so reading it first is
mandatory:

- **Cluster size** — `sectors_per_cluster` (offset 0x24) × `bytes_per_sector` (0x20). This converts every
  LCN into a byte offset and also fixes *clusters-per-container*, which drives the translation arithmetic
  in step 5 (see [Cluster and Page Size](cluster_page_size.md)).
- **Version** (offset 0x28, packed `major.minor`) — selects which structure layouts apply downstream; a
  parser that skips this will misread version-gated fields (see [Version Detection](version_detection.md)).
- **Checksum algorithm selector** (offset 0x2A) — read only when the volume flags carry 0x40 (volumes formatted at
  3.10 or later): 2 = CRC64, 4 = SHA-256. On the other volumes refs.sys uses CRC64 whatever the field holds, and
  17134 does not read it at all.
- **Page-reference size** — set by the checksum type and the version. A
  [page reference](../structures/page_references.md) inside the B+-trees is 48 bytes with CRC64 and 72 with SHA-256;
  the checkpoint's own root references are 104 bytes where the volume is at 3.4, 3.7 or 3.9 (17134 writes that size
  as a constant, and the 3.7 and 3.9 volumes declare it too). The checkpoint states its root-reference size at
  +0x5C (step 4).
- **Volume flags** (offset 0x2C) — written by refs.sys at run time; two of its bits, 0x20 (hard links supported) and
  0x40, are fixed at format time and kept their values across the two upgrades measured.

The SUPB location is *not* read from the VBR — it is a fixed constant (LCN 0x1E).

The VBR carries a ROR1+ADD self-checksum at offset 0x16, computed over bytes 3 to (+0x14) − 1 with the two checksum
bytes excluded: 3..511 on every volume measured, where +0x14 is 0x200. The driver verifies it in
`RefsIsBootSectorOurs`, and a mismatch prevents mount.

The VBR's location depends on nothing but the partition start, which is why it can be the first thing read.

## Step 3 — Superblock (SUPB)

The Superblock always lives at LCN 0x1E — a fixed constant, not a value stored anywhere — and carries the `SUPB`
signature in its page header (a parser can test it; the driver validates the copy by its self-checksum instead). Its
only job in the bootstrap is to point at the two checkpoints: it holds a checkpoint-reference count (always 2) and,
at the offset SUPB+0x70 gives (0xC0 on the volumes measured), the two checkpoint LCNs at 0xC0 / 0xC8.

The SUPB is redundant, and a parser can fall back on its copies when the primary fails. There are **three
copies** — the primary at LCN 0x1E and two backups computed from the volume size (at `VolSize−2` and
`VolSize−3`).

Each copy carries its own self-checksum (a self-descriptor at SUPB+0xD0), and the driver *does* verify it at mount
through `ValidateSuperBlock`. The checksum is cluster-size-dependent: read the checksum-type byte at descriptor+0x22
to know whether it is CRC32-C (4-byte, on 4K-cluster volumes), CRC64 (8-byte, on 64K-cluster volumes), or SHA-256
(32-byte).

Which copy is read:

- the primary at LCN 0x1E, whenever it passes validation, whatever the backups hold;
- otherwise a backup: `ChooseSuperBlock`'s generation at SUPB+0x68 orders only the two backups (`VolSize−3` replaces
  `VolSize−2` only when its `+0x68` is strictly higher), so a corrupt primary silently falls back to a backup.

On a writable mount, unless the other two copies are valid with the same +0x68, the chosen copy is written over the
others and re-checksummed — the self-heal behaviour described on [Volume Redundancy](redundancy.md).

For a forensic parser the practical rule is: use the primary when it validates; otherwise compare the two backups,
and when no copy validates, read the primary (or the first signed backup) and say so.

## Step 4 — Checkpoint (CHKP)

The Checkpoint is the volume's atomic commit point and the step at which the chain reaches the trees. Like the SUPB, each CHKP
copy carries a self-checksum verified at mount (same cluster-size-dependent rule).

The driver (`ReadLatestCheckpoint`) chooses the copy this way:

- read the two checkpoint LCNs from the SUPB in the order it lists them;
- skip a copy that fails validation, so the lower-clock copy is read when the higher one fails;
- switch to the other copy only when its **virtual clock** (offset 0x60) is strictly greater — a tie between two
  valid copies keeps slot 0;
- the mount fails only when no copy passes.

On the 26100 builds a first pass also rejects a copy whose root 0xC, 7 or 8 fails to read or verify; see
[Checkpoint](../structures/chkp.md). The copy chosen is the current consistent state.

Each flush writes the *other* slot with `clock + 1`, so the lower-clock slot is the previous consistent state and a
rollback target until the next flush; this is the mechanism behind
[transactional crash-consistency](transactions_crash_consistency.md).

The CHKP then holds **13 root page references**, each the root of a system B+-tree. They are reached through 13 u32
in-record offsets, and each is the size CHKP+0x5C gives (104 bytes where the volume is at 3.4–3.9, 48 with CRC64 and
72 with SHA-256 from 3.10):

| Root | Table | Addressing |
|------|-------|-----------|
| 0 | Object ID Table | Virtual LCN |
| 1 | Medium Allocator | Virtual LCN |
| 2 | Container Allocator | Virtual LCN |
| 3 | Schema Table | Virtual LCN |
| 4 | Parent-Child Table | Virtual LCN |
| 5 | Object ID Table (duplicate) | Virtual LCN |
| 6 | Block Refcount | Virtual LCN |
| **7** | **Container Table** | **Real (physical) LCN** |
| **8** | **Container Table (duplicate)** | **Real (physical) LCN** |
| 9 | Schema Table (duplicate) | Virtual LCN |
| 10 | Container Index | Virtual LCN |
| 11 | Integrity State | Virtual LCN |
| **12** | **Small Allocator** | **Real (physical) LCN** |

Three failover pairs let a parser survive a corrupt root: Object Table 0/5, Schema Table 3/9, Container Table 7/8.
Block Refcount (#6) has no failover pair. refs.sys opens the Container Table pair by slot: root 7 first, root 8 when
root 7 fails.

The Container-Table pair is defined by the *set* of two table IDs at roots {7,8}, not by a
fixed index-to-table-ID order — one large (2 TB) volume carries the two swapped, so a robust parser treats either of
{7,8} as a valid Container-Table root.

Roots **7, 8, and 12** are the bootstrap exception: they store **real, physical LCNs** that are read
directly, with no translation. Every other root stores a virtual LCN and is unreadable until the
Container Table from roots 7/8 is loaded.

Where the 13 root offsets are depends on CHKP flag 0x0200:

- without it (formats 3.4–3.10), `CHKP+0x94` holds the 13 root offsets (u32) themselves;
- with it (3.11 and later), `CHKP+0x94` is the offset of a table of those 13 offsets inside the same record, and
  `CHKP+0x98` the table's length.

Either way the root references are reached through offsets; they are never stored inline at +0x94.

## Step 5 — Container Table: the VLCN→PLCN map

The [Container Table](../structures/container_table.md) is the structure that holds the per-container
physical-start map the chain leads to. It can be read without translation because its roots (#7/#8) carry real
LCNs, so every other address can be translated from it. (The Small Allocator,
root 12, is the other table read at a real LCN.)

The volume is divided into fixed **64 MiB containers**, and a VLCN is a container index in its high
bits and an in-container offset in its low bits. Translation is therefore a shift, a mask, and one table
lookup:

```text
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

The row size depends on checksum type and cluster size: **160 bytes** on 4 KiB clusters with CRC64 (or a selector
of 0), and **224 bytes** on 64 KiB clusters or SHA-256 (eight 16-byte units before the mapping range instead of
four, so the physical start is at value+0xD0). A parser must read the VBR's cluster-size and checksum fields (step 2)
to pick the right row stride here.

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
chkp   = chkp_b if chkp_b.valid and (not chkp_a.valid or chkp_b.vclock > chkp_a.vclock) else chkp_a  # slot order, strictly greater

container_root  = chkp.roots[7]                                  # real LCN — read directly
container_table = load_btree(disk, container_root, translate=False)

object_root  = chkp.roots[0]                                     # virtual LCN — needs translation
object_table = load_btree(disk, object_root, translate=container_table)
```

## Forensic notes

Each step of the chain also has a copy that a recovery can fall back on:

- a corrupt VBR can be checked against its backup at the volume's last sector (refs.sys itself reads the backup only
  when sector 0 cannot be read);
- a corrupt SUPB primary falls back to one of two end-of-volume copies, ordered by generation;
- a corrupt or higher-clock-invalid CHKP falls back to the lower-clock copy, which *is* the previous consistent state.

A tool that reads only the primary copy at any step will miss volumes that mount fine in Windows because the driver
itself fell back — so a forensic parser should mirror the driver's selection logic, not assume the primary is
authoritative.

Finally, step 4's lower-clock checkpoint can point at an older tree: when the image was taken between two checkpoint
writes that changed a root table, it exposes a previous state of the metadata. On a cleanly unmounted volume the two
copies usually point at the same tree — see [Copy-on-Write](copy_on_write.md#the-checkpoint-comparison-limit) and
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

The chain order and link positions are confirmed on the raw-disk corpus: SUPB at LCN 0x1E with two
end-of-volume backups, the CHKP virtual-clock selection at +0x60, and the 13 roots with roots 7/8/12 at
real LCNs. The self-checksum and selection logic are confirmed in the driver:

- `RefsIsBootSectorOurs` (VBR; read on 17134, 26100.9444 and Insider 29574);
- `ValidateSuperBlock` and `ChooseSuperBlock` (the backups' order by +0x68);
- `ReadLatestCheckpoint` (CHKP selection by +0x60, strictly greater, slot order; read on 17134, 26100.8115 to .9549
  and Insider 29574);
- `GetContainerIdFromRealRange` calling `RealRangeToContainerRange` with `IsValidContainerLcn` for the translation.

The SUPB/CHKP self-checksum being cluster-size-dependent and verified-at-mount (CRC32-C 4B on 4K-cluster, CRC64 8B on
64K, SHA-256 32B), with the selection rules above and the self-heal of stale copies, is decompiled and raw-disk
verified.

The counts behind the text:

- the root offsets: on the 12 volumes formatted at 3.4 (9), 3.7 (1) and 3.9 (2) the checkpoint copy in use declares
  +0x5C = 0x68 and holds its 13 root offsets at +0x94, and all 156 root references read there verify; flag 0x0200 is
  set on the 206 checkpoint copies of volumes at 3.11 or later and on none of the 28 copies of 3.4–3.10 volumes;
- the VBR checksummed length +0x14 is 0x200 on the 124 volumes whose boot sector reads;
- the swapped Container Table roots are on the 2 TB "millions of actions" volume and its later images.

See [how this was verified](../methodology.md) for the method.

<!-- findings: FS_CHKP_005, FS_SUPB_001, FS_SUPB_005, FS_SUPB_007, FS_SUPB_RA_003 -->
