# Migrating between releases

What a script that reads the output of `forefst.py` or `refsanalysis.py` must change from one release to the next:
the exit codes, the machine-output names, and the forms of their values.

The [changelog](../changelog.md) says why each change was made; this page lists what changed, release by release,
the breaking changes first.

## 1.14.0 → 1.14.1

What a script that reads the output of 1.14.0 may notice. No column, key or default changed.

| Command | What changed | What to do |
|---|---|---|
| `mlog --parse`, `mlog --csv`, `timeline` | An MLog row whose only time came from a record that rewrites part of a row (a file's inline bytes, its sizes), or from an inserted row that holds no record, has no time now, or the time of another of its records (232 of 886,813 rows over the test corpus, on five volumes) | Nothing, unless a script keyed on such a row's time |
| `details` | A target that reads as an id (`0x705`, `0x703:0x2e`) is an id; any other target is a path from the root, with or without its leading slash (1.14.0 exited 1 on a FileRef and on a path without the slash). Two error texts changed: `give --id OR --path, not both`, `no object for id <id>` | A name that reads as an id is reached with `--path /0x705` |
| `usn` | New `--id ID`: only that object's records (the list, the statistics, the exports); stderr says how many records carry it. `--id` with `--info` exits 1 | -- |
| `mlog` | New `--id ID` (with `--parse`, `--csv` or `--json`): only the payloads whose records name the object; the CSV gains a `MatchedBy` column and the JSON a `MatchedBy` key when `--id` is given; stderr counts the rows kept | -- |
| `timeline` | New `--id ID`, the same filter as `--fileref` (still accepted); with it, the MLog rows that name the object are kept (1.14.0 left them all out), their event text ending in `[by its table]`, `[by its file id]` or `[by one of its names]` | A script that filtered MLog rows out of `--fileref` output gets them now |
| `export recyclebin` | Writes each payload's named streams as `<name>__<stream>`, with their rows in `export_index.csv`; names each recycled folder on stderr, and exits 2 when one holds files; its last line counts the streams | A script that counted the directory's files counts the stream files too |
| `--list`, help | The one-line summaries of `details`, `usn` and `timeline`, and their help, name the new forms | -- |
| refsanalysis | Exits 1 with forefst 1.14.1: `refsanalysis 1.14.0 runs only with forefst 1.14.0; this forefst is 1.14.1 (...)` | Use both tools of the 1.14.0 release (tag `v1.14`) for refsanalysis |

## 1.13.1 → 1.14.0

Every machine output of both tools changes in 1.14.0. In short, a script must:

- read the new name of every JSON key and CSV header (the [rule](#the-key-names), and the [tables, command by
  command](#the-keys-command-by-command));
- expect exit 2 or exit 1 where 1.13.1 exited 0 ([exit codes](#exit-codes-in-1140));
- read each kind of value in its one form: times, hexadecimal identifiers, flag words, `true` / `false`
  ([values](#values));
- read `files --json` as the `files` CSV row: 42 columns, no `IsResident`;
- export again any metadata bundle written by 1.12.1 to 1.13.1.

### The key names

Every JSON key and every CSV header of both tools is written in one vocabulary, from one table in `forefst.py`
(`out_key`):

- a fact that `files` has takes its `files` column name in every command: `ObjectRef`, `FullPath`, `FileName`,
  `HomeOID`, `FileID`, `Created`, `Modified`, `Changed`, `Accessed`, `IsDirectory`, `SecurityId`, `OwnerSid`,
  `DataResidency`, `RecordPlacement` …;
- any other name is its words in PascalCase:
  - acronyms in capitals: `OID`, `ID`, `LCN`, `VLCN`, `PLCN`, `VCN`, `USN`, `LSN`, `GUID`, `UUID`, `SID`, `SHA256`,
    `CRC`, `ADS`, `EA`, `DACL`, `SACL` …;
  - the names `MLog` and `ReFS` in their own spelling;
  - a few abbreviations written out: `pct` → `Percent`, `len` → `Length`, `vc` → `VirtualClock`, `cksum` →
    `Checksum`, `idx` → `Index`, `attrs` → `Attributes`, `off` → `Offset` …;
- a map whose keys are values (a residency word, a root-table name, an attribute type) keeps its keys unchanged.

A few commands name a field otherwise where the rule would mislead (`summary`'s `HardLinkedFiles`, `timestomp`'s
`Confidence`). The [tables below](#the-keys-command-by-command) give every name as the tools write it.

### Exit codes in 1.14.0

Codes not listed keep their meaning: 0 when the command ran and flagged nothing, 1 for a usage error or an input that
cannot be read, 2 for a finding or for work the command could not complete ([forefst.md — Exit
codes](forefst.md#exit-codes)).

**Exit 2 where 1.13.1 exited 0 or 1: the superblock, the checkpoint and the Container Table**

| Tool and command | Condition | 1.13.1 | 1.14.0 |
|---|---|---|---|
| forefst `summary`, `integrity` | a superblock copy fails its self-checksum | 0 | 2 |
| forefst, every command | the primary superblock carries its signature but fails its self-checksum or another test refs.sys makes, and a backup passes them (the volume is read from the backup) | 0 | 2 |
| forefst, every command | no superblock copy passes those tests, and the primary carries its signature (the volume is read from the primary, and this is said) | 0 | 2 |
| forefst, every command | no superblock copy passes those tests, and only a backup carries the signature (the volume is read from the first such backup, and this is said) | 1 | 2 |
| forefst, every command | the superblock or checkpoint copy the volume is read from cannot be verified (an unknown checksum type) | 0 | 2 |
| forefst `summary`, `fastsummary`, `integrity` | the two checkpoint copies carry the same clock and one fails its self-checksum (other commands read the valid copy and keep their code) | 0 (2 in every command when the failing copy had the lower LCN) | 2 |
| forefst, every command | the newest checkpoint copy passes its self-checksum but refs.sys rejects it, so an older copy is read | 0 | 2 |
| forefst, every command | a root 0xC, 7 or 8 of the checkpoint copy in use does not verify against its digest, or cannot be checked | 0 | 2 |
| forefst, every command | the checkpoint copy in use records a version above the boot sector's | 0 | 2 |
| forefst `summary`, `fastsummary`, `integrity`; refsanalysis `summary` | the checkpoint copy not in use: refs.sys rejects it, or a root 0xC, 7 or 8 does not verify against its digest or cannot be checked | 0 | 2 |
| forefst, every command | the root page of a table the checkpoint copy in use refers to (the Object Table, the Container Table, the allocators, the Parent-Child Table …) does not match the digest that copy records for it, or cannot be verified | 0 | 2 |
| forefst `summary`, `fastsummary`, `integrity` | the second copy of the Object Table or of the Schema Table fails its check | 0 | 2 |
| forefst `summary`, `fastsummary`, `integrity`; refsanalysis `summary`, `boot --verify` | the boot sector's container size is 0 (what `refsutil fixboot` writes) | 0 | 2 |
| forefst `integrity`; refsanalysis `summary`, `boot --verify` | the boot sector's version is implausible or contradicted by the checkpoint and `$VOLUME_INFORMATION` (`summary` and `fastsummary` exit 2 for it since 1.13.0) | 0 | 2 |
| forefst, every command | the Container Table maps two containers onto overlapping clusters | 0 | 2 |
| forefst `summary`, `fastsummary`, `integrity` | the Container Table's two copies (roots 7 and 8) differ in more than the rows' flags word | 0 | 2 |

**Exit 2 where 1.13.1 exited 0 or 1: metadata pages and the directory tree**

| Tool and command | Condition | 1.13.1 | 1.14.0 |
|---|---|---|---|
| forefst `integrity --fullchecksums`; any command run with `--verify-pages` | a child page below a file's extent index or below an embedded attribute index fails its checksum | 0 | 2 |
| forefst `files`, `details`, `export metadata`, `usn --info`, and every command that reads a system table | the table's root page does not match the digest the Object Table records for it (the security table, OID 0x530; the system metadata table that holds the journal's entry, OID 0x520) | 0 | 2 |
| forefst, every directory walk | a directory is listed but cannot be entered (no Object Table entry, or no OID) | 0 | 2 |
| forefst `files`, `search`, `specials`, `ads`, `timestomp`, `snapshots`, `recyclebin`; refsanalysis `files`, `attributes` | the root directory (OID 0x600) is not in an Object Table read in full | 0 (an empty listing) | 2 |
| forefst `security`, `mlog`, `reparse` | a table the command needs is not in an Object Table read in full (the security table, the Logfile Information Table, the root directory) | 1 | 2 |
| forefst `extract`, `dataruns` | the object asked for is not among the rows of an Object Table read in part (over one read in full, "not found" keeps exit 1) | 1 | 2 |
| forefst `dataruns`, `extract`, and every command that reads a named stream's or the change journal's extent rows | a sub-record or extent row declares no legal size (the walk stops there and records it) | 0 | 2 |

**Exit 2 where 1.13.1 exited 0: the change journal and the MLog**

| Tool and command | Condition | 1.13.1 | 1.14.0 |
|---|---|---|---|
| forefst `mlog`, `timeline`, `summary --mlog` (its MLog section) | records are missing below the log end the control area recorded | 0 | 2 |
| forefst `usn`, `timeline`, `timestomp` | the change journal was re-created, and no record is missing | 0 | 2 |
| forefst `usn` | `$J` holds non-zero bytes and no record | 0 | 2 |

**Exit 2 where 1.13.1 exited 0 or 1: content and exports**

| Tool and command | Condition | 1.13.1 | 1.14.0 |
|---|---|---|---|
| forefst `deleted` (a slack or orphan-page scan), `export deleted` | a read error inside the scanned range | 0 | 2 |
| forefst `extract`, `export resident-all`, `export recyclebin`, `export snapshots` (`snapshots --extract`) | whether the bytes come from image holes cannot be checked on this host | 0 | 2 |
| forefst `extract` | the file is not found after a recorded skip, or the file of a readable volume cannot be reassembled, or a split name's backing row is not found | 1 | 2 |
| forefst `extract` | a cluster of the file cannot be read (an extent address beyond any file offset) | 1 | 2 |
| forefst `extract` | a hard-linked or moved file's integrity stream fails its CRC-32C (1.13.1 did not check it) | 0 | 2 |
| forefst bulk `export`s, `deleted --extract DIR` (`export deleted DIR`) or `--log FILE`, `snapshots --extract`, `extract -o` | a file the command could not write and went on without: a content file, `holes.json`, the recovery log, and the `export_index.csv` and `extract`'s `.holes.json` of a clean file that 1.14.0 adds | 0 | 2 |

**Exit 2 where 1.13.1 exited 0: refsanalysis**

| Tool and command | Condition | 1.13.1 | 1.14.0 |
|---|---|---|---|
| refsanalysis `supb`, `chkp`, `containers` | a checkpoint copy's clocks at `+0x10` and `+0x60` differ, in use or not (forefst exits 2 for it since 1.13.0) | 0 | 2 |
| refsanalysis `summary` | the newest checkpoint copy is damaged | 0 | 2 |
| refsanalysis `supb`, `chkp`, `containers` | a copy they show fails | 0 | 2 |
| refsanalysis `supb --verify`, `boot --verify` | a check fails | 0 | 2 |
| refsanalysis `chkp --verify` | a check fails other than the page's self-checksum and the allocator-clock check (those two exit 2 since 1.13.0) | 0 | 2 |
| refsanalysis `schema --verify`, `upcase --verify`, `objects --verify`, `parentchild --verify` | a check fails | 0 | 2 |
| refsanalysis `all` | a section exits 2 or stops part-way (1 when no section can run) | 0 | 2 |
| refsanalysis `<image> forefst <cmd>` | forefst would exit 2 for skipped metadata or a volume finding | the command's own code, without forefst's escalation to 2 | forefst's code |

**Exit 1 where 1.13.1 ran: an argument or an input the command refuses**

| Tool and command | Condition | 1.13.1 | 1.14.0 |
|---|---|---|---|
| refsanalysis, every command | the forefst it imports is not the one of its release | the command ran | 1, with one line naming both versions |
| forefst, 16 commands | a stray or unknown argument | 0 | 1 |
| forefst | a format the command does not write (`summary --csv`) | 0 | 1 |
| forefst `usn`, `mlog` | two machine formats on one run | 0 (the last one was used) | 1 |
| forefst `export` | an unknown subverb | 0 (a bundle was written) | 1 |
| forefst `deleted --carve` | carving is `export deleted DIR --carve` | 0 (nothing was carved) | 1 |
| forefst `files --filter resident` | the category is `inline` | 0 | 1 |
| forefst `snapshots --extract DIR --json` | `--json` lists the versions; it does not extract them | 0 (the listing, nothing extracted) | 1 |
| forefst `files --cow-before OLD` | `OLD` is an image of another volume, or the run asks for `--body` or `--filter` | 0 | 1 |
| forefst `verify-bundle`, the bundle reader | a bundle written by 1.12.1–1.13.1 (it has no `BundleFormat`) | 0 | 1 |
| forefst, the bundle reader | a bundle written with `export metadata --btree-mode per-object` (`verify-bundle` still checks it) | 0 (read as a volume of 0 objects) | 1 |

**A closed pipe**

| Tool and command | Condition | 1.13.1 | 1.14.0 |
|---|---|---|---|
| forefst and refsanalysis, every command | the reader closes the pipe that carries the output (`\| head`) | 0, a traceback or another code (120 with stderr in the pipe) | quietly: 2 if the run had recorded a finding or a skip before the close, else 0 |
| forefst and refsanalysis, every command | the reader closes a pipe that carries only messages: stderr, or stdout when the output goes to a FILE or a directory (`--csv FILE 2>&1 \| head -1`) | 120: the run stopped, and a FILE it had not yet written was not written | the run goes on, writes its output and exits with its own code |

### Values

One form for each kind of value, in every command and format ([forefst.md — Value forms](forefst.md#value-forms)).
The forms a parser meets first:

- **A time**: UTC ISO 8601 with seven fraction digits and `Z`: `2026-05-23T08:48:26.4368773Z`.
- **An identifier, an LCN or an offset**: lower-case hex, a string in JSON. A `SecurityId` too: `0x103`, where
  1.13.1 wrote `259`.
- **A flag word** (`FileAttributes`, `InternalFlags`, `ReparseTag` …): two fields, the names of its bits
  (`FileAttributes` = `Archive`) and the word in hex (`FileAttributesHex` = `0x20`).
  - Where a 1.13.1 field of the same name held the number, the number is now in the `…Hex` field.
  - `InternalFlags` names every bit that is set, bit 0x8 included.
- **A yes / no value**: `true` / `false` in CSV and in JSON; the 1.13.1 CSV wrote `True` / `False`.
- **A value the volume does not hold**: an empty cell in CSV, `null` in JSON, `(none)` in text.
- **A list of names** (`ADSNames`, `HardLinkNames`, `SnapshotNames`):
  one CSV cell joined with `;`, a `;` inside a name written `\;`; a list in JSON.
- **`DACLSummary`**: each ACE as `security` writes it, the ACEs separated by `; `:
  `ALLOWED SYSTEM (S-1-5-18): FULL_CONTROL`, and `[inherited]` after an inherited ACE.
  1.13.1 wrote `ALLOWED:SYSTEM (S-1-5-18):FULL_CONTROL`, the ACEs separated by ` | `.
- **`IsMoved`** is no longer a yes / no value: it is `false`, or words that say how it was decided
  ([`files` column 42](forefst.md#csv-output-fields)):
  - `moved (change journal)`, `a hard link made here (change journal)`,
    `in its creation directory (change journal)`;
  - `moved (the record's reference)`;
  - `moved, or hard-linked and the original name removed`, or `undetermined`, where neither decides.
- **The MLog classes** (`mlog`, `timeline`): the column is `DerivedAction`.
  - `REPARENT` is `TABLE_REPARENTED`, and `WRITE` is `DATA_OR_REPARSE_WRITE`.
  - New: `MOVE_AND_RENAME` (moved under a new name) and `MOVE_OR_RENAME` (where the directories of the names cannot
    tell a move from a rename).
  - A name removed with no new name for it is `ENTRY_REMOVE`, where 1.13.1 could print `RENAME`.
- **A directory without a path** (`usn`, `mlog`, `timeline`, `deleted`): `<undetermined 0x…>` when the Object Table,
  or the walk of the directory tree, was read only in part; 1.13.1 wrote `<oid 0x…>` or `<unlinked 0x…>` there.
- **The checksum type** (`summary`): the one refs.sys derives, CRC64 on a volume whose boot-sector flags lack 0x40,
  where 1.13.1 printed `none`.
- **A version**: `ReFS 3.14`, never `v3.14`.
- **A byte count** is exact in machine output.
- **`timestomp`'s signals**: `FUTURE` is retired; the other signals and the tiers are unchanged.

### Documents, files and commands

- **`files --json` is the CSV row**: the same fields, names and values, typed, with `null` for an empty cell.
  - The `files` CSV has 42 columns. `IsResident` is removed (it was `True` exactly when `DataResidency` is `inline`).
  - `FileAttributesHex`, `InternalFlagsHex` and `ReparseTagHex` follow the columns they belong to, so a script that
    reads the CSV by position re-maps every column after `FileAttributes`.
- **Documents that changed shape**:
  - `timeline --json` is an object (`Events`, `SourceCounts`, `Statements`), not a list;
  - `timestomp --json` lists its rows under `Rows`;
  - `specials` without a type writes its count table (`Type`, `Objects`, `Names`) in every format, and
    `specials TYPE` and `ads` write one row per object or stream;
  - `integrity --json` carries its copies under `BootstrapBackups`, as `summary` does;
  - `details DIR --json` carries the directory's structure under `Structure`;
  - `deleted` writes every entry it prints as a row of every format, with its `Status` (`DELETED`, `RENAMED`,
    `STILL PRESENT` …), the Trash rows, the checkpoint comparison and the `--scan-pages` entries included.
- **No journal**: on a volume without a change journal, `usn --csv` writes its header row alone and `usn --json` a
  document with no records, and the sentence goes to stderr. 1.13.1 wrote only the sentence, where the document was
  expected.
- **Output files**: a FILE output, and `extract -o FILE`, is written as `<FILE>.partial` (a short name beside it when
  that name would be too long) and renamed when complete.
  - A failed write leaves no file under FILE's name and names FILE in its error.
  - A FILE that is not a regular file (a device, a FIFO, a process substitution) is written directly.
  - Status lines (`Wrote …`) are on stderr.
- **`export file PATH` and `export ads PATH:STREAM` write to disk**: `./<the file's name>` (a stream:
  `<file>__<stream>`), or into `-o DIR/`, never over a file (`<name>.dupN`); `-o FILE` as given, `-o -` the screen.
  1.13.1 wrote to the screen without `-o`. `extract` stays the screen command.
- **Bundles**: `manifest.json` begins with `BundleFormat`.
  - A bundle written by 1.12.1–1.13.1 is refused: export it again with 1.14.0.
  - 1.13.1 cannot read a bundle 1.14.0 writes (it stops with `KeyError: 'cluster_size'`).
  - A second `export metadata` into a directory that already holds a bundle is written beside it (`<dir>_2`,
    `<dir>_3` …) and the path used is printed; 1.13.1 wrote into the same directory.
- **refsanalysis**:
  - `files` gains an `ObjectRef` and a `Data` column, and its header names its columns;
  - `attributes` writes a SecurityId as `0x103 (259)`;
  - `details` writes `USN: (none)` for a file with no journal record (1.13.1: `0`), and `details --json` adds
    `USNJournalID` and `PackedEASize`;
  - `boot` and `bootedit` write the volume flags as the word with its bits' names, a bit without a name last.

### Text views

A script that parses the text views meets these changes:

- **`summary`**:
  - its title is `ReFS Volume Summary` (1.13.1 printed `fastsummary`'s, `ReFS Volume Fast Extended Summary`);
  - `Volume modified:` is `Last mount (rw):`, `Containers used:` is `Containers mapped:`, `Integrity objects:` is
    `Integrity files:`, and `File data:` is `File contents:`;
  - `Files:` counts each file once, with its residency words, and the names are on their own `Names:` line; the
    census below it counts files, each once;
  - the image tail is on one line; sizes are in IEC units.
- **`timestomp`**: `Volume modified` is `Last mount (rw)`; 1.13.1's time column `Last real write` is `Changed`; each row's
  evidence follows its signals.
- **`integrity`**: the boot sectors, the superblock copies and the checkpoint copies are given their offsets from
  the start of the image, each checkpoint copy with its role.
- **Both tools**:
  - a count of one takes the singular (`1 file sharing 2 names`, `1 row`);
  - prose wraps at about 100 characters (data rows and stderr lines are never wrapped);
  - the rules between sections are 78 characters wide.

### The keys, command by command

Measured on 2026-11-16: each command's machine forms run with 1.13.1 and with 1.14.0 on the same five volumes (the
four public samples and one ReFS 3.4 volume, named in the Evidence section), and every key path the outputs held
paired with its 1.14.0 name.

A key that appears only on other volumes (a field that is written only when the volume holds it) is not in the
tables.

In a path, `A.B` is `B` inside the object `A`, `A[].B` is `B` inside each object of the list `A`, and `A{*}` is a map
whose keys are values. A row with a note was paired by reading both releases' code; every other row follows the rule
above.

<!-- key-migration: generated by analysis/verification/gen_key_migration.py page; do not edit -->

### `files`

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `IsResident` | (removed) | the alias kept since 1.10.0; it was True exactly when DataResidency is inline |

Unchanged: `Accessed`, `ADSNames`, `AllocatedSize`, `Changed`, `Created`, `CreationDir`, `DACLSummary`, `DataResidency`, `Extension`, `FileAttributes`, `FileID`, `FileName`, `FileSize`, `FullPath`, `GroupSid`, `HardLinkCount`, `HardLinkNames`, `HasADS`, `HasEA`, `HasIntegrity`, `HomeOID`, `InternalFlags`, `IsCompressed`, `IsDirectory`, `IsEncrypted`, `IsMoved`, `IsSparse`, `Modified`, `ObjectRef`, `OwnerSid`, `ParentOID`, `ParentPath`, `RecordPlacement`, `ReparseTag`, `ReparseTarget`, `SecurityId`, `SnapshotCount`, `SnapshotNames`, `USN`.

New in 1.14.0: `FileAttributesHex`, `InternalFlagsHex`, `ReparseTagHex`.

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `[].accessed` | `[].Accessed` |  |
| `[].ads_names` | `[].ADSNames` |  |
| `[].allocated_size` | `[].AllocatedSize` |  |
| `[].changed` | `[].Changed` |  |
| `[].created` | `[].Created` |  |
| `[].creation_dir` | `[].CreationDir` |  |
| `[].creation_dir_oid` | `[].HomeOID` | the directory the file was created in |
| `[].dacl_summary` | `[].DACLSummary` |  |
| `[].extension` | `[].Extension` |  |
| `[].file_attributes` | `[].FileAttributes` |  |
| `[].file_id` | `[].FileID` |  |
| `[].file_name` | `[].FileName` |  |
| `[].file_ref` | `[].ObjectRef` |  |
| `[].file_size` | `[].FileSize` |  |
| `[].full_path` | `[].FullPath` |  |
| `[].group_sid` | `[].GroupSid` |  |
| `[].hard_link_count` | `[].HardLinkCount` |  |
| `[].hard_link_names` | `[].HardLinkNames` |  |
| `[].has_ads` | `[].HasADS` |  |
| `[].has_ea` | `[].HasEA` |  |
| `[].has_integrity` | `[].HasIntegrity` |  |
| `[].id` | `[].ObjectRef` | one identity column: a directory's OID:0x0, a file's HomeOID:FileID |
| `[].internal_flags` | `[].InternalFlags` |  |
| `[].is_compressed` | `[].IsCompressed` |  |
| `[].is_directory` | `[].IsDirectory` |  |
| `[].is_encrypted` | `[].IsEncrypted` |  |
| `[].is_moved` | `[].IsMoved` |  |
| `[].is_resident` | (removed) | DataResidency holds the form |
| `[].is_sparse` | `[].IsSparse` |  |
| `[].modified` | `[].Modified` |  |
| `[].oid` | `[].ObjectRef` | a directory's OID is the first part of its ObjectRef (OID:0x0); it was null for a file |
| `[].owner_sid` | `[].OwnerSid` |  |
| `[].parent_oid` | `[].ParentOID` |  |
| `[].parent_path` | `[].ParentPath` |  |
| `[].reparse_tag` | `[].ReparseTag` |  |
| `[].reparse_target` | `[].ReparseTarget` |  |
| `[].security_id` | `[].SecurityId` |  |
| `[].snapshot_count` | `[].SnapshotCount` |  |
| `[].snapshot_names` | `[].SnapshotNames` |  |
| `[].usn` | `[].USN` |  |

New in 1.14.0: `[].DataResidency`, `[].FileAttributesHex`, `[].InternalFlagsHex`, `[].RecordPlacement`, `[].ReparseTagHex`.

**JSONL**: as JSON, one object per line.

### `search`

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `file_size` | `FileSize` |  |
| `id` | `ObjectRef` | one identity column |
| `is_deleted` | (removed) | not written in the CSV or JSON (no view marks a file deleted: the mark never fired; removed in 1.14.0) |
| `is_resident` | `DataResidency` | the boolean was DataResidency == inline |
| `modified` | `Modified` |  |
| `oid` | `ObjectRef` | held a directory's OID, or a file's data residency in parentheses |
| `parent_oid` | `ParentOID` |  |
| `path` | `FullPath` |  |
| `type` | `IsDirectory` | Dir / File -> true / false |

New in 1.14.0: `Created`, `FileName`.

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `[].created` | `[].Created` |  |
| `[].data` | `[].DataResidency` | the residency word |
| `[].file_size` | `[].FileSize` |  |
| `[].id` | `[].ObjectRef` | one identity column |
| `[].is_deleted` | (removed) | not written in the CSV or JSON (no view marks a file deleted: the mark never fired; removed in 1.14.0) |
| `[].is_resident` | `[].DataResidency` | the boolean was DataResidency == inline |
| `[].modified` | `[].Modified` |  |
| `[].name` | `[].FileName` | the name |
| `[].oid` | `[].ObjectRef` | held a directory's OID, or a file's data residency in parentheses |
| `[].parent_oid` | `[].ParentOID` |  |
| `[].path` | `[].FullPath` |  |
| `[].type` | `[].IsDirectory` | Dir / File -> true / false |

### `details`

**file JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `accessed` | `Accessed` |  |
| `ads_names` | `ADSNames` |  |
| `allocated_size` | `AllocatedSize` |  |
| `changed` | `Changed` |  |
| `created` | `Created` |  |
| `creation_dir` | `CreationDir` |  |
| `creation_dir_oid` | `HomeOID` | the directory the file was created in |
| `dacl_summary` | `DACLSummary` |  |
| `extension` | `Extension` |  |
| `file_attributes` | `FileAttributes` |  |
| `file_id` | `FileID` |  |
| `file_name` | `FileName` |  |
| `file_ref` | `ObjectRef` |  |
| `file_size` | `FileSize` |  |
| `full_path` | `FullPath` |  |
| `group_sid` | `GroupSid` |  |
| `hard_link_count` | `HardLinkCount` |  |
| `hard_link_names` | `HardLinkNames` |  |
| `has_ads` | `HasADS` |  |
| `has_ea` | `HasEA` |  |
| `has_integrity` | `HasIntegrity` |  |
| `id` | `ObjectRef` | one identity column |
| `internal_flags` | `InternalFlags` |  |
| `is_compressed` | `IsCompressed` |  |
| `is_directory` | `IsDirectory` |  |
| `is_encrypted` | `IsEncrypted` |  |
| `is_moved` | `IsMoved` |  |
| `is_resident` | (removed) | as in files |
| `is_sparse` | `IsSparse` |  |
| `modified` | `Modified` |  |
| `oid` | `ObjectRef` | a directory's OID is the first part of its ObjectRef |
| `owner_sid` | `OwnerSid` |  |
| `parent_oid` | `ParentOID` |  |
| `parent_path` | `ParentPath` |  |
| `reparse_tag` | `ReparseTag` |  |
| `reparse_target` | `ReparseTarget` |  |
| `security_id` | `SecurityId` |  |
| `snapshot_count` | `SnapshotCount` |  |
| `snapshot_names` | `SnapshotNames` |  |
| `usn` | `USN` |  |

New in 1.14.0: `DataResidency`, `FileAttributesHex`, `InternalFlagsHex`, `RecordPlacement`, `ReparseTagHex`.

**file CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `IsResident` | (removed) | as in files |

Unchanged: `Accessed`, `ADSNames`, `AllocatedSize`, `Changed`, `Created`, `CreationDir`, `DACLSummary`, `DataResidency`, `Extension`, `FileAttributes`, `FileID`, `FileName`, `FileSize`, `FullPath`, `GroupSid`, `HardLinkCount`, `HardLinkNames`, `HasADS`, `HasEA`, `HasIntegrity`, `HomeOID`, `InternalFlags`, `IsCompressed`, `IsDirectory`, `IsEncrypted`, `IsMoved`, `IsSparse`, `Modified`, `ObjectRef`, `OwnerSid`, `ParentOID`, `ParentPath`, `RecordPlacement`, `ReparseTag`, `ReparseTarget`, `SecurityId`, `SnapshotCount`, `SnapshotNames`, `USN`.

New in 1.14.0: `FileAttributesHex`, `InternalFlagsHex`, `ReparseTagHex`.

**dir JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `attribute_count` | `Structure.AttributeCount` | the directory's structure moved under Structure |
| `attribute_types` | `Structure.AttributeTypes` | moved under Structure |
| `attributes` | `Structure.Attributes` | moved under Structure |
| `attributes{*}` | `Structure.Attributes{*}` | moved under Structure |
| `attributes{*}{*}` | `Structure.Attributes{*}{*}` | moved under Structure |
| `attributes{*}{*}[].backing_alloc` | `Structure.Attributes{*}{*}[].BackingAlloc` | moved under Structure |
| `attributes{*}{*}[].backing_size` | `Structure.Attributes{*}{*}[].BackingSize` | moved under Structure |
| `attributes{*}{*}[].child_oid` | `Structure.Attributes{*}{*}[].ChildOID` | moved under Structure |
| `attributes{*}{*}[].cluster_count` | `Structure.Attributes{*}{*}[].ClusterCount` | moved under Structure |
| `attributes{*}{*}[].extent_key` | `Structure.Attributes{*}{*}[].ExtentKey` | moved under Structure |
| `attributes{*}{*}[].file_attrs` | `Structure.Attributes{*}{*}[].FileAttributes` | moved under Structure |
| `attributes{*}{*}[].file_size` | `Structure.Attributes{*}{*}[].FileSize` | moved under Structure |
| `attributes{*}{*}[].filename` | `Structure.Attributes{*}{*}[].FileName` | moved under Structure |
| `attributes{*}{*}[].home_backref` | `Structure.Attributes{*}{*}[].HomeBackref` | moved under Structure |
| `attributes{*}{*}[].key_len` | `Structure.Attributes{*}{*}[].KeyLength` | moved under Structure |
| `attributes{*}{*}[].raw_hex` | `Structure.Attributes{*}{*}[].RawHex` | moved under Structure |
| `attributes{*}{*}[].record` | `Structure.Attributes{*}{*}[].Record` | moved under Structure |
| `attributes{*}{*}[].si` | `Structure.Attributes{*}{*}[].SI` | moved under Structure |
| `attributes{*}{*}[].si.access_time` | `Structure.Attributes{*}{*}[].SI.Accessed` | moved under Structure |
| `attributes{*}{*}[].si.change_time` | `Structure.Attributes{*}{*}[].SI.Changed` | moved under Structure |
| `attributes{*}{*}[].si.create_time` | `Structure.Attributes{*}{*}[].SI.Created` | moved under Structure |
| `attributes{*}{*}[].si.datasize` | `Structure.Attributes{*}{*}[].SI.AllocatedSize` | renamed: $SI+0x38 is the allocated size on a file's record (1.13.1 called it the data size) |
| `attributes{*}{*}[].si.external_file_id_2` | `Structure.Attributes{*}{*}[].SI.ExternalFileID2` | moved under Structure |
| `attributes{*}{*}[].si.external_file_id_3` | `Structure.Attributes{*}{*}[].SI.ExternalFileID3` | moved under Structure |
| `attributes{*}{*}[].si.file_attrs` | `Structure.Attributes{*}{*}[].SI.FileAttributes` | moved under Structure |
| `attributes{*}{*}[].si.hard_link_count` | `Structure.Attributes{*}{*}[].SI.HardLinkCount` | moved under Structure |
| `attributes{*}{*}[].si.internal_flags` | `Structure.Attributes{*}{*}[].SI.InternalFlags` | moved under Structure |
| `attributes{*}{*}[].si.last_usn` | `Structure.Attributes{*}{*}[].SI.USN` | moved under Structure |
| `attributes{*}{*}[].si.modify_time` | `Structure.Attributes{*}{*}[].SI.Modified` | moved under Structure |
| `attributes{*}{*}[].si.next_file_id` | `Structure.Attributes{*}{*}[].SI.NextFileID` | moved under Structure |
| `attributes{*}{*}[].si.next_stream_set_id` | `Structure.Attributes{*}{*}[].SI.NextStreamSetID` | moved under Structure |
| `attributes{*}{*}[].si.packed_ea_size_or_reparse_low` | `Structure.Attributes{*}{*}[].SI.PackedEASizeOrReparseLow` | moved under Structure |
| `attributes{*}{*}[].si.reparse_tag` | `Structure.Attributes{*}{*}[].SI.ReparseTag` | moved under Structure |
| `attributes{*}{*}[].si.security_id` | `Structure.Attributes{*}{*}[].SI.SecurityId` | moved under Structure |
| `attributes{*}{*}[].si.si_field_0x30` | `Structure.Attributes{*}{*}[].SI.DataSize` | renamed: $SI+0x30 is the data size on a file's record; an integer (1.13.1 wrote a hex string) |
| `attributes{*}{*}[].si.usn_journal_id` | `Structure.Attributes{*}{*}[].SI.USNJournalID` | moved under Structure |
| `attributes{*}{*}[].storage` | `Structure.Attributes{*}{*}[].Storage` | moved under Structure |
| `attributes{*}{*}[].value_len` | `Structure.Attributes{*}{*}[].ValueLength` | moved under Structure |
| `attributes{*}{*}[].value_size` | `Structure.Attributes{*}{*}[].ValueSize` | moved under Structure |
| `oid` | `ObjectRef` | the directory's ObjectRef (OID:0x0); the OID itself is Structure.OID |
| `vlcns` | `Structure.VLCNs` | moved under Structure |

New in 1.14.0: `ChildEntries`, `DACLSummary`, `FullPath`, `GroupSid`, `IsDirectory`, `OwnerSid`, `Structure`, `Structure.Attributes{*}{*}[].FileAttributesHex`, `Structure.Attributes{*}{*}[].SI.FileAttributesHex`, `Structure.Attributes{*}{*}[].SI.InternalFlagsHex`, `Structure.Attributes{*}{*}[].SI.ReparseTagHex`, `Structure.OID`.

### `summary`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `ads_entries` | `ADSHostFiles` |  |
| `bootstrap_backups` | `BootstrapBackups` |  |
| `bootstrap_backups.checkpoint_authoritative_unusable` | `BootstrapBackups.CheckpointAuthoritativeUnusable` |  |
| `bootstrap_backups.checkpoint_selected_via_fallback` | `BootstrapBackups.CheckpointSelectedViaFallback` |  |
| `bootstrap_backups.checkpoint_tie` | `BootstrapBackups.CheckpointTie` |  |
| `bootstrap_backups.checkpoint_used_lcn` | `BootstrapBackups.CheckpointUsedLCN` |  |
| `bootstrap_backups.checkpoints` | `BootstrapBackups.Checkpoints` |  |
| `bootstrap_backups.checkpoints[].alloc_clock` | `BootstrapBackups.Checkpoints[].AllocClock` |  |
| `bootstrap_backups.checkpoints[].ckname` | `BootstrapBackups.Checkpoints[].ChecksumName` |  |
| `bootstrap_backups.checkpoints[].cksum_ok` | `BootstrapBackups.Checkpoints[].ChecksumOK` |  |
| `bootstrap_backups.checkpoints[].clock_divergence` | `BootstrapBackups.Checkpoints[].ClockDivergence` |  |
| `bootstrap_backups.checkpoints[].lcn` | `BootstrapBackups.Checkpoints[].LCN` |  |
| `bootstrap_backups.checkpoints[].lsn` | `BootstrapBackups.Checkpoints[].LSN` |  |
| `bootstrap_backups.checkpoints[].role` | `BootstrapBackups.Checkpoints[].Role` |  |
| `bootstrap_backups.checkpoints[].roots_ok` | `BootstrapBackups.Checkpoints[].RootsOK` |  |
| `bootstrap_backups.checkpoints[].self_lcn` | `BootstrapBackups.Checkpoints[].SelfLCN` |  |
| `bootstrap_backups.checkpoints[].self_lcn_ok` | `BootstrapBackups.Checkpoints[].SelfLCNOK` |  |
| `bootstrap_backups.checkpoints[].sha256` | `BootstrapBackups.Checkpoints[].SHA256` |  |
| `bootstrap_backups.checkpoints[].sig_ok` | `BootstrapBackups.Checkpoints[].SignatureOK` |  |
| `bootstrap_backups.checkpoints[].tied_clock` | `BootstrapBackups.Checkpoints[].TiedClock` |  |
| `bootstrap_backups.checkpoints[].vc` | `BootstrapBackups.Checkpoints[].VirtualClock` |  |
| `bootstrap_backups.checkpoints[].vc_page` | `BootstrapBackups.Checkpoints[].VirtualClockPage` |  |
| `bootstrap_backups.supb` | `BootstrapBackups.SUPB` |  |
| `bootstrap_backups.supb[].ckname` | `BootstrapBackups.SUPB[].ChecksumName` |  |
| `bootstrap_backups.supb[].cksum_ok` | `BootstrapBackups.SUPB[].ChecksumOK` |  |
| `bootstrap_backups.supb[].lcn` | `BootstrapBackups.SUPB[].LCN` |  |
| `bootstrap_backups.supb[].ok` | `BootstrapBackups.SUPB[].OK` |  |
| `bootstrap_backups.supb[].role` | `BootstrapBackups.SUPB[].Role` |  |
| `bootstrap_backups.supb[].self_lcn` | `BootstrapBackups.SUPB[].SelfLCN` |  |
| `bootstrap_backups.supb[].self_lcn_ok` | `BootstrapBackups.SUPB[].SelfLCNOK` |  |
| `bootstrap_backups.supb[].sha256` | `BootstrapBackups.SUPB[].SHA256` |  |
| `bootstrap_backups.vbr` | `BootstrapBackups.VBR` |  |
| `bootstrap_backups.vbr.backup` | `BootstrapBackups.VBR.Backup` |  |
| `bootstrap_backups.vbr.backup.byte_offset` | `BootstrapBackups.VBR.Backup.ByteOffset` |  |
| `bootstrap_backups.vbr.backup.cksum_ok` | `BootstrapBackups.VBR.Backup.ChecksumOK` |  |
| `bootstrap_backups.vbr.backup.lba` | `BootstrapBackups.VBR.Backup.LBA` |  |
| `bootstrap_backups.vbr.backup.matches_primary` | `BootstrapBackups.VBR.Backup.MatchesPrimary` |  |
| `bootstrap_backups.vbr.backup.present` | `BootstrapBackups.VBR.Backup.Present` |  |
| `bootstrap_backups.vbr.backup.primary_version` | `BootstrapBackups.VBR.Backup.PrimaryVersion` |  |
| `bootstrap_backups.vbr.backup.sha256` | `BootstrapBackups.VBR.Backup.SHA256` |  |
| `bootstrap_backups.vbr.backup.version` | `BootstrapBackups.VBR.Backup.Version` |  |
| `bootstrap_backups.vbr.primary_cksum_ok` | `BootstrapBackups.VBR.PrimaryChecksumOK` |  |
| `bootstrap_backups.vbr.primary_ok` | `BootstrapBackups.VBR.PrimaryOK` |  |
| `bootstrap_backups.vbr.sector_size` | `BootstrapBackups.VBR.SectorSize` |  |
| `bootstrap_backups.vbr.total_sectors` | `BootstrapBackups.VBR.TotalSectors` |  |
| `capacity` | `Capacity` |  |
| `capacity.allocator_covered_bytes` | `Capacity.AllocatorCoveredBytes` |  |
| `capacity.free` | (removed) | a display string (Capacity.NotAllocatedBytes is the number) |
| `capacity.free_bytes` | (removed) | the same number as Capacity.NotAllocatedBytes |
| `capacity.not_allocated` | (removed) | a display string (Capacity.NotAllocatedBytes) |
| `capacity.not_allocated_bytes` | `Capacity.NotAllocatedBytes` |  |
| `capacity.outside_allocator_bytes` | `Capacity.OutsideAllocatorBytes` |  |
| `capacity.source` | `Capacity.Source` |  |
| `capacity.used` | (removed) | a display string (Capacity.UsedBytes) |
| `capacity.used_bytes` | `Capacity.UsedBytes` |  |
| `capacity.used_pct` | `Capacity.UsedPercent` |  |
| `capacity.volume_bytes` | `Capacity.VolumeBytes` |  |
| `checkpoint_flags` | `CheckpointFlagsHex` | the word in hex; CheckpointFlags now holds the names |
| `checkpoint_vc` | `CheckpointVirtualClock` |  |
| `checksum` | `Checksum` |  |
| `chkp_sha256` | `CHKPSHA256` |  |
| `cluster_size` | `ClusterSize` |  |
| `compressed_files` | `CompressedFiles` |  |
| `container_size` | `ContainerSize` |  |
| `containers_free` | `ContainersMappedBootRegion` | the rows that map the boot region; not free space |
| `containers_mapped` | `ContainersMapped` |  |
| `containers_used` | `ContainersMappedNonBoot` | the Container Table rows other than the boot region's; not usage |
| `directories` | `Directories` |  |
| `driver_note` | `DriverNote` |  |
| `driver_version` | `DriverVersion` |  |
| `encrypted_files` | `EncryptedFiles` |  |
| `files` | `Files` |  |
| `fs_metadata` | `FSMetadata` |  |
| `fs_metadata.children` | `FSMetadata.Children` |  |
| `fs_metadata.rows` | `FSMetadata.Rows` |  |
| `fs_metadata.usn_journal` | `FSMetadata.USNJournal` |  |
| `hardlink_extra` | `HardLinkExtraNames` |  |
| `hardlink_groups` | `HardLinkedFiles` |  |
| `hardlink_names` | `HardLinkNameCount` |  |
| `image` | `Image` |  |
| `image_size` | `ImageSize` |  |
| `integrity_files` | `IntegrityFiles` |  |
| `newest_timestamp` | `NewestTimestamp` |  |
| `non_resident_files` | `Residency{*}` | as above |
| `objects` | `ObjectCount` |  |
| `oldest_timestamp` | `OldestTimestamp` |  |
| `partition_start` | `PartitionStart` |  |
| `refs_version` | `ReFSVersion` |  |
| `reparse_index_entries` | `ReparseIndexEntries` |  |
| `resident_files` | `Residency{*}` | the files counted per residency category (inline, extents, ...) |
| `root_table_rows` | `RootTableRows` |  |
| `root_table_rows{*}` | `RootTableRows{*}` |  |
| `root_tables_unreadable` | `RootTablesUnreadable` |  |
| `security_descriptors` | `SecurityDescriptors` |  |
| `snapshot_files` | `SnapshotFiles` |  |
| `snapshots` | `SnapshotVersions` |  |
| `summary_mode` | `SummaryMode` |  |
| `supb_sha256` | `SUPBSHA256` |  |
| `tool` | `Tool` |  |
| `total_file_size` | `TotalFileSize` |  |
| `total_file_size_bytes` | `TotalFileSize` |  |
| `trash_table_entries` | `TrashTableEntries` |  |
| `usn_journal_id` | `USNJournalID` |  |
| `utilization_pct` | (removed) | it was the mapped-container count as a percentage; the usage is Capacity.UsedPercent |
| `vbr_sha256` | `VBRSHA256` |  |
| `volume_create_time` | `VolumeCreateTime` |  |
| `volume_guid` | `VolumeGUID` |  |
| `volume_label` | `VolumeLabel` |  |
| `volume_modify_time` | `VolumeLastWritableMountTime` | the last mount that could write |
| `volume_serial` | `VolumeSerial` |  |
| `volume_size` | `VolumeSize` |  |
| `volume_size_bytes` | `VolumeSize` |  |
| `volume_state` | `VolumeState` |  |
| `volume_version` | `VolumeVersion` |  |

New in 1.14.0: `BootstrapBackups.CheckpointFindings`, `BootstrapBackups.Checkpoints[].ByteOffset`, `BootstrapBackups.Checkpoints[].InUse`, `BootstrapBackups.Checkpoints[].RootFail`, `BootstrapBackups.Checkpoints[].RootUnchecked`, `BootstrapBackups.Checkpoints[].SHA256Bytes`, `BootstrapBackups.Checkpoints[].Use`, `BootstrapBackups.SUPB[].ByteOffset`, `BootstrapBackups.SUPB[].PayloadMatches`, `BootstrapBackups.SUPB[].SignatureOK`, `BootstrapBackups.SUPB[].Used`, `BootstrapBackups.VBR.Backup.ChecksumComputed`, `BootstrapBackups.VBR.Backup.ChecksumStored`, `BootstrapBackups.VBR.ByteOffset`, `BootstrapBackups.VBR.PrimaryChecksumComputed`, `BootstrapBackups.VBR.PrimaryChecksumStored`, `CheckpointFlags`, `CheckpointSHA256Bytes`, `ChecksumSelectorNote`, `ContainerSizeFrom`, `CountsUnreadable`, `FSMetadata.Children[].FileID`, `FSMetadata.Children[].Name`, `FSMetadata.Children[].StreamCount`, `FileNames`, `FilesAccessedAfterChange`, `ImageTail`, `ImageTail.AfterPartitionBytes`, `ImageTail.Bytes`, `ImageTail.InPartitionBytes`, `ImageTail.PartitionEntry`, `MLog`, `MLog.Read`, `RedundancyFindings`, `RedundancyNotes`, `ReparseFiles`, `Residency`, `SUPBUsedLCN`.

**mlog JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `ads_entries` | `ADSHostFiles` |  |
| `bootstrap_backups` | `BootstrapBackups` |  |
| `bootstrap_backups.checkpoint_authoritative_unusable` | `BootstrapBackups.CheckpointAuthoritativeUnusable` |  |
| `bootstrap_backups.checkpoint_selected_via_fallback` | `BootstrapBackups.CheckpointSelectedViaFallback` |  |
| `bootstrap_backups.checkpoint_tie` | `BootstrapBackups.CheckpointTie` |  |
| `bootstrap_backups.checkpoint_used_lcn` | `BootstrapBackups.CheckpointUsedLCN` |  |
| `bootstrap_backups.checkpoints` | `BootstrapBackups.Checkpoints` |  |
| `bootstrap_backups.checkpoints[].alloc_clock` | `BootstrapBackups.Checkpoints[].AllocClock` |  |
| `bootstrap_backups.checkpoints[].ckname` | `BootstrapBackups.Checkpoints[].ChecksumName` |  |
| `bootstrap_backups.checkpoints[].cksum_ok` | `BootstrapBackups.Checkpoints[].ChecksumOK` |  |
| `bootstrap_backups.checkpoints[].clock_divergence` | `BootstrapBackups.Checkpoints[].ClockDivergence` |  |
| `bootstrap_backups.checkpoints[].lcn` | `BootstrapBackups.Checkpoints[].LCN` |  |
| `bootstrap_backups.checkpoints[].lsn` | `BootstrapBackups.Checkpoints[].LSN` |  |
| `bootstrap_backups.checkpoints[].role` | `BootstrapBackups.Checkpoints[].Role` |  |
| `bootstrap_backups.checkpoints[].roots_ok` | `BootstrapBackups.Checkpoints[].RootsOK` |  |
| `bootstrap_backups.checkpoints[].self_lcn` | `BootstrapBackups.Checkpoints[].SelfLCN` |  |
| `bootstrap_backups.checkpoints[].self_lcn_ok` | `BootstrapBackups.Checkpoints[].SelfLCNOK` |  |
| `bootstrap_backups.checkpoints[].sha256` | `BootstrapBackups.Checkpoints[].SHA256` |  |
| `bootstrap_backups.checkpoints[].sig_ok` | `BootstrapBackups.Checkpoints[].SignatureOK` |  |
| `bootstrap_backups.checkpoints[].tied_clock` | `BootstrapBackups.Checkpoints[].TiedClock` |  |
| `bootstrap_backups.checkpoints[].vc` | `BootstrapBackups.Checkpoints[].VirtualClock` |  |
| `bootstrap_backups.checkpoints[].vc_page` | `BootstrapBackups.Checkpoints[].VirtualClockPage` |  |
| `bootstrap_backups.supb` | `BootstrapBackups.SUPB` |  |
| `bootstrap_backups.supb[].ckname` | `BootstrapBackups.SUPB[].ChecksumName` |  |
| `bootstrap_backups.supb[].cksum_ok` | `BootstrapBackups.SUPB[].ChecksumOK` |  |
| `bootstrap_backups.supb[].lcn` | `BootstrapBackups.SUPB[].LCN` |  |
| `bootstrap_backups.supb[].ok` | `BootstrapBackups.SUPB[].OK` |  |
| `bootstrap_backups.supb[].role` | `BootstrapBackups.SUPB[].Role` |  |
| `bootstrap_backups.supb[].self_lcn` | `BootstrapBackups.SUPB[].SelfLCN` |  |
| `bootstrap_backups.supb[].self_lcn_ok` | `BootstrapBackups.SUPB[].SelfLCNOK` |  |
| `bootstrap_backups.supb[].sha256` | `BootstrapBackups.SUPB[].SHA256` |  |
| `bootstrap_backups.vbr` | `BootstrapBackups.VBR` |  |
| `bootstrap_backups.vbr.backup` | `BootstrapBackups.VBR.Backup` |  |
| `bootstrap_backups.vbr.backup.byte_offset` | `BootstrapBackups.VBR.Backup.ByteOffset` |  |
| `bootstrap_backups.vbr.backup.cksum_ok` | `BootstrapBackups.VBR.Backup.ChecksumOK` |  |
| `bootstrap_backups.vbr.backup.lba` | `BootstrapBackups.VBR.Backup.LBA` |  |
| `bootstrap_backups.vbr.backup.matches_primary` | `BootstrapBackups.VBR.Backup.MatchesPrimary` |  |
| `bootstrap_backups.vbr.backup.present` | `BootstrapBackups.VBR.Backup.Present` |  |
| `bootstrap_backups.vbr.backup.primary_version` | `BootstrapBackups.VBR.Backup.PrimaryVersion` |  |
| `bootstrap_backups.vbr.backup.sha256` | `BootstrapBackups.VBR.Backup.SHA256` |  |
| `bootstrap_backups.vbr.backup.version` | `BootstrapBackups.VBR.Backup.Version` |  |
| `bootstrap_backups.vbr.primary_cksum_ok` | `BootstrapBackups.VBR.PrimaryChecksumOK` |  |
| `bootstrap_backups.vbr.primary_ok` | `BootstrapBackups.VBR.PrimaryOK` |  |
| `bootstrap_backups.vbr.sector_size` | `BootstrapBackups.VBR.SectorSize` |  |
| `bootstrap_backups.vbr.total_sectors` | `BootstrapBackups.VBR.TotalSectors` |  |
| `capacity` | `Capacity` |  |
| `capacity.allocator_covered_bytes` | `Capacity.AllocatorCoveredBytes` |  |
| `capacity.free` | (removed) | a display string (Capacity.NotAllocatedBytes is the number) |
| `capacity.free_bytes` | (removed) | the same number as Capacity.NotAllocatedBytes |
| `capacity.not_allocated` | (removed) | a display string (Capacity.NotAllocatedBytes) |
| `capacity.not_allocated_bytes` | `Capacity.NotAllocatedBytes` |  |
| `capacity.outside_allocator_bytes` | `Capacity.OutsideAllocatorBytes` |  |
| `capacity.source` | `Capacity.Source` |  |
| `capacity.used` | (removed) | a display string (Capacity.UsedBytes) |
| `capacity.used_bytes` | `Capacity.UsedBytes` |  |
| `capacity.used_pct` | `Capacity.UsedPercent` |  |
| `capacity.volume_bytes` | `Capacity.VolumeBytes` |  |
| `checkpoint_flags` | `CheckpointFlagsHex` | the word in hex; CheckpointFlags now holds the names |
| `checkpoint_vc` | `CheckpointVirtualClock` |  |
| `checksum` | `Checksum` |  |
| `chkp_sha256` | `CHKPSHA256` |  |
| `cluster_size` | `ClusterSize` |  |
| `compressed_files` | `CompressedFiles` |  |
| `container_size` | `ContainerSize` |  |
| `containers_free` | `ContainersMappedBootRegion` | the rows that map the boot region; not free space |
| `containers_mapped` | `ContainersMapped` |  |
| `containers_used` | `ContainersMappedNonBoot` | the Container Table rows other than the boot region's; not usage |
| `directories` | `Directories` |  |
| `driver_note` | `DriverNote` |  |
| `driver_version` | `DriverVersion` |  |
| `encrypted_files` | `EncryptedFiles` |  |
| `files` | `Files` |  |
| `fs_metadata` | `FSMetadata` |  |
| `fs_metadata.children` | `FSMetadata.Children` |  |
| `fs_metadata.rows` | `FSMetadata.Rows` |  |
| `fs_metadata.usn_journal` | `FSMetadata.USNJournal` |  |
| `hardlink_extra` | `HardLinkExtraNames` |  |
| `hardlink_groups` | `HardLinkedFiles` |  |
| `hardlink_names` | `HardLinkNameCount` |  |
| `image` | `Image` |  |
| `image_size` | `ImageSize` |  |
| `integrity_files` | `IntegrityFiles` |  |
| `newest_timestamp` | `NewestTimestamp` |  |
| `non_resident_files` | `Residency{*}` | as above |
| `objects` | `ObjectCount` |  |
| `oldest_timestamp` | `OldestTimestamp` |  |
| `partition_start` | `PartitionStart` |  |
| `refs_version` | `ReFSVersion` |  |
| `reparse_index_entries` | `ReparseIndexEntries` |  |
| `resident_files` | `Residency{*}` | the files counted per residency category (inline, extents, ...) |
| `root_table_rows` | `RootTableRows` |  |
| `root_table_rows{*}` | `RootTableRows{*}` |  |
| `root_tables_unreadable` | `RootTablesUnreadable` |  |
| `security_descriptors` | `SecurityDescriptors` |  |
| `snapshot_files` | `SnapshotFiles` |  |
| `snapshots` | `SnapshotVersions` |  |
| `summary_mode` | `SummaryMode` |  |
| `supb_sha256` | `SUPBSHA256` |  |
| `tool` | `Tool` |  |
| `total_file_size` | `TotalFileSize` |  |
| `total_file_size_bytes` | `TotalFileSize` |  |
| `trash_table_entries` | `TrashTableEntries` |  |
| `usn_journal_id` | `USNJournalID` |  |
| `utilization_pct` | (removed) | it was the mapped-container count as a percentage; the usage is Capacity.UsedPercent |
| `vbr_sha256` | `VBRSHA256` |  |
| `volume_create_time` | `VolumeCreateTime` |  |
| `volume_guid` | `VolumeGUID` |  |
| `volume_label` | `VolumeLabel` |  |
| `volume_modify_time` | `VolumeLastWritableMountTime` | the last mount that could write |
| `volume_serial` | `VolumeSerial` |  |
| `volume_size` | `VolumeSize` |  |
| `volume_size_bytes` | `VolumeSize` |  |
| `volume_state` | `VolumeState` |  |
| `volume_version` | `VolumeVersion` |  |

New in 1.14.0: `BootstrapBackups.CheckpointFindings`, `BootstrapBackups.Checkpoints[].ByteOffset`, `BootstrapBackups.Checkpoints[].InUse`, `BootstrapBackups.Checkpoints[].RootFail`, `BootstrapBackups.Checkpoints[].RootUnchecked`, `BootstrapBackups.Checkpoints[].SHA256Bytes`, `BootstrapBackups.Checkpoints[].Use`, `BootstrapBackups.SUPB[].ByteOffset`, `BootstrapBackups.SUPB[].PayloadMatches`, `BootstrapBackups.SUPB[].SignatureOK`, `BootstrapBackups.SUPB[].Used`, `BootstrapBackups.VBR.Backup.ChecksumComputed`, `BootstrapBackups.VBR.Backup.ChecksumStored`, `BootstrapBackups.VBR.ByteOffset`, `BootstrapBackups.VBR.PrimaryChecksumComputed`, `BootstrapBackups.VBR.PrimaryChecksumStored`, `CheckpointFlags`, `CheckpointSHA256Bytes`, `ChecksumSelectorNote`, `ContainerSizeFrom`, `CountsUnreadable`, `FSMetadata.Children[].FileID`, `FSMetadata.Children[].Name`, `FSMetadata.Children[].StreamCount`, `FileNames`, `FilesAccessedAfterChange`, `ImageTail`, `ImageTail.AfterPartitionBytes`, `ImageTail.Bytes`, `ImageTail.InPartitionBytes`, `ImageTail.PartitionEntry`, `MLog`, `MLog.ControlCopyPLCN`, `MLog.ControlCopySlot`, `MLog.ControlCopyVerifies`, `MLog.EarlierLogRecords`, `MLog.LogBlocks`, `MLog.LogEnd`, `MLog.LogStart`, `MLog.LogVersion`, `MLog.NewestRecordsMissing`, `MLog.Read`, `MLog.Statements`, `RedundancyFindings`, `RedundancyNotes`, `ReparseFiles`, `Residency`, `SUPBUsedLCN`.

### `fastsummary`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `bootstrap_backups` | `BootstrapBackups` |  |
| `bootstrap_backups.checkpoint_authoritative_unusable` | `BootstrapBackups.CheckpointAuthoritativeUnusable` |  |
| `bootstrap_backups.checkpoint_selected_via_fallback` | `BootstrapBackups.CheckpointSelectedViaFallback` |  |
| `bootstrap_backups.checkpoint_tie` | `BootstrapBackups.CheckpointTie` |  |
| `bootstrap_backups.checkpoint_used_lcn` | `BootstrapBackups.CheckpointUsedLCN` |  |
| `bootstrap_backups.checkpoints` | `BootstrapBackups.Checkpoints` |  |
| `bootstrap_backups.checkpoints[].alloc_clock` | `BootstrapBackups.Checkpoints[].AllocClock` |  |
| `bootstrap_backups.checkpoints[].ckname` | `BootstrapBackups.Checkpoints[].ChecksumName` |  |
| `bootstrap_backups.checkpoints[].cksum_ok` | `BootstrapBackups.Checkpoints[].ChecksumOK` |  |
| `bootstrap_backups.checkpoints[].clock_divergence` | `BootstrapBackups.Checkpoints[].ClockDivergence` |  |
| `bootstrap_backups.checkpoints[].lcn` | `BootstrapBackups.Checkpoints[].LCN` |  |
| `bootstrap_backups.checkpoints[].lsn` | `BootstrapBackups.Checkpoints[].LSN` |  |
| `bootstrap_backups.checkpoints[].role` | `BootstrapBackups.Checkpoints[].Role` |  |
| `bootstrap_backups.checkpoints[].roots_ok` | `BootstrapBackups.Checkpoints[].RootsOK` |  |
| `bootstrap_backups.checkpoints[].self_lcn` | `BootstrapBackups.Checkpoints[].SelfLCN` |  |
| `bootstrap_backups.checkpoints[].self_lcn_ok` | `BootstrapBackups.Checkpoints[].SelfLCNOK` |  |
| `bootstrap_backups.checkpoints[].sha256` | `BootstrapBackups.Checkpoints[].SHA256` |  |
| `bootstrap_backups.checkpoints[].sig_ok` | `BootstrapBackups.Checkpoints[].SignatureOK` |  |
| `bootstrap_backups.checkpoints[].tied_clock` | `BootstrapBackups.Checkpoints[].TiedClock` |  |
| `bootstrap_backups.checkpoints[].vc` | `BootstrapBackups.Checkpoints[].VirtualClock` |  |
| `bootstrap_backups.checkpoints[].vc_page` | `BootstrapBackups.Checkpoints[].VirtualClockPage` |  |
| `bootstrap_backups.supb` | `BootstrapBackups.SUPB` |  |
| `bootstrap_backups.supb[].ckname` | `BootstrapBackups.SUPB[].ChecksumName` |  |
| `bootstrap_backups.supb[].cksum_ok` | `BootstrapBackups.SUPB[].ChecksumOK` |  |
| `bootstrap_backups.supb[].lcn` | `BootstrapBackups.SUPB[].LCN` |  |
| `bootstrap_backups.supb[].ok` | `BootstrapBackups.SUPB[].OK` |  |
| `bootstrap_backups.supb[].role` | `BootstrapBackups.SUPB[].Role` |  |
| `bootstrap_backups.supb[].self_lcn` | `BootstrapBackups.SUPB[].SelfLCN` |  |
| `bootstrap_backups.supb[].self_lcn_ok` | `BootstrapBackups.SUPB[].SelfLCNOK` |  |
| `bootstrap_backups.supb[].sha256` | `BootstrapBackups.SUPB[].SHA256` |  |
| `bootstrap_backups.vbr` | `BootstrapBackups.VBR` |  |
| `bootstrap_backups.vbr.backup` | `BootstrapBackups.VBR.Backup` |  |
| `bootstrap_backups.vbr.backup.byte_offset` | `BootstrapBackups.VBR.Backup.ByteOffset` |  |
| `bootstrap_backups.vbr.backup.cksum_ok` | `BootstrapBackups.VBR.Backup.ChecksumOK` |  |
| `bootstrap_backups.vbr.backup.lba` | `BootstrapBackups.VBR.Backup.LBA` |  |
| `bootstrap_backups.vbr.backup.matches_primary` | `BootstrapBackups.VBR.Backup.MatchesPrimary` |  |
| `bootstrap_backups.vbr.backup.present` | `BootstrapBackups.VBR.Backup.Present` |  |
| `bootstrap_backups.vbr.backup.primary_version` | `BootstrapBackups.VBR.Backup.PrimaryVersion` |  |
| `bootstrap_backups.vbr.backup.sha256` | `BootstrapBackups.VBR.Backup.SHA256` |  |
| `bootstrap_backups.vbr.backup.version` | `BootstrapBackups.VBR.Backup.Version` |  |
| `bootstrap_backups.vbr.primary_cksum_ok` | `BootstrapBackups.VBR.PrimaryChecksumOK` |  |
| `bootstrap_backups.vbr.primary_ok` | `BootstrapBackups.VBR.PrimaryOK` |  |
| `bootstrap_backups.vbr.sector_size` | `BootstrapBackups.VBR.SectorSize` |  |
| `bootstrap_backups.vbr.total_sectors` | `BootstrapBackups.VBR.TotalSectors` |  |
| `capacity` | `Capacity` |  |
| `capacity.allocator_covered_bytes` | `Capacity.AllocatorCoveredBytes` |  |
| `capacity.free` | (removed) | a display string (Capacity.NotAllocatedBytes is the number) |
| `capacity.free_bytes` | (removed) | the same number as Capacity.NotAllocatedBytes |
| `capacity.not_allocated` | (removed) | a display string (Capacity.NotAllocatedBytes) |
| `capacity.not_allocated_bytes` | `Capacity.NotAllocatedBytes` |  |
| `capacity.outside_allocator_bytes` | `Capacity.OutsideAllocatorBytes` |  |
| `capacity.source` | `Capacity.Source` |  |
| `capacity.used` | (removed) | a display string (Capacity.UsedBytes) |
| `capacity.used_bytes` | `Capacity.UsedBytes` |  |
| `capacity.used_pct` | `Capacity.UsedPercent` |  |
| `capacity.volume_bytes` | `Capacity.VolumeBytes` |  |
| `checkpoint_flags` | `CheckpointFlagsHex` | the word in hex; CheckpointFlags now holds the names |
| `checkpoint_vc` | `CheckpointVirtualClock` |  |
| `checksum` | `Checksum` |  |
| `chkp_sha256` | `CHKPSHA256` |  |
| `cluster_size` | `ClusterSize` |  |
| `container_size` | `ContainerSize` |  |
| `containers_free` | `ContainersMappedBootRegion` | the rows that map the boot region; not free space |
| `containers_mapped` | `ContainersMapped` |  |
| `containers_used` | `ContainersMappedNonBoot` | the Container Table rows other than the boot region's; not usage |
| `driver_note` | `DriverNote` |  |
| `driver_version` | `DriverVersion` |  |
| `fs_metadata` | `FSMetadata` |  |
| `fs_metadata.children` | `FSMetadata.Children` |  |
| `fs_metadata.rows` | `FSMetadata.Rows` |  |
| `fs_metadata.usn_journal` | `FSMetadata.USNJournal` |  |
| `image` | `Image` |  |
| `image_size` | `ImageSize` |  |
| `objects` | `ObjectCount` |  |
| `partition_start` | `PartitionStart` |  |
| `refs_version` | `ReFSVersion` |  |
| `reparse_index_entries` | `ReparseIndexEntries` |  |
| `root_table_rows` | `RootTableRows` |  |
| `root_table_rows{*}` | `RootTableRows{*}` |  |
| `root_tables_unreadable` | `RootTablesUnreadable` |  |
| `security_descriptors` | `SecurityDescriptors` |  |
| `summary_mode` | `SummaryMode` |  |
| `supb_sha256` | `SUPBSHA256` |  |
| `tool` | `Tool` |  |
| `trash_table_entries` | `TrashTableEntries` |  |
| `utilization_pct` | (removed) | the mapped-container count as a percentage; the usage is Capacity.UsedPercent |
| `vbr_sha256` | `VBRSHA256` |  |
| `volume_create_time` | `VolumeCreateTime` |  |
| `volume_guid` | `VolumeGUID` |  |
| `volume_label` | `VolumeLabel` |  |
| `volume_modify_time` | `VolumeLastWritableMountTime` | the last mount that could write |
| `volume_serial` | `VolumeSerial` |  |
| `volume_size` | `VolumeSize` |  |
| `volume_size_bytes` | `VolumeSize` |  |
| `volume_state` | `VolumeState` |  |
| `volume_version` | `VolumeVersion` |  |

New in 1.14.0: `BootstrapBackups.CheckpointFindings`, `BootstrapBackups.Checkpoints[].ByteOffset`, `BootstrapBackups.Checkpoints[].InUse`, `BootstrapBackups.Checkpoints[].RootFail`, `BootstrapBackups.Checkpoints[].RootUnchecked`, `BootstrapBackups.Checkpoints[].SHA256Bytes`, `BootstrapBackups.Checkpoints[].Use`, `BootstrapBackups.SUPB[].ByteOffset`, `BootstrapBackups.SUPB[].PayloadMatches`, `BootstrapBackups.SUPB[].SignatureOK`, `BootstrapBackups.SUPB[].Used`, `BootstrapBackups.VBR.Backup.ChecksumComputed`, `BootstrapBackups.VBR.Backup.ChecksumStored`, `BootstrapBackups.VBR.ByteOffset`, `BootstrapBackups.VBR.PrimaryChecksumComputed`, `BootstrapBackups.VBR.PrimaryChecksumStored`, `CheckpointFlags`, `CheckpointSHA256Bytes`, `ChecksumSelectorNote`, `ContainerSizeFrom`, `CountsUnreadable`, `FSMetadata.Children[].FileID`, `FSMetadata.Children[].Name`, `FSMetadata.Children[].StreamCount`, `ImageTail`, `ImageTail.AfterPartitionBytes`, `ImageTail.Bytes`, `ImageTail.InPartitionBytes`, `ImageTail.PartitionEntry`, `MLog`, `RedundancyFindings`, `RedundancyNotes`, `SUPBUsedLCN`.

### `integrity`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `checkpoint_vc` | `CheckpointVirtualClock` |  |
| `checksum_type` | `Checksum` | summary's name |
| `checksum_verification` | `ChecksumVerification` |  |
| `clean` | `Clean` |  |
| `cluster_size` | `ClusterSize` |  |
| `container_map_entries` | `ContainersMapped` | summary's name |
| `coverage_complete` | `CoverageComplete` |  |
| `image` | `Image` |  |
| `issues` | `Issues` |  |
| `page_statistics` | `PageStatistics` |  |
| `page_statistics.btree_inner_ok` | `PageStatistics.BTreeInnerOK` |  |
| `page_statistics.btree_leaf_ok` | `PageStatistics.BTreeLeafOK` |  |
| `page_statistics.btree_struct_error` | `PageStatistics.BTreeStructError` |  |
| `page_statistics.page_references` | `PageStatistics.PageReferences` |  |
| `page_statistics.pages_checked` | `PageStatistics.PagesChecked` |  |
| `page_statistics.pages_invalid_sig` | `PageStatistics.PagesInvalidSignature` |  |
| `page_statistics.pages_selfaddr_bad` | `PageStatistics.PagesSelfAddressBad` |  |
| `page_statistics.pages_selfaddr_ok` | `PageStatistics.PagesSelfAddressOK` |  |
| `page_statistics.pages_valid_sig` | `PageStatistics.PagesValidSignature` |  |
| `page_statistics.pages_vc_exceed` | `PageStatistics.PagesVirtualClockExceed` |  |
| `page_statistics.pages_vc_ok` | `PageStatistics.PagesVirtualClockOK` |  |
| `page_statistics.pages_volsig_match` | `PageStatistics.PagesVolumeSignatureMatch` |  |
| `page_statistics.pages_volsig_mismatch` | `PageStatistics.PagesVolumeSignatureMismatch` |  |
| `redundancy` | (removed) | its parts are BootstrapBackups, RedundancyFindings, RedundancyNotes |
| `redundancy.backup_copies` | `BootstrapBackups` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoint_authoritative_unusable` | `BootstrapBackups.CheckpointAuthoritativeUnusable` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoint_selected_via_fallback` | `BootstrapBackups.CheckpointSelectedViaFallback` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoint_tie` | `BootstrapBackups.CheckpointTie` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoint_used_lcn` | `BootstrapBackups.CheckpointUsedLCN` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints` | `BootstrapBackups.Checkpoints` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].alloc_clock` | `BootstrapBackups.Checkpoints[].AllocClock` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].ckname` | `BootstrapBackups.Checkpoints[].ChecksumName` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].cksum_ok` | `BootstrapBackups.Checkpoints[].ChecksumOK` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].clock_divergence` | `BootstrapBackups.Checkpoints[].ClockDivergence` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].lcn` | `BootstrapBackups.Checkpoints[].LCN` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].lsn` | `BootstrapBackups.Checkpoints[].LSN` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].role` | `BootstrapBackups.Checkpoints[].Role` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].roots_ok` | `BootstrapBackups.Checkpoints[].RootsOK` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].self_lcn` | `BootstrapBackups.Checkpoints[].SelfLCN` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].self_lcn_ok` | `BootstrapBackups.Checkpoints[].SelfLCNOK` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].sha256` | `BootstrapBackups.Checkpoints[].SHA256` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].sig_ok` | `BootstrapBackups.Checkpoints[].SignatureOK` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].tied_clock` | `BootstrapBackups.Checkpoints[].TiedClock` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].vc` | `BootstrapBackups.Checkpoints[].VirtualClock` | the copies, under summary's name |
| `redundancy.backup_copies.checkpoints[].vc_page` | `BootstrapBackups.Checkpoints[].VirtualClockPage` | the copies, under summary's name |
| `redundancy.backup_copies.supb` | `BootstrapBackups.SUPB` | the copies, under summary's name |
| `redundancy.backup_copies.supb[].ckname` | `BootstrapBackups.SUPB[].ChecksumName` | the copies, under summary's name |
| `redundancy.backup_copies.supb[].cksum_ok` | `BootstrapBackups.SUPB[].ChecksumOK` | the copies, under summary's name |
| `redundancy.backup_copies.supb[].lcn` | `BootstrapBackups.SUPB[].LCN` | the copies, under summary's name |
| `redundancy.backup_copies.supb[].ok` | `BootstrapBackups.SUPB[].OK` | the copies, under summary's name |
| `redundancy.backup_copies.supb[].role` | `BootstrapBackups.SUPB[].Role` | the copies, under summary's name |
| `redundancy.backup_copies.supb[].self_lcn` | `BootstrapBackups.SUPB[].SelfLCN` | the copies, under summary's name |
| `redundancy.backup_copies.supb[].self_lcn_ok` | `BootstrapBackups.SUPB[].SelfLCNOK` | the copies, under summary's name |
| `redundancy.backup_copies.supb[].sha256` | `BootstrapBackups.SUPB[].SHA256` | the copies, under summary's name |
| `redundancy.backup_copies.vbr` | `BootstrapBackups.VBR` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.backup` | `BootstrapBackups.VBR.Backup` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.backup.byte_offset` | `BootstrapBackups.VBR.Backup.ByteOffset` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.backup.cksum_ok` | `BootstrapBackups.VBR.Backup.ChecksumOK` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.backup.lba` | `BootstrapBackups.VBR.Backup.LBA` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.backup.matches_primary` | `BootstrapBackups.VBR.Backup.MatchesPrimary` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.backup.present` | `BootstrapBackups.VBR.Backup.Present` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.backup.primary_version` | `BootstrapBackups.VBR.Backup.PrimaryVersion` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.backup.sha256` | `BootstrapBackups.VBR.Backup.SHA256` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.backup.version` | `BootstrapBackups.VBR.Backup.Version` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.primary_cksum_ok` | `BootstrapBackups.VBR.PrimaryChecksumOK` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.primary_ok` | `BootstrapBackups.VBR.PrimaryOK` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.sector_size` | `BootstrapBackups.VBR.SectorSize` | the copies, under summary's name |
| `redundancy.backup_copies.vbr.total_sectors` | `BootstrapBackups.VBR.TotalSectors` | the copies, under summary's name |
| `redundancy.notes` | `RedundancyNotes` | moved to the top level |
| `redundancy.warnings` | `RedundancyFindings` | the findings, under summary's name |
| `refs_version` | `ReFSVersion` |  |
| `verdict` | `Verdict` |  |
| `volume_sig` | `VolumeSignature` |  |

New in 1.14.0: `BootstrapBackups.CheckpointFindings`, `BootstrapBackups.Checkpoints[].ByteOffset`, `BootstrapBackups.Checkpoints[].InUse`, `BootstrapBackups.Checkpoints[].RootFail`, `BootstrapBackups.Checkpoints[].RootUnchecked`, `BootstrapBackups.Checkpoints[].SHA256Bytes`, `BootstrapBackups.Checkpoints[].Use`, `BootstrapBackups.SUPB[].ByteOffset`, `BootstrapBackups.SUPB[].PayloadMatches`, `BootstrapBackups.SUPB[].SignatureOK`, `BootstrapBackups.SUPB[].Used`, `BootstrapBackups.VBR.Backup.ChecksumComputed`, `BootstrapBackups.VBR.Backup.ChecksumStored`, `BootstrapBackups.VBR.ByteOffset`, `BootstrapBackups.VBR.PrimaryChecksumComputed`, `BootstrapBackups.VBR.PrimaryChecksumStored`, `ChecksumSelectorNote`, `IntegrityStreams`.

### `usn`

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `attrs` | `FileAttributes` | the names |
| `attrs_hex` | `FileAttributesHex` | the word in hex |
| `entry_type` | `IsDirectory` | dir / file -> true / false |
| `file_id` | `FileID` |  |
| `file_ref` | `ObjectRef` |  |
| `filename` | `FileName` |  |
| `home_oid` | `HomeOID` |  |
| `parent_idx` | `ParentFileID` | the parent's FileID |
| `parent_oid` | `ParentOID` |  |
| `path` | `FullPath` |  |
| `reason` | `Reason` |  |
| `reason_hex` | `ReasonHex` |  |
| `record_length` | `RecordLength` |  |
| `security_id` | `SecurityId` |  |
| `source_info` | `SourceInfo` |  |
| `timestamp` | `Timestamp` |  |
| `usn` | `USN` |  |

New in 1.14.0: `SourceInfoHex`, `StreamOffset`.

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `journal` | `Journal` |  |
| `journal.allocation_delta` | `Journal.AllocationDelta` |  |
| `journal.journal_id` | `Journal.JournalID` |  |
| `journal.max_params_offset` | `Journal.MaxParamsOffset` |  |
| `journal.max_resident` | `Journal.MaxResident` |  |
| `journal.max_size` | `Journal.MaxSize` |  |
| `journal.meta_field_0x00` | `Journal.MetaField0x00` |  |
| `journal.meta_field_0x08` | `Journal.MetaField0x08` |  |
| `journal.meta_field_0x10` | `Journal.MetaField0x10` |  |
| `journal.meta_field_0x18` | `Journal.MetaField0x18` |  |
| `journal.metadata_size` | `Journal.MetadataSize` |  |
| `record_count` | `RecordCount` |  |
| `records` | `Records` |  |
| `records[].entry_type` | `Records[].IsDirectory` | dir / file -> true / false |
| `records[].file_attrs` | `Records[].FileAttributesHex` | the number; FileAttributes now holds the names |
| `records[].file_id` | `Records[].FileID` |  |
| `records[].file_ref` | `Records[].ObjectRef` |  |
| `records[].filename` | `Records[].FileName` |  |
| `records[].home_oid` | `Records[].HomeOID` |  |
| `records[].parent_idx` | `Records[].ParentFileID` | the parent's FileID |
| `records[].parent_oid` | `Records[].ParentOID` |  |
| `records[].path` | `Records[].FullPath` |  |
| `records[].reason` | `Records[].ReasonHex` | the number; Reason now holds the names |
| `records[].reason_text` | `Records[].Reason` | the names |
| `records[].record_length` | `Records[].RecordLength` |  |
| `records[].security_id` | `Records[].SecurityId` |  |
| `records[].source_info` | `Records[].SourceInfoHex` | the number; SourceInfo now holds the names |
| `records[].timestamp` | `Records[].Timestamp` |  |
| `records[].usn` | `Records[].USN` |  |

New in 1.14.0: `Journal.ChangeJournalEntry`, `Journal.ChangeJournalEntry.Created`, `Journal.ChangeJournalEntry.StreamCount`, `Journal.ChangeJournalEntry.ValueSize`, `Journal.JAllocatedSize`, `Journal.JDeclared`, `Journal.JDeclared.AllocatedSize`, `Journal.JDeclared.DiskAllocation`, `Journal.JDeclared.Size`, `Journal.JDeclared.ValidDataLength`, `Journal.JDeclaredMismatch`, `Journal.JRuns`, `Journal.JRuns[].Clusters`, `Journal.JRuns[].FileVCN`, `Journal.JRuns[].PLCN`, `Journal.JRuns[].VLCN`, `Records[].FileAttributes`, `Records[].SourceInfo`, `Records[].StreamOffset`.

### `mlog`

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `action` | `DerivedAction` | derived from the records, not read |
| `name` | `Name` |  |
| `oid` | `OID` |  |
| `opcodes` | `Opcodes` |  |
| `path` | `PathToday` | the path in the live tree now, not at the event |
| `plcn` | `PLCN` |  |
| `record_count` | `RecordCount` |  |
| `seq` | `Seq` |  |
| `timestamp` | `Timestamp` |  |

New in 1.14.0: `Block`, `OpcodesHex`, `ParentPathToday`, `TimeSource`.

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `control` | `Control` |  |
| `control.ctrl_uuid` | (removed) | there is no UUID at +0x50; the log instance's UUID is Control.PayloadUUID (+0x28) |
| `control.data_end_lcn` | `Control.DataEndBlock` | a block number, not an LCN |
| `control.data_start_lcn` | `Control.DataStartBlock` | a block number, not an LCN |
| `control.entry_header_offset` | `Control.EntryHeaderOffset` |  |
| `control.flags` | `Control.Flags` |  |
| `control.format_magic` | `Control.FormatMagic` |  |
| `control.generation` | `Control.LogEnd` | +0x20 is the log end; 1.13.1 kept its low 32 bits |
| `control.lsn_oldest` | `Control.LogStart` | +0x18 is the log start |
| `control.payload_offset` | `Control.PayloadOffset` |  |
| `control.payload_size` | `Control.PayloadSize` |  |
| `control.plcn` | `Control.PLCN` |  |
| `control.sector_size` | `Control.LogBlockSize` | the log block size at header +0x0C |
| `control.sequence` | `Control.Sequence` |  |
| `control.sequence_raw` | `Control.HeaderLogOpenCount` | the header's +0x20 carries the log open count |
| `control.signature` | `Control.Signature` |  |
| `control.total_entries` | (removed) | there is no entry count at +0x48; +0x44 is Control.HostInfo |
| `control.uuid` | `Control.UUID` |  |
| `control.version` | (removed) | the header word at +0x08 is written as 1 and read by nothing; in Control.HeaderUndecodedBytes |
| `control.write_counter` | `Control.LogOpenCount` | +0x38 is the log open count |
| `data_area` | `DataArea` |  |
| `data_area.page_types` | `DataArea.PageTypes` |  |
| `data_area.page_types.data` | `DataArea.PageTypes[].PageType`, `DataArea.PageTypes[].LogBlocks` | as above |
| `data_area.page_types.MLog` | `DataArea.PageTypes[].PageType`, `DataArea.PageTypes[].LogBlocks` | a page type is a value: one row per type |
| `data_area.page_types.zero` | `DataArea.PageTypes[].PageType`, `DataArea.PageTypes[].LogBlocks` | as above |
| `data_area.total_pages` | `DataArea.LogBlocks` | the 4 KiB log blocks (a metadata page is 16 or 64 KiB) |
| `integrity` | `Integrity` |  |
| `integrity.checked` | `Integrity.Checked` |  |
| `integrity.failed` | `Integrity.Failed` |  |
| `integrity.failures` | `Integrity.Failures` |  |
| `integrity.failures_truncated` | `Integrity.FailuresTruncated` |  |
| `integrity.verified` | `Integrity.Verified` |  |
| `mlog_info` | `MLogInfo` |  |
| `mlog_info.ctrl_plcn_0` | `MLogInfo.ControlPLCN0` | renamed |
| `mlog_info.ctrl_plcn_1` | `MLogInfo.ControlPLCN1` | renamed |
| `mlog_info.data_end_lcn` | `MLogInfo.DataEndLCN` |  |
| `mlog_info.data_size_clusters` | `MLogInfo.DataSizeClusters` |  |
| `mlog_info.data_start_lcn` | `MLogInfo.DataStartLCN` |  |
| `mlog_info.oid` | `MLogInfo.OID` |  |
| `mlog_info.rows` | `MLogInfo.Rows` |  |
| `mlog_info.table_name` | `MLogInfo.TableName` |  |
| `records` | `Records` |  |
| `records[].block` | `Records[].Block` |  |
| `records[].block_lcn` | `Records[].BlockIndex` | a block index, not an LCN |
| `records[].flags` | `Records[].FlagsHex` | the number; Flags now holds the names |
| `records[].object_id` | `Records[].AllocatorClock` | the record's +0x20, the allocator clock, in decimal, not an object id; the table's object id is TargetOID |
| `records[].offset` | `Records[].RecordOffset` | renamed |
| `records[].op_name` | `Records[].OpName` |  |
| `records[].opcode` | `Records[].Opcode` |  |
| `records[].page_type` | `Records[].PageType` |  |
| `records[].plcn` | `Records[].PLCN` |  |
| `records[].redo_block` | `Records[].RedoBlock` |  |
| `records[].size` | `Records[].Size` |  |
| `records[].table_path_len` | `Records[].TablePathLen` | renamed |
| `records[].txn_commit` | `Records[].TxnCommit` |  |
| `records[].txn_start` | `Records[].TxnStart` |  |
| `records[].vlcn` | (removed) | it held the PLCN, a duplicate of PLCN |
| `version` | `ReFSVersion` | the volume's format version |

New in 1.14.0: `Control.HeaderUndecodedBytes`, `Control.HeaderUndecodedBytes[].Bytes`, `Control.HeaderUndecodedBytes[].Length`, `Control.HeaderUndecodedBytes[].Offset`, `Control.HostInfo`, `Control.LogVersion`, `Control.PayloadUUID`, `Control.Slot`, `Control.UndecodedBytes`, `ControlCopies`, `ControlCopies[].Computed`, `ControlCopies[].InUse`, `ControlCopies[].IntegrityVerified`, `ControlCopies[].PLCN`, `ControlCopies[].Sequence`, `ControlCopies[].Slot`, `ControlCopies[].Stored`, `DataArea.EarlierLogRecords`, `EarlierLogs`, `LogInstance`, `LogInstance.FormatMagic`, `LogInstance.UUID`, `Records[].Flags`, `Records[].InheritedTableOID`, `Records[].Key`, `Records[].Mnemonic`, `Records[].TargetOID`, `Records[].Time`, `Transactions`, `Transactions[].Block`, `Transactions[].DerivedAction`, `Transactions[].Entries`, `Transactions[].Entries.Added`, `Transactions[].Entries.Added[].Name`, `Transactions[].Entries.Added[].ParentOID`, `Transactions[].Entries.Pairs`, `Transactions[].Entries.Pairs[].Kind`, `Transactions[].Entries.Pairs[].NewName`, `Transactions[].Entries.Pairs[].NewParentOID`, `Transactions[].Entries.Pairs[].OldName`, `Transactions[].Entries.Pairs[].OldParentOID`, `Transactions[].Entries.Removed`, `Transactions[].Entries.Removed[].Name`, `Transactions[].Entries.Removed[].ParentOID`, `Transactions[].FirstRecordIndex`, `Transactions[].Name`, `Transactions[].OID`, `Transactions[].Opcodes`, `Transactions[].OpcodesHex`, `Transactions[].PLCN`, `Transactions[].ParentPathToday`, `Transactions[].PathToday`, `Transactions[].RecordCount`, `Transactions[].Seq`, `Transactions[].TimeSource`, `Transactions[].Timestamp`, `View`.

### `security`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `security_descriptors` | `SecurityDescriptors` |  |
| `security_descriptors[].computed_hash` | `SecurityDescriptors[].ComputedHash` |  |
| `security_descriptors[].control` | `SecurityDescriptors[].ControlHex` | the number; Control now holds the names |
| `security_descriptors[].control_flags` | `SecurityDescriptors[].Control` | the names |
| `security_descriptors[].dacl` | `SecurityDescriptors[].DACL` |  |
| `security_descriptors[].dacl[].flags` | `SecurityDescriptors[].DACL[].FlagsHex` | the number; Flags now holds the names |
| `security_descriptors[].dacl[].mask` | `SecurityDescriptors[].DACL[].MaskHex` | the number; Mask now holds the names |
| `security_descriptors[].dacl[].mask_str` | `SecurityDescriptors[].DACL[].Mask` | the names |
| `security_descriptors[].dacl[].sid` | `SecurityDescriptors[].DACL[].SID` |  |
| `security_descriptors[].dacl[].sid_name` | `SecurityDescriptors[].DACL[].SIDName` |  |
| `security_descriptors[].dacl[].size` | `SecurityDescriptors[].DACL[].Size` |  |
| `security_descriptors[].dacl[].type` | `SecurityDescriptors[].DACL[].Type` |  |
| `security_descriptors[].dacl[].type_id` | `SecurityDescriptors[].DACL[].TypeID` |  |
| `security_descriptors[].generation` | `SecurityDescriptors[].Generation` |  |
| `security_descriptors[].group` | `SecurityDescriptors[].GroupSid` | as above |
| `security_descriptors[].group_name` | `SecurityDescriptors[].GroupSid` | as above |
| `security_descriptors[].hash_valid` | `SecurityDescriptors[].HashValid` |  |
| `security_descriptors[].key_hex` | `SecurityDescriptors[].KeyHex` |  |
| `security_descriptors[].key_len` | `SecurityDescriptors[].KeyLength` |  |
| `security_descriptors[].owner` | `SecurityDescriptors[].OwnerSid` | the SID with its name, in one field |
| `security_descriptors[].owner_name` | `SecurityDescriptors[].OwnerSid` | as above |
| `security_descriptors[].revision` | `SecurityDescriptors[].Revision` |  |
| `security_descriptors[].sacl` | `SecurityDescriptors[].SACL` |  |
| `security_descriptors[].sacl[].flags` | `SecurityDescriptors[].SACL[].FlagsHex` | the number; Flags now holds the names |
| `security_descriptors[].sacl[].mask` | `SecurityDescriptors[].SACL[].MaskHex` | the number; Mask now holds the names |
| `security_descriptors[].sacl[].mask_str` | `SecurityDescriptors[].SACL[].Mask` | the names |
| `security_descriptors[].sacl[].sid` | `SecurityDescriptors[].SACL[].SID` |  |
| `security_descriptors[].sacl[].sid_name` | `SecurityDescriptors[].SACL[].SIDName` |  |
| `security_descriptors[].sacl[].size` | `SecurityDescriptors[].SACL[].Size` |  |
| `security_descriptors[].sacl[].type` | `SecurityDescriptors[].SACL[].Type` |  |
| `security_descriptors[].sacl[].type_id` | `SecurityDescriptors[].SACL[].TypeID` |  |
| `security_descriptors[].sd_hash` | `SecurityDescriptors[].SDHash` |  |
| `security_descriptors[].security_id` | `SecurityDescriptors[].SecurityId` |  |
| `security_descriptors[].size` | `SecurityDescriptors[].Size` |  |

New in 1.14.0: `Damage`, `SecurityDescriptors[].DACL[].Flags`, `SecurityDescriptors[].SACL[].Flags`.

### `specials`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `counts` | `[]` | the counts are rows: Type, Objects, Names |
| `counts{*}` | `[].Type`, `[].Objects`, `[].Names` | a type's count is a row |
| `image` | (removed) | the document is the count table |

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `detail` | (removed) | as above |
| `file_id` | (removed) | as above |
| `home_oid` | (removed) | as above |
| `is_dir` | (removed) | as above |
| `path` | (removed) | specials without a type writes the count table (Type, Objects, Names) in every format; the rows are `specials TYPE` |
| `type` | `Type` |  |

New in 1.14.0: `Names`, `Objects`.

**ads JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `image` | (removed) | the document is the list of rows |
| `specials` | (removed) | the rows are the document (a list) |
| `specials.ads` | `[]` | one row per named stream (ObjectRef, FullPath, Stream, StreamSize, DataResidency ...); 1.13.1 listed paths |

New in 1.14.0: `[].DataResidency`, `[].FullPath`, `[].IsDirectory`, `[].ObjectRef`, `[].Stream`, `[].StreamSize`, `[].Type`.

**hardlink JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `image` | (removed) | the document is the list of rows |
| `specials` | (removed) | the rows are the document (a list) |
| `specials.hardlink` | `[]` | one row per file (ObjectRef, FullPath, HardLinkCount, HardLinkNames ...); 1.13.1 listed paths |

New in 1.14.0: `[].FullPath`, `[].HardLinkCount`, `[].HardLinkNames`, `[].IsDirectory`, `[].ObjectRef`, `[].Type`.

**reparse JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `image` | (removed) | the document is the list of rows |
| `specials` | (removed) | the rows are the document (a list) |
| `specials.reparse` | `[]` | one row per file (ObjectRef, FullPath, ReparseTag, ReparseTarget ...); 1.13.1 listed paths |

New in 1.14.0: `[].FullPath`, `[].IsDirectory`, `[].ObjectRef`, `[].ReparseTag`, `[].ReparseTagHex`, `[].ReparseTarget`, `[].Type`.

**hardlink CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `detail` | (removed) | its facts are columns (HardLinkCount, HardLinkNames, StreamSize, ReparseTag ...) |
| `file_id` | `ObjectRef` | HomeOID:FileID in one column |
| `home_oid` | `ObjectRef` | HomeOID:FileID in one column |
| `is_dir` | `IsDirectory` |  |
| `path` | `FullPath` |  |
| `type` | `Type` |  |

New in 1.14.0: `AllocatedSize`, `DataResidency`, `FileSize`, `HardLinkCount`, `HardLinkNames`, `ReparseTag`, `ReparseTagHex`, `ReparseTarget`, `SnapshotCount`, `Stream`, `StreamSize`.

### `ads`

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `detail` | (removed) | its facts are columns (Stream, StreamSize, DataResidency ...) |
| `file_id` | `ObjectRef` | HomeOID:FileID in one column |
| `home_oid` | `ObjectRef` | HomeOID:FileID in one column |
| `is_dir` | `IsDirectory` |  |
| `path` | `FullPath` |  |
| `type` | `Type` |  |

New in 1.14.0: `AllocatedSize`, `DataResidency`, `FileSize`, `HardLinkCount`, `HardLinkNames`, `ReparseTag`, `ReparseTagHex`, `ReparseTarget`, `SnapshotCount`, `Stream`, `StreamSize`.

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `image` | (removed) | the document is the list of rows |
| `specials` | (removed) | the rows are the document (a list) |
| `specials.ads` | `[]` | one row per named stream; 1.13.1 listed paths |

New in 1.14.0: `[].DataResidency`, `[].FullPath`, `[].IsDirectory`, `[].ObjectRef`, `[].Stream`, `[].StreamSize`, `[].Type`.

### `reparse`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `reparse_points` | `ReparsePoints` |  |
| `reparse_points[].file_attrs` | `ReparsePoints[].FileAttributesHex` | the number; FileAttributes now holds the names |
| `reparse_points[].has_reparse` | (removed) | true on every row of the list |
| `reparse_points[].is_dir` | `ReparsePoints[].IsDirectory` |  |
| `reparse_points[].name` | `ReparsePoints[].FullPath` | the file's path |
| `reparse_points[].reparse_data` | `ReparsePoints[].ReparseData` |  |
| `reparse_points[].reparse_data.data_len` | `ReparsePoints[].ReparseData.DataLength` |  |
| `reparse_points[].reparse_data.flags` | `ReparsePoints[].ReparseData.FlagsHex` | the number; Flags now holds the names |
| `reparse_points[].reparse_data.print_name` | `ReparsePoints[].ReparseData.PrintName` |  |
| `reparse_points[].reparse_data.relative` | `ReparsePoints[].ReparseData.Relative` |  |
| `reparse_points[].reparse_data.substitute_name` | `ReparsePoints[].ReparseData.SubstituteName` |  |
| `reparse_points[].reparse_data.tag` | (removed) | the tag is the row's ReparseTag / ReparseTagHex |
| `reparse_points[].reparse_data.tag_name` | `ReparsePoints[].ReparseTag` | the tag's name, once per row (1.13.1 also wrote it inside reparse_data) |
| `reparse_points[].reparse_tag_value` | `ReparsePoints[].ReparseTagHex` | the tag word in hex (ReparseTag holds its name) |
| `reparse_points[].reparse_target` | `ReparsePoints[].ReparseTarget` |  |
| `reparse_points[].wsl_eas` | `ReparsePoints[].WSLEAs` |  |

New in 1.14.0: `ReparsePoints[].FileAttributes`, `ReparsePoints[].ObjectRef`, `ReparsePoints[].ReparseData.Flags`, `Summary`, `Summary.Listed`, `Summary.ReparsePointNames`, `Summary.ReparsePointObjects`.

**index JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `reparse_index` | `ReparseIndex` |  |
| `reparse_index[].dir_oid` | `ReparseIndex[].HomeOID` | the file's home directory, not its containing directory |
| `reparse_index[].file_ref_word0` | `ReparseIndex[].FileID` | the FileID half of the reference |
| `reparse_index[].key_hex` | `ReparseIndex[].KeyHex` |  |
| `reparse_index[].marker` | `ReparseIndex[].Marker` |  |
| `reparse_index[].reparse_tag` | `ReparseIndex[].ReparseTagHex` | the number; ReparseTag now holds the name |
| `reparse_index[].tag_name` | `ReparseIndex[].ReparseTag` | the tag's name, now once (ReparseTagHex holds the number) |
| `reparse_index[].value_len` | `ReparseIndex[].ValueLength` |  |

New in 1.14.0: `ReparseIndex[].ObjectRef`.

### `deleted`

**CSV**

Unchanged: `Category`, `Cluster`, `ContentFile`, `Created`, `FileAttributes`, `FileName`, `IsDirectory`, `Modified`, `Recoverability`, `RecoveredChild`, `RecoveredFrom`, `RecoverySource`, `Reliability`.

New in 1.14.0: `Copies`, `CopiesDiffer`, `Dates`, `DatesDiffer`, `FileAttributesHex`, `FormerLocation`, `FoundInTable`, `IdentitySource`, `LiveFile`, `ObjectRef`, `Offset`, `PlausibleTimes`, `PreviousPaths`, `RawKey`, `RawValue`, `SameNameTimeLive`, `Status`.

**JSON**

Unchanged: `[].Category`, `[].Cluster`, `[].ContentFile`, `[].Created`, `[].FileAttributes`, `[].FileName`, `[].IsDirectory`, `[].Modified`, `[].Recoverability`, `[].RecoveredChild`, `[].RecoveredFrom`, `[].RecoverySource`, `[].Reliability`.

New in 1.14.0: `[].Copies`, `[].CopiesDiffer`, `[].Dates`, `[].DatesDiffer`, `[].FileAttributesHex`, `[].FormerLocation`, `[].FoundInTable`, `[].IdentitySource`, `[].LiveFile`, `[].ObjectRef`, `[].Offset`, `[].PlausibleTimes`, `[].PreviousPaths`, `[].RawKey`, `[].RawValue`, `[].SameNameTimeLive`, `[].Status`.

### `recyclebin`

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `decoded` | `Decoded` |  |
| `deletion_time` | `DeletionTime` |  |
| `i_file` | `IFile` |  |
| `original_path` | `OriginalPath` |  |
| `r_file` | `RFile` |  |
| `r_present` | `RFilePresent` |  |
| `sid` | `UserSID` |  |
| `size` | `Size` |  |

### `snapshots`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `cluster_size` | `ClusterSize` |  |
| `files` | `Files` |  |
| `files[].create_time` | `Files[].Created` |  |
| `files[].modify_time` | `Files[].Modified` |  |
| `files[].path` | `Files[].FullPath` |  |
| `files[].resident_bytes` | `Files[].RecordValueBytes` | the name row's value length, which holds the versions; it does not count inline data |
| `files[].snapshots` | `Files[].Snapshots` |  |
| `files[].snapshots[].allocation_size` | `Files[].Snapshots[].ValidDataLength` | the field at +0x28 is the valid data length |
| `files[].snapshots[].name` | `Files[].Snapshots[].Name` |  |
| `files[].snapshots[].snapshot_id` | `Files[].Snapshots[].DataSubID` | the data sub-id at +0x44; there is no snapshot id on disk |
| `files[].snapshots[].stream_size` | `Files[].Snapshots[].StreamSize` |  |
| `files_with_snapshots` | `FilesWithSnapshots` |  |
| `image` | `Image` |  |
| `refs_version` | `ReFSVersion` |  |
| `total_snapshots` | `TotalSnapshots` |  |

New in 1.14.0: `Files[].Snapshots[].AllocatedSize`, `Files[].Snapshots[].CreationTime`.

### `dataruns`

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `clusters` | `Clusters` |  |
| `data_residency` | `DataResidency` |  |
| `extent_count` | `ExtentCount` |  |
| `extents` | `Extents` |  |
| `file_size` | `FileSize` |  |
| `path` | `FullPath` |  |
| `record_placement` | `RecordPlacement` |  |
| `storage` | (removed) | a duplicate of DataResidency |

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `[].clusters` | `[].Clusters` |  |
| `[].data_residency` | `[].DataResidency` |  |
| `[].extent_count` | `[].ExtentCount` |  |
| `[].extents` | `[].Extents` |  |
| `[].file_size` | `[].FileSize` |  |
| `[].path` | `[].FullPath` |  |
| `[].record_placement` | `[].RecordPlacement` |  |
| `[].runs` | `[].Runs` |  |
| `[].runs[].clusters` | `[].Runs[].Clusters` |  |
| `[].runs[].disk_offset` | `[].Runs[].DiskOffset` |  |
| `[].runs[].file_vcn` | `[].Runs[].FileVCN` |  |
| `[].runs[].is_hole` | `[].Runs[].IsHole` |  |
| `[].runs[].plcn` | `[].Runs[].PLCN` |  |
| `[].runs[].vlcn` | `[].Runs[].VLCN` |  |
| `[].storage` | (removed) | a duplicate of DataResidency |

### `timeline`

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `event` | `Event` |  |
| `name` | `Name` |  |
| `oid` | `OID` |  |
| `source` | `Source` |  |
| `timestamp_utc` | `Timestamp` | renamed (the time form says UTC) |

New in 1.14.0: `PathToday`, `TimeSource`.

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `[].event` | `Events[].Event` | the events moved into an envelope: Events, SourceCounts, Statements |
| `[].name` | `Events[].Name` | the events moved into an envelope: Events, SourceCounts, Statements |
| `[].oid` | `Events[].OID` | the events moved into an envelope: Events, SourceCounts, Statements |
| `[].source` | `Events[].Source` | the events moved into an envelope: Events, SourceCounts, Statements |
| `[].timestamp_utc` | `Events[].Timestamp` | the events moved into an envelope: Events, SourceCounts, Statements |

New in 1.14.0: `Events`, `Events[].PathToday`, `Events[].TimeSource`, `MLogRowsUndated`, `SourceCounts`, `SourceCounts{*}`, `Statements`, `USNRecordsRead`.

### `timestomp`

**CSV**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `accessed` | `Accessed` |  |
| `changed` | `Changed` |  |
| `confidence` | `Confidence` |  |
| `created` | `Created` |  |
| `evidence_ref` | `EvidenceRefs` | renamed |
| `modified` | `Modified` |  |
| `path` | `FullPath` |  |
| `signals` | `Signals` |  |
| `storage` | `RecordPlacement`, `DataResidency` | the two axes in two columns |

New in 1.14.0: `Basis`, `ObjectRef`.

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `counts` | `Counts` |  |
| `counts{*}` | `Counts{*}` |  |
| `files_examined` | `FilesExamined` |  |
| `image` | `Image` |  |
| `journal_last_usn` | `JournalLastUSN` |  |
| `journal_present` | `JournalPresent` |  |
| `journal_truncated_bytes` | `JournalTruncatedBytes` |  |
| `refs_version` | `ReFSVersion` |  |
| `suspects` | `Rows` | every row the command writes, not only the flagged ones' name |
| `suspects[].accessed` | `Rows[].Accessed` | moved with suspects |
| `suspects[].changed` | `Rows[].Changed` | moved with suspects |
| `suspects[].created` | `Rows[].Created` | moved with suspects |
| `suspects[].evidence_ref` | `Rows[].EvidenceRefs` | moved with suspects |
| `suspects[].modified` | `Rows[].Modified` | moved with suspects |
| `suspects[].path` | `Rows[].FullPath` | the files name |
| `suspects[].signals` | `Rows[].Signals` | moved with suspects |
| `suspects[].storage` | `Rows[].RecordPlacement`, `Rows[].DataResidency` | the two axes in two fields |
| `suspects[].tier` | `Rows[].Confidence` | moved with suspects |
| `volume_create` | `VolumeCreated` |  |
| `volume_modify` | `VolumeLastWritableMount` | the last mount that could write |

New in 1.14.0: `JournalState`, `Rows[].Basis`, `Rows[].ObjectRef`.

### `export deleted`

**the files it writes**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `holes.json:hole_bytes` | `holes.json:HoleBytes` |  |
| `holes.json:note` | `holes.json:Note` |  |
| `holes.json:refused` | `holes.json:Refused` |  |
| `holes.json:status` | `holes.json:Status` |  |
| `holes.json:streams` | `holes.json:Streams` |  |
| `holes.json:streams_undeterminable` | `holes.json:StreamsUndeterminable` |  |
| `holes.json:streams_with_holes` | `holes.json:StreamsWithHoles` |  |
| `holes.json:undeterminable` | `holes.json:Undeterminable` |  |
| `recovery_manifest.json:entries` | `recovery_manifest.json:Entries` |  |
| `recovery_manifest.json:image` | `recovery_manifest.json:Image` |  |
| `recovery_manifest.json:note` | `recovery_manifest.json:Note` |  |
| `recovery_manifest.json:records` | `recovery_manifest.json:Records` |  |
| `recovery_manifest.json:records[].carved_declared_size` | `recovery_manifest.json:Records[].CarvedDeclaredSize` |  |
| `recovery_manifest.json:records[].carved_len` | `recovery_manifest.json:Records[].CarvedLength` |  |
| `recovery_manifest.json:records[].category` | `recovery_manifest.json:Records[].Category` |  |
| `recovery_manifest.json:records[].confidence` | `recovery_manifest.json:Records[].PlausibleTimes` |  |
| `recovery_manifest.json:records[].confidence_reason` | `recovery_manifest.json:Records[].ConfidenceReason` |  |
| `recovery_manifest.json:records[].content_file` | `recovery_manifest.json:Records[].ContentFile` |  |
| `recovery_manifest.json:records[].declared_size` | `recovery_manifest.json:Records[].DeclaredSize` |  |
| `recovery_manifest.json:records[].decoded_len` | `recovery_manifest.json:Records[].DecodedLength` |  |
| `recovery_manifest.json:records[].hole_runs` | `recovery_manifest.json:Records[].HoleRuns` |  |
| `recovery_manifest.json:records[].is_resident` | (removed) | a duplicate of another key (the command writes it once) |
| `recovery_manifest.json:records[].later_file` | `recovery_manifest.json:Records[].LaterFile` |  |
| `recovery_manifest.json:records[].name` | `recovery_manifest.json:Records[].FileName` |  |
| `recovery_manifest.json:records[].page_off` | `recovery_manifest.json:Records[].Offset` |  |
| `recovery_manifest.json:records[].plcn` | `recovery_manifest.json:Records[].Cluster` |  |
| `recovery_manifest.json:records[].recoverable` | `recovery_manifest.json:Records[].RecoverabilityCode` |  |
| `recovery_manifest.json:records[].refused_all_unwritten` | `recovery_manifest.json:Records[].RefusedAllUnwritten` |  |
| `recovery_manifest.json:records[].reliability` | `recovery_manifest.json:Records[].Reliability` |  |
| `recovery_manifest.json:records[].row_file` | `recovery_manifest.json:Records[].RowFile` |  |
| `recovery_manifest.json:records[].source` | `recovery_manifest.json:Records[].Scan` |  |
| `recovery_manifest.json:records[].tag` | `recovery_manifest.json:Records[].RecoverySource` |  |
| `recovery_manifest.json:records[].unwritten_nonzero_on_disk_bytes` | `recovery_manifest.json:Records[].UnwrittenNonzeroOnDiskBytes` |  |
| `recovery_manifest.json:records[].unwritten_runs` | `recovery_manifest.json:Records[].UnwrittenRuns` |  |
| `recovery_manifest.json:records[].unwritten_zero_filled_bytes` | `recovery_manifest.json:Records[].UnwrittenZeroFilledBytes` |  |
| `recovery_manifest.json:records[].value_len` | `recovery_manifest.json:Records[].ValueLength` |  |
| `recovery_manifest.json:records[].verdict` | `recovery_manifest.json:Records[].Recoverability` |  |

Unchanged: `deleted_files.csv:Category`, `deleted_files.csv:Cluster`, `deleted_files.csv:ContentFile`, `deleted_files.csv:Created`, `deleted_files.csv:FileAttributes`, `deleted_files.csv:FileName`, `deleted_files.csv:IsDirectory`, `deleted_files.csv:Modified`, `deleted_files.csv:Recoverability`, `deleted_files.csv:RecoveredChild`, `deleted_files.csv:RecoveredFrom`, `deleted_files.csv:RecoverySource`, `deleted_files.csv:Reliability`, `deleted_files.json:[].Category`, `deleted_files.json:[].Cluster`, `deleted_files.json:[].ContentFile`, `deleted_files.json:[].Created`, `deleted_files.json:[].FileAttributes`, `deleted_files.json:[].FileName`, `deleted_files.json:[].IsDirectory`, `deleted_files.json:[].Modified`, `deleted_files.json:[].Recoverability`, `deleted_files.json:[].RecoveredChild`, `deleted_files.json:[].RecoveredFrom`, `deleted_files.json:[].RecoverySource`, `deleted_files.json:[].Reliability`.

New in 1.14.0: `deleted_files.csv:Copies`, `deleted_files.csv:CopiesDiffer`, `deleted_files.csv:Dates`, `deleted_files.csv:DatesDiffer`, `deleted_files.csv:FileAttributesHex`, `deleted_files.csv:FormerLocation`, `deleted_files.csv:FoundInTable`, `deleted_files.csv:IdentitySource`, `deleted_files.csv:LiveFile`, `deleted_files.csv:ObjectRef`, `deleted_files.csv:Offset`, `deleted_files.csv:PlausibleTimes`, `deleted_files.csv:PreviousPaths`, `deleted_files.csv:RawKey`, `deleted_files.csv:RawValue`, `deleted_files.csv:RenameReason`, `deleted_files.csv:SHA256`, `deleted_files.csv:SameNameTimeLive`, `deleted_files.csv:Status`, `deleted_files.json:[].Copies`, `deleted_files.json:[].CopiesDiffer`, `deleted_files.json:[].Dates`, `deleted_files.json:[].DatesDiffer`, `deleted_files.json:[].FileAttributesHex`, `deleted_files.json:[].FormerLocation`, `deleted_files.json:[].FoundInTable`, `deleted_files.json:[].IdentitySource`, `deleted_files.json:[].LiveFile`, `deleted_files.json:[].ObjectRef`, `deleted_files.json:[].Offset`, `deleted_files.json:[].PlausibleTimes`, `deleted_files.json:[].PreviousPaths`, `deleted_files.json:[].RawKey`, `deleted_files.json:[].RawValue`, `deleted_files.json:[].RenameReason`, `deleted_files.json:[].SHA256`, `deleted_files.json:[].SameNameTimeLive`, `deleted_files.json:[].Status`, `recovery_manifest.json:Records[].Carve`, `recovery_manifest.json:Records[].ContentConfidence`, `recovery_manifest.json:Records[].Copies`, `recovery_manifest.json:Records[].CopiesDiffer`, `recovery_manifest.json:Records[].Copies[].Cluster`, `recovery_manifest.json:Records[].Copies[].FoundInTable`, `recovery_manifest.json:Records[].Copies[].Offset`, `recovery_manifest.json:Records[].Copies[].RecoveredFrom`, `recovery_manifest.json:Records[].Copies[].RecoverySource`, `recovery_manifest.json:Records[].Copies[].Shown`, `recovery_manifest.json:Records[].Copies[].Times`, `recovery_manifest.json:Records[].Copies[].ValueLength`, `recovery_manifest.json:Records[].Dates`, `recovery_manifest.json:Records[].DatesDiffer`, `recovery_manifest.json:Records[].IdentitySource`, `recovery_manifest.json:Records[].LiveFile`, `recovery_manifest.json:Records[].NoCarveReason`, `recovery_manifest.json:Records[].ObjectRef`, `recovery_manifest.json:Records[].RenameReason`, `recovery_manifest.json:Records[].SHA256`, `recovery_manifest.json:Records[].SameNameTimeLive`, `recovery_manifest.json:Records[].Status`, `recovery_manifest.json:Records[].UnwrittenUncheckedOnDiskBytes`.

### `export metadata`

**the files it writes**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `holes.json:hole_bytes` | `holes.json:HoleBytes` |  |
| `holes.json:note` | `holes.json:Note` |  |
| `holes.json:refused` | `holes.json:Refused` |  |
| `holes.json:status` | `holes.json:Status` |  |
| `holes.json:streams` | `holes.json:Streams` |  |
| `holes.json:streams[].file` | `holes.json:Streams[].File` |  |
| `holes.json:streams[].hole_bytes` | `holes.json:Streams[].HoleBytes` |  |
| `holes.json:streams[].what` | `holes.json:Streams[].What` |  |
| `holes.json:streams_undeterminable` | `holes.json:StreamsUndeterminable` |  |
| `holes.json:streams_with_holes` | `holes.json:StreamsWithHoles` |  |
| `holes.json:undeterminable` | `holes.json:Undeterminable` |  |
| `manifest.json:absent_pages` | `manifest.json:AbsentPages` |  |
| `manifest.json:artifacts` | `manifest.json:Artifacts` |  |
| `manifest.json:artifacts[].bytes` | `manifest.json:Artifacts[].Bytes` |  |
| `manifest.json:artifacts[].file` | `manifest.json:Artifacts[].File` |  |
| `manifest.json:artifacts[].lba` | `manifest.json:Artifacts[].LBA` |  |
| `manifest.json:artifacts[].lcn` | `manifest.json:Artifacts[].LCN` |  |
| `manifest.json:artifacts[].sha256` | `manifest.json:Artifacts[].SHA256` |  |
| `manifest.json:artifacts[].source` | `manifest.json:Artifacts[].Source` |  |
| `manifest.json:cluster_size` | `manifest.json:ClusterSize` |  |
| `manifest.json:image` | `manifest.json:Image` |  |
| `manifest.json:inline_content` | `manifest.json:InlineContent` |  |
| `manifest.json:inline_content.bytes` | `manifest.json:InlineContent.Bytes` |  |
| `manifest.json:inline_content.streams` | `manifest.json:InlineContent.Streams` |  |
| `manifest.json:on_demand_clusters` | `manifest.json:OnDemandClusters` |  |
| `manifest.json:partition_start_bytes` | `manifest.json:PartitionStart` |  |
| `manifest.json:provenance` | `manifest.json:Provenance` |  |
| `manifest.json:provenance.exported_utc` | `manifest.json:Provenance.Exported` |  |
| `manifest.json:provenance.host` | `manifest.json:Provenance.Host` |  |
| `manifest.json:provenance.source_content_pin` | `manifest.json:Provenance.SourceContentPin` |  |
| `manifest.json:provenance.source_path` | `manifest.json:Provenance.SourcePath` |  |
| `manifest.json:provenance.source_size_bytes` | `manifest.json:Provenance.SourceSize` |  |
| `manifest.json:provenance.tool` | `manifest.json:Provenance.Tool` |  |
| `manifest.json:provenance.tool_version` | `manifest.json:Provenance.ToolVersion` |  |
| `manifest.json:refs_version` | `manifest.json:ReFSVersion` |  |
| `manifest.json:source_holes` | `manifest.json:SourceHoles` |  |
| `manifest.json:source_holes[].clusters` | `manifest.json:SourceHoles[].Clusters` |  |
| `manifest.json:source_holes[].hole_bytes` | `manifest.json:SourceHoles[].HoleBytes` |  |
| `manifest.json:source_holes[].lcn` | `manifest.json:SourceHoles[].LCN` |  |
| `manifest.json:warnings` | `manifest.json:Warnings` |  |
| `manifest.json:warnings[].reason` | `manifest.json:Warnings[].Reason` |  |
| `manifest.json:warnings[].what` | `manifest.json:Warnings[].What` |  |
| `metadata_index.csv:byte_offset` | `metadata_index.csv:ByteOffset` |  |
| `metadata_index.csv:head_plcn` | `metadata_index.csv:HeadPLCN` |  |
| `metadata_index.csv:n_clusters` | `metadata_index.csv:Clusters` | renamed |
| `metadata_index.csv:owner` | `metadata_index.csv:Owner` |  |
| `mlog_log_index.csv:block_lcn` | `mlog_log_index.csv:BlockIndex` | a block index, not an LCN |
| `mlog_log_index.csv:byte_offset` | `mlog_log_index.csv:ByteOffset` |  |
| `usn_J_index.csv:byte_offset` | `usn_J_index.csv:ByteOffset` |  |
| `usn_J_index.csv:clusters` | `usn_J_index.csv:Clusters` |  |
| `usn_J_index.csv:plcn` | `usn_J_index.csv:PLCN` |  |

New in 1.14.0: `manifest.json:BundleFormat`, `manifest.json:BytesPerSector`, `manifest.json:Carries`, `manifest.json:SourceHolesCover`.

### `refsanalysis summary`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `checkpoint_flags` | `CheckpointFlagsHex` | the word in hex; CheckpointFlags now holds the names |
| `checkpoint_vc` | `CheckpointVirtualClock` |  |
| `checksum` | `Checksum` |  |
| `cluster_size` | `ClusterSize` |  |
| `compression` | `Compression` |  |
| `container_size` | `ContainerSize` |  |
| `containers_mapped` | `ContainersMapped` |  |
| `directories` | `Directories` |  |
| `files` | `Files` |  |
| `image` | `Image` |  |
| `newest_timestamp` | `NewestTimestamp` |  |
| `non_resident_files` | `Residency{*}` | as above |
| `objects` | `ObjectCount` |  |
| `oldest_timestamp` | `OldestTimestamp` |  |
| `refs_version` | `ReFSVersion` |  |
| `resident_files` | `Residency{*}` | the files counted per residency category |
| `root_table_rows` | `RootTableRows` |  |
| `root_table_rows{*}` | `RootTableRows{*}` |  |
| `schema_tables` | `SchemaTables` |  |
| `security_descriptors` | `SecurityDescriptors` |  |
| `total_file_size` | `TotalFileSize` |  |
| `total_file_size_bytes` | `TotalFileSize` |  |
| `volume_guid` | `VolumeGUID` |  |
| `volume_label` | `VolumeLabel` |  |
| `volume_size` | `VolumeSize` |  |
| `volume_size_bytes` | `VolumeSize` |  |

New in 1.14.0: `ADSHostFiles`, `BootstrapBackups`, `BootstrapBackups.CheckpointAuthoritativeUnusable`, `BootstrapBackups.CheckpointFindings`, `BootstrapBackups.CheckpointSelectedViaFallback`, `BootstrapBackups.CheckpointTie`, `BootstrapBackups.CheckpointUsedLCN`, `BootstrapBackups.Checkpoints`, `BootstrapBackups.Checkpoints[].AllocClock`, `BootstrapBackups.Checkpoints[].ByteOffset`, `BootstrapBackups.Checkpoints[].ChecksumName`, `BootstrapBackups.Checkpoints[].ChecksumOK`, `BootstrapBackups.Checkpoints[].ClockDivergence`, `BootstrapBackups.Checkpoints[].InUse`, `BootstrapBackups.Checkpoints[].LCN`, `BootstrapBackups.Checkpoints[].LSN`, `BootstrapBackups.Checkpoints[].Role`, `BootstrapBackups.Checkpoints[].RootFail`, `BootstrapBackups.Checkpoints[].RootUnchecked`, `BootstrapBackups.Checkpoints[].RootsOK`, `BootstrapBackups.Checkpoints[].SHA256`, `BootstrapBackups.Checkpoints[].SHA256Bytes`, `BootstrapBackups.Checkpoints[].SelfLCN`, `BootstrapBackups.Checkpoints[].SelfLCNOK`, `BootstrapBackups.Checkpoints[].SignatureOK`, `BootstrapBackups.Checkpoints[].TiedClock`, `BootstrapBackups.Checkpoints[].Use`, `BootstrapBackups.Checkpoints[].VirtualClock`, `BootstrapBackups.Checkpoints[].VirtualClockPage`, `BootstrapBackups.SUPB`, `BootstrapBackups.SUPB[].ByteOffset`, `BootstrapBackups.SUPB[].ChecksumName`, `BootstrapBackups.SUPB[].ChecksumOK`, `BootstrapBackups.SUPB[].LCN`, `BootstrapBackups.SUPB[].OK`, `BootstrapBackups.SUPB[].PayloadMatches`, `BootstrapBackups.SUPB[].Role`, `BootstrapBackups.SUPB[].SHA256`, `BootstrapBackups.SUPB[].SelfLCN`, `BootstrapBackups.SUPB[].SelfLCNOK`, `BootstrapBackups.SUPB[].SignatureOK`, `BootstrapBackups.SUPB[].Used`, `BootstrapBackups.VBR`, `BootstrapBackups.VBR.Backup`, `BootstrapBackups.VBR.Backup.ByteOffset`, `BootstrapBackups.VBR.Backup.ChecksumComputed`, `BootstrapBackups.VBR.Backup.ChecksumOK`, `BootstrapBackups.VBR.Backup.ChecksumStored`, `BootstrapBackups.VBR.Backup.LBA`, `BootstrapBackups.VBR.Backup.MatchesPrimary`, `BootstrapBackups.VBR.Backup.Present`, `BootstrapBackups.VBR.Backup.PrimaryVersion`, `BootstrapBackups.VBR.Backup.SHA256`, `BootstrapBackups.VBR.Backup.Version`, `BootstrapBackups.VBR.ByteOffset`, `BootstrapBackups.VBR.PrimaryChecksumComputed`, `BootstrapBackups.VBR.PrimaryChecksumOK`, `BootstrapBackups.VBR.PrimaryChecksumStored`, `BootstrapBackups.VBR.PrimaryOK`, `BootstrapBackups.VBR.SectorSize`, `BootstrapBackups.VBR.TotalSectors`, `CHKPSHA256`, `Capacity`, `Capacity.AllocatorCoveredBytes`, `Capacity.NotAllocatedBytes`, `Capacity.OutsideAllocatorBytes`, `Capacity.Source`, `Capacity.UsedBytes`, `Capacity.UsedPercent`, `Capacity.VolumeBytes`, `CheckpointFlags`, `CheckpointSHA256Bytes`, `ChecksumSelectorNote`, `CompressedFiles`, `ContainerSizeFrom`, `ContainersMappedBootRegion`, `ContainersMappedNonBoot`, `CountsUnreadable`, `DriverNote`, `DriverVersion`, `EncryptedFiles`, `FSMetadata`, `FSMetadata.Children`, `FSMetadata.Children[].FileID`, `FSMetadata.Children[].Name`, `FSMetadata.Children[].StreamCount`, `FSMetadata.Rows`, `FSMetadata.USNJournal`, `FileNames`, `FilesAccessedAfterChange`, `HardLinkExtraNames`, `HardLinkNameCount`, `HardLinkedFiles`, `ImageSize`, `ImageTail`, `ImageTail.AfterPartitionBytes`, `ImageTail.Bytes`, `ImageTail.InPartitionBytes`, `ImageTail.PartitionEntry`, `IntegrityFiles`, `MLog`, `MLog.Read`, `PartitionStart`, `RedundancyFindings`, `RedundancyNotes`, `ReparseFiles`, `ReparseIndexEntries`, `Residency`, `RootTablesUnreadable`, `SUPBSHA256`, `SUPBUsedLCN`, `SnapshotFiles`, `SnapshotVersions`, `SummaryMode`, `Tool`, `TrashTableEntries`, `USNJournalID`, `VBRSHA256`, `VolumeCreateTime`, `VolumeLastWritableMountTime`, `VolumeSerial`, `VolumeState`, `VolumeVersion`.

**mlog JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `checkpoint_flags` | `CheckpointFlagsHex` | the word in hex; CheckpointFlags now holds the names |
| `checkpoint_vc` | `CheckpointVirtualClock` |  |
| `checksum` | `Checksum` |  |
| `cluster_size` | `ClusterSize` |  |
| `compression` | `Compression` |  |
| `container_size` | `ContainerSize` |  |
| `containers_mapped` | `ContainersMapped` |  |
| `directories` | `Directories` |  |
| `files` | `Files` |  |
| `image` | `Image` |  |
| `newest_timestamp` | `NewestTimestamp` |  |
| `non_resident_files` | `Residency{*}` | as above |
| `objects` | `ObjectCount` |  |
| `oldest_timestamp` | `OldestTimestamp` |  |
| `refs_version` | `ReFSVersion` |  |
| `resident_files` | `Residency{*}` | the files counted per residency category |
| `root_table_rows` | `RootTableRows` |  |
| `root_table_rows{*}` | `RootTableRows{*}` |  |
| `schema_tables` | `SchemaTables` |  |
| `security_descriptors` | `SecurityDescriptors` |  |
| `total_file_size` | `TotalFileSize` |  |
| `total_file_size_bytes` | `TotalFileSize` |  |
| `volume_guid` | `VolumeGUID` |  |
| `volume_label` | `VolumeLabel` |  |
| `volume_size` | `VolumeSize` |  |
| `volume_size_bytes` | `VolumeSize` |  |

New in 1.14.0: `ADSHostFiles`, `BootstrapBackups`, `BootstrapBackups.CheckpointAuthoritativeUnusable`, `BootstrapBackups.CheckpointFindings`, `BootstrapBackups.CheckpointSelectedViaFallback`, `BootstrapBackups.CheckpointTie`, `BootstrapBackups.CheckpointUsedLCN`, `BootstrapBackups.Checkpoints`, `BootstrapBackups.Checkpoints[].AllocClock`, `BootstrapBackups.Checkpoints[].ByteOffset`, `BootstrapBackups.Checkpoints[].ChecksumName`, `BootstrapBackups.Checkpoints[].ChecksumOK`, `BootstrapBackups.Checkpoints[].ClockDivergence`, `BootstrapBackups.Checkpoints[].InUse`, `BootstrapBackups.Checkpoints[].LCN`, `BootstrapBackups.Checkpoints[].LSN`, `BootstrapBackups.Checkpoints[].Role`, `BootstrapBackups.Checkpoints[].RootFail`, `BootstrapBackups.Checkpoints[].RootUnchecked`, `BootstrapBackups.Checkpoints[].RootsOK`, `BootstrapBackups.Checkpoints[].SHA256`, `BootstrapBackups.Checkpoints[].SHA256Bytes`, `BootstrapBackups.Checkpoints[].SelfLCN`, `BootstrapBackups.Checkpoints[].SelfLCNOK`, `BootstrapBackups.Checkpoints[].SignatureOK`, `BootstrapBackups.Checkpoints[].TiedClock`, `BootstrapBackups.Checkpoints[].Use`, `BootstrapBackups.Checkpoints[].VirtualClock`, `BootstrapBackups.Checkpoints[].VirtualClockPage`, `BootstrapBackups.SUPB`, `BootstrapBackups.SUPB[].ByteOffset`, `BootstrapBackups.SUPB[].ChecksumName`, `BootstrapBackups.SUPB[].ChecksumOK`, `BootstrapBackups.SUPB[].LCN`, `BootstrapBackups.SUPB[].OK`, `BootstrapBackups.SUPB[].PayloadMatches`, `BootstrapBackups.SUPB[].Role`, `BootstrapBackups.SUPB[].SHA256`, `BootstrapBackups.SUPB[].SelfLCN`, `BootstrapBackups.SUPB[].SelfLCNOK`, `BootstrapBackups.SUPB[].SignatureOK`, `BootstrapBackups.SUPB[].Used`, `BootstrapBackups.VBR`, `BootstrapBackups.VBR.Backup`, `BootstrapBackups.VBR.Backup.ByteOffset`, `BootstrapBackups.VBR.Backup.ChecksumComputed`, `BootstrapBackups.VBR.Backup.ChecksumOK`, `BootstrapBackups.VBR.Backup.ChecksumStored`, `BootstrapBackups.VBR.Backup.LBA`, `BootstrapBackups.VBR.Backup.MatchesPrimary`, `BootstrapBackups.VBR.Backup.Present`, `BootstrapBackups.VBR.Backup.PrimaryVersion`, `BootstrapBackups.VBR.Backup.SHA256`, `BootstrapBackups.VBR.Backup.Version`, `BootstrapBackups.VBR.ByteOffset`, `BootstrapBackups.VBR.PrimaryChecksumComputed`, `BootstrapBackups.VBR.PrimaryChecksumOK`, `BootstrapBackups.VBR.PrimaryChecksumStored`, `BootstrapBackups.VBR.PrimaryOK`, `BootstrapBackups.VBR.SectorSize`, `BootstrapBackups.VBR.TotalSectors`, `CHKPSHA256`, `Capacity`, `Capacity.AllocatorCoveredBytes`, `Capacity.NotAllocatedBytes`, `Capacity.OutsideAllocatorBytes`, `Capacity.Source`, `Capacity.UsedBytes`, `Capacity.UsedPercent`, `Capacity.VolumeBytes`, `CheckpointFlags`, `CheckpointSHA256Bytes`, `ChecksumSelectorNote`, `CompressedFiles`, `ContainerSizeFrom`, `ContainersMappedBootRegion`, `ContainersMappedNonBoot`, `CountsUnreadable`, `DriverNote`, `DriverVersion`, `EncryptedFiles`, `FSMetadata`, `FSMetadata.Children`, `FSMetadata.Children[].FileID`, `FSMetadata.Children[].Name`, `FSMetadata.Children[].StreamCount`, `FSMetadata.Rows`, `FSMetadata.USNJournal`, `FileNames`, `FilesAccessedAfterChange`, `HardLinkExtraNames`, `HardLinkNameCount`, `HardLinkedFiles`, `ImageSize`, `ImageTail`, `ImageTail.AfterPartitionBytes`, `ImageTail.Bytes`, `ImageTail.InPartitionBytes`, `ImageTail.PartitionEntry`, `IntegrityFiles`, `MLog`, `MLog.ControlCopyPLCN`, `MLog.ControlCopySlot`, `MLog.ControlCopyVerifies`, `MLog.EarlierLogRecords`, `MLog.LogBlocks`, `MLog.LogEnd`, `MLog.LogStart`, `MLog.LogVersion`, `MLog.NewestRecordsMissing`, `MLog.Read`, `MLog.Statements`, `PartitionStart`, `RedundancyFindings`, `RedundancyNotes`, `ReparseFiles`, `ReparseIndexEntries`, `Residency`, `RootTablesUnreadable`, `SUPBSHA256`, `SUPBUsedLCN`, `SnapshotFiles`, `SnapshotVersions`, `SummaryMode`, `Tool`, `TrashTableEntries`, `USNJournalID`, `VBRSHA256`, `VolumeCreateTime`, `VolumeLastWritableMountTime`, `VolumeSerial`, `VolumeState`, `VolumeVersion`.

### `refsanalysis summary++`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `ads_entries` | `ADSHostFiles` |  |
| `capacity` | `Capacity` |  |
| `capacity.allocator_covered_bytes` | `Capacity.AllocatorCoveredBytes` |  |
| `capacity.free` | (removed) | a display string (Capacity.NotAllocatedBytes is the number) |
| `capacity.free_bytes` | (removed) | the same number as Capacity.NotAllocatedBytes |
| `capacity.not_allocated` | (removed) | a display string (Capacity.NotAllocatedBytes) |
| `capacity.not_allocated_bytes` | `Capacity.NotAllocatedBytes` |  |
| `capacity.outside_allocator_bytes` | `Capacity.OutsideAllocatorBytes` |  |
| `capacity.source` | `Capacity.Source` |  |
| `capacity.used` | (removed) | a display string (Capacity.UsedBytes) |
| `capacity.used_bytes` | `Capacity.UsedBytes` |  |
| `capacity.used_pct` | `Capacity.UsedPercent` |  |
| `capacity.volume_bytes` | `Capacity.VolumeBytes` |  |
| `checkpoint_flags` | `CheckpointFlagsHex` | the word in hex; CheckpointFlags now holds the names |
| `checkpoint_vc` | `CheckpointVirtualClock` |  |
| `checksum` | `Checksum` |  |
| `cluster_size` | `ClusterSize` |  |
| `compressed_files` | `CompressedFiles` |  |
| `compression` | `Compression` |  |
| `container_size` | `ContainerSize` |  |
| `containers_free` | `ContainersMappedBootRegion` | the rows that map the boot region; not free space |
| `containers_mapped` | `ContainersMapped` |  |
| `containers_used` | `ContainersMappedNonBoot` | the Container Table rows other than the boot region's; not usage |
| `directories` | `Directories` |  |
| `driver_version` | `DriverVersion` |  |
| `encrypted_files` | `EncryptedFiles` |  |
| `files` | `Files` |  |
| `fs_metadata` | `FSMetadata` |  |
| `fs_metadata.children` | `FSMetadata.Children` |  |
| `fs_metadata.children[].flags` | `FSMetadata.Children[].FileID` | the word at value+0x80 is the child's file id |
| `fs_metadata.children[].name` | `FSMetadata.Children[].Name` |  |
| `fs_metadata.children[].stream_count` | `FSMetadata.Children[].StreamCount` |  |
| `fs_metadata.rows` | `FSMetadata.Rows` |  |
| `fs_metadata.usn_journal` | `FSMetadata.USNJournal` |  |
| `hardlink_extra` | `HardLinkExtraNames` |  |
| `hardlink_groups` | `HardLinkedFiles` |  |
| `hardlink_names` | `HardLinkNameCount` |  |
| `image` | `Image` |  |
| `integrity_files` | `IntegrityFiles` |  |
| `newest_timestamp` | `NewestTimestamp` |  |
| `non_resident_files` | `Residency{*}` | as above |
| `objects` | `ObjectCount` |  |
| `oldest_timestamp` | `OldestTimestamp` |  |
| `refs_version` | `ReFSVersion` |  |
| `reparse_files` | `ReparseFiles` |  |
| `reparse_index_entries` | `ReparseIndexEntries` |  |
| `resident_files` | `Residency{*}` | the files counted per residency category |
| `root_table_rows` | `RootTableRows` |  |
| `root_table_rows{*}` | `RootTableRows{*}` |  |
| `schema_count_500` | `VerifyBlockLCN`, `VerifyBlockClusters` | the key-0x540 row is the verify block's location (u64 first cluster, u64 cluster count); 1.13.1 read +0x00 as a schema count |
| `schema_tables` | `SchemaTables` |  |
| `security_descriptors` | `SecurityDescriptors` |  |
| `snapshot_files` | `SnapshotFiles` |  |
| `snapshots` | `SnapshotVersions` |  |
| `symlinks` | `Symlinks` |  |
| `total_file_size` | `TotalFileSize` |  |
| `total_file_size_bytes` | `TotalFileSize` |  |
| `trash_table_entries` | `TrashTableEntries` |  |
| `utilization_pct` | (removed) | the mapped-container count as a percentage; the usage is Capacity.UsedPercent |
| `volume_create_time` | `VolumeCreateTime` |  |
| `volume_guid` | `VolumeGUID` |  |
| `volume_label` | `VolumeLabel` |  |
| `volume_modify_time` | `VolumeLastWritableMountTime` | the last mount that could write |
| `volume_size` | `VolumeSize` |  |
| `volume_size_bytes` | `VolumeSize` |  |
| `volume_version` | `VolumeVersion` |  |

New in 1.14.0: `BootstrapBackups`, `BootstrapBackups.CheckpointAuthoritativeUnusable`, `BootstrapBackups.CheckpointFindings`, `BootstrapBackups.CheckpointSelectedViaFallback`, `BootstrapBackups.CheckpointTie`, `BootstrapBackups.CheckpointUsedLCN`, `BootstrapBackups.Checkpoints`, `BootstrapBackups.Checkpoints[].AllocClock`, `BootstrapBackups.Checkpoints[].ByteOffset`, `BootstrapBackups.Checkpoints[].ChecksumName`, `BootstrapBackups.Checkpoints[].ChecksumOK`, `BootstrapBackups.Checkpoints[].ClockDivergence`, `BootstrapBackups.Checkpoints[].InUse`, `BootstrapBackups.Checkpoints[].LCN`, `BootstrapBackups.Checkpoints[].LSN`, `BootstrapBackups.Checkpoints[].Role`, `BootstrapBackups.Checkpoints[].RootFail`, `BootstrapBackups.Checkpoints[].RootUnchecked`, `BootstrapBackups.Checkpoints[].RootsOK`, `BootstrapBackups.Checkpoints[].SHA256`, `BootstrapBackups.Checkpoints[].SHA256Bytes`, `BootstrapBackups.Checkpoints[].SelfLCN`, `BootstrapBackups.Checkpoints[].SelfLCNOK`, `BootstrapBackups.Checkpoints[].SignatureOK`, `BootstrapBackups.Checkpoints[].TiedClock`, `BootstrapBackups.Checkpoints[].Use`, `BootstrapBackups.Checkpoints[].VirtualClock`, `BootstrapBackups.Checkpoints[].VirtualClockPage`, `BootstrapBackups.SUPB`, `BootstrapBackups.SUPB[].ByteOffset`, `BootstrapBackups.SUPB[].ChecksumName`, `BootstrapBackups.SUPB[].ChecksumOK`, `BootstrapBackups.SUPB[].LCN`, `BootstrapBackups.SUPB[].OK`, `BootstrapBackups.SUPB[].PayloadMatches`, `BootstrapBackups.SUPB[].Role`, `BootstrapBackups.SUPB[].SHA256`, `BootstrapBackups.SUPB[].SelfLCN`, `BootstrapBackups.SUPB[].SelfLCNOK`, `BootstrapBackups.SUPB[].SignatureOK`, `BootstrapBackups.SUPB[].Used`, `BootstrapBackups.VBR`, `BootstrapBackups.VBR.Backup`, `BootstrapBackups.VBR.Backup.ByteOffset`, `BootstrapBackups.VBR.Backup.ChecksumComputed`, `BootstrapBackups.VBR.Backup.ChecksumOK`, `BootstrapBackups.VBR.Backup.ChecksumStored`, `BootstrapBackups.VBR.Backup.LBA`, `BootstrapBackups.VBR.Backup.MatchesPrimary`, `BootstrapBackups.VBR.Backup.Present`, `BootstrapBackups.VBR.Backup.PrimaryVersion`, `BootstrapBackups.VBR.Backup.SHA256`, `BootstrapBackups.VBR.Backup.Version`, `BootstrapBackups.VBR.ByteOffset`, `BootstrapBackups.VBR.PrimaryChecksumComputed`, `BootstrapBackups.VBR.PrimaryChecksumOK`, `BootstrapBackups.VBR.PrimaryChecksumStored`, `BootstrapBackups.VBR.PrimaryOK`, `BootstrapBackups.VBR.SectorSize`, `BootstrapBackups.VBR.TotalSectors`, `CHKPSHA256`, `CheckpointFlags`, `CheckpointSHA256Bytes`, `ChecksumSelectorNote`, `ContainerSizeFrom`, `CountsUnreadable`, `DriverNote`, `FileNames`, `FilesAccessedAfterChange`, `ImageSize`, `ImageTail`, `ImageTail.AfterPartitionBytes`, `ImageTail.Bytes`, `ImageTail.InPartitionBytes`, `ImageTail.PartitionEntry`, `MLog`, `MLog.Read`, `PartitionStart`, `RedundancyFindings`, `RedundancyNotes`, `Residency`, `RootTablesUnreadable`, `SUPBSHA256`, `SUPBUsedLCN`, `SummaryMode`, `Tool`, `USNJournalID`, `VBRSHA256`, `VolumeSerial`, `VolumeState`.

### `refsanalysis details`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `accessed` | `Accessed` |  |
| `changed` | `Changed` |  |
| `created` | `Created` |  |
| `data_size_alloc` | `AllocatedSize` |  |
| `file_attrs` | `FileAttributes` |  |
| `file_size` | `FileSize` |  |
| `internal_flags` | `InternalFlags` |  |
| `last_usn` | `USN` |  |
| `modified` | `Modified` |  |
| `name` | `FileName` |  |
| `oid` | `ObjectRef` | the object's ObjectRef (its OID was 0 for a split record) |
| `packed_ea_size` | (removed) | not written (the text view prints it) |
| `parent_oid` | `ParentOID` |  |
| `path` | `FullPath` |  |
| `record_placement` | `RecordPlacement` |  |
| `reparse_tag` | `ReparseTag` |  |
| `security_id` | `SecurityId` |  |
| `snapshot_count` | `SnapshotCount` |  |
| `storage` | `DataResidency` |  |
| `subrecords` | `SubRecords` |  |
| `subrecords.ads` | `Streams` | the streams once: Name, Size, DataResidency |
| `subrecords.ads[].name` | `Streams[].Name` | as above |
| `subrecords.ads[].size` | `Streams[].Size` | as above |
| `subrecords.data` | `SubRecords.Data` |  |
| `subrecords.data[].name` | `SubRecords.Data[].FileName` |  |
| `subrecords.data[].size` | `SubRecords.Data[].Size` |  |
| `subrecords.ea` | `SubRecords.EA` |  |
| `subrecords.reparse` | `SubRecords.Reparse` |  |
| `subrecords.snapshots` | `SubRecords.Snapshots` |  |
| `usn` | `USN` |  |
| `usn_journal_id` | (removed) | not written (the text view prints it) |
| `value_len` | `ValueLength` |  |

New in 1.14.0: `ADSNames`, `CreationDir`, `DACLSummary`, `Extension`, `FileAttributesHex`, `FileID`, `GroupSid`, `HardLinkCount`, `HardLinkNames`, `HasADS`, `HasEA`, `HasIntegrity`, `HomeOID`, `InternalFlagsHex`, `IsCompressed`, `IsDirectory`, `IsEncrypted`, `IsMoved`, `IsSparse`, `OwnerSid`, `PackedEASize`, `ParentPath`, `ReparseTagHex`, `ReparseTarget`, `SnapshotNames`, `Streams[].DataResidency`, `USNJournalID`.

### `refsanalysis allocators`

**JSON**

| 1.13.1 | 1.14.0 | |
|---|---|---|
| `capacity` | `Capacity` |  |
| `capacity.cluster_size` | `Capacity.ClusterSize` |  |
| `capacity.covered_clusters` | `Capacity.CoveredClusters` |  |
| `capacity.format` | `Capacity.Format` |  |
| `capacity.free_clusters` | `Capacity.FreeClusters` |  |
| `capacity.outside_allocator_clusters` | `Capacity.OutsideAllocatorClusters` |  |
| `capacity.used_clusters` | `Capacity.UsedClusters` |  |
| `capacity.volume_clusters` | `Capacity.VolumeClusters` |  |
| `cluster_size` | `ClusterSize` |  |
| `image` | `Image` |  |
| `refs_version` | `ReFSVersion` |  |
| `tiers` | `Tiers` |  |
| `tiers[].addressing` | `Tiers[].Addressing` |  |
| `tiers[].allocated_clusters` | `Tiers[].AllocatedClusters` |  |
| `tiers[].bitmap_rows` | `Tiers[].BitmapRows` |  |
| `tiers[].compact_rows` | `Tiers[].CompactRows` |  |
| `tiers[].foreign_rows_rejected` | `Tiers[].ForeignRowsRejected` |  |
| `tiers[].free_clusters` | `Tiers[].FreeClusters` |  |
| `tiers[].root_index` | `Tiers[].RootIndex` |  |
| `tiers[].root_page_table_id` | `Tiers[].RootPageTableID` |  |
| `tiers[].rows` | `Tiers[].Rows` |  |
| `tiers[].span_clusters` | `Tiers[].SpanClusters` |  |
| `tiers[].summary_agrees` | `Tiers[].SummaryAgrees` |  |
| `tiers[].summary_covered_clusters` | `Tiers[].SummaryCoveredClusters` |  |
| `tiers[].summary_format` | `Tiers[].SummaryFormat` |  |
| `tiers[].summary_free_clusters` | `Tiers[].SummaryFreeClusters` |  |
| `tiers[].table_id` | `Tiers[].TableID` |  |
| `tiers[].tier` | `Tiers[].Tier` |  |
| `volume_clusters` | `VolumeClusters` |  |

<!-- /key-migration -->

## 1.13.0 → 1.13.1

1.13.1 renames and removes no column and no key. A script meets two exit codes and some values.

### Exit codes in 1.13.1

| Tool and command | Condition | 1.13.0 | 1.13.1 |
|---|---|---|---|
| forefst `integrity --checksums` | the check is incomplete: a checksummed cluster or a file holding them was not verified | 0 | 2 |
| forefst `extract` | a checksummed row of the file could not be read | 0 | 2 |

### What else a script meets

- **`summary --json`** adds `not_allocated_bytes` and `not_allocated`; the `free*` keys keep their names and values.
- **`usn`'s `path`**:
  - `<unlinked 0x…>` is a parent that still exists but has no name; `<oid 0x…>` is a parent whose object is gone
    (1.13.0 wrote `<oid 0x…>` for both);
  - a file in the root directory has the leading `/` every other path has, and the root's own records read `/`.
- **`timestomp`'s `storage` column** uses the residency words of `files` (a small hard-linked file whose bytes are
  inline printed `(extents)`).
- **`--csv -` and `--json -`** mean standard output in every command; the commands that share the output-format parser
  (`timeline`, `timestomp` and `specials` among them) rejected the `-`.
- **`timeline`**: a file's `$SI` rows carry the OID of the file's home directory (1.13.0 left it blank), and
  `--fileref HOME:ID` is new.
- **USN reasons**: a bare close reads `CLOSE` in both USN renderers, and an unrecognised reason bit is shown.
- **`integrity --checksums`** figures change on every volume with integrity streams: every checksummed cluster is
  checked.

## 1.12.3 → 1.13.0

### Exit codes in 1.13.0

From 1.13.0, exit 2 in `forefst.py` means "a finding, or work the command could not complete".

In 1.12.3 a command exited 2 only for a failed `integrity` check, for bytes that `extract` or a bulk export drew
from image holes, for a file `extract` could not reassemble, and for a bundle `verify-bundle` found damaged;
otherwise it returned 0 whenever it produced output.

`refsanalysis.py` kept its own exit codes until 1.14.0 (above).

| Tool and command | Condition | 1.12.3 | 1.13.0 |
|---|---|---|---|
| forefst `summary`, `integrity` | a redundancy warning: a missing backup boot sector, fewer than two intact superblock copies | 0 | 2 |
| forefst `summary`, `integrity` | a checkpoint copy's allocator clock is ahead of its virtual clock | 0 | 2 |
| forefst `integrity --max-pages` | the cap was reached (a partial check) | 0 | 2 |
| forefst `integrity` | a page does not match the digest its parent's page reference records | 0 | 2 |
| forefst, the listing and content commands | an object's root page does not match the digest the Object Table records for it | 0 | 2 |
| forefst, every listing and count | a page could not be read as a B+ node | 0 | 2 |
| forefst, every command | a recorded skip | 0 | 2 |
| forefst | the Security Descriptor table is destroyed (the verdict reads `UNDETERMINED`, not `CLEAN`) | 0 | 2 |
| forefst | a journal region zeroed inside the written span | 0 | 2 |
| forefst `usn` | the FS-metadata directory could not be read | 0 | 2 |
| forefst `summary` | a bootstrap copy is missing, damaged or invalid | 0 | 2 |
| forefst, every command | the primary superblock is unreadable and a backup is used (the volume is read) | 1 | 2 |
| forefst, every command | the newest checkpoint fails its self-checksum and an older one is used | 0 | 2 |
| forefst `summary`, `fastsummary` | the boot sector's version is implausible or contradicted by the checkpoint and `$VOLUME_INFORMATION` | 0 | 2 |
| forefst `usn --info`, `timeline` | journal records after the last surviving one are missing | 0 | 2 |
| forefst `integrity --checksums` | a file's integrity-stream CRC-32C fails | 0 | 2 |
| refsanalysis `chkp --verify` | the checkpoint page fails its own self-checksum, or its allocator clock is ahead of its virtual clock | 0 | 2 |
| forefst `summary`, `integrity` | the volume was not cleanly dismounted | 0 | 2 |

A script that treats any non-zero code as failure stops on volumes 1.12.3 accepted; those runs were incomplete or had
a finding.

Where only hard corruption matters, branch on the JSON: `integrity --json` carries `clean` and `coverage_complete`
(`Clean` and `CoverageComplete` from 1.14.0), which separate "found a problem" from "could not check".

Usage errors stay 1, `--help` stays 0, and a clean and complete run stays 0. Unwritten journal ring space is not a
skip.

## Evidence

The key tables of "1.13.1 → 1.14.0" were measured on the four public samples `win11refs2tspecials`,
`win11refs2tsnapshots`, `wininsiderrefs8gtest2` and `win11refstestmftecmd`, and on the ReFS 3.4 volume
`win10refs2tspecials`.
