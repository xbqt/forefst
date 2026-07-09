# Dossier — MD_ATTR_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Complete attribute values catalog: 0x10 (dir), 0x16 (hidden+system+dir), 0x20 (archive), 0x220 (sparse+archive), 0x420 (reparse+archive), 0x4020 (encrypted+archive), 0x10000400 (dir+reparse ext).

**Canonical claim (reference_table.csv):** Metadata: Complete attribute values catalog: 0x10 (dir), 0x16 (hidden+system+dir), 0x20 (archive), 0x220 (sparse+archive), 0x420 (reparse+archive), 0x4020 (encrypted+archive), 0x10000400 (dir+reparse ext).

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — FileAttributes at dirent value+0x40 across all images. CONFIRMED: 0x20(archive)=66067, 0x220(sparse+arch)=1, 0x420(reparse+arch)=2047, 0x4020(enc+arch)=12, 0x10000400(dir+reparse)=8. CONTRADICTED: 0x10(dir) count=0 and 0x16(hidden+system+dir) count=0 - ReFS uses the EXTENDED directory bit 0x10000000, never Win32 0x10; on disk 'hidden+system+dir' is 0x10000006, not 0x16.

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- FileAttributes ($SI+0x20) value catalog; the dir bit 0x10000000 disk-proven (MD_SI_RA_004). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_001.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 12.1 | RE-VERIFIED 2026-06-18 (all-disk): claimed catalog includes 0x10 (dir) and 0x16 (hidden+system+dir); disk shows 0 occurrences of either - directories carry 0x10000000 (the errata 'dir bit is 0x10000000 not 0x10' pitfall). The other 5 catalog values are present.

## Proof links
- `proofs/validation/MD_ATTR_RA_001.csv` (matrix) — 
