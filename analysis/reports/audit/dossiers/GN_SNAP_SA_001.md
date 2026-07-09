# Dossier — GN_SNAP_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** Win11 snapshot support: 6->24 functions; CStreamSnapshot class; $SNAPSHOT attribute; no SnapshotId field in $SI; 0x50=PackedEaSize. Snapshots link via the type-0xB0 stream index at val[0x44]

**Canonical claim (reference_table.csv):** General: Win11 snapshot support: 6->24 functions; CStreamSnapshot class; $SNAPSHOT attribute; no SnapshotId field in $SI; 0x50=PackedEaSize. Snapshots link via the type-0xB0 stream index at val[0x44]

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Snapshot support is on-disk via the type-0xB0 stream index (val[0x10] discriminator =2 for snapshot, confirmed on 29 entries). The static parts (6->24 functions, CStreamSnapshot class, 0x50=PackedEaSize, link at val[0x44]) are E2/driver. The audit's own disk note says 'snapshot-enabled image shows no additional root tables' - consistent: snapshots live inside type-0xB0 sub-records, not in new system roots.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** E2 (win11+)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Snapshots] Win11 snapshot support: 6->24 functions; CStreamSnapshot class; $SNAPSHOT attribute; no SnapshotId field in $S — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_SNAP_SA_001.csv`
- corrected registry note: Snapshot-enabled image shows no additional root tables or visible structural changes | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NOT_CONFIRMED): Function-count and class-name claims are static (E2 win11+). Disk confirms snapshots add no new root tables and live as 0xB0 sub-records, consistent with the claim.

## Proof links
- `proofs/validation/GN_SNAP_SA_001.csv` (matrix) — 
