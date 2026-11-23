# Detecting a Back-Dated (Timestomped) File

**Goal:** take a ReFS image, find the files whose creation time looks forged into the past, and corroborate each
lead with a record outside the file's own timestamps (the change journal, a second hard-link name) rather than with
a single suspicious timestamp.

## Setup

Image: `win11refstestmftecmd.raw`, a ReFS 3.14 volume of the test corpus, formatted **2026-05-23**.

It was then driven through four replay runs of the lab generator, into `test/`, `test2/`, `testspecials/` and
`testintegrity/`. Together they issued **195 `SET_TIMESTAMPS` actions, 186 of which succeeded**; each one sets a
file's Created, Modified and Accessed times to one forged instant, between 2021-05-18 and 2026-05-10, every one of
them earlier than the volume's format.

Every file the generator created is named `xbpt_*`. Which of them were back-dated, to what value and when is in the
generator's logs published with the sample (`provenance/fsactivity/*_replay_log.csv`, action `SET_TIMESTAMPS`), so
every flag the tool raises can be checked. Many targets were renamed or moved afterwards: check a flag against the
file's identity and its Created value, not its current path.

## Steps

### Step 1 — Triage with the high-confidence filter

The output (the header and the first suspects):

```text
$ forefst.py win11refstestmftecmd.raw timestomp --min HIGH
==============================================================================
ReFS Timestamp-Anomaly (Timestomp) Detection
==============================================================================
  Image:           win11refstestmftecmd.raw  (ReFS 3.14)
  Volume created:  2026-05-23T06:04:52.2710301Z
  Last mount (rw): 2026-05-23T11:15:52.2975673Z
  USN journal:     Active; it starts at USN 0, dated 2026-05-23T07:38:44.2867313Z, its lowest
                   surviving record.
                   Files changed before 2026-05-23T07:38:44.2867313Z cannot be corroborated by it.
  Files examined:  1507
  Flagged:         194  (HIGH 137 / MEDIUM 0 / LOW 0 / INFO 57 — INFO = ambiguous: a
                   timestamp-preserving copy and a backdated creation produce the same signals;
                   corroborate with USN)

  This flags timestamps that LOOK anomalous — it is investigative INFORMATION, not proof of
  tampering. Weigh the BASIS of each row: a journal/hardlink signal is authoritative; an
  intrinsic ($SI-only) signal is a heuristic that also fires on legitimate timestamp-preserving
  copies/restores. Tiers, exactly as timestomp_verdict() decides them:
    HIGH   — an AUTHORITATIVE corroboration: the change journal, or a disagreement between
             two of the file's own hard-link names. A count of intrinsic signals never reaches HIGH.
    MEDIUM — CHANGE_LATE without PRE_FORMAT (created on THIS volume, metadata altered later).
    INFO   — every signal present is one a timestamp-preserving copy also produces
             (PRE_FORMAT / CHANGE_LATE / CREATE_GT_MODIFY / ROUND_TIMESTAMPS), so a copy and a
             backdate are indistinguishable here however many of them fire.
    LOW    — anything else (no current signal reaches it).

  Conf   Basis         Claimed birth                Changed                      Path
  ------------------------------------------------------------------------------------------------
  HIGH   journal/link  2022-08-02T07:16:28.1705690Z 2026-05-23T07:34:02.0123753Z test/elvis_dir_record_449015/elvis_dir_lima_252141/elvis_dir_oscar_306778/xbpt_romeo_output_531365.cfg
         signals: PRE_FORMAT, HARDLINK_MACB_MISMATCH   evidence: hardlink:test/elvis_dir_record_449015/elvis_dir_papa_104235/elvis_dir_sync_718743/elvis_dir_gamma_109016/elvis_dir_zulu_984398/elvis_dir_cache_558805/xbpt_hardlink_audit_219848.cfg
  HIGH   journal/link  2026-05-23T07:33:58.7196982Z 2026-05-23T07:34:01.0429129Z test/elvis_dir_record_449015/elvis_dir_papa_104235/elvis_dir_sync_718743/elvis_dir_gamma_109016/elvis_dir_zulu_984398/elvis_dir_cache_558805/xbpt_hardlink_audit_219848.cfg
         signals: HARDLINK_MACB_MISMATCH   evidence: hardlink:test/elvis_dir_record_449015/elvis_dir_lima_252141/elvis_dir_oscar_306778/xbpt_romeo_output_531365.cfg
  HIGH   journal/link  2026-01-01T07:16:17.1671215Z 2026-05-23T07:38:51.6323343Z test2/elvis_dir_index_149423/elvis_dir_victor_121923/elvis_dir_hotel_670324/elvis_dir_output_358165/xbpt_audit_echo_178867.tmp
         signals: PRE_FORMAT, USN_BASIC_INFO_CHANGE, USN_CREATE_MISMATCH   evidence: usn:BASIC_INFO_CHANGE@0x782:0x2, usn:FILE_CREATE@0x782:0x2
  HIGH   journal/link  2024-08-03T07:17:33.0580290Z 2026-05-23T07:38:52.0221762Z test2/elvis_dir_index_149423/elvis_dir_victor_121923/elvis_dir_hotel_670324/elvis_dir_output_358165/xbpt_zulu_india_473528.csv
         signals: CHANGE_LATE, PRE_FORMAT, USN_BASIC_INFO_CHANGE, USN_CREATE_MISMATCH   evidence: usn:BASIC_INFO_CHANGE@0x7a8:0x4, usn:FILE_CREATE@0x7a8:0x4
[...]
```

