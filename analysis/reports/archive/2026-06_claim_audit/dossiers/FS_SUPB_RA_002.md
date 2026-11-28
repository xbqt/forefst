# Dossier — FS_SUPB_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** SUPB page has NO self-checksum (offset 0x08 always 0x00000000). SUPB is outside the Merkle-tree checksum chain — it is the root and has no parent to store its checksum. Silently repaired by driver on v3.14 mount.

**Canonical claim (reference_table.csv):** File System: SUPB page has NO self-checksum (offset 0x08 always 0x00000000). SUPB is outside the Merkle-tree checksum chain — it is the root and has no parent to store its checksum. Silently repaired by driver on v3.14 mount.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SUPB+0x08 (page-header self-checksum slot) == 0x00000000 on 48/48.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_supb__forefst.txt
- SUPB page header 0x08 is always 0x00000000 (no self-checksum in the page header). Byte-verified.

## Raw-disk proof
- probe `supb_int` ; validation matrix: `proofs/validation/FS_SUPB_RA_002.csv`
- corrected registry note: Verified on win11refsmini_beforecorruption.raw and post-mount image: SUPB offset 0x08 = 0 in both. See ra_step4_15_corrupted_metadata_report.md

## Proof links
- `proofs/static/parse_supb__forefst.txt` (static) — parse_supb
- `proofs/validation/FS_SUPB_RA_002.csv` (matrix) — 
