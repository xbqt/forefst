# Dossier — FS_REPS_RA_003 (STRUCTURAL)

**Claim (this audit tests):** WSL special-file reparse tags confirmed on disk (win11refs2gtargeted): AF_UNIX 0x80000023, LX_FIFO 0x80000024, LX_CHR 0x80000025, LX_BLK 0x80000026 (WSL 'ln -s' on a DrvFs metadata mount produced a Windows SYMLINK 0xA000000C, not LX_SYMLINK 0xA000001D). Linux metadata in EAs: $LXUID/$LXGID/$LXMOD = u32 (4B); $LXDEV = 8 bytes = u32 major + u32 minor, present only on device nodes (chr/blk). Reparse tag VALUES are minifilter-handled (opaque to refs.sys); the $LX* EAs ARE parsed by refs.sys. Corrects the prior off-by-one tag guesses and '$LXDEV=4B / not observed'.

**Canonical claim (reference_table.csv):** File System: WSL special-file reparse tags confirmed on disk (win11refs2gtargeted): AF_UNIX 0x80000023, LX_FIFO 0x80000024, LX_CHR 0x80000025, LX_BLK 0x80000026 (WSL 'ln -s' on a DrvFs metadata mount produced a Windows SYMLINK 0xA000000C, not LX_SYMLINK 0xA000001D). Linux metadata in EAs: $LXUID/$LXGID/$LXMOD = u32 (4B); $LXDEV = 8 bytes = u32 major + u32 minor, present only on device nodes (chr/blk). Reparse tag VALUES are minifilter-handled (opaque to refs.sys); the $LX* EAs ARE parsed by refs.sys. Corrects the prior off-by-one tag guesses and '$LXDEV=4B / not observed'.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsQueryLxMetadataEa__decomp.txt
- E2+RD. RD (win11refs2gtargeted): 4 WSL tags read by raw struct.unpack; $LXDEV testchr 1:3 / testblk 7:0 (matches mknod c 1 3 / b 7 0 oracle), device nodes only; lxsymlink=0xA000000C. Static: RefsQueryLxMetadataEa (win11_4b0558f6 + insider) validates $LXDEV EaValueLength==8 and splits major/minor; tag values 0x80000023-26 are 0 matches in all refs.sys builds (minifilter-handled). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_REPS_RA_003.csv`
- corrected registry note: win11refs2gtargeted.raw: 5 WSL files; tags read by struct.unpack match exactly; $LXDEV testchr=1,3 testblk=7,0 (matches 'mknod c 1 3'/'b 7 0' oracle); $LXDEV present only on chr/blk. lxsymlink tag=0xA000000C. Whole-image LX_SYMLINK 0xA000001D count=0.

## Proof links
- `proofs/static/RefsQueryLxMetadataEa__decomp.txt` (static) — RefsQueryLxMetadataEa
- `proofs/validation/FS_REPS_RA_003.csv` (matrix) — 
