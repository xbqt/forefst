# Sample image — win11refstestmftecmd

The **USN change journal** image: an active ReFS USN journal (9 371 on-disk records), shipped with the
matching `fsutil usn readjournal` **export** so you can cross-check the tool's journal parsing against
Windows' own output. Created for a cross-tool (MFTECmd / fsutil) journal test.

## At a glance (read directly from the image)

| ReFS version | Cluster size | Metadata checksum | Files / Dirs | Highlights |
|--------------|--------------|-------------------|--------------|------------|
| 3.14 | 4 KiB (16 KiB pages) | CRC64 | 1225 / 237 | active **USN journal** (9 371 records) · 340 integrity-stream files · 168 hard-linked files (450 names) |

Top-level directories: `test`, `test2`, `testspecials`, `testintegrity` (four baseline-replay trees;
the journal was created with `fsutil usn createjournal` before population).

## Layout

- `win11refstestmftecmd.raw.zst` — the ReFS disk image: a zstd archive (`zstd --ultra -22`) stored via Git LFS.
  Decompress before use (see **Reproduce** below). All tool output here was produced from the raw image.
- `provenance/`
  - `commands.md` — create / format / `createjournal` / populate / export / unmount, verified
    against the on-disk tree.
  - **`usn_readjournal_export.txt`** — the `fsutil usn readjournal` export (9 367 records; UTF-8,
    originally UTF-16LE). Same journal as the image: each of its 9 367 records (USN 0–1 261 000) is in
    the image with the same USN, file name and reason, and the image holds 4 more, from USN 1 261 144 (the
    export's own Next USN) to 1 261 568, written after the export was read. Cross-check against
    `refsanalysis/usn.txt`.
  - `fsactivity/` — the 4 `Generate-FSActivity` reports that shaped this volume, with their replay
    logs and replay inputs.
  - `usn_queryjournal_first.txt`, `usn_readjournal_first.txt`, `usn_queryjournal_last.txt` — the
    journal's state as `fsutil` reported it. See **Ground truth** below for every provenance file.
- `manifest.md` — every output file mapped to the exact command that produced it.
- `forefst/` — every forefst command's output (the `USN` column in the CSV is populated from `$SI` LastUsn).
- `refsanalysis/` — every subcommand at default + fullest verbosity, plus the option variants.
  Start with **`usn.txt`** (9 371 records) — the reason this image is here.

## Reproduce (from the repo root)

```bash
cd analysis/samples/disks/win11refstestmftecmd
git lfs pull --include "analysis/samples/disks/win11refstestmftecmd/*" && zstd -d win11refstestmftecmd.raw.zst && cd -   # fetch + decompress -> win11refstestmftecmd.raw
python3 refsanalysis.py analysis/samples/disks/win11refstestmftecmd/win11refstestmftecmd.raw usn
python3 refsanalysis.py analysis/samples/disks/win11refstestmftecmd/win11refstestmftecmd.raw usn -v
# compare the tool's output to provenance/usn_readjournal_export.txt (fsutil's own readjournal)
```

## Ground truth (`provenance/`)

What was done to this volume, and Windows' own record of it. Use it to check forefst's `usn` and
`timeline` output against the operations that were performed and against Windows' decode of the same
journal. These files are in the repository only; none of them is built into the website.

| File | What it is |
|------|------------|
| `commands.md` | How the volume was made, journaled, populated and exported. |
| `fsactivity/*_replay_log.csv` (4) | The generator's log of each replay run on this volume: one row per action (1 000 per run) with UTC time, action, result (`OK` or `SKIP`), path, destination, details and error. |
| `fsactivity/*_replay_report.txt` (4) | The generator's summary of each run: input file, roots, action counts, first skips. |
| `fsactivity/fsactivity_20260523_093947_replay.json`, `fsactivity/fsactivity_20260523_094753_replay.json` | The replay inputs for `testspecials` and `testintegrity`: the generator's parameters (seed, count, special-file rate, large-file sizes) and the 1 000 actions it recorded on the NTFS twin (`m:`), which the runs here replayed. `analysis/lab/Generate-FSActivity.ps1` (v3.20; these runs used v3.18) takes such a file with `-ReplayFile`. |
| `usn_readjournal_export.txt` | `fsutil usn readjournal n:`, run on the live volume after the last operation: 9 367 records. Converted from fsutil's UTF-16LE to UTF-8; no other change. |
| `usn_queryjournal_first.txt`, `usn_readjournal_first.txt` | `fsutil usn queryjournal` and `readjournal` run right after `createjournal`: journal ID `0x01dcea86b624a787`, next USN 0. |
| `usn_queryjournal_last.txt` | `fsutil usn queryjournal` run just before the export: next USN `0x133e58` (1 261 144), maximum size `0x8000000` (128 MiB). |

The four replay runs (times in UTC, 2026-05-23):

| Directory | Run | Input | OK / SKIP |
|-----------|-----|-------|-----------|
| `test` | 07:33:58–07:34:06 | `C:\tools\fsactivity_baseline.json` (not in the repository; `analysis/lab/fsactivity_baseline.json` is a different file) | 996 / 4 |
| `test2` | 07:38:44–07:38:52 | the same file | 996 / 4 |
| `testspecials` | 07:44:15–07:44:23 | `fsactivity_20260523_093947_replay.json` | 940 / 60 |
| `testintegrity` | 07:53:46–07:53:54 | `fsactivity_20260523_094753_replay.json` | 952 / 48 |

What the files show, when compared with each other and with this sample's tool output:

- **The journal starts after the `test` run.** Its first record (USN 0) is the creation of `test2`
  at 07:38:44 UTC, and none of the 309 successful `CREATE_FILE` and `CREATE_DIR` actions of the
  `test` run has a *File create* record under its name within the run's time window. For the other
  three runs, all 824 such actions have one.
- **Operations outside the generator** appear in the journal and in no replay log: `testintegrity`
  was created (07:44:49 UTC) and switched to integrity streams (*Integrity change*, 07:46:05 UTC)
  before its run, and after the last run two installers were copied into it and one of them deleted
  (`dotnet-sdk-9.0.314-win-x64.exe`, `dotnet-sdk-10.0.300-win-x64.exe`: 19 records, USN
  1 258 480–1 261 000, 07:54:48–07:55:54 UTC).
- **The export's time stamps are the lab VM's local time, UTC+2.** USN 0 reads 09:38:44 in the
  export, 07:38:44 UTC in `refsanalysis/usn.v.txt`, and the `test2` replay log's first action is at
  07:38:44.449 UTC.
- **The image holds the whole export.** `refsanalysis/usn.v.txt` contains every one of the export's
  9 367 records with the same USN, file name, reason, time stamp (to the second), file ID and parent
  ID (the export's 128-bit IDs split into the tool's `OID:ordinal` form). The image's journal has 4
  more records (USN 1 261 144–1 261 568, 11:15:52 UTC: `MountPointManagerRemoteDatabase` and
  `AadRecoveryPasswordDelete` in `System Volume Information`), written when the volume was mounted
  again after the export.

Every file in `provenance/` is the lab's own output, byte for byte, apart from the journal export:
Windows wrote it as UTF-16 with a byte-order mark, and it is stored here as UTF-8 without one (the
text is identical). The SHA-256 of each file, and the name it had in the lab, so that a copy can be
checked against the lab's:

| File | Name in the lab | SHA-256 |
|------|-----------------|---------|
| `fsactivity/fsactivity_20260523_093358_replay_log.csv` | same | `6f953fb821bb137f17271dc5281c17577c9d19a1e1534e7b981672b544ec5ffc` |
| `fsactivity/fsactivity_20260523_093844_replay_log.csv` | same | `0104a50e70ff04c8d532b590c153ab68199c58dafb2477f01cdac9f922d76013` |
| `fsactivity/fsactivity_20260523_094415_replay_log.csv` | same | `189dfd9e29a89ded1139446970c31da45602a8997e12df1d4f89ae4e31a517a7` |
| `fsactivity/fsactivity_20260523_095346_replay_log.csv` | same | `f8735d3f72e97e922eef35192f8a335b08172d88c73c26bfdc07dbbb2553b7c3` |
| `fsactivity/fsactivity_20260523_093947_replay.json` | same | `344544735c7b5afc80d1050633d84717f9505e1dfb1ea47c4332dd248b15cc07` |
| `fsactivity/fsactivity_20260523_094753_replay.json` | same | `79f8ae4d46a6e8b677807728b30ae01e9454560398e28ac60b425191c70f2eaa` |
| `usn_queryjournal_first.txt` | `n_usnqueryfirst.txt` | `51f03943aaba9e66be1059915090c9ff6cf03733c98d5455d0a25881692a5f21` |
| `usn_readjournal_first.txt` | `n_usnreadfirst.txt` | `9945efc427f95bb8a68bf649694e12462205a8bc3f95a25d29c208917de1cc63` |
| `usn_queryjournal_last.txt` | `n_usnquerylast.txt` | `be570ee752fab296efe9add066244b8f916e2371523b956a17e5daa2879e6984` |
| `usn_readjournal_export.txt` | `n_usnreadlast.txt` (UTF-16 original: `1e98cf7b45781a667dd7b7f7be79e0f9cc644741038364a77ebc5756c65daa10`) | `fb4645fed84da4c8f87b4d64ca74ff70b058b315f81c32a7712c9cbc67331ed6` |

The paths in the replay files name the lab machine's account, `refs`, and its host, `WIN11`; both
are generic lab names. Not included: the generator's runs on the NTFS twin, the twin's journal
exports, and the operator's session transcripts.
