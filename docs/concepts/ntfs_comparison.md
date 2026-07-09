# NTFS vs ReFS Comparison

Almost every ReFS forensic mistake is really an NTFS habit applied to the wrong file system. NTFS is a
flat **Master File Table** updated **in place**, with a **redo *and* undo** journal; ReFS is a forest of
per-object **B+-trees** updated by **copy-on-write**, with a **redo-only** log. Those two structural
choices ripple into addressing, residency, slack, snapshots, the change journal, and what a crashed
volume leaves behind — and each ripple is a place an NTFS-trained tool silently produces wrong output.
This page maps the structures to their NTFS counterparts and, for every difference, states the forensic
consequence.

## The two architectures at a glance

| Concept | NTFS | ReFS |
|---------|------|------|
| Volume bootstrap | BPB → $MFT → metadata files | VBR → SUPB → CHKP → 13 B+-tree roots |
| File identification | MFT record number (reusable) | Object ID (64-bit, monotonic, never reused) |
| Metadata storage | MFT records (fixed 1 KiB) | B+-tree entries (variable size) |
| Directory index | B-tree ($INDEX_ROOT / $INDEX_ALLOCATION) | Per-directory B+-tree |
| Address translation | Data runs in $DATA (one level: VCN → LCN) | Two levels: extents (VCN → VLCN), then Container Table (VLCN → PLCN) |
| Attribute model | Named/typed within an MFT record | Named/typed within a B+-tree entry |
| Update model | In-place write + redo/undo journal | Copy-on-write + redo-only log |
| Crash recovery | $LogFile redo and undo | MLog redo only |
| Space management | $Bitmap (bit-per-cluster) | Three-tier allocator |
| Integrity | Optional ($Verify on Server) | Integrity streams + metadata checksums |
| Snapshots | Volume Shadow Copy (volume-level) | Per-stream `$SNAPSHOT` attribute |
| Change journal | `USN_RECORD_V2` (64-bit file ID) | `USN_RECORD_V3` (128-bit: parent OID + entry index) |

The bootstrap row sets the tone: there is no `$MFT` to scan. Where an NTFS tool walks a contiguous
record array, a ReFS tool must descend the [bootstrap chain](bootstrap_chain.md) — VBR to
[superblock](../structures/supb.md) to [checkpoint](../structures/chkp.md) to the 13 B+-tree roots — and
then traverse trees. The rest of this page is the set of differences that change forensic procedure, not
just terminology.

## Address translation is two-level

NTFS resolves a file offset in one hop: a data run in `$DATA` maps the file's VCN straight to an LCN, a
real cluster on disk. ReFS inserts a virtual layer. A file's extents map VCN to **VLCN** (a position in
the volume-wide *virtual* address space), and only the [Container Table](../structures/container_table.md)
knows the second arrow, VLCN → **PLCN**, the real cluster. The full path is **VCN → VLCN → PLCN**.

The forensic consequence is the single most common ReFS parsing error: a tool that treats a ReFS extent
pointer as a physical address — the reflex of NTFS data-run handling — reads clusters that are not the
file's data, and every result derived from those bytes is wrong. The discipline is to load the Container
Table first and route *every* VLCN through it before touching the disk. [Virtual
addressing](virtual_addressing.md) explains the shift/mask arithmetic and the three bootstrap roots that
are the lone exception (they store real LCNs because there is no table to translate them yet).

## Resident storage thresholds differ by orders of magnitude

In NTFS a file's data is resident only if it fits in the slack of its 1 KiB MFT record — roughly 700
bytes after the record's attributes. ReFS has no fixed record, so the threshold is a driver policy
decision, and it is large and version-dependent:

| File system | Resident threshold |
|-------------|--------------------|
| NTFS | ~700 bytes (constrained by the 1 KiB MFT record) |
| ReFS v3.4–v3.10 | 128 KiB hard cap (`STATUS_FILE_SYSTEM_LIMITATION` above it) |
| ReFS v3.11+ | 2 KiB data threshold |

