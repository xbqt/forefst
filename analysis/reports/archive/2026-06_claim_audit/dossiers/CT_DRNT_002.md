# Dossier — CT_DRNT_002 (BEHAVIORAL)

**Claim (this audit tests):** Flags: 0x0010=data, 0x0080=CRC32, 0x0100=CRC64

**Canonical claim (reference_table.csv):** Content: Flags: 0x0010=data, 0x0080=CRC32, 0x0100=CRC64

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — v3.14 strict extent flag census (76,476 entries / 47 images): real flags = 0x180050 (72,706), 0x180040 (3,923), 0x180850 (396), 0x1c00d0 (261), 0x180054 (119), 0x180064 (31). 0x180040 is a genuine data-run extent but has bit 0x10 CLEAR; no high-frequency flag has bit 0x100; 0x1c00d0 (bit 0x80 set) is the integrity checksum-page entry, NOT a CRC32 selector.

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Extent-run flag bits. Detailed format; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_DRNT_002.csv`
- corrected registry note: PT: Extent flags at value[0x00] verified. OID 0x707 on win11refslasttests: flags=0x00A8 | RE-VERIFIED 2026-06-18 (all-disk): claimed 0x0010=data / 0x0080=CRC32 / 0x0100=CRC64; disk shows bit 0x10 is NOT 'data' (0x180040 data run lacks it), bit 0x80 marks the integrity-stride entry (0x1c00d0), and bit 0x100 (CRC64) appears in 0 of all clean extent flags corpus-wid

## Proof links
- `proofs/validation/CT_DRNT_002.csv` (matrix) — 
