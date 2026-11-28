# Dossier — MD_ATTR_005 (BEHAVIORAL)

**Claim (this audit tests):** $DATA: core file content (always non-resident)

**Canonical claim (reference_table.csv):** Metadata: $DATA: core file content (always non-resident)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $DATA (type 0x80) is EMBEDDED in resident directory entries (type 0x30) or stored as extents (type 0x40), not as a standalone top-level row in the object B+-tree (verified: 0x80 never appears top-level across 110 images). Presence proven via the data-extent + resident-content claims. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_005.csv`
- corrected registry note: Win10: 100% resident for small test files. Win11: ~92% resident. Threshold confirmed empirically.

## Proof links
- `proofs/validation/MD_ATTR_005.csv` (matrix) — 