The header shows the **volume creation time** (`$VOLUME_INFORMATION +0x90`), the value `PRE_FORMAT` compares each
Created time against.

It also says where the USN journal starts: the journal cross-check reaches the files changed after its lowest
surviving record, and no earlier. On this volume the journal was created after the `test/` replay and before the
`test2/` one, so none of the files back-dated under `test/` can be corroborated by it.

The `Basis` column says why a row is HIGH. Every HIGH row says **`journal/link`**: a record outside the file's own
timestamps corroborates it.

- **The journal:** a standalone `BASIC_INFO_CHANGE` record for the file (`USN_BASIC_INFO_CHANGE`: its basic
  information was edited with no content change), or a `FILE_CREATE` record whose time disagrees with Created
  (`USN_CREATE_MISMATCH`).
- **A second name:** two of the file's own hard-link names disagree on Created (`HARDLINK_MACB_MISMATCH`); each name
  caches a copy of the file's times.

Only such a record gives HIGH; **a count of intrinsic signals never does**, however many fire. Every row below HIGH is
`intrinsic`.

The other 57 rows are `INFO`, and the distinction matters more than the number. Legitimate time-setting (Windows servicing
and installers writing files with their package dates, a copy keeping its source's times) produces the same `$SI`-only
signals as a backdate, so on those rows the volume cannot separate the two.

`INFO` means *ambiguous*: neither cleared nor confirmed. On this image most of the 57 are real back-dates made under
`test/` before the journal existed; the others carry a current Created with a forged Modified, what a copy of a
back-dated file leaves.

### Step 2 — Read the full verdict and signal legend

Running the same subcommand with `--min INFO` lists every tier (the screen shows HIGH by default; CSV
and JSON carry every tier), and every listing ends with the legend the analyst needs to read the signals.
The tail of `timestomp --min INFO`:

```text
$ forefst.py win11refstestmftecmd.raw timestomp --min INFO
[...]
  Signal legend  (AUTHORITATIVE = a second structure: the change journal or another name's entry ·
                  HEURISTIC = suggestive, from the $SI alone):
    [AUTHORITATIVE]
      USN_BASIC_INFO_CHANGE  the USN journal recorded a basic-info change (no content change)
      USN_CREATE_MISMATCH    $SI created differs from the FILE_CREATE journal record (true birth known)
      HARDLINK_MACB_MISMATCH one hard-link name's $SI created diverges from another's (ReFS per-name
                             MACB). No routine cause was observed on the corpus; which name is
                             authentic is NOT established, and its absence means nothing
    [HEURISTIC — $SI only, corroborate]
      CHANGE_LATE            $SI change-time post-dates created/modified (SetFileTime/PowerShell/.NET
                             can't reach change-time) — defeated by a native-API/raw-disk stomp
      PRE_FORMAT             created before the volume existed
      CREATE_GT_MODIFY       created after last write
      ROUND_TIMESTAMPS       created AND modified are whole-second (.0000000) — a tool often sets a
                             date with no sub-second time; alone it is INFO and it never raises a
                             tier (driver packages also carry whole-second times)
  Note: PRE_FORMAT / CHANGE_LATE / CREATE_GT_MODIFY also fire on legitimate time-setting —
  Windows servicing and installers write files with their package dates, a copy keeps its
  source's times — and equally on a deliberately backdated creation. PRE_FORMAT with
  CHANGE_LATE alone is INFO: ambiguous, not cleared. The one $SI signal that reaches HIGH is
  HARDLINK_MACB_MISMATCH, which a copy cannot produce; corroborate anything below HIGH with
  the USN journal.
```

`CHANGE_LATE` stands in for NTFS's `$SI`-vs-`$FN` check. ReFS has no `$FILE_NAME` set: for a single-named file it
keeps one timestamp set, so instead of a second set the check uses the **change time** (`$SI +0x10`), which the
common timestamp APIs cannot set, as the reference. (A hard-linked file's names each cache a copy of the times;
`HARDLINK_MACB_MISMATCH` compares those.)

`PRE_FORMAT` looks impossible, because a file cannot predate its own filesystem. But a timestamp-preserving copy of
an older file carries a creation time from the volume it came from, which predates this one.

That is why **their agreement is not conclusive**, and why the pair rates `INFO`. More heuristic signals do
not make a result authoritative; they repeat the same ambiguity. What lifts a row to HIGH is a record
outside the file's own timestamps: the change journal, or a disagreement between the times cached in the file's
hard-link names.

### Step 3 — Pull a single flagged record

One flagged row (one object of the report's `Rows` list):

```text
$ forefst.py win11refstestmftecmd.raw timestomp --json
[...]
    {
      "ObjectRef": "0x76e:0x4",
      "FullPath": "test/elvis_dir_index_149423/elvis_dir_victor_121923/elvis_dir_hotel_670324/elvis_dir_output_358165/xbpt_zulu_india_473528.csv",
      "RecordPlacement": "embedded",
      "DataResidency": "extents",
      "Confidence": "INFO",
      "Basis": "intrinsic",
      "Signals": [
        "CHANGE_LATE",
        "PRE_FORMAT"
      ],
      "EvidenceRefs": [],
      "Created": "2024-08-03T07:17:33.0580290Z",
      "Modified": "2024-08-03T07:17:33.0580290Z",
      "Changed": "2026-05-23T07:34:05.8110736Z",
      "Accessed": "2024-08-03T07:17:33.0580290Z"
    },
[...]
```

This is **not** the HIGH row from Step 1, and the difference between them is what this step shows. The volume carries
`xbpt_zulu_india_473528.csv` twice, as two different files created and back-dated the same way by two replay runs:

- this one, `0x76e:0x4` under `test/`, flagged **INFO** on `CHANGE_LATE|PRE_FORMAT` alone;
- its namesake `0x7a8:0x4` under `test2/`, which appears in Step 1 as **HIGH**: the same two intrinsic signals
  *plus* `USN_BASIC_INFO_CHANGE` and `USN_CREATE_MISMATCH`.

Only the second was back-dated after the journal was created (between the two runs), so only it has journal
records, and only it reaches HIGH.

Their forged birth is the same instant (`2024-08-03T07:17:33.0580290Z`). Their change times differ
(`2026-05-23T07:34:05.8110736Z` here, `2026-05-23T07:38:52.0221762Z` there): each is the moment that file's times
were forged.

This is what a stomp with the common APIs leaves, and it is also what a timestamp-preserving copy leaves. **B = M = A**
all hold the forged 2024 instant: the generator set them with three .NET calls (`SetCreationTimeUtc`,
`SetLastWriteTimeUtc`, `SetLastAccessTimeUtc`). **C** (`Changed`) was set by the file system to the moment of those
calls (07:34:05.811, 0.6 s after the file was created), because those APIs cannot choose its value. C therefore
dates the stomp, not the last write.

The two intrinsic indicators are computed straight from the `$SI` MACB times. What raises a row above INFO is a
journal record for the file, which exists only if the journal was running when the file was edited, or a
disagreement between its hard-link names.

## What this tells you

- The file `xbpt_zulu_india_473528.csv` under `test/` was created on this volume on **2026-05-23** at 07:34:05,
  and its Created, Modified and Accessed times were forged back to **2024-08-03**.
  - We know it was a deliberate back-date from the generator's log.
  - From the image alone it stays ambiguous (INFO): a timestamp-preserving copy made on this volume leaves the same
    traces.
  - Its change time, 07:34:05.811, is the moment its times were forged, not its birth.
- The two signals are one observation, not two proofs. `PRE_FORMAT` says the Created value is older than the volume,
  which a copy or a restore also produces. `CHANGE_LATE` shows C later than B and M, which a stomp with the common
  APIs leaves until the file is next written, and which a timestamp-preserving copy also leaves.
- This file has no journal record: the journal was created after it was back-dated. Its `test2/` namesake has
  `BASIC_INFO_CHANGE` records from 07:38:52, evidence that its times were edited after it was created there.
- A lone old creation date is only a suspicion. The `forefst.py timestomp` HIGH tier
  means **one record outside the file's own timestamps** (a journal record or a second hard-link name) corroborates
  the anomaly. On this one ground-truth image that produced 137 HIGH detections, all true positives — a
  single-image datapoint, not a measured accuracy rate.
- **One command judges timestamps.** `forefst.py timestomp` is where a timestamp anomaly is judged; `files` carries
  no verdict column: a listing cannot read the journal, so it could only report the signals that need no
  journal.

## See also

- [Timestomping detection](../concepts/timestomp_detection.md) — the three sources to check a time against,
 the signal table, and the confidence-tier logic
- [Artifact timeline](../concepts/artifact_timeline.md) — the timestamp sources (`$SI`, USN journal, MLog,
 checkpoint clock, volume times) and how to cross-validate them
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the MACB FILETIMEs
 at `$SI +0x00/+0x08/+0x10/+0x18` (value+0x28 in an embedded record or a split file's backing; a split file's
 name row caches them at value+0x10)
- [USN journal](../structures/usn_journal.md) — the `BASIC_INFO_CHANGE` and
 `FILE_CREATE` records the journal check uses
- [$VOLUME_INFORMATION](../attributes/VOLUME_INFORMATION.md) — volume creation time at
 `+0x90`, the value `PRE_FORMAT` compares Created against
- Master **§C.7** ($STANDARD_INFORMATION timestamps), **§C.13** (USN journal records)
