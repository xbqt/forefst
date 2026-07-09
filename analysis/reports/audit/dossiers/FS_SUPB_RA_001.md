# Dossier — FS_SUPB_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** SUPB page header fully decoded (0x00-0x4F). Page header version always 2. Reserved fields at 0x08 and 0x18 always zero. Volume signature = XOR of GUID dwords. LCN slots 1-3 always zero (SUPB is single-cluster). Table OID = 0. Gap 0x60-0x67 between Volume GUID and SUPB version confirmed always zero.

**Canonical claim (reference_table.csv):** File System: SUPB page header fully decoded (0x00-0x4F). Page header version always 2. Reserved fields at 0x08 and 0x18 always zero. Volume signature = XOR of GUID dwords. LCN slots 1-3 always zero (SUPB is single-cluster). Table OID = 0. Gap 0x60-0x67 between Volume GUID and SUPB version confirmed always zero.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — SUPB page header (0x00-0x4F) on 48/48: ph_version(0x04)==2, reserved(0x08)==0, reserved(0x18)==0, volume-signature(0x0C)==XOR of GUID dwords. All four hold 48/48.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsVolume::Start. SUPB page header fully decoded (0x00-0x4F). Page header version always 2. Reserved fields at 0x08 and 0x18 alw. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_SUPB_RA_001.csv`
- corrected registry note: Page header fields verified on 13 images. SUPB 0x60-0x67 zero across all configurations. See ra_step4_12_deep_structure_report.md

## Proof links
- `proofs/validation/FS_SUPB_RA_001.csv` (matrix) — 
