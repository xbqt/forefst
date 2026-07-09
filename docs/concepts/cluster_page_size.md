# Cluster and Page Size

The cluster size is a single number chosen when a ReFS volume is formatted, and it quietly sets the
geometry of almost everything else on disk: how many clusters fit in a container, the stride of the
virtual-to-physical address arithmetic, the size of a Container Table row, and the ceiling on a resident
stream. An analyst who reads it wrong from the [VBR](../structures/vbr.md) will mis-size structures and
mis-translate addresses across the whole volume, so it is one of the first values any parser must fix and
the value almost every other layout decision is keyed to. This page explains the two configurations, how
the cluster size derives the page and container geometry, and the structures that change shape with it.

## Two configurations, fixed at format time

ReFS supports exactly two cluster sizes — **4 KiB** and **64 KiB** — and the choice is permanent. It is
recorded as a sector count at [VBR](../structures/vbr.md) offset `0x24` (sectors-per-cluster), and since
the sector size is always 512 bytes, the cluster size is simply `512 × sectors_per_cluster`:

| Cluster size | Sectors/cluster (VBR 0x24) | CPC | Page size |
|--------------|---------------------------|-----|-----------|
| 4 KiB | 8 | 16,384 | 16 KiB (4 clusters) |
| 64 KiB | 128 | 1,024 | 64 KiB (1 cluster) |

Nothing later changes this. The cluster size is not version-dependent — both 4 KiB and 64 KiB appear on
v3.4 and v3.14 — and it is never modified by an in-place upgrade, so the value read at format time is the
value for the life of the volume. Note that 64 KiB clusters are a relatively recent, less common
configuration; most volumes in the wild are 4 KiB.

## CPC: the number everything is derived from

The volume is carved into fixed **64 MiB containers** — `bytes_per_container` at
[VBR](../structures/vbr.md) offset `0x40` is `0x04000000` and is invariant across every version and
cluster size. Dividing that by the cluster size gives **CPC**, the clusters-per-container count:

```
CPC = bytes_per_container / cluster_size = 64 MiB / cluster_size
    = 16,384  (4 KiB clusters)
    =  1,024  (64 KiB clusters)
```

CPC is the constant that drives the [virtual addressing](virtual_addressing.md) arithmetic. Because a
container is always 64 MiB, a larger cluster means fewer clusters per container, which is why CPC drops
by a factor of 16 when the cluster size grows by 16. CPC is also stored on disk: every
[Container Table](../structures/container_table.md) row carries it at value offset `0x18`, so a parser
can read CPC directly from a container row rather than recomputing it.

## The metadata page

The **page** is the unit in which the B+-tree storage engine reads and writes durable metadata — the
[page header](../structures/page_header.md), the node, and its rows all live inside one page. The page
size follows directly from the cluster size:

- **4 KiB clusters** → page = **16 KiB** = 4 consecutive clusters
- **64 KiB clusters** → page = **64 KiB** = 1 cluster

So a 64 KiB-cluster volume aligns one page to one cluster, while a 4 KiB-cluster volume packs four
clusters into a page. This is purely a function of the cluster size and is identical on v3.4 and v3.14;
the 80-byte [page header](../structures/page_header.md) layout is the same regardless of page size. What
*does* differ between configurations is the [page reference](../structures/page_references.md) format
that a parent uses to point at and checksum a child page — but that is driven by version and checksum
type, not by the page size, and is covered on the
[checksum architecture](checksum_architecture.md) page.

One deliberate exception is worth knowing: the transaction-log block stays **4 KiB** even on a
64 KiB-cluster volume, so the [MLog](../structures/mlog.md) layout does not scale with the cluster size
the way the metadata page does.

## What changes shape with the cluster size

### Address-translation stride

The cluster size sets the shift and mask used to split a VLCN into a container index and an in-container
offset (the full mechanism is on the [virtual addressing](virtual_addressing.md) page):

| Cluster size | Shift (`CPC.bit_length()`) | Mask (`CPC − 1`) |
|--------------|---------------------------|------------------|
| 4 KiB | 15 | 0x3FFF |
| 64 KiB | 11 | 0x3FF |

```
container_index     = vlcn >> shift
offset_in_container = vlcn & mask
physical_LCN        = container_phys_start + offset_in_container
```

The shift is `CPC.bit_length()` (15 for 4 KiB, 11 for 64 KiB), one more than `log2(CPC)`. The driver
stores `log2(CPC)` in the volume structure and adds 1 before shifting in `GetContainerIdFromRealRange`;
the extra bit is safe because `IsValidContainerLcn` guarantees that bit `log2(CPC)` is never set in a
valid container LCN, so the `CPC − 1` mask still captures the whole in-container offset. Using the
unadjusted `log2(CPC)` (14 / 10) misroutes a VLCN to the wrong container, which is why the shift is `CPC.bit_length()` = 15 for 4 KiB clusters (11 for 64 KiB).

