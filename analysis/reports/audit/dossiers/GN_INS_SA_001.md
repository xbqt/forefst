# Dossier — GN_INS_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Insider build 10.0.29574.1000: 6430 funcs (+10.5% vs Win11); 648 insider-only PDB names; boot volume support

**Canonical claim (reference_table.csv):** General: Insider build 10.0.29574.1000: 6430 funcs (+10.5% vs Win11); 648 insider-only PDB names; boot volume support

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Insider] Insider build 10.0.29574.1000: 6430 funcs (+10.5% vs Win11); 648 insider-only PDB names; boot volume support — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_INS_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_INS_SA_001.csv` (matrix) — 
