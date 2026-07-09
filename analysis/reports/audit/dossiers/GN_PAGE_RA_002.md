# Dossier — GN_PAGE_RA_002 (STRUCTURAL)

**Claim (this audit tests):** Page header Table OID (0x48): MSB+ pages store the Object ID of their owning table (e.g. 0x02=Object ID Table 0x0B=Container Table 0x22=Small Allocator). Enables identification of orphaned CoW-discarded pages. SUPB and CHKP have Table OID = 0.

**Canonical claim (reference_table.csv):** General: Page header Table OID (0x48): MSB+ pages store the Object ID of their owning table (e.g. 0x02=Object ID Table 0x0B=Container Table 0x22=Small Allocator). Enables identification of orphaned CoW-discarded pages. SUPB and CHKP have Table OID = 0.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — page+0x48 (Table OID): holds the owning-table OID on 34,046/34,046 live MSB+ pages across 111 images (observed OIDs 0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9,0xa,0xb,0xc,0xd,0x22,0x500,0x520,0x530,0x540,0x600,0x70x...). SUPB/CHKP Table OID == 0 on 111/111. page+0x40 is always 0.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- structure_reference.md:111 page header 0x48 = 'Table identifier (low)'. GN_PAGE_RA_002 asserts MSB+ pages store the owning table's Object ID at 0x48. Verified on the Object-ID-Table root (root 0): +0x48 = 0x02. Corroborated by all 13 root pages (FS_CHKP_009-021 matrices), where +0x48 == each table's ID.

## Raw-disk proof
- probe `chkp_root_table` ; validation matrix: `proofs/validation/GN_PAGE_RA_002.csv`
- corrected registry note: Verified on 13 root table MSB+ pages: Table OID matches expected table identity. OID values observed: 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x22. See ra_step4_12_deep_structure_report.md

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/GN_PAGE_RA_002.csv` (matrix) — 
