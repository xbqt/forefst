# Dossier — FS_SCHM_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** Schema 0xe110 = Read Cache Metadata. Created by CmsReadCache::ResetReadCacheMetadataFile. First appears in v3.7 (Win11 21H2).

**Canonical claim (reference_table.csv):** File System: Schema 0xe110 = Read Cache Metadata. Created by CmsReadCache::ResetReadCacheMetadataFile. First appears in v3.7 (Win11 21H2).

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — Schema 0xe110 (Read Cache Metadata) is present on ALL versions including v3.4: v3.4=13/13, v3.7=1/1, v3.9=2/2, v3.10=2/2, v3.14=92/92, v3.15=1/1 (111/111 total).

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** E2 (win11+)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsReadCache::ResetReadCacheMetadataFile. Schema 0xe110 = Read Cache Metadata. Created by CmsReadCache::ResetReadCacheMetadataFile. First appears in v3.. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_SCHM_RA_002.csv`
- corrected registry note: Schema 0xe110 absent on v3.4. Present on v3.7+ images | RE-VERIFIED 2026-06-18 (all-disk): claim: '0xe110 ... First appears in v3.7 (Win11 21H2)' — disk: 0xe110 present on every v3.4 image (13/13), i.e. since v3.4, NOT first at v3.7

## Proof links
- `proofs/validation/FS_SCHM_RA_002.csv` (matrix) — 
