# Dossier — CT_COMP_RA_001 (ABSENCE)

**Claim (this audit tests):** Compression configuration NOT visible via fsutil or raw metadata structures — only refsutil compression /q

**Canonical claim (reference_table.csv):** Content: Compression configuration NOT visible via fsutil or raw metadata structures — only refsutil compression /q

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ABSENCE/behavioral (per-container compression, finding S9). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_COMP_RA_001.csv`
- corrected registry note: No fsutil fsinfo or metadata field exposes compression status. Must use refsutil compression /q

## Proof links
- `proofs/validation/CT_COMP_RA_001.csv` (matrix) — 
