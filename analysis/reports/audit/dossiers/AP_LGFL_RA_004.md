# Dossier — AP_LGFL_RA_004 (BEHAVIORAL)

**Claim (this audit tests):** MLog data pages = LogCore records with a 0x78 (120)-byte header [sig@0x00 + magic@0x04 (constant-per-volume NOT a CRC; see E42) + version@0x08 + log_block_size@0x0C + UUID@0x10 + counter@0x20 + LSN@0x28 + prevLSN@0x30 + length-in-4K-blocks@0x38/0x3C + entry_offset@0x54=0x78]. CORRECTED from "56-byte (CRC...)"

**Canonical claim (reference_table.csv):** Application: MLog data pages = LogCore records with a 0x78 (120)-byte header [sig@0x00 + magic@0x04 (constant-per-volume NOT a CRC; see E42) + version@0x08 + log_block_size@0x0C + UUID@0x10 + counter@0x20 + LSN@0x28 + prevLSN@0x30 + length-in-4K-blocks@0x38/0x3C + entry_offset@0x54=0x78]. CORRECTED from "56-byte (CRC...)"

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile] MLog data pages = LogCore records with a 0x78 (120)-byte header [sig@0x00 + magic@0x04 (constant-per-volume NO — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_RA_004.csv`
- corrected registry note: probe_logcore_record.py RD-verified on 10 images (v3.4/3.7/3.14/upgraded/compression/262K/Insider-4K+64K). 0x04 constant per volume (win11 0x84c1ffcf; win10 0x998da6fd); entry+0x08 checksum varies per record; LSN chains prevLSN[n]==LSN[n-1] pre-wrap

## Proof links
- `proofs/validation/AP_LGFL_RA_004.csv` (matrix) — 
