# Dossier — FS_OTBL_SA_007 (BEHAVIORAL)

**Claim (this audit tests):** MsGetObjectRecordPayload: 46-byte helper extracting LcnWithChecksum pointer from Object Table row. Returns pointer to the page reference within the row's value buffer at offset derived from row header.

**Canonical claim (reference_table.csv):** File System: MsGetObjectRecordPayload: 46-byte helper extracting LcnWithChecksum pointer from Object Table row. Returns pointer to the page reference within the row's value buffer at offset derived from row header.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/MsGetObjectRecordPayload__decomp.txt
- Static driver evidence: extracts the object-record payload (LcnWithChecksum). Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_SA_007.csv`
- corrected registry note: See ObjectIdLifecycle.md

## Proof links
- `proofs/static/MsGetObjectRecordPayload__decomp.txt` (static) — MsGetObjectRecordPayload
- `proofs/validation/FS_OTBL_SA_007.csv` (matrix) — 
