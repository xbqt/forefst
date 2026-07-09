# Dossier — MD_DATA_RA_009 (BEHAVIORAL)

**Claim (this audit tests):** MI $DATA (0x80): 40B keys, 40-288B values. Does NOT follow common 12B header. Contains extent/allocation metadata, NOT inline content. Each resident file has exactly 1 SI + 1+ MI entries.

**Canonical claim (reference_table.csv):** Metadata: MI $DATA (0x80): 40B keys, 40-288B values. Does NOT follow common 12B header. Contains extent/allocation metadata, NOT inline content. Each resident file has exactly 1 SI + 1+ MI entries.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — MI $DATA (marker 0x80000002): key length == 40 bytes on 100% of MI entries every version (v3.7:582/582, v3.9:2076/2076, v3.10:392/392, v3.14:72,255/72,255). Does NOT follow the 12B common header. Inner header size@0x00==0x88 on exactly the extent-bearing half (the rest are 0x0-summary stubs).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- E2/RD: multi-instance $DATA (marker 0x80000002, 1567 observed) has variable value sizes and no 4B-zero header. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DATA_RA_009.csv`
- corrected registry note: MI $DATA values never contain content extractable as file bytes. Key is 40B (vs SI 16B).

## Proof links
- `proofs/validation/MD_DATA_RA_009.csv` (matrix) — 
