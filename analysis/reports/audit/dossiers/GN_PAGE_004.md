# Dossier — GN_PAGE_004 (BEHAVIORAL)

**Claim (this audit tests):** 0x10-0x18: virtual allocator clock

**Canonical claim (reference_table.csv):** General: 0x10-0x18: virtual allocator clock

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — page+0x10-0x18 (virtual allocator clock): non-zero u64 on live MSB+/CHKP pages, zero on immutable SUPB; varies per page. Field present and plausible on all images.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Page Header] 0x10-0x18: virtual allocator clock — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_PAGE_004.csv`
- corrected registry note: Virtual clock read from CHKP offset 0x10; values match between checkpoint and page headers | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Offset/presence confirmed. The 'allocator virtual clock' SEMANTIC (vs tree-update clock at 0x18) is E2/CHKP-correlated; the two 8-byte counters at 0x10 and 0x18 both exist on disk but distinguishing which is allocator vs tree cloc

## Proof links
- `proofs/validation/GN_PAGE_004.csv` (matrix) — 
