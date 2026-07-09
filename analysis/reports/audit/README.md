# How the Knowledge and Tools Were Audited

This project's published knowledge (the docs + their central reference) and its forensic tools were validated by
**four distinct audits**. All of them gate on **ground truth** — raw-disk bytes (and, for the tools' baked-in
reference tables, the decompilation/master) — never exit codes; use **adversarial re-verification** (default "not
confirmed" until independently re-measured); and were **calibrated for sensitivity** before any verdict was trusted.
Together they are why the docs and tools can be published as a forensic reference.

| # | Audit area | What it validated | Result here |
|---|-----------|-------------------|-------------|
| 1 | **References & central findings** | every claim in `reference_table.csv` + the master structure reference | [AUDIT_COMPLETE.md](AUDIT_COMPLETE.md), `proof_index.csv`, `dossiers/`, `proofs/validation/` |
| 2 | **The analysis tree** | `analysis/` consistency (corpus, lab, scripts, reference table) | [analysis_consistency_audit.md](analysis_consistency_audit.md) |
| 3 | **The documentation** | every authored `docs/` page's prose against ground truth (two passes) | corrections folded into the docs + `changelog.md` |
| 4 | **The tools** | `forefst.py` / `refsanalysis.py` correctness — every option × every image, **plus their embedded reference tables** | [tool_audit.md](tool_audit.md), `verify_tool_tables.py` |

---

## Area 1 — References & central findings

Two complementary programs validate the byte-level source of truth that every doc page cites.

### Program A — Claim audit (the 409 `reference_table.csv` claims)

Audits every claim in the reference table → a spec → a proof (disk matrix / exported decompiled function / sourced
citation) → a corpus-aware verdict. Result: **409 / 409 audited, 0 byte-layout failures**, 5 CONTESTED-by-design
(documented corrections), disk-validated across the ReFS image corpus.

| File | Role |
|------|------|
| [AUDIT_COMPLETE.md](AUDIT_COMPLETE.md) | Headline result + the numbers (409/409, verdict distribution, the 5 CONTESTED) |
| `proof_index.csv` | Master table: claim → class, verdict, n_pass/n_applicable, correspondence, artifact |
| `proof_links.csv` | Many-to-many claim ↔ proof artifact |
| `specs.jsonl` | The 409 authored specs (harness input) |
| `audit_harness.py` | Regenerates all matrices/dossiers/index from `specs.jsonl` |
| `images.csv` | The image-corpus manifest |
| `dossiers/<ref_id>.md` | Per-claim dossier (claim ↔ canonical claim, verdict, static + disk proof) |
| `proofs/static/`, `proofs/validation/<ref_id>.csv` | Exported decompiled functions + per-claim corpus matrices |

**Regenerate:** `python3 audit_harness.py` (the ref_id↔claim correspondence gate rejects any ref_id not in
`reference_table.csv`).

### Program B — Master structure-reference audit (3 independent passes + calibration)

The master byte-level reference was independently verified in three passes — a section-split first pass, then a
second pass that broke raw-read circularity (catching 13 errors, including two structural ones), then a converged
third pass plus a per-build class-table rebuild and the 0x1F0 schema-vs-attribute resolution. The passes converged to
**zero byte-layout defects**, and a calibration confirmed the instrument is sensitive (**10/10 planted errors
caught, 3/3 structural**). The detailed pass-by-pass working notes are kept with the project's internal records and
are not part of this published repository; their net result is reflected in the master reference and
`reference_table.csv`.

---

## Area 2 — The analysis tree

→ **[analysis_consistency_audit.md](analysis_consistency_audit.md)**. Verifies that the published `analysis/`
tree (corpus evidence, lab generation harness, reference table, research scripts) is internally consistent,
consistent with its dev source, and consistent with the canonical reference registry. Verdict: consistent (one
4-row `reference_table.csv` reconciliation applied).

---

## Area 3 — The documentation

The authored `docs/` prose was audited in **two passes**: a first pass cross-checking each page's prose against the
reference (21 corrections applied, the post-thesis errata verified), then a whole-content adversarial re-review after
the overhaul in which every claim was re-checked against the master with independent verification → 45 confirmed
issues + 2 example errors, **64 fixes applied**, gates green. All corrections were folded into the published docs and
recorded in `changelog.md`.

---

## Area 4 — The tools

→ **[tool_audit.md](tool_audit.md)**. A full-census correctness audit of `forefst.py` / `refsanalysis.py`: every
option on every image (**13,356 command cells**), each output verified for correctness against independent oracles
and cross-tool consistency, with a strict re-run → second-source → raw-bytes → decompilation discrepancy protocol.
Verdict: the tools are sound (13 stale-matrix mismatches, 35 expected states); **3 real tool bugs found and fixed**.

A second, complementary check — **`analysis/reports/verify_tool_tables.py`** — closes a blind spot the census audit cannot see:
the census verifies values *parsed from disk*, but not the tools' own **hardcoded reference tables** (opcode/schema/
OID/flag name maps). This gate asserts those against the master + decompilation — the gap that had let a stale
`0x17 → STATUS_LOG_CORRUPTION` label and a fabricated `$CBW4` name survive in the tool *source* unnoticed. **22 PASS /
0 FAIL**, with a `--calibrate` mode that proves it fires on planted errors. Run it alongside the two doc gates.

---

## Calibration (why the verdicts carry weight)

Every audit validated its own instrument before trusting it. The reference audits' first calibration was a
measurement defect (an under-powered calibration setup); the corrected re-run caught **10/10 planted errors, 3/3
structural**. The tool audit caught **4 checker false-positives** during calibration (a CSV header read as data, the
boot sector's `SHA-256:` hash line matching on every image, a header counted as a data row, and a join on OID — which
is not unique because resident files share the parent OID) before any tool finding was accepted. In every audit a
finding is "not confirmed" until independently re-measured against the bytes — a flag is not a fix.
