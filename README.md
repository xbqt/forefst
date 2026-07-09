# forefst 

**Forensic analysis tools and structural documentation for the Resilient File System (ReFS) versions 3.4 through 3.14.**

## What is this?

ReFS is Microsoft's modern file system, increasingly deployed on Windows Server and Windows 11. Public forensic documentation has been limited to ReFS 3.4 (the excellent work of Paul Prade et al., *"Forensic analysis of the resilient file system (ReFS) version 3.4"*, 2019). This project updates that knowledge to the current version 3.14 and provides:

- **A forensic tool ([forefst](forefst.py))** - a forensic file lister and analysis tool for ReFS volumes
- **[Structural documentation](docs/)** of every on-disk format decoded during the analysis 
- **An analysis tool ([refsanalysis](refsanalysis.py)) and the [lab and verification materials](analysis/)** for creating controlled ReFS test images and analyzing them 

**The structural documentation is also published as a browsable website at [xbpt.gitlab.io/forefst](https://xbpt.gitlab.io/forefst/).**

All versions 3.4–3.14 parse; some enriched fields are version-dependent (best coverage on 3.10+/3.14). Python 3.6+, stdlib only, no install. 

Originally developed for my master's thesis (*"Forensic analysis of the Resilient File System (ReFS) version 3.14"* (University of Mons, 2026)), the project now covers features and findings well beyond its academic scope.

The forensic tool, **forefst**, and the documentation are really important to reach the principle of *forensic soundness* when a ReFS is analyzed which was my main master's thesis goal: provide to analysts an auditable open source tool and enough documentation to understand the filesystem.  
The analysis tool, **refsanalysis**, and all the laboratory procedures and scripts are important to test the tool and to facilitate future tests and updates. ReFS is a filesystem that is evolving a lot so it is necessary to keep the tools and knowledge accurate and valid.  

Because I'm not a developer and it's 2026, it is vibe coded. But I did a lot (really a lot) of tests, labs, analysis, validation, comparison, etc. So I think that my methodology is solid, and so are my results.
I hope this will be helpful, and please feel free to give any feedback.

## Requirements

- **Python 3.6+, standard library only** — no `pip install`, no dependencies, no build step. Clone and run.
- **Input:** a raw ReFS image — a `dd` / `.raw` acquisition, a raw disk or partition device, or an E01 exported to raw. forefst locates the ReFS partition inside a full-disk image automatically.

## Quick start

```bash
# Everything forefst can do, one line each
python3 forefst.py --list

# Full forensic file listing -> 38-column CSV (the ReFS answer to MFTECmd)
python3 forefst.py disk.raw -o files.csv

# One-line volume overview (version, size, counts, upgrade state)
python3 forefst.py disk.raw summary

# List the special-attribute files (WSL / reparse / ADS / hard-link groups)
python3 forefst.py disk.raw specials

# Carve one file's data stream back out, by path
python3 forefst.py disk.raw extract /path/to/file > recovered.bin

# Decode the durable transaction log into concrete file operations
python3 forefst.py disk.raw mlog --parse
```

Every subcommand has detailed help: `python3 forefst.py <image> help <subcommand>`.

## Repository layout

```
forefst/
├── forefst.py                # forensic file lister + full forensic suite (MFTECmd-style)
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

forefst finds deleted entries three ways — the Trash table, a checkpoint differential, and a B+-tree node-slack scan — and tags each with a **recoverability verdict**: *full file* (resident content is inline in the record), *extent-backed* (non-resident data whose extent map survives, so `export deleted --carve` can reconstruct it), or *metadata only*. `export deleted DIR` writes the recoverable ones out.

## refsanalysis.py — the analysis tool

Where `forefst.py` answers *"what happened on this volume?"*, `refsanalysis.py` answers *"what does this structure look like?"* — it decodes one on-disk structure at a time. It is the companion for learning the format, validating the forensic tool, and adapting to new ReFS builds.

| Category | Subcommands |
|----------|-------------|
| Quick analysis | `summary`, `summary++`, `all` |
| File-system content | `files`, `attributes`, `details` |
| Structures | `boot`, `supb`, `chkp`, `objects`, `schema`, `parentchild`, `containers`, `upcase`, `oid30` |
| Boot-sector repair | `bootedit` (VBR inspect / export / repair) |

Run `python3 refsanalysis.py <image> --list` for the full set with per-command options.

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

GNU General Public License v3.0 — see [LICENSE](LICENSE).
