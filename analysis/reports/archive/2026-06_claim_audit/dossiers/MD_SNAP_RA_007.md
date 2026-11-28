# Dossier — MD_SNAP_RA_007 (STRUCTURAL)

**Claim (this audit tests):** E20 reaffirmed: ALL alternate data streams (ADS, type 0xB0) are inline/resident — every 0xB0 ADS has stream_flags=0x02 (159/159), including the single attr_flags=0x1000 ADS (still inline). The "genuine non-resident ADS" claim is REFUTED; attr-bit 0x1000 marks ADS-on-a-file-with-snapshots/stream-set, not non-residency.

**Canonical claim (reference_table.csv):** Metadata: E20 reaffirmed: ALL alternate data streams (ADS, type 0xB0) are inline/resident — every 0xB0 ADS has stream_flags=0x02 (159/159), including the single attr_flags=0x1000 ADS (still inline). The "genuine non-resident ADS" claim is REFUTED; attr-bit 0x1000 marks ADS-on-a-file-with-snapshots/stream-set, not non-residency.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Every 0xB0 ADS (flags@val[0x10]==0) is inline/resident - found as an embedded sub-record inside the resident type-0x30 directory value (956/956), never as a non-resident extent stream. The snapshot entries (flags==2) are also embedded. No non-resident 0xB0 ADS exists in the 113-image corpus.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Same as MD_SNAP_RA_005 ($SI framing). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SNAP_RA_007.csv`
- corrected registry note: All 159 ADS stream_flags=0x02 (inline); the one attr_flags=0x1000 ADS still stream_flags=0x02. E20 (ADS always inline) HOLDS.

## Proof links
- `proofs/validation/MD_SNAP_RA_007.csv` (matrix) — 
