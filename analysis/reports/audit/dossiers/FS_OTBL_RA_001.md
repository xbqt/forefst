# Dossier — FS_OTBL_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** OID 0x30 = Session Activity Table. First appears in v3.10 (Win11 23H2). Stores per-mount-session IO/allocation statistics. Key: FILETIME + sub-ID. Present on all 46 v3.10+/v3.14 images, absent on all 15 v3.4/v3.7/v3.9 images. Created during upgrade of pre-3.10 volumes.

**Canonical claim (reference_table.csv):** File System: OID 0x30 = Session Activity Table. First appears in v3.10 (Win11 23H2). Stores per-mount-session IO/allocation statistics. Key: FILETIME + sub-ID. Present on all 46 v3.10+/v3.14 images, absent on all 15 v3.4/v3.7/v3.9 images. Created during upgrade of pre-3.10 volumes.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OID 0x30 present exactly on v3.10+ : 97/113 total. By version: v3.4 0/13, v3.7 0/1, v3.9 0/2 (ABSENT); v3.10 2/2, v3.14 92/92, v3.15 1/1, v6.66 2/2 (PRESENT). The 'first appears in v3.10' scoping is exact on disk.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 1/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsTelemetryPerfCountersWorker__decomp.txt
- Static driver evidence: RefsTelemetryPerfCountersWorker. OID 0x30 = Session Activity Table. First appears in v3.10 (Win11 23H2). Stores per-mount-session IO/allocation. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_RA_001.csv`
- corrected registry note: Deep-decoded via refs_oid30_analysis.py: B+ tree with FILETIME-keyed rows, two value formats (80-byte summary, 44-byte per-category). Correlates with RefsTelemetryPerfCountersWorker in static analysis. Independent of heat gathering. Forensic value: mount session timestamps and activity metrics.

## Proof links
- `proofs/static/RefsTelemetryPerfCountersWorker__decomp.txt` (static) — RefsTelemetryPerfCountersWorker
- `proofs/validation/FS_OTBL_RA_001.csv` (matrix) — 
