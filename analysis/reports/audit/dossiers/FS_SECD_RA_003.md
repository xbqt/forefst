# Dossier — FS_SECD_RA_003 (BEHAVIORAL)

**Claim (this audit tests):** Schema 0x160 naming correction: 0x160 is used by Reparse Point Index (OIDs 0x540/0x541) via InitializeReparseIndexTable not by Security Descriptors (OID 0x530). OID 0x530 uses stream-type table without schema. Schema name 'Security Descriptor' is misleading.

**Canonical claim (reference_table.csv):** File System: Schema 0x160 naming correction: 0x160 is used by Reparse Point Index (OIDs 0x540/0x541) via InitializeReparseIndexTable not by Security Descriptors (OID 0x530). OID 0x530 uses stream-type table without schema. Schema name 'Security Descriptor' is misleading.

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Naming/static claim (schema 0x160 = Reparse Index for OIDs 0x540/0x541, not Security Descriptors OID 0x530). Disk-consistent: OID 0x530 has NO schema attached (stream-type) while OID 0x540 uses schema 0x160 per structure_reference §F.4/F.4c. No counter-evidence on disk.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Security Descriptors] Schema 0x160 naming correction: 0x160 is used by Reparse Point Index (OIDs 0x540/0x541) via InitializeReparseI — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SECD_RA_003.csv`
- corrected registry note: OID 0x540 B+ tree confirmed using schema 0x160 key structure (24-byte keys). OID 0x530 B+ tree uses different key structure (16-byte keys with hash-based lookup) | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Pure schema-naming correction; verified against structure_reference (0x530 schema='—', 0x540 schema=0x160). The InitializeReparseIndexTable attribution is E2/static — not byte-checkable. Confirmed consistent, label not independent

## Proof links
- `proofs/validation/FS_SECD_RA_003.csv` (matrix) — 
