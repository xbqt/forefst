# Dossier — MD_DDIR_006 (BEHAVIORAL)

**Claim (this audit tests):** Security descriptor ID

**Canonical claim (reference_table.csv):** Metadata: Security descriptor ID

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- SecurityId@$SI+0x28 (resolves in OID 0x530, E19). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DDIR_006.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/MD_DDIR_006.csv` (matrix) — 
