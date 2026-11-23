# Cluster and Page Size

The cluster size is a single number chosen when a ReFS volume is formatted, and it sets the
layout of almost everything else on disk:

- how many clusters fit in a container;
- the stride of the virtual-to-physical address arithmetic;
- the size of a metadata page;
- the size of a Container Table row (with the checksum type).

An analyst who reads it wrong from the [VBR](../structures/vbr.md) will mis-size structures and mis-translate
addresses across the whole volume, so it is one of the first values any parser must fix and the value almost every
other layout decision is keyed to.

This page explains the two configurations, how the cluster size derives the page and container geometry, and the
structures that change shape with it.

## Two configurations, fixed at format time

Every volume measured has one of two cluster sizes — **4 KiB** or **64 KiB** — and the choice is permanent. It is
recorded as a sector count at [VBR](../structures/vbr.md) offset `0x24` (sectors-per-cluster), and the
cluster size is `bytes_per_sector × sectors_per_cluster` — both read from the VBR, `0x20` and `0x24`.

Most volumes measured here report **512** bytes per sector, but **not all**: two lab volumes are real
4Kn volumes reporting **4096 × 1**, verified against the operator's own SHA-256 inventory (every file). So the product
must be taken from the two fields and never shortcut to `512 × sectors_per_cluster` — the same 4 KiB cluster is
reached as `512 × 8` on a 512e volume and as `4096 × 1` on a 4Kn one:

| Cluster size | Sectors/cluster (VBR 0x24) | CPC | Page size |
|--------------|---------------------------|-----|-----------|
| 4 KiB | 8 (1 on a 4Kn volume) | 16,384 | 16 KiB (4 clusters) |
| 64 KiB | 128 | 1,024 | 64 KiB (1 cluster) |

Nothing later changes this. The cluster size is not version-dependent — both 4 KiB and 64 KiB appear on
v3.4 and v3.14 — and it is never modified by an in-place upgrade, so the value read at format time is the
value for the life of the volume. Most volumes measured here have 4 KiB clusters.

## CPC: clusters per container

The volume is divided into fixed **64 MiB containers** — `bytes_per_container` at
[VBR](../structures/vbr.md) offset `0x40` is `0x04000000` and is invariant across every version and
cluster size. Dividing that by the cluster size gives **CPC**, the clusters-per-container count:

