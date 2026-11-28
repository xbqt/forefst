# Dossier — FS_SCHM_RA_004 (BEHAVIORAL)

**Claim (this audit tests):** Schema 0xe130 = Heat Engine Persistence Table. CmsVolumeHeatEngine::Initialize creates table via MsCreateDurableTableObject. Persists container heat metrics for tiered storage optimization (compression/decompression/recompression heat classes). Found in Insider refs.sys binary only (not in Win11 26H1 build). First appears v3.10.

**Canonical claim (reference_table.csv):** File System: Schema 0xe130 = Heat Engine Persistence Table. CmsVolumeHeatEngine::Initialize creates table via MsCreateDurableTableObject. Persists container heat metrics for tiered storage optimization (compression/decompression/recompression heat classes). Found in Insider refs.sys binary only (not in Win11 26H1 build). First appears v3.10.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Schema 0xe130 (Heat Engine) first appears at v3.10: absent v3.4 (0/13), v3.7 (0/1), v3.9 (0/2); present v3.10 (2/2), v3.14 (92/92), v3.15 (1/1). Gating matches structure_reference F.3 (0xe130 = v3.10+).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsVolumeHeatEngine::Initialize. Schema 0xe130 = Heat Engine Persistence Table. CmsVolumeHeatEngine::Initialize creates table via MsCreateDurab. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_SCHM_RA_004.csv`
- corrected registry note: Schema 0xe130 absent on v3.4/v3.7. Present on v3.10+. Always 0 rows on test volumes (no active tiered storage)

## Proof links
- `proofs/validation/FS_SCHM_RA_004.csv` (matrix) — 
