# Dossier — FS_SCHM_RA_005 (BEHAVIORAL)

**Claim (this audit tests):** Schema 0x1b0 = $SNAPSHOT/$NAMED_STREAM attribute (NOT Index Root). Confirmed via RefsQueryStreamsInfo: uVar5 = 0xb0 alongside RtlInitUnicodeString($SNAPSHOT). Type code 0xB0 exists in all driver builds but schema 0x1B0 only registered on disk at v3.14+.

**Canonical claim (reference_table.csv):** File System: Schema 0x1b0 = $SNAPSHOT/$NAMED_STREAM attribute (NOT Index Root). Confirmed via RefsQueryStreamsInfo: uVar5 = 0xb0 alongside RtlInitUnicodeString($SNAPSHOT). Type code 0xB0 exists in all driver builds but schema 0x1B0 only registered on disk at v3.14+.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Schema 0x1B0 version-gating: absent v3.4 (0/13), present v3.7 (1/1), v3.9 (2/2), v3.10 (2/2), v3.14 (92/92), v3.15 (1/1). Appears in schema table as a registered attribute schema (type 0xB0) on 98/111 images (all v3.7+).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Schema Table] Schema 0x1b0 = $SNAPSHOT/$NAMED_STREAM attribute (NOT Index Root). Confirmed via RefsQueryStreamsInfo: uVar5 = — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SCHM_RA_005.csv`
- corrected registry note: Type code in driver since v3.4 but schema table entry only on v3.14+ disk images

## Proof links
- `proofs/validation/FS_SCHM_RA_005.csv` (matrix) — 
