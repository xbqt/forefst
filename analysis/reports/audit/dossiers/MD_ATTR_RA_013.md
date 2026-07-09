# Dossier — MD_ATTR_RA_013 (STRUCTURAL)

**Claim (this audit tests):** $EA_INFO/$EA co-occurrence: 3854 pairs always co-occur. 25 orphan $EA_INFO without $EA. 0 orphan $EA without $EA_INFO. Near-perfect co-occurrence invariant.

**Canonical claim (reference_table.csv):** Metadata: $EA_INFO/$EA co-occurrence: 3854 pairs always co-occur. 25 orphan $EA_INFO without $EA. 0 orphan $EA without $EA_INFO. Near-perfect co-occurrence invariant.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Per-container (type-0x10 value or resident type-0x30 value), D0 and E0 ALWAYS co-occur: 3875 containers with both, 0 orphan D0, 0 orphan E0 across 107 images. The co-occurrence invariant holds even STRONGER than claimed.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 4/4 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Every object carrying $EA_INFO (0xD0) also carries $EA (0xE0). Byte-verified 4/4 co-occurrence. N/A where no EAs.

## Raw-disk proof
- probe `subrec` ; validation matrix: `proofs/validation/MD_ATTR_RA_013.csv`
- corrected registry note: 3854 pairs, 25 orphans (EA_INFO only). 0 reverse orphans.

## Proof links
- `proofs/validation/MD_ATTR_RA_013.csv` (matrix) — 
