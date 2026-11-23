# Carrier's Five Data Categories Applied to ReFS

Brian Carrier's *File System Forensic Analysis* (Addison-Wesley, 2005) organises every file-system artifact into five
reference categories — **File System, Content, Metadata, File Name, and Application**.

For an analyst, the model tells where to look for each kind of fact: most things you want to know belong to one
category, and each category maps to a known set of ReFS structures. This page does that mapping.

In ReFS the File System category must be parsed before the other four, which the NTFS literature does not prepare
you for: nothing else on the volume can be read until it gives you a working virtual-to-physical address
translator.

## The File System category comes first

Carrier's model is layered — the File System category tells you how to find and interpret everything else, and the
remaining four become reachable only afterwards (they have no order among themselves). In ReFS that dependency is
*stricter* than in NTFS, because almost every address on the volume is **virtual** and must be translated through the
[Container Table](../structures/container_table.md) before the cluster it names can be read. A parser that reads in another order
translates addresses without the map and reads the wrong clusters.

```text
1. FILE SYSTEM   VBR -> SUPB -> CHKP -> 13 root tables -> Container Table
                 (establishes layout + VLCN->PLCN translation)
                   |
                   v
2. CONTENT       $DATA extents / inline bytes / integrity streams / refcounts
3. METADATA      $SI, security, OIDs, attribute + system schemas
4. FILE NAME     directory entries (type 0x30), Parent-Child Table, reparse
5. APPLICATION   MLog/redo, checkpoint replay, USN journal, snapshot versions
```

### Category 1 — File System

**Contains** the structures needed to find and interpret every other structure. In ReFS that is the
bootstrap chain plus the address-translation layer: the [Volume Boot Record](../structures/vbr.md)
(512 bytes), the [Superblock](../structures/supb.md) (`SUPB`, with two backups near the end of the
volume), the [Checkpoint](../structures/chkp.md) (`CHKP`, two alternating copies), the
[13 root references](../structures/chkp.md) located through CHKP+0x94 (13 in-page offsets, or on v3.14 an
offset to them), the
[Container Table](../structures/container_table.md), the [Allocator tables](../structures/allocators.md),
and the [80-byte common page header](../structures/page_header.md) shared by `SUPB`/`CHKP`/`MSB+` pages.

An analyst uses this category to validate the volume, select the live checkpoint, enumerate the root
tables, and build the VLCN→PLCN translator, which every later step needs. Checkpoint
selection is the highest virtual clock (CHKP+0x60) among the copies that pass the cluster-size-dependent
self-check (CRC32-C / 4 B on 4 KiB clusters, CRC64 / 8 B on 64 KiB, SHA-256 / 32 B on SHA-256 volumes),
made in `ReadLatestCheckpoint`'s pass over the copies in superblock slot order (a tie keeps slot 0); an invalid
higher-clock copy is skipped and the lower-clock valid copy is used.

Of the 13 roots, only **#7 and #8 (the Container Table's two failover copies) and #12 Small Allocator** use real
(physical) LCNs — the bootstrap exception that lets translation get started; the other ten are virtual and unreadable
until the translator is loaded.

The page header's numeric table-OID (at offset 0x48, the low half of the 16-byte identifier; the high half at 0x40 is
always 0) and the `MSB+` signature at offset 0x00 are what a scan for metadata pages keys on.

→ [Bootstrap chain](bootstrap_chain.md) · [Virtual addressing (VLCN→PLCN)](virtual_addressing.md) ·
[Cluster / page size](cluster_page_size.md)

### Category 2 — Content

**Contains** file content plus the structures that locate or allocate it. In ReFS:

- the [`$DATA`](../attributes/DATA.md) attribute: inline bytes, or an extent map (a B+-tree node of 24-byte
  [extent entries](../structures/extent_descriptors.md), longer when each cluster carries a CRC32-C);
- [`$NAMED_DATA`](../attributes/NAMED_DATA.md) alternate streams;
- [compression parameters](compression.md);
- the [Block Refcount Table](../structures/block_refcount.md) (per-cluster counts of the references beyond the
  first);
- the [Integrity State Table](../structures/integrity_state.md), and the per-cluster CRC32-C checksums stored in the
  extent map of each integrity-stream file.

An analyst uses this category to carve and reconstruct file bytes. The residency decision matters here because it
determines whether a small file's content sits inline in its record or out in extents:

- on a volume of format 3.11 or later, the driver (`RefsAddAllocationForResidentWrite`) moves a stream to extents when
  it reaches **2,048 bytes (0x800)**;
- on format 3.10 and earlier a file's main data is always extent-backed; only named streams are inline there, up to
  **128 KiB (0x20000)**.

Following an extent then means translating each VLCN through the Container Table, so this category depends on
Category 1.

