# Dossier — AP_LGFL_002 (BEHAVIORAL)

**Claim (this audit tests):** Log Record Header: 56 bytes, checksum

**Canonical claim (reference_table.csv):** Application: Log Record Header: 56 bytes, checksum

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Logfile] Log Record Header: 56 bytes, checksum — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/AP_LGFL_002.csv`
- corrected registry note: probe_logcore_record.py: entry+0x08 checksum varies per record (win11 0xfa2a568b/0x163223eb/0x1becc9a9) while page+0x04 magic is constant. Inner _SmsRedoRecord still >= 0x38. See finding #319.

## Proof links
- `proofs/validation/AP_LGFL_002.csv` (matrix) — 
