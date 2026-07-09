# Dossier — MD_SNAP_RA_006 (PURE-RD-LAYOUT)

**Claim (this audit tests):** $SNAPSHOT/ADS (0xB0): identical stream summary format to SI $DATA. Storage type at val[0x10]: 0=ADS, non-zero=snapshot. 979 MI entries across 110 images (678 ADS + 30 snapshots).

**Canonical claim (reference_table.csv):** Metadata: $SNAPSHOT/ADS (0xB0): identical stream summary format to SI $DATA. Storage type at val[0x10]: 0=ADS, non-zero=snapshot. 979 MI entries across 110 images (678 ADS + 30 snapshots).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — $SNAPSHOT/ADS (0xB0) storage-type at val[0x10]: 0=ADS, non-zero(==2)=snapshot, confirmed on 985 entries across 47 images (956 ADS + 29 snapshots). Same stream-summary offset layout as SI $DATA. Snapshot sub-records observed with snapshot name stored inline as UTF-16LE in the sub-record key at key[16:] (e.g. 'firstversion','v2','v3','last' on win11refs2tsnapshots).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 47/47 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- 0xB0 (ADS / snapshot stream) sub-records carry marker 0x80000002 (multi-instance). Byte-verified 184/184. N/A where no ADS.

## Raw-disk proof
- probe `subrec` ; validation matrix: `proofs/validation/MD_SNAP_RA_006.csv`
- corrected registry note: 979 entries: val[0x10]=0 for ADS, val[0x10]!=0 for snapshots. Stream summary at same offsets as SI $DATA.

## Proof links
- `proofs/validation/MD_SNAP_RA_006.csv` (matrix) — 
