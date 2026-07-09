# Dossier — MD_ATTR_007 (BEHAVIORAL)

**Claim (this audit tests):** $NAMED_DATA: ADS, resident, limited size

**Canonical claim (reference_table.csv):** Metadata: $NAMED_DATA: ADS, resident, limited size

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — ADS observed on disk as resident 0xB0 sub-records (marker MI 0x80000002, StreamSummary flags!=0) with a named key, e.g. 'latotale'/'test2'/'test3' (116-byte values). The string '$NAMED_DATA' itself is an E1 binary literal, not on disk; 'resident, limited size' is the static label.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** E1 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ADS capability (0xB0, disk-proven in MD_SNAP_RA_006). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_007.csv`
- corrected registry note: DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NOT_TESTED): ADS-as-0xB0 disk mechanism confirmed; the attribute-name string and size-limit are static (E1).

## Proof links
- `proofs/validation/MD_ATTR_007.csv` (matrix) — 
