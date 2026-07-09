# Dossier — MD_ATTR_006 (BEHAVIORAL)

**Claim (this audit tests):** $INDEX_ROOT: present but appears unused

**Canonical claim (reference_table.csv):** Metadata: $INDEX_ROOT: present but appears unused

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Attribute capability. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_006.csv`
- corrected registry note: Schema type 0x1b0 = Index Root present in Win11 schema table (absent in Win10)

## Proof links
- `proofs/validation/MD_ATTR_006.csv` (matrix) — 
