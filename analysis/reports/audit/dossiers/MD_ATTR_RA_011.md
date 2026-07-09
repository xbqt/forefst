# Dossier — MD_ATTR_RA_011 (PURE-RD-LAYOUT)

**Claim (this audit tests):** $EA_INFO (0xD0): fixed 20B. CORRECTION: $SI+0x50 PackedEaSize (v3.10+) = val[0x0C] (= Σ(5+EaNameLength+EaValueLength), the NTFS-conventional PackedEaSize cached in FCB+0xA0), NOT val[0x10]. val[0x10] = Σ align4(8+nameLen+1+valLen) = serialized on-disk footprint. The two size fields were inverted in the prior claim. 3889 entries across 3 v3.14 images.

**Canonical claim (reference_table.csv):** Metadata: $EA_INFO (0xD0): fixed 20B. CORRECTION: $SI+0x50 PackedEaSize (v3.10+) = val[0x0C] (= Σ(5+EaNameLength+EaValueLength), the NTFS-conventional PackedEaSize cached in FCB+0xA0), NOT val[0x10]. val[0x10] = Σ align4(8+nameLen+1+valLen) = serialized on-disk footprint. The two size fields were inverted in the prior claim. 3889 entries across 3 v3.14 images.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — EA_INFO(0xD0) is fixed 20B: 3900/3900. $SI+0x50 (= type-0x10 value+0x78, since $SI base is value+0x28) == EA_INFO val[0x0C] in 5/5 files where $SI+0x50 is nonzero; == val[0x10] in 0/5. The inversion CORRECTION is directionally confirmed (PackedEaSize=val[0x0C], NOT val[0x10]). Example: val[0x0C]=45, val[0x10]=60, $SI+0x50=45.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 4/4 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $EA_INFO (0xD0) value is fixed 20 bytes. Byte-verified 4/4 on the attributes image. N/A where no EAs.

## Raw-disk proof
- probe `subrec` ; validation matrix: `proofs/validation/MD_ATTR_RA_011.csv`
- corrected registry note: $SI+0x50 == val[0x0C] in 3852/3852, == val[0x10] in 0% (small image: $SI+0x50=45=val0x0C, val0x10=60). val[0x10] does NOT match.

## Proof links
- `proofs/validation/MD_ATTR_RA_011.csv` (matrix) — 
