# Dossier — GN_PREF_003 (STRUCTURAL)

**Claim (this audit tests):** 0x24-0x26: checksum length

**Canonical claim (reference_table.csv):** General: 0x24-0x26: checksum length

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED**

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md:1070-1071 page-ref 0x24 = checksum length. Byte-verified cklen matches cktype (CRC64->8, SHA256->32). axis=checksum.

## Raw-disk proof
- probe `pref_field` ; validation matrix: `proofs/validation/GN_PREF_003.csv`
- corrected registry note: PT: CRC64 ref checksum length at 0x24 = 8 (verified on win11refsmini v3.14)

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/GN_PREF_003.csv` (matrix) — 
