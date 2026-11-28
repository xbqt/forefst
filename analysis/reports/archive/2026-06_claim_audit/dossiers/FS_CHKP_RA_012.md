# Dossier — FS_CHKP_RA_012 (PURE-RD-LAYOUT)

**Claim (this audit tests):** CHKP 0x8C: 0x20 (32) OR 0x0 — NOT always 32. CORRECTED 2026-06-18: it co-varies with CHKP+0x88 (both populated=0x20 / both zero=0x0); zeroed on native-v3.14 checkpoints. So '+0x88/+0x8C' is a field-pair, not a static 'max root capacity = 32' constant (no E2 ties it to MS_CHECKPOINT_MAX_ROOTS as a literal).

**Canonical claim (reference_table.csv):** File System: CHKP 0x8C: 0x20 (32) OR 0x0 — NOT always 32. CORRECTED 2026-06-18: it co-varies with CHKP+0x88 (both populated=0x20 / both zero=0x0); zeroed on native-v3.14 checkpoints. So '+0x88/+0x8C' is a field-pair, not a static 'max root capacity = 32' constant (no E2 ties it to MS_CHECKPOINT_MAX_ROOTS as a literal).

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — CHKP+0x8C is 0x20 OR 0x0 (native-v3.14 zeroes), not always 32

**Original audit verdict:** CONTRADICTED (disk held 84/112 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- Tests the Prade claim CHKP+0x8C == 0x20. CONTESTED BY DESIGN: 0x20 on 82/110 but 0x0 on 28 (all 4K v3.14 native) — not a universal constant (finding #339).

## Raw-disk proof
- probe `chkp_int` ; validation matrix: `proofs/validation/FS_CHKP_RA_012.csv`
- corrected registry note: See structure_reference §A.4, finding #339; both-zero on native v3.14.

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_RA_012.csv` (matrix) — 
