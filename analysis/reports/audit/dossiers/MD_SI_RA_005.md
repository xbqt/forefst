# Dossier — MD_SI_RA_005 (ABSENCE)

**Claim (this audit tests):** InternalFlags ($SI+0x24) transition: zero on ALL v3.4/v3.7/v3.9/v3.10 images (0/18). Non-zero on ALL v3.14 images (90/90, 368380 entries). Transition at v3.14, not v3.10 as E25 conservative estimate.

**Canonical claim (reference_table.csv):** Metadata: InternalFlags ($SI+0x24) transition: zero on ALL v3.4/v3.7/v3.9/v3.10 images (0/18). Non-zero on ALL v3.14 images (90/90, 368380 entries). Transition at v3.14, not v3.10 as E25 conservative estimate.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — InternalFlags @+0x4C (=$SI+0x24): on resident type-0x30 index entries = 0/5513 across 18 pre-3.14 images (v3.4/3.7/3.9/3.10), and 367338/404001 nonzero across 95 v3.14+ images with EVERY v3.14 image having res_nz>0 (0 images with res_n>0 and res_nz==0). On type-0x10 own-rows the only nonzero is 0x20 (reparse-trust) = 78 on winsider = exactly the 78 reparse points.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 18/18 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $SI+0x24 InternalFlags. Byte-verified 0 on v3.4-v3.10 (the field is populated only from v3.14, gated by FCB bits). Applicability version<=3.10.

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_SI_RA_005.csv`
- corrected registry note: 111 images / 525165 entries: zero on v3.4-v3.10 (8389 entries), non-zero on v3.14 (368380). Bits 4-5 via callers.

## Proof links
- `proofs/validation/MD_SI_RA_005.csv` (matrix) — 
