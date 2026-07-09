# Dossier — CT_CTBL_009 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x10-0x17: Container ID (Lee)

**Canonical claim (reference_table.csv):** Content: 0x10-0x17: Container ID (Lee)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Container ID (u64) at key+0x00 AND value+0x00 (redundant). cid_val==cid_key on 796688/796688 rows. IDs start at 2.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/_parse_ct_page__forefst.txt
- structure_reference.md:0x00 'Container ID (redundant copy of key)'. Lee's '0x10' is ROW-relative (row header 16B + key@0x10). Verified across all CT rows: value+0x00 container ID == key container ID.

## Raw-disk proof
- probe `ct_row` ; validation matrix: `proofs/validation/CT_CTBL_009.csv`
- corrected registry note: Key contains container ID but exact offset within row value not yet verified

## Proof links
- `proofs/static/_parse_ct_page__forefst.txt` (static) — _parse_ct_page
- `proofs/validation/CT_CTBL_009.csv` (matrix) — 
