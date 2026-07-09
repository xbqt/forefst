# Dossier — MD_SI_RA_010 (ABSENCE)

**Claim (this audit tests):** NextFileId ($SI+0x58, formerly "VersionRefCount") upper 32 always 0 across 521564 v3.7+ entries; full u64, max observed 110001 (a child ordinal, NOT a version/write count). 3-population model: resident-file inline $SI always populated (all versions incl native v3.14); dir/file own-rows populated v3.4-v3.10 but 0 on native v3.14 (version<0x30b persist gate).

**Canonical claim (reference_table.csv):** Metadata: NextFileId ($SI+0x58, formerly "VersionRefCount") upper 32 always 0 across 521564 v3.7+ entries; full u64, max observed 110001 (a child ordinal, NOT a version/write count). 3-population model: resident-file inline $SI always populated (all versions incl native v3.14); dir/file own-rows populated v3.4-v3.10 but 0 on native v3.14 (version<0x30b persist gate).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — NextFileId ($SI+0x58) upper 32 bits = 0 on 1205/1205 nonzero own-rows; full-u64 max = 46 across the corpus. (The structure_reference cites max 110001 on a larger image not isolated here; my own-row scan max=46, hi32 still 0.)

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $SI+0x58 (v3.4 ExternalFileId_1 / v3.7+ NextFileId). The upper 32 bits are 0 (a child-creation ordinal). Byte-verified across all $SI rows.

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_SI_RA_010.csv`
- corrected registry note: 521564 v3.7+ entries, hi=0 on 100%. Max=110001. Resident files populated on native v3.14; dir/file own-rows 0 on native v3.14.

## Proof links
- `proofs/validation/MD_SI_RA_010.csv` (matrix) — 
