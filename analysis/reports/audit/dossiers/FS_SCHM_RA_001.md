# Dossier — FS_SCHM_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** Schema 0xe0d0 = Trash Table. Created by CmsTrashTable::InitializeTable with OID 0xD. Present on all versions (3.4+).

**Canonical claim (reference_table.csv):** File System: Schema 0xe0d0 = Trash Table. Created by CmsTrashTable::InitializeTable with OID 0xD. Present on all versions (3.4+).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Schema 0xe0d0 (Trash Table) present in the schema table on 111/111 images, every version (v3.4 13/13, v3.7 1/1, v3.9 2/2, v3.10 2/2, v3.14 92/92, v3.15 1/1).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsTrashTable::InitializeTable. Schema 0xe0d0 = Trash Table. Created by CmsTrashTable::InitializeTable with OID 0xD. Present on all versions (. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_SCHM_RA_001.csv`
- corrected registry note: Schema 0xe0d0 present on all 48 images

## Proof links
- `proofs/validation/FS_SCHM_RA_001.csv` (matrix) — 
