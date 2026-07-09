# Dossier — CT_CTBL_RA_006 (STRUCTURAL)

**Claim (this audit tests):** Deep container row structure: 160-byte (4K/CRC64) with 13 decoded fields. 224-byte (64K or SHA256) with 128-byte extended area. Universal parsing: CPC at +0x18, CSC at value[len-16:len-8]. Container flags bitmask decoded. Extended area (0x50+) = per-container integrity checksum buffer managed by CmsIntegrityState. Size = num_slots x 16: 4 slots (64B) for CRC64, 8 slots (128B) for SHA256. E2: GetNumAllocatedForContainerEntry + PersistContainerCacheWorker confirm via field_18c. E1: zero on 80+ images except 1 container on win10refs2tspecials. Ref: report_container_and_allocator_tables.md §1.3.1

**Canonical claim (reference_table.csv):** Content: Deep container row structure: 160-byte (4K/CRC64) with 13 decoded fields. 224-byte (64K or SHA256) with 128-byte extended area. Universal parsing: CPC at +0x18, CSC at value[len-16:len-8]. Container flags bitmask decoded. Extended area (0x50+) = per-container integrity checksum buffer managed by CmsIntegrityState. Size = num_slots x 16: 4 slots (64B) for CRC64, 8 slots (128B) for SHA256. E2: GetNumAllocatedForContainerEntry + PersistContainerCacheWorker confirm via field_18c. E1: zero on 80+ images except 1 container on win10refs2tspecials. Ref: report_container_and_allocator_tables.md §1.3.1

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Universal parsing: CPC@value+0x18 on 796688/796688; physical start at value[len-16] (0x90 for 160B, 0xD0 for 224B) on 796688/796688. 160B=4K/CRC64 (13 fields); 224B=64K-or-SHA256 with 128B (vs 64B) integrity buffer at 0x50+. E2: GetNumAllocatedForContainerEntry + PersistContainerCacheWorker present in win11/insider decomp.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (win10)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/_parse_ct_page__forefst.txt
- structure_reference.md B.1: 160-byte row (4K/CRC64) vs 224-byte (64K or SHA-256). Byte-verified: 4K CRC64 rows = 160B (phys start @0x90), 64K rows = 224B (phys start @0xD0). Probe expects 160 iff (cs==4096 and cksel in {none,crc32,crc64}) else 224.

## Raw-disk proof
- probe `ct_row` ; validation matrix: `proofs/validation/CT_CTBL_RA_006.csv`
- corrected registry note: Extended area decoded as integrity checksum buffer (2026-05-23)

## Proof links
- `proofs/static/_parse_ct_page__forefst.txt` (static) — _parse_ct_page
- `proofs/validation/CT_CTBL_RA_006.csv` (matrix) — 
