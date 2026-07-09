# Dossier — FS_VBR_001 (STRUCTURAL)

**Claim (this audit tests):** 0x00-0x03: reserved jump instruction (zeros)

**Canonical claim (reference_table.csv):** File System: 0x00-0x03: reserved jump instruction (zeros)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — VBR[0x00:0x03]==000000 on 113/113 ReFS images (all versions, 4K+64K). 0x07-0x0F also all-zero on 113/113.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:15 VBR 0x00, 3 bytes, '00 00 00'. Probe tests the u16 at 0x00 (bytes 0-1 = 0); byte 0x02 is also 0 (byte-verified on v3.4+v3.14). PARTIAL: u16 proxy for the 3-byte field.

## Raw-disk proof
- probe `vbr_int` ; validation matrix: `proofs/validation/FS_VBR_001.csv`
- corrected registry note: All 39 images show zeros at bytes 0-2 of VBR

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_001.csv` (matrix) — 
