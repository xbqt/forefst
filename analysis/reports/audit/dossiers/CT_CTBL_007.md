# Dossier — CT_CTBL_007 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0xD0-0xD8: physical start LCN (64K clusters, Prade)

**Canonical claim (reference_table.csv):** Content: 0xD0-0xD8: physical start LCN (64K clusters, Prade)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — value+0xD0 == value[len-16] (physical start) on 278873/278873 224-byte rows (64K AND SHA256 images).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 5/5 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/_parse_ct_page__forefst.txt
- structure_reference.md: 224-byte row physical start at 0xD0. Byte-verified: for 64K (224B) rows, value+0xD0 == value[len-16] (the universal physical-start location). applicability cluster=65536.

## Raw-disk proof
- probe `ct_row` ; validation matrix: `proofs/validation/CT_CTBL_007.csv`
- corrected registry note: For 224-byte rows (64K or SHA256): row[-16]=offset 0xD0 is correct

## Proof links
- `proofs/static/_parse_ct_page__forefst.txt` (static) — _parse_ct_page
- `proofs/validation/CT_CTBL_007.csv` (matrix) — 
