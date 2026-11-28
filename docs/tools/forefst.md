# forefst.py in long

The full reference of `forefst.py`: every command, its options and what it prints. [forefst.py in short](forefst_short.md)
has what it does, a quick start and every command on one line.

> **Known issues in 1.14.1.** The limits of this release that can change what an examiner reports, each with what to do,
> are on their own page: [Known issues in 1.14.1](known_issues.md).

## Invocation

```sh
forefst.py <image> [subcommand] [options]
forefst.py <image>                  # no subcommand → volume summary
forefst.py <image> <cmd> --help     # detailed help + examples for one subcommand
forefst.py <image> help <cmd>       # same targeted help — `help` as the subcommand token
forefst.py <image> help             # the general overview (the image is not read)
forefst.py --list                   # one-line index of the subcommands (fastsummary is hidden: help fastsummary)
forefst.py help <cmd>               # per-command help without needing an image
forefst.py <bundle-dir> verify-bundle   # check a metadata bundle: the bundle directory comes first, as an image
```

**What the output is.** `--list`, `--help` and each command's help say it: read from the volume, or inferred or
recovered (corroborate before relying on it) -- `mlog --parse`, `timeline`, `timestomp` and `deleted`. `extract`,
`export` and `verify-bundle` get data out or check a bundle. Prose in the text views and the help is wrapped at about
100 characters; data rows (listings, tables, entries, CSV, JSON) and the stderr lines are never wrapped.

The subcommand token comes **after** the image path. Options every command shares:

- Output formats `--json`, `--jsonl` and `--body` are mutually exclusive; `files`' default is CSV, every other
  command's text.
- `--partition-start <bytes>` gives the volume's byte offset in the image (accepts `0x` hex). Without it the tool
  takes the ReFS partition from the image's GPT; a bare volume image needs `--partition-start 0`, and an image of an
  MBR disk the partition's offset.
- `--verify-pages` (every command) checks each metadata page the command reads below a table's root page against the
  digest in its parent's page reference (on the corpus's 60 GiB Windows Insider boot volume `files` took 135 s with it
  and 109 to 114 s without). At exit it says how many pages it checked and how many did not match, naming the first
  eight (exit 2).
- `-q`/`--quiet` (on the native subcommands — `files`/`summary`/`search`/`details`) silences the progress lines
  printed to stderr.

> **Version support:** validated mainly on ReFS 3.14; the formats 3.4, 3.7, 3.9 and 3.10 are read too (no 3.11-3.13
> volume was available to test). Some enriched fields (e.g. the target of a symlink whose record is split) may be
> incomplete on 3.4–3.10.

## Native subcommands

### `files` — list files and directories

