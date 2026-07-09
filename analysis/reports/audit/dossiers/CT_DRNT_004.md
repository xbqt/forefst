# Dossier — CT_DRNT_004 (BEHAVIORAL)

**Claim (this audit tests):** Optional per-cluster checksums

**Canonical claim (reference_table.csv):** Content: Optional per-cluster checksums

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Integrity per-cluster checksum extents (flag 0x1c00d0) present and all run_length==1 on 261/261 entries across v3.14 integrity-enabled files; absent on non-integrity files (optional). 24-byte extent stride parses cleanly.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Per-cluster checksum option in the extent run. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_DRNT_004.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/CT_DRNT_004.csv` (matrix) — 
