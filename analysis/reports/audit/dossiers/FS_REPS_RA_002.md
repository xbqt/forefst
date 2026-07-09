# Dossier — FS_REPS_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** WSL stores Linux metadata in Extended Attributes ($LXUID $LXGID $LXMOD $LXDEV) using FILE_FULL_EA_INFORMATION format NOT in reparse data. WSL special files use reparse tags AF_UNIX 0x80000023, LX_FIFO 0x80000024, LX_CHR 0x80000025, LX_BLK 0x80000026 (CORRECTED off-by-one, E41/#341; confirmed on win11refs2gtargeted). $LXDEV = 8 bytes (u32 major + u32 minor); $LXUID/$LXGID/$LXMOD = 4B. WSL symlinks use IO_REPARSE_TAG_LX_SYMLINK (0xA000001D). Requires -o metadata mount option.

**Canonical claim (reference_table.csv):** File System: WSL stores Linux metadata in Extended Attributes ($LXUID $LXGID $LXMOD $LXDEV) using FILE_FULL_EA_INFORMATION format NOT in reparse data. WSL special files use reparse tags AF_UNIX 0x80000023, LX_FIFO 0x80000024, LX_CHR 0x80000025, LX_BLK 0x80000026 (CORRECTED off-by-one, E41/#341; confirmed on win11refs2gtargeted). $LXDEV = 8 bytes (u32 major + u32 minor); $LXUID/$LXGID/$LXMOD = 4B. WSL symlinks use IO_REPARSE_TAG_LX_SYMLINK (0xA000001D). Requires -o metadata mount option.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Reparse Points] WSL stores Linux metadata in Extended Attributes ($LXUID $LXGID $LXMOD $LXDEV) using FILE_FULL_EA_INFORMATION — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_REPS_RA_002.csv`
- corrected registry note: EA parsing verified on win11refs4gattributes.raw WSL files. $LXUID/$LXGID/$LXMOD extracted. See ra_step4_3_attributes_report.md and ra_step4_14_reparse_points_report.md

## Proof links
- `proofs/validation/FS_REPS_RA_002.csv` (matrix) — 
