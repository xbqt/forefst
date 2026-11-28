# Dossier — GN_PAGE_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Page header LCN tuple (0x20-0x38): MSB+ pages store 4 consecutive cluster LCNs (self self+1 self+2 self+3) for their 4-cluster extent. SUPB and CHKP use only slot 0 (self-block); slots 1-3 are zero. This is because SUPB is fixed at LCN 30 and CHKP locations are stored in SUPB checkpoint references.

**Canonical claim (reference_table.csv):** General: Page header LCN tuple (0x20-0x38): MSB+ pages store 4 consecutive cluster LCNs (self self+1 self+2 self+3) for their 4-cluster extent. SUPB and CHKP use only slot 0 (self-block); slots 1-3 are zero. This is because SUPB is fixed at LCN 30 and CHKP locations are stored in SUPB checkpoint references.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — 4K MSB+ pages: LCN tuple slots[1,2,3] == self+1,+2,+3 on 106/106 4K images (every page). SUPB/CHKP slots1-3 == 0 on 111/111. (On 64K the page is 1 cluster so the +1/+2/+3 extension does not apply — claim is implicitly 4K-page-scoped.)

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 107/107 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- structure_reference.md:106-109 page header 0x20-0x38 = 4 LCN slots (self-block + 3). Byte-verified on OT-root: slots = [self, self+1, self+2, self+3] (a 16 KiB page = 4 consecutive 4 KiB clusters). SCOPED to 4K clusters: at 64 KiB clusters a page is a single 64 KiB cluster, so only slot 0 is populated (slots 1-3 = 0) — the 5 64K images correctly fall outside applicability.

## Raw-disk proof
- probe `page_consistency` ; validation matrix: `proofs/validation/GN_PAGE_RA_001.csv`
- corrected registry note: Verified on 13 MSB+ root table pages from Win11 4K image: all have LCN[1]=Self+1 LCN[2]=Self+2 LCN[3]=Self+3. SUPB/CHKP confirmed zero at slots 1-3. See ra_step4_12_deep_structure_report.md

## Proof links
- `proofs/validation/GN_PAGE_RA_001.csv` (matrix) — 
