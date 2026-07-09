# Container Index

The Container Index (root #10, table ID 0x0E, schema 0xe100) is an alternate index over the
[Container Table](container_table.md), keyed by allocation state and free space rather than by
sequential container ID. It lets the allocator answer free-space queries without scanning the entire
Container Table. On a crash-consistent image it is an **empty B+-tree**: everything it would hold is
derivable from the Container Table, and it is likely populated only transiently during allocation
(unverified — no populated state was ever observed in the corpus) — so at checkpoint time there are no
rows to read.

## Identity and observed state

| Property | Value |
|----------|-------|
| Root number | #10 (in the CHKP root-pointer list; it has no Object-Table OID) |
| Table ID | 0x0E |
| Schema | 0xe100 |
| Addressing | Virtual (VLCN → PLCN via the Container Table) |
| Failover pair | None |
| Data rows | 0 on every analysed image (valid MSB+ root page, no leaf rows) |
| Version presence | All versions, v3.4 → Insider |

Because the table is empty on every checkpoint-consistent image, ReFS publishes **no key/value row
layout** for it — there is nothing on disk to decode. The root page survives a version upgrade in place
(its root LCN is unchanged across a v3.4 → v3.14 upgrade).

## Purpose

The [Container Table](container_table.md) (roots #7/#8) is keyed by sequential container ID. The
Container Index complements it with lookup **by state** — free, partially used, metadata, and so on —
for the allocator subsystem. It appears to be a performance/index structure: everything it would hold is
recomputable from the Container Table, which is consistent with a quiescent on-disk image showing it
empty. Treat a populated Container Index as an in-flight allocation artifact, not a persistent forensic
record.

## Cross-references

- [Container Table](container_table.md) — the authoritative VLCN→PLCN map this index is derived from
- [Allocators](allocators.md) — the three-tier allocator subsystem that consumes the index
- [Checkpoint (CHKP)](chkp.md) — root #10 of the root-pointer list
- [Schema Table](schema_table.md) — schema 0xe100

## Evidence

Identity (root #10 / table ID 0x0E / schema 0xe100 / virtual addressing / no failover pair) and the
empty-on-disk result are raw-disk verified across the corpus (RD) and corroborated in the driver (E2):
`CmsVolumeContainer::InitializeIndex` (with the salvage-path twin `CsalvVolumeContainer::InitializeIndex`)
builds the index, and the `CmsContainerRangeMap` class manages the in-memory container ranges it is
derived from; the table name also appears as a binary string literal (E1). The 0-row state was
re-confirmed by reading CHKP root #10 directly on v3.4 and v3.14 images. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
