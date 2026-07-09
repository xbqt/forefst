# Dossier — CT_ALLC_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Deep allocator row structure: key=[range_start,range_length]. Two value formats: bitmap (24B header + 2048B bitmap; 1=allocated 0=free; free_count=range_len-bits_set; field_22=used_count) and compact (24B; flags=0x2 for fully allocated). Three-tier: Small (real LCN root #12), Medium (virtual root #1), Container (virtual root #2)

**Canonical claim (reference_table.csv):** Content: Deep allocator row structure: key=[range_start,range_length]. Two value formats: bitmap (24B header + 2048B bitmap; 1=allocated 0=free; free_count=range_len-bits_set; field_22=used_count) and compact (24B; flags=0x2 for fully allocated). Three-tier: Small (real LCN root #12), Medium (virtual root #1), Container (virtual root #2)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Bitmap row=2072B with key=[range_start@0x00,range_length@0x08], free_count@0x10, flags@0x12, header_size@0x14, used_count@0x16, bitmap@0x18. Invariant free_count==range_length-popcount(bitmap) on 5172/5172 clean bitmap rows across all images. Compact rows=24B (1172 seen), flag 0x2=fully-allocated. Tiers: Medium=root#1(virtual), Container=root#2(virtual), Small=root#12(real LCN).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Medium Allocator (checkpoint root 1) rows have 16-byte keys [range_start, range_length]. Byte-verified (e.g. [0, 0x4000]).

## Raw-disk proof
- probe `root_row` ; validation matrix: `proofs/validation/CT_ALLC_RA_001.csv`
- corrected registry note: See report_container_and_allocator_tables.md

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/CT_ALLC_RA_001.csv` (matrix) — 
