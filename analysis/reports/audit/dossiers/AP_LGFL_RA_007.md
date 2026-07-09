# Dossier — AP_LGFL_RA_007 (BEHAVIORAL)

**Claim (this audit tests):** MLog FOUR-layer model (resolves B2b): each data page = a LogCore data record. L1 = 0x78 (120)-byte record header (sig@0x00 + per-volume-magic@0x04 NOT-CRC + ver=1@0x08 + log-block-size-0x1000@0x0C + UUID@0x10 + counter@0x20 + LSN@0x28 + prevLSN@0x30 + length-in-4K-blocks@0x38/0x3C + entry-offset@0x54=0x78). L2 = entry header @record+0x78 (LSN@+0x00 + checksum@+0x08 + payload-len@+0x20 + payload-offset@+0x28 + type@+0x30=2-data/1-control). L3 = redo block _SmsRedoHeader @record+0xB0. L4 = _SmsRedoRecord entries.

**Canonical claim (reference_table.csv):** Application: MLog FOUR-layer model (resolves B2b): each data page = a LogCore data record. L1 = 0x78 (120)-byte record header (sig@0x00 + per-volume-magic@0x04 NOT-CRC + ver=1@0x08 + log-block-size-0x1000@0x0C + UUID@0x10 + counter@0x20 + LSN@0x28 + prevLSN@0x30 + length-in-4K-blocks@0x38/0x3C + entry-offset@0x54=0x78). L2 = entry header @record+0x78 (LSN@+0x00 + checksum@+0x08 + payload-len@+0x20 + payload-offset@+0x28 + type@+0x30=2-data/1-control). L3 = redo block _SmsRedoHeader @record+0xB0. L4 = _SmsRedoRecord entries.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile] MLog FOUR-layer model (resolves B2b): each data page = a LogCore data record. L1 = 0x78 (120)-byte record head — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_RA_007.csv`
- corrected registry note: probe_logcore_record.py PASS on 10 images (v3.4/3.7/3.14/upgraded/compression/262K-record/Insider-4K+64K). 0x0C stays 0x1000 on a 64K-cluster volume (proves log-block-size != cluster-size). LSN chains prevLSN[n]==LSN[n-1] pre circular-buffer-wrap.

## Proof links
- `proofs/validation/AP_LGFL_RA_007.csv` (matrix) — 
