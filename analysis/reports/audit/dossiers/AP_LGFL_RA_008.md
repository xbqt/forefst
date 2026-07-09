# Dossier — AP_LGFL_RA_008 (BEHAVIORAL)

**Claim (this audit tests):** MLog control-page field at page+0x04 is a per-volume constant magic, NOT a CRC. Confirmed by reformat differential on the same partition: win11refs2gtargeted +0x04 = 0x6d790647; its reformatted copy = 0x5e524606, while ~90% of the control-page bytes are identical (the volume serial/GUID also changed) — a content CRC would match across the identical bytes, a per-volume constant differs. Corroborates E42/#329/#325b.

**Canonical claim (reference_table.csv):** Application: MLog control-page field at page+0x04 is a per-volume constant magic, NOT a CRC. Confirmed by reformat differential on the same partition: win11refs2gtargeted +0x04 = 0x6d790647; its reformatted copy = 0x5e524606, while ~90% of the control-page bytes are identical (the volume serial/GUID also changed) — a content CRC would match across the identical bytes, a per-volume constant differs. Corroborates E42/#329/#325b.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/LogValidateEntryHeader__decomp.txt
- E2+RD. RD: win11refs2gtargeted +0x04 = 0x6d790647 vs reformated 0x5e524606 while ~90% of control-page bytes identical and volume serial/GUID changed; all 195 records share +0x04 while page+0x80 XOR-fold has 193 distinct values -> stored constant, not a CRC. Static (win11_4b0558f6): LogCoreWriteDataRecord copies handle+0x2fe8; LogValidateEntryHeader equality-checks; real per-record checksum is the separate LogVerifyChecksumEntryHeader. Corroborates AP_LGFL_RA_004/E42. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_RA_008.csv`
- corrected registry note: win11refs2gtargeted.raw vs _reformated.raw control pages @0x9000000: +0x04 = 0x6d790647 vs 0x5e524606; all 195 MLog records share the same +0x04 while page+0x80 XOR-fold takes 193 distinct values -> +0x04 is a stored per-volume constant, not a CRC. (Per-volume value; earlier docs quoted 0x6d6c6f07/0x5e534d06 from a pre-regeneration image.)

## Proof links
- `proofs/static/LogValidateEntryHeader__decomp.txt` (static) — LogValidateEntryHeader
- `proofs/validation/AP_LGFL_RA_008.csv` (matrix) — 
