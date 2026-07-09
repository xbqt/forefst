# Dossier — CT_CTBL_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Translation: CN = LCN & (CPC - 1)

**Canonical claim (reference_table.csv):** Content: Translation: CN = LCN & (CPC - 1)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Translator mask=CPC-1 (0x3FFF for 4K, 0x3FF for 64K). tr(base+5)==phys+5 verified within container on 113/113.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/Translator__forefst.txt
- structure_reference.md:287 mask=CPC-1. Determined by CPC (cpc probe verifies CPC=16384/1024 at CT value+0x18). forefst Translator.mask=cpc-1. A constant-offset probe cannot test a bitmask formula; CPC is the determining constant.

## Raw-disk proof
- probe `cpc` ; validation matrix: `proofs/validation/CT_CTBL_003.csv`
- corrected registry note: Offset within container: VLCN & (CPC-1). CPC=16384(4K) or 1024(64K)

## Proof links
- `proofs/static/Translator__forefst.txt` (static) — Translator
- `proofs/validation/CT_CTBL_003.csv` (matrix) — 
