# Dossier — MD_SNAP_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Snapshots preserve complete extent descriptor sets for each file version. Enables recovery of previous file content from raw disk.

**Canonical claim (reference_table.csv):** Metadata: Snapshots preserve complete extent descriptor sets for each file version. Enables recovery of previous file content from raw disk.

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Snapshot sub-records carry stream-summary descriptors (flags@0x10==2) per file version; multiple versions per file observed (e.g. test.txt has 4 snapshot entries: firstversion/v2/v3/last). The 'preserves complete extent descriptor sets enabling prior-content recovery' is a recovery-capability claim; only resident/inline content was present in-corpus, so extent-set preservation is inferred from the descriptor presence, not a measured non-resident extent set.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Snapshot extents (S7). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SNAP_RA_002.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 10.3 | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NEW): Behavioral/recovery claim; the descriptor structure is on-disk but the non-resident extent recovery path is not exercised by corpus images.

## Proof links
- `proofs/validation/MD_SNAP_RA_002.csv` (matrix) — 
