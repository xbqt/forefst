# analysis/ — laboratory materials & verification harness

Everything needed to reproduce and audit the structural analysis behind `forefst.py` /
`refsanalysis.py`. The two tools at the repository root do **not** depend on anything here.

## Contents

| Path | What it holds |
|------|---------------|
| [`reference_table.csv`](reference_table.csv) | The central claim register — 503 structural claims, each with a raw-disk verification status and an evidence level. **This is the live reference.** |
| [`reports/`](reports/README.md) | The validation record. Its [`archive/`](reports/archive/README.md) keeps the earlier records, each named by its date and what it checked: the June 2026 claim audit (claim specs, proof index, per-claim dossiers, validation matrices), the generated reports and scripts of June-July 2026, the July self-validations, the answer to the blind audit of release 1.12.3. |
| [`lab/`](lab/) | VM setup, ReFS disk-generation procedure, and the `Generate-FSActivity.ps1` activity generator + baseline replay file. |
| [`samples/`](samples/) | Example `forefst`/`refsanalysis` output captured against corpus images, plus [`samples/corpus/`](samples/corpus/) — per-structure output across versions/checksums/upgrade. |

## Note on the disk corpus

The raw ReFS disk images themselves (`*.raw`, 112 parseable ReFS volumes + 6 non-parseable negative tests) are **not
distributed** with this repository — they are large and lab-generated. The verification scripts and
proof artifacts reference those images by name as provenance; to re-run them, point the scripts at
your own corpus via the `REFS_DISKS` / `REFS_CORPUS` environment variables (see each script's
header). The `lab/` procedures let you regenerate an equivalent corpus.
