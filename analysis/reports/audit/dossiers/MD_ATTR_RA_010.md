# Dossier — MD_ATTR_RA_010 (PURE-RD-LAYOUT)

**Claim (this audit tests):** $REPARSE_V2 (0xC0): REPARSE_DATA_BUFFER stored verbatim at val[0x0C]. Tag at val[0x0C], data_length at val[0x10]. CORRECTION: 0x8000001B = APPEXECLINK (app execution alias), the tag observed on winsider — NOT WCI/WOF. The prior _REPARSE_TAGS table was broadly mislabeled (off-by-one), now corrected to authoritative ntifs.h values: 0x80000024=LX_FIFO not AF_UNIX; AF_UNIX=0x80000023; WOF=0x80000017; WCI=0x80000018. WOF/WCI/DEDUP (0x80000013) NOT observed; AF_UNIX (0x80000023), LX_CHR (0x80000025), LX_BLK (0x80000026) NOW OBSERVED on win11refs2gtargeted (FS_REPS_RA_003/#341). Inventory (2084 instances / 47 images): SYMLINK 0xA000000C=2007, MOUNT_POINT 0xA0000003=47, APPEXECLINK 0x8000001B=28, LX_FIFO 0x80000024=2 (empty, the lxfifo file, mode S_IFIFO). refs.sys structurally recognizes only symlink/junction; all other tags stored verbatim.

**Canonical claim (reference_table.csv):** Metadata: $REPARSE_V2 (0xC0): REPARSE_DATA_BUFFER stored verbatim at val[0x0C]. Tag at val[0x0C], data_length at val[0x10]. CORRECTION: 0x8000001B = APPEXECLINK (app execution alias), the tag observed on winsider — NOT WCI/WOF. The prior _REPARSE_TAGS table was broadly mislabeled (off-by-one), now corrected to authoritative ntifs.h values: 0x80000024=LX_FIFO not AF_UNIX; AF_UNIX=0x80000023; WOF=0x80000017; WCI=0x80000018. WOF/WCI/DEDUP (0x80000013) NOT observed; AF_UNIX (0x80000023), LX_CHR (0x80000025), LX_BLK (0x80000026) NOW OBSERVED on win11refs2gtargeted (FS_REPS_RA_003/#341). Inventory (2084 instances / 47 images): SYMLINK 0xA000000C=2007, MOUNT_POINT 0xA0000003=47, APPEXECLINK 0x8000001B=28, LX_FIFO 0x80000024=2 (empty, the lxfifo file, mode S_IFIFO). refs.sys structurally recognizes only symlink/junction; all other tags stored verbatim.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — 0xC0 REPARSE tags at val[0x0C] across 2099 reparse records: 0xa000000c(MOUNT_POINT)=2018, 0xa0000003=47, 0x8000001b(APPEXECLINK)=28, 0x80000024(LX_FIFO)=3, 0x80000023(AF_UNIX)=1, 0x80000025(LX_CHR)=1, 0x80000026(LX_BLK)=1. APPEXECLINK=0x8000001b CONFIRMED (not WCI/WOF); AF_UNIX=0x80000023, LX_CHR=0x80000025, LX_BLK=0x80000026 all observed as the correction states.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 48/48 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Reparse sub-records (0xC0) carry marker 0x80000001 (REPARSE_DATA_BUFFER at val[0x0C]). Byte-verified 491/491. N/A where no reparse points.

## Raw-disk proof
- probe `subrec` ; validation matrix: `proofs/validation/MD_ATTR_RA_010.csv`
- corrected registry note: APPEXECLINK=0x8000001B (28 on winsider), not WCI/WOF. LX_FIFO=0x80000024 (the lxfifo file). WOF (0x80000017) + WCI (0x80000018) + DEDUP + LX_SYMLINK 0xA000001D NOT observed; AF_UNIX 0x80000023 + LX_CHR 0x80000025 + LX_BLK 0x80000026 NOW OBSERVED on win11refs2gtargeted (#341). refsanalysis _REPARSE_TAGS table rebuilt to authoritative values (maintainer flag).

## Proof links
- `proofs/validation/MD_ATTR_RA_010.csv` (matrix) — 
