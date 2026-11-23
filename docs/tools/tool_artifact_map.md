# Tool-to-Artifact Map

This page maps each forensic goal to the command that finds its artifact and to the page that documents the
artifact's byte layout.

For each forensic *goal* — recover deleted names, find the change journal, test whether a timestamp was forged — it
names the `forefst.py` / `refsanalysis.py` invocation that surfaces the artifact and the doc page that documents its
on-disk shape. Use it to go from a question straight to a command, and from any tool output back to the structure
that justifies it.

The claim behind every row is cited in the [Evidence](#evidence) section at the bottom, keyed to the same goal.

## One parsing core, two front ends

Both tools share a single parsing core. `bootstrap()` opens the image, parses the
[VBR](../structures/vbr.md) / [SUPB](../structures/supb.md) / [CHKP](../structures/chkp.md), builds the
[Container Table](../structures/container_table.md) translator and the
[Object Table](../structures/object_table.md) map, then exposes every structure through `walk_bplus()` and
`obj_map[oid]`. That bootstrap is described step by step on the [Bootstrap Chain](../concepts/bootstrap_chain.md) page,
and nothing in the bridge table below is reachable until it has run — every artifact is found by walking a
specific B+-tree from a known root or OID that bootstrap has already located.

The two tools differ in the *form of their output*, not in *what they can read*:

- `forefst.py` is the **batch lister** — one row per file, emitted as CSV, body-file, or JSON, plus
  volume summaries and version recovery. It suits timelines: it walks the whole tree and outputs a
  table.
- `refsanalysis.py` is the **interactive inspector** — registered subcommands that dump and decode one
  structure at a time. It is for detailed inspection: given a single OID or table, it shows the raw row.

Because both read the *same* on-disk bytes through the *same* core, a value seen in a lister CSV can always
be re-derived with the matching inspector subcommand. So when a
timeline entry looks wrong, run the inspector on that object and read the bytes the lister summarized.

## Bridge table

| Goal | Tool command | Artifact | Doc page |
|------|--------------|----------|----------|
| Volume version / state | `refsanalysis.py IMG summary` · `forefst.py IMG summary` | CHKP volume-state flags (0x002 / 0x602 / 0x682 …), VBR version | [version detection](../concepts/version_detection.md), [CHKP](../structures/chkp.md) |
| Native vs upgraded discrimination | `refsanalysis.py IMG chkp -vv` · `forefst.py IMG integrity` (Redundancy section) | CHKP bit 0x080; VBR 0x2A / 0x2C / 0x48; backup-boot version mismatch | [version detection](../concepts/version_detection.md), [redundancy](../concepts/redundancy.md) |
| Per-file MACB + attributes (timeline) | `forefst.py IMG files --csv out.csv` · `forefst.py IMG files --body t.body` · `… --json` | The file's type-0x30 name row: the `$SI` at value+0x28 when the record is embedded, a cached copy at value+0x10 when it is split (Created / Modified / Changed / Accessed at `$SI` 0x00–0x18) | [directory entries](../structures/directory_entries.md), [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) |
| Single object's full attribute dump | `forefst.py IMG details /path` · `… details 0x705` · `refsanalysis.py IMG attributes` | All embedded sub-records of one file or directory (markers 0x80000001 / 0x80000002) | [attributes](../concepts/attributes.md), [Object Table](../structures/object_table.md) |
| Search for a file by name | `forefst.py IMG search "*.docx"` · `… search rx --regex` | Type-0x30 filename keys (full long name; ReFS has no 8.3 entry) | [directory entries](../structures/directory_entries.md) |
| Timestomp detection | `forefst.py IMG timestomp` | `$SI` MACB anomalies (the change time against Created / Modified, Created against the volume's creation), hard-link names, USN `BASIC_INFO_CHANGE` / `FILE_CREATE` cross-check | [timestomp detection](../concepts/timestomp_detection.md), [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) |
| File content extraction | `forefst.py IMG extract NAME > out` · `… extract "NAME:stream"` | The `$DATA` value: inline bytes, or its extent map (whatever the record's placement); named streams: see [Evidence](#evidence) | [record placement and data residency](../concepts/placement_and_residency.md), [extent records](../structures/extent_descriptors.md) |
| Data-extent (datarun) mapping | `forefst.py IMG dataruns -v` | 24-byte extent entries (VLCN @ 0x00, VCN @ 0x0C, runlen @ 0x14), the leaf rows of the extent node inside the `$DATA` value | [extent records](../structures/extent_descriptors.md), [virtual addressing](../concepts/virtual_addressing.md) |
| Security descriptor / owner SID | `forefst.py IMG security --files` · `forefst.py IMG files` (OwnerSid column) | OID 0x530 security table; SecurityId at $SI 0x28 | [security descriptors](../structures/security_descriptors.md) |
| Reparse points (symlinks / junctions / WSL) | `forefst.py IMG reparse` · `… reparse --index` · `forefst.py IMG files` (ReparseTarget column) | $REPARSE_POINT data (type 0xC0); ReparseTag at $SI 0x54; OID 0x540 index | [reparse points](../structures/reparse_points.md), [$REPARSE_POINT](../attributes/REPARSE_POINT.md) |
| Extended attributes / WSL metadata | `refsanalysis.py IMG attributes --filter wsl` · `forefst.py IMG files --filter ea` | EA sub-records, LX* metadata, $EFS stream | [attributes](../concepts/attributes.md), [$EA_INFORMATION](../attributes/EA_INFORMATION.md), [$EFS](../attributes/EFS.md) |
| Stream snapshots vs ADS | `forefst.py IMG snapshots -v` · `… snapshots --show/--extract` · `forefst.py IMG files` (HasADS column) | Type-0xB0 sub-records: a stream snapshot, or a named stream (`$NAMED_DATA`) | [$SNAPSHOT](../attributes/SNAPSHOT.md), [copy-on-write](../concepts/copy_on_write.md) |
| Deleted files — trash / diff / slack | `forefst.py IMG deleted` · `forefst.py IMG deleted --full` | Trash Table (OID 0x0D), two-CHKP diff, B+-tree node slack (live pages; `--full` adds a whole-volume orphan-page sweep) | [Trash Table](../structures/trash_table.md), [deletion recovery](../concepts/deletion_recovery.md) |
| Deleted names from node slack | `forefst.py IMG deleted` · `forefst.py IMG export deleted DIR` | Stale type-0x30 rows in B+-tree node free region (offset slot freed, body persists) | [deletion recovery](../concepts/deletion_recovery.md), [B+-tree node](../structures/btree_node.md) |
| Compare two images of one volume | `forefst.py IMG files --cow-before EARLIER.raw` | One row per object created, removed or changed between the two images (the volume GUID is checked), with the fields that differ | [copy-on-write](../concepts/copy_on_write.md), [Object Table](../structures/object_table.md) |
| Durable log (MLog) log payloads | `forefst.py IMG mlog --parse` · `… --csv` · `… --stats` | LogCore four-layer records; redo opcode at `_SmsRedoRecord + 0x04` | [MLog](../structures/mlog.md) |
| USN change journal | `forefst.py IMG usn --stats` · `… --csv` | OID 0x520 `$J` stream → USN_RECORD_V3 (128-bit FileIDs); $Max in the type-0xF0 attribute | [USN journal](../structures/usn_journal.md) |
| Super-timeline (MACB + USN + MLog) | `forefst.py IMG timeline` · `… --fast` · `… --source USN` | $SI / USN / MLog events merged by time, not joined ($SI and USN rows carry the home directory's OID, MLog rows the directory changed) | [artifact timeline](../concepts/artifact_timeline.md), [forensic analysis workflow](../concepts/forensic_analysis_workflow.md) |
| When the volume had I/O (OID 0x30) | `refsanalysis.py IMG oid30` | Heat engine table (OID 0x30; from v3.10) — I/O metrics in 10-minute generations | [system OIDs](../structures/system_oids.md#heat-engine-table-oid-0x30) |
| Metadata / checksum integrity | `forefst.py IMG integrity --checksums` · `… --fullchecksums` | Page-reference Merkle tree; CRC64 (cktype 2) / SHA-256 (cktype 4) | [checksum architecture](../concepts/checksum_architecture.md), [Integrity State](../structures/integrity_state.md) |
| Raw metadata export ("dump the $MFT") | `forefst.py IMG export -o DIR` · `… --what btree,usn,mlog` | SHA-256-sealed VBR / CHKP / SUPB / MLog / USN / B+-tree forest + manifest | [Object Table](../structures/object_table.md), [page header](../structures/page_header.md) |
| System-table inspection | `refsanalysis.py IMG schema` · `… objects` · `… containers -v` · `… parentchild` | Schema (roots 3 / 9), Object (0 / 5), Container (7 / 8), Parent-Child (root 4) | [Schema Table](../structures/schema_table.md), [system OIDs](../structures/system_oids.md), [Parent-Child Table](../structures/parent_child_table.md) |
| Boot-sector read / repair | `refsanalysis.py IMG boot -vv` · `… bootedit repair --dry-run` | VBR fields + ROR1+ADD self-checksum at 0x16 | [VBR](../structures/vbr.md) |

## Two NTFS readings that are wrong on ReFS

The map exists because the obvious NTFS-trained reading of several of these artifacts is wrong on ReFS, and the
wrong reading produces false findings that look reliable. Two of them:

- **Read `$SI + 0x70` from the file's record, not from a name.** It is the link count as the driver last
  wrote it: 1 in a record embedded in its name row, the number of names in a hard-linked file's backing
  record (a name row of a hard-linked file is only a pointer to it). Which names belong together is found
  by resolving each name to that backing record — see the
  [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) and [Hard Links](../concepts/hard_links.md) pages.
- **For a single-named file, the NTFS `$SI`-vs-`$FILE_NAME` timestomp cross-check has no ReFS equivalent** — ReFS
  stores no `$FILE_NAME` and no short name. Looking for a `$FILE_NAME` that does not exist is the classic ReFS
  mis-read.
  - A **hard-linked** file *does* have an analogue: each name's type-0x30 row carries a cached copy of the file's
    MACB, and those copies *can* diverge (the `HARDLINK_MACB_MISMATCH` signal). A divergence of the names' Created
    times is evidence (their Changed times diverge routinely).
  - Agreement proves nothing: the file's own record takes the new time for every name at once, and each name's row
    is a cache refreshed only when the file is opened through that name, so a read through a stale name erases the
    difference.
  - For single-named files, [timestomp detection](../concepts/timestomp_detection.md) instead compares the `$SI` times with each
    other (the change time against Created and Modified) and with the volume's creation time, and cross-checks the
    USN journal (`BASIC_INFO_CHANGE`, `FILE_CREATE`).

## Operational notes

Three behaviors decide whether a command returns the artifact you expect:

- **The lister populates the SID / owner / ADS / reparse / snapshot columns in every CSV.** The inspector
  subcommands (`security`, `reparse`, `snapshots`) decode the same artifacts in depth, so the CSV columns and
  the inspectors agree; use an inspector for the full descriptor / target detail behind a column.
- **Deleted-data recovery has several layers.** The `deleted` command's trash / checkpoint-diff path
  recovers objects that are *referenced but unlinked*.

  Node-slack recovery (the default `deleted` scan, extended by `deleted --full`) recovers *names whose offset slot
  was freed but whose row body still persists* in a B+-tree node's free region — a class the live-tree iterators of
  both tools otherwise skip entirely.

  A comparison of whole-tree states (`--cow-before`) needs a *second, earlier* image: after a clean unmount the two
  checkpoints usually decode to the same root list, so a single clean image usually yields no prior whole-tree
  state. The [deletion recovery](../concepts/deletion_recovery.md) and [copy-on-write](../concepts/copy_on_write.md) pages explain why each
  layer reaches a different population.
- **Integrity has a fast mode and a full mode.** `integrity` alone gives a fast structural verdict;
  `integrity --checksums` verifies only the root tables; only `--fullchecksums` walks every object B+-tree for a
  complete tamper check. Exit code 2 signals any
  failure, which makes the full mode scriptable for triage. The [checksum architecture](../concepts/checksum_architecture.md)
  page documents the page-reference Merkle tree both modes verify.

Every command above accepts `--partition-start OFFSET` to override GPT detection. `forefst.py` adds
`--json` / `--jsonl` (and `--body`) for structured output and `--depth N` to bound recursion, and its forensic
subcommands take `--csv FILE` to export. `refsanalysis.py` adds `--json` on `summary`/`details` and the
`-v`/`-vv`/`--verify`/`--raw`/`-H` verbosity flags on the structure commands (each command's row shows which
it accepts). `refsanalysis.py --list` prints the full subcommand set, and `refsanalysis.py IMG all` runs the main
structure tools in sequence (summary, boot, supb, chkp, schema, objects, parentchild, containers, files).

## Cross-references

- [forefst.py](forefst.md) — the batch lister and the shared parsing library both tools build on
- [refsanalysis.py](refsanalysis.md) — the interactive inspector with one subcommand per structure
- [Bootstrap Chain](../concepts/bootstrap_chain.md) — the common initialization that must run before any artifact here is reachable
- [Forensic Analysis Workflow](../concepts/forensic_analysis_workflow.md) — the end-to-end methodology that sequences these commands into a case
- [Virtual Addressing](../concepts/virtual_addressing.md) — why a cluster number in any artifact above is virtual and must be translated first

## Evidence

Each goal in the bridge table rests on registered findings in the master reference (`structure_reference.md`)
and the claim register; the [knowledge map](../KNOWLEDGE_MAP.md) lists them for this page. Grades are E1 (string), E2
(decompiled driver), E3 (inference), and RD (raw-disk measured); what each goal rests on:

- **Volume version / state** — the observed composite CHKP state values (0x002 / 0x602 / 0x682 …) and the VBR
  version are confirmed on disk.
- **Native vs upgraded** — CHKP bit 0x080 plus the VBR fields set at format (0x2A, 0x48, and the volume flags' bits
  0x20 / 0x40 at 0x2C, which were the same before and after the upgrades measured) discriminate native from upgraded.
- **Per-file MACB + attributes** — the four $SI timestamps sit at 0x00 / 0x08 / 0x10 / 0x18; a split name row
  caches them at value+0x10 after its 16-byte ordinal and home backref.
- **Single-object attribute dump** — embedded sub-records use markers 0x80000001 (single-instance) and 0x80000002
  (multi-instance).
- **Search by name** — ReFS has no 8.3 entry, so the type-0x30 key holds the full name.
- **Timestomp detection** — no NTFS `$FILE_NAME` cross-check for a single-named file (the `$SI`-only analogue is
  the change time against Created / Modified); for a **hard-linked** file, compare the names' Created times — a
  divergence is evidence (the `HARDLINK_MACB_MISMATCH` signal), agreement is not; their Changed times diverge
  routinely.
- **File content extraction** — the data's residency is the `$DATA` descriptor's form (inline or extents), not the
  record's placement (`key_flags` 0x01 embedded / 0x02 split into a type-0x40 backing); on format 3.11+ a named
  stream below 2 KiB is inline unless its writer pre-allocated, and one of 2 KiB or more is extent-backed.
- **Data-extent mapping** — the 24-byte extent entry holds VLCN @ 0x00, file VCN @ 0x0C, run length @ 0x14; extents
  may be stored out of file order.
- **Security descriptor / owner SID** — SecurityId at $SI 0x28 resolves directly in OID 0x530.
- **Reparse points** — $REPARSE_POINT (type 0xC0); ReparseTag at $SI 0x54; OID 0x540 is the reparse index.
- **Extended attributes / WSL** — EA sub-records, LX* metadata, and the $EFS stream.
- **Stream snapshots vs ADS** — type-0xB0 sub-records carry both snapshots and named data streams; the recovery of
  a snapshot's prior content is a registered finding too.
- **Deleted files (trash / orphan / chkp-diff)** — the Trash Table (OID 0xD, schema 0xe0d0), the deletion flow, the
  page header's table OID, and the recovery-efficiency order (the Trash Table, then the checkpoint differential, then
  the orphan scan).
- **Deleted names from node slack** — a removed row leaves its data in the page's slack (Method 5 of
  [deletion recovery](../concepts/deletion_recovery.md)).
- **CoW prior-version recovery** — requires a second/earlier image or a dirty volume — after a clean unmount the two
  checkpoints usually reference the same roots.
- **Durable log (MLog)** — the redo opcode is at `_SmsRedoRecord + 0x04`.
- **USN change journal** — USN_RECORD_V3 with 128-bit File IDs; $Max metadata is the type-0xF0 attribute on the Change
  Journal file under OID 0x520.
- **Super-timeline** — the per-file MACB timestamps above, plus the MLog's records.
- **When the volume had I/O** — the heat engine table (OID 0x30), from v3.10, keeps the heat engine's I/O metrics in
  10-minute generations; the one volume measured that was formatted with heat gathering disabled holds them too.
- **Metadata / checksum integrity** — CRC64 is checksum-type 2, SHA-256 is type 4.
- **Raw metadata export** — the page header: the signature at 0x00, the table identifier at 0x40-0x50.
- **System-table inspection** — schema roots 3 / 9, Object roots 0 / 5, Container roots 7 / 8, Parent-Child root 4.
- **Boot-sector read / repair** — the VBR carries a ROR1+ADD self-checksum at 0x16.

The read-`$SI + 0x70`-from-the-file's-record and no-8.3-short-name traps are registered findings too.
See [how this was verified](../methodology.md) to trace any row to the exact images and measurements.

<!-- findings: AP_LGFL_001, AP_LGFL_RA_002, AP_LGTB_004, CT_CNTX_001, CT_DRNT_RA_001, CT_DRNT_RA_002,
               CT_INTS_001, FN_LINK_002, FN_LINK_003, FS_CHKP_009, FS_CHKP_012, FS_CHKP_014, FS_CHKP_016,
               FS_CHKP_017, FS_CHKP_018, FS_CHKP_RA_001, FS_CHKP_RA_003, FS_CHKP_RA_009, FS_DEL_RA_001,
               FS_DEL_RA_003, FS_DEL_RA_004, FS_DEL_RA_005, FS_OTBL_RA_001, FS_OTBL_RA_003, FS_PCHL_001,
               FS_PCTB_RA_001, FS_SCHM_RA_001, FS_SCHM_RA_005, FS_SCHM_RA_007, FS_SCHM_RA_008,
               FS_SCHM_RA_010, FS_SECD_RA_001, FS_SECD_RA_002, FS_SECD_RA_003, FS_SNAP_RA_001, FS_UPCS_001,
               FS_VBR_RA_013, GN_ARCH_002, GN_ARCH_004, GN_ARCH_005, GN_PAGE_001, GN_PAGE_007,
               GN_PAGE_RA_002, GN_PREF_001, GN_SNAP_SA_001, MD_ATTR_011, MD_DATA_RA_001, MD_DATA_RA_005,
               MD_DISK_RA_003, MD_DISK_RA_004, MD_SECT_001, MD_SI_RA_002, MD_SI_RA_003, MD_SI_RA_015,
               MD_SNAP_RA_002, MD_SNAP_RA_003, MD_SNAP_RA_005, MD_SNAP_RA_006, MD_SNAP_RA_007, MD_TS_RA_005,
               MD_UNSUP_RA_001, MD_USN_RA_004
     errata: E61 -->
