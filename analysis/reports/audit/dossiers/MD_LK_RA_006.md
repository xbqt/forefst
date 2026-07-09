# Dossier — MD_LK_RA_006 (ABSENCE)

**Claim (this audit tests):** $OBJ_LINK version evolution: type 0x38 (v3.4, no instance markers) → type 0x39 (v3.7+, with 0x80000002 MI marker). Upgraded volumes retain v3.4 format for existing entries. Version check at VCB+0x2ACC.

**Canonical claim (reference_table.csv):** Metadata: $OBJ_LINK version evolution: type 0x38 (v3.4, no instance markers) → type 0x39 (v3.7+, with 0x80000002 MI marker). Upgraded volumes retain v3.4 format for existing entries. Version check at VCB+0x2ACC.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Version evolution confirmed: 13 native v3.4 images carry ONLY type 0x38; 100 v3.7+ images carry ONLY type 0x39 (0/113 mix anomalies). The upgrade image win10to11refs4g.raw (reports v3.14, retains v3.4 format) has 0x38 entries (A=32 no-marker + B=8 with 0x80000001 SI-marker) and ZERO 0x39 entries, confirming 'upgraded volumes retain v3.4 format.'

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ObjLink version change. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_LK_RA_006.csv`
- corrected registry note: win10to11refs4g.raw (v3.4→v3.14 upgrade): 39 OIDs all retain type 0x38 despite v3.14 version number.

## Proof links
- `proofs/validation/MD_LK_RA_006.csv` (matrix) — 
