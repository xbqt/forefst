# Dossier — FS_CHKP_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x54-0x56: major ReFS version

**Canonical claim (reference_table.csv):** File System: 0x54-0x56: major ReFS version

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP+0x54 (u16 major) == 3 on 48/48 (across both copies).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md CHKP body: 0x54 u16 major version. Major is 3 for all ReFS (minor at 0x56 varies: 4,7,9,10,14). Read from the newest CHKP page. Byte-verified 3 on v3.4+v3.14.

## Raw-disk proof
- probe `chkp_int` ; validation matrix: `proofs/validation/FS_CHKP_002.csv`
- corrected registry note: Major version matches VBR: 3 in all images

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_002.csv` (matrix) — 
