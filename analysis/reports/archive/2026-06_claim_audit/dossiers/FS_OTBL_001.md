# Dossier — FS_OTBL_001 (BEHAVIORAL)

**Claim (this audit tests):** Key: table identifier

**Canonical claim (reference_table.csv):** File System: Key: table identifier

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Object Table key is 16 bytes on 34522/34522 rows; the OID (table identifier) is at le64(key,8) (forefst build_object_map uses oid=le64(kd,8)); key bytes 0..7 are the record-header prefix. Key uniquely identifies the table/object. Holds 113/113 images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsObjectTable::GetObjectRecordOfIdentifier. Key: table identifier. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_001.csv`
- corrected registry note: Object table key is 16 bytes: 8-byte padding + 8-byte OID; confirmed on all images

## Proof links
- `proofs/validation/FS_OTBL_001.csv` (matrix) — 
