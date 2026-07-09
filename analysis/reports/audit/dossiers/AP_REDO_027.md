# Dossier — AP_REDO_027 (BEHAVIORAL)

**Claim (this audit tests):** 0x1B: RedoGhostExtents (v3.4 only — gap in v3.14)

**Canonical claim (reference_table.csv):** Application: 0x1B: RedoGhostExtents (v3.4 only — gap in v3.14)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/PerformRedo__decomp.txt
- Redo opcode -> operation mapping from the PerformRedo dispatch (E2; v3.14 = 32 ops/37 values, all E2). Proof is the decompiled dispatch + redo_opcode_complete.md.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/AP_REDO_027.csv`
- corrected registry note: (none)

## Proof links
- `proofs/static/PerformRedo__decomp.txt` (static) — PerformRedo
- `proofs/validation/AP_REDO_027.csv` (matrix) — 
