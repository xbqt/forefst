# Dossier — FS_SECD_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** OID 0x530 B+ tree key/value structure decoded. Key (16B): value_size(4)+padding(4)+SecurityId_high(4)+SD_hash(4). Value: hash_echo(4)+count_echo(4)+size_echo(4)+SECURITY_DESCRIPTOR_RELATIVE. SD is self-relative Windows format with Owner/Group SIDs and DACL/SACL.

**Canonical claim (reference_table.csv):** File System: OID 0x530 B+ tree key/value structure decoded. Key (16B): value_size(4)+padding(4)+SecurityId_high(4)+SD_hash(4). Value: hash_echo(4)+count_echo(4)+size_echo(4)+SECURITY_DESCRIPTOR_RELATIVE. SD is self-relative Windows format with Owner/Group SIDs and DACL/SACL.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SD key high=generation(=1)/low=hash; SecurityId=(hi<<32)|lo

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Security Descriptors] OID 0x530 B+ tree key/value structure decoded. Key (16B): value_size(4)+padding(4)+SecurityId_high(4)+SD_hash( — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SECD_RA_001.csv`
- corrected registry note: Parsed on win11refsmini.raw (12 SDs), win10refs2g.raw (8 SDs), win11refs4gattributes.raw (10 SDs). All SDs have revision=1 SE_SELF_RELATIVE. Tool: refs_security.py

## Proof links
- `proofs/validation/FS_SECD_RA_001.csv` (matrix) — 
