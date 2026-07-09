# Changelog

## v3.6.0 — 2026-07-04 (first-audit enhancements · F5 residency fix · F6 per-name-MACB timestomp · `recyclebin`)

**New forensic capabilities from the first-audit review, plus two disk-proven findings.**

- **`recyclebin` subcommand (F8).** Decodes `$RECYCLE.BIN` `$I` metadata (formats 1 & 2) → original path, deletion
  time, size, and `$R` payload presence. Confirmed on-disk (3 Explorer-deleted files).
- **`files` CSV 33 → 38 columns.** Added `HardLinkNames` (Q5), `FileId` + `HomeOid` (Q2, join keys reconstructing the
  USN 128-bit FileID), `IsSparse` (F5, `FILE_ATTRIBUTE_SPARSE_FILE`), `InternalFlags` (Q3, e.g. DeleteDisposition) —
  appended before `RefsVersion`; matching JSON keys. `--full-path-column` appends a `FullPath` column.
- **`extract` now recovers resident files (Q7).** Writes a resident file's inline `$DATA` bytes (previously refused).
- **`timestomp` HARDLINK_MACB_MISMATCH (F6).** ReFS stores `$SI` **per hard-link name**, not per-inode — a
  name-scoped timestomp leaves sibling names at the true birth. Journal-independent; flags only the back-dated name.
  Reference: errata E59, finding FN_LINK_003.
- **`is_resident` bug fixed (F5).** A large non-resident file whose type-0x30 value carries an inline `0x10028`
  extent-list (`disk_alloc>0` on the current stream) was mislabeled resident; corrected (validated corpus-wide).
- **`deleted --slack` (Q6)** shows the directory each recovered row was deleted **from** (owning-table OID → path).
- Smaller parities: volume serial in `fastsummary`, `Modified` column in `search`, bodyfile `(deleted)` suffix +
  file_id inode (Q10, F11), Translator-shift comment (Q9).

## v3.5.0 — 2026-06-30 (CLI restructured to subcommands · forensic suite unified in forefst · hand-written help)

**`forefst.py` is now the unified forensic tool and `refsanalysis.py` the slim structure/lab tool.**

- **CLI restructure (breaking).** `forefst.py` moved from flat command-flags to a subcommand model:
  `forefst.py <image> <subcommand> [options]`. The old `--summary` / `--summary-plus` / `--fastsummary` /
  `--fastsummary-plus` / `--oid` / `--search` flags are removed. `summary` and `fastsummary` are now
  **extended-by-default**; object/file inspection is the `details` subcommand (`/path` | `0xOID` |
  `--path` | `--oid`); name search is the `search` subcommand. A version banner notes when a volume is
  &lt;3.14 (some enriched fields may be incomplete).
- **Forensic suite unified in forefst.** The twelve file-level forensic commands — `usn`, `mlog`,
  `timeline`, `timestomp`, `extract`, `security`, `reparse`, `deleted`, `snapshots`, `integrity`,
  `export`, `dataruns` — now live in `forefst.py` (validated byte-identical to the previous
  `refsanalysis.py` implementations across all images, then de-duplicated). Running them under
  `refsanalysis.py` prints a one-line redirect. The old `attributes` command is folded into
  `files --filter <category>` (12 categories). `refsanalysis.py` keeps the structure/lab commands
  (boot/supb/chkp/objects/schema/parentchild/containers/upcase/oid30/files/attributes/details/all/bootedit).
- **`files` CSV is now 32 columns** — `GroupSid`, `AllocatedSize` and `ReparseTag` were appended before
  `RefsVersion` (which stays last); columns 0–27 keep stable indices. `OwnerSid`/`GroupSid` render the
  friendly name + SID; `ReparseTarget` now covers non-resident symlinks on v3.14.
- **Hand-written in-tool help.** Both tools gained per-command help with options + runnable examples:
  `forefst.py <image> <cmd> --help` (or `forefst.py help <cmd>`) and the same for `refsanalysis.py`,
  plus an enriched top-level overview / `--list`. The `docs/tools/` pages were rewritten to match.
- **Fixes (cross-tool consistency):**
  - `refsanalysis.py details` reparse sub-record tag was always `0x00000000` (it read a reserved field);
    now reads the REPARSE_DATA_BUFFER tag at `v+0x0C`, matching the header `ReparseTag` mirror.
  - `refsanalysis.py details` attribute decode now uses the canonical `attrs_to_str` (shows EA /
    Compressed / IntegrityStream / … — previously only six flags).
  - `refsanalysis.py files`/`attributes`/`details` no longer under-report non-resident `HasEA`: the EA bit
    (`0x40000`) is read from the authoritative type-0x40 backing (`+0x48`) instead of the type-0x30 pointer
    (`+0x40`), matching forefst (e.g. +8,141 correctly-flagged files on the Insider image).
  - `forefst.py extract` accepts a leading-slash absolute path and `--path` (symmetric with `details`);
    unknown options are rejected instead of being silently ignored.

## v3.4.2 — 2026-06-20 (hard-link grouping SIZE-MATCHED — fixes a surviving over-merge)

**Tool fix — `forefst.hard_link_count` / `refsanalysis summary++` (`hardlink_extra`):** the v3.4.1
"content-aware" key (resolve to the local `(parent,file_id)` type-0x40 if `alloc>0`, else the home record)
**still over-merged distinct files.** The per-directory ordinal (`file_id` = `value+0x00`) collides — a directory
can hold the type-0x40 stream of a *different* file home'd there under the same ordinal — so the local
content-bearing record at a colliding ordinal is that other file's. Distinct-size files fused (e.g.
`xbpt_output_lima` 403,765 B + `xbpt_record_index` 415,474 B as one group; 30 such groups on `wininsiderrefs8gtest2`,
5 on `win11refs2g`). **Fix:** resolve each name to the candidate stream — local `(parent,file_id)` or home
`(home,file_id)` — whose 0x40 size **equals the name's own size** (`value+0x38`); group on that stream's
`(owner, file_id)`; names matching no candidate are not merged. **Validated by an INDEPENDENT oracle** (each name's
own `value+0x38`, not the grouping key): **0 over-merge across 112 images**, fsutil control `[4,2]`, genuine groups
preserved (`winsider` 33,104). Errata **E51**; master §J / §C.3 updated.

