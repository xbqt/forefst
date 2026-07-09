# Dossier — CT_CTBL_006 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x90-0x98: physical start LCN (4K clusters, Prade)

**Canonical claim (reference_table.csv):** Content: 0x90-0x98: physical start LCN (4K clusters, Prade)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — value+0x90 == value[len-16] (physical start) on 517815/517815 160-byte (4K) rows across all 4K images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 107/107 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/_parse_ct_page__forefst.txt
- For 160-byte (4K) rows, value+0x90 == value[len-16] (physical start). Byte-verified. applicability 4K.

## Raw-disk proof
- probe `ct_row` ; validation matrix: `proofs/validation/CT_CTBL_006.csv`
- corrected registry note: NORMALIZED 2026-06-19 (was INVALIDATED): Position-independent: phys_start at row[-16] (last 16 bytes). For 160-byte rows: offset 0x90 is correct; fails on 224-byte rows. Universal formula: row[len(row)-16]. Works for 160-byte (0x90) and 224-byte (0xD0). Merged from CT_CTBL_RA_002

## Proof links
- `proofs/static/_parse_ct_page__forefst.txt` (static) — _parse_ct_page
- `proofs/validation/CT_CTBL_006.csv` (matrix) — 
