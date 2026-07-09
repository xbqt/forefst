# Dossier — FS_VBR_003 (STRUCTURAL)

**Claim (this audit tests):** 0x10-0x14: FSRS identifier 'FSRS'

**Canonical claim (reference_table.csv):** File System: 0x10-0x14: FSRS identifier 'FSRS'

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — VBR[0x10:0x14]=='FSRS' on 113/113 ReFS images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:18 VBR 0x10, 4 bytes, ASCII 'FSRS' (CONFIRMED). le32('FSRS')=0x53525346=1397904198. Matches the consensus majority (6/13 votes) and byte-verified on disk.

## Raw-disk proof
- probe `vbr_int` ; validation matrix: `proofs/validation/FS_VBR_003.csv`
- corrected registry note: 'FSRS' signature confirmed at offset 0x10 in all valid images by refs_boot.py

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_003.csv` (matrix) — 
