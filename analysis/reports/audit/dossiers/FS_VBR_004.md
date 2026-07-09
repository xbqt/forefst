# Dossier — FS_VBR_004 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x14-0x16: VBR size 0x200

**Canonical claim (reference_table.csv):** File System: 0x14-0x16: VBR size 0x200

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — le16(VBR,0x14)==0x200 (512) on 113/113.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:19 VBR 0x14, u16, 0x0200 (512). Byte-verified on v3.4+v3.14.

## Raw-disk proof
- probe `vbr_int` ; validation matrix: `proofs/validation/FS_VBR_004.csv`
- corrected registry note: Value 0x200 observed in all images

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_004.csv` (matrix) — 
