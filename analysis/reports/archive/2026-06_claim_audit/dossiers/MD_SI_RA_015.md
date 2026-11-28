# Dossier — MD_SI_RA_015 (BEHAVIORAL)

**Claim (this audit tests):** RETRACTED: $SI+0x30 is NOT a USN/change-journal byte-offset. Type-0x10 $SI+0x30 = 0 on 0/32,629 own-rows across the corpus. The real per-file->journal link is LastUsn ($SI+0x40 / value+0x68) = virtual byte offset of the file's latest $UsnJrnl:$J record + UsnJournalId ($SI+0x48 / value+0x70).

**Canonical claim (reference_table.csv):** Metadata: RETRACTED: $SI+0x30 is NOT a USN/change-journal byte-offset. Type-0x10 $SI+0x30 = 0 on 0/32,629 own-rows across the corpus. The real per-file->journal link is LastUsn ($SI+0x40 / value+0x68) = virtual byte offset of the file's latest $UsnJrnl:$J record + UsnJournalId ($SI+0x48 / value+0x70).

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — $SI+0x30 is UNPOPULATED (0/32629), not a USN — E30 retracted

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- E2/RD: $SI+0x30 USN is a $UsnJrnl:$J byte offset (not a sequence number). Semantic; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SI_RA_015.csv`
- corrected registry note: RETRACTED 2026-06-19 (E30 retracted 2026-06-17, E45): the 'USN at $SI+0x30, populated 53-99.5%' values were a misread of the type-0x30 index-entry FileSize at value+0x58. Proven: USN = LastUsn@value+0x68 (480/480 $J-record matches). | 0% nonzero on file_own + dir_own across ALL versions; file_resident 53-99.5% (tracks journal activity).

## Proof links
- `proofs/validation/MD_SI_RA_015.csv` (matrix) — 
