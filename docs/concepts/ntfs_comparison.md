# NTFS vs ReFS Comparison

> On NTFS every file's record is in `$MFT` (one MFT record, or several that `$ATTRIBUTE_LIST` links), so only one
> property varies: whether the file's data is resident (stored inside its MFT record) or not. ReFS has two separate properties. Record placement is where the
> file's record is stored: embedded in its directory's name row, or split out into a backing record. Data residency
> is where the file's bytes are stored: inline in the record, or in extents. Both are explained in
> [Record placement and data residency](placement_and_residency.md).

Almost every ReFS forensic mistake comes from applying an NTFS habit to ReFS.

- NTFS is a flat **Master File Table** updated **in place**, with a **redo *and* undo** journal.
- ReFS is a forest of per-object **B+-trees** updated by **copy-on-write**, with a **redo-only** log.

These two design choices affect addressing, residency, slack, snapshots, the change journal, and what a crashed
volume leaves behind. In each of these areas a tool built for NTFS can silently produce wrong output.

This page maps the structures to their NTFS counterparts and, for every difference, states the forensic consequence.

## The two architectures at a glance

| Concept | NTFS | ReFS |
|---------|------|------|
| Volume bootstrap | BPB → $MFT → metadata files | VBR → SUPB → CHKP → 13 B+-tree roots |
| File identification | MFT record number (reusable) | `HomeOID:FileID`: the creation directory's object ID and an ordinal from that directory, neither reused (one exception for the OID on volumes the Windows 10 1803 driver writes: [OID allocation](oid_allocation.md#at-mount)) |
| Metadata storage | MFT records (fixed 1 KiB) | B+-tree entries (variable size) |
| Where the *record* is | One MFT record per file, always in `$MFT` | **Record placement**: `embedded` in the directory name row, or `split` into a backing record — a move or a hard link relocates it |
| Where the *bytes* are | "Resident" if they fit the MFT record's slack; this is the only property that varies, since the record is always in `$MFT` | **Data residency**: `inline`, `extents`, `snapshot-shared` or `unallocated` — decided by the descriptor's form, independently of placement |
| Directory index | B-tree ($INDEX_ROOT / $INDEX_ALLOCATION) | Per-directory B+-tree |
| Address translation | Data runs in $DATA (one level: VCN → LCN) | Two levels: extents (VCN → VLCN), then Container Table (VLCN → PLCN) |
| Attribute model | Named/typed within an MFT record | Named/typed within a B+-tree entry |
| Update model | In-place write + redo/undo journal | Copy-on-write + redo-only log |
| Crash recovery | $LogFile redo and undo | MLog redo only |
| Space management | $Bitmap (bit-per-cluster) | Three-tier allocator |
| Integrity | Update-sequence fixups in each MFT record (a torn-write check, not a checksum of the content) | Integrity streams + metadata checksums |
| Snapshots | Volume Shadow Copy (volume-level) | Per-stream `$SNAPSHOT` attribute |
| Change journal | `USN_RECORD_V2` (64-bit file ID) | `USN_RECORD_V3` (128-bit: creation-directory OID + ordinal) |

The bootstrap row shows the first difference: there is no `$MFT` to scan. Where an NTFS tool walks a contiguous
record array, a ReFS tool must descend the [bootstrap chain](bootstrap_chain.md) — VBR to
[superblock](../structures/supb.md) to [checkpoint](../structures/chkp.md) to the 13 B+-tree roots — and
then traverse trees. The rest of this page is the set of differences that change forensic procedure, not
just terminology.

## Address translation is two-level

NTFS translates a file offset in one step: a data run in `$DATA` maps the file's VCN directly to an LCN, a
real cluster on disk. ReFS adds a virtual layer. A file's extents map VCN to **VLCN** (a position in
the volume-wide *virtual* address space), and only the [Container Table](../structures/container_table.md)
holds the second mapping, VLCN → **PLCN**, the real cluster. The full path is **VCN → VLCN → PLCN**.

