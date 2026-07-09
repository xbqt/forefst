# Dossier — CT_BKRC_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** BRC key = start_lcn(u64) + block_count(u64 always 0x400). Value = 1024 per-cluster u16: bit 15=shared/dedup-managed, bit 14=dedup metadata flag, bits 13:0=reference count (0-505 observed). Value header at +0x18 = TotalRefCount (u32) == Sum(array entry & 0x3FFF), upper 16 bits always 0 (230/230 rows, master B.6).

**Canonical claim (reference_table.csv):** Content: BRC key = start_lcn(u64) + block_count(u64 always 0x400). Value = 1024 per-cluster u16: bit 15=shared/dedup-managed, bit 14=dedup metadata flag, bits 13:0=reference count (0-505 observed). Value header at +0x18 = TotalRefCount (u32) == Sum(array entry & 0x3FFF), upper 16 bits always 0 (230/230 rows, master B.6).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — cluster_count 0x400, one entry/cluster, 230/230

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- BRC block_count is 0x400 for full ranges; the audit found a single partial/final range per volume that differs (winsider 1/108, test2 1/45). The 16-byte key structure is disk-proven in CT_BKRC_RA_001. Cited with the partial-range caveat.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_BKRC_RA_002.csv`
- corrected registry note: CORRECTED 2026-06-19 (master B.6): +0x18 = TotalRefCount = Sum(entry&0x3FFF), re-confirmed 230/230 rows 2026-06-17. The earlier 'compound field / 67/97 violations / not simple total' reading was a 2026-06-16 citation error, retracted. | 97 BRC rows on win11refs8gdedup.raw; 99328 tracked clusters; val+0x18 has 67/97 violations as simple sum

## Proof links
- `proofs/validation/CT_BKRC_RA_002.csv` (matrix) — 
