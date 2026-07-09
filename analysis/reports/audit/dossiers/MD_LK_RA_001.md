# Dossier — MD_LK_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Junctions, directory symlinks, and file symlinks all supported on ReFS. All symlink types show 'l' flag in PowerShell Mode column.

**Canonical claim (reference_table.csv):** Metadata: Junctions, directory symlinks, and file symlinks all supported on ReFS. All symlink types show 'l' flag in PowerShell Mode column.

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — PowerShell 'l' Mode flag for junctions/symlinks is a UI/reparse-attribute observation, not a byte-layout claim. The underlying reparse attribute (has_reparse bit 0x0400) is observable on disk but the 'l flag in PowerShell Mode' is presentation-layer.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Link capability; reparse (0xC0) disk-proven (MD_ATTR_RA_010). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_LK_RA_001.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 8.1 | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NEW): Pure RD-observation/behavioral; no measurable byte-layout assertion.

## Proof links
- `proofs/validation/MD_LK_RA_001.csv` (matrix) — 
