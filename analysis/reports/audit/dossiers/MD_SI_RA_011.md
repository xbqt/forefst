# Dossier — MD_SI_RA_011 (ABSENCE)

**Claim (this audit tests):** PackedEaSize transition at v3.10 confirmed: v3.4-v3.9 max=12 (SYMLINK & 0xFFFF). v3.10+ max=209 (EA sizes). V4 invariant (ReparseTagLow16 == Tag & 0xFFFF): 0 violations on v3.4-v3.9.

**Canonical claim (reference_table.csv):** Metadata: PackedEaSize transition at v3.10 confirmed: v3.4-v3.9 max=12 (SYMLINK & 0xFFFF). v3.10+ max=209 (EA sizes). V4 invariant (ReparseTagLow16 == Tag & 0xFFFF): 0 violations on v3.4-v3.9.

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — $SI+0x50 (val+0x78): pre-3.10 images = all 0 (max 0, <=12, vacuously satisfies the v3.4-3.9 bound; corpus has NO reparse/symlink on pre-3.10 own-rows so the ReparseTagLow16 upper value and the V4 invariant ReparseTagLow16==Tag&0xFFFF cannot be exercised). v3.10+ = PackedEaSize up to 45 on own-rows (attribute-test images); reference cites 209 on EA-heavy resident entries.

**Original audit verdict:** INFERRED (disk held 16/16 at audit time) · **Registry status:** INFERRED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $SI+0x50 PackedEaSize. On v3.4-v3.9 the max observed is 12 (SYMLINK); the larger EA values appear from v3.10. Probe asserts <=12 on v3.4-v3.9.

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_SI_RA_011.csv`
- corrected registry note: v3.4: 187 non-zero (max 12). v3.7: 116 (max 12). v3.9: 242 (max 12). v3.10: 0. v3.14: 3991 (max 209). | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Offset confirmed; field is small. The semantic transition (v3.4-3.9 ReparseTagLow16 vs v3.10+ PackedEaSize) and the V4 invariant are E2-grounded and not disk-verifiable on the pre-3.10 side (UNCONFIRMABLE there - no pre-3.10 repar

## Proof links
- `proofs/validation/MD_SI_RA_011.csv` (matrix) — 
