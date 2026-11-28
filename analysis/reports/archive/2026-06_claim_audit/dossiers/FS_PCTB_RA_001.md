# Dossier — FS_PCTB_RA_001 (BEHAVIORAL)

**Claim (this audit tests):** Deep row structure: Key=32B [u64 zero, u64 ParentOID, u64 zero, u64 ChildOID]. Value overlaps key (key_offset==val_offset key_length==val_length). Pure set/index with no payload data; 48-byte rows. Only directories tracked; no multi-parent entries across 31392 entries on 76 images. Schema 0xe040 u32[7]=0x08 = key-comparison-rules selector (8 -> CmsRulesPARENT_CHILD_LINK; NOT a bitfield, E50); value-overlaps-key is a caller-side same-buffer construction (AddParentChildLink), not a schema flag. Format version-invariant v3.4-v3.14

**Canonical claim (reference_table.csv):** File System: Deep row structure: Key=32B [u64 zero, u64 ParentOID, u64 zero, u64 ChildOID]. Value overlaps key (key_offset==val_offset key_length==val_length). Pure set/index with no payload data; 48-byte rows. Only directories tracked; no multi-parent entries across 31392 entries on 76 images. Schema 0xe040 u32[7]=0x08 = key-comparison-rules selector (8 -> CmsRulesPARENT_CHILD_LINK; NOT a bitfield, E50); value-overlaps-key is a caller-side same-buffer construction (AddParentChildLink), not a schema flag. Format version-invariant v3.4-v3.14

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Parent-Child Table] Deep row structure: Key=32B [u64 zero, u64 ParentOID, u64 zero, u64 ChildOID]. Value overlaps key (key_offset= — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_PCTB_RA_001.csv`
- corrected registry note: See ra_step4_25_parent_child_table_report.md | CORRECTED 2026-06-19 (E50): u32[7]=0x08 confirmed unique to 0xe040; value-overlaps-key 238/238 PCT rows, 0 on all other tables. Bit-3 hypothesis REFUTED on disk: schema 0x130 (u32[7]=0x9, bit3 set) tables do NOT overlap. u32[7] is a key-rules enum, not a bitfield. See pct_schema_u32_7_2026-06-19.md.

## Proof links
- `proofs/validation/FS_PCTB_RA_001.csv` (matrix) — 
