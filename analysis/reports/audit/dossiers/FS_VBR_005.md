# Dossier — FS_VBR_005 (STRUCTURAL)

**Claim (this audit tests):** 0x16-0x18: checksum for boot sector

**Canonical claim (reference_table.csv):** File System: 0x16-0x18: checksum for boot sector

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — ROR1+ADD checksum over bytes 3..511 EXCLUDING 0x16/0x17 == stored le16(VBR,0x16) on 113/113. Without the 0x16/0x17 exclusion: 0/113 match (proves the exclusion is required). Fixboot image stored=0xfa81 recompute=0xfa81 (refsutil recomputed it).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- structure_reference.md:20 VBR 0x16 = ROR1+ADD self-checksum. Non-zero on every intact VBR; the value itself is per-image (depends on VBR contents).

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_VBR_005.csv`
- corrected registry note: refs_boot.py validates checksum on all 39 images; all pass

## Proof links
- `proofs/validation/FS_VBR_005.csv` (matrix) — 
