# Dossier — MD_USN_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** USN Journal version 3 record format on ReFS with 128-bit File IDs. Record lengths range from 96 to 168 bytes depending on file name length.

**Canonical claim (reference_table.csv):** Metadata: USN Journal version 3 record format on ReFS with 128-bit File IDs. Record lengths range from 96 to 168 bytes depending on file name length.

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — USN v3 records on 9 USN-active v3.14 images: major u16@+0x04==3, minor u16@+0x06==0 (100%). recordlen@+0x00 == pad8(0x4C + name_byte_len) on 100% of records. Measured length range = 80..312 B (winsider), 88..184 (attributestest2), 80..152, 88..144 — i.e. MIN 80 (0x50), MAX 312.

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- USN v3 format (forefst cmd_usn parses it). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_USN_RA_001.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 3.1 | RE-VERIFIED 2026-06-18 (all-disk): claimed 'Record lengths range from 96 to 168 bytes'; disk shows 80..312 across the corpus. The 96-168 window is both too high a floor (driver min is 0x50=80) and too low a ceiling (312 observed). structure_reference §C.13 already CORRECTED 

## Proof links
- `proofs/validation/MD_USN_RA_001.csv` (matrix) — 
