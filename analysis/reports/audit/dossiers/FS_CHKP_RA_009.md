# Dossier — FS_CHKP_RA_009 (BEHAVIORAL)

**Claim (this audit tests):** CHKP flag 0x2000: Windows Insider only (build 29574+). Present on all insider-formatted and insider-upgraded disks. Absent on Win11 24H2 (build 26200). Related to CmsVolumeAttestation/CmsRollbackProtection

**Canonical claim (reference_table.csv):** File System: CHKP flag 0x2000: Windows Insider only (build 29574+). Present on all insider-formatted and insider-upgraded disks. Absent on Win11 24H2 (build 26200). Related to CmsVolumeAttestation/CmsRollbackProtection

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP flag 0x2000 set on 3/3 insider images and 0/45 non-insider images (perfect correlation).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Checkpoint] CHKP flag 0x2000: Windows Insider only (build 29574+). Present on all insider-formatted and insider-upgraded d — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_CHKP_RA_009.csv`
- corrected registry note: 6 insider images all have 0x2000 set. See report_checkpoint_deep_analysis.md

## Proof links
- `proofs/validation/FS_CHKP_RA_009.csv` (matrix) — 
