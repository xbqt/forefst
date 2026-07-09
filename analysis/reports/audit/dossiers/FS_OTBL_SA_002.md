# Dossier — FS_OTBL_SA_002 (BEHAVIORAL)

**Claim (this audit tests):** CmsObjectTable::InitializeTable: bootstraps OID counter at mount time. Two-source: (1) reads stored counter from B+-tree root data; (2) validates by FindRow with _CmsKey::RightMost sentinel → returns actual max key. If max key > stored counter, updates to max. Schema 0xe030. 815 bytes (Insider).

**Canonical claim (reference_table.csv):** File System: CmsObjectTable::InitializeTable: bootstraps OID counter at mount time. Two-source: (1) reads stored counter from B+-tree root data; (2) validates by FindRow with _CmsKey::RightMost sentinel → returns actual max key. If max key > stored counter, updates to max. Schema 0xe030. 815 bytes (Insider).

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsObjectTable::InitializeTable. CmsObjectTable::InitializeTable: bootstraps OID counter at mount time. Two-source: (1) reads stored counter fr. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_SA_002.csv`
- corrected registry note: See ObjectIdLifecycle.md

## Proof links
- `proofs/validation/FS_OTBL_SA_002.csv` (matrix) — 
