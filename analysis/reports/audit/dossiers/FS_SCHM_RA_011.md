# Dossier — FS_SCHM_RA_011 (BEHAVIORAL)

**Claim (this audit tests):** Schema counts per version verified: v3.4=27(15+12), v3.7=30(15+15), v3.9=31(16+15), v3.10=30(15+15), v3.14=29(13+16), Insider=30(14+16) [E53]. Complete evolution matrix.

**Canonical claim (reference_table.csv):** File System: Schema counts per version verified: v3.4=27(15+12), v3.7=30(15+15), v3.9=31(16+15), v3.10=30(15+15), v3.14=29(13+16), Insider=30(14+16) [E53]. Complete evolution matrix.

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — On-disk distinct schema-table ENTRY counts (mode per version): v3.4=27 (15 sys+12 attr), v3.7=30 (15+15), v3.9=31 (16+15), v3.10=30 (15+15), v3.14 native=29 (13+16), Insider=30 (14+16). The claimed v3.4=27/v3.7=30/v3.9=31/v3.10=30 are each exactly +2 too low: the legacy attribute schemas 0x004 and 0x006 occupy real schema-table rows on EVERY v3.4/v3.7/v3.9/v3.10 image (and on upgraded v3.14) but are excluded from the claimed counts.

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Schema Table] Schema counts per version verified: v3.4=27(15+12), v3.7=30(15+15), v3.9=31(16+15), v3.10=30(15+15), v3.14=29( — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SCHM_RA_011.csv`
- corrected registry note: Exact counts match on all 20 test images | RE-VERIFIED 2026-06-18 (all-disk): claim: v3.4=27(15+12), v3.7=30(15+15), v3.9=31(16+15), v3.10=30(15+15), v3.14=29(13+16), Insider=30(14+16) [E53] — disk: v3.4=27, v3.7=30, v3.9=31, v3.10=30 (each +2 from omitted legacy 0x004+0x006); v3.14=29 and Insider=30 MATCH

## Proof links
- `proofs/validation/FS_SCHM_RA_011.csv` (matrix) — 