**Audit context — why v3.4.1's "0 mixed across 113 images" was wrong:** that validation
(`verify_hl_integrity.py` / `verify_claim.py` #12) resolved each member's content through the **same colliding key**
the tool grouped by, so over-merged members fetched the identical record and looked consistent — a self-deceiving
check (surfaced by the 2026-06-19/20 forefst soundness audit). Both gates were **re-based on the independent
per-name size signal**: they now FAIL on the buggy tool and PASS on the fixed one (mutation-calibrated). Regression
**12/12**.

## v3.4.1 — 2026-06-19 (hard-link grouping re-fix + WSL/FIFO corpus verification)

**Tool fix — `forefst.hard_link_count` and `refsanalysis --summary-plus` (`hardlink_extra`):** the hard-link
grouping previously keyed on the metadata tuple `(home-dir backref, FileId/ordinal, size, ctime, mtime)`, which is
**not an object identity** and **false-merged distinct files** on synthetic `.lnk`/`xbpt_` timestamp-cloned test
images (proven 2026-06-19: two files with different on-disk clusters / SHA1 reported as one hard link). Both tools
now resolve each non-resident name to its **content-bearing type-0x40 record** — the local `(own parent, file_id)`
record only if it has real content (`alloc>0`), else follow the home backref to `(home, file_id)` through any
`alloc=0` link **stub** (the stub representation `MD_DATA_RA_006` describes — it IS real) — and group only names
sharing that physical record. This fixes BOTH the original false-merge AND an over-split (a first presence-based
re-fix wrongly resolved a link's `alloc=0` stub locally; corrected to content-aware). Validated: reproduces
`fsutil hardlink list` exactly (win11refs2gtargeted `[4,2]`); **all-disk content-integrity = 0 mixed across 113
images**; winsider = 33,101 genuine WinSxS groups (preserved); block-clones (CoW, distinct objects sharing
clusters) correctly kept separate. Regression **11/11 all-disk**, gates **453 PASS / 0 FAIL**.

**WSL/FIFO/hard-link corpus verification (all 113 ReFS images):** confirmed the two formerly-"unconfirmable" claims
are *present* on existing images, not absent — **MD_ATTR_RA_004** (WSL FIFO) on exactly **3** images (reparse tag
`0x80000024` + `$LXMOD` `S_IFIFO`), **MD_DATA_RA_006** (hard links) on **52** distinct images (53 rows; genuine, per the fixed tool — fsutil-ground-truthed on win11refs2gtargeted; the pre-fix tool reported 28, under-counting via over-split). New
durable per-disk feature table **`image_special_features.csv`** (WSL / FIFO / device-node /
hard-link presence) so these never need a full re-scan. Corrected the MD_ATTR_RA_004 octal
(`0120000`→`S_IFIFO 0o010000`) and §J `winsider=10`→33,101 (genuine, content-aware). Reports:
`fifo_hardlink_corpus_scan_2026-06-19.md`, `hardlink_false_positive_verification_2026-06-19.md`.


## v3.4.x — 2026-06-19 (knowledge corrections E45–E50 + workspace consistency pass)

**Reference corrections (errata E45–E50, static-decompilation + all-disk verified):**
- **E45 / E30** — the resident type-0x30 directory-entry value is an INDEX ENTRY (FILE_NAME-like), not a verbatim `$SI`; `value+0x58` = FileSize (not USN). The per-file → change-journal link is **LastUsn** (`$SI+0x40` / `value+0x68`) + UsnJournalId (`+0x70`) — proven 480/480 `$J`-record matches.
- **E46** — MSB+ page header `0x40` = TableIdHigh (**always 0**), not "Schema"; the numeric table OID is `TableIdLow` at **`0x48`** (137,444/137,444 pages).
- **E47 → E49** — frame error reversed: Prade's "Index Root" is the `_SmsIndexRoot` descriptor at page+0x50 (schema@0x0C, extents@0x18, total-rows@0x20); GN_IDXR_002/003/004 all CONFIRMED.
- **E48** — non-resident snapshots exist and use the type-0x40 24-byte VLCN extent format (29/30 true snapshots; content byte-exactly recovered).
- **E50** — Parent-Child schema `u32[7]` is the key-comparison-rules selector (8 → `CmsRulesPARENT_CHILD_LINK`), not a "bit-3 = value-overlaps-key" flag; the overlap is a caller-side same-buffer construction.

**Workspace consistency pass (2026-06-19):** propagated all corrections (E45–E50 + E14/E21/E23/E35/E39/§A.4/§B.1a/§B.2/§B.6/FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003/AP_REDO_001–039) from the master `structure_reference.md` + `errata.md` to every drifted derived file (registry rows, structure/concept docs, ``). Self-checksum docs corrected to **cluster-size-dependent**; `$CBW4` marked fabricated everywhere (E35); `$SI` field labels corrected (E21/E23/E39); schema v3.4 count 27→25 (E14); page-OID 0x40→**0x48** (E46). **Regression 11/11 all-disk, gates 0 FAIL, parity green.** (The dated round-1/2 doc-audit artifacts under `audit/` were left as history with a superseded-values banner.)


## v3.4.0 — 2026-06-13 (timestomp detection)

- **New `refsanalysis.py <image> timestomp` subcommand — ReFS timestamp-tamper detection.** NTFS's
 `$SI`-vs-`$FN` dual-set cross-check does not exist on ReFS (no `$FN` timestamps), but timestomping
 is still detectable via three independent anchors, which this subcommand combines:
 - **CHANGE_LATE (intrinsic):** the high-level APIs timestomp tools normally use (Win32 `SetFileTime`,
 PowerShell, .NET) expose only Creation/Write/Access — **not** the metadata-change time (`$SI+0x10`) — so a
 back-dated Created/Modified leaves `change >> max(created, modified)`. A heuristic against common tools,
 **not** tamper-proof: `NtSetInformationFile(FILE_BASIC_INFORMATION.ChangeTime)` or a raw-disk edit can set
 the change time too and defeat it.
 - **USN_BASIC_INFO_CHANGE / USN_CREATE_MISMATCH (authoritative):** a standalone `BASIC_INFO_CHANGE`
 (reason `0x8000`) journal record is a deliberate basic-info edit with no content change, recorded
 at the real time; `FILE_CREATE` gives the true creation time to compare against `$SI`.
 - **PRE_FORMAT / FUTURE:** Created before the volume existed / after its last write.
 Confidence tiers **HIGH/MEDIUM/LOW** reflect independent-source agreement. Output: human table,
 `--json`, `--csv` (per-file path/confidence/signals/MACB), `--all`, `--min`, `--margin-days`.
 **Validated** on `win11refstestmftecmd.raw` (75 `SET_TIMESTAMPS` ground truth): HIGH precision 100 %
 (every HIGH has a provable basis), 0 false positives on the clean baseline and a clean operations
 image (renames/ADS/snapshots/hardlinks). Honest limitation: intrinsic-only HIGH (CHANGE_LATE +
 PRE_FORMAT) also matches a creation-time-preserving copy (robocopy `/COPY:T`, restore) — the USN
 journal disambiguates. Method doc: `docs/concepts/timestomp_detection.md`.
- **Shared `forefst.timestomp_intrinsic_flags()` helper** (stdlib) exposes the intrinsic
 CHANGE_LATE/PRE_FORMAT/CREATE_GT_MODIFY/FUTURE flags so a listing can carry them per-row without the
 journal. `docs/concepts/standard_information.md` + `docs/ntfs_comparison.md` corrected (they had said
 ReFS timestomp detection was "not available").

## 2026-06-13 — Full claim audit (405/405) + doc-statement audit

- **Claim audit COMPLETE — all 405 reference_table claims** validated through a deterministic harness
 (`analysis/reports/audit/`): each has a verified ref_id↔claim correspondence, a proof (disk matrix /
 exported decompiled function / sourced citation), and a corpus-aware verdict across 110 ReFS images.
 Result: 115 CONFIRMED + 69 STATIC-CONFIRMED + 212 STATIC-CITED + 3 CORROBORATED + 1 RD-LIMITED +
 5 CONTESTED-by-design (documented corrections, findings FS_CHKP_RA_015/CT_CTBL_010, CT_CTBL_RA_006/FS_CHKP_RA_012, FS_CHKP_RA_005, FS_CHKP_RA_001, FS_CHKP_RA_013). See `AUDIT_COMPLETE.md`.
- **Doc-statement audit (76/76 docs)** — ~41 verified fixes; the docs were already excellent (errata applied).
 Two stale clusters fixed (each predating the claim-audit): SUPB/CHKP self-checksum is **CRC64, verified +
 self-healed** (FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003, not "CRC32-C not verified"); DataSize = `$DATA` allocated_size, **not** 8-byte-aligned
 (CT_CTBL_RA_003, AP_LGFL_RA_008, AP_LGFL_RA_004). See `DOC_AUDIT.md`.
- **CRC64 label corrected everywhere** — ReFS metadata CRC64 uses the **custom poly 0x9A6C9329AC4BC9B5**
 (`ClMulCsCrc64`), **NOT ECMA-182** (GN_PREF_002; proven: `forefst.refs_crc64` reproduces every stored page-ref
 checksum, 0 mismatches; ECMA gives different values). The stale "CRC64-ECMA" was propagated out of
 `structure_reference.md`, `reference_table.csv`, and several docs to match.

## v3.3.4 — 2026-06-13 (tool changes driven by the claim audit: CT-by-ID, $SI type-0x10 gate, CRC64 labels)

These are the **tool-behavior** changes that followed the 405-claim audit (the entry above corrected the
*docs/reference*; this entry corrects the *tools*). Plan + evidence: `analysis/reports/plan_tool_updates_from_audit.md`.

- **Container-Table selection is now by Table-ID `0x0B`, not by root index 7 (finding FS_CHKP_RA_015, robustness).**
 New `_select_ct_root(f, ps, cs, roots)` picks the Container-Table root from the failover pair {root 7, root 8}
 by reading the table-root page header `+0x48` (prefers the primary `0x0B`, falls back to the duplicate `0x0C`,
 then to index 7). Used in `bootstrap()`, the older-checkpoint reader, and the 3 `refsanalysis` CT-read sites.
 **Full-corpus regression: bootstrap 110/110, selected CT carries Table-ID `0x0B` on 110/110, translator
 resolves 110/110, 0 failures.** Old (index-7) vs new (id-`0x0B`) differ on exactly the 4 `millionsofactions`
 2 TB images, where root 7 carried the `0x0C` duplicate; the duplicate and primary maps are byte-identical
 (16192 containers each), so the old behaviour already produced correct results — the fix makes the selection
 canonical and robust to a stale copy.
- **`$SI` is now parsed only from a top-level type-`0x10` row (validation via $SI USN re-sourcing MD_SI_RA_015).** `cmd_oid_detail` previously
 parsed `if at in (0x10, 0x90)`, which mis-decoded a top-level **type-`0x90`** row (the `$I30_INDEX` template /
 the Upcase-table payload on system OIDs such as `0x7`) as a garbage `$SI` with bogus MACB timestamps. Gated to
 type `0x10`; corpus-safe (0/215 top-level type-`0x90` rows are a valid `$SI`). Validated against ground truth:
 PowerShell fsactivity log **85/85 = 100 %** (create_time + file_size, unique-filename keyed); filename-keyed
 USN journal **411/429 = 96 %**, all 18 residuals explained (17 intentional timestomps that the tool faithfully
 reports, 1 tolerance-boundary artifact) — see `analysis/reports/usn_si_crosscheck_oid_investigation.md`.
- **Attribute-name map: top-level type `0x90` relabelled** "$STANDARD_INFORMATION (own)" → "$I30_INDEX / table
 payload (schema-dependent)" — type `0x90` is overloaded (`$I30_INDEX` when embedded in a 0x30 dir entry per
 MD_ATTR_RA_015; an Upcase/table payload at the top level of a system object), and is never `$SI`.
- **CRC64 output labels: 6 "CRC64-ECMA" strings → "CRC64"** in `forefst.py` + `refsanalysis.py` (`integrity`,
 `boot`, `fixboot` output and the checksum-algo map). Computation was already the custom poly (GN_PREF_002); only the
 printed label was wrong. **DataSize** comment/label clarified to "= `$DATA` allocated_size; not logical, not
 always 8-byte-aligned" (CT_CTBL_RA_003, AP_LGFL_RA_008, AP_LGFL_RA_004/E26).
- Publish gate after these changes: `verify_docs_static.py` 0 FAIL; `verify_docs_tools.py` **453 PASS / 0 FAIL**.

## v3.3.3 — 2026-06-13 (deleted --slack recovery + export subcommand)

- **`deleted --slack` (deletion-recovery "Method 5", finding FS_DEL_RA_005).** Recovers deleted directory entries
 from **B+-tree node slack** — ReFS deletion removes only the row's offset-array slot, so the row body
 (name + inline `$SI` MACB + attrs) persists until a later CoW rewrite. The scanner brute-walks every
 live + orphan metadata page for type-0x30 row headers not in the live offset array, **grades each by
 confidence** (high = both MACB timestamps plausible; medium = one; partial = name fragment only), and
 cross-flags **deleted** (name absent from the live tree) vs **prior-version** (CoW remnant of a living
 file). Validated: **0 false positives** on the clean baseline (all 19 recovered names genuinely absent
 from the live tree — `arg.txt`, `New folder`, superseded `FVE2.{…}` BitLocker metadata); ~70% high-
 confidence, partials flagged honestly. `--extract DIR` writes the recovered rows. Robust on
 v3.4/64K/corrupt.
- **`export -o DIR` (new subcommand) — the ReFS analogue of dumping a raw `$MFT`.** Writes raw,
 hash-verified artifacts: VBR primary + backup, both checkpoints, the SUPB copies, the MLog control
 pages + live log pages (+ index), the reassembled USN `$J` stream, and the **whole object B+-tree
 forest** (`--btree-mode packed` = one `metadata_pages.bin` + `metadata_index.csv`, or `per-object` =
 one file per OID), plus **`manifest.json`** (per-artifact source/lcn/length/sha256) and
 **`sha256sums.txt`** (`sha256sum -c`-verifiable). `--what vbr,chkp,supb,mlog,usn,btree,all` selects
 structures. Reuses `bootstrap` + the integrity backup locators + the MLog/USN readers.

## v3.3.2 — 2026-06-13 (fidelity flags, backup-version analysis, redundancy docs)

- **Perf/fidelity policy — every speed tradeoff now has an enable path.** Added `integrity --max-pages N`
 (raise the full-tree checksum page cap, default 300000; the cap NOTE now points to it) and
 `timeline --depth N` (the $SI walk depth, default 12). Documented the policy in
 `docs/tools/refsanalysis.md` ("Performance & fidelity"): **fast by default, full fidelity always
 reachable by a flag.** Clarified that the v3.3.1 `timeline` `enrich=False` change is a pure
 optimisation with **no output change** (it only gated SecurityId/ADS/reparse fetches the timeline
 never displays; MACB timestamps come from the directory entry).
- **Backup boot-sector message corrected (deeper static analysis, FS_VBR_RA_013 refined + FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003 new).** Tracing
 `refs.sys` showed the VBR backup is validated only by its own 0x16 checksum and is consulted **only on
 a primary read failure** (no cross-copy CRC64/clock), so a version mismatch is reported honestly as
 **"an UPGRADE … or VBR tampering"** (not a definitive upgrade). Corpus check: the divergence appears on
 genuine upgrades (backup keeps the original v3.4 / v3.9) AND on VBR-tampered test images (primary
 v6.66 / v3.15, backup authentic v3.14). By contrast the **SUPB (3 copies) + checkpoint pair** carry
 8-byte CRC64 self-checksums, are selected by highest virtual clock, and self-heal at mount (finding
 FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003) — documented in the new `docs/concepts/redundancy.md`. Backup *failover* (use a backup when the
 primary is corrupt) is planned, not implemented: `analysis/reports/plan_backup_failover.md`.
- **Help + docs:** CLI help and `docs/tools/refsanalysis.md` updated for `--checksums`/`--fullchecksums`,
 the integrity backup section, `timeline --fast`/`--depth`, and the v3.7 routing; `timeline` (previously
 undocumented) added to the command reference; glossary opcode counts and the checksum-architecture
 scope corrected.

## v3.3.1 — 2026-06-13 (split checksums + backup scan, v3.7 opcode routing, fast timeline)

- **`integrity` checksum split:** `--checksums` now verifies **only the system root tables** (fast);
 `--fullchecksums` verifies the **entire metadata tree** (the v3.3.0 full-coverage walk). The
 `--checksums` output points to `--fullchecksums`.
- **`integrity` Redundancy / Backup section (new):** scans ReFS's redundant copies — the backup boot
 sector (last LBA), the alternating checkpoint pair, and the secondary SUPB copies — and verifies each
 (VBR self-checksum `_vbr_checksum`, CHKP signature+vclock+roots, SUPB signatures). Surfaces a real
 forensic signal: on an **upgraded** volume the backup boot sector retains the **original pre-upgrade
 version** (e.g. backup=v3.4 vs primary=v3.14), reported as "UPGRADED from vX.Y" (finding FS_VBR_RA_013). The
 failover (using a backup when the primary is corrupt) is intentionally deferred. Backup anomalies are
 WARNs, not failures.
- **MLog opcode routing fix (finding AP_LGFL_RA_009):** v3.7–v3.13 now use the v3.14 dispatch table (was
 `vmin >= 9`, now `vmin >= 7` via `_redo_ops_for_version`). v3.7 emits the 0x1D–0x1F stream opcodes
 (absent from v3.4) and the old routing left 78 records unresolved on win1121h2test. RD-validated to
 **0 unknown opcodes across all 83 corpus images** with an MLog log; cross-source consistency
 (USN/$SI by OID, MLog by path) confirmed.
- **`timeline` performance (finding via profiling):** the `$SI` MACB phase did one extra B+-tree read
 **per object** (`enrich=True`) that the timeline never used — dropped it (`enrich=False`), and added
 **`--fast`** (alias of `--no-si`) which skips the per-file `$SI` MACB walk entirely. On winsider
 (35K objects / 147K entries) the default `$SI` walk is ~157 s while MLog+USN are ~3 s, so `--fast`
 turns a >180 s run into **~3 s** (change-journals only). A large-volume hint now points to `--fast`.

## v3.3.0 — 2026-06-13 (full-coverage checksum verifier + corrected MLog opcode tables)

- **A1 — `integrity --checksums` now verifies the ENTIRE metadata tree**, not just the ~8–13
 root-table pages. The walk crosses the Object Table's leaf rows (each embeds the object root's page
 reference at value+0x20) into every file/dir/stream B+-tree, recomputing CRC64 (cktype 2) / SHA-256
 (cktype 4) over every interior + leaf page. Coverage rises from ~8 pages to the full tree (e.g.
 snapshots image 906 pages, winsider 35,327). Verified: **full-coverage parity with the structural
 walk and zero false positives on 40 clean images** (v3.4→3.14, 4K/64K, CRC64/SHA-256, upgraded);
 catches the injected corruption in `win11refslasttests_baseline_corrupted` (LCN 0x6400) that the old
 root-only walk missed. Three bugs fixed along the way:
 - **Indirect-checkpoint root base**: the verifier hard-coded the root-offset list at `chk+0x94`; for
 indirect checkpoints (CHKP flags bit 0x200, native v3.14) the base is `le32(chk,0x94)`. Without this,
 root index 0 wasn't the Object Table and object trees were never reached.
 - **`dl`-vs-compact-ref guard**: inner-node child pointers and the OT-leaf embedded ref are the
 compact 0x30-byte page-reference form even when the descriptor length `dl` is larger (0x68 on v3.4);
 the old `len ≥ dl` guard skipped every v3.4 subtree (~40% of pages uncovered). Now guards on the
 checksum's own extent.
 - **Structural false positive**: `_walk_btree_pages` treated each 4 KiB cluster slot of a multi-cluster
 (16 KiB) page as a standalone page, FAILing the all-zero continuation clusters as "Invalid signature"
 on **every** clean multi-cluster volume. Now reads each page-reference's slots as one logical page.
 - `integrity` now returns **exit code 2 on failure** (structural or checksum) for scriptability.
