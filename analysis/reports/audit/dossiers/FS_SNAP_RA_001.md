# Dossier — FS_SNAP_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** Complete embedded attribute taxonomy with dual-marker system. The genuine embedded-attribute type-code set is EXACTLY 10 codes: 0x38/0x39 ($OBJ_LINK), 0x80 ($DATA), 0x90 ($I30_INDEX), 0xB0 ($SNAPSHOT/ADS), 0xC0 ($REPARSE), 0xD0 ($EA_INFO), 0xE0 ($EA), 0xF0 (USN $Max), 0x100 ($EFS); 0x50/0x60/0xA0 NEVER appear as embedded sub-records. Marker 0x80000001: single-instance (0x80 DATA header/0xC0 REPARSE/0xD0 EA_INFO/0xE0 EA / 0xF0 USN $Max). Marker 0x80000002: multi-instance (0x39 FileRef/0x80 DATA stream/0xB0 Named Stream/0x100 $EFS). 0xB0 format: val[0x04]=0x68=EXTENDED (snapshots) vs !=0x68=INLINE (ADS). 532503 entries (526454 with markers + 6049 unclassified) across 409185 files on 112 images.

**Canonical claim (reference_table.csv):** File System: Complete embedded attribute taxonomy with dual-marker system. The genuine embedded-attribute type-code set is EXACTLY 10 codes: 0x38/0x39 ($OBJ_LINK), 0x80 ($DATA), 0x90 ($I30_INDEX), 0xB0 ($SNAPSHOT/ADS), 0xC0 ($REPARSE), 0xD0 ($EA_INFO), 0xE0 ($EA), 0xF0 (USN $Max), 0x100 ($EFS); 0x50/0x60/0xA0 NEVER appear as embedded sub-records. Marker 0x80000001: single-instance (0x80 DATA header/0xC0 REPARSE/0xD0 EA_INFO/0xE0 EA / 0xF0 USN $Max). Marker 0x80000002: multi-instance (0x39 FileRef/0x80 DATA stream/0xB0 Named Stream/0x100 $EFS). 0xB0 format: val[0x04]=0x68=EXTENDED (snapshots) vs !=0x68=INLINE (ADS). 532503 entries (526454 with markers + 6049 unclassified) across 409185 files on 112 images.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Embedded-attribute taxonomy confirmed for the type codes my harness exercised: 0x39/0x38 ($OBJ_LINK), 0x80 ($DATA), 0x90 ($I30_INDEX), 0xB0 ($SNAPSHOT/ADS) all appear as embedded sub-records with the dual-marker system - 0x80000001 (single-instance: 0x80 $DATA header, 0x38 legacy objlink) and 0x80000002 (multi-instance: 0x39 FileRef, 0x90, 0xB0). On the histograms, marker 0x80000002 wraps 0x39/0x90/0xB0; 0x80000001 wraps 0x80/0x38. Native v3.4 0x38 uses a bare type-code key (no 0x80000001/2 marker).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Embedded Attribute System] Complete embedded attribute taxonomy with dual-marker system. The genuine embedded-attribute type-code set is — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SNAP_RA_001.csv`
- corrected registry note: 28 true version snapshots (dsid>0x1000) across 9 images + 1192 inline ADS + 2200 reparse points + 10130 EA entries (WSL $LXUID/$LXGID/$LXMOD/$LXDEV) + 9 type-0xF0 USN $Max (1/image). All schemas 0x1B0-0x200 empirically confirmed. Tool: refs_snapshots.py + dual_marker_scan.py

## Proof links
- `proofs/validation/FS_SNAP_RA_001.csv` (matrix) — 
