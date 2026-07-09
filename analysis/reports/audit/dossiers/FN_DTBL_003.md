# Dossier — FN_DTBL_003 (STRUCTURAL)

**Claim (this audit tests):** Type 0x20 is the per-object FileId-resolution index (RefsFindFileId/RefsCreateFileId2), NOT a directory reverse-lookup. Key = 0x80000020 + 0 + FileId(u64) + 0 (24B). Format A (type_flag=0, variable) = filename, for non-resident files. Format B (fixed 24B, type_flag=1 on v3.4 / =2 on v3.7+) = {tf, 0, FileId, home-dir back-ref OID}, for subdirectories + cross-dir links. Format B present on v3.4 (as tf=1); tf=1->tf=2 transition at v3.7.

**Canonical claim (reference_table.csv):** File Name: Type 0x20 is the per-object FileId-resolution index (RefsFindFileId/RefsCreateFileId2), NOT a directory reverse-lookup. Key = 0x80000020 + 0 + FileId(u64) + 0 (24B). Format A (type_flag=0, variable) = filename, for non-resident files. Format B (fixed 24B, type_flag=1 on v3.4 / =2 on v3.7+) = {tf, 0, FileId, home-dir back-ref OID}, for subdirectories + cross-dir links. Format B present on v3.4 (as tf=1); tf=1->tf=2 transition at v3.7.

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — type-0x20 / 0x80000020 FileId-resolution index entries present (451,181 across corpus). Key marker 0x80000020 confirmed on disk.

**Original audit verdict:** INFERRED (disk held 112/112 at audit time) · **Registry status:** INFERRED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- Type 0x20 (FileId-resolution index) present on every object (finding #333).

## Raw-disk proof
- probe `attr_types` ; validation matrix: `proofs/validation/FN_DTBL_003.csv`
- corrected registry note: win10refs2tspecials (v3.4): 113 Format B all tf=1 non-self-referencing. Coverage on OID 0x702: 12 Format A == 12 non-resident files; subdirs get Format B. | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): The Format A/B / tf=1->tf=2 transition and the RefsFindFileId semantic are E2+RD (decompilation-grounded); the byte presence of the 0x20 index is disk-confirmed but the detailed semantic discrimination is not a pure byte-layout cl

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/FN_DTBL_003.csv` (matrix) — 
