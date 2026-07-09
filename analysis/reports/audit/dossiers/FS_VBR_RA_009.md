# Dossier — FS_VBR_RA_009 (BEHAVIORAL)

**Claim (this audit tests):** Version evolution: 3.7/3.9 structurally identical to 3.4; 3.10 is critical transition (CRC64+indirect roots+compact refs+native flag+version echo+Format GUID+OID 0x30); CHKP flag 0x2000 = insider-only

**Canonical claim (reference_table.csv):** File System: Version evolution: 3.7/3.9 structurally identical to 3.4; 3.10 is critical transition (CRC64+indirect roots+compact refs+native flag+version echo+Format GUID+OID 0x30); CHKP flag 0x2000 = insider-only

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Version-evolution narrative. Disk supports the structural deltas: v3.10 is where Extended GUID (0x48) becomes nonzero (2/2), 0x2A becomes 0x02/CRC64 (2/2), and flags reach 0x66 (2/2); v3.7/3.9 share 0x26 flags + 0x00 selector + zero GUID like v3.4.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Multi-image observation across 7 Step-4 images (21H2 v3.7, 22H2 v3.9, 23H2 v3.10, Insider): the on-disk structures match v3.4; only VBR 0x28/0x29 + CHKP 0x54/0x56 change. Cross-version meta-claim, corroborated by the version_consistency probe (FS_VBR_009).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_VBR_RA_009.csv`
- corrected registry note: 7 new images from Step 4 version analysis (21H2/22H2/23H2/Insider). See sublab_step4_version_analysis.md | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Multi-part behavioral claim; the VBR-observable parts (CRC64 selector, GUID, native flag, version echo at v3.10) are disk-consistent. Non-VBR parts (indirect roots, compact refs, OID changes) are out of this region's scope -- belo

## Proof links
- `proofs/validation/FS_VBR_RA_009.csv` (matrix) — 
