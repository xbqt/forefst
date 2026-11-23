# Driver Architecture

The ReFS driver is built in two layers, and only the lower one reads and writes the disk. For a parser this is the
most useful fact about the driver:

- The upper layer implements Windows filesystem semantics: files, names, permissions, encryption.
- The lower layer, **Minstore**, is a transactional key-value store: it stores rows in B+-trees and maps them onto
  clusters, and of these semantics it knows only how file names compare (through the volume's upcase table).

Because the lower layer writes every page, row and B+-tree of the on-disk format, a tool that correctly models
Minstore can read ReFS metadata whichever upper-layer features are switched on. The upper layer still decides what
goes into the rows: for example, the size of a directory's index entry (84 or 72 bytes) is set by the driver that
writes the entry.

This page explains the two layers, the narrow interface between them, and the dispatch path every I/O takes through
both.

## Two layers, one narrow interface

The function names follow the split between the layers. Functions named `Refs*` implement filesystem semantics and reach
the B+-trees through the storage engine's row API: no `Refs*` function of 17134 or 26100.9444 was found handling a
B+-tree page directly. Functions named `Cms*` / `Ms*` implement the storage engine, but the split is not absolute in
that direction: the engine collates file names case-insensitively with the volume's upcase table
(`CmsRulesUNICODE_STRING::CompareKeys`), which is file semantics. The rest crosses the boundary through a small, stable
API:

```text
┌──────────────────────────────────────────────────┐
│ Upper layer: Refs*  (filesystem semantics)        │
│   IRP handling, FCB/VCB lifecycle, security,      │
│   attribute management, Cache Manager integration │
├──────────────────────────────────────────────────┤
│ Narrow Minstore API                               │
│   FindRow / InsertRow / DeleteRow / UpdateRow     │
│     (CmsTable)                                    │
│   FindFirstIndexEntry / FindNextIndexEntry        │
│   CmsStream::LookupAllocation / AddAllocation     │
├──────────────────────────────────────────────────┤
│ Lower layer: Cms*/Ms*  (Minstore engine)          │
│   B+-trees, transactions, allocation, logging,    │
│   checkpointing, streams, containers              │
└──────────────────────────────────────────────────┘
```

The row operations `FindRow`, `InsertRow`, `DeleteRow` and `UpdateRow` belong to the B+-tree base class `CmsTable`
(there is no function named `ModifyRow`); a row's value is also changed through `UpdateDataWithRoot`
(`MsUpdateDataWithRoot`). [Copy-on-write](copy_on_write.md) works a level below: a page whose rows change is written
to new clusters.

Iteration over a tree is `CmsBPlusTable::FindFirstIndexEntry` / `FindNextIndexEntry`, and a file's extents are
resolved through the `CmsStream` extent API (`LookupAllocation` / `AddAllocation` / `DeleteAllocation` /
`DuplicateExtents`).

These methods are the whole interface between the layers: the upper layer decides *what* a row means, the lower layer decides
*how and where* it is stored.

### Why this matters for a parser

Because storage is owned by the lower layer, upper-layer features change how a row is *used*, not how it is
*laid out*. Encryption, snapshots, deduplication, and tiering all add `Refs*` logic above the API, but the
bytes on disk are still ordinary Minstore rows in ordinary B+-tree pages. So a parser
needs to model only Minstore: the [B+-tree node](../structures/btree_node.md) format,
the [container](../structures/container_table.md) translation that turns virtual cluster numbers into disk
positions (see [virtual addressing](virtual_addressing.md)), and the
[checkpoint](../structures/chkp.md) that names the live tree roots. Everything else is the upper layer's
interpretation of the rows.

## The upper layer: Refs*

The upper layer implements the Windows filesystem contract — IRP dispatch, control-block lifecycle (VCB,
FCB, SCB, CCB), security enforcement, attribute interpretation, namespace resolution, and Cache Manager
integration. It is also where the **attribute vocabulary** is defined: the set of typed records ReFS
attaches to a file, registered as **attribute schemas**. The set grew from **12 attribute schemas** in
v3.4 to **16** in v3.14 (18 distinct across all versions): the two legacy schemas (`0x04`/`0x06`) were
retired at v3.14, and six were added across v3.7 and v3.14 — bringing stream snapshots (`$SNAPSHOT`),
extended attributes (`$EA_INFORMATION`/`$EA`, the carrier for WSL's `$LXUID`/`$LXGID`/`$LXMOD`/`$LXDEV`
Linux metadata), USN-journal metadata, and encryption (`$EFS`), plus a revised `$REPARSE_POINT` schema.
The WSL `$LX*` values are EA *entries* inside `$EA`, not standalone attribute schemas.

A new attribute is a new key type in a B+-tree row, and code that never queries for it does not see it. This is how
ReFS adds attributes without changing the row format. (An older driver still refuses a newer format version at mount:
17134 mounts no volume above 3.4.) The full set is catalogued on the [attributes reference](../attributes/README.md).

Between versions the upper layer also changed *style*. v3.4 is purely procedural: a large flat set of free
`Refs*` functions and no named C++ classes. v3.14 reorganised the same work into C++ idioms, introducing
`RefsAttributeManager` for centralised attribute access and struct-scoped helper classes (`_FCB`, `_VCB`,
`_SCB`, `_CCB`, `_LCB`). The refactoring itself did not change the disk format.

## The lower layer: Cms*/Ms* (Minstore)

Minstore is the storage engine: B+-tree primitives, transactions, allocation, logging, checkpointing,
streams, and container management. It is semantically independent of ReFS — the same engine could in
principle back any key-value workload. Its principal classes are below; their method counts per build are on the
[Driver Interface](driver_architecture.md#minstore-class-reference) page.

| Class | Role |
|-------|------|
| `CmsTable` | B+-tree **base** class — owns `FindRow` / `InsertRow` / `DeleteRow` / `UpdateRow` |
| `CmsBPlusTable` | B+-tree layer over `CmsTable` — iteration via `FindFirstIndexEntry` / `FindNextIndexEntry` |
| `CmsFailoverBPlusTable` | Redundant dual-copy trees for the critical Object, Schema, and Container tables |
| `CmsObjectTable` | Master [OID → table](../structures/object_table.md) mapping |
| `CmsVolumeContainer` | [Container Table](../structures/container_table.md) management; rotation/compaction added in v3.14 |
| `CmsAllocator` (v3.14) | Unified [allocator](../structures/allocators.md), replacing the v3.4 `CmsAllocatorBase` + `CmsGlobalAllocator` pair |
| `CmsVolume` | Volume state; also owns the [checkpoint](../structures/chkp.md) operations (`ReadLatestCheckpoint`, `ValidateCheckpointRecord`, `ChooseCheckpointRecord`) — there is no separate `CmsVolumeCheckpoint` class |
| `CmsLogRedoQueue` / `CmsTxMemLog` | Transaction-log I/O (there is no `CmsLogFile` class); see the [MLog](../structures/mlog.md) on-disk format |
| `CmsRestarter` | Crash recovery by replaying the [log](transactions_crash_consistency.md) |

These names are worth knowing because they are the symbols you will see while reverse-engineering a build,
and they map one-to-one onto on-disk structures: `CmsObjectTable` is the Object Table page, `CmsVolumeContainer`
is the Container Table, `CmsLogRedoQueue` produces the `MLog` blocks, and so on.

## Three-tier IRP dispatch

Every I/O Request Packet (IRP) the kernel hands to the driver follows a uniform three-tier path. Knowing the
path tells you which function to look at first when tracing any operation.

**Tier 1 — `RefsFsd*` handlers.** Small entry points that receive the raw IRP, allocate an `IRP_CONTEXT`,
and wrap the work in a `__try`/`__except` guard so that a fault is caught by `RefsExceptionFilter` instead
of becoming a kernel bugcheck. A handful of dedicated `RefsFsd*` handlers sit in the driver's
`MajorFunction[]` array; the less common IRP codes are routed internally by `RefsFsdDispatchSwitch`. v3.14
adds two handlers the v3.4 (17134) driver lacks — `IRP_MJ_QUERY_EA` and `IRP_MJ_SET_EA` — for the WSL
[Extended Attribute](../attributes/EA_INFORMATION.md) support.

**Tier 2 — `RefsCommon*` functions.** The actual filesystem logic, and the largest functions in the driver
by code size. `RefsCommonCreate` opens and creates, `RefsCommonCleanup` runs on last close, `RefsCommonWrite`
is the write path (over 12 KB of code on its own). This tier resolves paths, looks up control blocks,
validates security, and then calls down through the narrow Minstore API.

**Tier 3 — `Cms*`/`Ms*` functions.** The storage engine behind the API: B+-tree lookups, extent mapping,
transactions, and checkpoint commits. Tier 3 *is* the lower (Minstore) layer; tiers 1 and 2 are the upper
(Refs) layer. So the layer boundary and the dispatch boundary coincide exactly at the Minstore API.

### A file creation, end to end

A single `CreateFile` makes all three tiers visible at once, and shows the upper layer building the rows
that the lower layer ultimately stores and commits:

```text
User: CreateFile("E:\folder\newfile.txt", ...)
 │
 ├─ RefsFsdDispatchSwitch → RefsFspDispatch
 │   └─ RefsCommonCreate                          [Tier 2]
 │       ├─ EnsureDirectoryNormalizedName
 │       ├─ RefsAccessCheck
 │       ├─ RefsCreateNewFile
 │       │   ├─ RefsCreateFile
 │       │   │   ├─ MsCreateDurableChildTableFromTemplate   [Tier 3]
 │       │   │   ├─ RefsCreateFileId2
 │       │   │   └─ RefsBindMinstoreTransactionNoRaise
 │       │   ├─ RefsCreateDataAttribute
 │       │   │   ├─ CreateAttribute → MsInsertRow           [Tier 3]
 │       │   │   └─ RefsAllocateNonResidentDataAttribute
 │       │   ├─ RefsComputeStandardInformationFromFcb
 │       │   │   └─ RefsSetStandardInfo → MsUpdateDataWithRoot
 │       │   └─ RefsCreateDirectory
 │       │       └─ CreateOrOpenDirectoryTable
 │       ├─ RefsCreateFcb / RefsCreateScb
 │       └─ If encrypted: RefsEncryptStream
 │
 └─ RefsCheckpointCurrentTransaction
     └─ RefsCommitCurrentTransaction → CommitTopLevelAction
```

Read top to bottom, the upper layer assembles the file's
[$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) and [$DATA](../attributes/DATA.md) records, and each
`Ms*` call writes a row. `CommitTopLevelAction` commits the whole set of changes as one transaction:

- its redo records reach the log ([MLog](../structures/mlog.md)), the last one carrying the commit flag;
- the tree on disk changes when the next [checkpoint](../structures/chkp.md) is flushed;
- a mount replays the transactions logged after the last checkpoint.

That split is the foundation of ReFS's crash consistency, covered under
[transactions and crash consistency](transactions_crash_consistency.md).

## What changed from v3.4 to v3.14

Three consolidations account for most of the structural difference in the code between the two driver generations;
none of them is itself a change of the on-disk format:

1. **Allocator unification.** The v3.4 pair `CmsAllocatorBase` + `CmsGlobalAllocator` became a single
   `CmsAllocator`, and the number of allocation zones grew from 9 to 13 to support tiered storage.

   See the [allocators](../structures/allocators.md) structure page.
2. **Checksum consolidation.** Dozens of per-page-type CRC template specialisations plus the `CmsChecksumNone`
   stub were folded into one polymorphic `CmsChecksum` class computing CRC32-C / CRC64 via ClMul intrinsics,
   and delegating EFS SHA-256 to the imported `cng.sys` / BCrypt provider (`CmsBCrypt`) — **not** to an
   embedded SymCrypt library (that is an Insider-build volume-attestation component, not the production checksum
   backend). The mechanics are on the [checksum architecture](checksum_architecture.md) page.
3. **Attribute centralisation.** The scattered procedural attribute handling of v3.4 became the centralised
   `RefsAttributeManager` class in v3.14.

A common misreading is that the rename or write path "exploded" in size between versions. By function-body
size the individual path functions changed only modestly and in mixed directions: `RefsCommonSetInformation`
grew about 15% while `RefsCommonWrite` actually **shrank** about 11%. The driver binary nearly doubled
overall, but that growth went into *separate* helper functions — the new `RefsAttributeManager` class,
`RefsSetEncryption`, snapshot and compression handlers — not into the core path functions themselves. A
"with-callees" footprint looks much larger because it counts the called subsystem, not the function body;
the two metrics measure different things and must not be confused. The
[version evolution](version_evolution.md) page tracks these changes across the full release timeline.

## Cross-references

- [Bootstrap Chain](bootstrap_chain.md) — the parse order from VBR to any table, which exercises the lower layer end to end
- [Virtual Addressing](virtual_addressing.md) — the VLCN → PLCN translation the Minstore container layer performs
- [Driver Interface](driver_architecture.md) — import tables, embedded libraries, and per-subsystem growth
- [Version Evolution](version_evolution.md) — the per-version structural changes summarised above
- [Windows File Systems](windows_file_systems.md) — where ReFS sits in the Windows I/O / IRP dispatch model
- [Transactions and Crash Consistency](transactions_crash_consistency.md) — how the checkpoint commit at the end of the call chain makes changes durable
- [Copy-on-Write](copy_on_write.md) — how a changed page is written to new clusters
- [B+-Tree Node](../structures/btree_node.md) — the Minstore page format the lower layer reads and writes
- [Object Table](../structures/object_table.md) — the master OID → table map owned by `CmsObjectTable`
- [Container Table](../structures/container_table.md) — the structure `CmsVolumeContainer` manages
- [Checkpoint (CHKP)](../structures/chkp.md) — the root list `CmsVolume` validates and the commit point of every transaction
- [Allocators](../structures/allocators.md) — the three-tier allocation hierarchy unified into `CmsAllocator`
- [MLog](../structures/mlog.md) — the on-disk transaction log produced by `CmsLogRedoQueue`

## Evidence

- **PDB symbols and decompilation** across the v3.4, v3.14 and Insider builds confirm the two-layer model, the
  namespace partition, the Minstore API method ownership, the three-tier dispatch path, and the file-creation call
  chain.
- **Catalog-verified** class and method ownership: `FindRow`/`InsertRow`/`DeleteRow`/`UpdateRow` belong to `CmsTable`
  (no `ModifyRow` in any build), checkpoint ops live on `CmsVolume` with no `CmsVolumeCheckpoint`, and log I/O is
  `CmsLogRedoQueue`/`CmsTxMemLog` with no `CmsLogFile`.
- **On disk:** the B+-tree storage model and container translation are confirmed across the corpus.
- **The attribute-schema growth** (12 → 16, 18 distinct) is confirmed both in the driver and on disk — the driver's
  schema roster and the schema-table row counts measured across the disk corpus.
- **The function-body sizes** compared are 17134 against 26100.8115: `RefsCommonSetInformation` 4,365 → 5,039 bytes,
  `RefsCommonWrite` 14,068 → 12,543 bytes.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

<!-- findings: FN_OPEN_SA_001, GN_ARCH_001, GN_ARCH_002, GN_ARCH_SA_001, GN_FOPS_SA_001, GN_INS_SA_003,
               GN_IRP_SA_001, GN_OOP_SA_001, GN_WSL_SA_001, MD_ATTR_SA_001 -->
