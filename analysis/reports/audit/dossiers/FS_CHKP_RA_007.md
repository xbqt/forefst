# Dossier — FS_CHKP_RA_007 (BEHAVIORAL)

**Claim (this audit tests):** CHKP 0x50-0x53: version echo field. Contains 0x00 on Win10 (3.4) and packed version 0x000E0003 on Win11 (3.14)

**Canonical claim (reference_table.csv):** File System: CHKP 0x50-0x53: version echo field. Contains 0x00 on Win10 (3.4) and packed version 0x000E0003 on Win11 (3.14)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP+0x50 version echo: 0x00000000 on v3.4/3.7/3.9 (12 imgs), 0x000E0003 on v3.14 native (35 imgs), 0x000A0003 on v3.10 (1). Matches '0 on Win10/3.4, packed 0x000E0003 on Win11/3.14'.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/ReadLatestCheckpoint__decomp.txt
- CmsVolume::ReadLatestCheckpoint reads the version echo at CHKP+0x50. Byte-observed 0x0 (v3.4) / 0xe0003 (v3.14). Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_CHKP_RA_007.csv`
- corrected registry note: Win10: 0x00000000. Win11 native and upgraded: 0x000E0003 (=3.14 packed as major|minor). See report_checkpoint_deep_analysis.md

## Proof links
- `proofs/static/ReadLatestCheckpoint__decomp.txt` (static) — ReadLatestCheckpoint
- `proofs/validation/FS_CHKP_RA_007.csv` (matrix) — 
