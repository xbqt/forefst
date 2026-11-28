# Dossier — FS_CHKP_005 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x60-0x68: checkpoint virtual clock

**Canonical claim (reference_table.csv):** File System: 0x60-0x68: checkpoint virtual clock

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP virtual clock: header(0x10) == body(0x60) on 48/48 (both copies).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md:166 CHKP 0x60 = virtual clock (body copy). Non-zero on a mounted volume (monotonic).

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_CHKP_005.csv`
- corrected registry note: Virtual clock at CHKP+0x10 (not 0x60 as in Prade); increases monotonically; higher value selects active checkpoint

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_005.csv` (matrix) — 
