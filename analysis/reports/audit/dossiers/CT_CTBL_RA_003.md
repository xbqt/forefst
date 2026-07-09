# Dossier — CT_CTBL_RA_003 (STRUCTURAL)

**Claim (this audit tests):** Both SHA256 checksums AND 64K clusters cause container row size to increase from 160 to 224 bytes (they do not stack)

**Canonical claim (reference_table.csv):** Content: Both SHA256 checksums AND 64K clusters cause container row size to increase from 160 to 224 bytes (they do not stack)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Row-len by class: (4096,CRC32-C,160B)=106 imgs; (4096,SHA256,224B)=2; (65536,CRC64,224B)=3; (65536,SHA256,224B)=2. So 64K OR SHA256 -> 224B; neither stacks beyond 224B (SHA256+64K still 224B, not 288B).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/_parse_ct_page__forefst.txt
- Row size = 224 when (64K cluster) OR (SHA-256), else 160. Byte-verified (same probe as CT_CTBL_RA_006).

## Raw-disk proof
- probe `ct_row` ; validation matrix: `proofs/validation/CT_CTBL_RA_003.csv`
- corrected registry note: Confirmed across 64K and SHA256 images. Row sizes: 160 (CRC64+4K), 224 (SHA256 or 64K)

## Proof links
- `proofs/static/_parse_ct_page__forefst.txt` (static) — _parse_ct_page
- `proofs/validation/CT_CTBL_RA_003.csv` (matrix) — 
