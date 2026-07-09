# Tool-to-Artifact Map

This page is the bridge between the question in your head and the byte layout that answers it. For each
forensic *goal* — recover deleted names, find the change journal, prove a timestamp was forged — it names
the `forefst.py` / `refsanalysis.py` invocation that surfaces the artifact and the doc page that documents
its on-disk shape. Use it to go from a question straight to a command, and from any tool output back to the
audited structure that justifies it. The audited claim behind every row is cited in the
[Evidence](#evidence) section at the bottom, keyed to the same goal.

## One parsing core, two front ends

Both tools share a single parsing core. `bootstrap()` opens the image, parses the
[VBR](../structures/vbr.md) / [SUPB](../structures/supb.md) / [CHKP](../structures/chkp.md), builds the
[Container Table](../structures/container_table.md) translator and the
[Object Table](../structures/object_table.md) map, then exposes every structure through `walk_bplus()` and
`obj_map[oid]`. That bootstrap is described step by step on the [Bootstrap Chain](bootstrap_chain.md) page,
and nothing in the bridge table below is reachable until it has run — every artifact is found by walking a
specific B+-tree from a known root or OID that bootstrap has already located.

The split between the two tools is about *shape of output*, not *what they can see*:

- `forefst.py` is the **batch lister** — one row per file, emitted as CSV, body-file, or JSON, plus
  volume summaries and version recovery. It is the timeline-friendly path: it sweeps the whole tree and
  hands you a table.
- `refsanalysis.py` is the **interactive inspector** — registered subcommands that dump and decode one
  structure at a time. It is the deep-dive path: point it at a single OID or table and it shows the raw row.

Because both read the *same* on-disk bytes through the *same* core, a value seen in a lister CSV can always
be re-derived with the matching inspector subcommand. That is the discipline behind the whole table: when a
timeline entry looks wrong, drop to the inspector on that object and read the bytes the lister summarized.

## Bridge table

| Goal | Tool command | Artifact | Doc page |
|------|--------------|----------|----------|
| Volume version / state | `refsanalysis.py IMG summary` · `forefst.py IMG summary` | CHKP volume-state flags (0x002 / 0x602 / 0x682 …), VBR version | [version detection](version_detection.md), [CHKP](../structures/chkp.md) |
| Native vs upgraded discrimination | `refsanalysis.py IMG chkp -vv` · `forefst.py IMG integrity` (Redundancy section) | CHKP bit 0x080; VBR 0x2A / 0x2C / 0x48; backup-boot version mismatch | [version detection](version_detection.md), [redundancy](redundancy.md) |
| Per-file MACB + attributes (timeline) | `forefst.py IMG files -o out.csv` · `forefst.py IMG files --body -o t.body` · `… --json` | Resident type-0x30 dir entry + child $SI (Created / Modified / Changed / Accessed at $SI 0x00–0x18) | [directory entries](../structures/directory_entries.md), [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) |
| Single object's full attribute dump | `forefst.py IMG details 0x705` · `refsanalysis.py IMG attributes` | All embedded sub-records of one OID (markers 0x80000001 / 0x80000002) | [attributes](attributes.md), [Object Table](../structures/object_table.md) |
| Search for a file by name | `forefst.py IMG search "*.docx"` · `… search rx --regex` | Type-0x30 filename keys (full long name; ReFS has no 8.3 entry) | [directory entries](../structures/directory_entries.md) |
| Timestomp detection | `forefst.py IMG timestomp` · `forefst.py IMG files --timestomp` (per-row `TimestompFlags`) | $SI MACB anomalies (parent-0x30 vs child-0x10), USN `BASIC_INFO_CHANGE` cross-check | [timestomp detection](timestomp_detection.md), [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) |
| File content extraction | `forefst.py IMG extract NAME > out` · `… extract "NAME:stream"` | Resident value (key flags 0x01) / non-resident type-0x40 extents; a small ADS (< 2 KB) is inline, a large ADS (≥ 2 KB) is extent-backed (E61) | [resident storage](resident_storage.md), [extent descriptors](../structures/extent_descriptors.md) |
| Data-extent (datarun) mapping | `forefst.py IMG dataruns -v` | 24-byte extent descriptors (VLCN @ 0x00, VCN @ 0x0C, runlen @ 0x14) | [extent descriptors](../structures/extent_descriptors.md), [virtual addressing](virtual_addressing.md) |
| Security descriptor / owner SID | `forefst.py IMG security --files` · `forefst.py IMG files` (OwnerSid column) | OID 0x530 security table; SecurityId at $SI 0x28 | [security descriptors](../structures/security_descriptors.md) |
| Reparse points (symlinks / junctions / WSL) | `forefst.py IMG reparse` · `… reparse --index` · `forefst.py IMG files` (ReparseTarget column) | $REPARSE_POINT data (schema 0x170 / 0x1C0); ReparseTag at $SI 0x54; OID 0x540 index | [reparse points](../structures/reparse_points.md), [$REPARSE_POINT](../attributes/REPARSE_POINT.md) |
| Extended attributes / WSL metadata | `refsanalysis.py IMG attributes --filter wsl` · `forefst.py IMG files --filter ea` | EA sub-records, LX* metadata, $EFS stream | [attributes](attributes.md), [$EA_INFORMATION](../attributes/EA_INFORMATION.md), [$EFS](../attributes/EFS.md) |
| Stream snapshots vs ADS | `forefst.py IMG snapshots -v` · `… snapshots --show/--extract` · `forefst.py IMG files` (HasAds column) | Type-0xB0 sub-records: snapshot vs ADS (inline) | [$SNAPSHOT](../attributes/SNAPSHOT.md), [copy-on-write](copy_on_write.md) |
| Deleted files — trash / orphan / chkp-diff | `forefst.py IMG files --deleted` · `forefst.py IMG deleted --scan-pages` | Trash Table (OID 0x0D), orphan MSB+ pages, two-CHKP diff | [Trash Table](../structures/trash_table.md), [deletion recovery](deletion_recovery.md) |
| Deleted directory names from node slack | `forefst.py IMG deleted --slack` · `… --extract DIR` | Stale type-0x30 rows in B+-tree node free region (offset slot freed, body persists) | [deletion recovery](deletion_recovery.md), [B+-tree node](../structures/btree_node.md) |
| CoW prior-version recovery (two images) | `forefst.py IMG files --cow-before EARLIER.raw` | Object-Table OIDs whose metadata-page LCN changed → old page at stale LCN | [copy-on-write](copy_on_write.md), [Object Table](../structures/object_table.md) |
| Durable log (MLog) transactions | `forefst.py IMG mlog --parse` · `… --csv` · `… --stats` | LogCore four-layer records; redo opcode at `_SmsRedoRecord + 0x04` | [MLog](../structures/mlog.md) |
| USN change journal | `forefst.py IMG usn --stats` · `… --csv` | OID 0x520 `$J` stream → USN_RECORD_V3 (128-bit FileIDs); $Max at schema 0x1F0 | [USN journal](../structures/usn_journal.md) |
| Super-timeline (MACB + USN + MLog) | `forefst.py IMG timeline` · `… --fast` · `… --source USN` | Merged $SI / USN / MLog events (USN and $SI join by OID, MLog by path) | [forensic analysis workflow](forensic_analysis_workflow.md) |
| Mount-session forensics (OID 0x30) | `refsanalysis.py IMG oid30` | Session Activity Table (OID 0x30; v3.10+ only) — mount-session history | [system OIDs](../structures/system_oids.md) |
| Metadata / checksum integrity | `forefst.py IMG integrity --checksums` · `… --fullchecksums` | Page-reference Merkle tree; CRC64 (cktype 2) / SHA-256 (cktype 4) | [checksum architecture](checksum_architecture.md), [Integrity State](../structures/integrity_state.md) |
| Raw metadata export ("dump the $MFT") | `forefst.py IMG export -o DIR` · `… --what btree,usn,mlog` | Hash-verified VBR / CHKP / SUPB / MLog / USN / B+-tree forest + manifest | [Object Table](../structures/object_table.md), [page header](../structures/page_header.md) |
| System-table inspection | `refsanalysis.py IMG schema` · `… objects` · `… containers -v` · `… parentchild` | Schema (roots 3 / 9), Object (0 / 5), Container (7 / 8), Parent-Child (root 4) | [Schema Table](../structures/schema_table.md), [system OIDs](../structures/system_oids.md), [Parent-Child Table](../structures/parent_child_table.md) |
| Boot-sector read / repair | `refsanalysis.py IMG boot -vv` · `… bootedit repair --dry-run` | VBR fields + ROR1+ADD self-checksum at 0x16 | [VBR](../structures/vbr.md) |

## Traps the table is there to prevent

The map exists because the obvious NTFS-trained reading of several of these artifacts is wrong on ReFS, and
the wrong reading produces confident-looking false findings. A few are worth stating outright:

- **`$SI + 0x70` is not a hard-link counter.** It is a resident-layout field that is always 0 or 1, never
  greater, even on a volume that genuinely has hard links. Real hard links are non-resident and are counted
  by resolving each name to its shared stream record, not by reading this field — see the
  [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) page and
  [copy-on-write](copy_on_write.md) for the link mechanism.
- **For a single-named file, the NTFS `$SI`-vs-`$FILE_NAME` timestomp cross-check has no ReFS equivalent** — ReFS
  stores no `$FILE_NAME` and no short name. But a **hard-linked** file *does* have a ReFS-only analogue: each name is
  a separate type-0x30 row with its own MACB, so a name-scoped timestomp leaves the sibling names at the true birth
  (`FN_LINK_003`; the `HARDLINK_MACB_MISMATCH` signal). For single-named files,
  [timestomp detection](timestomp_detection.md) instead compares the parent's type-0x30 inline timestamps
  against the child's type-0x10 $SI and cross-checks the USN `BASIC_INFO_CHANGE` reason code. Looking for a
  `$FILE_NAME` that does not exist is the classic ReFS mis-read.

## Operational notes

A handful of behaviors decide whether a command returns the artifact you expect:

- **The lister populates the SID / owner / ADS / reparse / snapshot columns in every CSV.** The inspector
  subcommands (`security`, `reparse`, `snapshots`) decode the same artifacts in depth, so the CSV columns and
  the inspectors agree; use an inspector for the full descriptor / target detail behind a column.
- **Deleted-data coverage is layered, not single-shot.** The trash / orphan / checkpoint-diff path
  (`--deleted`) recovers objects that are *referenced but unlinked*. Node-slack recovery (`deleted --slack`)
  recovers *names whose offset slot was freed but whose row body still persists* in a B+-tree node's free
  region — a class the live-tree iterators of both tools otherwise skip entirely. CoW prior-version recovery
  (`--cow-before`) needs a *second, earlier* image (or a dirty volume): after a clean unmount both
  checkpoints point at the same roots, so a single clean image yields no prior whole-tree state. The
  [deletion recovery](deletion_recovery.md) and [copy-on-write](copy_on_write.md) pages explain why each
  layer reaches a different population.
- **Integrity has a fast mode and a full mode.** `integrity --checksums` verifies only the root tables;
  only `--fullchecksums` walks every object B+-tree for a complete tamper check. Exit code 2 signals any
  failure, which makes the full mode scriptable for triage. The [checksum architecture](checksum_architecture.md)
  page documents the page-reference Merkle tree both modes verify.

Every command above accepts `--partition-start OFFSET` to override GPT detection. `forefst.py` adds
`--json` / `--jsonl` (and `--body`) for structured output and `--depth N` to bound recursion, and its forensic
subcommands take `--csv FILE` to export. `refsanalysis.py` adds `--json` on `summary`/`details` and the
`-v`/`-vv`/`--verify`/`--raw`/`-H` verbosity flags on the structure commands (each command's row shows which
it accepts). `refsanalysis.py --list` prints the full subcommand set, and `refsanalysis.py IMG all` sweeps
every structure tool in sequence.

## Cross-references

- [forefst.py](../tools/forefst.md) — the batch lister and the shared parsing library both tools build on
- [refsanalysis.py](../tools/refsanalysis.md) — the interactive inspector with one subcommand per structure
- [Bootstrap Chain](bootstrap_chain.md) — the common initialization that must run before any artifact here is reachable
- [Forensic Analysis Workflow](forensic_analysis_workflow.md) — the end-to-end methodology that sequences these commands into a case
- [Virtual Addressing](virtual_addressing.md) — why a cluster number in any artifact above is virtual and must be translated first

## Evidence

Each goal in the bridge table is backed by an audited claim in the master reference (`structure_reference.md`)
and the findings register. Grades are E1 (string), E2 (decompiled driver), E3 (inference), and RD (raw-disk
measured); the per-goal backing is:

- **Volume version / state** — FS_CHKP_RA_001, FS_CHKP_RA_009, FS_CHKP_RA_003. The observed composite CHKP state values
  (0x002 / 0x602 / 0x682 …) and the VBR version are RD-confirmed.
- **Native vs upgraded** — FS_CHKP_RA_001, FS_CHKP_RA_003, FS_VBR_RA_013. CHKP bit 0x080 plus the format-time VBR fields
  0x2A / 0x2C / 0x48 (never rewritten on upgrade) discriminate native from upgraded.
- **Per-file MACB + attributes** — MD_SI_RA_002, MD_SI_RA_003, MD_DATA_RA_005, MD_DISK_RA_003, MD_SI_RA_015. The four $SI timestamps sit at 0x00 / 0x08 /
  0x10 / 0x18.
- **Single-object attribute dump** — FS_SNAP_RA_001. Embedded sub-records use markers
  0x80000001 (single-instance) and 0x80000002 (multi-instance).
- **Search by name** — MD_TS_RA_005, MD_UNSUP_RA_001. ReFS has no 8.3 entry, so the type-0x30 key holds the full name.
- **Timestomp detection** — MD_TS_RA_005, MD_UNSUP_RA_001, FN_LINK_003. No NTFS `$FILE_NAME` cross-check for a
  single-named file (the analog is parent-0x30 vs child-0x10); for a **hard-linked** file, compare the per-name MACB
  across the file's names — a name-scoped stomp leaves siblings at the true birth (the `HARDLINK_MACB_MISMATCH` signal).
- **File content extraction** — MD_SNAP_RA_005, MD_SNAP_RA_006, MD_SNAP_RA_007. Resident value (key flags 0x01) vs
  non-resident type-0x40 extents; a small ADS (< 2 KB) is inline, a large ADS (≥ 2 KB) is extent-backed (E61).
- **Data-extent mapping** — MD_DATA_RA_001, MD_SNAP_RA_003, CT_DRNT_RA_001, CT_DRNT_RA_002. The 24-byte extent entry holds VLCN @ 0x00,
  file VCN @ 0x0C, run length @ 0x14; extents may be stored out of file order (CT_DRNT_RA_002).
- **Security descriptor / owner SID** — FS_SECD_RA_002, FS_SECD_RA_001, MD_SECT_001. SecurityId at $SI 0x28 resolves directly
  in OID 0x530.
- **Reparse points** — FS_SCHM_RA_008, FS_SECD_RA_003, FS_SCHM_RA_005, FS_SCHM_RA_010. $REPARSE_POINT schema 0x170 / 0x1C0; ReparseTag at
  $SI 0x54; OID 0x540 is the reparse index.
- **Extended attributes / WSL** — MD_ATTR_011. EA sub-records, LX* metadata, and the $EFS stream.
- **Stream snapshots vs ADS** — MD_SNAP_RA_005, MD_SNAP_RA_006, MD_SNAP_RA_007, MD_DISK_RA_004, MD_SNAP_RA_002, MD_SNAP_RA_003, CT_DRNT_RA_001, GN_SNAP_SA_001 (CoW prior-content recovery). Type-0xB0
  sub-records carry both snapshots and named data streams.
- **Deleted files (trash / orphan / chkp-diff)** — FS_OTBL_RA_003, FS_SCHM_RA_001, FS_DEL_RA_001, GN_PAGE_RA_002, FS_DEL_RA_004.
- **Deleted names from node slack** — FS_DEL_RA_003, FS_DEL_RA_005 (Method 5).
- **CoW prior-version recovery** — GN_ARCH_002, MD_SNAP_RA_002, MD_SNAP_RA_003, CT_DRNT_RA_001, GN_SNAP_SA_001. Requires a second/earlier image or a dirty
  volume — after clean unmount both checkpoints reference the same roots.
- **Durable log (MLog)** — AP_LGFL_RA_002, AP_LGTB_004, AP_LGFL_001. The redo opcode is at `_SmsRedoRecord + 0x04`.
- **USN change journal** — MD_USN_RA_004, FS_SCHM_RA_007. USN_RECORD_V3 with 128-bit File IDs; $Max metadata is the
  schema-0x1F0 attribute (v3.14+ schema entry) on the Change Journal file under OID 0x520.
- **Super-timeline** — MD_SI_RA_002, MD_SI_RA_003, MD_DATA_RA_005, MD_DISK_RA_003, MD_SI_RA_015, AP_LGFL_001.
- **Mount-session forensics** — FS_OTBL_RA_001. The Session Activity Table (OID 0x30) is present from v3.10+
  even when heat tracking is off.
- **Metadata / checksum integrity** — GN_ARCH_004, GN_PREF_001, FS_CHKP_RA_001. CRC64 is checksum-type 2,
  SHA-256 is type 4.
- **Raw metadata export** — GN_PAGE_001, GN_ARCH_005, GN_PAGE_007.
- **System-table inspection** — FS_CHKP_009, FS_CHKP_014, FS_CHKP_012, FS_CHKP_018, FS_CHKP_016, FS_CHKP_017, FS_UPCS_001, FS_PCTB_RA_001, FS_PCHL_001, CT_INTS_001, CT_CNTX_001, FS_OTBL_RA_003. Schema roots 3 / 9, Object roots 0 / 5,
  Container roots 7 / 8, Parent-Child root 4.
- **Boot-sector read / repair** — FS_VBR_RA_013. The VBR carries a ROR1+ADD self-checksum at 0x16.

The `$SI + 0x70`-is-not-a-counter and no-8.3-short-name traps are findings FN_LINK_002 and MD_TS_RA_005, MD_UNSUP_RA_001.
See [how this was verified](../methodology.md) to trace any row to the exact images and measurements.
