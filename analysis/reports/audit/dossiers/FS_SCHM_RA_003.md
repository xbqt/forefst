# Dossier — FS_SCHM_RA_003 (BEHAVIORAL)

**Claim (this audit tests):** Schema 0xe120 = Candidate Table (dirty range tracking). CCandidateCmsTable class + MsInsertDirtyRangeEntry validation check. First appears in v3.10 (Win11 23H2).

**Canonical claim (reference_table.csv):** File System: Schema 0xe120 = Candidate Table (dirty range tracking). CCandidateCmsTable class + MsInsertDirtyRangeEntry validation check. First appears in v3.10 (Win11 23H2).

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — Schema 0xe120 (Candidate/Dirty-Range Table) first appears at v3.9, not v3.10: absent v3.4 (0/13) and v3.7 (0/1), PRESENT on both v3.9 images (2/2), and v3.10 (2/2), v3.14 (92/92), v3.15 (1/1).

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** E2 (win11+)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Schema Table] Schema 0xe120 = Candidate Table (dirty range tracking). CCandidateCmsTable class + MsInsertDirtyRangeEntry val — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SCHM_RA_003.csv`
- corrected registry note: Schema 0xe120 absent on v3.4/v3.7. Present on v3.10+ images | RE-VERIFIED 2026-06-18 (all-disk): claim: '0xe120 ... First appears in v3.10 (Win11 23H2)' — disk: present on v3.9 (Win11 22H2) images win1122h2test.raw + win1122h2test_testchecksum.raw, so first appearance is v3.9

## Proof links
- `proofs/validation/FS_SCHM_RA_003.csv` (matrix) — 
