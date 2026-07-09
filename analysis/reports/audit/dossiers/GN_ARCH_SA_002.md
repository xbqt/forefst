# Dossier — GN_ARCH_SA_002 (BEHAVIORAL)

**Claim (this audit tests):** DriverEntry initialization: registers IRP dispatch table (IRP_MJ_CREATE/CLEANUP/CLOSE/READ/WRITE/DEVICE_CONTROL/SET_INFORMATION/QUERY_INFORMATION/etc.). Initializes global state and registry configuration. ~7533 bytes Win10.

**Canonical claim (reference_table.csv):** General: DriverEntry initialization: registers IRP dispatch table (IRP_MJ_CREATE/CLEANUP/CLOSE/READ/WRITE/DEVICE_CONTROL/SET_INFORMATION/QUERY_INFORMATION/etc.). Initializes global state and registry configuration. ~7533 bytes Win10.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — DriverEntry IRP-dispatch registration is a code-behavior claim (E2, win10). Not present in on-disk filesystem structures — cannot be measured from raw images.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2 (win10)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Architecture] DriverEntry initialization: registers IRP dispatch table (IRP_MJ_CREATE/CLEANUP/CLOSE/READ/WRITE/DEVICE_CONTRO — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_ARCH_SA_002.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_ARCH_SA_002.csv` (matrix) — 
