# Dossier — GN_INS_SA_003 (BEHAVIORAL)

**Claim (this audit tests):** Embedded SymCrypt (153 funcs) for early boot + MinCrypt (57 funcs) for certificate chain validation before CNG.sys available

**Canonical claim (reference_table.csv):** General: Embedded SymCrypt (153 funcs) for early boot + MinCrypt (57 funcs) for certificate chain validation before CNG.sys available

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Insider Boot] Embedded SymCrypt (153 funcs) for early boot + MinCrypt (57 funcs) for certificate chain validation before CNG — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_INS_SA_003.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_INS_SA_003.csv` (matrix) — 
