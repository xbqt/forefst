# Dossier — MD_DDIR_001 (STRUCTURAL)

**Claim (this audit tests):** Creation time

**Canonical claim (reference_table.csv):** Metadata: Creation time

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED**

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Directory descriptors are the directory's $SI own-row; CreateTime@$SI+0x00 is a valid FILETIME (same field as MD_FTBL_001, covers directory rows).

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_DDIR_001.csv`
- corrected registry note: Directory timestamps extracted by refs_dirfiles.py; creation time confirmed in all images

## Proof links
- `proofs/validation/MD_DDIR_001.csv` (matrix) — 
