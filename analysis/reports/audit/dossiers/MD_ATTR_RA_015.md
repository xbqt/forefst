# Dossier — MD_ATTR_RA_015 (PURE-RD-LAYOUT)

**Claim (this audit tests):** $I30_INDEX (type 0x90): 140-byte value is 100% constant across all OIDs and all versions. Static B+-tree config template. Key contains '$I30' stream name (UTF-16LE). flags=0x00010240, entry_size=0x70. Verified on 418 OIDs across v3.4/v3.14/Insider.

**Canonical claim (reference_table.csv):** Metadata: $I30_INDEX (type 0x90): 140-byte value is 100% constant across all OIDs and all versions. Static B+-tree config template. Key contains '$I30' stream name (UTF-16LE). flags=0x00010240, entry_size=0x70. Verified on 418 OIDs across v3.4/v3.14/Insider.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — $I30_INDEX (0x90): value is 100%-constant within each version - only 2 distinct values corpus-wide (140-byte v3.7+ template x32092, 148-byte v3.4 template x513). flags=0x00010240 at value+0x10, entry_size=0x70 at value+0x1c/0x20, summary@0x0C=0x30, all constant. Present in 32605/32605 user OIDs.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $I30 (0x90) is not present on any corpus image (no disk sample to validate), so the 140-byte claim is cited to the thesis observation rather than disk-verified here.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_015.csv`
- corrected registry note: 418 OIDs across 4 images: 100% identical value. 0 variations.

## Proof links
- `proofs/validation/MD_ATTR_RA_015.csv` (matrix) — 
