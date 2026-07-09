# Dossier — FN_DTBL_001 (STRUCTURAL)

**Claim (this audit tests):** Directory Descriptor row: type 0x10

**Canonical claim (reference_table.csv):** File Name: Directory Descriptor row: type 0x10

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Directory rows present as key_flags 0x02 + directory attribute bit 0x10000000 at value+0x40 (115,682 non-resident/dir entries). 'type 0x10' = the $SI/descriptor key type, confirmed 32,726 type-0x10 own-rows across corpus.

**Original audit verdict:** INFERRED (disk held 112/112 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- Type 0x10 = the directory/file $SI own-row, present on every object.

## Raw-disk proof
- probe `attr_types` ; validation matrix: `proofs/validation/FN_DTBL_001.csv`
- corrected registry note: Directory entries identified by flag 0x10000000 (bit 28) in all images | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Semantic label 'Directory Descriptor row: type 0x10' is a Prade naming; the type-0x10 key marker exists on disk but FN_DTBL_005 supersedes the directory-discrimination model (dirs are kf=0x02+attr-bit, not a distinct row type). Of

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/FN_DTBL_001.csv` (matrix) — 
