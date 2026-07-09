# Dossier — CT_ALLC_001 (BEHAVIORAL)

**Claim (this audit tests):** Manages own tree + Med Alloc + BRC + Integrity State

**Canonical claim (reference_table.csv):** Content: Manages own tree + Med Alloc + BRC + Integrity State

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — E2 symbols present: CmsAllocator, GetIntegrityStateTable, TriageIntegrityState, GetNumAllocatedForContainerEntry. Disk: allocator tree exists at roots 1/2/12 and integrity-state at root 11 on all 113 images.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Allocator hierarchy role (checkpoint root 12 = 0x22, disk-presence verified in FS_CHKP_RA_004/CT_CTBL_RA_004). Role description cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_ALLC_001.csv`
- corrected registry note: Small Allocator (root #12) uses real LCNs as bootstrap fallback; confirmed in all 39 images | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Behavioral claim 'Manages own tree + Med Alloc + BRC + Integrity State' - the structural pieces are disk-present (3-tier allocator rows, integrity-state table) and E2-symbol-backed, but the 'manages' relationship is not a single b

## Proof links
- `proofs/validation/CT_ALLC_001.csv` (matrix) — 
