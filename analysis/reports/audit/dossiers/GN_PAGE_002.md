# Dossier — GN_PAGE_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x04-0x08: constant 0x2

**Canonical claim (reference_table.csv):** General: 0x04-0x08: constant 0x2

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — page+0x04 == 0x00000002 on 100% of pages — every live MSB+ page (34,046/34,046) and every swept SUPB/CHKP/MSB+ across 111 images; the ONLY distinct value in the corpus is 0x2.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- structure_reference.md:101 page header 0x04, u32, always 0x00000002. Byte-verified on the OT-root page (v3.4+v3.14).

## Raw-disk proof
- probe `page_const` ; validation matrix: `proofs/validation/GN_PAGE_002.csv`
- corrected registry note: Observed value 0x2 at offset 0x04 in all MSB+ pages across all images

## Proof links
- `proofs/validation/GN_PAGE_002.csv` (matrix) — 
