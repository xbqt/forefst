# Dossier — MD_SI_RA_008 (STRUCTURAL)

**Claim (this audit tests):** $SI+0x58 (v3.4 "ExternalFileId_1" / v3.7+ "VersionRefCount") = NextFileId, a directory CHILD-CREATION ordinal — NOT a version/write counter. Write path RefsMoveFile increments the parent dir SCB's NextFileId (SCB+0x1b8 win11/+0x1a8 insider, init=1) and stamps the new child FCB+0x158. Non-zero on 100% of v3.4 entries (3601/3601), values small integers = assigned child ordinals.

**Canonical claim (reference_table.csv):** Metadata: $SI+0x58 (v3.4 "ExternalFileId_1" / v3.7+ "VersionRefCount") = NextFileId, a directory CHILD-CREATION ordinal — NOT a version/write counter. Write path RefsMoveFile increments the parent dir SCB's NextFileId (SCB+0x1b8 win11/+0x1a8 insider, init=1) and stamps the new child FCB+0x158. Non-zero on 100% of v3.4 entries (3601/3601), values small integers = assigned child ordinals.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — NextFileId ($SI+0x58, val+0x80): nonzero on 1205 own-rows, upper-32-bits ZERO on 1205/1205, max observed = 46 (small near-contiguous ints). Probed values 1,2,5 on v3.4. 0 on native-v3.14 dir own-rows (persisted to object-record payload on v3.11+, per §C.7).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $SI+0x58 holds NextFileId (the directory child-creation ordinal); the upper 32 bits are 0 (same field/probe as MD_SI_RA_010, different framing).

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_SI_RA_008.csv`
- corrected registry note: 3601/3601 v3.4 entries non-zero; values = child ordinals (near-contiguous from 2). dir own-row = max(child ordinal): 0 violations across 232 dirs on v3.7/3.9/3.10.

## Proof links
- `proofs/validation/MD_SI_RA_008.csv` (matrix) — 
