# Dossier — FS_OTBL_002 (STRUCTURAL)

**Claim (this audit tests):** Value: page ref + durable LSN + variable buffer. Row header 8xu32 at start; generation counter at u32[6] = checkpoint virtual clock

**Canonical claim (reference_table.csv):** File System: Value: page ref + durable LSN + variable buffer. Row header 8xu32 at start; generation counter at u32[6] = checkpoint virtual clock

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OT value header decoded on 34522/34522 rows across 113/113 ReFS images: value+0x00==0x2 (100%); u32[2] (value+0x08)==0x18 = key_offset (100%); u32[3] (value+0x0C)==0x30 = value_offset (100%); generation counter sits at u32[6] (value+0x18) and is a monotonic per-row epoch (0 for system OIDs 0x7-0x600, increasing for files). 4xQ LCN tuple at value+0x20 (build_object_map already reads these). The header-offset structure (page ref + record header + generation) is fully byte-confirmed.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** ENRICHED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- structure_reference.md Object Table: leaf value = page ref + durable LSN + buffer. Verified: user-object values resolve through the embedded page-ref to valid MSB+ object-root pages (build_object_map reads the ref at value+0x20).

## Raw-disk proof
- probe `otbl_value` ; validation matrix: `proofs/validation/FS_OTBL_002.csv`
- corrected registry note: Deep decode (FS_OTBL_RA_002): 8xu32 header (format=2, reserved, key_off=0x18, val_off=0x30, record_len, reserved, generation, dirty_gen) + LCN tuple (4xQ) + checksum. v3.10 compact format (80/88B) vs legacy (200/208B)

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/FS_OTBL_002.csv` (matrix) — 