`RefsAddAllocationForResidentWrite` is the function that makes the call, converting to non-resident
(via `RefsConvertToNonResident`) once allocation crosses the threshold. The practical impact: a tool
calibrated to NTFS's ~700-byte line under-counts resident files on ReFS, and on v3.4–v3.10 it misses
files up to 128 KiB that live entirely inside a B+-tree page with no external extents. The 2 KiB
v3.11+ threshold is why v3.14 volumes show non-resident files where Win10 v3.4 volumes show almost none.
Alternate data streams follow the same rule: a small ADS (< 2 KB) is resident/inline, and a large ADS
(>= 2 KB) is promoted to non-resident extents. See [Resident Storage](resident_storage.md) for the
conversion logic.

## Slack space takes a different form

Both file systems leak deleted data into unused space, but the shape of that space differs, so the
carving target differs:

| Aspect | NTFS | ReFS |
|--------|------|------|
| Source | Fixed 1 KiB MFT-record tail | Stale rows in variable-length B+-tree pages |
| Mechanism | Unused tail after the record's attributes | Deleted rows left in the data area, then propagated by copy-on-write |
| Artifact to target | Fixed-size trailing slack at a record boundary | A stale row body inside a live or superseded page |

On NTFS the analyst knows exactly where slack begins — the byte after the last attribute in a 1 KiB
record. On ReFS there is no record boundary; a deleted directory row is simply not relinked, and
[copy-on-write](copy_on_write.md) can carry that stale body forward into the new version of the page.
Recovery therefore means scanning page bodies for orphaned rows, not reading a fixed tail — the
technique [Deletion Recovery](deletion_recovery.md) describes.

## The change journal records are wider

NTFS's USN journal uses **V2** records with 64-bit file references. ReFS uses **V3** records with
128-bit references: the upper 8 bytes are the **parent directory's Object Table OID** and the lower 8
bytes are a **sequential entry index** within that directory (monotonically increasing, never reused).
A tool that assumes V2 layout mis-parses every ReFS USN record. The reason codes themselves are shared
between the two file systems, so once the record is parsed correctly the timeline semantics carry over —
`FILE_CREATE`, `FILE_DELETE`, `RENAME_OLD_NAME`/`RENAME_NEW_NAME`, `BASIC_INFO_CHANGE`, and the rest mean
the same thing. Only the file-ID width and the parsing change. The [USN Journal](../structures/usn_journal.md)
page gives the record layout and the 128-bit ID decomposition.

## Compression operates at a different granularity

NTFS compresses transparently in the I/O path, per cluster, with the result visible through the normal
file API. ReFS v3.14 (24H2) introduces background compression that is **per-container, not per-extent**:
there is no compression flag on the type-0x40 extent entry, the work happens asynchronously, and it is
not transparent to the file API. Configuration is recorded in the Container Table root header, not on the
file. The forensic consequence is that an NTFS-style per-file compression check finds nothing — a tool
must read the per-container parameters instead, and standard Windows APIs (including `fsutil`) do not
expose them. [Compression](compression.md) decodes the parameter record and the LZ4 / ZSTD / LZ4QAT
algorithm enum.

## Snapshots are per-stream, not per-volume

NTFS snapshots are a volume-level service (Volume Shadow Copy); recovery means mounting a shadow copy.
ReFS keeps versioning *inside* the file system, as a per-stream `$SNAPSHOT` attribute embedded in the
B+-tree entry:

| Aspect | NTFS | ReFS |
|--------|------|------|
| Level | Volume (VSS) | Per-stream (`$SNAPSHOT` attribute) |
| Management | OS-level Volume Shadow Copy | Embedded in the B+-tree entry |
| Recovery | Mount the shadow copy | Read the attribute structure on disk |

VSS enumeration techniques do not transfer: there is no shadow-copy store to mount. Instead the analyst
reads the [`$SNAPSHOT` attribute](../attributes/SNAPSHOT.md) directly and follows its extents — which use
the same type-0x40 extent format as ordinary file data — to recover the frozen prior content. See
[Snapshots and Versioning](snapshots_versioning.md).

## Security descriptors: same blob, different lookup

This is a difference of indexing only, and the good news for tooling is that the descriptor *format* is
identical:

