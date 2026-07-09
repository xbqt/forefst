# Dossier — FS_OTBL_004 (BEHAVIORAL)

**Claim (this audit tests):** Root directory ID = 0x600

**Canonical claim (reference_table.csv):** File System: Root directory ID = 0x600

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OID 0x600 present in Object Table on 113/113 images and is directory-structured (its own B+-tree yields >=1 type-0x30 entry on 113/113; e.g. baseline root children: $RECYCLE.BIN->0x703, System Volume Information->0x701, test->0x702). Root is the first user-visible object.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Object Table] Root directory ID = 0x600 — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_OTBL_004.csv`
- corrected registry note: OID 0x600 = Root Directory in all 39 images; used as start point by refs_dirfiles.py

## Proof links
- `proofs/validation/FS_OTBL_004.csv` (matrix) — 
