# Dossier — MD_DATA_RA_004 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Type 0x40 key is 24 bytes: attr_type(2)=0x0040 + key_flags(2) + reserved(4) + stream_index(8) + parent_oid(8)

**Canonical claim (reference_table.csv):** Metadata: Type 0x40 key is 24 bytes: attr_type(2)=0x0040 + key_flags(2) + reserved(4) + stream_index(8) + parent_oid(8)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — type-0x40 file-extent key is 24 bytes on 41,018/41,018 keys across 53 images: attr_type(2)@0x00==0x0040 (100%), key_flags(2)@0x02==0x8000, reserved(4)@0x04, stream_index(8)@0x08, parent_oid(8)@0x10. Example: 4000 0080 00000000 0300000000000000 0207000000000000 in OID 0x702 -> stream_index=3, parent_oid=0x702.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 53/53 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Byte-verified: all type 0x40 keys are 24 bytes (key[0:2]=0x40). N/A on resident-only volumes.

## Raw-disk proof
- probe `row0x40` ; validation matrix: `proofs/validation/MD_DATA_RA_004.csv`
- corrected registry note: parent_oid = the directory OID containing the extent data. stream_index links type 0x30 to type 0x40

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/MD_DATA_RA_004.csv` (matrix) — 
