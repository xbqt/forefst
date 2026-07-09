# Worked Example: Detecting a Back-Dated (Timestomped) File

**Goal:** take a ReFS image, find the files whose creation time was forged into the
past, and prove the tampering with an independent anchor rather than a single
suspicious timestamp.

## Setup

Image: a ReFS 3.14 volume
formatted **2026-05-23** and then driven through a replay log that issued **75
`SET_TIMESTAMPS` operations** back-dating file creation into 2021–2025. The forged
files are named `xbpt_*`. This is ground truth: we know which files were stomped and
when the volume really existed, so every flag the tool raises can be checked.

## Steps

### Step 1 — Triage with the high-confidence filter

```
python3 forefst.py \
 image.raw timestomp --min HIGH
```

Actual output (header + first suspects):

```
==============================================================================
ReFS Timestamp-Anomaly (Timestomp) Detection
==============================================================================
 Image: <image>.raw (ReFS 3.14)
 Volume created: 2026-05-23 06:04:52
 Volume modified: 2026-05-23 11:15:52
 USN journal: present (authoritative cross-check ON)
 Files examined: 1507
 Flagged: 184 (HIGH 114 / MEDIUM 62 / LOW 8)

 Conf Created (forged?) Changed (real write) Path
 ----------------------------------------------------------------------------------------------
 HIGH 2024-08-03 07:17:33 2026-05-23 07:34:05 test/.../elvis_dir_output_358165/xbpt_zulu_india_473528.csv
 signals: CHANGE_LATE, PRE_FORMAT
 HIGH 2024-11-23 07:17:31 2026-05-23 07:34:05 test/.../xbpt_whiskey_delta_922359.tmp
 signals: CHANGE_LATE, PRE_FORMAT
 HIGH 2023-11-27 07:16:30 2026-05-23 07:34:03 test/.../xbpt_beta_archive_985685.tmp
 signals: CHANGE_LATE, PRE_FORMAT
```

The header pins the **volume creation bound** (`2026-05-23 06:04:52`) read from
`$VOLUME_INFORMATION +0x90`, and confirms the USN journal is present so the
authoritative cross-check is on. Each HIGH row shows a forged `Created` in 2023–2024
sitting *before* the volume existed, while the real metadata-write (`Changed`,
`$SI +0x10` MACB-block-relative = `value+0x38` in the master's value-relative
numbering, §C.2) is the true 2026-05-23 moment the stomp ran. Two independent intrinsic
signals — `CHANGE_LATE` and `PRE_FORMAT` — agree, which is what earns the HIGH tier.

### Step 2 — Read the full verdict and signal legend

Running the same subcommand without `--min` lists every tier and prints the legend
the analyst needs to read the signals. Actual tail of the output:

```
 Signal legend:
 CHANGE_LATE $SI change-time post-dates created/modified — common timestomp
 tools (SetFileTime/PowerShell/.NET) can't reach it; defeated by a
 native-API/raw-disk stomp that also sets the change time
 USN_BASIC_INFO_CHANGE journal recorded a deliberate basic-info edit (no content change)
 USN_CREATE_MISMATCH $SI created differs from the FILE_CREATE journal record
 PRE_FORMAT / FUTURE created before the volume existed / after its last write
 CREATE_GT_MODIFY created after last write
 Note: CHANGE_LATE / PRE_FORMAT also fire on creation-time-preserving copies
 (robocopy /COPY:T, restore); HIGH requires independent-source agreement.
```

`CHANGE_LATE` is the ReFS analogue of NTFS's `$SI`-vs-`$FN` check: ReFS keeps only one
timestamp set, so instead of a second set we use the **not-normally-reachable change
time** (`$SI +0x10`) as the reference. `PRE_FORMAT` is a hard physical impossibility —
a file cannot predate its own filesystem. The note is the reason the tier matters:
either signal alone could be an innocent creation-preserving copy; only their
agreement (or a USN confirmation) is conclusive.

### Step 3 — Pull a single flagged record from the lister

```
python3 forefst.py \
 image.raw --timestomp --jsonl
```

Actual flagged row (one JSONL object, abridged to the fields that matter):

```json
{
 "parent_path": "test/.../elvis_dir_output_358165",
 "file_name": "xbpt_zulu_india_473528.csv",
 "file_size": 472261,
 "is_directory": false,
 "created": "2024-08-03 07:17:33.0580290",
 "modified": "2024-08-03 07:17:33.0580290",
 "changed": "2026-05-23 07:34:05.8110736",
 "accessed": "2024-08-03 07:17:33.0580290",
 "file_attributes": "Archive",
 "timestomp_flags": "CHANGE_LATE|PRE_FORMAT",
 "refs_version": "3.14"
}
```

This is the same file as the first HIGH row in Step 1 — identical path, identical
`Created` (`2024-08-03 07:17:33`) and `Changed` (`2026-05-23 07:34:05`). The signature
of a common-tool stomp is laid bare here: **B = M = A** were all rewritten to the
forged 2024 instant in one `SetFileTime`-style call, while **C** (`changed`) stayed at
the real 2026 write — because the high-level API has no `ChangeTime` parameter to
reach it. The `TimestompFlags` column (`timestomp_flags` in JSONL) carries the two
intrinsic indicators computed straight from the `$SI` MACB times, no journal needed.

## What this tells you

- The file `xbpt_zulu_india_473528.csv` was created **2026-05-23** (its real change
 time, and after the volume was formatted) but its creation/modify/access times were
 forged back to **2024-08-03**. That is a deliberate back-date, not a copy artifact.
- The proof is layered: `PRE_FORMAT` is a physical impossibility (created before the
 volume existed), and `CHANGE_LATE` shows the asymmetry common timestomp tools leave
 behind. With the USN journal present, the `BASIC_INFO_CHANGE` records on this image
 would independently confirm the same.
- Method, not single value: a lone old creation date is only a suspicion. The
 `forefst.py timestomp` HIGH tier means **two independent anchors agree**, which
 on this one ground-truth image produced 114 HIGH detections, all true positives (0 false positives on
 the clean control) — a single-image datapoint, not a measured accuracy rate.
- `forefst.py --timestomp` is the fast intrinsic pass (`$SI`-only flags on every row);
 `forefst.py timestomp` is the full cross-source verdict that adds the journal.

## See also

- [Timestomping detection](../concepts/timestomp_detection.md) — the three anchors,
 the signal table, and the confidence-tier logic
- [Artifact timeline](../concepts/artifact_timeline.md) — every ReFS timestamp source
 and how to cross-validate them
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the MACB FILETIMEs
 at `$SI +0x00/+0x08/+0x10/+0x18` (value region from offset `0x28`)
- [USN journal](../structures/usn_journal.md) — the `BASIC_INFO_CHANGE` and
 `FILE_CREATE` records used as the authoritative anchor
- [$VOLUME_INFORMATION](../attributes/VOLUME_INFORMATION.md) — volume creation time at
 `+0x90`, the `PRE_FORMAT` lower bound
- Master **§C.7** ($STANDARD_INFORMATION timestamps), **§C.13** (USN journal records)
