# Dossier — FS_CHKP_001 (STRUCTURAL)

**Claim (this audit tests):** Page header with signature 'CHKP'

**Canonical claim (reference_table.csv):** File System: Page header with signature 'CHKP'

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP signature 'CHKP' present on both checkpoint pages on 48/48.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- Checkpoint page header signature = 'CHKP' (le32=1347110979). Byte-verified on the newest checkpoint.

## Raw-disk proof
- probe `chkp_int` ; validation matrix: `proofs/validation/FS_CHKP_001.csv`
- corrected registry note: CHKP signature at offset 0x00 of both checkpoint pages in all images

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_001.csv` (matrix) — 
