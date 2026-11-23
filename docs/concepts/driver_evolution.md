# Driver Evolution

The ReFS driver, `refs.sys`, changes between most of the builds read even where the on-disk format does not. This
page says what changed between the builds read, which driver functions decide how a file is stored, and what this
means when you read a volume.

- The builds read, and how each one was read, are listed on [Driver builds analysed](../methodology/driver_builds.md).
- The changes between on-disk formats (3.4 to 3.14) are on [Version Evolution](version_evolution.md).

For every Windows 11 26100 build read, the changes are servicing work and the on-disk format is untouched. The
Insider builds change how a few records are written (below).

## What changed, build to build

### 26100.8115 to 26100.8521

Small. An access-violation fix arrived behind a flag named for fuzzing, and two earlier feature flags were
**graduated** — the flag was removed and the behaviour became unconditional. The two functions that changed
most are the ones that find a starting node in a tree and the one that deallocates ranges.

### 26100.8521 to 26100.8972

The largest step: 69 functions changed size, against 6 in the previous step. Almost all of it is
internal tidying. Two changes are easy to misread, so they are stated precisely here.

**`RefsUpgradeVolume` did not disappear — it was folded into the function that called it.** It had exactly
one caller; in the newer build that caller absorbed it and grew by roughly 250 lines. Volume upgrade works
exactly as before. A diff that only lists added and removed names reports this as a removed capability,
which would be wrong.

**A predicate was renamed, and the new name is more accurate.** What the older build called
"does this stream have checksums" the newer one calls "does this stream use copy-on-write". The code is
identical — same field, same callers — so nothing about behaviour changed; Microsoft corrected the name.
The field it reads means *uses copy-on-write*.

Three other functions were renamed, one of them from a DES key-blob comparison to an AES one (`EfsSameDesKeyBlob`
→ `EfsSameAesKeyBlob`). Two flags covering trash-table work graduated.

### 26100.8972 to 26100.9444

Small, with one item of substance: a **security fix in the memory-mapped read path**. A new range check
validates that an offset is non-negative, does not run past the end, and that offset plus length lands
exactly on the end. It is reached from one function and sits behind a servicing flag. Separately, several
encryption functions grew; that work is unrelated to the fix.

### 26100.9444 to 26100.9549

No code change: the functions are the same.

### 26100.9549 to 26100.9711

A **mount policy for external disks**: a setting of the system (not of the volume) makes the driver warn about, or
refuse to mount, a ReFS volume on a USB, 1394 or removable disk; it writes nothing to the volume. Input validation was
added for schemas and for the `$EFS` stream. Everything this site documents is unchanged.

### 26100.9711 to 26100.9818

A **merge on deletion is paced** (behind a servicing flag): when the log is full, the merge that releases a deleted
tree's references is retried later instead of failing. The compression library was updated.

The functions behind this site's statements are the same in both builds, compared as decompiled code and as
instructions, apart from the two merge functions above and the jump-table addresses of one directory function.

### 26100.9818 to 26100.9974

Microsoft has not published the symbols of this build, so it was compared with .9818 by its machine code: every
function is the same apart from moved addresses, except one changed function and the two new functions of a new
feature flag. Behind that flag, the creation of a table set and of its first stream runs as one action, completed or
undone together. Nothing on disk changes.

### Insider 29574 to 29659 to 29683

The Insider line is rebuilt widely between these builds, so each statement was read in each build rather than
compared. The choice of the checkpoint copy, the two clocks a log record carries, the checks made when the log is
opened, the checkpoint's flag bits, the hard-link switch and the boot sector's tests are those of 29574.

What changed:

- **29683 logs a table deletion with record number 0x2D**, where every earlier build read uses 0x0F; its replay is the
  same, and 26100, 29574 and 29659 refuse a 0x2D record.
- 29659 and 29683 no longer read record 0x16's value (26100.9818 and 29574 read it as a range and do not use it).
- 29659 and 29683 read a log record's object id from its key when they decide whether to replay it, and no longer
  replay a record of the table {0, 0x100} without testing its log position.

See [MLog](../structures/mlog.md).

## A driver's version is not a volume's format

These are two different numbers, and they are easily confused:

- **The volume's format** — what the filesystem on the disk actually is; the newest format any released
  Windows writes is **3.14**.
- **The driver's version** — which build of `refs.sys` is doing the reading. A preview driver (Insider 29574)
  reports a *maximum supported version* of **3.15**.

