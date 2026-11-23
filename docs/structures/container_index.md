# Container Index

The Container Index (root #10, table ID 0x0E, schema 0xe100) holds, per container, what its
[Container Table](container_table.md) row does not: a compacted container's allocation bitmap and a compressed
container's compression headers.

Its key is {u64 container id, u32 index, u32 type}:

- type 3 is a container's initial allocation bitmap;
- type 7 its compression headers.

Like the other tables it is journaled: inserting a container's compression headers is logged as redo opcode 0x1A
(its writer, `InsertContainerCompressionHeaders`, read on 26100.9818 and Insider 29683).

It is empty on every corpus volume measured, which matches the Container Table: no corpus container is compacted or
compressed (no row carries flag 0x0008 or 0x0002).

Driver: a static reading of refs.sys 26100.9444; the key and type 7 read twice, type 3 once.

## Identity and observed state

| Property | Value |
|----------|-------|
| Root number | #10 (in the CHKP root-pointer list; it has no Object-Table OID) |
| Table ID | 0x0E |
| Schema | 0xe100 |
| Addressing | Virtual (VLCN → PLCN via the Container Table) |
| Failover pair | None |
| Data rows | 0 on every analysed image (valid MSB+ root page, no leaf rows) |
| Version presence | Every format, v3.4 to v3.14 |

No corpus volume holds a row, so the key above is the driver's alone, and the values of types 3 and 7 are not decoded
here.

The root page survives a version upgrade in place (its root LCN is unchanged across the v3.4 → v3.14 upgrade
measured).

## Purpose

A Container Table row locates a container. The Container Index holds what some containers need beyond it:

- for a compacted container (row flag 0x0008) refs.sys finds its clusters through the Container Index's type-3
  bitmap: a cluster's place is the count of the bits set before it;
- a compressed container (flag 0x0002) is read through its type-7 headers;
- a container that needs a row the index does not have is flagged 0x0080 | 0x0800, and refs.sys refuses a container
  with 0x0800.

A populated Container Index is therefore evidence of compaction or compression, which no corpus volume shows.

## Cross-references

- [Container Table](container_table.md) — the VLCN→PLCN map; its row flags say when a container needs this index
- [Allocators](allocators.md) — the three-tier allocator subsystem
- [Checkpoint (CHKP)](chkp.md) — root #10 of the root-pointer list
- [Schema Table](schema_table.md) — schema 0xe100

## Evidence

Identity (root #10 / table ID 0x0E / schema 0xe100 / virtual addressing / no failover pair) and the
empty-on-disk result are measured on the disk across the corpus and corroborated in the driver:
`CmsVolumeContainer::InitializeIndex` (with the salvage-path twin `CsalvVolumeContainer::InitializeIndex`)
builds the index; the table name also appears as a binary string literal.

The 0-row state was re-confirmed by reading CHKP root #10 directly on v3.4 and v3.14 images. The key, the row types
and the compacted-container lookup are a static reading of refs.sys (scopes above).

See [how this was verified](../methodology.md) for the method.

<!-- findings: CT_CNTX_001, FS_CHKP_019, GN_CROT_SA_001 -->
