# Dossier — MD_DEL_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** $RECYCLE.BIN creation captured in USN with full OID/attribute lifecycle. Created on-demand during first Recycle Bin deletion. Attributes set to Hidden|System|Directory (0x16).

**Canonical claim (reference_table.csv):** Metadata: $RECYCLE.BIN creation captured in USN with full OID/attribute lifecycle. Created on-demand during first Recycle Bin deletion. Attributes set to Hidden|System|Directory (0x16).

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — On the 8 recycle-bearing images, $RECYCLE.BIN appears as a directory containing $R (non-resident) and $I (resident) entries created on first deletion. The Hidden|System|Directory (0x16) attribute and USN-lifecycle parts are USN-log/behavioral, not measured by this byte-layout harness.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (deletion via USN). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DEL_RA_001.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 5.1 | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NEW): The on-disk presence/structure of $RECYCLE.BIN is confirmed; the USN-capture and attribute-bit (0x16) claims are behavioral/USN-log facts not exercised here.

## Proof links
- `proofs/validation/MD_DEL_RA_001.csv` (matrix) — 
