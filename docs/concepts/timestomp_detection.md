# Timestomping Detection

> **Experimental / informational.** Timestomp detection here is a corroborative aid, not a verdict.
>
> - Its strongest `$SI`-only signal, `CHANGE_LATE`, is defeated by a native-API or raw-disk stomp that also sets the
>   change time; the one intrinsic signal that reaches HIGH is a disagreement between a file's hard-link names.
> - `ROUND_TIMESTAMPS` is a weak signal that never raises a tier (alone it is INFO), and ordinary driver packages
>   produce it too.
> - Every flag needs confirmation against the USN journal or a file's hard-link siblings before you conclude
>   tampering.
>
> Treat the output as leads to verify, not proof.

Timestomping — back-dating a file's timestamps to hide when it was really created or written — is a standard
anti-forensic technique, and the usual NTFS check for it, comparing `$SI` with `$FILE_NAME`, does not exist on ReFS.

NTFS exposes it by comparing the two timestamp sets every file carries, the
[$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) set against the `$FILE_NAME` set; when a tool stomps
`$SI` but leaves `$FN` untouched, the mismatch reveals it. ReFS keeps a file's timestamps in its own record, and each
of its names carries a cached copy in its directory index entry; there is no separate `$FILE_NAME` attribute. So for a
**single-named** file there is no `$SI`-vs-`$FN` twin to compare against, and that cross-check is unavailable.

A **hard-linked** file differs: each of its names carries a cached copy of the file's times, refreshed only when the
file is opened, read and closed through that name, so the copies **can** hold different times. (NTFS's links share one `$SI`; each
NTFS link also has its own `$FILE_NAME`, with its own times.)

- A divergence of the names' **Created** times is evidence.
- Their **Changed** times diverge routinely: a hard link added later carries the time it was added.
- **Agreement is not** evidence: the file's own record takes the new time for every name at once, only each name's
  index entry lags behind, and an open, a read and a close of the file through a stale name catch it up (see [Hard Links](hard_links.md)).

Beyond that, timestomping is detectable through three other sources of a time:

- the metadata-change time that common tools cannot reach;
- the [USN change journal](../structures/usn_journal.md), when the volume has one and it still covers the period,
  which records the edit itself;
- the volume's own creation time, which a Created value contradicts only for a file created on this volume.

This page explains each source, why it works, and where it fails.

## Three sources to check a time against

ReFS gives the analyst these three sources. They are not independent of each other: one timestamp-preserving
copy or one back-date fires the change-time and the volume-creation signals together (see the INFO tier
below).

1. **The USN journal records the edit — the strongest, when the volume has a journal that covers the period.** A
   timestamp change is logged as a `BASIC_INFO_CHANGE` record at its real time, and a file's genuine creation is
   logged as a `FILE_CREATE` record. Only the file-system driver writes the journal, so it cannot be edited through
   the file APIs; but it is a fixed-size ring that overwrites its oldest records, and a data volume has none until
   one is created.
2. **The metadata-change time is left behind.** The high-level Windows APIs that ordinary timestomp tools call cannot
   set the change time, so the filesystem stamps it at the moment of the stomp while the forged times sit in the
   past. This is a heuristic against common tooling, not a guarantee, and it reaches MEDIUM at most.
3. **The volume creation time — the weakest.** A file created on this volume cannot have been created before the
   filesystem existed, so a creation time earlier than the volume's own creation is inconsistent. It is not by
   itself impossible: a copy that keeps the creation time (`robocopy /COPY:T`, a backup restore) brings an older
   time onto the volume, so the signal needs the analyst's context (see the tiers below).

The `forefst.py <image> timestomp` subcommand combines all three and ranks suspects by confidence.

### Two more sources when the journal is gone

The journal is the easiest of the three to lose. A data volume has none until one is created, and a
`fsutil usn createjournal` over an existing journal restarts its numbering at 0, so the earlier records are no longer
served as the journal (their bytes can survive above the new numbering; see
[USN journal](../structures/usn_journal.md)). Two other structures record a time independently, and both survive
that:

