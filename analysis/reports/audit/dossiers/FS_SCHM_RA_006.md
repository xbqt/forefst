# Dossier — FS_SCHM_RA_006 (BEHAVIORAL)

**Claim (this audit tests):** Schemas 0x1c0/0x1d0 = $REPARSE_POINT (0xC0) / $EA_INFORMATION (0xD0). NTFS-equivalent type codes reused by ReFS. Min resident 8B. v3.7+. 0xC0: RefsGetReparsePointValue calls LookupAttribute(0xc0). 0xD0: RefsLookupEasOnFile(Ea.c) calls LookupAttribute(0xd0) with _EA_INFORMATION* param.

**Canonical claim (reference_table.csv):** File System: Schemas 0x1c0/0x1d0 = $REPARSE_POINT (0xC0) / $EA_INFORMATION (0xD0). NTFS-equivalent type codes reused by ReFS. Min resident 8B. v3.7+. 0xC0: RefsGetReparsePointValue calls LookupAttribute(0xc0). 0xD0: RefsLookupEasOnFile(Ea.c) calls LookupAttribute(0xd0) with _EA_INFORMATION* param.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Schemas 0x1C0 and 0x1D0 version-gating: both absent v3.4 (0/13), present v3.7 (1/1), v3.9 (2/2), v3.10 (2/2), v3.14 (92/92), v3.15 (1/1) — i.e. v3.7+ exactly as claimed.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Schema Table] Schemas 0x1c0/0x1d0 = $REPARSE_POINT (0xC0) / $EA_INFORMATION (0xD0). NTFS-equivalent type codes reused by ReF — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SCHM_RA_006.csv`
- corrected registry note: Schemas 0x1c0/0x1d0 absent on v3.4. Present on v3.7+. No instances in directory B+ trees on 80+ images — stored in per-file attribute sets, not visible in Object Table directory entries

## Proof links
- `proofs/validation/FS_SCHM_RA_006.csv` (matrix) — 
