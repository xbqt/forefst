# Windows File Systems

Before a single ReFS byte is ever read off disk, the volume has already passed through half a dozen
Windows kernel layers, and an analyst who does not know that path can misread what `refs.sys` actually
controls and what the kernel does *around* it. ReFS is not a self-contained program — it is a
**file-system driver (FSD)** plugged into the Windows I/O model, sharing the same request packets,
caching, security checks, and mount machinery as NTFS. This page traces the path a file operation takes
from an application call down to the disk, and pins down exactly where `refs.sys` enters that path — the
boundary between behavior the kernel owns (and you cannot blame on ReFS) and behavior the ReFS driver
owns (which the rest of these pages decode). The internal model of `refs.sys` itself — its two layers and
the dispatch within them — is on the [Driver Architecture](architecture.md) page; this page is the layer
*above* it.

## Two privilege levels

Windows splits execution into two privilege levels, and the split decides where a file operation can and
cannot be tampered with:

- **User mode** — applications and services run with restricted privileges. They never touch a kernel
  object directly; they hold **handles** to them.
- **Kernel mode** — the OS core and device drivers manage memory, hardware, and privileged requests. This
  is where `refs.sys` lives.

A file operation *begins* in user mode but is always *serviced* in kernel mode. The forensic consequence
is that no user-mode tool — including the high-level Windows file APIs and PowerShell — can reach a field
that the FSD chooses not to expose, which is precisely why some ReFS metadata (the metadata-change time,
the on-disk attribute layout) is invisible to ordinary tools and only recoverable by reading the disk.

## The path of a file operation

A `CreateFile` call descends a fixed chain of components, and each one is a place a request can be
observed, redirected, or denied:

1. The **application** calls `CreateFileW` through the Win32 subsystem DLLs.
2. The **subsystem DLLs** (e.g. `Kernel32.dll`) translate it to the Native API call `NtCreateFile` in
   `ntdll.dll`.
3. **`ntdll.dll`** executes the `syscall` instruction, crossing into kernel mode.
4. The **System Service Dispatcher** routes to the kernel-mode `NtCreateFile`.
5. The **Object Manager** resolves the pathname to the mounted volume; the **I/O Manager** creates a file
   object and builds an `IRP_MJ_CREATE` request packet.
6. The **Filter Manager** and any registered **minifilters** may intercept and inspect the request.
7. The **file-system driver** (`ntfs.sys` or `refs.sys`) performs format-specific pathname resolution.
   This is where ReFS first sees the request.
8. The **Security Reference Monitor** checks the caller's token against the target's security descriptor.
9. The FSD completes processing and associates the file object with an **FCB** (File Control Block).
10. A **handle** is returned to the application.

The single most useful boundary to fix in your mind is step 7: everything above it is generic Windows
plumbing identical for every file system, and everything that depends on *ReFS structure* happens at or
below it, inside `refs.sys`. The chain that the ReFS driver then runs to locate its own on-disk roots is
the [bootstrap chain](bootstrap_chain.md).

## The components that matter forensically

### I/O Manager and the I/O Request Packet (IRP)

The **I/O Manager** is the generic Executive subsystem that turns open/read/write calls into a uniform
driver-facing model. It is *not* a file system — it builds an **IRP** (I/O Request Packet) describing the
operation, its target, parameters, and status, and routes it to the right driver stack. Every operation
ReFS performs arrives as an IRP tagged with a **major function code**, and that set of codes is the
contract between the kernel and the FSD:

| Code | Operation |
|------|-----------|
| `IRP_MJ_CREATE` | Open or create a file/directory |
| `IRP_MJ_READ` | Read file data |
| `IRP_MJ_WRITE` | Write file data |
| `IRP_MJ_QUERY_INFORMATION` | Query file metadata |
| `IRP_MJ_SET_INFORMATION` | Modify file metadata |
| `IRP_MJ_DIRECTORY_CONTROL` | List directory contents |
| `IRP_MJ_FILE_SYSTEM_CONTROL` | FSCTL commands |
| `IRP_MJ_CLEANUP` | Last handle closed |
| `IRP_MJ_CLOSE` | Last reference released |

