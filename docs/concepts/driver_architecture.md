# Driver Interface

The on-disk structures only tell half the story; the other half is the code that writes them. This page is
the static-analysis companion to the [Driver Architecture](architecture.md) model — it reads the `refs.sys`
binary across three builds (Win10 v3.4, Win11 v3.14, Insider) and reports what the imports, embedded
libraries, class tables, and IRP dispatch reveal about *which features a given driver can produce*. For an
analyst this matters because the driver is the ground truth: a feature visible on disk has a code path that
created it, and the presence or absence of that code path tells you what a volume could and could not
contain. Function counts are non-external (defined) functions only, and every class name, method, and count
below is verified against the function catalog.

## What the binary reveals across builds

The driver grows from 3,959 functions in v3.4 to 5,818 in v3.14 — a ~47% increase — while the count
of functions that carry a PDB-resolved name stays nearly flat (2,553 in v3.4 vs 2,565 in v3.14), so PDB
coverage falls from 64.5% to 44.1%. That combination is the signature of **refactoring plus new
subsystems**: many old functions were replaced rather than extended, and the added bulk is whole new
feature areas, not incremental edits to the storage core. The Insider build adds a further 612 functions
on top of v3.14 (6,430 total; 2,878 PDB-named, 44.8% coverage). The practical reading is that v3.4 structural knowledge remains a valid
baseline (the engine is stable) but each build can mint metadata the previous one could not.

## Imports: the driver's external dependencies

The import table is the cleanest external evidence of what a driver build can do, because a feature that
needs a kernel service must import the API that provides it. The v3.4 driver imports 415 functions from
just two libraries — `ntoskrnl.exe` (core kernel services) and `HAL.dll` (one performance-counter call).
The v3.14 driver imports 566 (+36%) from seven libraries — adding five — and each addition maps to a
specific new capability:

| Library | Purpose | Capability it gates |
|---------|---------|---------------------|
| `ntoskrnl.exe` | Core kernel services | (baseline) |
| `cng.sys` | `BCrypt*` cryptographic APIs | the EFS encryption engine — see [$EFS](../attributes/EFS.md) |
| `ext-ms-win-ntos-ksr-*` | Kernel Soft Restart | memory persistence across soft reboots (server availability) |
| `msrpc.sys` | Kernel-mode RPC | clustered-storage communication |
| `ext-ms-win-crypto-xbox-*` | Hardware-accelerated crypto | checksum / encryption acceleration |
| `HAL.dll` | Performance counter | (baseline) |
| `ext-ms-win-ntos-clipsp-*` | Client license policy | edition gating |

The `cng.sys` import is the most forensically useful single fact here: it is the driver-level proof that the
build supports EFS, because ReFS does not implement the RSA/AES crypto itself — it delegates the SHA-256
metadata and key operations to the `cng.sys` `BCrypt*` provider (the in-driver wrapper is `CmsBCrypt`). A
v3.4 driver, lacking that import, cannot encrypt a stream.

## Embedded libraries: compression evidence inside the binary

The v3.14 driver also embeds two complete compression-library implementations directly in the binary, which
accounts for part of its size growth and replaces the v3.4 LZX/XPRESS wrappers:

| Library | Functions | Replaces |
|---------|-----------|----------|
| ZSTD | 281 | v3.4 LZX/XPRESS compression wrappers |
| LZ4 | 15 | v3.4 LZX/XPRESS compression wrappers |

These embedded codecs are the driver-level counterpart to the [compression](compression.md) features visible
on disk: if the binary contains a ZSTD decompressor, the volume can hold ZSTD-compressed extents. Note that
the v3.14 *checksum* consolidation does **not** rely on an embedded crypto library — CRC32-C/CRC64 are
computed in-driver via ClMul intrinsics and XXH64 (the `CmsChecksum` class), with SHA-256 delegated to
`cng.sys`/`CmsBCrypt`. The embedded SymCrypt library is an Insider-build addition tied to early-boot and
attestation, not a v3.14 component.

## Where the growth landed

