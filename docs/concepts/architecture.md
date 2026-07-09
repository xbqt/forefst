# ReFS Driver Architecture

The single most useful fact for anyone parsing ReFS is that the driver is built in two layers, and only
the lower one ever touches the disk. The upper layer speaks Windows filesystem semantics — files, names,
permissions, encryption. The lower layer, **Minstore**, is a general-purpose transactional key-value
store that knows nothing about any of that; it stores rows in B+-trees and maps them onto clusters. Because
the on-disk format is produced *entirely* by the lower layer, a tool that correctly models Minstore can
read ReFS metadata regardless of which upper-layer features are switched on. This page explains the two
layers, the narrow interface between them, and the dispatch path every I/O takes through both.

## Two layers, one narrow interface

The boundary between the layers is not just a design diagram — it is enforced in the code as a strict
namespace partition. Functions named `Refs*` implement filesystem semantics and **never** manipulate a
B+-tree page directly. Functions named `Cms*` / `Ms*` implement the storage engine and **never** interpret
file semantics (names, timestamps, permissions). Everything that crosses the boundary goes through a small,
stable API:

```
┌──────────────────────────────────────────────────┐
│ Upper layer: Refs*  (filesystem semantics)        │
│   IRP handling, FCB/VCB lifecycle, security,      │
│   attribute management, Cache Manager integration │
├──────────────────────────────────────────────────┤
│ Narrow Minstore API                               │
│   FindRow / InsertRow / DeleteRow  (CmsTable)     │
│   FindFirstIndexEntry / FindNextIndexEntry        │
│   CmsStream::LookupAllocation / AddAllocation     │
├──────────────────────────────────────────────────┤
│ Lower layer: Cms*/Ms*  (Minstore engine)          │
│   B+-trees, transactions, allocation, logging,    │
│   checkpointing, streams, containers              │
└──────────────────────────────────────────────────┘
```

The row operations `FindRow`, `InsertRow`, and `DeleteRow` belong to the B+-tree base class `CmsTable`.
There is deliberately **no `ModifyRow`** — a row is changed by deleting and re-inserting it, which is what
makes [copy-on-write](copy_on_write.md) the natural update model. Iteration over a tree is
`CmsBPlusTable::FindFirstIndexEntry` / `FindNextIndexEntry`, and a file's extents are resolved through the
`CmsStream` extent API (`LookupAllocation` / `AddAllocation` / `DeleteAllocation` / `DuplicateExtents`).
That handful of methods is the whole contract: the upper layer decides *what* a row means, the lower layer
decides *how and where* it is stored.

### Why this matters for a parser

Because storage is owned by the lower layer, upper-layer features change how a row is *used*, not how it is
*laid out*. Encryption, snapshots, deduplication, and tiering all add `Refs*` logic above the API, but the
bytes on disk are still ordinary Minstore rows in ordinary B+-tree pages. The practical consequence is that
the parsing problem reduces to modelling Minstore: the [B+-tree node](../structures/btree_node.md) format,
the [container](../structures/container_table.md) translation that turns virtual cluster numbers into disk
positions (see [virtual addressing](virtual_addressing.md)), and the
[checkpoint](../structures/chkp.md) that names the live tree roots. Everything else is interpretation layered
on top.

## The upper layer: Refs*

The upper layer implements the Windows filesystem contract — IRP dispatch, control-block lifecycle (VCB,
FCB, SCB, CCB), security enforcement, attribute interpretation, namespace resolution, and Cache Manager
integration. It is also where the **attribute vocabulary** is defined: the set of typed records ReFS
attaches to a file, registered as **attribute schemas**. The set grew from **12 attribute schemas** in
v3.4 to **16** in v3.14 (18 distinct across all versions): the two legacy schemas (`0x04`/`0x06`) were
retired at v3.14, and six were added across v3.7 and v3.14 — bringing stream snapshots (`$SNAPSHOT`),
extended attributes (`$EA_INFORMATION`/`$EA`, the carrier for WSL's `$LXUID`/`$LXGID`/`$LXMOD`/`$LXDEV`
Linux metadata), USN-journal metadata, and encryption (`$EFS`), plus a revised `$REPARSE_POINT` schema.
The WSL `$LX*` values are EA *entries* inside `$EA`, not standalone attribute schemas. A new attribute is
just a new key type in a B+-tree row, invisible to code that never queries for it, which is how ReFS
extends its format without breaking older readers. The full set is catalogued on the
[attributes reference](../attributes/README.md).

Between versions the upper layer also changed *style*. v3.4 is purely procedural: a large flat set of free
`Refs*` functions and no named C++ classes. v3.14 reorganised the same work into C++ idioms, introducing
`RefsAttributeManager` for centralised attribute access and struct-scoped helper classes (`_FCB`, `_VCB`,
`_SCB`, `_CCB`, `_LCB`). The disk format did not move; the code that produces it was refactored.

## The lower layer: Cms*/Ms* (Minstore)

Minstore is the storage engine: B+-tree primitives, transactions, allocation, logging, checkpointing,
streams, and container management. It is semantically independent of ReFS — the same engine could in
principle back any key-value workload. Its principal classes (with method counts per version, v3.4 / v3.14
/ Insider) are:

