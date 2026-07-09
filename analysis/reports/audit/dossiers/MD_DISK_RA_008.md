# Dossier — MD_DISK_RA_008 (PURE-RD-LAYOUT)

**Claim (this audit tests):** $RECYCLE.BIN on disk: $R entry target_oid=0x7B1 links to source directory. $I metadata file (188 bytes resident) contains original path and deletion timestamp.

**Canonical claim (reference_table.csv):** Metadata: $RECYCLE.BIN on disk: $R entry target_oid=0x7B1 links to source directory. $I metadata file (188 bytes resident) contains original path and deletion timestamp.

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — $RECYCLE.BIN present (OID 0x600 child, parent 1536). $R<id>.txt entry value+0x08 = target_oid linking to source dir (0x7b1 on win11refs4gattributestest2; 0x707 on lasttests). $I<id>.txt is resident with file_size@0x58 = 188 B (attributestest2) / 102 B (lasttests).

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (recycle linkage). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DISK_RA_008.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 9.9 | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NEW): The mechanism is right; 0x7B1 and 188 are per-image samples and must be relabelled as examples.

## Proof links
- `proofs/validation/MD_DISK_RA_008.csv` (matrix) — 
