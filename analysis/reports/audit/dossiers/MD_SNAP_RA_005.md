# Dossier — MD_SNAP_RA_005 (ABSENCE)

**Claim (this audit tests):** E20 RETRACTED: ADS are always resident (inline). 956 ADS across 46 images all have StreamSummary flags=0. 29 snapshot entries have SS flags=2. 28 entries initially misclassified as extent-based ADS were actually snapshots (same 0x000500B0 descriptor). Discriminator: StreamSummary flags (u16) at val[0x10] — 0=ADS, 2=snapshot.

**Canonical claim (reference_table.csv):** Metadata: E20 RETRACTED: ADS are always resident (inline). 956 ADS across 46 images all have StreamSummary flags=0. 29 snapshot entries have SS flags=2. 28 entries initially misclassified as extent-based ADS were actually snapshots (same 0x000500B0 descriptor). Discriminator: StreamSummary flags (u16) at val[0x10] — 0=ADS, 2=snapshot.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — 985 type-0xB0 embedded entries across 47 images: 956 have StreamSummary flags@val[0x10]==0 (ADS) and 29 have flags@val[0x10]==2 (snapshot). Flag-value histogram is exactly {0:956, 2:29} - no other value occurs. Snapshots appear ONLY on v3.14 (29/29). Discriminator at val[0x10] (0=ADS, nonzero=snapshot) is the sole reliable classifier. Counts match the claim's '956 ADS + 29 snapshots' exactly.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ADS-always-resident (E20). 0xB0 disk-proven (MD_SNAP_RA_006). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SNAP_RA_005.csv`
- corrected registry note: 985 entries / 111 images: 956 ADS (SS flags=0) + 29 snapshots (SS flags=2). Both discriminators (val[0x10] and val[0x02] HasSnapshot bit) agree perfectly

## Proof links
- `proofs/validation/MD_SNAP_RA_005.csv` (matrix) — 
