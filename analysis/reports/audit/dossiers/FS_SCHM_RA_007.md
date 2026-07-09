# Dossier — FS_SCHM_RA_007 (BEHAVIORAL)

**Claim (this audit tests):** Schema 0x1e0 = $EA (0xE0). Schema 0x1f0 (type 0xF0) = USN change-journal $Max metadata (NTFS $UsnJrnl:$Max: MaximumSize/AllocationDelta/UsnId/LowestValidUsn), an unnamed single-instance attr on the "Change Journal" file under OID 0x520 — NOT EFS and NOT $LOGGED_UTILITY_STREAM. CORRECTION: 0xF0 is created by RefsSetupUsnJournal (NOT RefsCreateLoggedUtilityStream, which uses type 0x100), the type-0xF0 ATTRIBUTE code path is v3.4-era (RefsSetupUsnJournal), but the registered SCHEMA entry 0x1f0 is v3.14+ — disk-confirmed absent on all v3.4/v3.7/v3.9/v3.10 schema tables and present on all v3.14/Insider; EFS uses the separate 0x100/0x200 path. Min 32B payload (0x20) + 12B wrapper = 44B.

**Canonical claim (reference_table.csv):** File System: Schema 0x1e0 = $EA (0xE0). Schema 0x1f0 (type 0xF0) = USN change-journal $Max metadata (NTFS $UsnJrnl:$Max: MaximumSize/AllocationDelta/UsnId/LowestValidUsn), an unnamed single-instance attr on the "Change Journal" file under OID 0x520 — NOT EFS and NOT $LOGGED_UTILITY_STREAM. CORRECTION: 0xF0 is created by RefsSetupUsnJournal (NOT RefsCreateLoggedUtilityStream, which uses type 0x100), the type-0xF0 ATTRIBUTE code path is v3.4-era (RefsSetupUsnJournal), but the registered SCHEMA entry 0x1f0 is v3.14+ — disk-confirmed absent on all v3.4/v3.7/v3.9/v3.10 schema tables and present on all v3.14/Insider; EFS uses the separate 0x100/0x200 path. Min 32B payload (0x20) + 12B wrapper = 44B.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Schema 0x1E0 ($EA) and 0x1F0 (type 0xF0, USN $Max) version-gating: both absent on v3.4 (0/13), v3.7 (0/1), v3.9 (0/2), v3.10 (0/2); present only v3.14 (92/92) and v3.15 (1/1). Confirms the resolution: the registered 0x1F0 schema entry is v3.14+, NOT v3.4.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Schema Table] Schema 0x1e0 = $EA (0xE0). Schema 0x1f0 (type 0xF0) = USN change-journal $Max metadata (NTFS $UsnJrnl:$Max: Ma — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SCHM_RA_007.csv`
- corrected registry note: Type 0xF0 observed on exactly 9 images (1 per image, all where USN journal active), always on the Change Journal file under OID 0x520, marker 0x80000001, 44 bytes. MaxSize 32MB/128MB = standard fsutil usn createjournal sizes. v3.14 empirical floor is a sampling artifact (no pre-v3.14 corpus image had USN active).

## Proof links
- `proofs/validation/FS_SCHM_RA_007.csv` (matrix) — 
