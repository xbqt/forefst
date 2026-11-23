# Virtual Addressing

Virtual addressing is the rule that decides where ReFS data is stored on disk. It is the first thing a tool
built for NTFS gets wrong.

A cluster number found in a file's extent map or in a B+-tree page reference is a *virtual* address — it is **not**
a disk offset, and reading the sector at that number gives you the wrong bytes. Every such number must be translated
through the [Container Table](../structures/container_table.md) before any disk access. The exceptions are few and
fixed; they are listed below.

This page explains the two-level scheme, the arithmetic that performs the translation, and why ReFS is built this
way.

## Two levels of indirection

NTFS translates in one step: a data run maps a file's VCN (virtual cluster number — the logical offset
*within the file*) straight to an LCN (the physical cluster on disk). ReFS inserts a virtual layer
between the two, so translation takes **two** steps:

- **Level 1 — per file (VCN → VLCN).** A file whose data is in extents has an extent map — a B+-tree node inside
  its `$DATA` record — whose 24-byte rows map the file's VCNs to **VLCNs** (virtual logical cluster numbers —
  positions in ReFS's volume-wide *virtual* address space). This is the analogue of an NTFS data run, except the
  result is still virtual. The byte layout of these entries is on the
  [Extent Records](../structures/extent_descriptors.md) page.
- **Level 2 — per volume (VLCN → PLCN).** The [Container Table](../structures/container_table.md) maps a
  VLCN to its **PLCN** — the real cluster on disk. This second step is what NTFS has no equivalent of.

So the full path from a file offset to a disk sector is **VCN → VLCN → PLCN**, and the Container Table
is the only structure that holds the second mapping.

## The translation arithmetic

The volume is divided into fixed **64 MiB containers**. A VLCN is a container number in its high
bits and an offset *within* that container in its low bits, so the translation is a shift, a mask, and
one table lookup:

```text
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

The shift needs care. The driver stores `log2(CPC)` (= 14 for 4 KiB
clusters) in the volume structure and shifts by that value **plus one** (on every build read), so the effective
shift is 15, not 14. The extra bit is safe because a valid container LCN never sets bit `log2(CPC)` — the driver's
own `IsValidContainerLcn` check enforces it — so the `CPC − 1` mask (14 bits) still captures the whole
in-container offset even though the shift discards 15. This `+1` is exactly what the driver does in
`GetContainerIdFromRealRange`:

```c
// GetContainerIdFromRealRange (refs.sys 26100.8115)
lVar1 = RealRangeToContainerRange((CmsVolumeContainer *)local_18, param_1, &local_18, param_3, 0, 0);
if (-1 < lVar1) {
    // container_index = real_lcn >> (log2(CPC) + 1)
    *param_4 = *param_3 >> ((char)*(undefined4 *)(*(longlong *)(this + 8) + 0x50) + 1U & 0x3f);
}
return lVar1;
```

`+0x50` is where the volume structure holds `log2(CPC)` on the 26100 and Insider builds read (on 17134 it is
`+0x4C`, and `+0x50` holds CPC itself); the `+ 1U` is the adjustment.

## Why a virtual layer at all

The indirection is what lets ReFS move data on disk without rewriting metadata. Because a file's extents
point at *virtual* clusters, the file system can relocate a whole container — defragmenting, or moving
it between [storage tiers](tiering.md) — by changing a single physical-start value in the Container
Table, with **no edit to any per-file extent table**. The driver has the code for it (a `MoveContainer` redo record,
container rotation on the 26100 and Insider builds); a container move was not measured on disk here.

[Copy-on-write](copy_on_write.md) is a separate mechanism: a changed page is written to new clusters and the
reference to it is rewritten.

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

- roots **#7 / #8** — the [Container Table](../structures/container_table.md) and its failover copy;
- root **#12** — the Small [Allocator](../structures/allocators.md).

They are read directly from the [checkpoint](../structures/chkp.md) root list at physical positions. This
is the one place a cluster number in a ReFS root *is* a disk offset.

Two other kinds of cluster number are physical too, and must not be translated:

- the fixed anchors: the superblock at LCN 0x1E and its backups, and the two checkpoint LCNs the superblock lists;
- the ranges in the Medium allocator's rows, which count physical clusters (see
  [Allocators](../structures/allocators.md)).

Everywhere else, translation is mandatory.

## Forensic impact

Treating a VLCN as a physical address, as an NTFS-trained parser does, reads clusters that are not the file's data, and
every result derived from them is wrong. Load the Container Table first (it is the step of the [bootstrap
chain](bootstrap_chain.md) that makes address resolution possible), and translate **every** VLCN through it before
reading the disk. Any recovery or carving workflow that skips this step — see [Deletion Recovery](deletion_recovery.md)
— will reconstruct content from the wrong sectors.

A sparse hole's extent row carries a VLCN that mirrors its file VCN, not an address. A hole is the
row's flag 0x20; reading its "VLCN" as an address puts unrelated volume clusters inside the file (see
[Extent Records](../structures/extent_descriptors.md)).

## Cross-references

- [Container Table](../structures/container_table.md) — the structure that holds the VLCN → PLCN map
- [Extent Records](../structures/extent_descriptors.md) — the per-file VCN → VLCN extent entries
- [Allocators](../structures/allocators.md) — manage allocation within the virtual address space
- [VBR](../structures/vbr.md) — `bytes_per_container` (0x40) and the cluster-size fields
- [Cluster and Page Size](cluster_page_size.md) — how the cluster size fixes CPC
- [Bootstrap Chain](bootstrap_chain.md) — where loading the Container Table sits in the parse order
- [NTFS vs ReFS](ntfs_comparison.md) — the one-level vs two-level translation contrast

## Evidence

The two-level scheme and the shift/mask arithmetic are confirmed in the driver — the translation is
performed by `GetContainerIdFromRealRange` (calling `RealRangeToContainerRange`), with `IsValidContainerLcn`
guaranteeing the boundary bit is zero — and on the raw-disk corpus: CPC at container value+0x18, the
physical start at value[len−16], and `PLCN = container_start + (vlcn & (CPC−1))` resolved consistently
across the corpus, including the roots-7/8/12 real-LCN exception. The **15**-bit shift for 4 KiB
clusters (11 for 64 KiB) is `CPC.bit_length()`.

The Medium allocator's physical row addresses: its span is exactly the volume's physical cluster range on every
image measured, and live file-data extents are marked allocated 99–100 % of the time by their translated physical
cluster against 0–27 % by their VLCN (13,917 extents on 28 images). The hole rule: `flags & 0x20` is a strict superset
of `VLCN == 0`, with no counterexample, on four volumes (8,864 rows). Container moves and rotation are driver code
(`MoveContainer`, `RotateContainers`), not measured on disk.

See [how this was verified](../methodology.md) for the method.

<!-- findings: CT_ALLC_003 -->
