# Dossier — FS_VBR_002 (STRUCTURAL)

**Claim (this audit tests):** 0x03-0x0B: FSRS signature 'ReFS'

**Canonical claim (reference_table.csv):** File System: 0x03-0x0B: FSRS signature 'ReFS'

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — VBR[0x03:0x07]=='ReFS' on 113/113; [0x07:0x0B] zero padding on 113/113.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:16 VBR 0x03, 8 bytes, ASCII 'ReFS\0\0\0\0' (CONFIRMED). Probe tests first 4 bytes 'ReFS' (le32=0x53466552). fixboot does NOT zero the OEM string, so no fixboot exception (unlike FS_VBR_011).

## Raw-disk proof
- probe `vbr_int` ; validation matrix: `proofs/validation/FS_VBR_002.csv`
- corrected registry note: refs_boot.py validates 'ReFS' at offset 0x03 on all valid images

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_002.csv` (matrix) — 
