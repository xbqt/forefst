# Dossier — MD_SI_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** Type-0x10 $SI+0x38 (DataSize slot) = 0 across all versions / 110 images (CONFIRMED). The value previously attributed to 'resident directory-entry $SI DataSize' is the type-0x30 INDEX-ENTRY FileSize at value+0x58 (master C.2) — a DIFFERENT structure, not $SI+0x38.

**Canonical claim (reference_table.csv):** Metadata: Type-0x10 $SI+0x38 (DataSize slot) = 0 across all versions / 110 images (CONFIRMED). The value previously attributed to 'resident directory-entry $SI DataSize' is the type-0x30 INDEX-ENTRY FileSize at value+0x58 (master C.2) — a DIFFERENT structure, not $SI+0x38.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — type-0x10 $SI+0x38 (DataSize slot, val+0x60) = 0 on 32629/32629 own-rows incl all 25494 directories AND all 7135 files. The populated size lives in the resident type-0x30 index entry: val+0x58(FileSize) nz 47559/47908 + val+0x60(AllocSize) nz 47560/47908 on winsider; the resident entry is the 'val>84' case the claim names.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- E2/RD: DataSize at $SI+0x38 is meaningful only for resident files; directories carry 0 (proven on disk by MD_SI_RA_004). Semantic conclusion cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SI_RA_002.csv`
- corrected registry note: CORRECTED 2026-06-19 (E45/E26, master C.7): the '$SI+0x38 DataSize populated in resident dir entry' label is wrong — that 97.9%-matching value is the type-0x30 index-entry FileSize at value+0x58. Type-0x10 $SI+0x38 itself is 0. | 110 images / 525145 entries: ALL child OID type 0x10 $SI have DataSize=0. Resident directory entries: 32573/33263 exact match (97.9%). Report: report_datasize_verification.txt

## Proof links
- `proofs/validation/MD_SI_RA_002.csv` (matrix) — 
