# Dossier — FS_VBR_SA_013 (BEHAVIORAL)

**Claim (this audit tests):** RefsIsBootSectorOurs: validates boot sector ownership. Checks "ReFS" signature at +0x03, sector size power-of-2, volume sector count > 0. Returns BOOLEAN.

**Canonical claim (reference_table.csv):** File System: RefsIsBootSectorOurs: validates boot sector ownership. Checks "ReFS" signature at +0x03, sector size power-of-2, volume sector count > 0. Returns BOOLEAN.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — RefsIsBootSectorOurs validation logic (ReFS sig @0x03, sector-size power-of-2, sector-count>0) is a decompiled-function behavioral claim. Disk-side: all 113 images satisfy these preconditions (ReFS@0x03, bps=512 power-of-2, sector-count>0), consistent with the function accepting them.

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsIsBootSectorOurs__decomp.txt
- Static driver evidence: RefsIsBootSectorOurs is the boot-sector validator (the basis of forefst._vbr_checksum and finding #331). Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_VBR_SA_013.csv`
- corrected registry note: (none)

## Proof links
- `proofs/static/RefsIsBootSectorOurs__decomp.txt` (static) — RefsIsBootSectorOurs
- `proofs/validation/FS_VBR_SA_013.csv` (matrix) — 
