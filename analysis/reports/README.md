# Reports (generated)

> **`CERTIFICATION.md`** is the one **authored** file here — the forefst soundness certification (v3.5.0, 2026-07-01): the verdict, what was delivered, the verification gates, and the audit trail. Everything else in this directory is machine-regenerated evidence.

Machine-regenerated verification outputs — **not** authored documentation. They are overwritten on every gate
run; treat them as the latest evidence snapshot, not a stable reference.

| File | Produced by | What it shows |
|------|-------------|---------------|
| `report_static_claims.txt` | `verify_docs_static.py` | Static-claim checks (function/symbol counts, version gating) — PASS/WARN/FAIL |
| `report_tool_execution.txt` | `verify_docs_tools.py` | Tool execution log (commands, exit codes, timing) over the image corpus |
| `report_tool_claims.txt` | `verify_docs_tools.py` | Tool-verified claim results — PASS/FAIL/SKIP |
| `report_summary.txt` | manual roll-up | Pre-publication summary |
| `report_static_verification.txt` | `verify_static.py` | Static-evidence pass over the reference-table `NOT_TESTED` entries (decompilation + function-catalog search) — PASS/WARN/FAIL |
| `report_oid_0x520_*.txt` | ad-hoc probe (`investigate_oid_0x520.py`) | Historical OID 0x520 (Change Journal / FS Metadata directory) investigation |

Regenerate (from the repo root): `python3 analysis/reports/verify_docs_static.py` and `python3 analysis/reports/verify_docs_tools.py`.

> Regeneration runs only against the private disk corpus and the Ghidra / decompiled exports, which are **not** bundled in this repository; point the scripts at a local copy via `REFS_DISKS` / `REFS_CORPUS` / `REFS_GHIDRA` / `REFS_DECOMPILED` / `REFS_FUNC_CATALOG`.
>
> The ~29,761-row function catalog is not bundled. `verify_docs_static.py` resolves it in order: `REFS_FUNC_CATALOG` → `forefst/analysis/function_catalog.csv` (drop a copy here) → `<corpus>/forclaude/intelligence/function_catalog.csv` (the workspace copy). If none is found it exits non-zero with a message naming the env override — it no longer aborts with a traceback.

A third gate, **`verify_tool_tables.py`** (in this directory) — reference-table consistency, asserts the tools' embedded opcode/schema/
OID/flag name maps against the master + decompilation), is **stdout-only** and writes no report file here; run it
alongside the two above (`--calibrate` proves it fires on planted errors).

Three more scripts in this directory verify reference-table claims directly: `verify_static.py` produces `report_static_verification.txt` (above); `verify_usn_claims.py` (USN / Change-Journal claims) and `verify_not_tested.py` (the remaining both-`NOT_TESTED` entries) are **stdout-only** and write no report file here.

## The `audit/` subdirectory

Where the reports above are machine-regenerated gate output, [`audit/`](audit/README.md) holds the
**authored audit deliverables** — the record of how the published knowledge and tools were validated
against ground truth (raw-disk bytes + decompilation), adversarially and with calibrated instruments.
It covers **four audits**: references & central findings, the analysis tree, the documentation, and
the tools. Full account in [audit/README.md](audit/README.md); the key contents:

| Path | What it is |
|------|-----------|
| `AUDIT_COMPLETE.md` | Headline result — 409/409 reference-table claims audited, 0 byte-layout failures |
| `proof_index.csv` | Master crosswalk: each claim → class, verdict, static proof, disk validation, dossier |
| `dossiers/<ref_id>.md` | Per-claim dossier — canonical claim, verdict, static + disk proof (one per claim) |
| `proofs/static/` | Exported decompiled functions backing the static/decompilation claims |
| `proofs/validation/<ref_id>.csv` | Per-claim **disk-corpus matrix**: one row per applicable image (`path,basename,group,result,value`). Header-only when a claim is proven by citation/decompilation rather than disk measurement — so ~285/411 are header-only by design, not missing data |
| `audit_harness.py` + `specs.jsonl` | Regenerate every matrix/dossier/index from the authored specs (`python3 audit/audit_harness.py`) |
| `tool_audit.md`, `analysis_consistency_audit.md` | The tool-correctness audit and analysis-tree consistency audit write-ups |

See also: [repo README](../../README.md)
