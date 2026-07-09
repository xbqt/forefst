# Dossier — GN_PAGE_007 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x40-0x50: table identifier (high+low)

**Canonical claim (reference_table.csv):** General: 0x40-0x50: table identifier (high+low)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-STATIC** — STATIC-RESOLVED 2026-06-18: FormatPageHeaderInternal writes page+0x40=TableIdHigh(id+0x178, always 0), page+0x48=TableIdLow(id+0x180, the numeric table OID, compared ==5/==6/1-4); 16-byte OID key. Original '0x40-0x50 high+low' CONFIRMED. RD: 0x40==0 on 137,444/137,444 pages. (The earlier 'page+0x40 reserved' re-measure was the over-correction; the doc 'Schema' label was the only error.)

**Original audit verdict:** CONFIRMED (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- structure_reference.md:110-111 page header 0x40 = Table OID high + Schema low, 0x48 = Table identifier low. On the OT-root MSB+ page +0x40 = 0 (byte-verified); the table id (0x02) sits at +0x48 (covered by GN_PAGE_RA_002). This probe verifies the +0x40 high word.

## Raw-disk proof
- probe `page_const` ; validation matrix: `proofs/validation/GN_PAGE_007.csv`
- corrected registry note: RE-MEASURED ALL-DISK 2026-06-18: page+0x40==0 on 137,444/137,444 MSB+ pages (all versions/cluster sizes + SUPB/CHKP); numeric table OID at 0x48. The '0x40-0x50 = table identifier high+low' framing is CONFIRMED (16-byte OID); the earlier 'low=schema type' note was wrong. Resolves the NEEDS-STATIC hold. See structure_reference A.2.

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/GN_PAGE_007.csv` (matrix) — 
