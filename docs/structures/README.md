# ReFS On-Disk Structures — Forensic Reference

A ReFS volume is a **tree of metadata pages**, not a flat table of records like NTFS's `$MFT`.

This page is the analyst's entry point to the byte-level structures:

- what each structure is;
- the fixed sequence a tool must walk before it can read anything (**VBR → SUPB → CHKP → roots → object trees**);
- the catalog of system B+-trees, keyed by their root number / OID / table ID / schema;
- the version-, checksum-, and cluster-size-dependent sizing rules that decide how every field is parsed.

Each structure has a byte-level detail page linked from the catalogs below.

The three references cover different things:

- **structures** (this page): where the bytes are stored and how they are laid out;
- [attributes](../attributes/README.md): the typed metadata inside an object's B+-tree row;
- [concepts](../concepts/README.md): how each mechanism works, and why.

Start here when you need an offset; start with [concepts](../concepts/README.md) when you need the idea.

## 1. What an on-disk structure page documents

Each page documents **one structure**: its byte/offset layout, the meaning of every field, the version
or checksum conditions that change it, and how a parser reaches and reads it.

By convention every page **leads with its layout table** (the offsets), then explains the fields, then records its
evidence at the foot. Driver function names appear where they establish a fact; the per-claim provenance (which images,
which build) lives in the project's `analysis/` tree — see [how this was verified](../methodology.md).

## 2. The bootstrap / parse order (VBR → SUPB → CHKP → roots)

Nothing on a ReFS volume can be read out of order. A tool — and an analyst by hand — must walk this
fixed chain (the conceptual walkthrough is in [Bootstrap Chain](../concepts/bootstrap_chain.md)):

1. **[VBR](vbr.md)** (sector 0) — read the cluster size and the version (and, on volumes formatted at 3.10 or
   later, the checksum selector). The later size rules depend on them and on the checkpoint's own sizes.
2. **[SUPB](supb.md)** (cluster 30) — the fixed volume anchor; points to the two alternating checkpoints.
3. **[CHKP](chkp.md)** — pick the valid checkpoint with the higher clock at +0x60 (on a tie, the first listed); read
   its **13 root pointers**, its page-reference size (+0x5C) and its flags (the direct-vs-indirect root encoding —
   flag `0x0200`).
