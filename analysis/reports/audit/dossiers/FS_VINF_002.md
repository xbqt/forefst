# Dossier — FS_VINF_002 (STRUCTURAL)

**Claim (this audit tests):** General info: creation/mount times, version

**Canonical claim (reference_table.csv):** File System: General info: creation/mount times, version

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OID 0x500 key 0x520 (vlen=448) present on 113/113. Layout holds: vol version@+0x80/+0x81, drv version@+0x82/+0x83, create FILETIME@+0x90, modify FILETIME@+0xA0. vol-ver@+0x80 == bootstrap version on 110/113.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- structure_reference.md F.4b OID 0x500 key 0x0520 = general info. Byte-verified present, vlen 448 (times+version block). Probe asserts presence + vlen>=64.

## Raw-disk proof
- probe `vinf_row` ; validation matrix: `proofs/validation/FS_VINF_002.csv`
- corrected registry note: Volume info rows contain timestamps (creation, last mount) parsed by refs_volume_info.py

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/FS_VINF_002.csv` (matrix) — 
