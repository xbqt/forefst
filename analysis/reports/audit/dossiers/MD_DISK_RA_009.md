# Dossier — MD_DISK_RA_009 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Case-sensitive directory on disk: both case variants (e.g. ABC.txt and abc.txt) coexist as separate B+-tree keys with distinct OIDs.

**Canonical claim (reference_table.csv):** Metadata: Case-sensitive directory on disk: both case variants (e.g. ABC.txt and abc.txt) coexist as separate B+-tree keys with distinct OIDs.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — On win11refs4gattributestest2 (case-sensitive dir feature), two filename keys differing only in case coexist as distinct type-0x30 B+-tree keys: 'WindowsCaseSensitive.txt' and 'windowsCaseSensitive.txt'. Both present with separate entries.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (case sensitivity on disk). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DISK_RA_009.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 9.10

## Proof links
- `proofs/validation/MD_DISK_RA_009.csv` (matrix) — 