- **A3/A4 — corrected the redo-opcode dispatch tables** (`REDO_OPS_V314`/`REDO_OPS_V34`,
 `OPCODE_CATEGORIES`). Re-read of `CmsLogRedoQueue::PerformRedo` shows the ranges are **contiguous and
 almost entirely handled**: v3.4 = 29 values 0x00–0x1C (0 gaps); v3.14 = 44 values 0x00–0x2B with only
 0x17 an explicit error. The previous tables wrongly tagged six handled v3.14 ops
 (0x04, 0x10, 0x14, 0x1B, 0x20, 0x26) and both v3.4 0x08/0x09 as "gaps", and were off-by-one across
 0x1A/0x1B, 0x1E/0x1F/0x20 and 0x28/0x29. Notably **0x20 = `CmsStream::UpdateStreamUserPayload`**
 (handled; 4.0% of records on win11refs2tsnapshots) — not a gap. On-disk proof: opcode 0x04 (formerly a
 "gap") appears in real records. (finding AP_REDO_001–039)
- **A4 — `details <path>` file size on snapshot-bearing resident files**: such files have no live
 `0x80000001` $DATA row; `get_resident_file_size` now falls back to the current-version
 descriptor-`0x10028` holder (sub_id `0x1000`) at value+0x38. Verified arg.txt=15, lasttest.txt=201,
 test.txt=5; normal files unchanged. The per-sub-record `$DATA (default)` line is now consistent too.
