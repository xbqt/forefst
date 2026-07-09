# Dossier — MD_DATA_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** Non-resident extent entry is 24 bytes: VLCN(4) + VLCN_hi(4) + flags(4) + file_VCN(4) + pad(4) + run_length(4)

**Canonical claim (reference_table.csv):** Metadata: Non-resident extent entry is 24 bytes: VLCN(4) + VLCN_hi(4) + flags(4) + file_VCN(4) + pad(4) + run_length(4)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — 24-byte extent entry: VLCN(8)@0x00 + flags(4)@0x08 + file_VCN(4)@0x0C + pad(4)@0x10 + run_length(4)@0x14. pad@0x10 == 0 on 76,476/76,476 v3.14 extent entries across 47 images. Decodes correctly on win11refs4gattributes (8 extents, VCN strictly increasing). alloc@0x60 == roundup(file_size@0x58) on 4,656/4,656 files with extents.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Internal extent-run entry layout within the 0x40 value. Cited (key size disk-proven in MD_DATA_RA_004).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DATA_RA_001.csv`
- corrected registry note: Confirmed by extraction verification: extent clusters sum matches alloc_size/cluster_size. Tested on 48 images

## Proof links
- `proofs/validation/MD_DATA_RA_001.csv` (matrix) — 
