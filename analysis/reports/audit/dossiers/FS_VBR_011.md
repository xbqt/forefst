# Dossier — FS_VBR_011 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x40-0x48: bytes per container

**Canonical claim (reference_table.csv):** File System: 0x40-0x48: bytes per container

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — le64(VBR,0x40) bytes-per-container == 0x04000000 (64 MiB) on 112/113. The single 0 is the fixboot image (refsutil fixboot sets container_size=0, per FS_VBR_RA_006).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 111/111 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:29 VBR 0x40, u64, 0x04000000 (64 MiB, invariant). Byte-verified.

## Raw-disk proof
- probe `vbr_int` ; validation matrix: `proofs/validation/FS_VBR_011.csv`
- corrected registry note: Always 0x4000000 (64 MiB) across all 39 images regardless of cluster size

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_011.csv` (matrix) — 
