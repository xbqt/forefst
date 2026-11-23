# refsanalysis.py

ReFS **structure and lab** analysis tool. It decodes:

- the boot sector, the superblock and the checkpoint;
- the object, schema and container tables, the allocator tables, the upcase table, the parent-child relationships and
  the OID 0x30 table;
- files and their attributes, in a lab-format browser.

It also has a boot-sector editor and a repair command for the bootstrap copies (`bootedit`).

It imports its parsing layer from [`forefst.py`](forefst.md) and never modifies it.

> **Status.** refsanalysis is a lab tool. 1.14.0 is its last update: it is not maintained after this release. It
> runs only with the forefst of its own release: with another forefst it writes one line naming both versions and
> exits 1 (the command does not run). A later release keeps forefst 1.14.0 beside it, in `refsanalysis_forefst/`,
> and that copy is the one it imports.

> **Known issues in 1.14.0.** The one that concerns refsanalysis: compressed and compacted containers are not read
> (`containers` lists them with the reason, and a read into one is a recorded skip). The full list, with what to do,
> is in [Known issues in 1.14.0](known_issues.md).

## Invocation

```sh
refsanalysis.py <image> <subcommand> [options]
refsanalysis.py <image>                       # no subcommand → summary
refsanalysis.py <image> summary++             # extended summary
refsanalysis.py <image> <cmd> --help          # detailed help + examples for one subcommand
refsanalysis.py help <cmd>                     # same, without needing an image
refsanalysis.py --list                         # list all subcommands
refsanalysis.py <image> forefst <cmd> [opts]   # run a forefst subcommand on a disk image (passthrough — see below)
```

Every subcommand accepts `--partition-start <offset>` to override GPT/volume detection (decimal or `0x` hex).

The **structure** commands draw from a common verbosity vocabulary. **Not every command accepts every flag**: each
command's `--help` lists the flags it accepts; the table below gives the main ones.

| Flag | Effect | Where |
|------|--------|-------|
| `-v` | verbose (extra interpreted values / details) | all structure commands |
| `-vv` | detailed (geometry arithmetic, raw rows) | boot/supb/chkp/objects/schema/parentchild/upcase/allocators |
| `--verify` | append a consistency-check table (OK/FAIL) | boot/supb/chkp/objects/schema/parentchild/upcase |
| `--raw` | hex+ASCII dump: the 512-byte boot sector, the first 512 bytes of the superblock page, the first 1,024 bytes of the checkpoint page | boot/supb/chkp |
| `-H` | force the header banner (boot/supb: image, SHA-256, offset; schema/upcase: image and version) | boot/supb/schema/upcase |

## Running forefst commands via refsanalysis

`refsanalysis.py <image> forefst <cmd> [options]` hands a disk image to [`forefst.py`](forefst.md), so every forefst
subcommand that reads a disk image is reachable without leaving refsanalysis: the file lister (`files`, `summary`,
`search`, `details`) and the forensic commands (`forefst.py --list` lists them).

A metadata bundle (an `export metadata` directory) and `verify-bundle` need `forefst.py` itself: refsanalysis opens
only a regular file.

It re-uses forefst's real dispatch (no code is duplicated), so the behaviour, options, output and exit code are
identical to running `forefst.py` directly:

- the passthrough returns the exit code `forefst.py` would, including the exit 2 it adds for skipped metadata or a
  volume finding (as in `summary`);
- it runs with the recursion limit `forefst.py` sets itself;
- it ends as `forefst.py` does when the reader closes the pipe (`| head`: no traceback; exit 2 if the run had already
  recorded a finding or a skip, else 0) or the run is interrupted (Ctrl-C: exit 130).

```sh
refsanalysis.py disk.raw forefst usn --stats            # forefst's USN activity summary
refsanalysis.py disk.raw forefst files --filter ea --json   # forefst's file listing (EA-only) as JSON
refsanalysis.py disk.raw forefst timeline --fast            # forefst's super-timeline
refsanalysis.py disk.raw forefst --help                     # forefst's full subcommand list
refsanalysis.py disk.raw forefst usn --help                 # help for one forefst command
```

