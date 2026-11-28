# Dossier — FS_VINF_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** Volume label (key 0x510) is raw UTF-16LE with no length header — first bytes are first character, null-terminated

**Canonical claim (reference_table.csv):** File System: Volume label (key 0x510) is raw UTF-16LE with no length header — first bytes are first character, null-terminated

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Key-0x510 value is raw UTF-16LE, no length prefix: first 2 bytes are the first character (low byte ASCII, high byte 0 for typical labels), null-terminated. Decoded cleanly on 113/113; empty label = zero-length value (winsider).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Volume Info] Volume label (key 0x510) is raw UTF-16LE with no length header — first bytes are first character, null-termina — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_VINF_RA_001.csv`
- corrected registry note: Initially misinterpreted as length-prefixed. Corrected in refs_volume_info.py Bug #3

## Proof links
- `proofs/validation/FS_VINF_RA_001.csv` (matrix) — 
