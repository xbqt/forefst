# Dossier — FS_SCHM_RA_010 (BEHAVIORAL)

**Claim (this audit tests):** Schema 0x160 = Reparse Index (naming correction). Previously unnamed or mislabeled as Security Descriptor in some contexts.

**Canonical claim (reference_table.csv):** File System: Schema 0x160 = Reparse Index (naming correction). Previously unnamed or mislabeled as Security Descriptor in some contexts.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Schema 0x160 (type 0x60, Reparse Index) present on ALL versions: v3.4=13/13, v3.7=1/1, v3.9=2/2, v3.10=2/2, v3.14=92/92, v3.15=1/1 (111/111). It is a distinct registered schema, separate from the Security-Descriptor stream (OID 0x530 has no schema).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Schema Table] Schema 0x160 = Reparse Index (naming correction). Previously unnamed or mislabeled as Security Descriptor in s — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SCHM_RA_010.csv`
- corrected registry note: Present in all v3.7+ images; absent in v3.4

## Proof links
- `proofs/validation/FS_SCHM_RA_010.csv` (matrix) — 
