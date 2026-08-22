# forefst — forensic ReFS analysis

<p align="center"><img src="https://xbpt.gitlab.io/images/forefst.png" alt="forefst" width="360"></p>

**Forensic tools and byte-level structural documentation for Microsoft's Resilient File System (ReFS), versions 3.4 through 3.14.**

The project consists of:  
- **The ReFS format reference**, documenting the structures, attributes, main concepts like addressing or checksum mechanisms and version-specific changes. Available as plain Markdown in docs/ but above all as a website, **[xbpt.gitlab.io/forefst/](https://xbpt.gitlab.io/forefst/)**.
- **The open-source forensic tool, forefst.py**, for analysing ReFS volumes, including file metadata, deleted data, journals, hard links and special files.
- **The reproducible research methodology and lab materials**, combining reverse engineering of Microsoft’s refs.sys driver with analysis of more than 100 disk images to validate the documented structures and behaviours. But also everything needed to reproduce and audit the structural analysis: hypervisor scripts, file-activity generators, tool output, some disk images and the refsanalysis.py tool.

And if you want a complete introduction to the project: **[https://xbpt.gitlab.io/refs](https://xbpt.gitlab.io/refs)**

## Quick start

The only requirement is **Python 3.7+** (standard library only).

```bash
# Everything forefst can do, one line each
forefst.py --list

# Help specific to a function
forefst.py mlog --help

# Volume overview (version, size, counts, upgrade state)
forefst.py disk.raw summary

# Full forensic file listing
forefst.py disk.raw files -csv files.csv

# Search a file 
forefst.py disk.raw search "passwords.txt"

# Details of a file
forefst.py disk.raw details "/users/bat/passwords.txt"

# Decode the durable transaction log into concrete file operations
forefst.py disk.raw mlog --parse
```

The input can be a raw ReFS image (`dd` / `.raw`), a raw disk or partition device, or an E01 exported to raw (`ewfexport disk.E01`, or mount with `xmount --in ewf --out raw`) — forefst finds the ReFS partition inside a full-disk image automatically. Reading a live device (`/dev/sdX`, `\\.\PhysicalDriveN`) needs root / Administrator; an image file does not.

## For NTFS analysts

One structural difference comes first, because it reframes the whole workflow: **there is nothing to extract.** NTFS analysis usually means pulling one file out of an image — `$MFT`, `$UsnJrnl:$J`, `$Boot`, `$SDS` — and feeding it to a parser (the niche a tool like MFTECmd fills). ReFS has no single `$MFT`-like file; its metadata lives across Minstore B+-trees hanging off the checkpoint root tables. So instead of extracting an artifact, you point forefst at the raw image (or device) and it bootstraps the volume itself. Every command below reads the whole volume, not a carved-out file.

| To… | NTFS (typical workflow) | ReFS (forefst) |
|---|---|---|
| Per-file metadata → CSV / body / JSON | `$MFT` parser | `files` — 39 columns, Timeline Explorer-ready |
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

- `Created`, `Modified`, `Changed`, and `Accessed` are the `0x10` (`$SI`) set. There is deliberately no `0x30` set: ReFS keeps no `$FILE_NAME` timestamp copy, so timestomping is eventually caught by [other signals](docs/concepts/timestomp_detection.md).
- The `files` and `usn` outputs are **joinable** on `FileId` + `HomeOid` — together the USN 128-bit FileID — so you can pivot from a file row straight into its change-journal history.

Deep dives: [NTFS vs ReFS](docs/concepts/ntfs_comparison.md) · [Tool-to-artifact map](docs/concepts/tool_artifact_map.md).

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
| Address a file by its stable identity, independent of path | `forefst.py disk.raw details --id HomeOid:FileId` |

### Example — deleted-file recovery

```
$ python3 forefst.py disk.raw deleted

── B+-tree Node Slack Scan ──
  (ReFS deletion removes only the row's index slot; the row body persists)
    FILE Change Journal   (resident, live-slack @ cluster 13824)
      Deleted from: FS Metadata
      Recoverable:  metadata only (non-resident — file data is not in this remnant)
```

ReFS deletion recovery has **five methods** — the Trash table, a checkpoint differential, an orphan-page scan, stream-snapshot reconstruction, and a B+-tree node-slack scan. The `deleted` command runs three of them in its quick default (Trash, checkpoint diff, node-slack); the complete **`--full`** mode adds the orphan-page scan and, on export, carves non-resident content. Stream-snapshot reconstruction — the one exact-content path — is exposed separately as `snapshots`, because it also recovers prior versions of files that still exist. Each recovered entry is tagged with a **recoverability verdict**: *full file* (resident content is inline in the record), *extent-backed* (non-resident data whose extent map survives, so `export deleted --carve` can reconstruct it), or *metadata only*. `export deleted DIR` writes the recoverable ones out.

## refsanalysis.py — the analysis tool

Where `forefst.py` answers *"what happened on this volume?"*, `refsanalysis.py` answers *"what does this structure look like?"* — it decodes one on-disk structure at a time: the boot chain (`boot`, `supb`, `chkp`), the B+-tree system tables (`objects`, `schema`, `containers`, `parentchild`, …), file-system content (`files`, `attributes`, `details`), quick volume overviews (`summary`, `summary++`, `all`), and boot-sector inspection/repair (`bootedit`). It is the companion for learning the format, validating the forensic tool, and adapting to new ReFS builds. Run `python3 refsanalysis.py <image> --list` for the full set with per-command options.

## Repository layout

```
forefst/
├── forefst.py                # forensic file lister + full forensic suite
├── refsanalysis.py           # structure / lab tool — decode one on-disk structure at a time
├── docs/                     # standalone ReFS structural reference
│   ├── structures/           #   25 byte-level on-disk layouts
│   ├── concepts/             #   34 forensic concepts & mechanisms
│   ├── attributes/           #   11 per-attribute pages
│   ├── examples/             #   6 worked walkthroughs (real tool output)
│   ├── tools/                #   tool usage documentation
│   ├── website/              #   Hugo site generator — publishes this reference as a static site
│   ├── methodology.md        #   how every claim was verified
│   └── KNOWLEDGE_MAP.md      #   topic -> authoritative-source index
└── analysis/                 # lab materials + verification harness (the tools don't depend on it)
    ├── reference_table.csv   #   the live claim register (440 findings)
    ├── lab/                  #   VM setup, disk generation, activity generator + baseline
    ├── samples/              #   captured tool output + samples/corpus/ + sample disks
    └── reports/              #   verification scripts, results, per-claim audit/ harness
```

## How it was built

forefst and its documentation exist to make ReFS analysis *forensically sound* — the core goal of my master's thesis: give analysts an auditable, open-source tool and enough documentation to understand what it reads. refsanalysis and the lab procedures are what keep it that way; ReFS evolves quickly, so both the tools and the knowledge have to stay re-testable against every new build.

A note on how it was built: the code was written with heavy LLM assistance — I'm a security engineer and forensic analyst, not a developer. What makes it trustworthy is not how it was generated but how it was verified. Every structural claim behind these tools had to hold in two independent places — the decompiled `refs.sys` driver and a 110+-image lab corpus — before it entered the [claim register](analysis/reference_table.csv), and the tools are regression-tested against that whole corpus. It is certainly not error-free, but every fact it emits is traceable to evidence you can re-inspect yourself. The method is detailed just below and in [docs/methodology.md](docs/methodology.md). Feedback and bug reports are very welcome.

## License

Written by Baptiste Bonnet and released under the GNU General Public License v3.0 or later — see [LICENSE](LICENSE).

This project started as my master’s thesis (*"Forensic Analysis of the Resilient File System (ReFS) Version 3.14"*, University of Mons, 2026). The thesis provided a solid foundation, but the work was not quite finished. I therefore continued it beyond the thesis, consolidating the findings into a more complete and reproducible reference and further improving the practical tool for forensic analysis. I hope I have built and documented a solid understanding of current ReFS and provided a forensic tool built on knowledge that others can inspect, verify, and improve.
