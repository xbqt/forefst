# forefst — forensic ReFS analysis

**Forensic tools and byte-level structural documentation for Microsoft's Resilient File System (ReFS), versions 3.4 through 3.14.**

ReFS is Microsoft's modern, self-healing file system — the default for Storage Spaces and Dev Drives, and increasingly common on Windows Server and Windows 11. Yet public forensic documentation has effectively stood still at ReFS 3.4, the version reverse-engineered by Paul Prade et al. in *"Forensic analysis of the resilient file system (ReFS) version 3.4"* (2019), and there is still no ReFS equivalent of the mature NTFS toolchain. This project sets out to close that gap: it carries the on-disk analysis forward to the current version 3.14, and ships two tools that read a raw volume with no dependencies.

- **[forefst.py](forefst.py)** — the forensic tool: a file lister and full forensic suite for ReFS volumes.
- **[refsanalysis.py](refsanalysis.py)** — the analysis tool: decode one on-disk structure at a time, for learning the format and validating the forensic tool against new builds.
- **[Structural documentation](docs/)** of every on-disk format decoded during the work, also published as a browsable website at **[xbpt.gitlab.io/forefst](https://xbpt.gitlab.io/forefst/)**.
- **[Lab and verification materials](analysis/)** for building controlled ReFS test images and re-checking every claim.

All versions 3.4–3.14 parse; some enriched fields are version-dependent, with the best coverage on 3.10+ and 3.14. Python 3.7+, standard library only — clone and run.

Why *forefst*? Because of *forensic* and Re*FS*. And also because ReFS is all about B+-trees. And finally because, I think, the more forest on the planet, the better.

Originally built for my master's thesis (*"Forensic analysis of the Resilient File System (ReFS) version 3.14"*, University of Mons, 2026), the project now reaches well beyond its original academic scope. This is its first public release.

I hope it's useful — please feel free to open an issue with feedback or corrections.

## What's novel here

**The tool itself, first of all.** ReFS is fourteen years old, and — as far as I know — an open-source forensic tool for it has never really existed. The open tools I'm aware of (libfsrefs, pyrefs, the Sleuth Kit extension from Prade et al.'s work, journal parsers such as ARIN) each cover only a slice — an early version, a single artifact, or the format as it stood at 3.4 — and everything that opens a *current* volume is commercial and closed, a file list you cannot audit. So, as far as I can tell, forefst is the first tool anyone can download, read line by line, and point at a modern ReFS volume for the complete forensic job — listing, timelines, both journals, deleted files, prior versions, content extraction, security descriptors. And refsanalysis is the companion none of its predecessors shipped: the structure-level lab that keeps all of it re-testable when Microsoft moves the format again — which is how earlier efforts have tended to fall behind.

**The knowledge, second.** The last public map of the format is the 3.4 analysis, and ReFS has moved a long way since: page references shrank from 104 to 48 bytes (72 with SHA-256), v3.14 reaches its thirteen roots through an indirect list, a native-format marker and a version echo now record the volume's own history, the redo-opcode set grew from 29 to 44, `$SI` gained eight bytes, and whole features — stream snapshots, Dev Drive — postdate everything in the literature. The documentation here carries the byte-level record from 3.4 to 3.14, and revisits the 3.4-era ground on the way: the Container Table rows that could only be partially decoded in 2019 are fully mapped, the checkpoint comparison that earlier work set aside is implemented (with an honest negative result: after a clean unmount, both checkpoints decode to the same tree), and the attribute set — barely sketched in the literature — gets a byte-level page each. All of it sits in the 432-claim register with graded evidence.

**And a few capabilities have no equivalent even in the mature NTFS toolchain** — they are what make forefst a *forensic* tool rather than a parser:

- **User actions reconstructed from the transaction log.** `mlog --parse` decodes the durable log into concrete operations — CREATE, WRITE, RENAME, MOVE, DELETE — with deliberately conservative semantics: a RENAME is told apart from a MOVE by comparing parent-directory OIDs, and a DELETE is reported only when the object's own table is destroyed, not on the bare row removal a rename also produces. The open NTFS world never had a maintained `$LogFile` parser; this is the closest thing to one for ReFS.
- **A timestomp signal NTFS cannot offer.** ReFS keeps no `$FILE_NAME` timestamp twin — but a hard-linked file carries one `$SI` set *per name*, so a back-dated name stands out against its siblings and against the change journal, flagging the tampered name specifically and independently of the log.
- **Deletion evidence that cannot be erased.** Object IDs are monotonic and never reused, so a gap in the OID sequence is durable evidence that an object once existed and was deleted — it survives even a complete overwrite of every byte that object ever touched. The caveat: small *resident* files don't get their own Object ID (they live inline in their parent directory), so a run of deleted resident files can leave only a small gap, or none — the signal is strongest for directories and larger objects. Even so, NTFS can't offer this at all: MFT records are recycled and erase their own evidence over time.
- **Provenance of the medium itself.** `summary` classifies a volume as original, upgraded, or native, from an on-disk marker an upgrade can never set — a permanent signature of the volume's history, with real capability consequences (POSIX unlink and hard links require the native format).
- **A parser that discloses its own uncertainty.** `--provenance` marks the output fields that rest on structural inference rather than on facts confirmed in both the decompiled driver and the disk bytes. Every emitted field traces to graded evidence in the claim register — so *"how do you know this column is right?"* has a written answer.

Each is documented in depth under [docs/concepts/](docs/concepts/).

## Quick start

The only requirement is **Python 3.7+** — standard library only: no `pip install`, no dependencies, no build step. Clone and run, on Linux, macOS, or Windows. Both tools open the input strictly **read-only**, so pointing either at evidence is safe (the one write-capable operation, `refsanalysis.py bootedit repair`, works on a sparse *copy* by default and refuses `--inplace` unless you ask for it).

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

The input can be a raw ReFS image (`dd` / `.raw`), a raw disk or partition device, or an E01 exported to raw (`ewfexport disk.E01`, or mount with `xmount --in ewf --out raw`) — forefst finds the ReFS partition inside a full-disk image automatically. Reading a live device (`/dev/sdX`, `\\.\PhysicalDriveN`) needs root / Administrator; an image file does not. Every subcommand has detailed help: `python3 forefst.py <image> help <subcommand>`.

### Try it in two minutes

The sample images are **Git LFS** objects. The quickest way in is to download the one used below directly — no clone needed:

```bash
curl -L -O https://github.com/xbqt/forefst/raw/main/analysis/samples/disks/win11refs2tsnapshots/win11refs2tsnapshots.raw.zst
zstd -d win11refs2tsnapshots.raw.zst

python3 forefst.py win11refs2tsnapshots.raw summary        # volume overview
python3 forefst.py win11refs2tsnapshots.raw -o files.csv   # full file listing
python3 forefst.py win11refs2tsnapshots.raw snapshots      # this image showcases CoW stream snapshots
```

If you cloned the repo, `git lfs install && git lfs pull` fetches all the sample images instead. See [`analysis/samples/README.md`](analysis/samples/README.md) for the other images (each a Git LFS object) and what each demonstrates.

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
│   ├── concepts/             #   33 forensic concepts & mechanisms
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

## License

Written by Baptiste Bonnet and released under the GNU General Public License v3.0 or later — see [LICENSE](LICENSE).
