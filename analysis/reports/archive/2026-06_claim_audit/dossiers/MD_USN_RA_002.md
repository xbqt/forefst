# Dossier — MD_USN_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 128-bit File ID structure: upper 8 bytes = table OID, lower 8 bytes = entry index. Enables direct mapping from USN record to B+-tree location.

**Canonical claim (reference_table.csv):** Metadata: 128-bit File ID structure: upper 8 bytes = table OID, lower 8 bytes = entry index. Enables direct mapping from USN record to B+-tree location.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — 128-bit File ID @+0x08 (16B): lower8@+0x08 = entry index, upper8@+0x10 = table OID. Upper8 resolves to a known directory OID in the object map far more than lower8: 6041/6481, 6699/6874, 6805 etc. for upper8 vs 651/1239 for lower8 (winsider/attributestest2). Small upper8 values (0x600,0x707,0x779,0x7ab) are directory OIDs.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- USN FileId structure. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_USN_RA_002.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 3.2

## Proof links
- `proofs/validation/MD_USN_RA_002.csv` (matrix) — 
