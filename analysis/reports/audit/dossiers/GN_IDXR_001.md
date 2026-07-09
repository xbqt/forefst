# Dossier — GN_IDXR_001 (BEHAVIORAL)

**Claim (this audit tests):** Root 0x00-0x04: size of index root

**Canonical claim (reference_table.csv):** General: Root 0x00-0x04: size of index root

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Index-root (MSB+ table-header descriptor) size field at root+0x00 == 40 (0x28) on all 113 ReFS images; table header located at fixed page offset thoff==632 (0x50 + le32(page,0x50)) on all 113. Matches claim 'size of index root = 0x28 / 40 bytes'.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Index Root] Root 0x00-0x04: size of index root — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_IDXR_001.csv`
- corrected registry note: RD all-disk: desc+0x04=0x28 on all table-root pages (113 images). The descriptor is the structure Prade calls Index Root. See structure_reference A.2b.

## Proof links
- `proofs/validation/GN_IDXR_001.csv` (matrix) — 
