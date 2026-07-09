# Dossier — GN_PREF_002 (STRUCTURAL)

**Claim (this audit tests):** 0x22-0x23: checksum type (1=CRC32-C, 2=CRC64 [custom poly, NOT ECMA-182, #326])

**Canonical claim (reference_table.csv):** General: 0x22-0x23: checksum type (1=CRC32-C, 2=CRC64 [custom poly, NOT ECMA-182, #326])

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — self-checksum cktype 1=CRC32-C(4K)/2=CRC64(64K)/4=SHA256 recomputed

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** ENRICHED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md:1070 page-ref 0x22 = checksum type. Byte-verified: 2 (CRC64) with cklen 8, 4 (SHA-256) with cklen 32. Probe asserts cktype is a known enum AND cklen == map[cktype]. axis=checksum. NOTE: cktype 2 = CRC64 with the CUSTOM poly 0x9A6C9329AC4BC9B5 (ClMulCsCrc64), NOT ECMA-182 — proven by forefst.refs_crc64 matching every stored checksum, 0 mismatches (#326).

## Raw-disk proof
- probe `pref_field` ; validation matrix: `proofs/validation/GN_PREF_002.csv`
- corrected registry note: VBR 0x2A is the selector: 0=None, 2=CRC64, 4=SHA256. Reference size changes accordingly: 0x68/0x30/0x48

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/GN_PREF_002.csv` (matrix) — 
