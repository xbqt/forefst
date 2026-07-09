# Dossier — AP_LGFL_RA_003 (BEHAVIORAL)

**Claim (this audit tests):** Log data area contains MSB+ page images (physical logging model, not logical field-level logging)

**Canonical claim (reference_table.csv):** Application: Log data area contains MSB+ page images (physical logging model, not logical field-level logging)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsRestarter::RedoPass. Log data area contains MSB+ page images (physical logging model, not logical field-level logging). Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/AP_LGFL_RA_003.csv`
- corrected registry note: 58-94 MSB+ pages found in log data area scans. CoW + physical page logging = complete page state preserved

## Proof links
- `proofs/validation/AP_LGFL_RA_003.csv` (matrix) — 
