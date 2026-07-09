# Dossier — MD_FTBL_007 (BEHAVIORAL)

**Claim (this audit tests):** Size / Allocated size

**Canonical claim (reference_table.csv):** Metadata: Size / Allocated size

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- DataSize at $SI+0x38 (resident-only; dir=0, disk-proven in MD_SI_RA_004). Field-role claim cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_FTBL_007.csv`
- corrected registry note: File sizes correctly parsed from directory entries; matches expected values from Generate-FSActivity

## Proof links
- `proofs/validation/MD_FTBL_007.csv` (matrix) — 
