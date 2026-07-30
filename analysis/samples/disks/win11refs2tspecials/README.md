# Sample image — win11refs2tspecials

The **special-artefacts** image: a heavy `-HeavySpcials` activity run that fills the volume with hard
links, symbolic links, and alternate data streams on top of a baseline file-system tree.

## At a glance (read directly from the image)

| ReFS version | Cluster size | Metadata checksum | Files / Dirs | Highlights |
|--------------|--------------|-------------------|--------------|------------|
| 3.14 | 4 KiB (16 KiB pages) | CRC64 | 1333 / 217 | 515 extra hard links · 344 reparse/symlink entries · alternate data streams |

Top-level directories: `test` (baseline replay), `testspecials`, `testspecials2` (the heavy runs).

> Note on ADS: the activity logs record `CREATE_ADS` actions and `refsanalysis snapshots` reports
> 109 ADS entries (0xB0 attribute) on 76 files. `forefst`'s file listing does **not** surface these
> (`HasAds` is `False` for every row) — both outputs are captured here so the difference is visible.

## Layout

- `win11refs2tspecials.raw.zst` — the ReFS disk image: a zstd archive (`zstd --ultra -22`) stored via Git LFS.
  Decompress before use (see **Reproduce** below). All tool output here was produced from the raw image.
- `provenance/`
  - `commands.md` — curated creation / populate / unmount commands, verified against the on-disk tree.
  - `fsactivity/` — the 3 `Generate-FSActivity` run reports that actually shaped this volume.
- `manifest.md` — every output file mapped to the exact command that produced it.
- `forefst/` — every forefst command's output (inventory, specials + per-type, snapshots, reparse,
  timeline, MLog, security, export, …); see `manifest.md`.
- `refsanalysis/` — every subcommand at default verbosity, plus the fullest verbosity where it
  adds detail (`.vv` for the 7 `-vv` subcommands, `.v` for the 8 `-v`-only ones), plus the option
  variants `security --files`, `reparse --index`, `deleted --scan-pages`, `summary`, `summary++`.

## Reproduce (from the repo root)

```bash
cd analysis/samples/disks/win11refs2tspecials
git lfs pull --include "analysis/samples/disks/win11refs2tspecials/*" && zstd -d win11refs2tspecials.raw.zst && cd -   # fetch + decompress -> win11refs2tspecials.raw
python3 forefst.py      analysis/samples/disks/win11refs2tspecials/win11refs2tspecials.raw --summary-plus
python3 refsanalysis.py analysis/samples/disks/win11refs2tspecials/win11refs2tspecials.raw boot -vv
```
