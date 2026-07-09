# ReFS On-Disk Structures — Forensic Reference

A ReFS volume is a **tree of metadata pages**, not a flat table of records like NTFS's `$MFT`. This page
is the analyst's entry point to the byte-level structures: what each structure is, the fixed sequence a
tool must walk before it can read anything (**VBR → SUPB → CHKP → roots → object trees**), the catalog
of system B+-trees keyed by their root number / OID / table ID / schema, and the version-, checksum-,
and cluster-size-dependent sizing rules that decide how every field is parsed. Each structure has a
byte-level detail page linked from the catalogs below.

The three references answer different questions: **structures** (this page) — *where do the bytes live
and how are they laid out?*; [attributes](../attributes/README.md) — *what typed metadata sits inside an
object's B+-tree row?*; [concepts](../concepts/README.md) — *how and why does the mechanism work?* Start
here when you need an offset; start with [concepts](../concepts/README.md) when you need the idea.

## 1. What an on-disk structure page documents

Each page documents **one structure**: its byte/offset layout, the meaning of every field, the version
or checksum conditions that change it, and how a parser reaches and reads it. By convention every page
**leads with its layout table** (the offsets), then explains the fields, then records its evidence at
the foot. Driver function names appear where they pin a fact; the per-claim provenance (which images,
which build) lives in the project's `analysis/` tree, reachable through each page's finding ID — see
[how this was verified](../methodology.md).

## 2. The bootstrap / parse order (VBR → SUPB → CHKP → roots)

Nothing on a ReFS volume can be read out of order. A tool — and an analyst by hand — must walk this
fixed chain (the conceptual walkthrough is in [Bootstrap Chain](../concepts/bootstrap_chain.md)):

1. **[VBR](vbr.md)** (sector 0) — read the cluster size, version, and checksum algorithm. Every later
   size rule depends on these three fields.
2. **[SUPB](supb.md)** (cluster 30) — the fixed volume anchor; points to the two alternating checkpoints.
3. **[CHKP](chkp.md)** — pick the valid checkpoint with the highest clock; read its **13 root pointers**
   and its flags (checksum mode, and direct-vs-indirect root encoding — flag `0x0200`).
