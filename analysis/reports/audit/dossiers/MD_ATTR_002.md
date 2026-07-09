# Dossier — MD_ATTR_002 (STRUCTURAL)

**Claim (this audit tests):** $FILENAME: present in driver

**Canonical claim (reference_table.csv):** Metadata: $FILENAME: present in driver

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — $FILE_NAME entries present: type-0x30 directory keys with UTF-16LE names decode on every image; 525178 type-0x30 keys across 107 images. Filename presence is disk-evident.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- Type 0x30 = directory-entry (filename) rows. Verified present (every volume has named children).

## Raw-disk proof
- probe `attr_types` ; validation matrix: `proofs/validation/MD_ATTR_002.csv`
- corrected registry note: Filenames extracted from directory B+-trees by refs_dirfiles.py; UTF-16LE decoding confirmed

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/MD_ATTR_002.csv` (matrix) — 
