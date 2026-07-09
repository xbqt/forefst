# Timestomping Detection

Timestomping — back-dating a file's timestamps to hide when it was really created or written — is a
standard anti-forensic move, and the technique an analyst reaches for first does not exist on ReFS.
NTFS exposes it by comparing the two timestamp sets every file carries, the
[$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) set against the `$FILE_NAME` set; when a
tool stomps `$SI` but leaves `$FN` untouched, the mismatch is the tell. ReFS carries **one `$SI`
timestamp set per name**, not a second `$FILE_NAME` copy — so for a **single-named** file there is no
`$SI`-vs-`$FN` twin to compare against and that particular cross-check is unavailable. A **hard-linked**
file is the exception: each of its names holds an **independent** timestamp copy, so a name-scoped stomp
leaves the sibling names sitting at the true birth, and comparing a file's names' MACB becomes a
ReFS-specific tamper check (see [Hard Links](hard_links.md)). Beyond that, timestomping is detectable
through different anchors: the metadata-change time that common
tools cannot reach, the [USN change journal](../structures/usn_journal.md) that records the tampering
operation itself, and the volume's own creation time as a hard floor. This page explains each anchor,
why it works, and where it fails.

## Three independent anchors

ReFS gives the analyst three things to lean on, in increasing order of strength:

1. **The metadata-change time is left behind.** The high-level Windows APIs that ordinary timestomp tools
   call cannot set the change time, so the filesystem stamps it at the moment of the stomp while the
   forged times sit in the past. This is a heuristic against common tooling, not a guarantee.
2. **The USN journal records the edit.** A deliberate timestamp change is logged as a `BASIC_INFO_CHANGE`
   record at its real time, and a file's genuine creation is logged as a `FILE_CREATE` record. The journal
   is append-only, so these are the stronger, harder-to-forge anchors.
3. **The volume creation time is a floor.** A file cannot have been created before the filesystem it lives
   on existed. Any creation time earlier than the volume's own creation is structurally impossible.

The `forefst.py <image> timestomp` subcommand combines all three and ranks suspects by confidence.

## Why the change time is the key intrinsic anchor

A ReFS `$SI` holds four FILETIMEs, all at fixed offsets in the type-0x10 own-row's value (see
[$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md)):

| Offset | Time | Letter |
|--------|------|--------|
| 0x00 | Creation | **B** |
| 0x08 | Modification / last write | **M** |
| 0x10 | Metadata change | **C** |
| 0x18 | Last access | **A** |

The metadata-change time `C` is an ordinary timestamp — nothing about it is cryptographic or
tamper-proof. What makes it useful is an **API asymmetry**: the high-level interfaces a timestomp tool
normally uses expose only three of the four times.

- Win32 `SetFileTime(hFile, &Creation, &LastAccess, &LastWrite)` has **no `ChangeTime` parameter**.
- PowerShell `Set-ItemProperty -Name CreationTime/LastWriteTime/LastAccessTime` and .NET
  `File.SetCreationTime / SetLastWriteTime / SetLastAccessTime` expose the **same three**.

A caller using any of these **cannot reach `C`**, and the filesystem updates `C` to *now* as a side
effect of the metadata write it performs. So after a back-dating stomp, B/M/A point into the past while
`C` is left at the real moment of the operation. The signature is

```
C >> max(B, M)
```

