# Dossier — FS_OTBL_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** Object Table row value header decoded: 8xu32 (format=2, reserved, key_off=0x18, val_off=0x30, record_len, reserved, generation, dirty_gen) + LCN tuple (4xQ) + checksum. v3.10 introduced compact format (80/88 bytes) replacing legacy (200/208 bytes). Upgraded volumes have mixed record sizes.

**Canonical claim (reference_table.csv):** File System: Object Table row value header decoded: 8xu32 (format=2, reserved, key_off=0x18, val_off=0x30, record_len, reserved, generation, dirty_gen) + LCN tuple (4xQ) + checksum. v3.10 introduced compact format (80/88 bytes) replacing legacy (200/208 bytes). Upgraded volumes have mixed record sizes.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Full OT value header confirmed on 113/113 images: u32 slots from value+0x00 = [0]=0x2(format/schema-ref), [1]=0 reserved, [2]=0x18 key_offset, [3]=0x30 value_offset, [4]=record_len (0xc8 for 240/248B v3.4 rows, 0x50 for 80/88B v3.14 rows), [5]=0x8 (file) / 0x0 (system), [6]=generation, [7]=dirty_gen (1-2 on files, 0 on system). Then 4xQ LCN tuple at +0x20. All offsets hold on every row of every applicable image.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsObjectTable::GetObjectRecordOfIdentifier. Object Table row value header decoded: 8xu32 (format=2, reserved, key_off=0x18, val_off=0x30, record_len, rese. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_RA_002.csv`
- corrected registry note: Decoded via refs_object_table.py -vv across 5 version-specific images. record_len field at u32[4] encodes the exact value size (0xC8/0xD0 for legacy, 0x50/0x58 for compact). Generation counter at u32[6] tracks checkpoint virtual clock.

## Proof links
- `proofs/validation/FS_OTBL_RA_002.csv` (matrix) — 