- **The transaction log.** While the log still holds them, it has two kinds of record of a stomped file:
  - **The creation.** The transaction that created the file carries its true times, and a creation time in `$SI`
    that disagrees with it is a contradiction between two structures. This speaks to the **birth time only**: a
    forged last-write agrees with it.
  - **Each call that set its times.** Each call writes the whole `$SI` to the log: the values it set, and the change
    time. A program that leaves the change time to the file system, as `SetFileTime`, PowerShell and .NET do, gets
    the moment of the call there, the same time the change journal records for it. A copy instead ends with its
    source's change time, older than the copy itself (measured for `Copy-Item`, .NET `File.Copy` and `robocopy`).
    Any program that sets the times and leaves the change time to the file system, an installer for example, leaves
    the same record as a stomp.

  Measured on the four files of a controlled set, on a volume whose journal had been re-created: the two with a
  back-dated creation contradicted their creating transaction, the two without agreed. On the volumes with a known
  list of calls every call had its record: 7 on the controlled set and 558 on a generated volume (both format 3.14),
  where each record's change time was within 28 ms of the generator's own log of the call and, where a journal
  existed, equal to the journal's record of it; on the controlled set it equals the change time Windows itself
  reported for each file afterwards. Every copy carried its source's change time. A program that sets the change time
  itself through the native API was not tested.

  What the records do not tell is why. On a real Windows volume such calls are routine: in the log of the corpus's
  Windows Server Insider system drive, 957 updates set a file's Created and 2,275 set Modified or Accessed back, by
  Windows servicing and application updates extracting files with their package dates. Use them to establish what was
  set, and when, on a file you are examining, not to screen a volume. `mlog --parse -v` lists the records (opcode 0x04
  on the file's table) under a row dated by the latest time its payload's records carry (for a call that set times
  back, at least the change time it wrote); it does not print the times the call set. The log is a rolling buffer, so old enough records
  have aged out of it.
- **A stream snapshot.** A snapshot descriptor timestamps the moment it was taken, not the file (see
  [`$SNAPSHOT`](../attributes/SNAPSHOT.md)). A file exists before it is snapshotted, so a creation time **later**
  than a snapshot of the same file is impossible: a creation time moved forward past one contradicts it. A creation
  time below the snapshot's is the normal order, so a backdated creation time is not caught this way.

Both are cross-checks an analyst runs today by reading `mlog --parse` and `snapshots` (the `Created:` line under each
snapshot is the moment that snapshot was taken) beside `timestomp`. `timestomp` itself reads neither.

## The change time: the source inside `$SI`

A ReFS `$SI` holds four FILETIMEs at fixed offsets (see
[$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md)):

| Offset | Time | Letter |
|--------|------|--------|
| 0x00 | Creation time | **B** |
| 0x08 | Modification time (last write) | **M** |
| 0x10 | Metadata change time | **C** |
| 0x18 | Last access time | **A** |

For a file the tool reads them from its directory entry: an embedded entry holds the `$SI` at value+`0x28`; a split
name row holds a cached copy at value+`0x10` to `0x2F`, while the file's own record (its type-0x40 backing) holds the
`$SI` at value+`0x28`.

The metadata-change time `C` is an ordinary timestamp — nothing about it is cryptographic or tamper-proof. What makes
it useful is an **API asymmetry**: the high-level interfaces a timestomp tool normally uses expose only three of the
four times.

- Win32 `SetFileTime(hFile, &Creation, &LastAccess, &LastWrite)` has **no `ChangeTime` parameter**.
- PowerShell `Set-ItemProperty -Name CreationTime/LastWriteTime/LastAccessTime` and .NET
  `File.SetCreationTime / SetLastWriteTime / SetLastAccessTime` expose the **same three**.

A caller using any of these **cannot reach `C`**, and the filesystem updates `C` to *now* as a side effect of the
metadata write it performs. So after a stomp that back-dates both Created and Modified, and until the file is next
written, B/M/A point into the past while `C` stays at the real moment of the operation. The signature is

```text
C >> max(B, M)
```

flagged as **CHANGE_LATE**. A stomp of Created alone, or any write after the stomp, leaves Modified current and does
not produce this signature.

For a single-named file it is the closest ReFS analogue of the NTFS `$SI`-versus-`$FN` comparison — using the
not-normally-reachable change time as the reference instead of a second timestamp set. (When the file is
**hard-linked**, a truer analogue is available: the names' cached copies, discussed below as
`HARDLINK_MACB_MISMATCH`.)

**This catches a stomp made with common tools, not one made by an attacker who also sets the change time.** The change time *is* settable through the native path:
`FILE_BASIC_INFORMATION.ChangeTime` passed to `NtSetInformationFile` carries an explicit change time, and the ReFS
driver honours it. The driver tracks, per open handle, which of the three auto-updated times (last write, change,
last access) the caller has set explicitly, and stops auto-updating those for that handle.

An attacker who sets all four through the native API, or who edits the raw `$SI` bytes on disk directly, leaves
**no** `CHANGE_LATE` signal. The change-time check catches a PowerShell / `SetFileTime` / .NET stomp that back-dates
Modified along with Created, as long as nothing writes the file afterwards; it does not catch someone who knows about
`ChangeTime`.

When the journal is present, it records an edit made through any Windows API (a raw-disk edit bypasses it); the tool
uses it as corroboration only (see the gate on `USN_BASIC_INFO_CHANGE` below).

## The signals

The tool emits a set of named signals. Each is one comparison or journal lookup, with its own strength and its own
way to be wrong.

| Signal | Meaning | Source | Strength |
|--------|---------|--------|----------|
| **CHANGE_LATE** | `$SI` change time (0x10) post-dates Created/Modified by a wide margin — back-dated B/M against the real metadata-write time | intrinsic ($SI only) | indicative against common tools when Modified was back-dated too; MEDIUM at most; **defeated** by a native-API or raw-disk stomp that sets `C` |
| **HARDLINK_MACB_MISMATCH** | two names of one hard-linked file disagree on Created | intrinsic (the per-name index entries) | strong lead, **journal-independent**; see [below the table](#what-the-hard-link-signal-says) |
| **USN_BASIC_INFO_CHANGE** | the journal holds a record whose reason is exactly `0x00008000` (`BASIC_INFO_CHANGE` and no other bit): a basic-info edit (timestamps or attributes) with no content change, recorded at its real time | USN journal | authoritative that an edit happened, not that it was a backdate; **gated** — see [below the table](#two-limits-of-usn_basic_info_change) |
| **USN_CREATE_MISMATCH** | `$SI` Created differs from the file's `FILE_CREATE` journal record (the journal's own record of the creation) | USN journal | authoritative that `$SI` Created is not the time the file was created on this volume |
| **PRE_FORMAT** | Created precedes the **volume** creation time — impossible for a file genuinely created here | intrinsic + volume | weak on its own (INFO)\* |
| **CREATE_GT_MODIFY** | Created after last write | intrinsic | weak\* |
| **ROUND_TIMESTAMPS** | both Created **and** Modified land on a whole second (`.0000000` sub-second) | intrinsic ($SI only) | **INFO**, not LOW — part of the copy signature |

\* `PRE_FORMAT`, `CREATE_GT_MODIFY` — and `CHANGE_LATE` — also fire on a **creation-time-preserving copy**
(robocopy `/COPY:T`, a backup restore), on files Windows servicing writes with their package dates, or on a legitimate
late attribute change on an aged file (measured); a rename or an ACL change plausibly does the same (not measured).
These keep or set an old creation time; the change time is the source's after a copy, and the moment of the write
after a program that sets the times and leaves the change time to the file system. Such a file is a genuine *inconsistency*, but whether it is malicious needs
analyst context.

The USN journal, when present, records the operation that caused the inconsistency at the time it happened; that
confirms an edit and dates it, not its intent.

`USN_CREATE_MISMATCH` has a limit of its own: a timestamp-preserving copy made while the journal was recording gets a
`FILE_CREATE` record at the copy moment against its preserved Created, so it raises the signal too (by the tool's
rule; not measured beyond the one-day margin).

`ROUND_TIMESTAMPS`: a set date is one cause, but VirtIO/QEMU driver packages also carry whole-second Created and
Modified times (145 of the 157 such files on a 30-image sweep). The lab's zip extraction (.NET)
does not raise it: it restored a whole-second Modified but set Created when it wrote the file.

### What the hard-link signal says

`HARDLINK_MACB_MISMATCH` is the exception to that dependence on context. A creation-preserving copy gives every name
the same times, so it does **not** trip on benign copies. It fires only when a file's own names disagree on Created;
no routine operation observed in the corpus produces that, while any explicit time set through one name while another
name is unopened does. It needs neither the journal nor the volume's creation time.

It only fires when a file has more than one name, and its **absence means nothing**: agreement has two causes, and
one of them is that somebody read the file (see the mechanism below).

What it does **not** tell you is *which* name holds the authentic birth. The mechanism below explains why the copies
disagree, but not which side of the disagreement is the original: the stale entry is the one nobody opened, and that
is not the same thing as the one nobody forged. So every name of a diverging group is flagged rather than a chosen
one. Follow it up in the [journal](../structures/usn_journal.md); it is not a conclusion on its own.

### Two limits of `USN_BASIC_INFO_CHANGE`

- **It is gated.** The signal is only recorded when `CHANGE_LATE`, `PRE_FORMAT` or `CREATE_GT_MODIFY` also fired on
  the same file, so a standalone journal edit with no intrinsic signal is **not reported at all**: the journal record
  is authoritative, but it is not shown when no heuristic signal fired. Treat a file's silence here as "not corroborated", never as
  "the journal recorded nothing".
- **It is not specific to tampering.** On a lab volume, most records with reason exactly `0x00008000` were not the
  lab's deliberate stomps: the rest were operations that legitimately rewrite basic information, such as
  `robocopy /COPY:DAT` and extracting an archive with stored times. It is authoritative that an edit happened, not
  that it was a backdate.

### Why the names' times differ, and what erases the difference

Two layers, and they refresh at different times:

* The **file's own record** takes the new timestamp **immediately**. In that sense a `SetFileTime` through one name
  updates every name at once, because the file has one set of times.
* Each **name's index entry** is a **lazily refreshed cache** of it. refs.sys refreshes only the entry of the name a
  handle was **opened** through: when that handle sets the basic information, the allocation or the end of file
  (`RefsUpdateFileDupInfo`), and on its close path (`RefsCommonCleanup` → `RefsUpdateDuplicateInfo`); siblings stay
  stale until each is opened in turn.

So a stomp through one name leaves that name's entry current and every un-opened sibling holding **pre-stomp** times
— which is the divergence this signal detects.

**It follows that agreement clears nothing**, because agreement has two causes: the names never diverged, *or* they
diverged and something opened the sibling. And it follows that the evidence is **perishable** — an open, a read and a
close of the file through a name refresh that name's entry.

- An antivirus scan, a search indexer, an inventory pass or a `Get-FileHash` sweep will erase it for the name it
  touches.
- A directory listing alone did not, on the lab volume measured (two `dir` listings left the stale name stale).

Measured on a controlled pair of lab images differing by exactly one recorded action, a read of the second name only:

- before, both names are HIGH on `HARDLINK_MACB_MISMATCH`, one showing the back-dated birth and the other the
  pre-stomp one;
- after **merely reading** the second name, the mismatch is gone: that name is not flagged at all, and the stomped
  name stays HIGH only because the journal recorded the edit.

**Image before anything touches the volume.** A read is not a safe operation for this evidence.

## Confidence tiers

The tool collapses the signal set into one of four verdicts. The dividing line is **corroboration from an independent
source** — the change journal, or a hard-link sibling — not the number of intrinsic signals that happen to fire
together.

| Tier | Reached when | Reading |
|---|---|---|
| **HIGH** | the journal records an edit to this file's times (`USN_BASIC_INFO_CHANGE`, reported only beside an intrinsic signal) or a creation time that disagrees with `$SI` (`USN_CREATE_MISMATCH`), **or** two of the file's names disagree on Created (`HARDLINK_MACB_MISMATCH`) | an independent source records an edit to the file's times, or disagrees with `$SI` |
| **MEDIUM** | `CHANGE_LATE` **without** `PRE_FORMAT` — created on *this* volume and altered afterwards | worth investigating; a copy of a file older than this volume cannot produce it |
| **INFO** | only the copy-signature set fires: `PRE_FORMAT`, `CHANGE_LATE`, `CREATE_GT_MODIFY`, `ROUND_TIMESTAMPS` | **ambiguous**, see below |
| **LOW** | **unreachable**: of the 128 inputs the command can build (5 signals × `usn_conf` × `hl_conf`), none reaches it (HIGH 111, MEDIUM 4, INFO 11, NONE 2, LOW 0) | the tier exists in the code and in `--min LOW` |

Neither journal signal separates a backdate from a timestamp-preserving copy made while the journal was recording.

MEDIUM has its own limit: a copy of a file newer than this volume, a late attribute change or Windows servicing can
also produce `CHANGE_LATE` without `PRE_FORMAT`.

LOW is unreachable because a journal or hard-link signal gives HIGH, `CHANGE_LATE` without `PRE_FORMAT` gives MEDIUM,
and every other signal is in the copy set that gives INFO (the enumeration is in the Evidence section).

### Why `PRE_FORMAT` + `CHANGE_LATE` is INFO, and what INFO does *not* mean

These two are not independent. A program that writes a file with older create/modify times and leaves the change
time to the file system — Windows servicing and application updates do this with their package dates — writes
create/modify that predate this volume when the package's do (`PRE_FORMAT`), while the change time is the moment of
the write (`CHANGE_LATE`). They are two halves of **one event**, so treating their co-occurrence as
two agreeing signals is wrong: on a real Windows installation the pair covers nearly every file, so treating it as
corroboration would flag the operating system itself and train an examiner to ignore the column.

**But the pair does not identify that event as a legitimate one.**

- Back-dating Created and Modified to before the volume's creation produces exactly the same two signals. A lab
  volume built by replaying timestamp-setting actions (each sets Created, LastWrite and LastAccess) carries this
  signature.
- Back-dating Created alone gives `PRE_FORMAT` alone (also INFO).
- A back-date that stays after the volume's creation gives `CHANGE_LATE` without `PRE_FORMAT` (MEDIUM).

So INFO means *a legitimate time-setting and a back-dated creation look the same in `$SI`*. A disagreement between a
file's hard-link names rules out a copy, because a copy has one name. The journal dates the edit, but its signals also fire on a
timestamp-preserving copy made while it was recording. **INFO is a lower tier; it does not clear the file.**

### How often each signal fires

Base rates over the corpus, measured in a single pass. Read them as lower bounds, not as the rates of a typical volume: the corpus is
mostly small purpose-built lab images.

| Signal | Base rate (about) | Tier contribution |
|---|---|---|
| `PRE_FORMAT` | 23 % | INFO |
| `CHANGE_LATE` | 22 % | MEDIUM only *without* `PRE_FORMAT` |
| `CREATE_GT_MODIFY` | 1 % | INFO |
| `ROUND_TIMESTAMPS` | 0.04 % | never lifts a tier |
| `HARDLINK_MACB_MISMATCH` | 0.04 % | **HIGH** |

The split by volume kind is the reason the tiers are shaped this way. On the corpus's one **real Windows
installation** the copy signature fires on **nearly every file (about 95 %)**, because installing an operating
system produces it, against **about 2 %** across the lab-built volumes. With the tiers above, the reviewable set on
that volume is **a few hundred HIGH and a few hundred MEDIUM**, rather than more than a hundred thousand rows all
claiming the same thing.

`ROUND_TIMESTAMPS` is capped by design. Whole-second Created **and** Modified stamps are *suggestive* of a
deliberately set date but are **not proof**: VirtIO/QEMU driver packages also write whole-second times, so the signal
never lifts another tier's verdict.

The tiers are assigned in one function, `timestomp_verdict()`, which only the `timestomp` command calls — see the
[tool reference](../tools/forefst.md) for the command-line surface and `--min TIER` filtering.

## What does not work as a substitute

Two other checks are unreliable and should not be treated as primary signals:

- **The NextFileId ordinal** is a per-directory child-creation ordinal: `RefsMoveFile` increments the parent
  directory's counter and stamps the new child with the value. Every file keeps its ordinal as the low half of its
  File ID, on every version; a directory's own-row copy (`$SI+0x58`) is written only below v3.11, so it is 0 on
  native v3.14 (the object record holds the counter on every version).

  Within one directory, ordinals are assigned in creation order (`RefsMoveFile` increments the counter), so a
  Created time out of ordinal order, among files created there, is corroborating. But it is coarse: it is directory-scoped and
  fixed at creation (a moved-in file keeps its creation directory's ordinal), and a copy that preserves Created shows
  the same inversion as a backdate. It cannot serve as a general check.
- **A zero sub-second fraction** (whole-second times, the low 100 ns part = 0) is sometimes left by timestomp tools
  that write second-granularity values, but it depends on the tool: a tool that copies full-resolution
  FILETIMEs leaves no such trace, and VirtIO/QEMU driver packages carry whole-second stamps on ordinary files (the lab's
  zip extraction left a whole-second Modified only). The tool surfaces it as the `ROUND_TIMESTAMPS` signal; on its own
  it gives **INFO**, and it never raises another tier. It is a lead to corroborate (with the USN journal or a hard-link MACB comparison),
  never a primary signal on its own.

## How the tool is wired

The detector has two parts, but **one command** runs them. `timestomp_intrinsic_flags()` computes the `$SI`-intrinsic signals
(`CHANGE_LATE`, `PRE_FORMAT`, `CREATE_GT_MODIFY`) without touching the journal, and `timestomp_verdict()` turns
signals into a tier. Both are reached only through `forefst.py <image> timestomp`, which loads the
[USN journal](../structures/usn_journal.md), adds the journal signals, the hard-link comparison and
`ROUND_TIMESTAMPS`, and then decides the tier.

Only the `timestomp` command reports timestamp anomalies; the `files` listing carries no timestomp column.

```sh
forefst.py <image> timestomp                # HIGH rows; lower tiers counted in a trailer
forefst.py <image> timestomp --min HIGH     # only high-confidence suspects
forefst.py <image> timestomp --json         # machine-readable (every tier)
forefst.py <image> timestomp --csv out.csv  # per-file CSV (every tier): ObjectRef, path, placement, residency, confidence, signals, evidence refs, MACB
forefst.py <image> timestomp --all          # every file with its flags (incl. NONE)
forefst.py <image> timestomp --margin-days N # anomaly margin (default 1 day)
```

The `--margin-days` value is the slack every time comparison allows before calling a gap suspicious (the intrinsic
ones, the hard-link one and the journal create one), which keeps ordinary clock skew and sub-day operation latency
from generating noise.

The two USN-based signals correlate a file to its journal records by **File ID** — the FileRef `(HomeOID, ordinal)`,
not the path — where the row has one; otherwise by file name, when that name is unique among live files. Because the
File ID is unchanged by a rename or a cross-directory move, a file that was renamed or relocated after creation is
still matched to its true `FILE_CREATE` record, so `USN_CREATE_MISMATCH` and `USN_BASIC_INFO_CHANGE` are not
defeated by an intervening move — a stomp cannot be hidden simply by moving the file afterward.

See [File IDs](file_ids.md).

## Cross-references

- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the four timestamps (B/M/C/A at `$SI`+0x00/0x08/0x10/0x18) and where a file's copies of them sit
- [File IDs](file_ids.md) — the FileRef that ties a file to its journal records across renames and moves, so a stomp can't be hidden by relocating the file
- [Hard Links](hard_links.md) — why each name of a file carries a cached copy of the file's times, which lags behind a stomp made through another name until the file is opened, read and closed through that name (the `HARDLINK_MACB_MISMATCH` basis)
- [USN Journal](../structures/usn_journal.md) — the in-place ring whose `BASIC_INFO_CHANGE` (reason exactly 0x8000) and `FILE_CREATE` records the journal signals read
- [Artifact Timeline](artifact_timeline.md) — how the MACB times feed a unified event timeline
- [Forensic Analysis Workflow](forensic_analysis_workflow.md) — the tamper check is step seven (`$SI` vs USN vs volume-create) of the standard workflow
- [$VOLUME_INFORMATION](../attributes/VOLUME_INFORMATION.md) — the `+0x90` creation time `PRE_FORMAT` compares against

## Two things that do not help

**SetMace and tools like it do not work as designed on ReFS.** They edit `$MFT` records, and ReFS has no `$MFT`
(reported by prior work; not tested here). A stomp through the ordinary Windows APIs (`SetFileTime`, PowerShell,
.NET) leaves the change time behind; one through `NtSetInformationFile` or a raw-disk edit need not.

**A write to a named stream moves the parent file's times.** An ADS write updates the host file's LastWrite — and,
with last-access updating enabled (as on the test volume), its LastAccess — so a file whose content never changed can
still carry a fresh modification time. Measured on format 3.14. Before reading a modification time as evidence of a
content change, check whether the file has streams.

## Evidence

The four-FILETIME `$SI` layout, the NextFileId ordinal, and the per-handle "caller supplied this time explicitly"
tracking are confirmed in the driver: `RefsComputeStandardInformationFromFcb` builds the `$SI` fields from the FCB
(26100.9444), `RefsMoveFile` writes the directory child-creation ordinal, and `RefsSetBasicInfo` honours an explicit
`FILE_BASIC_INFORMATION.ChangeTime`.

The two journal-independent witnesses are the embedded timestamp of the file's creating MLog transaction (measured
against `$SI` on a controlled set whose journal had been re-created) and the snapshot descriptor, which records the
snapshot moment, not a copy of `$SI`.

**What the detection is exercised on, and what that can and cannot establish.**

- The public sample `win11refstestmftecmd` is built by replaying timestamp-setting actions (each back-dates Created,
  LastWrite and LastAccess) on a freshly formatted volume. On its current output every HIGH row carries a journal or
  hard-link signal (137 HIGH, 57 INFO, no MEDIUM).
- The same synthetic back-dated files carry the same intrinsic signals wherever the test tree was written; their tier
  depends on the journal (the tree replayed before the journal was created is mostly INFO, the one replayed after it
  mostly HIGH).
- The cases that separate a name-keyed from a FileRef-keyed journal match — a stomp then a delete with an innocent
  namesake, a backdate then a rename, two live namesakes — are tested on a lab image built for them, where the
  FileRef correlation gives the expected verdict in all seven cases.
- A standalone `BASIC_INFO_CHANGE` record sits on the timestomp lab image at the tampering's real time while `$SI`
  shows the forged time. On that lab volume (T21), 34 records carry reason exactly `0x00008000` across 27 names, and
  only 12 are the lab's deliberate stomps: a second count gives the same, the 12 on the lab's nine back-dated files.

The per-name copies behind `HARDLINK_MACB_MISMATCH` are each name's index entry, a cache of the file's own record that
the driver refreshes only for a name the file was opened, read and closed through. They were observed diverging on a two-name file
where one name read a back-dated Created and the other the real creation moment. A later lab measurement found both
rows byte-identical after a `SetFileTime` through one name, because the lab's inventory pass had then opened both
names: agreement between names is not evidence of anything.

The controlled-set calibration (eight files with one known cause each, six flagged and all six at INFO) and an ADS
write updating the parent's LastWrite and LastAccess are registered findings too, as is each statement above; that
`$MFT`-editing tools cannot work here was reported by prior work for ReFS 3.2 and is not tested.

The counts behind the text:

- the controlled pair is `labA_image1` / `labA_image2`;
- on the real Windows installation (120,617 files) the copy signature alone covers 95.4 % of the files, and 95.7 %
  carry at least one signal; the back-dating lab volume's generator log records 74 timestamp-setting actions per
  replay;
- the base rates, over 96 images and 521,060 files (2026-09-06): `PRE_FORMAT` 22.67 %, `CHANGE_LATE` 22.32 %,
  `CREATE_GT_MODIFY` 1.04 %, `ROUND_TIMESTAMPS` 0.04 %, `HARDLINK_MACB_MISMATCH` 0.04 %; the copy signature on
  1.86 % of the files of the 95 lab-built volumes of the same pass;
- the reviewable set on the real Windows installation: 324 HIGH and 336 MEDIUM (measured 2026-09-21), against roughly
  115,000 rows under a tiering that treated the pair as corroboration;
- the tier enumeration: of the 128 inputs the pipeline can build (5 signals × journal corroboration × hard-link
  corroboration), `timestomp_verdict()` gives HIGH 111, MEDIUM 4, INFO 11, NONE 2 and LOW 0.

See [how this was verified](../methodology.md) to trace these statements to the exact images and measurements in
`analysis/`.

<!-- findings: MD_MISC_001, MD_SNAP_RA_010, MD_TS_RA_003, MD_TS_RA_007, MD_TS_RA_008, MD_TS_RA_009, MD_TS_RA_010, MD_TS_RA_011 -->
