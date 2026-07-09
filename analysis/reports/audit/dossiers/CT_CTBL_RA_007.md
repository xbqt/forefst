# Dossier — CT_CTBL_RA_007 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Address translation shift = CPC.bit_length() = 15 (4K) / 11 (64K), NOT log2(CPC) = 14/10. Driver stores log2(CPC) at volume+0x50 and adds 1 before shifting (GetContainerIdFromRealRange). Errata E18.

**Canonical claim (reference_table.csv):** Content: Address translation shift = CPC.bit_length() = 15 (4K) / 11 (64K), NOT log2(CPC) = 14/10. Driver stores log2(CPC) at volume+0x50 and adds 1 before shifting (GetContainerIdFromRealRange). Errata E18.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — shift==CPC.bit_length()==15(4K)/11(64K) on 113/113 images; addr translate (cid<<shift -> phys start) ok on 113/113. E2: win11 GetContainerIdFromRealRange @0x1400b3e64 = '*param_4 = *param_3 >> ((char)*(...+0x50)+1U & 0x3f)', i.e. >> (log2(CPC)+1) = CPC.bit_length(). Verified driver source.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/Translator__forefst.txt
- The shift is CPC.bit_length() (E18); cpc probe verifies CPC=16384/1024, hence shift 15/11. Same load-bearing constant as CT_CTBL_002.

## Raw-disk proof
- probe `cpc` ; validation matrix: `proofs/validation/CT_CTBL_RA_007.csv`
- corrected registry note: VLCN 81408 with shift=15 resolves to CID 2 (MSB+ valid); shift=14 gives CID 4 (wrong page). Verified on 20 images

## Proof links
- `proofs/static/Translator__forefst.txt` (static) — Translator
- `proofs/validation/CT_CTBL_RA_007.csv` (matrix) — 
