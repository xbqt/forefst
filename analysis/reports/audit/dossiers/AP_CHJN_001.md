# Dossier — AP_CHJN_001 (BEHAVIORAL)

**Claim (this audit tests):** Deactivated by default in ReFS

**Canonical claim (reference_table.csv):** Application: Deactivated by default in ReFS

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Change Journal] Deactivated by default in ReFS — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_CHJN_001.csv`
- corrected registry note: verify_usn_claims.py: Fresh image (win11refsmini) has empty OID 0x520 (1 row, no Change Journal entry). Activated image (win11refs4gattributestest2) has 3 rows including "Change Journal" file entry with stream_count=3. Journal structure absent by default, appears after explicit fsutil usn createjournal.

## Proof links
- `proofs/validation/AP_CHJN_001.csv` (matrix) — 
