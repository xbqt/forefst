# Dossier — MD_DATA_RA_010 (BEHAVIORAL)

**Claim (this audit tests):** $DATA (type 0x80) stream_flags at val+0x38 encodes the checksum type + integrity bit (not a plain resident/non-resident boolean). Stream summary header at val+0x00; resident inline content at val[0x3C].

**Canonical claim (reference_table.csv):** Metadata: $DATA (type 0x80) stream_flags at val+0x38 encodes the checksum type + integrity bit (not a plain resident/non-resident boolean). Stream summary header at val+0x00; resident inline content at val[0x3C].

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SI $DATA stream_flags@0x38 distribution across 367,356 v3.14+ SI $DATA records: 0x2 (367,178 = CRC), 0x4 (177 = SHA-256), 0x10002 (1 = CRC + integrity bit 0x10000). Encodes checksum-type (low byte) + integrity bit (0x10000), NOT a plain resident/non-resident boolean. Stream summary header at val+0x00; content at val+0x3C.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- E2/RD: $DATA stream summary flags at val+0x38. Detailed semantic; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DATA_RA_010.csv`
- corrected registry note: stream_flags at val+0x38 carries checksum-type + integrity bit; confirmed across resident $DATA sub-records.

## Proof links
- `proofs/validation/MD_DATA_RA_010.csv` (matrix) — 
