# Dossier — MD_SI_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** $SI size: Win10=116B (0x74); Win11=124B (0x7C). RefsMapStandardInfo validates minimum size. NOT backward-compatible

**Canonical claim (reference_table.csv):** Metadata: $SI size: Win10=116B (0x74); Win11=124B (0x7C). RefsMapStandardInfo validates minimum size. NOT backward-compatible

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — type-0x10 own-row value lengths: v3.4 = uniformly 640B; v3.14 = variable 456..>528B (depends on embedded sub-record chain length). The value includes a 0x28 row header + $SI + embedded sub-records, so the raw vlen does NOT directly equal the 116/124-byte $SI size. The $SI itself spans value+0x28 to +0x28+0x74 (Win10=116) or +0x28+0x7C (Win11=124).

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsMapStandardInfo__decomp.txt
- Static driver evidence: RefsMapStandardInfo validates $SI size 0x74 (v3.4) / 0x7C (v3.14). The row value holds more than $SI so the size is not the value length; proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/MD_SI_SA_001.csv`
- corrected registry note: Would need attribute-level parser to verify from raw disk

## Proof links
- `proofs/static/RefsMapStandardInfo__decomp.txt` (static) — RefsMapStandardInfo
- `proofs/validation/MD_SI_SA_001.csv` (matrix) — 
