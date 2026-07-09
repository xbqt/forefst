# refsanalysis.py

ReFS **structure and lab** analysis tool — boot sector, superblock, checkpoint, object/schema/container tables, the upcase table, parent-child relationships, a lab-format file/attribute browser, and a boot-sector editor/repair subsystem. It imports its parsing layer from [`forefst.py`](forefst.md) and never modifies it.

> **Forensic commands moved to forefst.** The file-level forensic commands — `usn`, `mlog`, `timeline`, `timestomp`, `extract`, `security`, `reparse`, `deleted`, `snapshots`, `integrity`, `export`, `dataruns` — now live in [`forefst.py`](forefst.md). Running them here prints a one-line redirect — **or reach them without leaving refsanalysis via the `forefst` passthrough** (see [Running forefst commands](#running-forefst-commands-via-refsanalysis)).

## Invocation

```
refsanalysis.py <image> <subcommand> [options]
refsanalysis.py <image>                       # no subcommand → summary
refsanalysis.py <image> summary++             # extended summary
refsanalysis.py <image> <cmd> --help          # detailed help + examples for one subcommand
refsanalysis.py help <cmd>                     # same, without needing an image
refsanalysis.py --list                         # list all subcommands
refsanalysis.py <image> forefst <cmd> [opts]   # run any forefst subcommand (passthrough — see below)
```

Every subcommand accepts `--partition-start <offset>` to override GPT/volume detection (decimal or `0x` hex). The **structure** commands draw from a common verbosity vocabulary — **not every command accepts every flag**; each command's row in the Subcommand Reference (and its `--help`) lists the ones it supports:

| Flag | Effect | Where |
|------|--------|-------|
| `-v` | verbose (extra interpreted values / details) | all structure commands |
| `-vv` | detailed (geometry arithmetic, raw rows) | boot/supb/chkp/objects/schema/parentchild/upcase |
| `--verify` | append a consistency-check table (OK/FAIL) | boot/supb/chkp/objects/schema/parentchild/upcase |
| `--raw` | hex+ASCII dump of the structure's page | boot/supb/chkp |
| `-H` | force the header banner (image, SHA-256, offset) | boot/supb/schema/upcase |

## Running forefst commands via refsanalysis

`refsanalysis.py <image> forefst <cmd> [options]` delegates to [`forefst.py`](forefst.md), so **every** forefst
subcommand is reachable without leaving refsanalysis — the file lister (`files`/`summary`/
`search`/`details`) and the full forensic suite (`usn`/`mlog`/`timeline`/`timestomp`/`extract`/`security`/
`reparse`/`deleted`/`snapshots`/`integrity`/`export`/`dataruns`). It re-uses forefst's real dispatch (no code
is duplicated), so the behaviour, options, and output are identical to running `forefst.py` directly.

```
refsanalysis.py disk.raw forefst usn --stats            # forefst's USN activity summary
refsanalysis.py disk.raw forefst files --filter ea --json   # forefst's file listing (EA-only) as JSON
refsanalysis.py disk.raw forefst timeline --fast            # forefst's super-timeline
refsanalysis.py disk.raw forefst --help                     # forefst's full subcommand list
refsanalysis.py disk.raw forefst usn --help                 # help for one forefst command
```

`refsanalysis.py help forefst` describes the passthrough itself. (This is a convenience bridge; `forefst.py`
remains the single implementation of the forensic commands.)

## Quick Start

```
refsanalysis.py disk.raw summary                       # volume overview
refsanalysis.py disk.raw summary++ --json              # extended summary, JSON
refsanalysis.py disk.raw files -v                       # lab-format file listing
refsanalysis.py disk.raw attributes --filter wsl        # files carrying WSL metadata
refsanalysis.py disk.raw details /dir/file.txt          # full per-file record by path
refsanalysis.py disk.raw boot --verify                  # decode + check the VBR
refsanalysis.py disk.raw chkp -vv                       # checkpoint + container translation
refsanalysis.py disk.raw objects                        # object-ID table
refsanalysis.py disk.raw schema                         # schema table
refsanalysis.py disk.raw bootedit repair --dry-run      # diagnose fixboot damage (preview)
refsanalysis.py disk.raw all > structure_dump.txt       # run every structure tool
```

## Subcommand Reference

### Volume overview

| Command | Description | Examples |
|---------|-------------|----------|
| `summary` | Volume overview: ReFS version, GUID/label, cluster & container size, checksum type, checkpoint state, root-table counts. | `summary` · `summary --json` |
| `summary++` | Extended overview: adds OID 0x500 volume detail and additional metrics. (forefst's `summary` is the forensic-grade equivalent.) | `summary++` · `summary++ --json` |
| `all` | Runs every owned structure tool in sequence (summary, boot, supb, chkp, schema, objects, parentchild, containers, files). | `all` · `all > dump.txt` |

### File-system content (lab format)

| Command | Description | Examples |
|---------|-------------|----------|
| `files` | Flat namespace listing from the root (or `--oid` subtree). `-v` adds a wide table with decoded attributes, sizes and modified-times. `--depth N` bounds recursion (default 20). | `files -v` · `files --oid 0x705` |
| `attributes` | Per-file attribute deep-dive: decoded flags (TitleCase, space-pipe-space separated, e.g. `Archive | Encrypted`), internal flags, timestamps, EFS/reparse/WSL. `-v` decodes the Extended-Attributes block ($LXMOD/$LXUID/…). `--filter {encrypted,wsl,reparse,snapshot}` narrows results. | `attributes --filter wsl` · `attributes -v --filter reparse` |
| `details` | Full record for ANY file by **path**: timestamps, attributes, SecurityId, and — for resident files — inline sub-records ($DATA, ADS, snapshots, $EA, reparse). Resident files have no Object-Table OID of their own. `--json` for structured output. | `details /hello.txt` · `details /dir/big.bin --json` |

> forefst's `files`/`details` subcommands are the forensic-grade equivalents (38-column CSV/JSON, owner+group SID, hard-link names+counts, snapshot counts, reparse targets, FileId/HomeOid join keys, IsSparse). refsanalysis keeps a lighter, human-readable lab view.

### Structure analysis

| Command | Description | Examples |
|---------|-------------|----------|
| `boot` | VBR decode: signature, version, cluster/container size, serial, checksum. `--verify` runs a consistency table; `--raw` dumps 512 bytes. | `boot` · `boot --verify` · `boot -vv` |
| `supb` | Superblock decode: GUID, version, self-descriptor, checkpoint pointers. `--verify` runs a 7-check table. | `supb` · `supb --verify` |
| `chkp` | Checkpoint decode + the 13 global root tables with VLCN→PLCN container translation. `-v` shows the translation layout; `--verify` checks root count == 13. | `chkp` · `chkp --verify` · `chkp -vv` |
| `objects` | Object-ID table: every OID with friendly name and root LCN. `-v` adds physical LCNs; `-vv` dumps raw entries; `--verify` checks page signatures. | `objects` · `objects -vv --verify` |
| `schema` | Schema / attribute table-type definitions (key rules, value layouts). `-vv` prints raw schema values. | `schema` · `schema --verify` |
| `parentchild` | Directory parent→child relationships. `-v` draws an ASCII tree; `-vv` dumps raw rows; `--verify` runs 6 structural checks. | `parentchild -v` · `parentchild -vv --verify` |
| `containers` | Container table & allocator: geometry, mapped-container counts, capacity/type totals. `-v` appends the per-container table (ID, Phys LCN, Flags, Row, Type). | `containers` · `containers -v` |
| `upcase` | Unicode upcase (case-folding) table. `-v` shows sample mappings; `-vv` dumps every non-identity mapping; `--verify` runs six checks. | `upcase` · `upcase -vv` |
| `oid30` | OID 0x30 session-activity table (v3.10+). `-v` dumps every row's decoded fields. | `oid30` · `oid30 -v` |

### Boot sector repair

`bootedit` inspects or repairs the ReFS VBR. **Writes go to a sparse copy unless `--inplace` is given; always preview with `--dry-run` first.**

| Action | Description |
|--------|-------------|
| `bootedit read` | Display & validate the boot sector (read-only). |
| `bootedit export -o FILE` | Write the 512-byte VBR verbatim to a file. |
| `bootedit repair [--dry-run]` | Diagnose & repair refsutil fixboot damage (zeroed container_size/serial/flags). |
| `bootedit set --field F --value V [--dry-run]` | Rewrite one VBR field and recompute the checksum. |
| `bootedit import -i FILE [--dry-run]` | Replace the boot sector with a 512-byte file. |
| `bootedit sparse -o FILE` | Create a sparse (zero-skipping) copy of the whole image. |

```
refsanalysis.py disk.raw bootedit read                                 # read-only display
refsanalysis.py disk.raw bootedit repair --dry-run                     # preview a fixboot repair
refsanalysis.py disk.raw bootedit set --field checksum_algo --value 2 --dry-run
```

`--inplace` modifies the **original** image (dangerous); without it, write actions target a sparse copy named by `-o/--output`.

## Architecture

`refsanalysis.py` imports its parsing layer from `forefst.py` and never modifies it. Each subcommand is a `cmd_*` function following one bootstrap pattern:

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

`bootstrap()` (from forefst.py) locates the partition, parses the VBR/SUPB/both checkpoints, reads the 13 root pointers, builds the Container Table translator and the Object Table map. Afterwards any structure is reachable via `obj_map[oid]` and `walk_bplus()`.

### Relationship to forefst.py

| From forefst.py | Used for |
|-----------------|----------|
| `bootstrap()` | full volume initialization |
| `walk_bplus()` | B+-tree traversal |
| `build_object_map()` | OID resolution |
| `Translator` | VLCN→PLCN translation |
| `le16/le32/le64`, `parse_vbr/supb/chkp` | byte/structure parsing |
| `parse_sid` / `sid_name` / `attrs_to_str` | the single canonical SID & attribute decoders (shared) |

`forefst.py` is the forensic file lister and forensic suite; `refsanalysis.py` is the structure/lab tool. Both share the same bootstrap and parsing layer. SID and attribute rendering use the **same canonical helpers** in both tools (attribute strings are TitleCase, e.g. `Archive`, `EA`, `ReparsePoint`, joined with ` | `).

## Dependencies

Python 3.6+ standard library only. No pip packages.

## Cross-References

- [forefst.py](forefst.md) — the forensic lister + forensic suite that provides the parsing library
- [Bootstrap Chain](../concepts/bootstrap_chain.md) — the volume initialization sequence
- [Virtual Addressing](../concepts/virtual_addressing.md) — VLCN to PLCN translation