Walks the directory B+-tree from the root object (OID `0x600`) and emits one enriched row per name: a hard-linked
file has one row for each of its names. Default output is the 42-column CSV described [below](#csv-output-fields).

It reads the metadata and, to decide `IsMoved`, the change journal's records where the volume has one (column 42) —
no file's data; see [what `summary` does not examine](#summary--full-volume-triage-report).

Each table's root page is checked against the digest the Object Table recorded for it. When the security table's root
page (object 0x530) does not match, the listing keeps the values it read, says on stderr that `SecurityId`,
`OwnerSid`, `GroupSid` and `DACLSummary` come from that page, and exits 2.

| Option | Description |
|--------|-------------|
| `--csv [FILE]` / `--json [FILE]` / `--jsonl [FILE]` | machine output (default CSV); bare flag → stdout, `+FILE` → write & print a `Wrote N … to FILE` count |
| `--body` | TSK/mactime body file instead of CSV |
| `-o, --output FILE` | deprecated: writes the selected format (CSV by default) to FILE, with a note; use `--csv FILE` or `--body FILE` |
| `--filter CATEGORY` | keep only one [attribute category](#files---filter-categories) |
| `--cow-before IMAGE` | instead of the listing, compare with an earlier image of the same volume (see [CoW version comparison](#cow-version-comparison)); `--cow-partition-start BYTES` gives the earlier image's partition offset (default: its own GPT) |
| `--csv-safe` | prefix any CSV cell that starts with `=`, `+`, `-`, `@`, a tab or a carriage return with a single quote, so a spreadsheet treats it as text (see the warning below). **Off by default** — it alters the reported name |
| `-q, --quiet` | silence the progress lines on stderr |
| `--depth N` | max directory recursion depth (default: the full tree) |

> **Filenames on a suspect volume are attacker-controlled, and CSV is opened in a spreadsheet.**
> A name beginning `=`, `+`, `-` or `@` is interpreted by Excel and LibreOffice as a **formula**, which is
> the classic CSV-injection hazard. The default output is **byte-faithful**: names are written exactly as
> they are on the volume, because silently rewriting an evidential filename is worse than the hazard. The
> tool instead **counts** such cells and tells you at the end of the run, and `--csv-safe` prefixes them with
> a single quote when you are about to open the file in a spreadsheet. Use it for viewing, not for the copy
> you keep as evidence — the quote changes the name.

The `files` listing covers the **live** tree only: an object waiting in the Trash is out of its directory already, so it is not listed. Deleted files are recovered by the separate [`deleted`](#deleted--the-deleted-file-view-list--recoverability) command, which also lists the Trash table's rows.

> Running `forefst.py <image>` with no subcommand prints the volume **summary**, not this listing — use `files` for the CSV.

```sh
forefst.py disk.raw files --csv listing.csv          # full CSV listing
forefst.py disk.raw files --filter hardlink           # only multi-link files
forefst.py disk.raw files --filter ea --json          # EA-bearing files as JSON
forefst.py disk.raw files --body t.body              # body file (live tree); deleted → `deleted`
```

### `summary` — full volume triage report

The report, in order (extended by default):

- **Volume identity**: version, GUID/label, cluster/container size, checksum type. The checksum type is the one
  refs.sys uses: the boot sector's selector at 0x2A when its flags at 0x2C carry 0x40, else CRC64, with a note naming
  what 0x2A holds when it is not read.
- A **Bootstrap structures** section listing the VBR (primary + backup), SUPB (primary + 2 backups) and the two CHKP
  copies, each named by its role — each with its address, validity, and the SHA-256 of that copy (a checkpoint's
  covers its record, one cluster).
- The on-disk state (original / upgraded / native), the 13 root-table row counts, the USN-journal status +
  UsnJournalId.
- A **Space used** line: the used space from the accounting ReFS maintains in the allocator's own root page, which
  equals Windows' own figure (`fsutil fsinfo refsinfo`: total − free − reserved). The rest is reported as *not
  allocated*, not as free, because Windows holds part of it in reserve and reports less as free.
- The **image tail** on one line: the part of the image file after the volume's last cluster (the rest of its
  partition and anything after the partition), which the tool does not read, with how much of it lies in the
  partition. A note follows when the allocator's summary and the boot sector disagree on the volume's length
  (`refsanalysis.py <image> allocators` shows the tiers behind it).
- Then a full directory walk:
  - the directories, the files (by data residency) and, on their own `Names:` line, the names (one per file, plus one
    per extra name of a hard-linked file);
  - the total size and the oldest and newest Created or Modified time;
  - `Last access`: the files read after their last change (an Accessed time more than 1 s after both Modified and
    Changed), which says last-access updating seems to have been on (a program can also set an Accessed time; none
    says nothing);
  - the encrypted/integrity/compressed/hard-link/snapshot/ADS tallies.

What the other sections say:

- **Bootstrap structures**: each checkpoint line names the copy's role — `in use`, `superseded`, `tied` or `newest`
  (a newer copy that is not the one in use). The superblock copies' payloads are compared: equal payloads are noted
  as redundancy; copies that differ are stated, with which of them pass their self-checksum, and the command exits 2.
- **Checkpoint** gives the clock of the copy in use and its flags, decoded.
- **Volume Detail** gives the volume and driver versions, `Volume created` and `Last mount (rw)` (the time of the last
  mount that wrote to the volume) from `$VOLUME_INFORMATION`, and the volume state (original / upgraded / native).
  The boot sector's version is tested: a version that is not 3.x with a minor of at most 14, or that
  `$VOLUME_INFORMATION` does not corroborate on a volume with no upgrade evidence, makes the state
  `VERSION CONTRADICTED - the boot sector is not corroborated`, and the command exits 2 (`fastsummary` and
  `integrity` make the same test; the other commands read the volume the same way and keep their exit code).
- **MLog** is read only with `--mlog` (or `-v`). One pass over the log gives the control copy in use and whether it
  verifies, the log version, log start and log end, the log blocks read, the records of an earlier volume or log, and
  whether the newest records are all present up to the log end (see `mlog`); its findings set the exit code as
  `mlog`'s do. Without the option the section says the log was not read and names the option, and no MLog finding is
  made; `fastsummary` reads no log.

| Option | Description |
|--------|-------------|
| `--json [FILE]` | emit one JSON object instead of the text report (bare → stdout, +FILE → write & count) |
| `--hash-image` | also SHA-256 the whole image (chain-of-custody; streams the image) |
| `--mlog` | also read the MLog for the report's MLog section (one pass over the log's data area) |
| `-v, --verbose` | the same as `--mlog` |
| `--depth N` | max recursion depth for the content census (default: full — the whole tree) |
| `-q, --quiet` | silence the progress lines on stderr |

```sh
forefst.py disk.raw summary                           # text triage report
forefst.py disk.raw summary --json                    # one JSON object
forefst.py disk.raw summary --hash-image              # + full-image SHA-256
```

When the Container Table has a container the tools do not translate (compressed, compacted, refused by refs.sys, or
mapped by more than one range), the report lists it with the reason ("Container not read: 0x5: it is compressed
(reading compressed containers is not supported)"; `ContainersNotRead` in `--json`), and a read into it is a recorded
skip (exit 2).

**What `summary` does not examine: file contents.** Everything after the bootstrap section is read from
metadata — directory rows, the allocator's accounting, the root tables. No file's data is read, so a report
without warnings says the metadata read cleanly and nothing about whether file contents are intact: a file
whose clusters were zeroed or overwritten is listed exactly as before.

None of these commands checks a file's content either: `files`, `search`, `details`, `dataruns`, `specials`,
`reparse`, `security`, `timestomp`, `timeline` and the `refsanalysis` listings (`timestomp` and `timeline` read the
journals' data, not the files').

Two things can be checked:

- `integrity --checksums` verifies the stored checksum of every file that carries an integrity stream
  (`HasIntegrity`); a file without one has no checksum on the volume, so damage to its data cannot be detected from
  the image.
- `extract` and the `export` modes report the ranges an image stores as holes (below).

### `search` — find files/directories by name  *(alias: `find`)*

Case-insensitive substring match on the name across the whole tree; add `--regex` for a Python regex against the basename. `find` is a friendly alias (`forefst.py disk.raw find report`).

| Option | Description |
|--------|-------------|
| `PATTERN` | (positional) name substring, or regex with `--regex` |
| `--regex` | treat PATTERN as a case-insensitive regular expression |
| `--filter CATEGORY` | keep only one [attribute category](#files---filter-categories) |
| `--csv [FILE]` / `--json [FILE]` / `--jsonl [FILE]` | machine output; bare flag → stdout, `+FILE` → write & print a `Wrote N … to FILE` count |
| `-q, --quiet` | silence the progress lines on stderr |

`search` prints a table of the matching rows, then the number of matches. It has no body-file output (use
`files --body`), and `-o` alone writes no file (use `--csv FILE`).

It covers the live tree — to search deleted objects use
[`deleted --search PATTERN`](#deleted--the-deleted-file-view-list--recoverability).

```sh
forefst.py disk.raw search report                     # names containing "report"
forefst.py disk.raw search '^link\d+_to' --regex      # regex on the basename
forefst.py disk.raw deleted --search secret           # search deleted objects
```

### `details` — all attributes for ONE object

Full record for a single file, directory or object: timestamps, attributes (incl. EA), SecurityId/owner, USN,
reparse target, and — where the record carries them — the inline sub-records (ADS, $EA / WSL metadata, snapshots).

Address it by path, or by id: a file by its FileRef (`HomeOID:FileID`, as `files` prints it in `ObjectRef`), a
directory or system object by its OID (files have no OID of their own). The target is read as an id when it reads as
one (`0x705`, `0x703:0x2e`), and as a path from the root otherwise, with or without its leading slash. `--path` and
`--id` are the explicit forms; a name that reads as an id is reached with `--path` (`--path /0x705`).

Its `Is moved` line is decided as `files`' `IsMoved` column is, from the change journal's records where the volume
has one.

| Option | Description |
|--------|-------------|
| `PATH` or `ID` | (positional) an id when it reads as one (an OID `0x705`, a FileRef `0x703:0x2e`), a path from the root otherwise (`/dir/file.txt`, `dir/file.txt`) |
| `--path P` | address by path |
| `--id ID` | address by id, an OID or a FileRef: an OID (`0x703`) or a FileRef `HomeOID:FileID` (`0x703:0x2e`) |
| `--json [FILE]` | the full record as JSON — for a directory, its on-disk structure |
| `--csv` / `--jsonl [FILE]` | one row in the `files` schema (the same columns, so it concatenates) |

```sh
forefst.py disk.raw details /wsltests/lxsymlink       # a reparse/WSL file by path
forefst.py disk.raw details 0x705                      # a directory object by OID
forefst.py disk.raw details 0x703:0x2e                 # a file by its FileRef, no path needed
forefst.py disk.raw details /dir/file.txt --json
```

---

## Forensic subcommands

### `usn` — USN (Change) Journal

Parses `$UsnJrnl:$J`: per record, the USN, timestamp, reason flags, the file name, its resolved path and the file
reference `ObjectRef` = `HomeOID:FileID` (the `ObjectRef` `files` gives the file).

The whole journal is read: every allocated extent of `$J` is parsed. Bare `usn` prints the activity summary.

| Option | Description |
|--------|-------------|
| `--list` | the on-screen per-record list |
| `-v, --verbose` | with `--list`: add RecLen/Version/StreamOffset per record |
| `--info` | journal metadata instead of records ($J extents, $Max, record count), the journal's health, and the checkpoint's journal cursor |
| `--stats` | activity summary: reason-code distribution, busiest files, time range (what bare `usn` shows) |
| `--id ID` | only the records of one object: a file's FileRef `HomeOID:FileID` (`0x703:0x2e`), or a directory's OID (`0x703`, its records carry `0x703:0x0`); with the summary, `--list`, `--csv` or `--json`. The journal's state is still checked over every record |
| `--csv [FILE]` | export all records to a 19-column CSV: `USN`, `Timestamp`, `Reason`, `ReasonHex`, `FileName`, `IsDirectory`, `ObjectRef`, `HomeOID`, `FileID`, `ParentOID`, `FullPath`, `FileAttributes`, `FileAttributesHex`, `RecordLength`, `SecurityId`, `SourceInfo`, `SourceInfoHex`, `ParentFileID`, `StreamOffset` |
| `--json [FILE]` | one document: `Journal` (the `$Max` fields, the `$J` runs and sizes), `RecordCount`, `Records` (each with the CSV's keys) |

What `usn` says about the journal itself, in every form (on stderr when stdout carries the export, on stdout when
the export goes to a FILE):

- **A re-created journal.** When the bytes show the journal was created again — its numbering restarted at USN 0
  (with a new id, or with the id kept), or files carry an earlier journal's id — a `Journal instances:` statement
  names it and the boundary (`USN 0 to N belong to the current journal; USN M to K belong to an earlier instance`),
  and the command exits 2.
- **Missing records.** When files on the volume still point past the journal's last surviving record, a `Journal
  tail:` statement names the missing USN range and the command exits 2. The journal cannot tell records lost (for
  example at an unclean detach) from records removed, so the statement says missing, never destroyed. Each range is
  counted against its own journal instance's records; where the image stores part of the range as holes, the
  statement says how much: those bytes were not captured or are zero on the disk, and the image cannot tell which.
- **Bytes that are not records.** Non-zero bytes past the journal's last record are ring space the journal has not
  written yet, holding earlier cluster contents: a note, not a finding. Inside the written span, or in a journal that
  holds no record at all, the same bytes may be records that are lost or removed: they are named, with their offsets,
  and the command exits 2.

`timeline` and `timestomp` make both statements, in the same words.

`usn --info` also prints **the checkpoint's journal cursor**: the change journal's position that the checkpoint copy
in use keeps in its area at +0x88. `Next USN` is where the journal's next record goes; the count beside it is the
records of the current journal at or past it, which were written after this checkpoint (after a re-creation, an earlier
instance's records are not compared: their USNs number another journal). `First USN` and the wrap base and size are 0
unless the journal has wrapped. A copy without the area says so: the checkpoint then does not say where the journal
stood. On the corpus no record of the current journal lies past the cursor.

When the root page of the system metadata table (OID 0x520), the table that holds the journal's entry, does not match
the checksum the Object Table recorded for it, every command that reads the journal warns and exits 2, and `usn --info`
marks the entry: `*** the root page of the system metadata table (OID 0x520) does not match the digest the Object Table
recorded for it: the entry below was read from that table.`

```sh
forefst.py disk.raw usn                                # activity summary (bare usn; use --list for the record list)
forefst.py disk.raw usn --info                         # journal layout & health
forefst.py disk.raw usn --stats                        # activity summary
forefst.py disk.raw usn --csv usn.csv                  # export to CSV
```

### `mlog` — MLog (durable transaction log)

Parses the durable logfile: control header, data-area page census, and the redo records.

`--parse` groups the low-level redo opcodes of each **log payload** into a **concrete action** and names the directory
and the name it changed (below). A row is one log payload: it can merge up to 15 redo blocks, and its time is the
latest time its records carry (a volume-information update gives its write time; a `$SI` update the latest of
its four times, so a call that set times back is dated at least by the change time it wrote).

The actions split into:

- **file operations**: `CREATE`, `DATA_OR_REPARSE_WRITE`, `RENAME`, `MOVE`, `MOVE_AND_RENAME`, `MOVE_OR_RENAME`,
  `DELETE`;
- the **low-level / metadata records** that accompany them: `STREAM_UPD`, `TABLE_REPARENTED`, `ENTRY_REMOVE`,
  `ALLOCATE`, `CONTAINER`, `MODIFY`, …

Every action is **derived** from the records (`mlog --info` lists the rules), not read from the log.

Two classifications need more than a bare opcode — and both are important forensically:

- **MOVE, RENAME, MOVE_AND_RENAME** — a rename and a move both remove the old name row and insert a new one, and on
  v3.14 ReFS emits a reparent record for *both* (on v3.4 a same-directory rename carries none), so a reparent record
  does not by itself mean a move. forefst reads the change from the file's own records: its name link
  (`$OBJ_LINK`: parent and name) replaced, or its table moved from the old name row to the new one. Same
  directory → `RENAME` (shown `(same parent 0x..: old → new)`); another directory, name kept → `MOVE` (`(parent
  0x<old> → 0x<new>)`); both → `MOVE_AND_RENAME` (`(parent 0x<old> → 0x<new>: old → new)`; a deletion to the
  Recycle Bin is one). A pair is read inside its own transaction first, so a name freed and taken again in one
  payload (an atomic save) hides neither change.

  Where the file's records give no pair (a ReFS 3.4 directory, and rarely on 3.14), the directories of the names
  removed and added decide and the detail says `names not paired` (such a row does not show that the names are one
  file); sets that overlap without being equal are `MOVE_OR_RENAME`. Where a side names more than one directory,
  both sets are shown (`parents undetermined: old 0x..;0x.., new 0x..;0x..`, or `same parents 0x..;0x..` when they
  are equal), never one picked. A reparent record that moves no name is `TABLE_REPARENTED`.
- **DELETE vs a name removal** — a bare `RedoDeleteRow` also fires on the old name of a rename/move, so it is
  **not** proof of deletion. `DELETE` is reported **only** when a record of the row destroys a table
  (`RedoDeleteTable` — opcode 0x0f, and 0x2d on Insider 29683 — shown `(object table destroyed)`). A row is a whole
  log payload, so the destroyed table is not necessarily the directory or file the row names, and a move in the same
  payload as a table deletion is labelled `DELETE`. A name removed with no new name for it is `ENTRY_REMOVE`
  (`no entry added for it`): that name was deleted (a file's, or a hard link's). An `ENTRY_REMOVE` that says
  `a row removed, not a directory entry` removed some other row.

A name row's directory is the table its record applies to: the record's own table path, or, for a record that
carries no path, the table the driver's redo pass keeps current — the previous record's, carried into a redo block
that continues a transaction, and none after a record that uses no table, a table deletion or a table-set commit
merge. The row is the directory's own entry only when that path has one component; a deeper path names a table
embedded in one of the directory's rows (an alternate stream's name row, for one).

A row that shows a name shows it in the directory that name entry was in; a payload's other changes are named after
`also` (for reading: `--json` `Entries` is the machine form).

Checked against two operation logs the tool did not produce (the public sample's Generate-FSActivity logs, a lab
volume's replay log): every
move and rename forefst reads that the log also holds has the log's class, and where the log covers the event and
never renames, moves or deletes the directory, the directory shown is the log's. The rows the directories alone
decide (`names not paired`) are not covered.

`mlog --parse -v` prints each redo record as `opcode  name  target_oid  @PLCN.blk+offset  key`, so each redo record
behind a row can be checked against the disk bytes (the row's time can come from the paired `$SI` update, which `-v`
does not print):

- `target_oid` is the record's table — its own path's, or marked `(inherited)` when it is the current table taken
  from an earlier record — and `(none)` when it is not determined (no table applies, or the record starts a redo
  block that starts a transaction);
- a file's name-link record also shows `link=0x.. "name"`, a reparent record `to=0x.. "name"` (or
  `to=0x.. FileId 0x..`): what the move or rename is read from.

Without `--parse`, `mlog -v` prints a table of the redo records and the LogCore record headers. That table gives each
record's **allocator clock** (record +0x20: the volume's allocator clock when the record was added, in decimal); it is
not a table identifier: one value is shared by records of different tables.

When the log holds opcode 0x2d, `mlog` (every mode) and `timeline` say once on stderr which of the builds read log a
table deletion with it and which refuse it. The `Dispatch table:` line of the text view names the opcode table the
volume's format selects, how many values it names and, for a value above 0x2b, which of the builds read dispatch it;
`mlog --info` lists the table per build.

See [MLog redo records](../structures/mlog_redo.md#concrete-actions--grouping-redo-opcodes-into-what-a-user-did).

| Option | Description |
|--------|-------------|
| `-v, --verbose` | with `--parse`: each redo record as `opcode`/`name`/`target_oid`/`@PLCN.blk+offset`/`key`; without it, a table of the redo records and the LogCore record headers |
| `--parse` | derive the concrete actions (file operations + low-level groups) with MOVE/RENAME parent OIDs |
| `--stats` | record-integrity check (every data record and both control copies: each record's own integrity value recomputed as the driver does) + opcode-frequency section |
| `--raw-scan` | per-page raw dump instead of the data-area summary |
| `--info` | the static opcode/action reference text (every opcode with its mnemonic and handler), then the control area's statements; no record is read |
| `--earlier-logs` | show only the records of earlier logs, in any mode above: another format magic is an earlier volume's log (the disk was formatted again), the volume's signature with another UUID an earlier log of this volume (the log was created again); each record carries its case (CSV/JSON `EarlierLogOf`: `earlier volume` / `this volume`, with the log's `FormatMagic` and `UUID`; in text `(an earlier volume's log)` / `(an earlier log of this volume)`); exit 0 |
| `--id ID` | with `--parse`, `--csv` or `--json`: only the log payloads whose records name one object -- a directory's table (its OID), or a file's rows, by its file id (a FileId row, a backing, in its home directory: exact) or by one of its names (the names the live tree and the change journal give it); each row says which (`MatchedBy` in CSV and JSON, `{by ...; Seq n}` in the text, with the row's place in the whole log), and stderr counts them. A row kept by a name can be another object that had the same name in the same directory |
| `--csv [FILE]` | one row per log payload: `Seq`, `Timestamp`, `TimeSource`, `DerivedAction`, `PathToday`, `ParentPathToday`, `Name`, `OID`, `Opcodes`, `OpcodesHex`, `RecordCount`, `PLCN`, `Block` |
| `--json [FILE]` | one document: `ReFSVersion`, `View`, `LogInstance`, `Control`, `ControlCopies`, `MLogInfo`, `EarlierLogs`, `DataArea`, `Integrity`, `Records` (each redo record once: its place, `PLCN` / `Block` / `BlockIndex` / `RecordOffset`, its fields, and what was read from its key, `TargetOID` / `Key` / `Time`; `AllocatorClock`, the record's +0x20 in decimal; `InheritedTableOID`, for a record without a table path the current table it applies to, derived, else null) and `Transactions` (one per log payload, with the CSV row's fields; `Opcodes` / `OpcodesHex` are lists; it refers to its records by their positions in `Records`, from 0: `FirstRecordIndex` with `RecordCount` when they are contiguous, else `RecordIndices`; `Entries`: `Pairs`, the moves and renames read -- `Kind`, `OldParentOID`, `OldName`, `NewParentOID`, `NewName` -- and `Removed` / `Added`, the names no pair takes); the document is written as a stream, so memory does not grow with the log |

**What `mlog` checks** (the driver's side of each test is on the [MLog](../structures/mlog.md#how-refssys-finds-reads-and-opens-the-log)
page). Only the log in use is read: the control copy refs.sys would use, each copy read as one 4 KiB record and
tested as the driver tests it.

Records whose format magic or UUID differ from the log's are left out and counted (`--earlier-logs` lists them): the
format magic is the volume's signature (from the superblock's volume GUID), the UUID the control payload's (`+0x28`).
Where the control record's own header disagrees with them, the view shows `Volume's magic` or `Payload UUID` beside
it.

Every mode that reads the records (all but `--info`), and `timeline`'s MLog source, exits 2 with a statement when:

- records stop before the log end the control area recorded (+0x20): the statement counts the 4 KiB log blocks from
  the newest record to the log end (one record can span several);
- the log end lies past the data area (stated with the log end and the data area's end; no count of missing records
  is made against it);
- the data area holds no record of the log although the log end says records were written (the records below the log
  end are missing, and how many cannot be counted).

Every mode, `--info` included, and `timeline`'s MLog source exit 2 with a statement when:

- the control copy in use fails its integrity check, or no control copy can be read (each copy named, with what was
  read there; the log's UUID is then unknown: records of another format magic are still left out, every other record
  is listed; the log start and end are unknown too, so whether the newest records are missing is not checked);
- refs.sys would not open the log: the Logfile Information Table (the failover pair OID 0xA, OID 0x9) has a copy
  missing (with both missing no log can be located), no row 1, a row 1 shorter than 48 bytes or a log size below 80
  clusters; or the control copy in use holds a log version (`Log version`, payload +0x40; refs.sys opens an existing log only at
  version 1) other than 1, a data range (+0x08 /
  +0x10) other than the table's, flags bit 0 clear, or a log start (+0x18) past the checkpoint's log position
  (CHKP +0x70; not tested by the 17134 driver);
- neither copy of the Logfile Information Table can be read, so the log's place is not determined;
- the Object Table could not be read in full and neither OID 0x9 nor OID 0xa is among the rows read: the Logfile
  Information Table could not be looked up, so no log record can be located (said as that, not as a missing table).

Each statement names the values read; with `--csv` / `--json` it goes to stderr when stdout carries the export, to
stdout when the export goes to a FILE. In every mode the control-record
tests above are made on the copy in use.

`--stats` and `--json` also report, with exit 2, the control copy not in use when it fails its check, a record that
fails its own integrity check, a table copy that is not the one read and fails (cannot be read,
or does not match the digest the Object Table records for its root page), two table copies that differ, and a
root descriptor carrying bit 0x8. Records written after the control area's last write are not covered (see
[Known issues](known_issues.md)).

```sh
forefst.py disk.raw mlog                               # control header + page census
forefst.py disk.raw mlog --parse                       # concrete file operations + low-level records
forefst.py disk.raw mlog --parse -v                    # same, plus the per-record byte-level proof
forefst.py disk.raw mlog --stats                       # record-integrity verdict + opcode frequency
forefst.py disk.raw mlog --earlier-logs --parse        # the actions of earlier logs
forefst.py disk.raw mlog --csv mlog_txns.csv           # export the action timeline
```

### `timeline` — super-timeline (USN + MLog + $SI MACB)

Experimental and informational: a corroborative reconstruction, not an authoritative log.

It merges three event sources — the USN journal, the MLog log payloads and the `$SI` MACB timestamps — into one list
sorted by time. The rows are **not joined** across sources (relating them, by identity, name and time, is the
reader's work), and what it covers depends on which journals are active (USN is off by default; the MLog is a shallow
circular buffer). `--fast`/`--no-si` skips the slow per-file `$SI` walk.

The **MLog** events use the same concrete-action classifier as `mlog --parse` above:

- a row labelled `MOVE` comes from a name removed and a name inserted, not from a bare row removal;
- a `DELETE` row means a table was destroyed within that log payload; the path shown is the row's directory and need
  not be the deleted object — confirm with the USN journal before reporting a deletion;
- an MLog row's time is the latest time its log payload's records carry (or the paired `$SI` update's, for a rename
  or delete that embeds none).

| Option | Description |
|--------|-------------|
| `--fast` / `--no-si` | skip the $SI MACB walk (USN + MLog only — much faster) |
| `-v, --verbose` | show the full name/path per event (no truncation) |
| `--csv` / `--json` / `--jsonl [FILE]` | machine output, to stdout or FILE (a record count on stderr): `Timestamp`, `TimeSource` (`USN record`, `$SI field`; for an MLog row `latest FILETIME of the log payload` or `paired $SI update`), `Source`, `OID`, `Name` (the name the source carries), `PathToday` (the live tree's path; none on a USN row), `Event`; `--json` is an object with `SourceCounts`, `Statements`, `Events` |
| `--source S` | keep only one source: `USN` / `MLOG` / `SI` |
| `--file SUB` | keep events whose path today (a USN row: its name) contains SUB; an MLog row's path is the directory the row names, as `mlog` gives it, so the file names a payload's records hold are listed by `mlog --parse` |
| `--oid O` | keep the events filed under object O (0x hex or decimal): a directory's own events and those of the files created in it. The `OID` column (below the table) says where each event is filed |
| `--id ID` | keep one object's events, by its id: a file's FileRef `HomeOID:FileID` (`files`' `ObjectRef`), a directory's OID (its rows carry `OID:0x0`): its `$SI` timestamps under every name, its USN records, and the MLog rows whose records name it: by its table (a directory), by its file id or by one of its names (a file), each row saying which; a name can be another object's that had the same name in the same directory |
| `--limit N` | keep only the first N events after filtering/sorting |
| `--depth N` | max recursion depth for the $SI walk (default: full) |

The `OID` column says where each event is filed:

- a directory's own OID;
- a file's **home directory** (the first half of its FileRef), in `$SI` and USN alike;
- for MLog, the directory the row names (as `mlog --parse` gives it).

A file stays filed under its home directory after it is moved, or named again by a hard link elsewhere, so `--oid` of
its *current* parent does not select it. Use `--id` for one file's `$SI`, USN and MLog events, or `--file`; an MLog
row `--file` finds is filed under a directory, as `mlog` gives it. With `--id` too, an MLog row is listed under the
table its log payload changed (its OID and path), which can be the parent directory's table, not the object's own.

What `timeline` states, and the exit code (with `--csv`/`--json`/`--jsonl` every statement goes to stderr when stdout carries the export, to stdout when it goes to a FILE):

- MLog rows of earlier logs (an earlier volume's log, left by a reformat; an earlier log of this volume, left when
  the log was created again) and MLog payloads with no embedded time are left out, each counted per case;
- MLog rows whose derived time is earlier than the volume's creation are kept with no time, and counted; when the
  volume's creation time cannot be read, the MLog rows' times are not compared with it, and that is said;
- every MLog condition `mlog` exits 2 on (see above), a re-created journal or missing journal records (see `usn`),
  and a USN record whose USN is not its offset in the journal: a statement, exit 2.

A USN record with no name (a `FILE_DELETE + CLOSE` carries none) is a row with an empty name, as `usn` lists it —
never filed under its home directory's path.

```sh
forefst.py disk.raw timeline --fast --limit 50         # quick USN+MLog timeline
forefst.py disk.raw timeline --csv > timeline.csv      # full super-timeline (CSV)
forefst.py disk.raw timeline --file hello.txt          # one file's $SI and USN events
forefst.py disk.raw timeline --source USN --oid 0x701  # USN events of directory 0x701 and of the files created in it
forefst.py disk.raw timeline --id 0x701:0x2             # one file's $SI, USN and MLog history
```

### `timestomp` — timestamp-anomaly detection

Experimental and informational. Flags timestamp anomalies (possible tampering) by comparing intrinsic $SI MACB
against USN-journal evidence and the volume's creation time (`PRE_FORMAT`; the last-mount time it prints is context,
compared with nothing). It tiers each flagged file HIGH, MEDIUM or INFO.

It also emits `HARDLINK_MACB_MISMATCH` — a ReFS-native, **journal-independent** signal. Each name's index entry keeps
a cached copy of the file's timestamps, refreshed only when that name is opened, so two names of one file can show
different Created values. Routine activity did not produce it on the corpus's one real installation; any
creation-time write made through one name produces it, whoever makes it.

Which name holds the true creation time is not established, and the signal's **absence means nothing**: the
file's own record takes the new time for every name at once, and any read of the file through another name
refreshes that name's entry and erases the difference.

| Option | Description |
|--------|-------------|
| `--all` | include every file, even those with no anomaly |
| `--min LEVEL` | lower the screen view's confidence floor: `HIGH` / `MEDIUM` / `LOW` / `INFO` (default: HIGH-only). INFO ranks below LOW, so only `--min INFO` shows it |
| `--margin-days N` | comparison tolerance in days (default 1) |
| `--csv [FILE]` / `--json [FILE]` | machine output (exports ALL tiers unless `--min` is explicit); no FILE or `-` → stdout. CSV columns: `ObjectRef`, `FullPath`, `RecordPlacement`, `DataResidency`, `Confidence`, `Basis`, `Signals`, `EvidenceRefs`, `Created`, `Modified`, `Changed`, `Accessed`; `--json` is an object with `Image`, `ReFSVersion`, `VolumeCreated`, `VolumeLastWritableMount`, `JournalPresent`, `JournalState`, `JournalTruncatedBytes`, `JournalLastUSN`, `FilesExamined`, `Counts`, `Rows` |
| `--depth N` | max recursion depth (default: full) |

The default screen view shows **HIGH-confidence rows only**, with a trailer counting the lower tiers; `--min
MEDIUM`, `--min LOW` or `--min INFO` reveals them (any other value exits 1). The CSV/JSON exports include every tier
unless you pass `--min`. The screen's `Changed` column is the `$SI` change time — the time the tool compares, which
a native-API stomp can set too, so it is not a proven last write. LOW is a tier no current signal reaches (`--min LOW`
shows HIGH, MEDIUM and LOW).

The header states the change journal's state and the earliest time a surviving journal record carries: a change
dated before it cannot be corroborated by the journal (where the clock stepped back, that time is earlier than the
time of the journal's first record). When the volume's `$VOLUME_INFORMATION` row cannot be read, the header says
`Volume created: not determined: <why>` and `Last mount (rw): not determined`, and `PRE_FORMAT` is not tested.

**What each signal means, and how often it fires.** Base rates measured over the corpus in a single pass. They are
corpus averages dominated by small purpose-built lab volumes: on the corpus's one **real Windows installation** the
copy signature fires on nearly every file (about 95 %), because installing an operating system
produces it. The counts are in the [Evidence](#evidence) section.

| Signal | Meaning | Base rate (about) | Weight |
|---|---|---|---|
| `HARDLINK_MACB_MISMATCH` | two names of one file disagree on Created ([above](#timestomp--timestamp-anomaly-detection)). Journal-independent; its absence means nothing | **0.04 %** | **HIGH** |
| `USN_BASIC_INFO_CHANGE` | the journal holds a record for this FileRef whose only reason is BASIC_INFO_CHANGE, and the file also carries `CHANGE_LATE`, `PRE_FORMAT` or `CREATE_GT_MODIFY` | — | **HIGH** |
| `USN_CREATE_MISMATCH` | the journal's create record disagrees with `$SI` | — | **HIGH** |
| `CHANGE_LATE` | change time post-dates create/modify | 22 % | MEDIUM **only without** `PRE_FORMAT` |
| `PRE_FORMAT` | created before this volume existed | 23 % | **INFO** (ambiguous — see below) |
| `CREATE_GT_MODIFY` | created after the last write | 1 % | **INFO** |
| `ROUND_TIMESTAMPS` | whole-second Created **and** Modified | 0.04 % | INFO alone; never lifts a tier |

`USN_BASIC_INFO_CHANGE` is a timestamp or attribute write with no content change.

The hard-link comparison takes a file's names from its **record**: only a record split out of its name row
can carry a second name, so those are grouped by their FileRef.

Each row's `storage` column is the file's data residency in the words `files` uses for `DataResidency`:
`(inline)`, `(extents)`, `(snapshot-shared)`, `(unallocated)` or `(unknown)`. It does not depend on the hard-link
grouping.

**Why `PRE_FORMAT` and `CHANGE_LATE` together are INFO — ambiguous, not cleared.** A program that writes a
file with older create/modify times and leaves the change time to the file system (Windows servicing and application
updates, with their package dates) writes create/modify from before this volume existed, so `PRE_FORMAT`, and the
change time of the write, so `CHANGE_LATE`. They are two halves of **one event**, not two agreeing sources, which is why tiering their co-occurrence as
corroboration is wrong.

**But the pair does not tell you what that event was.** Deliberately **backdating a creation time** can produce
the same two signals (or `PRE_FORMAT` alone) — a lab volume whose generator backdates creation times through the
file API carries this signature — so INFO must not be read as "legitimate, therefore innocent".

INFO means **ambiguous: a legitimate time-setting and a backdated creation are indistinguishable from `$SI` alone.** Only an independent
source separates them: the USN journal, a disagreement between the file's hard-link names, or the MLog's records of the
file (its creating transaction, and the call that set the times) while they survive. It is a lower tier; it does not clear the file.

Measured: the two occur together on almost every file that carries `CHANGE_LATE`; `CHANGE_LATE` occurs **without**
`PRE_FORMAT` on 0.33 % of the files carrying `CHANGE_LATE`, all on the one real Windows installation. Read as
corroboration, the pair would flag about **22 %** of the corpus and **95.4 %** of that real Windows volume at MEDIUM
or above — a flag on almost every file of an installed system. Under these tiers that volume's reviewable set is a
few hundred HIGH and a few hundred MEDIUM rows, against roughly 115,000.

What survives as evidence is `CHANGE_LATE` **without** `PRE_FORMAT` — a file created after this volume was formatted
whose metadata changed later (a rename, an ACL change, or a timestamp-preserving copy of a file itself created on or
after the format date) — plus the hard-link and journal signals. On the Windows volume those files are system
components whose change time post-dates their content, consistent with servicing writes; a MEDIUM tier says *look*,
not *tampered*.

`ROUND_TIMESTAMPS` is also produced by driver packages (VirtIO/QEMU), so round-ness suggests a set date but is not
proof.

```sh
forefst.py disk.raw timestomp                          # HIGH-confidence suspects (default)
forefst.py disk.raw timestomp --min MEDIUM             # reveal the MEDIUM tier too
forefst.py disk.raw timestomp --csv suspects.csv       # export ALL tiers to CSV
```


### `extract` — extract a file's content (or one ADS)

Recovers a file's bytes and writes them to stdout (redirect to a file, or `-o FILE`):

- **extent-backed** files from their extents — whether the file's record (which holds the extent map) is embedded in
  its name row, the common case on 3.14, or split out into its own record;
- **inline** files from the `$DATA` bytes in the record — including a file whose record was split out of its name
  row by a move or a hard link but whose bytes stayed inline inside that record;
- **snapshot-shared files unmodified since a snapshot** from the blocks they share with the latest snapshot;
- **unallocated** streams (no clusters of their own and no snapshot to share) as their size in zeros, which is what
  every byte reads as; the output says so, and a regular output file holds them as a hole.

Address by bare name, absolute `/path`, `--path` or `--id HomeOID:FileID`. Use `name:stream` to extract an ADS: from
its bytes in the record when it is inline, or from its extents when it is extent-backed (on format 3.11+, any stream
of 2 KiB or more).

When a file's extent map does not decode, `extract` writes nothing, says why and exits 2. `-o` naming an existing
directory is refused (exit 1) before anything is written. A modified-CoW file's prior
versions are in `snapshots --extract`.

The bytes written are the bytes the image holds. For a file without an integrity stream nothing on the volume says
what they should be, so zeroed or overwritten content comes out as it is, with exit 0; `integrity --checksums`
checks every file on the volume that carries one.

For a file that carries one (its own record split out of its name row included), `extract` checks each checksummed
cluster as it writes it:

- it says how many it verified (`integrity: 105/105 clusters CRC32-C-verified`);
- it adds how many of the file's clusters are in runs marked never written (written as zeros, nothing to verify) and
  how many are written but in rows that carry no CRC-32C (not verified), and how many are in rows whose flags declare a
  CRC64 per cluster (0x100, which refs.sys writes and reads; this tool verifies CRC-32C only, so not verified; no
  corpus row carries one);
- it exits 2 on a mismatch, and warns (exit 2) when it finds no CRC-32C row it reads in a file with extents.

An empty file that is a reparse point (a symlink, a junction) is written as 0 bytes, and the line says so with its
tag and, where its record holds one, its target — the path to extract for the data — whether that record is in its
name row or split out of it (`a REPARSE POINT, 0xa000000c (IO_REPARSE_TAG_SYMLINK); the link's own data stream is
empty; it points to ...`).

A file whose record was split out of its name row is listed by `files` even when the record holding its data
(its backing record) is not found; `extract` then says so (`the record holding its data (the backing of
ObjectRef …) was not found, so nothing is extracted`), writes nothing and exits 2, a recorded skip: the file
exists, its data was not read.

**An image that ends inside the file, or a cluster that cannot be read.** A range past the end of the image file is
known to be absent, unlike a hole, so by default the output ends at the last byte the image holds and a warning says
how many bytes are missing and where they start (a recorded skip, exit 2); a cluster that cannot be read ends the
output at that cluster the same way. `--fill-holes` writes zeros for those bytes instead, and the warning says they
were zero-filled, not read. When the decoded extents cover less than the declared size and the image does not end
inside them, the file is written as far as they go and a warning gives the bytes extracted against the declared
size.

A file larger than 256 MiB is written as it is read, never held in memory. A range its extent map marks as a hole (a sparse range of the file itself, not an image hole) reads as zeros: in a file larger than 256 MiB written with `-o FILE` into a regular file it is left as a hole in FILE, which reads back as zeros; otherwise it is written as zeros. If the write fails, the part written is removed and the error names FILE.

**Bytes that came from image holes are reported, not withheld.** A raw image is often stored sparsely (this
project's corpus is stored in a small fraction of its apparent size), and a sparse image stores a file's **own zero
content** exactly the way it stores a range that was never captured: as a hole. `cp --sparse=always` alone
takes a 67 MB sample to 40 MB by converting real zero clusters into holes. A hole is therefore **not**
evidence that data is missing, and the tool makes no such claim.

When any part of a file's data comes from a hole, `extract` **writes the bytes**, reports the hole ranges (for a
file reassembled from shared blocks, the hole byte count), then exits **2** so a script can branch on it. With
`-o FILE` it also writes `FILE.holes.json`: the ranges, or the byte count where the ranges cannot be known (it is
written for a clean file too). The wording is deliberately neutral: the image cannot distinguish "never written"
from "not captured", so neither can the report — it says the zeros are unconfirmed in both directions and to
corroborate them.

Pass **`--refuse-holes`** for a strict run: same report, same exit code, nothing written.

### Which commands check, and what each one does about it

Every command that writes file content runs the same check. What differs is *where* the report goes, because a
single file and a directory of files need different artifacts.

| producing command | note | exit 2 | sidecar | `--refuse-holes` |
|---|---|---|---|---|
| `extract` (own extents, inline, snapshot-shared, ADS) | yes | yes | `FILE.holes.json` with `-o` | writes nothing |
| `export deleted` (recovered + `--carve`) | yes | yes | `holes.json` in the export directory | skips the affected files |
| `export snapshots` / `snapshots --extract` | yes | yes | `holes.json` | skips the affected versions |
| `export resident-all` | yes | yes | `holes.json` | skips the affected files |
| `export recyclebin` | yes | yes | `holes.json` | skips the affected payloads |
| `export metadata` (the USN `$J` stream) | yes | yes | `holes.json` | skips `usn_J.bin` |

Two differences from `extract` are deliberate. A bulk export writes **one** `holes.json` for the run rather
than one file per output, naming each affected stream and its hole byte count, with paths relative to the
export directory so the directory stays portable. And `--refuse-holes` withholds **per stream**: the affected
outputs are not written, every clean output still is, and the refused list is in the sidecar. Refusing the
whole run would discard good evidence because one file was affected.

The sidecar is written even when nothing drew from holes (`"status": "none"`). An examiner keeping sidecars
beside extracted files should not have to infer, from a missing file, whether the run was checked and clean
or never checkable.
When the host cannot say whether a stream's bytes lie in holes, the sidecar's status is `undeterminable` and
names the stream, the command exits 2, and `--refuse-holes` withholds that stream too; the refusal line on
stderr gives each cause (holes found, or coverage not checked).

The reported ranges are the **holes**, not the extents containing them, and adjacent ranges are **merged**:
a hole that spans two extents is one range, because the split at an extent boundary describes the extent
map rather than the gap. Two ranges in the list therefore mean two separate gaps; between them lies captured data
or a sparse range of the file itself.

**The exact trigger.** The check fires when **any** byte of the file's data range lies in a hole of the image
file, tested with `SEEK_DATA`/`SEEK_HOLE` against the decoded extent list and clipped to `[0, file_size)` so
allocation slack past EOF is never counted. If the platform cannot answer, the run says so once on stderr ("could
not check whether the bytes this run read come from holes in the image file") and records it as a finding, so
the command exits 2 — never silently read as "no holes". It reports the true hole intervals, not the extents
containing them.

Expect it often on a sparsely-stored image: on one lab volume nearly every file has holes inside its
data range, and all of them are correct — the generator writes a 10-byte marker and then sets the file
length, so the tail is genuinely zero.

`rc == 2` from `extract` means *read the note*: on a sparse image it is most often this hole report, but the same
exit code also reports an integrity-stream checksum mismatch and an image that ends inside the file: each of those
is a finding.

**What it does not use.** It does not consult the valid-data-length field. ReFS keeps the field documented as the
valid data length in the file's multi-instance `$DATA` sub-record (value `+0x40`, measured on 3.7-3.14; v3.4:
`+0x44`, untested), not in the name row's value this check reads the sizes from (size `+0x58`, allocation `+0x60`),
whose bytes at `+0x40` are a timestamp. On every non-empty record of the corpus that field equals the stream size,
also on a file written as a short marker and then extended, so it would not separate *allocated but never written*
from *written but not captured* either; no behaviour is keyed on it.

Addressing by a full `/path` resolves it directly from the root (no depth limit); a **bare name** is searched
across the tree (to `--depth`) and the first match is extracted — pass the full path to pick a specific file when
the name is not unique.

**Case.** ReFS folds case by default, so a path resolves whatever case you type it in. Where a directory
carries the per-directory case-sensitive flag (`fsutil file setCaseSensitiveInfo`) it can hold two names
that differ only by case, and there the **exact spelling wins**: `hi.txt` and `HI.txt` each return their
own bytes. For a path, a spelling that matches nothing exactly falls back to a case-insensitive match, so
addressing a file by the wrong case keeps working on an ordinary directory. A bare name must match exactly: give the
path when you are unsure of the case.

| Option | Description |
|--------|-------------|
| `filename` / `/path` | (positional) the file to extract (full path = direct, no depth limit) |
| `--path P` | address the file by path (symmetric with `details`; resolved directly) |
| `--id HomeOID:FileID` | address the file by its reference (its home directory's OID and its ordinal, the `ObjectRef` column) — no path needed |
| `--oid O` | re-root a **bare-name** search at object O |
| `--depth N` | max depth for a **bare-name** search (default: full; a full path ignores this) |
| `--no-verify-integrity` | skip the per-cluster CRC32-C check on integrity-stream files |
| `--refuse-holes` | strict: report hole-sourced ranges and write nothing (default is to write the bytes and report) |
| `-o, --output FILE` | write the bytes to FILE (as `FILE.partial`, renamed when complete), with `FILE.holes.json` beside it |
| `--fill-holes` | write zeros for bytes past the image's end or in a cluster that cannot be read, instead of ending the output there (the warning says they were zero-filled) |

```sh
forefst.py disk.raw extract /specials/gamma.bak > out.bak   # extract by absolute path (any depth, direct)
forefst.py disk.raw extract report.dat:hidden_6247 > s.bin  # extract one inline ADS
forefst.py disk.raw extract deep.log --oid 0x73c            # scope a bare-name search to a subtree
```

### `security` — security descriptors / ACLs

Lists each security descriptor (owner, group, control flags, DACL/SACL ACEs). `--files` maps every file to its
SecurityId+owner.

`--audit` recomputes each descriptor's content hash (the security table, OID 0x530) and reports any that no longer
match the hash stored with it; an edit that also rewrites the hash passes. Its verdict is `CLEAN` only when every
descriptor's hash matches over a table read whole. When part of the table could not be read, or the table's root page
does not match the digest the Object Table recorded for it, the verdict is `UNDETERMINED` with the reason, and the
command exits 2.

| Option | Description |
|--------|-------------|
| `-v, --verbose` | include the raw SD hex dump |
| `--files` | map every file/dir to its SecurityId and owning SID |
| `--file SUB` | like `--files`, filtered to names containing SUB |
| `--sid ID` | print only the descriptor for SecurityId ID |
| `--audit` | tamper check: recompute each SD's content hash |
| `--json` | machine-readable output |

```sh
forefst.py disk.raw security                           # list all descriptors
forefst.py disk.raw security --files                   # map files to owners
forefst.py disk.raw security --audit                   # verify SD hashes
forefst.py disk.raw security --sid 0x1db3cc93d -v
```

### `specials` — special-attribute files (one discoverable home)

Lists files and directories carrying a special attribute:

- no argument prints a **count summary** of every type;
- `specials <type>` prints that type's list with type-specific columns;
- `specials all` prints every section.

It is the discovery/list layer (equivalent to `files --filter <type>`, which still works) — for deep operations use
`reparse --index`, `snapshots --extract`, `dataruns`, or `export ads`.

| Type | Shows |
|--------|-------------|
| `ads` | each named data stream + its host file (`export ads "file:stream"` to pull one) |
| `reparse` / `wsl` | tag + kind (symlink/junction/WSL) + target |
| `hardlink` | link groups (all names of each multi-linked file) |
| `sparse` | logical vs allocated size + bytes saved (`dataruns` for the extent map) |
| `encrypted` / `compressed` / `integrity` / `ea` / `snapshot` | the matching files, as `ObjectRef` and path (for `snapshot` also the number of snapshots of each) |

```sh
forefst.py disk.raw specials              # count summary of every type
forefst.py disk.raw specials ads          # every ADS + host file
forefst.py disk.raw specials hardlink     # hard-link groups
forefst.py disk.raw specials all --json   # every type, machine-readable
```

### `reparse` — reparse points (symlinks / junctions / WSL)

Walks the tree for files with the REPARSE_POINT attribute and decodes each buffer (tag, target) and, for a WSL file,
its UID/GID/mode. `--index` dumps the reparse index object (OID `0x540`).

| Option | Description |
|--------|-------------|
| `-v, --verbose` | include the raw reparse-buffer hex / index key bytes |
| `--index` | switch to the reparse INDEX view (OID 0x540) keyed by tag |
| `--tag T` | filter to one reparse tag (0x hex or decimal) |
| `--file SUB` | default mode: filter to names containing SUB |
| `--json [FILE]` | machine-readable output, to stdout or FILE |

```sh
forefst.py disk.raw reparse                            # all reparse points + targets
forefst.py disk.raw reparse --index -v                 # dump the reparse index
forefst.py disk.raw reparse --tag 0xa000000c --json    # only Windows symbolic links (IO_REPARSE_TAG_SYMLINK), as JSON
```

### `deleted` — the deleted-file view (list + recoverability)

`deleted` is a **read-only view** of the rows recovered from metadata pages — best effort, apart from the volume's
current content — each with what it is and a recoverability verdict. To **write files out**, use
[`export deleted`](#export--get-data-out-one-home-for-every-extraction-path). Two modes:

- `deleted` — the **recovery** pass (default): the Trash table, the checkpoint comparison and the slack scan of the
  pages the live tree uses. It recovers the common in-tree deletions.
- `deleted --full` — the **full** pass: also every cluster of the volume read for old pages (the freed pages of
  deleted objects), which finds the older deletions whose directory entry is gone from the tree; under `export
  deleted` it also carves extent-backed content.

**Recovery methods** (Windows `$RECYCLE.BIN` is separate — see [`recyclebin`](#recyclebin--decode-recyclebin-i-metadata)):

| Method | When | Finds |
|--------|------|-------|
| Trash table (`0xD`) | always | the row of each object deleted but not yet reclaimed, listed raw: its `ObjectRef` (the row's key is the object's reference) and its record (the value) |
| Checkpoint diff | always | the two checkpoints' trees compared object by object (by ObjectRef), at any depth: the objects in the other checkpoint's tree (the previous one, or the newer one when the newest copy is not used) and not in the current one, those renamed or moved (or with a hard-link name removed or added), and those added; content and metadata are not compared |
| B+-tree node-slack scan | **default** (skip with `--no-slack`) | deleted rows still sitting in a tree page's free space — plus the folder whose page holds each row (owning-table OID `page+0x48` → path; blank when the page names no owner). An owner that is not a live directory is shown as `$DELETED/DIR_OID_0x<oid>/`, with the deleted folder's name offered as a best-effort, ambiguity-flagged hint |
| Old-page scan | `--full`, `--scan-pages` | the rows each **old page** (a metadata page the live tree no longer references) still lists, or holds in its free space, whole volume |

`--no-slack` gives a fast Trash + checkpoint pass, `--trash` returns after the Trash table only; filter with
`--search SUB`.

The header's `Checkpoints:` line lists every checkpoint copy that carries a clock, the copy in use first, each with
its role (`in use`, `newest`, `superseded`, `tied`) and, where it applies, `self-checksum FAILED`, `checksum
cannot be verified` or `root list could not be read`: a copy newer than the one the volume is read from is named,
with why it is not used. The checkpoint comparison compares the copy in use with the next copy of that list whose
root list could be read: the **previous** checkpoint, or the **newer** one when the copy in use is not the newest
(the newest copy failed its self-checksum, for example, and an older one is read); the comparison's lines and rows name it so (`PreviousPaths`
holds that copy's paths either way). A condition of that copy that `summary` reports (it fails its self-checksum,
its checksum cannot be verified, refs.sys rejects it, a root 0xc, 7 or 8 does not verify) is printed above the
comparison and makes `deleted` exit 2: the comparison reads that copy.

**What each entry is.** Every entry is a row found in a metadata page — what the page holds, not the volume's current
content — and its **Status** is decided by the identity the row records (a directory row's own OID, a split row's
home + ordinal, an embedded row's FileRef from the change-journal record its `LastUsn` points to). The view lists
the entries under five headings, in this order:

| Status | Meaning |
|--------|---------|
| `DELETED` | the identity the row records (`ObjectRef`) is live nowhere |
| `DELETED, OR RENAMED` | no live file has this name + creation time, and the row records no identity the tool can check, so a rename or a move is not ruled out |
| `RENAMED` | not deleted: the same file (by the row's `ObjectRef`) is live under another name — a rename, a move with a new name and a removed hard-link name read alike |
| `SAME FILE, OTHER CREATION TIME` | not deleted: the same file is live under this name, and its creation time was set after this row was written (a lead for timestomping) |
| `STILL PRESENT` | a live file has this name + creation time, and no copy records the identity of another object |

A row whose recorded identity is **another** object's (a file deleted and a new one made with the same name and
times: a copy, a move by copy-and-delete, a safe-save) is its own entry, decided by that identity. For an entry
whose file is live, the view says whether the row is a copy of the current entry (`same`: all four times equal a live
row's) or an earlier version (`[earlier version: ... differ]`, the times that differ named; the `Dates` column).
`FOUND IN` is the folder whose page held the row (its path today), not necessarily where the file was deleted from.
One entry stands for every copy of the same row; the longest copy is shown, and the copies are counted (`Copies`,
`CopiesDiffer`).

**The view.** For each page scan, a table comes first: each status by what can be recovered from its rows -- `bytes
in the row` (written as found by `export deleted`; a live file's starred, not written: `extract` gives its current
content), `carve possible` (the extent map survives), `metadata only`, `directory`, `empty`. Then one line per entry,
under its status:

```text
  ── DELETED, OR RENAMED: 21 (no live file has this name + creation time; a rename is not ruled out) ──
    RECOVER        CREATED                       NAME                                           FOUND IN
    carve          2026-05-23T08:46:26.7071666Z  FVE2.{09cf57b8-9e6c-43d4-ae1f-0408882a397d}.1  System Volume Information
```

`RECOVER` is the entry's column in the table. After `FOUND IN`, a `RENAMED` entry gives the live name (`[now: ...]`),
a `SAME FILE, OTHER CREATION TIME` entry the live file's creation time, and an earlier version the times that differ. `-v` prints each entry's block instead: where its row
lies (cluster, offset, image offset), both times, the identity read and where from, the copies found, and the
recoverability verdict in full. Unless exporting, the view ends with the `export deleted` command that writes what it
found (`To recover:`).

**Where a row was found** (`RecoverySource`): `slack of a live page` (the free space of a page the live tree uses),
or, on an old page (read by `--full` and `--scan-pages`), `slack of an old page` or `listed on an old page`. Both
old-page scans read each old page whole and skip every page of the live tree. A page whose header carries another
volume's signature (`+0x0C`) is not this volume's: it is left out and counted (`--earlier-volumes` shows those
rows). A page with this volume's signature that does not lie at the address it names (`+0x20`, in its own units) is not read either: such bytes are a copy of the volume's pages inside a file's content (an image or a backup of its metadata) or a page whose address is damaged; the scan says how many clusters that was (the exit code is unchanged). A cluster the scan cannot read is counted: the coverage line gives the clusters read, says **INCOMPLETE**,
and the run exits 2.

**Recoverability verdict.** Every entry carries a verdict, computed by running the *same* inline-`$DATA` decoder
used for live files on the captured remnant bytes:

| Verdict (as printed) | Meaning | `export deleted` writes |
|---------|---------|--------------------------|
| `content inline` | the bytes the row holds inline | `content/<name>`, the bytes as found |
| `content inline in the file's type-0x40 backing` | a split file's data, inline in its backing record found in slack (joined by file id + home + size) | `content/<name>`, the bytes as found |
| `empty` | the row declares 0 B inline (for a symbolic link: its target is not recovered) | nothing to write |
| `metadata + carve` | the data is in extents whose **map** survives (in the row, or in a type-0x40 backing found in slack — then marked "bytes may be stale") | `content/<name>.carved` with `--carve` (best-effort; see below) |
| `metadata only` (with a reason) | a map survives but the carve plan makes no carve from it: every run unwritten, only sparse holes, above the size limit, outside the volume, a malformed row | an index row only; `NoCarveReason` says why |
| `metadata + extent map, not carved` | the same file is live, so no carve is offered for an earlier version; the verdict says where the map's clusters are now, from every live file's extents read once per run: the live file's at the same offsets (which `extract` reads), another live file's (named), in no live file's extents (stream snapshots and metadata pages not checked), or the count of each | an index row only |
| `metadata + N B inline, not written` | the same file is live (`extract` gives its current content), and an earlier row's bytes are not given as a version of it | an index row only |
| `metadata only` | the file's data is not in this remnant | an index row only (name/size/timestamps) |
| `content zero or absent` | the `$DATA` descriptor survived and still declares N inline bytes, and that region reads as zeros — the file held zeros, or the deletion took the bytes, and the remnant cannot separate the two | an index row only — **no content file** |
| `directory entry` | a directory holds no file data | an index row only |

The verdict is annotated for EFS (`CIPHERTEXT`) and for a row whose two timestamps are both outside 2009-2050
(`corroborate`). "Recoverable" means the bytes (or their extent map) are **present** in the remnant, *not* that they
are un-overwritten (there is no allocation/freshness check). A deletion can leave the descriptor while taking the
bytes; the declared region then reads as zeros — but so does a file that genuinely held zeros, and **nothing in the
remnant separates the two**, which is why the verdict names both and the tool writes no content file either way. A
file of real zeros is therefore withheld as well; that is rare (measured at roughly one live file with inline data
in several thousand) and the trade is deliberate — the record, name, size and timestamps are still reported, and an
evidence tool should not hand you bytes it never read, nor assert which of two explanations produced them. Count the
deleted files' recovered content by `ContentFile` in `deleted_files.csv`; each carve's account is in
`recovery_manifest.json` (`Carve`: the declared clusters read, zero-filled and why, the map's gaps, and each
cluster checked against the CRC-32C its map stores, where it stores one).

> **Inline vs extent-backed — what you can restore.** An **inline** deleted file's *full content* is recovered
> straight from the remnant (`content/<name>`).
>
> An **extent-backed** file keeps its data in separate on-disk extents, but the *extent map* can survive: in the
> record itself, or in the file's type-0x40 backing record. The backing is unlinked from the live tree at deletion,
> yet its body persists in page slack (on the same page or another) and is matched back to the name by `file_id` +
> home + size. `export deleted --carve` then reconstructs the file from those clusters **best-effort** (they may have
> been reallocated — the output is labelled `.carved` and flagged in the manifest).
>
> Only when the remnant holds neither the data nor a usable extent map is nothing but the record recoverable here. A
> complementary, not-yet-implemented method — **whole-disk signature carving** (scan every cluster for file magics,
> filesystem-agnostic) — could recover some of those files (those with a known header and contiguous, unreused
> clusters).

**What each depth costs.**

- The recovery pass reads only pages the tree walk already touches, plus — when an entry's file is live — every live
  file's extent map once, to say where that entry's map clusters are now. It takes seconds on small volumes and
  minutes on large ones (a few minutes on the two Windows Server Insider system volumes of the test corpus).
- `--carve` is **moderate**: it reads the data extents of each recovered extent-backed file, so its cost follows how
  much deleted data you reconstruct.
- `--full` and `--scan-pages` are **slow** — they read *every cluster on the volume* looking for old pages, so their
  cost follows the volume's size; measured on this project's host: at most 6.4 s on the 101 ReFS volumes up to 8 GiB measured,
  134 s and 250 s on the two 60 GiB ones, **25.5 min on a 2 TiB volume** (about 1.44 GB/s), about 3.2 h projected
  for 15 TiB; the scan prints its progress.

These scans cover the whole volume **by default** and print, after the scan, the clusters they read: a cluster that
could not be read is subtracted, and the line says **INCOMPLETE** (exit 2), on the screen and in the recovery log.

On a metadata bundle they read only the clusters the bundle carries (the live tree's pages), and the line says so
(**INCOMPLETE**, exit 2): a bundle cannot show deleted data outside the live tree.

`--max-scan N` trades that completeness for speed by stopping after N clusters; a bounded run is reported as
**INCOMPLETE** in the output and the recovery log.

| Option | Description |
|--------|-------------|
| `--full` | **slow**: also scan every cluster for old pages, and under `export deleted` carve extent-backed content |
| `--no-slack` | skip the slack scan (fast: Trash table + checkpoint diff only) |
| `--trash` | only the Trash table (its raw rows), then return (fastest; view only — no `--csv`/`--json`/export) |
| `--scan-pages` | **slow**: also run the old-page scan across the whole volume |
| `--slack` | run the slack scan (already the default) |
| `--orphans` | add a **low-confidence** tier: Object-Table OIDs unlinked from the tree (identity-filtered; opt-in) |
| `--earlier-volumes` | **slow**: show only the rows of the metadata pages an earlier ReFS volume left on the disk (another volume's signature at the address the page names, read in the page's own cluster size; the area was formatted again), grouped by that signature, never mixed with this volume's entries or matched with its files; `VolumeSignature` first in the machine outputs |
| `--carve` | with `export deleted` only (a view carves nothing): carve files whose data is in extents into `content/<name>.carved`, best-effort (on by default under `--full`) |
| `--later-data` | with `--carve`: also write, to a separate `content/<name>.later`, what the clusters of the runs this version marks **unwritten** hold now (the carve itself always zero-fills unwritten runs and holes: that version held no data there). It may be the file's later data or another file's, and it is never merged into the carve. Clusters of such a range that cannot be read (past the image's end, or a read error) are zero-filled in the `.later` file too, and the run says how many bytes that was. Every such range is listed in `recovery_manifest.json` (`UnwrittenRuns`, `HoleRuns`) |
| `--search SUB` | filter recovered entries by name substring |
| `-v`, `--verbose` | each entry's block (where the row lies, both times, the identity, the copies, the verdict in full) in place of its one line |
| `--no-system` | drop OS/BitLocker (`FVE2.{…}`) system churn from every output (the index, the machine outputs, the recovery log, the export) |
| `--max-scan N` | stop the old-page scan after N clusters. Default: **no limit** — the whole volume is scanned. Bounding it makes the run faster but **INCOMPLETE** |
| `--rows` | with `export deleted`: also write the raw remnant bytes to `rows/` (provenance) |
| `--rows-only` | with `export deleted`: write only `rows/` and the index |
| `--content-only` | with `export deleted`: content + index only (the default) |
| `--csv` / `--json` / `--jsonl [FILE]` | a row for **every** entry the view prints (the Trash table's raw rows, the checkpoint comparison's objects, both page scans' entries of every status, `STILL PRESENT` included, the `--orphans` tier), each with its `Status`, to FILE or to stdout (the report then goes to stderr). Columns: `FileName`, `IsDirectory`, `RecoverySource`, `RecoveredFrom`, `Recoverability`, `Created`, `Modified`, `RecoveredChild`, `Cluster`, `FileAttributes`, `Category`, `Reliability`, `ContentFile`, `FileAttributesHex`, `Status`, `LiveFile`, `ObjectRef`, `IdentitySource`, `FoundInTable`, `Offset`, `PlausibleTimes`, `Copies`, `CopiesDiffer`, `PreviousPaths`, `RawKey`, `RawValue`, `SameNameTimeLive`, `FormerLocation`, `Dates` (`same` / `differ`, for an entry whose file is live), `DatesDiffer` (the times that differ) — the columns of the exported `deleted_files.csv`, which adds `SHA256` and `RenameReason` |
| `--log PATH` | write the recovery-run log here; also forces a log on a plain view (when exporting, the default is `<export-dir>/recovery_log.txt`) |
| `--extract DIR` | **deprecated** — use `export deleted DIR` |

```sh
forefst.py disk.raw deleted                            # Trash + checkpoint + slack (default) + recoverability
forefst.py disk.raw deleted --no-slack                 # fast: Trash + checkpoint diff only
forefst.py disk.raw deleted --trash                    # fastest: Trash-only check
forefst.py disk.raw deleted --search report            # only deleted entries named like 'report'
forefst.py disk.raw deleted --earlier-volumes          # the rows an earlier volume (the disk formatted again) left
```

### `recyclebin` — decode `$RECYCLE.BIN` `$I` metadata

Walks `$RECYCLE.BIN/<SID>/` and decodes each `$I` metadata file — the **original full path**, **deletion time**, and
**logical size** of a recycled item — and reports whether its `$R` payload still survives.

Filesystem-agnostic Windows format (`$I` header `1` = Vista–8.1, `2` = Win10/11). Each `$I` is read through the same
content reader as `extract`: from the record on format 3.11 and later, from its extents on 3.4-3.10.

| Option | Description |
|--------|-------------|
| `--json` | machine-readable output |

```sh
forefst.py disk.raw recyclebin                         # original path + deletion time per recycled item
forefst.py disk.raw recyclebin --json
```

### `snapshots` — stream snapshots (CoW versions)

Inventories files carrying **stream snapshots** — prior versions kept by ReFS's copy-on-write / block-clone mechanism
(0xB0 records, `storage_type≠0`, `sub_id≥0x1000`) — and can recover/preview or extract each version's content.

A hard-linked or moved file is included: its versions are in its backing record, and it is listed once, under one of
its names, with the others named. Extraction is also available as
[`export snapshots`](#export--get-data-out-one-home-for-every-extraction-path).

| Option | Description |
|--------|-------------|
| `-v, --verbose` | per-snapshot allocation/id/value details |
| `--show` | recover & preview each snapshot's prior CoW content |
| `--file SUB` | only files whose path contains SUB (a fuller path disambiguates same-named files) |
| `--snapshot SEL` | select versions: a 1-based `[N]` index (one version), or part of a version name (every version whose name contains it, case-insensitively) |
| `--depth N` | max recursion depth (default: full) |
| `--extract DIR` | write each recovered version into DIR, with an `export_index.csv` (see [export](#export--get-data-out-one-home-for-every-extraction-path)) |
| `--json` | machine-readable inventory; `--file` and `--snapshot` select in it as in the listing. Not with `--extract` (exit 1) |

```sh
forefst.py disk.raw snapshots                          # list files with snapshots
forefst.py disk.raw snapshots --file lasttest.txt --snapshot first --show   # just one version
forefst.py disk.raw snapshots --file lasttest.txt --show -v
forefst.py disk.raw snapshots --extract ./recovered --depth 12
```

### `integrity` — verify metadata-page checksums

Structural audit of metadata pages:

- the default is a fast verdict;
- `--checksums` verifies the system root tables (Container-Table child pages included) and the root page of every
  object;
- `--fullchecksums` extends to every page of every object B-tree (CRC64 or SHA-256), including the child pages below
  a file's extent index and below its embedded attribute index, which no B+-tree row names (their references are
  inside a row's value): the extent index of every stream in extent form, in the key form of ReFS 3.4 and in that of
  3.7 and later.

> **Page-reference checksums (`integrity --checksums`).** This recomputes the checksum that each object's
> Object-Table row (the one in use) records for the object's root page, so it tells you whether each object's root
> page is the page the volume recorded; pages below the roots need `--fullchecksums`. The digest covers the whole
> page, after container translation. It is one page read per object (16 KiB, or 64 KiB on 64 KiB-cluster volumes),
> and the corpus's real Windows installation has tens of thousands of objects, so it is gated on `--checksums` like the other deep
> verification; the default `integrity` is much faster.

The checksum section's `Coverage:` line and its `VERDICT:` line name what was verified, and the VERDICT speaks for
those pages only: `VERDICT: all 15 checksummed pages of the system root tables VERIFIED — no tampering or corruption
detected in these pages (a checksum cannot prove the absence of a deliberate edit); the object B+-trees' pages below
their root pages are not covered: run --fullchecksums`.

- Under `--fullchecksums` the count of index child pages verified is part of both lines (`the system root tables and
  250 object B+-trees, with the 29 child page(s) below their extent and attribute indexes`).
- A condition of the checkpoint the volume is read from is named in the VERDICT in its own words.
- A page in an image hole is counted with the scope of the walk that met it (`In image holes: 1 of the 15 pages this
  checksum walk reached`; in bundle mode `In holes:`, the source image's or not carried by the bundle).
- The page walk's `Volume sig matches` and `VC within bounds` count only pages with a valid signature, so with
  `Valid signatures` they add up (`integrity --json`: `PageStatistics.PagesVolumeSignatureMatch` +
  `PagesVolumeSignatureMismatch` = `PagesValidSignature`).
- A page whose reference declares a checksum the tool does not compute (type 5, XXH64) is counted under `Checksum not
  computed`, not with the unchecksummed pages: it is not verified, and the coverage is then incomplete
  (`integrity --json`: `ChecksumVerification.NotComputed` and `NotComputedTypes`, present only when such a page is
  met).

The header lists the Container Table's rows ("Container map: N entries") and, when there is one, each container
the tools do not translate ("Container not read: 0x5: <reason>"; a read into it is a recorded skip, exit 2).
**A limit no check removes:** a container moved to other clusters with every digest covering it recomputed (the
table pages' digests and the checkpoint's own checksum) cannot be detected from the image — such a re-signed move
leaves the Container Table consistent, and the checks read it as the volume's. Two containers mapped onto overlapping
clusters, or a page that records another address than the one it was read for, are reported (exit 2).

With `--checksums` it also verifies every file that carries an **integrity stream**: each checksummed cluster is read
and its CRC-32C compared with the one the volume stores (`--json` carries this section as `IntegrityStreams`).

- It reports the clusters carrying a CRC and the clusters checked — counted per file, so block-cloned copies that
  share physical clusters each count theirs.
- It says "every … matches" only when every cluster carrying a CRC was checked, apart from any the output says were
  never checksummed by the driver, and no file or subtree of an extent map was left out. Anything short sets the exit
  code and is reported with a count, naming only the first five files it affects.
- An integrity file's clusters in extent rows that carry no CRC-32C are counted by what the row says: a run marked
  allocated but never written holds no data (it reads as zeros, and there is nothing to verify) and is counted on
  `Never written`; a written run without a CRC-32C is counted on `Clusters without a CRC` and is not verified. On the
  corpus every such run is marked never written. A run whose row declares a CRC64 per cluster (flags 0x100) is counted
  on `CRC64 clusters` and is not verified (no corpus row carries one). The VERDICT speaks for the checksummed clusters.
- A file whose stream holds allocated clusters but no CRC-32C row the tool reads is counted as not examined (exit 2);
  integrity files with no data in clusters are counted beside the files with a stream.

A file without an integrity stream has no checksum on the volume and cannot be checked this way. ReFS 3.4 volumes
carry the same inline CRC-32C as 3.7 and later.

| Option | Description |
|--------|-------------|
| `-v, --verbose` | per-page details (capped 200) |
| `--checksums` | verify the system root tables' checksums and each object's root page |
| `--fullchecksums` | verify every page of every object B-tree, the child pages below extent and attribute indexes included (implies `--checksums`) |
| `--scan-range A-B` | raw mode: inspect each LCN in the range standalone |
| `--max-pages N` | cap the checksum crawl (default 300000) |

```sh
forefst.py disk.raw integrity                          # fast structural verdict
forefst.py disk.raw integrity --checksums              # verify system-root checksums
forefst.py disk.raw integrity --fullchecksums -v       # full sweep + page details
```

### `export` — get data out (one home for every extraction path)

`export <what>` consolidates every "get data out" path. `export file` and `export ads` write one file or stream to
disk; `extract` writes it to the screen. A bare `export -o DIR` (no subverb) is the metadata bundle.

The bytes are reported against the image's holes as `extract` reports them: see
[Which commands check, and what each one does about it](#which-commands-check-and-what-each-one-does-about-it).

**Output convention.**

- `export file` and `export ads` write to the current directory under the file's name (`-o DIR/` into DIR,
  `-o FILE` to FILE, `-o -` to the screen).
- `export reparse` prints to the **screen** and reminds you to add `-o FILE` to save it.
- A **bulk** subverb (`resident-all` / `snapshots` / `deleted` / `recyclebin`) writes to a **directory** — and if you
  omit the directory it auto-creates a timestamped `forefst_export_<what>_<YYYYMMDD-HHMMSS>/` (and tells you where),
  so a forgotten path never errors or dumps binary to your terminal.
- `export metadata` needs its directory (`export metadata DIR`, or `-o DIR`).

| Subverb | Gets out |
|--------|-------------|
| `export file <path>` \[`-o FILE`\|`DIR/`\|`-`\] \| `--oid O` | one file's live `$DATA` (inline / snapshot-shared / extents), read as `extract` reads it, written to `./<its name>` (with `-o DIR/` into DIR), never over a file: a name taken is written `<name>.dupN`; the name follows the bulk exports' rule (letters, digits, `.`, `_`, `-` and space kept, any other character `_`) and the stderr line gives the name on the volume when it differs; `-o FILE` writes FILE, `-o -` the screen |
| `export ads "<path>:<stream>"` \[`-o FILE`\|`DIR/`\|`-`\] | one alternate data stream — inline (small) or reassembled from extents (on format 3.11+, ≥ 2 KiB) — written to `./<file>__<stream>` by the same rules |
| `export reparse` \[`--json`\] \[`-o FILE`\] | the reparse-point inventory (decoded targets/tags/kind) — text by default (same as `reparse`), or `--json` — stdout or `-o` |
| `export resident-all [dir]` | every file whose bytes are inline, and every snapshot-shared file, to a folder, tree preserved (0-byte and extent-backed files are skipped), with an `export_index.csv` |
| `export snapshots [dir]` | every stream-snapshot version — same as `snapshots --extract` (aliases: `snapshot`, `prior-versions`), with an `export_index.csv`; `--json` is refused here (exit 1): `snapshots --json` lists the versions |
| `export deleted [dir] [--carve] [--rows\|--rows-only]` | recover deleted remnants — an index (`deleted_files.csv`/`.json`), the decoded inline files in `content/`, with `--carve` also `.carved` files (extent-backed), a `recovery_manifest.json` and a recovery log; the raw `.row` remnants only with `--rows` or `--rows-only` |
| `export recyclebin [dir]` | surviving `$R` payloads, named by their decoded original filename, and each payload's named streams beside it as `<name>__<stream>` (a `Zone.Identifier`, for example), with an `export_index.csv` naming each one's `$R` file (a stream as `$R...:<stream>`); a recycled folder is named on stderr with its file count, and its files are not written (exit 2; `export file <path>` writes each) |
| `export metadata <dir>` (or `-o <dir>`) | the hash-verified metadata bundle (`--what vbr,chkp,supb,mlog,usn,btree` · `--btree-mode packed\|per-object` · `--max-scan N`) |
| `<bundle-dir> <subcommand>` | read a bundle back — pass the directory where you would pass an image; see [metadata bundles](metadata_bundles.md) |
| `<bundle-dir> verify-bundle` | check a bundle is whole (seal, manifest, indexes, rehydration); exit 0 when it is whole and reading its bootstrap structures recorded no finding, 2 when it is not whole or a finding was recorded (the report names each). It does not make the redundancy checks of `summary` and `integrity` (a checkpoint copy not in use, a backup boot sector or a superblock copy that fails its checksum): run `summary` on the bundle for those |

**No export writes over an earlier one.** `export metadata` writes into a directory that is new or empty; a bulk export (`resident-all`, `snapshots`, `deleted`, `recyclebin`) writes into a directory that holds no earlier export (none of `holes.json`, `export_index.csv`, `deleted_files.csv`/`.json`, `recovery_manifest.json`, `recovery_log.txt`, `_extract_failures.json`, `manifest.json`, `sha256sums.txt`). Otherwise the export goes to `<dir>_2` (then `_3`, ...), and stderr names the directory used: `[forefst] ./rec holds an earlier export: writing to ./rec_2 instead (nothing is overwritten)`. Inside the directory a content file whose name is taken — by a file already there, or by another file of the same export (two sources of one name) — is written as `<name>.dup1`, `.dup2`, ..., and the rename is recorded.

**A file that cannot be written does not stop a bulk export.** A name longer than the host file system allows, a full disk, a directory it may not write in: the export records the file and the error in `_extract_failures.json`, goes on with the other files and says on stderr how many it could not write; when the directory cannot take that list either, stderr says so and names the files (the first 20, then the count). The run then exits 2, as it does when `export_index.csv`, `holes.json` or the recovery log cannot be written (stderr names the file; for `holes.json`, the streams it would have listed). `export deleted` stops with exit 1 when it cannot write `deleted_files.csv`, `deleted_files.json` or `recovery_manifest.json`.

**The export index.** `export resident-all`, `export snapshots` and `export recyclebin` write `export_index.csv`, one row per file written: `ObjectRef` (the source's, as `files` prints it), `FullPath` (the source on the volume: for a snapshot version `path [version name]`, for a recycled payload its `$R` file), `ContentFile` (the file written, relative to the directory), `SHA256` (of the bytes written) and `RenameReason` (empty, or why the name differs, e.g. `test/ok.txt already exists in the output directory`). It is written also when nothing was exported. `export deleted` keeps its own index (below) with the same two columns.

**`export deleted DIR` writes, by default:** an index, `deleted_files.csv` and `deleted_files.json`, with one row per entry (its `ContentFile` column names the file written for it, if any, `SHA256` its hash and `RenameReason` why its name differs; the index is written also when no entry has content, for example when `--no-system` leaves out every entry or only `--orphans` rows are found); for a file whose inline `$DATA` decodes, the full content as **`content/<name>`**; a **`recovery_manifest.json`** that stamps every entry (source, cluster, confidence, verdict, sizes), a `recovery_log.txt` and a `holes.json`. With **`--carve`**, an **extent-backed** entry also gets a **`content/<name>.carved`** file unless its carve is refused or fails (`NoCarveReason` in `recovery_manifest.json` says why) — reassembled from the recovered extent map (in the record, or in a backing record recovered from slack; validated byte-exact on a known live extent-backed file; **best-effort** for deleted files because the clusters may have been reallocated — flagged in the manifest). Files never clobber — a collision auto-renames to `.dup1`/`.dup2`, and `recovery_manifest.json` gives each entry's `SHA256` and `RenameReason` as the index does (also for the prior versions of live files, which have no index row). The raw **`.row`** remnants (the recovered directory-entry records, verbatim — chain-of-custody evidence) are written to `rows/` only with `--rows`, or with `--rows-only`, which writes them and the index without any content. `--content-only` is accepted and changes nothing: content without rows is the default.

> Not yet implemented: **whole-disk signature carving** (scan every cluster for file magics), which could recover
> some of the `metadata only` files (see the [`deleted` view](#deleted--the-deleted-file-view-list--recoverability)).

```sh
forefst.py disk.raw export file /dir/report.docx                # one file -> ./report.docx
forefst.py disk.raw export ads "notes.txt:hidden"                # one ADS -> ./notes.txt__hidden
forefst.py disk.raw export reparse --json -o reparse.json        # the reparse inventory as JSON (omit --json for text)
forefst.py disk.raw export snapshots                             # every snapshot -> auto-timestamped folder
forefst.py disk.raw export resident-all ./resident/              # write every file whose bytes are inline or snapshot-shared
forefst.py disk.raw export deleted ./rec/ --carve                # index + content/ (inline, .carved) + manifest
forefst.py disk.raw export recyclebin ./recovered/              # recover the recycle-bin payloads
forefst.py disk.raw export metadata -o ./bundle/                 # metadata bundle (also `export -o DIR`)
```

### `dataruns` — file data extents / data-runs

Maps extent-backed files to their on-disk extents. Default lists extent-backed files; `-v` adds every other
file and every decoded run (fvcn/lcn/length).

It reports **where the bytes are**, which is not the same question as where the *record* is — see
[Record placement and data residency](../concepts/placement_and_residency.md). Each line names both: the state, and
the record's placement (`record=embedded|split` on `EXTENT` and `NOEXTENT` lines, `record is ...` on the others).

| Line | Meaning |
|---|---|
| `EXTENT` | the bytes are in on-disk extents; the runs follow. A stream of 0 bytes needs no run: it is listed as `0 runs (empty stream)` and counted as decoded |
| `INLINE` | the bytes are stored in the record itself — no clusters |
| `SHARED` | the stream owns **no allocation**: its bytes are still the snapshot's. Not inline, and not this stream's clusters |
| `UNALLOC` | the stream owns no clusters and has no snapshot to share, so every byte reads as zero |
| `NOEXTENT` | extent-backed, but the map did not decode (may live in a remote object) |

An embedded record is frequently extent-backed — placement does not imply residency — so a file listed as
`record=embedded` can still show runs (inline data needs format 3.11 or later). `attrs=` names every attribute bit the file carries, with the
names `files` uses (`IntegrityStream`, `Encrypted`, `SparseFile`, ...). In `--json`, each entry of `Runs` gives
`FileVCN`, `VLCN`, `PLCN`, `Clusters`, `DiskOffset` and `IsHole`; a hole has no cluster and no offset, so its
`VLCN`, `PLCN` and `DiskOffset` are `null`.

| Option | Description |
|--------|-------------|
| `-v, --verbose` | include inline, shared, unallocated and no-extent files, and every decoded run |
| `--oid O` | start at object O (default 0x600) |
| `--depth N` | max recursion depth (default: full) |

```sh
forefst.py disk.raw dataruns                           # map extent-backed files
forefst.py disk.raw dataruns -v --depth 5              # full per-file run dump
forefst.py disk.raw dataruns --oid 0x705 -v            # scope to one subtree
```

---

## Value forms

Each kind of value has one form, the same in every command and every output format; `refsanalysis.py` writes
the same forms.

| Kind of value | Text | CSV and JSON |
|---|---|---|
| A date and time | `2026-05-23T08:48:26.4368773Z`: UTC, ISO 8601, all seven digits of the 100 ns fraction, so it sorts as text | the same string |
| A time field that holds no time (0, or all ones) | `(none)` | an empty cell; JSON `null` |
| A time past the year 9999 | the field's raw value: `0x` and 16 hex digits | the same |
| An identifier (OID, FileID), an LCN, VLCN, PLCN or VCN, a byte offset | lower-case hex without padding: `0x2874` | the same; in JSON a string (`"0x2874"`), never a number |
| A fixed-width word: the volume serial, the journal id, an LSN, a reparse tag, a boot-sector checksum, an index key's marker | hex at its full width: `0xf2c6a426c6a3e955`, `0xa000000c`, `0x2c14`; an LSN also in parts, `0x00000003000000a4 (generation 3, offset 0xa4)` | the hex |
| A directory's reference | `0x701:0x0` (its OID, FileID 0) | the same |
| A SecurityId | `0x103 (259)`: the hex, then the decimal | `0x103` |
| A flag word | `0x20 (Archive)`: the hex, then the names of its bits; `0x0 (none set)`; a bit without a name is written in hex among the names (`TxnStart\|0x2000`) | two fields: the names (`FileAttributes` = `Archive`; `0x0` when no bit is set), then the word in hex (`FileAttributesHex` = `0x20`); both empty (`null`) when the word was not read |
| A byte count | `237968 bytes (232.4 KiB)`: the exact count, then a reading aid in IEC units (KiB, MiB, GiB; never KB or MB) | the integer number of bytes |
| A cluster or container size | `4 KiB`, `64 MiB` | the bytes: `4096` |
| A USN, a count | decimal, without thousands separators | an integer |
| A yes/no value | `yes` / `no` (or a word that says more) | `true` / `false`, in CSV too |
| A GUID | lower case, canonical: `1e868de1-5300-40e0-844a-435a7fa17d79` | the same |
| A value the volume does not hold | `(none)`; when it could not be read, the reason | an empty cell; JSON `null` |
| A list of names (a file's stream names, hard-link names, snapshot names) | — | JSON a list; CSV one cell, the names joined with `;`, a `;` inside a name written `\;` and a `\` written `\\` |
| A format version | `3.14` after a label (`ReFS version: 3.14`), `ReFS 3.14` on its own; never `v3.14` | `"3.14"` |
| A checksum algorithm | `CRC64`, `SHA-256`, `XXH64`, `CRC32-C` (integrity streams), `none`, `unknown (0x…)` | the same words |
| A path | `files`' FullPath form: no leading `/`, the root `.` (`test2/report.ini`) | the same |

The body file (`--body`) keeps its own format's forms: Unix seconds for the times (see
[Body File Format](#body-file-format)).

The pairs of fields of a flag word or a tag, in the machine outputs: `FileAttributes` / `FileAttributesHex`
(`files`, `details`, `usn`, `reparse`); `InternalFlags` / `InternalFlagsHex` (`files`, `details`); `ReparseTag` /
`ReparseTagHex` (`files`, `details`, `reparse`); `Reason` / `ReasonHex` and `SourceInfo` / `SourceInfoHex` (`usn`);
`Control` / `ControlHex`, `Flags` / `FlagsHex` and `Mask` / `MaskHex` (`security`); `Flags` / `FlagsHex`
(`reparse`, `mlog` records); `CheckpointFlags` / `CheckpointFlagsHex` (`summary`). `mlog`'s transactions carry
their opcodes the same way, as two lists: `Opcodes` (the mnemonics, `UPDATE_ROW`) and `OpcodesHex` (`0x3`).

**A directory without a path.** `files`, `search` and `timestomp` list what the directory walk from the root
reaches, so each of their rows has a path. `usn`, `mlog`, `timeline` and `deleted` also name directories
the walk did not reach (a journal record's parent, a table a log record changes); such a directory is written as
one of four labels:

| Label | Meaning |
|---|---|
| `<oid 0x…>` | the directory is not in the Object Table, which was read in full: it is gone |
| `<unlinked 0x…>` | the directory is in the Object Table, but the walk from the root, which read the whole tree, reached no name for it: unlinked from the namespace and not yet reclaimed |
| `<undetermined 0x…>` | the Object Table, or the directory tree the walk reads, was read only in part (a page or a table could not be read, or the walk reached its depth limit), so whether the directory exists, or where it is, is not determined |
| `<system 0x…>` | a system object (an OID below 0x700) without a known name |

**The change journal's state** is one of three words wherever a command reports it (`summary`, `usn`,
`timeline`, `timestomp`): `Active` (the volume holds a change journal), `Inactive` (the system metadata table,
read in full, holds none) or `unknown: <the reason>` (the journal, or the table that holds it, could not be read,
so neither can be said). A command may add what the state means for its own output: `timeline` prints
`USN Journal: Inactive — timeline is $SI + MLog only.`

---

## CSV Output Fields

The `files` CSV has **42 columns**, one row per name (a hard-linked file has one row for each of its names), in this
order (matching `CSV_COLUMNS` in `forefst.py`):

> Every header is a plain identifier — no slash, space or bracket — so a consumer can key on it
> (`df["HomeOID"]`, a Timeline Explorer column filter). A change to a name, the count or the order is
> listed as **breaking** in the [changelog](../changelog.md), with what a consumer must do. A `--json`
> record is the same row: these 42 names as its keys, in this order.

| # | Column | Description |
|---|--------|-------------|
| 1 | ObjectRef | the object's identity — a **directory** shows `OID:0x0` — its own OID in the home slot with FileID 0, which is exactly how the change journal references a directory (verified on the directories measured, no counterexample) — and a **file** its FileRef `HomeOID:FileID` (the USN `FileReferenceNumber`). Exactly one of the two applies, so they share one column |
| 2 | FullPath | full path from root (ParentPath + FileName) |
| 3 | FileName | file or directory name |
| 4 | Extension | file extension, **in the case it has on disk** (`.SYS` stays `.SYS`) — a forensic listing reports the name as stored, not a normalised form. Blank when the suffix after the last dot is longer than 10 characters, which is treated as not an extension |
| 5 | FileSize | logical file size in bytes — the `$DATA` stream's own size where the directory's cached copy of it disagrees |
| 6 | Created | $SI creation timestamp |
| 7 | Modified | $SI modification timestamp |
| 8 | Changed | $SI metadata-change timestamp (the MACB "C") |
| 9 | Accessed | $SI access timestamp; updated only while last-access updating is on (a Windows setting, not stored on the volume) |
| 10 | ParentPath | path of the directory this **name currently lives in** |
| 11 | ParentOID | OID of that current parent (differs from `HomeOID` after a move, or for a hard-link name in another directory) |
| 12 | CreationDir | resolved path of `HomeOID` (the directory the file was **created** in); the volume root reads `.` |
| 13 | HomeOID | OID of the directory the file was **created in** — frozen at creation, unchanged by move or rename; for an embedded record that carries a reference (`$SI+0x68`, a file moved on a volume without hard-link support), that reference's directory. Its resolved path is column 12, `CreationDir`. Differs from `ParentOID` (where the name is **now**) for a file that sits outside its creation directory: after a move, or for a hard-link name in another directory (`IsMoved` tells the two apart where it can); a file moved back home shows them equal |
| 14 | FileID | the per-directory child ordinal (low 64 bits) — monotonic, never re-used after deletion |
| 15 | USN | Update Sequence Number (LastUsn) |
| 16 | FileAttributes | the on-disk attribute word decoded with **ReFS** names, which is not the same as what Windows reports. Two differences are systematic: bit `0x10000000` prints as `Directory_Internal` where Windows reports `Directory` (0x10), and bit `0x40000` prints as `EA` where Windows reports nothing. Measured against the operator's PowerShell inventory on a lab volume: **about one row in ten differs, on exactly those two bits** (directories and files), and one further row differs for another reason. The tool is reading the bytes correctly; it is naming them differently. For a split record (`RecordPlacement = split`) the word is the file's own record's, not the copy cached in its name row; the change journal carries the same word as the file's own record |
| 17 | FileAttributesHex | the same attribute word in hex (`0x…`), every bit whether named or not; blank when the word was not read |
| 18 | SecurityId | ReFS security-descriptor ID |
| 19 | OwnerSid | owner: friendly name + SID (e.g. `BUILTIN\Administrators (S-1-5-32-544)`) |
| 20 | GroupSid | group: friendly name + SID (from the security descriptor) |
| 21 | DACLSummary | the count of the DACL's ACEs, then its first six in `security`'s ACE text, `; `-separated (`3 ACE(s): ALLOWED BUILTIN\Administrators (S-1-5-32-544): FULL_CONTROL; ALLOWED SYSTEM (S-1-5-18): FULL_CONTROL; ALLOWED DomainUser (RID=1001) (S-1-5-21-3829591975-2821165226-2477612932-1001): FULL_CONTROL`), `[inherited]` after an inherited ACE and `; …` when there are more than six; the full DACL is in `security` |
| 22 | HasADS | alternate data stream present |
| 23 | ADSNames | the names of the file's alternate data streams, `;`-joined (a list: see [Value forms](#value-forms)) |
| 24 | RecordPlacement | `embedded` when the file's record sits inside its name row, `split` when it lives in its own type-0x40 backing record. **On a volume with hard-link support a move or a hard link forces the split** — and moves no data; without it a move keeps the record embedded (its `ObjectRef` and `HomeOID` are then the reference it carries, and `IsMoved` is `moved (the record's reference)`). Blank for directories |
| 25 | DataResidency | where the current `$DATA` bytes actually are: `inline` (in the record), `extents` (on disk), `snapshot-shared` (the live stream owns no allocation; its bytes are the latest snapshot's, and `extract` still recovers them) or `unallocated` (owns no clusters and has no snapshot, so every byte reads as zero). A **0-byte** stream is classified by descriptor form like any other, so an extent-form one reads `extents`, not `unallocated`. Blank for directories |
| 26 | IsDirectory | `true` if the entry is a directory |
| 27 | IsEncrypted | EFS encryption flag |
| 28 | IsCompressed | compression flag |
| 29 | HasIntegrity | integrity-stream flag |
| 30 | HasEA | Extended Attributes present (for a split record, read from its own record) |
| 31 | HardLinkCount | number of names resolving to this file — `1` for an ordinary file, higher when hard-linked. Blank for directories (not applicable) |
| 32 | HardLinkNames | `;`-joined names sharing the content |
| 33 | SnapshotCount | number of stream snapshots |
| 34 | SnapshotNames | `;`-joined snapshot version labels (e.g. `v3;v2;v1`) |
| 35 | ReparseTag | the reparse tag's name (`IO_REPARSE_TAG_*`; its hex when the tag has none); blank when the object carries no tag |
| 36 | ReparseTagHex | the reparse tag in hex (`0x%08x`); blank when the object carries no tag |
| 37 | ReparseTarget | symlink/junction target |
| 38 | IsSparse | `FILE_ATTRIBUTE_SPARSE_FILE` (0x200) set. **`AllocatedSize < FileSize` does not corroborate it** — on the corpus the inequality fails on **most sparse files** (more than half): some have `AllocatedSize == FileSize`, others `AllocatedSize > FileSize`. Read the attribute bit; do not infer sparseness from the sizes. Distinct from `DataResidency = unallocated`, which is derived from the `$DATA` descriptor (extent form owning no allocation and no snapshot) rather than from the attribute bit. The two are independent readings: on the corpus the few `unallocated` rows are all marked sparse, while most sparse files are not `unallocated` |
| 39 | AllocatedSize | on-disk allocated size. It can be below `FileSize` only on a sparse file (which counts only allocated clusters); most sparse files do not show this. Blank when unresolved, when the cached copy is stale and the stream records no single allocation, and **blank for directories** — a directory's allocation is not a property this listing resolves (Windows reports 0) |
| 40 | InternalFlags | `$SI` internal flags: the names of the named bits (`DeleteDisposition`, `CaseSensitive`, `DataInRecord` -- the file's data held in its record --, `RedirectionTrust`), any other bit as hex (`DeleteDisposition\|0x4`), `0x0` when none is set; blank when the word was not read. `DataInRecord` and `DataResidency` `inline` go together on every file of the corpus |
| 41 | InternalFlagsHex | the `$SI+0x24` word in hex, every bit; blank when the word was not read |
| 42 | IsMoved | whether this name sits outside the directory the file was created in, by a stated rule (its values: below the table) |

**`IsMoved` values.** It says where the name sits now, not whether it ever moved: a file or directory moved away and
back reads `false` or `in its creation directory (change journal)`, and `usn` shows the moves.

- `false`: in its creation directory (HomeOID = ParentOID).
- Where the volume's change journal holds the record that put the name where it is, the journal decides:
  `moved (change journal)`, `a hard link made here (change journal)`, and for a directory, whose row records no
  creation directory, `in its creation directory (change journal)` or `moved (change journal)` from its creation
  record.
- A file whose embedded record carries the reference of another directory (`$SI+0x68`: a move on a volume without
  hard-link support) reads `moved (the record's reference)`.
- Elsewhere the metadata's value: `moved, or hard-linked and the original name removed` (the file's one name lies
  outside its creation directory, and the metadata does not tell a move from a hard link whose first name was
  removed) or `undetermined` (a file with two or more names, or a row without its creation directory).

The journal is used only when its history is whole: no gap in its written span, not created again since, no file
pointing past its last record; a line on stderr says how IsMoved was read (with `-q`, only when the journal could not
be used). A moved file may still hold its bytes inline (`DataResidency` `inline`): the move relocates the *record*,
not the *bytes*.

> The files whose data is held inline in the record are those with `DataResidency` `inline` (`--filter inline`);
> the spelling `--filter resident` is refused (exit 1) with a message naming `inline`.

> `FileRef` = `HomeOID:FileID` is the object's stable identity — it is the USN `FileReferenceNumber`, so the
> `files` and `usn` outputs join directly on it. `HomeOID` (the creation directory) is fixed at create time,
> while `ParentOID` follows the name to wherever it lives now; they differ for hard-links and moved files
> (`IsMoved`). `CreationDir` resolves HomeOID to a path. Deleted/recovered entries are **not** in `files` — the
> `deleted` command reports them (with `--csv`/`--json`/`--jsonl`). `FullPath` is a standard column; there is no
> `--full-path-column` option (the command refuses it as an unknown flag, exit 1).

### `files --filter` categories

`files --filter <category>` keeps only the matching rows (output format unchanged). The 12 categories are
field-based and EA-safe — `wsl` is detected via the reparse tag, not the EA-derived mode:

`reparse` · `encrypted` · `compressed` · `integrity` · `ea` · `ads` · `wsl` · `sparse` · `snapshot` · `directory` · `inline` · `hardlink`

## Body File Format

Sleuthkit/mactime compatible:

```text
MD5|name|inode|mode_as_string|UID|GID|size|atime|mtime|ctime|crtime
```

`inode` is the object's ObjectRef, as `files` prints it in its first column: `0x<OID>:0x0` for a directory or a system object, `<HomeOID>:<FileID>` for a file (so a file's hard-link names share it); `0` only for a row with neither. `mode` is The Sleuth Kit's form: `r/rrwxrwxrwx` for a file, `d/drwxrwxrwx` for a directory, `l/lrwxrwxrwx` for a reparse point, the write bits cleared (`r/r-xr-xr-x`) when the read-only attribute is set. `MD5`, `UID` and `GID` are `0`; the times are Unix epoch seconds (`0` for a time that is not set).

## Deleted File Detection

Deleted files are listed by the dedicated [`deleted`](#deleted--the-deleted-file-view-list--recoverability) command
(the `files` and `search` listings cover the **live** tree only), in its two modes: the recovery pass (default:
Trash table + checkpoint diff + the slack scan of the live tree's pages) and `--full` (also every cluster of the
volume read for old pages). Each entry is classified by the **identity the row records** (`ObjectRef`): `DELETED`
when that identity is live nowhere, `RENAMED` or `SAME FILE, OTHER CREATION TIME` when the same file is live,
`STILL PRESENT` when a live file has its name and creation time and no copy records another object's identity, and
`DELETED, OR RENAMED` when the row records no identity the tool can check. A name and a creation time alone do not
decide it: files created together share a creation time to the second. Identical rows found in several pages are one
entry, with every copy recorded in the log. Each entry carries a **recoverability verdict**. A plain `deleted` writes
nothing; `--log PATH` writes its recovery log. `export deleted DIR` writes an index of the entries, the content held
inline under `content/` (`--carve` also reconstructs extent-backed files best-effort; `--rows` adds the raw remnants)
and the recovery log (`DIR/recovery_log.txt` by default). `deleted --orphans` adds a low-confidence tier for
Object-Table objects unlinked from the tree.

## CoW version comparison

`files --cow-before <earlier_image>` outputs, instead of the listing, the comparison of two images of the same volume
(the superblocks' volume GUIDs are compared first: images of two different volumes are refused, exit 1, before either
is walked): one row per object, by `ObjectRef`, that was **created**, **removed** or
**changed** between them, with the fields that differ before and after (CSV / JSON / JSONL: `Change`, `ObjectRef`,
`IsDirectory`, `FullPath`, `ChangedFields`, then `Before<field>` / `After<field>` for `FullPath`, `FileSize`,
`AllocatedSize`, `Created`, `Modified`, `Changed`, `Accessed`, `FileAttributes`, `SecurityId`, `USN`,
`DataResidency`, `RecordPlacement`, `HardLinkCount`, `ADSNames`, `SnapshotCount`, `ReparseTag`, `ReparseTarget`,
`InternalFlags`). An object is said created or removed only when both walks are complete: a missing object of an
incomplete walk may sit on a page that was not read. The earlier image is read as a volume of its own; a condition
found reading it (a backup superblock, a stale checkpoint) makes the run exit 2 and is not reported as one of the image
named first. A file's earlier *content* is not recovered by this comparison; stream snapshots of a live file are under
`snapshots`.

The comparison compares the two images' checkpoints. Two images whose checkpoints carry the same virtual clock hold one
metadata state, so a change made after that checkpoint, before the next one committed it, is not in the comparison
(its records may be in the log: `mlog`). Compare `CheckpointVirtualClock` (`fastsummary --json`) first.

---

## Using forefst.py as a library

`forefst.py` is Python 3.7+ standard library only (no pip packages) and exports the parsing primitives, imported by `refsanalysis.py` and available to any script:

| Function | Signature | Purpose |
|----------|-----------|---------|
| `bootstrap()` | `(image_path, partition_start=None)` | `(f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns)` |
| `walk_bplus()` | `(f, ps, cs, tr, vlcns, max_depth=5, oid=None, root_out=None)` | list of `(key_data, value_data)` tuples; the table's root page is checked against the digest the Object Table recorded for it |
| `build_object_map()` | `(f, ps, cs, tr, ot_vlcns, register=True)` | `{oid: [vlcn_list]}` |
| `Translator` | `.tr(vlcn) → plcn` | virtual-to-physical address translation |
| `le16/le32/le64()` | `(data, offset)` | little-endian integer reads |
| `find_refs_partition()` | `(path)` | `(partition start, description)` from the GPT |
| `filetime_to_iso()` | `(ft)` | Windows FILETIME → ISO 8601 |
| `parse_resident_btree_rows()` | `(vd, ctx=None, salvage=False)` | embedded sub-records from an embedded (kf 0x01) value; pass `ctx=(f, ps, cs, tr)`, or the rows held in a child node are missed |
| `get_resident_file_size()` | `(vd, ctx=None, v34_key=True)` | the file size an embedded record carries |
| `NON_RESIDENT_MAX_VALUE` | `84` | placement threshold: `value_length > 84` ⇒ the record is embedded in the name row |

### The bootstrap() call

`bootstrap()` is the single entry point for volume initialization. In order:

1. locate the ReFS partition (the GPT's, or the one `partition_start` names);
2. parse the VBR (cluster size, version, container size) and the SUPB (checkpoint LCNs);
3. read the checkpoint copies in the superblock's order and use the one refs.sys would use: the valid copy with the
   strictly highest clock at +0x60, the first-listed on a tie (valid = its self-checksum does not fail, its root list
   parses, and no refs.sys build's record tests reject it — see [Checkpoint](../structures/chkp.md)):
   - a newer copy that cannot be used, and a copy in use that a refs.sys build would reject, are stated and make the
     command exit 2;
   - when no copy is valid the newest is read and said to be unverified (exit 2);
4. read the 13 root-table pointers, build the Container Table, initialize the VLCN→PLCN translator, and resolve all
   OIDs.

Afterwards the checkpoint-root tables are reachable through `roots[i]` and every OID-addressed table through
`obj_map[oid]`, both with `walk_bplus()`.

```python
#!/usr/bin/env python3
from forefst import bootstrap, walk_bplus, le16, le32, le64, NON_RESIDENT_MAX_VALUE

f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = bootstrap("disk.raw")
try:
    for key_data, value_data in walk_bplus(f, ps, cs, tr, obj_map[0x600]):
        if le16(key_data, 0) == 0x30:                       # filename entry
            name = key_data[4:].decode("utf-16-le").rstrip("\x00")
            # A short value (<= 84 bytes) is a split file's name row: value+0x38 is the size cached in the
            # name, which can be stale (the object's own size is in its type-0x40 backing, +0x58; `files`
            # reads it). An embedded record's size: get_resident_file_size(value_data, (f, ps, cs, tr)).
            if len(value_data) <= NON_RESIDENT_MAX_VALUE and not le32(value_data, 0x40) & 0x10000000:
                print(f"{name}: {le64(value_data, 0x38)} bytes (cached in the name row)")
finally:
    f.close()
```

## Dependencies

Python 3.7+ standard library only. No pip packages.

## Exit codes

`forefst.py` returns a process exit code so a script can branch on the result:

| Code | Meaning |
|------|---------|
| `0` | Success — the command ran and flagged nothing. |
| `1` | Error — the input could not be read or parsed, a **usage error**, or an output that could not be written. Uniform across every command. |
| `2` | Either **a finding of interest** or **work the command could not complete**. |

**Exit 1** covers:

- an input that could not be read or parsed: not a ReFS/GPT image, file missing, corrupt bootstrap (no boot-sector
  copy passes its tests and the primary carries no ReFS signature — a signed primary that fails a test is read,
  exit 2);
- a **usage error**: an unrecognised flag, a missing option value, a stray extra argument, or a bad subcommand;
- an output that could not be written: `cannot write the output (FILE): ...` when the device is full, a file-size or
  quota limit is reached or the file system is read-only; `FILE: <reason> (not the image)` for another error on an
  output file (a directory you may not write in, for example).

**Exit 2, a finding:**

- `integrity` found a checksum or structural failure; `security --audit` found descriptor tampering;
- a redundancy finding: missing backup boot sector, fewer than two intact superblock copies, two superblock copies
  that both verify and differ, a checkpoint copy not in use that fails;
- a volume read from a backup boot sector or from a primary that fails a test, or from a backup superblock;
- a checkpoint condition that changes what every command reads: the copy in use is not the newest, a refs.sys build
  would reject the copy in use, no copy is valid, or a copy's page-header clock +0x10 differs from its clock +0x60;
- the root page of one of the checkpoint's tables that does not match the digest the copy in use records for it or
  cannot be verified (the table is read as it is; the Object Table's and the Schema Table's second copies, which are
  not read, are redundancy findings);
- a boot-sector version that is implausible or not corroborated (`summary`, `fastsummary`, `integrity`);
- a structure the command needs missing from the volume (the Security Descriptor Stream, the root directory, the
  Upcase Table, the Schema or Parent-Child Table);
- an integrity-stream CRC-32C mismatch;
- journal records missing (files point past the last surviving record) or a journal re-created;
- a volume that was not cleanly dismounted.

**Exit 2, work the command could not complete:**

- any recorded skip, a page that could not be read as a B+ node, `integrity --max-pages` reaching its cap;
- `extract`/`export` content that came from image holes (written, with the ranges named; refused with
  `--refuse-holes`), hole coverage that could not be determined;
- a file the command could not write and went on without (a bulk export's content file, `export_index.csv`,
  `holes.json`, the recovery log, `extract`'s `.holes.json`).

`rc == 2` means **the command ran and either found something or could not certify the volume clean.** A
mistyped flag can never produce it, on any command, so `if rc == 2` is a safe branch in a script; it does not
by itself say which of the two happened: branch on the JSON (`integrity --json` carries `Clean` and
`CoverageComplete`) when you need to separate them. Every command prints the offending flag to stderr when
it rejects one. What changed in each release: [Migrating between releases](migration.md#exit-codes-in-1140).

A **redundancy** finding — a backup copy that fails, copies that differ, the root page of the Object Table's or the
Schema Table's second copy that fails its digest — is reported by `summary`, `fastsummary` and `integrity`, which
exit 2 for it. The other commands read the copy in use and keep their exit code (on a tie between two checkpoint
copies of which one is damaged, `files` exits 0).

`deleted` also reads the other checkpoint copy, for its checkpoint comparison: what `summary` says of that copy,
`deleted` says too, in the same words, and exits 2.

A condition that changes what every command reads (the volume read from a backup boot sector, a backup superblock or
a stale checkpoint, or a root page of one of the checkpoint's tables that fails its digest, other than a second copy
that is not read, for example) makes every command exit 2.

**A file that is not in the image exits `1`, not `2`** — that is an input error, not a finding, in both default
and `--refuse-holes` modes — unless the run recorded metadata it could not read: then "not found" is not evidence
that the file is absent, the command says so, and it exits `2`.

A usage error exits `1`, never `2`, so `2` always means the command ran.

**An output that stops part-way.** Every output file the tool writes (a `--csv`, `--json`, `--jsonl` or `--body`
FILE, `mlog --csv FILE`, `export reparse -o FILE`, the index and record files of an export, `extract -o FILE` and its
sidecar) is written as `<FILE>.partial` (as `.<16 hex digits>.partial` beside it when `<FILE>.partial` would be
longer than the file system allows) and renamed to its name only once it is complete; a write that fails removes
the `.partial` file and names FILE in its error line, so a file under the final name is never a partial one. A FILE
that is not a regular file -- a device such as `/dev/null`, a FIFO, a process substitution -- is written directly:
there is no file under its name to protect. On stdout, an output that stops part-way is followed by a line on stderr, `[forefst] the output on stdout is
INCOMPLETE: it stopped part-way (<error type>: <message>)`, unless the reader closed the pipe (`| head`): the run
then stops quietly and exits 2 if it had already recorded a finding or a skip, else 0. A closed pipe that carries
only progress lines, statements and warnings -- stderr, or stdout when the output goes to a FILE or a directory
(`--csv FILE 2>&1 | head`) -- does not stop the run: what would have gone into it is dropped, and the run writes
its output and exits with its own code.

## Cross-References

- [refsanalysis.py](refsanalysis.md) — the structure/lab analysis tool that imports this library
- [Internals](internals.md) — how the tools read a volume, function by function, and the driver behaviour each step follows
- [Bootstrap Chain](../concepts/bootstrap_chain.md) — the initialization sequence in detail
- [Directory Entries](../structures/directory_entries.md) — key type 0x30 format
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — timestamp and attribute layout

## Evidence

The counts behind the text:

- `mlog --parse`: the rows whose file records give no pair, on the corpus: 406 rows of 3.4 volumes and 119 of 3.14
  volumes; checked against the two operation logs, the moves and renames both read: 698 (the public sample) and 242
  (the lab volume);
- `timestomp` base rates (2026-09-06, 96 images, 521,060 files): `PRE_FORMAT` 22.67 %, `CHANGE_LATE` 22.32 %,
  `CREATE_GT_MODIFY` 1.04 %, `HARDLINK_MACB_MISMATCH` 0.04 %, `ROUND_TIMESTAMPS` 0.04 %; `CHANGE_LATE` with
  `PRE_FORMAT` 115,936 times, without it on 384 files (0.33 % of `CHANGE_LATE`), all on the real Windows
  installation (120,617 files), where the copy signature alone covers 95.4 % of the files and 95.7 % carry at least
  one signal; its reviewable set: 324 HIGH and 336 MEDIUM (measured with 1.13.0, 2026-09-21); the back-dating lab
  volume's generator log records 74 timestamp-setting actions per replay;
- `integrity --checksums`: the real Windows installation has about 27,000 Object-Table rows;
- the corpus's storage: 55 TB apparent against 58 GB allocated (2026-09-06);
- `deleted`'s recovery pass: 197.5 s and 401.0 s on the two Windows Server Insider system volumes of the test corpus;
- the holes note: on the lab volume, 996 of 1,020 files have holes inside their data range;
- `ObjectRef` of a directory (`OID:0x0`) against the change journal's reference: 589 directories, no counterexample;
- `FileAttributes` against the operator's PowerShell inventory on `lab314_main` (4,684 common paths): 490 rows differ
  on exactly the two bits (26 directories, 464 files), 1 further row for another reason;
- `IsSparse`: over 936,277 rows on 117 images, 137 are sparse; `AllocatedSize < FileSize` holds on 58 of them, 22
  have `AllocatedSize == FileSize` and 57 have `AllocatedSize > FileSize`, so it fails on 79 of 137 (57.7 %).
