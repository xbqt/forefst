# Dossier — FS_CHKP_007 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x70-0x78: oldest log record reference (compound u64: byte offset + segment number)

**Canonical claim (reference_table.csv):** File System: 0x70-0x78: oldest log record reference (compound u64: byte offset + segment number)

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — CHKP+0x70..0x77 present on 48/48 (compound u64). The compound decomposition (low32=log offset, high32=segment) is not directly disk-verifiable without log cross-reference.

**Original audit verdict:** INFERRED (disk held 112/112 at audit time) · **Registry status:** INFERRED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md:168 CHKP 0x70 = oldest log record ref (low32 offset, high32 segment). Byte-verified non-zero (0x100000092 / 0x100000039). Per-volume value.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_CHKP_007.csv`
- corrected registry note: Compound u64: low 32 bits = log area byte offset, high 32 bits = log segment number. Both CHKPs always identical. Values range from 0x39 (minimal) to 0x138C8 (heavy usage). See ra_step4_12_deep_structure_report.md | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): LOW. Offset/size disk-confirmed; the 'oldest log record reference' compound-field semantic is E2/structural, not byte-checkable here.

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_007.csv` (matrix) — 
