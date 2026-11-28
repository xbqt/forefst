# Dossier — FS_SCHM_RA_009 (BEHAVIORAL)

**Claim (this audit tests):** Production v3.14 has 29 schemas (13 system + 16 attribute), not 30 (14+16). 14 system schemas is the Insider count (adds 0xe140 Vol Attestation). Errata E14.

**Canonical claim (reference_table.csv):** File System: Production v3.14 has 29 schemas (13 system + 16 attribute), not 30 (14+16). 14 system schemas is the Insider count (adds 0xe140 Vol Attestation). Errata E14.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Native (non-upgraded, non-Insider) v3.14 volumes have exactly 29 schema-table entries = 13 system (e010,e030,e040,e060,e080,e090,e0b0,e0c0,e0d0,e100,e110,e120,e130) + 16 attribute (0x110-0x200) on 86/86 native v3.14 images. Insider v3.14 builds (winsider/wininsiderrefs*, 3 images) have 14 system (adds 0xe140 Vol Attestation) = 30, distinct from production. Upgraded v3.4->v3.14 volumes carry the union (35/36).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Schema Table] Production v3.14 has 29 schemas (13 system + 16 attribute), not 30 (14+16). 14 system schemas is the Insider c — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SCHM_RA_009.csv`
- corrected registry note: All 14 v3.14 test images show 29 schemas; Insider shows 30

## Proof links
- `proofs/validation/FS_SCHM_RA_009.csv` (matrix) — 
