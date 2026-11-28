# Dossier — CT_BKRC_001 (BEHAVIORAL)

**Claim (this audit tests):** Inferred support for cloning/dedup; fields unknown

**Canonical claim (reference_table.csv):** Content: Inferred support for cloning/dedup; fields unknown

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — E2 symbols: CmsBlockRefcount, AdjustRefcount, IncrementRefcount, MsKmeBlockRefCountUnderflowEventNotification. Disk: BRC root#6 populated only on v3.14 sharing-active images (37/113), tracking shared/dedup clusters.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Root 6 = BRC (0x05). Row format in CT_BKRC_RA_001/002; semantic fields cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_BKRC_001.csv`
- corrected registry note: Block Ref Count Table (root #6, ID 0x05) present in all images; no visible structural difference on dedup-enabled volumes | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): 'Inferred support for cloning/dedup; fields unknown' - the cloning/dedup support is E2-corroborated and the populated-only-on-sharing-volumes behavior is disk-observed (empty on plain v3.4/v3.14). Fields are actually now KNOWN (se

## Proof links
- `proofs/validation/CT_BKRC_001.csv` (matrix) — 
