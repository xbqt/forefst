# Dossier — GN_BIN_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Binary growth: refs.sys 1.92MB->3.53MB (+84%); 3959->5818 funcs (+47%); 415->566 imports (+36%); 1562->4445 strings (+185%). PDB-named: 2553(64.5%) / 2565(44.1%) / 2878(44.8%)

**Canonical claim (reference_table.csv):** General: Binary growth: refs.sys 1.92MB->3.53MB (+84%); 3959->5818 funcs (+47%); 415->566 imports (+36%); 1562->4445 strings (+185%). PDB-named: 2553(64.5%) / 2565(44.1%) / 2878(44.8%)

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Binary] Binary growth: refs.sys 1.92MB->3.53MB (+84%); 3959->5818 funcs (+47%); 415->566 imports (+36%); 1562->4445 st — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_BIN_SA_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/GN_BIN_SA_001.csv` (matrix) — 
