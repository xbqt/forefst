# Dossier — MD_ATTR_003 (BEHAVIORAL)

**Claim (this audit tests):** $DIR_LINK: new in ReFS, stores dir name+parent ID+timestamps

**Canonical claim (reference_table.csv):** Metadata: $DIR_LINK: new in ReFS, stores dir name+parent ID+timestamps

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Attribute capability (0x30 key_flags=0x0002 dir-link, disk-proven in FN_DTBL_004). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_003.csv`
- corrected registry note: Directory names extracted via B+-tree walking; parent-child relationships confirmed

## Proof links
- `proofs/validation/MD_ATTR_003.csv` (matrix) — 
