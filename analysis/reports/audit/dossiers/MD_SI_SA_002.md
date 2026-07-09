# Dossier — MD_SI_SA_002 (BEHAVIORAL)

**Claim (this audit tests):** RefsComputeStandardInformationFromFcb (Win11 only): constructs complete 124-byte $STANDARD_INFORMATION from FCB fields. Maps all $SI offsets (corrected names: LastUsn 0x40, UsnJournalId 0x48, PackedEaSize 0x50, ReparseTag 0x54, NextFileId 0x58, ExtFileId_2/3 0x60/0x68, HardLinkCount 0x70, NextStreamSetId 0x74). Not present in Win10.

**Canonical claim (reference_table.csv):** Metadata: RefsComputeStandardInformationFromFcb (Win11 only): constructs complete 124-byte $STANDARD_INFORMATION from FCB fields. Maps all $SI offsets (corrected names: LastUsn 0x40, UsnJournalId 0x48, PackedEaSize 0x50, ReparseTag 0x54, NextFileId 0x58, ExtFileId_2/3 0x60/0x68, HardLinkCount 0x70, NextStreamSetId 0x74). Not present in Win10.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — All $SI offsets that RefsComputeStandardInformationFromFcb maps are individually disk-confirmed at value+0x28+offset (timestamps, attrs, iflags, LastUsn, UJID, PackedEaSize, ReparseTag, NextFileId, HardLinkCount). The function-level construction logic itself is decompilation-only.

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsComputeStandardInformationFromFcb__decomp.txt
- Static driver evidence: the $SI is assembled from FCB fields. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/MD_SI_SA_002.csv`
- corrected registry note: Would need attribute-level parser to verify from raw disk

## Proof links
- `proofs/static/RefsComputeStandardInformationFromFcb__decomp.txt` (static) — RefsComputeStandardInformationFromFcb
- `proofs/validation/MD_SI_SA_002.csv` (matrix) — 
