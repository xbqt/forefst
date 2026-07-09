# Dossier — AP_LGFL_RA_005 (BEHAVIORAL)

**Claim (this audit tests):** Log wrapping detection: record_index can exceed physical page count in data area. Circular buffer confirmed

**Canonical claim (reference_table.csv):** Application: Log wrapping detection: record_index can exceed physical page count in data area. Circular buffer confirmed

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile] Log wrapping detection: record_index can exceed physical page count in data area. Circular buffer confirmed — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_RA_005.csv`
- corrected registry note: Confirmed by refs_mlog.py. win11refs2tmillionsofactions shows max record_index=41142 vs 12738 physical pages

## Proof links
- `proofs/validation/AP_LGFL_RA_005.csv` (matrix) — 
