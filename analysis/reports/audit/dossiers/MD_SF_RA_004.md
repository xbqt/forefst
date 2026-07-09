# Dossier — MD_SF_RA_004 (BEHAVIORAL)

**Claim (this audit tests):** Fully sparse files have alloc_size=0 on disk (confirmed via refs_dataruns.py). No clusters allocated for fully sparse content.

**Canonical claim (reference_table.csv):** Metadata: Fully sparse files have alloc_size=0 on disk (confirmed via refs_dataruns.py). No clusters allocated for fully sparse content.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral/structural (sparse alloc=0); the 0x40 alloc_size field is disk-proven in MD_DATA_RA_005. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SF_RA_004.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 4

## Proof links
- `proofs/validation/MD_SF_RA_004.csv` (matrix) — 
