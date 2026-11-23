# Timestamp Sources and the Super-Timeline

> **Experimental / informational.** The super-timeline (`forefst.py <image> timeline`) merges USN, MLog and `$SI`
> rows and sorts them by time. It does not join them, so one file can appear under different identities: its home
> directory's OID on its `$SI` and USN rows, the directory the transaction changed on an MLog row.
>
> It is a corroborative reconstruction, not an authoritative log. Its reach depends on what the volume kept: a data
> volume has no USN journal until one is created, and the MLog is a circular buffer whose reach depends on its size
> and on how much has been written since. Use it to build and cross-check leads against the underlying artifacts,
> not as a standalone source of truth.

Most filesystem investigations are built on times. ReFS records them in five sources that an analyst reads
separately and then reconciles:

- the per-file `$SI` MACB times;
- the USN change journal;
- the MLog transaction log;
- the checkpoint virtual clock;
- the volume's creation time.

No single one of them is a complete history, and they are not equally trustworthy. Nor are they independent of each
other: the MLog's times are values its transactions wrote into `$SI` and volume rows.

This page catalogues the main timestamp sources you can read off a ReFS image, how to read each one, and how to
cross-validate them against each other. The cross-validation is the part that matters forensically.

That cross-validation is the foundation of [timestomp detection](timestomp_detection.md). On ReFS an inconsistency
*between* these sources is what reveals an edit, because a single-named file has no second timestamp set to compare, as NTFS has
in `$FILE_NAME`. A hard-linked file is the exception: each of its names caches the file's times in its own index
entry, and the caches can diverge (see below).

> **Read the times with care.** Every file and directory carries four times in its `$STANDARD_INFORMATION`:
> Created, Modified (the data), Changed (the metadata) and Accessed. Two cautions before you build a timeline
> on them:
>
> - **Accessed is usually not maintained.** Windows does not update it on read unless last-access updating is
>   turned on, a setting of the machine, not of the volume. Treat it as weak, and look at whether it ever moves
>   past Modified and Changed (`summary` tells you when some files show it was on at some point).
> - **Times can be set by a program.** `timestomp` looks for the traces a backdating leaves: a Created time
>   before the volume existed (a copy that keeps its times leaves it too), a Changed time later than the others in
>   a way a copy does not produce, the journal recording a change of basic information, or the names of
>   a hard-linked file disagreeing on their Created time. It grades what it finds; its strongest grade needs
>   corroboration from the journal or a second name, and its weakest findings are leads, not conclusions.
>
> See [Timestomp detection](timestomp_detection.md).

## One timestamp set per file, a cached copy per name

