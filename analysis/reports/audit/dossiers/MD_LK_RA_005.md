# Dossier — MD_LK_RA_005 (STRUCTURAL)

**Claim (this audit tests):** $OBJ_LINK (type 0x39 on v3.7+, 0x38 on v3.4) stores primary filename + parent OID within each object's type 0x10 B+-tree record. Enables path reconstruction from Object Table alone without directory walk. Driver: RefsInitializeObjLinkRow.

**Canonical claim (reference_table.csv):** Metadata: $OBJ_LINK (type 0x39 on v3.7+, 0x38 on v3.4) stores primary filename + parent OID within each object's type 0x10 B+-tree record. Enables path reconstruction from Object Table alone without directory walk. Driver: RefsInitializeObjLinkRow.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OBJ_LINK is an embedded sub-record inside each object's type-0x10 ($SI) row (NOT a top-level B+ key). 0x39 form: 32204/32204 entries across 98 images have val_marker@0x00==0x80000002, type@0x04==0x39, parent_oid@0x08 resolves to a real OID in the object map (32204/32204). 0x38 form: 522 entries across 15 v3.4 images. Clean version split: native v3.4 only 0x38, v3.7+ only 0x39, 0 anomalies. fname@0x18 matched the directory-key name on 17008/32204 (rest unreachable in best-effort name-walk, not a contradiction).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ObjLink type by version (embedded in $SI value). Feature-gated; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_LK_RA_005.csv`
- corrected registry note: 110 images: v3.4 images use 0x38 (509 entries), v3.7+ use 0x39 (32077 MI + 14 SI). Parent OID verified via directory walk cross-reference.

## Proof links
- `proofs/validation/MD_LK_RA_005.csv` (matrix) — 