The IRP code is the seam between this page and the driver internals: each code enters `refs.sys` through
its three-tier dispatch and is handled by a `RefsFsd*` entry point, then a `RefsCommon*` worker — for
example `IRP_MJ_CREATE` reaches `RefsCommonCreate` and `IRP_MJ_CLEANUP` reaches `RefsCommonCleanup`. Which
codes a build routes is itself a capability fingerprint (the two EA codes are the WSL-metadata signature),
a point developed on the [Driver Interface](driver_architecture.md) and
[Architecture §Three-tier IRP dispatch](architecture.md#three-tier-irp-dispatch) pages. One caveat for
any IRP-level reasoning: the Fast I/O path lets some cached operations bypass IRP creation entirely, so an
IRP trace is **not** a complete record of activity — a read served from cache may leave no IRP at all.

### Object Manager and handles

The **Object Manager** owns kernel objects — files, devices, events, processes — and the handle namespace
over them. User-mode code never manipulates a kernel object directly; it receives a **handle**, a
per-process token carrying the access rights that were granted at open time. This indirection is why a
file's identity in the kernel (its FCB) is decoupled from any name a user used to reach it.

### Security Reference Monitor (SRM)

The **SRM** enforces access control at open time by comparing the caller's security token against the
target's security descriptor. Every FSD — ReFS included — relies on the SRM rather than implementing its
own authorization logic, which is why ReFS stores only the descriptor *blob* (centralised in OID 0x530)
and a per-file SecurityId, and leaves the actual permission check to the kernel. The descriptor format is
the standard `SECURITY_DESCRIPTOR` documented on the
[Security Descriptors](../structures/security_descriptors.md) page; the SecurityId that keys it sits in
[`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md).

### Filter Manager and minifilters

The **Filter Manager** (`fltmgr.sys`) hosts **minifilter** drivers that observe or modify file-system
operations without implementing a file system. Anti-virus, backup, encryption, and synchronisation
products attach here. For an analyst this is a source of *non-ReFS* artifacts on a ReFS volume — a
minifilter can stamp its own metadata or reparse tags — and a reason an operation may be altered before
ReFS ever sees it.

### Cache Manager and the I/O paths after open

Once a handle exists, reads and writes take one of three paths, and the path determines what reaches the
disk and when:

- **Cached I/O** (the default) — the **Cache Manager** maps file contents into the system cache; reads are
  served from cache and dirty pages are flushed later by the lazy writer (write-back caching). Because the
  flush is deferred, a crash can lose recently written data that the application already believed
  committed — a window ReFS narrows with its transaction model but does not eliminate at the cache layer.
- **Mapped I/O** — applications map file sections into their address space and the **Memory Manager**
  resolves page faults through the same cache/FSD path.
- **Non-cached I/O** — with `FILE_FLAG_NO_BUFFERING` the cache is bypassed entirely;
  `FILE_FLAG_WRITE_THROUGH` forces an immediate disk commit.

ReFS cooperates with the Cache Manager and Memory Manager through the same common interfaces NTFS uses, so
the *caching behavior* is shared; what differs is only how the FSD lays the flushed bytes onto the volume.

## Volume mounting: how a volume becomes a ReFS volume

A file-system driver cannot resolve any path until Windows has bound the volume to it. Mounting is the
step that makes `refs.sys` the owner of a given volume:

1. A volume becomes available.
2. File-system **recognizers** examine it for a known format.
3. If a recognizer claims it, the FSD mounts the volume and builds a **Volume Control Block (VCB)** — its
   private in-memory state for that volume.
4. The I/O Manager records the binding through a **Volume Parameter Block (VPB)**.
5. Subsequent IRPs route to that FSD's stack.

If *no* file system recognizes the volume, Windows assigns the **RAW** file-system driver, which offers
sector-level access only — which is exactly the state an analyst works in when reading a ReFS image on a
host whose `refs.sys` cannot mount it. ReFS recognition turns on the on-disk format markers the
[VBR](../structures/vbr.md) carries (`RefsIsBootSectorOurs` performs the signature and version check;
`InitializeVcbFromBootSector` extracts the geometry into the VCB), and a version mismatch — a v3.4 driver
meeting a native v3.14 volume — is one way mounting fails. The on-disk side of what the driver reads at
mount is the [bootstrap chain](bootstrap_chain.md), and the format markers that gate recognition are the
[version-detection](version_detection.md) fields.

## In-memory control blocks

While mounted, the ReFS driver maintains a hierarchy of **runtime** structures — these are kernel objects,
not on-disk data, and they vanish when the volume unmounts:

| Structure | Scope |
|-----------|-------|
| **VCB** (Volume Control Block) | per mounted volume |
| **FCB** (File Control Block) | per file/directory, linked to the file object |
| **SCB** (Stream Control Block) | per stream (the unnamed `$DATA` stream, and each named/alternate stream) |
| **CCB** (Context Control Block) | per open handle |

The nesting is **VCB → FCB → SCB → CCB**, and it mirrors the on-disk model closely enough to be a useful
reading aid: an FCB corresponds to a file's B+-tree entry, and an SCB to one of that entry's streams,
which is why a file with [alternate data streams](../attributes/NAMED_DATA.md) holds several SCBs under one
FCB. Crucially, the on-disk `$STANDARD_INFORMATION` is *derived from* the FCB at write time, so several
fields the analyst sees on disk are really snapshots of these runtime structures — a relationship the
[`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) page exploits when interpreting fields
whose source is an in-memory FCB bit.

## NTFS and ReFS as peer drivers

Both `ntfs.sys` and `refs.sys` participate in the Windows I/O model **identically**: they register with
the I/O Manager, take part in volume recognition, create device objects for their mounted volumes, expose
the standard IRP dispatch interface, and cooperate with the Cache Manager and Memory Manager through
common interfaces. An application issuing `CreateFile` / `ReadFile` / `WriteFile` follows the same path
regardless of which file system backs the volume — the divergence happens only once the IRP reaches the
mounted FSD and is interpreted against that file system's own structures.

The difference is entirely internal:

- **NTFS** associates file state with **MFT records** (a flat Master File Table).
- **ReFS** associates file state with **B+-tree entries** managed by the **Minstore** storage engine — there
  is no flat metadata table to scan.

That one structural choice is the root of nearly every ReFS-specific forensic difference — addressing,
residency, slack, snapshots, the change journal — each enumerated on the
[NTFS vs ReFS](ntfs_comparison.md) page. The internal organisation of `refs.sys` that produces the B+-tree
format — the Refs/Minstore two-layer split and the three-tier IRP dispatch within it — is the subject of
the [Driver Architecture](architecture.md) page.

## Pathname resolution and namespace redirection

Resolving a path happens at two levels, and only the second is ReFS's responsibility:

1. **OS level** — the Object Manager resolves the drive/volume reference (e.g. `E:\`) and identifies the
   mounted FSD instance.
2. **Format-specific** — the FSD resolves the remaining path inside its own on-disk namespace. NTFS walks
   `$INDEX` B-tree entries; ReFS walks Minstore B+-tree rows in each
   [directory's own tree](../structures/directory_entries.md).

Windows also redirects the namespace through **reparse points**, and ReFS supports them from its earliest
version:

- **Symbolic links** — path-based indirection to another file or directory.
- **Junctions** — redirect directory traversal to another location.
- **Volume mount points** — expose another volume at a directory path.

All three are stored on ReFS as reparse data, decoded on the
[Reparse Points](../structures/reparse_points.md) structure page; the tag set (including the WSL device
tags) is part of why the [Driver Interface](driver_architecture.md) treats reparse support as a build
capability.

## Cross-references

- [Driver Architecture](architecture.md) — the internal two-layer (`Refs*` / Minstore) model and the
  three-tier IRP dispatch *inside* `refs.sys`, one layer below this page
- [Driver Interface](driver_architecture.md) — the IRP handler set as a per-build capability fingerprint
- [NTFS vs ReFS](ntfs_comparison.md) — how the MFT-vs-B+-tree choice ripples into every forensic difference
- [File Systems](file_systems.md) — the general file-system vocabulary (clusters, extents, consistency)
  this page sits above
- [Bootstrap Chain](bootstrap_chain.md) — what `refs.sys` reads off disk at mount, after recognition
- [Version Detection](version_detection.md) — the VBR format markers that gate ReFS recognition and mount
- [VBR](../structures/vbr.md) — the on-disk signature `RefsIsBootSectorOurs` checks at recognition time
- [Directory Entries](../structures/directory_entries.md) — the B+-tree rows the FSD walks for path
  resolution
- [Reparse Points](../structures/reparse_points.md) — the symlink / junction / mount-point redirection data
- [Security Descriptors](../structures/security_descriptors.md) — the `SECURITY_DESCRIPTOR` blob the SRM
  evaluates, centralised in OID 0x530
- [`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) — the on-disk fields derived from the
  in-memory FCB
- [`$DATA` / named streams](../attributes/NAMED_DATA.md) — the multiple SCBs an FCB can own

## Evidence

The Windows I/O model components on this page (I/O Manager, IRP, Object Manager, SRM, Filter Manager, Cache
Manager, VCB/VPB mounting) are standard documented kernel behavior, not ReFS-specific claims. The
ReFS-specific facts it asserts are confirmed in the decompiled driver (E2): the three-tier IRP dispatch
(`RefsFsd*` exception frame → `RefsCommon*` logic → `Cms*` storage, with `RefsFsdDispatchSwitch` routing
the less common codes and `RefsExceptionFilter` guarding faults) and its handler counts (18 on v3.4, 20 on
v3.14) are catalog-verified; the named IRP handlers `RefsCommonCreate` (`IRP_MJ_CREATE`) and
`RefsCommonCleanup` (`IRP_MJ_CLEANUP`) are catalog-verified; the in-memory control-block hierarchy
VCB → FCB → SCB → CCB is catalog-verified; and the recognition/mount functions `RefsIsBootSectorOurs`
(signature + version check) and `InitializeVcbFromBootSector` (geometry into the VCB) are catalog-verified
boot/mount functions. The Refs-vs-Minstore namespace partition that makes ReFS a peer driver is master
§G.1. See [how this was verified](../methodology.md) to trace these to the exact builds and measurements in
`analysis/`.
