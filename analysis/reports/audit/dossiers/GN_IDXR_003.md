# Dossier — GN_IDXR_003 (BEHAVIORAL)

**Claim (this audit tests):** Root 0x18-0x20: number of extents

**Canonical claim (reference_table.csv):** General: Root 0x18-0x20: number of extents

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CONFIRMED 2026-06-19 (was NEEDS-STATIC): _SmsIndexRoot+0x18 (u64) = leaf extent/page count (0 single-page; ==leaf census on multi-level: oid7=10/oid73f=3/oid760=1). Static CreateIndex win10 @73244 -> this+0x40 extent counter. Prade 'number of extents' correct.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Index Root] Root 0x18-0x20: number of extents — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_IDXR_003.csv`
- corrected registry note: CONFIRMED ALL-DISK 2026-06-19: desc+0x18 = number of leaf extents/pages (0 single-page; == leaf-page census on every clean multi-level table: oid7=10, oid73f=3, oid760=1). PRADE 'number of extents' CORRECT. See structure_reference A.2b. (Was NEEDS-STATIC in re-verify.)

## Proof links
- `proofs/validation/GN_IDXR_003.csv` (matrix) — 