| | NTFS | ReFS |
|---|------|------|
| Storage | `$Secure` (MFT entry 9) with the SII / SDH indexes | OID 0x530 (descriptors keyed directly by SecurityId) |
| Descriptor format | `SECURITY_DESCRIPTOR` | `SECURITY_DESCRIPTOR` (identical) |

Both centralise descriptors behind a per-object SecurityId stored in the file's metadata. NTFS resolves
that ID through two index streams; ReFS resolves it directly in a single table, OID 0x530, which holds
the owner SID, group SID, DACL, and SACL. A tool that already parses descriptor blobs needs no change to
its blob parser — only its lookup path is rerouted from `$Secure` to OID 0x530. The
[Security Descriptors](../structures/security_descriptors.md) table documents the key format; the
SecurityId itself lives at [`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) offset 0x28.

## Timestamps and timestomping detection

Both file systems carry four timestamps with identical semantics: creation, modification,
metadata-change, and last access. The difference that matters forensically is how many *copies* of those
timestamps exist:

| Aspect | NTFS | ReFS |
|--------|------|------|
| Timestamp sets per file | Two (`$SI` and `$FN`), shared across all hard links | One `$SI` set **per name** — a hard-linked file has one independent copy per name |
| Timestomping detection | Compare `$SI` vs `$FN` (different update rules) | Single-named file: a *different but still effective* method (below). Hard-linked file: compare MACB across the names |
| Corroborating ordinal | — | v3.4–v3.10 NextFileId child-creation ordinal at `$SI`+0x58 |

The classic NTFS timestomping check — comparing the `$STANDARD_INFORMATION` set against the
`$FILE_NAME` set, which the high-level APIs cannot reach — has no equivalent on ReFS **for a
single-named file**, because there is only one `$SI` set and no `$FN` twin to compare it against. A
**hard-linked file is the exception**: ReFS carries one `$SI` set *per name*, so each name is an
independent timestamp copy, and a name-scoped timestomp (the usual case — the analyst opens one path and
sets its time) rewrites only that name's set while the sibling names keep the true birth. Comparing MACB
across a file's names is therefore a ReFS-specific tamper check — the latest Created among the siblings is
the authentic creation, it is journal-independent, and it is *stronger* than NTFS's `$SI`-vs-`$FN`, where
all hard links share one `$SI` and cannot diverge. For single-named files, timestomping is nonetheless
detectable by three other means. The metadata-change time
(`$SI`+0x10) is filesystem-controlled and not reachable through the high-level APIs common tools use
(`SetFileTime`, PowerShell), so a back-dated Created or Modified value leaves change-time far in the
future relative to both. The USN journal records the tampering operation itself
(`BASIC_INFO_CHANGE` / `FILE_CREATE`). And the volume-creation time is a hard lower bound on any genuine
file timestamp. The USN anchor is the most robust of the three. On v3.4–v3.10 the NextFileId ordinal at
`$SI`+0x58 — a directory's monotonically assigned child-creation counter — corroborates creation order
independently of the timestamps. [Timestomping Detection](timestomp_detection.md) develops the full
method.

## Logging and recovery: redo-only changes everything

NTFS's `$LogFile` carries both redo and undo records; undo exists because in-place updates must be
rollable-back. ReFS's MLog is **redo-only**, and the reason is structural: because metadata is updated by
[copy-on-write](copy_on_write.md), an interrupted transaction never overwrote the prior state, so there
is nothing to undo. The log only needs to record *what to re-apply*.

| Aspect | NTFS | ReFS |
|--------|------|------|
| Log type | Redo + undo | Redo only |
| Pre-images in the log | Yes (undo records) | **No** |
| Why | In-place updates need rollback | CoW makes undo unnecessary |
| Prior states from the log | Read `$LogFile` backward | **Not from the log** — no pre-images in MLog |
| Prior-state alternative | — | Scan for dereferenced CoW pages on disk |

The forensic trade-off is subtle and runs *in ReFS's favour*. On NTFS, recovering a prior state from the
journal works only until the circular log wraps and an in-place overwrite destroys the old bytes. On
ReFS the log holds no pre-images at all — but it does not need to, because every modified page was
written to a *new* cluster, leaving the old page intact on disk until the allocator reuses its clusters.
The recovery window is therefore governed by allocator pressure, not by log wrap, and tends to be longer.
[Transactions and Crash Consistency](transactions_crash_consistency.md) covers the MLog model and the
checkpoint-flush commit point; the redo records are dispatched on replay by
`CmsLogRedoQueue::PerformRedo`, decoded in the [MLog](../structures/mlog.md) structure page.

## The `$Extend` directory and its ReFS analogue

OID 0x520 is the ReFS counterpart of NTFS's `$Extend` directory: both are containers for system-level
metadata objects. Their *contents* diverge, because ReFS implements only a subset of the NTFS metadata
services:

| NTFS `$Extend` child | ReFS equivalent | Notes |
|----------------------|-----------------|-------|
| `$UsnJrnl` | "Change Journal" in OID 0x520 | Created dynamically when USN journaling is activated; carries the `$J`/`$Max` streams plus metadata |
| `$Reparse` | "Reparse Index" in OID 0x520 (v3.4–v3.7) / standalone OID 0x540 (all versions) | v3.4 has both a file-entry wrapper in OID 0x520 and the standalone OID 0x540 B+-tree; v3.9+ keeps only the standalone OID |
| `$ObjId` | No equivalent | ReFS does not implement distributed link tracking |
| `$Quota` | No equivalent | ReFS does not support NTFS-style disk quotas |
| `$RmMetadata` | No equivalent | ReFS has no transactional resource manager |

On v3.4 through v3.7, OID 0x520 also holds two "degenerate" children with no NTFS analogue — a
**Security Descriptor Stream** (a file-entry wrapper for OID 0x530) and a **Volume Direct IO File** (a
DASD placeholder for raw volume I/O). These are backward-compatibility wrappers created at format time by
`CreateDownlevelDegenerateMetadataObjects` and removed in v3.9+; the standalone OIDs they reference
(0x530 for security, 0x540 for reparse) persist on every version. An upgraded v3.4→v3.14 volume keeps the
original degenerate children, which makes their presence a marker of original-format provenance. The
full child table is in [System OIDs](../structures/system_oids.md).

## File identity and creation-order reasoning

NTFS reuses MFT record numbers after deletion, which is why MFT position is only a *partial*
chronological signal — a low record number can belong to a recently created file that reclaimed a freed
slot. ReFS Object IDs are 64-bit, monotonically increasing, and **never reused** after deletion. That
gives the analyst two things NTFS does not: a strict creation ordering (a lower OID is always older), and
**gaps in the OID sequence as direct evidence of past deletions**. The same monotonic counter underlies
the [USN](../structures/usn_journal.md) 128-bit file IDs. See
[Object IDs and File IDs](object_ids_fileids.md) for how OIDs are allocated and how to read deletion
gaps.

## What this means for an NTFS-trained tool

Grouping the differences by the kind of change they force on a tool:

**No ReFS equivalent — the NTFS technique simply does not apply.** Several NTFS *attribute names* have no
ReFS counterpart (`$FILE_NAME`, `$ATTRIBUTE_LIST`, `$EXTEND`, `$OBSOLETE`, `$VOLUME_NAME`, `$OBJECT_ID`,
`$INDEX_ALLOCATION`); see [Attributes — Forensic Reference §4](../attributes/README.md) for what each maps
to. Concretely retired techniques:

- MFT-array scanning — there is no flat metadata table; the closest analogue is MSB+ page-signature
  carving.
- The `$FN`/`$SI` timestomping cross-check — a single-named ReFS file has one `$SI` set and no `$FN`
  twin; use the change-time + USN + volume-creation method instead. A hard-linked file is the exception:
  ReFS stores one `$SI` set per name, so its names' MACB can be compared directly (see
  [Timestomping Detection](timestomp_detection.md)).
- `$LogFile` undo-record analysis — MLog is redo-only.
- Volume Shadow Copy enumeration — versioning is per-stream `$SNAPSHOT`, on disk.

**Structurally similar — reuse the parser, change the lookup.**

- Security-descriptor analysis: the blob format is identical; reroute the lookup from `$Secure` to OID
  0x530.
- Four-timestamp interpretation: unchanged for the `$SI` set.
- Resident-file extraction: same idea, different size threshold (128 KiB or 2 KiB, not ~700 bytes).

**Same capability, different mechanism.**

- *Previous-state recovery*: NTFS reads its log backward; ReFS scans for dereferenced CoW pages, with a
  recovery window bounded by allocator reuse rather than log wrap.
- *Creation-order reasoning*: NTFS uses MFT positions (weakened by reuse); ReFS uses monotonic OIDs
  (strict order, gaps = deletion evidence).
- *Transaction classification*: NTFS `$LogFile` carries named operation codes; on ReFS the MLog redo
  opcodes (`CmsLogRedoQueue::PerformRedo` dispatches 26 handlers on v3.4 and ~39 on v3.14) can be
  abstracted by a tool into a small set of higher-level action types (CREATE, DELETE, RENAME, WRITE, and
  so on) via opcode-sequence analysis.
- *USN timeline analysis*: both use USN journals with the same reason codes; ReFS V3 records carry
  128-bit file IDs that need different parsing but yield the same timeline.

## Cross-references

- [Virtual Addressing](virtual_addressing.md) — the two-level VCN → VLCN → PLCN scheme that NTFS has no
  equivalent of, and the most common ReFS parsing error
- [Copy-on-Write](copy_on_write.md) — why ReFS needs no undo log and why prior pages survive on disk
- [Transactions and Crash Consistency](transactions_crash_consistency.md) — the redo-only MLog model and
  the checkpoint-flush commit point
- [Resident Storage](resident_storage.md) — the 128 KiB / 2 KiB residency thresholds versus NTFS's
  ~700-byte line
- [Deletion Recovery](deletion_recovery.md) — recovering stale B+-tree rows, the ReFS analogue of
  MFT-record slack
- [Object IDs and File IDs](object_ids_fileids.md) — monotonic 64-bit OIDs versus reusable MFT numbers
- [Timestomping Detection](timestomp_detection.md) — the ReFS method that replaces the `$SI`/`$FN`
  cross-check
- [Snapshots and Versioning](snapshots_versioning.md) — per-stream `$SNAPSHOT` versus volume VSS
- [Compression](compression.md) — per-container compression versus NTFS per-cluster
- [Bootstrap Chain](bootstrap_chain.md) — the VBR → SUPB → CHKP → roots path that replaces `$MFT` scanning
- [Windows File Systems](windows_file_systems.md) — where NTFS and ReFS sit in the Windows I/O stack
- [USN Journal](../structures/usn_journal.md) — the V3 128-bit record layout
- [Security Descriptors](../structures/security_descriptors.md) — OID 0x530, the `$Secure` replacement
- [System OIDs](../structures/system_oids.md) — OID 0x520 and the `$Extend`-equivalent children
- [`$SNAPSHOT`](../attributes/SNAPSHOT.md) — the per-stream snapshot attribute and its extents
- [`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) — the single timestamp set and the
  SecurityId

## Evidence

The mechanism-level facts are confirmed in the decompiled driver (E2) and corroborated on the raw-disk
corpus (RD). The residency thresholds (128 KiB pre-v3.11, 2 KiB v3.11+) come from
`RefsAddAllocationForResidentWrite` / `RefsConvertToNonResident`. The redo-only log model and
the per-opcode dispatch are from `CmsLogRedoQueue::PerformRedo` (26 handlers on v3.4, ~39 on
v3.14). The 128-bit USN V3 record (parent-OID + entry-index) is RD-confirmed. Security descriptors
in OID 0x530 and the `$Extend`-equivalent OID 0x520 children (built by
`CreateDownlevelDegenerateMetadataObjects`) are decompiled-confirmed (E2). The monotonic-OID chronology
contrast with reusable MFT numbers is raw-disk-confirmed. The compression difference — per-container, with no
type-0x40 extent flag — is finding **AP_REDO_037**; the NextFileId child-creation ordinal at `$SI`+0x58 is
finding **MD_SI_RA_008**. See [how this was verified](../methodology.md) to trace these to the exact images and
measurements in `analysis/`.
