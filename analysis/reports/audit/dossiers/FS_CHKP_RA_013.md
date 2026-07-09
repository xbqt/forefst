# Dossier — FS_CHKP_RA_013 (STRUCTURAL)

**Claim (this audit tests):** Three forensically distinguishable volume states via CHKP flags: original v3.4 (0x002), upgraded v3.4->v3.14 (0x602), native v3.14 (0x682). Missing bit 0x080 distinguishes upgraded from native.

**Canonical claim (reference_table.csv):** File System: Three forensically distinguishable volume states via CHKP flags: original v3.4 (0x002), upgraded v3.4->v3.14 (0x602), native v3.14 (0x682). Missing bit 0x080 distinguishes upgraded from native.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Three volume states via CHKP flags reproduce: 0x002 (v3.4 original, 11 imgs), 0x602 (upgraded: no 0x080, has 0x200+0x400, 1 img), 0x682 (native v3.14: has 0x080, 30 imgs). Bit 0x080 (native marker) distinguishes native from upgraded on 48/48. Also 0x082(v3.10),0x7b2(dedup),0x2682(insider) observed.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 103/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- Tests the 3-state flags model. CONTESTED BY DESIGN: also observed 0x082 (v3.10), 0x2602/0x2682 (0x2000 bit), 0x7b2 — the field has more states than the exact 3-value enum, though bit 0x002 is universal (FS_CHKP_RA_001). See finding #339.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_CHKP_RA_013.csv`
- corrected registry note: Verified on 20 images: flag patterns are invariant within each category

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_RA_013.csv` (matrix) — 
