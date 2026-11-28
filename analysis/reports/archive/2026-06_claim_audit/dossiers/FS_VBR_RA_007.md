# Dossier — FS_VBR_RA_007 (BEHAVIORAL)

**Claim (this audit tests):** refsutil fixboot changes checksum selector (0x2A) from 0x02 to 0x00 — mismatches existing CRC64 metadata

**Canonical claim (reference_table.csv):** File System: refsutil fixboot changes checksum selector (0x2A) from 0x02 to 0x00 — mismatches existing CRC64 metadata

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Fixboot image VBR 0x2A==0x00; a normal native v3.14 image has 0x2A==0x02 (CRC64). 0x2A selector distribution on disk: v3.14 {0x02:84, 0x00:4(upgraded), 0x04:4(SHA-256)}, v3.10 0x02, v3.4/3.7/3.9 0x00.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- refsutil.exe behavior: fixboot resets the cksel. RD-observed on the fixboot-test image (cksel reads 0 there).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_VBR_RA_007.csv`
- corrected registry note: Volume formatted with CRC64 but fixboot resets to None; integrity check mismatch prevents mount | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Behavioral; the fixboot 0x2A->0x00 effect is visible on the one fixboot image. 'Mismatches existing CRC64 metadata' is an inference about mount behavior, not re-measured.

## Proof links
- `proofs/validation/FS_VBR_RA_007.csv` (matrix) — 
