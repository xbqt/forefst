# Sample image — wininsiderrefs8gtest2

The **format-variant** image: created under a Windows Insider Server build (29574) with **64 KiB
clusters and SHA-256 metadata checksums** — the combination that grows container-table rows to
224 bytes and changes page-reference sizing. Also carries an integrity-streams directory.

## At a glance (read directly from the image)

| ReFS version | Cluster size | Metadata checksum | Files / Dirs | Highlights |
|--------------|--------------|-------------------|--------------|------------|
| 3.14 | 64 KiB (64 KiB pages) | SHA-256 | 776 / 118 | 64 KiB clusters · SHA-256 checksums · `testintegrity` directory · 232 extra hard links |

Top-level directories: `testspecials` (heavy run), `testintegrity` (baseline replay with integrity
streams enabled on the directory).

> Note on ADS: the activity logs record `CREATE_ADS` actions and `refsanalysis snapshots` reports
> 54 ADS entries (0xB0 attribute) on 35 files; `forefst`'s file listing does not surface these.

## Layout

- `wininsiderrefs8gtest2.raw.zst` — the ReFS disk image: a zstd archive (`zstd --ultra -22`) stored via Git LFS.
  Decompress before use (see **Reproduce** below). All tool output here was produced from the raw image.
- `provenance/`
  - `commands.md` — curated creation / populate / unmount commands, verified against the on-disk tree.
  - `fsactivity/` — the 4 `Generate-FSActivity` run reports that actually shaped this volume.
- `manifest.md` — every output file mapped to the exact command that produced it.
- `forefst/` — every forefst command's output (inventory, specials, integrity, snapshots, timeline,
  MLog, security, export, …); see `manifest.md`.
- `refsanalysis/` — every subcommand at default verbosity, plus the fullest verbosity where it
  adds detail (`.vv` for the 7 `-vv` subcommands, `.v` for the 8 `-v`-only ones), plus the option
  variants `security --files`, `reparse --index`, `deleted --scan-pages`, `summary`, `summary++`.

## Reproduce (from the repo root)

```bash
cd analysis/samples/disks/wininsiderrefs8gtest2
git lfs pull --include "analysis/samples/disks/wininsiderrefs8gtest2/*" && zstd -d wininsiderrefs8gtest2.raw.zst && cd -   # fetch + decompress -> wininsiderrefs8gtest2.raw
python3 forefst.py      analysis/samples/disks/wininsiderrefs8gtest2/wininsiderrefs8gtest2.raw --summary-plus
python3 refsanalysis.py analysis/samples/disks/wininsiderrefs8gtest2/wininsiderrefs8gtest2.raw boot -vv
```
