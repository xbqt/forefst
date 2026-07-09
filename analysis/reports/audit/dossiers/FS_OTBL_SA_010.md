# Dossier — FS_OTBL_SA_010 (BEHAVIORAL)

**Claim (this audit tests):** CmsObjectTable::InsertIntoParentChildTable: inserts [parent_OID child_OID] pair into Parent-Child Table (schema 0xe040). Called for every directory entry creation. Enables reverse lookup (find children of a parent). ~280 bytes (Insider).

**Canonical claim (reference_table.csv):** File System: CmsObjectTable::InsertIntoParentChildTable: inserts [parent_OID child_OID] pair into Parent-Child Table (schema 0xe040). Called for every directory entry creation. Enables reverse lookup (find children of a parent). ~280 bytes (Insider).

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsObjectTable::InsertIntoParentChildTable. CmsObjectTable::InsertIntoParentChildTable: inserts [parent_OID child_OID] pair into Parent-Child Table (schem. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_SA_010.csv`
- corrected registry note: See ObjectIdLifecycle.md

## Proof links
- `proofs/validation/FS_OTBL_SA_010.csv` (matrix) — 
