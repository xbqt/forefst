# Dossier — FS_VINF_001 (STRUCTURAL)

**Claim (this audit tests):** Volume label row (key 0x510, UTF-16)

**Canonical claim (reference_table.csv):** File System: Volume label row (key 0x510, UTF-16)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OID 0x500 key-type 0x510 row present and value decodes as UTF-16LE label on 113/113 ReFS images (winsider has empty label = allowed). Key is 8B (type u16@0x00, pad to 0x08).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- structure_reference.md:1324 OID 0x500 key 0x0510 = volume label (UTF-16LE). Verified the label ROW is present on every volume; the label TEXT is optional (winsider is an unlabeled volume with an empty 0x510 value), so the probe asserts row presence, not non-empty text.

## Raw-disk proof
- probe `vinf_row` ; validation matrix: `proofs/validation/FS_VINF_001.csv`
- corrected registry note: Volume label extracted as UTF-16LE from key 0x510 row; refs_volume_info.py works on all images

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/FS_VINF_001.csv` (matrix) — 
