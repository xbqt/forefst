# Dossier — MD_SI_RA_004 (ABSENCE)

**Claim (this audit tests):** Directory DataSize=0 invariant: 32490/32490 directories (100%) have $SI+0x38 = 0 across all 110 tested images and all versions (v3.4 through v3.14+/insider). Directories never have a $DATA stream, so DataSize is always zero.

**Canonical claim (reference_table.csv):** Metadata: Directory DataSize=0 invariant: 32490/32490 directories (100%) have $SI+0x38 = 0 across all 110 tested images and all versions (v3.4 through v3.14+/insider). Directories never have a $DATA stream, so DataSize is always zero.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — directory $SI+0x38 (DataSize) = 0 on 25494/25494 directories across all 113 images (v3.4 through v3.14+/insider). 0 nonzero. Directory classification by presence of type-0x30 filename rows OR dir-attr bit, robust to native-v3.14 masked dir flag.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $SI base = value+0x28; DataSize at SI+0x38. Directories (file_attrs SI+0x20 bit 0x10000000) have DataSize 0 (32490/32490 in the thesis). Byte-verified: 0 directories with non-zero DataSize.

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_SI_RA_004.csv`
- corrected registry note: 110 images scanned: 32490 directories, 0 exceptions. Invariant holds on v3.4 (12 images), v3.7-v3.10 (5 images), v3.14+ (91 images), v6.66 (2 images).

## Proof links
- `proofs/validation/MD_SI_RA_004.csv` (matrix) — 
