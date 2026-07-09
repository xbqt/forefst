# Dossier — AP_CHJN_002 (BEHAVIORAL)

**Claim (this audit tests):** Uses USN_RECORD_V3 (128-bit file ref vs NTFS V2 32-bit)

**Canonical claim (reference_table.csv):** Application: Uses USN_RECORD_V3 (128-bit file ref vs NTFS V2 32-bit)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Change Journal] Uses USN_RECORD_V3 (128-bit file ref vs NTFS V2 32-bit) — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_CHJN_002.csv`
- corrected registry note: 128-bit keys (8 padding + 8 OID) observed in Object Table across all images

## Proof links
- `proofs/validation/AP_CHJN_002.csv` (matrix) — 
