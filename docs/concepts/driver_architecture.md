# Driver Interface

The on-disk structures are one source of evidence; the code that writes them is the other.

This page is the static-analysis companion to the [Driver Architecture](architecture.md) model. It reads the
`refs.sys` binary across three builds (Win10 17134 for v3.4, Win11 26100.8115 for v3.14, Insider 29574) and reports
what the imports, embedded libraries, class tables, and IRP dispatch reveal about *which features a given driver can
produce*.

For an analyst this matters because a feature visible on disk was created by a code path in the driver, so the
presence or absence of that code path tells you what a volume could and could not contain.

Function counts are non-external (defined) functions only, and every class name, method, and count below is verified
against the function catalog.

## What the binary reveals across builds

The driver grows from 3,959 functions in v3.4 (17134) to 5,818 in v3.14 (26100.8115), about 47 % more, and the
Insider build 29574 has 6,430.

Almost every function carries its own name from Microsoft's symbol file: 3,723 of the 17134 functions and 5,519 of
the 26100.8115 ones; the rest are unnamed (`FUN_*`, about 5 % on both) or thunks. The names quoted on this site are
those names, not guesses.

So what is known about the v3.4 structures remains a baseline, but each build can write metadata the previous one
could not.

## Imports: the driver's external dependencies

The import table is the cleanest external evidence of what a driver build can do, because a feature that needs a kernel
service must import the API that provides it. The v3.4 driver imports 415 functions from just two libraries —
`ntoskrnl.exe` (core kernel services) and `HAL.dll` (one performance-counter call). The 26100.8115 driver imports 566
(+36%) from seven libraries — adding five (26100.9444: 567; Insider 29574 and 29683: 564 and 572, from six) — and each
addition maps to a specific new capability, read from its callers on 26100.9444:

| Library | Purpose | Capability it gates |
|---------|---------|---------------------|
| `ntoskrnl.exe` | Core kernel services | (baseline) |
| `cng.sys` | `BCrypt*` cryptographic APIs | the EFS encryption engine — see [$EFS](../attributes/EFS.md) |
| `ext-ms-win-ntos-ksr-*` | Kernel Soft Restart | keeps each mounted volume's container-table state (not on an SMR disk) in memory across a soft restart, for the next mount to reuse |
| `msrpc.sys` | Kernel-mode RPC | EFS's calls to its user-mode service (decrypt a file key, generate a key) |
| `ext-ms-win-crypto-xbox-*` | Xbox crypto provider | an alternative EFS XTS-AES key and decryption provider, used when it reports itself supported (it never encrypts) |
| `HAL.dll` | Performance counter | (baseline) |
| `ext-ms-win-ntos-clipsp-*` | Client license policy | the license callbacks EFS uses for file-license headers and keys |

The `cng.sys` import shows that the
build supports EFS, because ReFS does not implement the RSA/AES crypto itself — it delegates the SHA-256
metadata and key operations to the `cng.sys` `BCrypt*` provider (the in-driver wrapper is `CmsBCrypt`). A
v3.4 driver, lacking that import, cannot encrypt a stream.

## Embedded libraries: compression evidence inside the binary

The v3.14 driver also embeds two complete compression-library implementations directly in the binary, which
accounts for part of its size growth. The v3.4 driver has other codec classes instead (`CmsCompressionLZNT1`,
`CmsCompressionLZX`, `CmsCompressionXPRESS`, `CmsCompressionXPRESS_HUFF`) and neither library:

| Library | Functions | In the v3.4 driver |
|---------|-----------|--------------------|
| ZSTD | 281 | absent (0 functions) |
| LZ4 | 15 | absent (0 functions) |

These embedded codecs are the driver-level counterpart to the [compression](compression.md) features visible
on disk: if the binary contains a ZSTD decompressor, the volume can hold ZSTD-compressed containers.

Note that the v3.14 *checksum* consolidation does **not** rely on an embedded crypto library — CRC32-C/CRC64 are
computed in-driver via ClMul intrinsics and XXH64 (the `CmsChecksum` class), with SHA-256 delegated to
`cng.sys`/`CmsBCrypt`. The embedded SymCrypt library (153 functions) is in the Insider builds read (29574, 29659,
29683) and in no 17134 or 26100 build read: on 29574 it computes the volume attestation's HMAC-SHA256 of checkpoint and
log records and checks the PKCS#7 / RSA signatures of attestation certificates.

## Where the growth landed

Counted in the project's function catalogue (17134: 3,929 functions; 26100.8115: 5,787), the growth includes new
feature code and embedded libraries:

| Code (rule) | 17134 | 26100.8115 |
|-------------|-------|------------|
| EFS (names starting `Efs` or `Edp`) | 0 | 157 |
| ZSTD and LZ4 libraries (names starting `ZSTD`, `LZ4`) | 0 | 296 |
| Heat engine and its lists (names containing "heat") | 2 | 83 |
| Deduplication (names containing "dedup") | 0 | 8 |
| Table sets (`CmsTableSetBase`, `TmsTableSet`) | 0 | 89 |
| B+-tree class `CmsBPlusTable` | 186 | 160 |
| Restart (`CmsRestarter`) | 29 | 28 |

