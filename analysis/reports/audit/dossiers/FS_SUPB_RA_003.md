# Dossier — FS_SUPB_RA_003 (BEHAVIORAL)

**Claim (this audit tests):** SUPB corruption is silently repaired during mount by Win11 3.14 driver. Corrupted Volume GUID byte (0x2A→0xD5) at SUPB+0x55 was restored to original value during mount. Repair occurs as part of normal checkpoint update cycle (CoW write of fresh SUPB).

**Canonical claim (reference_table.csv):** File System: SUPB corruption is silently repaired during mount by Win11 3.14 driver. Corrupted Volume GUID byte (0x2A→0xD5) at SUPB+0x55 was restored to original value during mount. Repair occurs as part of normal checkpoint update cycle (CoW write of fresh SUPB).

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/ChooseSuperBlock__decomp.txt
- ChooseSuperBlock selects the highest-clock validating SUPB copy and memcpy's it over stale copies at mount (finding #332). Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_SUPB_RA_003.csv`
- corrected registry note: Binary comparison: corrupted byte 0xD5 reverted to 0x2A after mount. 82 pages changed during mount. See ra_step4_15_corrupted_metadata_report.md

## Proof links
- `proofs/static/ChooseSuperBlock__decomp.txt` (static) — ChooseSuperBlock
- `proofs/validation/FS_SUPB_RA_003.csv` (matrix) — 
