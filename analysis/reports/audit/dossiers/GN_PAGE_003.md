# Dossier — GN_PAGE_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x0C-0x10: volume signature

**Canonical claim (reference_table.csv):** General: 0x0C-0x10: volume signature

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — page+0x0C == XOR of the 4 volume-GUID dwords (SUPB+0x50): 100% on LIVE tree pages (e.g. 19/19, 18/18, 24/24, 45/45 64K, 46/46 SHA256). Raw-sweep 'misses' (e.g. baseline family 22/26) are all STALE orphan pages carrying a DIFFERENT prior volume GUID (single shared alt-volsig 0xe23e6f3f), confirmed not in the live tree; corruption-test images correctly mismatch.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 110/110 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- structure_reference.md:103 page header 0x0C = XOR of the four GUID dwords. Byte-verified on OT-root page v3.4+v3.14: header+0x0C == XOR(SUPB+0x50 dwords).

## Raw-disk proof
- probe `page_consistency` ; validation matrix: `proofs/validation/GN_PAGE_003.csv`
- corrected registry note: XOR of volume GUID dwords; verified on all 39 images (filesystem_category.md Section 2.3)

## Proof links
- `proofs/validation/GN_PAGE_003.csv` (matrix) — 
