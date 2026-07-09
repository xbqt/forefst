# Dossier — FS_VBR_RA_006 (BEHAVIORAL)

**Claim (this audit tests):** refsutil fixboot sets container_size=0 at offset 0x40, preventing virtual-to-physical address translation

**Canonical claim (reference_table.csv):** File System: refsutil fixboot sets container_size=0 at offset 0x40, preventing virtual-to-physical address translation

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Fixboot image has le64(VBR,0x40)==0 (container size zeroed). This directly causes FS_VBR_011's only outlier.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [VBR] refsutil fixboot sets container_size=0 at offset 0x40, preventing virtual-to-physical address translation — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_VBR_RA_006.csv`
- corrected registry note: Critical finding: without container size the mount code cannot resolve virtual LCNs via container table | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Behavioral; corroborated on the 1 fixboot image. The 'prevents VLCN->PLCN translation' consequence is logical (container size feeds Translator cpc) but I did not attempt to mount/translate the corrupted image.

## Proof links
- `proofs/validation/FS_VBR_RA_006.csv` (matrix) — 