- **A2 — MLog control-page region (B1) resolved**: the `0xE48` control area is a compact header
 (populated to ≈byte 0xF8) followed by zero padding (~93% of the area is zero on every image). The
 former "~124 undecoded bytes" are zero gaps + a couple of small constants, not hidden fields.
 (finding AP_LGFL_RA_008)

## v3.2.9 — 2026-06-12 (resident-file details + version export + upgrade flag)

- **A — `details <path>`** (new): full details for ANY file **by path** — resident files have **no OID**
 (their `target_oid` is the sentinel `0x1e000000001`; they live inline in the parent dir row), so `--oid`
 could never reach them. Decodes inline `$SI` (MACB, SecurityId, LastUsn, FileSize (resident index entry; the type-0x10 $SI DataSize is unpopulated)), `$DATA`, ADS,
 snapshots, `$EA`, reparse for resident files; own B+-tree for non-resident. `--json`. Verified: matches
 the lister 15/15 (size + SecurityId).
- **B — `snapshots --file <name>`** lists a file's snapshot versions; `--extract DIR` exports each
 (the 2 modes; built on the verified `recover_snapshot_streams`).
- **C — `deleted --extract DIR`**: export recovered deleted/old-version rows (the orphan-page scan now
 carries the recovered bytes). (Clean volumes have few orphans — image-dependent.)
- **E — summary upgrade flag**: `--fastsummary-plus`/`--summary-plus` now print **"⚠ APPEARS UPGRADED
 (formatted pre-v3.10, now running v3.X)"** vs **"NATIVE vX.Y"**, from the CHKP native-bit 0x080 +
 $VolInfo version-stamp markers (finding FS_CHKP_RA_001, FS_CHKP_RA_003/FS_VOLI_RA_002).
- **F1 robustness fix**: `integrity --checksums` no longer crashes on an upgraded volume (un-translatable
 page slots are skipped, not fatal).
- **Tested:** new-features matrix on the 25 baseline + 64K images (26 total) — **234 PASS, 0 fail**.
 Script: `analysis/tools/analysis_scripts/test_new_features_matrix.py`.

## v3.2.8 — 2026-06-12 (F1 page-checksum verify + F3 super-timeline)

- **F1 — `integrity --checksums`**: recompute each metadata page's checksum vs the stored value
 (tamper/corruption detection). **The ReFS metadata CRC64 was decoded**: reflected, custom poly
 `0x9A6C9329AC4BC9B5` (driver `ClMulCsCrc64`) — **NOT ECMA-182** (the doc's prior poly was wrong),
 init=xorout=~0, over the full page; SHA-256 = `sha256(full_page)`. 0 mismatches across v3.4/v3.14/64K/
 SHA-256. `forefst.refs_crc64()`; finding GN_PREF_002; corrects `checksum_architecture.md`. (Covers root-table
 metadata; per-object B+-tree coverage is a future extension.)
- **F3 — `timeline`**: super-timeline merging **USN + MLog + $SI MACB** into one chronologically-sorted,
 OID-joined event stream (`--file`/`--oid`/`--source`/`--no-si`/`--limit`/`--csv`). The 3 source parsers
 were each validated independently first (USN 6805 / MLog 1322 / $SI 6976 on `win11refstestmftecmd`).
 Caveat: MLog times join by OID + time window (no shared key with USN).

## v3.2.6 — 2026-06-12 (audit follow-up: tool quick-wins + weak-claim reanalysis)

- **Q4 — `security --audit`**: one-shot content-addressed-hash audit over every descriptor → single
 verdict ("CLEAN — 0/N fail") + lists any failures (tamper/corruption check). (FS_SECD_RA_002/FS_SECD_RA_001)
- **Q6 — `extract` EFS guard**: extracting an EFS-encrypted file (FILE_ATTRIBUTE_ENCRYPTED 0x4000) now
 prints a CIPHERTEXT warning instead of silently writing encrypted bytes. (MD_EFS_RA_005)
- **Weak-claim reanalysis (finding CT_CTBL_RA_003, AP_LGFL_RA_008, AP_LGFL_RA_004)**: MD_SI_RA_016 DataSize STRENGTHENED (36/36 == allocated incl. 4
 discriminating desktop.ini cases refuting align8(logical)); AP_LGFL_RA_004, AP_LGFL_RA_007, AP_LGFL_RA_008, AP_LGFL_002 MLog 0x04 magic STRENGTHENED
 (per-volume-stable, survives v3.4→v3.14 upgrade, ≠ VBR serial); CT_CTBL_RA_003 SHA-256 224-byte row CONFOUND
 DECOUPLED (triggered independently by SHA-256 *and* by 64K). Reports: `audit_weak_claims`,
 `plan_F5_extent_resolution`.
- **F1 (page-checksum verify)**: goal documented; shipped in v3.2.8 once the CRC64 was decoded.

## v3.2.5 — 2026-06-12 (finalization: relabel fixes + doc consolidation)

- **Tool relabel bug-fixes** (correctness; from the finalization audit): `fmt_map` compression format 3
 `"LZX"` → **`"LZ4QAT"`** (AP_REDO_037); reparse-index key+0x08 `"parent_oid"` → **`"name_ordinal"`** (FS_REPS_RA_001, FS_OTBL_RA_005);
 `_INTERNAL_FLAGS` += `0x20 REDIRECT_TRUST` (MD_SI_RA_014/E29, was silently dropped).
- **Documentation consolidation:** fixed two internal contradictions (`mlog.md` stale "two-layer"
 summary → four-layer; `SNAPSHOT.md` 0x000E0080 vs 0x10028 reconciled); added the **two checksum
 families omitted from `checksum_architecture.md`** (MLog XOR-fold @entry+0x08 / E42; 24H2
 container-compression per-unit checksums); added **`deletion_recovery.md` Method 4 (Stream Snapshot
 Recovery)** + the FS_CHKP_RA_014 checkpoint-comparison RD result + the disk-snapshot-vs-stream-snapshot caveat;
 added the **compression-policy section to `container_table.md`**; repaired
 **`attributes/STANDARD_INFORMATION.md`** (added a key-offset table incl. SecurityId@0x28, the 0x73/0x7b
 min-size thresholds, the 0x44=high-dword-of-LastUsn note, the HLC-own-row=0 caveat); deduped the
 recovery tables (canonical in `deletion_recovery.md`); added cross-links.
- **Audit reports:** `analysis/reports/audit_weak_claims_2026-06-12.md` (6 under-verified high-impact
 claims + how to strengthen) and `audit_tool_gaps_2026-06-12.md` (applied fixes + F1–F3 feature gaps).

## Docs — 2026-06-12 (S9 compression + S10 system tables)

- **New `concepts/compression.md`**: ReFS 24H2 volume compression decoded (E2 + RD). It is
 **per-container** (not per-file/per-extent); format enum 0=None/1=LZ4/2=ZSTD/3=LZ4QAT; policy on
 disk at the Container Table root-page extended header (format @0xA4, chunk @0xA8) — RD-confirmed
 before/after on the 8 GiB set; `_SmsContainerCompressionHeader` (0x40 B + per-unit u32 length
 array). **Honest limit:** raw end-to-end decompression not achieved (no verified compressed-container
 image in the corpus). Open-question B3 partially resolved; finding AP_REDO_037.
- **S10 system-table docs RD-re-verified + deepened** (finding FS_UPCS_001, FS_PCTB_RA_001, FS_PCHL_001, CT_INTS_001, CT_CNTX_001, FS_OTBL_RA_003): `upcase_table.md` corrected —
 on disk it's a **387-row B+-tree** (name row + index-keyed rows that concatenate to the ~131 KiB
 map, md5-identical across versions), not a flat array; `parent_child_table.md`, `integrity_state.md`,
 `container_index.md`, `trash_table.md` gained RD-verification notes (parent-child/container-index/
 integrity are CHKP-root-only, absent from the Object Table). Script `verify_system_tables.py`.

