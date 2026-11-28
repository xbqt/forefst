# Dossier — MD_SI_RA_003 (BEHAVIORAL)

**Claim (this audit tests):** The 97.9% exact-match value (32573/33263 on winsider.raw) is the type-0x30 INDEX-ENTRY FileSize at value+0x58 (master C.2), NOT '$SI DataSize' (the type-0x10 $SI+0x38 DataSize slot is 0 across the corpus). FileSize == embedded $DATA content size (8-byte aligned; FileSize >= content always).

**Canonical claim (reference_table.csv):** Metadata: The 97.9% exact-match value (32573/33263 on winsider.raw) is the type-0x30 INDEX-ENTRY FileSize at value+0x58 (master C.2), NOT '$SI DataSize' (the type-0x10 $SI+0x38 DataSize slot is 0 across the corpus). FileSize == embedded $DATA content size (8-byte aligned; FileSize >= content always).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — resident type-0x30 value+0x58 == independently-parsed embedded-$DATA size on 405721/409514 (99.07%) resident entries across all 113 images. Mismatches are the known 8-byte-alignment-padding cases (DataSize = ceil-to-8 of content).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Statistical RD observation (97.9% match across the thesis corpus). Cited; not a single-field invariant.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SI_RA_003.csv`
- corrected registry note: CORRECTED 2026-06-19 (E45/E26, master C.7): re-attributed from '$SI DataSize' to the type-0x30 index-entry FileSize at value+0x58. The measurement is real; only the field label was wrong. | winsider.raw: 32573 exact + 689 alignment + 1 outlier = 33263 total resident. All 689 mismatches follow ceil(n/8)*8 pattern. Excluding win11refs2tmillionsofactionsv2: 97.0% match across remaining images.

## Proof links
- `proofs/validation/MD_SI_RA_003.csv` (matrix) — 