4. **The system tables** at those roots — above all the **[Container Table](container_table.md)**
   (VLCN → PLCN translation) and the **[Object Table](object_table.md)** (OID → the page where an
   object's tree lives). Most roots are *virtually* addressed and cannot be located until the Container
   Table is loaded; roots **7, 8, 12** are the exception — they use **real (physical) LCNs**, the bootstrap
   exception: roots 7 and 8 hold the translation everything else needs
   ([Virtual Addressing](../concepts/virtual_addressing.md)).
5. **Any object's own B+-tree** — reached by its OID through the Object Table — yields the object's
   [directory entries](directory_entries.md) and its [attributes](../attributes/README.md).

## 3. System-table catalog

### The 13 checkpoint roots

Read from the checkpoint's root-pointer list. Verified against the master root register; failover pairs
are **0/5** (Object), **3/9** (Schema), **7/8** (Container); Block Refcount (#6) is unpaired.

| Table | Root # | Table ID | Schema | Addressing | What it is |
|-------|--------|----------|--------|------------|-----------|
| [Object Table](object_table.md) | #0 / #5 | 0x02 / 0x04 | 0xe030 | Virtual | Master OID → table-location map for every directory and system object (files have no entry) |
| [Allocators](allocators.md) | #1 / #2 / #12 | 0x21 / 0x20 / 0x22 | 0xe010 | Virtual / Virtual / **Real** | Three-tier cluster allocator (Medium / Container / Small) |
| [Schema Table](schema_table.md) | #3 / #9 | 0x01 / 0x06 | 0xe060 | Virtual | Self-describing per-table key-comparison rules |
| [Parent-Child Table](parent_child_table.md) | #4 | 0x03 | 0xe040 | Virtual | Directory hierarchy index (parent → child OIDs) |
| [Block Refcount](block_refcount.md) | #6 | 0x05 | 0xe0b0 | Virtual | Clone and deduplication reference counts |
| [Container Table](container_table.md) | #7 / #8 | 0x0B / 0x0C | 0xe0c0 | **Real** | VLCN → PLCN translation (the virtual container map) |
| [Container Index](container_index.md) | #10 | 0x0E | 0xe100 | Virtual | The rows a compacted or compressed container needs (empty on every volume measured) |
| [Integrity State](integrity_state.md) | #11 | 0x0F | 0xe080 | Virtual | An integrity state per range of clusters (meaning not decoded) |

The Container-Table failover pair is the **set `{0x0B, 0x0C}` at roots {7,8}**, not a fixed
index→table-ID order. Roots 7/8/12 are the **real-LCN bootstrap exception**.

A failover pair is two copies of one table, each checked on its own; neither copy is a primary
([Checkpoint](chkp.md#13-root-table-pointers)).

### OID-addressed system tables

Reached by reserved OID through the Object Table rather than by a checkpoint root.

| Table | OID | Schema | What it is |
|-------|-----|--------|-----------|
| [Security Descriptors](security_descriptors.md) | 0x530 | — (stream, no schema) | Central SecurityId → owner / DACL / SACL store |
| [Volume Information](volume_info.md) | 0x500 / 0x501 | 0x150 | Volume label, timestamps, version flags, the verify block's location |
| [Reparse Points](reparse_points.md) | 0x540 / 0x541 | 0x160 | Global reparse-point index (by tag + file reference) |
| [Upcase Table](upcase_table.md) | 0x07 / 0x08 | 0xe090 | Unicode uppercase map for case-insensitive compare |
| [Trash Table](trash_table.md) | 0x0D | 0xe0d0 | Asynchronous (deferred) deletion queue |

The reserved OIDs below 0x700 — including the **FS Metadata directory (OID 0x520)**, the host of the
Change Journal — are cataloged in [System OIDs](system_oids.md). The Logfile Info table (OIDs 0x09/0x0A,
schema 0xe090, MLog metadata) is covered by [MLog](mlog.md).

The forensic relevance of each table is developed in the concept pages:

- allocation in [Space Allocation](../concepts/allocation_space_mgmt.md);
- identity in [Object IDs](../concepts/object_ids.md), [File IDs](../concepts/file_ids.md) and
  [OID Allocation](../concepts/oid_allocation.md);
- block sharing in [Deduplication](../concepts/deduplication.md);
- per-file checksums in [Integrity Streams](../concepts/integrity_streams.md).

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
| [Reverse Index (Type 0x20)](reverse_index.md) | The per-object FileId-resolution index (FileId → name, or where the record is) |
| [Extent Records](extent_descriptors.md) | The 24-byte extent entries (VCN → VLCN): the leaf rows of the extent-map node inside a file's `$DATA` value |

**Journals and the system-OID hub**
| Structure | What it is |
|-----------|-----------|
| [MLog](mlog.md) | Redo-only metadata write-ahead log (crash consistency) |
| [USN Journal](usn_journal.md) | USN_RECORD_V3 change journal (128-bit file IDs), inside OID 0x520 |
| [System OIDs](system_oids.md) | The catalog of reserved OIDs below 0x700, incl. the FS Metadata directory (0x520) |

## 5. Sizing rules — structure sizes are not constant

A parser must not assume a structure has one fixed size. Sizes vary by **ReFS version**, **metadata checksum
algorithm**, and **cluster size** — so the VBR (version, cluster size), the checkpoint's page-reference size
(CHKP+0x5C) and the CHKP flags must be read *first* ([Version Detection](../concepts/version_detection.md)). An
analyst who skips this misaligns every field that follows.

| Structure | Size depends on | Values |
|-----------|-----------------|--------|
| [Page reference](page_references.md) | where it is stored + checksum | 48 B (CRC64) · 72 B (SHA-256) · 104 B (checkpoint roots, v3.4–3.9) |
| [Container-Table row](container_table.md) | checksum + cluster size | 160 B (default) · 224 B (64 KiB clusters or SHA-256) |
| [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) | version | 116 B (v3.4) · 124 B (v3.7+): the extension from 0x56 differs, and +0x50's meaning changes at v3.10 |
| [Directory entry](directory_entries.md), index-entry form | the driver and format it was written under | 72 B · 84 B |
| SUPB/CHKP **self**-checksum | cluster size | CRC32-C / 4 B (4 KiB) · CRC64 / 8 B (64 KiB) · SHA-256 / 32 B — read the cktype byte ([Checksum Architecture](../concepts/checksum_architecture.md)) |
| Metadata **page** size | cluster size | 16 KiB (4 KiB clusters) · 64 KiB (64 KiB clusters) — not version-dependent ([Cluster and Page Size](../concepts/cluster_page_size.md)) |

## Evidence and verification

Every structure layout here is checked against **two independent sources** wherever both can be read — the
decompiled driver and the raw-disk corpus. The 13-root register, the failover pairs, and the real-LCN bootstrap
exception are documented across these pages, as are the cluster-size-dependent self-checksum and the
`{0x0B,0x0C}`-set root invariant.

See [how this was verified](../methodology.md) for the methodology and the evidence levels.

<!-- findings: FS_CHKP_004, FS_CHKP_RA_015, FS_SUPB_006, GN_PREF_002 -->
