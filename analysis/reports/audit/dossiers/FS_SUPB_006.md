# Dossier — FS_SUPB_006 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x78-0x7C: self-descriptor offset/length

**Canonical claim (reference_table.csv):** File System: 0x78-0x7C: self-descriptor offset/length

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SUPB+0x78 self-descriptor OFFSET == 0xD0 on 48/48; SUPB+0x7C LENGTH = 0x30 (32 imgs, v3.14 CRC-class), 0x68 (12 imgs, v3.4), 0x48 (4 imgs, SHA-256). Self-descriptor at 0xD0 has dataoff byte +0x23==0x08 on 48/48.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_supb__forefst.txt
- structure_reference.md:127 SUPB 0x78 = self-descriptor offset. Non-zero on all volumes.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_SUPB_006.csv`
- corrected registry note: Offset=0xD0 length=0x30 (48 bytes for CRC64 mode). Contains self-referencing page reference to LCN 0x1E

## Proof links
- `proofs/static/parse_supb__forefst.txt` (static) — parse_supb
- `proofs/validation/FS_SUPB_006.csv` (matrix) — 
