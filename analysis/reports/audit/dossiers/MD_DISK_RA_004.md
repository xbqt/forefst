# Dossier — MD_DISK_RA_004 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Stream count semantics: 1=normal file, 2=sparse or link, 3=EFS encrypted, 4-6=files with stream snapshots.

**Canonical claim (reference_table.csv):** Metadata: Stream count semantics: 1=normal file, 2=sparse or link, 3=EFS encrypted, 4-6=files with stream snapshots.

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — stream_count@+0x20 distribution on win11refs4gattributestest2: {1:23, 2:1147, 3:98, 4:18, 5:5, 6:2, 8:3, 10:1, 14:1}. sc=2 is the DOMINANT value for ordinary files (attrs=0x20). Normal files appear at sc=1 AND sc=2; sparse bigsparse.dat (attrs=0x220) had sc=2 (same as normals); .lnk files reached sc=8/10/14.

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Stream count interpretation. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DISK_RA_004.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 9.5 | RE-VERIFIED 2026-06-18 (all-disk): claimed '1=normal, 2=sparse or link, 3=EFS, 4-6=stream snapshots'; disk shows stream_count is a COUNT of embedded streams/snapshot-versions, not a file-type tag. sc=2 is the common case for plain files, not 'sparse or link'. The fixed seman

## Proof links
- `proofs/validation/MD_DISK_RA_004.csv` (matrix) — 
