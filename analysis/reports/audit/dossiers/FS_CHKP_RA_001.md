# Dossier — FS_CHKP_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** CHKP flags (0x78-0x7B) full decomposition: bit 0x002=always set, bit 0x080=native Win11 format (format-time only), bit 0x200=indirect root list mode, bit 0x400=CRC64 metadata checksumming, bits 0x010+0x020+0x100=dedup-specific. 4 observed composite values: 0x002(Win10), 0x602(upgraded), 0x682(native Win11), 0x7b2(Win11+dedup)

**Canonical claim (reference_table.csv):** File System: CHKP flags (0x78-0x7B) full decomposition: bit 0x002=always set, bit 0x080=native Win11 format (format-time only), bit 0x200=indirect root list mode, bit 0x400=CRC64 metadata checksumming, bits 0x010+0x020+0x100=dedup-specific. 4 observed composite values: 0x002(Win10), 0x602(upgraded), 0x682(native Win11), 0x7b2(Win11+dedup)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CHKP+0x78 flags: bit 0x002 set on 48/48 (every copy). Observed composites 0x682(30),0x002(11),0x2682(3),0x7b2(2),0x602(1),0x082(1) — all match documented A.4a set. Bit 0x080 present iff native(not upgraded), 0x200/0x400 present on v3.14.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- ValidateCheckpointRecord checks CHKP+0x78 for 0x2. Byte-verified: 0x002 & 0x002 and 0x682 & 0x002 both set. Probe asserts bit 0x002 present.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_CHKP_RA_001.csv`
- corrected registry note: Flags 0x682 for native Win11 vs 0x602 for upgraded Win10. 0x7b2 for dedup volumes. Bit 0x080 absent on upgraded volumes = format-time flag for native 3.14. Bit 0x200 controls root pointer parsing mode (direct vs indirect). Bit 0x400 correlates with CRC64 metadata checksumming (from ValidateCheckpointRecord SA). Bits 0x010/0x020/0x100 appear only on dedup-enabled volumes. See report_checkpoint_deep_analysis.md

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_RA_001.csv` (matrix) — 
