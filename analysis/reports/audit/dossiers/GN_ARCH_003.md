# Dossier — GN_ARCH_003 (BEHAVIORAL)

**Claim (this audit tests):** Virtual addressing with Container Table translation (v2+)

**Canonical claim (reference_table.csv):** General: Virtual addressing with Container Table translation (v2+)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/CmsVolumeContainer__decomp.txt
- Static driver evidence: CmsVolumeContainer. Virtual addressing with Container Table translation (v2+). Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_ARCH_003.csv`
- corrected registry note: Translation formula verified: PLCN = map[VLCN >> shift] + (VLCN & mask). Tested on 39 images, all configurations

## Proof links
- `proofs/static/CmsVolumeContainer__decomp.txt` (static) — CmsVolumeContainer
- `proofs/validation/GN_ARCH_003.csv` (matrix) — 
