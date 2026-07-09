# Sample image — win11refstestmftecmd

The **USN change journal** image: an active ReFS USN journal (6 805 on-disk records), shipped with the
matching `fsutil usn readjournal` **export** so you can cross-check the tool's journal parsing against
Windows' own output. Created for a cross-tool (MFTECmd / fsutil) journal test.

## At a glance (read directly from the image)

| ReFS version | Cluster size | Metadata checksum | Files / Dirs | Highlights |
|--------------|--------------|-------------------|--------------|------------|
| 3.14 | 4 KiB (16 KiB pages) | CRC64 | 1507 / 237 | active **USN journal** (6 805 records) · 559 integrity-stream files · 413 extra hard links |

Top-level directories: `test`, `test2`, `testspecials`, `testintegrity` (four baseline-replay trees;
the journal was created with `fsutil usn createjournal` before population).

## Layout

- `win11refstestmftecmd.raw.zst.part-*` — the ReFS disk image: a zstd archive (`zstd --ultra -22`) split into parts.
  Recompose and decompress before use (see **Reproduce** below). All tool output here was produced from the raw image.
- `provenance/`
  - `commands.md` — create / format / `createjournal` / populate / export / unmount, verified
    against the on-disk tree.
  - **`usn_readjournal_export.txt`** — the `fsutil usn readjournal` export (9 367 records; UTF-8,
    originally UTF-16LE). Same journal as the image; the two agree record-for-record over USN
    0–917 280 (6 805 records each), and the export's extra 2 562 records lie beyond the image's last
    record (later live activity than this snapshot). Cross-check against
    `refsanalysis/usn.txt`.
  - `fsactivity/` — the 4 `Generate-FSActivity` reports that shaped this volume.
- `manifest.md` — every output file mapped to the exact command that produced it.
- `forefst/` — every forefst command's output (the `USN` column in the CSV is populated from `$SI` LastUsn).
- `refsanalysis/` — every subcommand at default + fullest verbosity, plus the option variants.
  Start with **`usn.txt`** (6 805 records) / **`usn.v.txt`** — the reason this image is here.

## Reproduce (from the repo root)

```bash
cd analysis/samples/disks/win11refstestmftecmd
cat win11refstestmftecmd.raw.zst.part-* > win11refstestmftecmd.raw.zst && zstd -d win11refstestmftecmd.raw.zst && cd -   # recompose + decompress -> win11refstestmftecmd.raw
python3 refsanalysis.py analysis/samples/disks/win11refstestmftecmd/win11refstestmftecmd.raw usn
python3 refsanalysis.py analysis/samples/disks/win11refstestmftecmd/win11refstestmftecmd.raw usn -v
# compare the tool's output to provenance/usn_readjournal_export.txt (fsutil's own readjournal)
```
