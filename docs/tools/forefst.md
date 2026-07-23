# forefst.py

ReFS forensic analysis tool. `forefst.py` is the MFTECmd-equivalent for ReFS — it produces comprehensive per-file metadata (CSV / JSON / body file) from a raw disk image — and a full forensic suite on top: the USN journal, the MLog transaction log, super-timelines, timestamp-anomaly detection, file extraction, security descriptors, reparse points, deleted-file recovery, snapshots, integrity checking, and a metadata exporter.

## Invocation

```
forefst.py <image> [subcommand] [options]
forefst.py <image>                  # no subcommand → files (the default)
forefst.py <image> <cmd> --help     # detailed help + examples for one subcommand
forefst.py <image> help <cmd>       # same targeted help — `help` as the subcommand token
forefst.py <image> help             # the general overview (with an image loaded)
forefst.py --list                   # one-line index of every subcommand
forefst.py help <cmd>               # per-command help without needing an image
```

The subcommand token comes **after** the image path. Output formats `--json`, `--jsonl` and `--body` are mutually exclusive; the default is CSV. `--partition-start <bytes>` overrides volume auto-detection (accepts `0x` hex), and `-q`/`--quiet` (on the native subcommands — `files`/`summary`/`search`/`details`) silences the progress lines printed to stderr.

> **Version support:** validated on ReFS 3.14 (24H2). All versions 3.4–3.14 parse, but some enriched fields (e.g. non-resident symlink targets) may be incomplete on 3.4–3.10.

## Quick Start

```
forefst.py disk.raw                                   # CSV file listing to stdout
forefst.py disk.raw files -o listing.csv              # … to a file
forefst.py disk.raw files --json                      # JSON array
forefst.py disk.raw files --body -o timeline.body     # body file for mactime
forefst.py disk.raw files --filter ea                 # only EA-bearing files
forefst.py disk.raw files --deleted                   # include recovered deleted files
forefst.py disk.raw summary                           # full volume triage report
forefst.py disk.raw search "*.docx"                   # find files by name
forefst.py disk.raw details /dir/file.txt             # everything about one file
forefst.py disk.raw usn --stats                       # change-journal activity summary
forefst.py disk.raw timeline --fast --limit 50        # quick super-timeline
forefst.py disk.raw security --audit                  # tamper-check security descriptors
```

---

## Native subcommands

### `files` — list files and directories (default)