4. **The system tables** at those roots — above all the **[Container Table](container_table.md)**
   (VLCN → PLCN translation) and the **[Object Table](object_table.md)** (OID → the page where an
   object's tree lives). Most roots are *virtually* addressed and cannot be located until the Container
   Table is loaded; roots **7, 8, 12** are the exception — they use **real (physical) LCNs** precisely
   because they bootstrap the translation everything else needs ([Virtual Addressing](../concepts/virtual_addressing.md)).
5. **Any object's own B+-tree** — reached by its OID through the Object Table — yields the object's
   [directory entries](directory_entries.md) and its [attributes](../attributes/README.md).

## 3. System-table catalog

### The 13 checkpoint roots

Read from the checkpoint's root-pointer list. Verified against the master root register; failover pairs
are **0/5** (Object), **3/9** (Schema), **7/8** (Container); Block Refcount (#6) is unpaired.

| Table | Root # | Table ID | Schema | Addressing | What it is |
|-------|--------|----------|--------|------------|-----------|
| [Object Table](object_table.md) | #0 / #5 | 0x02 / 0x04 | 0xe030 | Virtual | Master OID → table-location map for every persistent object |
| [Allocators](allocators.md) | #1 / #2 / #12 | 0x21 / 0x20 / 0x22 | 0xe010 | Virtual / Virtual / **Real** | Three-tier cluster allocator (Medium / Container / Small) |
| [Schema Table](schema_table.md) | #3 / #9 | 0x01 / 0x06 | 0xe060 | Virtual | Self-describing per-table key-comparison rules |
| [Parent-Child Table](parent_child_table.md) | #4 | 0x03 | 0xe040 | Virtual | Directory hierarchy index (parent → child OIDs) |
| [Block Refcount](block_refcount.md) | #6 | 0x05 | 0xe0b0 | Virtual | Shared-block refcounts (snapshots, dedup, clones) |
| [Container Table](container_table.md) | #7 / #8 | 0x0B / 0x0C | 0xe0c0 | **Real** | VLCN → PLCN translation (the virtual container map) |
| [Container Index](container_index.md) | #10 | 0x0E | 0xe100 | Virtual | Alternate Container-Table index by free space (empty on disk) |
| [Integrity State](integrity_state.md) | #11 | 0x0F | 0xe080 | Virtual | Volume-level integrity-stream coverage |

The Container-Table failover pair is the **set `{0x0B, 0x0C}` at roots {7,8}**, not a fixed
index→table-ID order (finding FS_CHKP_RA_015). Roots 7/8/12 are the **real-LCN bootstrap exception**.

### OID-addressed system tables

Reached by reserved OID through the Object Table rather than by a checkpoint root.

| Table | OID | Schema | What it is |
|-------|-----|--------|-----------|
| [Security Descriptors](security_descriptors.md) | 0x530 | — (stream, no schema) | Central SecurityId → owner / DACL / SACL store |
| [Volume Information](volume_info.md) | 0x500 / 0x501 | 0x150 | Volume label, timestamps, version flags, schema count |
| [Reparse Points](reparse_points.md) | 0x540 / 0x541 | 0x160 | Global reparse-point index (by tag + file reference) |
| [Upcase Table](upcase_table.md) | 0x07 / 0x08 | 0xe090 | Unicode uppercase map for case-insensitive compare |
| [Trash Table](trash_table.md) | 0x0D | 0xe0d0 | Asynchronous (deferred) deletion queue |

The reserved OIDs below 0x700 — including the **FS Metadata directory (OID 0x520)**, the host of the
Change Journal — are cataloged in [System OIDs](system_oids.md). The Logfile Info table (OIDs 0x09/0x0A,
schema 0xe090, MLog metadata) is covered by [MLog](mlog.md). The forensic relevance of each table is
developed in the concept pages: allocation in [Space Allocation](../concepts/allocation_space_mgmt.md),
identity in [Object IDs and FileIds](../concepts/object_ids_fileids.md) and
[OID Allocation](../concepts/oid_allocation.md), block sharing in [Deduplication](../concepts/deduplication.md),
and per-file checksums in [Integrity Streams](../concepts/integrity_streams.md).

## 4. On-disk formats and row types

The page/row formats every table is built from — not system tables themselves, but the building blocks.

**Bootstrap anchors**
| Structure | What it is |
|-----------|-----------|
| [VBR](vbr.md) | 512-byte volume boot record at sector 0 — cluster size, version, checksum algorithm |
| [SUPB](supb.md) | Superblock at cluster 30 — anchor pointing to the two checkpoints |
| [CHKP](chkp.md) | Checkpoint — the atomic commit point carrying the 13 root pointers |
| [Page Header](page_header.md) | The common 80-byte header shared by SUPB, CHKP, and every MSB+ page |
| [Page References](page_references.md) | The 104 / 48 / 72-byte parent→child link that chains the tree into a Merkle tree |

**B+-tree building blocks**
| Structure | What it is |
|-----------|-----------|
| [B+-Tree Node (MSB+ page)](btree_node.md) | The "MSB+" metadata page: header + index header + data area + key index |
| [Directory Entries](directory_entries.md) | Type-0x30 rows — resident / non-resident / directory layouts and the sub-record chain |
| [Reverse Index (Type 0x20)](reverse_index.md) | The per-object FileId-resolution index (name ↔ FileId ↔ home directory) |
| [Extent Descriptors](extent_descriptors.md) | Type-0x40 rows — VCN → VLCN extent maps for non-resident content |

**Journals and the system-OID hub**
| Structure | What it is |
|-----------|-----------|
| [MLog](mlog.md) | Redo-only metadata write-ahead log (crash consistency) |
| [USN Journal](usn_journal.md) | USN_RECORD_V3 change journal (128-bit file IDs), inside OID 0x520 |
| [System OIDs](system_oids.md) | The catalog of reserved OIDs below 0x700, incl. the FS Metadata directory (0x520) |

## 5. Sizing rules — structure sizes are not constant

The single most common parser error on ReFS is assuming a structure has one fixed size. Sizes vary by
**ReFS version**, **metadata checksum algorithm**, and **cluster size** — so the VBR (version + checksum)
and the CHKP flags must be read *first* ([Version Detection](../concepts/version_detection.md)). An
analyst who skips this misaligns every field that follows.

| Structure | Size depends on | Values |
|-----------|-----------------|--------|
| [Page reference](page_references.md) | version + checksum | 104 B (v3.4–3.9) · 48 B (v3.10+ CRC64) · 72 B (SHA-256) |
| [Container-Table row](container_table.md) | checksum + cluster size | 160 B (default) · 224 B (64 KiB clusters or SHA-256) |
| [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) | version | 116 B (v3.4) · 124 B (v3.7+); layout from 0x50 rearranged |
| Non-resident [directory entry](directory_entries.md) | version | 72 B (v3.4–3.9) · 84 B (v3.10+) |
| SUPB/CHKP **self**-checksum | cluster size | CRC32-C / 4 B (4 KiB) · CRC64 / 8 B (64 KiB) · SHA-256 / 32 B — read the cktype byte ([Checksum Architecture](../concepts/checksum_architecture.md)) |
| Metadata **page** size | cluster size | 16 KiB (4 KiB clusters) · 64 KiB (64 KiB clusters) — not version-dependent ([Cluster and Page Size](../concepts/cluster_page_size.md)) |

## Evidence and verification

Every structure layout here is confirmed by **two independent sources** — the decompiled driver (`E2`)
and the raw-disk corpus (`RD`). The 13-root register, the
failover pairs, and the real-LCN bootstrap exception are documented across these pages; the cluster-size-dependent
self-checksum is finding FS_SUPB_006, FS_CHKP_004, GN_PREF_002; the `{0x0B,0x0C}`-set root invariant is FS_CHKP_RA_015. See
[how this was verified](../methodology.md) for the methodology, the evidence levels, and how to trace any
fact to the exact images and measurements in the project's `analysis/` tree.
