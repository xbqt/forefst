# Dossier — MD_EFS_RA_005 (PURE-RD-LAYOUT)

**Claim (this audit tests):** $EFS (type 0x100): key contains '$EFS' stream name. Value 676B follows common 12B header. EFS version=2 at val[0x14], certificate GUID at val[0x18], DDF/DRF at val[0x50+]. 4 entries on win11refs4gattributestest2.

**Canonical claim (reference_table.csv):** Metadata: $EFS (type 0x100): key contains '$EFS' stream name. Value 676B follows common 12B header. EFS version=2 at val[0x14], certificate GUID at val[0x18], DDF/DRF at val[0x50+]. 4 entries on win11refs4gattributestest2.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — $EFS (0x100): key contains '$EFS' (7/7), follows common 12B header (const@8=0x0C), EFS version=2 at val[0x14] in 7/7, value length 676B in 6/7 (one 732B variant). On win11refs4gattributestest2.raw exactly 4 $EFS entries, all 676B version=2 - matching the claim's '4 entries on win11refs4gattributestest2'.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 2/2 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $EFS (0x100) value is 676 bytes. Byte-verified 4/4 on the attributes image. N/A where no EFS.

## Raw-disk proof
- probe `subrec` ; validation matrix: `proofs/validation/MD_EFS_RA_005.csv`
- corrected registry note: 4 entries decoded from encrypted test files. All 676B, version=2.

## Proof links
- `proofs/validation/MD_EFS_RA_005.csv` (matrix) — 