Counting functions per subsystem shows the engine is mature and the new code is concentrated in feature
areas, not the storage core:

| Subsystem | v3.4 | v3.14 | Change |
|-----------|------|-------|--------|
| Encryption (EFS) | 2 | 182 | +9,000% |
| Heat engine (tiering) | 2 | 55 | +2,650% |
| Snapshots | 6 | 24 | +300% |
| Streams | 56 | 105 | +88% |
| Containers | 101 | 184 | +82% |
| Allocator | 100 | 168 | +68% |
| Volume management | 125 | 184 | +47% |
| Logging | 95 | 112 | +18% |
| Deduplication | 0 | 7 | New |
| B+-tree (core) | 240 | 252 | +5% |
| Integrity / Checkpoint / Transactions | stable | stable | <10% |

The storage core — the [B+-tree node](../structures/btree_node.md) layer, integrity, checkpoint, and
transactions — changed by less than 10%, which is *why* the on-disk layout of those structures is stable
across versions. The explosive growth is in encryption (2 to 182 functions) and the
[heat engine](tiering.md) (2 to 55), confirming that EFS and tiering are the headline v3.14 features and
that their on-disk artifacts (the [$EFS](../attributes/EFS.md) attribute, the heat-tracking tables) appear
only from the builds that carry the code.

## How requests enter: the IRP handler set

Every file operation reaches the driver as an I/O Request Packet (IRP), tagged with a *major function code*.
The set of codes a driver routes is itself a capability fingerprint. v3.4 handles 18 major functions; v3.14
adds two — `IRP_MJ_QUERY_EA` and `IRP_MJ_SET_EA` — and those two are the driver-level signature of
**WSL Extended Attribute support**: the code that reads and writes the [`$LXUID`/`$LXGID`/`$LXMOD`/`$LXDEV`](wsl_metadata.md)
attributes. A volume whose driver lacks the EA handlers cannot have produced WSL metadata.

