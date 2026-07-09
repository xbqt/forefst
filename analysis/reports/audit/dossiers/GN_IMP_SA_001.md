# Dossier — GN_IMP_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Import table: v3.4=415 imports (2 libraries) vs v3.14=566 (7 libraries). +36% growth. New Win11 libraries: cng.sys(15) ext-ms-win-ntos-ksr(6) msrpc.sys(6) ext-ms-win-crypto-xbox(5) ext-ms-win-ntos-clipsp(1). 184 new imports total; 33 removed

**Canonical claim (reference_table.csv):** General: Import table: v3.4=415 imports (2 libraries) vs v3.14=566 (7 libraries). +36% growth. New Win11 libraries: cng.sys(15) ext-ms-win-ntos-ksr(6) msrpc.sys(6) ext-ms-win-crypto-xbox(5) ext-ms-win-ntos-clipsp(1). 184 new imports total; 33 removed

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Imports] Import table: v3.4=415 imports (2 libraries) vs v3.14=566 (7 libraries). +36% growth. New Win11 libraries: cng — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_IMP_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_IMP_SA_001.csv` (matrix) — 
