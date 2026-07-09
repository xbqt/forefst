# Dossier — GN_PREF_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x00-0x20: referenced page LCN quadruple

**Canonical claim (reference_table.csv):** General: 0x00-0x20: referenced page LCN quadruple

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED**

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md:1065-1068 page-ref 0x00-0x20 = 4 LCN slots. Verified on the checkpoint root-0 page reference: slot0 == roots[0][0] (the OT-root LCN). Page references live inside index entries, NOT the page header.

## Raw-disk proof
- probe `pref_field` ; validation matrix: `proofs/validation/GN_PREF_001.csv`
- corrected registry note: Root references in CHKP contain LCN quadruples; size varies: 0x68(3.4) vs 0x30(3.14/CRC64) vs 0x48(SHA256)

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/GN_PREF_001.csv` (matrix) — 