The codes that are resolved to a single named handler in the PDB are the two control-path entries; the rest
are dispatched internally through the lower layers (see
[Architecture §Three-tier IRP dispatch](architecture.md#three-tier-irp-dispatch)) and have no single named
entry point:

| IRP code | Handler | Purpose |
|----------|---------|---------|
| `IRP_MJ_CREATE` | `RefsCommonCreate` | Open file/directory |
| `IRP_MJ_CLOSE` | — | Close handle |
| `IRP_MJ_READ` | — | Read file data |
| `IRP_MJ_WRITE` | — | Write file data |
| `IRP_MJ_CLEANUP` | `RefsCommonCleanup` | Cleanup on last close |
| `IRP_MJ_FILE_SYSTEM_CONTROL` | — | FSCTL commands |
| `IRP_MJ_SET_INFORMATION` | — | Set file attributes |
| `IRP_MJ_QUERY_INFORMATION` | — | Query file attributes |

One forensic caveat: the Fast I/O path lets some cached operations bypass IRP creation entirely, so an
IRP-level trace is not a complete record of activity — a read served from cache may leave no IRP at all.

## Minstore class reference

The lower-layer [Minstore engine](architecture.md#the-lower-layer-cmsms-minstore) is organized as a set of
C++ classes whose method counts can be read straight from the symbol tables. The tables below give method
counts per class for **Win10 v3.4 / Win11 v3.14 RTM / Insider**; every class name, method ownership, and
count is verified against the function catalog.

### B+-tree infrastructure

| Class | v3.4 | v3.14 | Insider | Role |
|-------|------|-------|---------|------|
| `CmsTable` | 16 | 17 | 14 | B+-tree **base** class — owns the row operations `FindRow` / `InsertRow` / `DeleteRow` (there is no `ModifyRow` in any build) |
| `CmsBPlusTable` | 186 | 160 | 166 | B+-tree layer over `CmsTable` — adds iteration: `FindFirstIndexEntry` / `FindNextIndexEntry` |
| `CmsTableCursor` | 2 | 2 | 2 | Cursor / iterator |
| `CmsFailoverBPlusTable` | 47 | 27 | 27 | Redundant B+-tree for dual-copy tables (see [redundancy](redundancy.md)) |
| `CmsObjectTable` | 31 | 28 | 29 | Master OID-to-table mapping — the [Object Table](../structures/object_table.md) |
| `CmsSchemaTable` | 7 | 6 | 5 | Table [schema](../structures/schema_table.md) definitions + key comparison |
| `CmsDurableLog` | 43 | 40 | 40 | Persistent B+-tree management |

The split is worth internalising: the row primitives (`FindRow` / `InsertRow` / `DeleteRow`) live on the
base class `CmsTable`, and `CmsBPlusTable` layers the tree-walk iteration on top. This is the code that
reads and writes every [B+-tree node](../structures/btree_node.md) on the volume.

### Container and allocation classes

| Class | v3.4 | v3.14 | Insider | Role |
|-------|------|-------|---------|------|
| `CmsVolumeContainer` | 72 | 130 | 133 | [Container Table](../structures/container_table.md) management — the VLCN→PLCN map |
| `CmsContainerRangeMap` | 26 | 22 | 23 | Container range operations |
| `CmsAllocatorBase` | 42 | — | — | Base allocator (v3.4 only) |
| `CmsGlobalAllocator` | 43 | — | — | Global allocator (v3.4 only) |
| `CmsAllocator` | — | 106 | 105 | Unified allocator (v3.14+; replaces Base + Global) |
| `TmsAllocatorEngine` | — | 6 | 6 | Allocation-strategy specialisations (6 strategy templates) |

`CmsVolumeContainer` is the class that performs the [virtual-to-physical translation](virtual_addressing.md)
this corpus depends on. The allocator unification — two v3.4 classes collapsed into one `CmsAllocator` — is
documented from the on-disk side on the [Allocators](../structures/allocators.md) page.

### Checksum classes

| Class | v3.4 | v3.14 | Insider | Role |
|-------|------|-------|---------|------|
| `CmsChecksumNone` | 8 | — | — | Stub: `VerifyChecksum` always returns TRUE (v3.4) |
| `CmsCrc32` | 47 | — | — | CRC32-C computation templates (v3.4) |
| `CmsCrc64` | 49 | — | — | CRC64 computation templates (v3.4); custom poly, **not** ECMA-182 |
| `CmsChecksum` | 4 | 11 | 13 | Unified polymorphic checksum class (v3.14+; CRC32-C/CRC64 via ClMul + XXH64) |

v3.14 consolidated dozens of per-page-type checksum templates plus the `CmsChecksumNone` stubs into one
polymorphic `CmsChecksum` class. The existence of `CmsChecksumNone` in v3.4 — a `VerifyChecksum` that always
returns TRUE — is the code-level explanation for why a v3.4 volume formatted without integrity does not
detect metadata corruption. The full integrity picture is on
[checksum architecture](checksum_architecture.md).

### Volume and checkpoint classes

| Class | v3.4 | v3.14 | Insider | Role |
|-------|------|-------|---------|------|
| `CmsVolume` | 143 | 180 | 179 | Volume-level state; also owns the checkpoint ops (`ValidateCheckpointRecord` / `ChooseCheckpointRecord`) — there is **no** separate `CmsVolumeCheckpoint` class |
| `CmsRestarter` | 29 | 28 | 28 | Crash recovery via log replay |
| `CmsTransactionContext` | 29 | 27 | 26 | Transaction boundaries |
| `CmsLogRedoQueue` | 33 | 39 | 37 | Transaction-log redo I/O |
| `CmsTxMemLog` | 6 | 7 | 7 | In-memory transaction log |

The checkpoint validation that selects which [checkpoint](../structures/chkp.md) to trust at mount lives on
`CmsVolume`, and crash recovery (`CmsRestarter` replaying the log) plus the redo-queue classes
(`CmsLogRedoQueue` / `CmsTxMemLog`) are the engine behind the [transaction / crash-consistency](transactions_crash_consistency.md)
model. The log-record layout they produce is on the [MLog](../structures/mlog.md) page.

## Configuration registers on disk

Several on-disk fields act as runtime configuration registers — the driver reads them at mount to decide
which structures and behaviors are live. They are the bridge between the code above and the bytes on the
platter:

| Field | Offset | Role | Detail |
|-------|--------|------|--------|
| CHKP flags | CHKP + 0x78 | Feature-activation register | Decoded bits select which structures/behaviors are live |
| VBR checksum selector | VBR + 0x2A | Metadata verification mode | 0x0000 = None (CRC32-C only), 0x0002 = CRC64, 0x0004 = SHA-256 |
| VBR volume flags | VBR + 0x2C | Format-time configuration | 0x06 (Win10) vs 0x66 (Win11 native) |
| CHKP page ref size | CHKP + 0x5C | Page-reference format selector | 104, 48, or 72 bytes |

The VBR format-time fields (0x2A, 0x2C, 0x48) are **never** modified during an upgrade — which is what makes
them reliable [version-detection](version_detection.md) markers even on a volume that has been upgraded in
place. Full decode tables are on the [VBR](../structures/vbr.md) and [Checkpoint](../structures/chkp.md)
pages.

## Insider-only subsystems

The Insider build adds subsystems that are genuinely absent from production Windows 11 24H2, and they signal
the direction of ReFS development:

| Subsystem | Marker | Purpose |
|-----------|--------|---------|
| Boot-volume support | ~50+ functions | Lets ReFS host the system volume and paging file — the first bootable ReFS. |
| Volume attestation | `CmsVolumeAttestation` (40 methods, **0 in v3.14 RTM**) | Binds the volume identity to a TPM-backed measurement to detect offline tampering (`Attest*` methods). |

Two classes that *look* Insider-only are not, and getting this right matters for dating a volume:
`CmsRollbackProtection` (NVRAM checkpoint-clock rollback detection) is present in **v3.14 RTM (14 methods)**
and Insider (13), and `CmsVolumeHeatEngine` is **v3.14 RTM (24)** / Insider (20). Neither is exclusive to the
Insider build. The embedded cryptographic libraries the Insider subsystems rely on (SymCrypt, MinCrypt) are
present in the Insider binary.

## Cross-references

- [Driver Architecture](architecture.md) — the two-layer model and three-tier IRP dispatch this page measures
- [Version Evolution](version_evolution.md) — the per-version structural changes the subsystem growth produces
- [Checksum Architecture](checksum_architecture.md) — how the `CmsChecksum` consolidation appears on disk
- [Allocators](../structures/allocators.md) — the on-disk side of the `CmsAllocatorBase` → `CmsAllocator` unification
- [MLog](../structures/mlog.md) — the log records produced by `CmsLogRedoQueue` / `CmsTxMemLog` / `CmsRestarter`
- [$EFS](../attributes/EFS.md) — the encryption metadata enabled by the `cng.sys` import
- [WSL / Linux Metadata](wsl_metadata.md) — the EA attributes gated by the `IRP_MJ_*_EA` handlers
- [VBR](../structures/vbr.md) and [Checkpoint](../structures/chkp.md) — the configuration registers the driver reads at mount

## Evidence

The binary inventory, import tables, embedded-library set, subsystem counts, IRP handler set, Minstore class
tables, and Insider subsystems are all from static analysis of the three `refs.sys` builds with full PDB
symbols (E2). The Minstore class names, method ownership, and per-build method counts were
rebuilt and catalog-verified against `function_catalog.csv` (audit 3); the named handlers
(`RefsCommonCreate`, `RefsCommonCleanup`), the row primitives (`FindRow` / `InsertRow` / `DeleteRow`), the
checkpoint ops (`ValidateCheckpointRecord` / `ChooseCheckpointRecord`), and the checksum stub
(`CmsChecksumNone::VerifyChecksum`) are all catalog-verified. The configuration-register offsets are
raw-disk corroborated (RD). The "Insider-only" corrections to `CmsRollbackProtection` and
`CmsVolumeHeatEngine` are catalog-verified (audit 3). See [how this was verified](../methodology.md) to
trace these to the exact builds and measurements in `analysis/`.
