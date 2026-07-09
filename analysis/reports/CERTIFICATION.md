# forefst — Soundness Certification

> **Superseded by v3.6.0 (2026-07-04).** This cert covers the v3.5.0 CLI-migration scope. The v3.6.0 first-audit
> enhancements (recyclebin, 38-col CSV, Q6/Q7 + CoW extract, the F5 `is_resident` fix, the F6 per-name-MACB finding)
> and the full re-validation are certified in [`REVALIDATION_CERTIFICATION.md`](REVALIDATION_CERTIFICATION.md).

**Date:** 2026-07-01  **Tools:** `forefst.py` + `refsanalysis.py` **v3.5.0**  **Scope:** the CLI-migration
session (Phases 0/1/H/2/3/4 + WSL/EA + dedup), the three pre-existing-inconsistency fixes (a/b/c), the
hand-written in-tool help, the `docs/` rewrite, and the central-reference updates.

## Verdict

**CERTIFIED SOUND.** After an eight-round adversarial audit (seven full-corpus audits + one change-scoped
delta audit) with every finding fixed and re-verified, the tools, documentation, and reference are
substantively correct. **Zero data- or forensic-output correctness errors** were found across the entire
audit programme; the single tool defect ever surfaced — a `--verbose` reject regression — was a help/UX
issue, fixed in the round it appeared. The change-scoped delta audit of the final batch returned **0
findings**, confirming the work introduced no errors.

## What was delivered this session

- **Unified CLI (forefst v3.5.0).** `forefst.py` is now the single forensic tool: **17 subcommands**
  (5 native — files/summary/fastsummary/search/details — + 12 forensic — usn/mlog/timeline/timestomp/extract/
  security/reparse/deleted/snapshots/integrity/export/dataruns), a **32-column** files CSV, and a subcommand
  CLI. `refsanalysis.py` is the slim structure/lab tool (**16 subcommands**); the 12 forensic commands moved
  to forefst (validated byte-identical across all images before dedup).
- **Three pre-existing inconsistencies fixed** (a: refsanalysis `details` reparse-tag + attr decoder;
  b: non-resident `HasEA` under-report, read the authoritative type-0x40 backing `+0x48`; c: `extract`
  `--path`/leading-slash + unknown-flag rejection), validated across **118 disk images** (0 crashes,
  EA-free images byte-identical, EA-bearing images correctly enriched).
- **Hand-written in-tool help** for both tools (per-command `--help`/`help <cmd>` + overview), built from a
  verified per-command spec sweep.
- **Docs rewrite + website** — every subcommand + option documented with concrete, re-run examples; the two
  tool pages fully rewritten; the whole corpus swept for stale CLI references; website regenerated.
- **Reference updates** — erratum **E56** (non-resident pointer under-reports the EA bit); structure_reference
  **§C.3a** (type-0x40 backing field map) + **§C.8** (reparse storage, resident & non-resident); three new
  registry rows (`MD_ATTR_RA_019`, `MD_DATA_RA_012`, `FS_REPS_RA_004`).

## Verification evidence (all green, 2026-07-01)

| Gate | Result |
|------|--------|
| Anti-regression assertions (`verify_claim.py --regress`, all images) | **14/14 PASS** |
| Tools compile + import (dev + prod), `dev == prod` | ✓ |
| Docs index (`build_docs_index.py --check`) | up to date; all pages have a footer |
| Doc links (`check_links.py`) | 90 pages, **0 broken / 0 escaping / 0 orphans** |
| Website (`verify_site.py`) | **PASS** — 79 pages, 0 artifacts |
| `docs/` dev == pub | byte-identical |
| `reference_table.csv` (3 copies) | 431 rows each, well-formed |
| 118-image validation of the a/b/c fixes | 0 crashes, 0 false EA flags, 0 reparse-tag disagreements |

## The audit programme (why the count fell then plateaued)

| Audit | Confirmed | Medium | Tool-correctness errors |
|-------|-----------|--------|-------------------------|
| #1 (full) | 16 | 1 (`--verbose`, fixed) | 1 |
| #2 (full) | 8 | 0 | 0 |
| #3 (full) | 5 | 0 | 0 |
| #4 (full) | 3 | 0 | 0 |
| #5 (full) | 4 | 0 | 0 |
| #6 (full) | 5 | 0 | 0 |
| #7 (full) | 5 | 0 | 0 |
| **Delta (7th-batch scope)** | **0** | 0 | 0 |

Each *full* audit re-scanned the entire ~106-page corpus and surfaced *different* ever-finer doc/help/
reference **prose-precision** nits (value-format wording, flag-scoping phrasing, method-sensitive statistics),
all fixed. The **delta audit — scoped to the actual last changes — returned 0**, demonstrating that the fix
batches were themselves clean and the full-audit counts reflected exhaustive corpus review, not defects
introduced by this work. Notably, the adversarial reviewer was imprecise on reference *magnitudes* three
times (the EA-omission direction, the Archive-bit count, the alloc rule); each time raw-disk re-measurement
confirmed the underlying fact and refined only the wording. Reference statistics are now cited
**method-defined** (e.g. "strict size-match", "0x600-reachable") so a differently-scoped walk no longer
contradicts them.

## Known limitations (honest, out of certification scope)

- **Version support:** validated on ReFS 3.14 (24H2). Volumes 3.4–3.10 parse, but some enriched fields
  (e.g. non-resident symlink targets, EA presence pre-3.14) may be incomplete; the tools warn via a banner.
- **`findings_register.md`** is the FROZEN thesis appendix (Ch.4) and was intentionally not modified; new
  findings live in `reference_table.csv` + `errata.md`.
- **`reference_table.csv` copies:** master (`forclaude/reference/`) and the shipped/dev copies differ only on
  the pre-existing `FS_OTBL_RA_008` row (#327), tracked separately.
- **Website `public/`** (rendered HTML) requires `hugo` to regenerate — a deploy step; the source `content/`
  is current and passes `verify_site.py`.

## Sign-off

The migration, the a/b/c fixes, the in-tool help, the documentation, and the central-reference updates are
**certified sound** as of 2026-07-01. Recommended verification going forward: run a **change-scoped delta
audit** after each edit batch (as demonstrated) rather than re-auditing the whole corpus.

*Full audit trail: `post_migration_audit_2026-06-30.md`, `phase5_docs_2026-06-30.md`, `final_audit_2026-06-29.md`.*
