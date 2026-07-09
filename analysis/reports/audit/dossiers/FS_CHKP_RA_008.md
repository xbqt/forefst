# Dossier — FS_CHKP_RA_008 (BEHAVIORAL)

**Claim (this audit tests):** Root table provenance chain: all 13 root index-to-table mappings confirmed by three independent sources: (1) PDB-named initialization function at that index (2) schema type from B+-tree page header (3) table ID from page header. Bootstrap roots {7 8 12} hardcoded in ValidateCheckpointRecord

**Canonical claim (reference_table.csv):** File System: Root table provenance chain: all 13 root index-to-table mappings confirmed by three independent sources: (1) PDB-named initialization function at that index (2) schema type from B+-tree page header (3) table ID from page header. Bootstrap roots {7 8 12} hardcoded in ValidateCheckpointRecord

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Root-table provenance: the 13 index->Table-ID mappings are disk-confirmed 47-48/48 each (see CHKP_009-021). Real-LCN roots 7/8/12 read directly as 0x0B/0x0C/0x22.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsVolume::Start. Root table provenance chain: all 13 root index-to-table mappings confirmed by three independent sources: (1) P. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_CHKP_RA_008.csv`
- corrected registry note: All 48 images show invariant root ordering. Schema types and table IDs match at every resolved address

## Proof links
- `proofs/validation/FS_CHKP_RA_008.csv` (matrix) — 
