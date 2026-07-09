# Dossier — MD_DDIR_004 (STRUCTURAL)

**Claim (this audit tests):** Access time (may be disabled)

**Canonical claim (reference_table.csv):** Metadata: Access time (may be disabled)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED**

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- AccessTime@$SI+0x18, valid FILETIME (covers directories).

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_DDIR_004.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/MD_DDIR_004.csv` (matrix) — 