`refsanalysis.py help forefst` describes the passthrough itself. (This is a convenience bridge; `forefst.py`
remains the single implementation of the forensic commands.)

## Quick Start

```sh
refsanalysis.py disk.raw summary                       # volume overview
refsanalysis.py disk.raw summary++ --json              # extended summary, JSON
refsanalysis.py disk.raw files -v                       # lab-format file listing
refsanalysis.py disk.raw attributes --filter wsl        # files carrying WSL metadata EAs ($LX*)
refsanalysis.py disk.raw details /dir/file.txt          # full per-file record by path
refsanalysis.py disk.raw boot --verify                  # decode + check the VBR
refsanalysis.py disk.raw chkp -vv                       # checkpoint + container translation
refsanalysis.py disk.raw objects                        # object-ID table
refsanalysis.py disk.raw schema                         # schema table
refsanalysis.py disk.raw bootedit repair --dry-run      # check the bootstrap copies, preview restores + fixboot
refsanalysis.py disk.raw all > structure_dump.txt       # run the main structure tools in turn
```

## Subcommand Reference

### Volume overview

| Command | Description | Examples |
|---------|-------------|----------|
| `summary` | Volume overview: ReFS version, GUID/label, cluster & container size, checksum type, checkpoint state, root-table counts. | `summary` · `summary --json` · `summary --mlog` |
| `summary++` | Extended overview: adds OID 0x500 volume detail (the verify block's location among it) and additional metrics. | `summary++` · `summary++ --json` |
| `all` | Runs summary, boot, supb, chkp, schema, objects, parentchild, containers and files in turn. | `all` · `all > dump.txt` |

- `summary --mlog` (or `-v`) adds forefst `summary`'s MLog section, as forefst reads it; without the option the
  section says the log was not read.
- forefst's `summary` is the full forensic report: a walk of the whole directory tree and every metric.
- `all` does not run `allocators`, `upcase` or `oid30`. Its `summary` does not read the MLog (`summary --mlog` does),
  so an MLog finding does not set its exit code. It exits 2 when a section exits 2, or when some sections fail while
  others read the volume; 1 when every section fails.

### File-system content (lab format)

| Command | Description | Examples |
|---------|-------------|----------|
| `files` | Flat namespace listing from the root (or `--oid` subtree). `-v` adds a wide table with decoded attributes, sizes and modified-times. `--depth N` bounds recursion (default FULL — the whole tree). | `files -v` · `files --oid 0x705` |
| `attributes` | Per-file attribute deep-dive: attribute word and internal flags, timestamps, EFS/reparse/WSL, and a `Storage:` line. | `attributes --filter wsl` · `attributes -v --filter reparse` |
| `details` | Full record for ANY file by **path**: timestamps, attributes, SecurityId, the `ObjectRef` (`HomeOID:FileID`), sub-records or extents. | `details /hello.txt` · `details /dir/big.bin --json` |

`attributes`:

- the attribute word and the internal flags are written in `forefst`'s form (`0x20 (Archive)`, `0x0 (none set)`);
- the `Storage:` line uses the words `files` uses: the data residency (`inline` / `extents` / `snapshot-shared` /
  `unallocated` / `unknown`) and the record placement (`embedded`, with the row's size, or `split`);
- `-v` lists the Extended-Attributes block ($LXMOD/$LXUID/…) of a file whose record is embedded; a split (moved or
  hard-linked) file's block is not listed — forefst `details` reads it;
- `--filter {encrypted,wsl,reparse,snapshot}` narrows results; `--filter wsl` selects files with WSL metadata EAs
  ($LX*), a split file's included, where forefst `files --filter wsl` selects by reparse tag (the two counts can
  differ);
- `--depth N` defaults to FULL.

`details`:

- for a file whose record is embedded, it lists the inline sub-records ($DATA, ADS, snapshots, $EA, reparse); for a
  file whose data is in extents, its extents;
- files have no Object-Table OID of their own — address them by path;
- for a split (moved or hard-linked) file, the four times in the text view are the copies cached in its name row,
  which the driver refreshes lazily, so they can lag the file's own record;
- its `Storage:` line gives the data residency and record placement as `files` reports them (JSON `DataResidency` /
  `RecordPlacement`);
- `--json` writes the record as a `files` row (the same 42 keys) followed by `ValueLength`, `USNJournalID`,
  `PackedEASize`, `Streams` and `SubRecords`.

> forefst's `files`/`details` subcommands are the forensic views (42-column CSV/JSON, owner+group SID, hard-link
> names+counts, snapshot counts, reparse targets, the ObjectRef / HomeOID / FileID join keys, IsSparse). refsanalysis
> keeps a lighter, human-readable lab view.

