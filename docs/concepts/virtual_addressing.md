# Virtual Addressing

Virtual addressing is the rule that decides where ReFS data actually lives on disk, and it is the first
thing a tool built for NTFS gets wrong. A cluster number found in a file's extent table or in a B+-tree
root is a *virtual* address — it is **not** a disk offset, and reading the sector at that number gives
you the wrong bytes. Every such number must be translated through the
[Container Table](../structures/container_table.md) before any disk access. This page explains the
two-level scheme, the arithmetic that performs the translation, and why ReFS is built this way.

## Two levels of indirection

NTFS translates in one step: a data run maps a file's VCN (virtual cluster number — the logical offset
*within the file*) straight to an LCN (the physical cluster on disk). ReFS inserts a virtual layer
between the two, so translation takes **two** steps:

- **Level 1 — per file (VCN → VLCN).** Each file's content is described by an extent table that maps the
  file's VCNs to **VLCNs** (virtual logical cluster numbers — positions in ReFS's volume-wide *virtual*
  address space). This is the analogue of an NTFS data run, except the result is still virtual. The
  byte layout of these entries is on the [Extent Descriptors](../structures/extent_descriptors.md) page.
- **Level 2 — per volume (VLCN → PLCN).** The [Container Table](../structures/container_table.md) maps a
  VLCN to its **PLCN** — the real cluster on disk. This second step is what NTFS has no equivalent of.

So the full path from a file offset to a disk sector is **VCN → VLCN → PLCN**, and the Container Table
is the only thing that knows the second arrow.

## The translation arithmetic

The volume is carved into fixed **64 MiB containers**. A VLCN is simply a container number in its high
bits and an offset *within* that container in its low bits, so the translation is a shift, a mask, and
one table lookup:

```
shift = log2(CPC) + 1      # 15 for 4 KiB clusters, 11 for 64 KiB
mask  = CPC - 1

container_index     = vlcn >> shift
offset_in_container = vlcn & mask
physical_LCN        = container_map[container_index] + offset_in_container
```

`CPC` is **clusters per container** = 64 MiB ÷ cluster size = **16,384** on 4 KiB clusters or **1,024**
on 64 KiB (it depends only on the format-time cluster size — see
[Cluster and Page Size](cluster_page_size.md)). `container_map` is the per-container physical start
cluster held in the Container Table.

The one subtlety worth understanding is the shift. The driver stores `log2(CPC)` (= 14 for 4 KiB
clusters) in the volume structure and shifts by that value **plus one**, so the effective shift is 15,
not 14. The extra bit is safe because a valid container LCN never sets bit `log2(CPC)` — the driver's
own `IsValidContainerLcn` check enforces it — so the `CPC − 1` mask (14 bits) still captures the whole
in-container offset even though the shift discards 15. This `+1` is exactly what the driver does in
`GetContainerIdFromRealRange`:

```c
// GetContainerIdFromRealRange (Win11 v3.14 driver)
lVar1 = RealRangeToContainerRange((CmsVolumeContainer *)local_18, param_1, &local_18, param_3, 0, 0);
if (-1 < lVar1) {
    // container_index = real_lcn >> (log2(CPC) + 1)
    *param_4 = *param_3 >> ((char)*(undefined4 *)(*(longlong *)(this + 8) + 0x50) + 1U & 0x3f);
}
return lVar1;
```

`+0x50` is where the volume structure holds `log2(CPC)`; the `+ 1U` is the adjustment. (An earlier
account of this shift used 14; the disk and the driver both give 15 — see Evidence below.)

## Why a virtual layer at all

The indirection is what lets ReFS move data on disk without rewriting metadata. Because a file's extents
point at *virtual* clusters, the file system can relocate a whole container — defragmenting, or moving
it between [storage tiers](tiering.md) — by changing a single physical-start value in the Container
Table, with **no edit to any per-file extent table**. The same property underlies
[copy-on-write](copy_on_write.md) at the container level and lets the
[three-tier allocator](allocation_space_mgmt.md) manage virtual space independently of physical layout.

A forensic consequence follows directly: a file's content can sit at a different physical location than
it did yesterday even though none of its metadata or timestamps changed. Physical position is not a
stable identifier for a file's data.

## Containers

A container is a fixed **64 MiB** region; the size is `bytes_per_container` at
[VBR](../structures/vbr.md) offset 0x40 (`0x04000000`, invariant across every volume). The volume holds
one container per 64 MiB:

| Volume size | Cluster size | Containers |
|-------------|--------------|-----------|
| 2 GiB | 4 KiB | 31 |
| 8 GiB | 4 KiB | 127 |
| 2 TiB | 4 KiB | 32,767 |
| 15 TiB | 64 KiB | 245,759 |

## The bootstrap exception

Almost everything on the volume is virtually addressed — but the Container Table itself cannot be, or
there would be no way to start translating. Three roots therefore store **real (physical) LCNs**:

- roots **#7 / #8** — the [Container Table](../structures/container_table.md) and its duplicate;
- root **#12** — the Small [Allocator](../structures/allocators.md).

They are read directly from the [checkpoint](../structures/chkp.md) root list at physical positions. This
is the one place a cluster number in a ReFS root *is* a disk offset; everywhere else, translation is
mandatory.

## Forensic impact

Treating a VLCN as a physical address — the reflex of an NTFS-trained parser — reads clusters that are
not the file's data. This is the single most common ReFS parsing error, and it corrupts every result
derived from it. The discipline is simple: load the Container Table first — it is the step of the
[bootstrap chain](bootstrap_chain.md) that makes address resolution possible — and route **every** VLCN
through it before touching the disk.
Any recovery or carving workflow that skips this step — see [Deletion Recovery](deletion_recovery.md) —
will reconstruct content from the wrong sectors.

## Cross-references

- [Container Table](../structures/container_table.md) — the structure that holds the VLCN → PLCN map
- [Extent Descriptors](../structures/extent_descriptors.md) — the per-file VCN → VLCN extent entries
- [Allocators](../structures/allocators.md) — manage allocation within the virtual address space
- [VBR](../structures/vbr.md) — `bytes_per_container` (0x40) and the cluster-size fields
- [Cluster and Page Size](cluster_page_size.md) — how the cluster size fixes CPC
- [Bootstrap Chain](bootstrap_chain.md) — where loading the Container Table sits in the parse order
- [NTFS vs ReFS](ntfs_comparison.md) — the one-level vs two-level translation contrast

## Evidence

The two-level scheme and the shift/mask arithmetic are confirmed in the driver (E2) — the translation is
performed by `GetContainerIdFromRealRange` (calling `RealRangeToContainerRange`), with `IsValidContainerLcn`
guaranteeing the boundary bit is zero — and on the raw-disk corpus (RD): CPC at container value+0x18, the
physical start at value[len−16], and `PLCN = container_start + (vlcn & (CPC−1))` resolved consistently
across the corpus, including the roots-7/8/12 real-LCN exception. The **15**-cluster shift for 4 KiB
clusters (11 for 64 KiB) is `CPC.bit_length()`. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
