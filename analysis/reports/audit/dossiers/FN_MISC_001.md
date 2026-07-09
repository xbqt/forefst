# Dossier — FN_MISC_001 (LITERATURE)

**Claim (this audit tests):** v1.2: 64 KiB entry blocks; v3.2+: different sizes

**Canonical claim (reference_table.csv):** File Name: v1.2: 64 KiB entry blocks; v3.2+: different sizes

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Metadata page (entry block) = 4 clusters on 4K-cluster volumes (MSB+ self-LCN slots consecutive: e.g. 65780/65781/65782/65783 => 16 KiB page) and 1 cluster on 64K-cluster volumes (slot0 only, slots1-3=0 => 64 KiB page). Confirmed on 4K and 64K sample images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NOT_TESTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- LITERATURE (historical versions). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FN_MISC_001.csv`
- corrected registry note: (none)

## Proof links
- `proofs/validation/FN_MISC_001.csv` (matrix) — 
