# Dossier — FS_OTBL_SA_008 (BEHAVIORAL)

**Claim (this audit tests):** RefsOpenFcbById: opens a file by its 128-bit OID. Largest Refs-layer OID consumer (5792B Win11 / 5958B Insider). Call chain: OID lookup → FCB create → RefsMapStandardInfo → security load → RefsOpenFile. Two FCB creation paths (normal + hardlink/special).

**Canonical claim (reference_table.csv):** File System: RefsOpenFcbById: opens a file by its 128-bit OID. Largest Refs-layer OID consumer (5792B Win11 / 5958B Insider). Call chain: OID lookup → FCB create → RefsMapStandardInfo → security load → RefsOpenFile. Two FCB creation paths (normal + hardlink/special).

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsOpenFcbById__decomp.txt
- Static driver evidence: RefsOpenFcbById. RefsOpenFcbById: opens a file by its 128-bit OID. Largest Refs-layer OID consumer (5792B Win11 / 5958B Insider. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_SA_008.csv`
- corrected registry note: See RefsOpenFcbById.md

## Proof links
- `proofs/static/RefsOpenFcbById__decomp.txt` (static) — RefsOpenFcbById
- `proofs/validation/FS_OTBL_SA_008.csv` (matrix) — 