A driver also records itself on the volume: `$VOLUME_INFORMATION` keeps the driver of the last mount that wrote to
the volume, separately from the volume's own format (a mount that writes nothing, such as one through a write
blocker, leaves it, and a later writing mount by another driver replaces it). So a 3.14 volume whose last writing
mount was by a preview build carries format 3.14 and driver 3.15 — a signal that a preview build wrote to it, which
says nothing about the format.

**No volume of the corpus is formatted 3.15: 3.15 is the highest format the Insider 29574 driver reports it can write, not the format of any volume here.**

See [Volume Information](../structures/volume_info.md) for the two fields and
[Format Support](../format_support.md) for what has been measured on what.

## What this means for reading a volume

Nothing on disk changed across the Windows 11 26100 builds. Every structure this site documents is identical in all
of them, among them:

- how a record is framed, and where a directory's flag lives;
- the limit on storing a file's bytes inside its record;
- the checksum algorithm and the journal's dispatch table;
- the way containers translate addresses, and the tree search that walks into an embedded sub-tree.

So **a volume written by any of these builds is read the same way**, and an
examiner does not need to know which servicing update wrote a volume in order to interpret it. A volume an
Insider build wrote can hold what no released build writes: Insider checkpoint records carry an attestation area
([Checkpoint](../structures/chkp.md)), and a log written by 29683 records a table deletion as 0x2D.

## The functions that change a file's storage

Two different things get called "making a file non-resident", and different driver code decides them:

- **Record placement**: is the object's record embedded in its name row, or split out into its own type-0x40 backing
  record? Moves and links change this, on volumes with hard-link support.
- **Data residency**: are the stream's bytes inline in that record, or in extents? Writes, snapshots and encryption
  change this; a file created under integrity starts in extents.

Neither implies the other: see [Record placement and data residency](placement_and_residency.md). The table lists the
functions that change a file's storage, what each one changes, which builds have it, and its on-disk witness.

### The functions

| Function | Changes | Builds | Confirmed on disk |
|---|---|---|---|
| `RefsMoveFile` | **placement only** (a split, on volumes with hard-link support) | all | yes — controlled before/after move |
| `RefsAddLink` / `RefsRemoveLink` / `RefsSetLinkInfo` | **placement only** | all | yes — a hard-linked pair: two names, one backing, its data inline |
| `RefsAddAllocationForResidentWrite` | **residency** — the gate itself | all | yes — the largest inline main stream read on 3.11+ volumes is 2,047 B |
| `RefsConvertToNonResident` | **residency** — inline → extents | v3.14-era only; **absent from win10 17134** | — |
| `RefsCreateStreamSnapshot` | residency (snapshot) | v3.14-era | yes — 12 small snapshotted streams |
| `RefsSetEncryption` | residency (EFS) | v3.14-era | yes — 13 encrypted files, all extent-backed |
| `RefsDuplicateExtents` | residency (block clone) | v3.14-era | — |
| `RefsCascadesSetFileRemote` | residency (tiering) | v3.14-era | — |
| `RefsSetFileStrictlySequential` | residency | v3.14-era | — |
| `RefsSetAllocationInfo` / `RefsSetEndOfFileInfo` | residency, when the size set is 2 KiB or more | v3.14-era | the allocation, yes — one lab file; the end of file set before any write, no (see below) |
| `RefsReplaceDataAttribute` | residency | v3.14-era | — |
| `RefsChangeResidentStreamIntegrity` | none — enabling integrity leaves an inline stream inline | all | yes — controlled lab pair (below) |
| `RefsTelemetryUnsupportedADS` | none — reports the 128 KiB **named-stream** cap | win10 17134 | — |
| `RefsCheckValidResidentDataAttribute` | none — validates a resident `$DATA` | v3.14-era only | — |

The rows marked "residency" are exactly the callers of `RefsConvertToNonResident` — the complete set, taken
from every call site in the v3.14 decompilation.

**No rename, move or link function is in it**: none of those function bodies contains a call, on win11 26100 or win10
17134, by a scan control-tested against six known callers. Nor is `RefsChangeResidentStreamIntegrity`: a stream
written first and given integrity afterwards stays inline, while a file *created* in a directory that already has
integrity on is extent-backed from the start (a creation path, not a conversion).

There is no `ConvertToResident` in any build: a stream converted to extents is not converted back.

### The gate

`RefsAddAllocationForResidentWrite` branches on the **volume's** format version, read from the VCB at
`+0x318`/`+0x319` and compared against `0x30b` (3.11):

