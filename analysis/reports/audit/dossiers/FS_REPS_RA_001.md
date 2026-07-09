# Dossier — FS_REPS_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** Reparse Index (OID 0x540/0x541 schema 0x160) key structure decoded (24 bytes): key_type(2 always 0x0001)+key_flags(2 0x8000)+ReparseTag(4)+ParentOID(8)+FileOID(8). Value: minimal/empty (pure index). Enables fast enumeration of all reparse points by tag.

**Canonical claim (reference_table.csv):** File System: Reparse Index (OID 0x540/0x541 schema 0x160) key structure decoded (24 bytes): key_type(2 always 0x0001)+key_flags(2 0x8000)+ReparseTag(4)+ParentOID(8)+FileOID(8). Value: minimal/empty (pure index). Enables fast enumeration of all reparse points by tag.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Reparse Points] Reparse Index (OID 0x540/0x541 schema 0x160) key structure decoded (24 bytes): key_type(2 always 0x0001)+key_f — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_REPS_RA_001.csv`
- corrected registry note: Parsed on win11refs4gattributes.raw: 162 entries (161 SYMLINK + 1 AF_UNIX). win10refs2g.raw: 3 SYMLINK. Key structure consistent across versions. Tool: refs_reparse.py

## Proof links
- `proofs/validation/FS_REPS_RA_001.csv` (matrix) — 
