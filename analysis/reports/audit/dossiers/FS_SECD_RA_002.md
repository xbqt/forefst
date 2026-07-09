# Dossier — FS_SECD_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** Per-file SecurityId (at $SI+0x28 = entry offset 0x50) is compound u64: (reference_count << 32) | sd_hash. Lookup in OID 0x530 by matching key[8:12]==SecurityId_high and key[12:16]==SecurityId_low. CmsHashTable provides O(1) hash-based lookup.

**Canonical claim (reference_table.csv):** File System: Per-file SecurityId (at $SI+0x28 = entry offset 0x50) is compound u64: (reference_count << 32) | sd_hash. Lookup in OID 0x530 by matching key[8:12]==SecurityId_high and key[12:16]==SecurityId_low. CmsHashTable provides O(1) hash-based lookup.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SD lookup key[8:12]=hi, key[12:16]=lo verified

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Security Descriptors] Per-file SecurityId (at $SI+0x28 = entry offset 0x50) is compound u64: (reference_count << 32) | sd_hash. Look — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SECD_RA_002.csv`
- corrected registry note: Cross-verified: file SecurityId 0x10a9f9562 correctly maps to SD with hash 0x0a9f9562 in OID 0x530 table. Same mapping works on Win10 3.4 and Win11 3.14

## Proof links
- `proofs/validation/FS_SECD_RA_002.csv` (matrix) — 
