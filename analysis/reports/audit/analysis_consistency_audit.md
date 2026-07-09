# Analysis-Tree Consistency Audit — `analysis/` (published as `forefst/analysis/`)

*Published snapshot. Source material: `analysis/reports/` (field re-analysis + registry-consolidation reports).*

Verifies that the published analysis tree (`forefst/analysis/`: the corpus evidence, the lab generation harness,
the reference table, and the research scripts) is internally consistent, consistent with its dev source, and
consistent with the corrected central reference registry.

## Verdict: consistent (one stale-row reconciliation applied)

| Dimension | Result |
|-----------|--------|
| dev↔pub structure | **Consistent** — differs only by an intentional curation (pub moved working scripts into `archive/scripts/`, keeping the live `refs_mlog.py`/`refs_usn.py` in `scripts/`). `reference_table.csv` byte-identical dev↔pub. |
| Internal documentation | **Consistent** — cross-document counts agree (118 images / 562 tool outputs / 16 evidence files); `lab/disk_generation.md` correctly records `--targetbus virtio`; `scripts/README.md` correctly flags the legacy `refs_logfile_v2.py` as superseded. No references to missing files. |
| Corpus subdirectories | **Consistent** — `bootstrap/`, `version_evolution/`, `cross_version_upgrade/`, `checksum_variants/`, `file_attributes/` each contain exactly what `corpus_description.md` / `corpus/README.md` describe (CHKP-flag evolution table verified against the captured outputs). |
| `reference_table.csv` vs canonical registry | **Reconciled** — 4 rows were stale (see below) and were brought into line with the canonical `reference_table.csv`. |

## The reconciliation

The published `reference_table.csv` (409 rows) lagged the canonical registry on **4 rows** — corrections made during
this session's reference/tool audits that had not been propagated. Each canonical value is byte-/catalog-verified;
the 4 rows were updated (in both the dev and published copies) to match:

| Row | Was (stale) | Now (canonical, verified) |
|-----|-------------|---------------------------|
| `FS_CHKP_020` | CmsIntegrityState "17 Win10 / 66 Win11" | win10=17, win11=12, insider=13 (a contraction, not growth) — `function_catalog.csv` |
| `CT_INTS_001` | "17/66 funcs" | win10=17, win11=12, insider=13 |
| `FS_SCHM_RA_007` | schema 0xF0 "present since v3.4" | absent on v3.4–v3.10 schema tables, present on v3.14+/Insider (; cf. erratum E44) |
| `FS_SCHM_RA_011` | totals v3.4=27 / v3.7=30 / v3.9=31 / v3.10=30 | v3.4=25 / v3.7=28 / v3.9=29 / v3.10=28 / v3.14=29 / Insider=30 (master §B.4) |

The frozen thesis snapshot `analysis/archive/reference_table_thesis.csv` was **not** touched.

## Scope note

This audit covers structural/consistency integrity of the analysis tree. The *claims* the analysis tree records are
audited separately and exhaustively under **Area 1** (the 409-claim audit + the `structure_reference.md` audit); the
deep $SI / attribute field re-analysis that produced several of the reconciled values is documented in
`analysis/reports/` (`report_field_reanalysis_2026-06-12.md`, `audit_si_claims.md`, `audit_structures_registries.md`).
