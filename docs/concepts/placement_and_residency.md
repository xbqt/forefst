# Record placement and data residency

ReFS answers **two** questions about every file, and they are independent. Almost every mistake made about
ReFS storage — including several made by this project and corrected in its own errata — comes from treating
them as one.

| The question | The answer is called | Its values |
|---|---|---|
| **Where is the file's *record*?** | `RecordPlacement` | `embedded` · `split` |
| **Where are the file's *bytes*?** | `DataResidency` | `inline` · `extents` · `snapshot-shared` · `unallocated` |

A single word — `resident` — used to name both, which is why it names neither any more.

## The two questions, one picture

```
  RECORD PLACEMENT                          DATA RESIDENCY
  ────────────────                          ──────────────

  embedded                                  inline
  ┌─ directory B+-tree ─────────┐           ┌─ the record ────────────┐
  │ name row ─┬─ the record     │           │ $DATA ─┬─ length        │
  │           └─ …              │           │        └─ THE BYTES     │
  └─────────────────────────────┘           └─────────────────────────┘

  split                                     extents
  ┌─ directory B+-tree ─────────┐           ┌─ the record ────────────┐      ┌─ disk ───┐
  │ name row ── points to ──┐   │           │ $DATA ─┬─ length        │  ──▶ │ clusters │
  └─────────────────────────┼───┘           │        └─ an extent list│      └──────────┘
  ┌─ backing record (0x40) ◀┘   │           └─────────────────────────┘
  │ the record lives here       │           snapshot-shared → no allocation of its own;
  └─────────────────────────────┘             the bytes are still the snapshot's
                                            sparse → no allocation, no snapshot: never written
```

**The left column and the right column do not constrain each other.** A record embedded in its name row can
have its bytes out in extents; a record split into a backing can keep its bytes inline. Both happen on
ordinary volumes, in quantity.

## One file, through four states

The same file, as operations happen to it. The two column values are written beside each state — notice
that no operation changes both.

```
                                              RecordPlacement   DataResidency
  ┌────────────────────────────────────────┐
  │ 1. created, 600 bytes                  │      embedded    ·    inline
  │    record in the name row,             │
  │    bytes inside that record            │
  └───────────────┬────────────────────────┘
                  │  write past the format-3.11+ ceiling ── residency only
  ┌───────────────▼────────────────────────┐
  │ 2. grown to 60 KiB                     │      embedded    ·    extents
  │    record unmoved; the bytes are now   │                       ▲
  │    on disk, described by an extent list│                    changed
  └───────────────┬────────────────────────┘
                  │  moved to another directory          ── placement only
  ┌───────────────▼────────────────────────┐
  │ 3. moved                               │       split      ·    extents
  │    the record is split out into a      │        ▲
  │    backing record; NO data moved       │     changed
  └───────────────┬────────────────────────┘
                  │  snapshot taken, file not written    ── residency only
  ┌───────────────▼────────────────────────┐
  │ 4. snapshotted, untouched since        │       split      · snapshot-shared
  │    owns no allocation of its own;      │                       ▲
  │    the bytes are still the snapshot's  │                    changed
  └────────────────────────────────────────┘
```

The step-1→2 ceiling is the 2 KiB inline limit of **format 3.11 and later**; on format 3.10 and
earlier a file's main data starts at step 2 and never has a step 1. Truncating back to 0 bytes would **not**
return it to `inline`: that arrow runs one way.
Renaming it at any step changes neither value.

## What changes what

| Operation | `RecordPlacement` | `DataResidency` |
|---|---|---|
| Create a small file | `embedded` | `inline` (on format ≥ 3.11) |
| Grow it past the inline ceiling | unchanged | `inline` → `extents` |
| Truncate it back to 0 | unchanged | **stays `extents`** — the change runs one way only |
| **Move it to another directory** | `embedded` → **`split`** | **unchanged** |
| **Add a hard link** | `embedded` → **`split`** | **unchanged** |
| Rename in place | unchanged | unchanged |
| Take a snapshot, then read (not write) | unchanged | `extents` → `snapshot-shared` |
| Write to a snapshot-shared file | unchanged | `snapshot-shared` → `extents` |

The two rows in bold are the whole point: **a move or a hard link relocates the record and moves no data
at all.** Every driver examined has a `RefsConvertToNonResident` and none has a `ConvertToResident`, which
is why the truncate row does not go back.

*Evidence: `MD_PLAC_RA_001` (operation table, RD + E2), `MD_DATA_RA_015`, `E87`, `E82`, `E83`, `E88`.*

## Which residencies a format can produce

