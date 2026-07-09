# Dossier — GN_HIER_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** In-memory hierarchy: VCB (per-volume) -> FCB (per-file) -> SCB (per-stream) -> CCB (per-handle). Attribute def table at VCB+0xa00 (Win10) / VCB+0xd90 (Win11)

**Canonical claim (reference_table.csv):** General: In-memory hierarchy: VCB (per-volume) -> FCB (per-file) -> SCB (per-stream) -> CCB (per-handle). Attribute def table at VCB+0xa00 (Win10) / VCB+0xd90 (Win11)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- In-memory driver structures (not on-disk): VCB->FCB->SCB. Documented from decompilation; no disk obligation. LITERATURE/static.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_HIER_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_HIER_SA_001.csv` (matrix) — 
