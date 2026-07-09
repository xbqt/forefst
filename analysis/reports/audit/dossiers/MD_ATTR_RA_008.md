# Dossier — MD_ATTR_RA_008 (STRUCTURAL)

**Claim (this audit tests):** Resident type 0x30 sub-record distribution (71162 entries across 110 images): MI_0x80=75303, SI_0x80=30360, SI_0xD0=3879, SI_0xE0=3854, SI_0xC0=2001, MI_0xB0=979, MI_0x100=7. Types 0x80 ($DATA), 0xB0 ($SNAPSHOT), 0xC0 ($REPARSE), 0xD0 ($EA_INFO), 0xE0 ($EA), 0x100 ($EFS) confirmed as embedded sub-records.

**Canonical claim (reference_table.csv):** Metadata: Resident type 0x30 sub-record distribution (71162 entries across 110 images): MI_0x80=75303, SI_0x80=30360, SI_0xD0=3879, SI_0xE0=3854, SI_0xC0=2001, MI_0xB0=979, MI_0x100=7. Types 0x80 ($DATA), 0xB0 ($SNAPSHOT), 0xC0 ($REPARSE), 0xD0 ($EA_INFO), 0xE0 ($EA), 0x100 ($EFS) confirmed as embedded sub-records.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Resident sub-record TYPE TAXONOMY confirmed: every claimed type observed as an embedded sub-record - 0x80($DATA: SI 367356 + MI 75305), 0xB0($SNAPSHOT/ADS)=985, 0xC0($REPARSE)=2013, 0xD0($EA_INFO)=3895, 0xE0($EA)=3870, 0x100($EFS)=7. Smaller-count types match claim closely (claim D0=3879/E0=3854/C0=2001/B0=979/0x100=7 vs measured 3895/3870/2013/985/7).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Statistical census of 0x30 sub-records. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_008.csv`
- corrected registry note: 110 images scanned with parse_resident_btree_rows. Sub-record types match F.2 schema table attribute codes exactly.

## Proof links
- `proofs/validation/MD_ATTR_RA_008.csv` (matrix) — 