ReFS keeps a file's four times once, in the file's own record, in
[`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) (`$SI`) at offset `0x28` of the record's value:

- a directory's own type-0x10 row;
- a file's embedded type-0x30 [directory-entry](../structures/directory_entries.md) row;
- a split file's type-0x40 backing (its name row then caches the times at value+`0x10`).

For a single-named file there is no `$FILE_NAME` twin as on NTFS to compare `$SI` against. That is why the
cross-validation uses the USN journal, the MLog and the volume's creation time. The checkpoint clock orders states
but gives no date.

Every FILETIME on ReFS is a little-endian `u64` counting 100-ns intervals since 1601-01-01 UTC, converted with the
standard FILETIME epoch.

The one exception is a **hard-linked file**. Its times are in its own record (the type-0x40 backing), and each name's
index entry carries a cached copy, so a file with N names has one set and N copies. (NTFS's hard links share one
`$SI`; each NTFS link has its own `$FILE_NAME`, with its own times.)

The copies **can** hold different times. A `SetFileTime` through one name updates the file's own record at once, but
refreshes only that name's entry; the other names keep their old times until the file is opened, read and closed through each of them
(a directory listing does not refresh them).

- A disagreement between a file's names on **Created** is evidence worth following.
- A disagreement on **Changed** is routine: each name's entry is refreshed at its own moments.
- Agreement does not show that the times were not edited: a read of the file through a stale name (an antivirus
  scan, a live triage) erases the difference.

The [timestomp detection](timestomp_detection.md) page turns this into the `HARDLINK_MACB_MISMATCH` signal, which
tests Created only.

The remaining four sources are not per-file metadata at all; they are **volume-level event and
clock artifacts**, each with a different relationship to wall-clock time:

```text
 ┌──────────────────────────────────────────────────────────────┐
 │ $VOLUME_INFORMATION +0x90 → volume creation                   │
 ├──────────────────────────────────────────────────────────────┤
 │ $SI Created/Modified/Changed/Accessed → the file's own MACB   │
 ├──────────────────────────────────────────────────────────────┤
 │ USN $J records (+0x30 FILETIME) → per-operation event log     │
 ├──────────────────────────────────────────────────────────────┤
 │ MLog redo records (embedded FILETIMEs) → times txns wrote     │
 ├──────────────────────────────────────────────────────────────┤
 │ CHKP virtual clock (+0x60) → checkpoint sequence number       │
 └──────────────────────────────────────────────────────────────┘
```

Conceptually they divide like this:

- `$SI` is the *current* state: the live row holds only the latest four times (earlier versions of the row can
  survive; see [Building a super-timeline](#building-a-super-timeline)).
- The USN journal is the *history* of how it got there, kept in a fixed-size ring that overwrites its oldest records.
- The MLog holds every transaction its circular buffer has not yet overwritten, whether or not it has been folded
  into a checkpoint.
- The CHKP virtual clock is an *ordering* — a count of checkpoints, not a wall clock.
- The volume's creation time is the reference `PRE_FORMAT` compares Created against. It is a floor for files created
  on the volume, not for `$SI` times in general: copies and restores carry older times from other volumes.

Three more fields carry a time and are not timeline rows:

- a stream snapshot's descriptor holds the moment the snapshot was taken, so a Created time later than it is a
  contradiction between two structures (see [Snapshots and versioning](snapshots_versioning.md));
- `$SI+0x48`, the UsnJournalId, is a FILETIME naming the journal instance (see the pitfalls below);
- the Object Table's per-object log sequence number orders an object's last write in log time, not in wall-clock
  time.

## The five sources in detail

| Source | Field | Offset | Meaning | How to read |
|--------|-------|--------|---------|-------------|
| **`$SI`** | Created (B) | value `0x28`+`0x00` | File creation | FILETIME `u64` LE; `$SI` starts at offset `0x28` of the object's record value (a directory's type-0x10 own row; a file's embedded type-0x30 name row, or its type-0x40 backing once split) |
| **`$SI`** | Modified / LastWrite (M) | value `0x28`+`0x08` | Last data write | FILETIME `u64` LE |
| **`$SI`** | Metadata-Change (C) | value `0x28`+`0x10` | Last metadata change (the metadata change time) | FILETIME `u64` LE; **not** reachable by `SetFileTime`/PowerShell/.NET |
| **`$SI`** | Accessed (A) | value `0x28`+`0x18` | Last access | FILETIME `u64` LE; not updated on read by default (registry `RefsDisableLastAccessUpdate`=1; 0 enables it) |
| **Split name row** (cached copy) | B/M/C/A | value `0x10`/`0x18`/`0x20`/`0x28` | A split file's four times, cached in its type-0x30 name row | FILETIMEs sit at value+`0x10` (after the 16-byte ordinal + home-dir-backref header), **not** value+`0x28`; the file's own `$SI` is in its type-0x40 backing at value+`0x28` |
| **USN `$J` record** | Timestamp | record `0x30` | Wall-clock time the operation was journalled | FILETIME `u64` LE; record at `OID 0x520` "Change Journal" → `$J` stream |
| **USN `$J` record** | Reason | record `0x38` | Which operation (bitmask) | `u32` LE; see reason codes below |
| **USN `$J` record** | USN | record `0x28` | Virtual byte offset of this record in the journal (the file's `$SI`+0x40 LastUsn points here) | `u64` LE; increasing within one journal instance (`fsutil usn createjournal` over a journal restarts it at 0); can far exceed the `$J` allocation, because `$J` is an in-place ring |
| **USN `$J` record** | File ID / Parent ID | record `0x08` / `0x18` | The file's fixed identity vs its parent at the time of the record | two `u128`; **File ID** = `(HomeOID, ordinal)` — the creation directory OID + ordinal, unchanged by rename or move; **Parent ID** = the parent when the record was written (records written after a move carry the new one) |
| **MLog redo record** | Embedded times | opcode-specific | FILETIME values the logged transaction wrote (a file's `$SI` times, or the volume's format and mount times) — not a clock of the operation | FILETIME `u64` LE inside the `_SmsRedoRecord` value data (record+`0x38`+); **no dedicated header timestamp field** |
| **CHKP** | Virtual clock | CHKP `0x60` (header copy `0x10`) | Counter of checkpoint writes (NOT wall clock) | `u64` LE; higher = newer checkpoint; allocator clock at `0x68` ≤ virtual clock |
| **`$VOLUME_INFORMATION`** (`OID 0x500`, key 0x0520) | Volume creation time | key value `0x90` | Volume format time — a floor for files created on the volume (a copy or a restore brings an older time) | FILETIME `u64` LE; set at format (see [Version and state differences](#version-and-state-differences)). At `0xA0`, the time of the last mount that writes |

Almost every first parser gets two properties wrong:

1. **The MLog has no timestamp in its record headers.** An [MLog](../structures/mlog.md) record is a LogCore
   header, an entry header, then a chain of up to 15 merged redo blocks, each holding `_SmsRedoRecord` entries. It
   carries an LSN and a per-record integrity value, not a wall clock.

   The *only* times in the log are FILETIME values in the redo records' value data, at opcode-specific offsets: a
   file's `$SI` times (`InsertRow`/`0x01` carries B/M/A/C), and in volume-information updates the volume's format
   and mount times.

   These are values the logged transactions wrote into the rows, not a clock of the operation:
   - close to the operation time for a create or a write;
   - the object's older time for a rename or a move;
   - the forged value, in a payload that rewrites a back-dated file's row.

   Most log payloads carry a time, not all: system and allocator operations typically carry none.

   See [Timestamp extraction](../structures/mlog.md#timestamp-extraction) on the MLog page for the per-opcode
   offsets.

2. **The CHKP virtual clock is an ordering, not a clock.** It is a monotone counter of checkpoint writes, held in the
   [checkpoint](../structures/chkp.md) at `+0x60`. How many checkpoints a workload produces depends on what ran and
   for how long, so the value measures neither file operations nor transactions (values read are in the Evidence
   section).

   It tells you the *relative order* of metadata states; it does **not** map to a wall-clock time. Use it for
   sequencing and for selecting the current vs. previous consistent checkpoint, never for dating an event.

### USN reason codes worth recognizing on a timeline

The reason bitmask at USN record `+0x38` is what makes the journal a log of *events*, not only of
timestamps. The codes below matter most forensically:

| Reason | Hex | What it means on the timeline |
|--------|-----|-------------------------------|
| File create | `0x00000100` | File or directory creation — records the true creation time |
| Data overwrite / extend | `0x00000001` / `0x00000002` | Content was written |
| File delete | `0x00000200` | File deleted |
| Rename old / new name | `0x00001000` / `0x00002000` | The two halves of a rename |
| Basic info change | `0x00008000` | Timestamp or attribute edit — a back-date writes it, and so do `robocopy /COPY:DAT`, archive extraction and attribute changes |
| Reparse point change | `0x00100000` | Junction / symlink creation |
| Close | `0x80000000` | OR-ed onto the final reason for a handle |

## Building a super-timeline

A ReFS super-timeline is built from:

- four `$SI` MACB rows per file, harvested from the directory-entry walk;
- one row per USN `$J` record — a wall-clock event log, but only when the volume has a journal;
- optionally the MLog-embedded times of every transaction the log still holds.

The `$VOLUME_INFORMATION+0x90` creation time is a reference point: events on the volume follow it, while `$SI` times
brought by copies may precede it.

Each source contributes something the others cannot:

- **`$SI` is the current state.** The live row holds the latest four times, and it is what a timestomp tool forges.
  Earlier versions of the row can survive in node slack and unreferenced pages (`deleted --full` lists them) and can
  hold the times from before an edit. A later MLog payload that rewrites the row carries the forged values too, and its change time is the moment of
  the edit when the program leaves that field to the file system (a plain copy carries its source's); the log keeps the
  earlier values until they are overwritten, and the USN journal dates the edit itself.
- **The USN journal is the history.** It records the *operation itself* with its real wall-clock time at record
  `+0x30`. Only the file-system driver writes it, so it cannot be edited through the file APIs; it can still wrap, be
  re-created, or be edited on the raw disk.

  A data volume has no USN journal until one is created (`fsutil usn createjournal`, or an application),
  so on many images there is no journal to check against. (A Windows system volume on ReFS in
  the corpus carried one.)
- **The MLog can surface operations the journal does not hold** — operations made before the journal was created,
  for example — whether or not they have been checkpointed. It is a circular buffer, so its reach depends on its
  size and on how much has been written since.

In practice `forefst.py <image> timeline` merges the three sources (USN events, MLog log payloads, per-file MACB) into
one list sorted by time; it does not join them. `summary` prints the volume's creation time, the reference point for the list.

How the MLog rows are dated:

- a row's time is the latest time its log payload's records carry (a payload can merge up to 15 redo blocks);
- a payload that carries none takes the time of its paired `$SI` update, or is left out (and counted);
- a row whose derived time predates the volume is undated and marked.

**Correlate on the File ID, not the path.** A file's identity — its FileRef `(HomeOID, ordinal)`, which is the
USN File ID — is fixed across renames and cross-directory moves, while its path is not. A move changes the Parent ID
and the name but leaves the File ID untouched (unchanged across every real move measured).

Correlating a file's USN and `$SI` rows on the **File ID** (the ObjectRef column of `usn --csv` and of `files --csv`)
therefore follows it through every rename and relocation. A path- or name-keyed join would split one file's history
into several unrelated fragments — or, worse, merge two different files that happened to occupy the same path at
different times. When a file has been moved, its `$SI` sits under the new path while older USN records name the old
one; the File ID links the two.

An MLog row carries no File ID: it names the table its records change (a directory, by its OID and its path today),
so it is matched to a file by that directory and the name, not by identity.

See [File IDs](file_ids.md).

## Pitfalls that corrupt a ReFS timeline

- **Do not look for a `$FN` twin.** For a single-named file there is no second timestamp set on ReFS to
  cross-check `$SI` against — use the metadata-change time, the USN journal, the MLog and the volume's creation time
  instead.

  A hard-linked file is the exception: each name caches the file's times in its own index entry, so comparing the
  names' Created values can reveal an edit made through one name.
- **Embedded vs. split offset shift.** An embedded file's row carries the four FILETIMEs at value+`0x28`. A split
  file's name row caches them at value+`0x10` (after the 16-byte ordinal + home-dir-backref header), while its
  type-0x40 backing holds its own `$SI` at value+`0x28`.

  Parsing a split name row with the embedded offset reads 24 bytes too far: its Accessed time, allocated size and
  file size come back as Created, Modified and Changed.
- **Detect the version before parsing the `$SI` tail, not the times.** The `$SI` length differs by version (116 B
  on v3.4, 124 B from v3.7 on), but the four MACB FILETIMEs at `0x00`–`0x18` are version-invariant. Only the
  post-`0x50` tail moves.
- **`$SI+0x40` is a USN byte offset, not a timestamp.** It is the file's LastUsn — the virtual byte offset of its
  most recent `$UsnJrnl:$J` record.
- **`$SI+0x48` is a journal time, not a file time.** The UsnJournalId is a FILETIME that names the journal instance
  (the moment that journal was created). It belongs on a timeline as a journal event, not as an event of the file.
- **`$SI+0x30` is not a USN either.** In a file's record it holds a cached copy of the file size, and it is 0 in a
  directory's own row. Do not plot it.
- **Access time is usually stale.** ReFS does not update A on reads by default (`RefsDisableLastAccessUpdate`=1), so
  treat it as a weak signal.
- **The CHKP virtual clock is not a date.** Plotting it as a wall clock is wrong; it counts checkpoints. Use it only
  to order states that carry no wall clock.

## Cross-validating the sources

Check the sources against each other: an inconsistency between them is what you look for. The checks below go from
the weakest, which is always available, to the strongest, which uses records only the driver writes and holds only
while the journal covers the period:

1. **`$SI` vs. the volume's creation time — always available.** A Created earlier than
   `$VOLUME_INFORMATION+0x90` (format time) is `PRE_FORMAT`: impossible for a file created on this volume, normal for
   a copied or restored one (robocopy `/COPY:T`, restores). It needs only the image, but it flags an inconsistency,
   not proof.

2. **`$SI` internal consistency.** The metadata-change time `C` (`$SI+0x10`) is not reachable through the high-level
   `SetFileTime` / PowerShell / .NET APIs that common timestomp tools use.

   After such a stomp `C` holds the moment of the stomp itself (the file system updates it on the call; these APIs
   cannot choose its value), while B and M carry the back-dated value. So `C >> max(B, M)` (`CHANGE_LATE`) — when M
   was back-dated too, and until the file is next written.

   This is a heuristic against common tooling only: a native-API (`NtSetInformationFile.ChangeTime`) or raw-disk
   stomp can set `C` too and leave no signal.

3. **`$SI` vs. the USN journal — the strongest check, for what happened after the journal was created and before its
   records were overwritten.** The journal is written and dated only by the driver, so it is a strong reference while
   it covers the period: it wraps, and a `fsutil usn createjournal` over it restarts the numbering at 0 (the older
   records are no longer served as the journal).
   - `$SI` Created vs. the file's `FILE_CREATE` (reason `0x100`) record — a mismatch is `USN_CREATE_MISMATCH`.
   - A **standalone** `BASIC_INFO_CHANGE` (reason exactly `0x8000`) records a basic-info edit at its real time; beside
     an intrinsic signal the tool reports it as `USN_BASIC_INFO_CHANGE`, while `$SI` shows the forged time. A
     back-date writes it, and so do `robocopy /COPY:DAT`, archive extraction and attribute changes.
   - The wall clocks at USN `+0x30` order events; the checkpoint clock orders only checkpoint states.

4. **CHKP virtual clock for sequencing.** Where two metadata states or two checkpoint copies exist, the higher
   virtual clock (`CHKP+0x60`) is the newer one — use it to order states that carry no wall clock.

How `timestomp` grades what it finds:

- **HIGH** only when a record outside the file's own timestamps corroborates it: the journal shows the times were
  edited, or two of the file's hard-link names disagree on Created.
- **MEDIUM** is `CHANGE_LATE` without `PRE_FORMAT` (created on this volume, altered afterwards).
- **INFO** is the copy-signature set on its own — `PRE_FORMAT` with `CHANGE_LATE`. A timestamp-preserving copy and a
  back-dated creation produce it identically, so it is ambiguous rather than cleared.

The full signal/tier model, the base rates and their validation live on the
[timestomp detection](timestomp_detection.md) page.

## Version and state differences

- **`$SI` length:** 116 B on v3.4 vs. 124 B from v3.7 on. The four MACB FILETIMEs at `0x00`–`0x18` are
  identical across all versions; only the post-`0x50` tail differs. A Win11 driver rejects a sub-124-byte `$SI` as
  corrupt, so version detection must precede tail parsing.
- **USN journal format:** ReFS always uses `USN_RECORD_V3` with 128-bit File IDs (major version 3,
  minor 0). Unlike NTFS there is no V2 record.
- **MLog redo opcodes carrying times:** the time-bearing opcodes (`InsertRow` `0x01`, `UpdateRow`
  `0x03`, `UpdateDataWithRoot` `0x04`) are stable across v3.4 and v3.14. The opcode *range* grows
  (v3.4 `0x00`–`0x1C`, v3.14 `0x00`–`0x2B`), but the time-bearing core is unchanged.
- **Volume creation time** is set at format. The driver's writers of the volume-information row that were read
  change other fields (the version bytes, the driver stamp, the last-mount time at `+0xA0`), and `+0x90` was
  unchanged across the v3.4→v3.14 upgrade measured.

  The upgrade rewrites the volume *version* bytes at `$VOLUME_INFORMATION+0x80`–`0x81`; every writable mount stamps
  its driver's version at `+0x82`–`0x83`. Neither touches the creation FILETIME at `+0x90`.

## Tooling

| Need | Command |
|------|---------|
| Merged super-timeline | `forefst.py <image> timeline [--csv FILE] [--fileref HOME:ID] [--source USN\|MLog\|SI] [--fast]` |
| Per-file MACB | `forefst.py <image> files` |
| Timestamp-anomaly verdict | `forefst.py <image> timestomp` — the one surface that judges one |
| Full cross-source timestomp verdict (adds USN) | `forefst.py <image> timestomp [--min HIGH] [--json] [--csv out.csv]` |
| USN event log (the history) | `forefst.py <image> usn [--csv] [--json] [--stats] [--info]` |
| MLog transaction times | `forefst.py <image> mlog --parse` / `--csv FILE` (one row per log payload: Seq, Timestamp, TimeSource, DerivedAction, PathToday, ParentPathToday, Name, OID, Opcodes, OpcodesHex, RecordCount, PLCN, Block) |

`forefst.py <image> timeline --csv FILE` merges the USN, MLog and `$SI` events into one time-sorted CSV (Timestamp,
TimeSource, Source, OID, Name, PathToday, Event). Read it against the volume's creation time from `summary` (the
`timestomp` header prints it too).

## Cross-references

- [File IDs](file_ids.md) — the FileRef `(HomeOID, ordinal)` that stays fixed across rename and move, the correct key for correlating a file's events over time
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the four `$SI` MACB FILETIMEs, the `$SI+0x40` LastUsn (a journal offset) and the `$SI+0x48` UsnJournalId (a FILETIME naming the journal instance)
- [Timestomping detection](timestomp_detection.md) — the signal/tier model built on `$SI`, the volume times, the USN journal and the hard-link names (the MLog check is manual)
- [USN journal](../structures/usn_journal.md) — the `USN_RECORD_V3` layout, reason codes, and `$J` storage behind the event-log column
- [MLog transaction log](../structures/mlog.md) — the four-layer record structure and the embedded-timestamp extraction this page summarises
- [CHKP checkpoint](../structures/chkp.md) — the virtual clock (`+0x60`) used for sequencing and current-vs-previous selection
- [$VOLUME_INFORMATION](../attributes/VOLUME_INFORMATION.md) / [volume info table](../structures/volume_info.md) — the `+0x90` creation FILETIME and the `+0xA0` last writable mount
- [Directory entries](../structures/directory_entries.md) — where the `$SI`-layout values live in the tree (a directory's type-0x10 row; a file's type-0x30 row or type-0x40 backing)

## Evidence

Each fact on this page carries its own evidence; there is no single proof of a "five-source model".

- The `$SI` MACB layout and the `$SI+0x40` LastUsn / `$SI+0x48` UsnJournalId reading are disk-proven: the
  per-file→journal link was confirmed by matching every LastUsn still inside the journal (13,550 of 13,550 on the
  real Windows volume of the corpus) to a `$J` record that names the file.
- The CHKP virtual clock counts checkpoints, not a wall clock; the higher clock selects the newer of two validating
  checkpoint copies (driver and disk). Values read: 29–63 on the nine volumes formatted by Windows 10; 27, then 68
  across one in-place upgrade (+41 checkpoints); 57–534 on the lab volumes; 662 and 293 after the "millions of
  actions" workloads; 617 on the public sample after four 1,000-action replays.
- The MLog has no header timestamp; the only times are FILETIME values embedded in `_SmsRedoRecord` value data,
  dispatched by `CmsLogRedoQueue::PerformRedo`, with the time-bearing opcodes (`0x01`/`0x03`/`0x04`) stable across
  v3.4 and v3.14. On the four public samples, 71.5 % to 97.3 % of the rows of `mlog --csv` carry a time. On the
  public sample (cleanly taken offline) the log area is 7.4 % used and still holds all 28,940 transactions since the
  volume's first mount.
- The per-name copies of a hard-linked file are index-entry caches of the file's record, and both directions are
  disk-proven: two names of one file carried different Created values, and reading the stale name erased the
  difference. A directory listing alone did not refresh a stale name; an open, a 1-byte read and a close through it
  did. Across the corpus the names' Changed times diverge routinely; on Created no routine case was found (the
  disagreeing files the journal still covered carried a basic-information change).
- The File ID was unchanged across 1,858 real cross-directory moves.

Each is a registered finding.

See [how this was verified](../methodology.md) to trace these statements to the exact images and
measurements in `analysis/`.

<!-- findings: FN_LINK_003, MD_ATTR_001, MD_TS_RA_004, MD_TS_RA_008 -->
