# Dossier — FS_CHKP_RA_002 (STRUCTURAL)

**Claim (this audit tests):** CHKP root reference sizes: 0x68(3.4), 0x30(3.14/CRC64), 0x48(3.14/SHA256)

**Canonical claim (reference_table.csv):** File System: CHKP root reference sizes: 0x68(3.4), 0x30(3.14/CRC64), 0x48(3.14/SHA256)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP+0x5C page-ref size: 0x68 on all v3.4/3.7/3.9 (10 imgs), 0x30 on v3.14 CRC32-C/CRC64 (32 imgs incl 64K-CRC64), 0x48 on v3.14 SHA-256 (4 imgs), 0x30 on v3.10 (1). Matches 0x68(3.4)/0x30(3.14-CRC64)/0x48(SHA256).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md:128 self-descriptor length varies by version+checksum: 0x68 v3.4, 0x30 v3.14 CRC64, 0x48 SHA-256. parse_chkp reads desc_len at 0x5C. Byte-verified 0x30/0x68/0x48.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_CHKP_RA_002.csv`
- corrected registry note: Reference size determined by version+checksum combination. 3.14 uses compacted references

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_RA_002.csv` (matrix) — 
