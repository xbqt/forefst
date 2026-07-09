# Dossier — MD_ATTR_RA_007 (STRUCTURAL)

**Claim (this audit tests):** Embedded B+-tree key/value overlap: key[0:8] = le64(value_length), key[8:] = value[0:]. Row offset table at end of value: pairs of [le16 offset][0xFFFF]. Same format used in type 0x10 and resident type 0x30 values.

**Canonical claim (reference_table.csv):** Metadata: Embedded B+-tree key/value overlap: key[0:8] = le64(value_length), key[8:] = value[0:]. Row offset table at end of value: pairs of [le16 offset][0xFFFF]. Same format used in type 0x10 and resident type 0x30 values.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Embedded key/value overlap key[0:8]==le64(value_length): 65306/65306 (100%) across all type-0x10 and resident type-0x30 embedded rows on 107 images. Row offset table at end of value confirmed as [le16 offset][0xFFFF] pairs (parse_resident_btree_rows succeeds on 100%).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Embedded-tree key/value structure. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_007.csv`
- corrected registry note: Cross-verified across 32721 type 0x10 entries: key[0:8] as le64 matches value length in 100% of parsed rows.

## Proof links
- `proofs/validation/MD_ATTR_RA_007.csv` (matrix) — 