```c
if (volume_format < 0x30b && 0x20000 < new_size)   // < 3.11 and > 128 KiB
    raise STATUS_FILE_SYSTEM_LIMITATION;           //   = the NAMED-STREAM cap
if (volume_format < 0x30b || new_size < 0x800)     // < 3.11, or < 2048 bytes
    stay inline;
else
    convert to extents;
```

Because the field is the volume's, a current driver mounting an older volume takes the older path — and an
upgrade changes only future writes. On a v3.4 volume upgraded to v3.14, no pre-existing file changed
residency.

### What is measured, and what is not

**The split mechanism is measured, not explained.** That a move or a hard link forces the record split on a
volume with hard-link support is established directly: on a controlled before/after move of a whole volume, 5 files
changed placement and 0 changed residency. Without hard-link support a move keeps the record embedded and moves it
whole (measured on several volumes, a lab volume among them).

*Why* the split is required is a different claim. The usual explanation — that only the split layout has the
`value+0x08` field carrying the frozen creation-directory home — is an **inference**.

`RefsMoveFile` (win11 26100 @`1400e9500`, 277 lines) calls `MsReparentChildTable`, `RefsCreateFileId2`,
`RefsDeleteFileId2`, `RefsConvertToStandardInfoExternalId` and `RefsPersistNextFileId`; it references no such
offset, and contains no call to `RefsAddLink` or `RefsRemoveLink` at all. The observation stands; the mechanism does
not yet have a driver citation.

**One trigger is measured on one file.** On format 3.11+ volumes, about half the sub-2 KiB extent-backed main
streams have no identified trigger. Their mix suggests a pattern rather than chance: ETW `.etl` loggers,
`Diagnostic.log`, browser-cache entries, and a uniform 128-byte generator series. That is what a writer that sets
the allocation *before* writing would leave.

On a lab volume, setting a file's allocation to 1 MiB before writing left a 16-byte file extent-backed while controls
of comparable size stayed inline; setting the end of file before any write (`fsutil file createnew`) does not, and an
Edge download's 128-byte `Zone.Identifier` stayed inline. In the driver both paths convert only when the size set is
2 KiB or more. Whether the unexplained streams' writers set their allocation is not shown.

## Cross-references

- [Driver builds analysed](../methodology/driver_builds.md): the builds read, and the volumes each is known to have
  written
- [Version Evolution](version_evolution.md): what changed between on-disk formats
- [Driver Interface](driver_architecture.md): what the imports, embedded codecs and class tables reveal about which
  features a build can produce, and where these functions sit
- [Record placement and data residency](placement_and_residency.md): the two properties and the format gate
- [Copy-on-Write](copy_on_write.md) and [Integrity Streams](integrity_streams.md): the snapshot trigger, and integrity
  at a file's creation
- [Hard Links](hard_links.md): what the split means for a link group
- [$DATA](../attributes/DATA.md) / [$NAMED_DATA](../attributes/NAMED_DATA.md): the descriptor forms
- [Format Support](../format_support.md): which ReFS formats each area's statements were confirmed on

## Evidence

- **Static:** `refs.sys` win10 17134 (v3.4), win11 26100 and 26100.8521 (v3.14), Insider 29574. The caller set is
  taken from every call site in the v3.14 decompilation (re-listed on 26100.8115), and the absence scan was
  control-tested against six known callers. The set-allocation and set-end-of-file conversions test the size set
  against 0x800 on format 3.11+ (26100.8115).
- **On disk:** 79 distinct volumes. The controlled witnesses are a before/after cross-directory move, a hard-linked
  300-byte pair whose two names resolve to one backing, and a lab volume with three arms of 512- and 1,500-byte
  files: integrity enabled after the write (inline), created under integrity (extents, a full cluster) and a control
  (inline). The snapshot and encryption witnesses are file populations rather than controlled pairs.
- **The counts behind the text:** the rename, move and link function bodies scanned are 17 on win11 26100 and 18 on
  win10 17134, 0 with a call; on the v3.4 volume upgraded to v3.14, 0 of 262 pre-existing files changed residency; 44
  of the 86 sub-2 KiB extent-backed main streams on format 3.11+ volumes have no identified trigger; a move without
  hard-link support kept the record embedded on 8 volumes.

<!-- findings: FS_MOVE_RA_002, FS_RESD_SA_001, FS_RESD_SA_002, GN_VCB_SA_001, MD_ADS_RA_003, MD_DATA_RA_025,
               MD_EFS_RA_003, MD_SI_RA_007 -->