## v3.2.4 — 2026-06-12

### Stream-snapshot prior-content recovery (CoW) + E2 grounding

- **`snapshots --show` / `--extract DIR`**: recover the prior (snapshotted) content of a file by
 following the extent chain — `$SNAPSHOT` `val[0x44]` data_sub_id → `$DATA` sub-record (key+0x10 ==
 data_sub_id, descriptor 0x10028) → 24-byte extents (VLCN @+0x00, file_vcn @+0x0C, run_length @+0x14)
 → sort by file_vcn → VLCN→PLCN (Container Table) → read → trim to stream size. `forefst.py` adds
 `parse_snapshot_data_entry()` + `recover_snapshot_streams()`.
- **E2 grounding** of the chain: `RefsCreateStreamSnapshot` (win11 L162081-162127) builds the 0x68-byte
 StreamSummary, sets the snapshot flag, stamps the stream-set id + FILETIME; `GetResidentStreamSummaryFromDisk`
 confirms the on-disk layout. The data_sub_id is the snapshotted stream's stream-set id (monotonic).
- **Verified byte-for-byte** (MD5-identical to the independent Step 4.9b export) on 9+ files across
 win11refs2tsnapshots / win11refs4gattributes(test2) / wininsiderrefs2t, incl. multi-extent chains
 (test.txt 42→65→92→"abc"; xbpt json 71 KB / 3.2 MB / 8 extents; up to 21 extents / 13.4 MB).
- Docs: `concepts/copy_on_write.md` gains a **Stream Snapshot Content Recovery** section;
 `attributes/SNAPSHOT.md` gains the full extent-chain recovery procedure + DATA-entry format.
- Verification: `analysis/tools/analysis_scripts/recover_snapshot_content.py`.

## v3.2.3 — 2026-06-12

### MLog LogCore record format fully decoded (four-layer model) + 0x04 erratum

- Resolved open-question **B2b**: each MLog data page is a **LogCore data record** with four
 nested layers — (L1) 0x78-byte record header, (L2) 56-byte entry header (64 on Insider),
 (L3) redo block `_SmsRedoHeader`, (L4) `_SmsRedoRecord`. Decoded from `LogCoreWriteDataRecord`/
 `LogCoreScanDataRecord`/`LogInitializeEntryHeader` (v3.4/v3.14/Insider) + RD on 10 images
 (findings AP_LGFL_001, AP_LGFL_002, AP_LGFL_RA_004, AP_LGFL_RA_007, AP_LGFL_RA_008; `structure_reference.md` E.2/E.2a/E.4; `structures/mlog.md` rewritten).
- L1 fields: sig@0x00, **format magic @0x04 (per-volume constant, NOT a CRC)**, ver@0x08,
 **log-block size @0x0C (0x1000 always — not the volume cluster size)**, UUID@0x10, counter@0x20,
 **LSN@0x28**, **prevLSN@0x30** (chains pre-wrap), length-in-4K-blocks@0x38/0x3C, entry-off@0x54=0x78.
 L2: LSN@+0x00, **checksum (XOR-fold) @+0x08 = page+0x80**, payload-len@+0x20, payload-off@+0x28
 (**0x38 v3.4–v3.14 / 0x40 Insider**), type@+0x30 (2=data, 1=control).
- **Erratum E42**: page+0x04 is a per-volume constant magic, **not a CRC32** — proven (constant
 across every control page + data record in a volume; copied from the log handle, validated by
 equality). The real per-record checksum is the XOR-fold at entry+0x08. Corrects the thesis
 (`analysis_application.tex:74`), `mlog.md`, and `forefst.py`.
- `forefst.py`: `parse_mlog_control_page` field `crc32` → `format_magic`; added
 `parse_mlog_record_header()`. `refsanalysis.py mlog -v`: new **LogCore Record Headers** table
 (per-record LSN / prevLSN / checksum / type / payload-offset with `!chain` wrap markers).
- **64K-cluster scanner fix**: `scan_mlog_data_area` now iterates **4 KiB log blocks** (the MLog's
 fixed I/O unit), not clusters — so 64K-cluster volumes pack 16 log blocks per cluster and the
 scanner sees all of them. Previously it read 1 block/cluster and exposed only 1/16 of the records
 (e.g. `wininsiderrefs8gtest2` 127 → 2,039; `win11refs15t64k` → 2,395). 4K-cluster volumes are
 unchanged (1 block/cluster). Validated on the 25 baseline + all 5 64K-cluster images (26 total),
 all PASS. New `block`/`block_lcn` fields on data-area pages and records; `-v` shows `PLCN.blk`.
- Verification: `analysis/tools/analysis_scripts/probe_logcore_record.py`.

## v3.2.1 — 2026-06-12

### Security descriptor (OID 0x530) full decode

- Decoded the 12-byte ReFS SD value wrapper: +0x00 SD hash (=SecurityId low), +0x04 generation
 (=SecurityId high), +0x08 entry size; SD at +0x0C (findings FS_SECD_RA_001, FS_SECD_RA_002).
- **SecurityId = (generation << 32) | hash32(SD)** — content-addressed dedup. Low 32 = the NTFS
 `$Secure` SD hash (`h=(d+ROL(h,3))`, verified 1,113/1,113); high 32 = collision generation.
 Proven cross-volume (same SD → same SecurityId-low on 3–4 images, 8/8).
- `refsanalysis.py`: added `_refs_sd_hash()` + hash-verification in `security` (`[hash OK]` /
 `[HASH MISMATCH]`, tampering detection); fixed the wrapper "ref_count" mislabel → generation.
- `structures/security_descriptors.md` rewritten with the full byte-level format + dedup model.
- Closes the #1 gap from `audit_missing_information.md`.

## v3.2.0 — 2026-06-12

### Exhaustive $SI / attribute field re-analysis + corrections

Deep per-field analysis of all 18 $SI fields and every attribute type (static
decompilation + 111-image census + ground truth + adversarial verification). Empirical
backbone: `analysis/tools/analysis_scripts/study_all_fields.py` →
`all_fields_census.json` + `field_digest.json` (3-population model:
file_resident / file_own / dir_own). Verdicts in `analysis/tools/analysis_scripts/field_verdicts/`.

Doc/reference corrections (errata E27–E41; findings MD_SI_RA_013, MD_SNAP_RA_007, MD_SNAP_RA_005; MD_USN_RA_004, FS_SCHM_RA_007/MD_ATTR_RA_016/MD_SI_RA_010, MD_SI_RA_008/FN_LINK_002, MD_SI_RA_009
corrected):

- **$SI+0x40 ClassTag → LastUsn**; **$SI+0x48 SessionTimestamp → UsnJournalId** (USN journal
 fields; "storage tiering" disproven). FCB bit 23 = cached-last-USN-valid-for-epoch.
- **$SI+0x58 VersionRefCount → NextFileId** directory child-creation ordinal (not version/CoW).
- **$SI+0x30** = an UNPOPULATED USN slot (0 corpus-wide); the nonzero 're-sourced from $DATA stream summary' data was the type-0x30 index-entry FileSize@value+0x58 (different structure). Real per-file USN = LastUsn ($SI+0x40). [Superseded 2026-06-17: E30 RETRACTED / E45.]
- **InternalFlags bit5 (0x20)** = symlink redirection trust level (not hardlink-zero).
- **HardLinkCount** always 1; prior "confirmed hard links" was a value+0x08 artifact (no real
 hard links in corpus). **$SI+0x74** = NextStreamSetId (base 0xF000), not ExternalFileObjectId.