| Class | Role |
|-------|------|
| `CmsTable` | B+-tree **base** class — owns `FindRow` / `InsertRow` / `DeleteRow` (no `ModifyRow`) |
| `CmsBPlusTable` | B+-tree layer over `CmsTable` — iteration via `FindFirstIndexEntry` / `FindNextIndexEntry` |
| `CmsFailoverBPlusTable` | Redundant dual-copy trees for the critical Object, Schema, and Container tables |
| `CmsObjectTable` | Master [OID → table](../structures/object_table.md) mapping |
| `CmsVolumeContainer` | [Container Table](../structures/container_table.md) management; rotation/compaction added in v3.14 |
| `CmsAllocator` (v3.14) | Unified [allocator](../structures/allocators.md), replacing the v3.4 `CmsAllocatorBase` + `CmsGlobalAllocator` pair |
| `CmsVolume` | Volume state; also owns the [checkpoint](../structures/chkp.md) operations (`ValidateCheckpointRecord` / `ChooseCheckpointRecord`) — there is no separate `CmsVolumeCheckpoint` class |
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
adds two handlers over v3.4 — `IRP_MJ_QUERY_EA` and `IRP_MJ_SET_EA` — for the WSL
[Extended Attribute](../attributes/EA_INFORMATION.md) support that arrived with that version.

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

```
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
[$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) and [$DATA](../attributes/DATA.md) records;
each `Ms*` call writes a row; and the whole set of changes is made durable as one unit when
`CommitTopLevelAction` writes the next [checkpoint](../structures/chkp.md). Nothing is visible on disk until
that commit — which is the foundation of ReFS's crash consistency, covered under
[transactions and crash consistency](transactions_crash_consistency.md).

## What changed from v3.4 to v3.14

Three consolidations account for most of the structural difference between the two driver generations,
and none of them altered the on-disk format:

1. **Allocator unification.** The v3.4 pair `CmsAllocatorBase` + `CmsGlobalAllocator` became a single
   `CmsAllocator`, and the number of allocation zones grew from 9 to 13 to support tiered storage. See the
   [allocators](../structures/allocators.md) structure page.
2. **Checksum consolidation.** Dozens of per-page-type CRC template specialisations plus the `CmsChecksumNone`
   stub were folded into one polymorphic `CmsChecksum` class computing CRC32-C / CRC64 via ClMul intrinsics,
   and delegating EFS SHA-256 to the imported `cng.sys` / BCrypt provider (`CmsBCrypt`) — **not** to an
   embedded SymCrypt library (that is an Insider-build early-boot/attestation component, not the production
   checksum backend). The mechanics are on the [checksum architecture](checksum_architecture.md) page.
3. **Attribute centralisation.** The scattered procedural attribute handling of v3.4 became the centralised
   `RefsAttributeManager` class in v3.14.

A common misreading is that the rename or write path "exploded" in size between versions. By function-body
size the individual path functions changed only modestly and in mixed directions: `RefsCommonSetInformation`
grew about 15% while `RefsCommonWrite` actually **shrank** about 11%. The driver binary nearly doubled
overall, but that growth went into *separate* helper functions — the new `RefsAttributeManager` class,
`RefsSetEncryption`, snapshot and compression handlers — not into the core path functions themselves. A
"with-callees" footprint looks much larger because it counts the called subsystem, not the function body;
the two metrics tell different stories, and conflating them is a known pitfall. The
[version evolution](version_evolution.md) page tracks these changes across the full release timeline.

## Cross-references

- [Bootstrap Chain](bootstrap_chain.md) — the parse order from VBR to any table, which exercises the lower layer end to end
- [Virtual Addressing](virtual_addressing.md) — the VLCN → PLCN translation the Minstore container layer performs
- [Driver Interface](driver_architecture.md) — import tables, embedded libraries, and per-subsystem growth
- [Version Evolution](version_evolution.md) — the per-version structural changes summarised above
- [Windows File Systems](windows_file_systems.md) — where ReFS sits in the Windows I/O / IRP dispatch model
- [Transactions and Crash Consistency](transactions_crash_consistency.md) — how the checkpoint commit at the end of the call chain makes changes durable
- [Copy-on-Write](copy_on_write.md) — why the absence of `ModifyRow` makes CoW the natural update model
- [B+-Tree Node](../structures/btree_node.md) — the Minstore page format the lower layer reads and writes
- [Object Table](../structures/object_table.md) — the master OID → table map owned by `CmsObjectTable`
- [Container Table](../structures/container_table.md) — the structure `CmsVolumeContainer` manages
- [Checkpoint (CHKP)](../structures/chkp.md) — the root list `CmsVolume` validates and the commit point of every transaction
- [Allocators](../structures/allocators.md) — the three-tier allocation hierarchy unified into `CmsAllocator`
- [MLog](../structures/mlog.md) — the on-disk transaction log produced by `CmsLogRedoQueue`

## Evidence

The two-layer model, the namespace partition, the Minstore API method ownership, the three-tier dispatch
path, and the file-creation call chain are all confirmed by PDB symbols and decompilation across the v3.4,
v3.14, and Insider builds (E2). Class and method ownership — including that `FindRow`/`InsertRow`/`DeleteRow`
belong to `CmsTable` with no `ModifyRow`, that checkpoint ops live on `CmsVolume` with no `CmsVolumeCheckpoint`,
and that log I/O is `CmsLogRedoQueue`/`CmsTxMemLog` with no `CmsLogFile` — is catalog-verified. The B+-tree
storage model and container translation are additionally raw-disk confirmed across the corpus (RD). The
attribute-schema growth (12 → 16, 18 distinct) is E2/RD — the driver's schema roster and the schema-table
row counts measured across the disk corpus. Findings:
**GN_ARCH_001** (Minstore B+-tree engine), **GN_ARCH_002** (copy-on-write update policy). See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
