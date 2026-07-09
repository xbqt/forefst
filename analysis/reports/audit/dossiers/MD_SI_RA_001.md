# Dossier — MD_SI_RA_001 (STRUCTURAL)

**Claim (this audit tests):** E21: $SI field corrections — ReparseTag at +0x54 (not 0x4C), HardLinkCount at +0x70 (not 0x48), +0x48 is conditional u64, +0x50 is u16-derived u32. Five corrections from RefsComputeStandardInformationFromFcb decompilation.

**Canonical claim (reference_table.csv):** Metadata: E21: $SI field corrections — ReparseTag at +0x54 (not 0x4C), HardLinkCount at +0x70 (not 0x48), +0x48 is conditional u64, +0x50 is u16-derived u32. Five corrections from RefsComputeStandardInformationFromFcb decompilation.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — $SI base inside a type-0x10 own-row value is at value+0x28 (0x28-byte row header: size@0x00, si_off=0x28@0x04). With that base, the corrected offsets hold on all 113 images: ReparseTag@$SI+0x54 (val+0x7C), HardLinkCount@$SI+0x70 (val+0x98) is u32 ={0,1}, $SI+0x50 is a small u32, $SI+0x48 (UJID) is conditional u64. Probed raw bytes on v3.4 (win10refsmini) and v3.14 (win11refs2gtargeted) confirm field positions.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- E21: ReparseTag is at $SI+0x54 (not 0x4C). Verified: every $SI row's +0x54 is 0 or a valid reparse tag (bit 31 set; WSL tags 0xA000xxxx observed on the attributes image).

## Raw-disk proof
- probe `si_field` ; validation matrix: `proofs/validation/MD_SI_RA_001.csv`
- corrected registry note: 525K entries / 111 images: +0x54 correct for symlinks. +0x70 always 0 or 1. CORRECTION: the prior "confirmed cross-directory hard links" (87/41 multi-parent OIDs) were a parser artifact — non-resident type-0x30 value[0x08] is the home-directory OID back-reference (shared by siblings), not a child OID. $SI+0x70 is the resident-layout HLC (always 0/1) and is NOT the multi-name counter. The pre-step6 corpus had no genuine hard links, but they DO exist (non-resident type-0x30 mechanism) and were since observed on win11refs2gtargeted (FN_LINK_002/#340)

## Proof links
- `proofs/validation/MD_SI_RA_001.csv` (matrix) — 
