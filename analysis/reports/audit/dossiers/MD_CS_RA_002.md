# Dossier — MD_CS_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Case-sensitive files get distinct OIDs and type 0x20 stream indices. Files differing only in case coexist as separate B+-tree entries.

**Canonical claim (reference_table.csv):** Metadata: Case-sensitive files get distinct OIDs and type 0x20 stream indices. Files differing only in case coexist as separate B+-tree entries.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral; type 0x20 index disk-proven (FN_DTBL_003). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_CS_RA_002.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 7.2

## Proof links
- `proofs/validation/MD_CS_RA_002.csv` (matrix) — 
