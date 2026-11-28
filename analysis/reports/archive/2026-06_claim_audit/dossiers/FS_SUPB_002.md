# Dossier — FS_SUPB_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x50-0x60: volume GUID

**Canonical claim (reference_table.csv):** File System: 0x50-0x60: volume GUID

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SUPB+0x50..0x5F is a 16-byte Volume GUID, nonzero on 48/48. Page-header volume-signature at 0x0C == XOR of the four GUID dwords on 48/48 (corroborates that 0x50 is the GUID).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_supb__forefst.txt
- structure_reference.md:122 SUPB 0x50 = volume GUID (16B). Per-volume; verified non-zero (any byte set).

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_SUPB_002.csv`
- corrected registry note: Volume GUID extracted from SUPB+0x50; matches VBR GUID; preserved across version upgrade

## Proof links
- `proofs/static/parse_supb__forefst.txt` (static) — parse_supb
- `proofs/validation/FS_SUPB_002.csv` (matrix) — 
