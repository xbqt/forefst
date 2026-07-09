# Dossier — MD_SI_RA_013 (BEHAVIORAL)

**Claim (this audit tests):** $SI+0x40 ClassTag = the file LastUsn (byte offset of its most recent $UsnJrnl:$J record, from journal write cursor VCB+0x3a0 / FCB+0xe0; 8-byte aligned). $SI+0x48 SessionTimestamp = the USN JOURNAL ID (VCB+0x388, a FILETIME). NOT a storage-tiering tag (the E3/E24 tiering theory is DISPROVEN). FCB bit23 = cached last-USN valid for current journal epoch. Both written atomically by RefsWriteFcbUsnRecordToJournal->RefsPartialSetStandardInfo (gated VCB+0x18 & 0x80000), explaining the 0-violation co-occurrence.

**Canonical claim (reference_table.csv):** Metadata: $SI+0x40 ClassTag = the file LastUsn (byte offset of its most recent $UsnJrnl:$J record, from journal write cursor VCB+0x3a0 / FCB+0xe0; 8-byte aligned). $SI+0x48 SessionTimestamp = the USN JOURNAL ID (VCB+0x388, a FILETIME). NOT a storage-tiering tag (the E3/E24 tiering theory is DISPROVEN). FCB bit23 = cached last-USN valid for current journal epoch. Both written atomically by RefsWriteFcbUsnRecordToJournal->RefsPartialSetStandardInfo (gated VCB+0x18 & 0x80000), explaining the 0-violation co-occurrence.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — LastUsn ($SI+0x40, val+0x68): nonzero on 3392 own-rows across exactly 10 USN-active images (winsider 2890, win11refstestmftecmd 200, win11refs4gattributestest2 270, win11refs2gtargeted 8, win11refslasttests x4...); ALL 3392 are 8-byte aligned (3392/3392) and upper-32 = 0 (3392/3392). UsnJournalId ($SI+0x48, val+0x70) co-populated on the same 10 images. Zero on all 103 USN-inactive images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- E2/RD (errata): $SI+0x40 (formerly 'ClassTag') = LastUsn, a $UsnJrnl:$J byte offset. Populated when USN active (270/388 rows on the attributes image). Semantic; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SI_RA_013.csv`
- corrected registry note: 717/717 ClassTag values 8-byte aligned (USN records are 8-aligned); exactly 1 distinct SessionTimestamp per volume (journal id, not per-file); upper-32 always 0; nonzero only on v3.14+ images with active USN journal.

## Proof links
- `proofs/validation/MD_SI_RA_013.csv` (matrix) — 
