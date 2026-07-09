# Dossier — MD_DEL_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Explorer deletion: $R entry is non-resident with target_oid pointing to source directory. $I entry (544 bytes) contains original path + deletion timestamp.

**Canonical claim (reference_table.csv):** Metadata: Explorer deletion: $R entry is non-resident with target_oid pointing to source directory. $I entry (544 bytes) contains original path + deletion timestamp.

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — $R entry: confirmed NON-RESIDENT (value len 84B, key_flags 0x02, home backref to a real source-dir OID e.g. 0x707) on 8 images. $I entry: the $I file's $DATA content is NOT 544 bytes - measured sizes are 102 / 62 / 70 / 188 bytes across images (variable). The $I content holds the original path + a FILETIME deletion timestamp (e.g. 'R:\test\filetodeletewithexplorer.txt' + FILETIME). The resident $I directory-entry value is 416 bytes (still not 544).

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (recycle). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DEL_RA_002.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 5.2 | RE-VERIFIED 2026-06-18 (all-disk): claimed '$I entry (544 bytes)'; disk shows $I $DATA content is 62-188 bytes (variable, holds the path) - the 544 figure is the fixed NTFS $I size, not the ReFS reality. The 'contains original path + deletion timestamp' and '$R non-resident'

## Proof links
- `proofs/validation/MD_DEL_RA_002.csv` (matrix) — 
