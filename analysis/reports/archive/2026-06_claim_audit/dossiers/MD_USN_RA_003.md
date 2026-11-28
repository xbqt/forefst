# Dossier — MD_USN_RA_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** USN reason code catalog for ReFS operations including Reparse point change 0x100000. Covers file create/delete/modify/rename/attribute change/encryption/sparse/security.

**Canonical claim (reference_table.csv):** Metadata: USN reason code catalog for ReFS operations including Reparse point change 0x100000. Covers file create/delete/modify/rename/attribute change/encryption/sparse/security.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — USN reason@+0x38 catalog observed on disk incl. reparse-point-change 0x100000 (874 records on attributestest2), create 0x100, delete 0x200, rename-old 0x1000, rename-new 0x2000, basic-info 0x8000, encryption 0x40000, data overwrite 0x1, data extend 0x2, close 0x80000000 (OR-ed). All catalog codes appear as the base bits of real records.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- USN reason catalog (forefst usn_reason_to_str). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_USN_RA_003.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 3.3

## Proof links
- `proofs/validation/MD_USN_RA_003.csv` (matrix) — 
