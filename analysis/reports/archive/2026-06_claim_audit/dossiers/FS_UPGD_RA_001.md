# Dossier — FS_UPGD_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** SUPB is NOT modified during version upgrade; only VBR and CHKP are modified. SUPB retains old self-descriptor length (0x68) even after upgrade to 3.14.

**Canonical claim (reference_table.csv):** File System: SUPB is NOT modified during version upgrade; only VBR and CHKP are modified. SUPB retains old self-descriptor length (0x68) even after upgrade to 3.14.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Version Upgrade] SUPB is NOT modified during version upgrade; only VBR and CHKP are modified. SUPB retains old self-descriptor — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_UPGD_RA_001.csv`
- corrected registry note: See sublab_step4_version_analysis.md Section 6

## Proof links
- `proofs/validation/FS_UPGD_RA_001.csv` (matrix) — 