| Stream | format ≤ 3.10 | format ≥ 3.11 | Evidence |
|---|---|---|---|
| main `$DATA` | never `inline` | `inline` below 2 KiB, else `extents` | RD (corpus-wide; the boundary is **fixed at 2 KiB**, not cluster-relative — 1,900 B inline / 2,100 B extents on 4 KiB, 64 KiB and 4Kn alike) |
| named stream (ADS) | `inline` up to a hard 128 KiB cap | `inline` below 2 KiB, else `extents` | driver gate is format ≥ 3.11 (E2). Volumes measured: 3.14 only, on 4 KiB, 64 KiB **and** 4Kn — no image of 3.11–3.13 exists, so the lower bound comes from the driver, not from a measurement; a 131,073-byte ADS exists there, so the cap is not a 3.14 rule); **the ≤ 3.10 cap is E2 + vendor documentation, not yet witnessed on disk** |

The format version is the volume's, not the driver's: a v3.4 volume mounted by a v3.14 driver keeps v3.4
behaviour. The evidence column is deliberately per row — an upgrade of the second row is a lab result,
not an edit.

## Eight files, measured

Generated from the shipped sample volumes by
`analysis/tools/analysis_scripts/gen_residency_examples.py`, and re-checked by the gate, so these cannot
drift away from the tool.


<!-- BEGIN generated: worked examples -->
| File | Size | `RecordPlacement` | `DataResidency` | What it shows |
|---|---:|---|---|---|
| `WPSettings.dat` | 12 | `embedded` | `inline` | small, never moved — record in the name row, bytes in the record |
| `xbpt_large_149mb_alpha_610845.dat` | 156,237,824 | `embedded` | `extents` | **149 MB, never moved** — the record is still in the name row; placement says nothing about size |
| `xbpt_log_november_496320.csv` | 552,331 | `split` | `extents` | moved once — the record was split out, and the bytes were already in extents |
| `index_data_269514.bin` | 1,108 | `split` | `inline` | **hard-linked, and its bytes are inline** — a split record still carries its own `$DATA` (E82) |
| `hardlink_sync_683343.lnk` | 0 | `split` | `inline` | 0 bytes, hard-linked — the descriptor form decides, even with nothing to store (E88) |
| `test.txt` | 5 | `embedded` | `snapshot-shared` | unmodified since a snapshot — the bytes are the snapshot's, not this stream's (E83) |
| `lasttest.txt` | 201 | `embedded` | `snapshot-shared` | the same state at 201 bytes — size does not decide this one either |
| `WPSettings.dat` | 12 | `embedded` | `inline` | the same file on a second volume — the two axes are per-file, not per-volume |
<!-- END generated: worked examples -->


## How to check on your own image

```sh
forefst.py disk.raw files --csv -q            # RecordPlacement and DataResidency columns
forefst.py disk.raw details /path/to/file     # both axes for one file, with the record's own numbers
forefst.py disk.raw dataruns -v               # INLINE / EXTENT / SHARED / SPARSE, with record=… beside each
forefst.py disk.raw extract /path/to/file     # the bytes, whichever of the four states they are in
```

`extract` handles all four; you never need to know the state to recover the content.

## Five questions

**Is `split` a sign of tampering?** No. It means the file was moved or hard-linked — both ordinary.

**Does a big file always have `extents`?** On format ≥ 3.11 yes above 2 KiB; below it, no. On ≤ 3.10 main
data is *never* inline whatever the size.

**Can a hard-linked file have its bytes inline?** Yes — see `index_data_269514.bin` above. About one in five
split records keeps its data inline.

**`snapshot-shared` — where are the bytes?** In the snapshot's clusters. The live stream owns no allocation
until something writes to it.

**Is `IsResident` still there?** Yes, deprecated: it is `True` exactly when `DataResidency` is `inline`.
Prefer the two named columns.

## Cross-references

- [Record placement in the byte layout](resident_storage.md) — `key_flags`, the descriptor forms, the counts
- [Directory entries](../structures/directory_entries.md) · [`$DATA`](../attributes/DATA.md) ·
  [Extent descriptors](../structures/extent_descriptors.md)
- [Hard links](hard_links.md) · [Snapshots and versioning](snapshots_versioning.md) ·
  [NTFS comparison](ntfs_comparison.md)

## A snapshot changes what residency reports

Residency is not a function of size alone. Take a stream snapshot of a small file and leave the file
completely untouched, and its live stream stops reporting `inline` and starts reporting
`snapshot-shared` — because the stream now owns no allocation of its own; the bytes are the snapshot's.
Measured on format 3.14 with a **600-byte** file, far below the 2 KiB inline ceiling.

So `snapshot-shared` is not a state reserved for large, extent-backed files, and a file can move between
reported states without any write to it at all.

Related, and worth knowing before you rely on a snapshot: a file snapshotted while inline and then grown
past the inline ceiling was measured to retain **no snapshot record at all**.

## Evidence

That a snapshot alone moves an unmodified inline stream to `snapshot-shared` is **MD_SNAP_RA_009**; that the order of a rename and a cross-directory move leaves no distinguishable trace in the record is **FS_MOVE_RA_003**; that `SetEndOfFile` before any write does not force extent-backing is **MD_DATA_RA_027**. All three were measured on format 3.14 lab volumes against ground truth written on the volume itself.
