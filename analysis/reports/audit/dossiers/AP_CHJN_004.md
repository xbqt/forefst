# Dossier — AP_CHJN_004 (BEHAVIORAL)

**Claim (this audit tests):** Located in File System Metadata/Change Journal

**Canonical claim (reference_table.csv):** Application: Located in File System Metadata/Change Journal

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Change Journal] Located in File System Metadata/Change Journal — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_CHJN_004.csv`
- corrected registry note: verify_usn_claims.py: OID 0x520 is "FS Metadata" directory (child of root 0x600 per parent-child table). Contains "Change Journal" file entry when journal is active. Path confirmed: Root (0x600) / FS Metadata (0x520) / Change Journal.

## Proof links
- `proofs/validation/AP_CHJN_004.csv` (matrix) — 
