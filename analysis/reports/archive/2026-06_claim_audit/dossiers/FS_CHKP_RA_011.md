# Dossier — FS_CHKP_RA_011 (BEHAVIORAL)

**Claim (this audit tests):** CHKP 0x7C-0x87: 12-byte reserved field. Prade Table 4.7 labeled these as 'Offset to table references' (0x7C) 'Table reference count' (0x80) and 'Offset to unknown buffer' (0x84). All three are always zero on all 66 images tested (Prade correction).

**Canonical claim (reference_table.csv):** File System: CHKP 0x7C-0x87: 12-byte reserved field. Prade Table 4.7 labeled these as 'Offset to table references' (0x7C) 'Table reference count' (0x80) and 'Offset to unknown buffer' (0x84). All three are always zero on all 66 images tested (Prade correction).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP+0x7C..0x87 (12 bytes) == all-zero on 48/48 (both copies).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/ValidateCheckpointRecord__decomp.txt
- ValidateCheckpointRecord does not read CHKP+0x7C..0x87 — confirms the field is reserved (Prade Table 4.7 label). Proof is the decompiled validator.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_CHKP_RA_011.csv`
- corrected registry note: Verified zero on 13 representative + previously confirmed on 48 images (Step 4.5). See ra_step4_12_deep_structure_report.md

## Proof links
- `proofs/static/ValidateCheckpointRecord__decomp.txt` (static) — ValidateCheckpointRecord
- `proofs/validation/FS_CHKP_RA_011.csv` (matrix) — 