```text
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
the 80-byte [page header](../structures/page_header.md) layout is the same regardless of page size.

The checkpoint is the exception: its record is one cluster on every geometry. On a 4 KiB-cluster volume the
allocator reserves a page's four clusters for it and the record uses the first.

What *does* differ between configurations is the [page reference](../structures/page_references.md) format
that a parent uses to point at and checksum a child page — but that is driven by version and checksum
type, not by the page size, and is covered on the
[checksum architecture](checksum_architecture.md) page.

One exception: the transaction-log block stays **4 KiB** even on a
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

```text
container_index     = vlcn >> shift
offset_in_container = vlcn & mask
physical_LCN        = container_phys_start + offset_in_container
```

The shift is `CPC.bit_length()` (15 for 4 KiB, 11 for 64 KiB), one more than `log2(CPC)`. The driver
stores `log2(CPC)` in the volume structure and adds 1 before shifting in `GetContainerIdFromRealRange`;
the extra bit is safe because `IsValidContainerLcn` guarantees that bit `log2(CPC)` is never set in a
valid container LCN, so the `CPC − 1` mask still captures the whole in-container offset. Using the
unadjusted `log2(CPC)` (14 / 10) misroutes a VLCN to the wrong container.

### Container Table row size

A [Container Table](../structures/container_table.md) row is **160 bytes** in the common case and grows
to **224 bytes** on a 64 KiB-cluster or a SHA-256 volume. Each of the two conditions forces the larger row on its
own, and they do **not** stack:

| Cluster size | Checksum | Row size | Physical-start offset |
|--------------|----------|----------|----------------------|
| 4 KiB | CRC64 (or a selector of 0) | 160 | 0x90 |
| 4 KiB | SHA-256 | 224 | 0xD0 |
| 64 KiB | any | 224 | 0xD0 |

The difference is the run of 16-byte units that starts at row offset `0x50`, before the mapping range: 4 units
(64 bytes) on a 160-byte row, 8 units (128 bytes) on a 224-byte row; their content is not decoded. Because the
physical-start cluster sits after them, its offset moves with the row size — but one parsing rule works for both row
sizes:
the physical start is always at `value[len − 16]`, and CPC is always at `value + 0x18`, regardless of
which row size is in play. A parser that hard-codes `0x90` reads the wrong bytes on a 64 KiB or SHA-256
volume.

### Inline stream ceiling

The cluster size does not set the inline ceiling; the volume's format does.

- On format 3.11+, a small Alternate Data Stream (content below 2 KiB) is kept [inline](placement_and_residency.md) in a
  B+-tree row; a larger one is extent-backed from the 2 KiB threshold up, like main `$DATA`. Below 2 KiB a stream
  can still be in extents when a conversion trigger fired (a pre-allocation, a snapshot, encryption, ...).
- On formats below 3.11, a named stream stays inline, and the driver refuses an inline write past 128 KiB; main
  `$DATA` is always in extents there.

So the inline-ADS ceiling is the 2 KiB conversion threshold on 3.11+ (well within a single row on any page size),
not the page capacity. A record with many attributes is not capped by the page either: its attributes move to a child
page ([Directory Entries](../structures/directory_entries.md#when-the-sub-record-table-moves-into-a-child-node)).

### Self-checksum coverage

The SUPB and CHKP records have no parent to hold their checksum, so each verifies itself over **exactly
one cluster** in `ComputeOrVerifySelfChecksumBlock`. The covered range is therefore 4 KiB or 64 KiB
depending on the cluster size, and the algorithm itself is cluster-size-dependent — so the
format-time cluster choice also affects the self-checksum. The detail is on the
[checksum architecture](checksum_architecture.md) page.

## Forensic impact

The cluster size is read once and used everywhere, so one wrong value silently corrupts many
results. It fixes CPC, which fixes the address-translation shift, which decides
whether every VLCN resolves to the right container; it fixes the page size, which decides how many bytes
the parser walks per metadata page; and it fixes the Container Table row size, which decides where the
physical-start cluster lives. Read sectors-per-cluster from the VBR first,
derive CPC and the page size from it, and never hard-code a row offset: use `value[len − 16]` for the
physical start and `value + 0x18` for CPC so the same code handles both configurations.

## Cross-references

- [VBR](../structures/vbr.md) — `sectors_per_cluster` (0x24) and `bytes_per_container` (0x40), the two fields this page derives everything from
- [Virtual Addressing](virtual_addressing.md) — uses CPC to set the shift/mask that translate a VLCN to a PLCN
- [Container Table](../structures/container_table.md) — the row whose size (160 vs 224) and physical-start offset depend on cluster size and checksum
- [Page Header](../structures/page_header.md) — the 80-byte header is the same regardless of page size
- [Page References](../structures/page_references.md) — the parent-to-child reference that varies by version/checksum, not page size
- [Record placement and data residency](placement_and_residency.md) — the inline ceiling: 2 KiB on format 3.11+, the older formats' rule
- [Checksum Architecture](checksum_architecture.md) — the self-checksum covers exactly one cluster, sized by the cluster choice
- [MLog](../structures/mlog.md) — the log block stays 4 KiB even on 64 KiB-cluster volumes

## Evidence

Sectors-per-cluster at VBR 0x24 and `bytes_per_container = 0x04000000` at VBR 0x40 are confirmed in the driver
and on the raw-disk corpus. CPC at container-row offset `0x18` and the universal `value[len − 16]` physical-start
rule are raw-disk decoded across the corpus, and the 160-vs-224 row sizing — with 64 KiB clusters and SHA-256 each
independently forcing 224 and not stacking — is confirmed on disk.

The address-translation shift of 15 (4 KiB) / 11 (64 KiB) is confirmed by decompilation of
`GetContainerIdFromRealRange` (with `IsValidContainerLcn` guaranteeing the boundary bit; 17134, 26100.8115 to .9444
and Insider 29574) and on disk.

The inline ceiling is the driver's format gate (`RefsAddAllocationForResidentWrite`: 2 KiB from format 3.11, the
128 KiB error branch below it) and the conversion-trigger callers of `RefsConvertToNonResident`, read on 26100.8115
(the symbol is present in 26100.8521 and Insider 29574 too, and absent from 17134). On disk, over 8,238 named streams on 57 images, no inline stream
reaches 2,048 bytes and the extent-backed ones of 2 KiB or more start at exactly 2,048; 161 of 161 extent-backed ADS
of a 2 KiB – 2 MB size sweep were reconstructed byte-exact (a 1,920-byte one inline, a 2,048-byte one
extent-backed). The 128 KiB branch is not exercised on disk: every named stream found on the format ≤ 3.10 volumes
is 47 bytes or less.

The single-cluster self-checksum is proven by recomputation across the corpus in
`ComputeOrVerifySelfChecksumBlock`.

The counts behind the text: the 4Kn volumes are `lab314_4kn` and `lab314_4kn_step2`, 626 of 626 files verified
against the operator's SHA-256 inventory; 7 of the 124 volumes whose boot sector reads have 64 KiB clusters.

See [how this was verified](../methodology.md) for the method.

<!-- findings: CT_CTBL_002, CT_CTBL_003, CT_CTBL_RA_003, CT_CTBL_RA_006, CT_CTBL_RA_007, FS_VBR_008,
               FS_VBR_011 -->
