# Changelog

## v1.14.0 — 2026-11-23 — the 1.13.1 known issues fixed, one name and one form for every field, and refsanalysis's last update

**Everything here is relative to v1.13.1.** The work was planned as 1.13.2 and ships as 1.14.0 because it changes
every machine output. It fixes every defect the 1.13.1 notes listed as a known issue, follows refs.sys's own rules
where the tools kept rules of their own, and gives each field of both tools one name and each kind of value one
form. **It is the last version with refsanalysis updates** (see [refsanalysis](#refsanalysis-its-last-update)).

**What a script must change**, in short: every JSON key and CSV header has a new name (the measured old → new tables
are in [Migrating between releases](tools/migration.md)); `files --json` is now the `files` CSV row; the `IsResident`
column and `--filter resident` are gone; several conditions that exited 0 now exit 2, and arguments that were ignored
now exit 1. The sections below say what changed and why.

### Breaking changes

- **One name for every field, in both tools.** Every JSON key and CSV header is written in one vocabulary: a fact
  that `files` has takes its `files` column name in every command (`ObjectRef`, `FullPath`, `FileName`, `HomeOID`,
  `FileID`, `Created` …); any other name is its words in PascalCase, acronyms in capitals (`OID`, `LCN`, `USN`, `GUID`,
  `SID`). The tables, command by command, are in [Migrating between releases](tools/migration.md).
- **`files --json` is the CSV row**: the same fields, names and values, typed, with `null` for an empty cell; 1.13.1
  wrote a separate, smaller set of keys. The `files` CSV goes from 40 to 42 columns: **`IsResident` is removed** (the deprecated
  alias kept since 1.10.0: it was `True` exactly when `DataResidency` is `inline`), and `FileAttributesHex`, `InternalFlagsHex`
  and `ReparseTagHex` are added beside the names. **`--filter resident` is removed** and exits 1 naming its
  replacement, `inline`.
- **One form for each kind of value**, in every command and every format ([Value forms](tools/forefst.md#value-forms)):
  a time in UTC ISO 8601 with all seven digits of the fraction and `Z`; a value the volume does not hold as `(none)` in
  text, an empty cell in CSV and `null` in JSON; identifiers, LCNs, offsets, checksums and marker words in lower-case
  hex, a string in JSON (`reparse --json` writes a tag once: `ReparseTag` / `ReparseTagHex`); a
  flag word as the names of its bits plus a `…Hex` field with the word (a bit without a name written in hex among the
  names); exact byte counts in machine output; `true` / `false` in CSV and JSON; `ReFS 3.14`, never `v3.14`.
  `files`' `DACLSummary` writes each ACE as `security` does (`ALLOWED SYSTEM (S-1-5-18): FULL_CONTROL`), the ACEs
  separated by `; ` (1.13.1: `ALLOWED:SYSTEM (S-1-5-18):FULL_CONTROL`, separated by ` | `).
- **Exit codes.** A command now exits **2** for conditions it reported without a finding in 1.13.1 — among them a
  superblock or checkpoint copy that fails its self-checksum, a Container Table that maps two containers onto
  overlapping clusters, a re-created change journal, an MLog whose newest records are missing, a read error inside a
  `deleted` scan, a byte range whose image-hole state could not be checked, and a file an export could not write. It
  exits **1** where 1.13.1 ignored the input: a stray or unknown argument (16 commands accepted one silently), a format
  the command does not write, two machine formats on one `usn` or `mlog` run, an unknown `export` subverb (1.13.1 wrote
  a bundle), `deleted --carve` (it did nothing; carving is `export deleted DIR --carve`), a bundle written by
  1.12.1–1.13.1, and `files --cow-before` with an image of another volume. The exit-code changes, each with its
  condition: [Migrating between releases — exit codes](tools/migration.md#exit-codes-in-1140); among them, besides the
  ones this list names: the checkpoint conditions that change what every command reads, a missing root directory or
  required table (1 -> 2), the two Container Table copies differing beyond their flags word, an unreadable `extract`
  cluster (1 -> 2), `snapshots --extract DIR --json` (0 -> 1) and a per-object bundle given as input (0 -> 1).
- **What a bundle carries** is said -- in `manifest.json` (`Carries`), the export's last lines, the reader's banner and
  `verify-bundle`: names, times, SIDs, `$I` paths, inline content and the free space of the metadata pages, the
  journal's and the MLog's records when it holds them, and the source path and host. 1.13.1 stated the inline content
  only.
- **A bundle that does not carry a table's pages** (`export metadata --what`) is said to: the Container Table's copies
  are "not carried by this bundle" (not copies that fail their check), and the container-mapping warning names the
  bundle and that cause (not the reader's temporary file and a corrupt table). `extract` from a bundle says the bytes it
  refuses are not in the bundle and to read the stream from the source image.
- **Bundles carry a format number.** `export metadata` writes `BundleFormat` into `manifest.json`; `verify-bundle` and
  the bundle reader refuse a bundle without it (written by 1.12.1–1.13.1) with a message, where they could misread it.
  Export the bundle again with 1.14.0. A bundle 1.14.0 writes is read with 1.14.0: 1.13.1 stops on it with
  `KeyError: 'cluster_size'`. A second `export metadata` into a directory that already holds a bundle is
  written beside it (`<dir>_2`, `<dir>_3` …) and the path used is printed; 1.13.1 wrote into the same directory and
  overwrote the first bundle's seal.
- **Output files.** A machine-output FILE, and `extract -o FILE`, is written as `<FILE>.partial` (a short name beside it
  when that name would be too long) and renamed when it is complete; a write that fails removes the partial file and
  names FILE, where 1.13.1 could leave a truncated file under FILE's name. A FILE that is not a regular file (a device,
  a FIFO, a process substitution) is written directly. Status lines (`Wrote …`) go to stderr.
- **`export file PATH` and `export ads PATH:STREAM` write to disk**: `./<the file's name>` (a stream:
  `<file>__<stream>`), or into `-o DIR/`, never over a file (`<name>.dupN`); the name follows the bulk exports' rule and
  the stderr line gives the name on the volume when it differs; `-o FILE` as given, `-o -` the screen. 1.13.1 wrote to
  the screen without `-o`. `extract` stays the screen command.
- **`summary`'s text**: its title is `ReFS Volume Summary` (1.13.1 printed `fastsummary`'s, `ReFS Volume Fast Extended
  Summary`). `Files:` counts each file once, with its residency words (`inline`, `extents`, `snapshot-shared` …), and
  the names are on their own `Names:` line (one per file, plus one per extra name of a hard-linked file). The census
  below it counts files too, each once and no directory: `Integrity files:` (1.13.1 `Integrity objects:`), `ADS host
  files:` and the encrypted, compressed and snapshot counts; 1.13.1 counted names, and the directories carrying the bit
  (on the public sample `win11refstestmftecmd`: files 1,507 → 1,225, integrity 559 → 340, ADS hosts 263 → 150).
  `Containers mapped:` gives the containers the Container Table maps and how many lie outside the boot region (1.13.1
  `Containers used: 62 / 63`, which read as usage). Each checkpoint copy's line gives the record's size and the copy's
  role (in use, newest, superseded or tied). The image tail is on one line: 1.13.1 took the volume's length from the
  image and called the tail space "beyond the last container" that no allocator tracks. Then `File contents: not
  read`, and a closing rule. The text views and the help wrap
  their prose at about 100 characters; data rows and the stderr lines are never wrapped. The rules between sections
  are 78 characters wide (`specials` and `mlog --info` drew 68 and 70, refsanalysis 72 and 74); a table's underline keeps
  its table's width.
- **A count of one takes the singular** in the text of both tools (`1 file sharing 2 names`, `1 row`, `1 entry`,
  `1 cluster`, `1 byte`): 1.13.1 printed `1 files`, `1 rows`, `1 entries` (on the public sample
  `win11refs2tsnapshots`: `Hard-linked: 1 files sharing 2 names`).
- **An export's statements** (what a command says about what it read) go to stderr when stdout carries the export and
  to stdout when the export goes to a FILE, in `usn`, `mlog`, `timeline` and `timestomp` (`usn` with no journal
  writes them to stderr in every machine mode, its empty document on stdout). With no journal to read,
  `usn --csv` writes its header row alone and `usn --json` a document with no records; 1.13.1 wrote neither, only a sentence
  on stdout, which a CSV reader reading stdout took for the header row.
- **A closed pipe** (`| head`) that carries the output stops the run quietly and exits 2 if the run had recorded a
  finding or a skip before the close, else 0; a closed pipe that carries only messages (stderr, or stdout when the
  output goes to a FILE or a directory) no longer stops the run. 1.13.1 exited 120 whenever stderr was in the closed
  pipe, and `files --csv FILE 2>&1 | head -1` never wrote FILE.
- **MLog words** (`mlog`, `timeline`). The class a row derives from its records is the column `DerivedAction`, and the
  outputs say it is derived, not read; `REPARENT` is now `TABLE_REPARENTED` (no pair of names is implied) and `WRITE`
  is `DATA_OR_REPARSE_WRITE`. New: `TimeSource` (where a row's time comes from) and `PathToday` / `ParentPathToday`
  (the path in the live tree now, which is not the path at the time of the event). A move or rename is read from the
  file's own records (its name link replaced, or its table moved from the old name to the new): `RENAME`, `MOVE` (the
  name kept) and the new `MOVE_AND_RENAME` (moved under a new name, as a deletion to the Recycle Bin is); `--parse`'s detail
  gives a rename's old and new name and a move's directories, `--json` Entries every pair. Where those records are
  absent (a ReFS 3.4 directory) the directories of the names decide, said as `names not paired`, and the new
  `MOVE_OR_RENAME` says when they cannot. A name removed with no new name for it is
  `ENTRY_REMOVE`; a new name no removal pairs with is `CREATE`. 1.13.1 printed `RENAME` for such a removal (files a lab
  script deleted), `REPARENT` for renames the reparent record carries, `MOVE` for a move under a new name and `WRITE`
  for a file created in a payload that also removes a row of the new file. A row shows its name in that name's own directory
  and names a payload's other changes after `also`; `--json` Transactions add `Entries`. A record's `+0x20` is
  the allocator clock: `mlog -v`'s column `AllocClock` and `--json`'s `AllocatorClock`, in decimal; `--json` adds
  `InheritedTableOID`.
- **`IsMoved` is no longer a yes/no value.** It says how it was decided: `false` (in its creation directory), the
  values the change journal decides (`moved (change journal)`, `a hard link made here (change journal)`, `in its
  creation directory (change journal)`), `moved (the record's reference)`, and where neither decides, `moved, or
  hard-linked and the original name removed` or `undetermined` ([`files` column 42](tools/forefst.md#csv-output-fields)).
- **`summary`'s `Volume modified` is `Last mount (rw)`**, and its keys are renamed with it: the field is the time of
  the last mount that could write (E142), not a modification time.
- **`timestomp`'s FUTURE signal is retired.** It compared a file's creation time with that same mount time, called
  "the volume's last metadata write". The other signals and tiers are unchanged; `--min LOW` now shows the LOW tier.
- **`timestomp`'s text** gives each row's evidence after its signals (`evidence:` the journal records, as
  `usn:REASON@ObjectRef`, and the hard-link name, as `hardlink:PATH`, the signals rest on; the CSV and JSON carried it already), says from
  when the journal can corroborate (its lowest surviving record and that record's time: a file changed before it
  cannot be corroborated by it), and prints `Last mount (rw)` where 1.13.1 printed `Volume modified`. Its time column
  is `Changed` (below).
- **`deleted` writes every entry it prints as a row of every format, with its `Status`**, including the Trash rows,
  the checkpoint comparison and the `--scan-pages` entries ([`deleted`](tools/forefst.md#deleted--the-deleted-file-view-list--recoverability)).
- **`refsanalysis files`** gains an `ObjectRef` and a `Data` column, and its header names its columns.
- **`details <directory> --json` names the `$SI` sizes for what they are**: `SI.DataSize` is `$SI+0x30`, an integer
  (1.13.1 `si.si_field_0x30`, a hex string it called unpopulated), and `SI.AllocatedSize` is `$SI+0x38` (1.13.1
  `si.datasize`). On a file's record they are its data size and allocated size; on a directory's own row both are 0.

### The known issues of 1.13.1

The 1.13.1 notes listed 21 known defects. Each is fixed:

- **A superblock copy that fails its self-checksum** is a finding: `summary` and `integrity` name the copy and exit 2,
  the volume GUID comes from a copy that verifies, and "payload is identical" is printed only when the copies were
  compared and are.
- **`integrity`'s superblock offsets** are from the start of the image, as `summary`'s, and its Redundancy section
  says so; the boot sectors and the checkpoint copies are given their offsets too, each checkpoint copy with its role.
- **The displays of a checkpoint** (the Checkpoint sections of `summary`, `fastsummary` and refsanalysis `summary` /
  `summary++`, `integrity`'s header, refsanalysis `supb`'s marker, `chkp` and `containers`) show the copy in use,
  chosen by refs.sys's rule (below).
- **A checkpoint copy that fails its self-checksum** is labelled by its checksum state, never `valid`, and is a
  finding (exit 2) also when both copies carry the same clock.
- **`deleted`'s checkpoint comparison and the checkpoint hash** of `summary` / `fastsummary` use the copy refs.sys
  would use; the hash covers the checkpoint record, one cluster (E118). The comparison names the other copy the
  newer one when it is (the newest copy failed and an older one is in use), and states what `summary` says of the
  copy it compares against -- a failed self-checksum, a checksum that cannot be verified, a copy refs.sys rejects, a
  root 0xc, 7 or 8 that does not verify -- and exits 2 for it.
- **refsanalysis `supb --verify`** prints a self-checksum row for every superblock and checkpoint copy;
  `supb --verify` and `boot --verify` exit 2 on a row that fails. `chkp --verify` adds a self-checksum row for each
  checkpoint copy it does not decode, and exits 2 when one fails.
- **refsanalysis** exits 2 after skipping metadata it could not read, prints `unreadable` instead of `0 rows`, takes
  the GUID from a copy that verifies, and its `forefst` passthrough returns forefst's exit code.
- **`integrity --checksums`** names what it covered (the system tables and each object's root page) and does not
  say "no tampering" of pages it did not check; `--fullchecksums` and `--verify-pages` now verify the child pages
  below a file's extent index and below an embedded attribute index too. A clean verdict reads "VERIFIED — no
  tampering or corruption detected in these pages (a checksum cannot prove the absence of a deliberate edit)".
- **The Container Table** is checked: two containers mapped onto overlapping clusters are a condition of every
  command (a warning and exit 2; `summary`, `dataruns`, `integrity` without `--checksums` and refsanalysis
  `containers` agree), a row laid out unlike the volume's other rows is not translated through, and a page read
  through the table that carries another address than the one asked for is recorded and not used. A container moved
  with every digest covering it recomputed stays undetectable from the image, and the pages say so.
- **Sizes and scan ranges** come from the volume's length, not the image's.
- **An MLog whose newest records were destroyed** is a finding (exit 2), up to the log end its control area recorded
  (the limit is stated in the Known issues). The finding counts the 4 KiB log blocks from the newest record to the log
  end; an LSN's generation is not a count of laps (it also goes up when a log is begun anew at the same offset).
- **`mlog`'s control-header labels**: `+0x18` is the log start and `+0x20` the log end, each as of the control area's
  last write (E116); `+0x38` is the log's open count (E117).
- **`summary`'s file counts** are given per residency category and sum to the total.
- **A re-created change journal** is reported as a re-creation, with the boundary between the journals' records; a
  missing range is stated as missing, without calling it destroyed.
- **The FUTURE signal** is retired (above).
- **`deleted` no longer lists a renamed file's old name as a deleted file** where the volume can tell: an entry's
  identity is checked against the live tree and, for an embedded row, the change journal, and the entry says what
  it is (`RENAMED`, `STILL PRESENT` …).
- **A carve shorter than the file, or zero-filled over a gap of its extent map,** says so and counts the clusters; a
  remnant that produces no carve says why.
- **Carved integrity-stream data** is checked: every carved cluster whose map row carries a CRC-32C is compared with
  it.
- **`deleted` no longer says it carves**, and `deleted --carve` exits 1 naming `export deleted DIR --carve`.
- **A read error during `deleted`'s slack or orphan-page scan** is a recorded skip: the coverage line states the
  clusters read, and the command exits 2.
- **Bulk exports record their renames**: `export resident-all`, `export recyclebin` and the other bulk exporters
  write `export_index.csv` (ObjectRef, FullPath, ContentFile, SHA256, RenameReason); `export metadata` no longer
  writes into an existing bundle (above).

### Defects of 1.13.1 that its Known-issues list did not name

Found after 1.13.1 was published; each is fixed in 1.14.0. What to re-check in work done with 1.13.1:

- **`extract --id` could write another file's bytes and exit 0.** A name with the same ordinal in the directory asked
  for -- a file moved into it, or a hard-link name placed in it -- stood in for the file: on `win11refs2tspecials`
  `0x75e:0x3` wrote `hardlink_uniform_706791.bin` (218,785 bytes) instead of `lima_victor_148410.cfg` (413,666 bytes),
  on `win11refs2tsnapshots` `0x731:0x2` wrote `xbpt_audit_echo_178867.tmp` instead of `xbpt_log_foxtrot_796125.ini`.
  *Re-check:* extract again by path, or with 1.14.0, every file 1.13.1 extracted by `--id`, and compare the hashes.
- **A bulk export that could not write a file exited 0.** The content files of `export resident-all` and the other
  bulk exporters, `holes.json` and the recovery log warned and went on: into a read-only directory `export
  resident-all` wrote nothing and exited 0. *Re-check:* an export made with 1.13.1 whose run printed a warning that a
  file could not be written is incomplete, whatever its exit code.
- **`security --audit` said `VERDICT: CLEAN` over an altered page.** With the security table's root page no longer
  matching the digest the Object Table recorded for it, the descriptors' own hashes still passed: the audit warned and
  exited 2 under a CLEAN verdict. The verdict is now `UNDETERMINED`, naming the page. *Re-check:* a CLEAN audit of 1.13.1
  whose run warned that the page of object 0x530 does not match its recorded checksum.
- **`usn --info` read the journal's entry from an altered page in silence.** When the root page of the system metadata
  table (OID 0x520) did not match its digest, `usn --info` printed the entry, its extents and its records with no warning
  and exited 0 (`summary` warned). It now warns, marks the entry and exits 2; every command that reads the journal's entry
  verifies that page. *Re-check:* journal figures taken with 1.13.1 from a volume whose `summary` warned about the page of
  object 0x520.
- **`files` printed access-control data from an altered security table and exited 0.** It read the security table's
  root page without the check against the digest the Object Table records for it, which `security --audit` and
  `summary` make: with one bit of an access-control entry flipped from allowed to denied, `files --csv` and `--json`
  (also from a bundle) printed the denied entry in `DACLSummary` with no warning. `details` read that page the same way,
  and `export metadata` copied every system table's root page without checking it. Every table walk now verifies the
  root page of the object it reads; `files` keeps the values it read, says on stderr that `SecurityId`, `OwnerSid`,
  `GroupSid` and `DACLSummary` come from that page, and exits 2. *Re-check:* the security columns of a 1.13.1 listing of
  a volume whose `security --audit` or `summary` named the page of object 0x530.
- **An altered root page of a checkpoint table was read without a warning.** With one bit flipped in the root page
  of the Medium Allocator, `summary` and `files --csv` exited 0 and said nothing; so did `files --csv` with the root
  page of the Object Table's duplicate altered. Every command now checks, when it opens the volume, the root page of
  each of the checkpoint's 13 tables against the digest the checkpoint copy in use records for it: the Medium and
  Container Allocators, the Schema Table and its duplicate, the Parent-Child Table, Block RefCount, the Container
  Index, Integrity State and the Object Table's duplicate, beside the Object Table, the Container Table and the Small
  Allocator. A page that does not match, or cannot be verified, is named on stderr, the table is read as it is, and
  the command exits 2. The duplicates of the Object Table and the Schema Table, which are not read, are named as any
  backup copy that fails is: by `summary`, `fastsummary` and `integrity`, which exit 2 for them. *Re-check:* run
  `summary` with 1.14.0 on a volume examined with 1.13.1.
- **A hard-linked or moved file's stream snapshots were not listed.** `snapshots` and the `SnapshotCount` /
  `SnapshotNames` columns read a file's snapshots from its name row only; the driver keeps a hard-linked or moved
  file's snapshot rows in its backing record, so such a file showed none. They are now read from the backing; a file
  with several names is listed once, its other names named. No volume of the test corpus holds such a file.
  *Re-check:* the snapshots of a hard-linked or moved file in a 1.13.1 inventory.
- **A change journal holding no record was said to have bytes beyond its last record.** With non-zero bytes in `$J`
  and no record, `usn` called them ring space not yet written and gave no finding; nothing shows they are not records
  that are lost or removed. They are now named as bytes of a journal that holds no record, and the command exits 2.
  *Re-check:* a 1.13.1 `usn` run that printed "BEYOND the last record" and listed no record.
- **A per-object metadata bundle read as a volume of 0 objects.** A bundle written with `--btree-mode per-object`
  holds each object's pages without their addresses; read as input it gave a volume of 0 objects. It is now refused
  as input with the reason (exit 1); `verify-bundle` still checks it. *Re-check:* any 1.13.1 result read from such a
  bundle.
- **An MLog with no record left read as complete.** The check of the newest records counted from the
  newest record it found; with none left, `mlog --stats` printed "Log may be clean" and `summary --mlog` "none missing
  (the log end checked)", and both exited 0. A data area that holds no record of the volume's log, below a log end that
  says records were written, is now a finding (exit 2): the records are missing, and how many cannot be counted.
  *Re-check:* a volume on which 1.13.1's `mlog` found no redo record.
- **Bytes whose hole state could not be checked were written as checked.** On a host that cannot answer the hole query
  (no `SEEK_DATA`), `export snapshots`, `export resident-all`, `export recyclebin`, and `extract` (its main path, and an extent-backed
  ADS, a snapshot-shared file or a file whose extent map is held in its directory entry) wrote the bytes, also under
  `--refuse-holes`, and exited 0; the bulk exports' `holes.json` said `none`. On `win11refs4gattributes`, `export
  snapshots --refuse-holes` wrote its 4 versions that way. Where a stream was withheld for that reason (`export
  metadata`'s `usn_J.bin`), stderr said its bytes would have come from image holes. Each is now `undeterminable`,
  withheld under `--refuse-holes` with that cause given, and the command exits 2. *Re-check:* content exported or
  extracted with 1.13.1 on a host without `SEEK_DATA`.
- **Two statements of the 1.13.1 pages were wrong:** the MLog page said the commit flag (record +0x2C bit 1) is always
  0 on disk -- it is set on the last record of each transaction; the timestomp page said a creation time backdated
  below a snapshot of the same file is impossible -- one later than the snapshot is impossible, one below it is the
  normal order, so a snapshot does not catch backdating. *Re-check:* a conclusion drawn from either sentence.
- **Two labels of `timestomp`'s text misstated what it printed:** the column `Last real write` was the file's `$SI`
  Changed time, which a stomp through the native API sets too (the column is now `Changed`); the legend gave
  `ROUND_TIMESTAMPS` as `LOW only`, where the tier rule gives that signal alone INFO and never lets it raise a tier.
  *Re-check:* a conclusion that took that column for the time the file was last written (every release from 1.8 on
  printed it).

### Verdicts that follow refs.sys

- **The checkpoint in use is chosen as refs.sys chooses it**, by every command of both tools from one definition: the
  copies in slot order, a copy that fails its self-checksum skipped, a switch only to a strictly greater clock at
  `+0x60`, so a tie between two valid copies keeps slot 0 (read on 17134, 26100.8115 to .9549 and Insider 29574).
- **A clock divergence** (`+0x10` against `+0x60`) on either checkpoint copy, in use or not, keeps exit 2 in every
  command of both tools.
- **The superblock**: when no copy passes its self-checksum, the volume is read from the primary, said, and exit 2;
  a copy that passes refs.sys's tests but carries no `SUPB` signature is read, as the driver reads it, with the reason.
- **The Container Table** is read from root 7, and from root 8 only when root 7 fails, as the driver does; the two
  copies are compared row by row: a difference only in the rows' flags word is a note that leaves the exit code as
  it is (6 of 117 corpus volumes, bits 0x2000 / 0x4000 set in root 7 only; E135), any other difference a redundancy
  finding (exit 2).
- **The checksum type** is the one refs.sys derives: CRC64 when the boot sector's flags lack 0x40, whatever the
  selector byte `+0x2A` holds (E136). On the 16 corpus volumes in that state 1.13.1 printed `Checksum: none`. Type 5
  is named XXH64 (it is reported as not verifiable: its seed is not read).
- **A boot-sector container size of 0** (what `refsutil fixboot` writes) is a finding that names the value and the
  driver's default, with exit 2 in the five commands that read it.
- **A checkpoint whose record version is above the boot sector's** is a condition that changes what every command
  reads (exit 2): refs.sys 26100 and Insider 29574 fail the mount after choosing it; the volume is read as it is.
- **Checkpoint flag 0x400** is no longer called "metadata-checksum" (E141): it marks the record's rollback-protection
  fields, an offset and a length at `+0x9C` / `+0xA0`, set from ReFS 3.13 (E158); flag 0x2000 marks Insider's
  attestation HMAC at `+0xA4` / `+0xA8` (E159), and refsanalysis `chkp` names `+0x88` / `+0x8C` as the offset and
  length of an area of the record, not a "data area end" and a "max root capacity" (E159). Checkpoint flags 0x010, 0x020, 0x040 and 0x100 are named as four separate features (E126).
- **System tables kept in two copies** (0x7/0x8, 0x9/0xA, 0x500/0x501, 0x540/0x541) are named by their OIDs, not
  "primary" and "duplicate": neither copy is either (E121, E129).

### Content that came out wrong

- **A directory without a path** (`usn`, `mlog`, `timeline`, `deleted`) is `<undetermined 0x…>` when the Object Table,
  or the walk of the directory tree, was read only in part: whether it exists, or where it is, is not determined.
  1.13.1 wrote `<oid 0x…>` (gone) or `<unlinked 0x…>` there.
- **A file whose extent map is an index node** (Data Deduplication's `DedupIndex.db`, a sparse embedded `$DATA`) is
  decoded and extracted (`dataruns` 762 → 763 of 763 decoded on the dedup volume); `extract` streams a file above
  256 MiB to its output instead of holding it in memory.
- **On a volume without hard-link support, a moved file's identity** (`ObjectRef`, `HomeOID`, `IsMoved`) is the
  reference its record carries; 1.13.1 composed it from the directory the record sits in, which could give the
  `ObjectRef` of another file (E144).
- **`extract --id`** resolves a file in its own home directory only: a name with the same ordinal in another directory
  no longer stands in for it.
- **Two split-record backings with the same (home, file id)** resolve to no record, with a finding, instead of the
  first match (0 such collisions on the corpus).
- **v3.4 integrity streams** are verified (their CRC-32C is inline, E152).
- **`integrity --checksums` and `extract` say what an integrity file's clusters without a CRC-32C are**: a run marked
  never written holds no data (it reads as zeros; nothing to verify) and is counted on `Never written`; only a written
  run without a CRC-32C is "NOT verified". On the corpus all 670,385 such clusters (2,469 files, 10 volumes) are never
  written; the public sample's 46,723 among them.
- **`extract` verifies the integrity stream of a hard-linked or moved file**: its checksums are read from the file's
  own record (split out of its name row), as `integrity --checksums` reads them. 1.13.1 extracted such a file without
  checking it and exited 0, whatever its bytes. An empty hard-linked or moved symlink is named with its tag and target,
  as an embedded one is (1.13.1 said only that it is a reparse point).
- **refsanalysis `files` and `attributes`** count each file once (980 files, not 1,333 names, on
  `win11refs2tspecials`) and list a split file's named streams from its backing record (870 there, where 1.13.1 listed
  109).
- **`InternalFlags`** shows every bit that is set, bit 0x8 included (set on 583,088 of 586,970 non-zero values, the
  3.14 inline-residency files); `$SI+0x24` bit 0x02 is decoded as `CaseSensitive` (E125).
- **An extent node whose index names none of its rows** is read as a header that does not validate, not as a hole or
  a cut map.
- **A bulk export that cannot write a file exits 2.** It goes on with the other files, as 1.13.1 did, which exited 0.
  When it cannot write its list of them (`_extract_failures.json`: a full, read-only or missing directory) or
  `holes.json`, stderr says so and names the files or streams (the first 20); 1.13.1 pointed at the list it had not
  written and said it had written `holes.json`. `export_index.csv`, the recovery log and `extract`'s `.holes.json`
  that cannot be written exit 2 too.
- **`extract` of a stream that owns no clusters** (`unallocated`: no allocation of its own and no snapshot to share)
  writes its size in zeros, which is what every byte reads as, and says so; a regular output file holds them as a hole.
  1.13.1 wrote nothing and exited 2. `export file` writes it the same way.
- **`extract -o DIR`**, DIR an existing directory, is refused before anything is written; 1.13.1 wrote `DIR.holes.json`
  beside the directory and then refused.
- **An extent row whose flags declare a CRC64 per cluster** (0x100, which refs.sys writes and reads) is stepped over by
  its own declared size, and its clusters are said to be not verified (`extract`, `integrity --checksums`); 1.13.1
  ended the walk of the file's extents there. No corpus row carries one.
- **An extent row's file VCN** is read as the 64-bit field refs.sys writes; eight readers took its low 32 bits.
- **Labels that named a retired reading**: `summary`'s root list names the second copies `Object ID Table copy 2`,
  `Container Table copy 2` and `Schema Table copy 2` (1.13.1 `… dup`; neither copy is a primary); a type-0x40 row is a
  `Backing Record` (1.13.1 `Extent Descriptor`); OID 0x30 is the `Heat Engine Table` (1.13.1 `Session Activity
  Table`); `deleted`'s slack scan says a deletion removes the row's index slot and marks the row (1.13.1: it removes
  only the slot); `timestomp`'s legend says the journal recorded a basic-info change (not a deliberate one), that no
  routine cause of two names' disagreement was observed on the corpus, that driver packages carry whole-second times,
  and that legitimate time-setting comes from Windows servicing, installers and copies.
- **Help text**: `search --filter` lists `inline` (not the removed `resident`); `snapshots --snapshot` with part of a
  version name selects every version that contains it; `deleted --later-data` says the carve zero-fills those ranges
  with or without it; `deleted`'s cost figures are the measured ones, and so is `--verify-pages`' (about 1.3x on a
  command that walks the tree; the help said 3-6x); `dataruns` says an unallocated stream owns no clusters and reads as
  zeros (not "never written").

### Deleted files and carving

- **`deleted` is rewritten**: an entry is identified by its name, creation time and kind, checked against the live
  tree and, for an embedded row, the change journal; each entry has a status that says what it is.
- **One carve plan per remnant**, shared by the verdict and the carve; the CRC check covers every cluster that has one.
- **A live file's earlier extent map is not carved**: its clusters can hold the live file's current data. The entry
  says so (`not carved: the same file is live`), and the inline bytes of a live file's earlier row are held back the
  same way.
- **Pages of an earlier ReFS volume** on the same disk are recognised only where their own LCNs name where they lie
  (`deleted --earlier-volumes`); another signature alone also fires on a dedup index's pages or on never-written
  leftovers (E124).
- **The scan coverage lines** state the clusters read and how many of them are image holes, or that this could not be
  checked on this host.
- **A carve refusal states its reason** (a size of 0 B, no allocation with rows, sizes that disagree), and the carve
  cover guard bounds its scan by the node header.
- **`deleted` shows a table first**: for each page scan, every status by what can be recovered from its rows (bytes in
  the row, carve possible, metadata only, directory, empty), then one line per entry -- what can be recovered, the
  creation time, the name, the folder whose page held the row. `deleted -v` prints each entry's details as before.
- **A Trash-table row's `ObjectRef` is the deleted object's own**: the row's key is the object's reference (a file's
  `<directory>:<ordinal>`, a directory's `<oid>:0x0`); 1.13.1 printed the key's second half as the row's "OID", which
  for a file is its directory.
- **`help deleted`**: `deleted --full` writes nothing (only `export deleted DIR` carves); plain `deleted` is not
  described as taking seconds (197.5 s and 401.0 s were measured on two Windows Insider system volumes).
- **`files`, `search`, `details` and the body file lose a deleted mark that never fired** (`[DEL]`, "Is deleted", the
  body file's ` (deleted)`, `files`' "(0 deleted)"): an object waiting in the Trash is already out of its
  directory, so the walk never meets one.

### The change journal and the MLog

- **An MLog row's time is the latest time its records carry**, each record's value read where its form keeps its
  times: a `$SI` update's four times, a directory index entry's four, an embedded record's `$SI`. 1.13.1 took the
  first plausible time in a fixed order: a `$SI` update gave its Created and an index entry its Accessed (its change
  time was never read), so the records of a call that set a file's times back carried the forged date. On 121 corpus
  volumes 230,143 of 786,365 timed rows move, every one later; the rows dated before their volume was created go
  from 58,235 to 25,316 (a copied file keeps its source's times). A payload merges up to 15 redo blocks (1.13.1's
  help: 15 transactions).
- **The MLog's schema list (`mlog --info`, `mlog --parse -v`) names tables**, by format era (a file's record table,
  a directory's own-row table, a data stream's table …), not attributes.
- **A re-created journal is a finding** (exit 2) even when no record is missing, and `usn` / `usn --info` state which
  records belong to the current journal and which to an earlier one.
- **`mlog --json`** writes each record once and streams it; 1.13.1 wrote every record twice and could run out of
  memory on the largest logs.
- **A redo record's table is the one refs.sys applies it to.** `mlog` no longer reads a record's `+0x20` as an
  object id (E147: `+0x18` and `+0x20` are the volume's clocks when the record was added). A record without a table
  path applies to the table the driver's redo pass keeps current, the previous record's (kept into a redo block that
  continues a transaction);
  1.13.1 took that table from another record carrying the same `+0x20` value, so a rename could be called a move into
  an unrelated directory, and an alternate stream's creation a move. A name row is a directory's own entry only when
  its table path has one component, and a row shows its name in that name row's own directory. Checked against two
  independent operation logs: the 109 and 106 log payloads whose name rows pair with exactly one rename or move of
  the log (of 456 and 242) are all classed as the logs' paths say. `mlog --parse -v` marks a table taken from an
  earlier record `(inherited)`. A one-character name is read (1.13.1 skipped a 6-byte row key).
- **Opcode 0x2D is a table deletion** (`DELETE`, named `RedoDeleteTable`): Insider 29683 logs every table deletion
  with it, where the other builds read log 0x0F (E160); `mlog` and `timeline` say so on stderr when a log holds one.
  Opcodes 0x25 and 0x2B are named by their handlers, `RedoTableSetWeakRefPurge` and
  `RedoTableSetStrongRefMergeSingle` (E160), and `mlog --info` says which builds dispatch which values. `mlog`'s
  `Dispatch table:` line gives the values the table names and, above 0x2B, which of the builds read dispatch them
  (`45 opcodes: 0x0-0x2b, and 0x2d, which of the builds read only Insider 29683 dispatches`; 1.13.1 printed
  `44 opcodes`).
- **A name row in a directory's key form without a table path keeps its whole name**: 1.13.1 dropped its first six
  characters (`System Volume Information` was printed ` Volume Information`).
- **`usn`, `timeline` and `timestomp` read the journal faster**: a run of unwritten ring space is stepped over in one
  search (204 s → 29 s over the 39 corpus journals, 990,528 records, with the same records, findings and notes).
- **The journal's state** has one vocabulary in `summary`, `usn`, `timeline` and `timestomp`.
- **`mlog --stats`' Record Integrity note** names what the check misses: the value is the XOR of the record's 32-bit
  words, so a reordering of those words, or changes whose XOR cancels, keep it; a single changed bit or byte always
  changes it (E78). 1.13.1 said it catches damage and byte-level edits (`help mlog`: damage and edits), with no
  blind spot.

### New

- **What the output is**: `--list`, `--help` and each command's help say whether a command's output is read from the
  volume or inferred or recovered (corroborate before relying on it): `mlog --parse`, `timeline`, `timestomp`,
  `deleted`.
- **`summary` counts the files read after their last change** (`Last access`; `FilesAccessedAfterChange` in JSON): an
  Accessed time more than 1 s after both Modified and Changed says last-access updating seems to have been on; a
  program can also set an Accessed time, and none says nothing. `details`, `help files` and `timeline` say when an
  Accessed time is updated.
- **`details` on a directory** gives an embedded file's size and attributes, as for a split file, and no empty
  `Storage:` line for a subdirectory; `ads` explains its ObjectRef and residency columns.
- **`refsanalysis bootedit repair`** restores a damaged boot-sector or superblock copy from a healthy sibling (never
  from a copy that records another version); `--dry-run` shows the plan. Held back since 1.11.3, it ships now.
- **`files --cow-before OLD`** is a comparison of two images of the same volume: one row per object that was created,
  removed or changed, with the changed fields and their values before and after; images of two different volumes
  are refused.
- **`summary --mlog`** (or `summary -v`; refsanalysis `summary` too) adds an MLog section: the control copy in use and
  whether it verifies, the log version and range, and the earlier-log and missing-record findings, built on `mlog`'s
  code. Without the option the section says the log was not read: the pass over the log costs from 0.6 s to 38 s on
  the corpus volumes.
- **`usn --info` prints the checkpoint's journal cursor**: the change journal's position the checkpoint copy in use
  keeps (its next USN, and the first USN and wrap fields of a wrapped journal), with the count of the current
  journal's records at or past it, written after that checkpoint (none on the corpus). A copy without the area says
  that the checkpoint does not say where the journal stood.
- **`extract -o`** always writes `<file>.holes.json`, with status `none` when the file was checked and holds no hole.
- **`deleted` and `dataruns` decode each shared home tree once per walk** (`dataruns --json` on winsider 161.0 →
  119.9 s; no output changes on any corpus image).

### refsanalysis: its last update

**1.14.0 is the last version with refsanalysis updates.** refsanalysis is a lab tool; after this release it is not
maintained, and a defect found in it later is listed as a known issue on its page. It runs only with the forefst of
its own release, 1.14.0, and refuses another version, so no later forefst change can break it (and no later forefst
fix reaches it). In this release it uses forefst's own checkpoint selection, superblock checks and exit-code rules
(its copies of them are removed), and its `--verify` checks say `K check(s) FAILED (N/M passed)` and exit 2 when one
fails; `refsanalysis all` exits 2 when a section does. With another forefst it writes one line naming both versions and
exits 1. `containers -v`'s help names the columns it prints and `Total volume size` has the byte count; `attributes`
writes a SecurityId as `0x103 (259)`, as forefst's `security` lines now do; `details` writes `USN: (none)` for a file
with no journal record (it wrote `0` and a journal id of 0) and prints forefst's note under `Accessed:`; `boot` and
`bootedit` write the volume flags as the word with its bits' names, a bit without a name last:
`0x66 (WritableMount|HardLinksSupported|ChecksumSelectorRead|0x4)`.
`details --json` carries the journal id and the packed EA size its text prints (`USNJournalID`, `PackedEASize`). `summary++` gives the volume-information row keyed 0x540 as the verify block's location (`Verify block: LCN …, N
clusters`; `VerifyBlockLCN`, `VerifyBlockClusters`), not a schema count. `oid30` reads the heat engine's table: its
generations, and each row's role from its key and size (1.13.1: "sessions", "IO counters", "Category A-H"). `schema`
names the object schemas as the tables they describe, by format era (a file's record table, a directory's own-row
table, a data stream's table), not as attributes.

### Reference corrections

The errata ship with the repository from this release (`analysis/errata.md`, E1–E165). Filed during this release:

- **E116** — MLog control `+0x18` is the log start and `+0x20` the log end, each as of the last control-area write; `+0x18` is neither the log's tail nor where replay begins, and the "Generation" 1.13.1 printed is `+0x20`'s block offset.
- **E117** — MLog control `+0x38` is a u32 log open count, not a write counter; each record's header `+0x20` carries it.
- **E118** — A checkpoint record is one cluster on every geometry; only its allocation is a metadata page.
- **E119** — The superblock primary is privileged: `+0x68` orders only the two backups, and only an extend bumps it.
- **E120** — Container Table row `+0x20` counts allocated clusters, not free ones.
- **E121** — OID 0x7/0x8 and 0x9/0xA are failover pairs: no copy is the "primary" or the "duplicate", and the driver reads 0x8 and 0xA first.
- **E122** — `RefsIsBootSectorOurs` makes no version test, and its checksum runs to the boot sector's own length.
- **E123** — Redo opcodes 0x12 and 0x15 call no handler in `PerformRedo`; 0x12 is a tree-update record.
- **E124** — A page with another signature at +0x0C is an earlier volume's only at the address it names, in its own units; the LCN slots list one cluster on a 64 KiB page.
- **E125** — `$SI+0x24` bit 0x02 marks a case-sensitive directory, not dedup / CoW.
- **E126** — Checkpoint flags 0x010, 0x020, 0x040 and 0x100 are four separate features; only 0x010 is dedup.
- **E127** — `refsutil fixboot` rewrites the volume flags (0x66 -> 0x04) and writes a valid boot-sector checksum; a container size of 0 is replaced by the driver.
- **E128** — Boot-sector flags bit 0x20 is the hard-link support switch, not a "Win11 format" marker.
- **E129** — OID 0x500 / 0x501 and 0x540 / 0x541 are failover pairs: neither copy is a "primary" or a "duplicate".
- **E130** — The word at value+0x80 of the OID 0x520 children is the object's file id, not a "degenerate flag".
- **E131** — `RefsLinkFileToSelf` adds no name: the IsMoved rule has no "keep-alive link" exception.
- **E132** — A superblock copy's header clocks +0x10 / +0x18 are those of the moment the driver wrote that copy, not "0 (immutable)".
- **E133** — A hard-linked file's names diverge on Changed routinely: the per-name cross-check is a Created test.
- **E134** — `VersionCheck` compares with the volume's version from the boot sector, and its field is at +0x894 / +0x895 on Insider.
- **E135** — The Container Table's two copies differ in bits 0x2000 and 0x4000 of the row flags, not in bit 0x4000 alone.
- **E136** — The boot sector's checksum selector +0x2A is read only when its flags +0x2C carry 0x40.
- **E137** — Container Table row `+0x28` is not decoded: it is not "free clusters".
- **E138** — A boot-sector checksum selector of 0 is not a volume without metadata checksums.
- **E139** — Container Table row +0x50 is k units of 16 bytes before the ranges, and +0x98 is the first range's u64 length.
- **E140** — The 104-byte page reference is the checkpoint's root reference on 3.4-3.9, written at a fixed size; the root list decodes at that stride.
- **E141** — 17134 checks a metadata page against its reference's checksum type: `CmsChecksumNone` is the stream table's type-0 object, and checkpoint flag 0x400 is not a verification switch.
- **E142** — `$VOLUME_INFORMATION`+0xA0 is the time of the last mount that writes, not a modification time.
- **E143** — A directory listing does not refresh a hard link's stale name; an open, a read and a close through that name do.
- **E144** — On a volume without hard-link support a cross-directory move moves the whole record and leaves its reference at $SI+0x60 / +0x68.
- **E145** — A delete goes through the Trash only when the object's data stream set holds two or more tables, not for every non-resident file or directory.
- **E146** — A sparse hole's VLCN mirrors its file VCN on every hole row measured, so `VLCN == 0` fires on the holes at file VCN 0.
- **E147** — A redo record's +0x18 and +0x20 are the volume's virtual and allocator clocks when the record was added: +0x20 is not an object id and not a table handle.
- **E148** — The MLog control payload has no "Total entries" at +0x48 and no "Control UUID" at +0x50: +0x44 is the host info, the log instance's UUID is at +0x28.
- **E149** — The two checkpoint copies usually, not always, decode to the same 13-root list, and their bytes differ in more than the clock and checksums.
- **E150** — A Block Refcount entry is a 13-bit count of the references beyond the first: hard links and snapshots add none, and a range is shared at a count of 1.
- **E151** — An extent node's bit-0x04 row is a slot its key index does not list, the index word is not reliably the file VCN, and +0x04 is the end of the rows.
- **E152** — V3.4 integrity streams carry inline CRC-32C, and most integrity files also hold runs without one.
- **E153** — The EA chain: the data-area size is the chain's length, the last entry's NextEntryOffset is its own size, and PackedEaSize is a u16.
- **E154** — The checkpoint virtual clock counts checkpoints, not file operations or transactions.
- **E155** — The first user OID is 0x701, and a gap in the OID sequence is a deletion or a failed creation.
- **E156** — The volume-information driver stamp names the last writable mount's driver, not the highest; the label has no terminator.
- **E157** — The USN truth layer: createjournal grows but never shrinks, a range from 0 is not proof of a re-creation, and the Change Journal's sub-records are two $J data records and the $Max.
- **E158** — Checkpoint flag 0x400 marks a record that carries the rollback-protection fields: +0x9C and +0xA0 locate the blob, and are zero when there is none.
- **E159** — The checkpoint record locates its optional areas by (offset, length) pairs: +0x88 / +0x8C is a 32-byte area (not a "data area end" and a "max root capacity"), and flag 0x2000 marks Insider's attestation HMAC at +0xA4 / +0xA8.
- **E160** — The redo records' writers name opcodes 0x1A, 0x25 and 0x2B on 26100 too, and Insider 29683 logs a table deletion as 0x2D, not 0x0F.
- **E161** — `$SI+0x70` is the file's link count as the driver last wrote it: 1 in an embedded record, the number of names in a split record's backing.
- **E162** — The allocator covers the whole volume: its summary equals the volume's length on 117 of 117 corpus volumes; the 48 MiB once called "past the last container" is the image's bytes after the volume (corrects E74's coverage row).
- **E163** — `PerformRedo`'s current table belongs to the redo queue and carries into a redo block that continues a transaction; it is not emptied at a block's start.
- **E164** — `RefsLinkFileToSelf` copies no identity into each name: it runs once per file and re-parents the file's own table under the type-0x40 key {0x80000040, 0, file reference} (a key prefix, not a tag); each further name is written by `RefsAddLink` (amends E69's static sentence).
- **E165** — A file's main `$DATA` is single-instance when its data is inline (key marker 0x80000001, subtype 0x0000) and multi-instance when it is in extents (0x80000002, subtype 0x000E); a record carries one form, never both (corrects the master's marker tables, which listed `$DATA` as multi-instance only).

In the register (`analysis/reference_table.csv`): the clean-dismount row (on a cleanly dismounted volume the
highest Object Table log position equals the checkpoint's `+0x70`) is `FS_CHKP_RA_017`; it shared
`FS_CHKP_RA_012` with the checkpoint `+0x8C` row. The `static_scope` column names each `refs.sys` build one way
(`win10`, `win11.8115` to `win11.9818`, `insider.29574`, `insider.29659`, `insider.29683`), where it used seven
forms; `all`, which meant the six builds read at the time, is written out as those six, and 60 more rows have a
scope: the builds whose function index holds every function the row cites. Eight confirmed rows now name the image
and the file offset where their measurement can be checked (the MLog control payload, the Container Table's
allocated count, the extent flags, the checkpoint's `+0x88` / `+0x8C` and record size, the change journal's tail).
The checkpoint `+0x88` row lists every value measured (`0x370` on 3.10; `0x388`, `0x4D0` and `0x4D8` on some 3.14
records) where it gave `0x380` for 3.14.

### Corrections to earlier entries

- **1.13.0 did not list its MLog framing fix** (E97). Since 1.13.0, `mlog` reads every merged redo block of a log
  payload (up to 15) and gives each block the record budget its own header declares; 1.12.3 read 137 of the 746
  records of `win11refsmini`. The commit flag 1.12.3 reported as absent is set on the last record of each
  transaction (refs.sys `CmsMemLog::MergeTxLog`), and it is there on every block of the volumes measured.
- **1.13.1's carve count** is corrected in place (258 → 237, not 258 → 272).
- **1.13.0's hole contract** is corrected in place: the *cannot say* state reached `export deleted` and `export
  metadata`, not every path; the other bulk exports and three branches of `extract` have it from 1.14.0.
- **1.12.2's note on the driver stamp** is corrected in place (E156): the stamp names the driver of the last mount
  that could write, not every driver that touched the volume.
- **`timestomp`'s `ROUND_TIMESTAMPS` signal** was never listed here. It flags a file whose Created and Modified both
  fall on a whole second; on its own it gives INFO and never raises a tier. It has been in `timestomp` since August
  2026 (1.10.0, the earliest release copy at hand, carries it).
- **1.13.0's migration table** was a file outside the published tree; it is now part of [Migrating between
  releases](tools/migration.md#exit-codes-in-1130).

### Documentation

- A new first page, **ReFS Forensics 101**, and a **Value forms** section in the tool reference.
- A new background page, **[What ReFS Is](concepts/what_is_refs.md)**: what ReFS is for and why Microsoft built it,
  what it left out in 2012 and has gained since, where it is used (Windows Server, the client editions, Dev Drive)
  and how it compares with ZFS, Btrfs and APFS, each fact with its source; the concepts index lists it and Forensics
  101.
- A new page, **[Internals](tools/internals.md)**: how the two tools read a volume, function by function, the rule
  each step follows and the driver behaviour it comes from; a gate checks that every function it names exists.
- [Driver builds analysed](methodology/driver_builds.md) records six more `refs.sys` builds read: 26100.9549, .9711,
  .9818 and .9974 (no symbols are published for .9974: its machine code is compared with .9818's), and Insider 29659
  and 29683. A page's build scope names them where its fact was read there.
- `help extract` lists `-o FILE` / `--output FILE` and `--fill-holes`, and writes the reference `HomeOID:FileID`.
- The one-line `files` entry in `forefst list` / `help` called a directory's identity "a directory's own OID"; it
  is `OID:0x0`, the form `files`' own `ObjectRef` column writes.
- `help details` and the tools page named `$DATA` among the sub-records a file's detail view prints; it does not --
  the view lists ADS, `$EA`/WSL metadata and snapshots (a stream's own data is `dataruns`' command, not `details`').
- `verify-bundle`'s three help forms print one text, its usage names the bundle directory, and `forefst verify-bundle
  DIR` says the bundle comes first; `help files` no longer calls `files` the default subcommand (a bare run is
  `summary`), `help mlog` names the CSV columns as written, `help summary` lost a missing space.
- The Known issues are rewritten for 1.14.0: they now hold only what the tools do not read or check, each with what
  to do.
- The pages no longer carry finding ids or erratum numbers in their text; the knowledge map keeps each page's links.
- The Methodology page, the README, About and CONTRIBUTING state the method as it is practised: each claim is
  checked against the driver's code and the bytes on disk wherever both can be read, and the claim register records
  which of the two supports it. They said every claim met both, and that no claim rests on a single image; the
  register does not support either.
- The Methodology page's version tables: the 3.7, 3.9 and 3.10 volumes are native formats of Windows 11 21H2, 22H2
  and 23H2, whose drivers were not read (it said they are reached only by an upgrade); the twelve driver builds read
  are listed; 64 KiB clusters are exercised on 3.4 and 3.14 only, and the metadata checksum by format.
- Pages state what the work measured: the MLog page ties a mount to the Windows event log, shows the integrity check's
  blind spot on an untouched volume, and gives what two of its classes stood for on the public sample; the journal page
  says the USN, not the time, orders the writes; the file-ID page says only a creation uses up an ordinal; the
  `$STANDARD_INFORMATION` page gives how rare case-sensitive directories are; the `$DATA` page no longer gives a
  relationship for a field that was not measured.
- The Methodology pages say what the register holds: a grade on each axis that was checked, each row's disk status
  and origin, and that the register, the master reference and the errata together hold the findings (an erratum
  overrides both); the worked example follows one finding with the register's own figures.
- The Methodology page tells how the method grew, in six steps, each with the kind of error it catches: two
  readings of one structure (the thesis), one protocol for every claim, the register and its errata, fixed outputs
  and gates, reviews in other language-model sessions, and fixes that start from a failing test.
- The checksum pages say what a checksum that recomputes shows: that a page holds what the volume recorded for it,
  not that nobody edited it (the checksums are not keyed); and that the page references of a v3.4 volume carry CRC64
  too, which the v3.4 driver checks when it reads a page from disk; the version pages give the 3.10 checksum
  selector as a selector, not as the start of verification.
- The hard-link pages say where the link count is kept (the file's own record), and the NTFS comparison says that a
  file's reference, and the change journal's file ID, is its creation directory's object ID and an ordinal: a file
  has no object ID of its own.
- The Known issues add one for deleted files: an earlier version of a live file is not carved, and what the entry
  says about where its clusters are now.
- The samples page no longer says the 64 KiB sample holds integrity streams: its `testintegrity` directory holds no
  file that carries one.
- [Format support](format_support.md) counts a statement under a format only when a measurement on an image of
  that format confirmed it. A statement read only from the driver, inferred, not yet tested on an image, or
  contradicted by a measurement has its own column, and each area holds the statements about its structures.

## v1.13.1 — 2026-09-25 — a verdict that checked 127 of 55,586, and carves that were real

**Everything here is relative to v1.13.0**, and it corrects two things that release shipped: a verdict
that claimed more than it had checked, and published evidence that was wrong.

- **`integrity` checks every checksummed cluster, and says "every" only when it has.** On the public sample
  `win11refstestmftecmd`, 1.13.0 verified **127** clusters and printed "every checksummed file cluster
  matches"; the volume holds **55,586** checksummed clusters in **189** files, and 1.13.1 checks all of them.
  Five things kept the rest out of the check, silently: extent rows were stepped by their *size* instead of
  their 8-byte aligned *step*; a node's slots were walked in order, so a superseded slot could stand in
  front of the live row; a file whose extent map spans more than one node was read as having none; a
  hard-linked or moved file's checksums are in its own record, and the check looked at its name instead;
  and a record stored above the physical cluster count was treated as impossible. The check now reads each
  node through its key index as extraction does, reports clusters carrying a CRC and clusters checked, prints
  "every" only when they are equal, and treats any gap as a finding that sets the exit code.

- **Deleted-content recovery gets 14 files back.** The same misstep made the carve path read valid extent
  maps as broken ones and refuse the files; the 14 match their live twins where one exists. *Corrected in
  1.14.0:* this note first said recovery went "258 → 272 files, with 0 lost and 0 changed", which counts this
  fix alone. With the next item, the release's net on that sample is **258 → 237**: 14 regained, and 35
  refused because every run their rows describe is unwritten (20 of them differed from their live twin under
  1.13.0, 3 equalled it, 11 have no twin, and 1 is still carved by another path); 3 carves changed content.

- **A prior-version carve says what it zero-filled, on every path — and no longer reads what its row calls
  unwritten.** When a deleted remnant is an earlier version of a file, a range that version marks
  unwritten, or held as a sparse hole, is zero-filled, not read: at that moment the file held no data
  there, and unwritten clusters can hold another file's bytes. One of the three carve paths discarded the
  row's flags and read those runs anyway, merging whatever the clusters held later into the carve; it now
  follows the same rule. Nothing is silent: each such file gets a note naming the ranges and how many
  non-zero bytes lie under them now; `recovery_manifest.json` records `unwritten_runs`, `hole_runs`,
  `unwritten_zero_filled_bytes`, `unwritten_nonzero_on_disk_bytes` and `refused_all_unwritten`; a carve
  whose zeros cover data that is on disk now is no longer labelled `confidence: high`; and a carve refused
  because every run is unwritten says so.

- **`export deleted --carve --later-data`** writes what those zero-filled ranges hold on disk now as a
  separate `<name>.later` file, at their own offsets and nowhere else. It may be the file's later data or
  another file's, and it is never merged into the carve. On the public sample, a carve and its `.later`
  together reproduce every byte the previous carve path produced — 268 remnants, none lost.

- **A public carve oracle ships with the harness.** It checks every carve of the public sample against the
  file still on the volume with the same name and size, using only files that Windows' own journal —
  exported on the live system and shipped with the sample — shows were written once and never changed.
  A carve must equal that file, differ only inside ranges it disclosed, or be refused with a stated
  reason. 318 carves judged, 0 fail.

- **The v1.13.0 notes about recovered files were wrong, and are corrected.** They described the files
  1.13.0 stopped recovering as invented bytes and advised against relying on them. Compared with the files
  still present on the same volume, most of them are exact copies of real content. Files a 1.12.3 carve
  produced are not made unreliable by this release.

### The findings held at v1.13.0

Fifteen audit findings were held so 1.13.0 could ship; each is now fixed from a failing case, and where the
audit could not say what the right answer was, the answer comes from a source outside the tool.

- **A file's attributes and allocation come from its own record.** The name row carries a cached copy of
  both, and the cache goes stale. For a file whose record is split out of its name row (a hard link or a move
  forces that, and it stays split after the link is removed) `files`, `dataruns`, `reparse`, `export reparse` and
  `refsanalysis attributes` / `details` now report the attributes of the file's own record; Windows' change journal, which records the attributes the driver holds, agrees with that
  copy on 79 of 79 names where the two differ and with the cache on none. A row whose size was newer than its
  allocation (a live SQLite WAL: 3,271,312 bytes "in" 3,211,264) now reports the allocation its extent map
  covers. `refsanalysis files -v` prints the file's size rather than the name's cached one (202 rows on 44
  volumes were stale).
- **Older volumes.** Every embedded file on a v3.4 volume showed "File size: 0 bytes" in `refsanalysis
  details`; the size is read.
- **`summary` says what it does not check, and what "free" means.** A report without warnings means the
  metadata read cleanly; no file's data is read, and `summary` now says so on its last content line. The space
  line reads *not allocated* instead of *free*: Windows keeps part of that space in reserve and reports less
  as free. The used figure is unchanged — it equals Windows' own, exactly, where Windows' figure is on record.
  JSON adds `not_allocated_bytes` / `not_allocated`; the `free*` keys keep their names and value.
- **A damaged checkpoint no longer looks like a tampered-but-intact one.** A bootstrap copy whose stored
  self-address was zeroed is re-checked with it restored, and `summary` says whether that was the only damage.
- **USN `path` labels mean one thing each.** `<oid 0x…>` is a parent whose object is gone; a parent that still
  exists but has no name — a directory unlinked and not yet reclaimed — is `<unlinked 0x…>` (8,931 records on
  one real installation). Files in the root now get the leading `/` every other path has.
- **`timestomp`'s `storage` column says where the data is, and the hard-link check still sees every name.** One
  flag did both jobs: it printed the column and decided which rows the hard-link comparison skips. A small
  hard-linked file whose bytes are stored inline in its own record printed `(extents)` — 1,641 rows on 31
  volumes. The column now follows the same residency test as `files`, and the comparison groups a file's
  names by how its record is stored instead, so no group is lost: every verdict is unchanged over 482,425 rows.
  `refsanalysis files` prints `(inline)` / `(extents)` for the same rows. Both now use all five words `files` uses —
  a snapshot-shared or unallocated stream is no longer shown as `(extents)` — and so do the `Storage:` lines of
  `refsanalysis attributes` and `details`, which said RESIDENT / NON-RESIDENT from the same flag and now name the
  data residency and the record placement separately; `attributes` counts "Inline files" as `summary` does.
- **`timeline --oid` means the same thing in every source, and `--fileref` shows one file.** A file's `$SI`
  timestamps carried no OID, so `--oid` of a directory returned the USN and MLog events of the files created in it
  but not their timestamps; they are now filed under the file's home directory, as its USN events are, and the
  text header says so. A file stays filed there after a move, so `--oid` of its current parent does not select it.
  `--fileref HOME:ID` keeps one file's `$SI` and USN events under all its names; MLog events name a directory, not
  a file, and are left out with a note.
- **`refsanalysis allocators` says "not allocated" per tier too**, as the volume line does.
- **`--csv -` / `--json -` mean standard output in every command**, as documented. Commands that share the
  output-format parser (`timeline`, `timestomp`, `specials` among them) rejected the `-`.
- **`timestomp`'s screen view counts the INFO rows it hides.** The trailer read "0 MEDIUM + 0 LOW row(s) hidden"
  while hiding every INFO row (95 on one sample volume); it now counts them and names `--min INFO`, which shows
  them (INFO ranks below LOW, so `--min LOW` does not).
- **Smaller corrections.** A bare close reads `CLOSE` in both USN renderers and an unrecognised reason bit is
  shown, not dropped; `export resident-all` counts what it did not write by reason — an empty file as empty and a
  file whose bytes are in extents as non-inline, whatever its record's placement; `refsanalysis details` prints the
  FileRef `files` prints (for an embedded file whose data is in extents it printed two unrelated fields and a false
  "relocated" line) and finds the file however the path is typed; `details` of a directory gives each child's data
  residency and its own record's attributes, as `files` does; a symlink extracted as 0
  bytes says it is a reparse point and where it points; the journal's skipped-bytes warning counts bytes, not
  words, including the ones it used to step past, and unwritten ring space is reported as a note about the data,
  not as skipped work; the root directory's own USN records read `/`; the `deleted` slack line counts remnants
  and the names they belong to ("N split-record remnant(s) of M name(s)"); an alternate data stream is no longer listed as a snapshot's current version; the directory path map
  no longer contains one file per volume and reaches the full depth the listing does; forefst and refsanalysis
  share one directory walker, which terminates on a cyclic tree. The shipped sample bundles are regenerated from
  this release; the 1.13.0 bundles carried an empty `timestomp.csv` (its command was one the CLI rejects).

**Known issues.** Defects found while planning 1.14 are in this release and in 1.13.0; they were listed, with what to do meanwhile, in the section "Known issues in 1.13.1" of that release's `tools/forefst.md`. Release 1.14.0 fixes them: see [its entry](#the-known-issues-of-1131).

**Output that changes** (the columns and keys do not): `integrity --checksums` figures on every volume with
integrity streams; `files` `FileAttributes` on some split records and `AllocatedSize` on stale-cache rows; `usn` `path` for unlinked parents and root files; the `summary`
space line and one new line; `timestomp` `storage` on split files whose data is inline and on snapshot-shared or
unallocated streams; `timeline` `oid` on file `$SI` rows (it was blank) and a new `--fileref`; `refsanalysis files`
labels (`(inline)` / `(extents)`) and `-v` sizes on hard-linked names; `dataruns` `attrs=`, `reparse` /
`export reparse` `Attrs`, and `refsanalysis attributes` `Attributes:` on split records; the `Storage:` line and
summary count of `refsanalysis attributes` and the `Storage:` line / JSON `storage` of `refsanalysis details`;
the `deleted` slack line; `mlog --parse` "paths resolved" (one fewer: the bogus path-map key is gone); the
`refsanalysis summary++` space lines; the `timestomp` screen trailer; the `export resident-all` summary
counts; `details` of a directory (`Record` / `Storage` / `File attrs` per child); `refsanalysis details`
`FileRef` on embedded files; the `refsanalysis summary` Files line wording (`inline + extent-backed`).

## v1.13.0 — 2026-09-22 — the audit response: wrong bytes, wrong verdicts, and the checks that could not fail

**Everything here is relative to v1.12.3**, and it is the largest correctness release so far. It answers
a 215-finding audit made in another language-model session, given only the published material (a blind audit, part of
the project): **every `wrong_bytes` finding (18) and every `wrong_verdict` finding (51)
is now addressed**, each with a failing case built first and a measurement after. `AUDIT_RESPONSE.md`
lists all 215 with where the answer can be checked.

Exit codes and several messages change. The migration table is in [Migrating between
releases](tools/migration.md#exit-codes-in-1130) (*corrected in 1.14.0:* this note first named a report file that
the published tree does not hold); the short version is that **rc 2 now means
"a finding, OR I could not certify this clean"**, and a command that could not do all its work no longer
returns 0.

### Files that came out wrong now come out right

- **A truncated image no longer shortens the file, and no longer invents the missing bytes.** Assembling
  a stream used a slice assignment that *resizes* on a short read, so a read cut off by the end of the
  image shrank the buffer and every later extent landed shifted — 8,192 bytes delivered for a
  10,240-byte file, blamed on "a coverage gap or a sparse file" when the extents were perfect and the
  **image** ended. The bytes present are now placed correctly and the message names the real cause.
  A range **past the end of the image is known absent**, not ambiguous like a sparse hole, so the output
  now **ends at the last byte the image holds** rather than being zero-filled to the declared size:
  measured on a truncated `lab314_main`, the 1,813 bytes beyond the image end are non-zero in the real
  file, and all 1,813 zeros written in their place were wrong. `--fill-holes` opts back into the old
  form; both write the `.holes.json` sidecar and exit `2`.
- **VLCN 0 is no longer read as data.** One reader translated it like any other run and returned
  **volume cluster 0 — the boot sector** — as file content. It also capped streams at 512 MiB *silently*;
  it now refuses loudly rather than truncating.
- **A run that was allocated but never written reads as zeros**, not as whatever the clusters happen to
  hold. The flag that says "written" is `0x10`; without it the tool was serving stale disk content.
- **A snapshot version that cannot be resolved is no longer written as a 0-byte file** under that
  version's name — an artefact indistinguishable from a version that really was empty.
- **On 64 KiB volumes, a metadata bundle no longer loses the whole change log.** The MLog block index
  counts 4 KiB blocks; three consumers multiplied it by the cluster size. A freshly made bundle failed
  its own `verify-bundle` and reported "no redo records" where the image has 13,420.

### Verdicts that ignored their own findings

- **A verdict is now computed from every mismatch counter it prints.** The Object-Table page-reference
  counter was read **nowhere but its own print statement**, so a flipped byte in a directory's root page
  produced `Mismatched: 1` and, three lines later, "all N checksummed pages VERIFIED — no
  tampering/corruption", `PASS`, **rc 0**. Findings now go through one collector that both the verdict
  and the exit code read, and a gate (`check_finding_reachability.py`) asserts no counter is print-only
  — it immediately found a fourth instance, the MLog page-verification count.
- **An object's root page is verified on the listing and content paths**, not only its children.
  `--verify-pages` covered pages reached inside the walk; the root page comes from the Object Table and
  had no check. A flipped byte there now names the object and exits `2`, at a cost of 10 s → 47 s on a
  64 GB volume and **0 false alarms** on five clean volumes across 4K, 64K and 4Kn.
- **A damaged primary superblock is a finding on every command.** It exited `2` from `summary` and `0`
  from `files` and `integrity`, because the escalation read a hand-written list of registers.

### The content path verifies what it reads

- **`extract` and `export` now verify the metadata page a record came from.** The listing path checked
  an object's root page against the Object Table's digest; the content path resolved records through its
  own walk and never looked. On a volume with one byte flipped in a directory's root page, `files`
  warned and exited 2 while `extract` of a file recorded on that page wrote the bytes with **rc 0 and no
  note**. The check now runs wherever the walk can name its object — 27 call sites, one digest per object
  per run — so the evidence path answers the way the listing path does. Measured: **0 changed rows across
  121 undamaged images**, and a file on an intact page of a damaged volume still extracts silently at
  rc 0.

- **Deleted-content recovery no longer reads clusters a prior version never wrote.** A deleted remnant
  is often an earlier version of a file whose row marks some runs unwritten; those runs are zero-filled
  rather than read, because unwritten clusters can hold another file's bytes.

### Evidence that did not exist

- **Alternate data streams that were never there are gone** — 44 fabricated stream names across 28
  files. Live enumeration is now bounded by the node header's row count; the carve and slack paths keep
  the unbounded scan, because a deletion *decrements* that header while the slots below still address
  real rows. Carved content is unchanged.
- **`summary`'s "Total file size" no longer counts each hard-link name.** 25.3 GB → 14.7 GB on a
  Windows volume with a large WinSxS store; unchanged where there are no hard links.
- **A hole report names the stream it belongs to**, with the exact byte ranges, instead of naming the
  host file and explaining the gap with "shares blocks with other streams" — which was false on the
  volume it was printed for (0 of 1,235 runs overlap).
- **The metadata bundle's manifest declares split-record inline streams**, which it had been omitting:
  159 streams / 8,866 B becomes 326 / 17,040.
- **`timestomp --csv` gains `evidence_ref`**, naming the corroborating USN record or hard-link sibling
  behind every HIGH. The corroboration is now keyed by file identity rather than by name, which removes
  a large class of false positives: on one Windows volume HIGH falls 1,714 → 324, because the record
  that had been corroborating a live file by name belonged to a since-deleted namesake.
- **`refsanalysis` reads bytes-per-sector from the VBR**, so a 4Kn volume reports 3.9 GB, not 504.0 MB.
  It now *imports* the helper `forefst.py` already had, rather than carrying a second copy of the rule.

### Damage that used to read as health

- **A destroyed primary superblock no longer makes a readable volume unreadable.** ReFS keeps three
  copies; the tool now falls back to a verified backup and says the primary is gone.
- **A corrupted newest checkpoint is no longer used silently.** Selection follows the driver's own clock
  (`+0x60`) and verifies the page's self-checksum; when that means reading an older checkpoint, the run
  says so — **the view is stale** — instead of producing it quietly.
- **An uncleanly dismounted volume is now distinguishable from a recovered one.** On a clean dismount the
  checkpoint is written last, so the highest per-object log position equals the checkpoint's own; a
  volume torn away mid-work carries objects past it. Measured across 117 images, exactly one is ahead —
  the one that was.
- **`export metadata` no longer stamps "current" on the superseded checkpoint.** The role was assigned by
  the artefact's position in the superblock's list; ReFS alternates between two checkpoint copies, so that
  position is the stale one about half the time — on 58 of 117 corpus volumes. The label now follows the
  driver's selection clock (`+0x60`) and prints the clock beside it, so the choice can be checked rather
  than trusted. Where the old rule was already right, the verdict is unchanged.
- **A hand-edited boot sector is no longer echoed back as fact.** `Volume state` was built from the boot
  sector alone; an image declaring `v6.66` reported `NATIVE v6.66`. It is now corroborated against the
  checkpoint and `$VOLUME_INFORMATION`.
- **An allocator clock ahead of the checkpoint clock is a finding**, not two numbers printed two lines
  apart under "17/17 checks passed".
- **A journal whose tail was destroyed is detected.** Nothing inside `$J` can distinguish a wipe from
  unwritten ring space — but every file records the journal offset of its own last record, and those
  pointers survive the wipe. `timestomp` no longer calls such a journal an "authoritative cross-check".
- **`integrity --checksums` now verifies file data**, not only metadata pages: ReFS integrity streams are
  the volume's own mechanism for detecting tampering with content.
- **An empty listing caused by unreadable metadata says `LISTING FAILED`**, not `Wrote 0 entries`.

### Detection that was losing true positives

**`timestomp` correlated by filename.** A backdate followed by a rename put the evidence under the old
name, and two live namesakes blocked corroboration entirely — both dropped from HIGH to INFO. Every
negative case passed, so this was missed detection, not over-flagging. Correlation is now keyed on the
file's identity, which survives renames and separates namesakes. On one ordinary volume this recovers
**nine** true positives that were previously invisible; HIGH counts are unchanged on every other image.

### The hole contract, on more paths

Hole coverage has three states — present, none, and *this host cannot say* — and the third was reported
as the second on every path except `extract`'s main loop. A stream whose coverage was unknown was written
under `--refuse-holes` and its sidecar said `none`. `holes.json` now carries `undeterminable`, which `export
deleted` and `export metadata` record (the other bulk exports and three branches of `extract` record it from
1.14.0), and `export metadata` accepts `--refuse-holes` (it previously rejected it as an unknown option while
writing content assembled from the volume).

### Reference corrections

- **E104** — the Object-Table field at `value+0x18` is a per-object **log sequence number**, not a
  "generation counter = checkpoint virtual clock". Proven by a controlled three-image experiment with an
  untouched control, and confirmed on 15/15 volumes where the maximum equals the checkpoint's own LSN.
- **E105** — the superblock **does** carry a self-checksum, in its descriptor at `+0xD0`. The register
  said it did not, on the strength of a different offset being zero.
- **E106** — a container-table claim was refuted against the wrong origin: row-relative, `+0xA0` is the
  container start on every 160-byte row measured.
- **E107** — enabling integrity does **not** convert a resident stream; a file *born* under integrity is
  extent-backed from the start. The two questions had been merged.

### Also

`refsanalysis chkp --verify` verifies the checkpoint page's own checksum, and a run with a failing check
no longer ends "N/M checks passed". `--margin-days` refuses a negative or fractional value instead of
accepting it or leaking a Python error. Bundles record when an export failed rather than looking
complete, and `verify-bundle` runs its rehydrate check even when something else already failed — and
requires the rehydrated volume to contain something.

## v1.12.3 — 2026-09-13 — a retracted claim removed from the tool and every page

**Everything here is relative to v1.12.2.** One correction, and the check that keeps it corrected. No
change to how a volume is parsed; no file's data, timestamps or listing move.

### Comparing a hard-linked file's names does not clear it

The tool and twelve pages said that a name-scoped timestomp rewrites only the opened name, so the other
names keep the true birth — making a comparison across a file's names a self-contained tamper check, and
the latest Created among them the authentic one.

**A lab measurement had already refuted that.** Calling `SetFileTime` through one name of a two-name file
leaves **both** name rows byte-identical across their whole 84-byte value, timestamps included. The
ordinary tool updates every name at once.

What survives is narrower, and is what the tool and the pages now say:

- **A disagreement between a file's names is evidence.** It was observed on disk and nothing routine
  produces it. ReFS is genuinely different from NTFS here, where every hard link shares one `$SI` and the
  copies cannot diverge at all.
- **Agreement between them clears nothing.** It is exactly what a name-scoped `SetFileTime` leaves behind,
  and also what an untouched file looks like.
- **Which name holds the true birth is not established**, because the mechanism behind the observed
  divergence was never decompiled.

This mattered in the direction that matters most: the old wording invited an examiner to *clear* a
tampered file because its names agreed.

- **What to change:** if you have cleared a multi-name file on the strength of its names agreeing,
  that reasoning does not hold. The signal itself still fires on the same files.
- **Output changes.** The `timestomp` legend and two `--help` texts are reworded, and
  `HARDLINK_MACB_MISMATCH` now flags **every name** of a group whose Created values disagree, not only the
  older one. Flagging a single name asserted the others were clean, which is the claim being withdrawn.
  Expect **more** rows carrying this signal on a volume that has any — one per name in the group rather
  than one per group. No other signal, tier or file changes.

## v1.12.2 — 2026-09-13 — a bundle that holds what the reader needs

**Everything here is relative to v1.12.1.** Two defects in that release made a bundle disagree with the
volume it came from. Nothing about how a disk image is parsed changes, and no output on a disk image moves.

### A bundle was missing pages the reader asks for on demand

`export metadata` captured the pages its own walk enumerated. That is not the set a listing needs: some
backing records are fetched **on demand**, and those pages never reached the bundle. The result was a
bundle whose own `files --csv` disagreed with its source volume on **31 split-record files**, reporting
`HasADS=False` and `DataResidency=unknown` — wrong answers on an evidence artefact.

The export now runs a full listing against a recording handle and adds every page it touches. Listing a
bundle is byte-identical to listing its volume on all seven volumes tested, the 31 disagreements included.

Enumerating today's on-demand callers would have fixed the known cases and missed the next one; recording
what the reader actually reads covers readers added later too.

### A bundle understated the content it carries, by more than twenty times

The manifest's `inline_content` counted main streams only. Every alternate data stream raised an error that
was silently swallowed, so a volume whose bundle carries **113** inline streams reported **5**.

Both figures are now correct. This changed what the manifest *says*, not what the bundle *holds* — the
content was always there. If you have recorded an `inline_content` figure from a v1.12.1 bundle, re-export
to get the true one.

- **What to change:** nothing, but **re-export any v1.12.1 bundle you intend to rely on.** A bundle made by
  that version can be missing on-demand pages, which is not visible from the bundle itself.

### Skips are recorded rather than swallowed

Roughly a dozen places that discarded an exception now record what was skipped and why. This does not
change any result; it makes a partial answer say so.

### Correction (E96): nothing here is verified on ReFS 3.15, and the site no longer says otherwise

The tagline, the coverage line on the home and about pages, the verification page and the format-support
matrix all presented this project as covering **ReFS 3.4–3.15**. That was wrong.

**3.14 is the newest format any released Windows writes.** A preview driver reports a maximum supported
version of 3.15 and stamps that number into the volume's *driver* field when it mounts the volume for
writing. The field names the driver of the last writable mount: 3.15 there shows that the last mount that
could write was by a preview driver, a later writable mount by a released driver replaces it, and a
read-only mount leaves it, so its absence does not show that no preview build mounted the volume. *Corrected
in 1.14.0 (E156):* this note first called the stamp "a useful signal that a preview build touched a volume".
But no volume is *formatted* 3.15. The one
image in the corpus that reported 3.15 is a v3.14 volume with a hand-edited version byte, built alongside a
`6.66` twin to test how the tools handle an implausible version. A driver's maximum supported version had
been read as a volume format.

- **What to change:** nothing. No claim became less true and no output changed — each statement was verified
  on the volume it was always verified on. What changed is the name under which that verification was
  counted, and the removal of a published implication of evidence that does not exist.
- The format-support matrix now shows six formats instead of seven. **Every 3.14 count is unchanged**, because
  every statement that had been credited to 3.15 was already credited to 3.14 — which is what that volume is.

Reported by the project maintainer.

### A boot-sector version edited *downward* erases itself on the next mount

Investigating the 3.15 images turned up a behaviour worth an examiner's attention, now documented on
[Redundancy](concepts/redundancy.md).

The boot sector is duplicated, and a mismatch between the two copies is the standard way to spot a tampered
version field. That works only for tampering the driver leaves alone. A version set **below** the volume's
true format is **rewritten upward the next time the volume is mounted**, and the boot sector's own checksum
is recomputed with it — so a volume edited to an older version and then mounted once carries a boot sector
byte-for-byte identical to an untouched one.

Measured on a purpose-built series: one volume edited to 3.12 mounts, reads back 3.14, and its boot sector
matches the pristine one exactly. The same volume edited to an impossible 6.66 does **not** mount at all —
the image is unchanged after the attempt, checkpoint clock included.

**A consistent version field is not evidence the field was never altered.** Only an edit the driver does not
correct — a higher version, or an impossible one — survives to be caught by comparing the two copies.

### Which driver builds have been read

New page: [Driver Builds Analysed](methodology/driver_builds.md) — the `refs.sys` builds behind the structural
claims on this site, and what changed between them. Six builds spanning ReFS 3.4 to 3.14 and an Insider
build. Across the four 24H2 builds nothing on disk changed: the servicing updates rename functions, fold
one into its caller, graduate feature flags, and add a range check. A volume written by any of them is read
the same way.

## v1.12.1 — 2026-09-12 — read a metadata bundle without the disk

**Everything here is relative to v1.12.0.** One new capability and one new command; no change to how any
volume is parsed, and no output on a disk image moves.

### Point forefst at an `export metadata` bundle

`export metadata` has always written a hash-sealed set of the volume's structures. It can now be **read
back**: pass the bundle directory where you would pass an image.

```sh
forefst.py disk.raw export metadata ./bundle     # on the machine with the disk
forefst.py ./bundle files --csv                  # anywhere, later, without the disk
```

The bundle is rehydrated into a sparse image and read by the ordinary code path, so a bundle and its
source volume give the **same answers from the same parser** — there is no second way of addressing bytes.
Measured: `files --csv` from a bundle is **byte-identical** to the source volume on six volumes spanning
format 3.4 and 3.14, 4 KiB and 64 KiB clusters, SHA-256 checksums and snapshots. `usn`, `mlog`, `timeline`,
`deleted`, `security`, `ads`, `reparse`, `specials`, `snapshots`, `recyclebin` and `timestomp` all work.

- **What to change:** nothing. A bundle is a new kind of input, not a change to an old one.
- **Rehydration is sparse.** A bundle from a 2 TB volume reconstructs a 2 TB apparent file holding a few
  tens of MB; it never materialises dense.

### A bundle carries file content — inline content, and it says how much

"Metadata" understates what a bundle holds. ReFS stores a small stream **inside** the record, so every
inline file and inline ADS travels with the pages. **Sharing a bundle shares that content.**

The manifest now states the amount (`inline_content`), and the banner repeats it on every run. On one lab
volume that is 4,037 streams and 1.2 MB.

`--redact-inline` is **not** implemented and refuses rather than approximating: a first attempt located
payloads by searching for their bytes, and short payloads occur many times, so it zeroed 2 of 8 and left
the rest — two files checked afterwards still returned their original content. A flag that leaves content
behind while claiming redaction is worse than no flag.

### Extent-backed content is refused, not returned as zeros

A bundle holds no extent content. Asking for it returns **nothing and exits 2**, with a note saying the
bytes are not in the bundle — a different statement from the one a sparse *image* gets, where zeros
genuinely cannot be attributed. `deleted` and `snapshots` say in their header that their verdicts describe
the records, not the bytes.

### New: `verify-bundle`

```sh
forefst.py ./bundle verify-bundle      # exit 0 whole, 2 not
```

Checks the sha256 seal, the manifest's required fields, that every index row lies inside the blob it
indexes, and that the bundle rehydrates and bootstraps. Declared absences are reported as notes. A bundle
that fails is **refused on open** too, so a damaged bundle cannot be half-read.

### The bundle records where it came from

Every manifest now carries provenance — tool and version, source path, a content pin for the source image,
export time, host — plus the pages that were **already absent** when the bundle was made and the holes the
source image had at that moment. A derived artefact has to name what it was derived from.

### Fixed: a failed journal export was silent

The USN branch of `export metadata` was `except Exception: pass`. A failure produced a bundle silently
missing the journal, and nothing downstream could tell that from a volume that never had one. Both are now
recorded in the manifest and printed when the bundle is opened.

### Fixed: the shipped hole fixtures could not run from a clone

`run_hole_fixtures.py` pinned each image by hashing its **allocated extent map** as well as its bytes, so
the same volume unpacked a different way failed the check — `zstd -d`, `zstd -d --sparse` and
`cp --sparse=always` each produce different hole boundaries for byte-identical content. The pin is now
**content at fixed offsets**, which is the same for every unpacking, and the fixtures run from a clone.

### Documentation

The known-issue notice for the 1.11.3 decoder defect is retired — 1.12.0 fixed it.

## v1.12.0 — 2026-09-12 — one decoder order, and the consolidation

**Everything here is relative to v1.11.3.** Work in progress; this entry is written as the net effect for
someone upgrading from 1.11.3, not as a diary of the milestones behind it.

### Fixed: some files were mapped to the wrong clusters, and nine to the boot sector

A non-resident file's extent map is held in one of **two forms**, and forefst has a **structural reading**
for each: the nested B+-tree node, which is read through the node's own index array; and the plain holder,
whose entries are read at a fixed stride from a descriptor whose start, end, count and capacity must agree
before an entry is read. Behind both sits a **heuristic marker scan** that matches a 4-byte constant.

Through 1.11.3 the order was inverted, so the marker scan could answer first. The guard that accepts a
decode cannot catch that: a wrong single run of the right length covers the file's allocation exactly as
well as the right one does.

Measured across the whole corpus — **102 readable ReFS volumes**, in which 1.11.3 maps 109,567 files —
that was **11 distinct files mapped to the wrong clusters, 23 occurrences** (several of the files exist on
more than one image):

- **9 files were mapped to cluster 0, the volume boot record**, and `extract` returned 43 non-zero bytes of
  `ReFS` signature as though it were file content. Nothing warned.
- **1 file** was mapped through `0x000E0080`, a `$DATA` sub-record descriptor constant, and extracted as
  505,381 zero bytes. Its real content was recoverable all along.
- **1 file** was mapped from an unindexed row inside its own extent node.

- **What to change:** nothing. If you extracted one of those files with 1.11.3 or earlier, re-extract it.
- **Where it could bite:** ReFS 3.7, 3.9, 3.10 and 3.14; both 4K and 64K clusters. Rare — 23 of the
  109,567 files 1.11.3 maps — but silent.

### 593 more files get a decoded extent map — 152 of them proven, 441 not

The structural decoder resolves maps the marker scan could not, so files that previously reported no
extents now report them. Counted across every readable volume in the corpus: **593 files** that 1.11.3
could not map, 1.12.0 maps. On one ReFS 3.7 volume, files with decoded extents go from **469 to 508**.

**"Decodes now" is not "decodes correctly", so here is the split.** Of the 593:

- **152 are byte-proven** — the bytes carry the lab generator's content marker, a record this project did
  not produce.
- **441 are unproven.** They decode and return real content — a 12-file random sample returned 77 KB to
  509 KB each, over 99 % non-zero bytes, and **none returned zeros** — but no independent record confirms
  those bytes. They sit on volumes with no inventory and no content marker.
- A second implementation (`refscat`) corroborates a small number where it can read them at all: on one
  4 KiB volume, **3 of 49** byte-identical, **0 disagreements**, 46 unreadable by it.

If you are relying on one of these files as evidence, corroborate it. `dataruns` names the reading that
produced each map.

Run boundaries are also now reported as the node records them, so a file's extent **count** can change
while its clusters do not — `extents=2` becoming `extents=5` for the same 46 clusters. No bytes change.

### Scope

This changes the decoder **order** only. All three decoders remain, and the index array is still the only
one that answers on ReFS 3.4.

### `deleted` now says when a map came from the heuristic

Three readings can produce a file's extent map; one of them — the marker scan — matches a 4-byte constant
and is accepted only if it exactly covers the file's allocation. A coincidence can satisfy that too. On
**live** files it now never answers. On **deleted remnants** it is often the only reading that recovers
anything, so it stays — and when it produced a map, `deleted` prints a note on stderr saying how many maps
came from it. The note appears on 42 of the 106 corpus volumes. **No recovered data changed**: on every one
of those volumes `deleted`'s output is byte-identical to 1.11.3.

### Also

- **The checks now ship, so you can re-run them from a clone.** `analysis/verification/` carries the hole
  fixtures (`hole_fixtures.tsv` + `run_hole_fixtures.py`), the single-source list and its lint, and two
  documentation checks that need **no disk image at all**: one fails if two pages state the same fact with
  different numbers, the other if a page states a load-bearing figure that disagrees with the reference.
- **The worked examples are now covered.** The check that runs every documented command read three files;
  the step-by-step walkthrough pages set a shell variable for the image, so none of their commands was ever
  run. It now reads the fenced command blocks on every page — 129 commands instead of 102, and all of them
  are accepted by the CLI.

## v1.11.3 — 2026-09-11 — `--refuse-holes` does what the page says, on every path

**Everything here is relative to v1.11.2.** One correctness fix on a safety flag; no output changes for
files that draw no bytes from image holes.

### Fixed: `--refuse-holes` wrote the bytes it promised to withhold

1.11.2 routed every content producer through one hole check, but `extract` reports the result on four
different code paths and only one of them carried the whole contract. On a **snapshot-shared
(copy-on-write)** file, an **extent-backed alternate data stream**, or a file whose extent map is held
**inline**, `extract` printed the note but wrote no `FILE.holes.json`, and under `--refuse-holes` it wrote
the bytes anyway. The tool page said it did both.

The inline-holder path also exited **0** — a file whose bytes came from image holes reported success.

- **What to change:** nothing, unless you scripted around the bug. `--refuse-holes` now withholds the
  bytes on every path, `-o FILE` always produces `FILE.holes.json` when holes were involved, and a
  hole-sourced extract always exits 2.
- **On shared-cluster paths the sidecar reports a byte count, not file-relative ranges**, and says so
  (`"ranges_available": false`). A stream reassembled from blocks it shares with other streams does not
  know the intervals; the alternative was inventing them.

### Why it needed a structural change rather than a patch

`extract` had nine places that wrote bytes and the hole report lived at the bottom of one of them. That
shape has now produced three separate findings, each fixed where it was found. There is now a single
content exit that every branch returns through, and the writer can only be called from it — asserted by a
gate check, so a new branch cannot emit content without the report attached.

### Also

- Four helpers that returned `None` both for "this record does not exist" and for "the lookup failed" can
  now tell a caller which it was. Callers that do not ask are unchanged.
- `snapshots --extract` — the command that reassembles snapshot content — is covered by the release
  fingerprint for the first time; it previously had none.

## v1.11.2 — 2026-09-10 — a wrong-bytes fix, and the hole check on every producer

**Everything here is relative to v1.11.1.** One correctness fix that can change which bytes you get, and
one behaviour change: the bulk export commands can now exit **2**.

### Fixed: two files differing only by case could serve each other's bytes

A directory carrying the per-directory case-sensitivity flag (`fsutil file setCaseSensitiveInfo`) can hold
two names that differ only by case; the B+-tree then compares keys binary rather than case-folded. Path
resolution folded case for every comparison and took the **first** matching row, so on such a directory
every spelling resolved to whichever name came first in tree order.

`extract /dir/hi.txt` could therefore write `/dir/HI.txt`'s bytes — the wrong file, under the requested
name, with exit 0 and no warning. `--id` resolves through the same code and was wrong in the same way.
Listing was never affected: `files` showed both names with their distinct ObjectRefs throughout.

- **What to change:** nothing. An exact spelling now wins; a case-insensitive match is still accepted as a
  fallback, so wrong-case paths keep resolving on ordinary directories.
- **Where it could bite:** only volumes with a case-sensitive directory — rare, and the reason this
  survived: no corpus image exercised it until one with an operator SHA-256 inventory did.

### The hole check covers every content producer

1.11.1 reported hole-sourced bytes for `extract` only. Every content path now reports them with the same
wording: prior-version (copy-on-write) content, snapshot versions, extent-backed alternate data streams,
carved content, the inline-holder reassembler, and the shared reader behind `recyclebin` and
`export recyclebin` — which reassembled extents on its own and asked about holes only when its output was
entirely zero, so a partially unacquired file was never flagged.

Every producer now clips to the stream's logical size, so a hole in a file's **tail slack** is no longer
reported: slack is not content. On the shipped sample this took one snapshot version from 69,632 to 67,299
reported bytes, all of the difference being padding past end-of-file.

The bulk export commands now report holes the way `extract` always has: a note, a `holes.json` sidecar in
the export directory, and **exit 2**. `--refuse-holes` works on them too.

- **What to change:** if a script treats any non-zero exit from `export deleted`, `export snapshots`,
  `export resident-all`, `export recyclebin` or `export metadata` as failure, it will now see **2** on a
  sparsely-stored image where some bytes came from image holes. As with `extract`, `rc == 2` means *read
  the note*, not *something went wrong*; usage errors are still 1.
- `--refuse-holes` withholds **per stream**: affected outputs are not written, clean ones still are, and
  the refused list is in the sidecar. Refusing a whole run because one file was affected would discard
  good evidence.
- The sidecar is written even when nothing drew from holes (`"status": "none"`), so a missing sidecar
  never has to be read as "checked and clean".

### One more producer, and a lint that finds the next one

`export metadata` writes the USN `$J` change-journal stream to `usn_J.bin`. Those bytes are read from
clusters and were never hole-checked, so on a sparsely-stored image a punched cluster became a zero-filled
stretch of journal presented as the volume's own record. It now goes through the same check.

It was found by strengthening the check that is supposed to catch this: instead of only verifying a
declared list, the lint now **discovers** candidates — any function that reads the image and returns bytes
must be a declared producer or carry a written exemption. The declared list had been the only defence, and
it had already missed one producer.

## v1.11.1 — 2026-09-09 — the flag 1.11.0 promised for one release, and the end of the label vocabulary

**Everything here is relative to v1.11.0.** One breaking output change (`search`'s `oid` placeholder) and
one label pass; everything else is output-neutral.

### `--legacy-link-join` is removed

v1.11.0 kept the pre-1.11 six-branch resolution ladder behind the flag "for one release". It is gone,
along with the ladder and the now-dead local `(parent_oid, file_id)` lookup that only it consumed. The
object's home is the only resolution path.

The flag had in fact been promised for one release **twice** — v1.10.0 introduced it for the E89
on-demand home lookup and said the same thing. It survived five releases.

- **What to change:** `--legacy-link-join` now exits 1 as an unknown option. It resolved the same records
  as the default on every corpus image, so no result produced with it differs from one produced without.

### Correction: the second resolution assertion does *not* retire

The 1.11.0 changelog said the older path-agreement assertion "stops testing anything once
`--legacy-link-join` is removed". **That was wrong.** It compares `walk_directory_tree`/`_home_t40`
against `_analyze_dir_extents`/`_home_streams` — two separate implementations that both still exist, and
that removing a CLI option does not merge. It stays, and retires when those two paths merge.

Stated here rather than by editing the 1.11.0 entry, which is a record of what that release shipped.

### Breaking: `search` says `(inline)` / `(extents)`, and the label vocabulary is finished

E87 established that *resident* named two different things: **record placement** (embedded vs split) and
**data residency** (inline vs extents). 1.11.0 renamed the `DataResidency` value; **thirteen** output labels
still used the ambiguous word. They are now assigned by axis:

- **placement** — the reparse tag reads `[split record]`; the slack join reports `split-record file(s)`
- **data** — the walk log, the deleted-recovery counts and the carve hints read `inline` / `extent-backed`

**Two of the thirteen are structured values, and both are breaking:**

- **`search`'s `oid` field** emitted `(resident)` / `(non-res)` for a row with no OID; now `(inline)` /
  `(extents)`. The `id` field beside it is unchanged and remains the identity to parse.
- **`timestomp`'s `storage` column** (text and `--csv`) emitted the same pair; now the same replacements.

Both carry the DATA axis — the walk sets `record_embedded` as placement and refines `is_resident` from
the `$DATA` descriptor — so the words now match what `files` prints.

**This completes the rename begun in 1.11.0. No further label change is planned.**

Defects fixed with it, in the vocabulary's own documentation: `_data_residency`'s docstring — the function
that *defines* the vocabulary — still listed `sparse`, a value 1.11.0 had renamed; `export resident-all`
printed `CoW-shared` where the tool's value is `snapshot-shared`; and four pages, **including the glossary
and the residency value table**, still named the residency value `sparse`.

`--filter sparse`, `specials sparse` and the `IsSparse` column are untouched — they report the
`FILE_ATTRIBUTE_SPARSE_FILE` bit, a different fact from the residency state.

### Large sparse files no longer reassemble at three times their size

`_recover_inline_extent_content` allocated a buffer at exactly the stream size, then returned
`bytes(buf[:stream_size])` — a slice copy of a buffer already that length, so a reassembly held **three**
copies of the file at once. On a 2,556 MiB stream that is roughly 7.6 GiB of live memory.

This is on the extraction path: anyone reassembling a large sparse file paid it. The bytes returned are
identical; only the peak allocation changes.

### Evidence paths no longer answer with a default

A path that produces bytes, a size or a verdict must not swallow a failure and return a plausible value.
Four cases where it did — none of which fires on a healthy image, which is exactly why they went unseen:

- **`integrity` could report a clean verdict over a volume it had not fully read.** A page that could not
  be *read* took the same exit as a page that is not a B+ page: unchecked, uncounted, unmentioned. The
  command now counts unreadable pages and says so — `the N checksummed pages that COULD be read
  VERIFIED — M page(s) were unreadable and are NOT covered`.
- **`--refuse-holes` did not refuse when hole coverage could not be determined.** "I cannot tell" was
  treated as "no holes". It now refuses, and the ordinary path warns. The default exit stays 0: the usual
  cause is a filesystem without `SEEK_DATA`/`SEEK_HOLE`, which says nothing about the evidence.
- **A file could be written with zero-filled clusters where a snapshot-shared block failed to resolve.**
  Four paths in the live-content reassembler ended that way; they now defer rather than emit.
- **Counts that read as facts** — security descriptors, reparse entries, trash rows, symlinks, snapshots
  and an unrenderable timestamp all defaulted silently. Each now records the failure and reports it at
  exit.

### Documentation now has to match the tool

Three worked examples showed output the tool no longer produces — one of them for three releases. The
`search` example predated the `ObjectRef` rename; a `files --csv` example told the reader to filter on
field 5, which is `FileSize` rather than `FileName`, so the documented command matched nothing; and the
timestomping example claimed two agreeing heuristic signals *earn* the HIGH tier when the tool rates that
pair **INFO**. All three are regenerated from real runs.

Four pages, including the glossary and the residency value table, still named the residency value
`sparse` after 1.11.0 renamed it `unallocated`.

Two checks now run in the gate: documented labels must be ones the tool can emit, and documented column
headers must match what the tool prints. Both read the tool rather than a frozen list, so a rename cannot
leave them asserting the past.

### Smaller

- `details` gained golden coverage — 1.11.0's per-stream ADS residency had shipped through a command no
  fingerprint touched.
- The claim register gains a machine-readable verification scope for five more rows; 74 remain unrecorded
  and are counted as unverified rather than assumed.
- **New: `docs/format_support.md`** — a generated table of which ReFS formats each area of the project has
  been *verified on*, built from the register's verification scope alone rather than from what a claim
  asserts. Rows whose scope was never recorded get their own column instead of being dropped, so coverage
  is not overstated where it is least documented. Repo-facing for now; not published to the website.

## v1.11.0 — 2026-09-08 — one identity format, one timestomp surface, one resolution path

**Everything here is relative to [v1.10.3].** Four output changes are **breaking**; each is listed below
with what a consumer must do.

### Breaking: `files` is a fixed 40 columns

`TimestompFlags` **and** the `--timestomp` flag are removed. The column carried a tier computed without the
change journal — the walk does not read `$J` — so it could only ever report the half of the answer that a
timestamp-preserving copy also produces, while sitting in a column that looked like a verdict.
Timestamp-anomaly information now comes from `timestomp` alone.

The schema is now **fixed** at 40 columns rather than 40-or-41 depending on a flag. That was the point of
removing the flag as well as the column: an earlier fix had already made `--no-timestomp` *blank* the
column rather than drop it, precisely to keep the schema stable, and re-introducing a flag that changes the
column count would have undone it.

- **What to change:** read the tier from `forefst.py IMG timestomp --csv`. `--timestomp` and
  `--no-timestomp` now exit 1 as unknown options.
- The regression assertion that pinned *column == command* retires with the column: with one surface there
  is no second ladder to guard. The unit assertions on `timestomp_verdict()` remain.

### Breaking: `DataResidency` says `unallocated`, not `sparse`

One word named two different things in the same output — the residency state (*this stream has no
allocation behind it*) and the `FILE_ATTRIBUTE_SPARSE_FILE` bit that `IsSparse`, `--filter sparse` and
`specials sparse` report. Those three are unchanged; only the residency value is renamed. `dataruns` prints
`UNALLOC` for the same state, and that label is now documented — it never was.

- **What to change:** a filter on `DataResidency == "sparse"` matches nothing; use `"unallocated"`.

### Breaking: a directory's `ObjectRef` is `0x600:0x0`

The column now carries one format for every row. A directory is its own home with ordinal 0 — which is
exactly what the change journal writes for a directory's self-reference — so it renders `0x70e:0x0` rather
than a bare `0x70e`. Previously a consumer had to branch on row type to parse a single column.

### Named streams say where their bytes are

`details` and `specials ads` now print each stream's residency beside its name, from the same parser
`export ads` uses. An ADS below 2 KiB is inline; at or above it the bytes are in a type-0x0 extent record
and the name row holds only the descriptor. Printing a name alone invited the reader to assume the content
was in the record. No column was added; `files` stays at 40.

### One name→record resolution path

`walk_directory_tree` resolved a split name through a six-branch ladder that tried the local
`(parent_oid, file_id)` key before the object's home. `file_id` is a **per-directory ordinal**, so the local
key can name a different object that merely holds that ordinal in the same directory.

The local branches were reachable but never decisive: removing them changes **no output on any corpus
image** — the release golden is byte-identical across it. This is a simplification, not a correction: six
branches become one, and `--legacy-link-join` restores the old ladder for one release.

- **A new regression assertion** checks the resolution against the driver rather than against a second
  implementation: every split name must be listed by its resolved backing's own type-0x39 link set — the
  list ReFS itself writes. **83,521 names, on the 64 corpus images that contain a split name, 0
  exceptions.** It catches something the
  existing path-agreement assertion cannot: two implementations can agree and both be wrong. It also
  outlives the other one, which stops testing anything once `--legacy-link-join` is removed — **that
  assertion retires in the next release, with the flag.**

### The register's evidence columns are machine-readable

`reference_table.csv` gains seven derived columns and keeps both old ones unchanged, so nothing that read
it before reads differently: `static_evidence` · `static_scope` · `disk_examined` · `disk_status` ·
`origin` · `format_claimed` · `format_verified`.

Two of those exist because the data required them. `refs_version` says what a claim is **about** and
`verified_on` says what it was **checked on**, and on **69 rows** the claim names a format the
verification never covered — so they are two columns, and the support matrix builds from
`format_verified` alone. And an `RD` marker in the old static column meant *the disk was read*,
which is not what the reading concluded: of the 116 rows that carry it, 10 have a non-confirmed
outcome, and 221 rows are disk-confirmed without carrying it — so neither ever implied the other.

`format_verified` reads `unknown` on **79 rows** whose `verified_on` holds an audit date rather than a
version. Those are treated as **not verified**, and recorded as a data-quality item.

### Documentation

Every register row that a page's text already supported is now cited there: **16 of 482** rows are
still uncited, against the **299 of 473** the 2026-09-07 triage measured on the same scope (the five
content directories, each `README.md` excluded). All 16 are internal-only — tool defects, superseded
prior work, censuses — which are owed nothing. New material where the citation had nowhere to land:
the `_SmsIndexRoot` root descriptor and how it differs from the node header on the same page; prior
work's seven MLog operation patterns re-measured (three reproduce exactly, one is mislabelled, one
does not occur as a single transaction, two are reordered); where a split record keeps its streams
and its reparse buffer; what a snapshot does to reported residency; sparse ratios; image holes; EFS
on disk; the two deletion paths.

**One register row corrected.** `MD_DATA_RA_026` described a reader defect as *not fixed*. It was fixed
in v1.10 — its own erratum (E89) has said so since — and the row never caught up. Re-measured before
this release by running the walk with and without `--legacy-link-join`, which disables the fix: 1,012
rows differ over 124 images, including the 548 on `winsider` that E89 reports, to the digit.

**A new gate** fails when a page claims verification on a format its cited findings were never verified on.

## v1.10.3 — 2026-09-07 — three defects the purpose-built lab volumes found

**Everything here is relative to v1.10.2.** No new decoders and no new columns. Seven lab tests were read
against volumes built to create cases the corpus did not contain; four confirmed the documented model and
three found defects. All three are fixed here.

### `export deleted` no longer writes content it does not hold

A deleted file's remnant can keep its `$DATA` descriptor while losing the bytes the descriptor describes.
The recoverability verdict was decided by the value's *length*, so such a remnant was graded
`recoverable_inline`, reported as **"FULL FILE recoverable … EXACT"**, and written out as a file of zeros.

- A new outcome, **`content_zero_or_absent`** — *"content zero or absent (indistinguishable in the
  remnant)"*, reliability `NO CONTENT` — covers it. The verdict names **both** explanations because the
  remnant cannot separate them: the file held zeros, or the deletion took the bytes. The record, its name,
  size and timestamps are still reported; no content file is written either way.
- Measured before → after, content files written / all-zero among them: `winsider` **8,459 / 6,110 → 2,349 /
  0**, `lab314_main` 877 / 228 → 649 / 0, `win11refs8g` 72 / 57 → 15 / 0, `win11refstestmftecmd` 15 / 11 →
  4 / 0. On every image the number withheld equals the previous all-zero count, so **no populated content
  was lost**.
- The proof that those zeros were fabricated rather than real: the lab generator wrote the same 300
  non-zero bytes to every one of 8,000 files, and 214 of the 849 recovered came back as 300 zeros.
- **A genuinely zero-filled resident file is withheld too.** That cost is measured — 1 of 4,037 live
  resident files on one volume, 1 of 33,263 on another — and it is the right side to err on: the metadata
  is still reported, and an evidence tool should not assert bytes it never read.

### Named streams on moved and hard-linked files are visible again

Stream enumeration read only the directory-entry row. When a move or a hard link splits a file's record,
its `0xB0` stream sub-records live in the type-0x40 backing, which nothing inspected — so those files
reported **no streams at all**, in `files`, in `specials ads`, and in `extract "file:stream"`.

- All three now enumerate from the backing. `extract "…:s500"` on a moved host returns the stream's bytes,
  SHA-256-identical to the value recorded on the volume when it was made.
- Split-record rows carrying streams, before → after: **0 → 178**, **0 → 179**, **0 → 95** on three
  volumes. Corpus-wide, 655 backing records on 28 of 102 images held streams no command could reach.
- The code asserted this path was complete, citing a corpus recount that agreed exactly (678 == 678). The
  recount was sound; the conclusion was not. No corpus image had a stream on a moved file, so the case the
  branch could not handle was simply absent from the evidence.

### The timestomp legend now describes the tiers the tool actually assigns

The printed legend promised *"HIGH = >=2 independent signals or 1 authoritative"*. `timestomp_verdict()`
awards HIGH **only** for an authoritative corroboration — the change journal, or a hard-link sibling — and
never for a count of heuristic signals. On a controlled set of eight files with one known manipulation
each, six are flagged and all six are INFO, which is correct: every signal they carry is one a
timestamp-preserving copy also produces.

- All **three** descriptions are rewritten from the verdict function: the table header, the subcommand help
  text, and the docstring. **The tier logic is unchanged** — only the descriptions were wrong.

### Documentation

- `usn_journal.md` gains the **journal-recreation signal**. `fsutil usn createjournal` does not resize the
  journal on ReFS and does not merely reset a counter: it discards the history. A request for 1 MiB
  produced a 32 MiB journal with delta 0, nothing wrapped, and no pre-call record survived. A USN range
  starting at **0** on a volume with prior activity means the journal was recreated — so absence of a
  record in it is not evidence the operation did not happen.

## v1.10.2 — 2026-09-07 — release hygiene: what the tool says, what the docs say, and what the site serves

**Everything here is relative to v1.10.1.** No new decoders and no new columns. This release closes the gap
between three things that had drifted apart: the tool's own wording, the documentation, and the published
artefacts.

### `dataruns` now speaks the whole residency vocabulary

- v1.10.1 gave `dataruns` two data states, `inline` and `extents`. ReFS has four. A **snapshot-shared**
  stream — one that owns no allocation because its bytes are still the snapshot's — was printed as
  "bytes stored in the record", which is wrong twice over: the bytes are neither inline nor this stream's.
  `dataruns` now resolves residency through `_stream_data_form()`, the same classifier `files` uses, and
  prints `SHARED` and `SPARSE` alongside `INLINE` and `EXTENT`, with a per-state summary line.
- **A regression assertion now holds the two commands together**: `dataruns` and `files` must report the
  same residency for every file. Measured across the corpus — **521,060 files on 96 volumes, 0
  disagreements**. The listing and the data-run view can no longer drift apart silently.

### Hole reporting says what it means

- `FILE.holes.json` and the `extract` note **merge adjacent ranges**. A hole crossing an extent boundary was
  reported as two entries (`0–4095`, `4096–97672`); that split described the extent map, not the hole. The
  byte total was always right — the range list now is too.
- The `timestomp` trailer no longer says "an intrinsic-only HIGH is not proof" because the signals it named
  can no longer reach HIGH: since v1.10.1 they top out at INFO. The one intrinsic signal that does reach
  HIGH is `HARDLINK_MACB_MISMATCH`, which a copy cannot produce — so the caveat was attached to a verdict it
  no longer applied to.

### Documentation caught up with the tool

- **`concepts/timestomp_detection.md` documented a rule the tool no longer follows.** It described three
  tiers and awarded HIGH to "two independent intrinsic signals agree (`CHANGE_LATE` + `PRE_FORMAT`)" — the
  exact rule v1.10.1 removed. Rewritten: four tiers with what each means, the measured base rates, the
  lab-vs-real-installation split (**95.7 %** against **1.86 %**), and why INFO means *ambiguous* rather than
  *cleared*. `concepts/artifact_timeline.md` carried the same superseded sentence and is corrected.
- `analysis/README.md` claimed **435** register rows; there are **469**. It had drifted because the
  register-count gate scanned only `README.md` and `docs/` and knew two phrasings; it now covers that file
  and a third phrasing.
- `verify_samples.py` requires **all four** sample images and exits non-zero naming the missing ones. That
  was correct but undocumented, so a partial run looked like a tooling failure rather than a deliberate
  refusal to certify a subset.

### The gate can now see the published site

- A new check fetches the **live site** and asserts its footer version equals the published tool's `VERSION`,
  and that no live page carries a retired phrase. v1.10.1 shipped correct pages while the site served
  v1.10.0 for a day, and every in-repo gate stayed green throughout — because every check read the working
  tree. This one reads the site. An unreachable site is reported as SKIP, never PASS. Between a sync and the
  push it fails by design: that failure is the statement "the published tree is ahead of the live site".
- The four shipped **sample bundles are regenerated** from the released tool, and the gate now regenerates
  them and diffs. The v1.10.1 bundles were copied rather than rebuilt, so they showed `dataruns` with 51
  extent rows where the tool produces 258, and `timestomp` as `HIGH 36 / MEDIUM 14 / LOW 4` where the tool
  now says `HIGH 1 / INFO 53`.


## v1.10.1 — 2026-09-06 — one timestamp verdict, and two checks that say what they can prove

**Everything here is relative to v1.10.0.** A consolidation release: no new decoders and no new columns. The
listing and the `timestomp` command stop disagreeing, two checks that existed only in the maintainer's gate
become visible to the reader, and three claims are corrected by measuring the whole corpus rather than a
sample.

### The timestamp column and the timestomp command gave different answers

- **They now share one function.** Each used to compute its own confidence tier, and on three volumes
  **101 of 184, 62 of 151 and 50 of 114** flagged files got a different answer depending on which one you
  ran — the column said MEDIUM where the command said HIGH for the identical signal set. `timestomp_verdict()`
  is now the only place a tier is decided. Verified across the corpus: **122,929 flagged rows on 100 volumes,
  0 disagreements**, with the column never rating a file higher than the command and their signal sets nested.
- **A copy is no longer reported as suspicion.** `PRE_FORMAT` (created before this volume existed) and
  `CHANGE_LATE` (change time after create/modify) were tiered as two agreeing signals. They are not
  independent: a timestamp-preserving copy — `robocopy /COPY:T`, a restore, an archive extraction — produces
  **both**, which is why across 521,060 files they occur together 115,936 times and `CHANGE_LATE` appears
  without `PRE_FORMAT` only 384 times. Tiering the pair as corroboration was worst exactly where it mattered
  most: on the corpus's one **real Windows installation**, 115,488 of 120,617 files — **95.7 %** — carried the
  copy signature, because that is what installing an operating system looks like. The old tiering called
  almost every file on it MEDIUM. That pair alone is now the new **INFO** tier. HIGH is unchanged, and on
  that volume the actionable set is **385 files instead of ~115,000**.
- **INFO means ambiguous, not innocent.** The two signals are halves of one event — but they do not identify
  that event as a copy: **backdating a creation time produces exactly the same pair**, and a lab volume whose
  generator log records **74 `SetCreationTimeUtc` calls** carries this signature. So INFO is documented as
  *a copy and a backdated creation are indistinguishable here; corroborate with the USN journal*, never as
  "not suspicion". It lowers the tier; it does not clear the file.
- **Each signal is documented with its measured base rate**, so a reader can judge what a flag is worth. Over
  521,060 files: `PRE_FORMAT` 22.67 %, `CHANGE_LATE` 22.32 %, `CREATE_GT_MODIFY` 1.04 %,
  `HARDLINK_MACB_MISMATCH` 0.04 %. Those averages are dominated by small purpose-built lab volumes — the rate
  on a real installed system is far higher, which is the reason the tier changed.

### Two checks the tool could already make but never reported

- **Metadata page checksums.** Every Object-Table row records a checksum of the page it points at, binding
  the metadata tree together. **`integrity --checksums`** now recomputes them, so you can tell whether the
  tree a listing was built from is the tree the volume recorded. The digest covers the whole page, after
  container translation. It is gated on the flag, and kept out of `summary` entirely, because it is one
  4-cluster read per object — 26,681 of them on a real Windows volume, 427 MB and ~38 s. No default path
  got slower. A reference is reported in one of four ways, kept apart because they mean different things:
  **verified**, **failed** (the page changed since the checksum was written), **absent** (the page is not in
  this image — a partial acquisition, not an alteration), and **superseded** (the Object Table holds a newer
  row for that object; on one volume 107 of 200 references are of this kind). Reporting an absent page as a
  failure would have read as evidence of tampering on any partial image.
- **Bytes that came from image holes are reported, not withheld.** Raw images are stored sparsely — this
  project's corpus is 55 TB apparent against 58 GB allocated — and a sparse image stores a file's **own zero
  content** exactly the way it stores a range that was never captured: as a hole. (`cp --sparse=always`
  alone takes a 67 MB sample to 40 MB by converting real zero clusters into holes.) A hole is therefore
  **not** evidence that data is missing, and the tool no longer says it is. When any part of a file's data
  comes from a hole, `extract` writes the bytes, names the ranges, exits `2`, and with `-o FILE` leaves
  `FILE.holes.json`. The wording is neutral in both directions: the image cannot tell "never written" from
  "not captured", so the report does not pretend to. `--refuse-holes` gives a strict run that writes nothing.
  The check now fires on **any** hole in the data range, not only on an all-zero file — a partial gap inside
  a file with real content is the case that previously passed in silence. Expect it often on a sparse image
  (996 of 1,020 files on one lab volume, all of them correct), so `rc == 2` here means *read the note*.

### `dataruns` was still using the retired model

- **It reported record placement as if it were data residency.** `dataruns` keyed its whole output on one
  field and printed every **embedded** record as `RESIDENT — data inline in directory entry`. On one sample
  volume that mislabelled **475 of 1,010** so-called inline files: they are extent-backed, the largest 149 MB,
  and `extract` decodes their runs perfectly well — `dataruns` simply never asked. The command whose job is to
  show clusters was contradicting the two axes the same release introduced. It now reports both:
  `record=embedded|split` beside `INLINE`/`EXTENT`, prints the runs for embedded extent-backed files, and
  counts by data residency. Files with decoded extents on that volume: **284 → 759**. The machine formats
  gain `record_placement` and `data_residency` columns, and `storage` now carries the data axis.

### Known, and deferred to 1.11

Two label/formatting residuals found in testing, neither affecting recovered bytes:

- **`dataruns -v` prints a snapshot-shared file as `INLINE`.** Three files on one volume
  (`testsnapshots/test.txt`, `testads.txt`, `lasttest.txt`) hold their bytes in a snapshot's cluster, which
  `files` reports correctly as `snapshot-shared`; `dataruns` has only two data states and calls them
  "bytes stored in the record". It is the same label-mismatch class as the embedded/extent-backed fix above,
  one state further on: `dataruns` needs the full residency vocabulary, not just inline vs extents.
- **`FILE.holes.json` splits one contiguous hole at extent boundaries.** A hole spanning two adjacent
  extents is written as two entries (`0–4095`, `4096–97672`) instead of one; the byte total is right, the
  range list is more fragmented than the truth. Adjacent ranges should be merged before they are reported.

### Documentation and the register

- The published tree had three pages still saying **40-column** and a home page still using the retired
  vocabulary; the tool page contradicted its own column table. All corrected, and the gate now compares the
  two documentation trees and checks every stated column count on every page, not just the table.
- The test suite moved to `analysis/tests/`, where the repo already keeps lab material, and no longer carries
  a maintainer's absolute path or a plugin-dependent `pytest.ini`.
- **The two extent decoders are now asserted to agree**, as the safety net for a merge that has not happened
  yet. `_decode_holder_extents` tries an embedded B+-tree index array first and falls back to a
  contiguous-array **scan** — but the naming is misleading: the scan produces **60,938 of 74,258** accepted
  covers (82 %) against the index array's 13,320, so **the scan decoder is the primary decoder in practice**
  and the index array is the special case. A merge cannot treat the scan as removable.

  Where both return a map they almost always return the same one: of 11,560 such values, all but **18** map
  every file offset to the same cluster, once list order and run fragmentation are ignored (the scan starts
  mid-record, and the index array may split a run the scan reports whole). For those 18 the covers genuinely
  disagree. **Four are now settled against the operator's own SHA-256 inventory**: on `win11bidule`,
  `secret.txt`, `vmmemctl.sys`, `fvevol.sys.mui` and `winnat.sys.mui` reproduce the operator's hash exactly
  from the cover the tool uses and *not* from the other one, so the alternative is a false candidate there.
  The remaining **14 have no byte-exact ground truth and are content-unverified** — they are named in the
  release notes and are first on the 1.11 list. The count is pinned so it cannot grow unnoticed.
- **Three helper bodies that were copied between the two tools now live once.** `die`, `_int_arg` and
  `_parse_args` were byte-identical in both files, but each read its own module-level program name, so
  importing them would have made `refsanalysis` report errors as `forefst:`. The logic moved to `forefst.py`
  and `refsanalysis.py` keeps three one-line wrappers that pass its own name — identical output, one
  implementation. The test that guards this compares function **bodies** now, not names.
- **Known weakness in the maintainer's golden, stated rather than hidden:** 22 of its 3,598 rows are
  fingerprints of output that passed through shell command substitution, which silently drops NUL bytes. For
  those rows the hash does not cover NULs, so they are weaker evidence than the rest. It is the hazard the
  generator already documents for `extract` (which writes to a temp file to avoid it); routing every command
  the same way is a 1.11 change, since it costs a re-bless.
- A **public golden** for the four sample volumes ships with the repo, so the published claims can be
  reproduced from a clone without the private corpus. Its fingerprints no longer depend on where you keep
  the images: several commands print the image's absolute path, and hashing that made the golden match only
  in the tree it was blessed in. The path is normalised out, so a clone with the images anywhere verifies.
- **`rc == 2` now means a finding, and nothing else.** An audit proposed renumbering every usage error *to*
  `2`. That was rejected — `2` is already the scriptable "finding of interest" code for `integrity` and
  `security --audit`, so it would have made a mistyped flag indistinguishable from a real integrity failure.
  The overload is removed the other way instead: **usage errors now exit `1` on all 19 commands**, where
  before the four argparse-backed ones (`files`, `summary`, `search`, `details`) exited `2`. So `0` success,
  `1` runtime *or* usage error, `2` a finding — `if rc == 2` is now a safe branch in a script. Measured
  across every command and locked by tests.

## v1.10.0 — 2026-09-05 — one word meant two things: record placement and data residency are now separate

**Everything here is relative to v1.9.0.** One word — *resident* — was doing two jobs. It named **where a
file's record sits** (inside its directory-entry row, or split out into a backing record) and, separately,
**where the file's bytes are** (inline in that record, or out in extents on disk). The two are independent:
moving or hard-linking a file forces the record to be split out and moves **no data at all**. Because a
single `IsResident` column collapsed both, files were reported wrong and some could not be extracted.

### The listing now answers both questions

- **Two columns replace one.** `RecordPlacement` says `embedded` or `split`; `DataResidency` says `inline`,
  `extents`, `snapshot-shared` or `sparse`. `IsResident` stays for one release as a deprecated alias — it is
  `True` exactly when `DataResidency` is `inline` — so existing scripts keep working while they move over.
  The CSV goes from 40 to 41 columns: the two new ones land after the ADS columns, and the separate `OID`
  and `FileRef` columns merge into one (below), so everything after the ADS columns shifts right by two.
- **Exactly one header name changes for you: `OID` and `FileRef` become `ObjectRef`.** Every other v1.9
  header keeps its name, including `HomeOID` and `TimestompFlags`. (Both were briefly mangled during
  development into `CreationDirOID (HomeOID)` and `TimestompFlags (informational)`; neither was ever
  released, and both are back to the names v1.9 published.) All 41 headers are plain identifiers with no
  slash, space or bracket, so a consumer can key on them — and they are **frozen for the 1.10 line**.
  `HomeOID` is the directory the file was **created** in; `CreationDir` is that same directory's path.
- **`--filter inline`** replaces `--filter resident`, which still works for one release.
- **`-o FILE` keeps working on `files` and `summary`.** It had been refused outright, on the reasoning that
  the same flag produced CSV, JSON or a bodyfile depending on other flags. The reasoning was sound and the
  correction was not: it broke the README's own first example and four more in the tool page, against the
  promise above that existing spellings keep working. `-o` is accepted as the selected format's
  destination (CSV by default), with a deprecation note pointing at `--csv FILE`, and it warns instead of
  silently losing the value if you also name a destination on the format flag.
- **`search` says which form too.** Its `Res` column was a Yes/No — the same collapse. It now reads
  `Data` and prints the form itself, using **exactly** the `DataResidency` value set (both read the same
  function, so the two views cannot drift apart), and its identity column shows a real file reference
  where it used to print the placeholder `(non-res)`.
- **A moved file can be `split` and `inline` at once**, and that is now sayable. It is the common case for a
  small file: **16,191 rows across the corpus** are split records whose bytes are still in the record
  (14,666 with content plus 1,525 empty ones).

### Files that could not be extracted, or were described wrongly

- **Empty files that had been moved or hard-linked did not exist as far as `extract` was concerned.** A
  0-byte file whose record had been split out was dropped from the record list entirely, so `extract`
  answered `file '<name>' not found` for a name that `files` and `details` both listed happily. **772 such
  rows on 11 volumes.** They now extract, writing nothing, as an empty file should.
- **Files whose home directory the walk never visited lost their data residency, USN, owner and size.**
  A split record is found through the directory that owns it; when that directory was not itself walked, the
  lookup missed and every field the backing record carries was silently left unset — so `files` called the
  file extent-backed while `extract`, which resolves differently, correctly read it as inline. **548 names on
  one real Windows volume.** The backing is now fetched on demand from the owning object. The previous join
  is kept for one release behind `--legacy-link-join`.
- **Agreement is now exact.** Against an independent byte-level classifier built from the on-disk descriptors,
  the listing agrees on **every record of every volume tested** — 507,433 records across 79 distinct volumes
  (523,756 comparisons over the 117 images as measured, before counting byte-identical copies once). It was
  99.686 % before.

### Three things the tool reported that it should not have

- **`HardLinkCount` was blank for a file with one name** — blank meant "not computed", not "unknown", and it
  made `files` disagree with `summary`. A file with no backing record provably has exactly one name, so it
  now reads **1**. Directories stay blank, where the count does not apply.
- **`deleted` promised a carve it could not honour.** The single-extent fallback accepted a match without
  checking the cluster number could actually be mapped, and an unmapped number is passed through unchanged —
  so matches landing 52 GB into a 5 GB image were reported as recoverable data. Mappability is now checked
  first, and the counts drop to what can really be carved (103 → 96 and 45 → 35 on the two affected volumes).
- **`CreationDir` was empty for a file created in the volume root**, which read as "unknown". The root is
  `.` everywhere else in the listing and is now `.` here too.

### Reading the change journal

- **A directory's journal identity is its own object ID**, with file number 0 — verified on 589 directories
  across 10 volumes, with no counterexample. `OID` and `FileRef` were two columns of which exactly one was
  ever filled; they are one column, `ObjectRef`, and either kind of object is addressable by it.
- **The journal is read in journal order.** Records are ordered by their USN, each record's position is
  checked against the journal's own wrap arithmetic, and the torn record at the wrap point is reported rather
  than stepped over silently.

### Smaller corrections

- **`extract -o` on a 0-byte file now creates the file.** It printed `0 bytes` and wrote nothing, so a
  caller who asked for a file got none.
- **The tool stopped using the word the documentation retired.** `summary` counted files as
  "resident + non-resident" and `extract`/`details` said the same in five more places; they now say
  `inline` / `extent-backed` / `snapshot-shared`, matching the columns.
- **`--no-timestomp`** leaves the column blank rather than removing it — the documented behaviour now
  matches, and the schema no longer depends on a flag.
- **The CSV formula hazard is documented.** A filename beginning `=`, `+`, `-` or `@` is a formula to a
  spreadsheet, and filenames on a suspect volume are attacker-controlled. Output stays byte-faithful by
  default, the count is reported at the end of a run, and `--csv-safe` — which existed but was
  undocumented — is now on the tool page with the caveat that it alters the recorded name.

### Documentation and the claim register

- **Reference corrections.** The container-table compression header's marker at `+0xA0` is **not** the
  constant it was recorded as — it reads `0x07` on a v3.4-format volume and `0x0F` from v3.7 on, measured on
  every volume in the corpus whose container-table root page is an index root. The `$EFS` decryption-field
  layout, the block-refcount value's trailing field, and the two-axis storage model are all now carried in
  the claim register rather than only on a page.
- **What a metadata page's checksum actually covers is now settled.** Each page reference stores a digest
  of the page it points at; that digest is taken over the **whole** page — every cluster of it, after the
  virtual-to-physical translation — with nothing excluded, not even the page's own header. Recomputing it
  matches the stored value on **34,291 of 34,291** live references across 89 volumes, under both the CRC64
  and SHA-256 algorithms. That is the count for the row a reader actually uses: an object table can hold more
  than one row for the same object, an earlier one and a current one, and only the current one is read.
- **The pages say which axis they mean.** The word *resident* is replaced by `embedded`/`split` for record
  placement and `inline`/`extents`/`snapshot-shared`/`sparse` for data residency wherever the distinction
  carries weight, and a check now fails the build if a page reintroduces it.
- **Every byte offset published in a page's offset table is checked against the claim register**, so a page
  cannot state an offset that no measurement backs. It found three real gaps, all since closed.
- **Four reference corrections.** The checkpoint's direct root list at `+0x94` holds **13 `u32` in-page
  offsets**, not the page references themselves. The VBR's checksum selector records what the volume was
  *formatted* with, so the authority for the on-disk page-reference format is the **checkpoint's** size
  field, not the VBR's. Cluster size is `bytes_per_sector × sectors_per_cluster`, both read from the VBR,
  rather than assuming 512-byte sectors. The Trash Table page now says plainly that the table was **empty
  on every image measured**, so its key content is inferred from the driver and not observed — and that a
  file, having no object id, cannot contribute one the way a directory does.
- **Two new gate checks.** Every command example in the README and the tool pages is now run, and the gate
  fails if the CLI rejects one — the check that would have caught the `-o` break. And the documentation
  checker now fails when it scans zero pages instead of reporting green, which is what it did when run
  from anywhere but the maintainer's own tree.

## v1.9.0 — 2026-09-03 — file recovery made complete: five ways a file's data was unreachable, all fixed

**Everything here is relative to v1.8.** The headline is recovery correctness: five separate mechanisms could
leave a file's data unreadable, or readable but wrong, and all five are fixed. On the reference volume — a
4 GB Windows 11 volume that arrives with its **operator's own SHA-256 inventory**, written before the image
ever reached this project — the number of files recovering byte-exact goes from **41 to 629 of 629**.

### Files whose data could not be read, or came back wrong

- **A file's extent map is a B+-tree node, not a flat list.** The records saying where a file's bytes live are
  the *rows* of a small B+-tree held inside its data record. A file with one run looks exactly like a flat
  array — which is why small files always worked — but a fragmented or large file needs more rows, and past
  one node the map continues in a separate page. Neither was walked, so those files reported **no extents at
  all** and `extract` stopped with nothing. Both are now read: **48 more files** across the test corpus report
  their data runs, and on the reference volume the last 21 unreadable files — 1 MB to 791 MB, including a
  782 MB archive and a 791 MB disc image — come back byte-exact.

- **Extents in the upper half of the address space were being discarded.** An extent names a *virtual* cluster,
  which the container table maps to a physical one; the virtual space runs roughly twice as far as the
  physical. The check compared virtual numbers against the *physical* count, so any extent above it was thrown
  out — and because the decoder stops at the first rejected entry, one rejection discarded the file's **whole**
  map. On the reference volume this alone hid the contents of **583 of 629 files**.

- **Small moved and hard-linked files gave up nothing.** Moving or hard-linking a file moves its *record* into
  a separate backing record; it does not move the file's *bytes*, which for a small file usually stay inside
  that record. Every such file was treated as stored on disk, so `extract` failed with "no extents decoded"
  while the content sat in a record already in hand. **16,191 files across 26 volumes** — 14,580 of them on a
  single real Windows volume.

- **Blocks shared with a snapshot were returned as zeros.** Stream snapshots are copy-on-write: only blocks
  written *since* a snapshot belong to the live version, and the rest are still described by the snapshot —
  one copy on disk, shared. Files were assembled from their own extents alone and the remainder treated as
  empty, producing a file of the **right length with the shared regions zero-filled** — bytes that are on the
  volume nowhere — with no warning. `snapshots --extract` had the mirror problem, writing short, shifted
  versions. Both now resolve every block position; a genuinely **sparse** file is untouched and its holes still
  read as zeros. Measured against the lab generator's recorded sequence: **20 of 20** prior versions byte-exact,
  against 8 of 20 before.

- **Extraction could use a stale size and truncate real content.** A name keeps a *cached* copy of the file's
  size and ReFS never refreshes it; the object's real size lives in its backing record. `files` already used
  the backing, but `extract`, `dataruns` and `export` used the name's copy — so what you recovered depended on
  which of an object's names you addressed. The cache can be too *small* as well as too large: three files in
  the corpus were being silently truncated by 186 KB, 274 KB and 49 KB. Every command now resolves the same
  size.

### Metadata that was missing or wrong

- **Directory junctions and directory symlinks now report their target.** On a directory the reparse buffer is
  never a top-level attribute row — it sits in the attribute tree embedded inside the directory's own record —
  so the tool printed the tag and no target at all. **98 targets across 11 volumes** come back, nothing else
  moves. On a real Windows volume that is 78 of its 81 reparse points.

- **`IsResident` answers the question it documents** — *is the current `$DATA` stream inline?* It read `False`
  for every file in the third item above. A hard-linked file may now show resident storage *and* a link count
  above one: the record moved, the bytes did not. *(Known remainder: on the busiest volume 548 of 14,580 keep
  the old label because their name cannot be size-matched to its backing; their content extracts correctly.)*

- **A volume upgraded from ReFS 3.9 no longer reports "formatted v3.14".** Two signals say a volume was
  upgraded, and the weaker was overwriting the stronger. The UPGRADED verdict itself was never affected.

- **`specials sparse` is labelled for what it tests** — the sparse attribute bit, not "allocated < logical
  size". The selection never changed; only the label was wrong.

### New

- **`mlog --stats` verifies every log record.** Each MLog record carries an integrity value the driver
  recomputes before replaying it; the algorithm — a four-way interleaved 64-bit XOR folded to 32 bits — is now
  reproduced, so a torn or edited record is named instead of parsed in silence. `mlog --json` carries the same
  verdict.

- **4Kn-sector disks are read.** GPT sits at LBA 1, so its byte offset follows the disk's logical sector size;
  only 512 was tried. **Untested on real 4Kn media** — the path is covered only by synthetic images, and a
  result obtained through it should be treated as unverified. 512-byte behaviour is unchanged.

### Fewer false alarms

- **A healthy volume no longer reports "corrupt/truncated container table".** The inline extent decoder
  enumerates many candidate rows and keeps only those forming a complete cover; it was translating every
  candidate before deciding, so rejected ones counted as container-map misses and raised a corruption warning
  on valid evidence. **6,475 of 6,520 spurious misses disappear**, while the 45 genuine ones still warn.

- **A stream's extent record is identified by its key shape**, not by a byte that happened to be zero. It never
  mis-resolved a stream on any image; the exact test removes the possibility.

### Validation

- **`win11bidule.raw` joins the verification corpus** — the first image arriving with its own operator-made
  record: 631 files with sizes, attributes, timestamps and **SHA-256**, full change-journal dumps, `fsutil`
  reports, and transcripts of the session that built it. Because that record was made on Windows before the
  image reached this project, a match against it is not the tools agreeing with themselves. Two of its files
  are pinned in the output fingerprint by their **operator-recorded hashes**.
- Corpus: **100 volumes** (ReFS 3.4 → 3.14 + Insider, 2 GB–16 TB, 4 K and 64 K clusters). Anti-regression
  **20/20**, unit suite **180 passed**, output fingerprint **3,498 command-runs**, every changed row accounted
  for individually.

### Format findings behind this release

The claim register grows to **455** and the errata list to **86**. Eleven entries are new, each confirmed on the
decompiled driver, the raw-disk corpus, or both. Two corrections worth singling out:

- **The extent record's flags field is two bytes, not four.** The two bytes above it hold the record's own
  size: `24` normally, `24 + run*4` when the run carries per-cluster CRC32-C. Read as a single 32-bit value the
  pair looks like one flag constant — which is why the values seen in the wild all begin `0x18`: that is `24`,
  the record size. Measured on **48,474 records across 40 volumes**, no exception; the field takes 136 distinct
  values and tracks the run up to 223 clusters. Records are **8-byte aligned**, which is where the
  long-documented "32-byte stride" for a single-cluster checksummed record comes from.
- **The change journal is an in-place ring** — `USN mod allocation == byte offset`. After a wrap two
  generations coexist, so byte order is **not** time order.

### Compatibility

Backward-compatible. Both tools remain **Python 3.7+, standard-library only** and open the input strictly
**read-only**. Volumes with moved or hard-linked small files, snapshotted files, directory junctions, large or
fragmented files, and integrity streams will report more than they did under v1.8 — nothing previously
reported has been removed or reinterpreted.

## v1.8.0 — 2026-09-01 — whole-volume deep recovery, real capacity reporting, and attributes hidden behind a multi-level embedded tree

**A correctness release with four independent parts: a deep deletion scan that no longer stops part-way
through the disk, capacity reporting built on a corrected allocator decode, alternate data streams that were
invisible on ReFS 3.4, and attributes that were invisible behind a multi-level embedded tree.**

### `deleted --full` and `--scan-pages` now scan the entire volume

**The deep scans stopped after the first 50,000 clusters — a fixed budget unrelated to the size of the disk, and
the analyst was never told. On a 64 GB volume that is 0.3% of the disk. Both scans now cover every cluster by
default, always print how much of the volume they examined, and mark any bounded run as INCOMPLETE.**

- **What it recovers.** On a 64 GB Windows volume, `deleted --full` goes from **165 to 22,353** orphan pages and
  from **23,386 to 39,089** deleted files — 15,703 files (40%) that were on the disk and reachable, and were
  silently skipped. Deleted metadata lands wherever the allocator last freed a page, so a prefix-bounded scan
  misses files for no reason the analyst can see.
- **The recovered files are real.** The two indexes were exported and compared: the old, bounded result is a
  strict *subset* of the complete one — nothing is lost by scanning further — and the 15,488 new unique
  identities were cross-checked against the volume's own USN change journal, an independent source the slack
  scan never reads. **90.2% carry an explicit USN *delete* record**, against **33.6%** for the set the tool
  already reported; among the entries graded byte-exact the rate is **99.3%**. The newly reached entries are
  therefore better evidenced than the ones already trusted.
- **It got faster at the same time**, so the wider scan is affordable. The scanner now reads the volume in 16 MiB
  sequential blocks instead of one 4-byte seek-and-read per cluster, hands back the bytes it already holds
  instead of re-reading each hit, and finds the `MSB+` signature through a one-byte-per-cluster strided digest
  rather than a Python comparison per cluster — 11–15× less CPU in the inner loop, which is what makes a multi-TB
  volume practical rather than grinding through half a billion Python iterations. The scan is now limited by the
  disk, not the tool: a 2 TB volume sweeps in **19.8 minutes** (111 GB/min) where the same scan without this
  change was CPU-bound and still unfinished after 45.
- **You are told what each option costs.** `help deleted` labels every option fast / moderate / slow / very slow
  with a concrete budget: the deep scans read the whole volume once at the disk's sequential read speed, so on a
  1–2 GB/s disk that is about **a minute per 60–100 GB** (≈1 min at 64 GB, ≈20–35 min at 2 TB, ≈2.5–4.5 h at
  16 TB), and long scans print progress. `--max-scan N` is still available to trade completeness for speed — it
  is now an explicit opt-out rather than a silent default, and the run is labelled INCOMPLETE in the output and
  the recovery log.
- **The quick default is unchanged.** Plain `deleted` never ran the orphan scan and still doesn't; it stays a
  seconds-long pass and now points at `--full` for the rest.

### The volume's real free/used space, and a corrected allocator format

**`summary` now reports capacity — how much of the volume is actually used — from ReFS's own accounting, and
a new `refsanalysis allocators` command shows the allocator tiers behind it. Decoding it corrected four points
of the published row format.**

- **`summary` gains a capacity line.** It comes from the 384-byte summary ReFS keeps in the allocator's root
  page — a single page read, so it costs nothing. It replaces a container-level "free space" estimate that was
  computed but never shown, and could not have been right: it counted unmapped containers as free, and the
  container table maps essentially the whole volume, so it reported about 64 MB free on any disk.
- **`refsanalysis <image> allocators` (new)** decodes all three tiers and prints, for each, what the rows say
  *and* what the volume's own summary says. The two can legitimately differ and the difference is evidence:
  on ReFS 3.4 the tiers are strictly separated so the Medium rows span less than the summary while the free
  counts still match exactly; if *both* numbers differ, the volume is damaged.
- **The row format was wrong in four places**, now corrected from the driver's own codec (both the 3.4 and
  3.14 generations) and re-measured on every corpus volume. The bitmap row is **variable length**
  (`ceil(range_length/8)` bytes of bitmap — 2,072 is just the 16,384-cluster case; 152- and 32-byte rows
  exist). The two bytes at `+0x14` are a **bitmap offset** and a **tier-dependent format byte**, not a u16
  "header size". **Flags bit 0** — not the row length — says whether a bitmap is present. And the field at
  `+0x16`, documented as a "used count", is a **driver hint that drifts**: it disagrees with the row's own
  bitmap on about one bitmap row in six, so nothing computes capacity from it. The rows also turned out to be
  keyed by **physical** cluster number, which is not what the published "addressing" column (about how the
  tables' own pages are reached) had led us to assume.
- **What the allocator does *not* cover is now stated.** The tail of the volume past the last container
  belongs to no tier — 48 MiB on almost every volume, up to ~2 GB on a real Windows disk. It is reported
  separately, never as free space.
- **A tier is identified by its table, not its root index**, and page by page. On one damaged volume family
  root 12 carries the container table rather than the small allocator, and a root that *does* claim the right
  table still leads into foreign pages; those rows are rejected and reported rather than averaged into a
  total. On undamaged volumes nothing is rejected.

### ReFS 3.4 alternate data streams were invisible

**On a ReFS 3.4 volume the tool reported no alternate data streams at all. It now finds them — 100
ADS-bearing files on one 2 TB test volume that previously showed zero — and their contents extract
byte-for-byte.**

- **Cause:** the key that identifies an ADS row comes in two forms. From 3.7 an instance marker sits at
  `key+0x08`, the attribute type at `key+0x0C` and the name from `key+0x10`; on 3.4 there is no marker, the
  type is at `key+0x08` and the name starts at `key+0x0C`. The reader matched only the first form, so every
  3.4 key failed the test and the answer came back as a confident "none". Both forms are now accepted, and
  the name is read at the offset the matched form implies.
- **Also affects upgraded volumes.** Marker-less rows survive an upgrade from 3.4, so the form is decided
  per record, not from the volume version — two upgraded 3.14 volumes in the corpus also gained streams.
- **Strictly additive:** 7 volumes change and every one goes from **0 to N**; nothing is lost or reinterpreted.
- Verified against the volume's own generator: the recovered names are exactly the streams it wrote, and the
  extracted contents match its text byte-for-byte.

### Attributes hidden behind a multi-level embedded tree

**On volumes where a file carries a large attribute set, some of its attributes were invisible — most visibly its
alternate data streams. They are now read. 548 previously-unreported ADS are recovered across the regression
corpus, and one test volume goes from reporting *no* ADS at all to 60.**

- **Attributes stored in a child node are now read.** A file's attributes live in a small B+-tree embedded in
  its directory record. When that set outgrows a single node, ReFS turns the embedded node into an *index*
  node whose rows point at a child page holding the real attributes. The reader only ever looked at the
  outer node, so for such files it saw nothing — no ADS, no reparse data, no `$DATA` record — and reported a
  confident, wrong "none". It now descends into the child, exactly as the driver does.
- **Scope:** 1,329 files across 19 of the 99 corpus volumes, on ReFS 3.4 through 3.14 — 4,094 attribute
  records recovered in total, of which 548 are alternate data streams.
- **Extraction works too**, not just listing: the recovered streams' contents extract byte-for-byte
  (verified against a generator that writes deterministic content, 5/5 streams, sizes 40 KB … 200 KB).
- **Nothing is lost or changed elsewhere.** The descent only applies where the old code returned nothing, so
  it is strictly additive (measured: 4,094 records gained, 0 lost). 3,070 of the 3,168 regression
  fingerprints are unchanged; every changed one is an image that gained attributes.

## v1.7.2 — 2026-08-29 — differential-audit follow-through: ID-based object-table selection + reference corrections

**A small hardening release from a differential audit against a second, independent ReFS reader
(`unsound/refsprogs`). No change to what the tools report on a valid volume — the 122-image regression corpus is
byte-identical bar the version banner.**

- **The object table is now selected by its on-disk table-ID, not its root index.** The container table was already
  chosen by ID (a primary/duplicate root pair is not bound to a fixed index→ID order); the object table now follows
  the same discipline, falling back to the historical index. On the whole corpus root 0 is always the object table,
  so the output is byte-identical — this only matters if a primary/duplicate root pair is ever exchanged (which is
  known to happen for the container-table pair on some large volumes).
- **Reference/structure corrections (documentation only — no tool behaviour change).** The non-resident `$DATA`
  stream-summary header is now documented as version-dependent: on ReFS v3.4 its size fields sit four bytes later
  (`stream_size` at 0x3C, not 0x38) and `summary_size` is 0x1A0 before v3.14 — the earlier tables had been measured
  on v3.14-only images. The tools already read v3.4 file sizes and content from version-independent fields, so this
  is a docs/reference fix only.

## v1.7.1 — 2026-08-28 — follow-up-audit fixes: extraction robustness, caveat coverage, and de-duplication

**A small hardening release answering a follow-up review of v1.7.0, made in another language-model session. No change to what the tools report
on a valid volume (the 122-image regression corpus is byte-identical bar the version banner); the changes are error
handling, surfaced caveats, and removing duplicated code between the two tools.**

- **Bulk extraction survives an unwritable name.** The faithful (un-truncated) sanitizer can produce a name longer
  than the host filesystem's limit; the five bulk extractors (`deleted`, `snapshots`, `export metadata` /
  `resident-all` / `recyclebin`) now record such a write to `_extract_failures.json` and continue, instead of
  aborting the run with a traceback and a half-finished directory.
- **The container-mapping caveat is reported for every image.** `--cow-before` builds a second volume view; its
  unmapped-container caveat is no longer lost, and the warning now names which image it came from.
- **Unguarded formula-lead CSV cells are surfaced.** With the byte-faithful default, a cell beginning `= + - @`
  now triggers a one-line stderr note (re-run with `--csv-safe` before Excel) — the output stays byte-faithful.
- **A pathologically deep directory tree is a clean error, not a crash.** The walker's recursion limit is set to a
  value the C stack can hold, and a too-deep (corrupt/crafted) tree is reported instead of risking a hard process
  kill.
- **Shared byte-identical helpers are single-sourced.** `refsanalysis` now imports ten logic-identical helpers from
  `forefst` instead of carrying its own copies — verified behaviour-identical. (Genuinely divergent code between the
  two tools is deliberately left as-is.)

## v1.7.0 — 2026-08-28 — hardening pass (code-review response): robustness, fidelity, and consistency

**A hardening release answering a code review made in another language-model session. No change to what the tools report on a valid volume —
the full 122-image regression corpus is byte-identical — with malformed input, filename fidelity, forensic
timestamp recovery, and cross-command consistency all tightened.**

- **Robustness — malformed input can no longer crash or hang the tool.** A self-referential container table (which
  previously fanned out and hung *every* subcommand) is stopped by a cycle guard; a zero / non-power-of-two cluster
  size, an out-of-spec GPT entry array, and an over-long GPT entry count are all rejected with a clear error instead
  of `ZeroDivisionError` / `MemoryError`; a B+-tree row whose key or value runs past its page is skipped instead of
  read as a plausible-but-wrong record.
- **Fidelity — filenames are reported and extracted exactly as they are on the volume.** CSV output is now
  byte-faithful by **default**; the spreadsheet formula-injection guard (which prefixes a cell beginning `= + - @`)
  is available as an opt-in **`--csv-safe`**. Extraction **never truncates** a name (a previous 120-character cap
  quietly shortened long Windows names); very long names are surfaced rather than silently altered.
- **Forensics — timestomped event times are no longer hidden.** The plausible-FILETIME window used to pair MLog
  rename/delete events with their `$SI` timestamps was widened (~1968–2108), so a backdated or year-2000 event time
  is now recovered and shown (verified on the bi0sCTF ReFS-3.4 image, which ships a timestomping tool) — while the
  pairing discriminator stays strong enough that nothing is fabricated. Every command now also surfaces a stderr
  caveat when a corrupt/truncated container table forced identity-mapped reads (previously only `fastsummary` did).
- **Consistency — the two command families now behave the same.** One partition-acceptance policy (a ReFS partition
  behind an NTFS one is accepted by every command, not just `files`); an unknown flag is reported before the image
  is read; `details --json` with no target fails cleanly instead of printing help to stdout with a success code;
  `forefst` and `refsanalysis` print identical checkpoint-flag labels (single source of truth).
- **Hygiene & contract.** Both tools are lint-clean; the process exit-code contract is documented (see
  `docs/tools/forefst.md`) and locked by a regression matrix. `bootedit` on `refsanalysis` is unchanged.

## v1.6.0 — 2026-08-22 — MLog rename/event-time recovery, recycle-bin & bootstrap-corruption forensics, any-order flags

**A forensics-focused release driven by a real ReFS-3.4 case: the recycle bin decodes non-resident metadata, the
MLog reconstructs rename/delete labels *and* their event times, `summary` now flags a tampered bootstrap, and
`--partition-start` works in any position on both tools.**

- **Recycle bin recovers non-resident `$I`/`$R`.** `recyclebin` / `export recyclebin` previously failed on a
  non-resident `$I` record ("could not be decoded from a plain inline record") — common on ReFS 3.4. A single
  shared, residency-agnostic content reader (`get_file_content`) now resolves every recycle record the same way
  `extract` does (resident inline / CoW / inline extent-holder / on-disk extents), so original paths, deletion
  times, and the surviving `$R` payloads all come back. (Also fixed a `$R` reassembly bug that appended extents
  instead of placing them by `file_vcn`.)
- **MLog reconstructs renames and their event times.** `mlog --parse` (and the super-timeline) now (a) label a
  same-directory directory rename as **RENAME** (and a cross-directory one as **MOVE**) instead of `UPDATE` — the
  new name and its parent are resolved even when the record keys the table only by handle; and (b) recover the
  **event FILETIME** of a rename/permanent-delete, which ReFS writes to the paired `$SI`-update in the following
  log block rather than inline. On a busy volume this turns tens of thousands of previously-untimestamped
  operations into dated timeline events (with no change where a transaction already carried its own time).
- **`summary` flags a tampered/corrupt bootstrap.** Each superblock and checkpoint copy stores its own physical
  location; `summary` now checks it and prints **`CORRUPT self-reference`** + a `BOOTSTRAP TAMPERING` note when a
  copy's stored self-LCN doesn't match where it actually sits (e.g. a hand-zeroed superblock). The volume still
  parses from a good checkpoint — the point is that the tampering is no longer invisible. (Clean on the whole
  test corpus; only a deliberately-corrupted image trips it.)
- **`--partition-start` works in any position — both tools.** `forefst IMG --partition-start 0 integrity` and
  `refsanalysis IMG --partition-start 0 supb` (the flag *before* the subcommand) now work for every subcommand,
  matching the flag-after form; a bare `refsanalysis IMG --partition-start 0` still defaults to `summary`.
- **`details` and `refsanalysis summary` polish.** `refsanalysis summary` reports the resident/non-resident split
  in the default view (it was blank on some volumes).

## v1.5.0 — 2026-08-21 — deleted-recovery overhaul, full USN journal, richer `details`

**`export deleted` now produces an analyst-first output — a CSV/JSON index plus only the files you can actually
read — and recovers non-resident deleted content on every ReFS layout, not just the newest. The USN journal is
read in full, and `details` reports everything `files` does for a single file.**

- **Non-resident deleted files carve on every layout.** A deleted non-resident file keeps its extent map in
  page slack; on ReFS 3.4–3.10 and upgraded volumes that map is embedded *inside* the directory record as a
  small B+-tree the previous recovery path could not reach — so those files were reported metadata-only and
  never carved. `export deleted --carve`/`--full` now decodes that inline map (the same cover-guarded decoder
  `extract` uses) and reconstructs the file: byte-exact where its clusters survive, and nothing at all — never
  wrong or empty bytes — where the map points outside the volume. Corpus-wide this recovers thousands of files
  that were previously unrecoverable, with no regression on the layouts that already worked. (Also fixes a
  latent buffer-shrink where a past-EOF read could emit a 0-byte file.)
- **`export deleted` output redesigned.** Instead of flooding the output directory with one raw `.row` remnant
  per entry, the command writes **`deleted_files.csv` (+ `.json`)** — one row per deleted entry, with its
  recoverability, a reliability grade (exact / best-effort / none), a system-vs-user category, and the exported
  content file — plus a **`content/`** folder holding only the files that actually decode (resident byte-exact,
  and carved non-resident under `--full`/`--carve`; never a 0-byte placeholder), and a recovery log. The raw
  remnants are written only with **`--rows`**; **`--no-system`** hides OS/BitLocker churn; and the run ends with
  a plain-language summary of what was recovered and where. `--trash` is a quick Trash-table view and now says
  so when combined with an output/export flag, instead of silently writing nothing.
- **The USN journal is read in full.** `usn` (and the super-timeline and `usn --stats`) previously stopped after
  roughly the first 900 KB of a busy `$J` — a `$DATA` descriptor was being misread as the stream size — so most
  of a large journal was invisible. The whole rolling journal is now read; on active volumes this turns a few
  thousand visible records into the complete set (e.g. ~6.5 k → ~218 k on one image), and a file's `LastUsn`
  resolves to its journal record across the full window.
- **`details` reports everything `files` does.** `details <file>` is now a strict superset of a `files` row for
  the targeted file — adding the creation directory, a security-descriptor (DACL) summary, the sparse flag, and
  per-version snapshot names — so drilling into one file never shows less than the listing.
- **Reference & documentation.** The deleted-recovery, methodology, and About pages were revised; the
  Methodology page gained a clear *versions tested* table (driver builds and on-disk versions); a new reference
  finding and an erratum were recorded for the full-journal read; and the tool / reference / website set was
  reconciled to the current behaviour.

## v1.4.0 — 2026-08-16 — file identity completed, move/residency consolidation, output consistency + usability

**The file-identity model completed for resident files and proven end-to-end for moves, a batch of
usability/correctness fixes from real testing, and consistent machine-readable output across the tools.**

- **File identity completed.** `files`/`usn` lead with `FileRef = HomeOID:FileID` (the stable 128-bit
  reference, identical to the USN FileReferenceNumber) — now populated for **resident files too** (home ==
  parent, ordinal at the resident record's `$SI+0x58`). New `files` columns: **`CreationDir`** (the resolved
  path of HomeOID), **`IsMoved`** (the file currently sits outside its creation directory), **`DACLSummary`**
  (a compact per-descriptor ACE list), and **`SnapshotNames`** (the per-version labels). The CSV is now **40
  columns**, reordered, with `HomeOid→HomeOID`/`FileId→FileID`/`HasAds→HasADS`/`AdsNames→ADSNames`; the always-
  blank recovery columns moved out of `files` to the `deleted` command.
- **Move → non-residency, proven.** A controlled before/after experiment confirmed on disk that a
  cross-directory move converts a resident file to **non-resident** (a one-way ratchet — only the non-resident
  layout carries the frozen creation-directory home); a same-directory rename stays resident, a copy is a new
  object, and the per-directory ordinal is never reused after deletion. Recorded as a new reference finding +
  erratum; the concept/structure docs gained the move/copy/rename/hard-link storage model.
- **Bootstrap section reworked.** `summary` now verifies the SUPB/CHKP **self-checksums** (CRC32-C / CRC64 /
  SHA-256) and reports a truthful "checksum OK", labels the older checkpoint slot **secondary** (not "backup"),
  and notes that the three SUPB copies hash differently by design (identical payload).
- **Volume-state, version banner, and labels.** The Insider case (native format written by a newer driver) is
  no longer mislabelled "upgraded"; every run's first line shows the tool version; the `files`/`summary` lines
  now read `resident + non-resident` with a consistent, all-categories special-file line and a self-explaining
  `Hard-linked: G files sharing K names`; the misleading "free space" estimate was dropped and `FS Metadata`
  now shows its children.
- **`deleted` machine-readable output.** `deleted --csv/--json/--jsonl FILE` exports the recovered entries
  (composes with every recovery flag); `-o DIR` and other output paths now fail with a clean message instead of
  a traceback; extracted text to a terminal gets a trailing newline.
- **FileRef basics (from the prior identity work).** `details --id HomeOID:FileID` addresses a file by identity
  independent of its path; `details` prints the FileRef + a relocation note; hard-link names with stale cached
  sizes are reattached via the backing's type-0x39 back-pointers (no over-merge, keyed on `(HomeOID, FileID)`).
- **Hard-link resolution hardened (type-0x39).** A hard-link name whose cached size is stale (e.g. a size-0
  non-primary name) is reattached to its object through the backing's embedded type-0x39 back-pointers — the
  driver's own authoritative name list — so it groups correctly instead of showing as a separate
  `hard_link_count=1` row. No over-merge (verified corpus-wide; the anti-over-merge guard keys on the
  `(HomeOid, FileId)` object identity).
- **Output standardization.** `files`/`search`/`summary`/`details`/`fastsummary` take `--csv/--json/--jsonl
  [FILE]` (bare → stdout, `+FILE` → write & print a count); `usn --stats` prints alongside a file export;
  `integrity` mismatches show the container id + byte offset; `summary` gained a *Bootstrap structures* section;
  directory walks default to **full depth**; bare `forefst <image>` prints the volume summary.
- **refsanalysis consistency.** `files`/`attributes` default to full depth (cycle-guarded); `details` shows the
  FileRef + relocation note. The two tools remain 0-divergence on the shared enrichment layer.
- **Reference & documentation.** The FileRef identity is documented across the concept/structure pages (the
  identity concept page split into **Object IDs** and **File IDs**), with the creation-anchored, move-invariant
  identity proven on-disk; new reference findings and errata recorded; the whole documentation set reconciled to
  the current tool behaviour.

## v1.3.0 — 2026-08-06 — non-resident extraction, integrity verification, sparse-aware recovery

**`extract` now recovers non-resident files whose extent map is stored inline in the directory record — the
common case on ReFS 3.14 — verifies their per-cluster integrity checksums, and correctly handles sparse holes.
Validated corpus-wide (v3.4 / v3.14 / Insider, 2 GB–15 TB): no size mismatches, and snapshot/data output is
byte-identical to the previous release wherever it already worked.**

- **Inline-extent non-resident files extract.** A non-resident file often keeps its extent map *inline* in the
  directory value (the file lists as `IsResident=False`). `extract` now reassembles these directly — reading each
  extent's clusters and stitching them in file order — so ~45–79 % of 3.14 files that previously had to fall back
  to `dataruns` now extract in one step. Reassembly stops (and says so) only for the rare oversized/overflow
  extent table; nothing wrong is ever written.
- **Per-cluster CRC32-C integrity verification.** On an integrity-stream file (3.14, 4 KiB clusters), each cluster
  carries an inline CRC32-C checksum. `extract` recomputes and checks every one and reports
  `integrity: N/N clusters CRC32-C-verified`; a mismatch (on-disk corruption or tampering) is flagged prominently
  with the offending cluster and stored-vs-actual CRC — the bytes are still written. Disable with
  `--no-verify-integrity`. (SHA-256 and 64 KiB-cluster volumes store checksums out of line and are reported as
  such rather than verified inline.)
- **Sparse holes are zero-filled.** A hole in a file's extent map (a sparse region) is now reconstructed as zeros
  rather than read from disk, so recovered and carved files are byte-correct for sparse files, and the snapshot,
  CoW, and deleted-file carve paths share the same sparse-aware, integrity-aware extent decoder.
- **Full-path `extract` is direct.** Addressing a file by an absolute `/path` resolves it component-by-component
  from the root with no depth limit (a bare name is still searched across the tree); extracting a deep file by its
  full path is now instant.

## v1.2.0 — 2026-08-02 — deletion/recovery overhaul

**Deleted-file recovery is now organised into two simple modes and classified by file identity. Corpus-validated
across the whole image set (v3.4 / v3.14 / Insider, 2 GB–15 TB): no crashes, and every recovery-mode result is a
strict subset of the complete pass.**

- **Two recovery modes.** `deleted` (default, *recovery*) runs the Trash table, checkpoint differential, and the
  live-page B+-tree node-slack scan — quick. `deleted --full` adds a bounded orphan-page scan and carves
  non-resident content. All fine-grained flags (`--no-slack`, `--trash`, `--scan-pages`, `--carve`, `--max-scan`,
  `--search`) remain as overrides; each mode points to the other.
- **Identity-based classification.** A remnant is *deleted* only when no live file with the same **name and
  creation-time** exists anywhere on the volume; otherwise it is a still-present CoW prior version, or a neutral
  *former location* of a moved/renamed file. Creation-time is immutable across move/rename, so it separates the
  same file relocated from a different file that reuses the name (a common filename deleted from one folder is
  never hidden by an unrelated live copy elsewhere). This **supersedes** the earlier owner-aware / global-name
  tests. A copy-then-delete-original stays recoverable (the copy has a new creation-time).
- **Recover once, log every location.** Identical files deleted from several directories are recovered once, and
  the new **recovery log** — written on every run — records each deletion location plus the full
  deleted-vs-still-present split with each remnant's source page (`--log PATH` to place it).
- **`deleted --orphans` tier.** An opt-in, low-confidence scan for Object-Table objects unlinked from the tree,
  identity-filtered so a live file is never mislabelled deleted.
- **Exact-extent recovery of deleted non-resident files.** A deleted non-resident file's extent map lives in a
  type-0x40 backing record that survives in the same page slack; `deleted` recovers it, matches it to the name row
  by `(file_id, home-dir)` + exact size, and `export deleted --carve` reassembles the file byte-for-byte
  identically to the live `extract` path (best-effort — clusters may have been reused).
- **Deleted-directory grouping.** A deleted directory's children are grouped under `$DELETED/DIR_OID_0x<oid>/`,
  anchored on the physical page they were recovered from; the folder's name is a best-effort candidate, flagged
  **ambiguous** under rename/move churn — a named ancestor path is never asserted.
- **`files --deleted` and `search --deleted` removed.** Deleted-file recovery now lives solely in the `deleted`
  command; the `files`/`search` listings cover the live tree only.
- **Documented (not implemented) identity techniques:** journal-identity (USN `FILE_DELETE` close-time + MLog
  corroboration) and Parent-Child-Table OID-exact ancestry for deleted directories — both disk-analysed and
  written up on the Deletion Recovery page for manual use.

## v1.1.0 — 2026-07-28 — tool-consistency fixes

**Aligned `refsanalysis.py`'s enriched output with `forefst.py` so the two tools never diverge on the same image
(0 divergence across 110+ images); `forefst.py` byte-unchanged.**

- Residency, non-resident-directory `SecurityId` / `USN` / `InternalFlags`, non-resident backing size-matching, and
  the ADS summary count are now derived identically in both tools.

## v1.0.0 — 2026-07-23 — first public release

First public release. Functionally the same tool as the internal **v3.6.0** development build below —
renumbered to **1.0.0** for the public debut and to avoid confusion with ReFS's own version numbers
(ReFS 3.4–3.14). The per-version development history from the thesis follows.

## Development history (pre-1.0, during the thesis)

*The entries below are the internal `3.x` development versions from the thesis work — not ReFS versions,
and not separate public releases; they trace how v1.0.0 was built.*

## v3.6.0 — 2026-07-04 (first-audit enhancements · F5 residency fix · F6 per-name-MACB timestomp · `recyclebin`)

**New forensic capabilities from the first-audit review, plus two disk-proven findings.**

- **`recyclebin` subcommand (F8).** Decodes `$RECYCLE.BIN` `$I` metadata (formats 1 & 2) → original path, deletion
  time, size, and `$R` payload presence. Confirmed on-disk (3 Explorer-deleted files).
- **`files` CSV 33 → 38 columns.** Added `HardLinkNames` (Q5), `FileId` + `HomeOid` (Q2, join keys reconstructing the
  USN 128-bit FileID), `IsSparse` (F5, `FILE_ATTRIBUTE_SPARSE_FILE`), `InternalFlags` (Q3, e.g. DeleteDisposition) —
  appended before `RefsVersion`; matching JSON keys. `--full-path-column` appends a `FullPath` column.
- **`extract` now recovers resident files (Q7).** Writes a resident file's inline `$DATA` bytes (previously refused).
- **`timestomp` HARDLINK_MACB_MISMATCH (F6).** ReFS stores `$SI` **per hard-link name**, not per-inode — a
  name-scoped timestomp leaves sibling names at the true birth. Journal-independent; flags only the back-dated name.
  Reference: errata E59, finding FN_LINK_003.
- **`is_resident` bug fixed (F5).** A large non-resident file whose type-0x30 value carries an inline `0x10028`
  extent-list (`disk_alloc>0` on the current stream) was mislabeled resident; corrected (validated corpus-wide).
- **`deleted --slack` (Q6)** shows the directory each recovered row was deleted **from** (owning-table OID → path).
- Smaller parities: volume serial in `fastsummary`, `Modified` column in `search`, bodyfile `(deleted)` suffix +
  file_id inode (Q10, F11), Translator-shift comment (Q9).

## v3.5.0 — 2026-06-30 (CLI restructured to subcommands · forensic suite unified in forefst · hand-written help)

**`forefst.py` is now the unified forensic tool and `refsanalysis.py` the slim structure/lab tool.**

- **CLI restructure (breaking).** `forefst.py` moved from flat command-flags to a subcommand model:
  `forefst.py <image> <subcommand> [options]`. The old `--summary` / `--summary-plus` / `--fastsummary` /
  `--fastsummary-plus` / `--oid` / `--search` flags are removed. `summary` and `fastsummary` are now
  **extended-by-default**; object/file inspection is the `details` subcommand (`/path` | `0xOID` |
  `--path` | `--oid`); name search is the `search` subcommand. A version banner notes when a volume is
  &lt;3.14 (some enriched fields may be incomplete).
- **Forensic suite unified in forefst.** The twelve file-level forensic commands — `usn`, `mlog`,
  `timeline`, `timestomp`, `extract`, `security`, `reparse`, `deleted`, `snapshots`, `integrity`,
  `export`, `dataruns` — now live in `forefst.py` (validated byte-identical to the previous
  `refsanalysis.py` implementations across all images, then de-duplicated). Running them under
  `refsanalysis.py` prints a one-line redirect. The old `attributes` command is folded into
  `files --filter <category>` (12 categories). `refsanalysis.py` keeps the structure/lab commands
  (boot/supb/chkp/objects/schema/parentchild/containers/upcase/oid30/files/attributes/details/all/bootedit).
- **`files` CSV is now 32 columns** — `GroupSid`, `AllocatedSize` and `ReparseTag` were appended before
  `RefsVersion` (which stays last); columns 0–27 keep stable indices. `OwnerSid`/`GroupSid` render the
  friendly name + SID; `ReparseTarget` now covers non-resident symlinks on v3.14.
- **Hand-written in-tool help.** Both tools gained per-command help with options + runnable examples:
  `forefst.py <image> <cmd> --help` (or `forefst.py help <cmd>`) and the same for `refsanalysis.py`,
  plus an enriched top-level overview / `--list`. The `docs/tools/` pages were rewritten to match.
- **Fixes (cross-tool consistency):**
  - `refsanalysis.py details` reparse sub-record tag was always `0x00000000` (it read a reserved field);
    now reads the REPARSE_DATA_BUFFER tag at `v+0x0C`, matching the header `ReparseTag` mirror.
  - `refsanalysis.py details` attribute decode now uses the canonical `attrs_to_str` (shows EA /
    Compressed / IntegrityStream / … — previously only six flags).
  - `refsanalysis.py files`/`attributes`/`details` no longer under-report non-resident `HasEA`: the EA bit
    (`0x40000`) is read from the authoritative type-0x40 backing (`+0x48`) instead of the type-0x30 pointer
    (`+0x40`), matching forefst (e.g. +8,141 correctly-flagged files on the Insider image).
  - `forefst.py extract` accepts a leading-slash absolute path and `--path` (symmetric with `details`);
    unknown options are rejected instead of being silently ignored.

## v3.4.2 — 2026-06-20 (hard-link grouping SIZE-MATCHED — fixes a surviving over-merge)

**Tool fix — `forefst.hard_link_count` / `refsanalysis summary++` (`hardlink_extra`):** the v3.4.1
"content-aware" key (resolve to the local `(parent,file_id)` type-0x40 if `alloc>0`, else the home record)
**still over-merged distinct files.** The per-directory ordinal (`file_id` = `value+0x00`) collides — a directory
can hold the type-0x40 stream of a *different* file home'd there under the same ordinal — so the local
content-bearing record at a colliding ordinal is that other file's. Distinct-size files fused (e.g.
`xbpt_output_lima` 403,765 B + `xbpt_record_index` 415,474 B as one group; 30 such groups on `wininsiderrefs8gtest2`,
5 on `win11refs2g`). **Fix:** resolve each name to the candidate stream — local `(parent,file_id)` or home
`(home,file_id)` — whose 0x40 size **equals the name's own size** (`value+0x38`); group on that stream's
`(owner, file_id)`; names matching no candidate are not merged. **Validated by an INDEPENDENT oracle** (each name's
own `value+0x38`, not the grouping key): **0 over-merge across 112 images**, fsutil control `[4,2]`, genuine groups
preserved (`winsider` 33,104). Errata **E51**; master §J / §C.3 updated.

**Audit context — why v3.4.1's "0 mixed across 113 images" was wrong:** that validation
(`verify_hl_integrity.py` / `verify_claim.py` #12) resolved each member's content through the **same colliding key**
the tool grouped by, so over-merged members fetched the identical record and looked consistent — a self-deceiving
check (surfaced by the 2026-06-19/20 forefst soundness audit). Both gates were **re-based on the independent
per-name size signal**: they now FAIL on the buggy tool and PASS on the fixed one (mutation-calibrated). Regression
**12/12**.

## v3.4.1 — 2026-06-19 (hard-link grouping re-fix + WSL/FIFO corpus verification)

**Tool fix — `forefst.hard_link_count` and `refsanalysis --summary-plus` (`hardlink_extra`):** the hard-link
grouping previously keyed on the metadata tuple `(home-dir backref, FileId/ordinal, size, ctime, mtime)`, which is
**not an object identity** and **false-merged distinct files** on synthetic `.lnk`/`xbpt_` timestamp-cloned test
images (proven 2026-06-19: two files with different on-disk clusters / SHA1 reported as one hard link). Both tools
now resolve each non-resident name to its **content-bearing type-0x40 record** — the local `(own parent, file_id)`
record only if it has real content (`alloc>0`), else follow the home backref to `(home, file_id)` through any
`alloc=0` link **stub** (the stub representation `MD_DATA_RA_006` describes — it IS real) — and group only names
sharing that physical record. This fixes BOTH the original false-merge AND an over-split (a first presence-based
re-fix wrongly resolved a link's `alloc=0` stub locally; corrected to content-aware). Validated: reproduces
`fsutil hardlink list` exactly (win11refs2gtargeted `[4,2]`); **all-disk content-integrity = 0 mixed across 113
images**; winsider = 33,101 genuine WinSxS groups (preserved); block-clones (CoW, distinct objects sharing
clusters) correctly kept separate. Regression **11/11 all-disk**, gates **453 PASS / 0 FAIL**.

**WSL/FIFO/hard-link corpus verification (all 113 ReFS images):** confirmed the two formerly-"unconfirmable" claims
are *present* on existing images, not absent — **MD_ATTR_RA_004** (WSL FIFO) on exactly **3** images (reparse tag
`0x80000024` + `$LXMOD` `S_IFIFO`), **MD_DATA_RA_006** (hard links) on **52** distinct images (53 rows; genuine, per the fixed tool — fsutil-ground-truthed on win11refs2gtargeted; the pre-fix tool reported 28, under-counting via over-split). New
durable per-disk feature table **`image_special_features.csv`** (WSL / FIFO / device-node /
hard-link presence) so these never need a full re-scan. Corrected the MD_ATTR_RA_004 octal
(`0120000`→`S_IFIFO 0o010000`) and §J `winsider=10`→33,101 (genuine, content-aware). Reports:
`fifo_hardlink_corpus_scan_2026-06-19.md`, `hardlink_false_positive_verification_2026-06-19.md`.


## v3.4.x — 2026-06-19 (knowledge corrections E45–E50 + workspace consistency pass)

**Reference corrections (errata E45–E50, static-decompilation + all-disk verified):**
- **E45 / E30** — the resident type-0x30 directory-entry value is an INDEX ENTRY (FILE_NAME-like), not a verbatim `$SI`; `value+0x58` = FileSize (not USN). The per-file → change-journal link is **LastUsn** (`$SI+0x40` / `value+0x68`) + UsnJournalId (`+0x70`) — proven 480/480 `$J`-record matches.
- **E46** — MSB+ page header `0x40` = TableIdHigh (**always 0**), not "Schema"; the numeric table OID is `TableIdLow` at **`0x48`** (137,444/137,444 pages).
- **E47 → E49** — frame error reversed: Prade's "Index Root" is the `_SmsIndexRoot` descriptor at page+0x50 (schema@0x0C, extents@0x18, total-rows@0x20); GN_IDXR_002/003/004 all CONFIRMED.
- **E48** — non-resident snapshots exist and use the type-0x40 24-byte VLCN extent format (29/30 true snapshots; content byte-exactly recovered).
- **E50** — Parent-Child schema `u32[7]` is the key-comparison-rules selector (8 → `CmsRulesPARENT_CHILD_LINK`), not a "bit-3 = value-overlaps-key" flag; the overlap is a caller-side same-buffer construction.

**Workspace consistency pass (2026-06-19):** propagated all corrections (E45–E50 + E14/E21/E23/E35/E39/§A.4/§B.1a/§B.2/§B.6/FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003/AP_REDO_001–039) from the master `structure_reference.md` + `errata.md` to every drifted derived file (registry rows, structure/concept docs, ``). Self-checksum docs corrected to **cluster-size-dependent**; `$CBW4` marked fabricated everywhere (E35); `$SI` field labels corrected (E21/E23/E39); schema v3.4 count 27→25 (E14); page-OID 0x40→**0x48** (E46). **Regression 11/11 all-disk, gates 0 FAIL, parity green.** (The dated round-1/2 doc-audit artifacts under `audit/` were left as history with a superseded-values banner.)


## v3.4.0 — 2026-06-13 (timestomp detection)

- **New `refsanalysis.py <image> timestomp` subcommand — ReFS timestamp-tamper detection.** NTFS's
 `$SI`-vs-`$FN` dual-set cross-check does not exist on ReFS (no `$FN` timestamps), but timestomping
 is still detectable via three independent anchors, which this subcommand combines:
 - **CHANGE_LATE (intrinsic):** the high-level APIs timestomp tools normally use (Win32 `SetFileTime`,
 PowerShell, .NET) expose only Creation/Write/Access — **not** the metadata-change time (`$SI+0x10`) — so a
 back-dated Created/Modified leaves `change >> max(created, modified)`. A heuristic against common tools,
 **not** tamper-proof: `NtSetInformationFile(FILE_BASIC_INFORMATION.ChangeTime)` or a raw-disk edit can set
 the change time too and defeat it.
 - **USN_BASIC_INFO_CHANGE / USN_CREATE_MISMATCH (authoritative):** a standalone `BASIC_INFO_CHANGE`
 (reason `0x8000`) journal record is a deliberate basic-info edit with no content change, recorded
 at the real time; `FILE_CREATE` gives the true creation time to compare against `$SI`.
 - **PRE_FORMAT / FUTURE:** Created before the volume existed / after its last write.
 Confidence tiers **HIGH/MEDIUM/LOW** reflect independent-source agreement. Output: human table,
 `--json`, `--csv` (per-file path/confidence/signals/MACB), `--all`, `--min`, `--margin-days`.
 **Validated** on `win11refstestmftecmd.raw` (75 `SET_TIMESTAMPS` ground truth): HIGH precision 100 %
 (every HIGH has a provable basis), 0 false positives on the clean baseline and a clean operations
 image (renames/ADS/snapshots/hardlinks). Honest limitation: intrinsic-only HIGH (CHANGE_LATE +
 PRE_FORMAT) also matches a creation-time-preserving copy (robocopy `/COPY:T`, restore) — the USN
 journal disambiguates. Method doc: `docs/concepts/timestomp_detection.md`.
- **Shared `forefst.timestomp_intrinsic_flags()` helper** (stdlib) exposes the intrinsic
 CHANGE_LATE/PRE_FORMAT/CREATE_GT_MODIFY/FUTURE flags so a listing can carry them per-row without the
 journal. `docs/concepts/standard_information.md` + `docs/ntfs_comparison.md` corrected (they had said
 ReFS timestomp detection was "not available").

## 2026-06-13 — Full claim audit (405/405) + doc-statement audit

- **Claim audit COMPLETE — all 405 reference_table claims** validated through a deterministic harness
 (`analysis/reports/audit/`): each has a verified ref_id↔claim correspondence, a proof (disk matrix /
 exported decompiled function / sourced citation), and a corpus-aware verdict across 110 ReFS images.
 Result: 115 CONFIRMED + 69 STATIC-CONFIRMED + 212 STATIC-CITED + 3 CORROBORATED + 1 RD-LIMITED +
 5 CONTESTED-by-design (documented corrections, findings FS_CHKP_RA_015/CT_CTBL_010, CT_CTBL_RA_006/FS_CHKP_RA_012, FS_CHKP_RA_005, FS_CHKP_RA_001, FS_CHKP_RA_013). See `AUDIT_COMPLETE.md`.
- **Doc-statement audit (76/76 docs)** — ~41 verified fixes; the docs were already excellent (errata applied).
 Two stale clusters fixed (each predating the claim-audit): SUPB/CHKP self-checksum is **CRC64, verified +
 self-healed** (FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003, not "CRC32-C not verified"); DataSize = `$DATA` allocated_size, **not** 8-byte-aligned
 (CT_CTBL_RA_003, AP_LGFL_RA_008, AP_LGFL_RA_004). See `DOC_AUDIT.md`.
- **CRC64 label corrected everywhere** — ReFS metadata CRC64 uses the **custom poly 0x9A6C9329AC4BC9B5**
 (`ClMulCsCrc64`), **NOT ECMA-182** (GN_PREF_002; proven: `forefst.refs_crc64` reproduces every stored page-ref
 checksum, 0 mismatches; ECMA gives different values). The stale "CRC64-ECMA" was propagated out of
 `structure_reference.md`, `reference_table.csv`, and several docs to match.

## v3.3.4 — 2026-06-13 (tool changes driven by the claim audit: CT-by-ID, $SI type-0x10 gate, CRC64 labels)

These are the **tool-behavior** changes that followed the 405-claim audit (the entry above corrected the
*docs/reference*; this entry corrects the *tools*). Plan + evidence: `analysis/reports/plan_tool_updates_from_audit.md`.

- **Container-Table selection is now by Table-ID `0x0B`, not by root index 7 (finding FS_CHKP_RA_015, robustness).**
 New `_select_ct_root(f, ps, cs, roots)` picks the Container-Table root from the failover pair {root 7, root 8}
 by reading the table-root page header `+0x48` (prefers the primary `0x0B`, falls back to the duplicate `0x0C`,
 then to index 7). Used in `bootstrap()`, the older-checkpoint reader, and the 3 `refsanalysis` CT-read sites.
 **Full-corpus regression: bootstrap 110/110, selected CT carries Table-ID `0x0B` on 110/110, translator
 resolves 110/110, 0 failures.** Old (index-7) vs new (id-`0x0B`) differ on exactly the 4 `millionsofactions`
 2 TB images, where root 7 carried the `0x0C` duplicate; the duplicate and primary maps are byte-identical
 (16192 containers each), so the old behaviour already produced correct results — the fix makes the selection
 canonical and robust to a stale copy.
- **`$SI` is now parsed only from a top-level type-`0x10` row (validation via $SI USN re-sourcing MD_SI_RA_015).** `cmd_oid_detail` previously
 parsed `if at in (0x10, 0x90)`, which mis-decoded a top-level **type-`0x90`** row (the `$I30_INDEX` template /
 the Upcase-table payload on system OIDs such as `0x7`) as a garbage `$SI` with bogus MACB timestamps. Gated to
 type `0x10`; corpus-safe (0/215 top-level type-`0x90` rows are a valid `$SI`). Validated against ground truth:
 PowerShell fsactivity log **85/85 = 100 %** (create_time + file_size, unique-filename keyed); filename-keyed
 USN journal **411/429 = 96 %**, all 18 residuals explained (17 intentional timestomps that the tool faithfully
 reports, 1 tolerance-boundary artifact) — see `analysis/reports/usn_si_crosscheck_oid_investigation.md`.
- **Attribute-name map: top-level type `0x90` relabelled** "$STANDARD_INFORMATION (own)" → "$I30_INDEX / table
 payload (schema-dependent)" — type `0x90` is overloaded (`$I30_INDEX` when embedded in a 0x30 dir entry per
 MD_ATTR_RA_015; an Upcase/table payload at the top level of a system object), and is never `$SI`.
- **CRC64 output labels: 6 "CRC64-ECMA" strings → "CRC64"** in `forefst.py` + `refsanalysis.py` (`integrity`,
 `boot`, `fixboot` output and the checksum-algo map). Computation was already the custom poly (GN_PREF_002); only the
 printed label was wrong. **DataSize** comment/label clarified to "= `$DATA` allocated_size; not logical, not
 always 8-byte-aligned" (CT_CTBL_RA_003, AP_LGFL_RA_008, AP_LGFL_RA_004/E26).
- Publish gate after these changes: `verify_docs_static.py` 0 FAIL; `verify_docs_tools.py` **453 PASS / 0 FAIL**.

## v3.3.3 — 2026-06-13 (deleted --slack recovery + export subcommand)

- **`deleted --slack` (deletion-recovery "Method 5", finding FS_DEL_RA_005).** Recovers deleted directory entries
 from **B+-tree node slack** — ReFS deletion removes only the row's offset-array slot, so the row body
 (name + inline `$SI` MACB + attrs) persists until a later CoW rewrite. The scanner brute-walks every
 live + orphan metadata page for type-0x30 row headers not in the live offset array, **grades each by
 confidence** (high = both MACB timestamps plausible; medium = one; partial = name fragment only), and
 cross-flags **deleted** (name absent from the live tree) vs **prior-version** (CoW remnant of a living
 file). Validated: **0 false positives** on the clean baseline (all 19 recovered names genuinely absent
 from the live tree — `arg.txt`, `New folder`, superseded `FVE2.{…}` BitLocker metadata); ~70% high-
 confidence, partials flagged honestly. `--extract DIR` writes the recovered rows. Robust on
 v3.4/64K/corrupt.
- **`export -o DIR` (new subcommand) — the ReFS analogue of dumping a raw `$MFT`.** Writes raw,
 hash-verified artifacts: VBR primary + backup, both checkpoints, the SUPB copies, the MLog control
 pages + live log pages (+ index), the reassembled USN `$J` stream, and the **whole object B+-tree
 forest** (`--btree-mode packed` = one `metadata_pages.bin` + `metadata_index.csv`, or `per-object` =
 one file per OID), plus **`manifest.json`** (per-artifact source/lcn/length/sha256) and
 **`sha256sums.txt`** (`sha256sum -c`-verifiable). `--what vbr,chkp,supb,mlog,usn,btree,all` selects
 structures. Reuses `bootstrap` + the integrity backup locators + the MLog/USN readers.

## v3.3.2 — 2026-06-13 (fidelity flags, backup-version analysis, redundancy docs)

- **Perf/fidelity policy — every speed tradeoff now has an enable path.** Added `integrity --max-pages N`
 (raise the full-tree checksum page cap, default 300000; the cap NOTE now points to it) and
 `timeline --depth N` (the $SI walk depth, default 12). Documented the policy in
 `docs/tools/refsanalysis.md` ("Performance & fidelity"): **fast by default, full fidelity always
 reachable by a flag.** Clarified that the v3.3.1 `timeline` `enrich=False` change is a pure
 optimisation with **no output change** (it only gated SecurityId/ADS/reparse fetches the timeline
 never displays; MACB timestamps come from the directory entry).
- **Backup boot-sector message corrected (deeper static analysis, FS_VBR_RA_013 refined + FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003 new).** Tracing
 `refs.sys` showed the VBR backup is validated only by its own 0x16 checksum and is consulted **only on
 a primary read failure** (no cross-copy CRC64/clock), so a version mismatch is reported honestly as
 **"an UPGRADE … or VBR tampering"** (not a definitive upgrade). Corpus check: the divergence appears on
 genuine upgrades (backup keeps the original v3.4 / v3.9) AND on VBR-tampered test images (primary
 v6.66 / v3.15, backup authentic v3.14). By contrast the **SUPB (3 copies) + checkpoint pair** carry
 8-byte CRC64 self-checksums, are selected by highest virtual clock, and self-heal at mount (finding
 FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003) — documented in the new `docs/concepts/redundancy.md`. Backup *failover* (use a backup when the
 primary is corrupt) is planned, not implemented: `analysis/reports/plan_backup_failover.md`.
- **Help + docs:** CLI help and `docs/tools/refsanalysis.md` updated for `--checksums`/`--fullchecksums`,
 the integrity backup section, `timeline --fast`/`--depth`, and the v3.7 routing; `timeline` (previously
 undocumented) added to the command reference; glossary opcode counts and the checksum-architecture
 scope corrected.

## v3.3.1 — 2026-06-13 (split checksums + backup scan, v3.7 opcode routing, fast timeline)

- **`integrity` checksum split:** `--checksums` now verifies **only the system root tables** (fast);
 `--fullchecksums` verifies the **entire metadata tree** (the v3.3.0 full-coverage walk). The
 `--checksums` output points to `--fullchecksums`.
- **`integrity` Redundancy / Backup section (new):** scans ReFS's redundant copies — the backup boot
 sector (last LBA), the alternating checkpoint pair, and the secondary SUPB copies — and verifies each
 (VBR self-checksum `_vbr_checksum`, CHKP signature+vclock+roots, SUPB signatures). Surfaces a real
 forensic signal: on an **upgraded** volume the backup boot sector retains the **original pre-upgrade
 version** (e.g. backup=v3.4 vs primary=v3.14), reported as "UPGRADED from vX.Y" (finding FS_VBR_RA_013). The
 failover (using a backup when the primary is corrupt) is intentionally deferred. Backup anomalies are
 WARNs, not failures.
- **MLog opcode routing fix (finding AP_LGFL_RA_009):** v3.7–v3.13 now use the v3.14 dispatch table (was
 `vmin >= 9`, now `vmin >= 7` via `_redo_ops_for_version`). v3.7 emits the 0x1D–0x1F stream opcodes
 (absent from v3.4) and the old routing left 78 records unresolved on win1121h2test. RD-validated to
 **0 unknown opcodes across all 83 corpus images** with an MLog log; cross-source consistency
 (USN/$SI by OID, MLog by path) confirmed.
- **`timeline` performance (finding via profiling):** the `$SI` MACB phase did one extra B+-tree read
 **per object** (`enrich=True`) that the timeline never used — dropped it (`enrich=False`), and added
 **`--fast`** (alias of `--no-si`) which skips the per-file `$SI` MACB walk entirely. On winsider
 (35K objects / 147K entries) the default `$SI` walk is ~157 s while MLog+USN are ~3 s, so `--fast`
 turns a >180 s run into **~3 s** (change-journals only). A large-volume hint now points to `--fast`.

## v3.3.0 — 2026-06-13 (full-coverage checksum verifier + corrected MLog opcode tables)

- **A1 — `integrity --checksums` now verifies the ENTIRE metadata tree**, not just the ~8–13
 root-table pages. The walk crosses the Object Table's leaf rows (each embeds the object root's page
 reference at value+0x20) into every file/dir/stream B+-tree, recomputing CRC64 (cktype 2) / SHA-256
 (cktype 4) over every interior + leaf page. Coverage rises from ~8 pages to the full tree (e.g.
 snapshots image 906 pages, winsider 35,327). Verified: **full-coverage parity with the structural
 walk and zero false positives on 40 clean images** (v3.4→3.14, 4K/64K, CRC64/SHA-256, upgraded);
 catches the injected corruption in `win11refslasttests_baseline_corrupted` (LCN 0x6400) that the old
 root-only walk missed. Three bugs fixed along the way:
 - **Indirect-checkpoint root base**: the verifier hard-coded the root-offset list at `chk+0x94`; for
 indirect checkpoints (CHKP flags bit 0x200, native v3.14) the base is `le32(chk,0x94)`. Without this,
 root index 0 wasn't the Object Table and object trees were never reached.
 - **`dl`-vs-compact-ref guard**: inner-node child pointers and the OT-leaf embedded ref are the
 compact 0x30-byte page-reference form even when the descriptor length `dl` is larger (0x68 on v3.4);
 the old `len ≥ dl` guard skipped every v3.4 subtree (~40% of pages uncovered). Now guards on the
 checksum's own extent.
 - **Structural false positive**: `_walk_btree_pages` treated each 4 KiB cluster slot of a multi-cluster
 (16 KiB) page as a standalone page, FAILing the all-zero continuation clusters as "Invalid signature"
 on **every** clean multi-cluster volume. Now reads each page-reference's slots as one logical page.
 - `integrity` now returns **exit code 2 on failure** (structural or checksum) for scriptability.
- **A3/A4 — corrected the redo-opcode dispatch tables** (`REDO_OPS_V314`/`REDO_OPS_V34`,
 `OPCODE_CATEGORIES`). Re-read of `CmsLogRedoQueue::PerformRedo` shows the ranges are **contiguous and
 almost entirely handled**: v3.4 = 29 values 0x00–0x1C (0 gaps); v3.14 = 44 values 0x00–0x2B with only
 0x17 an explicit error. The previous tables wrongly tagged six handled v3.14 ops
 (0x04, 0x10, 0x14, 0x1B, 0x20, 0x26) and both v3.4 0x08/0x09 as "gaps", and were off-by-one across
 0x1A/0x1B, 0x1E/0x1F/0x20 and 0x28/0x29. Notably **0x20 = `CmsStream::UpdateStreamUserPayload`**
 (handled; 4.0% of records on win11refs2tsnapshots) — not a gap. On-disk proof: opcode 0x04 (formerly a
 "gap") appears in real records. (finding AP_REDO_001–039)
- **A4 — `details <path>` file size on snapshot-bearing resident files**: such files have no live
 `0x80000001` $DATA row; `get_resident_file_size` now falls back to the current-version
 descriptor-`0x10028` holder (sub_id `0x1000`) at value+0x38. Verified arg.txt=15, lasttest.txt=201,
 test.txt=5; normal files unchanged. The per-sub-record `$DATA (default)` line is now consistent too.
- **A2 — MLog control-page region (B1) resolved**: the `0xE48` control area is a compact header
 (populated to ≈byte 0xF8) followed by zero padding (~93% of the area is zero on every image). The
 former "~124 undecoded bytes" are zero gaps + a couple of small constants, not hidden fields.
 (finding AP_LGFL_RA_008)

## v3.2.9 — 2026-06-12 (resident-file details + version export + upgrade flag)

- **A — `details <path>`** (new): full details for ANY file **by path** — resident files have **no OID**
 (their `target_oid` is the sentinel `0x1e000000001`; they live inline in the parent dir row), so `--oid`
 could never reach them. Decodes inline `$SI` (MACB, SecurityId, LastUsn, FileSize (resident index entry; the type-0x10 $SI DataSize is unpopulated)), `$DATA`, ADS,
 snapshots, `$EA`, reparse for resident files; out-of-line extents for non-resident (no own B+-tree). `--json`. Verified: matches
 the lister 15/15 (size + SecurityId).
- **B — `snapshots --file <name>`** lists a file's snapshot versions; `--extract DIR` exports each
 (the 2 modes; built on the verified `recover_snapshot_streams`).
- **C — `deleted --extract DIR`**: export recovered deleted/old-version rows (the orphan-page scan now
 carries the recovered bytes). (Clean volumes have few orphans — image-dependent.)
- **E — summary upgrade flag**: `--fastsummary-plus`/`--summary-plus` now print **"⚠ APPEARS UPGRADED
 (formatted pre-v3.10, now running v3.X)"** vs **"NATIVE vX.Y"**, from the CHKP native-bit 0x080 +
 $VolInfo version-stamp markers (finding FS_CHKP_RA_001, FS_CHKP_RA_003/FS_VOLI_RA_002).
- **F1 robustness fix**: `integrity --checksums` no longer crashes on an upgraded volume (un-translatable
 page slots are skipped, not fatal).
- **Tested:** new-features matrix on the 25 baseline + 64K images (26 total) — **234 PASS, 0 fail**.
 Script: `analysis/tools/analysis_scripts/test_new_features_matrix.py`.

## v3.2.8 — 2026-06-12 (F1 page-checksum verify + F3 super-timeline)

- **F1 — `integrity --checksums`**: recompute each metadata page's checksum vs the stored value
 (tamper/corruption detection). **The ReFS metadata CRC64 was decoded**: reflected, custom poly
 `0x9A6C9329AC4BC9B5` (driver `ClMulCsCrc64`) — **NOT ECMA-182** (the doc's prior poly was wrong),
 init=xorout=~0, over the full page; SHA-256 = `sha256(full_page)`. 0 mismatches across v3.4/v3.14/64K/
 SHA-256. `forefst.refs_crc64()`; finding GN_PREF_002; corrects `checksum_architecture.md`. (Covers root-table
 metadata; per-object B+-tree coverage is a future extension.)
- **F3 — `timeline`**: super-timeline merging **USN + MLog + $SI MACB** into one chronologically-sorted,
 OID-joined event stream (`--file`/`--oid`/`--source`/`--no-si`/`--limit`/`--csv`). The 3 source parsers
 were each validated independently first (USN 6805 / MLog 1322 / $SI 6976 on `win11refstestmftecmd`).
 Caveat: MLog times join by OID + time window (no shared key with USN).

## v3.2.6 — 2026-06-12 (audit follow-up: tool quick-wins + weak-claim reanalysis)

- **Q4 — `security --audit`**: one-shot content-addressed-hash audit over every descriptor → single
 verdict ("CLEAN — 0/N fail") + lists any failures (tamper/corruption check). (FS_SECD_RA_002/FS_SECD_RA_001)
- **Q6 — `extract` EFS guard**: extracting an EFS-encrypted file (FILE_ATTRIBUTE_ENCRYPTED 0x4000) now
 prints a CIPHERTEXT warning instead of silently writing encrypted bytes. (MD_EFS_RA_005)
- **Weak-claim reanalysis (finding CT_CTBL_RA_003, AP_LGFL_RA_008, AP_LGFL_RA_004)**: MD_SI_RA_016 DataSize STRENGTHENED (36/36 == allocated incl. 4
 discriminating desktop.ini cases refuting align8(logical)); AP_LGFL_RA_004, AP_LGFL_RA_007, AP_LGFL_RA_008, AP_LGFL_002 MLog 0x04 magic STRENGTHENED
 (per-volume-stable, survives v3.4→v3.14 upgrade, ≠ VBR serial); CT_CTBL_RA_003 SHA-256 224-byte row CONFOUND
 DECOUPLED (triggered independently by SHA-256 *and* by 64K). Reports: `audit_weak_claims`,
 `plan_F5_extent_resolution`.
- **F1 (page-checksum verify)**: goal documented; shipped in v3.2.8 once the CRC64 was decoded.

## v3.2.5 — 2026-06-12 (finalization: relabel fixes + doc consolidation)

- **Tool relabel bug-fixes** (correctness; from the finalization audit): `fmt_map` compression format 3
 `"LZX"` → **`"LZ4QAT"`** (AP_REDO_037); reparse-index key+0x08 `"parent_oid"` → **`"name_ordinal"`** (FS_REPS_RA_001, FS_OTBL_RA_005);
 `_INTERNAL_FLAGS` += `0x20 REDIRECT_TRUST` (MD_SI_RA_014/E29, was silently dropped).
- **Documentation consolidation:** fixed two internal contradictions (`mlog.md` stale "two-layer"
 summary → four-layer; `SNAPSHOT.md` 0x000E0080 vs 0x10028 reconciled); added the **two checksum
 families omitted from `checksum_architecture.md`** (MLog XOR-fold @entry+0x08 / E42; 24H2
 container-compression per-unit checksums); added **`deletion_recovery.md` Method 4 (Stream Snapshot
 Recovery)** + the FS_CHKP_RA_014 checkpoint-comparison RD result + the disk-snapshot-vs-stream-snapshot caveat;
 added the **compression-policy section to `container_table.md`**; repaired
 **`attributes/STANDARD_INFORMATION.md`** (added a key-offset table incl. SecurityId@0x28, the 0x73/0x7b
 min-size thresholds, the 0x44=high-dword-of-LastUsn note, the HLC-own-row=0 caveat); deduped the
 recovery tables (canonical in `deletion_recovery.md`); added cross-links.
- **Audit reports:** `analysis/reports/audit_weak_claims_2026-06-12.md` (6 under-verified high-impact
 claims + how to strengthen) and `audit_tool_gaps_2026-06-12.md` (applied fixes + F1–F3 feature gaps).

## Docs — 2026-06-12 (S9 compression + S10 system tables)

- **New `concepts/compression.md`**: ReFS 24H2 volume compression decoded (E2 + RD). It is
 **per-container** (not per-file/per-extent); format enum 0=None/1=LZ4/2=ZSTD/3=LZ4QAT; policy on
 disk at the Container Table root-page extended header (format @0xA4, chunk @0xA8) — RD-confirmed
 before/after on the 8 GiB set; `_SmsContainerCompressionHeader` (0x40 B + per-unit u32 length
 array). **Honest limit:** raw end-to-end decompression not achieved (no verified compressed-container
 image in the corpus). Open-question B3 partially resolved; finding AP_REDO_037.
- **S10 system-table docs RD-re-verified + deepened** (finding FS_UPCS_001, FS_PCTB_RA_001, FS_PCHL_001, CT_INTS_001, CT_CNTX_001, FS_OTBL_RA_003): `upcase_table.md` corrected —
 on disk it's a **387-row B+-tree** (name row + index-keyed rows that concatenate to the ~131 KiB
 map, md5-identical across versions), not a flat array; `parent_child_table.md`, `integrity_state.md`,
 `container_index.md`, `trash_table.md` gained RD-verification notes (parent-child/container-index/
 integrity are CHKP-root-only, absent from the Object Table). Script `verify_system_tables.py`.

## v3.2.4 — 2026-06-12

### Stream-snapshot prior-content recovery (CoW) + E2 grounding

- **`snapshots --show` / `--extract DIR`**: recover the prior (snapshotted) content of a file by
 following the extent chain — `$SNAPSHOT` `val[0x44]` data_sub_id → `$DATA` sub-record (key+0x10 ==
 data_sub_id, descriptor 0x10028) → 24-byte extents (VLCN @+0x00, file_vcn @+0x0C, run_length @+0x14)
 → sort by file_vcn → VLCN→PLCN (Container Table) → read → trim to stream size. `forefst.py` adds
 `parse_snapshot_data_entry()` + `recover_snapshot_streams()`.
- **E2 grounding** of the chain: `RefsCreateStreamSnapshot` (win11 L162081-162127) builds the 0x68-byte
 StreamSummary, sets the snapshot flag, stamps the stream-set id + FILETIME; `GetResidentStreamSummaryFromDisk`
 confirms the on-disk layout. The data_sub_id is the snapshotted stream's stream-set id (monotonic).
- **Verified byte-for-byte** (MD5-identical to the independent Step 4.9b export) on 9+ files across
 win11refs2tsnapshots / win11refs4gattributes(test2) / wininsiderrefs2t, incl. multi-extent chains
 (test.txt 42→65→92→"abc"; xbpt json 71 KB / 3.2 MB / 8 extents; up to 21 extents / 13.4 MB).
- Docs: `concepts/copy_on_write.md` gains a **Stream Snapshot Content Recovery** section;
 `attributes/SNAPSHOT.md` gains the full extent-chain recovery procedure + DATA-entry format.
- Verification: `analysis/tools/analysis_scripts/recover_snapshot_content.py`.

## v3.2.3 — 2026-06-12

### MLog LogCore record format fully decoded (four-layer model) + 0x04 erratum

- Resolved open-question **B2b**: each MLog data page is a **LogCore data record** with four
 nested layers — (L1) 0x78-byte record header, (L2) 56-byte entry header (64 on Insider),
 (L3) redo block `_SmsRedoHeader`, (L4) `_SmsRedoRecord`. Decoded from `LogCoreWriteDataRecord`/
 `LogCoreScanDataRecord`/`LogInitializeEntryHeader` (v3.4/v3.14/Insider) + RD on 10 images
 (findings AP_LGFL_001, AP_LGFL_002, AP_LGFL_RA_004, AP_LGFL_RA_007, AP_LGFL_RA_008; `structure_reference.md` E.2/E.2a/E.4; `structures/mlog.md` rewritten).
- L1 fields: sig@0x00, **format magic @0x04 (per-volume constant, NOT a CRC)**, ver@0x08,
 **log-block size @0x0C (0x1000 always — not the volume cluster size)**, UUID@0x10, counter@0x20,
 **LSN@0x28**, **prevLSN@0x30** (chains pre-wrap), length-in-4K-blocks@0x38/0x3C, entry-off@0x54=0x78.
 L2: LSN@+0x00, **checksum (XOR-fold) @+0x08 = page+0x80**, payload-len@+0x20, payload-off@+0x28
 (**0x38 v3.4–v3.14 / 0x40 Insider**), type@+0x30 (2=data, 1=control).
- **Erratum E42**: page+0x04 is a per-volume constant magic, **not a CRC32** — proven (constant
 across every control page + data record in a volume; copied from the log handle, validated by
 equality). The real per-record checksum is the XOR-fold at entry+0x08. Corrects the thesis
 (`analysis_application.tex:74`), `mlog.md`, and `forefst.py`.
- `forefst.py`: `parse_mlog_control_page` field `crc32` → `format_magic`; added
 `parse_mlog_record_header()`. `refsanalysis.py mlog -v`: new **LogCore Record Headers** table
 (per-record LSN / prevLSN / checksum / type / payload-offset with `!chain` wrap markers).
- **64K-cluster scanner fix**: `scan_mlog_data_area` now iterates **4 KiB log blocks** (the MLog's
 fixed I/O unit), not clusters — so 64K-cluster volumes pack 16 log blocks per cluster and the
 scanner sees all of them. Previously it read 1 block/cluster and exposed only 1/16 of the records
 (e.g. `wininsiderrefs8gtest2` 127 → 2,039; `win11refs15t64k` → 2,395). 4K-cluster volumes are
 unchanged (1 block/cluster). Validated on the 25 baseline + all 5 64K-cluster images (26 total),
 all PASS. New `block`/`block_lcn` fields on data-area pages and records; `-v` shows `PLCN.blk`.
- Verification: `analysis/tools/analysis_scripts/probe_logcore_record.py`.

## v3.2.1 — 2026-06-12

### Security descriptor (OID 0x530) full decode

- Decoded the 12-byte ReFS SD value wrapper: +0x00 SD hash (=SecurityId low), +0x04 generation
 (=SecurityId high), +0x08 entry size; SD at +0x0C (findings FS_SECD_RA_001, FS_SECD_RA_002).
- **SecurityId = (generation << 32) | hash32(SD)** — content-addressed dedup. Low 32 = the NTFS
 `$Secure` SD hash (`h=(d+ROL(h,3))`, verified 1,113/1,113); high 32 = collision generation.
 Proven cross-volume (same SD → same SecurityId-low on 3–4 images, 8/8).
- `refsanalysis.py`: added `_refs_sd_hash()` + hash-verification in `security` (`[hash OK]` /
 `[HASH MISMATCH]`, tampering detection); fixed the wrapper "ref_count" mislabel → generation.
- `structures/security_descriptors.md` rewritten with the full byte-level format + dedup model.
- Closes the #1 gap from `audit_missing_information.md`.

## v3.2.0 — 2026-06-12

### Exhaustive $SI / attribute field re-analysis + corrections

Deep per-field analysis of all 18 $SI fields and every attribute type (static
decompilation + 111-image census + ground truth + adversarial verification). Empirical
backbone: `analysis/tools/analysis_scripts/study_all_fields.py` →
`all_fields_census.json` + `field_digest.json` (3-population model:
file_resident / file_own / dir_own). Verdicts in `analysis/tools/analysis_scripts/field_verdicts/`.

Doc/reference corrections (errata E27–E41; findings MD_SI_RA_013, MD_SNAP_RA_007, MD_SNAP_RA_005; MD_USN_RA_004, FS_SCHM_RA_007/MD_ATTR_RA_016/MD_SI_RA_010, MD_SI_RA_008/FN_LINK_002, MD_SI_RA_009
corrected):

- **$SI+0x40 ClassTag → LastUsn**; **$SI+0x48 SessionTimestamp → UsnJournalId** (USN journal
 fields; "storage tiering" disproven). FCB bit 23 = cached-last-USN-valid-for-epoch.
- **$SI+0x58 VersionRefCount → NextFileId** directory child-creation ordinal (not version/CoW).
- **$SI+0x30** = an UNPOPULATED USN slot (0 corpus-wide); the nonzero 're-sourced from $DATA stream summary' data was the type-0x30 index-entry FileSize@value+0x58 (different structure). Real per-file USN = LastUsn ($SI+0x40). [Superseded 2026-06-17: E30 RETRACTED / E45.]
- **InternalFlags bit5 (0x20)** = symlink redirection trust level (not hardlink-zero).
- **HardLinkCount** always 1; prior "confirmed hard links" was a value+0x08 artifact (no real
 hard links in corpus). **$SI+0x74** = NextStreamSetId (base 0xF000), not ExternalFileObjectId.
- **key_flags 0x04 does not exist**; directories use 0x02 + dir bit 0x10000000.
- **type 0xF0** = USN journal $Max metadata (since v3.4). **type 0x20** = per-object FileId index.
- **$SI+0x50 PackedEaSize** = EA_INFO val[0x0C] (not val[0x10]). **$DATA stream_flags** =
 checksum type (0x02 CRC / 0x04 SHA-256) + integrity bit 0x10000.
- **"$CBW4" is fabricated** (only $EFS exists). **$DIR_LINK = $OBJ_LINK** (same structure).
- **E20 reaffirmed** (all ADS inline; a "non-resident ADS" claim was refuted by verification).

### Tool fixes

- **refsanalysis.py `_REPARSE_TAGS`**: full rebuild to authoritative ntifs.h values — the prior
 table was off-by-one / mislabeled throughout (0x8000001B = APPEXECLINK not WOF; 0x80000024 =
 LX_FIFO not AF_UNIX; 0x80000017 = WOF not NFS; etc.). `_decode_reparse_data` notes corrected.
 Resolves the old "lxfifo file with AF_UNIX tag" anomaly (it was always LX_FIFO).
- Non-resident extent resolver: investigated and confirmed **correct** (size-guarded, never
 returns wrong extents); the residual 12–20% unresolved is a completeness gap, tracked in
 `field_verdicts/TOOL_ISSUES.md`, intentionally not rewritten to avoid regression.

### Deep verification of lower-confidence items (2026-06-12)

Four secondary items were deepened (static + raw disk) and personally re-verified on disk:
- **$VOLUME_INFORMATION driver stamp** (finding FS_VOLI_RA_001): +0x82/0x83 = highest driver build that
 ever mounted the volume. CORRECTED a misattribution — a v3.4→Win11-RTM upgrade is vol=3.14/
 **drv=3.14 (equal)**; **drv=3.15 means an Insider build touched the volume** (forensic signal).
- **MI $DATA value layout** (finding MD_DATA_RA_011): summary_size@0x0C = **0x200** (not 0x30); value+0x50 =
 version-count+sparse-flag (not a cluster count).
- **Type 0xB0 attr-bit 0x0800** (finding MD_ATTR_RA_018): E2 bit-gate confirmed (SCB+0x98|0x80); prior
 "non-resident MinStore stream" reading REFUTED; meaning is static-only (never isolated on disk).
- **$SI 0x58–0x6F writers**: reconciled — NextFileId (8-byte, dir own-row, v<3.11) and the
 ExternalFileId path (24-byte, moved file's row, cross-volume) never collide.

## v3.1.0 — 2026-06-11

### MLog (Durable Log) Integration

Core parsing moved from standalone `refs_mlog.py` into `forefst.py` (canonical library). Display and command wired as `refsanalysis.py mlog`.

- **Redo opcode tables**: E2-verified dispatch tables for v3.14 (37 opcodes/43 values) and v3.4 (25 opcodes/27 values)
- **Control page parsing**: MLog signature, UUID, sequence, write counter, data area bounds
- **Data area scanning**: Page classification (MLog/MSB+/DATA/zero), payload extraction
- **Redo record extraction**: `_SmsRedoHeader` + `_SmsRedoRecord` parsing with opcode resolution
- **Transaction decoding** (`--parse`): Groups records into file operations (CREATE, DELETE, RENAME, WRITE, MOVE, etc.) with resolved directory paths and embedded timestamps
- **Output modes**: Default summary, `-v` verbose records, `--parse` transactions, `--csv`, `--json`, `--stats` opcode histogram, `--raw-scan` page dump, `--info` reference

### USN (Change) Journal Integration

Core parsing moved from standalone `refs_usn.py` into `forefst.py`. Display wired as `refsanalysis.py usn`.

- **Journal location**: Finds "Change Journal" entry in OID 0x520 (FS Metadata directory)
- **Sub-record parsing**: Extracts `$J` and `$Max` streams from embedded extent descriptors via VLCN container translation
- **USN_RECORD_V3 parsing**: 128-bit file IDs, 23 reason codes, source flags, file attributes
- **Output modes**: Default list, `--csv`, `--json`, `--stats` reason distribution, `--info` metadata + format reference
- Graceful handling of images without journals (expected for most volumes)

### Code Consolidation

- `build_oid_path_map()` — single implementation in forefst.py (replaces duplicate in refs_mlog.py and refs_usn.py)
- `KNOWN_SYSTEM_OIDS` — consolidated into forefst.py
- All parsing logic in forefst.py, all display logic in refsanalysis.py
- forefst.py: 1515 → 2428 lines (+913: MLog + USN core parsing)
- refsanalysis.py: 5063 → 5743 lines (+680: cmd_mlog + cmd_usn display)
- VERSION bumped to 3.1

### Verification

- Full test suite: 117 images × 24 commands = 2688 tests
- **Results**: 2563 PASS, 120 SKIP (112 NTFS/BitLocker + 8 no-GPT raw partitions), 5 TIMEOUT (winsider 147K-entry image on full-tree commands)
- **0 failures** across all ReFS images on all commands
- All 20 refsanalysis subcommands: 107 PASS, 0 FAIL on all ReFS images
- All 4 forefst modes (csv, body, enrich, deleted): 106 PASS on all testable ReFS images (winsider exceeds 120s timeout)
- `cmd_all` now includes mlog and usn in its sequence

### Documentation

- `structures/mlog.md`: Fixed control page payload offset model (variable via entry header, not fixed page offsets), corrected sequence field to u64, decoded `_SmsRedoRecord` offset 0x10 as value_component_count, expanded UpdateRow timestamp offsets and MODIFY opcode list, updated tooling section for integrated parser
- `structures/usn_journal.md`: Fixed minimum record size (80 bytes structural minimum, 96+ typical), clarified stream_count and sub-record offsets as version-specific observations, added tooling section
- `ntfs_comparison.md`: Added transaction classification and USN timeline analysis comparison points

## v3.0.5 — 2026-06-11

### Research Reports (6 lab reports)

**Phase 3 — v3.4 ADS format**: v3.4 uses fundamentally different sub-record format for ADS — embedded B+-tree subtable headers at ~0xA0 instead of 0x80000001/0x80000002 marker-based chains. Marker pattern writes found in v3.4 decompilation are ETW event flags and storage notification IRPs, not sub-record construction. v3.4 ADS detection requires separate format reverse engineering. Report: `report_v34_ads_detection.txt`.

**Phase 4 — $SI fields 0x50+ verification (5 corrections, E21)**: Verified 883 $SI entries across 5 images against RefsComputeStandardInformationFromFcb decompilation. Five field corrections discovered:
1. ReparseTag at $SI+0x54, NOT $SI+0x4C (0xa000000c for 367+ symlinks)
2. HardLinkCount at $SI+0x70, NOT $SI+0x48
3. $SI+0x48 is conditional u64 (always 0 unless FCB flag bit 23 set)
4. $SI+0x50 is u16-derived u32 (always 0), NOT lower half of SnapshotId
5. VersionRefCount ($SI+0x58) ranges 0–273
Report: `report_si_fields_verification.txt`.

**Phase 5 — Compression extent format**: Container-level compression mechanism identified. File extents on compressed volumes point to VLCNs that translate to B+-tree metadata pages, not file data. `_SmsContainerCompressionHeader` mediates via header+0x40 variable-length mapping data. Full decompression requires parsing the mapping data. Report: `report_compression_extent_format.txt`.

**Phase 6 — BRC (Block RefCount) semantics**: BRC key = start_lcn(u64) + block_count(u64, always 0x400). Per-cluster u16: bit 15 = shared/dedup-managed, bit 14 = dedup metadata, bits 13:0 = reference count (0–505 observed). Value header at +0x18 is a compound field (NOT simple total — upper bits contain flags). 97 BRC rows analyzed on dedup image. Report: `report_brc_semantics.txt`.

**Phase 7 — MLog opcode sequences**: Empirical mapping of opcode sequences to operations across 245K+ transactions. 15 opcodes observed on v3.14 disk (of 37 in dispatch), 12 on v3.4. Dominant patterns: CREATE = INSERT+INSERT+SET_OBJREC (99.9%); DELETE = DELETE or DEL_TABLE chain; RENAME = DELETE+INSERT pairs; MOVE = DELETE+REPARENT+INSERT. Key evolution: v3.4 uses 0x04 at 27% vs <0.1% in v3.14 (replaced by 0x10+0x1F). Report: `report_mlog_opcode_sequences.txt`.

**Phase 8 — Extended GUID survey**: VBR+0x48 Extended GUID populated on ALL native v3.10+ volumes (93/113 images). ZERO on v3.4/v3.7/v3.9 and upgraded volumes. Boundary is v3.10 (Win11 23H2), confirmed by 2 v3.10 images with non-zero GUIDs. Unique per format instance, never modified after format or upgrade. Forensically useful as format-instance identifier and upgrade detector. Report: `report_extended_guid_static.txt`.

### Reference Updates

- **errata.md**: Added E21 — $SI HardLinkCount and ReparseTag at wrong offsets (5 corrections)
- **structure_reference.md**: Corrected C.7 $SI tables (Common, Win10 extension, Win11 extension) with verified field positions; enriched VBR Extended GUID description (native v3.10+, not v3.14+ — confirmed original claim correct)
- **open_questions.md**: Marked A2 RESOLVED (5 corrections), B2 RESOLVED (opcode sequences mapped), B2c RESOLVED (refs_mlog.py complete), B4 PARTIALLY RESOLVED (BRC key/value decoded, compound field at val+0x18 needs refinement), C1 PARTIALLY RESOLVED (GUID survey complete, NVRAM relationship unknown)

### Tools

- **mlog_differential.py**: New script for comparing MLog transactions between consecutive disk images (differential analysis). Confirmed step5/testatomic images all have identical MLog (log checkpointed between operations).
- **verify_si_fields.py**: New script for verifying $SI extension fields across all directory entries in an image.

## v3.0.4 — 2026-06-10

### Alternate Data Streams (ADS)

**refsanalysis.py**: ADS detection and inline extraction.

- Detects ADS in directory entry values via multi-instance sub-records (descriptor 0x000500B0)
- Parses stream names (UTF-16LE), stream sizes, and inline content from the ADS sub-record header
- Filters out snapshot streams (storage_type != 0) that share the same 0x000500B0 descriptor
- `files` command lists ADS with stream name and size
- `extract` command supports `filename:streamname` syntax to extract ADS content
- Validated: 678 ADS across 41 images, all inline (7--47 bytes). SmartScreen tags (7 bytes, "Anaheim"), lab-generated `hidden_NNNN` streams (46--47 bytes). Zero extent-based ADS observed — original thesis claim "ADS always resident" confirmed

### Resident File Extraction

**refsanalysis.py**: `extract` command now supports resident files (key_flags=0x01).

- Resident entries with extent-based data (alloc_size >= cluster_size) are extracted via the same scan-based extent heuristic used for non-resident files
- Properly parses file_size (0x58), alloc_size (0x60), file_attrs (0x48), and timestamps (0x28--0x47) from resident directory entry values
- Empty resident files (file_size=0) handled cleanly
- Inline small files (alloc_size < cluster_size) reported with informative message
- Validated: ho.txt (15 bytes, 1-cluster), xbpt_beta_sierra_570651.json (71,395 bytes, 18-cluster)

### Bug Fixes

- **refs_mlog.py**: Fixed `remaining` over-count (`total_size` → `total_size - first_record_offset`) in two locations; added top-level exception handler; added guard for minimum record size
- **refs_usn.py**: Added top-level exception handler and stream_size sanity check

### Documentation

- **usn_journal.md**: Added 13 missing reason codes (complete Windows SDK set: 23 flags)
- **glossary.md**: Added USN, Change Journal, USN_RECORD_V3 entries
- **page_header.md**: Corrected: MLog does not share the common 80-byte header
- **mlog.md**: Fixed iteration pseudocode (`remaining = total_size - first_off`); corrected page header cross-reference

### Reference Updates

- **errata.md**: E20 retracted — "extent-based ADS" were actually snapshot streams (same 0x000500B0 descriptor, discriminated by storage_type). Original thesis claim "ADS always resident" confirmed across 678 entries / 41 images
- **findings_register.md**: MD_SNAP_RA_005, MD_SNAP_RA_006, MD_SNAP_RA_007 reverted to CONFIRMED — ADS are always resident

## v3.0.3 — 2026-06-10

### USN Journal Parser

**refs_usn.py**: Standalone USN (Change) Journal parser for ReFS (780 lines).

- Locates Change Journal file entry in OID 0x520 (FS Metadata directory)
- Extracts $J data stream via scan-based extent table detection (handles embedded non-resident sub-records)
- Parses USN_RECORD_V3 entries: 128-bit file IDs (OID:index), reason codes, FILETIME timestamps
- OID-to-path resolution via directory tree walk from root 0x600
- Output modes: `--list` (default), `--csv [FILE]`, `--json`, `--stats`, `--info`, `-v`
- Validated: 44/44 ground truth records match (USN values, filenames, reason codes, file IDs, record lengths)
- Tested on 6,874-record image (win11refs4gattributestest2.raw) and 46-record image (win11refslasttests.raw)
- Clean handling of non-USN images ("No Change Journal found")

**Key technical details**:
- Stream size read from multi-instance sub-record marker + 4 (le32)
- Extent table header located by pattern scan (sub_rec_size 0x28, flags 0xe00, count validation) — same heuristic as `_find_extents_in_subrecord` in refsanalysis.py
- Extents require VLCN→PLCN container translation (unlike MLog data area which uses physical LCNs)
- $J stream is pre-allocated at max journal size (128 MB typical); stream_size indicates valid data boundary
- USN_RECORD_V3: minimum 0x50 bytes, 8-byte aligned, no page headers, zero record_length = end of data

## v3.0.2 — 2026-06-09

### MLog Parser

**refs_mlog.py**: Standalone MLog parser rewritten from scratch (1240 lines), replacing the broken `refs_logfile.py` that had wrong opcode numbering (E10), unreliable detection, and no two-layer parsing.

**Core parser** (completed 2026-06-08):
- Correct dispatch tables from E2 decompilation: v3.4 (27 opcode values / 25 handlers), v3.14 (37 / 32), including gap opcodes
- Proper two-layer parsing: outer `_SmsRedoHeader` → inner `_SmsRedoRecord` via `ForEachRedoInBlock` logic
- Opcode read from `_SmsRedoRecord+0x04` (not heuristic scanning)
- Physical LCN addressing for data area (no container translation)
- Validated: 25/25 baseline images, 0 unknown opcodes, record counts 135–33,334

**Transaction analysis** (`--parse`, completed 2026-06-09):
- Groups redo records into per-page transactions (start → operations → commit)
- Classifies into 14 action types: CREATE, DELETE, RENAME, MOVE, WRITE, MODIFY, UPDATE, INSERT, ALLOCATE, STREAM_UPD, CONTAINER, DEDUP, EXTENT_MOD, OP
- OID-to-path resolution via directory tree walk from OID 0x600
- Filename extraction from InsertRow value data (3 formats: tpl=1/schema 0x0130, tpl=0, tpl=2)
- Timestamp extraction from InsertRow v1 (offsets 0x28–0x40), UpdateDataWithRoot v0, UpdateRow v1 (~65–80% coverage)

**Output modes**: `--csv [FILE]` (transaction export), `--info` (action/opcode/timestamp reference), `--stats`, `--json`, `--raw-scan`, `-v`

**Key discovery**: MLog data area LCNs are physical, not virtual — no container translation needed. MLog data pages use the same "MLog" signature as control pages, with entry header at `page+0x54`.

### Documentation

- **mlog.md**: Corrected v3.14 dispatch table (previous version had wrong handler names for most opcodes — e.g. 0x05 listed as "RedoUpdatePageReference" instead of "RedoReparentTable"). Added: physical addressing, data page format, two-layer record structure with field layouts, `ForEachRedoInBlock` iteration logic, transaction classification table, timestamp extraction details, key component layout, tooling section.
- **roadmap.md**: Updated MLog section with --parse/--csv/--info completion.

## v3.0.1 — 2026-06-09

### Post-Thesis Verification

**Static analysis sweep**: 78 reference_table.csv entries promoted from SA=NOT_TESTED (75 to CONFIRMED, 3 to ENRICHED) via automated verification against 4 mass decompilations and the function catalog. Verification script: `analysis/reports/verify_static.py`, results: `analysis/reports/report_static_verification.txt`.

**USN/Change Journal verification** (3 claims):
- **AP_CHJN_001** (RA: NOT_TESTED → CONFIRMED): Compared fresh image (1 row in OID 0x520) vs activated image (3 rows including "Change Journal" file entry). Journal is absent by default.
- **AP_CHJN_004** (RA: NOT_TESTED → CONFIRMED): Walked OID 0x520 B+-tree — type 0x30 key contains "Change Journal" filename in UTF-16LE, confirming storage location.
- **MD_ATTR_009** (RA: NOT_TESTED → ENRICHED): Change Journal entry observed with stream_count=3 in OID 0x520. Attribute name "$USN_INFO" is analyst-assigned (not directly confirmed on disk).

**OID 0x520 correction** (E19): OID 0x520 is an **FS Metadata directory** (schema 0x200, child of root 0x600), NOT "Security ID Mapping". Confirmed by raw disk analysis across 25 images (all show directory-style B+-tree entries: type 0x10 descriptor, type 0x30 filenames) and static analysis of 3 builds (security functions go directly to OID 0x530 via VCB+0xb0; `MsInitializeWellKnownObjectId` is never called with 0x520). Investigation script: `analysis/reports/investigate_oid_0x520.py`, results: `analysis/reports/report_oid_0x520_investigation.txt`. Version-dependent contents: v3.4 has 3 children ("Reparse Index", "Security Descriptor Stream", "Volume Direct IO File"); v3.9+ is empty; USN activation adds "Change Journal".

**OID 0x520 content study**: Deep analysis of all children across 10 images (v3.4 4K/64K, v3.7, v3.9, v3.10, v3.14 upgraded/USN/Insider). Identified degenerate children as backward-compatibility wrappers created by `CreateDownlevelDegenerateMetadataObjects` (flags: 0x400=Reparse, 0x200=Security, 0x100=DASD). Version boundary: exactly v3.7→v3.9 (threshold < 0x307). Mapped Change Journal sub-records: 2 multi-instance (data extents) + 1 single-instance (metadata). OID 0x521 confirmed not persisted to disk. Study script: `analysis/tools/analysis_scripts/study_oid_0x520_children.py`, report: `analysis/reports/report_oid_0x520_children.txt`.

**Documentation updates**: Corrected security resolution chain in `security_descriptors.md` (SecurityId → OID 0x530 directly). Expanded `system_oids.md` with degenerate child details, row structure, Change Journal sub-records, and OID 0x521 status. Updated `usn_journal.md` with Change Journal file entry structure. Added $Extend child-by-child mapping to `ntfs_comparison.md`. Updated `standard_information.md`, `README.md`. Added Subtable F.4c (OID 0x520 children) to `structure_reference.md`. Added E19 to errata, corrected finding FS_SECD_RA_002, MD_SECT_001.

**Errata reformatted**: Backed up previous flat-table format as `errata_backup_20260609.md`. New `errata.md` uses structured per-erratum sections with precise thesis location references (section numbers, table numbers, page numbers from `memoire.pdf`). 19 errata total (E1–E19).

**Tool fix**: `refsanalysis.py` `_KNOWN_OIDS[0x0520]` changed from "Security ID Mapping" to "FS Metadata". `_PC_OID_NAMES` already had the correct label.

**Regression testing**: 190/190 refsanalysis.py (19 subcommands × 10 images) + 30/30 forefst.py (3 modes × 10 images). Images: v3.4 4K/64K, v3.7, v3.14 4K/SHA-256, upgraded, Insider, USN-active.

**reference_table.csv**: SA distribution: CONFIRMED=304, ENRICHED=17, NOT_TESTED=28, NEW=3. RA distribution: CONFIRMED=204, ENRICHED=16, NOT_TESTED=95, INVALIDATED=2, NEW=35.

## v3.0 — 2026-06-09

Major release: `refsanalysis.py` rewritten from subprocess dispatcher to self-contained analysis tool.

### refsanalysis.py

**New architecture**: All 19 analysis subcommands plus `bootedit` are now integrated into a single 4,845-line Python file. Previously, each command was a separate script invoked via `subprocess`. The new version imports parsing functions from `forefst.py` and implements all analysis logic internally.

**New subcommands**:
- `summary++` — Extended volume summary with OID 0x500 detail (version, timestamps, schema count), container utilization, and file attribute statistics (encryption, integrity, compression, hard links, symlinks, snapshots, ADS)
- `bootedit` — Boot sector editor with `repair` (fixboot damage), `set` (field modification), `export`, and `sparse` modes

**Integrated subcommands** (formerly separate scripts):
- `chkp` (from refs_chkp.py) — Checkpoint analysis with container translation
- `objects` (from refs_object_table.py) — Object ID table dump
- `parentchild` (from refs_parentchild.py) — Parent-child relationships
- `containers` (from refs_container.py) — Container table analysis
- `files` (from refs_dirfiles.py) — Directory tree listing
- `attributes` (from refs_attributes.py) — File attribute details
- `dataruns` (from refs_dataruns.py) — File data extent mapping
- `extract` (from refs_dataruns.py) — File content extraction
- `security` (from refs_security.py) — Security descriptor dump
- `reparse` (from refs_reparse.py) — Reparse point analysis
- `deleted` (from refs_deleted.py) — Deleted file recovery
- `snapshots` (from refs_snapshots.py) — Stream snapshots and ADS
- `integrity` (from refs_integrity.py) — Metadata page verification

**Improvements over previous scripts**:
- `reparse`: Recursive directory walk finds reparse points in subdirectories (archive only scanned root level)
- `integrity`: Full B+-tree walk checks all reachable metadata pages (archive only checked 16 root pages)
- Volume label: Fixed key type detection (0x0510, was checking 0x0200)
- Output consistency: All commands use 78-char width, consistent header format

**Dropped subcommands**:
- `timeline` — Duplicate of `forefst.py --body`
- `logfile` — Broken opcode numbering (see E9/E10 in errata). Replaced by standalone `refs_mlog.py` (see v3.0.2)
- `fs` — Duplicate of `all`
- `roots` — Redundant (each root has dedicated tool)
- `volume` — Merged into `summary++`

### Bug Fixes

- **Root 12 addressing**: `_CT_ROOT_INDICES` now includes root 12 (Small Allocator). Previously, root 12 VLCNs were incorrectly translated through the Container Table instead of being treated as physical LCNs.
- **Partition start type**: `--partition-start` value now converted to int immediately. Previously passed as string to `bootstrap()`, causing a crash.
- **GUID parsing**: `_guid_to_text()` wraps bytearray in `bytes()` before passing to `uuid.UUID(bytes_le=)`. Fixes crash in `bootedit repair`.
- **Deleted scan offsets**: `_scan_for_deleted_entries` now adds partition start offset before physical seeks. Previously scanned from byte 0 of the image file.
- **File handle leaks**: All 15 `cmd_*` functions using `bootstrap()` now use `try/finally` for cleanup.
- **Extract allocation cap**: 4 GiB cap on `cmd_extract` buffer allocation prevents OOM on malformed data.
- **Argument validation**: `_int_arg()` helper provides clear error messages for all user-facing integer arguments (`--oid`, `--depth`, `--sid`, `--tag`, `--max-scan`).
- **OID 0x520 label**: Corrected from "Security ID Mapping" to "FS Metadata".
- **Dead code removal**: Removed `tr.translate()` fallback calls (3 sites) — `tr.tr()` is the only method.
- **Extract help text**: Clarified `--oid` scopes directory walk root, not "extract by OID".
- **Schema 0x160 name**: Simplified from "Reparse Index (fka Security Descriptor)" to "Reparse Index".

### Documentation

- **Address translation formula** (E18): Corrected `log2(CPC)` to `CPC.bit_length()` across 4 documentation files. Shift values updated from 14/10 to 15/11.
- **Failover pair numbering**: Corrected Object Table (roots 0/5) and Schema Table (roots 3/9) in checksum_architecture.md.
- **MLog redo opcodes**: Updated from "19 catalogued" to full dispatch tables (32 handlers / 37 opcodes for v3.14, 25/27 for v3.4).
- **OID 0x500 key types**: Added Subtable F.4b to structure_reference.md documenting key types 0x0510, 0x0520, 0x0540.
- **Volume Information**: Expanded volume_info.md with key type layouts, decoded offsets, and driver function references.
- **New pages**: `docs/tools/refsanalysis.md`, `docs/tools/forefst.md` — complete tool documentation with architecture overview and custom script guide.
- **Examples**: Updated all example outputs with larger disk images (2 TiB specials images replacing 1.9 GiB mini baselines).

### Test Coverage

190 tests (10 images x 19 commands) across:
- v3.4 4K, v3.4 64K, v3.14 4K, v3.14 64K, minimal baseline
- Insider (SHA-256, 64K clusters), reparse-heavy (344 symlinks)
- LZ4 compression, upgraded (v3.4 to v3.14)

### forefst.py

No changes. Verified identical to pre-integration version.