The most common ReFS parsing error is to treat a ReFS extent pointer as a physical address, as NTFS data-run
handling does. A tool that does this reads clusters that are not the file's data, and every result derived from
those bytes is wrong. Load the Container Table first, and translate *every* VLCN through it before reading the
disk. [Virtual
addressing](virtual_addressing.md) explains the shift/mask arithmetic and the three bootstrap roots that
are the lone exception (they store real LCNs because there is no table to translate them yet).

## Resident storage thresholds differ by orders of magnitude

In NTFS a file's data is resident only if it fits in the slack of its 1 KiB MFT record — roughly 700
bytes after the record's attributes. ReFS has no fixed record, and it does not
have one threshold: it has a rule with two inputs — **which stream** and **which volume
format** — and for a file's main data on an older format the answer is "never":

| File system | Main `$DATA` | Named stream (ADS) |
|-------------|--------------|--------------------|
| NTFS | inline below ~700 bytes (constrained by the 1 KiB MFT record) | same record, same limit |
| ReFS format ≤ 3.10 | **never inline** — always extents, whatever the size | inline up to a 128 KiB hard cap (`STATUS_FILE_SYSTEM_LIMITATION` above it) |
| ReFS format ≥ 3.11 | inline below 2 KiB\* | inline below 2 KiB\*, then extents |

\* Unless something converts the stream or pre-allocates it: a snapshot, integrity streams (a file created with
them is extent-backed from birth), block cloning, encryption, an explicit set-allocation or set-end-of-file of
2 KiB or more, among the converters the driver calls.

`RefsAddAllocationForResidentWrite` makes this decision. It compares the **volume's** format version against
3.11 before it looks at any size, so the rule depends on the volume, not on the driver mounting it. An up-to-date
driver on an older volume still takes the older path, and upgrading a volume does not move data that is already
written.

A tool calibrated to NTFS's ~700-byte limit under-counts inline files on a **v3.14** volume, where anything
under 2 KiB is in the record. On a **v3.4** volume it has nothing to under-count, because no file's main data is
inline there: the smallest extent-backed file measured is 5 bytes occupying a whole 4 KiB cluster. What v3.4 *can* hide
in a record is a **named stream**, up to that 128 KiB cap.

See [Record placement and data residency](placement_and_residency.md) for the full rule.

## Slack space takes a different form

Both file systems leave deleted data in unused space. Where that space is differs, so the carving target
differs:

| Aspect | NTFS | ReFS |
|--------|------|------|
| Source | Fixed 1 KiB MFT-record tail | Stale rows in variable-length B+-tree pages |
| Mechanism | Unused tail after the record's attributes | Deleted rows left in the page's free space, and in superseded copies of the page |
| Artifact to target | Fixed-size trailing slack at a record boundary | A stale row body inside a live or superseded page |

On NTFS the analyst knows exactly where slack begins — the byte after the last attribute in a 1 KiB record. On
ReFS there is no record boundary: deleting a name row removes its slot from the page's offset array and marks the row, and its bytes
stay in the page's free space until a later rewrite reuses it. Because of [copy-on-write](copy_on_write.md), a
superseded copy of the page written elsewhere can still hold the row as well.

Recovery therefore means scanning page bodies for orphaned rows, not reading a fixed tail — the technique
[Deletion Recovery](deletion_recovery.md) describes.

## The change journal records are wider

NTFS's USN journal uses **V2** records with 64-bit file references. ReFS uses **V3** records with
128-bit references: the upper 8 bytes are the object ID of the directory the file was **created** in (it
does not change when the file is renamed or moved, so it need not be the current parent) and the lower 8
bytes are the file's **ordinal** in that directory (increment-only, never reused). A tool that assumes
V2 layout mis-parses every ReFS USN record. The reason codes themselves are shared between the two file
systems, so once the record is parsed correctly the timeline semantics carry over — `FILE_CREATE`,
`FILE_DELETE`, `RENAME_OLD_NAME`/`RENAME_NEW_NAME`, `BASIC_INFO_CHANGE`, and the rest mean the same
thing. Only the file-ID width and the parsing change. The [USN Journal](../structures/usn_journal.md)
page gives the record layout and the 128-bit ID decomposition.

## Compression operates at a different granularity

