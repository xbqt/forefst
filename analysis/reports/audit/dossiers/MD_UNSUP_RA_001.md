# Dossier — MD_UNSUP_RA_001 (ABSENCE)

**Claim (this audit tests):** Object IDs (fsutil objectid), short names (fsutil file setshortname), and DAX mode NOT supported on ReFS. Hard-link enumeration (fsutil hardlink list) IS supported on native v3.14 (#340/FN_LINK_002 — verified on win11refs2gtargeted); it was unsupported on v3.4.

**Canonical claim (reference_table.csv):** Metadata: Object IDs (fsutil objectid), short names (fsutil file setshortname), and DAX mode NOT supported on ReFS. Hard-link enumeration (fsutil hardlink list) IS supported on native v3.14 (#340/FN_LINK_002 — verified on win11refs2gtargeted); it was unsupported on v3.4.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ABSENCE (no $MFT/8.3 short names, #335; Object IDs and DAX unsupported). NOTE: hard-link enumeration (fsutil hardlink list) IS supported on native v3.14 (#340/FN_LINK_002, verified on win11refs2gtargeted) — it was unsupported on v3.4. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_UNSUP_RA_001.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 11.1

## Proof links
- `proofs/validation/MD_UNSUP_RA_001.csv` (matrix) — 