Per-class counts also move when classes are merged or renamed: `CmsCrc32` and `CmsCrc64` (96 functions on 17134) are
gone on 26100.8115, where `CmsChecksum` does their work, and `CmsAllocator` (1 → 106) took over `CmsGlobalAllocator`
and `CmsAllocatorBase` (85 on 17134). So the counts show where named code is, not how much an on-disk structure
changed. Two of the additions have on-disk artifacts, which appear only on volumes written by the builds that carry the code:
EFS (the [$EFS](../attributes/EFS.md) attribute) and the heat engine (the
[heat engine table](../structures/system_oids.md#heat-engine-table-oid-0x30)).

## How requests enter: the IRP handler set

Every file operation reaches the driver as an I/O Request Packet (IRP), tagged with a *major function code*. The set of
codes a driver routes shows what the driver can do. v3.4 handles 18 major functions; v3.14 adds two,
`IRP_MJ_QUERY_EA` and `IRP_MJ_SET_EA`, and those two show **WSL Extended Attribute
support**: the code that reads and writes the [`$LXUID`/`$LXGID`/`$LXMOD`/`$LXDEV`](wsl_metadata.md) attributes. A
volume whose driver lacks the EA handlers cannot have produced WSL metadata.

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
counts per class for **Win10 v3.4 (17134) / Win11 v3.14 (26100.8115) / Insider (29574)**; every class name, method
ownership, and count is verified against the function catalog.

### B+-tree infrastructure

| Class | v3.4 | v3.14 | Insider | Role |
|-------|------|-------|---------|------|
| `CmsTable` | 16 | 17 | 14 | B+-tree **base** class — owns the row operations `FindRow` / `InsertRow` / `DeleteRow` / `UpdateRow` (there is no `ModifyRow` in any build) |
| `CmsBPlusTable` | 186 | 160 | 166 | B+-tree layer over `CmsTable` — adds iteration: `FindFirstIndexEntry` / `FindNextIndexEntry` |
| `CmsTableCursor` | 2 | 2 | 2 | Cursor / iterator |
| `CmsFailoverBPlusTable` | 47 | 27 | 27 | Redundant B+-tree for dual-copy tables (see [redundancy](redundancy.md)) |
| `CmsObjectTable` | 31 | 28 | 29 | Master OID-to-table mapping — the [Object Table](../structures/object_table.md) |
| `CmsSchemaTable` | 7 | 6 | 5 | Table [schema](../structures/schema_table.md) definitions + key comparison |
| `CmsDurableLog` | 43 | 40 | 40 | Persistent B+-tree management |

The row primitives (`FindRow` / `InsertRow` / `DeleteRow` / `UpdateRow`) live on the
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
| `CmsCrc64` | 49 | — | — | CRC64 computation templates (v3.4); CRC-64/NVME, **not** ECMA-182 |
| `CmsChecksum` | 4 | 11 | 13 | Unified polymorphic checksum class (v3.14+; CRC32-C/CRC64 via ClMul + XXH64) |

v3.14 consolidated dozens of per-page-type checksum templates plus the `CmsChecksumNone` stubs into one
polymorphic `CmsChecksum` class. In v3.4, `CmsChecksumNone` — a `VerifyChecksum` that always returns TRUE — is
the type-0 entry of the stream checksum table; metadata pages are checked by the CRC64 or CRC32-C entry of the
metadata checksum table that their page reference names. All the checksums are described on
[checksum architecture](checksum_architecture.md).

### Volume and checkpoint classes

| Class | v3.4 | v3.14 | Insider | Role |
|-------|------|-------|---------|------|
| `CmsVolume` | 143 | 180 | 179 | Volume-level state; also owns the checkpoint ops (`ReadLatestCheckpoint`, `ValidateCheckpointRecord`, `ChooseCheckpointRecord`) — there is **no** separate `CmsVolumeCheckpoint` class |
| `CmsRestarter` | 29 | 28 | 28 | Crash recovery via log replay |
| `CmsTransactionContext` | 29 | 27 | 26 | Transaction boundaries |
| `CmsLogRedoQueue` | 33 | 39 | 37 | Transaction-log redo I/O |
| `CmsTxMemLog` | 6 | 7 | 7 | In-memory transaction log |

The checkpoint validation that selects which [checkpoint](../structures/chkp.md) to trust at mount lives on `CmsVolume`
(the choice is made in `ReadLatestCheckpoint`), and crash recovery (`CmsRestarter` replaying the log) plus the
redo-queue classes (`CmsLogRedoQueue` / `CmsTxMemLog`) are the engine behind the
[transaction / crash-consistency](transactions_crash_consistency.md) model. The log-record layout they produce is on the
[MLog](../structures/mlog.md) page.

## Configuration registers on disk

Several on-disk fields act as runtime configuration registers — the driver reads them at mount to decide
which structures and behaviors are live. They connect the code above to the bytes on
disk:

| Field | Offset | Role | Detail |
|-------|--------|------|--------|
| CHKP flags | CHKP + 0x78 | Feature-activation register | Decoded bits select which structures/behaviors are live |
| VBR checksum algorithm selector | VBR + 0x2A | Metadata checksum type | read only when the volume flags carry 0x40 (0x0002 = CRC64, 0x0004 = SHA-256); without 0x40 the volume uses CRC64; 17134 never reads it |
| VBR volume flags | VBR + 0x2C | Run-time flags, two format bits | written at run time (a writable mount sets 0x02, among others); its bits 0x20 and 0x40 come from the format; 0x06 (Win10) vs 0x66 (Win11 native) on the volumes measured |
| CHKP page reference size | CHKP + 0x5C | Size of the checkpoint's root page references | 104, 48, or 72 bytes |

Of the VBR fields, the checksum selector (0x2A) and the Extended GUID (0x48) are format-time: no boot-sector write
path of refs.sys 26100.9444 assigns them (`refsutil fixboot` rewrites both), and they kept their values across the two
upgrades measured (3.4 to 3.14 and 3.9 to 3.14) — which is what makes them
[version-detection](version_detection.md) markers on a volume upgraded in place.

The volume flags (0x2C) are written at run time; their format bits 0x20 and 0x40 kept their values across the same
two upgrades. Full decode tables are on the [VBR](../structures/vbr.md) and [Checkpoint](../structures/chkp.md)
pages.

## Insider-only subsystems

The Insider build adds subsystems that are genuinely absent from production Windows 11 24H2, and they signal
the direction of ReFS development:

| Subsystem | Marker | Purpose |
|-----------|--------|---------|
| Boot-volume support | ~50+ functions | Lets ReFS host the system volume — the first bootable ReFS (the test corpus holds the C: drive of an Insider 29574 machine). |
| Volume attestation | `CmsVolumeAttestation` (40 methods, **0 in 26100.8115**) | Binds the volume identity to a TPM-backed measurement to detect offline tampering (`Attest*` methods). |

Two classes that *look* Insider-only are not, and getting this right matters for dating a volume:

- `CmsRollbackProtection` (NVRAM checkpoint-clock rollback detection) is present in **26100.8115 (14 methods)** and
  Insider (13);
- `CmsVolumeHeatEngine` is in **26100.8115 (24)** and Insider (20).

Neither is exclusive to the Insider build. The embedded cryptographic libraries the Insider subsystems rely on
(SymCrypt, MinCrypt) are present in the Insider binary.

## Cross-references

- [Driver Evolution](driver_evolution.md) — which driver function changes a file's placement or its data residency, per build
- [Driver Architecture](architecture.md) — the two-layer model and three-tier IRP dispatch this page measures
- [Version Evolution](version_evolution.md) — the per-version structural changes the subsystem growth produces
- [Checksum Architecture](checksum_architecture.md) — how the `CmsChecksum` consolidation appears on disk
- [Allocators](../structures/allocators.md) — the on-disk side of the `CmsAllocatorBase` → `CmsAllocator` unification
- [MLog](../structures/mlog.md) — the log records produced by `CmsLogRedoQueue` / `CmsTxMemLog` / `CmsRestarter`
- [$EFS](../attributes/EFS.md) — the encryption metadata enabled by the `cng.sys` import
- [WSL / Linux Metadata](wsl_metadata.md) — the EA attributes gated by the `IRP_MJ_*_EA` handlers
- [VBR](../structures/vbr.md) and [Checkpoint](../structures/chkp.md) — the configuration registers the driver reads at mount

## Evidence

- **Static analysis** of the three `refs.sys` builds with their PDB symbols gives the binary inventory, import tables,
  embedded-library set, subsystem counts, IRP handler set, Minstore class tables, and Insider subsystems.
- **Catalog-verified** against `function_catalog.csv`: the Minstore class names, method ownership and per-build method
  counts; the named handlers (`RefsCommonCreate`, `RefsCommonCleanup`); the row primitives (`FindRow` / `InsertRow` /
  `DeleteRow` / `UpdateRow`); the checkpoint ops (`ReadLatestCheckpoint`, `ValidateCheckpointRecord`,
  `ChooseCheckpointRecord`); `CmsChecksumNone::VerifyChecksum`; and the presence of `CmsRollbackProtection` and
  `CmsVolumeHeatEngine` outside the Insider build.
- **On disk:** the configuration-register offsets are corroborated across the corpus.

See [how this was verified](../methodology.md) to
trace these to the exact builds and measurements in `analysis/`.

<!-- findings: FS_VBR_RA_011, GN_ARCH_006, GN_ARCH_SA_002, GN_BIN_SA_001, GN_HEAT_SA_001, GN_IMP_SA_001,
               GN_INS_SA_002, GN_KSR_SA_001 -->
