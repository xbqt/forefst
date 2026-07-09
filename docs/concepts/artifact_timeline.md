# Timestamp Sources and the Super-Timeline

Time is the spine of most filesystem investigations, and ReFS scatters it across five
independent artifacts that an analyst has to read separately and then reconcile: the per-file
`$SI` MACB times, the USN change journal, the MLog transaction log, the checkpoint virtual clock,
and the volume-creation bound. No single one of them is a complete history, and they are not
equally trustworthy. This page catalogues every timestamp source you can read off a ReFS image,
how to read each one, and — the part that actually matters forensically — how to cross-validate
them against each other. That cross-validation is the foundation of
[timestomp detection](timestomp_detection.md): on ReFS, an inconsistency *between* these sources
is the tell, because for a single-named file the system never built a redundant second timestamp
set the way NTFS did. (A hard-linked file is the exception — each of its names carries its own
independent `$SI` copy, giving a redundant set that *can* diverge; see below.)

## One timestamp set per name

ReFS carries **one** `$SI` timestamp set **per name**. The four FILETIMEs live in
[`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) (`$SI`), the fixed region of the
type-0x10 [directory-entry](../structures/directory_entries.md) value at offset `0x28+`. For a
single-named file there is no `$FILE_NAME` twin as on NTFS to compare `$SI` against — that crutch is
gone here, which is exactly why the *other* four sources carry the cross-validation load. Every
FILETIME on ReFS is a little-endian `u64` counting 100-ns intervals since 1601-01-01 UTC, converted
with the standard FILETIME epoch.

The one exception is a **hard-linked file**. Because `$SI` is stored per name rather than per inode,
a file with N names has N *independent* timestamp copies — one in each name's directory-entry row —
whereas NTFS keeps a single `$SI` that all hard links share. A name-scoped `SetFileTime` (opening
one path and setting its times) rewrites only that name's copy; the sibling names keep the true
birth. Comparing a file's names' MACB is therefore a ReFS-specific tamper check — journal-independent,
and *stronger* than NTFS's `$SI`-vs-`$FN`, where hard links cannot diverge because they share one
`$SI`. The [timestomp detection](timestomp_detection.md) page turns this into the
`HARDLINK_MACB_MISMATCH` signal.

The remaining four sources are not per-file metadata at all; they are **volume-level event and
clock artifacts**, each with a different relationship to wall-clock time:

```
 ┌──────────────────────────────────────────────────────────────┐
 │ $VOLUME_INFORMATION +0x90 → volume creation (hard lower bound)│
 ├──────────────────────────────────────────────────────────────┤
 │ $SI Created/Modified/Changed/Accessed → the file's own MACB   │
 ├──────────────────────────────────────────────────────────────┤
 │ USN $J records (+0x30 FILETIME) → per-operation event log     │
 ├──────────────────────────────────────────────────────────────┤
 │ MLog redo records (embedded FILETIMEs) → in-flight txn times  │
 ├──────────────────────────────────────────────────────────────┤
 │ CHKP virtual clock (+0x60) → monotone transaction sequence    │
 └──────────────────────────────────────────────────────────────┘
```

Conceptually they divide cleanly. `$SI` is the snapshot of "now" — the *current* state and nothing
historical. The USN journal is the append-only *history* of how it got there. The MLog holds the
most recent transactions that have not yet been folded into a checkpoint. The CHKP virtual clock is
a monotone *ordering* — a sequence counter, not a wall clock. And the volume-creation time is a
fixed floor underneath all of them.

## The five sources in detail

| Source | Field | Offset | Meaning | How to read |
|--------|-------|--------|---------|-------------|
| **`$SI`** | Created (B) | value `0x28`+`0x00` | File creation | FILETIME `u64` LE; `$SI` starts at the type-0x10 value offset `0x28` |
| **`$SI`** | Modified / LastWrite (M) | value `0x28`+`0x08` | Last data write | FILETIME `u64` LE |
| **`$SI`** | Metadata-Change (C) | value `0x28`+`0x10` | Last metadata change ("MFT change time") | FILETIME `u64` LE; **not** reachable by `SetFileTime`/PowerShell/.NET |
| **`$SI`** | Accessed (A) | value `0x28`+`0x18` | Last access | FILETIME `u64` LE; not updated on read by default (registry `RefsDisableLastAccessUpdate`=1) |
| **Non-resident `$SI`** | B/M/C/A | value `0x10`/`0x18`/`0x20`/`0x28` | Same four times for non-resident files | FILETIMEs sit at value+`0x10` (after the 16-byte ordinal + home-dir-backref header), **not** value+`0x28` |
| **USN `$J` record** | Timestamp | record `0x30` | Wall-clock time the operation was journalled | FILETIME `u64` LE; record at `OID 0x520` "Change Journal" → `$J` stream |
| **USN `$J` record** | Reason | record `0x38` | Which operation (bitmask) | `u32` LE; see reason codes below |
| **USN `$J` record** | USN | record `0x28` | Virtual byte offset of this record in the journal (the file's `$SI`+0x40 LastUsn points here) | `u64` LE; monotone, never reused; can far exceed the live `$J` stream size since `$J` is a sliding window |
| **USN `$J` record** | File ID / Parent ID | record `0x08` / `0x18` | 128-bit IDs (table OID ‖ entry index) | two `u128`; upper 8 = directory OID, lower 8 = entry ordinal |
| **MLog redo record** | Embedded `$SI` times | opcode-specific | FILETIMEs of the *operation being replayed* | FILETIME `u64` LE inside the `_SmsRedoRecord` value data (record+`0x38`+); **no dedicated header timestamp field** |
| **CHKP** | Virtual clock | CHKP `0x60` (header copy `0x10`) | Monotone transaction-sequence counter (NOT wall clock) | `u64` LE; higher = newer checkpoint; allocator clock at `0x68` ≤ virtual clock |
| **`$VOLUME_INFORMATION`** (`OID 0x500`, key 0x0520) | Volume creation | key value `0x90` | Volume format time — the hard lower bound | FILETIME `u64` LE; set at format, never rewritten. Modify time at `0xA0` (updated on mount) |

Two non-obvious properties trip up almost every first parser, and both deserve to be stated plainly:

1. **The MLog has no timestamp in its record headers.** The four-layer
[MLog](../structures/mlog.md) record (LogCore header → entry header → redo block →
`_SmsRedoRecord`) carries an LSN and a per-record checksum, not a wall clock. The *only* times in
the log are the **FILETIMEs of the file operation being logged**, embedded in the redo record's
value data at opcode-specific offsets (`InsertRow`/`0x01` carries B/M/A/C). These reflect the
*operation* time, not the log-write time, and only a workload-dependent majority of transactions
(roughly two-thirds to four-fifths in the images measured) carry any time at all —
system and allocator operations carry none. See the MLog page's "Timestamp Extraction" for the
per-opcode offsets.

2. **The CHKP virtual clock is an ordering, not a clock.** It is a monotone per-transaction counter
held in the [checkpoint](../structures/chkp.md) at `+0x60` (typical values ~20–30 on a freshly
formatted volume, ~50–100 after roughly a thousand file operations). It tells you the *relative
order* of metadata states and roughly how much activity a volume has seen; it does **not** map to a
wall-clock time. Use it for sequencing and for selecting the current vs. previous consistent
checkpoint, never for dating an event.

### USN reason codes worth recognizing on a timeline

The reason bitmask at USN record `+0x38` is what makes the journal an *event* log rather than a bag
of timestamps. A handful of codes carry most of the forensic weight:

| Reason | Hex | What it means on the timeline |
|--------|-----|-------------------------------|
| File create | `0x00000100` | File or directory creation — anchors the true creation time |
| Data overwrite / extend | `0x00000001` / `0x00000002` | Content was written |
| File delete | `0x00000200` | File deleted |
| Rename old / new name | `0x00001000` / `0x00002000` | The two halves of a rename |
| Basic info change | `0x00008000` | Timestamp or attribute edit — the timestomp signature |
| Reparse point change | `0x00100000` | Junction / symlink creation |
| Close | `0x80000000` | OR-ed onto the final reason for a handle |

## Building a super-timeline

A complete ReFS timeline is the union of:

- four `$SI` MACB rows per file, harvested from the directory-entry walk;
- one row per USN `$J` record — a wall-clock event log, but only when the journal is active;
- optionally the MLog-embedded operation times for the most-recent transactions not yet folded into
  a checkpoint;

anchored below by the `$VOLUME_INFORMATION+0x90` creation time and ordered, where wall clocks are
absent, by USN byte offset and CHKP virtual clock.

Each source contributes something the others cannot:

- **`$SI` is the current state only.** It is overwritten in place, so it shows the latest four times
  and nothing historical — and it is the one source a timestomp tool can trivially forge.
- **The USN journal is the append-only history.** It records the *operation itself* with its real
  wall-clock time at record `+0x30`, and because records are never rewritten in place it is the
  hard-to-forge anchor. The catch is that USN journaling is **not active by default** — it must be
  enabled with `fsutil usn createjournal` — so on many images the journal is simply absent and this
  anchor is unavailable.
- **The MLog can surface very recent operations** that have not yet been checkpointed and may not
  even be in the journal — but it is a circular buffer, so its reach is shallow and time-bounded.

In practice you join the three CSV exports (USN events, MLog times, per-file MACB) into one sortable
super-timeline and anchor it with the volume-creation time from the volume summary.

## Pitfalls that corrupt a ReFS timeline

- **Do not look for a `$FN` twin.** For a single-named file there is no second timestamp set on ReFS
  to cross-check `$SI` against — use the metadata-change time, the USN journal, and the volume bound
  instead. (A hard-linked file is the exception: each name carries its own `$SI` copy, so comparing
  the names' MACB *is* an intrinsic cross-check.)
- **Resident vs. non-resident offset shift.** Resident files carry the four FILETIMEs at
  `$SI` value+`0x28`; non-resident files carry them at value+`0x10` (after the 16-byte child-ordinal
  + home-dir-backref header). Parsing a non-resident value with the resident offset reads garbage 24
  bytes early.
- **Detect the version before parsing the `$SI` tail, not the times.** The `$SI` tail length differs
  by version (116 B on Win10 v3.4, 124 B on Win11 v3.14), but the four MACB FILETIMEs at `0x00`–`0x18`
  are version-invariant. Only the post-`0x50` tail moves.
- **`$SI+0x40` is a USN byte offset, not a timestamp.** It is the file's LastUsn — the virtual byte
  offset of its most recent `$UsnJrnl:$J` record — and `$SI+0x48` is the UsnJournalId. Neither is a
  FILETIME, and `$SI+0x30` is an unpopulated slot (it is *not* a USN). Do not plot any of them on a
  timeline.
- **Access time is usually stale.** ReFS does not update A on reads by default
  (`RefsDisableLastAccessUpdate`=1), so treat it as a weak signal.
- **The CHKP virtual clock is not a date.** Plotting it as a wall clock is wrong; it is a sequence
  counter. Use it only to order states that carry no wall clock.

## Cross-validating the sources

Corroborate the sources against each other; the inconsistency is the finding. There is a natural
hierarchy of strength, from "always available but circumstantial" to "immutable and authoritative":

1. **`$SI` vs. the volume bound — always available.** A file's `$SI` Created must be
   `≥ $VOLUME_INFORMATION+0x90` (format time). A creation time *before* the volume existed is
   impossible for a genuinely local file (`PRE_FORMAT`); a creation time *after* the volume's last
   metadata write is `FUTURE`. Both need only the image, but both also fire on legitimate
   creation-time-preserving copies (robocopy `/COPY:T`, restores) — so they flag an inconsistency,
   not proof.

2. **`$SI` internal consistency.** The metadata-change time `C` (`$SI+0x10`) is not reachable through
   the high-level `SetFileTime` / PowerShell / .NET APIs that common timestomp tools use. After such
   a stomp `C` is left at the real write time while B and M are back-dated, so `C >> max(B, M)`
   (`CHANGE_LATE`). This is a heuristic against common tooling only — a native-API
   (`NtSetInformationFile.ChangeTime`) or raw-disk stomp can set `C` too and leave no signal.

3. **`$SI` vs. the USN journal — authoritative when present.** The journal is immutable, so it is the
   strong anchor:
   - `$SI` Created vs. the file's `FILE_CREATE` (reason `0x100`) record — a mismatch is
     `USN_CREATE_MISMATCH`.
   - A **standalone** `BASIC_INFO_CHANGE` (reason `0x8000`, with **no** `FILE_CREATE` / `DATA_*`
     bits) is a deliberate basic-info/timestamp edit recorded at its real wall-clock time
     (`USN_BASIC_INFO_CHANGE`), while `$SI` shows the forged time.
   - The wall clocks at USN `+0x30` also let you re-order events that the CHKP clock can only rank.

4. **CHKP virtual clock for sequencing.** Where two metadata states or two checkpoint copies exist,
   the higher virtual clock (`CHKP+0x60`) is the newer one — use it to order states that carry no
   wall clock.

A verdict reaches **HIGH** confidence when the journal confirms a deliberate edit and an intrinsic
signal agrees, or when two independent intrinsic signals agree (`CHANGE_LATE` + `PRE_FORMAT`);
**MEDIUM** for one solid intrinsic signal with no journal; **LOW** for a weak signal alone. The full
signal/tier model and its validation live on the
[timestomp detection](timestomp_detection.md) page.

## Version and state differences

- **`$SI` tail length:** 116 B on Win10 v3.4 vs. 124 B on Win11 v3.14. The four MACB FILETIMEs at
  `0x00`–`0x18` are identical across all versions; only the post-`0x50` tail differs. A Win11 driver
  rejects a sub-124-byte `$SI` as corrupt, so version detection must precede tail parsing.
- **USN journal format:** ReFS always uses `USN_RECORD_V3` with 128-bit File IDs (major version 3,
  minor 0). Unlike NTFS there is no V2 record.
- **MLog redo opcodes carrying times:** the time-bearing opcodes (`InsertRow` `0x01`, `UpdateRow`
  `0x03`, `UpdateDataWithRoot` `0x04`) are stable across v3.4 and v3.14. The opcode *range* grows
  (v3.4 `0x00`–`0x1C`, v3.14 `0x00`–`0x2B`), but the time-bearing core is unchanged.
- **Volume creation time** is set at format and never rewritten — including across a v3.4→v3.14
  upgrade. The upgrade rewrites the *version* bytes at `$VOLUME_INFORMATION+0x80`–`0x83`, not the
  creation FILETIME at `+0x90`.

## Tooling

| Need | Command |
|------|---------|
| Per-file MACB + intrinsic timestomp flags | `forefst.py <image> ... --timestomp` (adds `TimestompFlags` / `timestomp_flags`) |
| Full cross-source timestomp verdict (adds USN) | `forefst.py <image> timestomp [--min HIGH] [--json] [--csv out.csv]` |
| USN event log (the history) | `forefst.py <image> usn [--csv] [--json] [--stats] [--info]` |
| MLog transaction times | `forefst.py <image> mlog --parse` / `--csv FILE` (seq, timestamp, action, path, oid) |

Combine the USN CSV, the MLog CSV, and the per-file MACB CSV to assemble a single sortable
super-timeline; anchor it with the volume-creation time from the `integrity` / volume summary.

## Cross-references

- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the four `$SI` MACB FILETIMEs and the non-timestamp `$SI+0x40` LastUsn / `$SI+0x48` UsnJournalId fields these reads come from
- [Timestomping detection](timestomp_detection.md) — the signal/tier model that consumes every source on this page
- [USN journal](../structures/usn_journal.md) — the `USN_RECORD_V3` layout, reason codes, and `$J` storage behind the event-log column
- [MLog transaction log](../structures/mlog.md) — the four-layer record structure and the embedded-timestamp extraction this page summarizes
- [CHKP checkpoint](../structures/chkp.md) — the virtual clock (`+0x60`) used for sequencing and current-vs-previous selection
- [$VOLUME_INFORMATION](../attributes/VOLUME_INFORMATION.md) / [volume info table](../structures/volume_info.md) — the `+0x90` creation FILETIME that floors the timeline
- [Directory entries](../structures/directory_entries.md) — where the type-0x10 `$SI` value lives in the tree

## Evidence

The five-source model is grounded in the driver (E2) and re-measured on the raw-disk corpus (RD).
The `$SI` MACB layout and the `$SI+0x40` LastUsn / `$SI+0x48` UsnJournalId reattribution are
disk-proven (the per-file→journal link was confirmed by matching every file's LastUsn to a `$J`
record that names it). The CHKP virtual clock is a monotone sequence counter, not a wall clock —
higher clock selects the newer of two validating checkpoint copies. The MLog has no header
timestamp; the only times are the operation FILETIMEs embedded in `_SmsRedoRecord` value data,
dispatched by `CmsLogRedoQueue::PerformRedo`, with the time-bearing opcodes (`0x01`/`0x03`/`0x04`)
stable across v3.4 and v3.14. The per-name `$SI` storage that makes a hard-linked file's names an
intrinsic cross-check is disk-proven: a name-scoped stomp of one name left the sibling name at the
true birth (FN_LINK_003 / E59). See [how this was verified](../methodology.md) to trace these to the
exact images and measurements in `analysis/`.
