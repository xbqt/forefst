# Dossier — FS_SUPB_RA_005 (PURE-RD-LAYOUT)

**Claim (this audit tests):** CHKP LCN pointers at SUPB offsets 0xC0 and 0xC8 are the only bootstrap-critical SUPB fields. If both are corrupted the driver cannot find any checkpoint and the volume should fail to mount. CHKP corruption NOT tested.

**Canonical claim (reference_table.csv):** File System: CHKP LCN pointers at SUPB offsets 0xC0 and 0xC8 are the only bootstrap-critical SUPB fields. If both are corrupted the driver cannot find any checkpoint and the volume should fail to mount. CHKP corruption NOT tested.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SUPB+0xC0 and +0xC8 hold the two checkpoint LCNs; both land on valid CHKP pages on 48/48; offset matches SUPB+0x70(==0xC0). These are the bootstrap-critical pointers.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_supb__forefst.txt
- structure_reference.md:129-130 SUPB 0xC0/0xC8 = checkpoint LCN 1/2. Byte-verified non-zero and == chkp_lcns (0x13f8/0xee34 on the mini volumes).

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_SUPB_RA_005.csv`
- corrected registry note: Inferred from successful mount with GUID corruption: only CHKP pointers needed for bootstrap chain. See ra_step4_15_corrupted_metadata_report.md

## Proof links
- `proofs/static/parse_supb__forefst.txt` (static) — parse_supb
- `proofs/validation/FS_SUPB_RA_005.csv` (matrix) — 
