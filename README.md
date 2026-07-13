# forefst — forensic ReFS analysis

**Forensic tools and byte-level structural documentation for Microsoft's Resilient File System (ReFS), versions 3.4 through 3.14.**

ReFS is Microsoft's modern, self-healing file system — the default for Storage Spaces and Dev Drives, and increasingly common on Windows Server and Windows 11. Yet public forensic documentation has effectively stood still at ReFS 3.4, the version reverse-engineered by Paul Prade et al. in *"Forensic analysis of the resilient file system (ReFS) version 3.4"* (2019), and there is still no ReFS equivalent of the mature NTFS toolchain. This project sets out to close that gap: it carries the on-disk analysis forward to the current version 3.14, and ships two tools that read a raw volume with no dependencies.

- **[forefst.py](forefst.py)** — the forensic tool: a file lister and full forensic suite for ReFS volumes.
- **[refsanalysis.py](refsanalysis.py)** — the analysis tool: decode one on-disk structure at a time, for learning the format and validating the forensic tool against new builds.
- **[Structural documentation](docs/)** of every on-disk format decoded during the work, also published as a browsable website at **[xbpt.gitlab.io/forefst](https://xbpt.gitlab.io/forefst/)**.
- **[Lab and verification materials](analysis/)** for building controlled ReFS test images and re-checking every claim.

All versions 3.4–3.14 parse; some enriched fields are version-dependent, with the best coverage on 3.10+ and 3.14. Python 3.6+, standard library only — clone and run.

Why *forefst*? Because of *forensic* and Re*FS*. And also because ReFS is all about B+-trees. And finally because, I think, the more forest on the planet, the better.

Originally built for my master's thesis (*"Forensic analysis of the Resilient File System (ReFS) version 3.14"*, University of Mons, 2026), the project now reaches well beyond its original academic scope. This is its first public release.

## What's novel here

Three capabilities are worth calling out first, because they have no real equivalent in the open NTFS toolchain — and they are what make forefst a *forensic* tool rather than a parser:

- **User actions reconstructed from the transaction log.** `mlog --parse` decodes ReFS's durable log into concrete operations — CREATE, WRITE, RENAME, MOVE, DELETE — with deliberately conservative semantics: a RENAME is told apart from a MOVE by comparing the old and new parent-directory OIDs, and a DELETE is reported only when the object's own B+-tree table is destroyed, not on the bare row removal that a rename also produces. The open NTFS world has never had a maintained `$LogFile` parser; this is the closest thing to one for ReFS.
- **A timestomp signal with no NTFS analog.** NTFS timestomp detection leans on `$STANDARD_INFORMATION` disagreeing with the `$FILE_NAME` timestamp copy. ReFS keeps no such copy — but a hard-linked file carries one `$SI` timestamp set *per name*, so a back-dated name stands out against its siblings and against the change journal, flagging the tampered name specifically and independently of the log.
- **Provenance of the medium itself.** `summary` classifies a volume as original, upgraded, or native, from an on-disk marker an upgrade can never set — a permanent signature of the volume's history, with real consequences (POSIX unlink and hard links require the native format). Nothing in the open NTFS toolchain dates the medium this way.

Each is documented in depth under [docs/concepts/](docs/concepts/).

## Requirements

- **Runs anywhere Python 3.6+ runs** — Linux, macOS, Windows. Standard library only: no `pip install`, no dependencies, no build step. Clone and run.
- **Read-only by design.** Both tools open the input strictly read-only. The single write-capable operation is `refsanalysis.py bootedit repair`, and even that works on a sparse *copy* by default and refuses `--inplace` unless you explicitly ask for it on a writable image — so pointing either tool at evidence is safe.
- **Input:** a raw ReFS image (`dd` / `.raw`), a raw disk or partition device, or an E01 exported to raw (`ewfexport disk.E01`, or mount with `xmount --in ewf --out raw`). forefst locates the ReFS partition inside a full-disk image automatically. Reading a live device (`/dev/sdX`, `\\.\PhysicalDriveN`) needs root / Administrator; reading an image file does not.
- **Performance:** pure Python, so it trades raw speed for portability and auditability. Runtime scales with volume size and file count; `timeline --fast`, `-q`, and `--depth` are the triage levers when you need a first pass fast.
- **Generating fresh test images needs Windows** — the lab is PowerShell, and only Windows can format ReFS. *Reading and analysing* images is cross-platform.

## Quick start

```bash
# Everything forefst can do, one line each
python3 forefst.py --list

# Full forensic file listing -> 38-column CSV
python3 forefst.py disk.raw -o files.csv

# One-line volume overview (version, size, counts, upgrade state)
python3 forefst.py disk.raw summary

# Decode the durable transaction log into concrete file operations
python3 forefst.py disk.raw mlog --parse
```

Every subcommand has detailed help: `python3 forefst.py <image> help <subcommand>`.

### Try it in two minutes

A small ReFS test image ships with the repo. Decompress it, then point forefst at it:

```bash
zstd -d analysis/samples/disks/win11refs2tsnapshots/win11refs2tsnapshots.raw.zst
IMG=analysis/samples/disks/win11refs2tsnapshots/win11refs2tsnapshots.raw

python3 forefst.py "$IMG" summary        # volume overview
python3 forefst.py "$IMG" -o files.csv   # full file listing
python3 forefst.py "$IMG" snapshots      # this image showcases CoW stream snapshots
```

The other sample images under `analysis/samples/disks/` ship as split archives — see [`analysis/samples/README.md`](analysis/samples/README.md) for the one-line reassemble-and-decompress recipe and what each image demonstrates.

## For NTFS analysts

One structural difference comes first, because it reframes the whole workflow: **there is nothing to extract.** NTFS analysis usually means pulling one file out of an image — `$MFT`, `$UsnJrnl:$J`, `$Boot`, `$SDS` — and feeding it to a parser (the niche a tool like MFTECmd fills). ReFS has no single `$MFT`-like file; its metadata lives across Minstore B+-trees hanging off the checkpoint root tables. So instead of extracting an artifact, you point forefst at the raw image (or device) and it bootstraps the volume itself. Every command below reads the whole volume, not a carved-out file.

| To… | NTFS (typical workflow) | ReFS (forefst) |
|---|---|---|
| Per-file metadata → CSV / body / JSON | `$MFT` parser | `files` — 38 columns, Timeline Explorer-ready |
| Change journal | `$UsnJrnl:$J` (+ `$MFT` for paths) | `usn` — names and FileIDs resolve from the volume itself |
| Transaction log → user actions | `$LogFile` (no maintained open parser) | `mlog --parse` → CREATE / WRITE / RENAME / MOVE / DELETE |
| Timestomp detection | `$SI` vs `$FN`, sub-second zeros | `timestomp` — USN corroboration + hard-link `$SI` divergence (ReFS has no `$FILE_NAME` twin) |
| Security descriptors | `$SDS` parser | `security` (+ `--audit` tamper check) |
| Recycle Bin | `$I` / `$R` parser | `recyclebin` |
| Deleted files | TSK / carving | `deleted` → `export deleted [--carve]`, with a per-entry recoverability verdict |
| Extract content / ADS | TSK `icat` | `extract`, `export ads` |
| Prior versions | VSS tooling | `snapshots` — CoW stream snapshots |
| Super-timeline | assembled in Timeline Explorer / mactime / Plaso | `timeline` — USN + MLog + `$SI` MACB, merged |
| Volume triage | fsstat / `$Boot` | `summary` — including original / upgraded / native state, `--hash-image` |

**A few things that will feel familiar — and one that won't:**

- `Created`, `Modified`, `Changed`, and `Accessed` are the `0x10` (`$SI`) set. There is deliberately no `0x30` set: ReFS keeps no `$FILE_NAME` timestamp copy, so timestomping is caught by [other signals](docs/concepts/timestomp_detection.md).
- The `files` and `usn` outputs are **joinable** on `FileId` + `HomeOid` — together the USN 128-bit FileID — so you can pivot from a file row straight into its change-journal history.
- The CSVs open directly in Timeline Explorer; `--body` feeds mactime.
- It's pure Python, not compiled C#, so expect to trade some raw speed for portability; `timeline --fast` and `-q` are the triage levers.

Deep dives: [NTFS vs ReFS](docs/concepts/ntfs_comparison.md) · [Tool-to-artifact map](docs/concepts/tool_artifact_map.md).

## Repository layout

```
forefst/
├── forefst.py                # forensic file lister + full forensic suite
├── refsanalysis.py           # structure / lab tool — decode one on-disk structure at a time
├── docs/                     # standalone ReFS structural reference
│   ├── structures/           #   25 byte-level on-disk layouts
│   ├── concepts/             #   34 forensic concepts & mechanisms
│   ├── attributes/           #   11 per-attribute pages
│   ├── examples/             #   5 worked walkthroughs (real tool output)
│   ├── tools/                #   tool usage documentation
│   ├── website/              #   Hugo site generator — publishes this reference as a static site
│   ├── methodology.md        #   how every claim was verified
│   └── KNOWLEDGE_MAP.md      #   topic -> authoritative-source index
└── analysis/                 # lab materials + verification harness (the tools don't depend on it)
    ├── reference_table.csv   #   the live claim register (432 findings)
    ├── lab/                  #   VM setup, disk generation, activity generator + baseline
    ├── samples/              #   captured tool output + samples/corpus/ + sample disks
    └── reports/              #   verification scripts, results, per-claim audit/ harness
```

The `docs/` tree is a self-contained ReFS reference — start at **[docs/README.md](docs/README.md)** or the topic index **[docs/KNOWLEDGE_MAP.md](docs/KNOWLEDGE_MAP.md)**. It covers the on-disk **[structures](docs/structures/)** (VBR, superblock, checkpoint, B+-tree pages, the 13 system tables, directory entries), the forensic **[concepts](docs/concepts/)** (copy-on-write, deletion recovery, version detection, WSL metadata, …), the **[attributes](docs/attributes/)** (`$STANDARD_INFORMATION`, `$DATA`, `$EA`, `$REPARSE_POINT`, `$SNAPSHOT`, …), and **[worked examples](docs/examples/)** with real tool output.

The same reference is published as a static website, generated from `docs/` by the Hugo site under **[docs/website/](docs/website/)** (`docs/website/README.md` has the build + deploy details). `.gitlab-ci.yml` and `.github/workflows/` at the repo root rebuild and publish it on every change.

## forefst.py — the forensic tool

`forefst.py <image> <subcommand> [options]`. The default subcommand is `files`; the rest make up a full ReFS forensic toolkit:

| You want to… | Command |
|--------------|---------|
| List every file + metadata (CSV / JSON / body) | `forefst.py disk.raw -o files.csv` |
| Recover deleted files (view, then write out) | `forefst.py disk.raw deleted` → `forefst.py disk.raw export deleted ./recovered` |
| Build a super-timeline (USN + MLog + `$SI` MACB) | `forefst.py disk.raw timeline --csv` |
| Parse the USN change journal | `forefst.py disk.raw usn --csv usn.csv` |
| Parse the MLog durable log (redo records) | `forefst.py disk.raw mlog --stats` |
| Recover CoW prior versions (stream snapshots) | `forefst.py disk.raw snapshots --extract ./versions` |
| Flag timestamp tampering (timestomping) | `forefst.py disk.raw timestomp --min HIGH` |
| Map owners / ACLs, or tamper-check `$Secure` | `forefst.py disk.raw security --files` · `security --audit` |
| Find every special file (ADS, reparse, WSL, hard-link, sparse, EFS, compressed, integrity, EA) | `forefst.py disk.raw specials` |
| Resolve symlinks / junctions / WSL reparse points | `forefst.py disk.raw reparse -v` |
| Decode `$RECYCLE.BIN` (`$I` metadata + `$R` payload) | `forefst.py disk.raw recyclebin` |
| Extract one file's content, or dump all its attributes | `forefst.py disk.raw extract /path` · `details /path` |
| See which emitted fields are **not** 100% certain | `forefst.py disk.raw --provenance` |

### Example — deleted-file recovery

```
$ python3 forefst.py disk.raw deleted

── B+-tree Node Slack Scan ──
  (ReFS deletion removes only the row's index slot; the row body persists)
    FILE Change Journal   (resident, live-slack @ cluster 13824)
      Deleted from: FS Metadata
      Recoverable:  metadata only (non-resident — file data is not in this remnant)
```

ReFS deletion recovery has **five methods** — the Trash table, a checkpoint differential, an orphan-page scan, stream-snapshot reconstruction, and a B+-tree node-slack scan. The `deleted` command runs three of them by default (Trash, checkpoint diff, node-slack); `--scan-pages` adds the orphan scan, and stream-snapshot reconstruction — the one exact-content path — is exposed separately as `snapshots`, because it also recovers prior versions of files that still exist. Each recovered entry is tagged with a **recoverability verdict**: *full file* (resident content is inline in the record), *extent-backed* (non-resident data whose extent map survives, so `export deleted --carve` can reconstruct it), or *metadata only*. `export deleted DIR` writes the recoverable ones out.

## refsanalysis.py — the analysis tool

Where `forefst.py` answers *"what happened on this volume?"*, `refsanalysis.py` answers *"what does this structure look like?"* — it decodes one on-disk structure at a time. It is the companion for learning the format, validating the forensic tool, and adapting to new ReFS builds.

| Category | Subcommands |
|----------|-------------|
| Quick analysis | `summary`, `summary++`, `all` |
| File-system content | `files`, `attributes`, `details` |
| Structures | `boot`, `supb`, `chkp`, `objects`, `schema`, `parentchild`, `containers`, `upcase`, `oid30` |
| Boot-sector repair | `bootedit` (VBR inspect / export / repair) |

Run `python3 refsanalysis.py <image> --list` for the full set with per-command options.

## How it was built

forefst and its documentation exist to make ReFS analysis *forensically sound* — the core goal of my master's thesis: give analysts an auditable, open-source tool and enough documentation to understand what it reads. refsanalysis and the lab procedures are what keep it that way; ReFS evolves quickly, so both the tools and the knowledge have to stay re-testable against every new build.

A note on how it was built: the code was written with heavy LLM assistance — I'm a security engineer and forensic analyst, not a developer. What makes it trustworthy is not how it was generated but how it was verified. Every structural claim behind these tools had to hold in two independent places — the decompiled `refs.sys` driver and a 110+-image lab corpus — before it entered the [claim register](analysis/reference_table.csv), and the tools are regression-tested against that whole corpus. It is certainly not error-free, but every fact it emits is traceable to evidence you can re-inspect yourself. The method is detailed just below and in [docs/methodology.md](docs/methodology.md). Feedback and bug reports are very welcome.

## The reference

Behind the tools is a full reverse-engineering of the ReFS on-disk format — the most complete public account of version 3.14. The highlights, each a starting point into the documentation:

- **[On-disk structures](docs/structures/README.md)** — the bootstrap chain (VBR → superblock → checkpoint) and the 13 system tables (Object, Container, Schema, Allocators, …) that map every object to its bytes.
- **[`$STANDARD_INFORMATION`](docs/attributes/STANDARD_INFORMATION.md)** — the timestamps, `SecurityId`, and USN link carried by every file: the basis of the MACB timeline and of [timestomping detection](docs/concepts/timestomp_detection.md).
- **[Copy-on-Write & deletion recovery](docs/concepts/deletion_recovery.md)** — why ReFS never overwrites metadata in place, and [what actually survives](docs/concepts/what_survives.md) a delete, format, or upgrade.
- **[The change history](docs/structures/usn_journal.md)** — reconstructing activity from the USN journal and the [MLog](docs/structures/mlog.md) durable transaction log.
- **[Version detection](docs/concepts/version_detection.md)** — telling a native v3.14 volume from an upgraded one, and the three forensically distinct volume states.

The complete index — every structure, attribute, and concept — is in **[docs/](docs/README.md)**.

**How it was verified.** Every claim lives in a live register — [`analysis/reference_table.csv`](analysis/reference_table.csv), **432 structural claims** across ReFS 3.4–3.14 — and carries an **evidence level**: **E1** (binary string literal), **E2** (PDB symbol / decompiled code), **E3** (structural inference), **RD** (parsed from a 110+ volume raw-disk corpus, decompiled against 4 `refs.sys` builds). A byte-level claim is accepted only when the decompiled driver and the raw disk agree (`E2+RD`). The method, the evidence model, and a worked example are in **[docs/methodology.md](docs/methodology.md)**; everything needed to reproduce it ships under `analysis/` (`lab/`, `samples/`, `reports/`) — point the scripts at your own corpus via `REFS_DISKS` / `REFS_CORPUS`.

## Author

Maintained by **xbqt** on GitHub and **xbpt** on GitLab — same author. The code and issues live on GitHub; the published reference lives on GitLab Pages at [xbpt.gitlab.io/forefst](https://xbpt.gitlab.io/forefst/). I hope it's useful — please feel free to open an issue with feedback or corrections.

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).
