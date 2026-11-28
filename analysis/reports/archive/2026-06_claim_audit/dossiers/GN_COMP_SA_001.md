# Dossier — GN_COMP_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Win11 embeds ZSTD(281 funcs) + LZ4(15 raw funcs); replaces Win10 CmsCompressionLZX(7 funcs). ZSTD added at v3.14 alongside existing LZ4. refsutil.exe also embeds 344 library functions

**Canonical claim (reference_table.csv):** General: Win11 embeds ZSTD(281 funcs) + LZ4(15 raw funcs); replaces Win10 CmsCompressionLZX(7 funcs). ZSTD added at v3.14 alongside existing LZ4. refsutil.exe also embeds 344 library functions

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsCompressionLZX. Win11 embeds ZSTD(281 funcs) + LZ4(15 raw funcs); replaces Win10 CmsCompressionLZX(7 funcs). ZSTD added at v3.. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_COMP_SA_001.csv`
- corrected registry note: NORMALIZED 2026-06-19 (was NOT_CONFIRMED: static function-count evidence, no disk-visible structural effect): 4 compression-enabled images parse identically to non-compressed; no visible structural effect at metadata level

## Proof links
- `proofs/validation/GN_COMP_SA_001.csv` (matrix) — 
