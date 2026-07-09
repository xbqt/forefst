# Dossier — MD_LK_RA_009 (ABSENCE)

**Claim (this audit tests):** v3.7+ $OBJ_LINK (type 0x39): NO common header. val[0:4]=marker 0x80000002, val[8:12]=parent_oid, val[24:]=filename. Timestamps removed vs v3.4. 26560 entries on Insider.

**Canonical claim (reference_table.csv):** Metadata: v3.7+ $OBJ_LINK (type 0x39): NO common header. val[0:4]=marker 0x80000002, val[8:12]=parent_oid, val[24:]=filename. Timestamps removed vs v3.4. 26560 entries on Insider.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — v3.7+ 0x39 'no common header' confirmed: val[0:4]=0x80000002 (32204/32204), parent_oid at val[8:12]=le32@0x08 (32204/32204 in map), filename at val[24:]=val[0x18:] (32204/32204 decode). No 12-byte timestamp header present (the 0x38 0c000100 signature never appears in 0x39 values). Decodes correctly on the Insider image (wininsiderrefs2t/winsider) and all v3.7+ images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ObjLink v3.7+ structure. Feature-gated (no obj-links on the corpus volumes); cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_LK_RA_009.csv`
- corrected registry note: 26560 entries. All decode correctly with parent OIDs matching directory tree.

## Proof links
- `proofs/validation/MD_LK_RA_009.csv` (matrix) — 
