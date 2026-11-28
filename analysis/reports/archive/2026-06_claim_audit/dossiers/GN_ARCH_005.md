# Dossier — GN_ARCH_005 (BEHAVIORAL)

**Claim (this audit tests):** Pages (1-4 clusters) with header: signature+clock+address

**Canonical claim (reference_table.csv):** General: Pages (1-4 clusters) with header: signature+clock+address

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Every metadata page (SUPB/CHKP/MSB+) carries the A.2 header: signature@0x00 (MSB+/CHKP/SUPB), hdr-version u32@0x04==2, virtual/tree clock u64@0x10 and @0x18, self-address (LCN slots) @0x20. MSB+ self-LCN slot0 == the page's own VLCN (e.g. 0x100f4) with consecutive slots for multi-cluster pages. Verified across 3376 metadata pages on the corpus.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Architecture] Pages (1-4 clusters) with header: signature+clock+address — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_ARCH_005.csv`
- corrected registry note: All 5 signatures observed in raw disk data: FSRS(VBR), SUPB(superblock), CHKP(checkpoint), MSB+(B+tree), MLog(log)

## Proof links
- `proofs/validation/GN_ARCH_005.csv` (matrix) — 
