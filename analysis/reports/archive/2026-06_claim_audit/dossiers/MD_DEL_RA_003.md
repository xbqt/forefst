# Dossier — MD_DEL_RA_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** PowerShell Remove-Item permanently deletes files (USN reason 0x80000200) bypassing $RECYCLE.BIN entirely.

**Canonical claim (reference_table.csv):** Metadata: PowerShell Remove-Item permanently deletes files (USN reason 0x80000200) bypassing $RECYCLE.BIN entirely.

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — PowerShell Remove-Item 'permanent delete bypassing $RECYCLE.BIN' and the USN reason code 0x80000200 are USN-journal behavioral facts, not on-disk byte-layout. Not measurable from static directory-tree bytes. Disk shows files simply absent from the directory tree (no $RECYCLE.BIN $R/$I pair).

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (deletion). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DEL_RA_003.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 5.3 | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NEW): USN-reason and deletion-path are behavioral; no byte-layout signal to confirm/contradict here.

## Proof links
- `proofs/validation/MD_DEL_RA_003.csv` (matrix) — 
