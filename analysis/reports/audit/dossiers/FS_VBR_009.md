# Dossier — FS_VBR_009 (STRUCTURAL)

**Claim (this audit tests):** 0x28-0x2A: major/minor ReFS version

**Canonical claim (reference_table.csv):** File System: 0x28-0x2A: major/minor ReFS version

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — VBR 0x28-0x29 packed (major.minor) == manifest version on 113/113 (0 mismatches). Packed values: 3.4=0x0304, 3.7=0x0307, 3.9=0x0309, 3.10=0x030A, 3.14=0x030E, plus test-edited 3.15/6.66.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 109/109 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:24 VBR 0x28 = version. Verified cross-structure: VBR byte 0x28(major)/0x29(minor) == CHKP 0x54/0x56. Byte-verified v3.4 (3.4) + v3.14 (3.14).

## Raw-disk proof
- probe `version_consistency` ; validation matrix: `proofs/validation/FS_VBR_009.csv`
- corrected registry note: 3.4 on all Win10 images; 3.14 on all Win11 and upgraded images

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_009.csv` (matrix) — 
