# Dossier — AP_LGFL_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** MLog physical location: PLCN 0x30 (3.4) vs PLCN 0x8000 (3.14). Version-specific relocation

**Canonical claim (reference_table.csv):** Application: MLog physical location: PLCN 0x30 (3.4) vs PLCN 0x8000 (3.14). Version-specific relocation

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsDurableLog::WriteLog. MLog physical location: PLCN 0x30 (3.4) vs PLCN 0x8000 (3.14). Version-specific relocation. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/AP_LGFL_RA_002.csv`
- corrected registry note: 3.14 moves MLog to container boundary, freeing early clusters for metadata

## Proof links
- `proofs/validation/AP_LGFL_RA_002.csv` (matrix) — 
