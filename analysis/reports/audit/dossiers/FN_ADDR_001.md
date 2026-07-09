# Dossier — FN_ADDR_001 (STRUCTURAL)

**Claim (this audit tests):** 128-bit: directory_id | file_id; root=0x600

**Canonical claim (reference_table.csv):** File Name: 128-bit: directory_id | file_id; root=0x600

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Structural: root directory is OID 0x600 (verified present in build_object_map on every volume). The 128-bit addressing scheme cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FN_ADDR_001.csv`
- corrected registry note: 128-bit keys observed in Object Table (8 bytes padding + 8 bytes OID); root=0x600 confirmed

## Proof links
- `proofs/validation/FN_ADDR_001.csv` (matrix) — 
