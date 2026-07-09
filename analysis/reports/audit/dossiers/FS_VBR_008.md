# Dossier — FS_VBR_008 (STRUCTURAL)

**Claim (this audit tests):** 0x24-0x28: sectors per cluster

**Canonical claim (reference_table.csv):** File System: 0x24-0x28: sectors per cluster

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — le32(VBR,0x24) sectors-per-cluster: {8->4K cluster:108 images, 128->64K cluster:5 images}. cs=bps*spc matches manifest cluster column.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:23 VBR 0x24, u32, 8 (4 KiB) or 128 (64 KiB). vbr_spc verifies the field equals cluster_size//512 — cluster-derived, discriminated by the 4K vs 64K images. Not a flat constant.

## Raw-disk proof
- probe `vbr_spc` ; validation matrix: `proofs/validation/FS_VBR_008.csv`
- corrected registry note: Values 0x08 (4K clusters) and 0x80 (64K clusters) observed; matches cluster_size/sector_size

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_008.csv` (matrix) — 