NTFS compresses a file's data transparently in the I/O path, with the result visible through the normal file API.

ReFS compression is **per-container, not per-file**, under one volume-wide policy:

- no flag on a file or on an extent entry marks it;
- the work is done by a background job of the deduplication / compaction engine (`refsutil compression /c` only
  sets the parameters);
- the policy is recorded in the Container Table root page, not on the file.

The forensic consequence is that an NTFS-style per-file compression check finds nothing — a tool must read the policy
and the containers instead, and standard Windows APIs (including `fsutil`) do not expose them (`refsutil compression
/q` does). [Compression](compression.md) decodes the parameter record and the algorithm numbers (LZ4 / ZSTD / LZ4QAT
on the 26100 drivers; 17134 numbers other codecs).

## Snapshots are per-stream, not per-volume

NTFS snapshots are a volume-level service (Volume Shadow Copy); recovery means mounting a shadow copy.
ReFS keeps versioning *inside* the file system, as a per-stream `$SNAPSHOT` attribute embedded in the
B+-tree entry:

| Aspect | NTFS | ReFS |
|--------|------|------|
| Level | Volume (VSS) | Per-stream (`$SNAPSHOT` attribute) |
| Management | OS-level Volume Shadow Copy | Embedded in the B+-tree entry |
| Recovery | Mount the shadow copy | Read the attribute structure on disk |

VSS enumeration techniques do not transfer: there is no shadow-copy store to mount. Instead the analyst reads the
[`$SNAPSHOT` attribute](../attributes/SNAPSHOT.md) directly and follows its extents — the same 24-byte extent entries
as ordinary file data — to recover the frozen prior content. A block unchanged since a snapshot is held once and
shared, so a version is read by resolving each file VCN across the file's streams.

See [Snapshots and Versioning](snapshots_versioning.md).

## Security descriptors: same format, different index

The two differ only in how descriptors are indexed; the descriptor *format* is identical:

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

## `$STANDARD_INFORMATION`, byte by byte

Both file systems keep a file's four times, its attributes and its security id in a structure named
`$STANDARD_INFORMATION`. The two structures are not the same size, and only their first 36 bytes and the USN at
0x40 have the same layout.

The figures show one file on two volumes of the test corpus that the same workload wrote: an NTFS volume
(`win11ntfstestmftecmd`) and a ReFS volume (`win11refstestmftecmd`, a public sample). Its Created, Modified and
Accessed times are the same 8 bytes on both.

<div class="hf-pair">

<!-- site: hexfig "si_ntfs_win11ntfstestmftecmd" -->

<!-- site: hexfig "si_refs_win11refstestmftecmd" -->

</div>

### The two layouts, field by field

The NTFS layout is that of Carrier's *File System Forensic Analysis* (2005), chapter 13; the bytes are read from the
NTFS volume's MFT. The ReFS fields are those of the [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md)
page.

