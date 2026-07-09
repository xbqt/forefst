# Dossier — MD_SI_RA_012 (ABSENCE)

**Claim (this audit tests):** ExternalFileObjectId ($SI+0x74 v3.7+): Only 1 non-zero entry across 525K entries (0xF000 on testads.txt in win11refs2tsnapshots). Effectively unused.

**Canonical claim (reference_table.csv):** Metadata: ExternalFileObjectId ($SI+0x74 v3.7+): Only 1 non-zero entry across 525K entries (0xF000 on testads.txt in win11refs2tsnapshots). Effectively unused.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — ExternalFileObjectId ($SI+0x74, val+0x9C, v3.7+): 0 nonzero across all type-0x10 own-rows on all v3.14 images (extfobj74_nz total = 0). Effectively unused.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 97/97 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $SI+0x74 (v3.7+ next_stream_set_id / 'ExternalFileObjectId'). Only 1 non-zero entry across the whole corpus; per image <=1. Byte-verified 0 on all sampled rows.

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_SI_RA_012.csv`
- corrected registry note: 1/525165 non-zero across 111 images.

## Proof links
- `proofs/validation/MD_SI_RA_012.csv` (matrix) — 
