# Dossier — FS_CHKP_004 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x58-0x5C: self-descriptor offset

**Canonical claim (reference_table.csv):** File System: 0x58-0x5C: self-descriptor offset

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP+0x58 (u32, table-descriptor end / self-descriptor offset) == 0xE0 (33 imgs, v3.14), 0xD0 (12, v3.4-3.10), 0xE8 (3, Insider). Matches documented version-keyed values exactly.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md CHKP 0x58 = self-descriptor offset. Non-zero on all checkpoints.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_CHKP_004.csv`
- corrected registry note: Self-descriptor offset used for root reference size calculation; confirmed at 0x5C

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_004.csv` (matrix) — 
