# Tool Correctness Audit — `forefst.py` + `refsanalysis.py`

*Published snapshot. Canonical report + harness: `analysis/reports/tool_audit_2026-06-15/`.*

A full-census correctness audit of the two production tools: **every option of `forefst.py` (20) and
`refsanalysis.py` (28 subcommands / ~45 options) run on every ReFS disk image**, with each output verified for
**correctness** — not merely that it ran without error — against independent oracles and for cross-tool / internal
consistency.

## Verdict

**The tools' core logic is sound.** Across **13,356 executed command cells** (every applicable option run against every image in the corpus) and ~51 investigated discrepancies, every feature-detection, integrity, USN, parent-child,
format, and regression "mismatch" resolved **in favour of the tools**. **3 real, adversarially-verified tool bugs**
were found — none in a core decode path — and **all 3 were fixed, re-tested, and shipped**.

| Classification | Count |
|----------------|-------|
| TOOL_BUG (confirmed, byte-proven, **all fixed**) | 3 |
| ORACLE_STALE (the feature matrix was wrong, the tool right) | 13 |
| EXPECTED (corrupt/salvage/degenerate/empty images, genuine absence) | 35 |
| DOC_ERROR | 0 |

Post-fix gates (from `forefst/`): `verify_docs_static.py` **52 PASS / 0 FAIL**, `verify_docs_tools.py` **453 PASS /
0 FAIL / 1 SKIP**; tool files byte-identical dev↔pub.

## Method — 6 layers over a full census + a strict discrepancy protocol

- **Census:** `analysis/tools/audit_tools/census_runner.py` captured `{rc, stdout, stderr, wall, sha}` for every
 (tool, option, image) cell. Resumable, parallel, timeout-bounded; `bootedit` write-modes and all `export`/`extract`
 sandboxed to temp — **no image was ever mutated**.
- **Layers:** L0 execution · L1 cross-tool consistency · L2 internal invariants · L3 ground-truth oracles ·
 L4 regression vs the prior `analysis/rawdisk/runs/` outputs · L5 negative/edge.
- **Oracles:** fsactivity manifest · testatomic differential chain · USN journal · MFTECmd/NTFS exports ·
 `image_feature_matrix.csv` · `structure_reference.md`/`errata.md`.
- **Discrepancy protocol (every candidate):** re-run → verify a second way (another tool **and** raw image bytes via
 `struct.unpack`) → consult the decompilation / master reference → root-cause → classify. A TOOL_BUG verdict
 **required byte-level proof** and was then **adversarially re-verified by an independent skeptic check** before counting.
- **Calibration:** the checkers themselves were validated first — this caught **4 checker false-positives** (a CSV
 header read as data, the boot sector's `SHA-256:` hash line matching on every image, a header counted as a data row,
 and a join on OID which is *not* unique because resident files share the parent OID). A flag is not a fix.

## The 3 confirmed bugs (all fixed + re-tested)

1. **[MAJOR] MLog/timeline OOM on large logs** — `scan_mlog_data_area` materialised the whole 1 GiB log + a dead
 record list (~2 GB RSS), OOM-killing the 334k-entry volume. Fixed by making it a **generator** (streaming
 consumers) + gating the dead code. Re-test: `mlog --csv` on that volume now **rc=0, 8 s, 513 MB** (was rc=-9 ~2 GB);
 all mlog/timeline output byte-identical on normal images.
2. **[MINOR] `details ./name` rejected** — `resolve_path` kept `.` segments, so the path forefst's own `--jsonl`
 emits failed. Fixed (drop `.` segments). Now rc=0.
3. **[MINOR] `attributes` under-reported non-resident files** — an early return skipped EFS/compress/reparse/EA flag
 derivation on the non-resident branch (`EFS encrypted: 0` while the detail view showed ENCRYPTED). Fixed; summary
 and detail now agree.

## What the tools get right (byte-proven)

CRC64/SHA-256 metadata integrity (the 22 rc=2 cells are the tool *correctly* flagging deliberately-corrupted /
dirty volumes), VLCN→PLCN container translation, the USN parser (FileId / reason / monotonicity), CSV⇔JSON⇔JSONL
format consistency, cross-version VBR/CHKP/SUPB/Object-Table parsing (the one regression-diff was the *old* tool's
64K-cluster bug the current tool fixes), and graceful refusal of NTFS / BitLocker / empty-stub images.

## Oracle note

The `image_feature_matrix.csv` snapshot/hardlink/EFS columns were derived from `fsutil` **capability** advertising
("Supports Hard Links"), not on-disk content — the source of the 13 ORACLE_STALE classifications. Recommendation:
regenerate those columns from on-disk scans so future audits don't see false mismatches.

## Reference-table consistency gate (2026-06-16)

The census audit verifies values **parsed from disk**. It does **not** verify the tools' own **hardcoded reference
tables** (opcode/schema/OID/flag name maps) against the master — a blind spot that let a stale `0x17 →
STATUS_LOG_CORRUPTION` label (decompilation: `0x17` returns `0xC0000427`) and a fabricated `$CBW4` attribute name
survive in the tool *source* unnoticed. A new gate **`analysis/reports/verify_tool_tables.py`** closes it: it imports the tools'
map objects and asserts a curated set of project-corrected facts (each cited to an erratum/master section) plus
structural self-consistency (contiguous opcode range, no orphan category label, cross-tool map agreement, single
imported source). **22 PASS / 0 FAIL**, and a `--calibrate` mode confirms it fires on planted errors (including the two
real stragglers). Run it alongside `verify_docs_static.py` / `verify_docs_tools.py`.

## Reproduce

`python3 analysis/tools/audit_tools/census_runner.py` populates the census; the checkers (`consistency_checks.py`,
`oracle_feature_matrix.py`, `oracle_manifest.py`, `oracle_differential.py`) emit verdicts; the root-cause pass is
`analysis/reports/tool_audit_2026-06-15/p5_rootcause_workflow.js`. Full report: `analysis/reports/tool_audit_2026-06-15/REPORT.md`.
The gates: `analysis/reports/verify_docs_static.py` · `analysis/reports/verify_docs_tools.py` · `analysis/reports/verify_tool_tables.py` (run from `forefst/`).
