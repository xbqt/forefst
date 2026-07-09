# Dossier — FS_CHKP_RA_003 (BEHAVIORAL)

**Claim (this audit tests):** 3.4->3.14 upgrade: CHKP flags change from 0x002 to 0x602 (adds 0x200+0x400). Ref_size changes from 0x68 to 0x30. New schemas added (union of old+new). Container Table and Small Allocator physically relocated to lower LCNs. ~35-41 checkpoint cycles observed.

**Canonical claim (reference_table.csv):** File System: 3.4->3.14 upgrade: CHKP flags change from 0x002 to 0x602 (adds 0x200+0x400). Ref_size changes from 0x68 to 0x30. New schemas added (union of old+new). Container Table and Small Allocator physically relocated to lower LCNs. ~35-41 checkpoint cycles observed.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — Disk shows the END states cleanly (v3.4 flags=0x002/refsize=0x68 vs v3.14 flags=0x682-or-0x602/refsize=0x30), so the claimed deltas are consistent with disk. But the BEHAVIORAL transition (an upgrade EVENT changing 0x002->0x602, adding schemas) requires a before/after upgrade pair, not measurable from static snapshots alone.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (upgrade path): the CHKP+0x78 flags gain the 0x600 bits on upgrade. RD-observed on upgrade images (win10to11refs4g); complements the 3-state model (FS_CHKP_RA_013, #332). No corpus field probe — verified on the specific upgrade lineage.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_CHKP_RA_003.csv`
- corrected registry note: Flags 0x002->0x602 confirmed. Ref_size 0x68->0x30. VBR immutable (0x2A/0x2C/0x48 unchanged). Extensive metadata reorganization.

## Proof links
- `proofs/validation/FS_CHKP_RA_003.csv` (matrix) — 
