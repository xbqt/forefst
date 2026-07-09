# Dossier — MD_DATA_RA_007 (BEHAVIORAL)

**Claim (this audit tests):** Integrity stream extents use variable-stride entries. Checksum page entries (flags=0x1c00d0): 32 bytes (24-byte entry + 8-byte CRC suffix) always run_len=1. Data run entries (flags=0x180040): standard 24 bytes variable run_len. Both types point to real file data. Table header format identical to normal extents.

**Canonical claim (reference_table.csv):** Metadata: Integrity stream extents use variable-stride entries. Checksum page entries (flags=0x1c00d0): 32 bytes (24-byte entry + 8-byte CRC suffix) always run_len=1. Data run entries (flags=0x180040): standard 24 bytes variable run_len. Both types point to real file data. Table header format identical to normal extents.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — 0x180040 standard run / 0x1c00d0 integrity run_len1 — extent flags

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Integrity stream extent tables use variable-stride entries (per the integrity-state table CT_INTS_001). Structural observation; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DATA_RA_007.csv`
- corrected registry note: Decoded and verified on 50 integrity sub-records across win11refs2g_setintegritystreams0/1.raw. All entries produce total_run matching needed clusters. refs_dataruns.py updated with variable-stride parser

## Proof links
- `proofs/validation/MD_DATA_RA_007.csv` (matrix) — 
