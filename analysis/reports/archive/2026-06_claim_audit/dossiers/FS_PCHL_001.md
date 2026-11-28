# Dossier — FS_PCHL_001 (BEHAVIORAL)

**Claim (this audit tests):** Key+value: parent table ID + child table ID

**Canonical claim (reference_table.csv):** File System: Key+value: parent table ID + child table ID

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Parent-Child Table] Key+value: parent table ID + child table ID — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_PCHL_001.csv`
- corrected registry note: Parent-child relationships parsed on all images; enables directory tree reconstruction via refs_parentchild.py

## Proof links
- `proofs/validation/FS_PCHL_001.csv` (matrix) — 
