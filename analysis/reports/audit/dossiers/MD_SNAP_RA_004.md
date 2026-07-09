# Dossier — MD_SNAP_RA_004 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Snapshot sub-record format: size + header + UTF-16 name + metadata + extents. Stream count increases per snapshot (4-6 for 1-2 snapshots).

**Canonical claim (reference_table.csv):** Metadata: Snapshot sub-record format: size + header + UTF-16 name + metadata + extents. Stream count increases per snapshot (4-6 for 1-2 snapshots).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Snapshot sub-record format confirmed: size + header + UTF-16 name (in key) + metadata + (snapshot) descriptor. On the 2-snapshot files, stream count rises with snapshot count (test.txt with multiple versions shows multiple 0xB0 snapshot rows). Each is a 116-byte value with flags==2. Consistent across the 29 snapshot entries.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Snapshot 0xB0 layout (disk-proven marker MD_SNAP_RA_006). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SNAP_RA_004.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 10.2

## Proof links
- `proofs/validation/MD_SNAP_RA_004.csv` (matrix) — 