Walks the directory B+-tree from the root object (OID `0x600`) and emits one enriched row per file/directory. Default output is the 38-column CSV described [below](#csv-output-fields).

| Option | Description |
|--------|-------------|
| `--json` / `--jsonl` / `--body` | output format instead of CSV (mutually exclusive) |
| `-o, --output FILE` | write to FILE instead of stdout |
| `--filter CATEGORY` | keep only one [attribute category](#files---filter-categories) |
| `--deleted` | also recover deleted files (Trash + orphans + checkpoint diff) |
| `--cow-before IMAGE` | recover prior CoW versions by diffing against an earlier image |
| `--timestomp` | add the `TimestompFlags` column ($SI heuristic) |
| `--depth N` | max directory recursion depth (default 100) |

```
forefst.py disk.raw files -o listing.csv              # full CSV listing
forefst.py disk.raw files --filter hardlink           # only multi-link files
forefst.py disk.raw files --filter ea --json          # EA-bearing files as JSON
forefst.py disk.raw files --deleted --body -o t.body  # body file incl. deleted
```

### `summary` — full volume triage report

Volume identity (version, GUID/label, cluster/container size, checksum type), anchoring VBR/SUPB/CHKP hashes, on-disk state (original / upgraded / native), the 13 root-table row counts, USN-journal status + UsnJournalId, then a full directory walk for file/dir/resident counts, total size, MACB extremes, and encrypted/integrity/compressed/hard-link/snapshot/ADS tallies. Extended by default.

| Option | Description |
|--------|-------------|
| `--json` | emit one JSON object instead of the text report |
| `--hash-image` | also SHA-256 the whole image (chain-of-custody; streams the image) |
| `--depth N` | max recursion depth for the content census (default 100) |

```
forefst.py disk.raw summary                           # text triage report
forefst.py disk.raw summary --json                    # one JSON object
forefst.py disk.raw summary --hash-image              # + full-image SHA-256
```

### `search` — find files/directories by name  *(alias: `find`)*

Case-insensitive substring match on the name across the whole tree; add `--regex` for a Python regex against the basename. `find` is a friendly alias (`forefst.py disk.raw find report`).

| Option | Description |
|--------|-------------|
| `PATTERN` | (positional) name substring, or regex with `--regex` |
| `--regex` | treat PATTERN as a case-insensitive regular expression |
| `--deleted` | also search recovered deleted objects (matches marked `[DEL]`) |
| `--json` / `--jsonl` | emit matches as JSON / JSON Lines |

```
forefst.py disk.raw search report                     # names containing "report"
forefst.py disk.raw search '^link\d+_to' --regex      # regex on the basename
forefst.py disk.raw search secret --deleted           # include deleted objects
```

### `details` — all attributes for ONE object

Full record for a single file, directory or object: timestamps, attributes (incl. EA), SecurityId/owner, USN, reparse target, and — for resident files — the inline sub-records ($DATA, ADS, $EA / WSL metadata, snapshots). Address it by `/path`, `0xOID`, or `--path`/`--oid`.

| Option | Description |
|--------|-------------|
| `/path` or `0xOID` | (positional) leading `/` ⇒ path, `0x` prefix ⇒ OID |
| `--path P` / `--oid O` | explicit addressing |
| `--json` | emit the full record as JSON |

```
forefst.py disk.raw details /wsltests/lxsymlink       # a reparse/WSL file by path
forefst.py disk.raw details 0x705                      # a directory object by OID
forefst.py disk.raw details /dir/file.txt --json
```

---

## Forensic subcommands

### `usn` — USN (Change) Journal

Parses `$UsnJrnl:$J`: per-record USN, timestamp, reason flags, resolved file name and FileID.

| Option | Description |
|--------|-------------|
| `-v, --verbose` | add RecLen/Version/StreamOffset per record |
| `--info` | journal metadata instead of records ($J extents, $Max, record count) |
| `--stats` | activity summary: reason-code distribution, busiest files, time range |
| `--csv FILE` | export all records to a 16-column CSV |
| `--json` | emit `{journal, record_count, records[]}` |

```
forefst.py disk.raw usn                                # list every change record
forefst.py disk.raw usn --info                         # journal layout & health
forefst.py disk.raw usn --stats                        # activity summary
forefst.py disk.raw usn --csv usn.csv                  # export to CSV
```

### `mlog` — MLog (durable transaction log)

Parses the durable logfile: control header, data-area page census, and the redo records. `--parse` groups the
low-level redo opcodes of each transaction into a **concrete action** and resolves the object it touched. The
actions split into **file operations** (`CREATE`, `WRITE`, `RENAME`, `MOVE`, `DELETE`) and the **low-level /
metadata records** that accompany them (`STREAM_UPD`, `REPARENT`, `ENTRY_REMOVE`, `ALLOCATE`, `CONTAINER`,
`MODIFY`, …).

Two classifications are decided by **fact, not by opcode presence** — and both are important forensically:

- **MOVE vs RENAME** — a rename and a move both remove the old name row and insert a new one, and ReFS emits a
  reparent opcode for *both*. forefst compares the **parent-directory OID** of the old vs new name entry: same
  parent → `RENAME` (shown `(same parent 0x..)`), changed parent → `MOVE` (shown `(parent 0x<old> → 0x<new>)`).
- **DELETE vs a row removal** — a bare `RedoDeleteRow` also fires on the old name of a rename/move, so it is
  **not** proof of deletion. `DELETE` is reported **only** when the object's own table is destroyed
  (`RedoDeleteTable`, shown `(object table destroyed)`); a bare row removal is `ENTRY_REMOVE`.

`-v` prints each redo record as `opcode  name  target_oid  @PLCN+offset  key`, so **every field of every action is
verifiable against the raw disk bytes**. (Validated against an independent op log — Generate-FSActivity replay +
the USN journal — MOVE/RENAME/CREATE matched the ground-truth log on all resolvable objects in that one validation run. See
[MLog](../structures/mlog.md#concrete-actions--grouping-redo-opcodes-into-what-a-user-did).)

| Option | Description |
|--------|-------------|
| `-v, --verbose` | byte-level proof: each redo record as `opcode`/`name`/`target_oid`/`@PLCN+offset`/`key` |
| `--parse` | reconstruct concrete actions (file operations + low-level groups) with MOVE/RENAME parent OIDs |
| `--stats` | opcode-frequency section |
| `--raw-scan` | per-page raw dump instead of the data-area summary |
| `--info` | static opcode/action reference text only |
| `--csv FILE` | export transactions (action + opcodes + oid + plcn) to CSV |
| `--json` | emit version/control/mlog_info/data_area/records as JSON |

```
forefst.py disk.raw mlog                               # control header + page census
forefst.py disk.raw mlog --parse                       # concrete file operations + low-level records
forefst.py disk.raw mlog --parse -v                    # same, plus the per-record byte-level proof
forefst.py disk.raw mlog --csv mlog_txns.csv           # export the action timeline
```

### `timeline` — super-timeline (USN + MLog + $SI MACB)

Merges three event sources into one chronological timeline. `--fast`/`--no-si` skips the slow per-file $SI walk.
The **MLog** events use the same concrete-action classifier as `mlog --parse` above — so a directory that was
moved appears as `MOVE` (not a spurious `DELETE`), and a `DELETE` in the timeline means the object's table was
actually destroyed.

| Option | Description |
|--------|-------------|
| `--fast` / `--no-si` | skip the $SI MACB walk (USN + MLog only — much faster) |
| `--csv` | emit CSV to stdout (`timestamp_utc,source,oid,name,event`) |
| `--source S` | keep only one source: `USN` / `MLOG` / `SI` |
| `--file SUB` | keep events whose name/path contains SUB |
| `--oid O` | keep only events for object O (0x hex or decimal) |
| `--limit N` | keep only the first N events after filtering/sorting |
| `--depth N` | max recursion depth for the $SI walk (default 12) |

```
forefst.py disk.raw timeline --fast --limit 50         # quick USN+MLog timeline
forefst.py disk.raw timeline --csv > timeline.csv      # full super-timeline (CSV)
forefst.py disk.raw timeline --file hello.txt          # events touching one file
forefst.py disk.raw timeline --source USN --oid 0x701  # one object's USN history
```

### `timestomp` — timestamp-anomaly detection

Flags timestamp tampering by comparing intrinsic $SI MACB against USN-journal evidence and volume create/modify bounds; tiers each suspect HIGH/MEDIUM/LOW. It also emits `HARDLINK_MACB_MISMATCH` — a ReFS-native, **journal-independent** signal: because `$SI` is stored per name, two hard-link names of one file with divergent Created reveal a name-scoped timestomp (the latest Created is the true birth). Only the back-dated name is flagged, never the clean sibling.

| Option | Description |
|--------|-------------|
| `--all` | include every file, even those with no anomaly |
| `--min LEVEL` | minimum confidence to report: `HIGH` / `MEDIUM` / `LOW` (default LOW) |
| `--margin-days N` | comparison tolerance in days (default 1) |
| `--csv FILE` | write CSV (use `-` for stdout) |
| `--json` | emit a JSON report to stdout |
| `--depth N` | max recursion depth (default 20) |

```
forefst.py disk.raw timestomp                          # list all flagged files
forefst.py disk.raw timestomp --min HIGH               # high-confidence suspects only
forefst.py disk.raw timestomp --csv suspects.csv --min MEDIUM
```

> The `files --timestomp` column is a quick $SI-only heuristic; the `timestomp` subcommand is the USN-corroborated analysis.

### `extract` — extract a file's content (or one ADS)

Recovers a file's bytes and writes them to stdout (redirect to a file): **non-resident** files from their extents, **resident** files from their inline `$DATA`, and **CoW resident files unmodified since a snapshot** from the blocks they share with the latest snapshot. Address by bare name, absolute `/path`, or `--path`; use `name:stream` to pull an ADS (a small ADS from its inline bytes, or a large ≥2 KB ADS reassembled from its on-disk extents). (A large sparse / inline-extent-list file is reported non-resident — use `dataruns` for its extent map; a modified-CoW file's prior versions are in `snapshots --extract`.)

| Option | Description |
|--------|-------------|
| `filename` / `/path` | (positional) the file to extract |
| `--path P` | address the file by path (symmetric with `details`) |
| `--oid O` | re-root the search at object O |
| `--depth N` | max recursion depth for locating the file (default 3) |

```
forefst.py disk.raw extract /specials/gamma.bak > out.bak   # carve by absolute path
forefst.py disk.raw extract report.dat:hidden_6247 > s.bin  # extract one inline ADS
forefst.py disk.raw extract deep.log --oid 0x73c --depth 5  # scope to a subtree
```

### `security` — security descriptors / ACLs

Lists each security descriptor (owner, group, control flags, DACL/SACL ACEs). `--files` maps every file to its SecurityId+owner; `--audit` recomputes the `$Secure` hash to detect tampering.

| Option | Description |
|--------|-------------|
| `-v, --verbose` | include the raw SD hex dump |
| `--files` | map every file/dir to its SecurityId and owning SID |
| `--file SUB` | like `--files`, filtered to names containing SUB |
| `--sid ID` | print only the descriptor for SecurityId ID |
| `--audit` | tamper check: recompute each SD's content hash |
| `--json` | machine-readable output |

```
forefst.py disk.raw security                           # list all descriptors
forefst.py disk.raw security --files                   # map files to owners
forefst.py disk.raw security --audit                   # verify SD hashes
forefst.py disk.raw security --sid 0x1db3cc93d -v
```

### `specials` — special-attribute files (one discoverable home)

Lists files carrying a special attribute. No argument prints a **count summary** of every type; `specials <type>` prints that type's list with type-specific columns; `specials all` prints every section. It is the discovery/list layer (equivalent to `files --filter <type>`, which still works) — for deep operations use `reparse --index`, `snapshots --extract`, `dataruns`, or `export ads`.

| Type | Shows |
|--------|-------------|
| `ads` | each named data stream + its host file (`export ads "file:stream"` to pull one) |
| `reparse` / `wsl` | tag + kind (symlink/junction/WSL) + target |
| `hardlink` | link groups (all names of each multi-linked file) |
| `sparse` | logical vs allocated size + bytes saved (`dataruns` for the extent map) |
| `encrypted` / `compressed` / `integrity` / `ea` / `snapshot` | the matching files (+ owner for EFS, prior-version count for snapshot) |

```
forefst.py disk.raw specials              # count summary of every type
forefst.py disk.raw specials ads          # every ADS + host file
forefst.py disk.raw specials hardlink     # hard-link groups
forefst.py disk.raw specials all --json   # every type, machine-readable
```

### `reparse` — reparse points (symlinks / junctions / WSL)

Walks the tree for files with the REPARSE_POINT attribute and decodes each buffer (tag, target, WSL UID/GID/mode). `--index` dumps the reparse index object (OID `0x540`).

| Option | Description |
|--------|-------------|
| `-v, --verbose` | include the raw reparse-buffer hex / index key bytes |
| `--index` | switch to the reparse INDEX view (OID 0x540) keyed by tag |
| `--tag T` | filter to one reparse tag (0x hex or decimal) |
| `--file SUB` | default mode: filter to names containing SUB |
| `--json` | machine-readable output |

```
forefst.py disk.raw reparse                            # all reparse points + targets
forefst.py disk.raw reparse --index -v                 # dump the reparse index
forefst.py disk.raw reparse --tag 0xa000000c --json    # only symlinks, as JSON
```

### `deleted` — the deleted-file view (list + recoverability)

`deleted` is a **read-only view**: it lists deleted entries and, for each, whether its content is recoverable. To **write files out**, use [`export deleted`](#export--get-data-out-one-home-for-every-extraction-path).

**Recovery methods** (Windows `$RECYCLE.BIN` is separate — see [`recyclebin`](#recyclebin--decode-recyclebin-i-metadata)):

| Method | When | Finds |
|--------|------|-------|
| Trash table (`0xD`) | always | names removed but storage not yet reclaimed — fast, reliable |
| Checkpoint diff | always | top-level names in the older checkpoint but not the current one |
| B+-tree node-slack scan | **default** (skip with `--no-slack`) | deleted rows still sitting in a tree page's free space — plus the directory each was **deleted from** (owning-table OID `page+0x48` → path; blank if unmapped, never invented) |
| Orphaned-page scan | `--scan-pages` | rows in metadata pages no longer linked into the live tree |

The slack scan **runs by default**; `--no-slack` gives a fast Trash+checkpoint pass and `--trash` returns after the Trash table only. Bound scans with `--max-scan`; filter with `--search SUB`.

**Recoverability verdict.** Every listed entry carries a verdict — computed disk-free by running the *same* inline-`$DATA` decoder used for live files on the captured remnant bytes:

| Verdict | Meaning | `export deleted` writes |
|---------|---------|--------------------------|
| `FULL FILE recoverable` | **resident** file — `$DATA` is inline in the record and decodes | `.recovered` (the full file) |
| `extent_backed` | **non-resident** file — data is in on-disk extents, but the extent **map** survives in the remnant | `.carved` **with `--carve`** (best-effort; see below) |
| `metadata only` | non-resident file with no usable data/extent info in the remnant | `.row` only (name/size/timestamps) |
| `fragment only` | a Trash-table key/value fragment | `.row` only |

The verdict is annotated for EFS (`CIPHERTEXT`), sparse (`short read expected`), and partial slack remnants (`corroborate`). "Recoverable" means the bytes (or their extent map) are **present** in the remnant, *not* that they are un-overwritten (there is no allocation/freshness check). A roll-up at the end splits **deleted files** from **prior versions of files still present**, so the counts reconcile exactly with the files `export deleted` writes.

> **Resident vs non-resident — what you can restore.** A **resident** deleted file's *full content* is recovered straight from the remnant (`.recovered`). A **non-resident** file keeps its data in separate on-disk extents — but for the common case the *extent map* is held inline in the record (`extent_backed`), so `export deleted --carve` reconstructs the file from those clusters **best-effort** (they may have been reallocated — the output is labelled `.carved` and flagged in the manifest). Only when even the extent map is gone (`metadata only`) is nothing but the record recoverable here. A complementary, not-yet-implemented method — **whole-disk signature carving** (scan every cluster for file magics, filesystem-agnostic) — would recover those remaining cases.

| Option | Description |
|--------|-------------|
| `--no-slack` | skip the slack scan (fast: Trash table + checkpoint diff only) |
| `--trash` | only the Trash table, then return (fastest) |
| `--scan-pages` | ALSO scan orphaned metadata pages (slower) |
| `--slack` | run the slack scan (already the default; kept for symmetry) |
| `--carve` | with `export deleted`: also reconstruct non-resident (extent-backed) files |
| `--search SUB` | filter recovered entries by name substring |
| `--max-scan N` | max clusters to scan (default 50000) |
| `--extract DIR` | **deprecated** — use `export deleted DIR` (identical result) |

```
forefst.py disk.raw deleted                            # Trash + checkpoint + slack (default) + recoverability
forefst.py disk.raw deleted --no-slack                 # fast: Trash + checkpoint diff only
forefst.py disk.raw deleted --trash                    # fastest: Trash-only check
forefst.py disk.raw deleted --search report            # only deleted entries named like 'report'
```

### `recyclebin` — decode `$RECYCLE.BIN` `$I` metadata

Walks `$RECYCLE.BIN/<SID>/` and decodes each `$I` metadata file — the **original full path**, **deletion time**, and **logical size** of a recycled item — and reports whether its `$R` payload still survives. Filesystem-agnostic Windows format (`$I` header `1` = Vista–8.1, `2` = Win10/11). The `$I` is a small resident file, so its bytes come from the same inline-`$DATA` path as `extract`.

| Option | Description |
|--------|-------------|
| `--json` | machine-readable output |

```
forefst.py disk.raw recyclebin                         # original path + deletion time per recycled item
forefst.py disk.raw recyclebin --json
```

### `snapshots` — stream snapshots (CoW versions)

Inventories files carrying **stream snapshots** — prior versions kept by ReFS's copy-on-write / block-clone mechanism (0xB0 records, `storage_type≠0`, `sub_id≥0x1000`) — and can recover/preview or extract each version's content. Extraction is also available as [`export snapshots`](#export--get-data-out-one-home-for-every-extraction-path).

| Option | Description |
|--------|-------------|
| `-v, --verbose` | per-snapshot allocation/id/value details |
| `--show` | recover & preview each snapshot's prior CoW content |
| `--file SUB` | only files whose path contains SUB (a fuller path disambiguates same-named files) |
| `--snapshot SEL` | select only ONE version: a 1-based `[N]` index, or part of a version name |
| `--depth N` | max recursion depth (default 10) |
| `--extract DIR` | write each recovered version into DIR |
| `--json` | machine-readable inventory |

```
forefst.py disk.raw snapshots                          # list files with snapshots
forefst.py disk.raw snapshots --file lasttest.txt --snapshot first --show   # just one version
forefst.py disk.raw snapshots --file lasttest.txt --show -v
forefst.py disk.raw snapshots --extract ./recovered --depth 12
```

### `integrity` — verify metadata-page checksums

Structural audit of metadata pages. Default is a fast verdict; `--checksums` verifies the system root tables, `--fullchecksums` extends to every object B-tree (CRC64 or SHA-256).

| Option | Description |
|--------|-------------|
| `-v, --verbose` | per-page details (capped 200) |
| `--checksums` | verify the system root tables' checksums |
| `--fullchecksums` | verify every object B-tree (implies `--checksums`) |
| `--scan-range A-B` | raw mode: inspect each LCN in the range standalone |
| `--max-pages N` | cap the checksum crawl (default 300000) |

```
forefst.py disk.raw integrity                          # fast structural verdict
forefst.py disk.raw integrity --checksums              # verify system-root checksums
forefst.py disk.raw integrity --fullchecksums -v       # full sweep + page details
```

### `export` — get data out (one home for every extraction path)

`export <what>` consolidates every "get data out" path. `extract` stays a working alias for `export file`; a bare `export -o DIR` (no subverb) is the metadata bundle (back-compat).

**Output convention.** A **single-value** subverb (`file` / `ads` / `reparse`) prints to the **screen** and reminds you to add `-o FILE` to save it. A **bulk** subverb (`resident-all` / `snapshots` / `deleted` / `recyclebin` / `metadata`) writes to a **directory** — and if you omit the directory it auto-creates a timestamped `forefst_export_<what>_<YYYYMMDD-HHMMSS>/` (and tells you where), so a forgotten path never errors or dumps binary to your terminal.

| Subverb | Gets out |
|--------|-------------|
| `export file <path>` \[`-o FILE`\] \| `--oid O` | one file's live `$DATA` (resident inline / CoW-shared / non-resident extents) — same as `extract`; stdout or `-o` |
| `export ads "<path>:<stream>"` \[`-o FILE`\] | one alternate data stream — inline (small) or reassembled from extents (large ≥ 2 KB) — stdout or `-o` |
| `export reparse` \[`--json`\] \[`-o FILE`\] | the reparse-point inventory (decoded targets/tags/kind) — text by default (same as `reparse`), or `--json` — stdout or `-o` |
| `export resident-all [dir]` | every resident file's inline `$DATA` to a folder, tree preserved (skips 0-byte / non-inline) |
| `export snapshots [dir]` | every stream-snapshot version — same as `snapshots --extract` (aliases: `snapshot`, `prior-versions`) |
| `export deleted [dir] [--carve] [--rows-only\|--content-only]` | recover deleted remnants — the raw `.row` **and** the decoded `.recovered` (resident); with `--carve` also `.carved` (non-resident), plus a `recovery_manifest.json` |
| `export recyclebin [dir]` | surviving `$R` payloads, named by their decoded original filename |
| `export metadata -o <dir>` | the hash-verified metadata bundle (`--what vbr,chkp,supb,mlog,usn,btree` · `--btree-mode packed\|per-object` · `--max-scan N`) |

**`export deleted` writes, per entry, by default:** the raw **`.row`** (the recovered directory-entry record, verbatim — chain-of-custody evidence) and, for a **resident** file whose inline `$DATA` decodes, the **`.recovered`** file (the full reconstructed content). With **`--carve`**, a **non-resident** `extent_backed` entry also gets a **`.carved`** file — reassembled from the extent map held inline in the record (validated byte-exact on a known live extent-backed file; **best-effort** for deleted files because the clusters may have been reallocated, and sparse files short-read — both flagged in the manifest). The distinct `.recovered`/`.carved` extensions mark carved remnants, never verbatim live copies. Files never clobber — a collision auto-renames to `.dup1`/`.dup2`. `--rows-only` reproduces the historical raw-row-only output byte-for-byte; `--content-only` writes just the decoded bytes (drops the evidence — used with a warning). A `recovery_manifest.json` stamps every entry (source, cluster, confidence, verdict, sizes).

> Not yet implemented: **whole-disk signature carving** (scan every cluster for file magics) would recover the `metadata only` cases where even the extent map is gone.

```
forefst.py disk.raw export file /dir/report.docx -o out.docx     # one file, saved
forefst.py disk.raw export ads "notes.txt:hidden"                # one ADS to the screen (add -o to save)
forefst.py disk.raw export reparse --json -o reparse.json        # the reparse inventory as JSON (omit --json for text)
forefst.py disk.raw export snapshots                             # every snapshot -> auto-timestamped folder
forefst.py disk.raw export resident-all ./resident/              # bulk-carve small resident files
forefst.py disk.raw export deleted ./rec/ --carve                # deleted rows: .row + .recovered + .carved + manifest
forefst.py disk.raw export recyclebin ./recovered/              # recover the recycle-bin payloads
forefst.py disk.raw export metadata -o ./bundle/                 # metadata bundle (= the old `export`)
```

### `dataruns` — file data extents / data-runs

Maps non-resident files to their on-disk extents. Default lists extent-backed files; `-v` adds resident/no-extent files and every decoded run (fvcn/lcn/length).

| Option | Description |
|--------|-------------|
| `-v, --verbose` | include resident/no-extent files and every decoded run |
| `--oid O` | start at object O (default 0x600) |
| `--depth N` | max recursion depth (default 3) |

```
forefst.py disk.raw dataruns                           # map extent-backed files
forefst.py disk.raw dataruns -v --depth 5              # full per-file run dump
forefst.py disk.raw dataruns --oid 0x705 -v            # scope to one subtree
```

---

## CSV Output Fields

The `files` CSV has **38 columns**, one row per file/directory, in this order (matching `CSV_COLUMNS` in `forefst.py`):

| # | Column | Description |
|---|--------|-------------|
| 0 | OID | Object Identifier (directories/objects; files emit empty — they have no own OID) |
| 1 | ParentOID | Parent directory OID |
| 2 | ParentPath | Path of the parent directory from root |
| 3 | FileName | File or directory name |
| 4 | Extension | File extension (lowercase) |
| 5 | FileSize | Logical file size in bytes |
| 6 | IsDirectory | `True` if the entry is a directory |
| 7 | IsDeleted | `True` if recovered as deleted |
| 8 | DeletionSource | Recovery method: `trash` / `orphan` / `chkp_diff` / `cow_modified` / `cow_deleted` |
| 9 | IsResident | `True` if content is stored inline in the B+-tree |
| 10 | Created | $SI creation timestamp |
| 11 | Modified | $SI modification timestamp |
| 12 | Changed | $SI metadata-change timestamp (MFT-equivalent) |
| 13 | Accessed | $SI access timestamp |
| 14 | FileAttributes | decoded Windows file-attribute flags |
| 15 | SecurityId | ReFS security-descriptor ID |
| 16 | OwnerSid | owner: friendly name + SID (e.g. `BUILTIN\Administrators (S-1-5-32-544)`) |
| 17 | USN | Update Sequence Number (LastUsn) |
| 18 | HasAds | alternate data stream present |
| 19 | AdsNames | names of detected ADS |
| 20 | IsEncrypted | EFS encryption flag |
| 21 | IsCompressed | compression flag |
| 22 | HasIntegrity | integrity-stream flag |
| 23 | HasEA | Extended Attributes present (correct for non-resident files too) |
| 24 | ReparseTarget | symlink/junction target |
| 25 | HardLinkCount | number of names sharing the file's content |
| 26 | SnapshotCount | number of stream snapshots |
| 27 | TimestompFlags | timestomp heuristic flags (populated with `--timestomp`) |
| 28 | GroupSid | group: friendly name + SID (from the security descriptor) |
| 29 | AllocatedSize | on-disk allocated size (blank when unresolved) |
| 30 | ReparseTag | `IO_REPARSE_TAG_* (0xTAG)` for reparse points |
| 31 | RecoveredChild | child name recovered during deleted/orphan reconstruction (blank for normal rows) |
| 32 | HardLinkNames | `;`-joined names sharing the file's content (non-resident files) |
| 33 | FileId | per-directory child ordinal — the low 64 bits of the USN 128-bit FileID (join key) |
| 34 | HomeOid | home-directory backref — the high 64 bits of the USN FileID (join key) |
| 35 | IsSparse | `FILE_ATTRIBUTE_SPARSE_FILE` (0x200) set — corroborated by AllocatedSize < FileSize |
| 36 | InternalFlags | `$SI` internal flags (e.g. `DeleteDisposition`); blank unless a confidently-named bit is set |
| 37 | RefsVersion | volume ReFS version (always the last column) |

> Columns 0–27 keep stable indices; `GroupSid`, `AllocatedSize`, `ReparseTag`, `RecoveredChild`, `HardLinkNames`, `FileId`, `HomeOid`, `IsSparse` and `InternalFlags` were appended before `RefsVersion`, which remains last, so positional CSV consumers keyed on the early columns or the last column are unaffected. `FileId`+`HomeOid` reconstruct a record's USN 128-bit FileID, making the `files` and `usn` outputs joinable. `--full-path-column` appends one further `FullPath` column (ParentPath/FileName) **after** `RefsVersion`.

### `files --filter` categories

`files --filter <category>` keeps only the matching rows (output format unchanged). Field-based and EA-safe — `wsl` is detected via the reparse tag, not the EA-derived mode:

`reparse` · `encrypted` · `compressed` · `integrity` · `ea` · `ads` · `wsl` · `sparse` · `snapshot` · `directory` · `resident` · `deleted` · `hardlink`

## Body File Format

Sleuthkit/mactime compatible:

```
MD5|name|inode|mode_as_string|UID|GID|size|atime|mtime|ctime|crtime
```

`inode` = OID for directories and system objects; files have no Object-Table OID of their own and emit inode `0`. `mode` is derived from file attributes, and timestamps are Unix epoch.

## Deleted File Detection

Three complementary methods, enabled with `--deleted` (on `files` and `search`):

1. **Trash Table** (OID `0x0D`): names removed but storage not yet reclaimed. Fast and reliable.
2. **Orphan Objects**: OIDs present in the Object Table but unreachable from the directory tree.
3. **Checkpoint Diff**: OIDs in the older checkpoint's Object Table but absent from the current one — deleted in the most recent transaction batch.

The `deleted` subcommand adds two further opt-in methods (orphaned-page scan, B+-tree node-slack scan), shows a **recoverability verdict** per entry (whether the content is present in the remnant and decodes), and pairs with `export deleted` to write the recovered `.row` evidence + the decoded `.recovered` content.

## CoW Version Recovery

`files --cow-before <earlier_image>` compares Object Tables across two images of the same volume. Files whose OID exists in both but whose metadata page LCN differs were modified (CoW allocated a new page); the earlier version's content is recoverable from the old LCN if its clusters were not reallocated. Recovered prior versions appear under a `$COW_PREVIOUS/` path.

---

## Using forefst.py as a library

`forefst.py` is Python 3.7+ standard library only (no pip packages) and exports the parsing primitives, imported by `refsanalysis.py` and available to any script:

| Function | Signature | Purpose |
|----------|-----------|---------|
| `bootstrap()` | `(image_path, partition_start=None)` | `(f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns)` |
| `walk_bplus()` | `(f, ps, cs, tr, vlcns, max_depth=5)` | list of `(key_data, value_data)` tuples |
| `build_object_map()` | `(f, ps, cs, tr, ot_vlcns)` | `{oid: [vlcn_list]}` |
| `Translator` | `.tr(vlcn) → plcn` | virtual-to-physical address translation |
| `le16/le32/le64()` | `(data, offset)` | little-endian integer reads |
| `find_refs_partition()` | `(path)` | partition start offset from GPT |
| `filetime_to_iso()` | `(ft)` | Windows FILETIME → ISO 8601 |
| `parse_resident_btree_rows()` | `(value_data)` | embedded sub-records from a resident value |
| `NON_RESIDENT_MAX_VALUE` | `84` | threshold: `value_length > 84` ⇒ resident entry |

### The bootstrap() call

`bootstrap()` is the single entry point for volume initialization: locate the ReFS partition, parse the VBR (cluster size, version, container size), parse the SUPB (Volume GUID, checkpoint LCNs), parse both checkpoints and select the higher virtual clock, read the 13 root-table pointers, build the Container Table, initialize the VLCN→PLCN translator, and resolve all OIDs. Afterwards any structure is reachable via `obj_map[oid]` and `walk_bplus()`.

```python
#!/usr/bin/env python3
from forefst import bootstrap, walk_bplus, le16, le64, NON_RESIDENT_MAX_VALUE

f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = bootstrap("disk.raw")
try:
    for key_data, value_data in walk_bplus(f, ps, cs, tr, obj_map[0x600]):
        if le16(key_data, 0) == 0x30:                       # filename entry
            name = key_data[4:].decode("utf-16-le").rstrip("\x00")
            # value+0x38 is the file size for NON-resident entries (value_len <= 84);
            # resident files store their size inline — read it with parse_resident_btree_rows().
            if len(value_data) <= NON_RESIDENT_MAX_VALUE:
                print(f"{name}: {le64(value_data, 0x38)} bytes")
finally:
    f.close()
```

## Dependencies

Python 3.7+ standard library only. No pip packages.

## Cross-References

- [refsanalysis.py](refsanalysis.md) — the structure/lab analysis tool that imports this library
- [Bootstrap Chain](../concepts/bootstrap_chain.md) — the initialization sequence in detail
- [Directory Entries](../structures/directory_entries.md) — key type 0x30 format
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — timestamp and attribute layout
