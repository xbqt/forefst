# Dossier — CT_DRNT_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** Snapshot extent entries use same 24-byte format (VLCN+flags+file_VCN+run_length) as regular type-0x40 data runs. Unified extent storage across non-resident directory entries and embedded DATA entries. Confirmed on 21 snapshots across 4 images.

**Canonical claim (reference_table.csv):** Content: Snapshot extent entries use same 24-byte format (VLCN+flags+file_VCN+run_length) as regular type-0x40 data runs. Unified extent storage across non-resident directory entries and embedded DATA entries. Confirmed on 21 snapshots across 4 images.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — All 29 snapshot streams across 10 snapshot-bearing images resolve via the identical 24-byte extent format (VLCN@0x00 + flags@0x08 + file_VCN@0x0C + pad@0x10 + run_length@0x14) used by type-0x40 data runs. forefst.recover_snapshot_streams uses the same parse path as type-0x40.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Snapshot extents reuse the 24-byte extent format. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_DRNT_RA_001.csv`
- corrected registry note: Validated on 12 files / 21 true snapshots / 4 images including 21-extent 13.4 MB chains

## Proof links
- `proofs/validation/CT_DRNT_RA_001.csv` (matrix) — 
