# Dossier — FS_SCHM_001 (BEHAVIORAL)

**Claim (this audit tests):** Defines table schemas, key datatypes, flags, sizes

**Canonical claim (reference_table.csv):** File System: Defines table schemas, key datatypes, flags, sizes

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Schema Table (roots 3/9, table-IDs 0x01/0x06) read on 111/111 images. Each entry: key=u32 schema ID at +0x00 (key length 4B on all 111), value length=80B uniform on all 111. Self-describing one-entry-per-table-type confirmed.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Schema Table] Defines table schemas, key datatypes, flags, sizes — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SCHM_001.csv`
- corrected registry note: Schema table parsed on all images; 27 entries (3.4) / 29 entries (3.14)

## Proof links
- `proofs/validation/FS_SCHM_001.csv` (matrix) — 
