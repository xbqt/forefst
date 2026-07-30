# Sample image — win11refs2tsnapshots

The **stream-snapshot** image: a baseline file-system tree plus ReFS stream snapshots created with
`refsutil streamsnapshot` (point-in-time copies of a file's data stream).

## At a glance (read directly from the image)

| ReFS version | Cluster size | Metadata checksum | Files / Dirs | Highlights |
|--------------|--------------|-------------------|--------------|------------|
| 3.14 | 4 KiB (16 KiB pages) | CRC64 | 270 / 34 | 5 files carrying 10 stream snapshots |

Top-level directories: `test` (baseline replay), `testsnapshots` (the `refsutil streamsnapshot`
exercise).

## Layout

- `win11refs2tsnapshots.raw.zst` — the ReFS disk image: a zstd archive (`zstd --ultra -22`) stored via Git LFS.
  Decompress before use (see **Reproduce** below). All tool output here was produced from the raw image.
- `provenance/`
  - `commands.md` — curated creation / populate / **stream-snapshot** / unmount commands, verified
    against the on-disk tree.
  - `fsactivity/` — the 1 `Generate-FSActivity` baseline-replay report that shaped the `test` tree.
- `manifest.md` — every output file mapped to the exact command that produced it.
- `forefst/` — every forefst command's output (inventory, specials, snapshots, timeline, MLog,
  security, export, …); see `manifest.md`. The `snapshots.txt` output is the one to look at first
  here (5 files / 10 snapshots).
- `refsanalysis/` — every subcommand at default verbosity, plus the fullest verbosity where it
  adds detail (`.vv` for the 7 `-vv` subcommands, `.v` for the 8 `-v`-only ones), plus the option
  variants `security --files`, `reparse --index`, `deleted --scan-pages`, `summary`, `summary++`.

## Reproduce (from the repo root)

```bash
cd analysis/samples/disks/win11refs2tsnapshots
git lfs pull --include "analysis/samples/disks/win11refs2tsnapshots/*" && zstd -d win11refs2tsnapshots.raw.zst && cd -   # fetch + decompress -> win11refs2tsnapshots.raw
python3 forefst.py      analysis/samples/disks/win11refs2tsnapshots/win11refs2tsnapshots.raw --summary-plus
python3 refsanalysis.py analysis/samples/disks/win11refs2tsnapshots/win11refs2tsnapshots.raw snapshots
```
