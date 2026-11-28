# Archived validation records

None of these describes the current release. Each checked the tools, the register or the documentation as they stood
at its date; what it found has since been corrected or confirmed, and the current state is in the register
(`analysis/reference_table.csv`), the errata (`analysis/errata.md`) and the documentation.

| Folder | Made | Checked |
|---|---|---|
| [`2026-06_claim_audit/`](2026-06_claim_audit/README.md) | June 2026 | the 409 register rows of that time, the analysis tree, the documentation, the tools (release 3.x numbering) |
| [`2026-06_generated_reports/`](2026-06_generated_reports/README.md) | June-July 2026 | machine-generated check outputs of that time, and their scripts |
| [`2026-07_self_validations/`](2026-07_self_validations/README.md) | 2026-07-01, 2026-07-04 | releases 3.5.0 and 3.6.0, with the project's own instruments |
| [`2026-09_blind_audit_of_1.12.3/`](2026-09_blind_audit_of_1.12.3/README.md) | September-November 2026 | the answer to the blind audit of release 1.12.3: every finding and where its answer can be checked |

Two things the later work showed about these records, so that they are read for what they are:

- the July self-validations reported the tools sound; the blind audit of September 2026 found 215 defects in release
  1.12.3, 207 of them in this project's tools, pages and reference;
- the June claim audit graded rows "confirmed on all disks" that its own matrices do not support: 72 of its 174
  `CONFIRMED-ALLDISK` verdicts have no passing image in `proof_index.csv`, and one row it passed on 112 of 112 images
  (the superblock has no self-checksum) is false.