| Offset | Size | NTFS field | ReFS at the same offset |
|--------|------|------------|-------------------------|
| 0x00 | 8 | Creation time | Created |
| 0x08 | 8 | Modification time | Modified (the data) |
| 0x10 | 8 | MFT change time | Changed (the metadata; ReFS has no MFT) |
| 0x18 | 8 | Access time | Accessed |
| 0x20 | 4 | File attributes | File attributes, with ReFS's own bits (a directory's 0x10000000 only on some volumes formatted at 3.4 to 3.9) |
| 0x24 | 4 | Maximum versions | Internal flags |
| 0x28 | 4 | Version number | Security ID: 8 bytes, 0x28 to 0x2F |
| 0x2C | 4 | Class ID | (the Security ID's high half) |
| 0x30 | 4 | Owner ID | File size: 8 bytes, 0x30 to 0x37 |
| 0x34 | 4 | Security ID | (the file size's high half) |
| 0x38 | 8 | Quota charged | Allocated size |
| 0x40 | 8 | USN | LastUsn: the file's last change-journal record, as on NTFS |

What differs:

- **Only 0x00 to 0x23 and 0x40 to 0x47 line up:** the four times, the attributes and the USN. A parser written for
  NTFS reads the fields in between, and those after the USN, wrongly on ReFS.
- **The security id** is 4 bytes at 0x34 on NTFS and 8 bytes at 0x28 on ReFS.
- **ReFS keeps the sizes here:** the file size at 0x30 and the allocated size at 0x38 of a file's record (0 on a
  directory). NTFS keeps them in the `$DATA` attribute and in each `$FILE_NAME`.
- **The USN is at 0x40 on both.** ReFS follows it with the journal's id (0x48), then fields NTFS has not: the
  extended-attribute size (0x50; the reparse tag's low half below format 3.10), the reparse tag (0x54), the file's
  ordinal in its directory (0x58), its reference when it sits outside that reference's directory (0x60, 0x68), its link count (0x70) and the next stream-set id (0x74), to 124 bytes (116 on 3.4).
- **NTFS has a second copy of the four times** in each `$FILE_NAME` attribute; ReFS has none. A ReFS file
  whose record is split (a hard link, or a move on a volume with hard-link support) keeps a copy in each name's
  index entry instead (see
  [Timestamps and timestomping detection](#timestamps-and-timestomping-detection)).

## Timestamps and timestomping detection

Both file systems carry four timestamps with identical semantics: creation, modification,
metadata-change, and last access. The difference that matters forensically is how many *copies* of those
timestamps exist:

| Aspect | NTFS | ReFS |
|--------|------|------|
| Timestamp sets per file | `$SI` (one, shared by all hard links) and `$FN` (one per name) | One `$SI` set per file, in its own record; each name's index entry caches a copy |
| Timestomping detection | Compare `$SI` vs `$FN` (different update rules) | Single-named file: the change time, the USN journal and the volume-creation time (below). Hard-linked file: compare Created across the names |
| Corroborating ordinal | — | The file's ordinal from its creation directory (the low half of its File ID) |

The classic NTFS timestomping check — comparing the `$STANDARD_INFORMATION` set against the `$FILE_NAME` set, which
the high-level APIs cannot reach — has no equivalent on ReFS **for a single-named file**, because there is only one
`$SI` set and no `$FN` twin to compare it against.

A **hard-linked file differs**: each of its names caches the file's times in its own index entry, and the copies
**can** hold different times. NTFS's hard links share one `$SI`, while each NTFS link has its own `$FILE_NAME` with its
own times, so the ReFS per-name copies are closer to those. The difference can be used, but only within limits, and
a later read can erase it:

- A `SetFileTime` through one name writes the file's **own record**, which every name shares, so the file's own
  times change at once; what can disagree is each name's **index entry**, a copy the driver refreshes for a name when the
  file is opened, read and closed through it.
- A sibling nobody has opened since the stomp still carries the pre-stomp times — and the next read through it, an
  antivirus scan included, refreshes that entry and destroys the difference (a directory listing alone did not, on
  the lab volume measured).
- A difference between the names' **Created** times is therefore evidence to follow up (their Changed times differ
  routinely). **Equal Created times do not show that the file was not stomped**: they are equal either because the
  times were not changed, or because somebody read the file through that name since.

See [Hard Links](hard_links.md).

For single-named files, timestomping is nonetheless detectable by three other means:

- The metadata-change time (`$SI`+0x10) is filesystem-controlled and not reachable through the high-level APIs
  common tools use (`SetFileTime`, PowerShell), so back-dating Created and Modified leaves the change time far later
  than both.
- The USN journal, when the volume has one that covers the period, records the edit itself (`BASIC_INFO_CHANGE`) and
  the true creation (`FILE_CREATE`). Of the three, the USN journal is the most robust.
- The volume-creation time is a floor for a file created on the volume (a copy or a restore that keeps the creation
  time brings an older one).

The file's ordinal — assigned from its creation directory's monotonically increasing child-creation counter, and
kept as the low half of its File ID — corroborates creation order within that directory independently of the
timestamps. [Timestomping Detection](timestomp_detection.md) develops the full method.

## Logging and recovery: redo only, no undo

NTFS's `$LogFile` carries both redo and undo records; undo exists because in-place updates must be
rollable-back. ReFS's MLog is **redo-only**, and the reason is structural: because metadata is updated by
[copy-on-write](copy_on_write.md), an interrupted transaction never overwrote the prior state, so there
is nothing to undo. The log only needs to record *what to re-apply*.

| Aspect | NTFS | ReFS |
|--------|------|------|
| Log type | Redo + undo | Redo only |
| Pre-images in the log | Yes (undo records) | **No** |
| Why | In-place updates need rollback | CoW makes undo unnecessary |
| Prior states from the log | Read `$LogFile` backward | **No pre-images** in MLog; older redo records still in the log hold the values earlier transactions wrote |
| Prior-state alternative | — | Scan for dereferenced CoW pages on disk |

For recovering a prior state, ReFS has the advantage. On NTFS, recovering a prior state from the journal
works only until the circular log wraps and an in-place overwrite destroys the old bytes.

On ReFS the log holds no pre-images at all — but it does not need to, because every modified B+-tree page was written to a
*new* cluster, leaving the old page intact on disk until the allocator reuses its clusters. The recovery window is
therefore governed by allocator pressure, not by log wrap. (The log still helps: an older redo record holds the
values its transaction wrote, such as the creating transaction's times of a file whose `$SI` was later back-dated.)
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
| `$Reparse` | "Reparse Index" in OID 0x520 (v3.4–v3.7) / standalone OID 0x540 (all versions) | v3.4 and v3.7 have both a file-entry wrapper in OID 0x520 and the standalone OID 0x540 B+-tree; v3.9+ keeps only the standalone OID |
| `$ObjId` | No equivalent | ReFS does not implement distributed link tracking |
| `$Quota` | No equivalent | ReFS does not support NTFS-style disk quotas |
| `$RmMetadata` | No equivalent | ReFS has no transactional resource manager |

On v3.4 through v3.7, OID 0x520 also holds two "degenerate" children with no NTFS analogue — a
**Security Descriptor Stream** (a file-entry wrapper for OID 0x530) and a **Volume Direct IO File** (a
DASD placeholder for raw volume I/O). These are backward-compatibility wrappers: a 26100 driver creates them
(`CreateDownlevelDegenerateMetadataObjects`) at a mount that writes, on a volume of version 3.7 or earlier, and v3.9
and later volumes do not hold them (what creates them on a volume formatted by 17134 is not read); the standalone OIDs they reference
(0x530 for security, 0x540 for reparse) persist on every version. An upgraded v3.4→v3.14 volume keeps the
original degenerate children, which makes their presence a marker of original-format provenance. The
full child table is in [System OIDs](../structures/system_oids.md).

## File identity and creation-order reasoning

NTFS reuses MFT record numbers after deletion, which is why MFT position is only a *partial*
chronological signal — a low record number can belong to a recently created file that reclaimed a freed
slot. ReFS numbers two things and reuses neither. A directory gets a 64-bit object ID from a volume-wide
counter that only increases; a file has no object ID of its own: its reference is its creation
directory's object ID plus an ordinal from that directory's own counter, and it is the 128-bit file ID
the [USN](../structures/usn_journal.md) journal records. That gives the analyst an ordering NTFS does
not: a lower directory OID is older, and among the files of one creation directory a lower ordinal is
older; a gap in either sequence marks an identifier issued and no longer seen: a deletion, a creation
that failed (an OID), or, on a volume without hard-link support, a move into that directory (an ordinal:
the moved file keeps its first reference).

See [Object IDs](object_ids.md) and
[File Identifiers](file_ids.md) for the two counters and how to read their gaps.

## What this means for an NTFS-trained tool

Grouping the differences by the kind of change they force on a tool:

**No ReFS equivalent: the NTFS technique does not apply.** Several NTFS *attribute names* have no
ReFS counterpart (`$FILE_NAME`, `$ATTRIBUTE_LIST`, `$EXTEND`, `$OBSOLETE`, `$VOLUME_NAME`, `$OBJECT_ID`,
`$INDEX_ALLOCATION`); see [Attributes — Forensic Reference §4](../attributes/README.md) for what each maps
to. NTFS techniques that do not apply to ReFS:

- MFT-array scanning — there is no flat metadata table; the closest analogue is MSB+ page-signature
  carving.
- The `$FN`/`$SI` timestomping cross-check — a single-named ReFS file has one `$SI` set and no `$FN`
  twin; use the change-time + USN + volume-creation method instead. A hard-linked file is the exception:
  each name caches the file's times, so its names' Created times can be compared directly (see
  [Timestomping Detection](timestomp_detection.md)).
- `$LogFile` undo-record analysis — MLog is redo-only.
- Volume Shadow Copy enumeration — versioning is per-stream `$SNAPSHOT`, on disk.

**Structurally similar — reuse the parser, change the lookup.**

- Security-descriptor analysis: the blob format is identical; reroute the lookup from `$Secure` to OID
  0x530.
- Four-timestamp interpretation: unchanged for the `$SI` set.
- Inline-file extraction: same idea, a different and format-dependent threshold (2 KiB on format 3.11+, and on
  older formats no main-data inlining at all), not NTFS's ~700 bytes.

**Same capability, different mechanism.**

- *Previous-state recovery*: NTFS reads its log backward; ReFS scans for dereferenced CoW pages, with a
  recovery window bounded by allocator reuse rather than log wrap.
- *Creation-order reasoning*: NTFS uses MFT positions (weakened by reuse); ReFS uses monotonic directory OIDs and
  per-directory file ordinals (strict order; a gap is a deletion, a failed directory creation, or, without hard-link support, a move into the
  directory).
- *Transaction classification*: NTFS `$LogFile` carries named operation codes; on ReFS the MLog redo
  opcodes (`CmsLogRedoQueue::PerformRedo` dispatches to 26 distinct handlers on v3.4 and ~39 on v3.14) can be
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
- [Record placement and data residency](placement_and_residency.md) — the format-gated residency rule versus NTFS's
  ~700-byte line
- [Deletion Recovery](deletion_recovery.md) — recovering stale B+-tree rows, the ReFS analogue of
  MFT-record slack
- [Object IDs](object_ids.md) — monotonic 64-bit OIDs versus reusable MFT numbers
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

The mechanism-level facts are confirmed in the decompiled driver and corroborated on the raw-disk corpus.

- The residency rule (main data never inline before 3.11, named streams inline up to 128 KiB there, 2 KiB from
  3.11) comes from `RefsAddAllocationForResidentWrite` /
  `RefsConvertToNonResident`.
- The redo-only log model and the per-opcode dispatch are from `CmsLogRedoQueue::PerformRedo` (26 distinct handlers
  on v3.4 / 17134, ~39 on v3.14 / 26100).
- The 128-bit USN V3 record (creation-directory OID + ordinal) is confirmed on disk.
- The NTFS side is measured on the corpus's two NTFS volumes (`win11ntfstestmftecmd`, `win11ntfs`) with a minimal
  reader: MFT records of 1,024 bytes, each with valid update-sequence fixups (1,567 and 786 records); MFT entry 9 is
  `$Secure`, with the `$SDS` stream and the `$SDH` / `$SII` indexes; a user file's record could hold at most 716 to
  721 bytes of data inline; the journal's 9,088 records are all `USN_RECORD_V2`, each with a 64-bit reference (a
  48-bit record number and a 16-bit sequence); 225 and 132 in-use records carry a sequence number above 1 (an NTFS
  system file's sequence equals its record number; for the others a sequence above 1 means the record number was
  used before). Neither volume holds a compressed file.
- Security descriptors in OID 0x530 and the `$Extend`-equivalent OID 0x520 children (built by
  `CreateDownlevelDegenerateMetadataObjects`) are confirmed in the driver.
- The monotonic-OID chronology contrast with reusable MFT numbers is confirmed on disk.
- The compression difference — a volume policy in the Container Table root page, applied by a background job, with
  no extent flag — and the child-creation ordinal are registered findings.

See [how this was verified](../methodology.md) to trace these to the exact images and
measurements in `analysis/`.

<!-- findings: AP_REDO_037, MD_SI_RA_008 -->