The Block Refcount per-cluster entry records how many references a cluster has (bits 12:0 = the count of references
beyond the first, bit 14 = a broken weak reference, bit 15 = a weak reference the deduplication path set; a snapshot
or a hard link adds no count), and user data can be validated against integrity streams where they are enabled.

→ [Record placement and data residency](placement_and_residency.md) · [Copy-on-write](copy_on_write.md) ·
[Compression](compression.md)

### Category 3 — Metadata

**Contains** the structures describing an object's properties — times, sizes, flags, security, and identity. In
ReFS these are not standalone records but fields inside the object's B+-tree value:

- the [`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) (`$SI`) fields — for an embedded file in its
  name row's value (creation / modification / metadata-change / access FILETIMEs at value+0x28 / +0x30 / +0x38 /
  +0x40, attributes at value+0x48); for a split file in its type-0x40 backing at the same offsets; for a directory in
  its own type-0x10 row;
- the [schema registry](attributes.md): 36 distinct schema ids across versions (18 attribute and 18 system), of which
  a volume carries 27–31;
- [security descriptors](../structures/security_descriptors.md), centralised in OID 0x530 and referenced by the
  SecurityId at `$SI`+0x28;
- the [Object-ID space](../structures/system_oids.md) (64-bit OIDs from a per-volume counter).

An analyst uses this category to build timelines, resolve ownership and ACLs, and order events. Two ReFS-specific
facts shape that work.

First, a directory's OID is a chronological signal that NTFS lacks: a new OID is always above every live
one, so **a lower OID means an earlier-created directory**, and a gap in the sequence is a deleted directory or a
directory creation that failed. Files carry no OID; their per-directory ordinal plays the same role within their
creation directory. `MsSetMinimumNewObjectId` seeds the counter at 0x700, so user objects start at **OID 0x701**;
system OIDs occupy 0x00–0x6FF, and 0x700 is never assigned (`RefsIsSystemObjectId` returns true for OID ≤ 0x6FF
except 0x600, the root directory).

Second, the `$SI` grows from 116 to 124 bytes at format 3.7, and the field at 0x50 changes meaning at 3.10; the
timestamps at 0x00–0x18 never move, so a parser branches on the record's own size and format only for the fields
from 0x50 on.

→ [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) · [Timestomp detection](timestomp_detection.md) ·
[Attributes overview](attributes.md) · [System OIDs](../structures/system_oids.md)

### Category 4 — File Name

**Contains** how names and path relationships are stored and recovered. The main ReFS difference
from NTFS is in this category: names are **B+-tree keys**, not standalone `$FILE_NAME` records.
[Directory entries](../structures/directory_entries.md) use key type **0x30** with the UTF-16LE name at
key+0x04 and key flags 0x01 (the row embeds the record) or 0x02 (an index entry: a split file, or a directory).
The
[Parent-Child Table](../structures/parent_child_table.md) (CHKP root #4) holds the hierarchy in 48-byte
rows (16-byte header + a 32-byte shared key/value where the value overlaps the key, ParentOID at +0x08
and ChildOID at +0x18). The [`$OBJ_LINK`](../attributes/OBJ_LINK.md) back-pointer (one per name, in the object's
own record) carries the parent OID, so on v3.7 and later the path of an unreferenced directory can be rebuilt by
chaining parents; v3.4 directories carry none.
[Reparse points](../structures/reparse_points.md) (symlink tag 0xA000000C, junction tag 0xA0000003) and
hard links round out the category.

An analyst uses this to reconstruct full paths — directory tables supply the names, the Object-ID and
Parent-Child structures supply the hierarchy — and to recover deleted names from B+-tree **node slack**:
a deletion only clears the offset-array slot, so the row body survives until the node is rewritten.

Two points mislead an analyst who applies NTFS habits:

- The directory marker is **attribute bit 0x10000000 at value+0x40** of the index entry, *not* a distinct key-flags
  value (key flags carry only 0x01 and 0x02; there is no 0x04 "directory").
- `$SI+0x70`, which the embedded layout labels "HardLinkCount", is the file's link count as the driver last wrote
  it: 1 in a record embedded in its name row, the number of names in a hard-linked file's backing record.

Which names belong together is found by resolving each name to its home backing — the type-0x40 record keyed
(home directory OID, ordinal) — and confirming it by size (the name's cached size at value+0x38) or, failing that, by
the backing's own list of names (its type-0x39 back-pointers). A home directory holds at most one backing per
ordinal, so this keeps different files apart; the confirmation guards against a stale cached size.

Hard links need the volume's hard-link flag, the boot-sector flags' bit 0x20, set on every corpus volume formatted
at 3.7 or later but one whose boot sector `refsutil fixboot` rewrote (`RefsHardlinksSupported` reads it;
`RefsLinkFileToSelf` is a driver helper).

→ [Directory entries](../structures/directory_entries.md) · [$OBJ_LINK](../attributes/OBJ_LINK.md) ·
[Parent-Child Table](../structures/parent_child_table.md) · [Reparse points](../structures/reparse_points.md)

### Category 5 — Application

**Contains** the artifacts of higher-level file-system features — chiefly journaling and the resilience
machinery. In ReFS: the [MLog transaction log](../structures/mlog.md) (redo-only; a four-layer record
structure with the opcode at `_SmsRedoRecord`+0x04, dispatched by `CmsLogRedoQueue::PerformRedo`), the
[checkpoint replay](../structures/chkp.md) relation (CHKP holds its log position at +0x70, where replay begins),
the [USN change journal](../structures/usn_journal.md) (USN_RECORD_V3; not created on a freshly formatted data
volume; an in-place ring that overwrites its oldest records), and stream-snapshot version recovery, which reads each
version's own extent table and the older snapshots' shared blocks.

An analyst uses this category to reconstruct operations from redo records, to compare the log's LSN range with the
checkpoint's log position and find operations logged after the last checkpoint, and to drive prior-content recovery.
The key property is that **ReFS logs redo only, never undo** — copy-on-write guarantees the old pages are still intact
on a crash, so there is nothing to roll back.

→ [MLog / transaction log](../structures/mlog.md) · [USN journal](../structures/usn_journal.md) ·
[Copy-on-write](copy_on_write.md)

## Forensic implications

**Parse the File System category first.** It is a hard prerequisite for the other four. You cannot read a
Content extent, a Metadata `$SI`, or a File-Name directory entry until the File System category has given
you a working VLCN→PLCN translator, because every one of those structures sits behind a virtual address —
the only physical-addressed roots are #7/#8/#12. An NTFS-trained parser that tries to carve `$DATA`
extents before bootstrapping the Container Table will reconstruct content from the wrong sectors. The
[virtual addressing](virtual_addressing.md) page gives the same rule: load the Container Table first, and
translate every VLCN through it.

**Prior content can be classified in three states.** The copy-on-write resilience model is what decides whether
deleted or prior content is still on disk. Any candidate cluster falls into exactly one of three states:

| State | Condition | Recoverability | Why |
|-------|-----------|----------------|-----|
| **Still referenced** | a live map names the clusters (a snapshot's extents, a clone's) | **Survives while that map lives** | The clusters are not free while that map lives (the Block Refcount table does not record a snapshot's sharing). |
| **Free, not yet reused** | no live map names them; the allocator marks them free | **Likely** | Clusters are freed but **not zeroed**; data survives until the allocator hands them to a new write. |
| **Reallocated** | clusters overwritten | **Lost** | A later allocation has written over the bytes. |

Check the allocator before claiming recoverability: an allocated cluster now belongs to other data; a free one may
still hold the old bytes, which only an independent check can confirm. On one measured sample, roughly half of the
modified extent-backed files still had their old data fully intact and a majority of the old metadata pages were still
valid. This helps, but it is not guaranteed, so the per-cluster state check is required.

**Checkpoint differential is weaker on ReFS than its NTFS analogue suggests.** After a clean unmount, the two CHKP
copies usually decode to the *same* 13-root pointer list (on the images measured and on all but one of the blind-audit
volumes; on that ReFS 3.4 volume five roots differ). So the "compare current vs previous checkpoint" recovery path
usually yields nothing on a cleanly unmounted or remountable image; it needs a capture between two checkpoint writes
that changed a root table. The durable single-image recovery paths are instead **stream
snapshots** (exact prior bytes, deterministic) and **B+-tree node-slack** recovery of deleted names. When
you do compare checkpoints, compare the *decoded root page-refs*, never the raw CHKP bytes — the copies differ in
several fields (virtual and allocator clocks, their own LCNs, checksums) even when the trees are identical, and
their clocks can tie.

**Category boundaries differ from NTFS, so do not apply NTFS habits.**

- Names are B+-tree keys, not `$FILE_NAME` records.
- Security descriptors live in a table (OID 0x530) rather than in NTFS's `$Secure` file.
- `$DATA` is inline only below 2 KiB, and only on format 3.11 and later.
- The metadata log (MLog) is redo-only, and the USN journal is an in-place ring that overwrites its oldest records
  where they lie.

Use NTFS expectations as questions to check, not as a model for the parser. The
[NTFS comparison](ntfs_comparison.md) page lists the differences structure by structure.

## Version and state differences

- **File System:** the CHKP composite flags encode volume state — 0x002 (v3.4 / 3.7 / 3.9), 0x082
  (v3.10), 0x682 (v3.14 native), 0x602 (v3.14 upgraded), 0x2682 (Insider). Classify original / upgraded /
  native from these (see [version detection](version_detection.md)); then read each record's layout from its own
  length, since an upgraded volume carries both.
- **Content:** on format 3.10 and earlier a file's main data is always extent-backed (named streams inline up to
  128 KiB); from 3.11 a stream is inline below 2 KiB (0x800). The Block Refcount Table schema (0xe0b0) exists since
  v3.4; its counts come from block cloning, deduplication and a few other paths — snapshots and hard links add none.
- **Metadata:** `$SI` grows from 116 to 124 bytes at format 3.7, and the field at 0x50 changes meaning at 3.10; the
  NextFileId own-row population is gated at version < 0x30b.
- **File Name:** hard links need the boot-sector flags' bit 0x20, set on volumes formatted at 3.7 or later and
  clear on 3.4 volumes; an upgrade does not set it, so a volume upgraded from 3.4 has none. Case-sensitive
  directories are not supported by the v3.4 driver (17134 has no `RefsSetCaseSensitiveInfo`); they are observed on
  3.14 volumes only.
- **Application:** the redo-opcode set grows across versions — v3.4 (17134) dispatches **29 opcode values
  (0x00–0x1C)**, 27 to a handler (26 distinct functions; 0x12 and 0x15 call none); v3.14 (26100) dispatches **44
  values (0x00–0x2B)**, 41 to a handler (about 39 distinct functions), 0x12 and 0x15 to none and 0x17 to an error;
  the Insider builds read dispatch up to 0x2C or 0x2D. Never hardcode an old opcode map.

## Tooling

The commands map onto these categories as follows (representative invocations):

```sh
refsanalysis.py <image> chkp                          # File System: CHKP + 13 roots (boot/supb for VBR/SUPB)
refsanalysis.py <image> containers                    # File System: Container Table / translation
forefst.py <image> snapshots --show              # Application/Content: prior-version bytes (--extract DIR writes them)
forefst.py <image> deleted                       # File Name: node-slack deleted-name recovery (--full = complete)
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
- [System OIDs](../structures/system_oids.md) — the OID floor; [OID allocation](oid_allocation.md) — the chronology
  signal used in Metadata
- [NTFS comparison](ntfs_comparison.md) — where the category boundaries diverge from NTFS

## Evidence

The category-to-structure mapping is grounded in the same evidence as the structure pages it routes to.

- In the driver: translation in `GetContainerIdFromRealRange` / `RealRangeToContainerRange` with the
  `IsValidContainerLcn` boundary check; checkpoint selection in `ReadLatestCheckpoint`'s slot loop (validity by
  `ValidateCheckpointRecord`, the clock comparison at +0x60); redo dispatch in `CmsLogRedoQueue::PerformRedo`; the
  residency gate in `RefsAddAllocationForResidentWrite`; the OID floor in `MsSetMinimumNewObjectId` /
  `RefsIsSystemObjectId`.