flagged as **CHANGE_LATE**. For a single-named file it is the closest ReFS analogue of the NTFS
`$SI`-versus-`$FN` comparison — using the not-normally-reachable change time as the reference instead of
a second timestamp set. (When the file is **hard-linked**, a truer analogue is available: the sibling
names' own timestamp copies, discussed below as `HARDLINK_MACB_MISMATCH`.)

**This defeats common tooling, not a determined attacker.** The change time *is* settable through the
native path: `FILE_BASIC_INFORMATION.ChangeTime` passed to `NtSetInformationFile` carries an explicit
change time, and the ReFS driver honours it. The driver tracks, per open handle, which of the four times
the caller supplied explicitly versus which the filesystem should auto-update — a flag per time
(change included) that only exists *because* every one of the four times can be set explicitly. An
attacker who sets all four through the native API, or who edits the raw `$SI` bytes on disk directly,
leaves **no** `CHANGE_LATE` signal. The intrinsic change-time anchor catches PowerShell / `SetFileTime`
/ .NET timestomp tools; it does not catch someone who knows about `ChangeTime`. When the journal is
present, it is the anchor that does not depend on the attacker's tool choice.

## The signals

The tool emits a set of named signals; each is a single comparison, and each has a different strength
and a different way to be wrong.

| Signal | Meaning | Source | Strength |
|--------|---------|--------|----------|
| **CHANGE_LATE** | `$SI` change time (0x10) post-dates Created/Modified by a wide margin — back-dated B/M against the real metadata-write time | intrinsic ($SI only) | strong vs common tools; **defeated** by a native-API or raw-disk stomp that sets `C` too |
| **HARDLINK_MACB_MISMATCH** | two names of one hard-linked file disagree on Created — a name-scoped stomp rewrites only the opened name's `$SI` copy, so the sibling name still holds the true birth (the **latest** Created among the names is authentic; only the back-dated name is flagged, never the clean sibling) | intrinsic (per-name `$SI`) | strong; **journal-independent**, and unlike NTFS the copies *can* diverge; only fires when a file has more than one name |
| **USN_BASIC_INFO_CHANGE** | the journal holds a **standalone** `BASIC_INFO_CHANGE` (reason 0x8000, with no `FILE_CREATE` or `DATA_*` bits) — a deliberate basic-info / timestamp edit with **no content change**, recorded at its real time | USN journal | authoritative |
| **USN_CREATE_MISMATCH** | `$SI` Created differs from the file's `FILE_CREATE` journal record (the journal is append-only) | USN journal | authoritative |
| **PRE_FORMAT** | Created precedes the **volume** creation time — impossible for a file genuinely created here | intrinsic + volume | strong\* |
| **FUTURE** | Created after the volume's last metadata write | intrinsic + volume | medium\* |
| **CREATE_GT_MODIFY** | Created after last write | intrinsic | weak\* |

\* `PRE_FORMAT`, `FUTURE`, `CREATE_GT_MODIFY` — and `CHANGE_LATE` — also fire on a
**creation-time-preserving copy** (robocopy `/COPY:T`, a backup restore) or a legitimate late rename or
ACL change on an aged file: these keep or set an old creation time while the metadata-write / change time
is recent. Such a file is a genuine *inconsistency*, but whether it is malicious needs analyst context.
The USN journal is what turns a suspicion into a confirmation, because it records the operation that
caused the inconsistency at the time it actually happened.

`HARDLINK_MACB_MISMATCH` is the exception to that dependence: a creation-preserving copy gives every name
the same times, so it does **not** trip on benign copies — it fires only when a file's own names genuinely
disagree on Created, which a name-scoped stomp is the natural cause of. That makes it a self-contained
tamper check that needs no journal and no volume-create floor to stand on.

## Confidence tiers

The tool collapses the signal set into one of three verdicts:

- **HIGH** — the journal confirms a deliberate edit (`USN_BASIC_INFO_CHANGE` or `USN_CREATE_MISMATCH`)
  **and** an intrinsic signal agrees; **or** two independent intrinsic signals agree
  (`CHANGE_LATE` + `PRE_FORMAT`); **or** the journal alone confirms it.
- **MEDIUM** — one solid intrinsic signal (`CHANGE_LATE` or `PRE_FORMAT`) with no journal to confirm it,
  so a creation-preserving copy cannot be ruled out.
- **LOW** — a weak or common signal alone (`FUTURE`, `CREATE_GT_MODIFY`).

The journal's presence is the dividing line between HIGH and MEDIUM: without it, even a strong intrinsic
inconsistency stays one explanation short of confirmation.

## What does not work as a substitute

Two tempting shortcuts do not hold up and should not be treated as primary signals:

- **The NextFileId ordinal** (`$SI+0x58` on v3.7–v3.10; `ExternalFileId_1` on v3.4) is a per-directory
  child-creation ordinal — it records each child's position in the directory's creation sequence, written
  by `RefsMoveFile` incrementing the parent directory's counter. A higher ordinal means the child was
  created later in *that directory's* lifecycle, so a gross created-time-versus-ordinal inversion within
  one directory is corroborating. But it is coarse: it is directory-scoped, and it is 0 on native v3.14
  own-rows (the ordinal moved into the object-record payload at v3.11), so it cannot be a general anchor.
- **A zero sub-second fraction** (whole-second times, the low 100 ns part = 0) is sometimes left by
  timestomp tools that write second-granularity values, but it is entirely tool-dependent — a tool that
  copies full-resolution FILETIMEs leaves no such fingerprint, so it is unreliable on its own.

## How the tool is wired

The two parts of the detector live in different places for a reason. The lister `forefst.py` defines the
shared `timestomp_intrinsic_flags()` helper, which computes only the `$SI`-intrinsic signals
(`CHANGE_LATE`, `PRE_FORMAT`, `CREATE_GT_MODIFY`, `FUTURE`) without touching the journal — invoking the
lister with `--timestomp` attaches these as a per-row `TimestompFlags` column (CSV) or `timestomp_flags`
field (JSON). The full cross-source verdict, which loads the [USN journal](../structures/usn_journal.md)
and adds the `BASIC_INFO_CHANGE` and create-mismatch signals, lives in
`forefst.py <image> timestomp`, which imports the same helper so the intrinsic logic is identical:

```
forefst.py <image> timestomp                # flagged files, ranked by confidence
forefst.py <image> timestomp --min HIGH     # only high-confidence suspects
forefst.py <image> timestomp --json         # machine-readable
forefst.py <image> timestomp --csv out.csv  # per-file CSV (path, confidence, signals, MACB)
forefst.py <image> timestomp --all          # every file with its flags (incl. NONE)
forefst.py <image> timestomp --margin-days N # anomaly margin (default 1 day)
```

The `--margin-days` value is the slack the intrinsic comparisons allow before calling a gap suspicious,
which keeps ordinary clock skew and sub-day operation latency from generating noise.

## Cross-references

- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the per-name timestamp set ReFS carries (B/M/C/A at 0x00/0x08/0x10/0x18) that every intrinsic signal reads
- [Hard Links](hard_links.md) — why each name of a file carries its own `$SI` copy, so their MACB can diverge under a name-scoped stomp (the `HARDLINK_MACB_MISMATCH` basis)
- [USN Journal](../structures/usn_journal.md) — the append-only record whose `BASIC_INFO_CHANGE` (reason 0x8000) and `FILE_CREATE` entries are the authoritative anchors
- [Artifact Timeline](artifact_timeline.md) — how the MACB times feed a unified event timeline
- [Forensic Analysis Workflow](forensic_analysis_workflow.md) — the tamper check is step seven (`$SI` vs USN vs volume-create) of the standard workflow
- [Copy-on-Write](copy_on_write.md) — why a content-preserving copy can keep an old creation time and trip the intrinsic signals
- [What Survives](what_survives.md) — the format-time immutables that fix the volume creation floor

## Evidence

The four-FILETIME `$SI` layout, the NextFileId ordinal, and the per-handle "caller supplied this time
explicitly" tracking are confirmed in the driver (E2): `RefsComputeStandardInformationInternalFromFcb`
builds the `$SI` fields from the FCB, `RefsMoveFile` writes the directory child-creation ordinal, and the
driver honours an explicit `FILE_BASIC_INFORMATION.ChangeTime`. The detection itself is validated on the
raw-disk corpus (RD) against a controlled ground-truth image built by a replay log of `SET_TIMESTAMPS`
operations that back-date creation by years on a freshly formatted volume: every HIGH-tier file has a
provable basis (created before the volume existed and/or a journal-confirmed deliberate edit), the clean
baseline and a clean operations image (real renames, ADS, snapshots, symlinks, hardlinks) flag nothing,
and the same synthetic back-dated files are flagged identically wherever the test corpus was written. The
journal's standalone `BASIC_INFO_CHANGE` records sit on the timestomp image at the tampering's real time
while `$SI` shows the forged time. The per-name MACB behind `HARDLINK_MACB_MISMATCH` is a documented
correction (RD): `$SI` is stored per name entry (per hard link), not per inode, so a name-scoped stomp on
one of two hard links leaves the sibling name at the true birth — measured directly on a two-name file
where the opened name reads a back-dated Created and its sibling reads the real creation moment. See [how this was verified](../methodology.md) to
trace these to the exact images and measurements in `analysis/`.
