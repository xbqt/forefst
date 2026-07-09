# Dossier — FS_SUPB_007 (STRUCTURAL)

**Claim (this audit tests):** Two backup copies near end of partition

**Canonical claim (reference_table.csv):** File System: Two backup copies near end of partition

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — backups at total_clusters-2/-3 (113/113), NOT -14339/-14338

**Original audit verdict:** CONTRADICTED (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_supb__forefst.txt
- structure_reference.md:117 + #332: primary SUPB at LCN 0x1E plus two backups near the partition end. Byte-verified 'SUPB' at total_clusters-2 and total_clusters-3.

## Raw-disk proof
- probe `supb_backup` ; validation matrix: `proofs/validation/FS_SUPB_007.csv`
- corrected registry note: 2 backups at LCN total_clusters-2 and total_clusters-3 (RE-MEASURED 2026-06-18, SUPB signature found at delta 2 AND 3 on 113/113 images; the earlier '-14339/-14338' was wrong). Identical GUID/chkp refs to primary.

## Proof links
- `proofs/static/parse_supb__forefst.txt` (static) — parse_supb
- `proofs/validation/FS_SUPB_007.csv` (matrix) — 
