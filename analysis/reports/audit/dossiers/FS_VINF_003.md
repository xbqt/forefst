# Dossier — FS_VINF_003 (STRUCTURAL)

**Claim (this audit tests):** Backup block row (key 0x540)

**Canonical claim (reference_table.csv):** File System: Backup block row (key 0x540)

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — OID 0x500 key 0x540 (keylen=8, vallen=16) decodes as schema_count u32@+0x00 = 0x23 (35) + flags u32@+0x08 = 1 on 113/113. val_hex=23000000 00000000 01000000 00000000. This is the schema-count/flags row, NOT a 'backup block'.

**Original audit verdict:** CONTRADICTED (disk held 112/112 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- structure_reference.md F.4b OID 0x500 key 0x0540 = backup block. Byte-verified present (vlen 16) on v3.4+v3.14.

## Raw-disk proof
- probe `vinf_row` ; validation matrix: `proofs/validation/FS_VINF_003.csv`
- corrected registry note: OID 0x540 present in Object Table of all images | RE-VERIFIED 2026-06-18 (all-disk): claimed 'Backup block row (key 0x540)'; disk shows key 0x540 in OID 0x500 = schema count (35) + flags, exactly as structure_reference §F.4b labels it. There is no 'backup block' here. The audit description mislabels this row.

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/FS_VINF_003.csv` (matrix) — 
