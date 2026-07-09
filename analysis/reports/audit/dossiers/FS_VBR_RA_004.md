# Dossier — FS_VBR_RA_004 (ABSENCE)

**Claim (this audit tests):** BitLocker FVE marker '-FVE-FS-' at VBR+0x03 replaces ReFS signature when volume is encrypted

**Canonical claim (reference_table.csv):** File System: BitLocker FVE marker '-FVE-FS-' at VBR+0x03 replaces ReFS signature when volume is encrypted

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — win11refs4gbitlocked.raw (GPT part @16MiB) has VBR[0x03:0x0B]=='-FVE-FS-' exactly where 'ReFS' sits on unencrypted volumes. 1/1 image that exercises BitLocker.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- RefsIsBootSectorOurs checks 'ReFS' at VBR+0x03; a BitLocker volume would carry '-FVE-FS-' there. ABSENCE: '-FVE-FS-' occurs 0 times across all ReFS metadata (complements FS_VBR_002).

## Raw-disk proof
- probe `absent` ; validation matrix: `proofs/validation/FS_VBR_RA_004.csv`
- corrected registry note: Confirmed on win11refs4gbitlocked. FVE header (eb 58 90 2d 46 56 45 2d 46 53 2d) completely replaces ReFS VBR

## Proof links
- `proofs/validation/FS_VBR_RA_004.csv` (matrix) — 
