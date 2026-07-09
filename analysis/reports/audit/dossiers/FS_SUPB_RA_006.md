# Dossier — FS_SUPB_RA_006 (BEHAVIORAL)

**Claim (this audit tests):** Mount on clean volume triggers ~27 checkpoint increments and ~82 page writes. CHKP virtual clock advanced from 64 to 91. This represents normal mount metadata activity including SUPB refresh.

**Canonical claim (reference_table.csv):** File System: Mount on clean volume triggers ~27 checkpoint increments and ~82 page writes. CHKP virtual clock advanced from 64 to 91. This represents normal mount metadata activity including SUPB refresh.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral observation (mount): a clean-volume mount advances the checkpoint virtual clock ~27 times. RD-observed across mount/remount test images; not a static-decodable field.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SUPB_RA_006.csv`
- corrected registry note: Observed on win11refsmini_aftercorruption_openedwith314.raw vs baseline. See ra_step4_15_corrupted_metadata_report.md

## Proof links
- `proofs/validation/FS_SUPB_RA_006.csv` (matrix) — 