- **key_flags 0x04 does not exist**; directories use 0x02 + dir bit 0x10000000.
- **type 0xF0** = USN journal $Max metadata (since v3.4). **type 0x20** = per-object FileId index.
- **$SI+0x50 PackedEaSize** = EA_INFO val[0x0C] (not val[0x10]). **$DATA stream_flags** =
 checksum type (0x02 CRC / 0x04 SHA-256) + integrity bit 0x10000.
- **"$CBW4" is fabricated** (only $EFS exists). **$DIR_LINK = $OBJ_LINK** (same structure).
- **E20 reaffirmed** (all ADS inline; a "non-resident ADS" claim was refuted by verification).

### Tool fixes

- **refsanalysis.py `_REPARSE_TAGS`**: full rebuild to authoritative ntifs.h values — the prior
 table was off-by-one / mislabeled throughout (0x8000001B = APPEXECLINK not WOF; 0x80000024 =
 LX_FIFO not AF_UNIX; 0x80000017 = WOF not NFS; etc.). `_decode_reparse_data` notes corrected.
 Resolves the old "lxfifo file with AF_UNIX tag" anomaly (it was always LX_FIFO).
- Non-resident extent resolver: investigated and confirmed **correct** (size-guarded, never
 returns wrong extents); the residual 12–20% unresolved is a completeness gap, tracked in
 `field_verdicts/TOOL_ISSUES.md`, intentionally not rewritten to avoid regression.

### Deep verification of lower-confidence items (2026-06-12)

Four secondary items were deepened (static + raw disk) and personally re-verified on disk:
- **$VOLUME_INFORMATION driver stamp** (finding FS_VOLI_RA_001): +0x82/0x83 = highest driver build that
 ever mounted the volume. CORRECTED a misattribution — a v3.4→Win11-RTM upgrade is vol=3.14/
 **drv=3.14 (equal)**; **drv=3.15 means an Insider build touched the volume** (forensic signal).
- **MI $DATA value layout** (finding MD_DATA_RA_011): summary_size@0x0C = **0x200** (not 0x30); value+0x50 =
 version-count+sparse-flag (not a cluster count).
- **Type 0xB0 attr-bit 0x0800** (finding MD_ATTR_RA_018): E2 bit-gate confirmed (SCB+0x98|0x80); prior
 "non-resident MinStore stream" reading REFUTED; meaning is static-only (never isolated on disk).
