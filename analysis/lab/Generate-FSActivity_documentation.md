# Generate-FSActivity - Scientific Documentation

**Version:** 3.20
**Tool:** `Generate-FSActivity.ps1`
**Platform:** Windows (PowerShell 5.1+), NTFS and ReFS volumes

---

## Table of Contents

1. [Motivation and Context](#1-motivation-and-context)
2. [Running the Tool](#2-running-the-tool)
3. [Theoretical Foundations](#3-theoretical-foundations)
4. [Action Set](#4-action-set)
5. [Scheduling Model](#5-scheduling-model)
6. [Expected Forensic Artefacts per Action](#6-expected-forensic-artefacts-per-action)
7. [Reproducibility and the Replay Format](#7-reproducibility-and-the-replay-format)
8. [Ground-Truth Log Format](#8-ground-truth-log-format)
9. [The Lab Baseline](#9-the-lab-baseline)
10. [Validity and Limitations](#10-validity-and-limitations)
11. [References](#11-references)

---

## 1. Motivation and Context

Forensic tool validation and research on file-system artefacts require datasets
with a known ground truth - that is, datasets for which every operation performed,
its parameters, and its expected forensic traces are fully documented. Using
real-world disk images raises ethical and legal concerns regarding personal data,
while manually constructed images are arduous to create and hard to reproduce
[Du et al., 2021; Scanlon et al., 2017].

This tool generates a configurable sequence of file-system operations against one
root directory, records every action in a structured ground-truth log, and emits a
**replay file** that reproduces the same logical sequence on any compatible volume.
It runs **without Administrator rights** for the main workload; privileged or
file-system-specific actions (symbolic links, and on some volumes hard links / ADS)
are logged as `SKIP` with a clear reason and replaced by a fallback `CREATE_FILE`
so the requested action count is preserved.

Primary research applications:

- Validation of file listers, timeline tools, and forensic suites against known ground truth
- Study of NTFS/ReFS artefact generation at the metadata layer ($MFT / Object Table, USN journal, $LogFile / MLog)
- Anti-forensic research (timestomping detection, ADS concealment, hard-link ambiguity)
- Education: teaching the relationship between user actions and file-system artefacts

---

## 2. Running the Tool

### 2.1 Prerequisites

- **Windows PowerShell 5.1+**. Administrator rights are **not** required for the
  main workload. Hard links and ADS do not normally need elevation but the target
  file system may still refuse them.
- **Symbolic links** require an elevated session, Windows **Developer Mode**, or
  `SeCreateSymbolicLinkPrivilege`; otherwise symlink actions are skipped.
- Target a **ReFS** (or NTFS) volume; point `-RootDir` at a directory on it.

### 2.2 Execution policy

```powershell
# Per-invocation, no persistent change (recommended):
powershell.exe -ExecutionPolicy Bypass -File .\Generate-FSActivity.ps1 -RootDir R:\test -Count 1000 -Seed 42 -LogDir .\logs

# Or unblock the downloaded file once:
Unblock-File .\Generate-FSActivity.ps1
```

Running the script with no parameters prints built-in usage.

### 2.3 Parameters

| Parameter | Meaning |
|---|---|
| `-RootDir <path>` | Directory where activity is generated (created if missing). Required unless `-ReplayFile` is used. |
| `-Count <n>` | Total number of logged actions. Default 100. Large files and the marked file are **included** in this total. |
| `-LogDir <path>` | Directory for the CSV log, replay JSON and text report. Default `.`. |
| `-Seed <int>` | Deterministic seed for the choices. Same seed → similar choices. Default = random (`TickCount`). |
| `-MaxFileSizeKB <int>` | Maximum size of a normal generated file, in KB. Default 512. Does not apply to `-LargeFileSizeMB` files. |
| `-LargeFileSizeMB <int[]>` | List of exact large-file sizes in MB; **one file per value**, duplicates preserved (`2,2,2` → three 2 MB files). Written with a chunked stream writer. Included in `-Count`. |
| `-MaxDepth <int>` | Maximum directory depth under RootDir. Default 4. |
| `-FileMarker <str>` | Prefix inserted in every generated **file** name (e.g. `xbpt` → `xbpt_alpha_beta_123456.txt`). |
| `-FileContentMarker <str>` | Writes exactly one text file whose name contains `marked` and whose content contains the marker. Included in `-Count`. |
| `-DirMarker <str>` | Prefix inserted in every generated **directory** name (e.g. `elvis` → `elvis_dir_alpha_123456`). |
| `-SkipSymlinks` | Disable symbolic-link actions. |
| `-SkipADS` | Disable alternate-data-stream actions. |
| `-HeavySpcials` | Heavy special-artefact mode: schedules many more `CREATE_HARDLINK` / `CREATE_SYMLINK_FILE` / `CREATE_ADS` attempts. (Spelling matches the lab command interface.) |
| `-SpecialEveryN <int>` | One full set of hardlink/symlink/ADS per N actions. `0` = default frequency: **250** normally, **25** with `-HeavySpcials`. |
| `-CleanRoot` | Delete RootDir contents before generating. Use carefully. |
| `-ReplayFile <json\|csv>` | Replay a previous JSON replay file or CSV log produced by this script. |

### 2.4 Generate a corpus

```powershell
.\Generate-FSActivity.ps1 -RootDir R:\test -Count 1000 -Seed 153524984 -LogDir .\logs `
  -FileMarker xbpt -DirMarker elvis -FileContentMarker XBPT_MARK -LargeFileSizeMB 2,86,7,5,149 -CleanRoot
```

Each run writes three timestamp-named artefacts to `-LogDir`:

- `fsactivity_<ts>_log.csv` - ground-truth log, one row per logged action.
- `fsactivity_<ts>_replay.json` - the resolved sequence for exact replay (`schema_version 3.20`).
- `fsactivity_<ts>_report.txt` - summary statistics.

### 2.5 The "specials" workload

The heavy special-artefact run used for feature-rich disks:

```powershell
.\Generate-FSActivity.ps1 -RootDir R:\specials -Count 1000 -LogDir .\logs -HeavySpcials -SpecialEveryN 10 -CleanRoot
```

### 2.6 Replay

```powershell
# Replay a JSON replay file onto a different volume (paths are remapped to -RootDir):
.\Generate-FSActivity.ps1 -ReplayFile .\logs\fsactivity_<ts>_replay.json -RootDir F:\refs_replay -LogDir .\logs -CleanRoot

# Replay the lab baseline onto a fresh ReFS volume:
.\Generate-FSActivity.ps1 -ReplayFile .\fsactivity_baseline.json -RootDir M:\test -LogDir .\logs -CleanRoot
```

Replay produces `fsactivity_<ts>_replay_log.csv` and `fsactivity_<ts>_replay_report.txt`.

---

## 3. Theoretical Foundations

### 3.1 File-system layer model (Carrier, 2005)

Carrier's layer model defines abstraction levels at which forensic analysis
operates. This tool generates artefacts at the upper layers:

| Layer | Description | Examples in this tool |
|---|---|---|
| **Physical** | Raw sectors | Not applicable (OS-level tool) |
| **Volume** | Partition layout, boot record | Implicit in all operations |
| **File System** | $MFT/$Bitmap/$LogFile (NTFS), Object Table/Allocators/MLog (ReFS) | All operations affect these |
| **Metadata** | MFT records / $SI, ReFS $STANDARD_INFORMATION | SET_TIMESTAMPS, attribute changes |
| **Name / Application** | Directory entries, paths | CREATE_FILE, RENAME, MOVE |

### 3.2 The SI/FN timestamp duality (and the ReFS difference)

On **NTFS**, timestamps live in two attributes: `$STANDARD_INFORMATION` ($SI),
freely settable by user-mode `SetFileTime()`, and `$FILE_NAME` ($FN), maintained by
the kernel and **not** user-settable. `SET_TIMESTAMPS` exploits this by stamping the
$SI times, leaving $FN unchanged; the resulting **SI/FN divergence** is the classic
timestomping signal [Oh et al., 2024].

On **ReFS** there is **no $FN timestamp set** to compare against, so that specific
cross-check does not exist - timestomping is instead detectable through the
metadata-change time, the USN change journal, and the volume creation time (see the
project's *Timestomping Detection* concept page). `SET_TIMESTAMPS` here sets all
three writable times (creation / write / access) to one value, which is the
forensically relevant pattern.

---

## 4. Action Set

v3.20 schedules a **flat set of atomic actions** (there are no composite/"complex"
actions). Each produces one logged row.

| Action | Effect | Notes |
|---|---|---|
| `CREATE_FILE` | Create a file with random bytes (≤ `MaxFileSizeKB`) | Large-file variant writes an exact `-LargeFileSizeMB` size with a chunked writer and is protected from later delete/rename/move |
| `CREATE_MARKED_FILE` | Create one text file named `*marked*` containing `-FileContentMarker` | Included in `-Count`; `marker_b64` recorded in Details |
| `CREATE_DIR` | Create a directory | Planner targets ~5% of `-Count` |
| `WRITE_FILE` | Overwrite an existing file with new random bytes | Falls back to `CREATE_FILE` if no file exists |
| `APPEND_FILE` | Append random bytes to an existing file | |
| `DELETE_FILE` | Delete an existing file | |
| `DELETE_DIR` | Delete an **empty** leaf directory | |
| `RENAME_FILE` | Rename a file within its directory | |
| `RENAME_DIR` | Rename a directory | |
| `MOVE_FILE` | Move a file to another directory | |
| `MOVE_DIR` | Move a directory to another parent | |
| `COPY_FILE` | Copy a file to another directory | |
| `SET_TIMESTAMPS` | Set creation/write/access times to a back-dated value | Timestomp signal |
| `CREATE_HARDLINK` | `CreateHardLink` (P/Invoke) to an existing file | SKIP + fallback `CREATE_FILE` if the FS refuses |
| `CREATE_SYMLINK_FILE` | Create a file symbolic link | SKIP if not elevated / no Developer Mode |
| `CREATE_ADS` | Write a named alternate data stream on an existing file | Supported on NTFS **and ReFS** (ReFS stores ADS inline); SKIP + fallback if unsupported or `-SkipADS` |

**Fallback rule.** When a special artefact (hardlink / symlink / ADS) is refused,
the attempt stays visible in the log (`Result = SKIP` with the reason) and a normal
`CREATE_FILE` is performed in the same logged row (`fallback_action=CREATE_FILE` in
Details), so `-Count` is preserved.

---

## 5. Scheduling Model

The planner (`New-ActionPlan`) builds the full action list before execution:

1. **Reserved tail.** The `-LargeFileSizeMB` files and the optional marked file are
   appended at the end, so later destructive actions cannot disturb them.
2. **Special-artefact frequency.** `effectiveEveryN` = `-SpecialEveryN` if non-zero,
   else **25** with `-HeavySpcials` or **250** otherwise. One full
   hardlink+symlink+ADS set is planted per `effectiveEveryN` actions.
3. **Directory target.** About **5%** of `-Count` is forced to `CREATE_DIR`
   (directories may later be renamed, moved, or deleted).
4. **Minimum count check.** `-Count` must cover the reserved tail + special
   attempts + directory target, or the script throws with the required minimum.
5. **Weighted body.** Remaining slots are filled from a weighted pool. `-HeavySpcials`
   biases the pool strongly toward hardlink/symlink/ADS; the default pool is
   creation-heavy so delete/move/rename always have material.
6. **Setup seeding.** The first seven slots are forced to `CREATE_FILE ×5` + `CREATE_DIR ×2`.
7. **Mandatory coverage (Count > 100).** The planner guarantees each core action
   (`CREATE_FILE`, `WRITE_FILE`, `APPEND_FILE`, `DELETE_FILE`, `DELETE_DIR`,
   `RENAME_FILE`, `RENAME_DIR`, `MOVE_FILE`, `MOVE_DIR`, `COPY_FILE`,
   `SET_TIMESTAMPS`) appears at least once, without overwriting the forced specials.

The final tree is **not** expected to contain `-Count` files: deletes, renames and
moves change the live set. **The CSV log is the ground truth.**

---

## 6. Expected Forensic Artefacts per Action

Reference artefacts on NTFS (USN reason codes from `wdm.h`); the ReFS analogue is
the Object Table row, the embedded `$STANDARD_INFORMATION`, and the USN journal
(`$UsnJrnl:$J`) where active.

| Action | $MFT / object attributes | USN reason | $FN updated? (NTFS) | Note |
|---|---|---|---|---|
| CREATE_FILE | New record; $SI, $FN, $DATA | FILE_CREATE(0x100)+CLOSE | Yes | Parent index updated |
| CREATE_DIR | New record; $SI, $FN, index | FILE_CREATE+CLOSE | Yes | |
| WRITE_FILE | $SI LastWrite; $DATA | DATA_OVERWRITE(0x1)+CLOSE | No | |
| APPEND_FILE | $SI LastWrite; $DATA extended | DATA_EXTEND(0x4)+CLOSE | No | Clusters may be allocated |
| DELETE_FILE | InUse cleared; $DATA deallocated | FILE_DELETE(0x200)+CLOSE | N/A | Recoverable until reused |
| DELETE_DIR | InUse cleared; index removed | FILE_DELETE+CLOSE | N/A | Empty dir only |
| RENAME_FILE | $FN name updated | RENAME_OLD(0x800)+RENAME_NEW(0x1000)+CLOSE | **Yes** | Entry number preserved |
| RENAME_DIR | $FN name updated | RENAME_OLD+RENAME_NEW+CLOSE | **Yes** | |
| MOVE_FILE | $FN parent ref + name | RENAME_OLD+RENAME_NEW+CLOSE | **Yes** | Same entry, new path |
| MOVE_DIR | $FN parent ref | RENAME_OLD+RENAME_NEW+CLOSE | **Yes** | |
| COPY_FILE | New record (dest); $SI Created=now | FILE_CREATE+CLOSE (dest) | Yes | Source unchanged |
| SET_TIMESTAMPS | $SI timestamps | BASIC_INFO_CHANGE(0x8000)+CLOSE | **No** | SI/FN divergence (NTFS) |
| CREATE_HARDLINK | New $FN on existing record | HARD_LINK_CHANGE(0x10000)+CLOSE | Yes (new) | LinkCount++ |
| CREATE_SYMLINK_FILE | New record; REPARSE_POINT | FILE_CREATE+REPARSE_POINT_CHANGE(0x100000) | Yes | Tag 0xA000000C |
| CREATE_ADS | Named $DATA on existing record | STREAM_CHANGE(0x200000)+CLOSE | No | ReFS stores ADS inline |

---

## 7. Reproducibility and the Replay Format

### 7.1 Schema (v3.20)

The replay file is a JSON document; the replay reader uses only `root_dir` and
`actions`, so any replay file or the lab baseline can be replayed regardless of its
declared `schema_version`.

```json
{
  "schema_version": "3.20",
  "generated_at_utc": "<ISO-8601 UTC>",
  "seed": 153524984,
  "root_dir": "H:\\test",
  "count": 1000,
  "count_semantics": "total_logged_actions_including_large_files",
  "file_marker": "test",
  "file_content_marker": "samplecontent",
  "dir_marker": "dir",
  "max_file_size_kb": 512,
  "large_file_size_mb": [2, 86, 7, 5, 149, 99, 14],
  "large_file_mode": "exactly_one_chunked_file_per_list_value",
  "heavy_spcials": false,
  "special_every_n": 0,
  "actions": [
    { "Sequence": 1, "TimestampUTC": "...", "Action": "CREATE_FILE",
      "Result": "OK", "SourcePath": "H:\\test\\...", "DestPath": "",
      "Details": "bytes=4096", "Error": "" }
  ]
}
```

Each `actions[]` entry is exactly one ground-truth CSV row (section 8).

### 7.2 Replay behaviour

- **Root remapping.** With a JSON replay file, every logged path is remapped from the
  original `root_dir` to `-RootDir`. With a CSV log there is no separate original
  root, so stored paths are used as-is.
- **Already-skipped originals.** A row whose original `Result` was not `OK` is replayed
  as `SKIP` (the original action did not succeed, so it is not reproduced).
- **Large-file fast path.** Replay reproduces the file-system effect and final size,
  not the original random bytes: large/normal files are recreated with
  `FileStream.SetLength` plus a short `GFSAREPLAY` signature. This avoids the slow
  per-byte rewrites that made large-file replays appear to hang near the end of a run.
- **Self-healing.** Missing parent directories and missing replay sources are
  recreated as needed; remaining failures keep the real exception in the `Error`
  column.
- **Privilege gaps.** Symlinks (and any FS-refused hardlink/ADS) are logged as `SKIP`
  with the reason when the environment cannot perform them.

---

## 8. Ground-Truth Log Format

The CSV log has **8 columns**, one row per logged action:

```
Sequence,TimestampUTC,Action,Result,SourcePath,DestPath,Details,Error
```

| Column | Description |
|---|---|
| `Sequence` | Monotonic action counter (1..Count) |
| `TimestampUTC` | Wall-clock time of the action (ISO-8601, round-trip "o") |
| `Action` | Action name (section 4) |
| `Result` | `OK` / `SKIP` / `ERROR` |
| `SourcePath` | Primary path operand |
| `DestPath` | Secondary path (rename, move, copy, link) |
| `Details` | Semicolon-separated key=value pairs (see below) |
| `Error` | Exception text for `SKIP`/`ERROR` rows |

**`Details` grammar (selected keys):** `bytes=N`, `appended_bytes=N`,
`large_file=true`, `target_mb=N`, `size_marker=Nmb`, `chunked_write=true`,
`protected_from_delete=true`, `stream=NAME` (ADS), `marked_file=true`,
`marker_b64=<base64>` (marked file), `fallback_action=CREATE_FILE` +
`fallback_result=...` (special-artefact fallback), `replay=true` (replay rows).

The CSV log is the authoritative record; the replay JSON and the report are derived
from it.

---

## 9. The Lab Baseline

`fsactivity_baseline.json` is the operation set used to populate most corpus disk
images: **1000 logged actions, seed 153524984**, file marker `test*`, dir marker
`dir*`, content marker `samplecontent`, normal-file cap 512 KiB, plus **7 large
chunked files** of {2, 5, 7, 14, 86, 99, 149} MiB. Action mix:

| Action | Count | | Action | Count |
|---|---|---|---|---|
| CREATE_FILE | 252 | | RENAME_DIR | 45 |
| WRITE_FILE | 111 | | MOVE_DIR | 43 |
| MOVE_FILE | 80 | | DELETE_DIR | 26 |
| APPEND_FILE | 79 | | CREATE_HARDLINK | 4 |
| SET_TIMESTAMPS | 75 | | CREATE_SYMLINK_FILE | 4 |
| RENAME_FILE | 74 | | CREATE_ADS | 4 |
| DELETE_FILE | 73 | | CREATE_MARKED_FILE | 1 |
| COPY_FILE | 72 | | **Total** | **1000** |
| CREATE_DIR | 57 | | | |

> **Version note.** The baseline declares `schema_version 3.16`. **v3.20 replays it
> directly** - the replay reader consumes only `root_dir` + `actions` and ignores the
> declared schema, and all 16 baseline action types are handled by v3.20. To replay
> it onto a fresh volume:
> `.\Generate-FSActivity.ps1 -ReplayFile .\fsactivity_baseline.json -RootDir <vol>:\test -LogDir .\logs -CleanRoot`.
> (The earlier v2.3 script in this directory could **not** replay it - it only
> accepted schema 2.0-2.3.) The baseline itself is a frozen artefact and is not
> regenerated.

---

## 10. Validity and Limitations

- **Traceability.** Every action maps to a documented kernel operation; its expected
  artefacts derive from the NTFS specification and the ReFS analysis in this project.
- **Ground truth.** The CSV log is a verifiable record of what was done, against which
  tool output (e.g. `forefst.py`) can be evaluated objectively.
- **OS-level only.** The tool operates through OS APIs and cannot fabricate
  below-OS artefacts ($LogFile/MLog redo-undo records, boot structures).
- **No composite actions.** v3.20 schedules atomic actions only; there is no
  percentage budget or complex-action chaining (those belonged to the older v2.x
  design). Coverage is driven by the weighted planner + mandatory-core guarantee.
- **Reproducibility scope.** A seed reproduces *similar* generation choices; the
  authoritative reproduction path is **replay** of a logged JSON/CSV, which is
  deterministic in file-system effect and final sizes (not in random byte content).
- **ADS / hard links / symlinks.** ADS and hard links work on NTFS and ReFS;
  symlinks need elevation or Developer Mode. Any refusal is logged as `SKIP` with a
  fallback `CREATE_FILE`, so the action count is preserved but the artefact may be
  absent on a given volume.
- **LastAccess.** Access-time updates depend on the volume's last-access policy and
  are not guaranteed.

---

## 11. References

1. **Carrier, B. (2005).** *File System Forensic Analysis.* Addison-Wesley.
2. **Du, X., Hargreaves, C., Sheppard, J., & Scanlon, M. (2021).** TraceGen: User
   Activity Emulation for Digital Forensic Test Image Generation. *FSI: Digital
   Investigation, 38,* 301133. https://doi.org/10.1016/j.fsidi.2021.301133
3. **Gobel, T., et al. (2022).** ForTrace - A Holistic Forensic Data Set Synthesis
   Framework. *FSI: Digital Investigation, 40,* 301344.
   https://doi.org/10.1016/j.fsidi.2022.301344
4. **Oh, J., Lee, S., & Hwang, H. (2024).** Forensic Detection of Timestamp
   Manipulation for Digital Forensic Investigation. *IEEE Access, 12,* 72544-72565.
   https://doi.org/10.1109/ACCESS.2024.3395644
5. **Scanlon, M., Du, X., & Lillis, D. (2017).** EviPlant: An Efficient Digital
   Forensic Challenge Creation, Manipulation and Distribution Solution. *Digital
   Investigation, 20,* S29-S36. https://doi.org/10.1016/j.diin.2017.01.010
6. **Microsoft Corporation. (2024).** Windows Driver Kit: `wdm.h`, `ntifs.h` -
   USN_REASON_* constants and reparse-point tag definitions.
   https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/
7. **The Open Group. (2017).** *IEEE Std 1003.1-2017 (POSIX).*
   https://pubs.opengroup.org/onlinepubs/9699919799/
8. **Zimmermann, E. (2019).** MFTECmd - NTFS $MFT Parser. https://ericzimmerman.github.io
