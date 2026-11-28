# Dossier — CT_INTS_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Row format decoded: Key=16B [u64 start_lcn, u64 block_count], Value=24B [u64 start_lcn(dup), u64 block_count(dup), u32 state_field, u32 config_field]. Rows cover contiguous LCN ranges spanning entire volume. Most images: 1 row with default [0x0002ffff, 0x00000100]. Large Win10: 3 rows — 1 container has modified state [0x00013f6c, 0x00000118]. Linked to Container Table extended area (per-container checksum buffer). CmsIntegrityState class win10=17, win11=12, insider=13 (contraction, not growth)

**Canonical claim (reference_table.csv):** Content: Row format decoded: Key=16B [u64 start_lcn, u64 block_count], Value=24B [u64 start_lcn(dup), u64 block_count(dup), u32 state_field, u32 config_field]. Rows cover contiguous LCN ranges spanning entire volume. Most images: 1 row with default [0x0002ffff, 0x00000100]. Large Win10: 3 rows — 1 container has modified state [0x00013f6c, 0x00000118]. Linked to Container Table extended area (per-container checksum buffer). CmsIntegrityState class win10=17, win11=12, insider=13 (contraction, not growth)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED**

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (win10)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- structure_reference.md:212 root 11 = Integrity State (table 0x0F). Byte-verified first key = [start_lcn=0, block_count=0x7c000=total clusters]. Probe asserts 16B keys with non-zero block_count.

## Raw-disk proof
- probe `ints_row` ; validation matrix: `proofs/validation/CT_INTS_001.csv`
- corrected registry note: IST (root #11) present on ALL 89 images. Row format invariant: Key=16B, Value=24B. 87/89: single row covering entire volume. 2/89: 3 rows with 1 container having modified integrity state

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/CT_INTS_001.csv` (matrix) — 
