# Dossier — AP_LGFL_RA_006 (BEHAVIORAL)

**Claim (this audit tests):** MLog data area LCNs (from OID 0x9 key=1) are physical — no container translation needed. Entire MLog operates in physical address space.

**Canonical claim (reference_table.csv):** Application: MLog data area LCNs (from OID 0x9 key=1) are physical — no container translation needed. Entire MLog operates in physical address space.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile] MLog data area LCNs (from OID 0x9 key=1) are physical — no container translation needed. Entire MLog operates — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_RA_006.csv`
- corrected registry note: refs_mlog.py reads data area pages at physical offsets (no tr.tr() call). All 25 baseline images parse correctly. Discovery contradicted implementation plan which assumed container translation was required.

## Proof links
- `proofs/validation/AP_LGFL_RA_006.csv` (matrix) — 
