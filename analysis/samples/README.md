# samples/

Reference disk images and reproducible tool output, so you can see exactly what `forefst.py` and
`refsanalysis.py` produce on real ReFS volumes — and re-run them yourself.

## What's here

### `corpus/` — per-structure output across versions

Curated structure-analysis output showing how the same structures (boot / checkpoint / attributes) look
**across ReFS versions, checksum types, and the cross-version upgrade** — `bootstrap/`, `checksum_variants/`,
`cross_version_upgrade/`, `file_attributes/`, `version_evolution/`. See `corpus/README.md` and
`corpus/corpus_description.md` (the full 118-image corpus table).

### `disks/` — full per-image bundles

Three ReFS 3.14 images, each chosen to showcase a different feature area, each shipped with its
provenance and a complete set of tool output:

| Image | Format | Showcases |
|-------|--------|-----------|
| `win11refs2tspecials` | 4 KiB clusters · CRC64 | hard links, symbolic links, alternate data streams (`-HeavySpcials`) |
| `wininsiderrefs8gtest2` | **64 KiB clusters · SHA-256** | the format variant (224-byte container rows) + an integrity-streams directory; Insider Server build |
| `win11refs2tsnapshots` | 4 KiB clusters · CRC64 | ReFS **stream snapshots** (`refsutil streamsnapshot`) |
| `win11refstestmftecmd` | 4 KiB clusters · CRC64 | active **USN change journal** (6 805 records) + its `fsutil usn readjournal` export |

Each `disks/<image>/` contains:

```
<image>.raw.zst.part-*    the ReFS disk image — a split zstd archive (recompose + decompress; see below)
README.md                  what the image showcases + how to reproduce its output
manifest.md                every output file -> the exact command that produced it
provenance/
  commands.md              curated create / populate / unmount commands, verified against the on-disk tree
  fsactivity/              the Generate-FSActivity run reports that actually shaped this volume
forefst/                   every forefst command's output — inventory (files CSV/JSON/JSONL/body, summary,
                           search), special files (specials + per-type), snapshots, deleted, reparse,
                           timeline (full CSV + preview + MLog-only), timestomp, USN, MLog (stats/parsed/csv),
                           security, integrity, dataruns, export (reparse text + json)
refsanalysis/              every subcommand at default + fullest verbosity, plus key option variants
```

So the per-format output examples (CSV, JSON, JSONL, body/mactime, and every subcommand) live in each
image's `forefst/` — see, for instance, `disks/win11refs2tsnapshots/forefst/files.csv` and
`.../snapshots.txt`. Every `.txt` sample opens with a `# forefst <image> …` header naming its command,
and each image's `manifest.md` maps **all** files (including the CSV/JSON ones) to their exact command.

### Recomposing the disk images

Each `.raw` ships as a **zstd archive (created with `zstd --ultra -22`) split into ~77 MiB parts**, so every
file stays within typical Git size limits. To use one — reassemble, decompress, and keep it sparse:

```bash
cat <image>.raw.zst.part-* > <image>.raw.zst    # 1. reassemble the parts (alphabetical order is correct)
zstd -d <image>.raw.zst                          # 2. decompress  ->  <image>.raw
```

ReFS volumes are mostly empty space, so the decompressed `.raw` is sparse; whenever you copy or move it, use
`cp --sparse=always <image>.raw <dest>` so it never materialises its full nominal size (2 TiB / 8 GiB). Each
image's own README gives its exact `cat` command (all images use the same `…raw.zst.part-*` part naming). `win11refs2tsnapshots.raw` is added later.

**Conventions in `refsanalysis/`:** `<sub>.txt` is the default run; `<sub>.vv.txt` /
`<sub>.v.txt` is the fullest verbosity that adds detail (`-vv` for the 7 subcommands that support it,
`-v` for the 8 that top out there); subcommands with no extra detail at higher verbosity have only
the default file. Variant files capture specific options (`security --files`, `reparse --index`,
`deleted --scan-pages`). `--hash-image` is not captured (it is a whole-image SHA-256 — run it
yourself if you want an integrity digest).

### Walkthroughs

- [`how_to_export_a_files_snapshots.md`](how_to_export_a_files_snapshots.md) — the three-step flow to
  find which files have stream snapshots, preview one file's versions, and export them to files
  (binary-safe).

## Provenance notes

The tool output was produced directly from the raw images with the tools in this repo. The
`fsactivity/` reports were filtered to only the runs that provably shaped each volume (matched by
`Root` / `ReplayRoot` against the directories actually present on disk) — runs from other drives that
shared a log directory during the same session are excluded. The `fsutil fsinfo` volume-info captures
are not included; the same volume facts (version, cluster size, checksum type, label) are read
directly off the disk by `refsanalysis.py boot` / `chkp -vv`. The one `fsutil` artefact that *is*
shipped is `win11refstestmftecmd`'s `usn_readjournal_export.txt` — the `fsutil usn readjournal` dump,
kept because it is the ground-truth reference for the tool's USN-journal parsing.
