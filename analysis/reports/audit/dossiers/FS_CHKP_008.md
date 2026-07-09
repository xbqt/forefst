# Dossier — FS_CHKP_008 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x90-0x94: pointer count (13 global tables)

**Canonical claim (reference_table.csv):** File System: 0x90-0x94: pointer count (13 global tables)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP+0x90 (u32 pointer/root count) == 13 on 48/48 (both copies).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md CHKP 0x90 u32 pointer count (13 global tables). Byte-verified 13 on BOTH v3.4 and v3.14 (corpus validation will confirm version-invariance).

## Raw-disk proof
- probe `chkp_int` ; validation matrix: `proofs/validation/FS_CHKP_008.csv`
- corrected registry note: All images report exactly 13 global root tables from checkpoint; field at offset 0x90

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_008.csv` (matrix) — 