### Structure analysis

| Command | Description | Examples |
|---------|-------------|----------|
| `boot` | VBR decode: signature, version, cluster/container size, serial, volume flags, checksum. [Details](#boot). | `boot` · `boot --verify` · `boot -vv` |
| `supb` | Superblock decode: GUID, version, self-descriptor, checkpoint pointers. [Details](#supb). | `supb` · `supb --verify` |
| `chkp` | Checkpoint decode, the 13 global root tables with VLCN→PLCN translation, and the record's SHA-256. [Details](#chkp). | `chkp` · `chkp --verify` · `chkp -vv` |
| `objects` | Object-ID table: every OID with friendly name and root LCN. | `objects` · `objects -vv --verify` |
| `schema` | The table schemas: the system tables' and the object tables' (a file's, a directory's, a data stream's, by format era), with their key rules and value layouts. | `schema` · `schema --verify` |
| `parentchild` | Directory parent→child relationships. | `parentchild -v` · `parentchild -vv --verify` |
| `containers` | Container table: geometry, mapped-container counts, the containers the tools do not translate. [Details](#containers). | `containers` · `containers -v` |
| `allocators` | The three allocator tiers (Medium / Container / Small) and the volume's used-vs-unallocated accounting. [Details](#allocators). | `allocators` · `allocators -v` · `allocators --json` |
| `upcase` | Unicode upcase (case-folding) table, from the copy refs.sys opens. [Details](#upcase). | `upcase` · `upcase -vv` |
| `oid30` | OID 0x30, the heat engine table (v3.10+). | `oid30` · `oid30 -v` |

`--verify`, on every command that has it, exits 2 when a check does not pass.

- `objects`: `-v` adds physical LCNs; `-vv` dumps raw entries; `--verify` checks the page signatures and that the
  expected OIDs (0x600, 0x520, 0x500, 0x7, 0x9) are present.
- `schema`: `-vv` prints raw schema values. Without a Schema Table the command says so and exits 2.
- `parentchild`: `-v` draws an ASCII tree; `-vv` dumps raw rows; `--verify` runs 6 structural checks. Without a
  Parent-Child Table the command says so and exits 2.
- `oid30` lists the generations (the 10-minute periods in which the volume had I/O) and each row's role, from its key and
  size: the generation's totals, or a container and direction. `-v` dumps every row's value as numbered 64-bit fields
  (not decoded further).

#### `boot`

- The volume flags are written in the flag-word form,
  `0x66 (WritableMount|HardLinksSupported|ChecksumSelectorRead|0x4)`; `-v` adds what refs.sys does with each bit.
- The copy decoded is sector 0 when it carries the ReFS signature, otherwise the backup boot sector the volume is read
  from (said on stderr, exit 2). With no copy found it exits 1, naming the range searched.
- Plain `boot` reads the boot sector only.
- `--verify` adds a consistency table: the fields, the checksum of the primary and of the backup boot sector (the last
  sector), and the version (3.x with a minor of at most 14, and the same as `$VOLUME_INFORMATION`'s unless an upgrade
  explains it).
- `--verify` exits 2 on a row that does not pass, on a container size of 0 (the value `refsutil fixboot` writes; one
  WARN row, the finding below the table) and on a version that is not corroborated. To compare the version it reads
  the volume, so it also exits 2 on a condition of the volume view, as every command that reads the view does.
- `--raw` dumps 512 bytes.

#### `supb`

- It decodes the copy the volume is read from (a backup when the primary is not usable).
- It exits 2 when it shows such a copy, or a copy said to have failed (no copy verifies), and when it marks a
  checkpoint copy FAILED or a newer checkpoint copy cannot be used (the copy named, with why; the full list is in
  `help supb`).
- When the primary is read and a backup that passes its self-checksum carries another `+0x68`, a NOTE gives both
  values and refs.sys's rule: the primary is read when it passes validation; `+0x68` orders only the two backups.
  Under `--verify` it is said below the table instead.
- Plain `supb` marks only a copy it says FAILED (its self-checksum or a root).
- `--verify` adds one row per check of the copy shown, one per superblock and checkpoint copy's self-checksum, one per
  checkpoint copy's roots 0xc, 7 and 8 against its digests, and a `supb_payloads_match` row:
  - two copies whose payloads differ (each copy's own LCN and self-checksum left out) fail it, the copy named below
    the table;
  - a primary passed over keeps its FAIL row, marked "not the copy read";
  - exit 2 on any row that does not pass.

#### `chkp`

- It decodes the copy in use. Its field table names +0x88 / +0x8C as the offset and length of an area of the record,
  and lists the offset / length pairs of the root-offset table, the rollback-protection fields and the attestation
  HMAC when their flags 0x200, 0x400, 0x2000 are set.
- The SHA-256 is given with the span it covers (`1 cluster, 4 KiB`; 64 KiB on a 64 KiB-cluster volume).
- It exits 2 when:
  - a checkpoint copy FAILED its self-checksum;
  - the copy in use cannot be verified or has a root 0xc, 7 or 8 that does not verify;
  - a newer copy cannot be used (the view is then stale), refs.sys rejects the newest copy or every copy, or a copy
    cannot be read;
  - a copy's `+0x10` and `+0x60` clocks differ;
  - the superblock read is not the primary or does not verify.

  The full list is in `help chkp`.
- `-v` shows the translation layout.
- `--verify` checks the copy's self-checksum and each other checkpoint copy's (every copy's roots: `supb --verify`),
  allocator clock ≤ virtual clock, roots 0xc, 7 and 8 against their digests, root count == 13, the root pages'
  signatures, the Container Table and the clusters per container against the VBR. Exit 2 on a check that fails or
  cannot be made.

#### `containers`

- It lists the geometry, the mapped-container counts, the containers the tools do not translate (each with its
  reason), and the allocator tables' row counts ("unreadable" when a table could not be read, never a short count).
- `-v` appends the capacity (the sum of the rows' capacities), a state line (translated / not translated, adding up to
  the rows) and the per-container table: ID, Phys LCN (the first mapping range's start), Flags in hex, Row length, and
  Type (the decoded flags: compressed, compacted, index row missing, all allocated).
- It exits 2 when the checkpoint copy it reads, or the newest copy, FAILED its self-checksum, when a newer copy cannot
  be used, when the superblock read is not the primary or does not verify, and on the other conditions
  `help containers` lists.
- For used-vs-unallocated space use `allocators`: containers are the address map, not the allocation state.

#### `allocators`

- For each tier it prints the totals **recomputed from the allocator's rows** (bitmap rows bit by bit, compact rows
  whole) beside the ones in the **summary ReFS keeps in the tier's root page**.
- Then the volume capacity, which covers the whole volume. What an image holds after the volume is the image tail
  `summary` reports, not free space.
- The two totals can legitimately differ: on ReFS 3.4 the tiers are strictly separated, so the Medium rows span less
  than the summary while the not-allocated counts still match. When both differ, that points at a damaged volume (on
  the volumes measured, only images whose Container Table is truncated); compare with `containers`.
- Rows are accepted only from pages that claim the tier's own table; anything rejected is reported.
- When the allocator's summary cannot be read, the capacity line says
  `Volume capacity: not available (<the reason>)`. When the summary and the boot sector disagree on the volume's
  length, a NOTE says so.
- `-v` adds the individual ranges, `-vv` every row, `--json` machine-readable.

#### `upcase`

- The table has two copies, OID 0x8 and OID 0x7. The rows come from the copy refs.sys opens: 0x8 first, and 0x7 when
  0x8's copy fails. A copy not read that fails, is flagged or differs is said on stderr.
- When no copy can be used, or neither is in the Object Table, the command says so and exits 2. When no copy passes,
  the rows come from a copy read as it is, said, exit 2.
- `-v` shows sample mappings; `-vv` dumps every non-identity mapping; `--verify` runs six checks.

### Boot sector repair

`bootedit` reads and edits the primary boot sector (the one at the start of the volume); `repair` also checks the
backup boot sector, the superblock copies and the checkpoint copies.

**Writes go to a sparse copy unless `--inplace` is given; always preview with `--dry-run` first.**

| Action | Description |
|--------|-------------|
| `bootedit read` | Display & validate the boot sector (read-only). |
| `bootedit export -o FILE` | Write the 512-byte VBR verbatim to a file. |
| `bootedit repair [--dry-run]` | Check every redundant copy of the bootstrap and restore a failing boot sector or superblock copy from one that passes; else diagnose `refsutil fixboot` damage in the primary boot sector. [Details](#what-repair-does). |
| `bootedit set --field F --value V [--dry-run]` | Rewrite one VBR field and recompute the checksum. |
| `bootedit import -i FILE [--dry-run]` | Replace the boot sector with a 512-byte file. |
| `bootedit sparse -o FILE` | Create a sparse (zero-skipping) copy of the whole image. |

```sh
refsanalysis.py disk.raw bootedit read                                 # read-only display
refsanalysis.py disk.raw bootedit repair --dry-run                     # preview the restores and the fixboot repair
refsanalysis.py disk.raw bootedit set --field checksum_algo --value 2 --dry-run
```

`--inplace` modifies the **original** image (dangerous; `repair`, `set` and `import` ask for a typed `YES`). Without
it, write actions target a sparse copy named by `-o/--output` (by default `<image name>_modified<extension>` beside
the image).

#### What `repair` does

- It checks the two boot sectors, the three superblocks and the two checkpoints.
- It restores a boot sector or superblock copy that fails from a copy that passes. Checkpoint copies are reported,
  never restored: each copy is its own record of the volume's state.
- It exits 2 when a copy fails or fixboot damage is found.

What it restores:

- A **boot sector** copy is one whole sector (the boot sector's bytes per sector, 4096 on a 4Kn disk):
  - the primary from the backup the volume is read from, never from a backup that records another version than the
    primary or an earlier one than the volume's checkpoint and `$VOLUME_INFORMATION` show (an upgrade rewrites
    sector 0 only);
  - the backup from the primary;
  - no boot sector is written where the volume has none.
- A **superblock** copy at LCN 0x1E, N−2 or N−3 that fails the superblock tests is rebuilt from the copy the volume
  is read from — its own LCN set at `+0x20` and in its self-descriptor, its self-checksum recomputed — and must pass
  the tests at its LCN before it is written.
- Nothing is written past the end of the image.
- Each restore is printed and appended to `<output>.repair.log` (source copy, offset, length, SHA-256 before and
  after), and every copy is checked again on the result.

The fixboot diagnosis reads the primary boot sector. It flags:

- a zero container size, a zero serial, an implausible version;
- on a 3.14 sector: a zero format GUID beside a zero container size, a checksum selector of 0 while the flags say it
  is read (0x40), and volume flags rewritten beside a zero container size (or flags of 0).

- It is made when no restore of the primary is planned; a run that writes restores leaves it to a `--dry-run` of the
  result.
- The one value it proposes is the container size the driver itself writes at mount (64 MiB), with the checksum
  recomputed. The serial, the GUID, the checksum selector and the flags are not guessed: a copy that verifies is
  their source.

See [Volume Redundancy](../concepts/redundancy.md).

## Exit codes

refsanalysis returns the exit codes `forefst.py` does ([forefst.md — Exit codes](forefst.md#exit-codes); what changed in 1.14.0: [Migrating between releases](migration.md#exit-codes-in-1140)):

| Code | Meaning |
|------|---------|
| `0` | the command ran and flagged nothing |
| `1` | a usage error, an image that cannot be read as a ReFS volume, a file or object named that is not on it, or an output that could not be written |
| `2` | a finding, or work the command could not complete; the output says which |

An output that could not be written is said as `refsanalysis: error: cannot write the output: <reason>` (the file
named when it is one), stdout on a full device included.

The conditions a structure command exits 2 on are in its section above, and in full in `help <cmd>`. A structure the
command needs that is missing from the volume (the Upcase Table for `upcase`, the Schema Table for `schema`, the
Parent-Child Table for `parentchild`) is one of them.

A redundancy finding — a copy the volume is not read from that fails, or copies that differ:

- makes `summary` exit 2 (its section "Redundancy findings (exit code 2)"), as forefst's `summary` does;
- `supb`, `chkp` and `containers`, which show the copies themselves, exit 2 as their sections say;
- the other commands, which read the volume through the copy in use, keep their exit code.

The passthrough returns forefst's.

## Value forms

refsanalysis writes every value in forefst's forms — the times, hex identifiers, flag words, sizes, version labels
and absent values of [forefst.md — Value forms](forefst.md#value-forms).

## Architecture

`refsanalysis.py` imports its parsing layer from `forefst.py` and never modifies it. Most subcommands (summary,
schema, objects, parentchild, allocators, upcase, oid30, files, attributes, details) are `cmd_*` functions that
follow one bootstrap pattern:

```python
def cmd_example(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v"], valued=["--oid"])
    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))
    try:
        # ... analysis using f, ps, cs, tr, obj_map ...
        return 0
    finally:
        f.close()
```

`bootstrap()` (from forefst.py) locates the partition, parses the VBR/SUPB/both checkpoints, reads the 13 root
pointers, builds the Container Table translator and the Object Table map. Afterwards the checkpoint-root tables are
reachable through `roots[i]` and every OID-addressed table through `obj_map[oid]`, both with `walk_bplus()`.

`boot`, `supb`, `chkp` and `containers` read the boot sector, the superblock and the checkpoint themselves, so they
still work when the bootstrap chain is broken (`boot --verify` reads the volume to compare the version). `bootedit`
has its own action dispatcher, and `all` calls the other handlers in turn.

### Relationship to forefst.py

| From forefst.py | Used for |
|-----------------|----------|
| `bootstrap()` | full volume initialization |
| `walk_bplus()` | B+-tree traversal |
| `Translator` | VLCN→PLCN translation |
| `le16/le32/le64`, `parse_vbr` / `parse_supb` | byte/structure parsing |
| `checkpoint_select`, `container_table_read` | the checkpoint copy in use, the Container Table |
| `flag_text` with `FILE_ATTR_FLAGS` | the single canonical flag-word and attribute decoder (shared) |

`forefst.py` is the forensic file lister and forensic suite; `refsanalysis.py` is the structure/lab tool. Both share
the same bootstrap and parsing layer.

Flag words and attributes are written by the **same canonical helper** in both tools: an attribute word is written
`0x420 (Archive|ReparsePoint)`, the hex, then the names joined with `|`.

## Dependencies

Python 3.7+ standard library only. No pip packages.

## Cross-References

- [forefst.py](forefst.md) — the forensic lister + forensic suite that provides the parsing library
- [Internals](internals.md) — how the shared parsing layer reads a volume, and the driver behaviour each step follows
- [Bootstrap Chain](../concepts/bootstrap_chain.md) — the volume initialization sequence
- [Virtual Addressing](../concepts/virtual_addressing.md) — VLCN to PLCN translation
