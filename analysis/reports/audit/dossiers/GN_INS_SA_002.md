# Dossier — GN_INS_SA_002 (BEHAVIORAL)

**Claim (this audit tests):** CmsVolumeAttestation (40 funcs): TPM/certificate attestation; HMAC over checkpoint/log records. CmsRollbackProtection (13 funcs): UEFI NVRAM monotonic counter

**Canonical claim (reference_table.csv):** General: CmsVolumeAttestation (40 funcs): TPM/certificate attestation; HMAC over checkpoint/log records. CmsRollbackProtection (13 funcs): UEFI NVRAM monotonic counter

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsVolumeAttestation. CmsVolumeAttestation (40 funcs): TPM/certificate attestation; HMAC over checkpoint/log records. CmsRollbackPro. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_INS_SA_002.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_INS_SA_002.csv` (matrix) — 
