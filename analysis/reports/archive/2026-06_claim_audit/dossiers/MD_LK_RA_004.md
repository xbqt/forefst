# Dossier — MD_LK_RA_004 (PURE-RD-LAYOUT)

**Claim (this audit tests):** USN reason 0x100000 (Reparse point change) identifies link creation events. Junctions get separate event; symlinks combine with File create (0x00100100).

**Canonical claim (reference_table.csv):** Metadata: USN reason 0x100000 (Reparse point change) identifies link creation events. Junctions get separate event; symlinks combine with File create (0x00100100).

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — USN reason 0x100000 (reparse-point change) and the junction-vs-symlink USN event grouping are USN-journal behavioral facts, not directory-tree byte layout. Not measurable from this static harness.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- USN reason code. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_LK_RA_004.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 8.3 | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NEW): USN-log behavioral; no byte-layout signal.

## Proof links
- `proofs/validation/MD_LK_RA_004.csv` (matrix) — 
