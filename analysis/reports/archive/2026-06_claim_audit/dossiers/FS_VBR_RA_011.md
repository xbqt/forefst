# Dossier — FS_VBR_RA_011 (BEHAVIORAL)

**Claim (this audit tests):** VBR format-time fields (0x2A checksum algo, 0x2C volume flags, 0x48 format GUID) are NEVER modified during version upgrade. Upgraded volumes retain original VBR values while CHKP shows new version.

**Canonical claim (reference_table.csv):** File System: VBR format-time fields (0x2A checksum algo, 0x2C volume flags, 0x48 format GUID) are NEVER modified during version upgrade. Upgraded volumes retain original VBR values while CHKP shows new version.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Upgraded volumes retain original VBR format-time fields: win10to11refs4g.raw (v3.14, upgraded from v3.4) keeps 0x2A=0x00, flags=0x06, GUID=zero (the v3.4 values, NOT the native v3.14 0x02/0x66/populated). win1122h2test_afteropenedwithinsider.raw (v3.14, upgraded from v3.9) keeps flags=0x26 + 0x2A=0x00 + zero GUID. All 4 zero-GUID v3.14 images are upgraded volumes.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Bootstrap Chain] VBR format-time fields (0x2A checksum algo, 0x2C volume flags, 0x48 format GUID) are NEVER modified during ver — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_VBR_RA_011.csv`
- corrected registry note: Upgraded image: VBR 0x2A=0x0000/0x2C=0x06/0x48=not set but CHKP version=3.14 flags=0x602. Verified on win10to11refs4g_afterwin11mount.raw

## Proof links
- `proofs/validation/FS_VBR_RA_011.csv` (matrix) — 
