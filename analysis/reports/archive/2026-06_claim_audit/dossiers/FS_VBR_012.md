# Dossier — FS_VBR_012 (STRUCTURAL)

**Claim (this audit tests):** 0x2A-0x37: 14 bytes unknown in Nordvik/Prade. 0x2A=checksum algo selector, 0x2B=reserved, 0x2C-0x2F=volume flags (0x06 Win10 / 0x66 Win11), 0x30-0x37=reserved

**Canonical claim (reference_table.csv):** File System: 0x2A-0x37: 14 bytes unknown in Nordvik/Prade. 0x2A=checksum algo selector, 0x2B=reserved, 0x2C-0x2F=volume flags (0x06 Win10 / 0x66 Win11), 0x30-0x37=reserved

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — Offsets confirmed: 0x2B==0 on 113/113 (reserved), 0x30-0x37==0000000000000000 on 113/113 (reserved). BUT the parenthetical flag characterization '0x06 Win10 / 0x66 Win11' is incomplete: 0x2C distribution = {0x06:15(v3.4 + upgraded), 0x66:90, 0x26:4(v3.7/v3.9 + upgraded), 0x04:1(fixboot), 0x63:2, 0x6666:1 (the last three are 'afterchangingvolumeflags' test images)}.

**Original audit verdict:** CONTRADICTED (disk held 112/112 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- structure_reference.md:25 VBR 0x2A = checksum algorithm selector. Byte-verified values 0 (v3.4 none), 2 (CRC64), 4 (SHA256). Probe asserts the selector is a known enum.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_VBR_012.csv`
- corrected registry note: 0x2A confirmed as checksum algorithm selector: 0=None(3.4), 2=CRC64(default 3.14), 4=SHA256. Immutable on upgrade: Win10-formatted volumes always 0=None even after 3.14 upgrade. Volume flags at 0x2C: Win10=0x06 (bits 0x02+0x04) vs Win11=0x66 (bits 0x02+0x04+0x20+0x40). Bit 0x02=mount marker (set by driver on first mount, RefsMountVolume decompiled). Bit 0x04=always present on valid ReFS. Bit 0x10=recovery/dirty (decompiled but never observed). Bit 0x20=Win11 format-time boot behavior. Bit 0x40=gates VBR 0x2A checksum algo (insider: 'used only if flags bit 6 set'). 0x30-0x37 always zero (reserved). See report_boot_sector_deep_analysis.md | RE-VERIFIED 2026-06-18 (all-disk): claimed flags are 0x06(Win10)/0x66(Win11); disk shows 0x26 is the genuine v3.7/v3.9 value (already documented in structure_reference Subtable A.1c), so the two-value summary in FS_VBR_012 is wrong/incomplete.

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_012.csv` (matrix) — 
