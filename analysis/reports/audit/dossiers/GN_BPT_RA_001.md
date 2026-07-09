# Dossier — GN_BPT_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** B+-tree row header is 16 bytes (not 14 as Prade documents). Extra u16 padding at 0x0E for 8-byte alignment

**Canonical claim (reference_table.csv):** General: B+-tree row header is 16 bytes (not 14 as Prade documents). Extra u16 padding at 0x0E for 8-byte alignment

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [B+-tree] B+-tree row header is 16 bytes (not 14 as Prade documents). Extra u16 padding at 0x0E for 8-byte alignment — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_BPT_RA_001.csv`
- corrected registry note: Matches ARIN tool ROW_HDR_3FORMAT '<I6H' = 16 bytes. Prade describes 7 fields totaling 14 bytes but omits alignment padding

## Proof links
- `proofs/validation/GN_BPT_RA_001.csv` (matrix) — 