### Container Table row size

A [Container Table](../structures/container_table.md) row is **160 bytes** in the common case and grows
to **224 bytes** when the extra integrity buffer is needed. Two independent conditions each force the
larger row, and they do **not** stack:

| Cluster size | Checksum | Row size | Physical-start offset |
|--------------|----------|----------|----------------------|
| 4 KiB | CRC64 or None | 160 | 0x90 |
| 4 KiB | SHA-256 | 224 | 0xD0 |
| 64 KiB | any | 224 | 0xD0 |

The difference is the per-container integrity checksum buffer that starts at row offset `0x50`: 4 slots
(64 bytes) on a 160-byte row, 8 slots (128 bytes) on a 224-byte row. Because the physical-start cluster
sits after that buffer, its offset moves with the row size — but the universal parsing rule absorbs that:
the physical start is always at `value[len − 16]`, and CPC is always at `value + 0x18`, regardless of
which row size is in play. A parser that hard-codes `0x90` will read garbage on a 64 KiB or SHA-256
volume.

### Resident stream ceiling

A small Alternate Data Stream (content below 2 KB) is kept [inline](resident_storage.md) in a B+-tree row;
a larger ADS is converted to non-resident extents at the ~2 KB threshold, like any large stream. So the
inline-ADS ceiling is the 2 KB conversion threshold (well within a single row on any page size), not the
page capacity — the page size instead bounds how much *resident metadata* a directory entry can hold
before the tree splits.

### Self-checksum coverage

The SUPB and CHKP records have no parent to hold their checksum, so each verifies itself over **exactly
one cluster** in `ComputeOrVerifySelfChecksumBlock`. The covered range is therefore 4 KiB or 64 KiB
depending on the cluster size, and the algorithm itself is cluster-size-dependent — another place where
the format-time cluster choice reaches into the integrity machinery. The detail is on the
[checksum architecture](checksum_architecture.md) page.

## Forensic impact

The cluster size is read once and trusted everywhere, so getting it wrong is a single mistake that
silently corrupts many results. It fixes CPC, which fixes the address-translation shift, which decides
whether every VLCN resolves to the right container; it fixes the page size, which decides how many bytes
the parser walks per metadata page; and it fixes the Container Table row size, which decides where the
physical-start cluster lives. The robust discipline is to read sectors-per-cluster from the VBR first,
derive CPC and the page size from it, and never hard-code a row offset — use `value[len − 16]` for the
physical start and `value + 0x18` for CPC so the same code handles both configurations.

## Cross-references

- [VBR](../structures/vbr.md) — `sectors_per_cluster` (0x24) and `bytes_per_container` (0x40), the two fields this page derives everything from
- [Virtual Addressing](virtual_addressing.md) — uses CPC to set the shift/mask that translate a VLCN to a PLCN
- [Container Table](../structures/container_table.md) — the row whose size (160 vs 224) and physical-start offset depend on cluster size and checksum
- [Page Header](../structures/page_header.md) — the 80-byte header is the same regardless of page size
- [Page References](../structures/page_references.md) — the parent-to-child reference that varies by version/checksum, not page size
- [Resident vs Non-Resident Storage](resident_storage.md) — the ADS ceiling is bounded by single-row capacity in one page
- [Checksum Architecture](checksum_architecture.md) — the self-checksum covers exactly one cluster, sized by the cluster choice
- [MLog](../structures/mlog.md) — the log block stays 4 KiB even on 64 KiB-cluster volumes

## Evidence

Sectors-per-cluster at VBR 0x24 (8 / 128) and `bytes_per_container = 0x04000000` at VBR 0x40 are
confirmed in the driver (E2) and on the raw-disk corpus (RD) — findings **FS_VBR_008**, **FS_VBR_011**.
CPC at container-row offset `0x18` and the universal `value[len − 16]` physical-start rule are raw-disk
decoded across the corpus (**CT_CTBL_RA_006**), and the 160-vs-224 row sizing — with 64 KiB clusters and
SHA-256 each independently forcing 224 and not stacking — is RD-confirmed (**CT_CTBL_RA_003**). The
address-translation shift of 15 (4 KiB) / 11 (64 KiB) is confirmed by decompilation of
`GetContainerIdFromRealRange` (with `IsValidContainerLcn` guaranteeing the boundary bit) and on disk
(**CT_CTBL_002**, **CT_CTBL_003**, **CT_CTBL_RA_007**). The inline-ADS
ceiling is the ~2 KB `RefsConvertToNonResident` threshold — a larger ADS is extent-backed — which is
driver- and disk-supported (E2/RD, reconstructed byte-exact across a 256 B → 2 MB ADS size sweep). The single-cluster self-checksum is proven by recomputation across the
corpus in `ComputeOrVerifySelfChecksumBlock`. See [how this was verified](../methodology.md) to trace
these to the exact images and measurements in `analysis/`.
