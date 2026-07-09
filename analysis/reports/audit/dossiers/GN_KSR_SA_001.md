# Dossier — GN_KSR_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Win11 Kernel Soft Restart: 6 imports from ext-ms-win-ntos-ksr-l1-1-1.dll (KsrMdlToMemoryRuns, KsrGetFirmwareInformation, etc.)

**Canonical claim (reference_table.csv):** General: Win11 Kernel Soft Restart: 6 imports from ext-ms-win-ntos-ksr-l1-1-1.dll (KsrMdlToMemoryRuns, KsrGetFirmwareInformation, etc.)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [KSR] Win11 Kernel Soft Restart: 6 imports from ext-ms-win-ntos-ksr-l1-1-1.dll (KsrMdlToMemoryRuns, KsrGetFirmwareIn — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_KSR_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_KSR_SA_001.csv` (matrix) — 
