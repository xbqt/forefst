# Dossier — MD_SECT_001 (BEHAVIORAL)

**Claim (this audit tests):** Centralized security descriptors indexed by security ID

**Canonical claim (reference_table.csv):** Metadata: Centralized security descriptors indexed by security ID

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Security table (OID 0x530, E19); SecurityId disk-proven (MD_FTBL_006). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SECT_001.csv`
- corrected registry note: Security Descriptor Stream (OID 0x530) present in all images' Object Tables

## Proof links
- `proofs/validation/MD_SECT_001.csv` (matrix) — 
