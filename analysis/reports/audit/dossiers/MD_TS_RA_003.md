# Dossier — MD_TS_RA_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** ADS (Alternate Data Stream) writes update parent file LastWriteTime AND LastAccessTime. The ADS operation is reflected in the main $SI timestamps.

**Canonical claim (reference_table.csv):** Metadata: ADS (Alternate Data Stream) writes update parent file LastWriteTime AND LastAccessTime. The ADS operation is reflected in the main $SI timestamps.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — ADS streams are stored as embedded type-0x80 sub-records under the parent's resident value; the parent $SI timestamps (M@val+0x30, A@val+0x40) are sane FILETIMEs. Whether an ADS write propagates to parent M/A is a live-operation behavioral property.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (ADS timestamp propagation). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_TS_RA_003.csv`
- corrected registry note: set-content -stream 'adstest' updated parent file M and A timestamps. See ra_step4_17_4th_timestamp_report.md

## Proof links
- `proofs/validation/MD_TS_RA_003.csv` (matrix) — 
