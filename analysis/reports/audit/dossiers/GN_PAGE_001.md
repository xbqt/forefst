# Dossier — GN_PAGE_001 (STRUCTURAL)

**Claim (this audit tests):** 0x00-0x04: page signature (SUPB/CHKP/MSB+)

**Canonical claim (reference_table.csv):** General: 0x00-0x04: page signature (SUPB/CHKP/MSB+)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — page signature at 0x00-0x04 ∈ {SUPB, CHKP, MSB+} on every metadata page; SUPB present at LCN30 on 111/111; MSB+/CHKP signatures matched on every swept page across all images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- structure_reference.md:100 page header 0x00, ASCII signature. The object-table root is an MSB+ page; le32('MSB+')=725766989. Byte-verified sig_otroot=MSB+.

## Raw-disk proof
- probe `page_const` ; validation matrix: `proofs/validation/GN_PAGE_001.csv`
- corrected registry note: Validated on all 39 images; every metadata page starts with 4-byte ASCII signature

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/GN_PAGE_001.csv` (matrix) — 