- **$SI 0x58–0x6F writers**: reconciled — NextFileId (8-byte, dir own-row, v<3.11) and the
 ExternalFileId path (24-byte, moved file's row, cross-volume) never collide.

## v3.1.0 — 2026-06-11

### MLog (Durable Log) Integration

Core parsing moved from standalone `refs_mlog.py` into `forefst.py` (canonical library). Display and command wired as `refsanalysis.py mlog`.

- **Redo opcode tables**: E2-verified dispatch tables for v3.14 (37 opcodes/43 values) and v3.4 (25 opcodes/27 values)
- **Control page parsing**: MLog signature, UUID, sequence, write counter, data area bounds
- **Data area scanning**: Page classification (MLog/MSB+/DATA/zero), payload extraction
- **Redo record extraction**: `_SmsRedoHeader` + `_SmsRedoRecord` parsing with opcode resolution
- **Transaction decoding** (`--parse`): Groups records into file operations (CREATE, DELETE, RENAME, WRITE, MOVE, etc.) with resolved directory paths and embedded timestamps
- **Output modes**: Default summary, `-v` verbose records, `--parse` transactions, `--csv`, `--json`, `--stats` opcode histogram, `--raw-scan` page dump, `--info` reference

### USN (Change) Journal Integration

Core parsing moved from standalone `refs_usn.py` into `forefst.py`. Display wired as `refsanalysis.py usn`.

- **Journal location**: Finds "Change Journal" entry in OID 0x520 (FS Metadata directory)
- **Sub-record parsing**: Extracts `$J` and `$Max` streams from embedded extent descriptors via VLCN container translation
- **USN_RECORD_V3 parsing**: 128-bit file IDs, 23 reason codes, source flags, file attributes
- **Output modes**: Default list, `--csv`, `--json`, `--stats` reason distribution, `--info` metadata + format reference
- Graceful handling of images without journals (expected for most volumes)

### Code Consolidation

- `build_oid_path_map()` — single implementation in forefst.py (replaces duplicate in refs_mlog.py and refs_usn.py)
- `KNOWN_SYSTEM_OIDS` — consolidated into forefst.py
- All parsing logic in forefst.py, all display logic in refsanalysis.py
- forefst.py: 1515 → 2428 lines (+913: MLog + USN core parsing)
- refsanalysis.py: 5063 → 5743 lines (+680: cmd_mlog + cmd_usn display)
- VERSION bumped to 3.1

### Verification

- Full test suite: 117 images × 24 commands = 2688 tests
- **Results**: 2563 PASS, 120 SKIP (112 NTFS/BitLocker + 8 no-GPT raw partitions), 5 TIMEOUT (winsider 147K-entry image on full-tree commands)
- **0 failures** across all ReFS images on all commands
- All 20 refsanalysis subcommands: 107 PASS, 0 FAIL on all ReFS images
- All 4 forefst modes (csv, body, enrich, deleted): 106 PASS on all testable ReFS images (winsider exceeds 120s timeout)
- `cmd_all` now includes mlog and usn in its sequence

### Documentation

- `structures/mlog.md`: Fixed control page payload offset model (variable via entry header, not fixed page offsets), corrected sequence field to u64, decoded `_SmsRedoRecord` offset 0x10 as value_component_count, expanded UpdateRow timestamp offsets and MODIFY opcode list, updated tooling section for integrated parser
- `structures/usn_journal.md`: Fixed minimum record size (80 bytes structural minimum, 96+ typical), clarified stream_count and sub-record offsets as version-specific observations, added tooling section
- `ntfs_comparison.md`: Added transaction classification and USN timeline analysis comparison points

## v3.0.5 — 2026-06-11

### Research Reports (6 lab reports)

**Phase 3 — v3.4 ADS format**: v3.4 uses fundamentally different sub-record format for ADS — embedded B+-tree subtable headers at ~0xA0 instead of 0x80000001/0x80000002 marker-based chains. Marker pattern writes found in v3.4 decompilation are ETW event flags and storage notification IRPs, not sub-record construction. v3.4 ADS detection requires separate format reverse engineering. Report: `report_v34_ads_detection.txt`.

**Phase 4 — $SI fields 0x50+ verification (5 corrections, E21)**: Verified 883 $SI entries across 5 images against RefsComputeStandardInformationFromFcb decompilation. Five field corrections discovered:
1. ReparseTag at $SI+0x54, NOT $SI+0x4C (0xa000000c for 367+ symlinks)
2. HardLinkCount at $SI+0x70, NOT $SI+0x48
3. $SI+0x48 is conditional u64 (always 0 unless FCB flag bit 23 set)
4. $SI+0x50 is u16-derived u32 (always 0), NOT lower half of SnapshotId
5. VersionRefCount ($SI+0x58) ranges 0–273
Report: `report_si_fields_verification.txt`.

**Phase 5 — Compression extent format**: Container-level compression mechanism identified. File extents on compressed volumes point to VLCNs that translate to B+-tree metadata pages, not file data. `_SmsContainerCompressionHeader` mediates via header+0x40 variable-length mapping data. Full decompression requires parsing the mapping data. Report: `report_compression_extent_format.txt`.

**Phase 6 — BRC (Block RefCount) semantics**: BRC key = start_lcn(u64) + block_count(u64, always 0x400). Per-cluster u16: bit 15 = shared/dedup-managed, bit 14 = dedup metadata, bits 13:0 = reference count (0–505 observed). Value header at +0x18 is a compound field (NOT simple total — upper bits contain flags). 97 BRC rows analyzed on dedup image. Report: `report_brc_semantics.txt`.

**Phase 7 — MLog opcode sequences**: Empirical mapping of opcode sequences to operations across 245K+ transactions. 15 opcodes observed on v3.14 disk (of 37 in dispatch), 12 on v3.4. Dominant patterns: CREATE = INSERT+INSERT+SET_OBJREC (99.9%); DELETE = DELETE or DEL_TABLE chain; RENAME = DELETE+INSERT pairs; MOVE = DELETE+REPARENT+INSERT. Key evolution: v3.4 uses 0x04 at 27% vs <0.1% in v3.14 (replaced by 0x10+0x1F). Report: `report_mlog_opcode_sequences.txt`.

**Phase 8 — Extended GUID survey**: VBR+0x48 Extended GUID populated on ALL native v3.10+ volumes (93/113 images). ZERO on v3.4/v3.7/v3.9 and upgraded volumes. Boundary is v3.10 (Win11 23H2), confirmed by 2 v3.10 images with non-zero GUIDs. Unique per format instance, never modified after format or upgrade. Forensically useful as format-instance identifier and upgrade detector. Report: `report_extended_guid_static.txt`.

### Reference Updates

- **errata.md**: Added E21 — $SI HardLinkCount and ReparseTag at wrong offsets (5 corrections)
- **structure_reference.md**: Corrected C.7 $SI tables (Common, Win10 extension, Win11 extension) with verified field positions; enriched VBR Extended GUID description (native v3.10+, not v3.14+ — confirmed original claim correct)
- **open_questions.md**: Marked A2 RESOLVED (5 corrections), B2 RESOLVED (opcode sequences mapped), B2c RESOLVED (refs_mlog.py complete), B4 PARTIALLY RESOLVED (BRC key/value decoded, compound field at val+0x18 needs refinement), C1 PARTIALLY RESOLVED (GUID survey complete, NVRAM relationship unknown)

### Tools

- **mlog_differential.py**: New script for comparing MLog transactions between consecutive disk images (differential analysis). Confirmed step5/testatomic images all have identical MLog (log checkpointed between operations).
- **verify_si_fields.py**: New script for verifying $SI extension fields across all directory entries in an image.

## v3.0.4 — 2026-06-10

### Alternate Data Streams (ADS)

**refsanalysis.py**: ADS detection and inline extraction.

- Detects ADS in directory entry values via multi-instance sub-records (descriptor 0x000500B0)
- Parses stream names (UTF-16LE), stream sizes, and inline content from the ADS sub-record header
- Filters out snapshot streams (storage_type != 0) that share the same 0x000500B0 descriptor
- `files` command lists ADS with stream name and size
- `extract` command supports `filename:streamname` syntax to extract ADS content
- Validated: 678 ADS across 41 images, all inline (7--47 bytes). SmartScreen tags (7 bytes, "Anaheim"), lab-generated `hidden_NNNN` streams (46--47 bytes). Zero extent-based ADS observed — original thesis claim "ADS always resident" confirmed

### Resident File Extraction

**refsanalysis.py**: `extract` command now supports resident files (key_flags=0x01).

- Resident entries with extent-based data (alloc_size >= cluster_size) are extracted via the same scan-based extent heuristic used for non-resident files
- Properly parses file_size (0x58), alloc_size (0x60), file_attrs (0x48), and timestamps (0x28--0x47) from resident directory entry values
- Empty resident files (file_size=0) handled cleanly
- Inline small files (alloc_size < cluster_size) reported with informative message
- Validated: ho.txt (15 bytes, 1-cluster), xbpt_beta_sierra_570651.json (71,395 bytes, 18-cluster)

### Bug Fixes

- **refs_mlog.py**: Fixed `remaining` over-count (`total_size` → `total_size - first_record_offset`) in two locations; added top-level exception handler; added guard for minimum record size
- **refs_usn.py**: Added top-level exception handler and stream_size sanity check

### Documentation

- **usn_journal.md**: Added 13 missing reason codes (complete Windows SDK set: 23 flags)
- **glossary.md**: Added USN, Change Journal, USN_RECORD_V3 entries
- **page_header.md**: Corrected: MLog does not share the common 80-byte header
- **mlog.md**: Fixed iteration pseudocode (`remaining = total_size - first_off`); corrected page header cross-reference

### Reference Updates

- **errata.md**: E20 retracted — "extent-based ADS" were actually snapshot streams (same 0x000500B0 descriptor, discriminated by storage_type). Original thesis claim "ADS always resident" confirmed across 678 entries / 41 images
- **findings_register.md**: MD_SNAP_RA_005, MD_SNAP_RA_006, MD_SNAP_RA_007 reverted to CONFIRMED — ADS are always resident

## v3.0.3 — 2026-06-10

### USN Journal Parser

**refs_usn.py**: Standalone USN (Change) Journal parser for ReFS (780 lines).

- Locates Change Journal file entry in OID 0x520 (FS Metadata directory)
- Extracts $J data stream via scan-based extent table detection (handles embedded non-resident sub-records)
- Parses USN_RECORD_V3 entries: 128-bit file IDs (OID:index), reason codes, FILETIME timestamps
- OID-to-path resolution via directory tree walk from root 0x600
- Output modes: `--list` (default), `--csv [FILE]`, `--json`, `--stats`, `--info`, `-v`
- Validated: 44/44 ground truth records match (USN values, filenames, reason codes, file IDs, record lengths)
- Tested on 6,874-record image (win11refs4gattributestest2.raw) and 46-record image (win11refslasttests.raw)
- Clean handling of non-USN images ("No Change Journal found")

**Key technical details**:
- Stream size read from multi-instance sub-record marker + 4 (le32)
- Extent table header located by pattern scan (sub_rec_size 0x28, flags 0xe00, count validation) — same heuristic as `_find_extents_in_subrecord` in refsanalysis.py
- Extents require VLCN→PLCN container translation (unlike MLog data area which uses physical LCNs)
- $J stream is pre-allocated at max journal size (128 MB typical); stream_size indicates valid data boundary
- USN_RECORD_V3: minimum 0x50 bytes, 8-byte aligned, no page headers, zero record_length = end of data

## v3.0.2 — 2026-06-09

### MLog Parser

**refs_mlog.py**: Standalone MLog parser rewritten from scratch (1240 lines), replacing the broken `refs_logfile.py` that had wrong opcode numbering (E10), unreliable detection, and no two-layer parsing.

**Core parser** (completed 2026-06-08):
- Correct dispatch tables from E2 decompilation: v3.4 (27 opcode values / 25 handlers), v3.14 (37 / 32), including gap opcodes
- Proper two-layer parsing: outer `_SmsRedoHeader` → inner `_SmsRedoRecord` via `ForEachRedoInBlock` logic
- Opcode read from `_SmsRedoRecord+0x04` (not heuristic scanning)
- Physical LCN addressing for data area (no container translation)
- Validated: 25/25 baseline images, 0 unknown opcodes, record counts 135–33,334

**Transaction analysis** (`--parse`, completed 2026-06-09):
- Groups redo records into per-page transactions (start → operations → commit)
- Classifies into 14 action types: CREATE, DELETE, RENAME, MOVE, WRITE, MODIFY, UPDATE, INSERT, ALLOCATE, STREAM_UPD, CONTAINER, DEDUP, EXTENT_MOD, OP
- OID-to-path resolution via directory tree walk from OID 0x600
- Filename extraction from InsertRow value data (3 formats: tpl=1/schema 0x0130, tpl=0, tpl=2)
- Timestamp extraction from InsertRow v1 (offsets 0x28–0x40), UpdateDataWithRoot v0, UpdateRow v1 (~65–80% coverage)

**Output modes**: `--csv [FILE]` (transaction export), `--info` (action/opcode/timestamp reference), `--stats`, `--json`, `--raw-scan`, `-v`

**Key discovery**: MLog data area LCNs are physical, not virtual — no container translation needed. MLog data pages use the same "MLog" signature as control pages, with entry header at `page+0x54`.

### Documentation

- **mlog.md**: Corrected v3.14 dispatch table (previous version had wrong handler names for most opcodes — e.g. 0x05 listed as "RedoUpdatePageReference" instead of "RedoReparentTable"). Added: physical addressing, data page format, two-layer record structure with field layouts, `ForEachRedoInBlock` iteration logic, transaction classification table, timestamp extraction details, key component layout, tooling section.
- **roadmap.md**: Updated MLog section with --parse/--csv/--info completion.

## v3.0.1 — 2026-06-09

### Post-Thesis Verification

**Static analysis sweep**: 78 reference_table.csv entries promoted from SA=NOT_TESTED (75 to CONFIRMED, 3 to ENRICHED) via automated verification against 4 mass decompilations and the function catalog. Verification script: `analysis/reports/verify_static.py`, results: `analysis/reports/report_static_verification.txt`.

**USN/Change Journal verification** (3 claims):
- **AP_CHJN_001** (RA: NOT_TESTED → CONFIRMED): Compared fresh image (1 row in OID 0x520) vs activated image (3 rows including "Change Journal" file entry). Journal is absent by default.
- **AP_CHJN_004** (RA: NOT_TESTED → CONFIRMED): Walked OID 0x520 B+-tree — type 0x30 key contains "Change Journal" filename in UTF-16LE, confirming storage location.
- **MD_ATTR_009** (RA: NOT_TESTED → ENRICHED): Change Journal entry observed with stream_count=3 in OID 0x520. Attribute name "$USN_INFO" is analyst-assigned (not directly confirmed on disk).

**OID 0x520 correction** (E19): OID 0x520 is an **FS Metadata directory** (schema 0x200, child of root 0x600), NOT "Security ID Mapping". Confirmed by raw disk analysis across 25 images (all show directory-style B+-tree entries: type 0x10 descriptor, type 0x30 filenames) and static analysis of 3 builds (security functions go directly to OID 0x530 via VCB+0xb0; `MsInitializeWellKnownObjectId` is never called with 0x520). Investigation script: `analysis/reports/investigate_oid_0x520.py`, results: `analysis/reports/report_oid_0x520_investigation.txt`. Version-dependent contents: v3.4 has 3 children ("Reparse Index", "Security Descriptor Stream", "Volume Direct IO File"); v3.9+ is empty; USN activation adds "Change Journal".

**OID 0x520 content study**: Deep analysis of all children across 10 images (v3.4 4K/64K, v3.7, v3.9, v3.10, v3.14 upgraded/USN/Insider). Identified degenerate children as backward-compatibility wrappers created by `CreateDownlevelDegenerateMetadataObjects` (flags: 0x400=Reparse, 0x200=Security, 0x100=DASD). Version boundary: exactly v3.7→v3.9 (threshold < 0x307). Mapped Change Journal sub-records: 2 multi-instance (data extents) + 1 single-instance (metadata). OID 0x521 confirmed not persisted to disk. Study script: `analysis/tools/analysis_scripts/study_oid_0x520_children.py`, report: `analysis/reports/report_oid_0x520_children.txt`.

**Documentation updates**: Corrected security resolution chain in `security_descriptors.md` (SecurityId → OID 0x530 directly). Expanded `system_oids.md` with degenerate child details, row structure, Change Journal sub-records, and OID 0x521 status. Updated `usn_journal.md` with Change Journal file entry structure. Added $Extend child-by-child mapping to `ntfs_comparison.md`. Updated `standard_information.md`, `README.md`. Added Subtable F.4c (OID 0x520 children) to `structure_reference.md`. Added E19 to errata, corrected finding FS_SECD_RA_002, MD_SECT_001.

**Errata reformatted**: Backed up previous flat-table format as `errata_backup_20260609.md`. New `errata.md` uses structured per-erratum sections with precise thesis location references (section numbers, table numbers, page numbers from `memoire.pdf`). 19 errata total (E1–E19).

**Tool fix**: `refsanalysis.py` `_KNOWN_OIDS[0x0520]` changed from "Security ID Mapping" to "FS Metadata". `_PC_OID_NAMES` already had the correct label.

**Regression testing**: 190/190 refsanalysis.py (19 subcommands × 10 images) + 30/30 forefst.py (3 modes × 10 images). Images: v3.4 4K/64K, v3.7, v3.14 4K/SHA-256, upgraded, Insider, USN-active.

**reference_table.csv**: SA distribution: CONFIRMED=304, ENRICHED=17, NOT_TESTED=28, NEW=3. RA distribution: CONFIRMED=204, ENRICHED=16, NOT_TESTED=95, INVALIDATED=2, NEW=35.

## v3.0 — 2026-06-09

Major release: `refsanalysis.py` rewritten from subprocess dispatcher to self-contained analysis tool.

### refsanalysis.py

**New architecture**: All 19 analysis subcommands plus `bootedit` are now integrated into a single 4,845-line Python file. Previously, each command was a separate script invoked via `subprocess`. The new version imports parsing functions from `forefst.py` and implements all analysis logic internally.

**New subcommands**:
- `summary++` — Extended volume summary with OID 0x500 detail (version, timestamps, schema count), container utilization, and file attribute statistics (encryption, integrity, compression, hard links, symlinks, snapshots, ADS)
- `bootedit` — Boot sector editor with `repair` (fixboot damage), `set` (field modification), `export`, and `sparse` modes

**Integrated subcommands** (formerly separate scripts):
- `chkp` (from refs_chkp.py) — Checkpoint analysis with container translation
- `objects` (from refs_object_table.py) — Object ID table dump
- `parentchild` (from refs_parentchild.py) — Parent-child relationships
- `containers` (from refs_container.py) — Container table analysis
- `files` (from refs_dirfiles.py) — Directory tree listing
- `attributes` (from refs_attributes.py) — File attribute details
- `dataruns` (from refs_dataruns.py) — File data extent mapping
- `extract` (from refs_dataruns.py) — File content extraction
- `security` (from refs_security.py) — Security descriptor dump
- `reparse` (from refs_reparse.py) — Reparse point analysis
- `deleted` (from refs_deleted.py) — Deleted file recovery
- `snapshots` (from refs_snapshots.py) — Stream snapshots and ADS
- `integrity` (from refs_integrity.py) — Metadata page verification

**Improvements over previous scripts**:
- `reparse`: Recursive directory walk finds reparse points in subdirectories (archive only scanned root level)
- `integrity`: Full B+-tree walk checks all reachable metadata pages (archive only checked 16 root pages)
- Volume label: Fixed key type detection (0x0510, was checking 0x0200)
- Output consistency: All commands use 78-char width, consistent header format

**Dropped subcommands**:
- `timeline` — Duplicate of `forefst.py --body`
- `logfile` — Broken opcode numbering (see E9/E10 in errata). Replaced by standalone `refs_mlog.py` (see v3.0.2)
- `fs` — Duplicate of `all`
- `roots` — Redundant (each root has dedicated tool)
- `volume` — Merged into `summary++`

### Bug Fixes

- **Root 12 addressing**: `_CT_ROOT_INDICES` now includes root 12 (Small Allocator). Previously, root 12 VLCNs were incorrectly translated through the Container Table instead of being treated as physical LCNs.
- **Partition start type**: `--partition-start` value now converted to int immediately. Previously passed as string to `bootstrap()`, causing a crash.
- **GUID parsing**: `_guid_to_text()` wraps bytearray in `bytes()` before passing to `uuid.UUID(bytes_le=)`. Fixes crash in `bootedit repair`.
- **Deleted scan offsets**: `_scan_for_deleted_entries` now adds partition start offset before physical seeks. Previously scanned from byte 0 of the image file.
- **File handle leaks**: All 15 `cmd_*` functions using `bootstrap()` now use `try/finally` for cleanup.
- **Extract allocation cap**: 4 GiB cap on `cmd_extract` buffer allocation prevents OOM on malformed data.
- **Argument validation**: `_int_arg()` helper provides clear error messages for all user-facing integer arguments (`--oid`, `--depth`, `--sid`, `--tag`, `--max-scan`).
- **OID 0x520 label**: Corrected from "Security ID Mapping" to "FS Metadata".
- **Dead code removal**: Removed `tr.translate()` fallback calls (3 sites) — `tr.tr()` is the only method.
- **Extract help text**: Clarified `--oid` scopes directory walk root, not "extract by OID".
- **Schema 0x160 name**: Simplified from "Reparse Index (fka Security Descriptor)" to "Reparse Index".

### Documentation

- **Address translation formula** (E18): Corrected `log2(CPC)` to `CPC.bit_length()` across 4 documentation files. Shift values updated from 14/10 to 15/11.
- **Failover pair numbering**: Corrected Object Table (roots 0/5) and Schema Table (roots 3/9) in checksum_architecture.md.
- **MLog redo opcodes**: Updated from "19 catalogued" to full dispatch tables (32 handlers / 37 opcodes for v3.14, 25/27 for v3.4).
- **OID 0x500 key types**: Added Subtable F.4b to structure_reference.md documenting key types 0x0510, 0x0520, 0x0540.
- **Volume Information**: Expanded volume_info.md with key type layouts, decoded offsets, and driver function references.
- **New pages**: `docs/tools/refsanalysis.md`, `docs/tools/forefst.md` — complete tool documentation with architecture overview and custom script guide.
- **Examples**: Updated all example outputs with larger disk images (2 TiB specials images replacing 1.9 GiB mini baselines).

### Test Coverage

190 tests (10 images x 19 commands) across:
- v3.4 4K, v3.4 64K, v3.14 4K, v3.14 64K, minimal baseline
- Insider (SHA-256, 64K clusters), reparse-heavy (344 symlinks)
- LZ4 compression, upgraded (v3.4 to v3.14)

### forefst.py

No changes. Verified identical to pre-integration version.
