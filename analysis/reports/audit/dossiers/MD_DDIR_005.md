# Dossier — MD_DDIR_005 (BEHAVIORAL)

**Claim (this audit tests):** Flags

**Canonical claim (reference_table.csv):** Metadata: Flags

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- FileAttributes@$SI+0x20; the directory bit 0x10000000 is disk-proven in MD_SI_RA_004. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DDIR_005.csv`
- corrected registry note: Directory flag is 0x10000000 (bit 28) not 0x10 as in Win32. Discovered via Bug #4 during tool development. Confirmed across all 39 images. Non-standard encoding specific to ReFS internal representation. Merged from MD_DDIR_RA_001

## Proof links
- `proofs/validation/MD_DDIR_005.csv` (matrix) — 
