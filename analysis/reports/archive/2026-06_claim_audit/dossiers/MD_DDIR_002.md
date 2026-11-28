# Dossier — MD_DDIR_002 (STRUCTURAL)

**Claim (this audit tests):** Modification time

**Canonical claim (reference_table.csv):** Metadata: Modification time

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED**

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ModifyTime@$SI+0x08, valid FILETIME (covers directories).

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_DDIR_002.csv`
- corrected registry note: Modification time parsed and displayed for all directories

## Proof links
- `proofs/validation/MD_DDIR_002.csv` (matrix) — 
