# Dossier — MD_SI_RA_006 (BEHAVIORAL)

**Claim (this audit tests):** InternalFlags bit mapping: bit0=DELETE/DISPOSITION (FCB bit27 — set in DeleteDirectoryOnDisk/EFS paths, NOT integrity; integrity-stream = file_attrs 0x8000 per MD_INTG_RA_001/#342), bit1=DEDUP/COW(FCB bit22), bit2=BIT_0xB(FCB bit11), bit3=BIT_0x1F(FCB bit31). Most common: 0x08 (BIT_0x1F at 33553 on Insider). Bits 4-5 from RefsConvertToStandardInfoLinkCount.

**Canonical claim (reference_table.csv):** Metadata: InternalFlags bit mapping: bit0=DELETE/DISPOSITION (FCB bit27 — set in DeleteDirectoryOnDisk/EFS paths, NOT integrity; integrity-stream = file_attrs 0x8000 per MD_INTG_RA_001/#342), bit1=DEDUP/COW(FCB bit22), bit2=BIT_0xB(FCB bit11), bit3=BIT_0x1F(FCB bit31). Most common: 0x08 (BIT_0x1F at 33553 on Insider). Bits 4-5 from RefsConvertToStandardInfoLinkCount.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — On-disk: type-0x10 own-row iflags take values {0, 0x20}; resident type-0x30 iflags take {0,0x08,0x28}. The individual bit-to-FCB-bit mapping (bit0=DELETE/DISPOSITION etc.) is not derivable from disk bytes alone.

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsComputeStandardInformationFromFcb__decomp.txt
- Static driver evidence: InternalFlags ($SI+0x24) bits map from FCB+0x08 flags. bit0<-FCB bit27 = a delete-disposition/EFS transient state (set in DeleteDirectoryOnDisk), NOT integrity (corrected E43/#342 — the integrity-stream marker is file_attrs 0x8000); bit1<-bit22 dedup/COW. Proof is the decompiled RefsComputeStandardInformationInternalFromFcb.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/MD_SI_RA_006.csv`
- corrected registry note: Insider: 0x08=33553, 0x01=997, 0x20=78, 0x05=7, 0x28=3

## Proof links
- `proofs/static/RefsComputeStandardInformationFromFcb__decomp.txt` (static) — RefsComputeStandardInformationFromFcb
- `proofs/validation/MD_SI_RA_006.csv` (matrix) — 
