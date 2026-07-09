# Dossier — MD_ATTR_RA_016 (ABSENCE)

**Claim (this audit tests):** Types 0x50/0x60/0x70: ZERO sub-records in user objects across 111 images. 0x50 in OID 0x500 (key 0x520, 448B). 0x60 in OID 0x540 (key 0x01). 0x70 not observed. CORRECTION: type 0xF0 IS observed — exactly 1 per image (9 images where USN journal active), the USN $Max attribute (marker 0x80000001, 44B) on the Change Journal file under OID 0x520. NOT a zero/never-observed type.

**Canonical claim (reference_table.csv):** Metadata: Types 0x50/0x60/0x70: ZERO sub-records in user objects across 111 images. 0x50 in OID 0x500 (key 0x520, 448B). 0x60 in OID 0x540 (key 0x01). 0x70 not observed. CORRECTION: type 0xF0 IS observed — exactly 1 per image (9 images where USN journal active), the USN $Max attribute (marker 0x80000001, 44B) on the Change Journal file under OID 0x520. NOT a zero/never-observed type.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Types 0x50/0x60/0x70: ZERO embedded sub-records in user objects across all 107 images (0/0/0). Type 0xF0 IS present: exactly 1 per image on 9 distinct USN-active images, always 44 bytes, SI marker (0x80000001), on system OID 0x520 (Change Journal $Max). Images: win11refs2gtargeted, win11refs4gattributestest2, win11refslasttests(+baselines x4), win11refstestmftecmd, winsider.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- ABSENCE: types 0x50/0x60/0x70 are unused in ReFS user objects. Verified 0 occurrences across all images.

## Raw-disk proof
- probe `attr_types` ; validation matrix: `proofs/validation/MD_ATTR_RA_016.csv`
- corrected registry note: Full re-scan of 111 images: 0xF0 found on 9 images (1:1 with USN-journal presence), always OID 0x520 Change Journal. 0x50/0x60/0x70 confirmed zero in user objects.

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/MD_ATTR_RA_016.csv` (matrix) — 
