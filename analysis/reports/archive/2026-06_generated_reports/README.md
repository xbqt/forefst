# Generated verification reports, June-July 2026 (archived)

Machine-generated verification outputs of June and July 2026 -- **not** authored documentation, and not a current
result: they were written by the scripts below and have not been regenerated since. The scripts are kept as they
were, for the record; they were written for the tools and the register of that time and are not maintained.

| File | Produced by | What it shows |
|------|-------------|---------------|
| `report_static_claims.txt` | `verify_static_claims.py` | Static-claim checks (function/symbol counts, version gating) — PASS/WARN/FAIL |
| `report_tool_execution.txt` | `verify_docs_tools.py` | Tool execution log (commands, exit codes, timing) over the image corpus |
| `report_tool_claims.txt` | `verify_docs_tools.py` | Tool-verified claim results — PASS/FAIL/SKIP |
| `report_summary.txt` | manual roll-up | Pre-publication summary |
| `report_static_verification.txt` | `verify_static.py` | Static-evidence pass over the reference-table `NOT_TESTED` entries (decompilation + function-catalog search) — PASS/WARN/FAIL |
| `report_oid_0x520_*.txt` | ad-hoc probe (`investigate_oid_0x520.py`) | Historical OID 0x520 (Change Journal / FS Metadata directory) investigation |

`verify_tool_tables.py` (the tools' embedded name maps against the master and the decompilation), `verify_usn_claims.py`
and `verify_not_tested.py` wrote to stdout only. Regeneration needed the private disk corpus and the Ghidra and
decompiled exports, which are not in this repository.
