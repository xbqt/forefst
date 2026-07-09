# Carrier's Five Data Categories Applied to ReFS

Brian Carrier's *File System Forensic Analysis* organises every file-system artifact into five
reference categories — **File System, Content, Metadata, File Name, and Application**. The value of
that model for an analyst is that it turns an open-ended question ("what was on this volume?") into a
routing problem: each thing you want to know lives in exactly one category, and each category maps to a
known set of ReFS structures. This page does that mapping. It also makes one point the NTFS literature
does not prepare you for — in ReFS the five categories are not just a filing scheme but a hard
**dependency order**: the File System category must be parsed first, because nothing else on the volume
can be read until it has handed you a working virtual-to-physical address translator.

## The categories are a parse order, not just a taxonomy

Carrier's model is layered — the File System category tells you how to find and interpret everything
else, and the remaining four become reachable only afterwards. In ReFS that dependency is *stricter*
than in NTFS, because almost every address on the volume is **virtual** and must be translated through
the [Container Table](../structures/container_table.md) before the cluster it names can be read. Parse
in the wrong order and you translate garbage.

```
1. FILE SYSTEM   VBR -> SUPB -> CHKP -> 13 root tables -> Container Table
                 (establishes layout + VLCN->PLCN translation)
                   |
                   v
2. CONTENT       $DATA extents / resident bytes / integrity streams / refcounts
3. METADATA      $SI, security, OIDs, attribute + system schemas
4. FILE NAME     directory entries (type 0x30), Parent-Child Table, reparse
5. APPLICATION   MLog/redo, checkpoint replay, CoW recovery, Block Refcount
```

### Category 1 — File System

**Contains** the structures needed to find and interpret every other structure. In ReFS that is the
bootstrap chain plus the address-translation layer: the [Volume Boot Record](../structures/vbr.md)
(512 bytes), the [Superblock](../structures/supb.md) (`SUPB`, with two backups near the end of the
volume), the [Checkpoint](../structures/chkp.md) (`CHKP`, two alternating copies), the
[13 root-table pointer list](../structures/chkp.md) at CHKP+0x94, the
[Container Table](../structures/container_table.md), the [Allocator tables](../structures/allocators.md),
and the [80-byte common page header](../structures/page_header.md) shared by `SUPB`/`CHKP`/`MSB+` pages.

An analyst uses this category to validate the volume, select the live checkpoint, enumerate the root
tables, and — the step that gates everything downstream — build the VLCN→PLCN translator. Checkpoint
selection is the highest virtual clock (CHKP+0x60) among the copies that pass the cluster-size-dependent
self-check (CRC32-C / 4 B on 4 KiB clusters, CRC64 / 8 B on 64 KiB, SHA-256 / 32 B on SHA-256 volumes),
performed by `ChooseCheckpointRecord`; an invalid higher-clock copy is skipped and the lower-clock valid
copy is used. Of the 13 roots, only **#7 Container Table, #8 Container Table duplicate, and #12 Small
Allocator** use real (physical) LCNs — the bootstrap exception that lets translation get started; the
other ten are virtual and unreadable until the translator is loaded. The page header's numeric table-OID
(at offset 0x48, the low half of the 16-byte identifier; the high half at 0x40 is always 0) and the
`MSB+` signature at offset 0x00 are what every later carving step keys on.

→ [Bootstrap chain](bootstrap_chain.md) · [Virtual addressing (VLCN→PLCN)](virtual_addressing.md) ·
[Cluster / page size](cluster_page_size.md)

### Category 2 — Content

**Contains** file content plus the structures that locate or allocate it. In ReFS: the
[`$DATA`](../attributes/DATA.md) attribute (resident inline bytes vs. non-resident runs described by
24-byte type-0x40 [extent descriptors](../structures/extent_descriptors.md)),
[`$NAMED_DATA`](../attributes/NAMED_DATA.md) alternate streams,
[compression parameters](compression.md), the [Block Refcount Table](../structures/block_refcount.md)
for clones and dedup, and the [Integrity State Table](../structures/integrity_state.md) plus per-file
copy-on-write checksum streams.

