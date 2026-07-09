# Dossier — MD_SI_RA_009 (ABSENCE)

**Claim (this audit tests):** HardLinkCount ($SI+0x70) >1: ZERO across 525165 entries / 111 images because $SI+0x70 is a RESIDENT-LAYOUT field always 0/1 — it is NOT the multi-name counter. Genuine hard links use the non-resident type-0x30 mechanism (FN_LINK_002/#340), observed on win11refs2gtargeted. Values: 0 (1004 special entries) or 1 (524161 regular entries).

**Canonical claim (reference_table.csv):** Metadata: HardLinkCount ($SI+0x70) >1: ZERO across 525165 entries / 111 images because $SI+0x70 is a RESIDENT-LAYOUT field always 0/1 — it is NOT the multi-name counter. Genuine hard links use the non-resident type-0x30 mechanism (FN_LINK_002/#340), observed on win11refs2gtargeted. Values: 0 (1004 special entries) or 1 (524161 regular entries).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — HardLinkCount ($SI+0x70, u32 at val+0x98) value distribution across all 113 images = {1: 32629}; >1 count = 0/32629. Includes win11refs2gtargeted (real hard links) and the timestamps/hardlink test images. Never >1.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ABSENCE/aggregate: the max plausible $SI+0x70 across all user objects is <=1 because it is a RESIDENT-layout field, not the hard-link counter. Genuine hard links use the non-resident type-0x30 mechanism (FN_LINK_002/#340, observed on win11refs2gtargeted); implausible (>=256) reads are field-overlap, discarded and counted.

## Raw-disk proof
- probe `hlc_max` ; validation matrix: `proofs/validation/MD_SI_RA_009.csv`
- corrected registry note: 111 images, 525165 entries: 0 with HLC>1. Distribution: 0=1004, 1=524161.

## Proof links
- `proofs/validation/MD_SI_RA_009.csv` (matrix) — 
