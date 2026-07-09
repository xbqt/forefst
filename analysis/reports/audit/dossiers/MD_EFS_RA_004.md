# Dossier — MD_EFS_RA_004 (ABSENCE)

**Claim (this audit tests):** $EFS (0x100): MI marker 0x80000002. CORRECTION: "$CBW4" is a FABRICATED stream name — it does not exist on disk (0 UTF-16LE occurrences) nor as an EFS name in the binary (the 140 "CBW4" decomp hits are mangled C++ template names span<$$CBW4byte@utl>, i.e. checksum span<4byte>, unrelated to EFS). Type 0x100 is the named $LOGGED_UTILITY_STREAM container; the only named instance on disk is $EFS. 7 entries across 110 images.

**Canonical claim (reference_table.csv):** Metadata: $EFS (0x100): MI marker 0x80000002. CORRECTION: "$CBW4" is a FABRICATED stream name — it does not exist on disk (0 UTF-16LE occurrences) nor as an EFS name in the binary (the 140 "CBW4" decomp hits are mangled C++ template names span<$$CBW4byte@utl>, i.e. checksum span<4byte>, unrelated to EFS). Type 0x100 is the named $LOGGED_UTILITY_STREAM container; the only named instance on disk is $EFS. 7 entries across 110 images.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — $EFS (type 0x100) carries MI marker 0x80000002 in 7/7 occurrences. Key stream name is '$EFS' in 7/7; ZERO '$CBW4' named instances anywhere. const@8=0x0C header present. Confirms '$CBW4 is fabricated, only named 0x100 instance on disk is $EFS'.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ABSENCE: the matrix IS the proof — '$CBW4' must occur 0 times across all metadata. The binary token $$CBW4byte@utl is a span<4 byte> checksum, not a stream name (errata E35). reference_table MD_EFS_RA_004 records the correction.

## Raw-disk proof
- probe `absent` ; validation matrix: `proofs/validation/MD_EFS_RA_004.csv`
- corrected registry note: UTF-16LE disk scan: $CBW4=0, $EFS=50. The 7 type-0x100 entries are all $EFS (encryption). No $CBW4 anywhere.

## Proof links
- `proofs/validation/MD_EFS_RA_004.csv` (matrix) — 
