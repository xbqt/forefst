# Dossier — MD_LK_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Symlinks stored as resident entries with attributes 0x420 (file) or 0x10000400 (directory). Target path stored twice in sub-record #3. Reparse data in sub-record #3.

**Canonical claim (reference_table.csv):** Metadata: Symlinks stored as resident entries with attributes 0x420 (file) or 0x10000400 (directory). Target path stored twice in sub-record #3. Reparse data in sub-record #3.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — Symlink resident-entry attributes (0x420 file / 0x10000400 dir) and 'target path stored twice in sub-record #3' need a per-reparse-entry sub-record dump across the symlink-bearing images (step5/testatomic) which my harness did not target. The reparse attribute bit and resident storage are observable, but the specific 0x420/0x10000400 attr values and double-path-in-subrec-3 need a dedicated reparse harness.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Symlink encoding (reparse 0x400 + archive 0x20). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_LK_RA_002.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 8.2

## Proof links
- `proofs/validation/MD_LK_RA_002.csv` (matrix) — 
