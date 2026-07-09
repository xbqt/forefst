# Dossier — FS_OTBL_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** CmsObjectTable::GenerateIdentifier: atomic OID allocation via LOCK prefix increment at this+0x18. Returns max+1 as new OID in 128-bit SmsBigIdentifier format [0, OID]. Win11/Insider: lock-free atomic; Win10: GuardedMutex at this+0x40. 458 bytes (Insider).

**Canonical claim (reference_table.csv):** File System: CmsObjectTable::GenerateIdentifier: atomic OID allocation via LOCK prefix increment at this+0x18. Returns max+1 as new OID in 128-bit SmsBigIdentifier format [0, OID]. Win11/Insider: lock-free atomic; Win10: GuardedMutex at this+0x40. 458 bytes (Insider).

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — No on-disk byte signal: this is a decompiled-function claim (CmsObjectTable::GenerateIdentifier, atomic OID alloc via LOCK inc at this+0x18, returns 128-bit SmsBigIdentifier). Disk corroboration of its EFFECT (monotonic non-reused OIDs starting 0x701) is captured under FS_OTBL_RA_006. The function/instruction-level detail requires the Ghidra E2 decompilation, not bytes.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsObjectTable::GenerateIdentifier. CmsObjectTable::GenerateIdentifier: atomic OID allocation via LOCK prefix increment at this+0x18. Returns max+. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_SA_001.csv`
- corrected registry note: See ObjectIdLifecycle.md

## Proof links
- `proofs/validation/FS_OTBL_SA_001.csv` (matrix) — 
