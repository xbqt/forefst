# Dossier — GN_PAGE_006 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0x20-0x40: page address LCN quadruple

**Canonical claim (reference_table.csv):** General: 0x20-0x40: page address LCN quadruple

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — page+0x20-0x40 = 4x u64 LCN quadruple. On 4K (page=4 clusters): slots = [self, self+1, self+2, self+3] verified on 106/106 4K images (every MSB+ page: lcn_seq==msb_n). On 64K (page=1 cluster): slot0=self (lcn0_self high, e.g. 267/395, 1027/1221), slots1-3 not sequential because page is single-cluster — the [LCN,LCN,0,0] / single-LCN form. SUPB/CHKP slots1-3 = 0 on 111/111.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- structure_reference.md:106 page header 0x20 = primary cluster LCN of this page. Byte-verified: OT-root header+0x20 == its virtual root LCN (the address it is referenced by), NOT the physical LCN.

## Raw-disk proof
- probe `page_consistency` ; validation matrix: `proofs/validation/GN_PAGE_006.csv`
- corrected registry note: LCN quadruples observed in all page headers; up to 4 LCNs for multi-cluster pages

## Proof links
- `proofs/validation/GN_PAGE_006.csv` (matrix) — 
