# Dossier — FS_CHKP_006 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x68-0x70: allocator virtual clock

**Canonical claim (reference_table.csv):** File System: 0x68-0x70: allocator virtual clock

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP+0x68 allocator clock <= CHKP+0x60 virtual clock on 48/48.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md:167 CHKP 0x68 = allocator clock, <= virtual clock. Verified allocator(0x68) <= virtual(0x60).

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_CHKP_006.csv`
- corrected registry note: Allocator clock always slightly lower than checkpoint virtual clock (typically vclock-3 to vclock-5)

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_006.csv` (matrix) — 
