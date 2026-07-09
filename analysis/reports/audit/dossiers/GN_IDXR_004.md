# Dossier — GN_IDXR_004 (BEHAVIORAL)

**Claim (this audit tests):** Root 0x20-0x28: number of rows

**Canonical claim (reference_table.csv):** General: Root 0x20-0x28: number of rows

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CONFIRMED 2026-06-19 (FRAME-ERROR REVERSAL, was CONTRADICTED): Prade 0x20-0x28 = _SmsIndexRoot+0x20 (u64) = whole-table row count (incremented per insert, EnqueueTreeUpdate this+0x38). RD desc+0x20==leaf-walk total on 34177/34207, diverges from per-node thoff+0x14 on multi-level trees. The CONTRADICTED verdict analysed the wrong structure (node header). See E49.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Index Root] Root 0x20-0x28: number of rows — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_IDXR_004.csv`
- corrected registry note: CORRECTED 2026-06-19 (FRAME ERROR REVERSED, was CONTRADICTED): Prade's '0x20-0x28 = number of rows' is CORRECT - it is the _SmsIndexRoot descriptor (page+0x50) +0x20 = whole-table row count. RD: desc+0x20 == independent leaf-walk total on 34,177/34,207 tables, diverging from the per-node _SmsIndexHeader+0x14 on multi-level trees (387 vs 10 children; 245,759 vs 2). The 2026-06-18 'CONTRADICTED / count at thoff+0x14' analysed the per-node NODE header (wrong frame). See errata E49, structure_reference A.2b.

## Proof links
- `proofs/validation/GN_IDXR_004.csv` (matrix) — 
