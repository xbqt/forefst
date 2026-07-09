# Dossier — FS_VBR_006 (STRUCTURAL)

**Claim (this audit tests):** 0x18-0x20: sector count (volume size)

**Canonical claim (reference_table.csv):** File System: 0x18-0x20: sector count (volume size)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — le64(VBR,0x18) sector-count >0 on 113/113 (e.g. fixboot 4294836224 = ~2TB). Geometry preserved even on fixboot.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:21 VBR 0x18 = total sector count. Per-image (volume size); verified non-zero on every intact VBR.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_VBR_006.csv`
- corrected registry note: Sector count matches file size / sector_size across all images

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_006.csv` (matrix) — 
