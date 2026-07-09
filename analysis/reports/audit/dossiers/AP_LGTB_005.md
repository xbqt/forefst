# Dossier — AP_LGTB_005 (BEHAVIORAL)

**Claim (this audit tests):** 0x30/0x8: LCN of second control entry

**Canonical claim (reference_table.csv):** Application: 0x30/0x8: LCN of second control entry

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile Info Table] 0x30/0x8: LCN of second control entry — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGTB_005.csv`
- corrected registry note: Control page 1: PLCN 0x31(3.4) or 0x8001(3.14)

## Proof links
- `proofs/validation/AP_LGTB_005.csv` (matrix) — 
