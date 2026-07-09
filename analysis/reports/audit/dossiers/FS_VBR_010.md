# Dossier — FS_VBR_010 (STRUCTURAL)

**Claim (this audit tests):** 0x38-0x40: volume serial number

**Canonical claim (reference_table.csv):** File System: 0x38-0x40: volume serial number

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — le64(VBR,0x38) volume serial !=0 on 112/113. The single zero is win11refs2tmillionsofactions_aftersalvage_fixboottest.raw (a refsutil-fixboot image, which by design zeroes the serial -- see FS_VBR_RA_005).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 111/111 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:30 VBR 0x38 = volume serial. Per-image; verified non-zero on every intact VBR (fixboot zeroes it — scoped).

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_VBR_010.csv`
- corrected registry note: Unique GUID per volume; preserved across upgrade (win10to11refs4g)

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_010.csv` (matrix) — 
