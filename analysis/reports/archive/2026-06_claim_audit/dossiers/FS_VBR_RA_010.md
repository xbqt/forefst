# Dossier — FS_VBR_RA_010 (BEHAVIORAL)

**Claim (this audit tests):** VBR 0x58-0x1FF: 424-byte trailing area confirmed all-zero on 13 representative images spanning all ReFS versions (3.4-3.14) and configurations (4K/64K/128K clusters, CRC64, SHA256, dedup, insider). No hidden data. True reserved space.

**Canonical claim (reference_table.csv):** File System: VBR 0x58-0x1FF: 424-byte trailing area confirmed all-zero on 13 representative images spanning all ReFS versions (3.4-3.14) and configurations (4K/64K/128K clusters, CRC64, SHA256, dedup, insider). No hidden data. True reserved space.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — VBR[0x58:0x200] (424 bytes) all-zero on 113/113 ReFS images (not just the 13 cited in the claim) -- spans v3.4 through v3.14, 4K and 64K clusters, all configurations including the fixboot image.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [VBR] VBR 0x58-0x1FF: 424-byte trailing area confirmed all-zero on 13 representative images spanning all ReFS versio — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_VBR_RA_010.csv`
- corrected registry note: Verified on 13 images: win10refs2g win10refs64k win11refsmini win11refs4gattributes win11refs64k win10to11refsupgrade win11refsdedup win11refssha256 win1121h2test win1122h2test win1123h2test insiderefs8g winsider. See ra_step4_12_deep_structure_report.md

## Proof links
- `proofs/validation/FS_VBR_RA_010.csv` (matrix) — 
