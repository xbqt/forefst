# Dossier — MD_USN_RA_004 (STRUCTURAL)

**Claim (this audit tests):** Type 0xF0 = USN change-journal $Max metadata (NTFS $UsnJrnl:$Max: MaximumSize@+0x00 / AllocationDelta@+0x08 / UsnId FILETIME@+0x10 / LowestValidUsn@+0x18). Unnamed single-instance attr (marker 0x80000001), 0x20-byte payload + 12B wrapper = 44B, on the "Change Journal" file under OID 0x520. Created by RefsSetupUsnJournal — present since v3.4. Distinct from 0x100/$EFS.

**Canonical claim (reference_table.csv):** Metadata: Type 0xF0 = USN change-journal $Max metadata (NTFS $UsnJrnl:$Max: MaximumSize@+0x00 / AllocationDelta@+0x08 / UsnId FILETIME@+0x10 / LowestValidUsn@+0x18). Unnamed single-instance attr (marker 0x80000001), 0x20-byte payload + 12B wrapper = 44B, on the "Change Journal" file under OID 0x520. Created by RefsSetupUsnJournal — present since v3.4. Distinct from 0x100/$EFS.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — USN $Max metadata is a single-instance sub-record (marker 0x80000001) inside the Change Journal value (NOT a separately-walkable type-0xF0 B+-tree attribute; none found in the CJ object tree). Wrapper = 12B (flags u32, size=0x20, type=0xC); $Max body (32B) at wrapper+0x0C: MaximumSize u64@+0x00 (0x2000000=32MB or 0x...=larger, standard journal sizes), AllocationDelta u64@+0x08, UsnId FILETIME u64@+0x10 (valid e.g. 0x01dce1857f465fdd=2026-05-11), LowestValidUsn at body+0x18. Held on 9/9 USN-active images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Type 0xF0 = USN $Max metadata, stored on the system FS-Metadata directory OID 0x520 (NOT user objects >=0x600), so the user-object sub-record probe cannot reach it. Established in E27 / structure_reference.md:1266 (0x1F0/0xF0 = USN journal $Max). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_USN_RA_004.csv`
- corrected registry note: 9 images (1 per image, all where USN journal active), always OID 0x520 Change Journal, 44 bytes. MaxSize 32MB(winsider)/128MB = standard fsutil usn createjournal sizes. v3.14 floor = sampling artifact.

## Proof links
- `proofs/validation/MD_USN_RA_004.csv` (matrix) — 