- On disk, across the corpus: the offsets, the checkpoint copies' root lists after a clean unmount (the volumes named
  above), the node-slack name survival and the hard-link grouping.
- Registered findings: freed clusters surviving until reallocation, redo-only logging, the NextFileId version gate,
  `$SI+0x70` as the link count, node-slack deleted-name recovery and the redo-opcode counts by version.

The three-state recovery taxonomy is a model, not a corpus measurement.

The counts behind the text: the two checkpoint copies decode to the same root list on 25 of the 26 volumes of the
first blind audit; the prior-state sample is one 2 GiB volume across a 266-transaction gap, where 9 of 18 modified
extent-backed files kept their old data fully intact and 13 of 21 old metadata pages were still valid.

See [how this was verified](../methodology.md) to trace these statements to the exact images and
measurements in `analysis/`.

<!-- findings: AP_CHJN_003, AP_LGFL_005, AP_REDO_001, AP_REDO_002, AP_REDO_003, AP_REDO_004, AP_REDO_005,
               AP_REDO_006, AP_REDO_007, AP_REDO_008, AP_REDO_009, AP_REDO_010, AP_REDO_011, AP_REDO_012,
               AP_REDO_013, AP_REDO_014, AP_REDO_015, AP_REDO_016, AP_REDO_017, AP_REDO_018, AP_REDO_019,
               AP_REDO_020, AP_REDO_021, AP_REDO_022, AP_REDO_023, AP_REDO_024, AP_REDO_025, AP_REDO_026,
               AP_REDO_027, AP_REDO_028, AP_REDO_029, AP_REDO_030, AP_REDO_031, AP_REDO_032, AP_REDO_033,
               AP_REDO_034, AP_REDO_035, AP_REDO_036, AP_REDO_037, AP_REDO_038, AP_REDO_039, FN_LINK_002,
               FS_CHKP_RA_014, FS_DEL_RA_002, FS_DEL_RA_005, MD_SI_RA_008, MD_SI_RA_009, MD_SI_RA_010 -->
