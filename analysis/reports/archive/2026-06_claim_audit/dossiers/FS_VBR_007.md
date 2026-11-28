# Dossier — FS_VBR_007 (STRUCTURAL)

**Claim (this audit tests):** 0x20-0x24: bytes per sector (0x200)

**Canonical claim (reference_table.csv):** File System: 0x20-0x24: bytes per sector (0x200)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — le32(VBR,0x20)==0x200 (512) on 113/113.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:22 VBR 0x20, u32, 512 (always). Byte-verified on v3.4+v3.14.

## Raw-disk proof
- probe `vbr_int` ; validation matrix: `proofs/validation/FS_VBR_007.csv`
- corrected registry note: All images show 0x200 (512 bytes per sector)

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_007.csv` (matrix) — 
