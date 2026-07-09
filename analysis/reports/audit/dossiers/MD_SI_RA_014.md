# Dossier — MD_SI_RA_014 (BEHAVIORAL)

**Claim (this audit tests):** InternalFlags ($SI+0x24) bit5 (0x20) = symlink/junction REDIRECTION-TRUST level (FCB[0xf4] bit1 from IoComputeRedirectionTrustLevel), NOT "HardLinkCount drops to 0". Written only in RefsSetReparsePointInternal for tags 0xa000000c/0xa0000003. The HLC-zero path (RefsConvertToStandardInfoLinkCount) ORs bit2 (0x04), never 0x20.

**Canonical claim (reference_table.csv):** Metadata: InternalFlags ($SI+0x24) bit5 (0x20) = symlink/junction REDIRECTION-TRUST level (FCB[0xf4] bit1 from IoComputeRedirectionTrustLevel), NOT "HardLinkCount drops to 0". Written only in RefsSetReparsePointInternal for tags 0xa000000c/0xa0000003. The HLC-zero path (RefsConvertToStandardInfoLinkCount) ORs bit2 (0x04), never 0x20.

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — InternalFlags bit5 (0x20) appears on type-0x10 own-rows: count = 78 on winsider.raw = exactly the 78 reparse points (0x20 is the only nonzero own-row iflags value observed). Consistent with bit5=symlink/junction redirection-trust.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- E2: InternalFlags bit5 marks symlink/junction redirection. Semantic bit-mapping; cited (the field zero-ness is disk-proven in MD_SI_RA_005).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SI_RA_014.csv`
- corrected registry note: winsider file_own internal_flags=0x20 count = 78 = EXACTLY the 78 reparse points (46 junctions + 32 symlinks). Across 47 v3.14+ images with bit5 set, all 47 have a symlink/junction; 0 counterexamples. | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): The 'redirection-trust level (FCB[0xf4] bit1 from IoComputeRedirectionTrustLevel)' semantic is static/E2-only. Disk confirms the 78=78 reparse-point correlation but the bit's exact FCB source is not disk-derivable.

## Proof links
- `proofs/validation/MD_SI_RA_014.csv` (matrix) — 