An analyst uses this category to carve and reconstruct file bytes. The resident/non-resident decision
matters here because it determines whether a small file's content sits inline in metadata or out in
extents: the driver (`RefsAddAllocationForResidentWrite`) converts to non-resident at **2048 bytes
(0x800) on v3.11+**, with a **128 KB (0x20000)** hard cap on v3.4–v3.10. Following an extent then means
running each VLCN through the Container Table — exactly the dependency this category inherits from
Category 1. Deduplicated and cloned regions are read from the Block Refcount per-cluster entry (bits
13:0 = reference count, bit 14 = dedup-metadata flag, bit 15 = dedup-managed), and user data can be
validated against integrity streams where they are enabled.

→ [Resident vs non-resident storage](resident_storage.md) · [Copy-on-write](copy_on_write.md) ·
[Compression](compression.md)

### Category 3 — Metadata

**Contains** the structures describing an object's properties — times, sizes, flags, security, and
identity. In ReFS these are not standalone records but fields inside the object's B+-tree value: the
inline [`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) (`$SI`) carried in the type-0x30
value (creation / modification / metadata-change / access FILETIMEs at value+0x28 / +0x30 / +0x38 /
+0x40, attributes at value+0x48), the [attribute schema registry](attributes.md) (18 attribute schemas)
and the 18 system schemas, [security descriptors](../structures/security_descriptors.md) (centralised
and referenced by SID under OID 0x530), and the [Object-ID space](../structures/system_oids.md) (64-bit
OIDs, never reused).

An analyst uses this category to build timelines, resolve ownership and ACLs, and order events. Two
ReFS-specific facts shape that work. First, the OID itself is a chronological signal that NTFS lacks:
because OIDs are monotonically increasing and never reused, **lower OID = earlier creation**, and a gap
in the OID sequence is direct evidence of a past deletion (`MsSetMinimumNewObjectId` hardcodes the user
floor). User objects start at **OID 0x701**; system OIDs occupy 0x00–0x6FF, with 0x700 the boundary that
is never assigned (`RefsIsSystemObjectId` returns true for OID ≤ 0x6FF except 0x600, the root directory).
Second, the `$SI` layout changes non-backward-compatibly at v3.14 (offset 0x50 and above), so a timeline
parser must branch on version before reading those fields.

→ [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) · [Timestomp detection](timestomp_detection.md) ·
[Attributes overview](attributes.md) · [System OIDs](../structures/system_oids.md)

### Category 4 — File Name

**Contains** how names and path relationships are stored and recovered. The defining ReFS difference
from NTFS lives here: names are **B+-tree keys**, not standalone `$FILE_NAME` records.
[Directory entries](../structures/directory_entries.md) use key type **0x30** with the UTF-16LE name at
key+0x04 and key flags 0x01 (resident) or 0x02 (non-resident-or-directory). The
[Parent-Child Table](../structures/parent_child_table.md) (CHKP root #4) holds the hierarchy in 48-byte
rows (16-byte header + a 32-byte shared key/value where the value overlaps the key, ParentOID at +0x08
and ChildOID at +0x18). The [`$OBJ_LINK`](../attributes/OBJ_LINK.md) directory attribute carries the
parent OID and lets you recover the path of an unreferenced directory.
[Reparse points](../structures/reparse_points.md) (symlink tag 0xA000000C, junction tag 0xA0000003) and
hard links round out the category.

An analyst uses this to reconstruct full paths — directory tables supply the names, the Object-ID and
Parent-Child structures supply the hierarchy — and to recover deleted names from B+-tree **node slack**:
a deletion only clears the offset-array slot, so the row body survives until the node is rewritten. Two
traps are worth flagging because they are exactly where NTFS reflexes mislead. The directory marker is
**attribute bit 0x10000000 at value+0x40**, *not* a distinct key-flags value (key flags carry only 0x01
and 0x02; there is no 0x04 "directory"). And `$SI+0x70`, which the resident layout labels
"HardLinkCount", cannot serve as a hard-link counter — it never exceeds 1, because resident files cannot
be hard-linked. Genuine hard links are instead counted by resolving each name to its physical type-0x40
stream record `(owner-dir, file_id)` — local `(parent, file_id)` or home `(home, file_id)` — selected by
the candidate whose 0x40 size **matches the name's own size** (value+0x38), then grouping the names that
share that stream. The size match is the load-bearing discriminator: it keeps two different files that
collide on the same per-directory child ordinal from being merged into one. Hard links are themselves
v3.14-native-only (driver helpers include `RefsHardlinksSupported`, `RefsLinkFileToSelf`).

→ [Directory entries](../structures/directory_entries.md) · [$OBJ_LINK](../attributes/OBJ_LINK.md) ·
[Parent-Child Table](../structures/parent_child_table.md) · [Reparse points](../structures/reparse_points.md)

### Category 5 — Application

**Contains** the artifacts of higher-level file-system features — chiefly journaling and the resilience
machinery. In ReFS: the [MLog transaction log](../structures/mlog.md) (redo-only; a four-layer record
structure with the opcode at `_SmsRedoRecord`+0x04, dispatched by `CmsLogRedoQueue::PerformRedo`), the
[checkpoint replay](../structures/chkp.md) relation (CHKP holds the oldest-log-record reference at +0x70),
the [USN change journal](../structures/usn_journal.md) (USN_RECORD_V3, disabled by default, a circular
buffer), and copy-on-write version recovery backed by the
[Block Refcount Table](../structures/block_refcount.md).

An analyst uses this category to reconstruct operations from redo records, to correlate the journal's LSN
range against the checkpoint and find committed-but-not-yet-on-tree operations, and to drive CoW
prior-content recovery. The key property is that **ReFS logs redo only, never undo** — copy-on-write
guarantees the old pages are still intact on a crash, so there is nothing to roll back. This is also why
the Application category is where recovery lives, and why it carries its own recoverability sub-taxonomy
(below).

→ [MLog / transaction log](../structures/mlog.md) · [USN journal](../structures/usn_journal.md) ·
[Copy-on-write](copy_on_write.md)

## Forensic implications

**Parse in category order, or fail.** The categories are a hard dependency chain. You cannot read a
Content extent, a Metadata `$SI`, or a File-Name directory entry until the File System category has given
you a working VLCN→PLCN translator, because every one of those structures sits behind a virtual address —
the only physical-addressed roots are #7/#8/#12. An NTFS-trained parser that tries to carve `$DATA`
extents before bootstrapping the Container Table will reconstruct content from the wrong sectors. This is
the same discipline the [virtual addressing](virtual_addressing.md) page argues at length: load the
Container Table first, route every VLCN through it.

**The Application category is where prior content is recovered, and it has a three-state sub-taxonomy.**
Carrier's "Application" category in ReFS subsumes the copy-on-write resilience model, which is what
decides whether deleted or prior content is still on disk. Any candidate cluster falls into exactly one
of three states:

| State | Refcount condition | Recoverability | Why |
|-------|--------------------|----------------|-----|
| **CoW-protected** | refcount ≥ 2 | **Guaranteed** | A snapshot or the prior checkpoint still references the clusters; both references must drop before reuse. |
| **Unreferenced, not reallocated** | refcount = 0, clusters not yet reused | **Likely** | Clusters are freed but **not zeroed**; data survives until the allocator hands them to a new write. |
| **Reallocated** | clusters overwritten | **Lost** | A later allocation has written over the bytes. |

Map a candidate cluster to one of these states via the
[Block Refcount Table](../structures/block_refcount.md) and the allocator bitmaps before claiming
recoverability. On a validated multi-transaction sample, roughly half of the modified non-resident files
still had their old data fully intact and a majority of the old metadata pages were still valid — useful,
but not a guarantee, which is why the per-cluster state check is mandatory rather than optional.

**Checkpoint differential is weaker on ReFS than its NTFS analogue suggests.** After a clean unmount,
both CHKP copies decode to the *same* 13-root pointer list. So the "compare current vs previous
checkpoint" recovery path yields nothing on any cleanly unmounted or remountable image; it needs a
genuine mid-transaction crash capture. The durable single-image recovery paths are instead **stream
snapshots** (exact prior bytes, deterministic) and **B+-tree node-slack** recovery of deleted names. When
you do compare checkpoints, compare the *decoded root page-refs*, never the raw CHKP bytes — the virtual
clock and per-page checksums always differ even when the tree state is identical.

**Category boundaries differ from NTFS, so do not port NTFS reflexes.** Names are B+-tree keys, not
`$FILE_NAME` records; security is centralised, not per-file; `$DATA` is effectively always non-resident
above a small threshold; the journal is redo-only with a circular USN buffer (overwritten entries are
much harder to recover than NTFS `$UsnJrnl` slack). Treat NTFS expectations as a *question set*, not a
parser model — the [NTFS comparison](ntfs_comparison.md) page lays out the divergences structure by
structure.

## Version and state differences

- **File System:** the CHKP composite flags encode volume state — 0x002 (v3.4 / 3.7 / 3.9), 0x082
  (v3.10), 0x682 (v3.14 native), 0x602 (v3.14 upgraded), 0x2682 (Insider). Classify original / upgraded /
  native from these before trusting any layout (see [version detection](version_detection.md)).
- **Content:** the resident→non-resident conversion threshold drops from 128 KB (v3.4–v3.10) to 2048
  bytes (v3.11+). The Block Refcount Table schema (0xe0b0) exists since v3.4 but is only *populated* on
  v3.14 sharing activity.
- **Metadata:** `$SI` layout changes non-backward-compatibly at v3.14 (offset 0x50 and above); the
  NextFileId own-row population is gated at version < 0x30b.
- **File Name:** native hard links (and POSIX unlink/rename) are v3.14-only and require the native-format
  CHKP flag 0x080 — not available on upgraded volumes. Case-sensitive directories are also v3.14-only but
  *do* work on upgraded volumes.
- **Application:** the redo-opcode set grows across versions — v3.4 has **29 opcode values (0x00–0x1C) /
  26 handlers**; v3.14 has **44 opcode values (0x00–0x2B) / ~39 handlers** (only 0x17 is a non-handler
  error). Never hardcode an old opcode map.

## Tooling

`forefst.py` and `refsanalysis.py` are organised along these same categories. Representative invocations:

```
refsanalysis.py <image> chkp                          # File System: CHKP + 13 roots (boot/supb for VBR/SUPB)
refsanalysis.py <image> containers                    # File System: Container Table / translation
forefst.py <image> snapshots --show / --extract  # Application/Content: CoW prior-version bytes
forefst.py <image> deleted --slack               # File Name: node-slack deleted-name recovery
forefst.py <image> mlog                               # Application: redo records
```

## Cross-references

- [Bootstrap chain](bootstrap_chain.md) — the File System category in execution order
- [Virtual addressing](virtual_addressing.md) — why Category 1 must precede 2–4; the VLCN→PLCN translator
  every other category depends on
- [Container Table](../structures/container_table.md) — the structure that holds the VLCN→PLCN map the
  parse order is built around
- [Copy-on-write](copy_on_write.md) — the mechanism behind the Application-category recovery sub-taxonomy
- [Deletion recovery](deletion_recovery.md) — the concrete recovery methods these categories enable
- [System OIDs](../structures/system_oids.md) — the OID floor and the chronology signal used in Metadata
- [NTFS comparison](ntfs_comparison.md) — where the category boundaries diverge from NTFS

## Evidence

The category-to-structure mapping is grounded in the same evidence as the structure pages it routes to:
the bootstrap chain, address translation, and redo dispatch are confirmed in the driver (E2) — translation
in `GetContainerIdFromRealRange` / `RealRangeToContainerRange` with the `IsValidContainerLcn` boundary
check, checkpoint selection in `ChooseCheckpointRecord`, redo dispatch in `CmsLogRedoQueue::PerformRedo`,
the resident threshold in `RefsAddAllocationForResidentWrite`, and the OID floor in
`MsSetMinimumNewObjectId` / `RefsIsSystemObjectId` — and the on-disk facts (offsets, the three-state
recovery taxonomy, the same-decoded-root-after-clean-unmount property, the node-slack name survival, and
the size-matched hard-link grouping) are raw-disk decoded (RD) across the corpus. Findings: **FS_DEL_RA_002**
(freed clusters survive until reallocation), **AP_LGFL_005** (redo-only logging), **MD_SI_RA_010, MD_SI_RA_008** (NextFileId
version gate), **FN_LINK_002, MD_SI_RA_009** (`$SI+0x70` is not a hard-link counter), **FS_CHKP_RA_014** (both CHKP copies decode
identically after clean unmount), **FS_DEL_RA_005** (node-slack deleted-name recovery), and **AP_REDO_001–039** (redo-opcode
counts by version). See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
