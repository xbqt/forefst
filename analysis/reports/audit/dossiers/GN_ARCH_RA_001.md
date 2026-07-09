# Dossier — GN_ARCH_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** Three-table real-LCN bootstrap exception: roots 7+8 (Container Table) + root 12 (Small Allocator). All other roots use virtual addressing

**Canonical claim (reference_table.csv):** General: Three-table real-LCN bootstrap exception: roots 7+8 (Container Table) + root 12 (Small Allocator). All other roots use virtual addressing

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Architecture] Three-table real-LCN bootstrap exception: roots 7+8 (Container Table) + root 12 (Small Allocator). All other r — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_ARCH_RA_001.csv`
- corrected registry note: Not documented in Prade or Lee. Prade only mentions Container Table; does not document Small Allocator exception

## Proof links
- `proofs/validation/GN_ARCH_RA_001.csv` (matrix) — 
