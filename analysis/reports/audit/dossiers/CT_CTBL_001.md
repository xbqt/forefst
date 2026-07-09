# Dossier — CT_CTBL_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Key: container identifier

**Canonical claim (reference_table.csv):** Content: Key: container identifier

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CT key=16B: Container ID(u64)@0x00 + constant tag(u64)@0x08==0x0000000100000000 on 796688/796688 rows across 113 images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/_parse_ct_page__forefst.txt
- The CT row key IS the container id; verified value+0x00 == key container id across all CT rows.

## Raw-disk proof
- probe `ct_row` ; validation matrix: `proofs/validation/CT_CTBL_001.csv`
- corrected registry note: Container ID is the key in B+-tree; sequential from 0 to container_count-1

## Proof links
- `proofs/static/_parse_ct_page__forefst.txt` (static) — _parse_ct_page
- `proofs/validation/CT_CTBL_001.csv` (matrix) — 
