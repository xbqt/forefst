# Dossier — FS_CHKP_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x56-0x58: minor ReFS version

**Canonical claim (reference_table.csv):** File System: 0x56-0x58: minor ReFS version

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP+0x56 (u16 minor) observed values 14(36 imgs),4(9),7(1),9(1),10(1) — every value in the documented {4,7,9,10,14} set, none outside.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 109/109 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md CHKP 0x56 = minor version. Verified == VBR 0x29 across versions (same cross-structure probe as FS_VBR_009).

## Raw-disk proof
- probe `version_consistency` ; validation matrix: `proofs/validation/FS_CHKP_003.csv`
- corrected registry note: Minor version matches VBR: 4(Win10) or 14(Win11)

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_003.csv` (matrix) — 
